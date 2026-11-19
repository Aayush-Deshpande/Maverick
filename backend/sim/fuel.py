"""Fuel systems (card M1-11, R 21.4, P 1.3l): port injection (912/915), carburettor (914), common rail (AE300/VRDE).

Faults act on parameters only:
  injector flow coefficient per cylinder   (F05 clog, F06 coking, F07 stuck open, F08 stuck closed)
  HP pump / rail health                    (F09 rail pressure decay: rail pressure falls, the ECU stretches the pulse
                                            width up to its limit, then delivery falls)
  low-pressure supply health               (F10: supply pressure falls; port injectors run lean, CI rail sags)
Fuel flow published by the engine is the sum of what each cylinder actually received (no constant offsets).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.sim.params import physics_values


@dataclass
class FuelSystem:
    kind: str                       # PORT_INJECTION | CARBURETTOR | COMMON_RAIL
    nominal_bar: float
    pw_max_factor: float
    rail_tau_s: float
    pressure_bar: float = 0.0

    @classmethod
    def for_engine(cls, cfg: Any) -> "FuelSystem":
        ph = physics_values(cfg.engine_id, "fuel")
        kind = str(cfg.fuel_system)
        if kind == "COMMON_RAIL":
            rail = cfg.rail_pressure_bar
            nominal = float(rail.value if hasattr(rail, "value") else rail)
        elif kind == "CARBURETTOR":
            nominal = ph["carb_fuel_pressure_bar"]
        else:
            nominal = ph["si_fuel_pressure_bar"]
        return cls(kind=kind, nominal_bar=nominal, pw_max_factor=ph["pulse_width_max_factor"],
                   rail_tau_s=ph["rail_time_constant_s"], pressure_bar=nominal)

    def steady_pressure(self, health: Optional[Dict[str, Any]] = None) -> float:
        hl = health or {}
        p = self.nominal_bar * hl.get("supply_health", 1.0)
        if self.kind == "COMMON_RAIL":
            p *= hl.get("rail_health", 1.0)
        return p

    def delivery_factor(self, pressure_bar: float) -> float:
        """Share of the commanded fuel that reaches the cylinders at this pressure."""
        ratio = max(pressure_bar, 0.0) / self.nominal_bar
        if self.kind == "COMMON_RAIL":
            needed = 1.0 / math.sqrt(max(ratio, 1e-6))          # pulse-width stretch the ECU applies
            return 1.0 if needed <= self.pw_max_factor else self.pw_max_factor / needed
        if self.kind == "PORT_INJECTION":
            return math.sqrt(ratio)                               # open-loop: flow ~ sqrt(dp), mixture leans
        return 1.0 if ratio > 0.5 else 2.0 * ratio                # carburettor: float bowl empties below half supply

    def pulse_width_factor(self, pressure_bar: float) -> float:
        if self.kind != "COMMON_RAIL":
            return 1.0
        return min(self.pw_max_factor, 1.0 / math.sqrt(max(pressure_bar / self.nominal_bar, 1e-6)))

    def step(self, dt: float, health: Optional[Dict[str, Any]] = None) -> float:
        target = self.steady_pressure(health)
        self.pressure_bar = target + (self.pressure_bar - target) * math.exp(-dt / self.rail_tau_s)
        return self.pressure_bar
