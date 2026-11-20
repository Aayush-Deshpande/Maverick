"""Per-cylinder combustion (card M1-05, R 21.4, P Part 4 Step 1.3d).

  W_indicated = m_fuel_burnt * LHV * eta_i * f_lambda * f_timing * quality
SI rich (lambda < 1): only the oxygen-limited fuel burns (m_burnt = lambda * m_fuel). SI lean: efficiency falls past
the lean optimum and the charge misfires beyond the lean limit. CI: delivered fuel is capped by the smoke limit
(lambda_min); CI is always lean so f_lambda = 1. eta_i is the reference indicated efficiency, CALIBRATED in M1-06 so
each engine meets its take-off power. COV_IMEP and the knock index are published as derived channels.
Faults act here only through inputs: quality (F01/F08 misfire, F02 instability), timing error (F11), ignition energy
(F04 lane loss), fuel per cylinder (F05-F07, from fuel.py in M1-11).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from backend.sim.params import physics_values

ROOT = Path(__file__).resolve().parents[2]


def load_fuel(fuel_id: str) -> Dict[str, float]:
    fuels = json.loads((ROOT / "configs" / "fuels.json").read_text(encoding="utf-8"))["fuels"]
    if fuel_id not in fuels:
        raise KeyError(f"fuel {fuel_id!r} is not in configs/fuels.json")
    return {k: float(v["value"]) for k, v in fuels[fuel_id].items()}


@dataclass
class Combustion:
    spark_ignition: bool
    lhv_j_kg: float
    stoich_afr: float
    eta_i: float                     # reference indicated efficiency (CALIBRATED in M1-06)
    best_lambda: float
    lean_loss: float
    lean_misfire_lambda: float
    timing_loss: float
    smoke_lambda_min: float
    cov_base_pct: float
    cov_limit_pct: float
    knock_ref_map_pa: float
    knock_ref_charge_k: float
    knock_adv_sens: float

    @classmethod
    def for_engine(cls, cfg: Any, eta_i: float = 1.0) -> "Combustion":
        fuel = load_fuel(cfg.fuel)
        ph = physics_values(cfg.engine_id, "combustion")
        return cls(spark_ignition=cfg.ignition_mode == "SPARK_IGNITION", lhv_j_kg=fuel["lhv_mj_kg"] * 1e6,
                   stoich_afr=fuel["stoich_afr"], eta_i=eta_i, best_lambda=ph["si_best_lambda"],
                   lean_loss=ph["lean_loss_coeff"], lean_misfire_lambda=ph["si_lean_misfire_lambda"],
                   timing_loss=ph["timing_loss_per_deg2"], smoke_lambda_min=ph["ci_smoke_lambda_min"],
                   cov_base_pct=ph["cov_base_pct"], cov_limit_pct=ph["cov_instability_limit_pct"],
                   knock_ref_map_pa=ph["knock_ref_map_kpa"] * 1000.0,
                   knock_ref_charge_k=ph["knock_ref_charge_c"] + 273.15,
                   knock_adv_sens=ph["knock_advance_sensitivity_per_deg"])

    # -- efficiency ----------------------------------------------------------------------------------------
    def lambda_factor(self, lam: float) -> float:
        """Energy actually released per unit of fuel energy, relative to the reference (1.0 at stoich SI)."""
        if not self.spark_ignition:
            return 1.0
        if lam < 1.0:
            return max(0.0, lam)                                   # oxygen-limited
        if lam >= self.lean_misfire_lambda:
            return 0.0
        excess = max(0.0, lam - self.best_lambda)
        gain = min(lam, self.best_lambda) - 1.0                    # small lean gain up to the optimum
        return max(0.0, 1.0 + 0.5 * gain - self.lean_loss * excess ** 2)

    def timing_factor(self, timing_error_deg: float) -> float:
        return max(0.0, 1.0 - self.timing_loss * timing_error_deg ** 2)

    def indicated_work_j(self, m_fuel_kg: float, lam: float, timing_error_deg: float = 0.0,
                         quality: float = 1.0) -> float:
        if m_fuel_kg <= 0 or quality <= 0:
            return 0.0
        return (m_fuel_kg * self.lhv_j_kg * self.eta_i * self.lambda_factor(lam) *
                self.timing_factor(timing_error_deg) * min(quality, 1.0))

    # -- limits and stability ------------------------------------------------------------------------------
    def deliverable_fuel(self, demanded_kg: float, m_air_kg: float) -> float:
        """CI smoke limit: fuel per cycle may not exceed m_air / (AFR_stoich * lambda_min)."""
        if self.spark_ignition:
            return demanded_kg
        return min(demanded_kg, m_air_kg / (self.stoich_afr * self.smoke_lambda_min))

    def cov_imep_pct(self, lam: float, load_fraction: float, ignition_energy: float = 1.0) -> float:
        """Cycle-to-cycle IMEP variation: rises lean, at low load and with weak ignition (P 1.3d)."""
        cov = self.cov_base_pct
        if self.spark_ignition:
            lean = max(0.0, lam - self.best_lambda) / max(1e-6, self.lean_misfire_lambda - self.best_lambda)
            cov *= 1.0 + 6.0 * lean ** 2
            cov *= 1.0 + 1.5 * (1.0 - min(max(ignition_energy, 0.0), 1.0))
        cov *= 1.0 + 2.0 * max(0.0, 0.3 - load_fraction) / 0.3
        return cov

    def knock_index(self, map_pa: float, charge_t_k: float, advance_error_deg: float) -> float:
        """1.0 at the reference point; > 1 means more knock-prone (SI only; 0 for CI)."""
        if not self.spark_ignition:
            return 0.0
        return ((map_pa / self.knock_ref_map_pa) * (charge_t_k / self.knock_ref_charge_k) ** 1.5 *
                math.exp(self.knock_adv_sens * advance_error_deg))
