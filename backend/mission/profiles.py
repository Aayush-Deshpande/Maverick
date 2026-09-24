"""MALE UAV Multi-Phase Mission Profiles (R10, B1.4, D16).

Defines standard operational flight profiles:
1. 24-Hour Maritime / Border Loiter Surveillance.
2. High-Altitude Leh / Ladakh Reconnaissance (3,300m density-altitude takeoff).
3. Tactical Dash & Low-Level Ingress.
4. Generates continuous operational profiles (altitude, throttle, ambient conditions, aux electrical load).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterator, List, Optional, Tuple


class MissionPhase(str, Enum):
    TAXI_OUT = "TAXI_OUT"
    TAKEOFF = "TAKEOFF"
    CLIMB = "CLIMB"
    CRUISE_TRANSIT = "CRUISE_TRANSIT"
    LOITER_RECON = "LOITER_RECON"
    DASH = "DASH"
    DESCENT = "DESCENT"
    APPROACH_LAND = "APPROACH_LAND"
    TAXI_IN = "TAXI_IN"
    SHUTDOWN = "SHUTDOWN"


@dataclass
class MissionSegment:
    phase: MissionPhase
    duration_sec: float
    start_alt_m: float
    end_alt_m: float
    throttle_pct: float
    airspeed_tas_mps: float
    aux_load_kw: float = 2.5     # Avionics + EO/IR payload electrical drain


@dataclass
class MissionProfile:
    name: str
    description: str
    base_elevation_m: float
    segments: List[MissionSegment]

    @property
    def total_duration_sec(self) -> float:
        return sum(s.duration_sec for s in self.segments)

    def sample_at(self, t_sec: float) -> Tuple[MissionPhase, float, float, float, float]:
        """Sample mission state at elapsed time t_sec:
        Returns: (phase, altitude_m, throttle_pct, tas_mps, aux_load_kw).
        """
        elapsed = 0.0
        for s in self.segments:
            if elapsed <= t_sec <= elapsed + s.duration_sec:
                frac = (t_sec - elapsed) / max(1e-6, s.duration_sec)
                alt = s.start_alt_m + frac * (s.end_alt_m - s.start_alt_m)
                return s.phase, alt, s.throttle_pct, s.airspeed_tas_mps, s.aux_load_kw
            elapsed += s.duration_sec

        # Past mission end: return shutdown state
        last = self.segments[-1]
        return last.phase, last.end_alt_m, 0.0, 0.0, 0.0


def create_standard_male_surveillance_mission(loiter_hours: float = 12.0) -> MissionProfile:
    """Standard 12-24 hr MALE UAV border / maritime surveillance profile."""
    loiter_sec = loiter_hours * 3600.0
    segments = [
        MissionSegment(MissionPhase.TAXI_OUT, duration_sec=300.0, start_alt_m=50.0, end_alt_m=50.0, throttle_pct=25.0, airspeed_tas_mps=5.0),
        MissionSegment(MissionPhase.TAKEOFF, duration_sec=60.0, start_alt_m=50.0, end_alt_m=300.0, throttle_pct=100.0, airspeed_tas_mps=35.0),
        MissionSegment(MissionPhase.CLIMB, duration_sec=1500.0, start_alt_m=300.0, end_alt_m=6000.0, throttle_pct=90.0, airspeed_tas_mps=45.0),
        MissionSegment(MissionPhase.CRUISE_TRANSIT, duration_sec=3600.0, start_alt_m=6000.0, end_alt_m=6000.0, throttle_pct=75.0, airspeed_tas_mps=55.0),
        MissionSegment(MissionPhase.LOITER_RECON, duration_sec=loiter_sec, start_alt_m=6000.0, end_alt_m=6000.0, throttle_pct=60.0, airspeed_tas_mps=42.0),
        MissionSegment(MissionPhase.DESCENT, duration_sec=1200.0, start_alt_m=6000.0, end_alt_m=300.0, throttle_pct=35.0, airspeed_tas_mps=50.0),
        MissionSegment(MissionPhase.APPROACH_LAND, duration_sec=180.0, start_alt_m=300.0, end_alt_m=50.0, throttle_pct=40.0, airspeed_tas_mps=30.0),
        MissionSegment(MissionPhase.TAXI_IN, duration_sec=300.0, start_alt_m=50.0, end_alt_m=50.0, throttle_pct=20.0, airspeed_tas_mps=5.0),
        MissionSegment(MissionPhase.SHUTDOWN, duration_sec=60.0, start_alt_m=50.0, end_alt_m=50.0, throttle_pct=0.0, airspeed_tas_mps=0.0),
    ]
    return MissionProfile(
        name="MALE_SURVEILLANCE_LONG_ENDURANCE",
        description="Standard MALE UAV border & maritime loiter surveillance mission",
        base_elevation_m=50.0,
        segments=segments,
    )


def create_high_altitude_leh_mission() -> MissionProfile:
    """High altitude northern forward base mission (3,300m elevation)."""
    segments = [
        MissionSegment(MissionPhase.TAXI_OUT, duration_sec=300.0, start_alt_m=3300.0, end_alt_m=3300.0, throttle_pct=30.0, airspeed_tas_mps=5.0),
        MissionSegment(MissionPhase.TAKEOFF, duration_sec=90.0, start_alt_m=3300.0, end_alt_m=3800.0, throttle_pct=100.0, airspeed_tas_mps=42.0),
        MissionSegment(MissionPhase.CLIMB, duration_sec=1800.0, start_alt_m=3800.0, end_alt_m=8500.0, throttle_pct=95.0, airspeed_tas_mps=48.0),
        MissionSegment(MissionPhase.LOITER_RECON, duration_sec=18000.0, start_alt_m=8500.0, end_alt_m=8500.0, throttle_pct=65.0, airspeed_tas_mps=45.0),
        MissionSegment(MissionPhase.DESCENT, duration_sec=1500.0, start_alt_m=8500.0, end_alt_m=3400.0, throttle_pct=30.0, airspeed_tas_mps=52.0),
        MissionSegment(MissionPhase.APPROACH_LAND, duration_sec=240.0, start_alt_m=3400.0, end_alt_m=3300.0, throttle_pct=45.0, airspeed_tas_mps=38.0),
        MissionSegment(MissionPhase.SHUTDOWN, duration_sec=60.0, start_alt_m=3300.0, end_alt_m=3300.0, throttle_pct=0.0, airspeed_tas_mps=0.0),
    ]
    return MissionProfile(
        name="HIGH_ALTITUDE_LEH_RECON",
        description="High elevation takeoff and 8,500m operating ceiling recon mission",
        base_elevation_m=3300.0,
        segments=segments,
    )
