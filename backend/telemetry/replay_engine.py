"""
Historical Mission Replay Engine (PRD F12 / final_tasks/02_HISTORICAL_MISSION_REPLAY_AND_SCRUBBER.md).
DRDO / iDEX Problem Statement ID: 26054

Indexes and serves past sortie telemetry for the Web GCS replay scrubber. Rather than adding a
second data model for `data/telemetry/*.csv`/`.parquet` as the original task doc assumed, this
reads the mission report bundles `report_dump/mission_NNN/` that `flight_mission_recorder.py`
(the canyon flight sim's own post-mission exporter) already produces — `mission.json` for the
manifest, `readings/telemetry_log.csv` for the per-sample time series, and
`timeline/fault_timeline.json` for event markers. Building a second ingester for a data shape
that already exists would be exactly the kind of duplicated data model goal_v1.md's F12
implementation notes warn against.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import bisect
import csv
import json
import os


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def default_report_dump_dir() -> str:
    return os.path.join(_repo_root(), "report_dump")


@dataclass
class _FrameIndex:
    times: List[float]        # ELAPSED_SEC, ascending
    rows: List[Dict[str, Any]]  # parsed CSV rows, numeric fields coerced to float/int where possible


_NUMERIC_FIELDS = {
    "TIMESTAMP_SEC", "ELAPSED_SEC", "ALTITUDE_M", "ALTITUDE_FT", "AGL_M", "AIRSPEED_KIAS",
    "GROUND_SPEED_MS", "HEADING_DEG", "PITCH_DEG", "ROLL_DEG", "ENGINE_RPM", "THROTTLE_PCT",
    "CHT_C", "CHT_RATE_C_S", "OIL_PRESS_BAR", "FUEL_FLOW_LH", "RADAR_FWD_M", "TTI_SEC",
}
_INT_FIELDS = {"COPILOT_ON"}


class ReplayEngine:
    """Loads and serves `report_dump/mission_NNN/` bundles as replayable sorties. Each
    mission's telemetry CSV is parsed once and cached in memory (these are minutes of
    sub-kHz telemetry — tens of thousands of rows at most, not a scale that needs a real
    index on disk), so `get_frame()` after the first call is an O(log n) bisect, never a
    linear re-scan from t=0, matching the task doc's "fast indexed seeker" requirement."""

    def __init__(self, report_dump_dir: Optional[str] = None):
        self.report_dump_dir = report_dump_dir or default_report_dump_dir()
        self._frame_cache: Dict[str, _FrameIndex] = {}
        self._manifest_cache: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Manifest listing
    # ------------------------------------------------------------------

    def list_manifests(self) -> List[Dict[str, Any]]:
        """Lightweight summary of every recorded sortie, newest first — for the sortie
        selector dropdown. Does not load telemetry CSVs (only mission.json)."""
        if not os.path.isdir(self.report_dump_dir):
            return []
        out = []
        for name in sorted(os.listdir(self.report_dump_dir), reverse=True):
            mission_json = os.path.join(self.report_dump_dir, name, "mission.json")
            if not os.path.isfile(mission_json):
                continue
            try:
                with open(mission_json, "r", encoding="utf-8") as f:
                    m = json.load(f)
            except Exception:
                continue  # a corrupt/partial bundle must not break the whole listing
            out.append({
                "mission_id": m.get("mission_id", name),
                "sortie_id": m.get("sortie_id"),
                "name": m.get("name"),
                "uav_tail_number": m.get("uav_tail_number"),
                "region": m.get("region"),
                "status": m.get("status"),
                "severity": m.get("severity"),
                "start_time": m.get("start_time"),
                "end_time": m.get("end_time"),
                "duration_hours": m.get("duration_hours"),
                "fault_count": m.get("fault_count"),
                "health_index_start": m.get("health_index_start"),
                "health_index_end": m.get("health_index_end"),
            })
        return out

    def get_manifest(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Full manifest for one sortie, including event markers built from
        timeline/fault_timeline.json (matching the ReplayEventMarker shape from
        final_tasks/02_HISTORICAL_MISSION_REPLAY_AND_SCRUBBER.md §3.1, adapted to this
        project's real event_type vocabulary: MISSION_START/FAULT_INJECTED/ACTION_ISSUED/
        MISSION_END rather than the task doc's illustrative ANOMALY_ONSET/PILOT_MITIGATION/
        MAINTENANCE_ORDER names, since those never appear in what the sim actually emits)."""
        if mission_id in self._manifest_cache:
            return self._manifest_cache[mission_id]

        mission_dir = os.path.join(self.report_dump_dir, mission_id)
        mission_json = os.path.join(mission_dir, "mission.json")
        if not os.path.isfile(mission_json):
            return None
        with open(mission_json, "r", encoding="utf-8") as f:
            m = json.load(f)

        start_epoch = m.get("start_epoch", 0.0)
        event_markers: List[Dict[str, Any]] = []
        timeline_path = os.path.join(mission_dir, "timeline", "fault_timeline.json")
        if os.path.isfile(timeline_path):
            try:
                with open(timeline_path, "r", encoding="utf-8") as f:
                    tl = json.load(f)
                for ev in tl.get("events", []):
                    epoch = ev.get("epoch", start_epoch)
                    event_markers.append({
                        "timestamp_epoch": epoch,
                        "mission_elapsed_sec": round(epoch - start_epoch, 3),
                        "event_type": ev.get("event_type", "UNKNOWN"),
                        "severity": ev.get("severity", "NOMINAL"),
                        "title": ev.get("title", ""),
                        "detail": ev.get("detail", ""),
                    })
            except Exception:
                pass  # missing/corrupt timeline: manifest is still usable without markers

        manifest = {
            "mission_id": m.get("mission_id", mission_id),
            "sortie_id": m.get("sortie_id"),
            "uav_tail_number": m.get("uav_tail_number"),
            "region": m.get("region"),
            "theater_region": m.get("region"),  # alias matching the task doc's field name
            "total_duration_sec": max(
                (m.get("duration_hours") or 0.0) * 3600.0,
                event_markers[-1]["mission_elapsed_sec"] if event_markers else 0.0,
            ),
            "start_epoch": start_epoch,
            "event_markers": event_markers,
        }
        self._manifest_cache[mission_id] = manifest
        return manifest

    # ------------------------------------------------------------------
    # Frame seeking
    # ------------------------------------------------------------------

    def _load_frames(self, mission_id: str) -> Optional[_FrameIndex]:
        if mission_id in self._frame_cache:
            return self._frame_cache[mission_id]

        csv_path = os.path.join(self.report_dump_dir, mission_id, "readings", "telemetry_log.csv")
        if not os.path.isfile(csv_path):
            return None

        times: List[float] = []
        rows: List[Dict[str, Any]] = []
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                row: Dict[str, Any] = {}
                for k, v in raw.items():
                    if k in _NUMERIC_FIELDS:
                        try:
                            row[k] = float(v)
                        except (TypeError, ValueError):
                            row[k] = None
                    elif k in _INT_FIELDS:
                        try:
                            row[k] = int(float(v))
                        except (TypeError, ValueError):
                            row[k] = None
                    else:
                        row[k] = v
                elapsed = row.get("ELAPSED_SEC")
                if elapsed is None:
                    continue  # a row that can't be placed on the timeline can't be replayed
                times.append(elapsed)
                rows.append(row)

        # telemetry_log.csv is written append-only during the sortie, so it is already
        # ascending by construction; still, don't assume that of a hand-edited/foreign file.
        if times != sorted(times):
            paired = sorted(zip(times, rows), key=lambda p: p[0])
            times = [p[0] for p in paired]
            rows = [p[1] for p in paired]

        idx = _FrameIndex(times=times, rows=rows)
        self._frame_cache[mission_id] = idx
        return idx

    def get_frame(self, mission_id: str, time_sec: float) -> Optional[Dict[str, Any]]:
        """Returns the telemetry sample at-or-before `time_sec` (never a future sample —
        scrubbing to T+04:16 must show what was true at T+04:16, not interpolate forward into
        what hadn't happened yet). O(log n) via bisect on the cached, sorted time index."""
        idx = self._load_frames(mission_id)
        if idx is None or not idx.times:
            return None
        pos = bisect.bisect_right(idx.times, time_sec) - 1
        pos = max(0, min(pos, len(idx.times) - 1))
        return idx.rows[pos]
