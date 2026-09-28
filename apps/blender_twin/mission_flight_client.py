"""Mission-Connected Blender Flight Cockpit (ARCH-2026-MP-001).

Reuses the proven photoreal environment/camera/terrain-radar code from
``standalone_canyon_flight_app.py`` (the good-looking, working manual-flight sim) but
replaces its manual W/S/A/D/E/Q flight loop with a client that polls the REAL mission
backend (``backend/mission/executive.py`` via the FastAPI REST API) and renders whatever
mission the web Mission Planner has launched: real waypoints, real autopilot-computed
position/heading/pitch/roll, real engine telemetry (RPM/CHT/EGT/oil), real faults.

This is a VISUALIZER, not a second physics engine: the backend's ``AutopilotFlightModel``
(backend/mission/kinematics.py) remains the single authoritative source of truth for where
the aircraft is and how it's flying. This script only reads that state and poses the UAV
object in Blender to match it -- exactly the same relationship the web app's
``apps/canyon_flight/index.html`` already has with the backend, just rendered through
Blender's EEVEE pipeline instead of Three.js/WebGL.

Coordinate mapping (verified against both assets' real DEM vertex data): the terrain
object in terrain.blend (``Copernicus_DSM_COG_10_N34_00_E077_00_DEM``) and the terrain GLB
served to the browser (``frontend/public/models/ladakh_canyon_terrain.glb``) are the same
real-world Copernicus DEM crop, in the SAME local coordinate convention as the backend's
ENU frame: Blender (x, y, z) = backend (pos_x_m, pos_y_m, pos_z_m) directly, no sign flip,
no rotation. This was confirmed by sampling matching elevations at matching coordinates in
both assets (e.g. ~3195m at ENU (657, 35338) in both).

Usage: launch via ``launch_mission_flight_client.bat`` (loads ``assets/models/terrain.blend``
and runs this script), with the backend server already running on port 8000 and a mission
loaded/started from the web Mission Planner.
"""

from __future__ import annotations

import json
import math
import time
import urllib.request
import urllib.error

import bpy
import mathutils

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
BACKEND_BASE_URL = "http://127.0.0.1:8000"
POLL_INTERVAL_SEC = 0.25          # 4 Hz poll of the real 20 Hz backend state -- cheap and
                                   # plenty smooth once interpolated visually between polls
UAV_NAME = "UAV_Predator_Master"  # reuse the rigged object already in terrain.blend
CAM_NAME = "Camera_UAV_Chase"
DEM_NAME = "Copernicus_DSM_COG_10_N34_00_E077_00_DEM"

CAM_DIST_BEHIND = 34.0
CAM_HEIGHT_ABOVE = 8.5
CAM_LOOK_AHEAD = 42.0
CAM_TURN_FOLLOW_FACTOR = 0.10
CAM_DEFAULT_LENS_MM = 38.0
CAM_SENSOR_WIDTH = 36.0
CAM_SENSOR_HEIGHT = 24.0


def _http_get_json(path: str, timeout: float = 0.5):
    """Fetches JSON from the mission backend. Returns None on any failure (offline
    backend, no mission loaded yet, etc.) -- the caller must tolerate a None gracefully
    rather than crash the Blender modal loop, since this poll runs every tick."""
    url = f"{BACKEND_BASE_URL}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _http_post_json(path: str, payload: dict, timeout: float = 0.5):
    url = f"{BACKEND_BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


