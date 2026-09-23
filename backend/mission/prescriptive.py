"""
Prescriptive advisory and mission re-planning — F57 / F58.

Predictive maintenance tells an operator what will fail. Prescriptive
maintenance tells them what to *do about it now*, on this sortie. The published
result this is built on is that progressively derating load to hold a constant
damage rate extends useful life substantially versus reactive control — the
lever exists and is well evidenced; what has been missing here is the
accounting that makes it actionable on a specific mission.

Three outputs, in ascending order of usefulness to the operator:

  1. "Mission reliability for the planned sortie is 0.87 [0.81-0.92].
      Limiting component: cylinder 2 injector."                       (F56)
  2. "Derate to 85 % power: damage rate -40 %, reliability 0.87 -> 0.95,
      endurance penalty 22 min."                                      (F57)
  3. "This sortie is not achievable as planned. Achievable: 14 h at
      22,000 ft at reliability 0.93."                                 (F58)

The third is the one that changes a mission. It is a search over the profile
space — reduce power, reduce altitude, shorten the loiter — for the closest
plan that meets the required reliability, which is how "prognostics driven
decision making" is framed in the literature: an optimisation that reduces use
of the impaired component.

Nothing here commands the aircraft. Every output is an advisory for a human,
which is deliberate: an advisory-only system sits at a far lower design
assurance level than one that closes a control loop, and that distinction is
the difference between a system that could be fielded and one that could not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .reliability import MissionProfile, MissionReliabilityEngine

__all__ = ["DerateOption", "PrescriptiveAdvisor", "ReplanResult"]


@dataclass
class DerateOption:
    """One candidate power setting and everything it costs or buys."""

    power_scale: float
    reliability: float
    ci_lower: float
    ci_upper: float
    delta_reliability: float
    damage_rate_ratio: float  # relative to the baseline plan
    endurance_penalty_min: float
    limiting_component: Optional[str]
    meets_requirement: bool

    def as_dict(self) -> dict:
        return {
            "power_setting_pct": round(self.power_scale * 100, 1),
            "reliability": round(self.reliability, 4),
            "ci": [round(self.ci_lower, 4), round(self.ci_upper, 4)],
            "delta_reliability": round(self.delta_reliability, 4),
            "damage_rate_vs_baseline": round(self.damage_rate_ratio, 3),
            "endurance_penalty_min": round(self.endurance_penalty_min, 1),
            "limiting_component": self.limiting_component,
            "meets_requirement": self.meets_requirement,
        }

    def sentence(self) -> str:
        direction = "reduces" if self.damage_rate_ratio < 1 else "increases"
        pct = abs(1.0 - self.damage_rate_ratio) * 100
        return (
            f"Derate to {self.power_scale:.0%} power: damage rate {direction} "
            f"{pct:.0f}%, reliability {self.reliability - self.delta_reliability:.3f} "
            f"-> {self.reliability:.3f}, endurance penalty "
            f"{self.endurance_penalty_min:.0f} min."
        )


@dataclass
class ReplanResult:
    achievable: bool
    profile: Optional[MissionProfile]
    reliability: float
    ci_lower: float
    changes: List[str] = field(default_factory=list)

    def sentence(self) -> str:
        if self.profile is None:
            return ("No variation of this sortie meets the required reliability. "
                    "Recommend aircraft substitution or maintenance before launch.")
        if not self.changes:
            return (f"Sortie achievable as planned at reliability "
                    f"{self.reliability:.3f}.")
        return (f"Sortie not achievable as planned. Achievable: "
                f"{'; '.join(self.changes)} at reliability {self.reliability:.3f} "
                f"(lower bound {self.ci_lower:.3f}).")

    def as_dict(self) -> dict:
        return {
            "achievable": self.achievable,
            "reliability": round(self.reliability, 4),
            "ci_lower": round(self.ci_lower, 4),
            "changes": self.changes,
            "profile_name": self.profile.name if self.profile else None,
            "profile_hours": round(self.profile.total_hours, 2) if self.profile else None,
            "recommendation": self.sentence(),
        }


class PrescriptiveAdvisor:
    """Turns a reliability number into a recommended action."""

    # Fuel flow scales roughly with power, so a derate extends endurance on
    # fuel but costs airspeed; for an ISR loiter the binding constraint is
    # usually time on station, so the penalty is expressed in minutes of
    # station time lost to the slower transit.
    _TRANSIT_PHASES = ("CLIMB", "TRANSIT", "RETURN_TRANSIT")

    def __init__(self, engine: MissionReliabilityEngine,
                 required_reliability: float = 0.90,
                 n_trials: int = 8000) -> None:
        self.engine = engine
        self.required = required_reliability
        self.n_trials = n_trials

    # -- F57: derate options ------------------------------------------------

    def _damage_rate(self, profile: MissionProfile) -> float:
        """Stress-hours: the integral of stress over the mission.

        This is the quantity a constant-damage-rate policy holds flat, and it
        is what makes the trade legible — the operator is buying reliability
        with stress-hours, not with an abstraction.
        """
        return sum(p.stress_factor * p.duration_hours for p in profile.phases)

    def _endurance_penalty_min(self, profile: MissionProfile, scale: float) -> float:
        """Station time lost because transit legs take longer at reduced power."""
        transit_hours = sum(p.duration_hours for p in profile.phases
                            if p.name.upper() in self._TRANSIT_PHASES)
        if scale >= 1.0 or transit_hours <= 0:
            return 0.0
        # Speed falls roughly as the cube root of power in level flight.
        speed_ratio = scale ** (1.0 / 3.0)
        extra_hours = transit_hours * (1.0 / speed_ratio - 1.0)
        return extra_hours * 60.0

    def derate_options(self, profile: MissionProfile,
                       scales: Sequence[float] = (1.0, 0.95, 0.90, 0.85, 0.80, 0.75)
                       ) -> List[DerateOption]:
        """Evaluate candidate power settings against the same mission."""
        baseline = self.engine.simulate(profile, n_trials=self.n_trials)
        base_r = baseline["reliability"]
        base_damage = self._damage_rate(profile)

        options: List[DerateOption] = []
        for scale in scales:
            p = profile if scale == 1.0 else profile.derated(scale)
            res = self.engine.simulate(p, n_trials=self.n_trials)
            options.append(DerateOption(
                power_scale=scale,
                reliability=res["reliability"],
                ci_lower=res["ci_lower"],
                ci_upper=res["ci_upper"],
                delta_reliability=res["reliability"] - base_r,
                damage_rate_ratio=(self._damage_rate(p) / base_damage
                                   if base_damage > 0 else 1.0),
                endurance_penalty_min=self._endurance_penalty_min(profile, scale),
                limiting_component=res["limiting_component"],
                meets_requirement=res["ci_lower"] >= self.required,
            ))
        return options

    def recommend_derate(self, profile: MissionProfile) -> Optional[DerateOption]:
        """The least aggressive derate that meets the requirement.

        Least aggressive rather than safest: over-derating a serviceable engine
        costs mission capability for no reliability the commander asked for.
        """
        for opt in self.derate_options(profile):
            if opt.meets_requirement:
                return opt
        return None

    # -- F58: re-planning ---------------------------------------------------

    def replan(self, profile: MissionProfile,
               min_useful_hours: float = 4.0) -> ReplanResult:
        """Find the closest achievable variation of this sortie.

        Search order matters and is deliberate: power first (cheapest to the
        mission), then altitude (costs sensor footprint), then duration (costs
        the mission outright). Each step is the next-least-damaging concession.
        """
        base = self.engine.simulate(profile, n_trials=self.n_trials)
        if base["ci_lower"] >= self.required:
            return ReplanResult(True, profile, base["reliability"], base["ci_lower"], [])

        # 1. Power only.
        opt = self.recommend_derate(profile)
        if opt is not None and opt.power_scale < 1.0:
            p = profile.derated(opt.power_scale)
            return ReplanResult(True, p, opt.reliability, opt.ci_lower,
                                [f"reduce power to {opt.power_scale:.0%}"])

        # 2. Power plus reduced cruise altitude — lowers turbo pressure ratio
        #    and restores cooling mass flow, both of which cut hazard.
        for scale in (0.90, 0.85, 0.80):
            for alt_cut in (4000.0, 6000.0, 8000.0):
                candidate = MissionProfile(
                    f"{profile.name} @ {scale:.0%} power, -{alt_cut:.0f}ft",
                    [type(ph)(ph.name, ph.duration_hours,
                              max(1500.0, ph.altitude_ft - alt_cut),
                              ph.power_fraction * scale, ph.oat_c,
                              ph.dust_mg_m3, ph.over_water)
                     for ph in profile.phases],
                )
                res = self.engine.simulate(candidate, n_trials=self.n_trials)
                if res["ci_lower"] >= self.required:
                    return ReplanResult(
                        True, candidate, res["reliability"], res["ci_lower"],
                        [f"reduce power to {scale:.0%}",
                         f"reduce cruise altitude by {alt_cut:.0f} ft"])

        # 3. Shorten the sortie. This is the concession that actually costs the
        #    mission, so it is searched last and reported explicitly.
        hours = profile.total_hours
        while hours > min_useful_hours:
            hours -= max(1.0, profile.total_hours * 0.1)
            candidate = profile.truncated_to(hours).derated(0.90)
            res = self.engine.simulate(candidate, n_trials=self.n_trials)
            if res["ci_lower"] >= self.required:
                return ReplanResult(
                    True, candidate, res["reliability"], res["ci_lower"],
                    [f"reduce power to 90%", f"shorten sortie to {hours:.1f} h"])

        return ReplanResult(False, None, base["reliability"], base["ci_lower"],
                            ["no achievable variation found"])

    # -- combined advisory --------------------------------------------------

    def advise(self, profile: MissionProfile) -> dict:
        """The full operator-facing advisory for one planned sortie."""
        assessment = self.engine.assess(profile, self.required, n_trials=self.n_trials)
        options = self.derate_options(profile)
        recommended = next((o for o in options if o.meets_requirement), None)
        replan = self.replan(profile) if recommended is None else None

        lines: List[str] = [assessment["rationale"]]
        if assessment["verdict"] == "GO":
            lines.append("Sortie may be flown as planned.")
        elif recommended is not None and recommended.power_scale < 1.0:
            lines.append(recommended.sentence())
        elif replan is not None:
            lines.append(replan.sentence())

        return {
            "assessment": assessment,
            "derate_options": [o.as_dict() for o in options],
            "recommended_derate": recommended.as_dict() if recommended else None,
            "replan": replan.as_dict() if replan else None,
            "advisory": lines,
        }
