"""Induction: air filter -> throttle (compressible orifice) -> manifold filling -> cylinders (card M1-04, R 21.4).

  dMAP/dt = (R T_m / V_m) * (mdot_throttle - mdot_cyl)
  mdot_cyl = eta_v * MAP / (R T_m) * V_d * rpm / 120                     (4-stroke speed-density)
  mdot_throttle = Cd A(theta) p_up / sqrt(R T_up) * Psi(MAP / p_up)       (isentropic orifice, choked below p*)
  p_up = p_source - k_filter * filter_factor * mdot^2                     (F13 raises filter_factor)

The manifold is faster than the 0.05 s plant step, so each step solves the quasi-steady MAP (flow balance) and moves
toward it with the exact exponential of the linearised filling time constant: stable at any step, physical lag.
The real rpm is an input (removes the old fixed 5200 rpm, audit V5). For turbo engines p_source is the charge
pressure from backend/sim/turbo.py (M1-10); for naturally aspirated engines it is ambient pressure.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional

from backend.sim.atmosphere import R_DRY, Atmosphere
from backend.sim.params import physics_values

GAMMA_AIR = 1.4                                       # ratio of specific heats, air
P_CRIT = (2 / (GAMMA_AIR + 1)) ** (GAMMA_AIR / (GAMMA_AIR - 1))   # choked-flow pressure ratio (0.528)


def _psi(pr: float) -> float:
    pr = min(max(pr, P_CRIT), 1.0)
    g = GAMMA_AIR
    return math.sqrt(max(0.0, 2 * g / (g - 1) * (pr ** (2 / g) - pr ** ((g + 1) / g))))


def throttle_area_fraction(throttle_pct: float, idle_fraction: float) -> float:
    """Butterfly opening -> flow area fraction (cosine law), with a closed-throttle leakage floor."""
    t = min(max(throttle_pct, 0.0), 100.0) / 100.0
    return idle_fraction + (1.0 - idle_fraction) * (1.0 - math.cos(t * math.pi / 2))


@dataclass
class Induction:
    displaced_m3: float
    manifold_m3: float
    eta_v: float
    cd: float
    idle_fraction: float
    area_m2: float = 0.0
    k_filter: float = 0.0
    map_pa: float = 0.0
    mdot_air: float = 0.0

    @classmethod
    def for_engine(cls, cfg: Any) -> "Induction":
        ph = physics_values(cfg.engine_id, "induction")
        vd = cfg.layout.displacement_cc * 1e-6
        ind = cls(displaced_m3=vd, manifold_m3=ph["manifold_volume_per_displacement"] * vd,
                  eta_v=ph["volumetric_efficiency"], cd=ph["throttle_cd"], idle_fraction=ph["idle_area_fraction"])
        ind.calibrate(cfg.rated_rpm, ph["wot_map_ratio"], ph["filter_dp_kpa_at_rated_flow"] * 1000.0)
        return ind

    # -- flows ---------------------------------------------------------------------------------------------
    def cylinder_flow(self, map_pa: float, t_k: float, rpm: float) -> float:
        return self.eta_v * map_pa / (R_DRY * t_k) * self.displaced_m3 * max(rpm, 0.0) / 120.0

    def throttle_flow(self, frac: float, p_up: float, t_up: float, map_pa: float) -> float:
        if p_up <= 0 or map_pa >= p_up:
            return 0.0
        return self.cd * self.area_m2 * frac * p_up / math.sqrt(R_DRY * t_up) * _psi(map_pa / p_up)

    def calibrate(self, rated_rpm: float, wot_map_ratio: float, filter_dp_pa: float) -> None:
        """Throttle area so WOT at rated rpm (ISA SL, no filter) gives wot_map_ratio; filter k from its rated drop."""
        sl = Atmosphere.at(0)
        p_man = wot_map_ratio * sl.pressure_pa
        m = self.cylinder_flow(p_man, sl.temperature_k, rated_rpm)
        per_area = self.cd * sl.pressure_pa / math.sqrt(R_DRY * sl.temperature_k) * _psi(wot_map_ratio)
        self.area_m2 = m / per_area
        self.k_filter = filter_dp_pa / (m * m)
        self.map_pa = p_man

    # -- dynamics ------------------------------------------------------------------------------------------
    def _steady_map(self, frac: float, p_up: float, t_k: float, rpm: float) -> float:
        lo, hi = 0.0, p_up
        for _ in range(50):                                   # bisection: throttle flow falls, cylinder flow rises
            mid = 0.5 * (lo + hi)
            if self.throttle_flow(frac, p_up, t_k, mid) > self.cylinder_flow(mid, t_k, rpm):
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def step(self, dt: float, throttle_pct: float, rpm: float, atm: Atmosphere, filter_factor: float = 1.0,
             source_pressure_pa: Optional[float] = None, source_temp_k: Optional[float] = None) -> float:
        p_src = atm.pressure_pa if source_pressure_pa is None else source_pressure_pa
        t_k = atm.temperature_k if source_temp_k is None else source_temp_k
        p_up = max(1.0, p_src - self.k_filter * filter_factor * self.mdot_air ** 2)
        frac = throttle_area_fraction(throttle_pct, self.idle_fraction)
        target = self._steady_map(frac, p_up, t_k, rpm)
        swept = self.eta_v * self.displaced_m3 * max(rpm, 1.0) / 120.0          # m3/s drawn by the cylinders
        tau = self.manifold_m3 / swept
        self.map_pa = target + (self.map_pa - target) * math.exp(-dt / tau)
        self.mdot_air = self.cylinder_flow(self.map_pa, t_k, rpm)
        return self.map_pa
