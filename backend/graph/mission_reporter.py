"""
Post-Flight Mission Reporter — Phase J
DRDO / iDEX Problem Statement ID: 26054

Generates standardized post-flight engineering debriefs (MISSION_xxx.md)
with YAML frontmatter, verified against the Mission Knowledge Graph.

PS reference: doc04 §2 — "Standardized Mission Records (MISSION_xxx.md)"
Schema fields (uav_tail_number, ambient_environment, telemetry_log_path,
chronological timeline, checkbox-style maintenance directives) match the
documented example there field-for-field, sourced from real graph/sortie
data rather than the placeholder frontmatter this reporter used to emit.
"""

import os
import time
from typing import Dict, Any, Optional, List
from backend.graph.mission_graph import MissionKnowledgeGraph, SortieNode, AnomalyEventNode, MaintenanceActionNode

# Static per-theater context. Only oat/altitude are ever sensor-derived (SortieNode's
# tracked envelope); base/flight_profile/humidity are documented operational reference
# values for the two PS-26054 theaters, not telemetry — the 27-parameter dictionary
# (doc03 §1) has no onboard humidity channel, so that figure is explicitly labeled as
# a climatological reference rather than a live reading.
THEATER_INFO = {
    "LADAKH": {
        "theater": "Northern Sector (Ladakh)",
        "base": "Leh Air Force Station (3,256m MSL)",
        "flight_profile": "High-Altitude ISR Loiter",
        "humidity_percent_reference": 18,
    },
    "THAR_DESERT": {
        "theater": "Western Sector (Thar Desert)",
        "base": "Jaisalmer Air Force Station (225m MSL)",
        "flight_profile": "Extreme-Heat Desert Border Patrol",
        "humidity_percent_reference": 12,
    },
}
DEFAULT_THEATER_INFO = {
    "theater": "Unclassified Sector",
    "base": "Forward Operating Base",
    "flight_profile": "Standard ISR Loiter",
    "humidity_percent_reference": 20,
}


def _fmt_relative(epoch: float, start_epoch: float) -> str:
    """Format an epoch timestamp as T+HH:MM:SS relative to sortie start."""
    delta = max(0, int(epoch - start_epoch))
    h, rem = divmod(delta, 3600)
    m, s = divmod(rem, 60)
    return f"T+{h:02d}:{m:02d}:{s:02d}"


