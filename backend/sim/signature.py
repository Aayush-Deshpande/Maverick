"""Paired-run signature check (T-FLT-1, R 22.2 item 2): run the plant twice from the same start, once healthy and once
with one registry fault at severity 1, and measure every expected_signature channel. Used by tests and by the
evaluation harness; it reads only plant outputs."""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from backend.sim.faults import FaultParameters
from backend.sim.plant import SimEngine

DT = 0.05


def channel_value(o: Any, channel: str, cylinder: Optional[int]) -> Optional[float]:
    """Expected-signature channel name -> plant output value (cylinder-resolved)."""
    if channel.startswith("vibration_orders."):
        return o.vibration.get(channel.split(".", 1)[1])
    for prefix, series in (("egt", o.egt), ("cht", o.cht)):
        if channel == f"{prefix}[{{cyl}}]":
            return series[(cylinder or 1) - 1]
        if channel == f"{prefix}[*]":
            return sum(series) / len(series)
    simple = {"rpm": o.rpm, "prop_rpm": o.prop_rpm, "map_kpa": o.map_kpa, "coolant_t": o.coolant_c, "oil_t": o.oil_c,
              "oil_p": o.oil_bar, "gearbox_t": o.gearbox_c, "fuel_flow": o.fuel_kg_h, "fuel_p": o.fuel_bar,
              "rail_p": o.fuel_bar, "power_kw": o.power_kw, "bus_v": o.bus_v, "batt_i": o.battery_a,
              "cov_imep": o.cov_imep_pct, "charge_t": o.charge_t_c, "turbo_rpm": o.turbo_rpm,
              "lane_status": float(o.lanes_failed), "oil_qty": o.oil_qty_l}
    return simple.get(channel)


@dataclass
class SignatureResult:
    channel: str
    direction: int
    min_delta: float
    delta: Optional[float]

    @property
    def ok(self) -> bool:
        return self.delta is not None and self.delta * self.direction >= self.min_delta


def run_pair(cfg: Any, registry: Any, fault_id: str, cylinder: Optional[int] = None, throttle_pct: float = 75.0,
             altitude_ft: float = 5000.0, severity: float = 1.0) -> List[SignatureResult]:
    spec = registry.get(fault_id)
    raw = spec.raw
    if raw["scope"] == "CYLINDER" and cylinder is None:
        cylinder = 2 if cfg.cylinder_count >= 2 else 1
    seconds = float(raw["default_ramp_s"]) + float(raw["detect_window_s"])
    fault = SimpleNamespace(fault_id=fault_id, cylinder=cylinder, channel=None, severity=severity,
                            ramp_s=float(raw["default_ramp_s"]), t0_s=0.0)
    engines, fp = [], FaultParameters(cfg, registry)
    for _ in range(2):
        eng = SimEngine(cfg)
        eng.levers.altitude_ft = altitude_ft
        eng.warm_start(throttle_pct)
        for _ in range(int(60 / DT)):                       # settle healthy first (identical for both)
            eng.step(DT)
        engines.append(eng)
    fault.t0_s = engines[1].t
    sigs = [x for x in raw["expected_signature"] if x["channel"] != "{channel}"]
    best = [None] * len(sigs)
    for _ in range(int(seconds / DT)):                      # lockstep: largest movement in the expected direction
        base = engines[0].step(DT)
        h, _sensors = fp.health([fault], engines[1].t, engines[1].core.combustion)
        faulty = engines[1].step(DT, h)
        for k, sig in enumerate(sigs):
            a_, b_ = channel_value(base, sig["channel"], cylinder), channel_value(faulty, sig["channel"], cylinder)
            if a_ is None or b_ is None:
                continue
            d = b_ - a_
            if best[k] is None or d * sig["direction"] > best[k] * sig["direction"]:
                best[k] = d
    res = [SignatureResult(sig["channel"], int(sig["direction"]), float(sig["min_delta"]), best[k])
           for k, sig in enumerate(sigs)]
    return res
