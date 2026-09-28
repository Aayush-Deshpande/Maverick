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

Two confirmed bugs fixed here (verified against the actual repo state, not just the shape the
task doc assumed):

1. `_load_frames()` used to key each row on an `ELAPSED_SEC` field. No writer anywhere in this
   codebase (`EngineStateService._log_telemetry_row()`, `can_streamer.py`) ever emits that field
   — every CSV this system actually produces (`report_dump/mission_*/readings/telemetry_log.csv`
   and `data/telemetry/live_sorties/*.csv`) uses `TIMESTAMP_SEC` (Unix epoch seconds) instead.
   So every `report_dump` mission that *did* have a CSV (mission_007/009/010) was still silently
   unreplayable — `get_frame()` always returned `None`. Fixed by deriving `ELAPSED_SEC` from
   `TIMESTAMP_SEC - <mission start epoch>` at load time; the epoch itself is never surfaced to
   callers, `ELAPSED_SEC` is still what frame-seeking is keyed on internally.

2. Only 3 of the (then) 13 `report_dump/mission_NNN/` bundles ever had a telemetry CSV at all —
   the rest were produced by `scripts/simulate_missions.py`, which synthesizes mission bundles
   directly and never runs the live 20 Hz `EngineStateService` tick loop that writes
   `readings/telemetry_log.csv`. `data/telemetry/live_sorties/*.csv` holds ~20 real recorded
   sorties from actual live runs that were never wired into replay at all. Fixed by treating
   `live_sorties/*.csv` as a second, additive manifest+frame source (never replacing
   `report_dump/`), with a synthesized manifest (no `mission.json` exists for these) built from
   the filename and the CSV's own first/last rows.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import bisect
import csv
import glob
import json
import os


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def default_report_dump_dir() -> str:
    return os.path.join(_repo_root(), "report_dump")


def default_live_sorties_dir() -> str:
    return os.path.join(_repo_root(), "data", "telemetry", "live_sorties")


# Prefix used to disambiguate a live_sorties CSV's filename stem (e.g.
# "SORTIE-SRV-20260927-011741") from a report_dump mission_id (e.g. "mission_007") in the single
# combined mission_id namespace the /api/replay/* routes expose. Chosen instead of a bare stem so
# `get_manifest`/`get_frame` can tell the two sources apart without re-globbing report_dump first.
LIVE_SORTIE_PREFIX = "live:"


