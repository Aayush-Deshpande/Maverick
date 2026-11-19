"""Crankshaft + gearbox + propeller torque balance with a constant-speed governor (card M1-03, R 21.4, P 1.3b).

  J * domega/dt = Q_engine - Q_prop / G
  P_prop = Cp * rho * n^3 * D^5,  n = propeller rev/s,  J_adv = V / (n D)
  Cp = cp_scale * pitch * max(0, 1 - J_adv / J0)          (generic curve, JSBSim FGPropeller form)
Fixed pitch: pitch = 1. Constant speed: a PI governor moves pitch between its stops to hold the rpm setpoint.
cp_scale is calibrated so the propeller absorbs the engine's take-off power at its rated propeller speed at sea level
and the design airspeed (CALIBRATED), so only the installation data in configs/installations is ASSUMED.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from backend.sim.atmosphere import Atmosphere

ROOT = Path(__file__).resolve().parents[2]
KT_TO_MS = 0.514444
RHO_SEA_LEVEL = 1.225          # kg/m3, ISA sea level (calibration reference)


def load_propellers() -> Dict[str, Any]:
    return json.loads((ROOT / "configs" / "installations" / "propellers.json").read_text(encoding="utf-8"))["types"]


def _v(block: Dict[str, Any], key: str) -> float:
    return float(block[key]["value"])


@dataclass
class Rotor:
    gear_ratio: float
    diameter_m: float
    j0: float
    inertia: float
    design_tas_kt: float
    rpm_setpoint: float                      # engine rpm the governor holds (constant speed) / calibration rpm
    governed: bool
    cp_scale: float = 0.0
    pitch: float = 1.0
    pitch_ref: float = 1.0                   # pitch the governor works around (calibration pitch)
    pitch_min: float = 1.0
    pitch_max: float = 1.0
    kp: float = 0.0
    ki: float = 0.0
    omega: float = 0.0                       # engine crankshaft rad/s
    _integral: float = field(default=0.0, repr=False)
    last_prop_power_w: float = 0.0

    @classmethod
    def for_engine(cls, cfg: Any, propellers: Optional[Dict[str, Any]] = None) -> "Rotor":
        props = propellers or load_propellers()
        governed = bool(cfg.propeller_governor)
        p = props["CONSTANT_SPEED" if governed else "FIXED_PITCH"]
        r = cls(gear_ratio=float(cfg.gearbox_ratio), diameter_m=_v(p, "diameter_m"), j0=_v(p, "j_zero_thrust"),
                inertia=_v(p, "rotating_inertia_kg_m2"), design_tas_kt=_v(p, "design_tas_kt"),
                rpm_setpoint=float(cfg.rated_rpm), governed=governed)
        pitch_ref = 1.0
        if governed:
            pitch_ref = _v(p, "pitch_reference")
            r.pitch_min, r.pitch_max = _v(p, "pitch_min"), _v(p, "pitch_max")
            r.kp, r.ki = _v(p, "governor_kp"), _v(p, "governor_ki")
        r.pitch = r.pitch_ref = pitch_ref
        r.calibrate(cfg.rated_power_kw * 1000.0, pitch_ref)
        r.omega = cfg.rated_rpm * 2 * math.pi / 60
        return r

    # -- propeller -----------------------------------------------------------------------------------------
    def _shape(self, n_rev_s: float, tas_kt: float) -> float:
        if n_rev_s <= 0:
            return 0.0
        j = tas_kt * KT_TO_MS / (n_rev_s * self.diameter_m)
        return max(0.0, 1.0 - j / self.j0)

    def calibrate(self, rated_power_w: float, pitch_ref: float) -> None:
        n = self.rpm_setpoint / self.gear_ratio / 60.0
        self.cp_scale = rated_power_w / (RHO_SEA_LEVEL * n ** 3 * self.diameter_m ** 5 *
                                         self._shape(n, self.design_tas_kt) * pitch_ref)

    def prop_power_w(self, n_rev_s: float, rho: float, tas_kt: float) -> float:
        cp = self.cp_scale * self.pitch * self._shape(n_rev_s, tas_kt)
        return cp * rho * n_rev_s ** 3 * self.diameter_m ** 5

    # -- dynamics ------------------------------------------------------------------------------------------
    @property
    def engine_rpm(self) -> float:
        return self.omega * 60 / (2 * math.pi)

    @property
    def prop_rpm(self) -> float:
        return self.engine_rpm / self.gear_ratio

    def step(self, dt: float, engine_torque_nm: float, atm: Atmosphere, tas_kt: Optional[float] = None,
             accessory_torque_nm: float = 0.0) -> None:
        tas = self.design_tas_kt if tas_kt is None else tas_kt
        n = max(self.omega, 0.0) / (2 * math.pi) / self.gear_ratio
        p_prop = self.prop_power_w(n, atm.density_kg_m3, tas)
        q_prop_engine_side = p_prop / max(self.omega, 1e-6) if self.omega > 0 else 0.0
        self.omega = max(0.0, self.omega + dt * (engine_torque_nm - q_prop_engine_side - accessory_torque_nm) / self.inertia)
        self.last_prop_power_w = p_prop
        if self.governed:
            err = (self.engine_rpm - self.rpm_setpoint) / self.rpm_setpoint      # >0: overspeed -> coarser pitch
            self._integral += err * dt
            target = self.pitch_ref + self.kp * err + self.ki * self._integral
            self.pitch = min(self.pitch_max, max(self.pitch_min, target))
            if self.pitch != target:                                               # anti-windup at the stops
                self._integral -= err * dt
