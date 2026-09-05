"""
MISSION KNOWLEDGE GRAPH — 3D POST-MISSION ANALYTICS EXPLORER
DRDO / iDEX Problem Statement ID: 26054

A native Blender application that renders every simulated mission in report_dump/ as
a glowing node in 3D space. Zoom into a mission and it opens like a molecule: one
child node per post-mission report the simulation actually produced. Click a child
and that report opens in the viewer.

    Scan report_dump/  ->  Mission nodes  ->  Report child nodes  ->  Report viewer

Nothing about the graph is hard-coded. The node tree is built entirely from what is
on disk, so a new mission folder or a new report category appears automatically on
the next scan, and a missing category simply draws no node.

Rendering is fully immediate-mode: node positions are projected on the CPU with
numpy and drawn as additive glow sprites straight into the viewport overlay. No
scene objects, no dependency-graph evaluation and no render pipeline are involved,
which is what keeps the whole thing at the 143 FPS timer budget while orbiting.

Controls
  [LMB drag]      Orbit the graph
  [LMB click]     Open a mission node / open a report
  [Wheel]         Zoom (over the graph) · Scroll (over an open report)
  [ESC]           Back one level — report, then mission, then exit
  [R]             Re-scan report_dump/
  [F]             Reframe the camera
"""

import bpy
import gpu
import blf
import math
import os
import sys
import time
import numpy as np
from gpu_extras.batch import batch_for_shader

# The two report modules live beside this file. Blender's bundled Python does not
# have the repo on its path, so put this directory on it before importing them.
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import report_scanner
import report_formatter


# ─────────────────────────────────────────────────────────────────────────────
# 1. VISUAL CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
TARGET_FPS = 143.0

GLOBE_RADIUS = 13.0          # world radius the mission nodes sit on
GLOBE_CAM_DIST = 42.0        # camera distance in globe mode
MISSION_CAM_DIST = 9.2       # camera distance once a mission is opened
REPORT_RING_RADIUS = 3.4     # radius of the child-report shell around a mission
DUST_COUNT = 1500            # ambient shell particles — pure atmosphere, never picked
NEIGHBOUR_LINKS = 2          # inter-mission web edges per node

CAM_SMOOTH = 11.0            # exponential camera follow rate (higher = snappier)
ANIM_SMOOTH = 9.0            # expansion / panel transition rate
GLOBE_SPIN = 0.045           # idle turntable rate, radians/sec
ORBIT_SENSITIVITY = 0.0075
ZOOM_STEP = 0.86
CLICK_SLOP_PX = 6            # drag further than this and it is an orbit, not a click

SEVERITY_COLORS = {
    "NOMINAL":  (0.30, 0.95, 0.72),
    "NORMAL":   (0.30, 0.95, 0.72),
    "ADVISORY": (0.40, 0.74, 1.00),
    "CAUTION":  (0.40, 0.74, 1.00),
    "WARNING":  (1.00, 0.66, 0.20),
    "CRITICAL": (1.00, 0.30, 0.32),
}

CLR_CHROME      = (0.00, 0.85, 1.00)
CLR_TEXT        = (0.88, 0.93, 0.98)
CLR_TEXT_DIM    = (0.50, 0.60, 0.72)
CLR_PANEL       = (0.020, 0.035, 0.060, 0.94)
CLR_PANEL_EDGE  = (0.00, 0.62, 0.88, 0.55)

# Text styling per formatted line kind: (point size, colour, top gap, bottom gap)
LINE_STYLES = {
    "h1":     (21, (0.00, 0.90, 1.00), 12, 8),
    "h2":     (16, (0.55, 0.86, 1.00), 12, 4),
    "kv":     (14, CLR_TEXT,            0, 0),
    "text":   (14, (0.74, 0.82, 0.90),  0, 0),
    "bullet": (15, (0.98, 0.92, 0.66),  4, 0),
    "rule":   (14, CLR_TEXT_DIM,        6, 6),
    "blank":  (14, CLR_TEXT_DIM,        0, 0),
}

_UNIT_CIRCLE = [(math.cos(a), math.sin(a))
                for a in np.linspace(0.0, math.tau, 21)]


# ─────────────────────────────────────────────────────────────────────────────
# 2. GRAPH MODEL
# ─────────────────────────────────────────────────────────────────────────────
class VisualNode:
    """A drawable node. `home` is its resting position, `pos` the animated one."""

    __slots__ = ("kind", "home", "pos", "color", "radius", "label", "detail",
                 "mission", "report", "alpha", "pulse")

    def __init__(self, kind, home, color, radius, label, detail,
                 mission=None, report=None):
        self.kind = kind                 # 'mission' | 'report'
        self.home = np.asarray(home, dtype=np.float64)
        self.pos = self.home.copy()
        self.color = color
        self.radius = radius             # world-space radius
        self.label = label
        self.detail = detail
        self.mission = mission
        self.report = report
        self.alpha = 1.0
        self.pulse = 0.0


