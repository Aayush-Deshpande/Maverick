"""Performance maps from the calibrated plant (card M1-14, P Step 1.3q).

The map is a sweep of the steady chain (backend/sim/engine.py) over rpm x load at ISA sea level: spark ignition sweeps
the throttle (MAP follows), a quality-governed diesel sweeps the power lever. Brake power, BSFC, brake efficiency,
MAP and mean EGT are outputs of the model, never configured. Written once per engine to var/maps/<engine_id>.json and
served by /api/v1/engines/{engine_id}/maps; the engineer view plots the live operating point on it.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from backend.runtime.paths import var_path
from backend.sim.atmosphere import Atmosphere
from backend.sim.engine import MeanValueEngine
from backend.sim.params import physics_values

W_PER_KW = 1000.0
G_PER_KG = 1000.0
S_PER_H = 3600.0


def build_maps(cfg: Any) -> Dict[str, Any]:
    grid = physics_values(cfg.engine_id, "maps")
    core = MeanValueEngine(cfg)
    atm = Atmosphere.at(0.0)
    n = int(grid["rpm_points"])
    lo = grid["rpm_fraction_min"] * cfg.rated_rpm
    rpms = [lo + (cfg.rated_rpm - lo) * i / (n - 1) for i in range(n)]
    step = grid["load_step_pct"]
    loads = [step * (i + 1) for i in range(int(round(100.0 / step)))]
    out = {k: [] for k in ("power_kw", "bsfc_g_kwh", "brake_efficiency", "map_kpa", "egt_c")}
    for rpm in rpms:
        rows = {k: [] for k in out}
        for load in loads:
            op = core.steady_point(load, rpm, atm)
            fuel = op.mdot_fuel_kg_s
            brake = op.brake_w
            ok = brake > 0 and fuel > 0
            h = core.heat_inputs(op, atm)
            egt = [core.thermal._egt_target(h, i) for i in range(core.n_cyl)]
            rows["power_kw"].append(brake / W_PER_KW)
            rows["bsfc_g_kwh"].append(fuel * G_PER_KG * S_PER_H / (brake / W_PER_KW) if ok else None)
            rows["brake_efficiency"].append(brake / (fuel * core.combustion.lhv_j_kg) if ok else None)
            rows["map_kpa"].append(op.map_pa / W_PER_KW)
            rows["egt_c"].append(sum(egt) / len(egt))
        for k in out:
            out[k].append(rows[k])
    return {"engine_id": cfg.engine_id, "evidence": "SIMULATION", "conditions": "ISA sea level, healthy engine",
            "load_kind": "power_lever_pct" if core.ci else "throttle_pct",
            "axes": {"rpm": rpms, "load_pct": loads}, **out}


_CACHE: Dict[str, Dict[str, Any]] = {}


def maps_for(cfg: Any, write: bool = True) -> Dict[str, Any]:
    """Cached per process; written to var/maps/<engine_id>.json for offline use."""
    m = _CACHE.get(cfg.engine_id)
    if m is None:
        m = _CACHE[cfg.engine_id] = build_maps(cfg)
        if write:
            path = var_path("maps") / f"{cfg.engine_id}.json"
            path.write_text(json.dumps(m), encoding="utf-8")
    return m


def best_bsfc(m: Dict[str, Any]) -> Optional[float]:
    vals = [v for row in m["bsfc_g_kwh"] for v in row if v is not None]
    return min(vals) if vals else None
