"""Flight Kinematics, Atmospheric ISA Modeling, and Stateful Waypoint Autopilot (ARCH-2026-MP-001).

Converts geodetic waypoints to Local Tangent Plane coordinates, models standard atmosphere
and density altitude, and integrates real UAV position/orientation via a persistent
autopilot state machine each simulation tick.

The autopilot integrator (``AutopilotFlightModel``) intentionally mirrors the reusable
patterns already proven in the standalone Blender canyon flight sim
(``apps/blender_twin/standalone_canyon_flight_app.py``): a first-order "FADEC" speed
governor converging toward a phase-commanded target airspeed, rate-limited heading/pitch/roll
integrators (not instantaneous geometric snapping), and coordinated-turn bank derived from
heading error -- all advanced by real elapsed ``dt`` each tick and carried forward as
persistent state, so position is genuinely integrated from velocity rather than interpolated
as a function of total mission-time fraction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .models import Waypoint, FlightPhase, EnvironmentalConditions
from .terrain import get_terrain_heightfield

EARTH_RADIUS_M = 6371000.0
GRAVITY_MPS2 = 9.80665

# Autopilot tuning constants (ported in spirit from the Blender sim's proven values).
MAX_BANK_RAD = math.radians(30.0)          # coordinated-turn bank ceiling
TURN_RATE_RADS = math.radians(12.0)        # cruise turn rate (rad/s) -- gentler than the
                                            # Blender sim's 26 deg/s "military" turns since
                                            # this is a patrol/recon UAV, not a fighter jet
BANK_PER_HEADING_ERROR = 2.2               # roll_rad = clamp(heading_error * K, +-MAX_BANK)
ROLL_LEVEL_RATE = 1.4                      # rad/s roll returns toward the commanded bank
MAX_PITCH_RAD = math.radians(18.0)
PITCH_RATE_RADS = math.radians(10.0)       # rad/s pitch integrator rate limit
CLIMB_RATE_MAX_MPS = 6.0                   # vertical speed ceiling used to derive pitch
SPEED_GOVERNOR_GAIN = 1.8                  # 1/s, first-order P-controller toward target TAS
MAX_ACCEL_MPS2 = 3.5
MIN_SPEED_MPS = 18.0                       # stall-margin floor so the integrator never stalls
WAYPOINT_ARRIVAL_RADIUS_M = 400.0
MIN_AGL_FLOOR_M = 5.0


class AtmosphericModel:
    """Standard ISA atmosphere with temperature and pressure lapse rate."""

    @staticmethod
    def sample(alt_m: float, qnh_hpa: float = 1013.25, isa_temp_offset_c: float = 0.0) -> Tuple[float, float, float]:
        """Compute (OAT in degC, ambient pressure in hPa, density altitude in ft)."""
        alt_clamped = max(0.0, min(alt_m, 20000.0))
        # ISA standard temperature at altitude
        t_isa_k = 288.15 - 0.0065 * alt_clamped
        t_actual_k = t_isa_k + isa_temp_offset_c
        t_actual_c = t_actual_k - 273.15

        # Barometric pressure (troposphere barometric formula)
        p_ratio = max(0.01, (1.0 - (0.0065 * alt_clamped) / 288.15)) ** 5.25588
        p_ambient_hpa = qnh_hpa * p_ratio

        # Density altitude (ft)
        press_alt_ft = (1.0 - (p_ambient_hpa / 1013.25) ** 0.190284) * 145366.45
        t_isa_c = t_isa_k - 273.15
        density_alt_ft = press_alt_ft + 120.0 * (t_actual_c - t_isa_c)

        return round(t_actual_c, 2), round(p_ambient_hpa, 2), round(density_alt_ft, 1)


# Fixed geodetic anchor for theaters whose ENU frame must line up with a real terrain
# mesh's own local coordinates (so physics AGL and the rendered terrain always agree).
# For LADAKH_HIGH_COLD this anchor is the point the Ladakh canyon terrain GLB's local
# (X=0, Z=0) actually represents in the real world -- NOT waypoints[0]'s own lat/lon
# (waypoints are authored to already sit at their correct terrain-local ENU offset from
# this anchor; see backend/mission/executive.py:create_ladakh_preset and
# backend/mission/terrain.py for the mesh-parsing side of this alignment).
THEATER_ENU_ANCHORS = {
    "LADAKH_HIGH_COLD": (34.60, 77.55),
}


class GeodeticProjector:
    """Projects WGS84 (lat, lon) to Local Tangent Plane (ENU meters) relative to theater datum."""

    def __init__(self, ref_lat: float = 34.2500, ref_lon: float = 77.5800, ref_alt_m: float = 3097.64) -> None:
        self.ref_lat = ref_lat
        self.ref_lon = ref_lon
        self.ref_alt_m = ref_alt_m
        self.cos_ref_lat = math.cos(math.radians(ref_lat))

    def to_enu(self, lat: float, lon: float, alt_m: float) -> Tuple[float, float, float]:
        """Returns (x_east_m, y_north_m, z_up_m) relative to theater datum."""
        d_lat_rad = math.radians(lat - self.ref_lat)
        d_lon_rad = math.radians(lon - self.ref_lon)
        x_m = d_lon_rad * EARTH_RADIUS_M * self.cos_ref_lat
        y_m = d_lat_rad * EARTH_RADIUS_M
        z_m = alt_m - self.ref_alt_m
        return x_m, y_m, z_m

    def from_enu(self, x_m: float, y_m: float, z_m: float) -> Tuple[float, float, float]:
        """Returns (lat, lon, alt_m) from ENU meters."""
        lat = self.ref_lat + math.degrees(y_m / EARTH_RADIUS_M)
        lon = self.ref_lon + math.degrees(x_m / (EARTH_RADIUS_M * self.cos_ref_lat))
        alt_m = z_m + self.ref_alt_m
        return lat, lon, alt_m


def _wrap_pi(angle_rad: float) -> float:
    """Wraps an angle to (-pi, pi]."""
    return (angle_rad + math.pi) % (2.0 * math.pi) - math.pi


def _phase_target_speed_ktas(phase: "FlightPhase", cruise_ktas: float, derate_scale: float) -> float:
    """Maps flight phase -> commanded true airspeed, derated demand reducing the ceiling
    (so DERATE genuinely caps achievable performance, not just a cosmetic throttle number)."""
    if phase == FlightPhase.PREFLIGHT:
        return 0.0
    if phase == FlightPhase.TAKEOFF:
        return max(MIN_SPEED_MPS * 1.944, cruise_ktas * 0.55) * derate_scale
    if phase == FlightPhase.CLIMB:
        return cruise_ktas * 0.85 * derate_scale
    if phase == FlightPhase.LOITER:
        return cruise_ktas * 0.60 * derate_scale
    if phase == FlightPhase.DESCENT:
        return cruise_ktas * 0.55
    if phase == FlightPhase.LANDING:
        return cruise_ktas * 0.45
    if phase == FlightPhase.COMPLETED:
        return 0.0
    return cruise_ktas * derate_scale  # CRUISE / TRANSIT / RETURN_TRANSIT


def _phase_throttle_pct(phase: "FlightPhase", derate_scale: float) -> float:
    if phase == FlightPhase.PREFLIGHT:
        return 25.0
    if phase == FlightPhase.TAKEOFF:
        return 100.0 * derate_scale
    if phase == FlightPhase.CLIMB:
        return 92.0 * derate_scale
    if phase == FlightPhase.LOITER:
        return 62.0 * derate_scale
    if phase == FlightPhase.DESCENT:
        return 35.0
    if phase == FlightPhase.LANDING:
        return 40.0
    if phase == FlightPhase.COMPLETED:
        return 0.0
    return 68.0 * derate_scale  # CRUISE / TRANSIT / RETURN_TRANSIT


@dataclass
class AutopilotFlightModel:
    """Stateful waypoint-seeking autopilot integrator. One instance per mission; ``advance()``
    is called once per simulation tick with real elapsed ``dt`` and mutates persistent state
    (position, heading, pitch, roll, speed) rather than recomputing position from a global
    time fraction. This is what makes the aircraft actually fly instead of translate."""

    waypoints: List[Waypoint]
    env: EnvironmentalConditions

    # Persistent kinematic state (ENU meters, radians, m/s)
    pos_x_m: float = 0.0
    pos_y_m: float = 0.0
    pos_z_m: float = 0.0            # AMSL meters
    heading_rad: float = 0.0
    pitch_rad: float = 0.0
    roll_rad: float = 0.0
    speed_mps: float = MIN_SPEED_MPS

    current_wp_idx: int = 0          # index of the waypoint currently being sought (1-based
                                      # in MissionState terms: 0 = still departing WP0)
    loiter_elapsed_sec: float = 0.0
    _initialized: bool = False

    arrival_radius_m: float = WAYPOINT_ARRIVAL_RADIUS_M

    # Optional manual override (same feel as the standalone Blender sim: W/S=pitch,
    # A/D=turn, E/Q=throttle). When any key is held, advance() integrates heading/pitch/
    # throttle directly from key state at the same rate-limited integrators the autopilot
    # itself uses, instead of seeking the current waypoint. Releasing all keys hands
    # control back to the autopilot automatically.
    manual_keys: dict = field(default_factory=dict)
    manual_throttle_pct: float = 65.0

    def __post_init__(self) -> None:
        anchor = THEATER_ENU_ANCHORS.get(self.env.theater_name)
        if anchor is not None:
            ref_lat, ref_lon = anchor
        else:
            ref_lat = self.waypoints[0].lat if self.waypoints else 34.2500
            ref_lon = self.waypoints[0].lon if self.waypoints else 77.5800
        self.projector = GeodeticProjector(ref_lat, ref_lon, self.env.base_elevation_m)
        self.enu_waypoints: List[Tuple[float, float, float, Waypoint]] = []
        for wp in self.waypoints:
            x, y, z = self.projector.to_enu(wp.lat, wp.lon, wp.alt_msl_m)
            self.enu_waypoints.append((x, y, z, wp))
        self.terrain = get_terrain_heightfield()

    def _ensure_initialized(self) -> None:
        if self._initialized or not self.enu_waypoints:
            return
        x0, y0, z0, wp0 = self.enu_waypoints[0]
        self.pos_x_m, self.pos_y_m = x0, y0
        self.pos_z_m = wp0.alt_msl_m
        if len(self.enu_waypoints) > 1:
            x1, y1, _, _ = self.enu_waypoints[1]
            self.heading_rad = math.atan2(x1 - x0, y1 - y0)
        self._initialized = True

    def _ground_elevation(self, x_m: float, y_m: float) -> float:
        if self.terrain.loaded:
            return self.terrain.elevation_at(x_m, y_m)
        # Fall back to interpolating authored waypoint terrain hints if the mesh failed
        # to load, rather than crashing the mission executive.
        if len(self.enu_waypoints) >= 2:
            _, _, _, wp0 = self.enu_waypoints[max(0, self.current_wp_idx - 1)]
            return wp0.terrain_alt_m or self.env.base_elevation_m
        return self.env.base_elevation_m

    def advance(
        self,
        dt: float,
        phase: "FlightPhase",
        derate_scale: float = 1.0,
    ) -> Tuple[
        Tuple[float, float, float],   # pos (x, y, z_amsl)
        float,                        # ground_elev_m
        float,                        # agl_m
        Tuple[float, float, float],   # attitude (heading_deg, pitch_deg, roll_deg)
        float,                        # commanded_throttle_pct
        float,                        # true_airspeed_ktas
        float,                        # indicated_airspeed_kias
        int,                          # current_wp_idx (1-based "next waypoint" index)
        float,                        # dist_remaining_to_wp_m
        float,                        # path_progress_fraction
    ]:
        self._ensure_initialized()
        if not self.enu_waypoints:
            return (0.0, 0.0, 0.0), self.env.base_elevation_m, 0.0, (0.0, 0.0, 0.0), 0.0, 0.0, 0.0, 0, 0.0, 0.0

        target_idx = min(self.current_wp_idx + 1, len(self.enu_waypoints) - 1)
        tx, ty, tz, target_wp = self.enu_waypoints[target_idx]

        dx = tx - self.pos_x_m
        dy = ty - self.pos_y_m
        dist_m = math.hypot(dx, dy)

        # --- Waypoint sequencing -------------------------------------------------------
        holding_loiter = False
        if dist_m < self.arrival_radius_m and target_idx > self.current_wp_idx:
            if target_wp.loiter_duration_sec > 0.0 and self.loiter_elapsed_sec < target_wp.loiter_duration_sec:
                holding_loiter = True
            else:
                self.current_wp_idx = target_idx
                self.loiter_elapsed_sec = 0.0
                if target_idx < len(self.enu_waypoints) - 1:
                    target_idx = target_idx + 1
                    tx, ty, tz, target_wp = self.enu_waypoints[target_idx]
                    dx = tx - self.pos_x_m
                    dy = ty - self.pos_y_m
                    dist_m = math.hypot(dx, dy)

        if phase == FlightPhase.LOITER:
            self.loiter_elapsed_sec += dt

        if holding_loiter:
            # Orbit the loiter point instead of flying straight through it: steer toward a
            # point on a circle of radius `loiter_radius_m` around the waypoint, rotating
            # over time -- gives a real racetrack/orbit pattern rather than freezing or
            # cutting straight across the holding fix.
            radius_m = max(300.0, target_wp.loiter_radius_m or 800.0)
            orbit_rate_rads = self.speed_mps / max(1.0, radius_m)  # v = r*omega
            orbit_angle = self.loiter_elapsed_sec * orbit_rate_rads
            orbit_tx = tx + radius_m * math.sin(orbit_angle)
            orbit_ty = ty + radius_m * math.cos(orbit_angle)
            dx = orbit_tx - self.pos_x_m
            dy = orbit_ty - self.pos_y_m
            dist_m = math.hypot(dx, dy)

        manual_active = any(self.manual_keys.values()) if self.manual_keys else False

        if manual_active:
            # --- Manual override (Blender-sim feel: W/S=pitch, A/D=turn, E/Q=throttle) --
            # Same rate-limited integrators the autopilot uses -- continuous smooth motion,
            # never an instant snap -- just driven by key state instead of a waypoint bearing.
            if self.manual_keys.get("turn_left"):
                self.heading_rad = _wrap_pi(self.heading_rad - TURN_RATE_RADS * dt)
                self.roll_rad = max(-MAX_BANK_RAD, self.roll_rad - ROLL_LEVEL_RATE * 2.0 * dt)
            elif self.manual_keys.get("turn_right"):
                self.heading_rad = _wrap_pi(self.heading_rad + TURN_RATE_RADS * dt)
                self.roll_rad = min(MAX_BANK_RAD, self.roll_rad + ROLL_LEVEL_RATE * 2.0 * dt)
            else:
                # Wings-level decay when no turn key is held.
                self.roll_rad -= max(-1.0, min(1.0, self.roll_rad)) * min(1.0, ROLL_LEVEL_RATE * dt)

            if self.manual_keys.get("pitch_up"):
                self.pitch_rad = min(MAX_PITCH_RAD, self.pitch_rad + PITCH_RATE_RADS * dt)
            elif self.manual_keys.get("pitch_down"):
                self.pitch_rad = max(-MAX_PITCH_RAD, self.pitch_rad - PITCH_RATE_RADS * dt)

            if self.manual_keys.get("throttle_up"):
                self.manual_throttle_pct = min(100.0, self.manual_throttle_pct + 40.0 * dt)
            elif self.manual_keys.get("throttle_down"):
                self.manual_throttle_pct = max(15.0, self.manual_throttle_pct - 40.0 * dt)

            target_speed_ktas = (self.manual_throttle_pct / 100.0) * (target_wp.airspeed_ktas or 100.0) * 1.5
            target_speed_mps = max(MIN_SPEED_MPS, target_speed_ktas * 0.514444)
            speed_error = target_speed_mps - self.speed_mps
            accel = max(-MAX_ACCEL_MPS2, min(MAX_ACCEL_MPS2, speed_error * SPEED_GOVERNOR_GAIN))
            self.speed_mps = max(MIN_SPEED_MPS, self.speed_mps + accel * dt)
            throttle_pct_override = self.manual_throttle_pct
        else:
            # --- Speed governor (first-order P-controller toward phase-commanded TAS) --
            cruise_ktas = target_wp.airspeed_ktas or 100.0
            target_speed_ktas = _phase_target_speed_ktas(phase, cruise_ktas, derate_scale)
            target_speed_mps = max(MIN_SPEED_MPS, target_speed_ktas * 0.514444)
            speed_error = target_speed_mps - self.speed_mps
            accel = max(-MAX_ACCEL_MPS2, min(MAX_ACCEL_MPS2, speed_error * SPEED_GOVERNOR_GAIN))
            self.speed_mps = max(MIN_SPEED_MPS, self.speed_mps + accel * dt)

            # --- Heading control (rate-limited turn toward bearing-to-waypoint) --------
            bearing_rad = math.atan2(dx, dy) if dist_m > 1.0 else self.heading_rad
            heading_error = _wrap_pi(bearing_rad - self.heading_rad)
            turn_step = max(-TURN_RATE_RADS * dt, min(TURN_RATE_RADS * dt, heading_error))
            self.heading_rad = _wrap_pi(self.heading_rad + turn_step)

            # --- Coordinated bank (proportional to heading error, decaying level) ------
            target_bank = max(-MAX_BANK_RAD, min(MAX_BANK_RAD, heading_error * BANK_PER_HEADING_ERROR))
            bank_step = max(-ROLL_LEVEL_RATE * dt, min(ROLL_LEVEL_RATE * dt, target_bank - self.roll_rad))
            self.roll_rad += bank_step

            # --- Pitch / climb control (rate-limited toward target altitude) -----------
            target_alt_amsl = target_wp.alt_msl_m
            alt_error = target_alt_amsl - self.pos_z_m
            desired_climb_mps = max(-CLIMB_RATE_MAX_MPS, min(CLIMB_RATE_MAX_MPS, alt_error * 0.15))
            target_pitch = math.asin(max(-1.0, min(1.0, desired_climb_mps / max(1.0, self.speed_mps))))
            target_pitch = max(-MAX_PITCH_RAD, min(MAX_PITCH_RAD, target_pitch))
            pitch_step = max(-PITCH_RATE_RADS * dt, min(PITCH_RATE_RADS * dt, target_pitch - self.pitch_rad))
            self.pitch_rad += pitch_step
            throttle_pct_override = None

        # --- Position integration (semi-implicit Euler: velocity updated, then applied) -
        cos_pitch = math.cos(self.pitch_rad)
        fwd_x = math.sin(self.heading_rad) * cos_pitch
        fwd_y = math.cos(self.heading_rad) * cos_pitch
        fwd_z = math.sin(self.pitch_rad)

        self.pos_x_m += fwd_x * self.speed_mps * dt
        self.pos_y_m += fwd_y * self.speed_mps * dt
        self.pos_z_m += fwd_z * self.speed_mps * dt

        # --- Terrain following -----------------------------------------------------------
        gnd_elev = self._ground_elevation(self.pos_x_m, self.pos_y_m)
        agl_m = self.pos_z_m - gnd_elev
        if agl_m < MIN_AGL_FLOOR_M:
            # Soft floor: never let the integrator drive the aircraft below the terrain
            # surface (mirrors the Blender sim's ground-collision floor), without silently
            # pretending AGL never gets low -- callers can still see this via agl_m.
            self.pos_z_m = gnd_elev + MIN_AGL_FLOOR_M
            agl_m = MIN_AGL_FLOOR_M

        # --- Outputs ----------------------------------------------------------------------
        throttle_pct = throttle_pct_override if throttle_pct_override is not None else _phase_throttle_pct(phase, derate_scale)
        tas_kt = self.speed_mps * 1.943844
        cur_alt_msl_m = self.pos_z_m
        t_c, p_hpa, _ = AtmosphericModel.sample(cur_alt_msl_m, self.env.qnh_hpa, self.env.isa_temp_offset_c)
        sigma = (p_hpa / 1013.25) * (288.15 / (t_c + 273.15))
        kias = tas_kt * math.sqrt(max(0.2, sigma))

        heading_deg = (math.degrees(self.heading_rad) + 360.0) % 360.0
        pitch_deg = math.degrees(self.pitch_rad)
        roll_deg = math.degrees(self.roll_rad)

        total_route_m = sum(
            math.hypot(
                self.enu_waypoints[i + 1][0] - self.enu_waypoints[i][0],
                self.enu_waypoints[i + 1][1] - self.enu_waypoints[i][1],
            )
            for i in range(len(self.enu_waypoints) - 1)
        ) or 1.0
        traveled_m = sum(
            math.hypot(
                self.enu_waypoints[i + 1][0] - self.enu_waypoints[i][0],
                self.enu_waypoints[i + 1][1] - self.enu_waypoints[i][1],
            )
            for i in range(min(self.current_wp_idx, len(self.enu_waypoints) - 1))
        )
        # Add partial progress along the leg currently being flown (straight-line distance
        # from the departure waypoint to the aircraft, clamped so a wide turn overshoot
        # can't push progress past the full leg length).
        if self.current_wp_idx < len(self.enu_waypoints) - 1:
            ox, oy, _, _ = self.enu_waypoints[self.current_wp_idx]
            leg_len_m = math.hypot(tx - ox, ty - oy) or 1.0
            covered_m = math.hypot(self.pos_x_m - ox, self.pos_y_m - oy)
            traveled_m += min(leg_len_m, covered_m)
        path_progress_fraction = max(0.0, min(1.0, traveled_m / total_route_m))

        return (
            (round(self.pos_x_m, 1), round(self.pos_y_m, 1), round(self.pos_z_m, 1)),
            round(gnd_elev, 1),
            round(agl_m, 1),
            (round(heading_deg, 1), round(pitch_deg, 1), round(roll_deg, 1)),
            round(throttle_pct, 1),
            round(tas_kt, 1),
            round(kias, 1),
            self.current_wp_idx + 1,
            round(dist_m, 1),
            round(path_progress_fraction, 3),
        )

    @property
    def is_final_waypoint_reached(self) -> bool:
        if not self.enu_waypoints:
            return True
        last_idx = len(self.enu_waypoints) - 1
        tx, ty, _, _ = self.enu_waypoints[last_idx]
        dist_m = math.hypot(tx - self.pos_x_m, ty - self.pos_y_m)
        return self.current_wp_idx >= last_idx and dist_m < WAYPOINT_ARRIVAL_RADIUS_M