class MissionClientState:
    """Visual state interpolated from the authoritative backend MissionState between polls,
    plus a small amount of local smoothing so 4 Hz backend updates still look like
    continuous 60fps flight rather than a stepped/jerky motion."""

    def __init__(self) -> None:
        self.connected = False
        self.last_poll_wall = 0.0
        self.backend_state: dict | None = None
        self.definition: dict | None = None

        # Rendered (smoothed) transform -- lags the raw backend state slightly via lerp,
        # same pattern the web canyon_flight app uses (uavSim.pos.lerp(targetPos, 0.12)).
        self.pos = mathutils.Vector((4000.0, 7500.0, 4572.0))
        self.heading_rad = math.radians(38.0)
        self.pitch_rad = 0.0
        self.roll_rad = 0.0
        self.rpm = 0.0

        self.cam_trailing_dir = None
        self.cam_world_pos = None

        self._logs: list[tuple[str, tuple]] = [
            ("[MISSION CLIENT] Polling backend at " + BACKEND_BASE_URL, (0.4, 0.8, 1.0, 1.0)),
        ]

    def poll(self) -> None:
        now = time.perf_counter()
        if now - self.last_poll_wall < POLL_INTERVAL_SEC:
            return
        self.last_poll_wall = now

        state = _http_get_json("/api/missions/state")
        if state is None:
            self.connected = False
            return
        self.connected = True
        self.backend_state = state

        if self.definition is None:
            self.definition = _http_get_json("/api/missions/definition")

    def target_pose(self) -> tuple[mathutils.Vector, float, float, float, float]:
        """Returns (pos, heading_rad, pitch_rad, roll_rad, rpm) straight from the last
        polled authoritative backend state -- the thing this client's rendered pose lerps
        toward every frame."""
        s = self.backend_state
        if s is None:
            return self.pos, self.heading_rad, self.pitch_rad, self.roll_rad, self.rpm
        pos = mathutils.Vector((
            float(s.get("pos_x_m", self.pos.x)),
            float(s.get("pos_y_m", self.pos.y)),
            float(s.get("pos_z_m", self.pos.z)),
        ))
        heading = math.radians(float(s.get("heading_deg", 0.0)))
        pitch = math.radians(float(s.get("pitch_deg", 0.0)))
        roll = math.radians(float(s.get("roll_bank_deg", 0.0)))
        rpm = float(s.get("rpm", 0.0) or 0.0)
        return pos, heading, pitch, roll, rpm


def _wrap_pi(a: float) -> float:
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def update_visual_pose(st: MissionClientState, dt: float) -> None:
    """Smoothly interpolates the rendered aircraft transform toward the latest polled
    backend state -- never snaps, even though the backend only updates a few times/sec
    from this client's point of view."""
    target_pos, target_hdg, target_pitch, target_roll, target_rpm = st.target_pose()

    # Position: exponential smoothing toward target (same lerp pattern as the web client).
    lerp_factor = min(1.0, 6.0 * dt)
    st.pos = st.pos.lerp(target_pos, lerp_factor)

    hdg_err = _wrap_pi(target_hdg - st.heading_rad)
    st.heading_rad = _wrap_pi(st.heading_rad + hdg_err * min(1.0, 6.0 * dt))
    st.pitch_rad += (target_pitch - st.pitch_rad) * min(1.0, 6.0 * dt)
    st.roll_rad += (target_roll - st.roll_rad) * min(1.0, 6.0 * dt)
    st.rpm += (target_rpm - st.rpm) * min(1.0, 4.0 * dt)

    uav = bpy.data.objects.get(UAV_NAME)
    if uav is None:
        return
    uav.location = st.pos
    # Blender rotation_euler order matches the rig's authored orientation: heading is yaw
    # about Z (up), pitch about X, roll about Y for this nose-forward-on-+Y rig (mirrors
    # the manual sim's own convention in update_simulation()).
    uav.rotation_euler = (st.pitch_rad, st.roll_rad, -st.heading_rad)

    prop = None
    for child in uav.children_recursive:
        if "propeller" in child.name.lower() or "prop_" in child.name.lower():
            prop = child
            break
    if prop is not None and st.rpm > 0:
        prop.rotation_euler.z += (st.rpm / 60.0) * math.pi * 2.0 * dt


