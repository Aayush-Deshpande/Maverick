"""
Historical Mission Replay Engine (PRD F12 / final_tasks/02_HISTORICAL_MISSION_REPLAY_AND_SCRUBBER.md).
DRDO / iDEX Problem Statement ID: 26054

Indexes and serves past sortie telemetry for the Web GCS replay scrubber. Discovers both:
1. `report_dump/mission_NNN/` bundles produced by debrief/mission recorder.
2. `data/telemetry/live_sorties/*.csv` recorded directly during live GCS sorties.
Loads and caches frames in memory, supporting O(log n) bisect seeking for the frontend scrubber.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import bisect
import csv
import json
import os
import shutil


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def default_report_dump_dir() -> str:
    return os.path.join(_repo_root(), "report_dump")


def default_live_sorties_dir() -> str:
    return os.path.join(_repo_root(), "data", "telemetry", "live_sorties")


@dataclass
class _FrameIndex:
    times: List[float]        # ELAPSED_SEC, ascending
    rows: List[Dict[str, Any]]  # parsed CSV rows, numeric fields coerced to float/int where possible


_NUMERIC_FIELDS = {
    "TIMESTAMP_SEC", "ELAPSED_SEC", "ALTITUDE_M", "ALTITUDE_FT", "AGL_M", "AIRSPEED_KIAS",
    "GROUND_SPEED_MS", "HEADING_DEG", "PITCH_DEG", "ROLL_DEG", "ENGINE_RPM", "THROTTLE_PCT",
    "TPS", "CHT_C", "CHT_RATE_C_S", "OIL_PRESS_BAR", "OIL_PRESS", "OIL_TEMP", "FUEL_FLOW_LH",
    "FUEL_FLOW", "FUEL_RAIL_P", "MAP", "VIB_GEARBOX_RMS", "BUS_VOLTAGE", "BATTERY_CURRENT",
    "RADAR_FWD_M", "TTI_SEC", "CHT_1", "CHT_2", "CHT_3", "CHT_4", "EGT_1", "EGT_2", "EGT_3", "EGT_4",
    "OAT_C", "TAS_KNOTS", "INJ_TIMING_BTDC", "INJ_PULSE_WIDTH_MS", "IGN_TIMING_BTDC",
    "LAMBDA_AFR", "BSFC_G_KWH", "POWER_KW", "THERMAL_EFFICIENCY", "HEALTH_INDEX"
}
_INT_FIELDS = {"COPILOT_ON", "DIAG_FAULT_ID"}


class ReplayEngine:
    """Loads and serves both report_dump bundles and live_sorties CSV logs as replayable sorties.
    Telemetry is parsed once and cached in memory with sorted time indexes for O(log n) scrubbing."""

    def __init__(self, report_dump_dir: Optional[str] = None, live_sorties_dir: Optional[str] = None):
        self.report_dump_dir = report_dump_dir or default_report_dump_dir()
        self.live_sorties_dir = live_sorties_dir or default_live_sorties_dir()
        self._frame_cache: Dict[str, _FrameIndex] = {}
        self._manifest_cache: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Manifest listing
    # ------------------------------------------------------------------

    def list_manifests(self) -> List[Dict[str, Any]]:
        """Summary of every recorded sortie (report_dump bundles + live_sorties CSV logs)."""
        out: List[Dict[str, Any]] = []
        seen_sorties = set()

        # 1. Index report_dump bundles
        if os.path.isdir(self.report_dump_dir):
            for name in sorted(os.listdir(self.report_dump_dir), reverse=True):
                mission_json = os.path.join(self.report_dump_dir, name, "mission.json")
                if not os.path.isfile(mission_json):
                    continue
                try:
                    with open(mission_json, "r", encoding="utf-8") as f:
                        m = json.load(f)
                except Exception:
                    continue
                s_id = m.get("sortie_id")
                if s_id:
                    seen_sorties.add(s_id)
                out.append({
                    "mission_id": m.get("mission_id", name),
                    "sortie_id": s_id,
                    "name": m.get("name", name),
                    "uav_tail_number": m.get("uav_tail_number", "TAPAS-BH-201-AF01"),
                    "region": m.get("region", "LADAKH"),
                    "status": m.get("status", "COMPLETED"),
                    "severity": m.get("severity", "NOMINAL"),
                    "start_time": m.get("start_time"),
                    "end_time": m.get("end_time"),
                    "duration_hours": m.get("duration_hours", 0.0),
                    "fault_count": m.get("fault_count", 0),
                    "health_index_start": m.get("health_index_start", 1.0),
                    "health_index_end": m.get("health_index_end", 1.0),
                })

        # 2. Index live_sorties CSV files
        if os.path.isdir(self.live_sorties_dir):
            for fname in sorted(os.listdir(self.live_sorties_dir), reverse=True):
                if not fname.endswith(".csv"):
                    continue
                s_name = fname[:-4]
                if s_name in seen_sorties:
                    continue
                seen_sorties.add(s_name)
                fpath = os.path.join(self.live_sorties_dir, fname)
                try:
                    stat = os.stat(fpath)
                    # Count approximate duration from file size / line count
                    dur_hrs = round(max(0.01, stat.st_size / 200000.0), 3)
                except Exception:
                    dur_hrs = 0.05
                out.append({
                    "mission_id": s_name,
                    "sortie_id": s_name,
                    "name": f"Live Sortie ({s_name})",
                    "uav_tail_number": "TAPAS-BH-201-AF01",
                    "region": "LADAKH",
                    "status": "COMPLETED",
                    "severity": "NOMINAL",
                    "start_time": None,
                    "end_time": None,
                    "duration_hours": dur_hrs,
                    "fault_count": 0,
                    "health_index_start": 1.0,
                    "health_index_end": 1.0,
                })

        return out

    def get_manifest(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Full manifest for one sortie, including event markers."""
        if mission_id in self._manifest_cache:
            return self._manifest_cache[mission_id]

        # Check report_dump bundle first
        mission_dir = os.path.join(self.report_dump_dir, mission_id)
        mission_json = os.path.join(mission_dir, "mission.json")
        if os.path.isfile(mission_json):
            try:
                with open(mission_json, "r", encoding="utf-8") as f:
                    m = json.load(f)
            except Exception:
                m = {}
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
                    pass

            # Pre-load frames if available to calculate exact duration
            idx = self._load_frames(mission_id)
            dur_candidate = idx.times[-1] if (idx and idx.times and idx.times[-1] > 0.0) else 0.0
            dur_markers = event_markers[-1]["mission_elapsed_sec"] if (event_markers and event_markers[-1].get("mission_elapsed_sec", 0.0) > 0.0) else 0.0
            dur_meta = (m.get("duration_hours") or 0.0) * 3600.0
            total_dur = max(dur_candidate, dur_markers, dur_meta, 60.0)

            manifest = {
                "mission_id": m.get("mission_id", mission_id),
                "sortie_id": m.get("sortie_id"),
                "uav_tail_number": m.get("uav_tail_number", "TAPAS-BH-201-AF01"),
                "region": m.get("region", "LADAKH"),
                "theater_region": m.get("region", "LADAKH"),
                "total_duration_sec": total_dur,
                "start_epoch": start_epoch,
                "event_markers": event_markers,
            }
            self._manifest_cache[mission_id] = manifest
            return manifest

        # Check live sorties directory
        csv_file = self._find_csv_path(mission_id)
        if csv_file and os.path.isfile(csv_file):
            idx = self._load_frames(mission_id)
            total_dur = idx.times[-1] if (idx and idx.times and idx.times[-1] > 0.0) else 60.0
            start_epoch = idx.rows[0].get("TIMESTAMP_SEC", 0.0) if (idx and idx.rows) else 0.0
            
            # Extract any anomaly markers from rows
            event_markers = []
            if idx and idx.rows:
                last_fid = 0
                for r in idx.rows:
                    fid = int(r.get("DIAG_FAULT_ID") or 0)
                    if fid > 0 and fid != last_fid:
                        last_fid = fid
                        event_markers.append({
                            "timestamp_epoch": r.get("TIMESTAMP_SEC", 0.0),
                            "mission_elapsed_sec": r.get("ELAPSED_SEC", 0.0),
                            "event_type": "FAULT_DETECTED",
                            "severity": "CRITICAL" if fid in (1, 2) else "WARNING",
                            "title": f"Fault #{fid} Isolated",
                            "detail": f"Anomaly isolated at T+{r.get('ELAPSED_SEC', 0.0):.1f}s",
                        })

            manifest = {
                "mission_id": mission_id,
                "sortie_id": mission_id,
                "uav_tail_number": "TAPAS-BH-201-AF01",
                "region": "LADAKH",
                "theater_region": "LADAKH",
                "total_duration_sec": total_dur,
                "start_epoch": start_epoch,
                "event_markers": event_markers,
            }
            self._manifest_cache[mission_id] = manifest
            return manifest

        return None

    # ------------------------------------------------------------------
    # Frame seeking & CSV path discovery
    # ------------------------------------------------------------------

    def _find_csv_path(self, mission_id: str) -> Optional[str]:
        """Discovers the telemetry CSV path across report_dump and data/telemetry locations."""
        # 1. report_dump bundle
        bundle_csv = os.path.join(self.report_dump_dir, mission_id, "readings", "telemetry_log.csv")
        if os.path.isfile(bundle_csv):
            return bundle_csv

        # 2. Check if mission_id maps to a sortie_id in mission.json
        mission_json = os.path.join(self.report_dump_dir, mission_id, "mission.json")
        sortie_id = None
        if os.path.isfile(mission_json):
            try:
                with open(mission_json, "r", encoding="utf-8") as f:
                    m = json.load(f)
                    sortie_id = m.get("sortie_id")
            except Exception:
                pass

        if sortie_id:
            sortie_csv = os.path.join(self.live_sorties_dir, f"{sortie_id}.csv")
            if os.path.isfile(sortie_csv):
                # Optionally cache/copy to report_dump bundle readings folder
                try:
                    dest_dir = os.path.join(self.report_dump_dir, mission_id, "readings")
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_file = os.path.join(dest_dir, "telemetry_log.csv")
                    if not os.path.exists(dest_file):
                        shutil.copyfile(sortie_csv, dest_file)
                        return dest_file
                except Exception:
                    pass
                return sortie_csv

        # 3. Direct match in live_sorties
        clean_id = mission_id[:-4] if mission_id.endswith(".csv") else mission_id
        live_csv = os.path.join(self.live_sorties_dir, f"{clean_id}.csv")
        if os.path.isfile(live_csv):
            return live_csv

        # 4. Check data/telemetry root datasets
        dataset_csv = os.path.join(_repo_root(), "data", "telemetry", f"{clean_id}.csv")
        if os.path.isfile(dataset_csv):
            return dataset_csv

        # 5. Check data/telemetry/source3_drdo_missions
        drdo_csv = os.path.join(_repo_root(), "data", "telemetry", "source3_drdo_missions", f"{clean_id}.csv")
        if os.path.isfile(drdo_csv):
            return drdo_csv

        # 6. Fallback: if live_sorties contains any CSVs, use the latest one as fallback
        if os.path.isdir(self.live_sorties_dir):
            csvs = [f for f in sorted(os.listdir(self.live_sorties_dir), reverse=True) if f.endswith(".csv")]
            if csvs:
                fallback_path = os.path.join(self.live_sorties_dir, csvs[0])
                return fallback_path

        return None

    def _load_frames(self, mission_id: str) -> Optional[_FrameIndex]:
        if mission_id in self._frame_cache:
            return self._frame_cache[mission_id]

        csv_path = self._find_csv_path(mission_id)
        if not csv_path or not os.path.isfile(csv_path):
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

                # Handle time / elapsed calculation
                ts = row.get("TIMESTAMP_SEC")
                if start_epoch is None and ts is not None:
                    start_epoch = ts

                elapsed = row.get("ELAPSED_SEC")
                if elapsed is None and ts is not None and start_epoch is not None:
                    elapsed = max(0.0, round(ts - start_epoch, 3))
                    row["ELAPSED_SEC"] = elapsed

                if elapsed is None:
                    continue

                # Normalise missing alias fields for frontend GCS dials
                if row.get("ALTITUDE_FT") is not None and row.get("AGL_M") is None:
                    row["AGL_M"] = round(row["ALTITUDE_FT"] * 0.3048, 1)
                elif row.get("ALTITUDE_M") is not None and row.get("ALTITUDE_FT") is None:
                    row["ALTITUDE_FT"] = round(row["ALTITUDE_M"] * 3.28084, 1)

                if row.get("AIRSPEED_KIAS") is None and row.get("TAS_KNOTS") is not None:
                    row["AIRSPEED_KIAS"] = row["TAS_KNOTS"]

                if row.get("THROTTLE_PCT") is None and row.get("TPS") is not None:
                    row["THROTTLE_PCT"] = row["TPS"]

                if row.get("OIL_PRESS_BAR") is None and row.get("OIL_PRESS") is not None:
                    row["OIL_PRESS_BAR"] = row["OIL_PRESS"]

                if row.get("CHT_C") is None:
                    chts = [float(row.get(f"CHT_{k}") or 0.0) for k in range(1, 5) if row.get(f"CHT_{k}") is not None]
                    if chts:
                        row["CHT_C"] = round(max(chts), 1)

                times.append(elapsed)
                rows.append(row)

        if not times:
            return None

        # Sort if needed
        if times != sorted(times):
            paired = sorted(zip(times, rows), key=lambda p: p[0])
            times = [p[0] for p in paired]
            rows = [p[1] for p in paired]

        idx = _FrameIndex(times=times, rows=rows)
        self._frame_cache[mission_id] = idx
        return idx

    def get_frame(self, mission_id: str, time_sec: float) -> Optional[Dict[str, Any]]:
        """Returns the telemetry sample at-or-before `time_sec`. O(log n) via bisect."""
        idx = self._load_frames(mission_id)
        if idx is None or not idx.times:
            return None
        pos = bisect.bisect_right(idx.times, time_sec) - 1
        pos = max(0, min(pos, len(idx.times) - 1))
        return idx.rows[pos]
