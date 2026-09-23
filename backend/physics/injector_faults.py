"""
Compression-ignition injector fault library — F41.

The problem statement lists "Injection timing parameters" as a monitored health
parameter and "Injector abnormalities" as a detection target. On a port-injected
spark engine, injection timing is a minor trim. On a common-rail compression
ignition engine — the AE300 on TAPAS BH-201 — it is the primary control variable
and the dominant failure mode, which is a strong hint about the engine class the
problem statement was written around.

The faults modelled here are the real ones from common-rail service experience:

  IDID / nozzle coking     Deposits inside the injector hinder movement of
                           critical parts, altering both the timing and the
                           quantity of fuel injected. Presents first as hard
                           cold starting and rough running, progressing to
                           injector sticking and, if several stick, to engine
                           failure.
  Needle stick             Binding at the needle seat; partial or total loss of
                           delivery on one cylinder.
  Rail pressure decay      Pump wear or leak-off; affects every cylinder, so it
                           is distinguishable from a single-injector fault by
                           being *symmetric*.
  Timing drift             Commanded vs actual start-of-injection diverges.
  Cold-soak delivery loss  Supplied by fuel_thermal.py, not duplicated here.

Why this strengthens rather than threatens the crank-angle thesis
-----------------------------------------------------------------
A diesel does not misfire in the spark sense, so one might expect the
per-cylinder misfire detector (F02) to lose its target. The opposite is true:
every fault above produces a **per-cylinder torque deficit at that cylinder's
firing angle**, which is precisely what the crankshaft angular-velocity detector
measures. The detector does not change; only the name of what it finds does.
It stops being a misfire detector and becomes a per-cylinder injection-health
detector, which is what the problem statement actually asks for.

All faults here modify *physical parameters* — delivered mass, injection timing,
rail pressure — never the output signal. A fault must be visible only through
the consequences it physically causes.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

__all__ = [
    "InjectorState",
    "InjectorFault",
    "InjectorBank",
    "CI_FAULT_MODES",
]

CI_FAULT_MODES = (
    "INJECTOR_COKING_IDID",
    "INJECTOR_NEEDLE_STICK",
    "RAIL_PRESSURE_DECAY",
    "INJECTION_TIMING_DRIFT",
    "INJECTOR_LEAK_OFF",
)


@dataclass
class InjectorState:
    """Per-cylinder injector condition."""

    cylinder: int
    delivery_fraction: float = 1.0  # of commanded mass actually injected
    timing_error_deg: float = 0.0  # actual minus commanded start of injection
    spray_quality: float = 1.0  # 1.0 = design atomisation; coking degrades it
    coking_index: float = 0.0  # 0..1 accumulated deposit
    sticking: bool = False
    leak_off_lph: float = 0.0

    def as_dict(self) -> dict:
        return {
            f"INJ_{self.cylinder}_DELIVERY": round(self.delivery_fraction, 4),
            f"INJ_{self.cylinder}_TIMING_ERR_DEG": round(self.timing_error_deg, 3),
            f"INJ_{self.cylinder}_SPRAY_QUALITY": round(self.spray_quality, 4),
            f"INJ_{self.cylinder}_COKING": round(self.coking_index, 4),
            f"INJ_{self.cylinder}_STICKING": self.sticking,
        }


@dataclass
class InjectorFault:
    mode: str
    cylinder: Optional[int]  # None = affects all cylinders
    severity: float = 0.0  # 0..1
    ramp_sec: float = 300.0
    _elapsed: float = 0.0

    @property
    def active_severity(self) -> float:
        """Severity ramps in; faults do not appear fully formed."""
        if self.ramp_sec <= 0:
            return self.severity
        return self.severity * min(1.0, self._elapsed / self.ramp_sec)


class InjectorBank:
    """All injectors on one engine, plus the shared rail.

    Rail pressure is deliberately shared, because that is what makes a rail
    fault distinguishable from an injector fault: a rail decay degrades every
    cylinder symmetrically, while coking degrades one. Any diagnostic that
    cannot tell those apart will recommend replacing the wrong part.
    """

    def __init__(
        self,
        n_cylinders: int = 4,
        nominal_rail_bar: float = 1800.0,
        nominal_timing_btdc: float = 8.0,
        seed: Optional[int] = None,
    ) -> None:
        self.n_cylinders = n_cylinders
        self.nominal_rail_bar = nominal_rail_bar
        self.nominal_timing_btdc = nominal_timing_btdc
        self.injectors: Dict[int, InjectorState] = {
            i: InjectorState(cylinder=i) for i in range(1, n_cylinders + 1)
        }
        self.rail_pressure_bar = nominal_rail_bar
        self.faults: List[InjectorFault] = []
        self._rng = random.Random(seed)
        # Unit-to-unit manufacturing scatter: no two injectors are identical,
        # and a detector that assumes they are will false-alarm on a healthy engine.
        self._baseline_delivery: Dict[int, float] = {}
        self._baseline_timing: Dict[int, float] = {}
        for i, inj in self.injectors.items():
            inj.delivery_fraction = 1.0 + self._rng.gauss(0.0, 0.004)
            inj.timing_error_deg = self._rng.gauss(0.0, 0.08)
            self._baseline_delivery[i] = inj.delivery_fraction
            self._baseline_timing[i] = inj.timing_error_deg

    # -- fault management ---------------------------------------------------

    def inject_fault(self, mode: str, cylinder: Optional[int] = None,
                     severity: float = 0.5, ramp_sec: float = 300.0) -> None:
        if mode not in CI_FAULT_MODES:
            raise ValueError(f"unknown CI injector fault {mode!r}; known: {CI_FAULT_MODES}")
        if cylinder is not None and cylinder not in self.injectors:
            raise ValueError(f"cylinder {cylinder} not present")
        self.faults.append(InjectorFault(mode=mode, cylinder=cylinder,
                                         severity=max(0.0, min(1.0, severity)),
                                         ramp_sec=ramp_sec))

    def clear_faults(self) -> None:
        self.faults.clear()
        for inj in self.injectors.values():
            inj.coking_index = 0.0
            inj.sticking = False
            inj.spray_quality = 1.0
            inj.leak_off_lph = 0.0
        self.rail_pressure_bar = self.nominal_rail_bar

    # -- update -------------------------------------------------------------

    def update(self, dt_sec: float, commanded_rail_bar: Optional[float] = None,
               commanded_timing_btdc: Optional[float] = None,
               fuel_temp_factor: float = 1.0) -> Dict[int, InjectorState]:
        """Advance injector condition. `fuel_temp_factor` comes from F42."""
        rail_target = commanded_rail_bar if commanded_rail_bar is not None else self.nominal_rail_bar
        timing_cmd = (commanded_timing_btdc if commanded_timing_btdc is not None
                      else self.nominal_timing_btdc)

        # Recompute from the healthy baseline every step, then apply active
        # faults. Mutating in place would compound the pressure term on every
        # update and drive delivery to zero on a perfectly healthy engine.
        rail = rail_target
        for i, inj in self.injectors.items():
            inj.sticking = False
            inj.delivery_fraction = self._baseline_delivery[i]
            inj.timing_error_deg = self._baseline_timing[i]
            inj.spray_quality = 1.0
            inj.leak_off_lph = 0.0

        for fault in self.faults:
            fault._elapsed += dt_sec
            sev = fault.active_severity
            if sev <= 0:
                continue
            targets = ([self.injectors[fault.cylinder]] if fault.cylinder
                       else list(self.injectors.values()))

            if fault.mode == "INJECTOR_COKING_IDID":
                for inj in targets:
                    inj.coking_index = max(inj.coking_index, sev)
                    # Deposits restrict flow, retard effective injection and
                    # wreck atomisation — all three, which is why coking is
                    # separable from a simple flow restriction.
                    inj.spray_quality = 1.0 - 0.55 * sev
                    inj.delivery_fraction = min(inj.delivery_fraction, 1.0 - 0.30 * sev)
                    inj.timing_error_deg += 1.8 * sev  # retarded
            elif fault.mode == "INJECTOR_NEEDLE_STICK":
                for inj in targets:
                    if sev > 0.75:
                        inj.sticking = True
                        inj.delivery_fraction = 0.0
                    else:
                        inj.delivery_fraction = min(inj.delivery_fraction, 1.0 - 0.85 * sev)
                    inj.timing_error_deg += 2.5 * sev
            elif fault.mode == "RAIL_PRESSURE_DECAY":
                rail = rail_target * (1.0 - 0.45 * sev)
            elif fault.mode == "INJECTION_TIMING_DRIFT":
                for inj in targets:
                    inj.timing_error_deg += 4.0 * sev
            elif fault.mode == "INJECTOR_LEAK_OFF":
                for inj in targets:
                    inj.leak_off_lph = 1.2 * sev
                    inj.delivery_fraction = min(inj.delivery_fraction, 1.0 - 0.15 * sev)

        self.rail_pressure_bar = rail

        # Rail pressure affects delivered mass through the orifice relation
        # (mass flow ~ sqrt(dP)), and cold fuel reduces delivery independently.
        pressure_factor = math.sqrt(max(rail, 1.0) / max(self.nominal_rail_bar, 1.0))
        for inj in self.injectors.values():
            inj.delivery_fraction = max(0.0, inj.delivery_fraction * pressure_factor
                                        * max(0.0, fuel_temp_factor))
        return self.injectors

    # -- observable consequences -------------------------------------------

    def torque_contributions(self) -> Dict[int, float]:
        """Per-cylinder torque fraction — the signal the crank-angle detector sees.

        Delivered mass sets the bulk of the contribution; poor atomisation
        lengthens ignition delay and burns less completely, and mistimed
        injection puts the heat release at the wrong crank angle. All three
        reduce the work extracted on that cylinder's power stroke.
        """
        out: Dict[int, float] = {}
        for i, inj in self.injectors.items():
            timing_penalty = 1.0 - min(0.35, abs(inj.timing_error_deg) * 0.03)
            spray_penalty = 0.75 + 0.25 * inj.spray_quality
            out[i] = max(0.0, inj.delivery_fraction * timing_penalty * spray_penalty)
        return out

    def imbalance_metrics(self) -> dict:
        """Symmetry statistics — how a rail fault is told apart from an injector one."""
        contrib = self.torque_contributions()
        values = list(contrib.values())
        n = len(values)
        mean = sum(values) / n
        var = sum((v - mean) ** 2 for v in values) / n
        cov = (var ** 0.5 / mean) if mean > 0 else 0.0
        worst = min(contrib, key=contrib.get)
        spread = max(values) - min(values)
        # A symmetric deficit is the rail; an asymmetric one is an injector.
        if mean < 0.92 and cov < 0.02:
            interpretation = "SYMMETRIC_DEFICIT — rail pressure or fuel supply, not one injector"
        elif cov >= 0.02:
            interpretation = f"ASYMMETRIC_DEFICIT — cylinder {worst} injector"
        else:
            interpretation = "NOMINAL"
        return {
            "mean_contribution": round(mean, 4),
            "cov_contribution": round(cov, 5),
            "spread": round(spread, 4),
            "weakest_cylinder": worst,
            "weakest_contribution": round(contrib[worst], 4),
            "rail_pressure_bar": round(self.rail_pressure_bar, 1),
            "interpretation": interpretation,
            "per_cylinder": {k: round(v, 4) for k, v in contrib.items()},
        }

    def as_dict(self) -> dict:
        out: dict = {"RAIL_PRESSURE_BAR": round(self.rail_pressure_bar, 1)}
        for inj in self.injectors.values():
            out.update(inj.as_dict())
        return out
