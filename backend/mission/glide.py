"""Glide reachability and divert ranking for an engine-out MALE UAV (card M5-09, idea text I-10).

Polar: the same airframe as the route planner (configs/planning.json "airframe": mass, wing area, CD0, induced k), so
(L/D)max = 1 / (2 sqrt(CD0 k)) at CL = sqrt(CD0 / k). A stopped engine windmills unless the installation has a
feathering propeller (configs/planning.json "glide"), and windmilling scales L/D by an ASSUMED factor.
Best-glide TAS from the ISA(+dev) density at the current altitude (backend/sim/atmosphere.py).
Airfields come from configs/planning.json "airfields" (public reference points with sources).

Per airfield: the altitude needed to arrive at pattern height after a straight glide (wind = constant head/tail
component, as given), the margin, and, when a DEM tile is given, a terrain check along the path: the glide line must
stay at least glide_clearance_ft above the terrain at every sample. A path that leaves the tile is reported
terrain_checked = false, never assumed clear. The footprint walks each bearing outward until the glide line meets
terrain + clearance (or the glide ends), giving the reachable area over real terrain.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.sim.atmosphere import Atmosphere

G = 9.80665                 # standard gravity, m/s^2
FT_PER_M = 3.28084
M_PER_NM = 1852.0
MS_TO_KT = 1.943844
MS_TO_FPM = 196.850394
EARTH_R_M = 6371000.0       # mean Earth radius for great-circle distances


def _planning() -> Dict[str, Any]:
    from backend.planning.performance import planning_config
    return planning_config()


def _v(block: Dict[str, Any], key: str) -> float:
    return float(block[key]["value"])


@dataclass(frozen=True)
class DiversionAirfield:
    id: str
    name: str
    lat: float
    lon: float
    elevation_ft: float
    ref: str = ""


def configured_airfields() -> List[DiversionAirfield]:
    return [DiversionAirfield(a["id"], a["name"], float(a["lat"]), float(a["lon"]), float(a["elevation_ft"]),
                              a.get("ref", "")) for a in _planning()["airfields"]["value"]]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_R_M * math.asin(math.sqrt(a))


def destination(lat: float, lon: float, bearing_deg: float, dist_m: float) -> Tuple[float, float]:
    d, b = dist_m / EARTH_R_M, math.radians(bearing_deg)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), math.degrees(l2)


@dataclass
class AirfieldReachability:
    airfield_id: str
    name: str
    lat: float
    lon: float
    distance_km: float
    alt_required_ft: float
    alt_margin_ft: float
    glide_time_min: float
    terrain_checked: bool
    min_terrain_clearance_ft: Optional[float]
    is_reachable: bool
    status: str             # REACHABLE_CONFIDENT | MARGINAL | UNREACHABLE | BLOCKED_BY_TERRAIN

    def as_dict(self) -> dict:
        return {
            "airfield_id": self.airfield_id, "name": self.name, "lat": self.lat, "lon": self.lon,
            "distance_km": round(self.distance_km, 2),
            "alt_required_ft": round(self.alt_required_ft, 0),
            "alt_margin_ft": round(self.alt_margin_ft, 0),
            "glide_time_min": round(self.glide_time_min, 1),
            "terrain_checked": self.terrain_checked,
            "min_terrain_clearance_ft": None if self.min_terrain_clearance_ft is None
            else round(self.min_terrain_clearance_ft, 0),
            "is_reachable": self.is_reachable,
            "status": self.status,
        }


@dataclass
class GlideAssessment:
    altitude_ft: float
    lat: float
    lon: float
    feathered: bool
    ld_ratio: float
    best_glide_tas_kt: float
    sink_rate_fpm: float
    still_air_range_km: float
    time_aloft_min: float
    headwind_kt: float
    airfields: List[AirfieldReachability]
    recommended_diversion: Optional[AirfieldReachability]
    footprint: Optional[List[Dict[str, float]]]

    def as_dict(self) -> dict:
        af = [a.as_dict() for a in self.airfields]
        return {
            "altitude_ft": round(self.altitude_ft, 0),
            "position": {"lat": self.lat, "lon": self.lon},
            "propeller_feathered": self.feathered,
            "glide_ratio": round(self.ld_ratio, 1),
            "speed_best_glide_kt": round(self.best_glide_tas_kt, 1),
            "sink_rate_fpm": round(self.sink_rate_fpm, 0),
            "still_air_range_km": round(self.still_air_range_km, 1),
            "time_aloft_min": round(self.time_aloft_min, 1),
            "headwind_kt": round(self.headwind_kt, 1),
            "reachable_count": sum(1 for a in self.airfields if a.is_reachable),
            "recommended_diversion": self.recommended_diversion.as_dict() if self.recommended_diversion else None,
            "reachable_airfields": af,
            "footprint": self.footprint,
            "evidence_class": "SIMULATION",
        }


class UAVGlidePolar:
    """Engine-out glide of the planning airframe."""

    def __init__(self, airframe: Optional[Dict[str, Any]] = None, glide: Optional[Dict[str, Any]] = None) -> None:
        c = _planning()
        af = airframe or c["airframe"]
        self.glide_cfg = glide or c["glide"]
        self.mass_kg = _v(af, "mass_kg")
        self.weight_n = self.mass_kg * G
        self.wing_area_m2 = _v(af, "wing_area_m2")
        self.cd0 = _v(af, "cd0")
        self.k_induced = _v(af, "induced_k")
        self.ld_max_feathered = 1.0 / (2.0 * math.sqrt(self.cd0 * self.k_induced))
        self.ld_max_windmilling = self.ld_max_feathered * _v(self.glide_cfg, "windmill_ld_factor")
        self.feathering = bool(self.glide_cfg["feathering_propeller"]["value"])

    def best_glide_tas_mps(self, alt_ft: float, isa_dev_c: float = 0.0) -> float:
        cl_bg = math.sqrt(self.cd0 / self.k_induced)
        rho = Atmosphere.at(alt_ft, isa_dev_c).density_kg_m3
        return math.sqrt(2.0 * self.weight_n / (rho * self.wing_area_m2 * cl_bg))

    def assess_glide(self, alt_ft: float, uav_lat: float, uav_lon: float, headwind_kt: float = 0.0,
                     feathered: Optional[bool] = None, isa_dev_c: float = 0.0,
                     airfields: Optional[Sequence[DiversionAirfield]] = None, terrain: Any = None,
                     footprint: bool = False) -> GlideAssessment:
        g = self.glide_cfg
        feath = self.feathering if feathered is None else (feathered and self.feathering)
        ld = self.ld_max_feathered if feath else self.ld_max_windmilling
        tas = self.best_glide_tas_mps(alt_ft, isa_dev_c)
        sink_mps = tas / ld
        gs = max(tas - headwind_kt / MS_TO_KT, 0.0)            # ground speed along the glide
        ground_per_m_drop = gs / sink_mps                      # metres over ground per metre of height lost
        alt_m = alt_ft / FT_PER_M
        pattern_ft = _v(g, "pattern_height_ft")
        confident = _v(g, "confident_margin_ft")
        out: List[AirfieldReachability] = []
        for f in (airfields if airfields is not None else configured_airfields()):
            d = haversine_m(uav_lat, uav_lon, f.lat, f.lon)
            drop_ft = (d / ground_per_m_drop) * FT_PER_M if ground_per_m_drop > 0 else math.inf
            need = f.elevation_ft + pattern_ft + drop_ft
            margin = alt_ft - need
            checked, clear = False, None
            if terrain is not None and math.isfinite(drop_ft):
                checked, clear = self._path_clearance(terrain, uav_lat, uav_lon, alt_m, f.lat, f.lon, d,
                                                      ground_per_m_drop)
            if margin < 0:
                status = "UNREACHABLE"
            elif checked and clear is not None and clear < _v(g, "glide_clearance_ft"):
                status = "BLOCKED_BY_TERRAIN"
            else:
                status = "REACHABLE_CONFIDENT" if margin >= confident else "MARGINAL"
            out.append(AirfieldReachability(
                f.id, f.name, f.lat, f.lon, d / 1000.0, need, margin,
                (drop_ft / FT_PER_M / sink_mps / 60.0) if math.isfinite(drop_ft) else math.inf,
                checked, clear, status in ("REACHABLE_CONFIDENT", "MARGINAL"), status))
        out.sort(key=lambda a: (not a.is_reachable, -a.alt_margin_ft))
        rec = out[0] if out and out[0].is_reachable else None
        fp = self._footprint(terrain, uav_lat, uav_lon, alt_m, ground_per_m_drop) if footprint and terrain else None
        return GlideAssessment(alt_ft, uav_lat, uav_lon, feath, ld, tas * MS_TO_KT, sink_mps * MS_TO_FPM,
                               ld * alt_m / 1000.0, alt_m / sink_mps / 60.0, headwind_kt, out, rec, fp)

    def _path_clearance(self, terrain: Any, lat0: float, lon0: float, alt0_m: float, lat1: float, lon1: float,
                        dist_m: float, ground_per_m_drop: float) -> Tuple[bool, Optional[float]]:
        """Minimum height of the straight glide line above terrain, in ft; (False, None) if any sample is off-tile."""
        step = _v(self.glide_cfg, "path_step_m")
        n = max(1, int(math.ceil(dist_m / step)))
        lowest = math.inf
        for i in range(1, n + 1):
            f = i / n
            lat, lon = lat0 + f * (lat1 - lat0), lon0 + f * (lon1 - lon0)
            if not terrain.contains(lat, lon):
                return False, None
            h = alt0_m - f * dist_m / ground_per_m_drop
            lowest = min(lowest, (h - terrain.elevation_m(lat, lon)) * FT_PER_M)
        return True, lowest

    def _footprint(self, terrain: Any, lat0: float, lon0: float, alt0_m: float,
                   ground_per_m_drop: float) -> List[Dict[str, float]]:
        """Reach along each bearing until the glide line comes within the clearance of terrain or leaves the tile."""
        g = self.glide_cfg
        clear_m = _v(g, "glide_clearance_ft") / FT_PER_M
        step = _v(g, "path_step_m")
        n_b = int(g["footprint_bearings"]["value"])
        pts = []
        for k in range(n_b):
            brg = 360.0 * k / n_b
            d, last = 0.0, (lat0, lon0)
            while True:
                lat, lon = destination(lat0, lon0, brg, d + step)
                if not terrain.contains(lat, lon):
                    break
                h = alt0_m - (d + step) / ground_per_m_drop
                if h - terrain.elevation_m(lat, lon) < clear_m:
                    break
                d += step
                last = (lat, lon)
            pts.append({"bearing_deg": brg, "lat": round(last[0], 5), "lon": round(last[1], 5),
                        "range_km": round(d / 1000.0, 2)})
        return pts
