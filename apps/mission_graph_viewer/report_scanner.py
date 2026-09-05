"""
report_dump/ discovery — DRDO / iDEX PS-26054

The viewer's only contract with the simulation: scan report_dump/, find whatever
missions and report categories happen to exist on disk, and describe them. Nothing
is hard-coded — add a new category folder to a mission and a node appears for it on
the next scan; omit one and no node is drawn.

Startup cost is one small mission.json read per mission. Report bodies are never
touched here; they are lazy-loaded by load_report() when a node is actually clicked.

Stdlib only — runs inside Blender's bundled Python.
"""

import csv
import io
import json
import os
from typing import Any, Dict, List, Optional

# Display names + accent colours (r, g, b) for the categories the simulators emit.
# Unknown folders still render — they just fall back to a title-cased name and the
# neutral accent, which is what keeps this viewer future-proof.
CATEGORY_STYLE: Dict[str, Dict[str, Any]] = {
    "readings":        {"label": "Sensor Readings",   "color": (0.20, 0.80, 1.00)},
    "health":          {"label": "Engine Health",     "color": (0.25, 1.00, 0.62)},
    "faults":          {"label": "Faults Detected",   "color": (1.00, 0.33, 0.30)},
    "timeline":        {"label": "Fault Timeline",    "color": (1.00, 0.68, 0.22)},
    "predictions":     {"label": "Predictions / RUL", "color": (0.72, 0.52, 1.00)},
    "actions":         {"label": "Actions & Orders",  "color": (1.00, 0.87, 0.35)},
    "mission_summary": {"label": "Mission Summary",   "color": (0.95, 0.95, 1.00)},
}

DEFAULT_CATEGORY_COLOR = (0.62, 0.74, 0.88)

# Preferred ring order; anything unrecognised is appended alphabetically after these.
CATEGORY_ORDER = [
    "readings", "health", "faults", "timeline",
    "predictions", "actions", "mission_summary",
]

_TEXT_EXTENSIONS = {".md", ".txt", ".log"}
_MAX_REPORT_BYTES = 4 * 1024 * 1024  # a report body larger than this is truncated, not loaded whole


def default_report_root() -> str:
    """<repo>/report_dump, resolved from this file rather than Blender's cwd."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "report_dump"))


def category_style(name: str) -> Dict[str, Any]:
    style = CATEGORY_STYLE.get(name)
    if style:
        return style
    return {"label": name.replace("_", " ").title(), "color": DEFAULT_CATEGORY_COLOR}


class ReportNode:
    """One report file — a leaf node in the graph, opened in the viewer on click."""

    __slots__ = ("category", "label", "color", "path", "filename", "size_bytes")

    def __init__(self, category: str, path: str, disambiguate: bool = False):
        style = category_style(category)
        self.category = category
        self.color = style["color"]
        self.path = path
        self.filename = os.path.basename(path)
        # A category holding several files (readings/ carries both the raw telemetry log
        # and its channel statistics) would otherwise draw two identically-named nodes.
        stem = os.path.splitext(self.filename)[0]
        self.label = f"{style['label']} · {stem.replace('_', ' ').title()}" if disambiguate else style["label"]
        try:
            self.size_bytes = os.path.getsize(path)
        except OSError:
            self.size_bytes = 0


class MissionNode:
    """One mission_NNN/ folder: its manifest plus the report leaves it actually contains."""

    __slots__ = ("mission_id", "path", "manifest", "reports", "title", "subtitle", "severity")

    def __init__(self, path: str, manifest: Dict[str, Any], reports: List[ReportNode]):
        self.path = path
        self.manifest = manifest
        self.reports = reports
        self.mission_id = manifest.get("mission_id") or os.path.basename(path)
        self.severity = str(manifest.get("severity", "NOMINAL")).upper()

        pretty_id = self.mission_id.replace("_", " ").title()
        self.title = pretty_id
        region = manifest.get("theater") or manifest.get("region") or ""
        faults = manifest.get("fault_count")
        bits = [b for b in (region, manifest.get("name")) if b]
        if faults:
            bits.append(f"{faults} fault{'s' if faults != 1 else ''}")
        self.subtitle = "  ·  ".join(bits)


def scan(root: Optional[str] = None) -> List[MissionNode]:
    """
    Discover every mission bundle under `root`.

    A directory qualifies as a mission if it holds a readable mission.json. Missions
    are ordered by start time when the manifest carries one, else by folder name, so
    the sphere layout stays stable between launches.
    """
    root = root or default_report_root()
    if not os.path.isdir(root):
        return []

    missions: List[MissionNode] = []
    for entry in sorted(os.listdir(root)):
        mission_dir = os.path.join(root, entry)
        if not os.path.isdir(mission_dir):
            continue
        manifest_path = os.path.join(mission_dir, "mission.json")
        if not os.path.exists(manifest_path):
            continue
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(manifest, dict):
            continue
        manifest.setdefault("mission_id", entry)
        missions.append(MissionNode(mission_dir, manifest, _scan_reports(mission_dir)))

    missions.sort(key=lambda m: (m.manifest.get("start_epoch") or 0.0, m.mission_id))
    return missions


def _scan_reports(mission_dir: str) -> List[ReportNode]:
    """Every file inside every category subfolder, in canonical ring order."""
    found: Dict[str, List[str]] = {}
    for entry in os.listdir(mission_dir):
        category_dir = os.path.join(mission_dir, entry)
        if not os.path.isdir(category_dir):
            continue
        files = sorted(
            os.path.join(category_dir, f)
            for f in os.listdir(category_dir)
            if os.path.isfile(os.path.join(category_dir, f)) and not f.endswith(".tmp")
        )
        if files:
            found[entry] = files

    ordered: List[ReportNode] = []
    for category in CATEGORY_ORDER + sorted(k for k in found if k not in CATEGORY_ORDER):
        paths = found.get(category) or []
        for path in paths:
            ordered.append(ReportNode(category, path, disambiguate=len(paths) > 1))
    return ordered


# ----------------------------------------------------------------------
# Lazy report loading
# ----------------------------------------------------------------------

def load_report(path: str) -> Dict[str, Any]:
    """
    Read one report file. Called only when its node is clicked — nothing here runs
    at scan time, so startup stays independent of how much telemetry is on disk.

    Returns {"kind": "json"|"csv"|"text"|"error", "data"|"rows"|"text": ...}.
    """
    ext = os.path.splitext(path)[1].lower()
    try:
        size = os.path.getsize(path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read(_MAX_REPORT_BYTES)
        truncated = size > _MAX_REPORT_BYTES
    except OSError as e:
        return {"kind": "error", "text": f"Unable to read report: {e}"}

    if ext == ".json":
        try:
            return {"kind": "json", "data": json.loads(raw)}
        except ValueError as e:
            return {"kind": "error", "text": f"Malformed JSON report: {e}"}

    if ext == ".csv":
        try:
            reader = csv.reader(io.StringIO(raw))
            rows = [r for _, r in zip(range(400), reader)]  # head only; stats live in the JSON sibling
        except csv.Error as e:
            return {"kind": "error", "text": f"Malformed CSV report: {e}"}
        return {"kind": "csv", "rows": rows, "truncated": truncated}

    if ext in _TEXT_EXTENSIONS or not ext:
        return {"kind": "text", "text": raw, "truncated": truncated}

    return {"kind": "text", "text": raw, "truncated": truncated}