class MissionGraph:
    """
    The scanned report_dump/ turned into positioned nodes and edges.

    Rebuilt wholesale on every scan — it is a few hundred numpy rows, so there is no
    incremental-update machinery to get wrong.
    """

    def __init__(self, root=None):
        self.root = root or report_scanner.default_report_root()
        self.missions = []
        self.mission_nodes = []
        self.web_edges = []              # (index_a, index_b) into mission_nodes
        self.dust = np.zeros((0, 3))
        self.dust_alpha = np.zeros(0)
        self.scan_error = None
        self.rescan()

    def rescan(self):
        try:
            self.missions = report_scanner.scan(self.root)
            self.scan_error = None
        except OSError as e:
            self.missions = []
            self.scan_error = str(e)

        count = len(self.missions)
        radius = GLOBE_RADIUS * (0.55 + 0.45 * min(1.0, count / 24.0)) if count else GLOBE_RADIUS
        points = _fibonacci_sphere(count) * radius

        self.mission_nodes = []
        for i, mission in enumerate(self.missions):
            color = SEVERITY_COLORS.get(mission.severity, SEVERITY_COLORS["NOMINAL"])
            # Node size carries information: a mission that produced more reports and
            # more faults reads as a bigger, brighter hub at a glance.
            weight = 1.0 + 0.06 * len(mission.reports) + 0.05 * float(mission.manifest.get("fault_count") or 0)
            self.mission_nodes.append(VisualNode(
                kind="mission",
                home=points[i],
                color=color,
                radius=0.30 * min(weight, 2.2),
                label=mission.title,
                detail=mission.subtitle,
                mission=mission,
            ))

        self.web_edges = _nearest_neighbour_edges(points, NEIGHBOUR_LINKS)
        self._build_dust(radius)

    def _build_dust(self, radius):
        """Static ambient shell — deterministic, so the field never flickers or reshuffles."""
        rng = np.random.default_rng(26054)
        directions = rng.normal(size=(DUST_COUNT, 3))
        directions /= np.linalg.norm(directions, axis=1, keepdims=True)
        shell = radius * (1.0 + rng.normal(scale=0.16, size=(DUST_COUNT, 1)))
        self.dust = directions * shell
        self.dust_alpha = rng.uniform(0.10, 0.55, size=DUST_COUNT)

    def build_report_nodes(self, mission_node):
        """Child nodes for one mission — one per report file actually on disk."""
        mission = mission_node.mission
        reports = mission.reports
        offsets = _fibonacci_sphere(len(reports)) * REPORT_RING_RADIUS
        nodes = []
        for i, report in enumerate(reports):
            nodes.append(VisualNode(
                kind="report",
                home=mission_node.home + offsets[i],
                color=report.color,
                radius=0.20,
                label=report.label,
                detail=report.filename,
                mission=mission,
                report=report,
            ))
            nodes[-1].pos = mission_node.home.copy()   # animates outward from the parent
        return nodes


def _fibonacci_sphere(n):
    """Evenly distributed unit-sphere points — the layout behind the globe."""
    if n <= 0:
        return np.zeros((0, 3))
    if n == 1:
        return np.array([[0.0, 0.0, 0.0]])
    idx = np.arange(n, dtype=np.float64)
    z = 1.0 - 2.0 * idx / (n - 1)
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    theta = idx * (math.pi * (3.0 - math.sqrt(5.0)))
    return np.stack([np.cos(theta) * r, np.sin(theta) * r, z], axis=1)


def _nearest_neighbour_edges(points, k):
    """Sparse proximity web between missions, so the globe reads as a connected fleet."""
    n = len(points)
    if n < 2:
        return []
    deltas = points[:, None, :] - points[None, :, :]
    dist = np.linalg.norm(deltas, axis=2)
    np.fill_diagonal(dist, np.inf)
    edges = set()
    for i in range(n):
        for j in np.argsort(dist[i])[:k]:
            edges.add((min(i, int(j)), max(i, int(j))))
    return sorted(edges)


