"""Vibration orders (card M1-09, R 21.4, P 1.3i): velocity amplitudes in mm/s at the gearbox sensor.

Order m of the crankshaft torque (per crank revolution) for cylinders firing at theta_k = k * 720 / n deg:
  A_m = | sum_k T_k exp(-i m theta_k) | / n,   T_k = per-cylinder torque fraction (firing sequence order)
m = n/2 is the firing order (proportional to mean torque); m = 0.5 and 1 appear only with imbalance (misfire,
injector faults, compression loss), on top of a small manufacturing spread, and are amplified by the mount
transmissibility at low orders (low_order_gain). Propeller 1x (F28), gear mesh (F27)
and the mount transmissibility (F29) are separate terms. RMS = sqrt(sum of squares).
"""
from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from typing import Any, Dict, Sequence

from backend.sim.params import physics_values


_PHASORS: dict = {}


@dataclass
class Vibration:
    n_cyl: int
    firing_order: Sequence[int]
    ph: Dict[str, float]

    @classmethod
    def for_engine(cls, cfg: Any) -> "Vibration":
        return cls(n_cyl=cfg.cylinder_count, firing_order=list(cfg.layout.firing_order),
                   ph=physics_values(cfg.engine_id, "vibration"))

    def _order(self, torques_by_firing: Sequence[float], m: float) -> float:
        n = self.n_cyl
        phasors = _PHASORS.get((n, m))
        if phasors is None:                       # firing-angle phasors depend only on (n, m): computed once
            phasors = _PHASORS[(n, m)] = [cmath.exp(-1j * m * math.radians(k * 720.0 / n)) for k in range(n)]
        return abs(sum(t * p for t, p in zip(torques_by_firing, phasors))) / n

    def orders(self, cylinder_torque: Sequence[float], torque_fraction: float, prop_rpm: float,
               prop_imbalance: float = 0.0, gear_damage: float = 0.0, mount_degradation: float = 0.0) -> Dict[str, float]:
        """cylinder_torque: relative torque per cylinder (index = cylinder number - 1), 1.0 = healthy."""
        ph = self.ph
        spread = ph["manufacturing_spread"]
        # healthy spread pattern (deterministic): alternate +-spread so the floor is non-zero but small
        t = [cylinder_torque[c - 1] * (1 + spread * (1 if i % 2 else -1) * (0.5 if i % 4 > 1 else 1))
             for i, c in enumerate(self.firing_order)]
        mean = sum(t) / self.n_cyl or 1e-9
        load = max(torque_fraction, 0.0)
        gain = ph["firing_order_mm_s_at_rated"] / 1.0              # firing order = mean torque at rated
        mount = 1.0 + (ph["mount_gain"] - 1.0) * mount_degradation
        out = {
            "0.5X": gain * load * self._order(t, 0.5) / mean * mount * ph["low_order_gain"],
            "1X": gain * load * self._order(t, 1.0) / mean * mount * ph["low_order_gain"],
            "firing": gain * load * self._order(t, self.n_cyl / 2) / mean * mount,
            "prop_1X": ph["prop_1x_mm_s"] * (1 + (ph["prop_imbalance_gain"] - 1) * prop_imbalance) * mount
                       * (max(prop_rpm, 0.0) / 2300.0) ** 2,
            "gear_mesh": ph["gear_mesh_mm_s_at_rated"] * load * (1 + (ph["gear_damage_gain"] - 1) * gear_damage) * mount,
        }
        out["rms"] = math.sqrt(sum(v * v for v in out.values()))
        return out

    def frequencies_hz(self, engine_rpm: float, prop_rpm: float) -> Dict[str, float]:
        f1 = engine_rpm / 60.0
        return {"0.5X": 0.5 * f1, "1X": f1, "firing": f1 * self.n_cyl / 2, "prop_1X": prop_rpm / 60.0}
