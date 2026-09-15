"""
Canyon flight sortie recorder -> report_dump/
DRDO / iDEX Problem Statement ID: 26054

Records the standalone canyon simulator's flight as a post-mission report bundle in
exactly the same seven-category layout the backend digital twin emits, so both
simulators feed one Mission Knowledge Graph.

Design constraints, in order of priority:
  1. Never cost the 143 FPS flight loop anything measurable. Sampling is a plain
     append of a small tuple at 2 Hz; every report is assembled once, at shutdown.
  2. Never invent a report. The canyon sim runs flight dynamics and a thermodynamic
     CHT loop, not the ML detection pipeline — so it writes no fault-classifier
     output, and writes a prediction report only when it actually observed a thermal
     drift rate to project from. A category with nothing real behind it is simply
     absent, and the viewer then draws no node for it.

Stdlib only apart from the report writer, which is stdlib too.
"""

import csv
import math
import os
import sys
import time

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.reports.report_dump_writer import (  # noqa: E402
    ReportDumpWriter,
    format_elapsed,
    summarise_telemetry_csv,
    worst_severity,
)

SAMPLE_INTERVAL_S = 0.5          # 2 Hz telemetry record
CHT_LIMIT_C = 135.0              # Rotax 912 iS certified cylinder head limit (doc01 §4)
OIL_PRESS_MIN_BAR = 2.0

# The three DRDO fault scenarios this simulator can inject, mapped to the canonical
# PS-26054 fault matrix so its reports cite the same identifiers as the backend twin.
FAULT_SPECS = {
    "fault_overheat": {
        "fault_id": 1, "name": "CYLINDER_2_CHT_OVERHEAT", "severity": "CRITICAL",
        "subsystem": "Cylinder #2 Head Assembly", "ata": "ATA 72-00",
        "trigger": "CHT > 135 °C on Cylinder #2",
        "action": "Enrich fuel trim +12%, throttle back 15%, descend into denser cooling air.",
    },
    "fault_injector": {
        "fault_id": 2, "name": "FUEL_INJECTOR_1_CLOG", "severity": "WARNING",
        "subsystem": "Fuel Injection System & Rails", "ata": "ATA 73-10",
        "trigger": "Fuel flow drop with EGT divergence",
        "action": "Switch to Lane B ECU backup map, activate auxiliary boost pump.",
    },
    "fault_oil_loss": {
        "fault_id": 4, "name": "OIL_PRESSURE_LOSS", "severity": "WARNING",
        "subsystem": "Dry-Sump Lubrication Circuit", "ata": "ATA 79-00",
        "trigger": "Oil pressure < 2.0 bar",
        "action": "Throttle back to 4,200 RPM, initiate precautionary landing.",
    },
}

TELEMETRY_COLUMNS = [
    "TIMESTAMP_SEC", "ELAPSED_SEC", "ALTITUDE_M", "ALTITUDE_FT", "AGL_M",
    "AIRSPEED_KIAS", "GROUND_SPEED_MS", "HEADING_DEG", "PITCH_DEG", "ROLL_DEG",
    "ENGINE_RPM", "THROTTLE_PCT", "CHT_C", "CHT_RATE_C_S", "OIL_PRESS_BAR",
    "FUEL_FLOW_LH", "RADAR_FWD_M", "TTI_SEC", "COPILOT_ON", "MISSION_PHASE",
]