# ─────────────────────────────────────────────────────────────────────────────
# 3. ORBIT CAMERA & CPU PROJECTION
# ─────────────────────────────────────────────────────────────────────────────
class OrbitCamera:
    """
    Smoothed turntable camera. Every value chases a target exponentially, which is
    what makes flying between the globe and a single mission feel continuous rather
    than cut.
    """

    def __init__(self):
        self.target = np.zeros(3)
        self.want_target = np.zeros(3)
        self.azimuth = 0.7
        self.want_azimuth = 0.7
        self.elevation = 0.22
        self.want_elevation = 0.22
        self.distance = GLOBE_CAM_DIST
        self.want_distance = GLOBE_CAM_DIST
        self.fov = math.radians(48.0)

    def reset(self):
        self.want_target = np.zeros(3)
        self.want_distance = GLOBE_CAM_DIST
        self.want_elevation = 0.22

    def focus(self, position, distance):
        self.want_target = np.asarray(position, dtype=np.float64).copy()
        self.want_distance = distance

    def orbit(self, dx, dy):
        self.want_azimuth -= dx * ORBIT_SENSITIVITY
        self.want_elevation = _clamp(self.want_elevation + dy * ORBIT_SENSITIVITY, -1.45, 1.45)

    def zoom(self, direction):
        factor = ZOOM_STEP if direction > 0 else 1.0 / ZOOM_STEP
        self.want_distance = _clamp(self.want_distance * factor, 2.4, 140.0)

    def update(self, dt, spin):
        self.want_azimuth += spin * dt
        k = 1.0 - math.exp(-CAM_SMOOTH * dt)
        self.azimuth += (self.want_azimuth - self.azimuth) * k
        self.elevation += (self.want_elevation - self.elevation) * k
        self.distance += (self.want_distance - self.distance) * k
        self.target += (self.want_target - self.target) * k

    def projector(self, width, height, center_shift_x):
        """
        Returns (project_fn, eye, scale).

        project_fn maps an (N, 3) world array to screen x, y and camera depth.
        `scale` converts a world-space radius at depth d into pixels: r_px = r * scale / d.
        """
        ce, se = math.cos(self.elevation), math.sin(self.elevation)
        ca, sa = math.cos(self.azimuth), math.sin(self.azimuth)
        eye = self.target + self.distance * np.array([ce * sa, ce * ca, se])

        forward = _normalize(self.target - eye)
        right = _normalize(np.cross(forward, np.array([0.0, 0.0, 1.0])))
        up = np.cross(right, forward)
        basis = np.stack([right, up, -forward])          # world -> camera rows

        scale = (1.0 / math.tan(self.fov * 0.5)) * (height * 0.5)
        cx = width * 0.5 + center_shift_x
        cy = height * 0.5

        def project(points):
            cam = (points - eye) @ basis.T
            depth = np.maximum(-cam[:, 2], 1e-4)
            sx = cx + cam[:, 0] / depth * scale
            sy = cy + cam[:, 1] / depth * scale
            return sx, sy, depth

        return project, eye, scale


def _normalize(vector):
    length = float(np.linalg.norm(vector))
    return vector / length if length > 1e-9 else np.array([0.0, 0.0, 1.0])


def _clamp(value, low, high):
    return low if value < low else (high if value > high else value)


def _ease_out(t):
    return 1.0 - (1.0 - t) ** 3


# ─────────────────────────────────────────────────────────────────────────────
# 4. IMMEDIATE-MODE GPU PAINTER
# ─────────────────────────────────────────────────────────────────────────────
class Painter:
    """Thin wrapper over the builtin GPU shaders — every draw call in the app goes through here."""

    def __init__(self):
        self._uniform = None
        self._smooth = None
        self._flat = None
        self.font = 0

    def _shader(self, name, cache_attr):
        shader = getattr(self, cache_attr)
        if shader is None:
            shader = gpu.shader.from_builtin(name)
            setattr(self, cache_attr, shader)
        return shader

    # --- flat 2D primitives -------------------------------------------------

    def rect(self, x, y, w, h, color):
        shader = self._shader('UNIFORM_COLOR', '_uniform')
        verts = [(x, y, 0.0), (x + w, y, 0.0), (x + w, y + h, 0.0), (x, y + h, 0.0)]
        batch = batch_for_shader(shader, 'TRIS', {"pos": verts}, indices=[(0, 1, 2), (0, 2, 3)])
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)

    def outline(self, x, y, w, h, color):
        shader = self._shader('UNIFORM_COLOR', '_uniform')
        verts = [(x, y, 0.0), (x + w, y, 0.0), (x + w, y + h, 0.0), (x, y + h, 0.0)]
        batch = batch_for_shader(shader, 'LINE_LOOP', {"pos": verts})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)

    def lines(self, verts, colors):
        if not verts:
            return
        shader = self._shader('SMOOTH_COLOR', '_smooth')
        batch = batch_for_shader(shader, 'LINES', {"pos": verts, "color": colors})
        shader.bind()
        batch.draw(shader)

    def tris(self, verts, colors, indices):
        if not verts:
            return
        shader = self._shader('SMOOTH_COLOR', '_smooth')
        batch = batch_for_shader(shader, 'TRIS', {"pos": verts, "color": colors}, indices=indices)
        shader.bind()
        batch.draw(shader)

    def points(self, verts, colors, size):
        if not verts:
            return
        shader = self._shader('FLAT_COLOR', '_flat')
        gpu.state.point_size_set(size)
        batch = batch_for_shader(shader, 'POINTS', {"pos": verts, "color": colors})
        shader.bind()
        batch.draw(shader)

    # --- text ---------------------------------------------------------------

    def text(self, string, x, y, size, color, alpha=1.0):
        blf.size(self.font, size)
        blf.position(self.font, x, y, 0)
        blf.color(self.font, color[0], color[1], color[2], alpha)
        blf.draw(self.font, string)

    def text_width(self, string, size):
        blf.size(self.font, size)
        return blf.dimensions(self.font, string)[0]


def build_glow(cx, cy, radius, color, alpha):
    """
    Vertices for one node: a soft halo disc plus a bright core, drawn additively.

    Returned as (verts, colors, indices) fans so a whole frame's worth of nodes can
    be uploaded as a single batch instead of one draw call each.
    """
    verts, colors, indices = [], [], []

    for layer_radius, layer_alpha in ((radius * 3.2, alpha * 0.22), (radius, alpha * 0.95)):
        base = len(verts)
        verts.append((cx, cy, 0.0))
        colors.append((color[0], color[1], color[2], layer_alpha))
        for ox, oy in _UNIT_CIRCLE:
            verts.append((cx + ox * layer_radius, cy + oy * layer_radius, 0.0))
            colors.append((color[0], color[1], color[2], 0.0))
        for i in range(len(_UNIT_CIRCLE) - 1):
            indices.append((base, base + 1 + i, base + 2 + i))

    return verts, colors, indices


