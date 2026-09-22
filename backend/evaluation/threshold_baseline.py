"""
Conventional threshold monitor, as a measured baseline — F13.

The problem statement frames the task as a transition *from* conventional
threshold-based monitoring. Every team asserts that transition; nobody measures
it. This module implements the thing we claim to beat — a plain limit checker of
the kind an existing engine monitor runs — so that "we detect earlier" becomes a
number with units instead of a slide.

It deliberately includes the two features that make real threshold monitors
non-trivial, because beating a strawman proves nothing:

  * persistence / debounce, so a single noisy sample does not raise an alarm;
  * caution and warning levels, as an EMS actually implements.

The comparison to report is `compare_detection()`: lead time in seconds, plus
false alarms per flight hour for both systems on nominal sorties. The sensor
drift case matters most — a limit checker cannot tell a drifting sensor from a
degrading engine, so it aborts a serviceable aircraft. That is the failure mode
the twin exists to remove.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

__all__ = [
    "Limit",
    "Alarm",
    "ThresholdMonitor",
    "ROTAX_914_LIMITS",
    "compare_detection",
    "false_alarm_rate",
]


@dataclass(frozen=True)
class Limit:
    """One channel's operating limits.

    `persistence_sec` is the dwell time an exceedance must survive before it is
    annunciated; without it any comparison against us is unfair in our favour.
    """

    channel: str
    caution_high: Optional[float] = None
    warning_high: Optional[float] = None
    caution_low: Optional[float] = None
    warning_low: Optional[float] = None
    persistence_sec: float = 2.0
    units: str = ""
    source: str = ""


@dataclass
class Alarm:
    channel: str
    level: str  # "CAUTION" | "WARNING"
    value: float
    limit: float
    t_sec: float
    direction: str  # "HIGH" | "LOW"

    def as_dict(self) -> dict:
        return {
            "channel": self.channel,
            "level": self.level,
            "value": round(self.value, 3),
            "limit": self.limit,
            "direction": self.direction,
            "t_sec": round(self.t_sec, 3),
        }


# Rotax 914 operating limits. Values are taken from the operator's manual now
# vendored at docs/reference/Rotax914_Operators_Manual.pdf; the `source` field
# records provenance so no number here is mistaken for an invention of ours.
_SRC = "Rotax 914 Operator's Manual (docs/reference/Rotax914_Operators_Manual.pdf)"

ROTAX_914_LIMITS: Dict[str, Limit] = {
    "CHT": Limit("CHT", caution_high=120.0, warning_high=135.0,
                 units="C", source=_SRC, persistence_sec=2.0),
    "EGT": Limit("EGT", caution_high=850.0, warning_high=900.0,
                 units="C", source=_SRC, persistence_sec=2.0),
    "OIL_TEMP": Limit("OIL_TEMP", caution_high=125.0, warning_high=130.0,
                      caution_low=50.0, units="C", source=_SRC),
    "OIL_PRESS": Limit("OIL_PRESS", caution_low=2.0, warning_low=1.5,
                       caution_high=7.0, units="bar", source=_SRC),
    "ENGINE_RPM": Limit("ENGINE_RPM", caution_high=5500.0, warning_high=5800.0,
                        units="rpm", source=_SRC),
    "BUS_VOLTAGE": Limit("BUS_VOLTAGE", caution_low=12.0, warning_low=11.5,
                         caution_high=15.5, units="V", source=_SRC),
}


class ThresholdMonitor:
    """A conventional limit checker with debounce and caution/warning levels."""

    def __init__(self, limits: Dict[str, Limit] | None = None) -> None:
        self.limits = limits if limits is not None else dict(ROTAX_914_LIMITS)
        self.alarms: List[Alarm] = []
        self._pending: Dict[str, float] = {}  # "<channel>|<level>|<dir>" -> first exceed time
        self._active: set[str] = set()

    def _evaluate_channel(self, key: str, channel: str, value: float, limit: float,
                          level: str, direction: str, t_sec: float,
                          persistence: float) -> None:
        exceeded = value > limit if direction == "HIGH" else value < limit
        if not exceeded:
            self._pending.pop(key, None)
            self._active.discard(key)
            return
        first = self._pending.setdefault(key, t_sec)
        if (t_sec - first) >= persistence and key not in self._active:
            self._active.add(key)
            self.alarms.append(
                Alarm(channel=channel, level=level, value=value,
                      limit=limit, t_sec=t_sec, direction=direction)
            )

    def update(self, t_sec: float, sample: Dict[str, float]) -> List[Alarm]:
        """Feed one telemetry frame. Returns alarms newly raised on this frame."""
        before = len(self.alarms)
        for channel, value in sample.items():
            limit = self.limits.get(channel)
            if limit is None or value is None:
                continue
            value = float(value)
            checks = (
                (limit.warning_high, "WARNING", "HIGH"),
                (limit.caution_high, "CAUTION", "HIGH"),
                (limit.warning_low, "WARNING", "LOW"),
                (limit.caution_low, "CAUTION", "LOW"),
            )
            for lim_value, level, direction in checks:
                if lim_value is None:
                    continue
                key = f"{channel}|{level}|{direction}"
                self._evaluate_channel(key, channel, value, lim_value, level,
                                       direction, t_sec, limit.persistence_sec)
        return self.alarms[before:]

    def first_alarm(self, level: str | None = None) -> Optional[Alarm]:
        for a in self.alarms:
            if level is None or a.level == level:
                return a
        return None

    def reset(self) -> None:
        self.alarms.clear()
        self._pending.clear()
        self._active.clear()


# ---------------------------------------------------------------------------
# The comparison that turns our core claim into a measurement
# ---------------------------------------------------------------------------


def compare_detection(
    twin_detection_t: Optional[float],
    baseline_alarm_t: Optional[float],
    failure_t: Optional[float] = None,
    fault_onset_t: Optional[float] = None,
) -> dict:
    """Lead time of the twin over a threshold monitor, in seconds.

    All four inputs are optional because every combination is a real outcome:
    the twin may miss, the baseline may never fire (fault stayed inside limits
    until failure), or there may be no functional failure in the run.
    """
    lead_over_baseline = None
    if twin_detection_t is not None and baseline_alarm_t is not None:
        lead_over_baseline = baseline_alarm_t - twin_detection_t

    warning_before_failure = None
    if twin_detection_t is not None and failure_t is not None:
        warning_before_failure = failure_t - twin_detection_t

    baseline_warning_before_failure = None
    if baseline_alarm_t is not None and failure_t is not None:
        baseline_warning_before_failure = failure_t - baseline_alarm_t

    detection_latency = None
    if twin_detection_t is not None and fault_onset_t is not None:
        detection_latency = twin_detection_t - fault_onset_t

    return {
        "twin_detection_t_sec": twin_detection_t,
        "baseline_alarm_t_sec": baseline_alarm_t,
        "lead_time_sec": (round(lead_over_baseline, 2)
                          if lead_over_baseline is not None else None),
        "lead_time_min": (round(lead_over_baseline / 60.0, 2)
                          if lead_over_baseline is not None else None),
        "twin_warning_before_failure_sec": warning_before_failure,
        "baseline_warning_before_failure_sec": baseline_warning_before_failure,
        "twin_detection_latency_sec": detection_latency,
        "twin_detected": twin_detection_t is not None,
        "baseline_detected": baseline_alarm_t is not None,
        "twin_only": twin_detection_t is not None and baseline_alarm_t is None,
        "baseline_only": baseline_alarm_t is not None and twin_detection_t is None,
    }


def false_alarm_rate(n_alarms: int, flight_hours: float) -> dict:
    """False alarms per flight hour on sorties known to be nominal."""
    if flight_hours <= 0:
        raise ValueError("flight_hours must be positive")
    per_hour = n_alarms / flight_hours
    return {
        "false_alarms": n_alarms,
        "flight_hours": round(flight_hours, 3),
        "false_alarms_per_hour": round(per_hour, 5),
        "hours_between_false_alarms": (round(1.0 / per_hour, 2)
                                       if per_hour > 0 else float("inf")),
    }
