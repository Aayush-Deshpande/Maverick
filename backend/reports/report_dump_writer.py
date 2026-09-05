"""
Post-Mission Report Dump Writer — DRDO / iDEX Problem Statement ID: 26054

Every simulated mission (backend 20 Hz engine service, or the standalone Blender
canyon simulator) writes one self-contained folder under report_dump/:

    report_dump/
      mission_001/
        mission.json              <- manifest; the ONLY file the graph viewer reads at startup
        readings/                 <- sensor readings (the 27-channel telemetry record)
        health/                   <- engine + subsystem health indices
        faults/                   <- ML-classified fault detections
        timeline/                 <- chronological mission event timeline
        predictions/              <- RUL prognostics & Go/No-Go advisory
        actions/                  <- pilot directives + CBM work orders
        mission_summary/          <- the human-readable debrief

The seven categories map 1:1 onto the PS-26054 deliverables (doc01 §2) and the four
Mission Reliability pillars (doc01 §3): sensor ingestion, health monitoring, fault
prediction, degradation trending / RUL, and prescriptive action.

Contract with the viewer application (apps/mission_graph_viewer):
  * A category folder is written ONLY when there is real content for it. The viewer
    renders a child node per folder actually present, so an absent category simply
    means no node — never an empty placeholder.
  * mission.json is small and complete enough to render the whole node graph without
    opening a single report file. Report bodies are lazy-loaded on click.

Stdlib only — importable from Blender's bundled Python.
"""

import csv
import json
import os
import re
import shutil
import time
from typing import Any, Dict, List, Optional

# Canonical category order. The viewer discovers categories from disk, but when a
# category is a known one it gets this display name / accent colour instead of a
# title-cased folder name.
CATEGORY_ORDER: List[str] = [
    "readings",
    "health",
    "faults",
    "timeline",
    "predictions",
    "actions",
    "mission_summary",
]

CATEGORY_LABELS: Dict[str, str] = {
    "readings": "Sensor Readings",
    "health": "Engine Health",
    "faults": "Faults Detected",
    "timeline": "Fault Timeline",
    "predictions": "Predictions",
    "actions": "Actions & Orders",
    "mission_summary": "Mission Summary",
}

_MISSION_DIR_RE = re.compile(r"^mission_(\d+)$")

_SEVERITY_RANK = {
    "NOMINAL": 0, "NORMAL": 0, "": 0,
    "ADVISORY": 1, "CAUTION": 1,
    "WARNING": 2,
    "CRITICAL": 3,
}


def default_report_root() -> str:
    """<repo>/report_dump — resolved relative to this file, not the cwd."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "report_dump"))


def worst_severity(severities: List[str]) -> str:
    """Highest-ranking severity in the list; drives the mission node's colour."""
    worst, rank = "NOMINAL", 0
    for s in severities:
        r = _SEVERITY_RANK.get(str(s).upper(), 0)
        if r > rank:
            worst, rank = str(s).upper(), r
    return worst


def format_elapsed(epoch: float, start_epoch: float) -> str:
    """T+HH:MM:SS relative to mission start."""
    delta = max(0, int(epoch - start_epoch))
    h, rem = divmod(delta, 3600)
    m, s = divmod(rem, 60)
    return f"T+{h:02d}:{m:02d}:{s:02d}"