# ─────────────────────────────────────────────────────────────────────────────
# 5. REPORT VIEWER PANEL
# ─────────────────────────────────────────────────────────────────────────────
class ReportViewer:
    """
    Holds one opened report. Content is read from disk at open time only, wrapped
    once for the current panel width, and then drawn as a virtualised window over
    the wrapped lines — so an 18-hour telemetry debrief scrolls as cheaply as a
    three-line summary.
    """

    def __init__(self):
        self.report = None
        self.mission = None
        self.lines = []
        self.wrapped = []
        self.scroll = 0.0
        self.max_scroll = 0.0
        self.wrap_width = 0
        self.error = None

    @property
    def is_open(self):
        return self.report is not None

    def open(self, mission, report):
        self.mission = mission
        self.report = report
        self.scroll = 0.0
        self.wrap_width = 0
        self.wrapped = []
        loaded = report_scanner.load_report(report.path)
        self.error = loaded.get("text") if loaded.get("kind") == "error" else None
        self.lines = report_formatter.format_report(loaded, report.label, report.path)

    def close(self):
        self.report = None
        self.mission = None
        self.lines = []
        self.wrapped = []

    def scroll_by(self, amount):
        self.scroll = _clamp(self.scroll + amount, 0.0, self.max_scroll)

    def ensure_wrapped(self, painter, char_limit):
        """Re-wrap only when the available width actually changed."""
        if char_limit == self.wrap_width and self.wrapped:
            return
        self.wrap_width = char_limit
        self.wrapped = []
        for kind, primary, secondary, indent in self.lines:
            budget = max(16, char_limit - indent * 3)
            if kind == "kv":
                self.wrapped.append((kind, primary, secondary, indent))
                continue
            if kind in ("rule", "blank"):
                self.wrapped.append((kind, "", "", indent))
                continue
            for chunk in _wrap_text(primary, budget):
                self.wrapped.append((kind, chunk, "", indent))


def _wrap_text(text, budget):
    if not text:
        return [""]
    if len(text) <= budget:
        return [text]
    out, current = [], ""
    for word in text.split(" "):
        while len(word) > budget:               # a single unbreakable token
            if current:
                out.append(current)
                current = ""
            out.append(word[:budget])
            word = word[budget:]
        candidate = word if not current else current + " " + word
        if len(candidate) <= budget:
            current = candidate
        else:
            out.append(current)
            current = word
    if current:
        out.append(current)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 6. APPLICATION STATE
# ─────────────────────────────────────────────────────────────────────────────
class ExplorerState:
    def __init__(self):
        self.graph = MissionGraph()
        self.camera = OrbitCamera()
        self.viewer = ReportViewer()

        self.selected = None              # selected mission VisualNode
        self.report_nodes = []
        self.expand = 0.0                 # 0 = globe, 1 = mission fully opened
        self.want_expand = 0.0
        self.panel = 0.0                  # 0 = no report panel, 1 = fully open
        self.want_panel = 0.0

        self.hover = None
        self.mouse = (0, 0)
        self.dragging = False
        self.drag_moved = 0
        self.drag_origin = (0, 0)
        self.last_tick = time.perf_counter()

        # Filled by the draw handler, consumed by picking on the next event.
        self.screen_nodes = []            # (node, sx, sy, radius_px)
        self.region_size = (1920, 1080)
        self.status = ""
        self.status_until = 0.0

    # --- navigation ---------------------------------------------------------

    def open_mission(self, node):
        if self.selected is node:
            return
        self.selected = node
        self.report_nodes = self.graph.build_report_nodes(node)
        self.want_expand = 1.0
        self.camera.focus(node.home, MISSION_CAM_DIST)
        self.viewer.close()
        self.want_panel = 0.0

    def open_report(self, node):
        self.viewer.open(node.mission, node.report)
        self.want_panel = 1.0

    def back(self):
        """One step out. Returns False when there is nothing left to close."""
        if self.viewer.is_open:
            self.viewer.close()
            self.want_panel = 0.0
            return True
        if self.selected is not None:
            self.selected = None
            self.report_nodes = []
            self.want_expand = 0.0
            self.camera.reset()
            return True
        return False

    def rescan(self):
        self.selected = None
        self.report_nodes = []
        self.want_expand = 0.0
        self.viewer.close()
        self.want_panel = 0.0
        self.graph.rescan()
        self.camera.reset()
        self.flash(f"Rescanned — {len(self.graph.missions)} mission"
                   f"{'s' if len(self.graph.missions) != 1 else ''} found")

    def flash(self, message, seconds=2.6):
        self.status = message
        self.status_until = time.time() + seconds

    # --- per-frame ----------------------------------------------------------

    def tick(self):
        now = time.perf_counter()
        dt = _clamp(now - self.last_tick, 0.001, 0.05)
        self.last_tick = now

        spin = GLOBE_SPIN if (self.selected is None and not self.dragging) else 0.0
        self.camera.update(dt, spin)

        k = 1.0 - math.exp(-ANIM_SMOOTH * dt)
        self.expand += (self.want_expand - self.expand) * k
        self.panel += (self.want_panel - self.panel) * k

        # Report nodes bloom outward from their parent as the mission opens.
        if self.selected is not None and self.report_nodes:
            t = _ease_out(_clamp(self.expand, 0.0, 1.0))
            parent = self.selected.home
            for node in self.report_nodes:
                node.pos = parent + (node.home - parent) * t
                node.alpha = t
        return dt

    def pick(self, mx, my):
        """Nearest node under the cursor, nearest-in-depth wins ties."""
        best, best_score = None, None
        for node, sx, sy, radius in self.screen_nodes:
            reach = max(radius * 1.9, 14.0)
            dx, dy = mx - sx, my - sy
            distance = math.hypot(dx, dy)
            if distance <= reach and (best_score is None or distance < best_score):
                best, best_score = node, distance
        return best


