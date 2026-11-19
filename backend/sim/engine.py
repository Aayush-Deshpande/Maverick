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
from backend.sim.thermal import HeatInputs, Thermal
from backend.sim.turbo import Turbo


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
        self.turbo = Turbo.for_engine(cfg, physics_values(cfg.engine_id, "induction")["wot_map_ratio"])
        if self.turbo is not None:
            self.calibrate_turbo()
        self.calibrate()
        self.thermal = Thermal.for_engine(cfg, self.combustion.lhv_j_kg)
        self.calibrate_thermal()

    # -- pieces --------------------------------------------------------------------------------------------
    def friction_w(self, rpm: float) -> float:
        k = rpm / 1000.0
        a, b, c = self.fmep
        return (a + b * k + c * k * k) * self.induction.displaced_m3 * rpm / 120.0

    def steady_point(self, throttle_pct: float, rpm: float, atm: Atmosphere, lam: Optional[float] = None,
                     filter_factor: float = 1.0, map_target_pa: Optional[float] = None,
                     turbo_health: Optional[Dict] = None) -> OperatingPoint:
        """Steady operating point. map_target_pa: boost controller MAP target (turbo engines; default take-off)."""
        lam = self.nominal_lambda if lam is None else lam
        ind = self.induction
        mdot = 0.0
        p_src, t_src = atm.pressure_pa, atm.temperature_k
        frac = throttle_area_fraction(throttle_pct, ind.idle_fraction)
        for _ in range(8):                                   # flow-dependent filter drop and boost: fixed point
            if self.turbo is not None:
                target = None if map_target_pa is None else map_target_pa / self.wot_map_ratio
                p_src = self.turbo.steady_charge(atm, mdot, target_pa=target, health=turbo_health)
                t_src = self.turbo.charge_temperature_k(atm, p_src, (turbo_health or {}).get("intercooler_fouling", 0.0))
            p_up = p_src - ind.k_filter * filter_factor * mdot ** 2
            map_pa = ind._steady_map(frac, p_up, t_src, rpm)
            mdot = ind.cylinder_flow(map_pa, t_src, rpm)
        cycles_per_s = rpm / 120.0
        m_air_cyl = mdot / max(cycles_per_s * self.n_cyl, 1e-9)
        m_fuel_cyl = self.combustion.deliverable_fuel(m_air_cyl / (self.combustion.stoich_afr * lam), m_air_cyl)
        w_cyl = self.combustion.indicated_work_j(m_fuel_cyl, lam)
        indicated = w_cyl * self.n_cyl * cycles_per_s
        friction = self.friction_w(rpm)
        return OperatingPoint(rpm=rpm, map_pa=map_pa, mdot_air_kg_s=mdot,
                              mdot_fuel_kg_s=m_fuel_cyl * self.n_cyl * cycles_per_s, indicated_w=indicated,
                              friction_w=friction, brake_w=indicated - friction)

    @property
    def wot_map_ratio(self) -> float:
        return physics_values(self.cfg.engine_id, "induction")["wot_map_ratio"]

    def calibrate_turbo(self) -> None:
        """Turbo capability (flat PR_max) from the documented critical altitude; a documented lower take-off
        critical altitude becomes the TCU take-off pressure-ratio cap (both CALIBRATED, see backend/sim/turbo.py)."""
        t = self.cfg.turbo
        to_kpa = t.map_takeoff_max_kpa or t.max_boost_kpa
        if t.critical_altitude_takeoff_ft is not None and t.map_continuous_max_kpa is not None:
            cap_kpa, cap_alt = t.map_continuous_max_kpa, t.critical_altitude_ft
            self.turbo.takeoff_pr_limit = (to_kpa * 1000.0 / self.wot_map_ratio) / Atmosphere.at(t.critical_altitude_takeoff_ft).pressure_pa
        else:
            cap_kpa, cap_alt = to_kpa, t.critical_altitude_ft
        pr = (cap_kpa * 1000.0 / self.wot_map_ratio) / Atmosphere.at(cap_alt).pressure_pa
        self.turbo.calibrate_line([(0.0, pr)])

    # -- calibration (R 21.5 step 1) -----------------------------------------------------------------------
    def calibrate(self) -> Dict[str, float]:
        sl = Atmosphere.at(0)
        self.combustion.eta_i = 1.0
        unit = self.steady_point(100, self.cfg.rated_rpm, sl)          # indicated power per unit eta_i
        target = self.cfg.rated_power_kw * 1000.0
        self.combustion.eta_i = (target + unit.friction_w) / unit.indicated_w
        self.calibration = {"eta_i": self.combustion.eta_i, "status": "CALIBRATED"}
        return self.calibration

    # -- heat (M1-07) --------------------------------------------------------------------------------------
    def heat_inputs(self, op: OperatingPoint, atm: Atmosphere, friction_multiplier: float = 1.0) -> HeatInputs:
        n = self.n_cyl
        return HeatInputs(rpm=op.rpm, fuel_kg_s=[op.mdot_fuel_kg_s / n] * n, burnt=[1.0] * n,
                          indicated_w=[op.indicated_w / n] * n,
                          exhaust_kg_s=[(op.mdot_air_kg_s + op.mdot_fuel_kg_s) / n] * n,
                          friction_w=op.friction_w * friction_multiplier, brake_w=op.brake_w,
                          manifold_t_k=atm.temperature_k)

    def calibration_atmosphere(self) -> Atmosphere:
        return Atmosphere.at(0, isa_dev_c=self.thermal.ph["calibration_isa_dev_c"])

    def calibrate_thermal(self) -> None:
        """R 21.5 step 4: max continuous rpm, WOT, ISA+15, design airspeed -> temperatures at their targets."""
        from backend.sim.rotor import load_propellers
        atm = self.calibration_atmosphere()
        props = load_propellers()["CONSTANT_SPEED" if self.cfg.propeller_governor else "FIXED_PITCH"]
        self.design_tas_kt = float(props["design_tas_kt"]["value"])
        op = self.steady_point(100, self.cfg.max_continuous_rpm, atm)
        self.thermal.calibrate(self.heat_inputs(op, atm), atm, self.design_tas_kt, self.cfg.rated_rpm)

    def settle_thermal(self, throttle_pct: float, rpm: float, atm: Atmosphere, tas_kt: Optional[float] = None,
                       seconds: float = 3600.0, dt: float = 0.5, health: Optional[Dict] = None) -> Thermal:
        """Run the heat balances to (near) steady state at a fixed operating point (tests, maps)."""
        tas = self.design_tas_kt if tas_kt is None else tas_kt
        for _ in range(int(seconds / dt)):
            op = self.steady_point(throttle_pct, rpm, atm)
            self.thermal.step(dt, self.heat_inputs(op, atm, self.thermal.friction_multiplier), atm, tas, health)
        return self.thermal