class FlightMissionRecorder:
    """Samples the live FlightState and exports one report bundle at shutdown."""

    def __init__(self, region="LADAKH", profile="Ladakh Canyon Low-Level Tactical Sortie"):
        self.region = region
        self.profile = profile
        self.start_epoch = time.time()
        self.samples = []
        self.events = []
        self.fault_onsets = {}       # state attribute -> epoch of first activation
        self.peak_cht = 0.0
        self.min_oil_press = 99.0
        self.max_cht_rate = 0.0
        self.min_agl = float("inf")
        self.min_altitude_ft = float("inf")
        self.max_altitude_ft = 0.0
        self.gcas_recoveries = 0
        self.gcas_warnings = 0
        self.crashed = False
        self.crash_detail = ""
        self._last_sample = 0.0
        self._prev_faults = {key: False for key in FAULT_SPECS}
        self._prev_warning = False
        self._prev_gcas = False

        self.log_event("MISSION_START", "NOMINAL", "Sortie launched",
                       f"{profile} — ingress at 5,800 m AMSL, Auto-GCAS armed.")

    # ------------------------------------------------------------------
    # Live capture — called from the flight loop
    # ------------------------------------------------------------------

    def log_event(self, event_type, severity, title, detail):
        self.events.append({
            "at": format_elapsed(time.time(), self.start_epoch),
            "epoch": round(time.time(), 3),
            "event_type": event_type,
            "severity": severity,
            "title": title,
            "detail": detail,
        })

    def sample(self, st):
        """
        One 2 Hz telemetry sample plus edge-detected event logging.

        Called every frame from the flight loop, so the early-out on the interval
        check is the hot path and everything below it runs 2x/sec at most.
        """
        now = time.time()
        if now - self._last_sample < SAMPLE_INTERVAL_S:
            return
        self._last_sample = now

        self.samples.append((
            round(now, 3),
            round(now - self.start_epoch, 2),
            round(st.altitude_m, 1),
            round(st.altitude_ft, 1),
            round(st.agl_m, 1),
            round(st.airspeed_kias, 1),
            # Ground speed logged consistently with airspeed_kias (both reflect the actual,
            # GROUND_SPEED_MULTIPLIER-scaled movement rate) — st.speed_ms alone is only the
            # internal aerodynamic model's speed, not what the aircraft visibly covers ground at.
            round(st.airspeed_kias * (1852.0 / 3600.0), 1),
            round(st.heading_deg, 1),
            round(math.degrees(st.pitch_rad), 2),
            round(math.degrees(st.roll_rad), 2),
            round(st.rpm, 1),
            round(st.throttle_pct, 1),
            round(st.cht_c, 2),
            round(st.cht_rate_c_s, 4),
            round(st.oil_p_bar, 3),
            round(st.fuel_flow_lh, 2),
            round(st.fwd_dist_m, 1),
            round(st.tti_s, 2),
            int(bool(st.copilot_on)),
            st.mission_phase,
        ))

        self.peak_cht = max(self.peak_cht, st.cht_c)
        self.min_oil_press = min(self.min_oil_press, st.oil_p_bar)
        self.max_cht_rate = max(self.max_cht_rate, st.cht_rate_c_s)
        self.min_agl = min(self.min_agl, st.agl_m)
        self.min_altitude_ft = min(self.min_altitude_ft, st.altitude_ft)
        self.max_altitude_ft = max(self.max_altitude_ft, st.altitude_ft)

        for key, spec in FAULT_SPECS.items():
            active = bool(getattr(st, key, False))
            if active and not self._prev_faults[key]:
                self.fault_onsets.setdefault(key, now)
                self.log_event("FAULT_INJECTED", spec["severity"],
                               f"Fault {spec['fault_id']:02d} — {spec['name']}",
                               f"{spec['trigger']} on {spec['subsystem']} ({spec['ata']}).")
                self.log_event("ACTION_ISSUED", spec["severity"],
                               "Prescriptive directive issued", spec["action"])
            elif not active and self._prev_faults[key]:
                self.log_event("FAULT_CLEARED", "NOMINAL",
                               f"Fault {spec['fault_id']:02d} cleared",
                               f"{spec['subsystem']} returned inside the certified envelope.")
            self._prev_faults[key] = active

        if st.warning_active and not self._prev_warning:
            self.gcas_warnings += 1
            self.log_event("GCAS_WARNING", "WARNING", "Terrain proximity advisory",
                           f"Time-to-impact {st.tti_s:.1f} s at {st.agl_m:.0f} m AGL.")
        self._prev_warning = st.warning_active

        if st.gcas_active and not self._prev_gcas:
            self.gcas_recoveries += 1
            self.log_event("GCAS_RECOVERY", "CRITICAL", "Auto-GCAS recovery commanded",
                           f"Automatic 2.5 G pull-up at {st.agl_m:.0f} m AGL "
                           f"(TTI {st.tti_s:.1f} s).")
        self._prev_gcas = st.gcas_active

    def log_crash(self, st, impact_type):
        self.crashed = True
        self.crash_detail = (f"{impact_type} at {st.altitude_m:.0f} m AMSL, "
                             f"{st.agl_m:.0f} m AGL, {st.airspeed_kias:.0f} KIAS, "
                             f"Copilot {'ON' if st.copilot_on else 'OFF'}.")
        self.log_event("CFIT_IMPACT", "CRITICAL", "Controlled flight into terrain",
                       self.crash_detail)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(self, st=None, root=None):
        """
        Write the bundle. Returns the mission folder path, or None if the sortie was
        too short to have recorded anything worth a debrief.
        """
        if len(self.samples) < 2:
            return None

        end = time.time()
        duration_hours = (end - self.start_epoch) / 3600.0
        active_faults = [FAULT_SPECS[k] for k in self.fault_onsets]
        severity = "CRITICAL" if self.crashed else worst_severity(
            [f["severity"] for f in active_faults]
        )
        health = self._health_index()

        self.log_event("MISSION_END", "CRITICAL" if self.crashed else "NOMINAL",
                       "Sortie terminated — " + ("AIRFRAME LOST" if self.crashed else "RECOVERED"),
                       f"{duration_hours * 3600:.0f} s flown. Peak CHT {self.peak_cht:.1f} °C, "
                       f"minimum oil pressure {self.min_oil_press:.2f} bar, "
                       f"final propulsion health {health * 100:.1f}%.")

        writer = ReportDumpWriter(root=root)
        mission_dir = writer.allocate_mission_dir()
        csv_path = self._write_telemetry_csv(mission_dir)

        manifest = {
            "sortie_id": f"SORTIE-CANYON-{time.strftime('%Y%m%d-%H%M%S', time.gmtime(self.start_epoch))}",
            "name": self.profile,
            "uav_tail_number": "TAPAS-BH-201-AF01",
            "region": self.region,
            "theater": "Northern Sector (Ladakh)",
            "status": "ABORTED" if self.crashed else "COMPLETED",
            "severity": severity,
            "start_time": _iso(self.start_epoch),
            "end_time": _iso(end),
            "start_epoch": round(self.start_epoch, 3),
            "end_epoch": round(end, 3),
            "duration_hours": round(duration_hours, 4),
            "health_index_start": 1.0,
            "health_index_end": round(health, 3),
            "fault_count": len(active_faults),
            "open_actions": len(active_faults) + (1 if self.crashed else 0),
            "altitude_range_ft": [int(self.min_altitude_ft), int(self.max_altitude_ft)],
            "generated_by": "canyon_flight_sim",
        }

        # allocate_mission_dir() already reserved the folder, so write_mission() would
        # claim a second one. Write straight into the reserved folder instead.
        writer_root_backup = writer.root
        writer.root = os.path.dirname(mission_dir)
        try:
            return _write_into(
                writer, mission_dir, manifest,
                readings=summarise_telemetry_csv(csv_path),
                health=self._build_health(health),
                faults=self._build_faults(active_faults),
                timeline=self._build_timeline(end, duration_hours),
                predictions=self._build_predictions(),
                actions=self._build_actions(active_faults),
                summary=self._build_summary(manifest, active_faults, health),
            )
        finally:
            writer.root = writer_root_backup

    # --- category builders --------------------------------------------------

    def _health_index(self):
        """
        Health from the two continuously modelled channels: thermal margin against the
        135 °C CHT limit and lubrication margin against the 2.0 bar floor. A CFIT
        impact zeroes it outright.
        """
        if self.crashed:
            return 0.0
        thermal = max(0.0, min(1.0, (CHT_LIMIT_C - self.peak_cht) / 40.0))
        lubrication = max(0.0, min(1.0, (self.min_oil_press - OIL_PRESS_MIN_BAR) / 2.0))
        return round(0.25 + 0.45 * thermal + 0.30 * lubrication, 3)

    def _build_health(self, health):
        return {
            "engine_health_index_start": 1.0,
            "engine_health_index_end": health,
            "health_degradation": round(1.0 - health, 3),
            "peak_cht_c": round(self.peak_cht, 2),
            "cht_limit_c": CHT_LIMIT_C,
            "cht_margin_c": round(CHT_LIMIT_C - self.peak_cht, 2),
            "max_cht_rise_rate_c_per_s": round(self.max_cht_rate, 4),
            "minimum_oil_pressure_bar": round(self.min_oil_press, 3),
            "oil_pressure_floor_bar": OIL_PRESS_MIN_BAR,
            "minimum_agl_m": round(self.min_agl, 1) if self.min_agl < float("inf") else None,
            "auto_gcas_warnings": self.gcas_warnings,
            "auto_gcas_recoveries": self.gcas_recoveries,
            "airframe_lost": self.crashed,
        }

    def _build_faults(self, active_faults):
        if not active_faults:
            return None
        detections = []
        for key, onset in self.fault_onsets.items():
            spec = FAULT_SPECS[key]
            detections.append({
                "detected_at": format_elapsed(onset, self.start_epoch),
                "detected_at_epoch": round(onset, 3),
                "fault_id": spec["fault_id"],
                "fault_name": spec["name"],
                "severity": spec["severity"],
                "ata_chapter": spec["ata"],
                "subsystem": spec["subsystem"],
                "sensor_trigger": spec["trigger"],
                "detection_source": "FADEC threshold monitor (flight simulator)",
                "recommended_action": spec["action"],
            })
        detections.sort(key=lambda d: d["detected_at_epoch"])
        return {"total_detections": len(detections), "detections": detections}

    def _build_timeline(self, end, duration_hours):
        return {
            "mission_start": _iso(self.start_epoch),
            "mission_end": _iso(end),
            "duration_hours": round(duration_hours, 4),
            "event_count": len(self.events),
            "events": self.events,
        }

    def _build_predictions(self):
        """
        Only written when a real thermal drift rate was measured — this simulator has
        no ML prognostics stack, so there is nothing else honest to project.
        """
        if self.max_cht_rate <= 0.01:
            return None
        margin = CHT_LIMIT_C - self.peak_cht
        seconds_to_limit = margin / self.max_cht_rate if self.max_cht_rate > 0 else None
        return {
            "method": "Linear extrapolation of the observed CHT rise rate against the "
                      "135 °C certified cylinder head limit.",
            "observed_cht_rise_rate_c_per_s": round(self.max_cht_rate, 4),
            "peak_cht_c": round(self.peak_cht, 2),
            "thermal_margin_c": round(margin, 2),
            "projected_seconds_to_cht_limit": (round(seconds_to_limit, 1)
                                               if seconds_to_limit and seconds_to_limit > 0 else 0.0),
            "advisory": ("Thermal limit already breached — descend into denser air immediately."
                         if margin <= 0 else
                         "Maintain convective cooling profile; re-evaluate on the next climb."),
        }

    def _build_actions(self, active_faults):
        directives = [f["action"] for f in active_faults]
        orders = [{
            "action_id": f"MAINT-CANYON-{i + 1:03d}",
            "subsystem_id": spec["subsystem"],
            "ata_chapter": spec["ata"],
            "description": f"Post-flight inspection of {spec['subsystem']} following an "
                           f"in-flight {spec['name'].replace('_', ' ').lower()} event.",
            "status": "OPEN",
        } for i, spec in enumerate(active_faults)]

        if self.crashed:
            orders.append({
                "action_id": f"MAINT-CANYON-{len(orders) + 1:03d}",
                "subsystem_id": "Airframe",
                "ata_chapter": "ATA 05-50",
                "description": "Airframe lost to controlled flight into terrain. "
                               "Raise a flight-safety investigation and impound the FDR record.",
                "status": "OPEN",
            })
        if self.gcas_recoveries:
            orders.append({
                "action_id": f"MAINT-CANYON-{len(orders) + 1:03d}",
                "subsystem_id": "Airframe / Powerplant Mounts",
                "ata_chapter": "ATA 05-51",
                "description": f"{self.gcas_recoveries} automatic 2.5 G terrain recovery "
                               f"pull-up(s) flown — perform a hard-manoeuvre load inspection.",
                "status": "OPEN",
            })

        if not directives and not orders:
            return None
        return {
            "open_orders": len(orders),
            "total_orders": len(orders),
            "maintenance_orders": orders,
            "in_flight_directives": directives or ["No prescriptive directive was required."],
        }

    def _build_summary(self, manifest, active_faults, health):
        lines = [
            "---",
            f'sortie_id: "{manifest["sortie_id"]}"',
            f'uav_tail_number: "{manifest["uav_tail_number"]}"',
            f'theater: "{manifest["theater"]}"',
            f'flight_profile: "{self.profile}"',
            f"duration_seconds: {int((time.time() - self.start_epoch))}",
            f"engine_health_index_end: {health:.2f}",
            f"primary_events_logged: {len(self.events)}",
            f'sortie_status: "{manifest["status"]}"',
            "---",
            "",
            f"# Mission Debrief: {manifest['sortie_id']}",
            "",
            f"**Profile:** {self.profile}  |  **Final Propulsion Health:** {health * 100:.1f}%",
            "",
            "## 1. Flight Envelope",
            f"* Altitude band flown: {self.min_altitude_ft:.0f} – {self.max_altitude_ft:.0f} ft AMSL.",
            f"* Minimum terrain clearance: {self.min_agl:.0f} m AGL.",
            f"* Peak cylinder head temperature: {self.peak_cht:.1f} °C "
            f"(limit {CHT_LIMIT_C:.0f} °C, margin {CHT_LIMIT_C - self.peak_cht:.1f} °C).",
            f"* Minimum oil pressure: {self.min_oil_press:.2f} bar (floor {OIL_PRESS_MIN_BAR:.1f} bar).",
            "",
            "## 2. Terrain Safety",
            f"* Auto-GCAS proximity advisories: {self.gcas_warnings}.",
            f"* Automatic terrain recoveries commanded: {self.gcas_recoveries}.",
        ]
        if self.crashed:
            lines.append(f"* **AIRFRAME LOST:** {self.crash_detail}")
        else:
            lines.append("* Airframe recovered with terrain separation maintained throughout.")

        lines += ["", "## 3. Propulsion Events"]
        if active_faults:
            for spec in active_faults:
                lines.append(f"- [ ] **Fault {spec['fault_id']:02d} — {spec['name']}** "
                             f"[{spec['ata']}]: {spec['action']}")
        else:
            lines.append("No propulsion faults were injected or detected during this sortie.")
        return "\n".join(lines)

    # --- telemetry file -----------------------------------------------------

    def _write_telemetry_csv(self, mission_dir):
        directory = os.path.join(mission_dir, "readings")
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "telemetry_log.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(TELEMETRY_COLUMNS)
            writer.writerows(self.samples)
        return path