# ─────────────────────────────────────────────────────────────────────────────
# 7. RENDERER
# ─────────────────────────────────────────────────────────────────────────────
class Renderer:
    def __init__(self):
        self.painter = Painter()

    def draw(self, state, width, height):
        state.region_size = (width, height)
        painter = self.painter

        panel_t = _ease_out(_clamp(state.panel, 0.0, 1.0))
        panel_width = min(880.0, width * 0.52) * panel_t
        project, _eye, scale = state.camera.projector(width, height, -panel_width * 0.5)

        gpu.state.blend_set('ALPHA')
        painter.rect(0, 0, width, height, (0.008, 0.012, 0.022, 1.0))

        gpu.state.blend_set('ADDITIVE')
        self._draw_dust(state, project, width, height)
        self._draw_edges(state, project, scale)
        self._draw_nodes(state, project, scale, width, height)

        gpu.state.blend_set('ALPHA')
        self._draw_labels(state)
        self._draw_chrome(state, width, height)
        if panel_t > 0.004:
            self._draw_report_panel(state, width, height, panel_width)
        self._draw_hover(state)
        gpu.state.blend_set('NONE')

    # --- 3D layers ----------------------------------------------------------

    def _draw_dust(self, state, project, width, height):
        dust = state.graph.dust
        if not len(dust):
            return
        sx, sy, depth = project(dust)
        visible = (depth > 0.05) & (sx > -40) & (sx < width + 40) & (sy > -40) & (sy < height + 40)
        if not visible.any():
            return

        fade = 1.0 - 0.72 * _clamp(state.expand, 0.0, 1.0)
        # Far particles dim out, which is what gives the shell its volume.
        near = np.clip(1.0 - (depth[visible] / (state.camera.distance * 2.2)), 0.05, 1.0)
        alpha = state.graph.dust_alpha[visible] * near * fade

        verts = np.stack([sx[visible], sy[visible], np.zeros(visible.sum())], axis=1).tolist()
        colors = np.stack([
            np.full(len(verts), 0.62), np.full(len(verts), 0.78),
            np.full(len(verts), 0.95), alpha,
        ], axis=1).tolist()
        self.painter.points(verts, colors, 2.0)

    def _draw_edges(self, state, project, scale):
        nodes = state.graph.mission_nodes
        if not nodes:
            return

        verts, colors = [], []
        dim = 1.0 - 0.85 * _clamp(state.expand, 0.0, 1.0)

        if dim > 0.02 and state.graph.web_edges:
            positions = np.array([n.pos for n in nodes])
            sx, sy, depth = project(positions)
            for a, b in state.graph.web_edges:
                if depth[a] <= 0.05 or depth[b] <= 0.05:
                    continue
                tint = (0.18, 0.72, 0.66, 0.16 * dim)
                verts.append((float(sx[a]), float(sy[a]), 0.0))
                colors.append(tint)
                verts.append((float(sx[b]), float(sy[b]), 0.0))
                colors.append(tint)

        # Mission -> report spokes: bright at the parent, fading into each child.
        if state.selected is not None and state.report_nodes:
            parent = np.array([state.selected.pos])
            psx, psy, pdepth = project(parent)
            if pdepth[0] > 0.05:
                child_positions = np.array([n.pos for n in state.report_nodes])
                csx, csy, cdepth = project(child_positions)
                for i, node in enumerate(state.report_nodes):
                    if cdepth[i] <= 0.05:
                        continue
                    r, g, b = node.color
                    verts.append((float(psx[0]), float(psy[0]), 0.0))
                    colors.append((r, g, b, 0.42 * node.alpha))
                    verts.append((float(csx[i]), float(csy[i]), 0.0))
                    colors.append((r, g, b, 0.10 * node.alpha))

        self.painter.lines(verts, colors)

    def _draw_nodes(self, state, project, scale, width, height):
        drawable = list(state.graph.mission_nodes) + list(state.report_nodes)
        if not drawable:
            state.screen_nodes = []
            return

        positions = np.array([n.pos for n in drawable])
        sx, sy, depth = project(positions)

        dim_others = 1.0 - 0.86 * _clamp(state.expand, 0.0, 1.0)
        verts, colors, indices = [], [], []
        screen_nodes = []
        pulse = 0.5 + 0.5 * math.sin(time.time() * 2.4)

        # Painter's algorithm: far nodes first so near glows layer on top.
        for i in np.argsort(-depth):
            node = drawable[i]
            d = float(depth[i])
            if d <= 0.05:
                continue
            x, y = float(sx[i]), float(sy[i])
            if x < -160 or x > width + 160 or y < -160 or y > height + 160:
                continue

            radius = _clamp(node.radius * scale / d, 2.0, 90.0)

            alpha = node.alpha
            if node.kind == "mission":
                alpha *= 1.0 if node is state.selected else dim_others
            if node is state.hover:
                alpha = min(1.0, alpha * 1.35 + 0.15)
                radius *= 1.18
            if node is state.selected:
                radius *= 1.0 + 0.06 * pulse
            if alpha <= 0.012:
                continue

            base = len(verts)
            v, c, idx = build_glow(x, y, radius, node.color, alpha)
            verts.extend(v)
            colors.extend(c)
            indices.extend([(a + base, b + base, cc + base) for a, b, cc in idx])
            screen_nodes.append((node, x, y, radius))

        self.painter.tris(verts, colors, indices)
        state.screen_nodes = screen_nodes

    # --- 2D overlays --------------------------------------------------------

    def _draw_labels(self, state):
        """
        Labels only where they help: the opened mission's children are always named,
        mission nodes only when the globe is not too crowded to read.
        """
        painter = self.painter
        lookup = {id(node): (x, y, r) for node, x, y, r in state.screen_nodes}

        if state.selected is None:
            show_missions = len(state.graph.mission_nodes) <= 28
            for node in state.graph.mission_nodes:
                placed = lookup.get(id(node))
                if not placed or (not show_missions and node is not state.hover):
                    continue
                x, y, r = placed
                painter.text(node.label, x + r + 9, y - 5, 13, node.color, 0.92)
        else:
            for node in state.report_nodes:
                placed = lookup.get(id(node))
                if not placed or node.alpha < 0.35:
                    continue
                x, y, r = placed
                painter.text(node.label, x + r + 9, y - 5, 14, node.color, node.alpha)

            placed = lookup.get(id(state.selected))
            if placed:
                x, y, r = placed
                painter.text(state.selected.label, x + r + 10, y + 12, 17, CLR_CHROME, 1.0)

    def _draw_chrome(self, state, width, height):
        painter = self.painter
        missions = state.graph.missions

        # Header
        header_h = 62
        hy = height - header_h
        painter.rect(0, hy, width, header_h, (0.015, 0.028, 0.048, 0.92))
        painter.rect(0, hy, width, 1.5, (*CLR_CHROME, 0.35))
        painter.text("MISSION KNOWLEDGE GRAPH  //  POST-MISSION ANALYTICS EXPLORER",
                     26, hy + 34, 19, CLR_CHROME)
        painter.text(f"DRDO / iDEX PS-26054   ·   report_dump/   ·   "
                     f"{len(missions)} mission{'s' if len(missions) != 1 else ''} indexed",
                     26, hy + 14, 13, CLR_TEXT_DIM)

        # Breadcrumb
        crumb = "FLEET"
        if state.selected is not None:
            crumb += f"   ›   {state.selected.label}"
        if state.viewer.is_open:
            crumb += f"   ›   {state.viewer.report.label}"
        painter.text(crumb, width - 26 - painter.text_width(crumb, 14), hy + 24, 14, CLR_TEXT)

        # Footer hints
        painter.rect(0, 0, width, 34, (0.015, 0.028, 0.048, 0.88))
        hint = ("LMB DRAG  Orbit      LMB  Open node      WHEEL  Zoom / Scroll      "
                "ESC  Back      R  Rescan      F  Reframe")
        painter.text(hint, 26, 12, 12, CLR_TEXT_DIM)

        # Empty / error states
        if not missions:
            message = ("report_dump/ is empty — run a mission to generate reports"
                       if state.graph.scan_error is None else state.graph.scan_error)
            painter.text(message,
                         width * 0.5 - painter.text_width(message, 16) * 0.5,
                         height * 0.5, 16, CLR_TEXT_DIM)

        # Transient status toast
        if state.status and time.time() < state.status_until:
            w = painter.text_width(state.status, 14)
            painter.rect(width * 0.5 - w * 0.5 - 16, 52, w + 32, 32, (0.02, 0.06, 0.10, 0.92))
            painter.outline(width * 0.5 - w * 0.5 - 16, 52, w + 32, 32, CLR_PANEL_EDGE)
            painter.text(state.status, width * 0.5 - w * 0.5, 62, 14, CLR_CHROME)

    def _draw_hover(self, state):
        node = state.hover
        if node is None or state.viewer.is_open:
            return
        placed = next((p for p in state.screen_nodes if p[0] is node), None)
        if not placed:
            return

        painter = self.painter
        _, x, y, r = placed
        lines = [node.label] + ([node.detail] if node.detail else [])
        if node.kind == "mission":
            manifest = node.mission.manifest
            lines.append(f"{len(node.mission.reports)} reports  ·  health "
                         f"{manifest.get('health_index_end', '—')}  ·  {node.mission.severity}")
        width_px = max(painter.text_width(line, 13) for line in lines) + 26
        height_px = 16 * len(lines) + 18

        bx, by = x + r + 14, y - height_px * 0.5
        bx = min(bx, state.region_size[0] - width_px - 12)
        by = _clamp(by, 44, state.region_size[1] - height_px - 74)

        painter.rect(bx, by, width_px, height_px, CLR_PANEL)
        painter.outline(bx, by, width_px, height_px, (*node.color, 0.6))
        for i, line in enumerate(lines):
            painter.text(line, bx + 13, by + height_px - 20 - i * 16, 13,
                         node.color if i == 0 else CLR_TEXT_DIM)

    def _draw_report_panel(self, state, width, height, panel_width):
        viewer = state.viewer
        if not viewer.lines or panel_width < 4:
            return

        painter = self.painter
        x0 = width - panel_width
        top = height - 62
        bottom = 34
        inner_x = x0 + 30
        inner_w = panel_width - 60

        painter.rect(x0, bottom, panel_width, top - bottom, CLR_PANEL)
        painter.rect(x0, bottom, 1.5, top - bottom, (*CLR_CHROME, 0.45))

        # Wrapping depends only on the panel width, so it is done once per resize.
        char_w = max(1.0, painter.text_width("MMMMMMMMMM", 14) / 10.0)
        viewer.ensure_wrapped(painter, int(inner_w / char_w))

        # Title block
        cursor = top - 34
        painter.text(viewer.report.label, inner_x, cursor, 20, viewer.report.color)
        cursor -= 22
        subtitle = f"{viewer.mission.title}   ·   {viewer.report.filename}"
        painter.text(subtitle, inner_x, cursor, 12, CLR_TEXT_DIM)
        cursor -= 16
        painter.rect(inner_x, cursor, inner_w, 1.0, (*CLR_CHROME, 0.28))
        cursor -= 14

        body_top = cursor
        body_height = body_top - bottom - 16

        # Measure the document once so the scrollbar and clamp are exact.
        heights = [self._line_height(kind) for kind, _, _, _ in viewer.wrapped]
        total = float(sum(heights))
        viewer.max_scroll = max(0.0, total - body_height)
        viewer.scroll = _clamp(viewer.scroll, 0.0, viewer.max_scroll)

        blf.enable(painter.font, blf.CLIPPING)
        blf.clipping(painter.font, x0, bottom, width, top - 4)

        # Virtualised draw: skip everything scrolled past, stop once past the bottom.
        y = body_top + viewer.scroll
        for i, (kind, primary, secondary, indent) in enumerate(viewer.wrapped):
            step = heights[i]
            y -= step
            if y > body_top + 4:
                continue
            if y < bottom - 20:
                break
            size, color, _, _ = LINE_STYLES.get(kind, LINE_STYLES["text"])
            x = inner_x + indent * 18

            if kind == "rule":
                painter.rect(x, y + 8, inner_w - indent * 18, 1.0, (*CLR_TEXT_DIM, 0.25))
            elif kind == "kv":
                key = f"{primary}"
                painter.text(key, x, y, size, CLR_TEXT_DIM)
                painter.text(secondary, x + min(230, inner_w * 0.42), y, size, CLR_TEXT)
            elif kind == "bullet":
                painter.rect(x, y + 5, 5, 5, (*color, 0.85))
                painter.text(primary, x + 14, y, size, color)
            elif kind != "blank":
                painter.text(primary, x, y, size, color)

        blf.disable(painter.font, blf.CLIPPING)

        # Scrollbar
        if viewer.max_scroll > 1.0:
            track_h = body_height
            thumb_h = max(30.0, track_h * (body_height / max(total, 1.0)))
            travel = track_h - thumb_h
            offset = travel * (viewer.scroll / viewer.max_scroll)
            painter.rect(width - 10, bottom + 16, 3, track_h, (*CLR_TEXT_DIM, 0.18))
            painter.rect(width - 10, bottom + 16 + travel - offset, 3, thumb_h, (*CLR_CHROME, 0.55))

    @staticmethod
    def _line_height(kind):
        size, _, gap_top, gap_bottom = LINE_STYLES.get(kind, LINE_STYLES["text"])
        return size + 7 + gap_top + gap_bottom


