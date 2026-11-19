"""Turbocharger + boost control + intercooler, quasi-steady with spool lag (card M1-10, R 21.4, P 1.3j).

Boost control (TCU wastegate or VGT) holds the charge pressure that gives the configured MAP target at wide-open
throttle. What the turbo can deliver is limited by its maximum shaft speed: on the top speed line the available
pressure ratio falls as corrected mass flow rises,
  PR_max(m_corr) = a - b * m_corr,     m_corr = mdot * sqrt(T_in / T_ref) / (p_in / p_ref)
so the critical altitude EMERGES (wastegate fully closed and MAP still falling). The line is CALIBRATED flat (b = 0)
from the documented critical altitude of the turbo's own capability. Where the manufacturer documents a LOWER
take-off critical altitude (Rotax 914: take-off power to 8,000 ft at 1350 hPa, continuous to 16,000 ft at 1200 hPa),
that limit is the boost controller's: the TCU caps the take-off pressure ratio (takeoff_pr_limit, CALIBRATED), since a
single compressor speed line cannot give more pressure ratio at the higher corrected flow of the 16,000 ft point.
Faults act on parameters: boost leak (F14) loses a share of the boost and the controller compensates until PR_max;
wastegate/VGT stuck open (F15) leaves no boost; stuck closed (F16) delivers PR_max (overboost); bearing wear (F17)
cuts the PR margin and slows the spool; intercooler fouling (F18) cuts its effectiveness.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.sim.atmosphere import Atmosphere, P0_PA, T0_K
from backend.sim.params import physics_values

GAMMA_AIR = 1.4


@dataclass
class Turbo:
    target_pa: float                    # charge pressure upstream of the throttle the controller holds
    lag_s: float
    intercooled: bool
    eta_c: float
    ic_eff: float
    no_boost_pr: float
    bearing_pr_loss: float
    bearing_lag_gain: float
    pr_a: float = 2.0
    pr_b: float = 0.0
    takeoff_pr_limit: Optional[float] = None    # TCU take-off pressure-ratio cap (documented lower take-off alt)
    p_charge: float = P0_PA
    t_charge_k: float = T0_K
    pressure_ratio: float = 1.0
    compressor_pa: float = P0_PA        # compressor outlet before any leak (sets the shaft speed)

    @classmethod
    def for_engine(cls, cfg: Any, wot_map_ratio: float) -> Optional["Turbo"]:
        t = cfg.turbo
        if t is None:
            return None
        ph = physics_values(cfg.engine_id, "turbo")
        map_target = (t.map_takeoff_max_kpa or t.max_boost_kpa) * 1000.0
        return cls(target_pa=map_target / wot_map_ratio, lag_s=float(t.lag_time_constant_sec),
                   intercooled=bool(t.intercooled), eta_c=ph["compressor_efficiency"],
                   ic_eff=ph["intercooler_effectiveness"], no_boost_pr=ph["no_boost_pressure_ratio"],
                   bearing_pr_loss=ph["bearing_pr_loss"], bearing_lag_gain=ph["bearing_lag_gain"])

    @staticmethod
    def corrected_flow(mdot: float, atm: Atmosphere) -> float:
        return mdot * math.sqrt(atm.temperature_k / T0_K) / (atm.pressure_pa / P0_PA)

    def calibrate_line(self, points) -> None:
        """points: [(m_corr, pr_max)] from documented critical altitudes (1 or 2 points)."""
        if len(points) >= 2:
            (m1, p1), (m2, p2) = points[:2]
            self.pr_b = (p1 - p2) / (m2 - m1) if m2 != m1 else 0.0
            self.pr_a = p1 + self.pr_b * m1
        else:
            self.pr_a, self.pr_b = points[0][1], 0.0

    def pr_max(self, m_corr: float, bearing_wear: float = 0.0) -> float:
        pr = max(1.0, self.pr_a - self.pr_b * m_corr)
        return 1.0 + (pr - 1.0) * (1.0 - self.bearing_pr_loss * bearing_wear)

    def steady_charge(self, atm: Atmosphere, mdot: float, target_pa: Optional[float] = None,
                      health: Optional[Dict[str, Any]] = None) -> float:
        """Charge pressure the controller reaches at steady state."""
        hl = health or {}
        target = self.target_pa if target_pa is None else target_pa
        if target_pa is None and self.takeoff_pr_limit is not None:
            target = min(target, atm.pressure_pa * self.takeoff_pr_limit)
        limit = atm.pressure_pa * self.pr_max(self.corrected_flow(mdot, atm), hl.get("bearing_wear", 0.0))
        if hl.get("wastegate_stuck") == "OPEN":
            self.compressor_pa = atm.pressure_pa * self.no_boost_pr
            return self.compressor_pa
        if hl.get("wastegate_stuck") == "CLOSED":
            self.compressor_pa = limit
            return limit
        leak = hl.get("boost_leak", 0.0)
        # a leak loses that share of the boost; the controller asks for more until the speed limit
        needed = atm.pressure_pa + (target - atm.pressure_pa) / max(1e-6, 1.0 - leak)
        delivered_before_leak = min(needed, limit)
        self.compressor_pa = delivered_before_leak
        return atm.pressure_pa + (delivered_before_leak - atm.pressure_pa) * (1.0 - leak)

    def charge_temperature_k(self, atm: Atmosphere, p_charge: float, ic_fouling: float = 0.0) -> float:
        pr = max(p_charge / atm.pressure_pa, 1.0)
        t2 = atm.temperature_k * (1.0 + (pr ** ((GAMMA_AIR - 1) / GAMMA_AIR) - 1.0) / self.eta_c)
        if not self.intercooled:
            return t2
        eff = self.ic_eff * (1.0 - ic_fouling)
        return t2 - eff * (t2 - atm.temperature_k)

    def step(self, dt: float, atm: Atmosphere, mdot: float, health: Optional[Dict[str, Any]] = None) -> float:
        hl = health or {}
        target = self.steady_charge(atm, mdot, health=hl)
        tau = self.lag_s * (1.0 + (self.bearing_lag_gain - 1.0) * hl.get("bearing_wear", 0.0))
        self.p_charge = target + (self.p_charge - target) * math.exp(-dt / tau)
        self.pressure_ratio = self.p_charge / atm.pressure_pa
        self.t_charge_k = self.charge_temperature_k(atm, self.p_charge, hl.get("intercooler_fouling", 0.0))
        return self.p_charge
