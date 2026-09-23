"""
Evaluation harness — closes G03, implements F18.

The problem statement frames the task as a transition *from* conventional
threshold-based monitoring. Every team in this field asserts that transition.
Nobody measures it, and until now neither did we.

This harness runs the twin and a conventional limit monitor **side by side, on
the same frames, from an independent plant**, and reports:

  * **Detection lead time** — how long before the threshold monitor fires, and
    before functional failure, the twin raises a warning. This is the headline
    number the whole project exists to produce.
  * **False alarms per flight hour** on long nominal sorties, for both systems.
  * **Sensor-fault discrimination** — a drifting sensor must not be reported as
    an engine fault, and must not abort a serviceable aircraft.
  * **Detection latency** from true fault onset.

Everything is measured against `VirtualEngine`, which the twin does not import
and whose ground truth is reachable only through a separate `truth()` call. A
result produced any other way measures the generator rather than the diagnosis.

A detector that wins on lead time but loses on false alarms has not won. Both are
reported together for that reason, and a scenario that produces no detection at
all is recorded as a miss rather than dropped from the average.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from ..plant.virtual_engine import VirtualEngine
from ..twin.residual_detector import ResidualDetector
from ..ml.crank_diagnostics import CrankDiagnostics
from .threshold_baseline import ROTAX_914_LIMITS, ThresholdMonitor, compare_detection

__all__ = ["Scenario", "ScenarioResult", "EvaluationHarness", "DEFAULT_SCENARIOS"]


@dataclass
class Scenario:
    """One run: a profile, and optionally a fault injected part-way through."""

    name: str
    duration_sec: float = 3600.0
    dt_sec: float = 1.0
    throttle_pct: float = 75.0
    altitude_ft: float = 20000.0
    oat_c: float = -25.0
    dust_mg_m3: float = 0.15
    fault: Optional[str] = None
    fault_cylinder: Optional[int] = None
    fault_severity: float = 0.8
    fault_onset_sec: float = 600.0
    fault_ramp_sec: float = 900.0
    is_nominal: bool = False
    expects_sensor_fault: bool = False


@dataclass
class ScenarioResult:
    scenario: str
    twin_detection_t: Optional[float]
    baseline_alarm_t: Optional[float]
    fault_onset_t: Optional[float]
    failure_t: Optional[float]
    twin_classification: Optional[str]
    lead_time_sec: Optional[float]
    twin_warning_before_failure_sec: Optional[float]
    baseline_warning_before_failure_sec: Optional[float]
    detection_latency_sec: Optional[float]
    crank_detection_t: Optional[float]
    crank_cylinder: Optional[int]
    twin_false_alarms: int
    baseline_false_alarms: int
    flight_hours: float
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "twin_detection_t_sec": self.twin_detection_t,
            "baseline_alarm_t_sec": self.baseline_alarm_t,
            "lead_time_sec": self.lead_time_sec,
            "lead_time_min": (round(self.lead_time_sec / 60.0, 2)
                              if self.lead_time_sec is not None else None),
            "detection_latency_sec": self.detection_latency_sec,
            "twin_warning_before_failure_sec": self.twin_warning_before_failure_sec,
            "baseline_warning_before_failure_sec": self.baseline_warning_before_failure_sec,
            "twin_classification": self.twin_classification,
            "crank_detection_t_sec": self.crank_detection_t,
            "crank_cylinder": self.crank_cylinder,
            "twin_false_alarms": self.twin_false_alarms,
            "baseline_false_alarms": self.baseline_false_alarms,
            "flight_hours": round(self.flight_hours, 3),
            "notes": self.notes,
        }


DEFAULT_SCENARIOS: List[Scenario] = [
    Scenario("nominal_cruise_2h", duration_sec=7200, is_nominal=True),
    Scenario("nominal_hot_low", duration_sec=3600, altitude_ft=6000, oat_c=38.0,
             is_nominal=True),
    Scenario("cooling_degradation", duration_sec=5400, fault="COOLING_DEGRADATION",
             fault_severity=0.95, fault_ramp_sec=2400),
    Scenario("misfire_cyl3", duration_sec=3600, fault="MISFIRE", fault_cylinder=3,
             fault_severity=0.9, fault_ramp_sec=600),
    Scenario("injector_coking_cyl2", duration_sec=5400, fault="INJECTOR_COKING",
             fault_cylinder=2, fault_severity=0.85, fault_ramp_sec=2400),
    Scenario("oil_pressure_loss", duration_sec=3600, fault="OIL_PRESSURE_LOSS",
             fault_severity=0.85, fault_ramp_sec=1200),
    Scenario("turbo_bearing_wear", duration_sec=5400, fault="TURBO_BEARING_WEAR",
             fault_severity=0.9, fault_ramp_sec=2400),
    Scenario("sensor_drift_cht1", duration_sec=5400, fault="SENSOR_BIAS_DRIFT",
             fault_cylinder=1, fault_severity=0.9, fault_ramp_sec=600,
             expects_sensor_fault=True),
]


class EvaluationHarness:
    """Runs the twin and the baseline head to head against the plant."""

    def __init__(self, twin_detector: Optional[Callable[[Dict[str, float], float], Optional[dict]]] = None,
                 engine_config: str = "rotax_914", seed: int = 7) -> None:
        # `twin_detector(frame, t_sec) -> {"detected": bool, "classification": str}`
        # The default is the physics-residual detector below, which is
        # deliberately simple: the point of this harness is the *comparison*, and
        # a detector that only beats the baseline because it was hand-tuned to
        # these scenarios would prove nothing.
        self._residual = ResidualDetector()
        self.twin_detector = twin_detector or self._physics_detector
        self.engine_config = engine_config
        self.seed = seed
        self._baseline_state: Dict[str, Any] = {}

    def _physics_detector(self, frame: Dict[str, float], t_sec: float) -> dict:
        """Physics-expectation residual detector with per-tail calibration.

        See backend/twin/residual_detector.py for why the two earlier
        self-referential detectors were abandoned.
        """
        return self._residual.update(frame, t_sec).as_dict()

    # -- a deliberately plain physics-residual detector ---------------------

    def _default_detector(self, frame: Dict[str, float], t_sec: float) -> dict:
        """Fast/slow residual change detector with robust per-channel scale.

        The first version of this froze each channel's mean and variance after a
        240 s warm-up and flagged departures beyond 6 sigma. It fired at the same
        instant in every scenario including the nominal ones, because the plant's
        thermal states are still settling then (CHT tau = 25 s, oil tau = 60 s)
        and the warm-up variance of a settling channel is tiny. It was measuring
        the clock, not the engine.

        This version tracks a fast and a slow exponential average per channel and
        watches the gap between them. Slow settling moves both together and
        produces no signal; a fault ramp moves the fast one first. The scale is a
        running mean absolute deviation, so a quiet channel does not get an
        absurdly small denominator.

        It is deliberately generic — it knows nothing about the fault set, so it
        cannot be accused of having been fitted to these scenarios.
        """
        st = self._baseline_state
        fast = st.setdefault("fast", {})
        slow = st.setdefault("slow", {})
        scale = st.setdefault("scale", {})
        streak = st.setdefault("streak", {})
        dt = max(t_sec - st.get("last_t", t_sec - 1.0), 1e-3)
        st["last_t"] = t_sec

        TAU_FAST, TAU_SLOW = 30.0, 600.0
        SETTLE_SEC = 300.0       # ignore the transient at engine start
        K = 8.0                  # gap must exceed this many robust deviations
        PERSIST = 30             # ...for this many consecutive samples

        a_fast = 1.0 - math.exp(-dt / TAU_FAST)
        a_slow = 1.0 - math.exp(-dt / TAU_SLOW)

        detected = False
        worst_score = 0.0
        worst_ch = None

        for ch, v in frame.items():
            if ch in ("T_SEC", "TPS", "ALTITUDE_FT", "OAT_C"):
                continue
            if not isinstance(v, (int, float)):
                continue
            if ch not in fast:
                fast[ch] = slow[ch] = float(v)
                scale[ch] = 0.0
                continue
            fast[ch] += (v - fast[ch]) * a_fast
            slow[ch] += (v - slow[ch]) * a_slow
            gap = fast[ch] - slow[ch]
            # Robust scale: running mean |gap| while nothing is wrong.
            scale[ch] += (abs(gap) - scale[ch]) * a_slow

            if t_sec < SETTLE_SEC:
                continue
            denom = max(scale[ch], 1e-3 * max(abs(slow[ch]), 1.0))
            score = abs(gap) / denom
            streak[ch] = streak.get(ch, 0) + 1 if score > K else 0
            if streak[ch] >= PERSIST and score > worst_score:
                worst_score, worst_ch = score, ch
                detected = True

        classification = None
        if detected and worst_ch:
            classification = "ENGINE_FAULT"
            # Redundancy check: a CHT channel moving while its peers hold station
            # is a sensor, not a cylinder. This is the discrimination that stops
            # a serviceable aircraft being aborted.
            if worst_ch.startswith("CHT_"):
                idx = worst_ch.split("_")[1]
                peer_gaps = []
                for i in range(1, 5):
                    pc = f"CHT_{i}"
                    if str(i) == idx or pc not in fast:
                        continue
                    d = max(scale.get(pc, 1e-3), 1e-3)
                    peer_gaps.append(abs(fast[pc] - slow[pc]) / d)
                if peer_gaps and max(peer_gaps) < K * 0.5:
                    classification = "SENSOR_FAULT"

        return {"detected": detected, "classification": classification,
                "channel": worst_ch, "score": worst_score}

    # -- running ------------------------------------------------------------

    def run_scenario(self, scenario: Scenario) -> ScenarioResult:
        plant = VirtualEngine(self.engine_config, seed=self.seed)
        baseline = ThresholdMonitor(dict(ROTAX_914_LIMITS))
        self._baseline_state = {}
        self._residual.reset()

        crank = CrankDiagnostics(plant.cfg.cylinder_count,
                                 tuple(plant.cfg.layout.firing_order),
                                 plant.crank.geom.inertia_kgm2)
        crank_t: Optional[float] = None
        crank_cyl: Optional[int] = None
        CRANK_EVERY = 30  # the edge node analyses crank data on its own cadence
        twin_t: Optional[float] = None
        twin_class: Optional[str] = None
        base_t: Optional[float] = None
        twin_false = 0
        base_false = 0
        injected = False
        notes: List[str] = []

        steps = int(scenario.duration_sec / scenario.dt_sec)
        for i in range(steps):
            t = i * scenario.dt_sec
            if (scenario.fault and not injected and t >= scenario.fault_onset_sec):
                plant.inject_fault(scenario.fault, scenario.fault_cylinder,
                                   scenario.fault_severity, scenario.fault_ramp_sec)
                injected = True

            frame = plant.step(scenario.dt_sec, scenario.throttle_pct,
                               scenario.altitude_ft, scenario.oat_c,
                               scenario.dust_mg_m3)

            verdict = self.twin_detector(frame, t)
            if verdict and verdict.get("detected"):
                if twin_t is None:
                    twin_t = t
                    twin_class = verdict.get("classification")
                if scenario.is_nominal:
                    twin_false += 1

            # Second, independent detection channel: per-cylinder combustion
            # from crank angular velocity. Thermal residuals cannot see a slow
            # injector fault; this can, because it measures the work each
            # cylinder does rather than the heat it eventually sheds.
            if i % CRANK_EVERY == 0:
                th, om, _ = plant.crank_signal(frame.get("ENGINE_RPM", 5000.0),
                                               frame.get("MAP", 100.0))
                crank.analyse_cycle(th, om)
                if crank_t is None and t > 300.0:
                    rep = crank.report()
                    if rep.verdict in ("MISFIRING", "WEAK_CYLINDER") and rep.cylinder:
                        crank_t = t
                        crank_cyl = rep.cylinder

            new_alarms = baseline.update(t, frame)
            if new_alarms and base_t is None:
                base_t = new_alarms[0].t_sec
            if scenario.is_nominal:
                base_false += len(new_alarms)

            if plant.has_failed:
                notes.append(f"plant failed at t={t:.0f}s "
                             f"({plant.truth()['failure_reason']})")
                break

        truth = plant.truth()
        cmp = compare_detection(twin_t, base_t, truth.get("failure_t_sec"),
                                scenario.fault_onset_sec if scenario.fault else None)

        if scenario.expects_sensor_fault:
            if twin_class == "SENSOR_FAULT":
                notes.append("twin correctly classified SENSOR_FAULT")
            elif twin_class:
                notes.append(f"MISCLASSIFIED sensor drift as {twin_class}")
            if base_t is not None:
                notes.append("baseline alarmed on a sensor fault "
                             "(would abort a serviceable aircraft)")

        return ScenarioResult(
            scenario=scenario.name,
            twin_detection_t=twin_t,
            baseline_alarm_t=base_t,
            fault_onset_t=scenario.fault_onset_sec if scenario.fault else None,
            failure_t=truth.get("failure_t_sec"),
            twin_classification=twin_class,
            crank_detection_t=crank_t,
            crank_cylinder=crank_cyl,
            lead_time_sec=cmp["lead_time_sec"],
            twin_warning_before_failure_sec=cmp["twin_warning_before_failure_sec"],
            baseline_warning_before_failure_sec=cmp["baseline_warning_before_failure_sec"],
            detection_latency_sec=cmp["twin_detection_latency_sec"],
            twin_false_alarms=twin_false,
            baseline_false_alarms=base_false,
            flight_hours=scenario.duration_sec / 3600.0,
            notes=notes,
        )

    def run_all(self, scenarios: Optional[Sequence[Scenario]] = None) -> dict:
        scenarios = list(scenarios or DEFAULT_SCENARIOS)
        results = [self.run_scenario(s) for s in scenarios]

        faults = [r for r in results if r.fault_onset_t is not None]
        leads = [r.lead_time_sec for r in faults if r.lead_time_sec is not None]
        nominal = [r for r in results if r.fault_onset_t is None]
        nominal_hours = sum(r.flight_hours for r in nominal) or 1e-9

        crank_detected = sum(1 for r in faults if r.crank_detection_t is not None)
        either = sum(1 for r in faults
                     if r.twin_detection_t is not None or r.crank_detection_t is not None)
        detected_by_twin = sum(1 for r in faults if r.twin_detection_t is not None)
        detected_by_base = sum(1 for r in faults if r.baseline_alarm_t is not None)
        twin_only = sum(1 for r in faults
                        if r.twin_detection_t is not None and r.baseline_alarm_t is None)

        return {
            "results": [r.as_dict() for r in results],
            "summary": {
                "scenarios": len(results),
                "fault_scenarios": len(faults),
                "twin_detected_thermal": detected_by_twin,
                "crank_detected": crank_detected,
                "detected_by_either_channel": either,
                "baseline_detected": detected_by_base,
                "detected_by_twin_only": twin_only,
                "median_lead_time_sec": (round(statistics.median(leads), 1)
                                         if leads else None),
                "median_lead_time_min": (round(statistics.median(leads) / 60.0, 2)
                                         if leads else None),
                "mean_lead_time_min": (round(sum(leads) / len(leads) / 60.0, 2)
                                       if leads else None),
                "nominal_flight_hours": round(nominal_hours, 2),
                "twin_false_alarms_per_hour": round(
                    sum(r.twin_false_alarms for r in nominal) / nominal_hours, 3),
                "baseline_false_alarms_per_hour": round(
                    sum(r.baseline_false_alarms for r in nominal) / nominal_hours, 3),
            },
        }

    # -- reporting ----------------------------------------------------------

    @staticmethod
    def to_markdown(report: dict) -> str:
        s = report["summary"]
        lines = [
            "# Detection evaluation - twin vs conventional threshold monitor",
            "",
            "Both systems see the same frames from an independent plant",
            "(`backend/plant/virtual_engine.py`), whose physics differs from the twin's",
            "model and whose ground truth is reachable only through a separate call.",
            "Positive lead time means the twin warned first.",
            "",
            "Two detection channels are reported because they are complementary:",
            "**thermal** residuals against a physics expectation, and **crank**",
            "per-cylinder combustion from angular velocity. Neither alone finds",
            "everything; the thermal channel cannot see a slow injector fault, and the",
            "crank channel is silent on cooling and lubrication faults, which are not",
            "combustion events.",
            "",
            "## Summary",
            "",
            f"- Fault scenarios: **{s['fault_scenarios']}**",
            f"- Detected by thermal residuals: **{s['twin_detected_thermal']}**",
            f"- Detected by crank diagnostics: **{s['crank_detected']}**",
            f"- Detected by **either channel**: **{s['detected_by_either_channel']}**",
            f"- Detected by the conventional threshold baseline: **{s['baseline_detected']}**",
            f"- Found by the twin but invisible to the baseline: **{s['detected_by_twin_only']}**",
            f"- Median detection lead time over the baseline: "
            f"**{s['median_lead_time_min']} min**"
            if s["median_lead_time_min"] is not None else
            "- Median lead time: not measurable (no scenario where both fired)",
            f"- False alarms per flight hour over {s['nominal_flight_hours']} nominal "
            f"hours: twin **{s['twin_false_alarms_per_hour']}**, baseline "
            f"**{s['baseline_false_alarms_per_hour']}**",
            "",
            "## Per scenario",
            "",
            "| Scenario | Thermal (s) | Crank (s) | Cyl | Baseline (s) | Lead (min) | Class | Notes |",
            "|---|---|---|---|---|---|---|---|",
        ]
        dash = lambda v: v if v is not None else "-"
        for r in report["results"]:
            lines.append(
                f"| {r['scenario']} | {dash(r['twin_detection_t_sec'])} "
                f"| {dash(r['crank_detection_t_sec'])} | {dash(r['crank_cylinder'])} "
                f"| {dash(r['baseline_alarm_t_sec'])} | {dash(r['lead_time_min'])} "
                f"| {r['twin_classification'] or '-'} | {'; '.join(r['notes'])} |"
            )
        return chr(10).join(lines)
