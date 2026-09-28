"""Phase-Based Mission Flight Model (ARCH-2026-MP-002).

Replaces AutopilotFlightModel (backend/mission/kinematics.py, waypoint/terrain-following
mode) as the live-flight driver for phase-based missions. A phase-based mission is not a
route: it exists to define engine *operating conditions* over time (altitude, throttle, OAT
per named phase), which drive the real propulsion Digital Twin. This module is
correspondingly simple -- no heading-to-waypoint seeking, no terrain-avoidance, no bank/turn
dynamics driven by navigation.

Position/attitude are still computed every tick (so the Blender/web visualizer keeps showing
continuous travel over the real canyon terrain, per the explicit requirement to see the
aircraft actually fly), but they are now COSMETIC outputs derived from the phase's altitude
ramp and throttle-implied airspeed along a fixed track -- not the mission's substance. The
mission's substance is `MissionPhaseSpec.to_reliability_phase()` feeding the real
MissionReliabilityEngine (backend/mission/reliability.py), and phase-scoped fault injection
feeding the real EngineRuntime -- both wired in backend/mission/executive.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .models import MissionPhaseSpec
from .terrain import get_terrain_heightfield

# Fixed visual track: the aircraft flies a straight line up the Nubra gorge (matching the
# real canyon terrain's own axis, see backend/mission/kinematics.py's THEATER_ENU_ANCHORS /
# terrain.py docstring for the coordinate frame this is anchored to) at a constant heading,
# looping back if a mission runs long enough to reach the far end. This is purely so there is
# something coherent on screen; the phase profile does not "go" anywhere geographically.
#
# Authentic Nubra valley canyon gorge ingress coordinates (matching apps/blender_twin/standalone_canyon_flight_app.py):
# INGRESS_X = 4000.0 (East), INGRESS_Y = 7500.0 (North), Ground Elevation = ~3095m AMSL.
# Heading 38.0° (azimuth) traces directly up the canyon riverbed axis where floor stays ~3095m-3300m,
# flanked by 5000m+ Himalayan mountain ridges on both sides.
TRACK_START_ENU = (4000.0, 7500.0)      # Nubra canyon river confluence ingress, ~3095m floor
TRACK_HEADING_RAD = math.radians(38.0)  # heading 38° northeast up Nubra canyon gorge axis
TRACK_LENGTH_M = 15000.0                # loop distance staying within low-terrain canyon run

MAX_PITCH_RAD = math.radians(12.0)     # cosmetic pitch during altitude ramps
PITCH_RATE_RADS = math.radians(6.0)
MIN_AGL_FLOOR_M = 5.0


@dataclass
class PhaseFlightModel:
    """Stateful phase-driven flight model. `advance()` is called once per simulation tick
    with real elapsed dt; tracks which phase is active and how far into it, interpolates
    altitude across that phase's start/end altitude, and derives a cosmetic track position
    from throttle-implied airspeed."""

    phases: List[MissionPhaseSpec]

    current_phase_idx: int = 0
    elapsed_in_phase_sec: float = 0.0
    track_distance_m: float = 0.0
    pos_z_m: float = 0.0
    pitch_rad: float = 0.0
    heading_rad: float = TRACK_HEADING_RAD
    roll_rad: float = 0.0
    speed_mps: float = 0.0
    _initialized: bool = False

    def __post_init__(self) -> None:
        self.terrain = get_terrain_heightfield()

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        if self.phases:
            self.pos_z_m = self.phases[0].start_alt_ft * 0.3048
        self._initialized = True

    @property
    def total_duration_sec(self) -> float:
        return sum(p.duration_sec for p in self.phases)

    @property
    def current_phase(self) -> Optional[MissionPhaseSpec]:
        if 0 <= self.current_phase_idx < len(self.phases):
            return self.phases[self.current_phase_idx]
        return None

    @property
    def is_complete(self) -> bool:
        return self.current_phase_idx >= len(self.phases)

    def advance(self, dt: float) -> Tuple[
        Tuple[float, float, float],   # pos (x, y, z_amsl) -- cosmetic
        float,                        # ground_elev_m
        float,                        # agl_m
        Tuple[float, float, float],   # attitude (heading_deg, pitch_deg, roll_deg) -- cosmetic
        float,                        # commanded_throttle_pct -- REAL, drives EngineRuntime
        float,                        # oat_c -- REAL, drives EngineRuntime
        float,                        # altitude_ft -- REAL, drives EngineRuntime
        int,                          # current_phase_idx
        float,                        # elapsed_in_phase_sec
        float,                        # phase_duration_sec
        str,                          # phase name (or "COMPLETED")
    ]:
        self._ensure_initialized()

        if self.is_complete or not self.phases:
            gnd = self.terrain.elevation_at(*self._track_xy())
            agl = max(MIN_AGL_FLOOR_M, self.pos_z_m - gnd)
            return (
                (*self._track_xy(), self.pos_z_m), gnd, agl,
                (math.degrees(self.heading_rad), 0.0, 0.0),
                0.0, 15.0, self.pos_z_m * 3.28084,
                len(self.phases), 0.0, 0.0, "COMPLETED",
            )

        phase = self.phases[self.current_phase_idx]
        self.elapsed_in_phase_sec += dt

        if self.elapsed_in_phase_sec >= phase.duration_sec:
            overflow = self.elapsed_in_phase_sec - phase.duration_sec
            self.current_phase_idx += 1
            self.elapsed_in_phase_sec = overflow
            if self.is_complete:
                return self.advance(0.0)
            phase = self.phases[self.current_phase_idx]

        frac = min(1.0, self.elapsed_in_phase_sec / max(0.01, phase.duration_sec))
        target_alt_m = (phase.start_alt_ft + frac * (phase.end_alt_ft - phase.start_alt_ft)) * 0.3048

        # Cosmetic vertical rate + pitch, purely for a smooth visual climb/descent (never
        # snaps) -- NOT what drives the real engine altitude lever (that's phase.start/end
        # altitude directly, see executive.py's set_levers call).
        alt_error = target_alt_m - self.pos_z_m
        climb_mps = max(-15.0, min(15.0, alt_error * 0.3))
        self.pos_z_m += climb_mps * dt
        target_pitch = max(-MAX_PITCH_RAD, min(MAX_PITCH_RAD, math.asin(
            max(-1.0, min(1.0, climb_mps / max(1.0, self.speed_mps or 20.0)))
        )))
        self.pitch_rad += max(-PITCH_RATE_RADS * dt, min(PITCH_RATE_RADS * dt, target_pitch - self.pitch_rad))
        self.roll_rad *= max(0.0, 1.0 - 1.5 * dt)  # wings-level decay (no turns in this mode)

        # Throttle-implied airspeed purely for cosmetic track progress (not a real airspeed
        # model -- the real propulsion physics/airspeed effects live in EngineRuntime).
        target_speed_mps = 20.0 + (phase.throttle_pct / 100.0) * 50.0
        self.speed_mps += max(-3.0, min(3.0, target_speed_mps - self.speed_mps)) * min(1.0, 2.0 * dt)
        self.track_distance_m = (self.track_distance_m + self.speed_mps * dt) % (2 * TRACK_LENGTH_M)

        x, y = self._track_xy()
        gnd_elev = self.terrain.elevation_at(x, y)
        agl_m = self.pos_z_m - gnd_elev
        if agl_m < MIN_AGL_FLOOR_M:
            self.pos_z_m = gnd_elev + MIN_AGL_FLOOR_M
            agl_m = MIN_AGL_FLOOR_M

        return (
            (round(x, 1), round(y, 1), round(self.pos_z_m, 1)),
            round(gnd_elev, 1),
            round(agl_m, 1),
            (round(math.degrees(self.heading_rad), 1), round(math.degrees(self.pitch_rad), 1), round(math.degrees(self.roll_rad), 1)),
            round(phase.throttle_pct, 1),
            round(phase.oat_c, 1),
            round(target_alt_m * 3.28084, 1),
            self.current_phase_idx,
            round(self.elapsed_in_phase_sec, 1),
            round(phase.duration_sec, 1),
            phase.name,
        )

    def _track_xy(self) -> Tuple[float, float]:
        """Ping-pongs along the fixed track so a long mission doesn't fly off the loaded
        terrain's edge -- purely cosmetic, see module docstring."""
        d = self.track_distance_m
        if d > TRACK_LENGTH_M:
            d = 2 * TRACK_LENGTH_M - d  # reverse direction on the back leg
        x = TRACK_START_ENU[0] + math.sin(self.heading_rad) * d
        y = TRACK_START_ENU[1] + math.cos(self.heading_rad) * d
        return x, y