def update_chase_camera(st: MissionClientState) -> None:
    cam = bpy.data.objects.get(CAM_NAME)
    if cam is None:
        return
    if cam.data.lens_unit != "MILLIMETERS":
        cam.data.lens_unit = "MILLIMETERS"
        cam.data.sensor_width = CAM_SENSOR_WIDTH
        cam.data.sensor_height = CAM_SENSOR_HEIGHT
        cam.data.lens = CAM_DEFAULT_LENS_MM
        cam.data.clip_start = 0.5
        cam.data.clip_end = 150000.0

    tail_dir = mathutils.Vector((-math.sin(st.heading_rad), -math.cos(st.heading_rad), 0.0)).normalized()
    if st.cam_trailing_dir is None:
        st.cam_trailing_dir = tail_dir.copy()
    else:
        st.cam_trailing_dir = st.cam_trailing_dir.lerp(tail_dir, CAM_TURN_FOLLOW_FACTOR).normalized()

    up_vec = mathutils.Vector((0.0, 0.0, 1.0))
    ideal_cam_pos = st.pos + st.cam_trailing_dir * CAM_DIST_BEHIND + up_vec * CAM_HEIGHT_ABOVE
    if st.cam_world_pos is None:
        st.cam_world_pos = ideal_cam_pos.copy()
    else:
        st.cam_world_pos = st.cam_world_pos.lerp(ideal_cam_pos, 0.12)

    cam.location = st.cam_world_pos
    fwd_horiz = mathutils.Vector((math.sin(st.heading_rad), math.cos(st.heading_rad), 0.0))
    look_target = st.pos + fwd_horiz * CAM_LOOK_AHEAD + up_vec * 3.0
    direction = (look_target - cam.location).normalized()
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


# ─────────────────────────────────────────────────────────────────────────────
# HUD (GPU overlay, mirrors the manual sim's info-dense but legible style)
# ─────────────────────────────────────────────────────────────────────────────
import blf
import gpu
from gpu_extras.batch import batch_for_shader

_shader = None


def _get_shader():
    # Lazy init: gpu.shader.from_builtin() requires an active GL context, which only
    # exists once Blender's window/draw loop is actually running -- importing this module
    # (e.g. for a headless syntax check, or before the first VIEW_3D redraw) must not
    # crash just because the shader hasn't been created yet.
    global _shader
    if _shader is None:
        _shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    return _shader