class MissionReporter:
    """Auto-generates structured MISSION_xxx.md debrief artifacts."""

    def __init__(self, output_dir: Optional[str] = None):
        if output_dir is None:
            output_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../../data/mission_reports")
            )
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_report(self, graph: MissionKnowledgeGraph, sortie_id: str) -> str:
        """
        Generate a Markdown debrief document with YAML frontmatter.

        Returns:
            Path to the saved report file.
        """
        sortie = graph.sorties.get(sortie_id)
        if not sortie:
            raise ValueError(f"Sortie {sortie_id} not found in knowledge graph.")

        anomaly_ids = graph.sortie_anomalies.get(sortie_id, [])
        anomalies = [graph.anomalies[aid] for aid in anomaly_ids if aid in graph.anomalies]
        action_ids = graph.sortie_actions.get(sortie_id, [])
        actions = [graph.maintenance_actions[aid] for aid in action_ids if aid in graph.maintenance_actions]

        theater_info = THEATER_INFO.get(sortie.region, DEFAULT_THEATER_INFO)

        frontmatter = self._build_frontmatter(sortie, theater_info, anomalies, actions)
        md_lines = [frontmatter, f"# Mission Debrief: {sortie.sortie_id}"]
        md_lines.extend(self._build_context_section(sortie, theater_info))
        md_lines.extend(self._build_timeline_section(sortie, anomalies, actions))
        md_lines.extend(self._build_directives_section(actions))
        md_lines.extend(self._build_cbm_table_section(actions))

        content = "\n".join(md_lines)
        file_path = os.path.join(self.output_dir, f"{sortie.sortie_id}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_frontmatter(self, sortie: SortieNode, theater_info: Dict[str, Any],
                           anomalies: List[AnomalyEventNode], actions: List[MaintenanceActionNode]) -> str:
        start_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(sortie.start_timestamp))
        end_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(sortie.end_timestamp or time.time()))
        date_str = time.strftime("%Y-%m-%d", time.gmtime(sortie.start_timestamp))

        oat_range = [sortie.min_oat_c, sortie.max_oat_c] if sortie.min_oat_c is not None else None
        alt_range = [sortie.min_altitude_ft, sortie.max_altitude_ft] if sortie.min_altitude_ft is not None else None
        ambient_lines = []
        if oat_range and alt_range:
            ambient_lines = [
                "ambient_environment:",
                f"  oat_range_celsius: [{oat_range[0]:.1f}, {oat_range[1]:.1f}]",
                f"  density_altitude_ft: [{int(alt_range[0])}, {int(alt_range[1])}]",
                f"  humidity_percent_reference: {theater_info['humidity_percent_reference']}"
                "  # regional climatological reference — no onboard humidity sensor channel exists",
            ]

        telemetry_line = ""
        if sortie.telemetry_log_path:
            rel_path = os.path.relpath(sortie.telemetry_log_path, os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../..")
            )).replace("\\", "/")
            telemetry_line = f'telemetry_log_path: "{rel_path}"'

        lines = [
            "---",
            f'sortie_id: "{sortie.sortie_id}"',
            f'uav_tail_number: "{sortie.uav_tail_number}"',
            f'date: "{date_str}"',
            f'theater: "{theater_info["theater"]}"',
            f'base: "{theater_info["base"]}"',
            f'flight_profile: "{theater_info["flight_profile"]}"',
            f"duration_hours: {sortie.flight_hours:.2f}",
            *ambient_lines,
        ]
        if telemetry_line:
            lines.append(telemetry_line)
        lines.extend([
            f"engine_health_index_start: {sortie.start_health_index:.2f}",
            f"engine_health_index_end: {sortie.final_health_index:.2f}",
            f"primary_events_logged: {len(anomalies)}",
            # Kept for backward-compat with the previous schema / anything already parsing it.
            f'theater_region: "{sortie.region}"',
            f'sortie_status: "{sortie.status}"',
            f'start_time: "{start_str}"',
            f'end_time: "{end_str}"',
            f"anomalies_detected: {len(anomalies)}",
            f"open_maintenance_actions: {len([a for a in actions if a.status == 'OPEN'])}",
            "---",
        ])
        return "\n".join(lines) + "\n"

    def _build_context_section(self, sortie: SortieNode, theater_info: Dict[str, Any]) -> List[str]:
        lines = [
            f"**Theater Region:** {theater_info['theater']} | **Flight Duration:** {sortie.flight_hours:.2f} hrs "
            f"| **Final Propulsion Health:** {sortie.final_health_index*100:.1f}%\n",
            "## 1. Environmental & Operational Context",
        ]
        if sortie.min_oat_c is not None:
            lines.append(
                f"* **Mission Regime:** {theater_info['flight_profile']} at "
                f"{sortie.min_altitude_ft:.0f}–{sortie.max_altitude_ft:.0f} ft MSL, "
                f"{sortie.min_oat_c:.1f}°C to {sortie.max_oat_c:.1f}°C OAT observed over the sortie."
            )
        else:
            lines.append(f"* **Mission Regime:** {theater_info['flight_profile']} ({theater_info['base']}).")
        lines.append(f"* **Base:** {theater_info['base']}.")
        return lines

    def _build_timeline_section(self, sortie: SortieNode, anomalies: List[AnomalyEventNode],
                                actions: List[MaintenanceActionNode]) -> List[str]:
        lines = ["\n## 2. Chronological Timeline & Anomaly Events"]
        # Interleave anomalies and their matching maintenance actions (same sortie, matched by
        # subsystem — actions don't carry their own detection timestamp, so they're shown
        # immediately after the anomaly that triggered them).
        events = sorted([(a.timestamp_epoch, a) for a in anomalies], key=lambda x: x[0])

        if not events:
            lines.append(
                f"* **T+00:00 to {_fmt_relative(sortie.end_timestamp or time.time(), sortie.start_timestamp)}:** "
                "Nominal flight profile maintained throughout. All 27 telemetry channels remained inside the "
                "certified operating envelope; no thermodynamic drift or mechanical vibration exceedances "
                "were recorded."
            )
            return lines

        actions_by_subsystem: Dict[str, List[MaintenanceActionNode]] = {}
        for act in actions:
            actions_by_subsystem.setdefault(act.subsystem_id, []).append(act)

        for ts, a in events:
            rel = _fmt_relative(ts, sortie.start_timestamp)
            if a.trend_note:
                lines.append(f"* **{rel} [ANOMALY DETECTED]:** {a.trend_note}")
            lines.append(
                f"* **{rel} [FAULT {a.fault_id:02d} CONFIRMED]:** Fast ML classifier confirmed "
                f"*{a.fault_name}* on `{a.subsystem_id}` (Score: {a.anomaly_score:.2f}, {a.ata_chapter})."
            )
            lines.append(f"* **{rel} [ACTION TAKEN]:** Operator directive issued: {a.recommended_action}")
            for act in actions_by_subsystem.get(a.subsystem_id, []):
                if act.rul_p10_hours is not None:
                    lines.append(
                        f"* **{rel} [MAINTENANCE ORDER `{act.action_id}`]:** {act.description} "
                        f"(RUL at time of order — P10: {act.rul_p10_hours:.1f} hrs / "
                        f"P50: {act.rul_p50_hours:.1f} hrs)"
                    )
        return lines

    def _build_directives_section(self, actions: List[MaintenanceActionNode]) -> List[str]:
        lines = ["\n## 3. Post-Flight Maintenance Directives (Generated by Reasoning Agent)"]
        if not actions:
            lines.append("No emergency or precautionary procedures were invoked during this sortie. "
                         "Propulsion certified for immediate turnaround.")
            return lines
        for act in actions:
            box = "[x]" if act.status == "SIGNED_OFF" else "[ ]"
            rul_note = ""
            if act.rul_p10_hours is not None:
                comp = act.limiting_component or act.subsystem_id
                rul_note = (f" Remaining Useful Life at time of order — {comp}: "
                           f"P10 {act.rul_p10_hours:.1f} hrs / P50 {act.rul_p50_hours:.1f} hrs.")
            lines.append(
                f"- {box} **Maintenance Order `{act.action_id}` [{act.ata_chapter}]:** {act.description}{rul_note}"
            )
        return lines

    def _build_cbm_table_section(self, actions: List[MaintenanceActionNode]) -> List[str]:
        lines = ["\n## 4. Condition-Based Maintenance (CBM) Work Orders"]
        if actions:
            lines.extend([
                "| Action ID | Subsystem | ATA Chapter | Maintenance Directive | RUL P10 / P50 (hrs) | Status |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ])
            for act in actions:
                rul_cell = (f"{act.rul_p10_hours:.1f} / {act.rul_p50_hours:.1f}"
                           if act.rul_p10_hours is not None else "—")
                lines.append(
                    f"| `{act.action_id}` | {act.subsystem_id} | `{act.ata_chapter}` | {act.description} "
                    f"| {rul_cell} | `{act.status}` |"
                )
        else:
            lines.append("Propulsion certified for immediate turnaround. Standard pre-flight inspection "
                         "checklist applies.")
        return lines
