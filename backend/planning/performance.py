"""Climb performance for route feasibility (card M5-08, P Part 4 Step 5.7).

Available power: the calibrated NOMINAL engine model (backend/sim, configs/engines) at full lever and max-continuous
rpm in the ISA(+dev) atmosphere at each altitude layer, times a power factor that describes the engine's present
health (1 = healthy). The factor comes from measured evidence only (power_factor_from_frame): measured / model MAP at
the measured lever, rpm and air (the air path sets the power a piston engine can make at a given rpm), and for a
fixed-pitch propeller also measured / model rpm (lost torque shows as lost rpm). It never reads the fault list.
Required power: drag polar CD = CD0 + k CL^2 at the climb equivalent airspeed (configs/planning.json airframe).
Climb rate = (eta_prop * P_available - D * TAS) / W. Service ceiling = highest layer with at least the configured
minimum climb rate.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from backend.sim.atmosphere import Atmosphere

ROOT = Path(__file__).resolve().parents[2]
G = 9.80665                         # standard gravity, m/s^2
RHO0 = 1.225                        # ISA sea-level density, kg/m^3
KT_TO_MS = 0.514444
MS_TO_FPM = 196.850394
FULL_LEVER_PCT = 100.0


@lru_cache(maxsize=1)
def planning_config() -> Dict[str, Any]:
    return json.loads((ROOT / "configs" / "planning.json").read_text(encoding="utf-8"))


def _v(block: Dict[str, Any], key: str) -> float:
    return float(block[key]["value"])


@lru_cache(maxsize=32)
def available_power_kw(engine_id: str, altitude_ft: float, isa_dev_c: float = 0.0) -> float:
    """Healthy-engine brake power at full lever and max-continuous rpm (nominal model)."""
    from backend.physics.engine_config import load_engine_config
    from backend.sim.engine import MeanValueEngine
    cfg = load_engine_config(engine_id)
    core = MeanValueEngine(cfg)
    op = core.steady_point(FULL_LEVER_PCT, cfg.max_continuous_rpm, Atmosphere.at(altitude_ft, isa_dev_c))
    return max(op.brake_w, 0.0) / 1000.0


def climb_rate_fpm(engine_id: str, altitude_ft: float, power_factor: float, isa_dev_c: float = 0.0) -> float:
    af = planning_config()["airframe"]
    atm = Atmosphere.at(altitude_ft, isa_dev_c)
    w = _v(af, "mass_kg") * G
    s = _v(af, "wing_area_m2")
    eas = _v(af, "climb_eas_kt") * KT_TO_MS
    tas = eas * math.sqrt(RHO0 / atm.density_kg_m3)
    q = 0.5 * atm.density_kg_m3 * tas ** 2
    cl = w / (q * s)
    drag = q * s * (_v(af, "cd0") + _v(af, "induced_k") * cl ** 2)
    p_av = _v(af, "prop_efficiency") * available_power_kw(engine_id, altitude_ft, isa_dev_c) * 1000.0 * power_factor
    return (p_av - drag * tas) / w * MS_TO_FPM


def service_ceiling_ft(engine_id: str, power_factor: float, isa_dev_c: float = 0.0) -> Optional[float]:
    """Highest planning layer with at least min_climb_rate_fpm; None when even the lowest layer has less."""
    c = planning_config()
    g, r = c["grid"], c["rules"]
    lo, hi, step = _v(g, "min_layer_ft"), _v(g, "max_layer_ft"), _v(g, "layer_ft")
    best = None
    h = lo
    while h <= hi + 1e-6:
        if climb_rate_fpm(engine_id, h, power_factor, isa_dev_c) >= _v(r, "min_climb_rate_fpm"):
            best = h
        h += step
    return best


def power_factor_from_frame(measured: Dict[str, Optional[float]], predicted: Dict[str, Optional[float]],
                            governed: bool) -> Tuple[Optional[float], Dict[str, float]]:
    """Health power factor from measured vs nominal-model MAP (and rpm for a fixed-pitch propeller).
    Returns (factor or None when no evidence, the ratios used). Ratios above 1 are capped at 1: the planner never
    assumes more power than the healthy model."""
    keys = ("map_kpa",) if governed else ("map_kpa", "rpm")
    ratios: Dict[str, float] = {}
    for k in keys:
        m, p = measured.get(k), predicted.get(k)
        if m is None or p is None or not math.isfinite(m) or not math.isfinite(p) or p <= 0:
            continue
        ratios[k] = min(1.0, m / p)
    if not ratios:
        return None, ratios
    return max(0.0, math.prod(ratios.values())), ratios


def power_factor_for_frame(engine_id: str, frame: Any) -> Tuple[Optional[float], Dict[str, float]]:
    """Power factor of a running engine from one measured Frame: the nominal model (backend/detect/reference.py)
    predicts MAP and rpm for the measured lever, rpm and air; no tail calibration, so a healthy tail reads close
    to 1 (capped at 1)."""
    from backend.detect.reference import ModelReference
    n = len(frame.cht or [])
    ref = ModelReference(engine_id, n, ("map_kpa", "rpm"))
    out, _ = ref.predict(frame)
    pred = {"map_kpa": float(out[2 * n]), "rpm": float(out[2 * n + 1])}
    return power_factor_from_frame({"map_kpa": frame.map_kpa, "rpm": frame.rpm}, pred, ref.rotor.governed)
