"""Canonical Mission Definition and State Models (F56, R10, ARCH-2026-MP-001).

Defines the single authoritative mission schema for planning, time-stepped simulation,
telemetry coupling, and sortie export across all five supported engine profiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class MissionStatus(str, Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    DERATED = "DERATED"


class FlightPhase(str, Enum):
    PREFLIGHT = "PREFLIGHT"
    TAKEOFF = "TAKEOFF"
    CLIMB = "CLIMB"
    TRANSIT = "TRANSIT"
    CRUISE = "CRUISE"
    LOITER = "LOITER"
    RETURN_TRANSIT = "RETURN_TRANSIT"
    DESCENT = "DESCENT"
    LANDING = "LANDING"
    COMPLETED = "COMPLETED"


@dataclass
class Waypoint:
    """Geographic waypoint -- DEPRECATED as the mission's primary authoring unit as of the
    phase-based mission pivot (ARCH-2026-MP-002). Kept for backward compatibility with the
    dormant AutopilotFlightModel route-following mode; new missions are authored as
    `MissionDefinition.phases` (MissionPhaseSpec) instead. Not removed so waypoint/route mode
    can be re-enabled later without resurrecting this type."""
    id: str
    name: str
    lat: float                     # Decimal degrees (e.g. 34.2500)
    lon: float                     # Decimal degrees (e.g. 77.5800)
    alt_msl_m: float               # Target altitude above sea level in meters
    airspeed_ktas: float           # Commanded true airspeed in knots
    loiter_radius_m: float = 0.0   # > 0 indicates loiter waypoint
    loiter_duration_sec: float = 0.0
    terrain_alt_m: float = 0.0     # Ground elevation below waypoint

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MissionPhaseSpec:
    """One authored segment of a phase-based mission plan (ARCH-2026-MP-002): the primary
    mission-planning unit, replacing geographic waypoints. Defines the operating conditions
    -- not a location -- the propulsion Digital Twin should be evaluated under for this
    segment. Converts directly to `backend.mission.reliability.MissionPhase` (that module's
    Monte Carlo mission-reliability engine already consumes exactly this shape) via
    `to_reliability_phase()`.
    """
    name: str                      # "TAKEOFF", "CLIMB", "CRUISE", "LOITER", "DESCENT", "LANDING"
    duration_sec: float
    start_alt_ft: float            # altitude at the start of this phase (chains from the
                                    # previous phase's end_alt_ft so altitude is continuous)
    end_alt_ft: float
    throttle_pct: float            # commanded throttle for this phase (0-100)
    oat_c: float                   # ambient temperature for this phase
    dust_mg_m3: float = 0.15

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_reliability_phase(self):
        """Builds a `backend.mission.reliability.MissionPhase` for feeding the existing
        Monte Carlo mission-reliability engine -- power_fraction is throttle_pct/100,
        altitude_ft is this phase's mean altitude (reliability's stress model wants one
        representative altitude per phase, not a ramp)."""
        from .reliability import MissionPhase as ReliabilityMissionPhase
        return ReliabilityMissionPhase(
            name=self.name,
            duration_hours=self.duration_sec / 3600.0,
            altitude_ft=(self.start_alt_ft + self.end_alt_ft) / 2.0,
            power_fraction=max(0.0, min(1.5, self.throttle_pct / 100.0)),
            oat_c=self.oat_c,
            dust_mg_m3=self.dust_mg_m3,
        )


@dataclass
class ScheduledEvent:
    """DEPRECATED trigger form: fires at `trigger_time_sec` since mission start. Kept for
    waypoint-mode backward compatibility. New phase-based missions use
    `PhaseScheduledEvent` (fires at an elapsed time within a named phase) instead."""
    trigger_time_sec: float
    action: str                    # "INJECT_FAULT", "WEATHER_CHANGE", "THROTTLE_BURST"
    fault_mode: Optional[str] = None
    cylinder: Optional[int] = None
    severity: float = 0.8
    ramp_sec: float = 10.0
    target_value: Optional[float] = None
    applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PhaseScheduledEvent:
    """A fault (or other event) scheduled to fire at a given elapsed time WITHIN a named
    mission phase -- e.g. "inject INJECTOR_CLOGGED 15 minutes into CRUISE" -- rather than at
    a fixed offset from mission start. This is what the phase-based mission planner's
    "Mission Event: Time 01:12:30, Inject Fault" UI authors."""
    phase_name: str                # must match a MissionPhaseSpec.name in the same mission
    elapsed_in_phase_sec: float
    action: str = "INJECT_FAULT"
    fault_mode: Optional[str] = None
    cylinder: Optional[int] = None
    severity: float = 0.8
    ramp_sec: float = 10.0
    applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EnvironmentalConditions:
    theater_name: str              # "LADAKH_HIGH_COLD", "THAR_HOT_HIGH", "COASTAL_MARITIME", "RAPID_TRANSIENTS"
    qnh_hpa: float = 1013.25       # Sea level pressure (hPa)
    isa_temp_offset_c: float = 0.0 # Deviation from standard ISA temperature
    base_elevation_m: float = 0.0  # Airfield ground elevation
    ambient_wind_kt: float = 0.0
    wind_direction_deg: float = 0.0
    dust_density_mg_m3: float = 0.15

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MissionDefinition:
    mission_id: str
    name: str
    engine_id: str                 # "rotax_912is", "rotax_914", "rotax_915is", "austro_ae300", "vrde_jayem_2_2l"
    airframe_id: str               # "TAPAS-BH-201"
    planned_duration_sec: float
    environment: EnvironmentalConditions
    # Primary mission-planning unit (ARCH-2026-MP-002): a phase-based operating profile.
    phases: List[MissionPhaseSpec] = field(default_factory=list)
    phase_events: List[PhaseScheduledEvent] = field(default_factory=list)
    # DEPRECATED geographic route fields -- see Waypoint/ScheduledEvent docstrings. Kept so
    # the dormant AutopilotFlightModel waypoint-following mode still has a valid input shape.
    waypoints: List[Waypoint] = field(default_factory=list)
    scheduled_events: List[ScheduledEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "name": self.name,
            "engine_id": self.engine_id,
            "airframe_id": self.airframe_id,
            "planned_duration_sec": self.planned_duration_sec,
            "environment": self.environment.to_dict(),
            "phases": [ph.to_dict() for ph in self.phases],
            "phase_events": [ev.to_dict() for ev in self.phase_events],
            "waypoints": [wp.to_dict() for wp in self.waypoints],
            "scheduled_events": [ev.to_dict() for ev in self.scheduled_events],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MissionDefinition":
        env_data = data.get("environment", {})
        env = EnvironmentalConditions(
            theater_name=env_data.get("theater_name", "LADAKH_HIGH_COLD"),
            qnh_hpa=float(env_data.get("qnh_hpa", 1013.25)),
            isa_temp_offset_c=float(env_data.get("isa_temp_offset_c", 0.0)),
            base_elevation_m=float(env_data.get("base_elevation_m", 3097.64)),
            ambient_wind_kt=float(env_data.get("ambient_wind_kt", 0.0)),
            wind_direction_deg=float(env_data.get("wind_direction_deg", 0.0)),
            dust_density_mg_m3=float(env_data.get("dust_density_mg_m3", 0.15)),
        )
        phases = [
            MissionPhaseSpec(
                name=str(p.get("name", f"PHASE_{i}")),
                duration_sec=float(p["duration_sec"]),
                start_alt_ft=float(p["start_alt_ft"]),
                end_alt_ft=float(p["end_alt_ft"]),
                throttle_pct=float(p.get("throttle_pct", 65.0)),
                oat_c=float(p.get("oat_c", 15.0)),
                dust_mg_m3=float(p.get("dust_mg_m3", 0.15)),
            )
            for i, p in enumerate(data.get("phases", []))
        ]
        phase_events = [
            PhaseScheduledEvent(
                phase_name=str(e["phase_name"]),
                elapsed_in_phase_sec=float(e["elapsed_in_phase_sec"]),
                action=str(e.get("action", "INJECT_FAULT")),
                fault_mode=e.get("fault_mode"),
                cylinder=e.get("cylinder"),
                severity=float(e.get("severity", 0.8)),
                ramp_sec=float(e.get("ramp_sec", 10.0)),
            )
            for e in data.get("phase_events", [])
        ]
        waypoints = [
            Waypoint(
                id=str(w.get("id", f"WP_{i}")),
                name=str(w.get("name", f"Waypoint {i}")),
                lat=float(w["lat"]),
                lon=float(w["lon"]),
                alt_msl_m=float(w["alt_msl_m"]),
                airspeed_ktas=float(w.get("airspeed_ktas", 120.0)),
                loiter_radius_m=float(w.get("loiter_radius_m", 0.0)),
                loiter_duration_sec=float(w.get("loiter_duration_sec", 0.0)),
                terrain_alt_m=float(w.get("terrain_alt_m", 0.0)),
            )
            for i, w in enumerate(data.get("waypoints", []))
        ]
        events = [
            ScheduledEvent(
                trigger_time_sec=float(e["trigger_time_sec"]),
                action=str(e["action"]),
                fault_mode=e.get("fault_mode"),
                cylinder=e.get("cylinder"),
                severity=float(e.get("severity", 0.8)),
                ramp_sec=float(e.get("ramp_sec", 10.0)),
                target_value=float(e["target_value"]) if e.get("target_value") is not None else None,
            )
            for e in data.get("scheduled_events", [])
        ]
        return cls(
            mission_id=str(data.get("mission_id", "MSN-DEFAULT")),
            name=str(data.get("name", "Standard Mission")),
            engine_id=str(data.get("engine_id", "rotax_912is")),
            airframe_id=str(data.get("airframe_id", "TAPAS-BH-201")),
            planned_duration_sec=float(data.get("planned_duration_sec", 7200.0)),
            environment=env,
            phases=phases,
            phase_events=phase_events,
            waypoints=waypoints,
            scheduled_events=events,
        )


@dataclass
class MissionState:
    mission_id: str
    status: str                    # DRAFT, READY, RUNNING, PAUSED, COMPLETED, ABORTED, DERATED
    phase: str                     # PREFLIGHT, TAKEOFF, CLIMB, TRANSIT, CRUISE, LOITER, RETURN_TRANSIT, DESCENT, LANDING, COMPLETED
    time_elapsed_sec: float
    time_remaining_sec: float
    time_scale: float = 1.0

    # Kinematics & Coordinates
    pos_x_m: float = 0.0           # Local Easting relative to theater datum
    pos_y_m: float = 0.0           # Local Northing relative to theater datum
    pos_z_m: float = 0.0           # Altitude AMSL in meters
    ground_elevation_m: float = 0.0
    agl_m: float = 0.0             # Above Ground Level (pos_z_m - ground_elevation_m)
    ground_speed_mps: float = 0.0
    true_airspeed_ktas: float = 0.0
    indicated_airspeed_kias: float = 0.0
    heading_deg: float = 0.0
    pitch_deg: float = 0.0
    roll_bank_deg: float = 0.0
    current_waypoint_idx: int = 0
    waypoint_distance_remaining_m: float = 0.0
    path_progress_fraction: float = 0.0

    # Phase-based mission progress (ARCH-2026-MP-002)
    current_phase_idx: int = 0
    elapsed_in_phase_sec: float = 0.0
    phase_duration_sec: float = 0.0

    # Atmospheric State at Altitude
    ambient_oat_c: float = 15.0
    ambient_pressure_hpa: float = 1013.25
    density_altitude_ft: float = 0.0

    # Commanded Propulsion Demand
    commanded_throttle_pct: float = 0.0
    effective_engine_load_pct: float = 0.0

    # Real-time Plant State
    engine_id: str = "rotax_912is"
    rpm: float = 0.0
    max_cht_c: float = 0.0
    max_egt_c: float = 0.0
    oil_press_bar: float = 0.0
    fuel_flow_kg_h: float = 0.0
    cht: List[float] = field(default_factory=list)
    egt: List[float] = field(default_factory=list)

    # PHM & Anomaly State
    active_faults: List[Dict[str, Any]] = field(default_factory=list)
    residual_alarm: bool = False
    confirmed_anomaly: bool = False
    top_divergent_channel: Optional[str] = None
    flyhash_novelty_score: float = 0.0
    is_novel_pattern: bool = False
    top_diagnostic_hypothesis: Optional[str] = None
    diagnostic_confidence: float = 0.0
    limiting_component: str = "nominal"
    mission_reliability: float = 1.0
    prescriptive_advisory: str = "Nominal operation meets reliability target."

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
