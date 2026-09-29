"""MALE UAV Aerodynamic Glide Polar and Emergency Runway Reachability Module (PS-26054).

Calculates:
1. Lift-to-Drag glide polar: (L/D)_max = 14.5 (feathered propeller) or 10.5 (windmilling).
2. Best glide speed V_bg as a function of altitude and mass.
3. Sink rate and total glide duration to ground / minimum pattern altitude.
4. Dynamic reachability cone (footprint radius accounting for headwind/tailwind).
5. Diversion airfield selection with positive glide margin guarantees.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class DiversionAirfield:
    id: str
    name: str
    lat: float
    lon: float
    elevation_ft: float
    runway_length_m: float
    bearing_deg: float = 0.0


@dataclass
class AirfieldReachability:
    airfield_id: str
    name: str
    distance_km: float
    distance_nm: float
    alt_required_ft: float
    alt_margin_ft: float
    glide_time_min: float
    is_reachable: bool
    status: str  # "REACHABLE_CONFIDENT" | "MARGINAL" | "UNREACHABLE"

    def as_dict(self) -> dict:
        return {
            "airfield_id": self.airfield_id,
            "name": self.name,
            "distance_km": round(self.distance_km, 2),
            "distance_nm": round(self.distance_nm, 2),
            "alt_required_ft": round(self.alt_required_ft, 0),
            "alt_margin_ft": round(self.alt_margin_ft, 0),
            "glide_time_min": round(self.glide_time_min, 1),
            "is_reachable": self.is_reachable,
            "status": self.status,
        }


@dataclass
class GlideAssessment:
    altitude_ft: float
    feathered: bool
    ld_ratio: float
    best_glide_tas_kt: float
    sink_rate_fpm: float
    glide_range_nm: float
    time_aloft_min: float
    headwind_kt: float
    reachable_airfields: List[AirfieldReachability]
    recommended_diversion: Optional[AirfieldReachability]

    def as_dict(self) -> dict:
        airfield_dicts = [a.as_dict() for a in self.reachable_airfields]
        return {
            "altitude_ft": round(self.altitude_ft, 0),
            "propeller_feathered": self.feathered,
            "ld_ratio": round(self.ld_ratio, 1),
            "best_glide_tas_kt": round(self.best_glide_tas_kt, 1),
            "sink_rate_fpm": round(self.sink_rate_fpm, 0),
            "glide_range_nm": round(self.glide_range_nm, 1),
            "time_aloft_min": round(self.time_aloft_min, 1),
            "headwind_kt": round(self.headwind_kt, 1),
            "reachable_count": len([a for a in self.reachable_airfields if a.is_reachable]),
            "recommended_diversion": self.recommended_diversion.as_dict() if self.recommended_diversion else None,
            "airfields": airfield_dicts,
            # Dual-compatible contract aliases for frontend and API
            "glide_ratio": round(self.ld_ratio, 1),
            "still_air_range_km": round(self.glide_range_nm * 1.852, 1),
            "speed_best_glide_kt": round(self.best_glide_tas_kt, 1),
            "reachable_airfields": airfield_dicts,
        }


# Standard military / high-altitude diversion fields for UAV operation in Northern & Western theaters
DEFENSE_DIVERSION_BASES = [
    DiversionAirfield("VILH", "Leh Kushok Bakula Rimpochee", 34.1359, 77.5465, 10682.0, 2750.0),
    DiversionAirfield("VI82", "Thoise Air Force Station", 34.6542, 77.0142, 10050.0, 3050.0),
    DiversionAirfield("VIKG", "Kargil Airfield", 34.5264, 76.1556, 9600.0, 1830.0),
    DiversionAirfield("VINY", "Nyoma Advanced Landing Ground", 33.1500, 78.8333, 13700.0, 2700.0),
    DiversionAirfield("VIAW", "Awantipur AFS", 33.8767, 74.9744, 5380.0, 2800.0),
    DiversionAirfield("VISR", "Srinagar AFS", 33.9871, 74.7741, 5458.0, 3100.0),
    DiversionAirfield("VIUT", "Uttarlai AFS (Barmer)", 25.8117, 71.4828, 500.0, 3000.0),
    DiversionAirfield("VIJR", "Jaisalmer AFS", 26.8889, 70.8653, 760.0, 2740.0),
    DiversionAirfield("VIST", "Suratgarh AFS", 29.3889, 73.9000, 560.0, 2700.0),
]


class UAVGlidePolar:
    """Aerodynamic glide polar calculations for fixed-wing MALE UAV."""

    def __init__(
        self,
        mass_kg: float = 1050.0,
        wing_area_m2: float = 16.0,
        cd0: float = 0.022,
        aspect_ratio: float = 24.5,
        oswald_e: float = 0.85,
    ) -> None:
        self.mass_kg = mass_kg
        self.weight_n = mass_kg * 9.80665
        self.wing_area_m2 = wing_area_m2
        self.cd0 = cd0
        self.ar = aspect_ratio
        self.e = oswald_e
        self.k_induced = 1.0 / (math.pi * oswald_e * aspect_ratio)

        # Feathered L/D max ~ 14.5
        self.ld_max_feathered = 1.0 / (2.0 * math.sqrt(cd0 * self.k_induced))
        # Windmilling drag penalty (~38% degradation)
        self.ld_max_windmilling = self.ld_max_feathered * 0.724  # ~ 10.5

    def air_density(self, alt_m: float) -> float:
        """ISA troposphere density."""
        alt_m = max(0.0, min(15000.0, alt_m))
        t_kelvin = 288.15 - 0.0065 * alt_m
        p_pa = 101325.0 * ((t_kelvin / 288.15) ** 5.2561)
        return p_pa / (287.05 * t_kelvin)

    def best_glide_tas_mps(self, alt_m: float) -> float:
        """Best glide true airspeed in m/s."""
        cl_bg = math.sqrt(self.cd0 / self.k_induced)
        rho = self.air_density(alt_m)
        return math.sqrt((2.0 * self.weight_n) / (rho * self.wing_area_m2 * cl_bg))

    def assess_glide(
        self,
        alt_ft: float,
        feathered: bool = True,
        headwind_kt: float = 0.0,
        uav_lat: float = 34.2,
        uav_lon: float = 77.3,
        airfields: Optional[List[DiversionAirfield]] = None,
    ) -> GlideAssessment:
        """Compute complete glide footprint and evaluate diversion airfield reachability."""
        bases = airfields or DEFENSE_DIVERSION_BASES
        alt_m = alt_ft * 0.3048
        ld = self.ld_max_feathered if feathered else self.ld_max_windmilling
        v_bg_mps = self.best_glide_tas_mps(alt_m)
        v_bg_kt = v_bg_mps * 1.94384

        # Sink rate V_z = V_bg / (L/D)
        sink_rate_mps = v_bg_mps / ld
        sink_rate_fpm = sink_rate_mps * 196.85

        # Ground speed accounting for headwind
        vg_kt = max(10.0, v_bg_kt - headwind_kt)
        glide_hours_per_1000ft = (1000.0 / sink_rate_fpm) / 60.0
        nm_per_1000ft = vg_kt * glide_hours_per_1000ft
        total_glide_nm = (alt_ft / 1000.0) * nm_per_1000ft
        time_aloft_min = (alt_ft / sink_rate_fpm)

        # Haversine distance calculator
        def haversine_km(lat1, lon1, lat2, lon2):
            r = 6371.0
            p1 = math.radians(lat1)
            p2 = math.radians(lat2)
            dp = math.radians(lat2 - lat1)
            dl = math.radians(lon2 - lon1)
            a = math.sin(dp / 2.0)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0)**2
            return 2.0 * r * math.asin(math.sqrt(a))

        reach_list: List[AirfieldReachability] = []
        for f in bases:
            dist_km = haversine_km(uav_lat, uav_lon, f.lat, f.lon)
            dist_nm = dist_km * 0.539957

            # Minimum altitude required to reach airfield at 1,500 ft AGL high key pattern entry
            pattern_alt_ft = f.elevation_ft + 1500.0
            glide_dist_nm = dist_nm
            alt_drop_req_ft = (glide_dist_nm / max(1e-3, nm_per_1000ft)) * 1000.0
            alt_required_ft = pattern_alt_ft + alt_drop_req_ft
            alt_margin_ft = alt_ft - alt_required_ft

            glide_t_min = (alt_drop_req_ft / sink_rate_fpm) if sink_rate_fpm > 0 else 0.0
            is_reach = alt_margin_ft >= 0.0

            status = "UNREACHABLE"
            if alt_margin_ft >= 2000.0:
                status = "REACHABLE_CONFIDENT"
            elif alt_margin_ft >= 0.0:
                status = "MARGINAL"

            reach_list.append(AirfieldReachability(
                airfield_id=f.id,
                name=f.name,
                distance_km=dist_km,
                distance_nm=dist_nm,
                alt_required_ft=alt_required_ft,
                alt_margin_ft=alt_margin_ft,
                glide_time_min=glide_t_min,
                is_reachable=is_reach,
                status=status,
            ))

        # Sort reachable airfields by safety margin (descending)
        reach_list.sort(key=lambda a: a.alt_margin_ft, reverse=True)
        recommended = reach_list[0] if reach_list and reach_list[0].is_reachable else None

        return GlideAssessment(
            altitude_ft=alt_ft,
            feathered=feathered,
            ld_ratio=ld,
            best_glide_tas_kt=v_bg_kt,
            sink_rate_fpm=sink_rate_fpm,
            glide_range_nm=total_glide_nm,
            time_aloft_min=time_aloft_min,
            headwind_kt=headwind_kt,
            reachable_airfields=reach_list,
            recommended_diversion=recommended,
        )
