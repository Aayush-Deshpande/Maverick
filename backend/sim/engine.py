"""Mean-value engine assembly (cards M1-06 onward; grows through M1-07..M1-14, R 21.2-21.5).

Steady-state power chain used for calibration and the T-PHY tests:
  induction (MAP, air flow) -> fuel per cylinder (lambda) -> combustion (indicated work) -> minus friction (FMEP)
  -> brake power. Calibration (R 21.5 step 1): eta_i is solved so brake power at sea level ISA, wide-open throttle and
  rated rpm equals the take-off power in configs/engines (status CALIBRATED, computed at start-up, not stored).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.sim.atmosphere import Atmosphere
from backend.sim.combustion import Combustion
from backend.sim.induction import Induction, throttle_area_fraction
from backend.sim.params import physics_values


@dataclass
class OperatingPoint:
    rpm: float
    map_pa: float
    mdot_air_kg_s: float
    mdot_fuel_kg_s: float
    indicated_w: float
    friction_w: float
    brake_w: float

    @property
    def bsfc_g_kwh(self) -> Optional[float]:
        return None if self.brake_w <= 0 else self.mdot_fuel_kg_s * 3.6e9 / self.brake_w


class MeanValueEngine:
    def __init__(self, cfg: Any) -> None:
        self.cfg = cfg
        self.n_cyl = cfg.cylinder_count
        self.induction = Induction.for_engine(cfg)
        self.combustion = Combustion.for_engine(cfg)
        fr = physics_values(cfg.engine_id, "friction")
        self.fmep = (fr["fmep_a_kpa"] * 1e3, fr["fmep_b_kpa_per_krpm"] * 1e3, fr["fmep_c_kpa_per_krpm2"] * 1e3)
        lam = cfg.nominal_lambda
        self.nominal_lambda = float(lam.value if hasattr(lam, "value") else lam)
        self.calibrate()

    # -- pieces --------------------------------------------------------------------------------------------
    def friction_w(self, rpm: float) -> float:
        k = rpm / 1000.0
        a, b, c = self.fmep
        return (a + b * k + c * k * k) * self.induction.displaced_m3 * rpm / 120.0

    def steady_point(self, throttle_pct: float, rpm: float, atm: Atmosphere, lam: Optional[float] = None,
                     filter_factor: float = 1.0) -> OperatingPoint:
        lam = self.nominal_lambda if lam is None else lam
        ind = self.induction
        mdot = 0.0
        for _ in range(4):                                   # filter drop depends on flow: fixed-point iteration
            p_up = atm.pressure_pa - ind.k_filter * filter_factor * mdot ** 2
            map_pa = ind._steady_map(throttle_area_fraction(throttle_pct, ind.idle_fraction), p_up, atm.temperature_k, rpm)
            mdot = ind.cylinder_flow(map_pa, atm.temperature_k, rpm)
        cycles_per_s = rpm / 120.0
        m_air_cyl = mdot / max(cycles_per_s * self.n_cyl, 1e-9)
        m_fuel_cyl = self.combustion.deliverable_fuel(m_air_cyl / (self.combustion.stoich_afr * lam), m_air_cyl)
        w_cyl = self.combustion.indicated_work_j(m_fuel_cyl, lam)
        indicated = w_cyl * self.n_cyl * cycles_per_s
        friction = self.friction_w(rpm)
        return OperatingPoint(rpm=rpm, map_pa=map_pa, mdot_air_kg_s=mdot,
                              mdot_fuel_kg_s=m_fuel_cyl * self.n_cyl * cycles_per_s, indicated_w=indicated,
                              friction_w=friction, brake_w=indicated - friction)

    # -- calibration (R 21.5 step 1) -----------------------------------------------------------------------
    def calibrate(self) -> Dict[str, float]:
        sl = Atmosphere.at(0)
        self.combustion.eta_i = 1.0
        unit = self.steady_point(100, self.cfg.rated_rpm, sl)          # indicated power per unit eta_i
        target = self.cfg.rated_power_kw * 1000.0
        self.combustion.eta_i = (target + unit.friction_w) / unit.indicated_w
        self.calibration = {"eta_i": self.combustion.eta_i, "status": "CALIBRATED"}
        return self.calibration
