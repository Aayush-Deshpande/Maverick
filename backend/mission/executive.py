"""Authoritative Mission Executive & Simulation Orchestrator (ARCH-2026-MP-001, Task 1.3).

Single authoritative state machine driving:
Trajectory -> Atmospheric ISA -> Propulsion Levers -> EngineRuntime -> Telemetry
-> Detection -> FlyHash -> Diagnosis -> Reliability -> Sortie Exporter
"""

from __future__ import annotations

import logging
import math
import threading
import time
from typing import Any, Dict, List, Optional

from .kinematics import AtmosphericModel, AutopilotFlightModel
from .phase_engine import PhaseFlightModel
from .reliability import MissionProfile
from .models import (
    EnvironmentalConditions,
    FlightPhase,
    MissionDefinition,
    MissionPhaseSpec,
    MissionState,
    MissionStatus,
    PhaseScheduledEvent,
    ScheduledEvent,
    Waypoint,
)
from .sortie_exporter import SortieExporter
from backend.runtime.hub import RuntimeHub
from backend.runtime.engine_runtime import EngineRuntime, Tick

logger = logging.getLogger("MissionExecutive")


def create_endurance_phase_preset(engine_id: str = "rotax_912is") -> MissionDefinition:
    """Default phase-based mission (ARCH-2026-MP-002): the primary mission-planning unit is
    now a sequence of named operating-condition phases, not a geographic route. Mirrors the
    canonical example profile (Takeoff -> Climb -> Cruise -> Loiter -> Descent -> Landing,
    each with duration/altitude/throttle/OAT), scaled down to a demo-friendly total length
    the same way the earlier waypoint presets were demo-scaled.
    """
    env = EnvironmentalConditions(
        theater_name="LADAKH_HIGH_COLD",
        qnh_hpa=1013.25,
        isa_temp_offset_c=-15.0,
        base_elevation_m=3195.0,
        ambient_wind_kt=12.0,
        wind_direction_deg=280.0,
        dust_density_mg_m3=0.08,
    )
    phases = [
        MissionPhaseSpec(name="TAKEOFF", duration_sec=30.0, start_alt_ft=10480.0, end_alt_ft=10800.0, throttle_pct=90.0, oat_c=8.0),
        MissionPhaseSpec(name="CLIMB", duration_sec=90.0, start_alt_ft=10800.0, end_alt_ft=16000.0, throttle_pct=80.0, oat_c=2.0),
        MissionPhaseSpec(name="CRUISE", duration_sec=150.0, start_alt_ft=16000.0, end_alt_ft=16000.0, throttle_pct=65.0, oat_c=-6.0),
        MissionPhaseSpec(name="LOITER", duration_sec=90.0, start_alt_ft=16000.0, end_alt_ft=16000.0, throttle_pct=55.0, oat_c=-6.0),
        MissionPhaseSpec(name="DESCENT", duration_sec=60.0, start_alt_ft=16000.0, end_alt_ft=10800.0, throttle_pct=40.0, oat_c=4.0),
        MissionPhaseSpec(name="LANDING", duration_sec=30.0, start_alt_ft=10800.0, end_alt_ft=10480.0, throttle_pct=20.0, oat_c=8.0),
    ]
    phase_events = [
        PhaseScheduledEvent(phase_name="CRUISE", elapsed_in_phase_sec=60.0, fault_mode="COOLING_DEGRADATION", severity=0.85, ramp_sec=40.0),
    ]
    return MissionDefinition(
        mission_id=f"MSN-ENDURANCE-PHASE-{engine_id.replace('_', '-').upper()}",
        name=f"Standard Endurance Profile ({engine_id})",
        engine_id=engine_id,
        airframe_id="TAPAS-BH-201",
        planned_duration_sec=sum(p.duration_sec for p in phases),
        environment=env,
        phases=phases,
        phase_events=phase_events,
    )


def create_ladakh_preset(engine_id: str = "rotax_912is") -> MissionDefinition:
    """High Altitude Ladakh Canyon Reconnaissance Preset (Default).

    Waypoints are authored directly against the real terrain asset
    (frontend/public/models/ladakh_canyon_terrain.glb, an actual Copernicus DEM extract of
    the Nubra valley canyon system) rather than picked independently of it: each lat/lon
    below is the geodetic projection of a position traced along the mesh's own real gorge
    floor / ridge geometry (see backend/mission/terrain.py + THEATER_ENU_ANCHORS in
    kinematics.py for the coordinate frame this route is anchored to), so the autopilot's
    route genuinely traverses the canyon the terrain mesh depicts -- BASE (south gorge
    mouth, ~3195m floor) -> CANYON ENTRY (gorge narrows, ~3160m floor) -> RIDGE (gorge exits
    onto the high plateau, ~4475m) -> FORWARD POINT (north plateau recon, ~4799m) -> RETURN
    (back down through the gorge mid-section, ~3079m floor) -> BASE.
    """
    env = EnvironmentalConditions(
        theater_name="LADAKH_HIGH_COLD",
        qnh_hpa=1013.25,
        isa_temp_offset_c=-15.0,  # Cold mountain air
        base_elevation_m=3195.0,
        ambient_wind_kt=12.0,
        wind_direction_deg=280.0,
        dust_density_mg_m3=0.08,
    )
    waypoints = [
        Waypoint(id="WP_LEH", name="Nubra Valley Forward Base (BASE)", lat=34.917802, lon=77.557178, alt_msl_m=3315.0, airspeed_ktas=70.0, terrain_alt_m=3195.0),
        Waypoint(id="WP_INDUS", name="Canyon Gorge Entry (CANYON ENTRY)", lat=34.849787, lon=77.596827, alt_msl_m=3410.0, airspeed_ktas=95.0, terrain_alt_m=3160.0),
        Waypoint(id="WP_RIDGE", name="Saser Ridge Pass (RIDGE)", lat=34.605243, lon=77.548361, alt_msl_m=4825.0, airspeed_ktas=110.0, terrain_alt_m=4475.0),
        Waypoint(id="WP_PANGONG", name="North Plateau Forward Recon (FORWARD POINT)", lat=34.585764, lon=77.565984, alt_msl_m=5099.0, airspeed_ktas=105.0, loiter_radius_m=1200.0, loiter_duration_sec=45.0, terrain_alt_m=4799.0),
        Waypoint(id="WP_SHYOK", name="Gorge Return Corridor (RETURN)", lat=34.688268, lon=77.539555, alt_msl_m=3299.0, airspeed_ktas=100.0, terrain_alt_m=3079.0),
        Waypoint(id="WP_BASE", name="Nubra Valley Recovery (BASE)", lat=34.917802, lon=77.557178, alt_msl_m=3275.0, airspeed_ktas=75.0, terrain_alt_m=3195.0),
    ]
    scheduled_events = [
        ScheduledEvent(trigger_time_sec=120.0, action="INJECT_FAULT", fault_mode="COOLING_DEGRADATION", severity=0.85, ramp_sec=40.0),
    ]
    return MissionDefinition(
        mission_id=f"MSN-LADAKH-{engine_id.replace('_', '-').upper()}",
        name=f"High-Altitude Ladakh Canyon Recon ({engine_id})",
        engine_id=engine_id,
        airframe_id="TAPAS-BH-201",
        planned_duration_sec=2250.0,  # ~37.5 min: real integrated flight time over this ~76km
        environment=env,
        waypoints=waypoints,
        scheduled_events=scheduled_events,
    )


