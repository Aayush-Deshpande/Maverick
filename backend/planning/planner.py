"""Terrain route planner with engine-health feasibility (card M5-08, P Part 4 Step 5.7, T-MIS-6).

Search space: the DEM tile cut into planning cells (configs/planning.json grid.block_px), each with the MAXIMUM
terrain elevation inside it, times altitude layers. Moves: level to one of the 8 neighbouring cells, or climb /
descend one layer inside a cell (a climbing orbit). A state is usable when the layer is at least min_clearance above
the terrain of its cell (for a diagonal move also the two cells it cuts across) and not above the engine's present
service ceiling (backend/planning/performance.py; the ceiling falls when the power factor falls). Cost = horizontal
distance + climb_cost x climb height; descents cost nothing. A* with the great-circle distance as heuristic
(admissible: it never exceeds the remaining cost).

Result: the waypoint list with per-leg margins, or a refusal with a reason. When no route exists, the planner
searches again without the ceiling to tell WHY: the lowest altitude the terrain needs vs the ceiling the engine can
reach. Replanning = planning again from the present position with the present power factor (replan()).
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.planning.performance import climb_rate_fpm, planning_config, service_ceiling_ft
from backend.terrain.dem import DemTile

FT_PER_M = 3.28084
EARTH_R_M = 6371008.8                   # mean Earth radius (IUGG), m
NEIGHBOURS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


@dataclass
class RoutePlan:
    feasible: bool
    reason: str
    engine_id: str
    power_factor: float
    service_ceiling_ft: Optional[float]
    waypoints: List[Dict[str, float]] = field(default_factory=list)
    distance_km: float = 0.0
    max_altitude_ft: float = 0.0
    min_clearance_ft: Optional[float] = None
    required_altitude_ft: Optional[float] = None

    def as_dict(self) -> Dict[str, Any]:
        return {"feasible": self.feasible, "reason": self.reason, "engine_id": self.engine_id,
                "power_factor": round(self.power_factor, 3), "service_ceiling_ft": self.service_ceiling_ft,
                "waypoints": self.waypoints, "distance_km": round(self.distance_km, 2),
                "max_altitude_ft": self.max_altitude_ft,
                "min_clearance_ft": None if self.min_clearance_ft is None else round(self.min_clearance_ft),
                "required_altitude_ft": self.required_altitude_ft}


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R_M * math.asin(math.sqrt(a))


class Planner:
    def __init__(self, tile: DemTile) -> None:
        c = planning_config()
        g, r = c["grid"], c["rules"]
        self.tile = tile
        self.block = int(g["block_px"]["value"])
        self.cell_max_m = tile.block_max(self.block)
        self.nr, self.nc = self.cell_max_m.shape
        self.layer_ft = float(g["layer_ft"]["value"])
        lo, hi = float(g["min_layer_ft"]["value"]), float(g["max_layer_ft"]["value"])
        self.layers = np.arange(lo, hi + 0.5 * self.layer_ft, self.layer_ft)
        self.clearance_ft = float(r["min_clearance_ft"]["value"])
        self.climb_cost = float(r["climb_cost_m_per_m"]["value"])
        # lowest usable layer index per cell (terrain + clearance); len(layers) when none
        need_ft = self.cell_max_m * FT_PER_M + self.clearance_ft
        self.floor_idx = np.searchsorted(self.layers, need_ft, side="left")

    # -- geometry ------------------------------------------------------------------------------------------------
    def cell_of(self, lat: float, lon: float) -> Tuple[int, int]:
        if not self.tile.contains(lat, lon):
            raise ValueError(f"({lat:.4f}, {lon:.4f}) is outside the loaded terrain tile {self.tile.name}")
        r = int((self.tile.lat0 - lat) / self.tile.dlat) // self.block
        c = int((lon - self.tile.lon0) / self.tile.dlon) // self.block
        return min(r, self.nr - 1), min(c, self.nc - 1)

    def centre(self, r: int, c: int) -> Tuple[float, float]:
        half = (self.block - 1) / 2.0
        return (self.tile.lat0 - (r * self.block + half) * self.tile.dlat,
                self.tile.lon0 + (c * self.block + half) * self.tile.dlon)

    def _usable(self, r: int, c: int, k: int, top: int) -> bool:
        return self.floor_idx[r, c] <= k <= top

    # -- search --------------------------------------------------------------------------------------------------
    def _search(self, start: Tuple[int, int, int], goal: Tuple[int, int], top: int) -> Optional[List[Tuple[int, int, int]]]:
        glat, glon = self.centre(*goal)
        h_cache: Dict[Tuple[int, int], float] = {}

        def h(r: int, c: int) -> float:
            v = h_cache.get((r, c))
            if v is None:
                v = h_cache[(r, c)] = haversine_m(*self.centre(r, c), glat, glon)
            return v

        step_m: Dict[Tuple[int, int, int, int], float] = {}
        best = {start: 0.0}
        prev: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}
        heap = [(h(start[0], start[1]), 0.0, start)]
        climb_m = self.layer_ft / FT_PER_M * self.climb_cost
        while heap:
            _f, g, s = heapq.heappop(heap)
            if g > best.get(s, math.inf):
                continue
            r, c, k = s
            if (r, c) == goal:
                path = [s]
                while path[-1] in prev:
                    path.append(prev[path[-1]])
                return path[::-1]
            moves = []
            for dr, dc in NEIGHBOURS:
                rr, cc = r + dr, c + dc
                if not (0 <= rr < self.nr and 0 <= cc < self.nc) or not self._usable(rr, cc, k, top):
                    continue
                if dr and dc and not (self._usable(r + dr, c, k, top) and self._usable(r, c + dc, k, top)):
                    continue                                    # a diagonal must clear both cells it cuts across
                key = (r, c, rr, cc)
                d = step_m.get(key)
                if d is None:
                    d = step_m[key] = haversine_m(*self.centre(r, c), *self.centre(rr, cc))
                moves.append(((rr, cc, k), d))
            if k + 1 <= top:
                moves.append(((r, c, k + 1), climb_m))
            if k - 1 >= self.floor_idx[r, c]:
                moves.append(((r, c, k - 1), 0.0))
            for t, cost in moves:
                ng = g + cost
                if ng < best.get(t, math.inf):
                    best[t] = ng
                    prev[t] = s
                    heapq.heappush(heap, (ng + h(t[0], t[1]), ng, t))
        return None

    def plan(self, engine_id: str, start: Tuple[float, float, float], goal: Tuple[float, float],
             power_factor: float, isa_dev_c: float = 0.0) -> RoutePlan:
        """start = (lat, lon, altitude_ft), goal = (lat, lon). The route ends over the goal cell at the lowest usable
        layer (the approach itself is outside this planner)."""
        lat0, lon0, alt0 = start
        ceiling = service_ceiling_ft(engine_id, power_factor, isa_dev_c)
        base = RoutePlan(False, "", engine_id, power_factor, ceiling)
        try:
            sr, sc = self.cell_of(lat0, lon0)
            gr, gc = self.cell_of(*goal)
        except ValueError as exc:
            base.reason = str(exc)
            return base
        top = -1 if ceiling is None else int(np.searchsorted(self.layers, ceiling, side="right")) - 1
        k0 = int(np.clip(np.searchsorted(self.layers, alt0, side="left"), 0, len(self.layers) - 1))
        k0 = max(k0, int(self.floor_idx[sr, sc]))
        path = None
        if top >= 0 and k0 <= top:
            path = self._search((sr, sc, k0), (gr, gc), top)
        if path is None:
            need = None                                     # lowest top layer that has any route at all
            for t in range(max(top + 1, k0), len(self.layers)):
                if self._search((sr, sc, k0), (gr, gc), t) is not None:
                    need = float(self.layers[t])
                    break
            ceil_txt = "below the lowest layer" if ceiling is None else f"{ceiling:.0f} ft"
            if need is None:
                base.reason = (f"no route clears the terrain by {self.clearance_ft:.0f} ft below "
                               f"{self.layers[-1]:.0f} ft (planning limit)")
            else:
                base.required_altitude_ft = need
                base.reason = (f"terrain on every route needs {need:.0f} ft ({self.clearance_ft:.0f} ft clearance) but "
                               f"the engine's service ceiling at power factor {power_factor:.2f}, ISA{isa_dev_c:+.0f} C is "
                               f"{ceil_txt}")
            return base
        return self._route(base, path, isa_dev_c)

    def _route(self, plan: RoutePlan, path: List[Tuple[int, int, int]], isa_dev_c: float) -> RoutePlan:
        pts, dist, min_clr = [], 0.0, math.inf
        last = None
        for r, c, k in path:
            lat, lon = self.centre(r, c)
            alt = float(self.layers[k])
            terrain_ft = float(self.cell_max_m[r, c] * FT_PER_M)
            min_clr = min(min_clr, alt - terrain_ft)
            if last is not None:
                dist += haversine_m(last[0], last[1], lat, lon)
            # keep turning points and altitude changes only
            pts.append({"lat": round(lat, 5), "lon": round(lon, 5), "altitude_ft": alt,
                        "terrain_ft": round(terrain_ft), "climb_rate_fpm": round(climb_rate_fpm(
                            plan.engine_id, alt, plan.power_factor, isa_dev_c))})
            last = (lat, lon)
        plan.waypoints = _simplify(pts)
        plan.feasible = True
        plan.reason = "route clears terrain and stays below the engine's service ceiling"
        plan.distance_km = dist / 1000.0
        plan.max_altitude_ft = max(p["altitude_ft"] for p in pts)
        plan.min_clearance_ft = min_clr
        return plan

    def replan(self, engine_id: str, position: Tuple[float, float, float], goal: Tuple[float, float],
               power_factor: float, isa_dev_c: float = 0.0) -> RoutePlan:
        """Plan again from the present position with the present engine health."""
        return self.plan(engine_id, position, goal, power_factor, isa_dev_c)


def _simplify(pts: List[Dict[str, float]]) -> List[Dict[str, float]]:
    """Drop intermediate points on straight, level runs (same heading and altitude)."""
    if len(pts) <= 2:
        return pts
    out = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        same_alt = a["altitude_ft"] == b["altitude_ft"] == c["altitude_ft"]
        d1 = (round(b["lat"] - a["lat"], 5), round(b["lon"] - a["lon"], 5))
        d2 = (round(c["lat"] - b["lat"], 5), round(c["lon"] - b["lon"], 5))
        if not (same_alt and d1 == d2):
            out.append(b)
    out.append(pts[-1])
    return out