# ─────────────────────────────────────────────────────────────────────────────
# 8. MODAL OPERATOR
# ─────────────────────────────────────────────────────────────────────────────
state = ExplorerState()
renderer = Renderer()


_draw_failed = False


def _draw_callback(context):
    global _draw_failed
    region = context.region
    if region is None:
        return
    try:
        renderer.draw(state, region.width, region.height)
    except Exception:
        # A draw handler that raises is removed by Blender and takes the whole viewport
        # down with it, so a dropped frame is always the better failure. Reported once
        # and once only — a per-frame traceback at 143 FPS would bury the console.
        if not _draw_failed:
            _draw_failed = True
            import traceback
            traceback.print_exc()


class OT_MissionGraphExplorer(bpy.types.Operator):
    bl_idname = "view3d.mission_graph_explorer"
    bl_label = "Mission Knowledge Graph Explorer"

    _timer = None
    _handle = None

    def invoke(self, context, event):
        if context.area is None or context.area.type != 'VIEW_3D':
            return {'CANCELLED'}

        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_callback, (context,), 'WINDOW', 'POST_PIXEL'
        )
        wm = context.window_manager
        self._timer = wm.event_timer_add(1.0 / TARGET_FPS, window=context.window)
        wm.modal_handler_add(self)
        state.last_tick = time.perf_counter()
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            state.tick()
            _redraw(context)
            return {'RUNNING_MODAL'}

        mx, my = event.mouse_region_x, event.mouse_region_y
        width, _height = state.region_size
        panel_x = width - min(880.0, width * 0.52) * _ease_out(_clamp(state.panel, 0.0, 1.0))
        over_panel = state.viewer.is_open and mx >= panel_x

        if event.type == 'MOUSEMOVE':
            if state.dragging:
                dx = mx - state.mouse[0]
                dy = my - state.mouse[1]
                state.drag_moved += abs(dx) + abs(dy)
                state.camera.orbit(dx, dy)
            else:
                state.hover = None if over_panel else state.pick(mx, my)
            state.mouse = (mx, my)
            return {'RUNNING_MODAL'}

        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            direction = 1 if event.type == 'WHEELUPMOUSE' else -1
            if over_panel:
                state.viewer.scroll_by(-direction * 90.0)
            else:
                state.camera.zoom(direction)
            _redraw(context)
            return {'RUNNING_MODAL'}

        if event.type in {'LEFTMOUSE', 'MIDDLEMOUSE'}:
            if event.value == 'PRESS':
                state.mouse = (mx, my)
                state.drag_origin = (mx, my)
                state.drag_moved = 0
                state.dragging = True
            elif event.value == 'RELEASE':
                was_click = state.drag_moved <= CLICK_SLOP_PX
                state.dragging = False
                if was_click and event.type == 'LEFTMOUSE' and not over_panel:
                    self._activate(state.pick(mx, my))
            return {'RUNNING_MODAL'}

        if event.value != 'PRESS':
            return {'RUNNING_MODAL'}

        if event.type in {'ESC', 'RIGHTMOUSE'}:
            if not state.back():
                self.cancel(context)
                _quit()
                return {'FINISHED'}
            _redraw(context)
            return {'RUNNING_MODAL'}

        if event.type == 'R':
            state.rescan()
            _redraw(context)
        elif event.type == 'F':
            if state.selected is not None:
                state.camera.focus(state.selected.home, MISSION_CAM_DIST)
            else:
                state.camera.reset()
            _redraw(context)

        return {'RUNNING_MODAL'}

    @staticmethod
    def _activate(node):
        if node is None:
            return
        if node.kind == "mission":
            state.open_mission(node)
        elif node.kind == "report":
            state.open_report(node)

    def cancel(self, context):
        if self._timer is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        if self._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self._handle = None
        _redraw(context)


