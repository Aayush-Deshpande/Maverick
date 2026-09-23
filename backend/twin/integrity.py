"""
Physics-constrained telemetry integrity — F54 / F55.

The problem statement names "secure telemetry architecture" as an innovation
area. The competitive answer is HMAC-signed telemetry, and signing is worth
having — but it protects the *link*, not the *truth*. A signature proves a frame
arrived unaltered from whatever produced it. It says nothing about whether a
compromised sensor, a spoofed ECU node or a replayed frame produced a value that
was never physically true. CAN in particular has no native authentication, and
impersonating a trusted node's identifiers is the standard attack.

We are unusually well placed to close that gap, because we already have a
physics model of the thing being measured. An attacker can forge a number; they
cannot easily forge a number that satisfies every physical relationship the
engine must obey simultaneously:

    manifold pressure vs throttle vs altitude
    fuel flow vs power vs BSFC
    EGT vs fuel flow vs lambda
    turbo pressure ratio vs charge temperature (isentropic relation)
    electrical load vs bus voltage
    shaft power vs RPM vs torque

Each constraint has a residual. Under normal operation those residuals are
bounded; a physically inconsistent injection breaks at least one. Conformal
calibration on nominal data gives the detector a **guaranteed false-alarm rate**
rather than a hand-tuned threshold, which matters because a spoof detector that
cries wolf will be switched off.

One sentence available to us and to nobody else in this field:
    cryptography tells you the frame arrived unaltered;
    physics tells you the frame was never true.

Also covers the cheap structural checks that catch the unsophisticated attacks
and the common failures: stale frames, frozen values, replayed timestamps, and
dual-lane FADEC disagreement.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, List, Optional, Sequence

__all__ = [
    "PhysicalConstraint",
    "IntegrityVerdict",
    "TelemetryIntegrityMonitor",
    "default_constraints",
]


@dataclass
class PhysicalConstraint:
    """One relationship the engine must satisfy, as a residual function.

    `residual` returns a value that should be near zero on physically consistent
    telemetry. `scale` is the expected magnitude of that residual under normal
    noise, used to normalise before thresholding.
    """

    name: str
    channels: List[str]
    residual: Callable[[Dict[str, float]], Optional[float]]
    scale: float = 1.0
    description: str = ""

    def evaluate(self, frame: Dict[str, float]) -> Optional[float]:
        if any(c not in frame or frame[c] is None for c in self.channels):
            return None
        try:
            r = self.residual(frame)
        except (ZeroDivisionError, ValueError, TypeError):
            return None
        if r is None or not math.isfinite(r):
            return None
        return r / max(self.scale, 1e-9)


def default_constraints() -> List[PhysicalConstraint]:
    """Constraints for a turbocharged piston engine.

    Coefficients are deliberately loose: the job is to catch values that are
    *physically impossible together*, not to re-implement the thermodynamic
    model. A tight constraint here would fire on every legitimate transient.
    """
    return [
        PhysicalConstraint(
            "map_vs_throttle_altitude",
            ["MAP", "TPS", "ALTITUDE_FT"],
            lambda f: f["MAP"] - _expected_map(f["TPS"], f["ALTITUDE_FT"]),
            scale=12.0,
            description="Manifold pressure must be consistent with throttle and ambient",
        ),
        PhysicalConstraint(
            "fuel_flow_vs_power",
            ["FUEL_FLOW", "POWER_KW"],
            lambda f: f["FUEL_FLOW"] - (f["POWER_KW"] * 0.30 + 1.5),
            scale=4.0,
            description="Fuel flow must track shaft power through BSFC",
        ),
        PhysicalConstraint(
            "power_vs_rpm_map",
            ["POWER_KW", "ENGINE_RPM", "MAP"],
            lambda f: f["POWER_KW"] - (f["ENGINE_RPM"] / 5800.0) * (f["MAP"] / 100.0) * 84.0,
            scale=12.0,
            description="Shaft power must follow speed and charge density",
        ),
        PhysicalConstraint(
            "egt_vs_fuel_flow",
            ["EGT_1", "FUEL_FLOW"],
            lambda f: f["EGT_1"] - (420.0 + 16.0 * f["FUEL_FLOW"]),
            scale=90.0,
            description="Exhaust temperature must track fuel burned",
        ),
        PhysicalConstraint(
            "turbo_isentropic",
            ["CHARGE_TEMP_C", "TURBO_PRESSURE_RATIO", "OAT_C"],
            lambda f: (f["CHARGE_TEMP_C"] + 273.15)
            - (f["OAT_C"] + 273.15) * (max(f["TURBO_PRESSURE_RATIO"], 1.0) ** 0.2857),
            scale=35.0,
            description="Charge temperature must obey the compression relation",
        ),
        PhysicalConstraint(
            "electrical_balance",
            ["BUS_VOLTAGE", "BATTERY_CURRENT"],
            lambda f: (f["BUS_VOLTAGE"] - 14.2) + 0.08 * f["BATTERY_CURRENT"],
            scale=1.2,
            description="Bus voltage must respond to electrical load",
        ),
        PhysicalConstraint(
            "oil_pressure_vs_rpm",
            ["OIL_PRESS", "ENGINE_RPM"],
            lambda f: f["OIL_PRESS"] - (0.6 + 0.00058 * f["ENGINE_RPM"]),
            scale=1.0,
            description="Oil pressure is produced by a pump driven at engine speed",
        ),
    ]


def _expected_map(throttle_pct: float, altitude_ft: float) -> float:
    """Crude ambient-limited manifold pressure, kPa."""
    amb = 101.325 * (1.0 - 2.25577e-5 * max(altitude_ft, 0.0) * 0.3048) ** 5.25588
    return amb * (0.20 + 0.80 * max(0.0, min(1.0, throttle_pct / 100.0)))


@dataclass
class IntegrityVerdict:
    consistent: bool
    max_violation: float
    violated_constraints: List[str] = field(default_factory=list)
    stale_channels: List[str] = field(default_factory=list)
    frozen_channels: List[str] = field(default_factory=list)
    lane_disagreements: List[str] = field(default_factory=list)
    classification: str = "NOMINAL"  # NOMINAL | SENSOR_FAULT | SUSPECTED_SPOOF | STALE_LINK
    detail: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "TELEM_CONSISTENT": self.consistent,
            "TELEM_MAX_VIOLATION": round(self.max_violation, 3),
            "TELEM_VIOLATED": self.violated_constraints,
            "TELEM_STALE": self.stale_channels,
            "TELEM_FROZEN": self.frozen_channels,
            "TELEM_LANE_DISAGREE": self.lane_disagreements,
            "TELEM_CLASSIFICATION": self.classification,
            "TELEM_DETAIL": self.detail,
        }


class TelemetryIntegrityMonitor:
    """Physics-based integrity checking with a conformal false-alarm guarantee."""

    def __init__(
        self,
        constraints: Optional[List[PhysicalConstraint]] = None,
        window: int = 300,
        freeze_tolerance: float = 1e-9,
        freeze_samples: int = 40,
    ) -> None:
        self.constraints = constraints if constraints is not None else default_constraints()
        self.window = window
        self.freeze_tolerance = freeze_tolerance
        self.freeze_samples = freeze_samples
        self._history: Dict[str, Deque[float]] = {}
        self._last_seen: Dict[str, float] = {}
        self._calibration: Dict[str, List[float]] = {}
        self._threshold: Dict[str, float] = {}
        self._calibrated = False

    # -- calibration --------------------------------------------------------

    def calibrate(self, nominal_frames: Sequence[Dict[str, float]],
                  alpha: float = 0.01) -> "TelemetryIntegrityMonitor":
        """Learn per-constraint thresholds from telemetry known to be genuine.

        Uses the conformal quantile, so the expected false-alarm rate is alpha
        by construction rather than by tuning. A spoof detector without a stated
        false-alarm rate is not deployable; operators switch off anything that
        cries wolf.
        """
        self._calibration = {c.name: [] for c in self.constraints}
        for frame in nominal_frames:
            for c in self.constraints:
                r = c.evaluate(frame)
                if r is not None:
                    self._calibration[c.name].append(abs(r))
        self._threshold = {}
        for name, scores in self._calibration.items():
            if not scores:
                continue
            scores = sorted(scores)
            n = len(scores)
            k = math.ceil((n + 1) * (1.0 - alpha))
            self._threshold[name] = scores[min(k, n) - 1] if k <= n else float("inf")
        self._calibrated = True
        return self

    @property
    def thresholds(self) -> Dict[str, float]:
        return dict(self._threshold)

    # -- checking -----------------------------------------------------------

    def check(self, frame: Dict[str, float], t_sec: Optional[float] = None,
              max_age_sec: float = 2.0) -> IntegrityVerdict:
        violated: List[str] = []
        detail: List[str] = []
        worst = 0.0

        for c in self.constraints:
            r = c.evaluate(frame)
            if r is None:
                continue
            mag = abs(r)
            worst = max(worst, mag)
            limit = self._threshold.get(c.name, 3.0)  # 3 sigma if uncalibrated
            if mag > limit:
                violated.append(c.name)
                detail.append(f"{c.name}: |residual| {mag:.2f} > {limit:.2f}")

        # Structural checks.
        frozen: List[str] = []
        for k, v in frame.items():
            if v is None or not isinstance(v, (int, float)):
                continue
            hist = self._history.setdefault(k, deque(maxlen=self.window))
            hist.append(float(v))
            if len(hist) >= self.freeze_samples:
                recent = list(hist)[-self.freeze_samples:]
                if max(recent) - min(recent) <= self.freeze_tolerance:
                    frozen.append(k)
            if t_sec is not None:
                self._last_seen[k] = t_sec

        stale: List[str] = []
        if t_sec is not None:
            for k, seen in self._last_seen.items():
                if t_sec - seen > max_age_sec:
                    stale.append(k)

        # Dual-lane FADEC disagreement — a free diagnostic on a redundant system,
        # and the cheapest way to catch a single spoofed node.
        lanes: List[str] = []
        for base in ("MAP", "ENGINE_RPM", "CHT_1", "EGT_1"):
            a, b = f"{base}_LANE_A", f"{base}_LANE_B"
            if a in frame and b in frame and frame[a] is not None and frame[b] is not None:
                spread = abs(float(frame[a]) - float(frame[b]))
                ref = max(abs(float(frame[a])), 1.0)
                if spread / ref > 0.05:
                    lanes.append(f"{base}: A={frame[a]:.1f} B={frame[b]:.1f}")

        classification = "NOMINAL"
        if stale:
            classification = "STALE_LINK"
        elif lanes:
            classification = "SUSPECTED_SPOOF" if len(violated) >= 1 else "SENSOR_FAULT"
        elif len(violated) >= 2:
            # A single broken constraint is most parsimoniously one bad sensor.
            # Several broken at once means the *set* of values is not physically
            # realisable together, which a genuine single-sensor fault does not
            # usually produce.
            classification = "SUSPECTED_SPOOF"
        elif len(violated) == 1 or frozen:
            classification = "SENSOR_FAULT"

        return IntegrityVerdict(
            consistent=not violated and not frozen and not stale and not lanes,
            max_violation=worst,
            violated_constraints=violated,
            stale_channels=sorted(set(stale)),
            frozen_channels=sorted(set(frozen)),
            lane_disagreements=lanes,
            classification=classification,
            detail=detail or ["all physical constraints satisfied"],
        )

    def reset(self) -> None:
        self._history.clear()
        self._last_seen.clear()