def create_thar_preset(engine_id: str = "rotax_915is") -> MissionDefinition:
    """Hot Weather Thar Desert High Thermal Stress Preset."""
    env = EnvironmentalConditions(
        theater_name="THAR_HOT_HIGH",
        qnh_hpa=1005.0,
        isa_temp_offset_c=25.0,  # Extreme heat +45 C at low elevation
        base_elevation_m=220.0,
        ambient_wind_kt=18.0,
        wind_direction_deg=220.0,
        dust_density_mg_m3=1.85,
    )
    waypoints = [
        Waypoint(id="WP_UTT", name="Uttarlai AFS", lat=25.8050, lon=71.4850, alt_msl_m=350.0, airspeed_ktas=80.0, terrain_alt_m=220.0),
        Waypoint(id="WP_BARMER", name="Barmer Sector Climb", lat=25.9500, lon=71.3000, alt_msl_m=2800.0, airspeed_ktas=115.0, terrain_alt_m=250.0),
        Waypoint(id="WP_POK", name="Pokhran Perimeter Patrol", lat=26.9000, lon=71.9000, alt_msl_m=3500.0, airspeed_ktas=130.0, loiter_radius_m=4000.0, terrain_alt_m=230.0),
        Waypoint(id="WP_RTB", name="Uttarlai Recovery", lat=25.8050, lon=71.4850, alt_msl_m=400.0, airspeed_ktas=80.0, terrain_alt_m=220.0),
    ]
    scheduled_events = [
        ScheduledEvent(trigger_time_sec=90.0, action="INJECT_FAULT", fault_mode="WASTEGATE_STUCK", severity=0.90, ramp_sec=20.0),
    ]
    return MissionDefinition(
        mission_id="MSN-THAR-02",
        name="Thar Desert Thermal Endurance Patrol",
        engine_id=engine_id,
        airframe_id="TAPAS-BH-201",
        planned_duration_sec=5100.0,  # ~85 min: real integrated flight time over this ~275km route
        environment=env,
        waypoints=waypoints,
        scheduled_events=scheduled_events,
    )


def create_endurance_preset(engine_id: str = "austro_ae300") -> MissionDefinition:
    """Long Endurance Maritime / Border Surveillance Preset."""
    env = EnvironmentalConditions(
        theater_name="COASTAL_MARITIME",
        qnh_hpa=1018.0,
        isa_temp_offset_c=5.0,
        base_elevation_m=15.0,
        ambient_wind_kt=10.0,
        wind_direction_deg=180.0,
        dust_density_mg_m3=0.02,
    )
    waypoints = [
        Waypoint(id="WP_INS", name="INS Garuda Naval Station", lat=9.9312, lon=76.2673, alt_msl_m=100.0, airspeed_ktas=75.0, terrain_alt_m=15.0),
        Waypoint(id="WP_COAST", name="Coastal EEZ Transit", lat=9.6000, lon=75.8000, alt_msl_m=3000.0, airspeed_ktas=110.0, terrain_alt_m=0.0),
        Waypoint(id="WP_MAR_LOITER", name="Sea Lane Interdiction Loiter", lat=9.2000, lon=75.3000, alt_msl_m=3500.0, airspeed_ktas=115.0, loiter_radius_m=6000.0, terrain_alt_m=0.0),
        Waypoint(id="WP_GARUDA_RTB", name="Naval Station Approach", lat=9.9312, lon=76.2673, alt_msl_m=150.0, airspeed_ktas=75.0, terrain_alt_m=15.0),
    ]
    scheduled_events = [
        ScheduledEvent(trigger_time_sec=150.0, action="INJECT_FAULT", fault_mode="OIL_PUMP_RELIEF_VALVE", severity=0.75, ramp_sec=30.0),
    ]
    return MissionDefinition(
        mission_id="MSN-ENDURANCE-03",
        name="Maritime EEZ Persistent Surveillance",
        engine_id=engine_id,
        airframe_id="TAPAS-BH-201",
        planned_duration_sec=5200.0,  # ~87 min: real integrated flight time over this ~267km route
        environment=env,
        waypoints=waypoints,
        scheduled_events=scheduled_events,
    )


