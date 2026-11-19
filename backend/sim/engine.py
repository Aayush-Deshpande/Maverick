"""Mean-value engine assembly (cards M1-06 onward; grows through M1-07..M1-14, R 21.2-21.5).

Steady-state power chain used for calibration and the T-PHY tests:
  induction (MAP, air flow) -> fuel per cylinder (lambda) -> combustion (indicated work) -> minus friction (FMEP)
  -> brake power. Calibration (R 21.5 step 1): eta_i is solved so brake power at sea level ISA, wide-open throttle and
  rated rpm equals the take-off power in configs/engines (status CALIBRATED, computed at start-up, not stored).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from backend.sim.atmosphere import Atmosphere
from backend.sim.combustion import Combustion
from backend.sim.fuel import FuelSystem
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
    cyl_fuel_kg_s: List[float] = field(default_factory=list)
    cyl_indicated_w: List[float] = field(default_factory=list)
    cyl_lambda: List[float] = field(default_factory=list)
    cyl_burnt: List[float] = field(default_factory=list)
    fuel_pressure_bar: Optional[float] = None

    @property
    def bsfc_g_kwh(self) -> Optional[float]:
        return None if self.brake_w <= 0 else self.mdot_fuel_kg_s * 3.6e9 / self.brake_w


class MeanValueEngine:
    def __init__(self, cfg: Any) -> None:
        self.cfg = cfg
        self.n_cyl = cfg.cylinder_count
        self.induction = Induction.for_engine(cfg)
        self.combustion = Combustion.for_engine(cfg)
        self.fuel = FuelSystem.for_engine(cfg)
        self.ci = not self.combustion.spark_ignition
        self.ci_full_fuel_cyl = 0.0          # CI injection quantity per cycle at full lever (CALIBRATED)
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
                     turbo_health: Optional[Dict] = None, fuel_health: Optional[Dict] = None,
                     injector: Optional[Sequence[float]] = None, quality: Optional[Sequence[float]] = None,
                     timing_error_deg: float = 0.0) -> OperatingPoint:
        """Steady operating point. SI: throttle_pct is the butterfly. CI (quality-governed): throttle_pct is the power
        lever = share of the full-load injection quantity; there is no butterfly. Per-cylinder faults enter through
        `injector` (flow coefficients) and `quality` (combustion quality); see backend/sim/fuel.py and combustion.py."""
        lam = self.nominal_lambda if lam is None else lam
        n = self.n_cyl
        inj = list(injector) if injector is not None else [1.0] * n
        qual = list(quality) if quality is not None else [1.0] * n
        ind = self.induction
        mdot = 0.0
        p_src, t_src = atm.pressure_pa, atm.temperature_k
        frac = throttle_area_fraction(100.0 if self.ci else throttle_pct, ind.idle_fraction)
        for _ in range(8):           # filter drop solved in closed form; boost depends on flow: short fixed point
            if self.turbo is not None:
                target = None if map_target_pa is None else map_target_pa / self.wot_map_ratio
                p_src = self.turbo.steady_charge(atm, mdot, target_pa=target, health=turbo_health)
                t_src = self.turbo.charge_temperature_k(atm, p_src, (turbo_health or {}).get("intercooler_fouling", 0.0))
                self.turbo.t_charge_k = t_src
            prev = mdot
            mdot, map_pa = ind.steady_flow(frac, p_src, t_src, rpm, filter_factor)
            if self.turbo is None or abs(mdot - prev) <= 1e-10 * max(mdot, 1e-12):
                break
        cycles_per_s = rpm / 120.0
        m_air_cyl = mdot / max(cycles_per_s * n, 1e-9)
        p_fuel = self.fuel.steady_pressure(fuel_health)
        delivery = self.fuel.delivery_factor(p_fuel)
        afr = self.combustion.stoich_afr
        cyl_fuel, cyl_w, cyl_lam, cyl_burnt = [], [], [], []
        for i in range(n):
            if self.ci:
                # boost-compensated full-load limit: the ECU never fuels richer than the full-load lambda, so power
                # falls as soon as air falls (above the critical altitude, boost leak); smoke limit stays the hard cap
                full = min(self.ci_full_fuel_cyl, m_air_cyl / (afr * self.nominal_lambda))
                demand = min(max(throttle_pct, 0.0), 100.0) / 100.0 * full * inj[i] * delivery
            else:
                demand = m_air_cyl / (afr * lam) * inj[i] * delivery
            m_f = self.combustion.deliverable_fuel(demand, m_air_cyl)
            lam_i = m_air_cyl / (afr * m_f) if m_f > 0 else float("inf")
            w = self.combustion.indicated_work_j(m_f, lam_i, timing_error_deg, qual[i])
            cyl_fuel.append(m_f * cycles_per_s)
            cyl_w.append(w * cycles_per_s)
            cyl_lam.append(lam_i)
            released = 0.0 if m_f <= 0 else min(1.0, max(qual[i], 0.0)) * (
                min(1.0, lam_i) if (not self.ci and lam_i < self.combustion.lean_misfire_lambda) or self.ci else 0.0)
            cyl_burnt.append(released)      # unburnt fuel only; timing/lean/burn losses heat the exhaust instead
        indicated = sum(cyl_w)
        friction = self.friction_w(rpm)
        return OperatingPoint(rpm=rpm, map_pa=map_pa, mdot_air_kg_s=mdot, mdot_fuel_kg_s=sum(cyl_fuel),
                              indicated_w=indicated, friction_w=friction, brake_w=indicated - friction,
                              cyl_fuel_kg_s=cyl_fuel, cyl_indicated_w=cyl_w, cyl_lambda=cyl_lam,
                              cyl_burnt=cyl_burnt, fuel_pressure_bar=p_fuel)

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
        if self.ci:   # full-load injection quantity: rated air at the documented full-load lambda (configs/engines)
            self.ci_full_fuel_cyl = 1.0
            air = self.steady_point(100, self.cfg.rated_rpm, sl).mdot_air_kg_s
            self.ci_full_fuel_cyl = air / (self.cfg.rated_rpm / 120.0 * self.n_cyl) / (
                self.combustion.stoich_afr * self.nominal_lambda)
        unit = self.steady_point(100, self.cfg.rated_rpm, sl)          # indicated power per unit eta_i
        target = self.cfg.rated_power_kw * 1000.0
        self.combustion.eta_i = (target + unit.friction_w) / unit.indicated_w
        self.calibration = {"eta_i": self.combustion.eta_i, "status": "CALIBRATED"}
        return self.calibration

    # -- heat (M1-07) --------------------------------------------------------------------------------------
    def heat_inputs(self, op: OperatingPoint, atm: Atmosphere, friction_multiplier: float = 1.0) -> HeatInputs:
        n = self.n_cyl
        air_cyl = op.mdot_air_kg_s / n
        return HeatInputs(rpm=op.rpm, fuel_kg_s=list(op.cyl_fuel_kg_s), burnt=list(op.cyl_burnt),
                          indicated_w=list(op.cyl_indicated_w),
                          exhaust_kg_s=[air_cyl + f for f in op.cyl_fuel_kg_s],
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

