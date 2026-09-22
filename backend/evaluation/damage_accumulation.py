"""
Physics-of-failure damage accumulation — F36 / F37.

Aerospace does not curve-fit a health index to obtain RUL; it counts damage.
This module converts a load history (cylinder metal temperature, shaft speed)
into closed fatigue cycles via ASTM E1049 rainflow counting, then accumulates
damage fractions with the Palmgren-Miner linear rule.

Two mechanisms are modelled:

  * Thermal low-cycle fatigue (LCF) on cylinder heads, driven by CHT swing.
    Cycles-to-failure from a Coffin-Manson style power law N = C * dT**(-m).
  * Shock cooling, driven by dCHT/dt. Rapid contraction of the head against a
    hotter barrel is a recognised piston-aero damage mechanism and is *not*
    captured by range counting alone, because a fast ramp and a slow ramp of
    equal amplitude close the same rainflow cycle.

The output is an auditable life-consumed fraction per component. A maintenance
authority can re-derive it from the same telemetry with a spreadsheet, which is
exactly the property a statistical RUL estimate lacks. It is also independent
of our simulator, so it survives the "you only learned your own generator"
objection that invalidates curve-fit RUL trained on synthetic degradation.

References
----------
ASTM E1049-85 (2017) "Standard Practices for Cycle Counting in Fatigue Analysis"
Palmgren-Miner linear cumulative damage hypothesis
US7243042 "Engine component life monitoring system ... remaining useful life"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence, Tuple

__all__ = [
    "Cycle",
    "extract_turning_points",
    "rainflow_cycles",
    "CoffinManson",
    "ShockCoolingLaw",
    "ComponentDamage",
    "DamageAccumulator",
]


# ---------------------------------------------------------------------------
# Rainflow counting (ASTM E1049-85)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Cycle:
    """One counted fatigue cycle."""

    range: float  # peak-to-peak amplitude, same units as the input series
    mean: float  # cycle mean level
    count: float  # 1.0 for a full cycle, 0.5 for a residual half cycle

    @property
    def amplitude(self) -> float:
        return self.range / 2.0


def extract_turning_points(series: Sequence[float]) -> List[float]:
    """Reduce a series to its alternating peaks and valleys.

    Monotonic runs carry no cycle information, so collapsing them first is both
    a correctness requirement for the rainflow stack algorithm and a large
    constant-factor saving on a 20 Hz telemetry stream.
    """
    pts: List[float] = []
    for x in series:
        x = float(x)
        if len(pts) < 2:
            # Avoid seeding the stack with a repeated value.
            if not pts or x != pts[-1]:
                pts.append(x)
            continue
        prev_slope = pts[-1] - pts[-2]
        new_slope = x - pts[-1]
        if new_slope == 0.0:
            continue
        if (prev_slope > 0) == (new_slope > 0):
            # Same direction: the previous point was not a turning point.
            pts[-1] = x
        else:
            pts.append(x)
    return pts


def rainflow_cycles(series: Sequence[float]) -> List[Cycle]:
    """Count closed cycles in a load history per ASTM E1049-85.

    Implements the three-point stack reduction: whenever the newest range is
    greater than or equal to the range before it, the inner range is a closed
    cycle and its two points are removed from the stack. Ranges that involve
    the very first point can only ever be closed once, so they are counted as
    half cycles, as are whatever points remain on the stack at the end.
    """
    points = extract_turning_points(series)
    cycles: List[Cycle] = []
    stack: List[float] = []

    for p in points:
        stack.append(p)
        while len(stack) >= 3:
            y = abs(stack[-2] - stack[-3])  # inner (older) range
            x = abs(stack[-1] - stack[-2])  # outer (newer) range
            if x < y:
                break
            mean = (stack[-2] + stack[-3]) / 2.0
            if len(stack) == 3:
                # Y contains the start of the history: half cycle, drop oldest.
                cycles.append(Cycle(range=y, mean=mean, count=0.5))
                stack.pop(0)
            else:
                cycles.append(Cycle(range=y, mean=mean, count=1.0))
                del stack[-3:-1]

    # Residual stack: every remaining range is an unclosed half cycle.
    for a, b in zip(stack[:-1], stack[1:]):
        cycles.append(Cycle(range=abs(b - a), mean=(a + b) / 2.0, count=0.5))

    return cycles


# ---------------------------------------------------------------------------
# Damage laws
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoffinManson:
    """Thermal LCF life law: N_f = C * (dT ** -m), floored at a threshold.

    Below `threshold_c` the swing is treated as non-damaging (elastic shakedown);
    without a threshold, the 20 Hz measurement noise on a CHT channel would
    otherwise accumulate spurious damage over an 18-hour sortie.

    Defaults are representative of an air-cooled aluminium cylinder head and are
    deliberately conservative. They must be replaced with values traceable to the
    engine's own LCF substantiation before any number leaves the lab; the
    `source` field exists to force that provenance to be recorded.
    """

    C: float = 1.0e9
    m: float = 2.6
    threshold_c: float = 12.0
    source: str = "placeholder — NOT traceable to engine LCF substantiation"

    def cycles_to_failure(self, delta_t_c: float) -> float:
        """Allowable cycles at a given temperature swing (inf if below threshold)."""
        if delta_t_c <= self.threshold_c:
            return float("inf")
        return self.C * (delta_t_c ** -self.m)

    def damage(self, cycle: Cycle) -> float:
        n_f = self.cycles_to_failure(cycle.range)
        if n_f == float("inf"):
            return 0.0
        return cycle.count / n_f


@dataclass(frozen=True)
class ShockCoolingLaw:
    """Damage from cooling rate, above and beyond the closed thermal cycle.

    Piston-aero practice limits CHT rate-of-change on descent (commonly quoted
    around 50 F/min, i.e. ~28 C/min). Damage is accrued per second of exceedance,
    scaled by how far past the limit the rate is.
    """

    limit_c_per_min: float = 28.0
    exponent: float = 2.0
    # Seconds at twice the limit that would consume the whole component life.
    reference_seconds: float = 3.0e5
    source: str = "placeholder — operator practice, not an OEM limit"

    def damage_rate(self, dtemp_dt_c_per_min: float) -> float:
        """Damage per second at the given (signed) cooling rate."""
        cooling = -dtemp_dt_c_per_min  # positive when temperature is falling
        if cooling <= self.limit_c_per_min:
            return 0.0
        excess = cooling / self.limit_c_per_min
        return (excess ** self.exponent) / self.reference_seconds


# ---------------------------------------------------------------------------
# Accumulator
# ---------------------------------------------------------------------------


@dataclass
class ComponentDamage:
    """Life consumed by one named component, split by mechanism."""

    name: str
    thermal_lcf: float = 0.0
    shock_cooling: float = 0.0
    counted_cycles: int = 0

    @property
    def total(self) -> float:
        return self.thermal_lcf + self.shock_cooling

    @property
    def life_remaining_fraction(self) -> float:
        return max(0.0, 1.0 - self.total)

    def as_dict(self) -> dict:
        return {
            "component": self.name,
            "damage_total": round(self.total, 9),
            "damage_thermal_lcf": round(self.thermal_lcf, 9),
            "damage_shock_cooling": round(self.shock_cooling, 9),
            "life_remaining_fraction": round(self.life_remaining_fraction, 6),
            "counted_cycles": self.counted_cycles,
        }


class DamageAccumulator:
    """Streaming damage accounting for one component's temperature channel.

    Rainflow counting is not causal — a cycle only closes when a later reversal
    proves it closed — so the temperature history is buffered and recounted.
    To keep that bounded on a long sortie, the buffer is reduced to its turning
    points on every update, which is lossless for cycle counting purposes.

    Usage:
        acc = DamageAccumulator("cylinder_2_head")
        for t, cht in stream:
            acc.update(t, cht)
        acc.state.as_dict()
    """

    def __init__(
        self,
        name: str,
        lcf_law: CoffinManson | None = None,
        shock_law: ShockCoolingLaw | None = None,
        initial_damage: float = 0.0,
    ) -> None:
        self.state = ComponentDamage(name=name, thermal_lcf=initial_damage)
        self.lcf_law = lcf_law or CoffinManson()
        self.shock_law = shock_law or ShockCoolingLaw()
        self._history: List[float] = []
        self._last_t: float | None = None
        self._last_temp: float | None = None

    def update(self, t_sec: float, temperature_c: float) -> None:
        """Feed one sample. `t_sec` must be monotonically increasing."""
        temperature_c = float(temperature_c)

        # Shock cooling is instantaneous and therefore integrated on the fly.
        if self._last_t is not None and self._last_temp is not None:
            dt = t_sec - self._last_t
            if dt > 0:
                rate = (temperature_c - self._last_temp) / dt * 60.0
                self.state.shock_cooling += self.shock_law.damage_rate(rate) * dt
        self._last_t = t_sec
        self._last_temp = temperature_c

        self._history.append(temperature_c)
        # Collapse monotonic runs so the buffer stays proportional to reversals.
        if len(self._history) > 512:
            self._history = extract_turning_points(self._history)

    def finalise(self) -> ComponentDamage:
        """Close out the history and fold its cycles into the damage state."""
        cycles = rainflow_cycles(self._history)
        for cycle in cycles:
            self.state.thermal_lcf += self.lcf_law.damage(cycle)
        self.state.counted_cycles += len(cycles)
        self._history = self._history[-1:] if self._history else []
        return self.state


def accumulate_from_series(
    name: str,
    times_sec: Sequence[float],
    temperatures_c: Sequence[float],
    lcf_law: CoffinManson | None = None,
    shock_law: ShockCoolingLaw | None = None,
) -> ComponentDamage:
    """Convenience path for a complete, already-recorded sortie."""
    acc = DamageAccumulator(name, lcf_law=lcf_law, shock_law=shock_law)
    for t, temp in zip(times_sec, temperatures_c):
        acc.update(t, temp)
    return acc.finalise()
