"""Nominal-model reference for the residual detector (M3-04/M3-08, P Part 0 rule 4).

For every frame, in time order, the NOMINAL engine model (backend/sim, configs/engines; no build variation, no
faults, no plant truth) predicts each detector channel from MEASURED inputs only:
  - air path and fuel (the plant's own knock-controlled operating point, backend/sim/plant.py, at the measured
    lever, rpm, altitude, OAT): MAP, fuel flow, brake power; ECU mixture, knock retard and TCU boost schedules are
    part of the model; on spark-ignition engines the ECU-published ignition timing (Frame.ign_cmd) is used as the
    measured input instead, and the knock level it implies sets the extra wall heat (the knock threshold depends on
    the tail's build, so predicting it from the levers would not match this engine);
  - temperatures: the M1 thermal network integrated in time with those heat inputs, so the slow oil and head
    temperatures follow lever changes with their real time constants instead of jumping to a steady value;
  - oil pressure: the pump/relief law at the measured rpm and oil temperature;
  - rpm: the propeller balance from the lever alone (governed: the setpoint; fixed pitch: brake power = propeller
    power at the measured airspeed), capped at the ECU rev-limiter (overspeed fuel cut) where the engine has one;
  - in the rev limiter the ECU cuts fuel on and off: the heat input is the duty cycle that holds the rpm
    (propeller + friction power / indicated power) for the slow temperatures; fuel flow, EGT and rpm carry no
    evidence there (a 1 Hz frame cannot resolve the cut cycle; the status evaluator reports the overspeed itself).
The tail calibration regresses only the small per-tail offset on top (backend/detect/calibration.py). Tail
parameters identified from nominal data (TailCalibration.fit: volumetric efficiency from measured / predicted fuel
flow) are applied to this reference's own copy of the model; the shared nominal model is never changed.

State: the thermal network is re-initialised from the measured temperatures on the first frame, when time goes
backwards (a new sequence) or after a gap longer than max_gap_s; a fault that is already present then shows up as
the model relaxes toward the nominal temperatures. A missing input gives NaN for the channels that need it (no
evidence), never a substituted number.
"""
from __future__ import annotations

import copy
from functools import lru_cache
from typing import Dict, List, Optional, Sequence

import numpy as np

from backend.core.frame import Frame
from backend.sim.atmosphere import Atmosphere
from backend.sim.params import physics_values
from backend.sim.plant import MECHANICAL_FUEL_SYSTEM, knock_controlled_point

KG_S_TO_KG_H = 3600.0
PA_PER_KPA = 1000.0
W_PER_KW = 1000.0
RPM_BRACKET = (0.3, 1.4)          # balance-rpm search range as a fraction of rated rpm
RPM_TOL = 0.5                     # rpm
MAX_STEP_S = 2.0                  # thermal integration sub-step (fastest balance, the heads, has tau ~60 s)
MAX_GAP_S = 120.0
MODELED = ("map_kpa", "fuel_flow", "oil_t", "oil_p", "rpm", "coolant_t", "gearbox_t")   # channels with a model term                 # a longer gap between frames starts a new sequence


@lru_cache(maxsize=None)
def _nominal(engine_config_id: str):
    from backend.physics.engine_config import load_engine_config
    from backend.sim.engine import MeanValueEngine
    from backend.sim.rotor import Rotor
    cfg = load_engine_config(engine_config_id)
    return MeanValueEngine(cfg), Rotor.for_engine(cfg)


def fuel_cut_rpm(core, ecu: Dict) -> Optional[float]:
    """ECU overspeed fuel-cut rpm (same rule as the plant); None for a mechanical fuel system."""
    if core.cfg.fuel_system == MECHANICAL_FUEL_SYSTEM:
        return None
    return (core.cfg.overspeed_rpm or core.cfg.rated_rpm) * (1 + ecu["overspeed_fuel_cut_margin"])