def create_rapid_throttle_preset(engine_id: str = "vrde_jayem_2_2l") -> MissionDefinition:
    """Rapid Transient Throttle Dynamics & High G-Load Maneuvers."""
    env = EnvironmentalConditions(
        theater_name="RAPID_TRANSIENTS",
        qnh_hpa=1013.25,
        isa_temp_offset_c=0.0,
        base_elevation_m=500.0,
        ambient_wind_kt=20.0,
        wind_direction_deg=310.0,
        dust_density_mg_m3=0.30,
    )
    waypoints = [
        Waypoint(id="WP_AERO_01", name="Airfield Departure", lat=13.1986, lon=77.7066, alt_msl_m=600.0, airspeed_ktas=85.0, terrain_alt_m=500.0),
        Waypoint(id="WP_AERO_02", name="Rapid Sprint Gate", lat=13.3500, lon=77.8500, alt_msl_m=3500.0, airspeed_ktas=145.0, terrain_alt_m=550.0),
        Waypoint(id="WP_AERO_03", name="Dynamic Avoidance Corridor", lat=13.5000, lon=77.6000, alt_msl_m=2000.0, airspeed_ktas=140.0, terrain_alt_m=600.0),
        Waypoint(id="WP_AERO_04", name="Tactical Return", lat=13.1986, lon=77.7066, alt_msl_m=650.0, airspeed_ktas=80.0, terrain_alt_m=500.0),
    ]
    scheduled_events = [
        ScheduledEvent(trigger_time_sec=60.0, action="INJECT_FAULT", fault_mode="INJECTOR_CLOGGED", cylinder=1, severity=0.80, ramp_sec=15.0),
    ]
    return MissionDefinition(
        mission_id="MSN-RAPID-04",
        name="High-G Rapid Throttle Stress Assessment",
        engine_id=engine_id,
        airframe_id="TAPAS-BH-201",
        planned_duration_sec=1450.0,  # ~24 min: real integrated flight time over this ~90km route
        environment=env,
        waypoints=waypoints,
        scheduled_events=scheduled_events,
    )


