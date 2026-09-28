"""Sortie Exporter and Debrief Generator (ARCH-2026-MP-001, Task 1.5).

Persists completed or aborted mission simulations into standard telemetry CSVs,
JSON manifests, event timelines, and debrief documentation. Fully compatible with
backend.telemetry.replay_engine.ReplayEngine for high-fidelity replay scrubbing.
"""

from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import MissionDefinition, MissionState


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


class SortieExporter:
    """Exports simulated mission execution records into replayable sorties and reports."""

    def __init__(self, output_root: Optional[Path] = None) -> None:
        self.root = output_root or _repo_root()
        self.live_sorties_dir = self.root / "data" / "telemetry" / "live_sorties"
        self.report_dump_dir = self.root / "report_dump"

        self.live_sorties_dir.mkdir(parents=True, exist_ok=True)
        self.report_dump_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        definition: MissionDefinition,
        final_state: MissionState,
        recorded_frames: List[Dict[str, Any]],
        fault_timeline: List[Dict[str, Any]],
        start_epoch: float,
        end_epoch: float,
    ) -> Dict[str, str]:
        """Writes the full bundle: live CSV, report_dump bundle, and debrief.md.

        Returns a dictionary of generated artifact file paths.
        """
        mission_id = definition.mission_id
        timestamp_str = datetime.fromtimestamp(start_epoch, tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
        sortie_id = f"SORTIE-MSN-{timestamp_str}"

        # 1. Target Directories
        mission_dump_dir = self.report_dump_dir / mission_id
        readings_dir = mission_dump_dir / "readings"
        timeline_dir = mission_dump_dir / "timeline"
        health_dir = mission_dump_dir / "health"

        readings_dir.mkdir(parents=True, exist_ok=True)
        timeline_dir.mkdir(parents=True, exist_ok=True)
        health_dir.mkdir(parents=True, exist_ok=True)

        live_csv_path = self.live_sorties_dir / f"{sortie_id}.csv"
        dump_csv_path = readings_dir / "telemetry_log.csv"
        mission_json_path = mission_dump_dir / "mission.json"
        timeline_json_path = timeline_dir / "fault_timeline.json"
        debrief_md_path = mission_dump_dir / "debrief.md"

        # 2. Write CSVs (identical headers and contents)
        headers = [
            "TIMESTAMP_SEC", "ENGINE_RPM", "PROP_RPM", "TPS",
            "LAT", "LON", "AGL_M", "HEADING_DEG", "PITCH_DEG", "ROLL_DEG",
            "CHT_1", "CHT_2", "CHT_3", "CHT_4",
            "EGT_1", "EGT_2", "EGT_3", "EGT_4",
            "OIL_PRESS", "OIL_TEMP", "FUEL_FLOW", "FUEL_RAIL_P",
            "MAP", "BUS_VOLTAGE", "BATTERY_CURRENT",
            "FADEC_ACTIVE_LANE", "ALTITUDE_FT", "OAT_C", "TAS_KNOTS",
            "FLIGHT_PHASE", "THEATER", "DIAG_FAULT_ID", "HEALTH_INDEX",
        ]

        def _write_csv(file_path: Path):
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
                writer.writeheader()
                for row in recorded_frames:
                    writer.writerow(row)

        _write_csv(live_csv_path)
        _write_csv(dump_csv_path)

        # 3. Write Timeline
        with open(timeline_json_path, "w", encoding="utf-8") as f:
            json.dump(fault_timeline, f, indent=2)

        # 4. Write Manifest (mission.json)
        duration_hours = round((end_epoch - start_epoch) / 3600.0, 4)
        # Continuous reliability-engine output, not a binary nominal/degraded toggle.
        health_end = round(final_state.mission_reliability, 4)

        manifest = {
            "sortie_id": sortie_id,
            "mission_id": mission_id,
            "name": definition.name,
            "engine_id": definition.engine_id,
            "uav_tail_number": f"{definition.airframe_id}-01",
            "region": definition.environment.theater_name,
            "theater": definition.environment.theater_name,
            "status": final_state.status,
            "severity": "CRITICAL" if final_state.confirmed_anomaly else "NOMINAL",
            "start_time": datetime.fromtimestamp(start_epoch, tz=timezone.utc).isoformat(),
            "end_time": datetime.fromtimestamp(end_epoch, tz=timezone.utc).isoformat(),
            "start_epoch": start_epoch,
            "end_epoch": end_epoch,
            "duration_hours": duration_hours,
            "health_index_start": 1.0,
            "health_index_end": health_end,
            "fault_count": len(fault_timeline),
            "open_actions": len(final_state.active_faults),
            "generated_by": "anumaan_mission_executive",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_at_epoch": time.time(),
            "categories": {
                "readings": ["telemetry_log.csv"],
                "timeline": ["fault_timeline.json"],
                "debrief": ["debrief.md"],
            },
        }

        with open(mission_json_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 5. Write Debrief Report
        debrief_content = f"""# Post-Mission Sortie Debrief

**Mission ID:** `{mission_id}`  
**Sortie ID:** `{sortie_id}`  
**Engine Profile:** `{definition.engine_id}`  
**Airframe:** `{definition.airframe_id}`  
**Theater:** `{definition.environment.theater_name}`  
**Status:** **{final_state.status}**  
**Duration:** {round(final_state.time_elapsed_sec, 1)} seconds ({duration_hours} hours)  
**Total Simulation Frames:** {len(recorded_frames)}  

---

## 1. Flight Execution & Atmospheric Profile
- **Base Airfield Elevation:** {definition.environment.base_elevation_m} m AMSL
- **Final Position:** X: {final_state.pos_x_m} m, Y: {final_state.pos_y_m} m, Alt: {final_state.pos_z_m} m AMSL
- **Final Airspeed:** {final_state.true_airspeed_ktas} KTAS ({final_state.indicated_airspeed_kias} KIAS)
- **Ambient Conditions:** OAT: {final_state.ambient_oat_c} °C, Ambient Pressure: {final_state.ambient_pressure_hpa} hPa
- **Density Altitude:** {final_state.density_altitude_ft} ft

---

## 2. Propulsion Health & Fault Diagnostic Chain
- **Active Faults:** {len(final_state.active_faults)}
- **Top Divergent Channel:** `{final_state.top_divergent_channel or "None"}`
- **Residual Alarm Active:** {final_state.residual_alarm}
- **Confirmed Anomaly:** {final_state.confirmed_anomaly}
- **FlyHash Novelty Score:** {final_state.flyhash_novelty_score} (Novel: {final_state.is_novel_pattern})
- **Top Diagnostic Hypothesis:** `{final_state.top_diagnostic_hypothesis or "NOMINAL"}`
- **Diagnostic Confidence:** {round(final_state.diagnostic_confidence * 100.0, 1)}%
- **Mission Reliability Index:** {round(final_state.mission_reliability * 100.0, 2)}%
- **Prescriptive Recommendation:** {final_state.prescriptive_advisory}

---

## 3. Event & Fault Timeline
"""
        if fault_timeline:
            debrief_content += "| Sim Time (s) | Mode | Cylinder | Severity | Ramp (s) | Origin |\n"
            debrief_content += "|---|---|---|---|---|---|\n"
            for ev in fault_timeline:
                cyl_str = str(ev.get("cylinder")) if ev.get("cylinder") is not None else "-"
                debrief_content += f"| {round(ev.get('t', 0.0), 1)} | `{ev.get('mode', '-')}` | {cyl_str} | {ev.get('severity', 0.0)} | {ev.get('ramp_sec', 0.0)} | {ev.get('origin', '-')} |\n"
        else:
            debrief_content += "*No faults injected or triggered during this sortie. Nominal flight profile.* \n"

        debrief_content += f"""
---
*Generated autonomously by Project ANUMAAN Mission Planning Executive.*
"""

        with open(debrief_md_path, "w", encoding="utf-8") as f:
            f.write(debrief_content)

        return {
            "live_csv": str(live_csv_path),
            "dump_csv": str(dump_csv_path),
            "manifest": str(mission_json_path),
            "timeline": str(timeline_json_path),
            "debrief": str(debrief_md_path),
        }