def _write_into(writer, mission_dir, manifest, readings, health, faults,
                timeline, predictions, actions, summary):
    """Write every category into an already-reserved mission folder, then the manifest."""
    import json

    written = {"readings": ["telemetry_log.csv"]}
    if readings:
        writer._write_json(mission_dir, "readings", "sensor_channels.json", readings)
        written["readings"].append("sensor_channels.json")

    for category, filename, payload in (
        ("health", "engine_health.json", health),
        ("faults", "faults_detected.json", faults),
        ("timeline", "fault_timeline.json", timeline),
        ("predictions", "flight_predictions.json", predictions),
        ("actions", "recommended_actions.json", actions),
    ):
        if payload:
            writer._write_json(mission_dir, category, filename, payload)
            written[category] = [filename]

    if summary:
        writer._write_text(mission_dir, "mission_summary", "mission_summary.md", summary)
        written["mission_summary"] = ["mission_summary.md"]

    full = dict(manifest)
    full.update({
        "mission_id": os.path.basename(mission_dir),
        "generated_at": _iso(time.time()),
        "generated_at_epoch": round(time.time(), 3),
        "categories": written,
    })
    path = os.path.join(mission_dir, "mission.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(full, f, indent=2, default=str)
    os.replace(tmp, path)
    return mission_dir


def _iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))