class ReportDumpWriter:
    """Writes one mission_NNN/ folder per simulated mission."""

    def __init__(self, root: Optional[str] = None):
        self.root = os.path.abspath(root) if root else default_report_root()

    # ------------------------------------------------------------------
    # Mission folder allocation
    # ------------------------------------------------------------------

    def allocate_mission_dir(self) -> str:
        """
        Reserve the next free mission_NNN/ folder and create it.

        Numbering continues from whatever is already on disk so re-runs accumulate
        into a growing fleet history rather than overwriting mission_001 forever.
        """
        os.makedirs(self.root, exist_ok=True)
        highest = 0
        for entry in os.listdir(self.root):
            m = _MISSION_DIR_RE.match(entry)
            if m and os.path.isdir(os.path.join(self.root, entry)):
                highest = max(highest, int(m.group(1)))
        path = os.path.join(self.root, f"mission_{highest + 1:03d}")
        os.makedirs(path, exist_ok=True)
        return path

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def write_mission(
        self,
        manifest: Dict[str, Any],
        readings: Optional[Dict[str, Any]] = None,
        telemetry_csv_source: Optional[str] = None,
        health: Optional[Dict[str, Any]] = None,
        faults: Optional[Dict[str, Any]] = None,
        timeline: Optional[Dict[str, Any]] = None,
        predictions: Optional[Dict[str, Any]] = None,
        actions: Optional[Dict[str, Any]] = None,
        summary_markdown: Optional[str] = None,
    ) -> str:
        """
        Write a complete mission bundle. Returns the mission folder path.

        Any category passed as None (or as an empty payload) is skipped entirely —
        no folder is created, so the viewer renders no node for it.
        """
        mission_dir = self.allocate_mission_dir()
        mission_id = os.path.basename(mission_dir)

        written: Dict[str, List[str]] = {}

        # 1. Sensor readings — the raw telemetry record plus per-channel statistics.
        reading_files: List[str] = []
        if telemetry_csv_source and os.path.exists(telemetry_csv_source):
            reading_files.append(
                self._copy_into(mission_dir, "readings", telemetry_csv_source, "telemetry_log.csv")
            )
        if readings:
            reading_files.append(self._write_json(mission_dir, "readings", "sensor_channels.json", readings))
        if reading_files:
            written["readings"] = reading_files

        # 2-6. JSON analytic categories.
        for category, filename, payload in (
            ("health", "engine_health.json", health),
            ("faults", "faults_detected.json", faults),
            ("timeline", "fault_timeline.json", timeline),
            ("predictions", "rul_prognostics.json", predictions),
            ("actions", "recommended_actions.json", actions),
        ):
            if payload:
                written[category] = [self._write_json(mission_dir, category, filename, payload)]

        # 7. Human-readable debrief.
        if summary_markdown and summary_markdown.strip():
            written["mission_summary"] = [
                self._write_text(mission_dir, "mission_summary", "mission_summary.md", summary_markdown)
            ]

        # Manifest last: its presence is the viewer's signal that the folder is complete.
        full_manifest = dict(manifest)
        full_manifest.update({
            "mission_id": mission_id,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "generated_at_epoch": round(time.time(), 3),
            "categories": {k: [os.path.basename(p) for p in v] for k, v in written.items()},
        })
        self._write_json_at(os.path.join(mission_dir, "mission.json"), full_manifest)

        return mission_dir

    # ------------------------------------------------------------------
    # Low-level file helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _category_dir(mission_dir: str, category: str) -> str:
        path = os.path.join(mission_dir, category)
        os.makedirs(path, exist_ok=True)
        return path

    def _write_json(self, mission_dir: str, category: str, filename: str, payload: Any) -> str:
        path = os.path.join(self._category_dir(mission_dir, category), filename)
        self._write_json_at(path, payload)
        return path

    @staticmethod
    def _write_json_at(path: str, payload: Any) -> None:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        os.replace(tmp, path)  # atomic — the viewer never sees a half-written report

    def _write_text(self, mission_dir: str, category: str, filename: str, text: str) -> str:
        path = os.path.join(self._category_dir(mission_dir, category), filename)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
        return path

    def _copy_into(self, mission_dir: str, category: str, source: str, filename: str) -> str:
        path = os.path.join(self._category_dir(mission_dir, category), filename)
        shutil.copyfile(source, path)
        return path


# ----------------------------------------------------------------------
# Telemetry CSV -> per-channel statistics
# ----------------------------------------------------------------------

def summarise_telemetry_csv(csv_path: str, max_channels: int = 64) -> Optional[Dict[str, Any]]:
    """
    Reduce a telemetry log to per-channel min/max/mean/last statistics.

    The raw CSV is copied into readings/ verbatim for the record; this summary is
    what the viewer actually renders, so an 18-hour sortie opens instantly instead
    of paging a million rows into a text panel.
    """
    if not csv_path or not os.path.exists(csv_path):
        return None
    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return None
            stats: Dict[str, Dict[str, Any]] = {}
            row_count = 0
            for row in reader:
                row_count += 1
                for key in reader.fieldnames[:max_channels]:
                    raw = row.get(key)
                    try:
                        value = float(raw)
                    except (TypeError, ValueError):
                        continue
                    entry = stats.get(key)
                    if entry is None:
                        stats[key] = {"min": value, "max": value, "_sum": value, "_n": 1, "last": value}
                    else:
                        entry["min"] = min(entry["min"], value)
                        entry["max"] = max(entry["max"], value)
                        entry["_sum"] += value
                        entry["_n"] += 1
                        entry["last"] = value
    except OSError:
        return None

    if not stats:
        return None

    channels = []
    for name, entry in stats.items():
        channels.append({
            "channel": name,
            "min": round(entry["min"], 3),
            "max": round(entry["max"], 3),
            "mean": round(entry["_sum"] / max(1, entry["_n"]), 3),
            "last": round(entry["last"], 3),
            "samples": entry["_n"],
        })
    return {
        "source_log": os.path.basename(csv_path),
        "sample_count": row_count,
        "channel_count": len(channels),
        "channels": channels,
    }