def _to_float(v: Any) -> Optional[float]:
    """Best-effort numeric coercion for raw (unparsed-by-DictReader) CSV string values used in
    the cheap first/last-row manifest summaries — returns None rather than raising on blank
    cells or non-numeric header drift instead of failing the whole listing."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


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

    def __init__(self, report_dump_dir: Optional[str] = None, live_sorties_dir: Optional[str] = None):
        self.report_dump_dir = report_dump_dir or default_report_dump_dir()
        self.live_sorties_dir = live_sorties_dir or default_live_sorties_dir()
        self._frame_cache: Dict[str, _FrameIndex] = {}
        self._manifest_cache: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Manifest listing
    # ------------------------------------------------------------------

    def list_manifests(self) -> List[Dict[str, Any]]:
        """Lightweight summary of every recorded sortie, newest first — for the sortie
        selector dropdown. Does not load full telemetry CSVs for report_dump bundles (only
        mission.json); live_sorties entries have no mission.json, so their summary is built
        from the filename plus a cheap read of the CSV's first/last rows."""
        out: List[Dict[str, Any]] = []

        if os.path.isdir(self.report_dump_dir):
            for name in os.listdir(self.report_dump_dir):
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
                    "_sort_key": m.get("start_epoch") or 0.0,
                })

        for summary in self._list_live_sortie_summaries():
            out.append(summary)

        out.sort(key=lambda r: r.pop("_sort_key", 0.0), reverse=True)
        return out

    def _list_live_sortie_summaries(self) -> List[Dict[str, Any]]:
        """Builds a manifest-listing entry per data/telemetry/live_sorties/*.csv without
        parsing the full file — just the header, first data row, and last data row."""
        if not os.path.isdir(self.live_sorties_dir):
            return []
        out: List[Dict[str, Any]] = []
        for path in sorted(glob.glob(os.path.join(self.live_sorties_dir, "*.csv"))):
            stem = os.path.splitext(os.path.basename(path))[0]
            try:
                first_row, last_row = self._first_and_last_csv_rows(path)
            except Exception:
                continue  # an unreadable/corrupt CSV must not break the whole listing
            if first_row is None or last_row is None:
                continue

            start_epoch = _to_float(first_row.get("TIMESTAMP_SEC"))
            end_epoch = _to_float(last_row.get("TIMESTAMP_SEC"))
            duration_hours = (
                (end_epoch - start_epoch) / 3600.0
                if start_epoch is not None and end_epoch is not None
                else None
            )
            out.append({
                "mission_id": f"{LIVE_SORTIE_PREFIX}{stem}",
                "sortie_id": stem,
                "name": "Live Sortie Recording",
                "uav_tail_number": None,
                "region": last_row.get("THEATER") or first_row.get("THEATER"),
                "status": "RECORDED",
                "severity": None,
                "start_time": None,
                "end_time": None,
                "duration_hours": duration_hours,
                "fault_count": None,  # would need a full scan; left unset rather than guessed
                "health_index_start": _to_float(first_row.get("HEALTH_INDEX")),
                "health_index_end": _to_float(last_row.get("HEALTH_INDEX")),
                "_sort_key": start_epoch or 0.0,
            })
        return out

    @staticmethod
    def _first_and_last_csv_rows(path: str):
        """Cheap first/last-row read for the manifest summary — avoids loading the whole
        file into memory just to list it (that full parse only happens in _load_frames,
        lazily, the first time a mission is actually opened for playback)."""
        first_row: Optional[Dict[str, str]] = None
        last_row: Optional[Dict[str, str]] = None
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if first_row is None:
                    first_row = row
                last_row = row
        return first_row, last_row

    def get_manifest(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Full manifest for one sortie, including event markers built from
        timeline/fault_timeline.json (matching the ReplayEventMarker shape from
        final_tasks/02_HISTORICAL_MISSION_REPLAY_AND_SCRUBBER.md §3.1, adapted to this
        project's real event_type vocabulary: MISSION_START/FAULT_INJECTED/ACTION_ISSUED/
        MISSION_END rather than the task doc's illustrative ANOMALY_ONSET/PILOT_MITIGATION/
        MAINTENANCE_ORDER names, since those never appear in what the sim actually emits)."""
        if mission_id in self._manifest_cache:
            return self._manifest_cache[mission_id]

        if mission_id.startswith(LIVE_SORTIE_PREFIX):
            manifest = self._get_live_sortie_manifest(mission_id)
            if manifest is not None:
                self._manifest_cache[mission_id] = manifest
            return manifest

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

    def _get_live_sortie_manifest(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """live_sorties has no mission.json/fault_timeline.json — the manifest and its event
        markers are both derived from the CSV itself: rising edges of DIAG_FAULT_ID stand in
        for FAULT_INJECTED markers (there's no separate action/mitigation log for these)."""
        stem = mission_id[len(LIVE_SORTIE_PREFIX):]
        csv_path = os.path.join(self.live_sorties_dir, f"{stem}.csv")
        if not os.path.isfile(csv_path):
            return None

        idx = self._load_frames(mission_id)
        if idx is None or not idx.times:
            return None

        start_epoch = _to_float(idx.rows[0].get("TIMESTAMP_SEC")) or 0.0
        event_markers: List[Dict[str, Any]] = [{
            "timestamp_epoch": start_epoch,
            "mission_elapsed_sec": 0.0,
            "event_type": "MISSION_START",
            "severity": "NOMINAL",
            "title": "Sortie recording start",
            "detail": "",
        }]
        prev_fault_id = 0
        for t, row in zip(idx.times, idx.rows):
            fault_id = int(_to_float(row.get("DIAG_FAULT_ID")) or 0)
            if fault_id != prev_fault_id:
                event_markers.append({
                    "timestamp_epoch": start_epoch + t,
                    "mission_elapsed_sec": round(t, 3),
                    "event_type": "FAULT_INJECTED" if fault_id > 0 else "FAULT_CLEARED",
                    "severity": "CRITICAL" if fault_id > 0 else "NOMINAL",
                    "title": f"DIAG_FAULT_ID -> {fault_id}",
                    "detail": "",
                })
            prev_fault_id = fault_id
        event_markers.append({
            "timestamp_epoch": start_epoch + idx.times[-1],
            "mission_elapsed_sec": round(idx.times[-1], 3),
            "event_type": "MISSION_END",
            "severity": "NOMINAL",
            "title": "Sortie recording end",
            "detail": "",
        })

        return {
            "mission_id": mission_id,
            "sortie_id": stem,
            "uav_tail_number": None,
            "region": idx.rows[0].get("THEATER"),
            "theater_region": idx.rows[0].get("THEATER"),
            "total_duration_sec": idx.times[-1],
            "start_epoch": start_epoch,
            "event_markers": event_markers,
        }

    # ------------------------------------------------------------------
    # Frame seeking
    # ------------------------------------------------------------------

    def _load_frames(self, mission_id: str) -> Optional[_FrameIndex]:
        if mission_id in self._frame_cache:
            return self._frame_cache[mission_id]

        if mission_id.startswith(LIVE_SORTIE_PREFIX):
            stem = mission_id[len(LIVE_SORTIE_PREFIX):]
            csv_path = os.path.join(self.live_sorties_dir, f"{stem}.csv")
        else:
            csv_path = os.path.join(self.report_dump_dir, mission_id, "readings", "telemetry_log.csv")
        if not os.path.isfile(csv_path):
            return None

        times: List[float] = []
        rows: List[Dict[str, Any]] = []
        start_epoch: Optional[float] = None
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

                # Every CSV this system actually writes carries TIMESTAMP_SEC (Unix epoch), not
                # ELAPSED_SEC — derive ELAPSED_SEC as mission-relative time from the first row's
                # epoch rather than requiring a field no writer produces (see module docstring).
                elapsed = row.get("ELAPSED_SEC")
                if elapsed is None:
                    epoch = row.get("TIMESTAMP_SEC")
                    if epoch is None:
                        continue  # a row that can't be placed on the timeline can't be replayed
                    if start_epoch is None:
                        start_epoch = epoch
                    elapsed = epoch - start_epoch
                    row["ELAPSED_SEC"] = elapsed
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