def _redraw(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def _quit():
    """Close Blender itself — this app owns the whole window, so ESC at the top level exits."""
    try:
        bpy.ops.wm.quit_blender()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# 9. LAUNCH
# ─────────────────────────────────────────────────────────────────────────────
def configure_viewport():
    """Strip the viewport to a bare black canvas — everything visible is drawn by us."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("MissionGraph")
        bpy.context.scene.world = world
    world.use_nodes = False
    world.color = (0.004, 0.006, 0.012)

    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for space in area.spaces:
                if space.type != 'VIEW_3D':
                    continue
                space.shading.type = 'SOLID'
                space.shading.background_type = 'VIEWPORT'
                space.shading.background_color = (0.008, 0.012, 0.022)
                space.overlay.show_overlays = False
                space.show_gizmo = False
                space.show_region_toolbar = False
                space.show_region_ui = False
                space.show_region_header = False

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for region in area.regions:
                if region.type != 'WINDOW':
                    continue
                try:
                    with bpy.context.temp_override(window=window, area=area, region=region):
                        bpy.ops.screen.screen_full_area(use_hide_panels=True)
                        bpy.ops.view3d.mission_graph_explorer('INVOKE_DEFAULT')
                except Exception:
                    pass
                return


def register():
    try:
        bpy.utils.unregister_class(OT_MissionGraphExplorer)
    except Exception:
        pass
    bpy.utils.register_class(OT_MissionGraphExplorer)


def unregister():
    try:
        bpy.utils.unregister_class(OT_MissionGraphExplorer)
    except Exception:
        pass


if __name__ == "__main__":
    register()
    if "--test-mode" in sys.argv or bpy.app.background:
        print(f"[MISSION GRAPH] Headless check OK — "
              f"{len(state.graph.missions)} mission bundle(s) discovered in {state.graph.root}")
    else:
        bpy.app.timers.register(configure_viewport, first_interval=0.3)
