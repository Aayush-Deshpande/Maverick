"""
Turbocharger / boosted induction model — F32.

MALE means medium *altitude*. A naturally aspirated engine cannot hold power at
20,000-28,000 ft, so every MALE-class piston UAV — MQ-1 Predator, IAI Heron,
Hermes 900, TAPAS — flies a boosted engine. The twin had no induction subsystem
at all, which meant altitude was a number that scaled a formula rather than a
physical constraint with its own failure modes.

What this adds:

  * Boost control to a target manifold pressure, with a wastegate that runs out
    of authority above the critical altitude — the defining behaviour of the
    Rotax 914's TCU and the reason "critical altitude" is a spec number at all.
  * First-order turbo lag, so a throttle step produces a transient rather than
    an instant jump (the twin's controls previously had no dynamics).
  * Compressor surge margin, which shrinks at high pressure ratio and low
    corrected flow — i.e. exactly during a high-altitude throttle chop.
  * Intercooler effectiveness, giving charge temperature, which feeds CHT.

Fault modes exposed for injection (F44): wastegate stuck open/closed, boost
leak, turbo bearing wear (efficiency decay), overspeed, intercooler fouling.

Every state here is observable from channels a real ECU already publishes
(manifold pressure, charge temperature, ambient pressure), so nothing in this
model requires instrumentation the aircraft would not have.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .engine_config import TurbochargerSpec

__all__ = ["TurboState", "TurbochargerModel", "isa_ambient"]

# Standard atmosphere constants
_P0_KPA = 101.325
_T0_K = 288.15
_LAPSE_K_PER_M = 0.0065
_G = 9.80665
_R = 287.05
_FT_TO_M = 0.3048
_GAMMA = 1.4
_CP = 1005.0  # J/kg/K


def isa_ambient(altitude_ft: float, isa_deviation_c: float = 0.0) -> tuple[float, float]:
    """ISA ambient pressure (kPa) and temperature (K) at a pressure altitude."""
    h = altitude_ft * _FT_TO_M
    if h < 11000.0:
        t = _T0_K - _LAPSE_K_PER_M * h
        p = _P0_KPA * (t / _T0_K) ** (_G / (_LAPSE_K_PER_M * _R))
    else:
        t11 = _T0_K - _LAPSE_K_PER_M * 11000.0
        p11 = _P0_KPA * (t11 / _T0_K) ** (_G / (_LAPSE_K_PER_M * _R))
        t = t11
        p = p11 * math.exp(-_G * (h - 11000.0) / (_R * t11))
    return p, t + isa_deviation_c


@dataclass
class TurboState:
    """Instantaneous induction state."""

    manifold_pressure_kpa: float = 101.3
    ambient_pressure_kpa: float = 101.3
    ambient_temp_k: float = 288.15
    compressor_outlet_temp_k: float = 288.15
    charge_temp_k: float = 288.15  # post-intercooler, what the cylinder sees
    pressure_ratio: float = 1.0
    shaft_rpm: float = 0.0
    wastegate_position: float = 1.0  # 1.0 = fully open (no boost), 0.0 = closed
    surge_margin: float = 1.0
    boost_authority_available: bool = True
    efficiency: float = 0.72

    def as_dict(self) -> dict:
        return {
            "MAP": round(self.manifold_pressure_kpa, 2),
            "AMBIENT_P_KPA": round(self.ambient_pressure_kpa, 2),
            "CHARGE_TEMP_C": round(self.charge_temp_k - 273.15, 2),
            "COMPRESSOR_OUT_TEMP_C": round(self.compressor_outlet_temp_k - 273.15, 2),
            "TURBO_PRESSURE_RATIO": round(self.pressure_ratio, 3),
            "TURBO_SHAFT_RPM": round(self.shaft_rpm, 0),
            "WASTEGATE_POS": round(self.wastegate_position, 3),
            "TURBO_SURGE_MARGIN": round(self.surge_margin, 3),
            "BOOST_AUTHORITY": self.boost_authority_available,
            "TURBO_EFFICIENCY": round(self.efficiency, 3),
        }


@dataclass
class TurboFaults:
    """Injected degradation. All default to healthy."""

    wastegate_stuck_position: Optional[float] = None  # freeze WG at this position
    boost_leak_fraction: float = 0.0  # 0..1 of boost pressure lost
    bearing_wear: float = 0.0  # 0..1, reduces achievable efficiency & speed
    intercooler_fouling: float = 0.0  # 0..1, reduces effectiveness


class TurbochargerModel:
    """Boost control with lag, surge margin and altitude authority limits."""

    def __init__(
        self,
        spec: TurbochargerSpec,
        intercooler_effectiveness: float = 0.65,
        base_efficiency: float = 0.72,
    ) -> None:
        self.spec = spec
        self.intercooler_effectiveness = intercooler_effectiveness if spec.intercooled else 0.0
        self.base_efficiency = base_efficiency
        self.faults = TurboFaults()
        self._map_state: Optional[float] = None  # lagged manifold pressure

    # -- internals ----------------------------------------------------------

    def _target_map(self, throttle_frac: float, ambient_kpa: float) -> float:
        """Commanded manifold pressure before lag and before authority limits."""
        # Below full throttle the butterfly is the restriction, so target rides
        # between ambient-limited NA behaviour and the boost ceiling.
        na_map = ambient_kpa * (0.18 + 0.82 * throttle_frac)
        boosted = self.spec.max_boost_kpa * (0.18 + 0.82 * throttle_frac)
        return max(na_map, min(boosted, self.spec.max_boost_kpa))

    def _authority_limited_map(self, target_kpa: float, ambient_kpa: float,
                               altitude_ft: float) -> tuple[float, bool]:
        """Apply the compressor's finite pressure ratio at altitude.

        Above the critical altitude the wastegate is already fully closed and
        the achievable manifold pressure falls with ambient — which is the
        physical meaning of "critical altitude" and the behaviour that makes a
        high-altitude power check meaningful.
        """
        crit_p, _ = isa_ambient(self.spec.critical_altitude_ft)
        max_pr = self.spec.max_boost_kpa / max(crit_p, 1e-3)
        achievable = ambient_kpa * max_pr
        eff_max_speed = self.spec.max_shaft_rpm * (1.0 - 0.35 * self.faults.bearing_wear)
        if eff_max_speed < self.spec.max_shaft_rpm:
            achievable *= (eff_max_speed / self.spec.max_shaft_rpm) ** 0.5
        if achievable < target_kpa:
            return achievable, False
        return target_kpa, True

    # -- public -------------------------------------------------------------

    def update(
        self,
        dt_sec: float,
        throttle_pct: float,
        altitude_ft: float,
        engine_rpm: float,
        isa_deviation_c: float = 0.0,
    ) -> TurboState:
        """Advance the induction state by one timestep."""
        throttle = max(0.0, min(1.0, throttle_pct / 100.0))
        amb_p, amb_t = isa_ambient(altitude_ft, isa_deviation_c)

        target = self._target_map(throttle, amb_p)
        target, authority = self._authority_limited_map(target, amb_p, altitude_ft)

        # Wastegate: fraction of available boost being dumped.
        if target > amb_p:
            wg = 1.0 - min(1.0, (target - amb_p) / max(self.spec.max_boost_kpa - amb_p, 1e-3))
        else:
            wg = 1.0
        if self.faults.wastegate_stuck_position is not None:
            wg = self.faults.wastegate_stuck_position
            # A stuck-closed gate overboosts; a stuck-open one cannot boost at all.
            span = max(self.spec.max_boost_kpa - amb_p, 0.0)
            target = amb_p + span * (1.0 - wg)

        if self.faults.boost_leak_fraction > 0 and target > amb_p:
            target = amb_p + (target - amb_p) * (1.0 - self.faults.boost_leak_fraction)

        # First-order lag — a throttle step must produce a transient.
        tau = max(self.spec.lag_time_constant_sec, 1e-3)
        if self._map_state is None:
            self._map_state = target
        else:
            alpha = 1.0 - math.exp(-max(dt_sec, 0.0) / tau)
            self._map_state += (target - self._map_state) * alpha
        map_kpa = self._map_state

        pr = max(1.0, map_kpa / max(amb_p, 1e-3))
        efficiency = self.base_efficiency * (1.0 - 0.30 * self.faults.bearing_wear)
        efficiency = max(0.25, efficiency)

        # Compressor outlet temperature from the isentropic relation, derated
        # by efficiency — this is what makes a boosted engine run hotter.
        t_rise_ideal = amb_t * (pr ** ((_GAMMA - 1.0) / _GAMMA) - 1.0)
        t_out = amb_t + t_rise_ideal / efficiency

        # Intercooler
        eff_ic = self.intercooler_effectiveness * (1.0 - self.faults.intercooler_fouling)
        charge_t = t_out - eff_ic * (t_out - amb_t)

        # Shaft speed scales roughly with corrected pressure rise.
        shaft = self.spec.max_shaft_rpm * min(1.2, (pr - 1.0) / max(
            (self.spec.max_boost_kpa / _P0_KPA) - 1.0, 1e-3))
        shaft = max(0.0, shaft)

        # Surge margin collapses at high PR with low flow (low RPM = low demand).
        flow_proxy = max(engine_rpm, 1.0) / 5800.0
        surge_margin = 1.0 - (pr - 1.0) * 0.55 / max(flow_proxy, 0.15)
        surge_margin = max(-1.0, min(1.0, surge_margin))

        return TurboState(
            manifold_pressure_kpa=map_kpa,
            ambient_pressure_kpa=amb_p,
            ambient_temp_k=amb_t,
            compressor_outlet_temp_k=t_out,
            charge_temp_k=charge_t,
            pressure_ratio=pr,
            shaft_rpm=shaft,
            wastegate_position=wg,
            surge_margin=surge_margin,
            boost_authority_available=authority,
            efficiency=efficiency,
        )

    def reset(self) -> None:
        self._map_state = None

    # -- fault injection ----------------------------------------------------

    def inject_fault(self, name: str, severity: float = 1.0) -> None:
        """Faults act on physical parameters, never on the output signal."""
        s = max(0.0, min(1.0, severity))
        if name == "WASTEGATE_STUCK_CLOSED":
            self.faults.wastegate_stuck_position = 0.0
        elif name == "WASTEGATE_STUCK_OPEN":
            self.faults.wastegate_stuck_position = 1.0
        elif name == "BOOST_LEAK":
            self.faults.boost_leak_fraction = 0.45 * s
        elif name == "TURBO_BEARING_WEAR":
            self.faults.bearing_wear = s
        elif name == "INTERCOOLER_FOULING":
            self.faults.intercooler_fouling = s
        else:
            raise ValueError(f"unknown turbo fault {name!r}")

    def clear_faults(self) -> None:
        self.faults = TurboFaults()

    def is_overspeed(self, state: TurboState) -> bool:
        return state.shaft_rpm > self.spec.max_shaft_rpm

    def is_surging(self, state: TurboState) -> bool:
        return state.surge_margin < self.spec.surge_margin_min