def _draw_rect(x, y, w, h, color):
    shader = _get_shader()
    verts = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
    indices = ((0, 1, 2), (2, 3, 0))
    batch = batch_for_shader(shader, "TRIS", {"pos": verts}, indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _draw_text(x, y, text, size=14, color=(1, 1, 1, 1)):
    font_id = 0
    blf.position(font_id, x, y, 0)
    blf.size(font_id, size)
    blf.color(font_id, *color)
    blf.draw(font_id, text)


def draw_hud(st: MissionClientState) -> None:
    region = bpy.context.region
    if region is None:
        return
    w, h = region.width, region.height

    _draw_rect(0, h - 34, w, 34, (0.01, 0.03, 0.06, 0.85))
    conn_color = (0.2, 0.9, 0.5, 1.0) if st.connected else (0.9, 0.3, 0.3, 1.0)
    conn_text = "BACKEND CONNECTED" if st.connected else "BACKEND OFFLINE -- start uvicorn + launch mission from web app"
    _draw_text(16, h - 24, f"MISSION FLIGHT CLIENT (READ-ONLY VISUALIZER)  |  {conn_text}", 13, conn_color)

    s = st.backend_state or {}
    d = st.definition or {}
    lines = [
        f"MISSION: {d.get('name', '--')}",
        f"STATUS: {s.get('status', '--')}   PHASE: {s.get('phase', '--')}",
        (
            f"T+ {s.get('time_elapsed_sec', 0):.0f}s   PHASE {s.get('current_phase_idx', 0) + 1}/{len(d.get('phases', [])) or 6} ({s.get('phase', '--')} {s.get('elapsed_in_phase_sec', 0):.0f}s / {s.get('phase_duration_sec', 0):.0f}s)"
            if (d.get("phases") or s.get("phase_duration_sec", 0) > 0)
            else f"T+ {s.get('time_elapsed_sec', 0):.0f}s   WAYPOINT {s.get('current_waypoint_idx', 0)} / {len(d.get('waypoints', []) or [])}"
        ),
        f"ALT MSL: {s.get('pos_z_m', 0):.0f} m   AGL: {s.get('agl_m', 0):.0f} m",
        f"HDG {s.get('heading_deg', 0):.0f}°  PITCH {s.get('pitch_deg', 0):.1f}°  BANK {s.get('roll_bank_deg', 0):.1f}°",
        f"TAS {s.get('true_airspeed_ktas', 0):.0f} kt   THROTTLE {s.get('commanded_throttle_pct', 0):.0f}%",
        "",
        f"ENGINE: {s.get('engine_id', '--')}   RPM {s.get('rpm', 0):.0f}",
        f"CHT {s.get('max_cht_c', 0):.1f}°C   EGT {s.get('max_egt_c', 0):.1f}°C   OIL {s.get('oil_press_bar', 0):.2f} bar",
        f"FLYHASH {s.get('flyhash_novelty_score', 0):.3f}   RELIABILITY {s.get('mission_reliability', 1.0) * 100:.1f}%",
    ]
    active_faults = s.get("active_faults") or []
    if active_faults:
        lines.append(f"ACTIVE FAULT: {active_faults[0].get('mode', active_faults[0].get('fault_mode', '?'))}")

    _draw_rect(16, h - 300, 420, 250, (0.01, 0.03, 0.06, 0.75))
    y = h - 50
    for line in lines:
        color = (1.0, 0.35, 0.35, 1.0) if line.startswith("ACTIVE FAULT") else (0.85, 0.92, 1.0, 1.0)
        _draw_text(24, y, line, 14, color)
        y -= 20

    _draw_text(16, 16, "This view mirrors the mission launched from the web Mission Planner. "
                        "Plan/launch/inject faults/derate/divert from the web app; this window is the visual cockpit. "
                        "ESC to exit.", 11, (0.6, 0.7, 0.8, 1.0))


def _draw_callback(_op, _ctx):
    draw_hud(_op.mission_state)


# ─────────────────────────────────────────────────────────────────────────────
# Modal Operator
# ─────────────────────────────────────────────────────────────────────────────
class OT_MissionFlightClient(bpy.types.Operator):
    bl_idname = "anumaan.mission_flight_client"
    bl_label = "ANUMAAN Mission Flight Client"

    _timer = None
    _draw_handle = None
    mission_state: MissionClientState = None

    def modal(self, context, event):
        if event.type == "ESC":
            self.cancel(context)
            return {"CANCELLED"}

        if event.type == "TIMER":
            self.mission_state.poll()
            dt = 1.0 / 60.0
            update_visual_pose(self.mission_state, dt)
            update_chase_camera(self.mission_state)
            context.area.tag_redraw()

        return {"PASS_THROUGH"}

    def invoke(self, context, event):
        self.mission_state = MissionClientState()
        wm = context.window_manager
        self._timer = wm.event_timer_add(1.0 / 60.0, window=context.window)
        wm.modal_handler_add(self)
        self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_callback, (self, context), "WINDOW", "POST_PIXEL"
        )
        return {"RUNNING_MODAL"}

    def cancel(self, context):
        wm = context.window_manager
        if self._timer is not None:
            wm.event_timer_remove(self._timer)
        if self._draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, "WINDOW")


def register():
    bpy.utils.register_class(OT_MissionFlightClient)


def unregister():
    bpy.utils.unregister_class(OT_MissionFlightClient)


def _auto_invoke():
    """Configures the photoreal environment (reused from the manual sim) and starts the
    modal operator automatically on launch, same pattern as configure_clean_viewport()
    in standalone_canyon_flight_app.py."""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import standalone_canyon_flight_app as manual_sim
        manual_sim.setup_photoreal_environment()
    except Exception as e:
        print(f"[MISSION CLIENT] Could not reuse photoreal environment setup: {e}")

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.overlay.show_overlays = False
                        space.shading.type = "RENDERED"
                for region in area.regions:
                    if region.type == "WINDOW":
                        with bpy.context.temp_override(window=window, area=area, region=region):
                            bpy.ops.anumaan.mission_flight_client("INVOKE_DEFAULT")
                        return


if __name__ == "__main__":
    register()
    bpy.app.timers.register(_auto_invoke, first_interval=0.5)
