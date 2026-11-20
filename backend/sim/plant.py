"""The dynamic engine plant: one fixed step of the whole engine (card M1-12, R 21.3, R 21.4 state machine).

Order per step (R 21.3): atmosphere -> ECU (timing, limiters, lanes) -> quasi-steady power chain at the CURRENT rpm
(induction/turbo/fuel/combustion/friction, backend/sim/engine.py) -> torque lag -> rotor (rpm from the torque balance)
-> thermal/coolant/oil/gearbox -> electrical -> vibration -> state machine. Faults arrive ONLY as parameter changes in
`health` (backend/sim/faults.py, M1-13); nothing here edits an output.

Published engine_state is what an observer can see: OFF, CRANKING, RUNNING, FAILED. "Degraded" is a verdict of the
status evaluator from evidence (M2-01), never a plant flag (that would leak the injected fault).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.sim.atmosphere import Atmosphere
from backend.sim.electrical import Electrical
from backend.sim.engine import MeanValueEngine
from backend.sim.params import physics_values
from backend.sim.rotor import Rotor
from backend.sim.vibration import Vibration

MECHANICAL_FUEL_SYSTEM = "CARBURETTOR"           # configs/schema fuel_system without electronic fuel control

OFF, CRANKING, RUNNING, FAILED = "OFF", "CRANKING", "RUNNING", "FAILED"


@dataclass
class Levers:
    throttle_pct: float = 0.0          # SI butterfly / CI power lever
    altitude_ft: float = 0.0
    isa_dev_c: float = 0.0
    humidity_pct: float = 0.0
    tas_kt: Optional[float] = None     # None = installation design airspeed


@dataclass
class PlantOutputs:
    t: float
    state: str
    failure: Optional[str]
    rpm: float
    prop_rpm: float
    throttle_pct: float
    map_kpa: float
    cht: List[float]
    egt: List[float]
    coolant_c: float
    oil_c: float
    oil_bar: float
    gearbox_c: float
    fuel_kg_h: float
    fuel_bar: float
    bus_v: float
    alternator_a: float
    battery_a: float
    soc: float
    power_kw: float
    torque_nm: float
    bsfc_g_kwh: Optional[float]
    lambda_cyl: List[float]
    ign_timing_btdc: Optional[float]
    inj_timing_btdc: Optional[float]
    cov_imep_pct: float
    knock_index: float
    charge_t_c: float
    boost_pr: Optional[float]
    vibration: Dict[str, float]
    lanes_failed: int
    oil_qty_l: Optional[float]
    turbo_rpm: Optional[float]
    altitude_ft: float
    oat_c: float
    tas_kt: float


def knock_controlled_point(core: MeanValueEngine, ecu: Dict[str, Any], throttle_pct: float, rpm: float,
                           atm: Atmosphere, timing_error_deg: float = 0.0, knock_factor: float = 1.0,
                           **steady_kw: Any) -> tuple:
    """Operating point after the ECU knock control (spark ignition: timing retard proportional to the knock index
    above 1). Shared by the plant and the detector's nominal reference so both run the same control law.
    Returns (OperatingPoint, knock index, retard deg)."""
    op = core.steady_point(throttle_pct, rpm, atm, timing_error_deg=timing_error_deg, **steady_kw)
    knock = core.combustion.knock_index(op.map_pa, (core.turbo.t_charge_k if core.turbo else atm.temperature_k),
                                        max(0.0, timing_error_deg)) * knock_factor
    retard = max(0.0, knock - 1.0) * ecu["knock_retard_deg_per_index"] if core.combustion.spark_ignition else 0.0
    if retard > 0:
        op = core.steady_point(throttle_pct, rpm, atm, timing_error_deg=timing_error_deg + retard, **steady_kw)
    return op, knock, retard


class SimEngine:
    def __init__(self, cfg: Any) -> None:
        self.cfg = cfg
        self.core = MeanValueEngine(cfg)
        self.rotor = Rotor.for_engine(cfg)
        self.electrical = Electrical.for_engine(cfg.engine_id)
        self.vibration = Vibration.for_engine(cfg)
        self.ecu = physics_values(cfg.engine_id, "ecu")
        self.fx = physics_values(cfg.engine_id, "fault_effects")
        self.ecu_fuel_cut = cfg.fuel_system != MECHANICAL_FUEL_SYSTEM
        self._gov = (self.rotor.kp, self.rotor.ki)
        self.sm = physics_values(cfg.engine_id, "state_machine")
        self.levers = Levers()
        self.state = OFF
        self.failure: Optional[str] = None
        self.t = 0.0
        self.torque = 0.0
        self._low_oil_s = 0.0
        self._overheat_s = 0.0
        self._glow_s = 0.0
        self.rotor.omega = 0.0
        self._last_op = None
        lim = cfg.limits or {}
        self._oil_min = (lim.get("oil_p", {}).get("rpm_rule", {}).get("below_min") or lim.get("oil_p", {}).get("warning_low"))
        self._hot_limits = {k: lim[k]["warning_high"] for k in ("coolant_t", "cht", "oil_t") if "warning_high" in lim.get(k, {})}

    # -- commands ------------------------------------------------------------------------------------------
    def start(self) -> None:
        if self.state == OFF:
            self.state = CRANKING
            self._glow_s = 0.0

    def stop(self) -> None:
        if self.state in (CRANKING, RUNNING):
            self.state = OFF

    def reset(self) -> None:
        """Explicit scenario reset after a failure (R 19.4): a seized engine does not un-seize by clearing faults."""
        self.state, self.failure = OFF, None
        self._low_oil_s = self._overheat_s = 0.0

    def warm_start(self, throttle_pct: float, atm: Optional[Atmosphere] = None) -> None:
        """Begin RUNNING at the calibrated rpm with temperatures at their calibration point (start of a mission)."""
        self.levers.throttle_pct = throttle_pct
        self.state = RUNNING
        self.rotor.omega = self.cfg.max_continuous_rpm * 2 * math.pi / 60

    # -- one step ------------------------------------------------------------------------------------------
    def step(self, dt: float, health: Optional[Dict[str, Any]] = None, publish: bool = True) -> PlantOutputs:
        """One fixed step. publish=False skips the stateless vibration orders (a substep nobody reads)."""
        hl = health or {}
        self.core._air_key = None          # the air-path cache only serves repeat calls inside this one step
        lv = self.levers
        atm = Atmosphere.at(lv.altitude_ft, isa_dev_c=lv.isa_dev_c, humidity_pct=lv.humidity_pct)
        tas = self.core.design_tas_kt if lv.tas_kt is None else lv.tas_kt
        rpm = self.rotor.engine_rpm
        n = self.core.n_cyl
        comb = self.core.combustion

        # ECU: lanes, timing, limiters
        lane_lost = bool(hl.get("lane_lost"))
        timing_err = hl.get("timing_error_deg", 0.0) + (self.ecu["lane_loss_timing_error_deg"] if lane_lost and comb.spark_ignition else 0.0)
        overspeed = (self.cfg.overspeed_rpm or self.cfg.rated_rpm) * (1 + self.ecu["overspeed_fuel_cut_margin"])
        fuel_on = self.state == RUNNING or (self.state == CRANKING and self._crank_fuel_ok(dt, hl))
        fuel_on = fuel_on and (rpm < overspeed or not self.ecu_fuel_cut)    # a carburettor has no ECU to cut fuel
        quality = list(hl.get("quality") or [1.0] * n)
        if self.core.thermal.coolant_c < self.fx["glow_warm_c"]:            # F35 matters only cold
            quality = [q * (self.fx["glow_cold_quality"] if g else 1.0)
                       for q, g in zip(quality, hl.get("glow_failed") or [False] * n)]
        throttle = lv.throttle_pct * hl.get("throttle_area", 1.0)             # F12 carb icing: less throat area
        if not fuel_on:
            quality = [0.0] * n

        op, knock, retard = knock_controlled_point(self.core, self.ecu, throttle, max(rpm, 1.0), atm, timing_err,
                                           hl.get("knock_factor", 1.0), filter_factor=hl.get("filter_factor", 1.0),
                                           turbo_health=hl.get("turbo"), fuel_health=hl.get("fuel"),
                                           injector=hl.get("injector"), quality=quality,
                                           late_burn=hl.get("late_burn"))
        friction_w = op.friction_w * self.core.thermal.friction_multiplier
        brake_w = (op.indicated_w - friction_w) if fuel_on else -friction_w
        if self.state == FAILED:
            brake_w = -friction_w * 3.0                    # seized/failed: no combustion, heavy drag
        omega = max(self.rotor.omega, 1e-3)
        target_torque = brake_w / omega
        if self.state == CRANKING:
            target_torque += self.sm["starter_torque_nm"]
        tau = (self.core.turbo.lag_s if self.core.turbo else self.ecu["torque_lag_na_s"])
        self.torque = target_torque + (self.torque - target_torque) * math.exp(-dt / tau)
        acc_torque = self.electrical.bus_v * self.electrical.alternator_a / 0.6 / omega if omega > 10 else 0.0
        g = hl.get("governor_gain", 1.0)                                       # F37 governor hunting
        self.rotor.kp, self.rotor.ki = self._gov[0] * g, self._gov[1] * g
        self.rotor.step(dt, self.torque, atm, tas, accessory_torque_nm=acc_torque)

        # heat, electrics, vibration
        heat = self.core.heat_inputs(op if fuel_on else op.__class__(**{**op.__dict__, "cyl_fuel_kg_s": [0.0] * n,
                                     "cyl_indicated_w": [0.0] * n, "cyl_burnt": [0.0] * n}), atm,
                                     self.core.thermal.friction_multiplier)
        heat.rpm = self.rotor.engine_rpm
        th_health = dict(hl.get("thermal") or {})
        th_health.setdefault("oil_p_min_bar", self._oil_min)
        th_health["egt_factor"] = hl.get("egt_factor")
        th_health["wall_heat_factor"] = 1.0 + self.fx["knock_wall_heat_gain"] * max(0.0, knock - 1.0)
        th_health["extra_oil_heat_w"] = self.fx["turbo_bearing_oil_heat_w"] * (hl.get("turbo") or {}).get("bearing_wear", 0.0)
        self.core.thermal.step(dt, heat, atm, tas, th_health)
        el = hl.get("electrical") or {}
        self.electrical.step(dt, self.rotor.engine_rpm, **el)
        mean_w = (sum(op.cyl_indicated_w) / n) if fuel_on and any(op.cyl_indicated_w) else 1.0
        cyl_t = [w / mean_w for w in op.cyl_indicated_w] if fuel_on else [0.0] * n
        torque_frac = max(0.0, self.torque) / max(self.cfg.rated_power_kw * 1000 / (self.cfg.rated_rpm * 2 * math.pi / 60), 1e-6)
        vib: Dict[str, float] = {}
        if publish:
            vib = self.vibration.orders(cyl_t, torque_frac, self.rotor.prop_rpm, **(hl.get("vibration") or {}))
            vib[f"{n // 2}X" if n % 2 == 0 else "firing_order"] = vib["firing"]
            vib["0.5X"] += self.fx["cycle_variation_vibration_mm_s"] * (hl.get("cov_factor", 1.0) - 1.0)
            vib["knock"] = (max(0.0, knock - 1.0) * self.fx["knock_vibration_mm_s_per_index"]
                            if comb.spark_ignition else 0.0)
        turbo_rpm = None
        if self.core.turbo is not None:
            pr = max(self.core.turbo.compressor_pa / atm.pressure_pa, 1.0)
            # shaft speed ~ sqrt(isentropic head): N/N_max = sqrt((PR^0.286-1)/(PR_max^0.286-1))
            pr_cap = max(self.core.turbo.pr_max(0.0), 1.0001)
            turbo_rpm = self.cfg.turbo.max_shaft_rpm * min(1.0, ((pr ** 0.2857 - 1) / (pr_cap ** 0.2857 - 1)) ** 0.5)
            wear = (hl.get("turbo") or {}).get("bearing_wear", 0.0)
            if publish:
                vib["turbo"] = (self.fx["turbo_sync_mm_s"] * (1 + (self.fx["turbo_sync_bearing_gain"] - 1) * wear)
                                * (turbo_rpm / self.cfg.turbo.max_shaft_rpm))
        if publish:
            vib["rms"] = (sum(v * v for k, v in vib.items()
                              if k in ("0.5X", "1X", "firing", "prop_1X", "gear_mesh", "knock", "turbo"))) ** 0.5

        self._update_state(dt, op, fuel_on)
        self.t += dt
        self._last_op = op
        lam = [l if math.isfinite(l) else None for l in op.cyl_lambda] if fuel_on else [None] * n
        load = op.brake_w / (self.cfg.rated_power_kw * 1000)
        ign = None if self.cfg.nominal_ign_timing_btdc is None else self.cfg.nominal_ign_timing_btdc - timing_err - retard
        inj = None if self.cfg.nominal_inj_timing_btdc is None else self.cfg.nominal_inj_timing_btdc - (0.0 if comb.spark_ignition else timing_err)
        power = max(0.0, self.torque * self.rotor.omega)
        return PlantOutputs(
            t=self.t, state=self.state, failure=self.failure, rpm=self.rotor.engine_rpm, prop_rpm=self.rotor.prop_rpm,
            throttle_pct=lv.throttle_pct, map_kpa=op.map_pa / 1000.0, cht=list(self.core.thermal.cht),
            egt=list(self.core.thermal.egt), coolant_c=self.core.thermal.coolant_c, oil_c=self.core.thermal.oil_c,
            oil_bar=self.core.thermal.oil_bar, gearbox_c=self.core.thermal.gearbox_c,
            fuel_kg_h=(op.mdot_fuel_kg_s * 3600.0) if fuel_on else 0.0, fuel_bar=self.core.fuel.step(dt, hl.get("fuel")),
            bus_v=self.electrical.bus_v, alternator_a=self.electrical.alternator_a, battery_a=self.electrical.battery_a,
            soc=self.electrical.soc, power_kw=power / 1000.0, torque_nm=self.torque,
            bsfc_g_kwh=(op.mdot_fuel_kg_s * 3.6e9 / power) if fuel_on and power > 1000 else None,
            lambda_cyl=lam, ign_timing_btdc=ign if comb.spark_ignition else None,
            inj_timing_btdc=inj, cov_imep_pct=hl.get("cov_factor", 1.0) * comb.cov_imep_pct(sum(l for l in lam if l) / max(1, len([l for l in lam if l])) if any(lam) else 1.0,
                                                               load, 0.5 if lane_lost else 1.0),
            knock_index=knock, charge_t_c=(self.core.turbo.t_charge_k if self.core.turbo else atm.temperature_k) - 273.15,
            boost_pr=(op.map_pa / atm.pressure_pa) if self.core.turbo else None, vibration=vib,
            lanes_failed=int(hl.get("lanes_failed", 0)), oil_qty_l=hl.get("oil_qty_l", self.cfg.oil_capacity_l),
            turbo_rpm=turbo_rpm,
            altitude_ft=lv.altitude_ft, oat_c=atm.temperature_k - 273.15, tas_kt=tas)

    # -- state machine -------------------------------------------------------------------------------------
    def _crank_fuel_ok(self, dt: float, hl: Dict[str, Any]) -> bool:
        if not self.cfg.glow_plugs:
            return True
        if self.core.thermal.coolant_c >= 20.0 or hl.get("glow_failed_all"):
            return not hl.get("glow_failed_all") or self.core.thermal.coolant_c >= 20.0
        self._glow_s += dt
        return self._glow_s >= self.sm["glow_preheat_s"]

    def _update_state(self, dt: float, op: Any, fuel_on: bool) -> None:
        rpm = self.rotor.engine_rpm
        if self.state == CRANKING and rpm >= self.sm["run_rpm_fraction_of_idle"] * self.cfg.idle_rpm and fuel_on:
            self.state = RUNNING
        if self.state != RUNNING:
            return
        th = self.core.thermal
        if self._oil_min and th.oil_bar < self._oil_min and rpm > 0.345 * self.cfg.rated_rpm:
            self._low_oil_s += dt
        else:
            self._low_oil_s = 0.0
        if self._low_oil_s >= self.sm["seize_time_s"]:
            self.state, self.failure = FAILED, "SEIZURE_LOW_OIL_PRESSURE"
            return
        values = {"coolant_t": th.coolant_c, "cht": max(th.cht), "oil_t": th.oil_c}
        hot = any(values[k] > v * (1 + self.sm["overheat_margin"]) for k, v in self._hot_limits.items())
        self._overheat_s = self._overheat_s + dt if hot else 0.0
        if self._overheat_s >= self.sm["overheat_time_s"]:
            self.state, self.failure = FAILED, "OVERHEAT"
            return
        delivered = op.mdot_fuel_kg_s
        if self.levers.throttle_pct > 20 and delivered <= 0.0:
            self.state = OFF                               # flameout / fuel starvation: restartable, not a failure