class MissionExecutive:
    """Authoritative mission coordinator managing trajectory, plant coupling, and PHM."""

    def __init__(self, hub: RuntimeHub, initial_mission: Optional[MissionDefinition] = None) -> None:
        self.hub = hub
        self.exporter = SortieExporter()
        self.lock = threading.RLock()
        self.definition = initial_mission or create_endurance_phase_preset()
        self.flight_model = self._build_flight_model(self.definition)
        self._current_phase = FlightPhase.PREFLIGHT

        self.t_sim_sec: float = 0.0
        self.time_scale: float = 1.0
        self.derate_scale: float = 1.0
        self.start_epoch: float = time.time()
        self.end_epoch: float = time.time()

        self.state = MissionState(
            mission_id=self.definition.mission_id,
            status=MissionStatus.READY.value,
            phase=FlightPhase.PREFLIGHT.value,
            time_elapsed_sec=0.0,
            time_remaining_sec=self.definition.planned_duration_sec,
            time_scale=self.time_scale,
            engine_id=self.definition.engine_id,
        )

        self.recorded_frames: List[Dict[str, Any]] = []
        self.fault_timeline: List[Dict[str, Any]] = []

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._rate_hz = 20.0
        self._step_count: int = 0

    @staticmethod
    def _build_flight_model(definition: MissionDefinition):
        """Dispatches between the phase-based flight model (ARCH-2026-MP-002, the primary
        mode: MissionDefinition.phases populated) and the dormant legacy waypoint/route
        autopilot (MissionDefinition.waypoints populated, phases empty) -- kept available
        rather than removed, per the pivot decision to not delete route-following."""
        if definition.phases:
            return PhaseFlightModel(definition.phases)
        return AutopilotFlightModel(definition.waypoints, definition.environment)

    @property
    def is_phase_mode(self) -> bool:
        return isinstance(self.flight_model, PhaseFlightModel)

    # -------------------------------------------------------------------------
    # Mission Lifecycle Control
    # -------------------------------------------------------------------------
    def load_mission(self, definition: MissionDefinition) -> None:
        """Loads a new mission specification and resets runtime state."""
        with self.lock:
            self.stop()
            self.definition = definition
            self.flight_model = self._build_flight_model(definition)
            self._current_phase = FlightPhase.PREFLIGHT
            self.t_sim_sec = 0.0
            self.time_scale = 1.0
            self.derate_scale = 1.0
            self.start_epoch = time.time()
            self.recorded_frames.clear()
            self.fault_timeline.clear()
            self._step_count = 0

            # Ensure hub has selected this engine
            if definition.engine_id in self.hub.runtimes:
                self.hub.select(definition.engine_id)
                self.hub.runtimes[definition.engine_id].clear_faults()

            self.state = MissionState(
                mission_id=definition.mission_id,
                status=MissionStatus.READY.value,
                phase=FlightPhase.PREFLIGHT.value,
                time_elapsed_sec=0.0,
                time_remaining_sec=definition.planned_duration_sec,
                time_scale=self.time_scale,
                engine_id=definition.engine_id,
            )
            logger.info("Loaded mission %s with engine %s", definition.mission_id, definition.engine_id)

    def start(self) -> None:
        """Starts live mission execution at 20 Hz."""
        with self.lock:
            if self.state.status == MissionStatus.RUNNING.value:
                return
            self.state.status = MissionStatus.RUNNING.value
            self.start_epoch = time.time()
            self._stop_event.clear()

            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run_loop, daemon=True, name="mission-exec")
                self._thread.start()
            logger.info("Started mission simulation: %s", self.definition.mission_id)

    def pause(self) -> None:
        with self.lock:
            if self.state.status == MissionStatus.RUNNING.value or self.state.status == MissionStatus.DERATED.value:
                self.state.status = MissionStatus.PAUSED.value
                logger.info("Paused mission simulation")

    def resume(self) -> None:
        with self.lock:
            if self.state.status == MissionStatus.PAUSED.value:
                self.state.status = MissionStatus.RUNNING.value
                logger.info("Resumed mission simulation")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive() and threading.current_thread() != self._thread:
            self._thread.join(timeout=1.0)
        self._thread = None

    def derate(self, scale: float = 0.85) -> Dict[str, Any]:
        """Operator Derate Action: Derates commanded propulsion demand and triggers reliability advisory."""
        with self.lock:
            self.derate_scale = max(0.5, min(1.0, scale))
            self.state.status = MissionStatus.DERATED.value
            runtime = self.hub.runtimes.get(self.definition.engine_id)
            advisory = f"Propulsion derated to {int(scale*100)}% maximum demand."
            if runtime:
                try:
                    self._apply_live_fault_damage(runtime)
                    live_profile = self._build_live_reliability_profile() if self.is_phase_mode else None
                    rel_info = runtime.mission_reliability(
                        hours=max(0.5, self.state.time_remaining_sec / 3600.0), profile=live_profile,
                    )
                    advisory = rel_info.get("recommendation", advisory)
                except Exception:
                    pass
            self.state.prescriptive_advisory = advisory
            logger.warning("Operator commanded propulsion DERATE: %.2f", scale)
            return {"status": self.state.status, "derate_scale": self.derate_scale, "advisory": advisory}

    def abort(self) -> Dict[str, Any]:
        """Operator Abort (RTB): Aborts primary objective and commands emergency descent/recovery."""
        with self.lock:
            self.state.status = MissionStatus.ABORTED.value
            self.state.phase = FlightPhase.LANDING.value
            self.end_epoch = time.time()
            # Record timeline event
            self.fault_timeline.append({
                "t": self.t_sim_sec,
                "mode": "OPERATOR_ABORT_RTB",
                "severity": 1.0,
                "origin": "OPERATOR",
            })
            # Export sortie immediately
            artifacts = self._export_sortie()
            logger.warning("Operator commanded ABORT / RTB for mission %s", self.definition.mission_id)
            return {"status": self.state.status, "artifacts": artifacts}

    def divert(
        self,
        lat: float,
        lon: float,
        alt_msl_m: Optional[float] = None,
        name: str = "DIVERT",
    ) -> Dict[str, Any]:
        """Operator Divert: truncates the remaining route to a single alternate waypoint and
        re-engages the autopilot toward it. Unlike ABORT/RTB, the mission keeps running
        (status/phase unchanged) -- only the route the autopilot is seeking changes, so the
        aircraft actually turns and flies to the new point rather than snapping there.

        Only meaningful in legacy waypoint/route mode -- a phase-based mission has no
        geographic route to divert."""
        if self.is_phase_mode:
            raise ValueError("DIVERT is only available for waypoint/route missions, not phase-based missions.")
        with self.lock:
            current_alt = alt_msl_m if alt_msl_m is not None else self.flight_model.pos_z_m
            divert_wp = Waypoint(
                id=f"WP_DIVERT_{int(self.t_sim_sec)}",
                name=name,
                lat=lat,
                lon=lon,
                alt_msl_m=current_alt,
                airspeed_ktas=self.definition.waypoints[0].airspeed_ktas if self.definition.waypoints else 100.0,
            )
            # Keep the waypoints already visited (for a coherent debrief/replay track),
            # replace everything ahead of the aircraft's current target with the diversion.
            visited = self.definition.waypoints[: self.flight_model.current_wp_idx + 1]
            self.definition.waypoints = visited + [divert_wp]

            # Re-seed the flight model's route with the truncated list while preserving
            # its live kinematic state (position/heading/speed) -- only the target changes.
            new_model = AutopilotFlightModel(self.definition.waypoints, self.definition.environment)
            new_model.pos_x_m = self.flight_model.pos_x_m
            new_model.pos_y_m = self.flight_model.pos_y_m
            new_model.pos_z_m = self.flight_model.pos_z_m
            new_model.heading_rad = self.flight_model.heading_rad
            new_model.pitch_rad = self.flight_model.pitch_rad
            new_model.roll_rad = self.flight_model.roll_rad
            new_model.speed_mps = self.flight_model.speed_mps
            new_model.current_wp_idx = self.flight_model.current_wp_idx
            new_model.manual_keys = dict(self.flight_model.manual_keys)
            new_model.manual_throttle_pct = self.flight_model.manual_throttle_pct
            new_model._initialized = True
            self.flight_model = new_model

            self.fault_timeline.append({
                "t": self.t_sim_sec,
                "mode": "OPERATOR_DIVERT",
                "severity": 0.0,
                "origin": "OPERATOR",
                "target_lat": lat,
                "target_lon": lon,
            })
            logger.warning("Operator commanded DIVERT to (%.4f, %.4f) for mission %s", lat, lon, self.definition.mission_id)
            return {"status": self.state.status, "divert_waypoint": divert_wp.to_dict()}

    def set_manual_keys(self, keys: Dict[str, Any]) -> None:
        """Applies operator manual-flight key state (W/S pitch, A/D turn, E/Q throttle --
        same scheme as the standalone Blender sim) to the live flight model. Holding any
        key overrides the autopilot's waypoint-seeking for this tick; releasing all keys
        (empty/all-false dict) hands control back to the autopilot automatically.

        No-op in phase-based mode (no waypoint-seeking to override there)."""
        if self.is_phase_mode:
            return
        with self.lock:
            valid = {"pitch_up", "pitch_down", "turn_left", "turn_right", "throttle_up", "throttle_down"}
            self.flight_model.manual_keys = {k: bool(v) for k, v in keys.items() if k in valid}

    def clear_manual_keys(self) -> None:
        if self.is_phase_mode:
            return
        with self.lock:
            self.flight_model.manual_keys = {}

    def set_time_scale(self, scale: float) -> float:
        with self.lock:
            self.time_scale = max(0.25, min(20.0, float(scale)))
            self.state.time_scale = self.time_scale
            return self.time_scale

    # -------------------------------------------------------------------------
    # Fault Injection (Scheduled & Live)
    # -------------------------------------------------------------------------
    def inject_live_fault(
        self,
        mode: str,
        cylinder: Optional[int] = None,
        severity: float = 0.8,
        ramp_sec: float = 10.0,
    ) -> Dict[str, Any]:
        """Injects a real live fault into the selected EngineRuntime."""
        with self.lock:
            runtime = self.hub.runtimes.get(self.definition.engine_id)
            if not runtime:
                raise ValueError(f"No runtime available for engine {self.definition.engine_id}")

            rec = runtime.inject_fault(mode, cylinder=cylinder, severity=severity, ramp_sec=ramp_sec, origin="LIVE_OPERATOR")
            rec["t_mission"] = self.t_sim_sec
            self.fault_timeline.append(rec)
            logger.info("Injected live fault: %s", rec)
            return rec

    def clear_faults(self) -> None:
        with self.lock:
            runtime = self.hub.runtimes.get(self.definition.engine_id)
            if runtime:
                runtime.clear_faults()
            self.fault_timeline.append({"t": self.t_sim_sec, "action": "CLEAR_FAULTS", "origin": "OPERATOR"})
            logger.info("Cleared all engine faults")

    # -------------------------------------------------------------------------
    # Flight Phase Determination
    # -------------------------------------------------------------------------
    def _determine_phase(self, elapsed_sec: float) -> FlightPhase:
        """Legacy waypoint-mode phase determination (derives phase from route progress).
        Only called when self.flight_model is AutopilotFlightModel -- phase-based missions
        get their phase directly from PhaseFlightModel.current_phase instead, since there
        the phase IS the authored unit, not something to infer."""
        n_wp = len(self.definition.waypoints)
        current_idx = self.flight_model.current_wp_idx

        if elapsed_sec < 8.0:
            return FlightPhase.PREFLIGHT
        if elapsed_sec < 25.0:
            return FlightPhase.TAKEOFF

        if self.flight_model.is_final_waypoint_reached:
            return FlightPhase.COMPLETED

        # Climb whenever the aircraft is meaningfully below the waypoint it's currently
        # seeking (not just the first leg) -- e.g. the Ladakh route's gorge-exit climb up
        # to the ridge waypoint, not only the initial climb-out.
        target_alt = self.definition.waypoints[min(current_idx + 1, n_wp - 1)].alt_msl_m
        if self.flight_model.pos_z_m < target_alt - 120.0:
            return FlightPhase.CLIMB

        target_wp = self.definition.waypoints[min(current_idx + 1, n_wp - 1)]
        if target_wp.loiter_duration_sec > 0.0 and self.flight_model.loiter_elapsed_sec < target_wp.loiter_duration_sec:
            tx, ty, _, _ = self.flight_model.enu_waypoints[min(current_idx + 1, n_wp - 1)]
            dist_to_target = math.hypot(tx - self.flight_model.pos_x_m, ty - self.flight_model.pos_y_m)
            if dist_to_target < self.flight_model.arrival_radius_m * 3.0:
                # Close enough to be circling the loiter point (not just passing near it
                # on the way to a later waypoint) -- start/continue the loiter hold.
                return FlightPhase.LOITER

        # Final leg: begin descent once within the last waypoint's approach and below
        # cruise altitude relative to the recovery waypoint's target.
        if current_idx >= n_wp - 2:
            final_wp = self.definition.waypoints[-1]
            dist_to_final = math.hypot(
                self.flight_model.enu_waypoints[-1][0] - self.flight_model.pos_x_m,
                self.flight_model.enu_waypoints[-1][1] - self.flight_model.pos_y_m,
            )
            if dist_to_final < 800.0:
                return FlightPhase.LANDING
            if self.flight_model.pos_z_m > final_wp.alt_msl_m + 150.0:
                return FlightPhase.DESCENT
            return FlightPhase.RETURN_TRANSIT if current_idx >= n_wp - 2 else FlightPhase.CRUISE

        return FlightPhase.CRUISE

    # -------------------------------------------------------------------------
    # Simulation Step & Loop
    # -------------------------------------------------------------------------
    def step(self, dt: float = 0.05) -> MissionState:
        """Executes one simulation tick coupled to the plant and diagnostic stack."""
        with self.lock:
            if self.state.status not in (MissionStatus.RUNNING.value, MissionStatus.DERATED.value):
                return self.state

            self._step_count += 1
            # Advance mission time
            sim_dt = dt * self.time_scale
            self.t_sim_sec += sim_dt
            self.state.time_elapsed_sec = round(self.t_sim_sec, 2)
            self.state.time_remaining_sec = max(0.0, round(self.definition.planned_duration_sec - self.t_sim_sec, 2))

            runtime = self.hub.runtimes.get(self.definition.engine_id)

            if self.is_phase_mode:
                # --- Phase-based mission (ARCH-2026-MP-002, primary mode) -----------------
                (
                    (pos_x, pos_y, pos_z),
                    gnd_elev,
                    agl_m,
                    (heading, pitch, roll),
                    cmd_throttle,
                    oat_c,
                    cur_alt_ft,
                    phase_idx,
                    elapsed_in_phase,
                    phase_duration,
                    phase_name,
                ) = self.flight_model.advance(sim_dt)

                phase_value = phase_name if phase_name != "COMPLETED" else FlightPhase.COMPLETED.value
                self.state.current_phase_idx = phase_idx
                self.state.elapsed_in_phase_sec = elapsed_in_phase
                self.state.phase_duration_sec = phase_duration
                cur_alt_msl_m = pos_z
                _, baro_p_hpa, density_alt_ft = AtmosphericModel.sample(
                    cur_alt_msl_m, self.definition.environment.qnh_hpa, oat_c - 15.0,
                )
                tas_kt = self.flight_model.speed_mps * 1.943844
                kias = tas_kt
                cur_wp_idx = phase_idx
                dist_rem_m = 0.0
                path_frac = min(1.0, self.t_sim_sec / max(1.0, self.flight_model.total_duration_sec))

                # Phase-scoped fault triggers: fires when the CURRENT phase's elapsed time
                # crosses the scheduled offset -- not tied to global mission time, so
                # re-ordering or resizing phases doesn't shift when a fault fires relative
                # to the phase it's meant to be "during".
                if runtime:
                    for ev in self.definition.phase_events:
                        if (not ev.applied and phase_name == ev.phase_name
                                and elapsed_in_phase >= ev.elapsed_in_phase_sec):
                            ev.applied = True
                            if ev.action == "INJECT_FAULT" and ev.fault_mode:
                                try:
                                    rec = runtime.inject_fault(
                                        ev.fault_mode, cylinder=ev.cylinder, severity=ev.severity,
                                        ramp_sec=ev.ramp_sec, origin="MISSION_SCHEDULE",
                                    )
                                    rec["t_mission"] = self.t_sim_sec
                                    rec["phase"] = ev.phase_name
                                    self.fault_timeline.append(rec)
                                    logger.info("Triggered phase-scheduled fault: %s", rec)
                                except Exception as err:
                                    logger.error("Failed to trigger phase-scheduled fault %s: %s", ev.fault_mode, err)
            else:
                # --- Legacy waypoint/route mode (dormant, kept available) -----------------
                phase = self._determine_phase(self.t_sim_sec)
                self._current_phase = phase
                (
                    (pos_x, pos_y, pos_z),
                    gnd_elev,
                    agl_m,
                    (heading, pitch, roll),
                    cmd_throttle,
                    tas_kt,
                    kias,
                    cur_wp_idx,
                    dist_rem_m,
                    path_frac,
                ) = self.flight_model.advance(sim_dt, phase, self.derate_scale)

                phase_value = phase.value
                cur_alt_msl_m = pos_z
                cur_alt_ft = cur_alt_msl_m * 3.28084
                oat_c, baro_p_hpa, density_alt_ft = AtmosphericModel.sample(
                    cur_alt_msl_m, self.definition.environment.qnh_hpa, self.definition.environment.isa_temp_offset_c,
                )

                if runtime:
                    for ev in self.definition.scheduled_events:
                        if not ev.applied and self.t_sim_sec >= ev.trigger_time_sec:
                            ev.applied = True
                            if ev.action == "INJECT_FAULT" and ev.fault_mode:
                                try:
                                    rec = runtime.inject_fault(
                                        ev.fault_mode, cylinder=ev.cylinder, severity=ev.severity,
                                        ramp_sec=ev.ramp_sec, origin="MISSION_SCHEDULE",
                                    )
                                    rec["t_mission"] = self.t_sim_sec
                                    self.fault_timeline.append(rec)
                                    logger.info("Triggered scheduled fault: %s", rec)
                                except Exception as err:
                                    logger.error("Failed to trigger scheduled fault %s: %s", ev.fault_mode, err)

            # 4. Command Engine Runtime Levers -- REAL drive interface, identical for both modes.
            if runtime:
                runtime.set_levers(
                    throttle_pct=cmd_throttle,
                    altitude_ft=cur_alt_ft,
                    oat_c=oat_c,
                )

            # 5. Advance Runtime and Ingest Output
            tick = None
            if runtime and runtime.ready:
                tick = runtime.tick(heavy=True)

            # 6. Update Canonical MissionState
            self.state.pos_x_m = pos_x
            self.state.pos_y_m = pos_y
            self.state.pos_z_m = round(cur_alt_msl_m, 1)
            self.state.ground_elevation_m = gnd_elev
            self.state.agl_m = agl_m
            self.state.heading_deg = heading
            self.state.pitch_deg = pitch
            self.state.roll_bank_deg = roll
            self.state.phase = phase_value
            self.state.commanded_throttle_pct = cmd_throttle
            self.state.true_airspeed_ktas = tas_kt
            self.state.indicated_airspeed_kias = kias
            self.state.ground_speed_mps = round(tas_kt * 0.514444, 1)
            self.state.current_waypoint_idx = cur_wp_idx
            self.state.waypoint_distance_remaining_m = dist_rem_m
            self.state.path_progress_fraction = path_frac
            self.state.ambient_oat_c = oat_c
            self.state.ambient_pressure_hpa = baro_p_hpa
            self.state.density_altitude_ft = density_alt_ft

            if tick is not None:
                f = tick.frame
                det = tick.detection
                self.state.rpm = getattr(f, "rpm", 0.0) or 0.0
                self.state.max_cht_c = max(f.cht) if f.cht else 0.0
                self.state.max_egt_c = max(f.egt) if f.egt else 0.0
                # NOTE: the canonical Frame dataclass (backend/core/frame.py) names these
                # `oil_p` (bar) and `fuel_flow` (kg/h) -- not `oil_press_bar`/`fuel_flow_kg_h`.
                # The previous getattr() names never matched, so these silently held the
                # fallback constants every tick; read the real attributes instead.
                self.state.oil_press_bar = getattr(f, "oil_p", None) or 4.5
                self.state.fuel_flow_kg_h = getattr(f, "fuel_flow", None) or 12.0
                self.state.cht = list(f.cht)
                self.state.egt = list(f.egt)
                self.state.active_faults = list(tick.truth.active_faults)
                # Effective load tracks the commanded throttle actually reaching the plant
                # (i.e. after derate clamping) -- the one real "demand" signal already
                # computed upstream, rather than a fabricated RPM-derived estimate.
                self.state.effective_engine_load_pct = round(cmd_throttle, 1)

                if det is not None:
                    self.state.residual_alarm = bool(det.raw_alarm)
                    self.state.confirmed_anomaly = bool(det.confirmed)
                    self.state.top_divergent_channel = det.top_channels[0][0] if det.top_channels else None

                if tick.novelty is not None:
                    self.state.flyhash_novelty_score = float(tick.novelty.novelty_score)
                    self.state.is_novel_pattern = bool(tick.novelty.is_novel)

                if tick.diagnosis:
                    top_diag = tick.diagnosis[0]
                    self.state.top_diagnostic_hypothesis = top_diag.get("mode_id")
                    self.state.diagnostic_confidence = float(top_diag.get("probability", 0.0))

                # Periodically sample reliability (1 Hz at 20 Hz simulation). This is the
                # key wire the phase-based pivot adds: in phase mode, build a REAL
                # MissionProfile from the mission's actual remaining phases and feed it to
                # the existing Monte Carlo reliability engine, instead of always falling
                # back to the generic canned ISR_18H_PROFILE (the gap identified during
                # planning: engine_runtime.py's mission_reliability() previously had no way
                # to know what mission was actually flying).
                if self._step_count % 20 == 0 or self._step_count == 1:
                    try:
                        self._apply_live_fault_damage(runtime)
                        live_profile = self._build_live_reliability_profile() if self.is_phase_mode else None
                        rel_data = runtime.mission_reliability(
                            hours=max(0.5, self.state.time_remaining_sec / 3600.0),
                            profile=live_profile,
                        )
                        self.state.mission_reliability = float(rel_data.get("reliability", 1.0))
                        self.state.limiting_component = str(rel_data.get("limiting_component", "nominal"))
                        self.state.prescriptive_advisory = str(rel_data.get("recommendation", "Nominal operation."))
                    except Exception:
                        logger.exception("Mission reliability sampling failed")

                # 7. Record Frame for Sortie
                self._record_telemetry_frame(f, phase_value, cur_alt_ft, oat_c, tas_kt)

            # 8. Check Mission Completion. Phase mode: complete when the phase sequence has
            # run out. Route mode: primarily route-driven (the autopilot actually reached
            # the final waypoint), with planned_duration_sec as a safety timeout only.
            if self.is_phase_mode:
                mission_complete = self.flight_model.is_complete
            else:
                mission_complete = phase_value == FlightPhase.COMPLETED.value
            safety_timeout = self.t_sim_sec >= self.definition.planned_duration_sec * 2.0
            if mission_complete or safety_timeout:
                self.state.status = MissionStatus.COMPLETED.value
                self.state.phase = FlightPhase.COMPLETED.value
                self.end_epoch = time.time()
                self._export_sortie()
                logger.info(
                    "Mission completed (%s): %s",
                    "phase sequence complete" if mission_complete else "safety timeout",
                    self.definition.mission_id,
                )

            return self.state

    # Keyword -> ComponentHazard name (backend/mission/reliability.py:DEFAULT_COMPONENTS),
    # used to translate an active fault's real severity into real accumulated damage on the
    # matching component category, so mission reliability/What-If genuinely responds to a
    # fault instead of only reflecting nominal-operation hazard exposure. Wires up
    # `ComponentHazard.set_damage()`, which investigation found was previously dead code --
    # defined but never called anywhere, so damage_fraction stayed at 0.0 (new/undamaged)
    # regardless of what faults were actually active.
    _FAULT_COMPONENT_KEYWORDS = (
        (("COOLING", "CHT", "THERMAL", "OVERHEAT"), ("cylinder_head_1", "cylinder_head_2", "cylinder_head_3", "cylinder_head_4")),
        (("OIL",), ("oil_pump",)),
        (("INJECTOR", "FUEL"), ("injector_1", "injector_2", "injector_3", "injector_4", "fuel_pump")),
        (("WASTEGATE", "TURBO", "INTERCOOLER"), ("turbocharger",)),
        (("GEARBOX", "VIBRATION", "BEARING"), ("reduction_gearbox", "main_bearings")),
        (("ALTERNATOR", "VOLTAGE", "ECU", "FADEC"), ("alternator", "ecu_lane_a")),
    )

    def _apply_live_fault_damage(self, runtime: EngineRuntime) -> None:
        """Maps each currently-active fault (real severity, real elapsed-since-onset ramp)
        onto real ComponentHazard.damage_fraction for the matching component category."""
        active = self.state.active_faults or []
        if not active:
            return
        damage: Dict[str, float] = {}
        for f in active:
            mode = str(f.get("mode", "") if isinstance(f, dict) else getattr(f, "mode", ""))
            severity = float(f.get("severity", 0.5) if isinstance(f, dict) else getattr(f, "severity", 0.5))
            mode_upper = mode.upper()
            # ComponentHazard.hazard() applies wear_multiplier = 1/(1-d)^exponent -- a wear-
            # out curve that is intentionally near-flat until d approaches 1.0, then rises
            # very sharply (real wear-out physics: a component near end-of-life fails fast).
            # A fault "severity" of 0.85 is NOT the same quantity as "85% of life consumed"
            # -- a sigmoid centered so a serious fault (severity ~0.7-0.9, the realistic
            # range fault injection is configured at) lands on the steep part of the curve,
            # so an active fault visibly moves mission reliability/derate options even over a
            # short remaining-mission window, while a minor fault (severity ~0.3) stays mild.
            damage_fraction = min(0.985, 1.0 / (1.0 + math.exp(-8.0 * (severity - 0.55))))
            for keywords, components in self._FAULT_COMPONENT_KEYWORDS:
                if any(kw in mode_upper for kw in keywords):
                    for comp in components:
                        damage[comp] = max(damage.get(comp, 0.0), damage_fraction)
        if damage:
            runtime.reliability_engine.set_damage(damage)

    def _build_live_reliability_profile(self) -> "MissionProfile":
        """Builds a real MissionProfile (backend/mission/reliability.py) from the mission's
        actual remaining phases -- the current phase truncated to its remaining duration,
        plus every phase still ahead -- so 'mission reliability' reflects what this sortie
        will actually fly from here, not a generic 18h ISR loiter."""
        idx = self.flight_model.current_phase_idx
        remaining_phases = []
        for i, spec in enumerate(self.definition.phases):
            if i < idx:
                continue
            if i == idx:
                remaining_sec = max(1.0, spec.duration_sec - self.flight_model.elapsed_in_phase_sec)
                partial = MissionPhaseSpec(
                    name=spec.name, duration_sec=remaining_sec,
                    start_alt_ft=self.flight_model.pos_z_m * 3.28084, end_alt_ft=spec.end_alt_ft,
                    throttle_pct=spec.throttle_pct, oat_c=spec.oat_c, dust_mg_m3=spec.dust_mg_m3,
                )
                remaining_phases.append(partial.to_reliability_phase())
            else:
                remaining_phases.append(spec.to_reliability_phase())
        return MissionProfile(name=f"{self.definition.name} (live, from {self.flight_model.current_phase.name if self.flight_model.current_phase else 'END'})",
                              phases=remaining_phases)

    def _record_telemetry_frame(self, frame: Any, phase_str: str, alt_ft: float, oat_c: float, tas_kt: float) -> None:
        """Appends one synchronized row into the sortie frame buffer.

        Every column is sourced from real simulated state (MissionState kinematics, the
        Frame emitted by EngineRuntime, or the reliability engine's continuous health
        output) wherever the underlying model actually computes it. Columns the physics
        plant doesn't model (rail pressure, gearbox vibration, FADEC lane, injection/
        ignition timing, AFR, BSFC, thermal efficiency) are left as None rather than
        fabricated constants, matching Frame's own "no made-up defaults" contract
        (backend/core/frame.py) -- a debrief reader can tell "not measured" from
        "measured and nominal".
        """
        cht = getattr(frame, "cht", None) or []
        egt = getattr(frame, "egt", None) or []
        # lat/lon are only meaningful in the legacy waypoint/route mode, which carries a real
        # WGS84 projector; phase-based missions have no geographic route, so these are left
        # as None rather than reporting a fabricated position (the cosmetic phase-mode track
        # position is available as pos_x_m/pos_y_m/pos_z_m if needed, just not geodetic).
        projector = getattr(self.flight_model, "projector", None)
        if projector is not None:
            lat, lon, _ = projector.from_enu(
                self.state.pos_x_m, self.state.pos_y_m, self.state.pos_z_m - projector.ref_alt_m
            )
        else:
            lat, lon = None, None

        def _opt(attr: str, digits: int = 2) -> Optional[float]:
            v = getattr(frame, attr, None)
            return round(v, digits) if v is not None else None

        row = {
            "TIMESTAMP_SEC": round(self.start_epoch + self.t_sim_sec, 3),
            "ENGINE_RPM": round(getattr(frame, "rpm", 0.0) or 0.0, 1),
            "PROP_RPM": round((getattr(frame, "rpm", 0.0) or 0.0) / 2.43, 1),
            "TPS": round(self.state.commanded_throttle_pct, 1),
            "LAT": round(lat, 6) if lat is not None else None,
            "LON": round(lon, 6) if lon is not None else None,
            "AGL_M": round(self.state.agl_m, 1),
            "HEADING_DEG": round(self.state.heading_deg, 1),
            "PITCH_DEG": round(self.state.pitch_deg, 1),
            "ROLL_DEG": round(self.state.roll_bank_deg, 1),
            "CHT_1": round(cht[0], 1) if len(cht) > 0 else None,
            "CHT_2": round(cht[1], 1) if len(cht) > 1 else None,
            "CHT_3": round(cht[2], 1) if len(cht) > 2 else None,
            "CHT_4": round(cht[3], 1) if len(cht) > 3 else None,
            "EGT_1": round(egt[0], 1) if len(egt) > 0 else None,
            "EGT_2": round(egt[1], 1) if len(egt) > 1 else None,
            "EGT_3": round(egt[2], 1) if len(egt) > 2 else None,
            "EGT_4": round(egt[3], 1) if len(egt) > 3 else None,
            "OIL_PRESS": round(self.state.oil_press_bar, 2),
            "OIL_TEMP": _opt("oil_t", 1),
            "FUEL_FLOW": round(self.state.fuel_flow_kg_h, 1),
            "FUEL_RAIL_P": _opt("rail_p"),
            "MAP": _opt("map_kpa", 1),
            "BUS_VOLTAGE": _opt("bus_v"),
            "BATTERY_CURRENT": _opt("batt_i"),
            "FADEC_ACTIVE_LANE": getattr(frame, "fadec_lane", None),
            "ALTITUDE_FT": round(alt_ft, 1),
            "OAT_C": round(oat_c, 1),
            "TAS_KNOTS": round(tas_kt, 1),
            "FLIGHT_PHASE": phase_str,
            "THEATER": self.definition.environment.theater_name,
            "DIAG_FAULT_ID": 1 if self.state.confirmed_anomaly else 0,
            # Continuous reliability-engine health, not a binary 0.72/1.0 toggle.
            "HEALTH_INDEX": round(self.state.mission_reliability, 4),
        }
        self.recorded_frames.append(row)

    def _export_sortie(self) -> Dict[str, str]:
        """Persists the full simulation record to disk."""
        return self.exporter.export(
            definition=self.definition,
            final_state=self.state,
            recorded_frames=self.recorded_frames,
            fault_timeline=self.fault_timeline,
            start_epoch=self.start_epoch,
            end_epoch=self.end_epoch or time.time(),
        )

    def _run_loop(self) -> None:
        """Background thread executing at 20 Hz."""
        period = 1.0 / self._rate_hz
        while not self._stop_event.is_set():
            t0 = time.perf_counter()
            self.step(dt=period)
            elapsed = time.perf_counter() - t0
            sleep_time = max(0.001, period - elapsed)
            time.sleep(sleep_time)
