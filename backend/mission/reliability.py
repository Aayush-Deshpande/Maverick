"""
Mission reliability — F56.

The problem statement is titled "... Health Monitoring, Fault Prediction and
**Mission Reliability Enhancement**". Every implementation in this field, ours
included, has answered the first two and replaced the third with a go/no-go
heuristic — a coloured badge derived from a health-index threshold.

Mission reliability is not a badge. It is a defined, computable quantity:

    R = P(the planned sortie completes without a propulsion-induced abort
          | current component health, planned profile, forecast environment)

This module computes it by Monte Carlo over per-component hazard models, phase
by phase, and reports it with a confidence interval and a **limiting component**
— the part actually driving the risk, which is what a mission commander can act
on.

Why hazard rates rather than "health index < 0.4 => no-go"
----------------------------------------------------------
A health index is dimensionless and its threshold is arbitrary. A hazard rate
has units (failures per hour) and composes correctly: risk accumulates with
exposure, so an 18-hour ISR sortie is genuinely riskier than a 2-hour transit at
identical engine health, and a high-power climb is riskier per minute than a
loiter. A threshold on a health index cannot express either fact.

The base hazard rates below are the weakest part of this module and are labelled
as such. They should come from fleet reliability data (MTBF/MTBUR per component)
or from the FMECA criticality analysis. Until they do, the *ranking* of limiting
components and the *relative* effect of derating are defensible; the absolute
probability is not.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

__all__ = [
    "MissionPhase",
    "MissionProfile",
    "ComponentHazard",
    "MissionReliabilityEngine",
    "DEFAULT_COMPONENTS",
    "ISR_18H_PROFILE",
    "FAULT_COMPONENT_IMPACT",
    "components_for_fault",
]


# ---------------------------------------------------------------------------
# Fault -> damaged component attribution
# ---------------------------------------------------------------------------
# Which components a given plant fault mode actually degrades. Without this, the only
# damage ever applied was to cylinder heads, so `limiting_component` reported whichever
# component happened to carry the highest base hazard rate no matter what had failed --
# a confirmed misfire still blamed the fuel pump.
#
# `{cyl}` is substituted with the 1-based cylinder index when the fault is localised to
# one. Attribution follows the fault's physical path, not its symptom: a stuck sensor
# degrades an ECU lane (deliberately not mission-critical), not the engine.
FAULT_COMPONENT_IMPACT: Dict[str, Tuple[str, ...]] = {
    "MISFIRE": ("cylinder_head_{cyl}", "injector_{cyl}", "ecu_lane_a"),
    "COOLING_DEGRADATION": ("cylinder_head_1", "cylinder_head_2",
                            "cylinder_head_3", "cylinder_head_4"),
    "OIL_PRESSURE_LOSS": ("oil_pump", "main_bearings"),
    "AIR_FILTER_BLOCKAGE": ("air_filter", "turbocharger"),
    "BOOST_LEAK": ("turbocharger",),
    "WASTEGATE_STUCK_OPEN": ("turbocharger",),
    "TURBO_BEARING_WEAR": ("turbocharger", "main_bearings"),
    "GEARBOX_VIBRATION": ("reduction_gearbox", "main_bearings"),
    "ALTERNATOR_FAILURE": ("alternator",),
    "SENSOR_STUCK": ("ecu_lane_a",),
    "SENSOR_BIAS_DRIFT": ("ecu_lane_a",),
}


Z95 = 1.96                                       # two-sided 95 % normal quantile


def components_for_fault(mode: str, cylinder: Optional[int] = None) -> Tuple[str, ...]:
    """Resolve a fault mode to the component names it degrades.

    Matching is substring-based so registry variants (`MISFIRE_CYL2`,
    `COOLING_DEGRADATION_L2`) resolve to the same physical impact as their base mode.
    Returns an empty tuple for an unmapped mode, which leaves reliability untouched
    rather than inventing an attribution.
    """
    upper = (mode or "").upper()
    for key, comps in FAULT_COMPONENT_IMPACT.items():
        if key in upper:
            return tuple(c.format(cyl=cylinder or 1) for c in comps)
    return ()


# ---------------------------------------------------------------------------
# Mission definition
# ---------------------------------------------------------------------------


@dataclass
class MissionPhase:
    """One segment of a planned sortie."""

    name: str
    duration_hours: float
    altitude_ft: float = 20000.0
    power_fraction: float = 0.70  # of max continuous
    oat_c: float = -20.0
    dust_mg_m3: float = 0.15
    over_water: bool = False

    @property
    def stress_factor(self) -> float:
        """Multiplier on base hazard for the conditions in this phase.

        Power dominates (hazard is strongly superlinear in load), with altitude
        and heat contributing through reduced cooling margin and sustained high
        turbo pressure ratio.
        """
        power = max(0.05, self.power_fraction)
        s = power ** 2.2
        s *= 1.0 + 0.35 * max(0.0, (self.altitude_ft - 16000.0) / 10000.0)
        s *= 1.0 + 0.30 * max(0.0, (self.oat_c + 10.0) / 45.0)
        s *= 1.0 + 0.25 * min(2.0, self.dust_mg_m3 / 6.0)
        return s


@dataclass
class MissionProfile:
    name: str
    phases: List[MissionPhase] = field(default_factory=list)

    @property
    def total_hours(self) -> float:
        return sum(p.duration_hours for p in self.phases)

    def truncated_to(self, hours: float) -> "MissionProfile":
        """The same profile flown only up to `hours` — used for re-planning."""
        out: List[MissionPhase] = []
        remaining = hours
        for p in self.phases:
            if remaining <= 0:
                break
            take = min(p.duration_hours, remaining)
            out.append(MissionPhase(p.name, take, p.altitude_ft, p.power_fraction,
                                    p.oat_c, p.dust_mg_m3, p.over_water))
            remaining -= take
        return MissionProfile(f"{self.name} (truncated {hours:.1f}h)", out)

    def derated(self, power_scale: float) -> "MissionProfile":
        """The same profile at reduced power — the prescriptive lever (F57)."""
        return MissionProfile(
            f"{self.name} @ {power_scale:.0%} power",
            [MissionPhase(p.name, p.duration_hours, p.altitude_ft,
                          p.power_fraction * power_scale, p.oat_c,
                          p.dust_mg_m3, p.over_water) for p in self.phases],
        )


# An 18-hour ISR sortie at 28,000 ft — the TAPAS BH-201 demonstrated envelope.
ISR_18H_PROFILE = MissionProfile(
    name="ISR 18h @ 28000ft",
    phases=[
        MissionPhase("TAKEOFF", 0.1, 1500, 1.00, 35.0, 6.0),
        MissionPhase("CLIMB", 1.2, 15000, 0.92, 5.0, 1.2),
        MissionPhase("TRANSIT", 2.0, 24000, 0.78, -25.0, 0.15),
        MissionPhase("LOITER", 12.5, 28000, 0.62, -40.0, 0.05),
        MissionPhase("RETURN_TRANSIT", 1.6, 22000, 0.75, -20.0, 0.15),
        MissionPhase("DESCENT", 0.5, 8000, 0.35, 10.0, 0.5),
        MissionPhase("LANDING", 0.1, 1500, 0.55, 35.0, 6.0),
    ],
)


# ---------------------------------------------------------------------------
# Component hazard model
# ---------------------------------------------------------------------------


@dataclass
class ComponentHazard:
    """Failure hazard for one component, conditioned on its damage state.

    `base_hazard_per_hour` is the healthy-component rate. `damage_exponent`
    controls how sharply hazard rises as accumulated damage approaches 1.0 — a
    wear-out mechanism has a high exponent, a random-failure mechanism (an
    electrical connector, say) has one close to zero.
    """

    name: str
    base_hazard_per_hour: float
    damage_fraction: float = 0.0  # 0 = new, 1 = life consumed (from F36)
    damage_exponent: float = 3.0
    mission_critical: bool = True  # False = degrades capability, not a hard abort
    source: str = "PLACEHOLDER — not from fleet reliability data"

    def hazard(self, stress_factor: float = 1.0) -> float:
        """Instantaneous hazard, failures per hour, under the given stress."""
        d = min(max(self.damage_fraction, 0.0), 0.999)
        wear_multiplier = 1.0 / ((1.0 - d) ** self.damage_exponent)
        return self.base_hazard_per_hour * wear_multiplier * max(0.0, stress_factor)

    def survival(self, hours: float, stress_factor: float = 1.0) -> float:
        return math.exp(-self.hazard(stress_factor) * max(0.0, hours))


def DEFAULT_COMPONENTS() -> List[ComponentHazard]:
    """A starting component set for a turbocharged piston UAV powerplant.

    Rates are order-of-magnitude placeholders chosen so a healthy engine
    completes an 18-hour sortie with high probability. They MUST be replaced
    from fleet MTBUR data or FMECA criticality before any absolute number is
    quoted; see the module docstring.
    """
    return [
        ComponentHazard("cylinder_head_1", 2.0e-5, damage_exponent=3.5),
        ComponentHazard("cylinder_head_2", 2.0e-5, damage_exponent=3.5),
        ComponentHazard("cylinder_head_3", 2.0e-5, damage_exponent=3.5),
        ComponentHazard("cylinder_head_4", 2.0e-5, damage_exponent=3.5),
        ComponentHazard("turbocharger", 6.0e-5, damage_exponent=3.0),
        ComponentHazard("injector_1", 3.0e-5, damage_exponent=2.5),
        ComponentHazard("injector_2", 3.0e-5, damage_exponent=2.5),
        ComponentHazard("injector_3", 3.0e-5, damage_exponent=2.5),
        ComponentHazard("injector_4", 3.0e-5, damage_exponent=2.5),
        ComponentHazard("fuel_pump", 4.0e-5, damage_exponent=2.0),
        ComponentHazard("oil_pump", 2.5e-5, damage_exponent=2.5),
        ComponentHazard("main_bearings", 1.5e-5, damage_exponent=4.0),
        ComponentHazard("reduction_gearbox", 3.0e-5, damage_exponent=3.5),
        ComponentHazard("alternator", 8.0e-5, damage_exponent=1.5, mission_critical=False),
        ComponentHazard("ecu_lane_a", 5.0e-5, damage_exponent=0.5, mission_critical=False),
        ComponentHazard("air_filter", 1.0e-5, damage_exponent=2.0, mission_critical=False),
    ]


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------


class MissionReliabilityEngine:
    """Monte Carlo mission reliability with limiting-component attribution."""

    def __init__(self, components: Optional[List[ComponentHazard]] = None,
                 seed: Optional[int] = None) -> None:
        self.components = components if components is not None else DEFAULT_COMPONENTS()
        self._rng = random.Random(seed)
        self._np_rng = np.random.default_rng(seed)

    def set_damage(self, damage: Dict[str, float]) -> None:
        """Apply current damage fractions, e.g. from the F36 accumulator."""
        by_name = {c.name: c for c in self.components}
        for name, frac in damage.items():
            if name in by_name:
                by_name[name].damage_fraction = max(0.0, min(0.999, frac))

    # -- analytic path (fast, exact for independent components) -------------

    def analytic_reliability(self, profile: MissionProfile,
                             critical_only: bool = True) -> dict:
        """Closed form: R = prod_c exp(-sum_phases h_c * stress * dt).

        Exact under the model's own assumption that component failures are
        independent, which is why the Monte Carlo path also exists: it is where
        dependence and phase-conditional aborts can be added later without
        changing the interface.
        """
        per_component: Dict[str, float] = {}
        for c in self.components:
            if critical_only and not c.mission_critical:
                continue
            integrated = sum(c.hazard(p.stress_factor) * p.duration_hours
                             for p in profile.phases)
            per_component[c.name] = math.exp(-integrated)
        r = 1.0
        for v in per_component.values():
            r *= v
        ranked = sorted(per_component.items(), key=lambda kv: kv[1])
        return {
            "reliability": r,
            "per_component_survival": per_component,
            "limiting_component": ranked[0][0] if ranked else None,
            "limiting_component_survival": ranked[0][1] if ranked else None,
            "mission_hours": profile.total_hours,
        }

    # -- Monte Carlo path ---------------------------------------------------

    def simulate(self, profile: MissionProfile, n_trials: int = 20000,
                 critical_only: bool = True) -> dict:
        """Sample mission outcomes; returns R with a Wilson interval (vectorised path, see simulate_with_limits)."""
        return self.simulate_with_limits(profile, n_trials=n_trials, critical_only=critical_only)

    def simulate_with_limits(self, profile: MissionProfile, n_trials: int = 20000, critical_only: bool = True,
                             limit_crossings: Optional[List[dict]] = None) -> dict:
        """Sample mission outcomes; returns R with a Wilson interval (card M4-04, idea text I-09).

        Per trial, each component's time-to-failure is drawn against the phase-varying hazard by inverse transform
        of its piecewise-linear cumulative hazard (vectorised over trials). limit_crossings are the twin's
        time-to-limit predictions ({channel, time_to_limit_s, low_s, high_s}): each is a lognormal crossing time
        whose median is the prediction and whose [low, high] is its 95 % range; a crossing inside the mission
        forces an abort too. The earliest abort cause and the phase it falls in are recorded, which is what turns
        "risky sortie" into "risky during the 12.5 h loiter".
        """
        comps = [c for c in self.components if (c.mission_critical or not critical_only)]
        dur = np.array([p.duration_hours for p in profile.phases])
        ends = np.cumsum(dur)
        starts = ends - dur
        names = [c.name for c in comps]
        times = []
        for c in comps:
            h = np.array([c.hazard(p.stress_factor) for p in profile.phases])
            cum_end = np.cumsum(h * dur)
            cum_start = cum_end - h * dur
            target = self._np_rng.exponential(1.0, n_trials)
            k = np.searchsorted(cum_end, target, side="left")
            t = np.full(n_trials, np.inf)
            inside = k < len(dur)
            kk = k[inside]
            hk = h[kk]
            t[inside] = starts[kk] + np.where(hk > 0, (target[inside] - cum_start[kk]) / np.where(hk > 0, hk, 1.0), 0.0)
            times.append(t)
        for lc in limit_crossings or []:
            med = max(float(lc["time_to_limit_s"]), 1e-3) / 3600.0
            lo = max(float(lc.get("low_s") or lc["time_to_limit_s"]), 1e-3) / 3600.0
            hi = max(float(lc.get("high_s") or lc["time_to_limit_s"]), 1e-3) / 3600.0
            sig = max((math.log(max(hi, lo)) - math.log(lo)) / (2 * Z95), 1e-6)    # [low, high] = 95 % range
            times.append(np.exp(self._np_rng.normal(math.log(med), sig, n_trials)))
            names.append(f"limit:{lc['channel']}")
        T = np.vstack(times) if times else np.full((1, n_trials), np.inf)
        first = T.min(0)
        who = T.argmin(0)
        failed = first <= profile.total_hours
        successes = int(n_trials - failed.sum())
        counts: Dict[str, int] = {}
        for w in who[failed]:
            counts[names[w]] = counts.get(names[w], 0) + 1
        phase_idx = np.searchsorted(ends, first[failed], side="left")
        phases: Dict[str, int] = {}
        for k in phase_idx:
            nm = profile.phases[min(int(k), len(profile.phases) - 1)].name
            phases[nm] = phases.get(nm, 0) + 1
        r = successes / n_trials
        lo, hi = _wilson_interval(successes, n_trials)
        ranked = sorted(counts.items(), key=lambda kv: -kv[1])
        limiting = ranked[0][0] if ranked else None
        n_fail = max(n_trials - successes, 1)
        aborts = np.sort(first[failed])
        return {
            "reliability": round(r, 5),
            "ci_lower": round(lo, 5),
            "ci_upper": round(hi, 5),
            "n_trials": n_trials,
            "mission_hours": round(profile.total_hours, 2),
            "limiting_component": limiting,
            "limiting_component_share": round(ranked[0][1] / n_fail, 4) if limiting else None,
            "failure_attribution": dict(ranked),
            "failure_phase_distribution": phases,
            "median_abort_hours": round(float(aborts[len(aborts) // 2]), 2) if len(aborts) else None,
        }

    # -- decision support ---------------------------------------------------

    def assess(self, profile: MissionProfile, required_reliability: float = 0.90,
               n_trials: int = 20000) -> dict:
        """Go / no-go against a stated reliability requirement.

        The verdict is driven by the *lower* confidence bound, not the point
        estimate: committing an airframe on a number whose uncertainty straddles
        the requirement is exactly the decision this system exists to prevent.
        """
        res = self.simulate(profile, n_trials=n_trials)
        meets = res["ci_lower"] >= required_reliability
        marginal = (not meets) and res["reliability"] >= required_reliability
        res["required_reliability"] = required_reliability
        res["verdict"] = ("GO" if meets else ("MARGINAL" if marginal else "NO-GO"))
        res["rationale"] = (
            f"R = {res['reliability']:.3f} [{res['ci_lower']:.3f}-{res['ci_upper']:.3f}] "
            f"against a requirement of {required_reliability:.2f}; "
            f"limiting component: {res['limiting_component']}"
        )
        return res


def _wilson_interval(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval — behaves correctly as R approaches 1.

    The normal approximation collapses to a zero-width interval when every trial
    succeeds, which would report certainty we do not have.
    """
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(max(p * (1 - p) / n + z * z / (4 * n * n), 0.0)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))