def balance_rpm(core, rotor, throttle: float, atm: Atmosphere, tas_kt: Optional[float],
                cut_rpm: Optional[float] = None) -> float:
    """Steady engine rpm the propeller settles at for this lever (nominal engine, no accessory load)."""
    if rotor.governed:
        return rotor.rpm_setpoint
    if cut_rpm is not None:
        return min(balance_rpm(core, rotor, throttle, atm, tas_kt), cut_rpm)
    tas = rotor.design_tas_kt if tas_kt is None else tas_kt

    def surplus(rpm: float) -> float:
        core._air_key = None
        n = rpm / rotor.gear_ratio / 60.0
        return core.steady_point(throttle, rpm, atm).brake_w - rotor.prop_power_w(n, atm.density_kg_m3, tas)

    lo, hi = (f * core.cfg.rated_rpm for f in RPM_BRACKET)
    if surplus(hi) > 0:
        return hi
    if surplus(lo) < 0:
        return lo
    while hi - lo > RPM_TOL:
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if surplus(mid) > 0 else (lo, mid)
    return 0.5 * (lo + hi)


class ModelReference:
    """Stateful nominal prediction of the detector channels [cht_k, egt_k, *scalars] for one frame stream."""

    N_REGRESSORS = 4              # design columns from the model (normalised): brake power, balance rpm, fuel, MAP

    def __init__(self, engine_config_id: str, n_cyl: int, scalars: Sequence[str],
                 tail: Optional[Dict[str, float]] = None) -> None:
        core, self.rotor = _nominal(engine_config_id)
        self.tail = dict(tail or {})
        if self.tail:
            core = copy.deepcopy(core)
            core.induction.eta_v *= self.tail.get("volumetric_efficiency", 1.0)
            core.fmep = tuple(x * self.tail.get("friction", 1.0) for x in core.fmep)
        self.core = core
        self.ecu = physics_values(engine_config_id, "ecu")
        self.cut_rpm = fuel_cut_rpm(core, self.ecu)
        self.limiter_band = self.ecu["overspeed_fuel_cut_margin"] / 2   # within half the margin of the cut: limiting
        self.knock_wall_gain = physics_values(engine_config_id, "fault_effects")["knock_wall_heat_gain"]
        self.thermal = copy.deepcopy(core.thermal)        # own state; the cached model stays at calibration
        self.n_cyl, self.scalars = n_cyl, tuple(scalars)
        core._air_key = None
        self.fuel_rated_kg_s = core.steady_point(100.0, core.cfg.rated_rpm, Atmosphere.at(0.0)).mdot_fuel_kg_s
        self.last_t: Optional[float] = None
        self._bal_key, self._bal_rpm = None, 0.0

    def _restart(self, f: Frame) -> None:
        th = self.thermal
        th.cht = [float(v) for v in f.cht] if len(f.cht) == self.n_cyl and None not in f.cht else list(self.core.thermal.cht)
        th.egt = [float(v) for v in f.egt] if len(f.egt) == self.n_cyl and None not in f.egt else list(self.core.thermal.egt)
        th.coolant_c = self.core.thermal.coolant_c if f.coolant_t is None else float(f.coolant_t)
        th.oil_c = self.core.thermal.oil_c if f.oil_t is None else float(f.oil_t)
        th.gearbox_c = self.core.thermal.gearbox_c if f.gearbox_t is None else float(f.gearbox_t)
        th.friction_multiplier = 1.0

    def predict(self, f: Frame) -> tuple[np.ndarray, np.ndarray]:
        """-> (prediction per channel, regressors [brake, balance rpm, fuel, MAP] normalised to the rated point);
        NaN where an input is missing. A tail's multiplicative build spread (volumetric efficiency, friction, ...)
        is then linear in these regressors."""
        n = self.n_cyl
        out = np.full(2 * n + len(self.scalars), np.nan)
        reg = np.full(self.N_REGRESSORS, np.nan)
        if f.throttle is None or f.alt is None or f.oat is None:
            self.last_t = None
            return out, reg
        core, th = self.core, self.thermal
        atm = Atmosphere.at(f.alt, oat_c=f.oat)
        tas = self.rotor.design_tas_kt if f.tas is None else f.tas
        key = (f.throttle, f.alt, f.oat, f.tas)
        if key != self._bal_key:                          # the levers rarely change between frames
            self._bal_key, self._bal_rpm = key, balance_rpm(core, self.rotor, f.throttle, atm, f.tas, self.cut_rpm)
        rpm_bal = self._bal_rpm
        reg[1] = rpm_bal / core.cfg.rated_rpm
        dt = None if self.last_t is None else f.t - self.last_t
        if dt is None or dt < 0 or dt > MAX_GAP_S:
            self._restart(f)
            dt = 0.0
        self.last_t = f.t
        pred = {"rpm": rpm_bal}
        if f.rpm is not None and f.rpm > 0:
            core._air_key = None                          # the air cache is only valid inside one plant step
            nominal_ign = core.cfg.nominal_ign_timing_btdc
            if core.combustion.spark_ignition and f.ign_cmd is not None and nominal_ign is not None:
                retard = nominal_ign - f.ign_cmd                     # measured: knock retard (+ any timing fault)
                op = core.steady_point(f.throttle, f.rpm, atm, timing_error_deg=retard)
                knock = 1.0 + max(0.0, retard) / self.ecu["knock_retard_deg_per_index"]
            else:
                op, knock, _retard = knock_controlled_point(core, self.ecu, f.throttle, f.rpm, atm)
            limiting = self.cut_rpm is not None and f.rpm >= self.cut_rpm * (1 - self.limiter_band)
            if limiting:                                  # rev limiter: fuel on for the share that holds the rpm
                n_prop = f.rpm / self.rotor.gear_ratio / 60.0
                need = self.rotor.prop_power_w(n_prop, atm.density_kg_m3, tas) + op.friction_w
                duty = min(1.0, max(0.0, need / max(op.indicated_w, 1e-9)))
                op = op.__class__(**{**op.__dict__, "mdot_fuel_kg_s": op.mdot_fuel_kg_s * duty,
                                     "indicated_w": op.indicated_w * duty, "brake_w": need - op.friction_w,
                                     "cyl_fuel_kg_s": [x * duty for x in op.cyl_fuel_kg_s],
                                     "cyl_indicated_w": [x * duty for x in op.cyl_indicated_w]})
            h = core.heat_inputs(op, atm, th.friction_multiplier)
            health = {"wall_heat_factor": 1.0 + self.knock_wall_gain * max(0.0, knock - 1.0)}
            steps = int(np.ceil(dt / MAX_STEP_S)) if dt > 0 else 0
            for _ in range(steps):
                th.step(dt / steps, h, atm, tas, health)
            reg[0] = op.brake_w / W_PER_KW / max(core.cfg.rated_power_kw, 1e-9)
            reg[2] = op.mdot_fuel_kg_s / max(self.fuel_rated_kg_s, 1e-12)
            reg[3] = op.map_pa / atm.pressure_pa
            out[:n] = th.cht
            pred.update(map_kpa=op.map_pa / PA_PER_KPA, oil_t=th.oil_c, coolant_t=th.coolant_c, gearbox_t=th.gearbox_c)
            if limiting:                                  # the cut cycle is faster than the frame: no evidence
                pred.pop("rpm")
            else:
                out[n:2 * n] = th.egt
                pred["fuel_flow"] = op.mdot_fuel_kg_s * KG_S_TO_KG_H
            if f.oil_t is not None:
                pred["oil_p"] = th.oil_pressure_bar(f.rpm, f.oil_t)
        else:
            self.last_t = None                            # engine not turning: the next frame starts over
        running = f.rpm is not None and f.rpm > 0
        for k, name in enumerate(self.scalars):
            if name in pred:
                out[2 * n + k] = pred[name]
            elif running and name not in MODELED:
                out[2 * n + k] = 0.0                     # no model term: the tail regression predicts it alone
        return out, reg

    def snapshot(self) -> tuple:
        th = self.thermal
        return (self.last_t, self._bal_key, self._bal_rpm, list(th.cht), list(th.egt), th.coolant_c, th.oil_c,
                th.gearbox_c, th.oil_bar, th.friction_multiplier)

    def restore(self, s: tuple) -> None:
        th = self.thermal
        (self.last_t, self._bal_key, self._bal_rpm, th.cht, th.egt, th.coolant_c, th.oil_c, th.gearbox_c, th.oil_bar,
         th.friction_multiplier) = s

    def channels(self) -> List[str]:
        return [f"cht_{i + 1}" for i in range(self.n_cyl)] + [f"egt_{i + 1}" for i in range(self.n_cyl)] + list(self.scalars)
