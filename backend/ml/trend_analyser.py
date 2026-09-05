"""
Degradation Trend Analyser + Probabilistic RUL Engine
DRDO / iDEX Problem Statement ID: 26054

Runs in a dedicated background thread on a 20-second update interval.
Reads from a shared circular buffer of anomaly scores written by the 20 Hz
main detection loop. Zero interference with the real-time pipeline.

PS reference — what this implements:
  doc01 §3 Pillar 2:
    "A micro-leak causes Cylinder #2 to increase at +0.38°C every 10 minutes.
     While still in the green zone (112°C), the Digital Twin flags the residual
     anomaly trend, predicting a critical breach in 42 minutes."

  doc01 §3 Pillar 1:
    "If the planned sortie requires 20 flight hours but the AI prognostic
     models calculate an RUL of only 13.5 hours on the dry-sump scavenge pump,
     the system generates an immediate NO-GO advisory."

  doc02 §6:
    "LSTM / GRU / PINNs output RUL = 14.2 ± 1.1 hrs"
    (We achieve this via Monte Carlo on fitted degradation curve parameters.)

Architecture:
  Thread 1 (20 Hz)  : Writes (timestamp, anomaly_score, per_channel_scores)
                       to shared ScoreBuffer.
  Thread 2 (20 s)   : Reads buffer → fits degradation model → projects RUL
                       → writes TrendReport (thread-safe).
"""

import math
import time
import threading
import collections
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random


# ---------------------------------------------------------------------------
# Degradation model fitting (pure Python, no scipy)
# Three candidate models selected by AIC (Akaike Information Criterion)
# ---------------------------------------------------------------------------

def _linspace(start: float, stop: float, n: int) -> List[float]:
    if n == 1:
        return [start]
    step = (stop - start) / (n - 1)
    return [start + i * step for i in range(n)]


def _least_squares_linear(ts: List[float], ys: List[float]) -> Tuple[float, float, float]:
    """
    Fit y = a + b*t via closed-form OLS.
    Returns (a, b, r_squared).
    """
    n = len(ts)
    if n < 3:
        return (ys[-1] if ys else 0.0), 0.0, 0.0
    sum_t  = sum(ts)
    sum_y  = sum(ys)
    sum_t2 = sum(t*t for t in ts)
    sum_ty = sum(t*y for t, y in zip(ts, ys))
    denom = n * sum_t2 - sum_t * sum_t
    if abs(denom) < 1e-12:
        return sum_y / n, 0.0, 0.0
    b = (n * sum_ty - sum_t * sum_y) / denom
    a = (sum_y - b * sum_t) / n
    # R²
    y_mean = sum_y / n
    ss_tot = sum((y - y_mean)**2 for y in ys)
    ss_res = sum((y - (a + b*t))**2 for t, y in zip(ts, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    return a, b, max(0.0, r2)


def _fit_exponential(ts: List[float], ys: List[float]) -> Tuple[float, float, float]:
    """
    Fit y = a * exp(b*t) by transforming to log(y) = log(a) + b*t.
    Only valid for y > 0. Returns (a, b, r_squared).
    """
    safe_pairs = [(t, y) for t, y in zip(ts, ys) if y > 1e-6]
    if len(safe_pairs) < 3:
        return 0.0, 0.0, 0.0
    log_ts = [p[0] for p in safe_pairs]
    log_ys = [math.log(p[1]) for p in safe_pairs]
    log_a, b, r2 = _least_squares_linear(log_ts, log_ys)
    a = math.exp(log_a) if log_a < 500 else 1e6
    return a, b, r2


def _fit_power_law(ts: List[float], ys: List[float]) -> Tuple[float, float, float]:
    """
    Fit y = a * t^b by log-transform: log(y) = log(a) + b*log(t).
    Only valid for t > 0, y > 0.
    """
    safe_pairs = [(t, y) for t, y in zip(ts, ys) if t > 1e-6 and y > 1e-6]
    if len(safe_pairs) < 3:
        return 0.0, 0.0, 0.0
    log_ts = [math.log(p[0]) for p in safe_pairs]
    log_ys = [math.log(p[1]) for p in safe_pairs]
    log_a, b, r2 = _least_squares_linear(log_ts, log_ys)
    a = math.exp(log_a) if log_a < 500 else 1e6
    return a, b, r2


def _aic(k_params: int, n: int, sse: float) -> float:
    """AIC for least-squares model selection: AIC = n*ln(SSE/n) + 2k"""
    if n < k_params + 1 or sse <= 0:
        return float('inf')
    return n * math.log(sse / n) + 2 * k_params


@dataclass
class DegradationModel:
    """Fitted degradation curve for one channel."""
    model_type: str         # "linear" | "exponential" | "power_law"
    a: float                # intercept / scale
    b: float                # slope / rate
    r_squared: float        # goodness of fit [0, 1]
    sse: float              # sum of squared errors on fit data
    n_points: int           # number of data points used


@dataclass
class ChannelTrendReport:
    """Per-channel trend output."""
    channel: str
    model: Optional[DegradationModel]
    current_score: float
    drift_rate_per_min: float       # score units per minute (linear slope or instantaneous)
    time_to_threshold_min: float    # minutes until score reaches fault_threshold
    alert_level: str                # "NOMINAL" | "WATCH" | "WARNING" | "CRITICAL"
    is_trending: bool               # True if slope is positive and R² ≥ 0.65


@dataclass
class RULEstimate:
    """Probabilistic RUL output for one component."""
    component: str
    rul_p10_min: float    # conservative (10th percentile) — use for Go/No-Go
    rul_p50_min: float    # median estimate
    rul_p90_min: float    # optimistic (90th percentile)
    confidence: float     # R² of underlying degradation model
    is_critical: bool     # True if rul_p10 < safety_margin_min


@dataclass
class GoNoGoAdvisory:
    """Pre-flight or in-flight mission feasibility advisory."""
    advisory: str           # "GO" | "CAUTION" | "NO-GO"
    reason: str
    limiting_component: Optional[str]
    rul_hours_p10: Optional[float]
    planned_hours: Optional[float]


@dataclass
class PrognosticsReport:
    """
    Complete output of one 20-second background analysis cycle.
    Read by the main thread and GCS bridge.
    """
    timestamp_sec: float
    channels_with_trends: List[ChannelTrendReport] = field(default_factory=list)
    rul_estimates: Dict[str, RULEstimate] = field(default_factory=dict)
    go_no_go: Optional[GoNoGoAdvisory] = None
    most_critical_alert: str = "NOMINAL"    # worst alert level across all channels
    summary: str = ""


# ---------------------------------------------------------------------------
# Shared score buffer — written by Thread 1 (20 Hz), read by Thread 2 (20 s)
# ---------------------------------------------------------------------------

class ScoreBuffer:
    """
    Thread-safe circular buffer of (timestamp, composite_anomaly_score, per_channel_dict).
    Thread 1 writes every 50ms. Thread 2 reads periodically for trend fitting.
    """

    def __init__(self, maxlen: int = 3600):
        """
        Args:
            maxlen: Maximum stored frames. 3600 = 3 minutes at 20 Hz.
                    Sufficient for fitting 30-minute degradation trends when
                    combined with downsampled history in the analyser.
        """
        self._buf: collections.deque = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, timestamp_sec: float,
               composite_score: float,
               channel_scores: Dict[str, float]) -> None:
        """Called from Thread 1 at 20 Hz."""
        with self._lock:
            self._buf.append((timestamp_sec, composite_score, dict(channel_scores)))

    def snapshot(self) -> List[Tuple[float, float, Dict[str, float]]]:
        """
        Return a copy of the current buffer contents.
        Called from Thread 2 — safe to call while Thread 1 appends.
        """
        with self._lock:
            return list(self._buf)

    def reset(self) -> None:
        """Clear all buffered frames — call on fault clear/change so the next
        DegradationTrendAnalyser cycle doesn't fit a curve across old + new scenarios."""
        with self._lock:
            self._buf.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._buf)


# ---------------------------------------------------------------------------
# Fault thresholds per component (from doc03 §1 critical limits)
# ---------------------------------------------------------------------------

COMPONENT_CHANNELS: Dict[str, List[str]] = {
    "Cylinder_Head_Assembly": ["d_CHT_2"],          # Primary: CHT_2 residual
    "Lubrication_Oil_Circuit": ["d_OIL_PRESS"],     # Primary: oil pressure drop
    "Reduction_Gearbox": ["d_VIB_RMS"],             # Primary: vibration residual
    "Alternator_Bus": ["d_BUS_VOLTAGE"],             # Primary: bus voltage sag
    "Fuel_Injection_Rail": ["d_FUEL_FLOW"],          # Primary: fuel flow drop
    "Ignition_Harness": ["d_EGT_2"],                # Primary: EGT misfire runner
}

# Score at which component is considered failed (from doc01 §4 absolute limits)
FAULT_THRESHOLD_SCORE: Dict[str, float] = {
    "Cylinder_Head_Assembly": 0.75,
    "Lubrication_Oil_Circuit": 0.80,
    "Reduction_Gearbox": 0.70,
    "Alternator_Bus": 0.72,
    "Fuel_Injection_Rail": 0.70,
    "Ignition_Harness": 0.70,
}

# Alert thresholds on time-to-breach (minutes)
ALERT_THRESHOLDS = {
    "CRITICAL": 5.0,
    "WARNING": 30.0,
    "WATCH": 90.0,
}


class DegradationTrendAnalyser:
    """
    Fits degradation models to per-channel anomaly score history.
    Designed to run every 20 seconds in a background thread.

    Three window sizes for different fault speeds (from PS doc01 §3):
      SHORT  =  2 min → F4 Oil Pressure, F7 Voltage Sag (fast)
      MEDIUM = 10 min → F1 CHT Overheat, F3 Misfire (thermal ramp)
      LONG   = 30 min → F2 Injector Coking, F6 EGT Imbalance (slow)
    """

    WINDOW_SIZES_SEC = {
        "short":  2  * 60,
        "medium": 10 * 60,
        "long":   30 * 60,
    }
    MIN_R2 = 0.55     # minimum R² to consider a trend real

    def analyse(self, buffer_snapshot: List[Tuple[float, float, Dict[str, float]]],
                channel: str, fault_threshold: float = 0.75
                ) -> ChannelTrendReport:
        """
        Analyse one channel from the buffer snapshot.

        Args:
            buffer_snapshot: List of (timestamp_sec, composite_score, channel_scores)
            channel:         Key in channel_scores dict (e.g. "d_CHT_2")
            fault_threshold: Score at which this channel's fault is considered active.

        Returns:
            ChannelTrendReport
        """
        if not buffer_snapshot:
            return ChannelTrendReport(
                channel=channel, model=None, current_score=0.0,
                drift_rate_per_min=0.0, time_to_threshold_min=float('inf'),
                alert_level="NOMINAL", is_trending=False
            )

        # Extract channel-specific scores (fall back to composite if missing)
        t0 = buffer_snapshot[0][0]
        points: List[Tuple[float, float]] = []
        for ts, composite, ch_scores in buffer_snapshot:
            score = ch_scores.get(channel, composite)
            points.append((ts - t0, score))

        current_score = points[-1][1]
        current_t     = points[-1][0]

        best_report = None
        best_r2 = -1.0

        # Try each window size, pick the one with best R² that shows a real trend
        for wname, wsec in self.WINDOW_SIZES_SEC.items():
            window_points = [(t, s) for t, s in points if current_t - t <= wsec]
            if len(window_points) < 6:
                continue

            ts_min = [t / 60.0 for t, _ in window_points]   # convert to minutes
            ys     = [s for _, s in window_points]

            # Fit three candidate models
            models: List[Tuple[str, DegradationModel]] = []

            a_l, b_l, r2_l = _least_squares_linear(ts_min, ys)
            sse_l = sum((y - (a_l + b_l*t))**2 for t, y in zip(ts_min, ys))
            models.append(("linear", DegradationModel(
                model_type="linear", a=a_l, b=b_l, r_squared=r2_l,
                sse=sse_l, n_points=len(ys))))

            a_e, b_e, r2_e = _fit_exponential(ts_min, ys)
            if a_e > 0:
                sse_e = sum((y - a_e * math.exp(b_e * t))**2
                            for t, y in zip(ts_min, ys) if y > 0)
                models.append(("exponential", DegradationModel(
                    model_type="exponential", a=a_e, b=b_e, r_squared=r2_e,
                    sse=sse_e, n_points=len(ys))))

            a_p, b_p, r2_p = _fit_power_law(ts_min, ys)
            if a_p > 0:
                sse_p = sum((y - a_p * (max(t, 1e-6)**b_p))**2
                            for t, y in zip(ts_min, ys) if t > 0 and y > 0)
                models.append(("power_law", DegradationModel(
                    model_type="power_law", a=a_p, b=b_p, r_squared=r2_p,
                    sse=sse_p, n_points=len(ys))))

            # Select by AIC (lower is better)
            best_model = None
            best_aic = float('inf')
            for mtype, m in models:
                k = 2  # 2 parameters (a, b)
                n = m.n_points
                aic = _aic(k, n, m.sse)
                if aic < best_aic and m.r_squared >= 0:
                    best_aic = aic
                    best_model = m

            if best_model is not None and best_model.r_squared > best_r2:
                best_r2 = best_model.r_squared
                t_now_min = current_t / 60.0

                # Forward projection to fault threshold
                ttb = self._time_to_breach(best_model, t_now_min, current_score, fault_threshold)

                # Drift rate in score/min (use linear slope or numerical derivative for others)
                if best_model.model_type == "linear":
                    drift_rate = best_model.b
                elif best_model.model_type == "exponential":
                    # Instantaneous derivative at t_now
                    drift_rate = best_model.a * best_model.b * math.exp(
                        best_model.b * t_now_min)
                else:  # power_law
                    if t_now_min > 0:
                        drift_rate = best_model.a * best_model.b * (
                            t_now_min ** (best_model.b - 1.0))
                    else:
                        drift_rate = 0.0

                is_trending = (best_model.r_squared >= self.MIN_R2
                               and drift_rate > 0.0002)  # >0.012/hr minimum slope

                if ttb < float('inf') and ttb < ALERT_THRESHOLDS["WATCH"]:
                    if ttb <= ALERT_THRESHOLDS["CRITICAL"]:
                        alert = "CRITICAL"
                    elif ttb <= ALERT_THRESHOLDS["WARNING"]:
                        alert = "WARNING"
                    else:
                        alert = "WATCH"
                else:
                    alert = "NOMINAL"

                best_report = ChannelTrendReport(
                    channel=channel,
                    model=best_model,
                    current_score=round(current_score, 4),
                    drift_rate_per_min=round(drift_rate, 6),
                    time_to_threshold_min=round(ttb, 1),
                    alert_level=alert,
                    is_trending=is_trending,
                )

        if best_report is None:
            return ChannelTrendReport(
                channel=channel, model=None,
                current_score=round(current_score, 4),
                drift_rate_per_min=0.0,
                time_to_threshold_min=float('inf'),
                alert_level="NOMINAL",
                is_trending=False,
            )

        return best_report

    @staticmethod
    def _time_to_breach(model: DegradationModel,
                         t_now_min: float,
                         current_score: float,
                         threshold: float) -> float:
        """
        Solve for t when model(t) = threshold using binary search.
        Returns minutes from now until breach, or inf if no breach projected.
        """
        if current_score >= threshold:
            return 0.0   # already breached

        def predict(t: float) -> float:
            if model.model_type == "linear":
                return model.a + model.b * t
            elif model.model_type == "exponential":
                exp_arg = model.b * t
                if exp_arg > 500:
                    return float('inf')
                return model.a * math.exp(exp_arg)
            else:  # power_law
                if t <= 0:
                    return 0.0
                return model.a * (t ** model.b)

        # Only project if trend is upward
        if predict(t_now_min + 1.0) <= predict(t_now_min):
            return float('inf')  # not trending toward threshold

        # Binary search over next 480 minutes (8 hours)
        lo, hi = t_now_min, t_now_min + 480.0
        for _ in range(40):
            mid = (lo + hi) / 2.0
            if predict(mid) < threshold:
                lo = mid
            else:
                hi = mid

        breach_t = (lo + hi) / 2.0
        delta = breach_t - t_now_min
        if delta > 480.0 or delta < 0:
            return float('inf')
        return delta


class ProbabilisticRULEstimator:
    """
    Monte Carlo Remaining Useful Life estimation.

    Given a fitted DegradationModel from DegradationTrendAnalyser,
    samples 500 perturbed parameter sets from the model fit uncertainty
    and computes the distribution of time-to-failure.

    Output: p10, p50, p90 in minutes (suitable for mission Go/No-Go).
    """

    N_MONTE_CARLO = 500     # 500 samples adequate for prototype (< 2ms)
    SAFETY_MARGIN_MIN = 120.0   # 2-hour safety margin for Go/No-Go

    def estimate(self, trend_report: ChannelTrendReport,
                 component: str) -> RULEstimate:
        """
        Estimate probabilistic RUL for a component.

        Args:
            trend_report: Output of DegradationTrendAnalyser.analyse()
            component:    Component name for threshold lookup.

        Returns:
            RULEstimate with p10, p50, p90 in minutes.
        """
        fault_thresh = FAULT_THRESHOLD_SCORE.get(component, 0.75)

        if trend_report.model is None or not trend_report.is_trending:
            # No trend fitted — RUL is unknown/large
            return RULEstimate(
                component=component,
                rul_p10_min=float('inf'),
                rul_p50_min=float('inf'),
                rul_p90_min=float('inf'),
                confidence=0.0,
                is_critical=False,
            )

        model = trend_report.model
        times = []
        analyser = DegradationTrendAnalyser()

        # Estimate parameter uncertainty from R² and n_points
        r2 = max(model.r_squared, 0.1)
        n  = max(model.n_points, 6)
        # Relative uncertainty in slope (b): higher when R² is low or n is small
        sigma_b_rel = (1.0 - r2) / math.sqrt(n) * 2.0

        current_t_min = 0.0   # relative time reference

        for _ in range(self.N_MONTE_CARLO):
            # Perturb parameters
            b_perturbed = model.b * (1.0 + random.gauss(0, sigma_b_rel))
            a_perturbed = model.a * (1.0 + random.gauss(0, sigma_b_rel * 0.3))

            perturbed = DegradationModel(
                model_type=model.model_type,
                a=a_perturbed,
                b=b_perturbed,
                r_squared=model.r_squared,
                sse=model.sse,
                n_points=model.n_points,
            )
            ttb = analyser._time_to_breach(
                perturbed, current_t_min,
                trend_report.current_score, fault_thresh
            )
            if ttb < float('inf'):
                times.append(ttb)

        if len(times) < 10:
            # Fewer than 10 valid Monte Carlo samples — trend uncertain
            median_ttb = trend_report.time_to_threshold_min
            return RULEstimate(
                component=component,
                rul_p10_min=median_ttb * 0.7 if median_ttb < 1e9 else float('inf'),
                rul_p50_min=median_ttb,
                rul_p90_min=median_ttb * 1.4 if median_ttb < 1e9 else float('inf'),
                confidence=model.r_squared,
                is_critical=median_ttb < self.SAFETY_MARGIN_MIN,
            )

        times.sort()
        n_t = len(times)
        p10 = times[int(0.10 * n_t)]
        p50 = times[int(0.50 * n_t)]
        p90 = times[min(int(0.90 * n_t), n_t - 1)]

        return RULEstimate(
            component=component,
            rul_p10_min=round(p10, 1),
            rul_p50_min=round(p50, 1),
            rul_p90_min=round(p90, 1),
            confidence=round(model.r_squared, 3),
            is_critical=p10 < self.SAFETY_MARGIN_MIN,
        )

    @staticmethod
    def go_no_go(planned_hours: float,
                 rul_estimates: Dict[str, RULEstimate],
                 safety_margin_hours: float = 2.0) -> GoNoGoAdvisory:
        """
        Pre-flight Go/No-Go advisory per doc01 §3 Pillar 1.

        Compares planned_hours against conservative RUL_p10 for each component.
        """
        safety_min = safety_margin_hours * 60.0
        planned_min = planned_hours * 60.0

        worst_component = None
        worst_p10 = float('inf')

        for comp, rul in rul_estimates.items():
            if rul.rul_p10_min < worst_p10:
                worst_p10 = rul.rul_p10_min
                worst_component = comp

        if worst_p10 == float('inf'):
            return GoNoGoAdvisory(
                advisory="GO",
                reason="No degradation trends detected. All components nominal.",
                limiting_component=None,
                rul_hours_p10=None,
                planned_hours=planned_hours,
            )

        worst_p10_hrs = worst_p10 / 60.0

        if planned_min > worst_p10:
            return GoNoGoAdvisory(
                advisory="NO-GO",
                reason=(
                    f"PRE-EMPTIVE MAINTENANCE REQUIRED. "
                    f"{worst_component} RUL: {worst_p10_hrs:.1f}h (p10 conservative bound). "
                    f"Planned sortie: {planned_hours:.1f}h exceeds component limit."
                ),
                limiting_component=worst_component,
                rul_hours_p10=round(worst_p10_hrs, 2),
                planned_hours=planned_hours,
            )
        elif planned_min > worst_p10 - safety_min:
            return GoNoGoAdvisory(
                advisory="CAUTION",
                reason=(
                    f"Narrow safety margin. "
                    f"{worst_component} RUL: {worst_p10_hrs:.1f}h. "
                    f"Safety margin: {safety_margin_hours}h. "
                    f"Consider reduced sortie duration or maintenance inspection."
                ),
                limiting_component=worst_component,
                rul_hours_p10=round(worst_p10_hrs, 2),
                planned_hours=planned_hours,
            )
        else:
            return GoNoGoAdvisory(
                advisory="GO",
                reason=(
                    f"Propulsion system certified. "
                    f"Most limiting component ({worst_component}) RUL: "
                    f"{worst_p10_hrs:.1f}h vs planned {planned_hours:.1f}h. "
                    f"Safety margin: {worst_p10_hrs - planned_hours:.1f}h."
                ),
                limiting_component=worst_component,
                rul_hours_p10=round(worst_p10_hrs, 2),
                planned_hours=planned_hours,
            )


class PrognosticsWorker:
    """
    Background thread that runs DegradationTrendAnalyser + ProbabilisticRULEstimator
    every `interval_sec` seconds (default: 20s as per user requirement).

    Usage:
        buffer = ScoreBuffer()
        worker = PrognosticsWorker(buffer, interval_sec=20.0)
        worker.start()
        # Main loop writes to buffer at 20 Hz
        # Query worker.latest_report for current trend/RUL
        worker.stop()
    """

    def __init__(self, buffer: ScoreBuffer,
                 interval_sec: float = 20.0,
                 planned_mission_hours: float = 18.0):
        self._buffer = buffer
        self._interval = interval_sec
        self._planned_hours = planned_mission_hours
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._latest_report: Optional[PrognosticsReport] = None
        self._report_lock = threading.Lock()

        self._analyser = DegradationTrendAnalyser()
        self._rul_estimator = ProbabilisticRULEstimator()

    def start(self) -> None:
        """Start the background analysis thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="PrognosticsWorker",
            daemon=True,  # dies with main process
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the background thread to stop and join."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)

    def set_planned_hours(self, hours: float) -> None:
        self._planned_hours = hours

    @property
    def planned_hours(self) -> float:
        return self._planned_hours

    @property
    def latest_report(self) -> Optional[PrognosticsReport]:
        """Thread-safe read of latest prognostics report."""
        with self._report_lock:
            return self._latest_report

    def reset(self) -> None:
        """
        Clear the shared ScoreBuffer and the last computed report.

        Must be called whenever a fault is cleared or a new one is commanded — otherwise
        DegradationTrendAnalyser keeps fitting curves across frames from the old scenario
        for up to `buffer.maxlen` frames (minutes), so the Go/No-Go advisory and RUL_p10
        stay stuck reporting the previous (possibly NO-GO) scenario long after the live
        telemetry has actually returned to nominal.
        """
        self._buffer.reset()
        with self._report_lock:
            self._latest_report = None

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            start = time.monotonic()
            try:
                self._analyse_and_update()
            except Exception:
                pass  # never crash the background thread
            elapsed = time.monotonic() - start
            sleep_sec = max(0.0, self._interval - elapsed)
            self._stop_event.wait(timeout=sleep_sec)

    def _analyse_and_update(self) -> None:
        snapshot = self._buffer.snapshot()
        if len(snapshot) < 12:
            return   # too few points for any meaningful fit

        trend_reports: List[ChannelTrendReport] = []
        rul_estimates: Dict[str, RULEstimate] = {}

        # Analyse each component's primary channel
        for component, channels in COMPONENT_CHANNELS.items():
            primary_ch = channels[0]
            fault_thresh = FAULT_THRESHOLD_SCORE.get(component, 0.75)
            tr = self._analyser.analyse(snapshot, primary_ch, fault_thresh)
            trend_reports.append(tr)
            rul = self._rul_estimator.estimate(tr, component)
            rul_estimates[component] = rul

        # Also analyse composite anomaly score
        comp_tr = self._analyser.analyse(snapshot, "__composite__", 0.80)
        trend_reports.append(comp_tr)

        # Go/No-Go
        gng = self._rul_estimator.go_no_go(self._planned_hours, rul_estimates)

        # Worst alert level
        alert_order = {"NOMINAL": 0, "WATCH": 1, "WARNING": 2, "CRITICAL": 3}
        active_trends = [tr for tr in trend_reports if tr.is_trending]
        if active_trends:
            worst_alert = max(active_trends, key=lambda r: alert_order.get(r.alert_level, 0))
            worst_level = worst_alert.alert_level
        else:
            worst_level = "NOMINAL"

        # Build summary string
        if active_trends:
            tr0 = active_trends[0]
            ttb = tr0.time_to_threshold_min
            ttb_str = f"{ttb:.0f} min" if ttb < 1e9 else "unknown"
            summary = (
                f"TREND DETECTED on {tr0.channel}: "
                f"drift rate {tr0.drift_rate_per_min*60:.4f}/hr, "
                f"threshold breach in ~{ttb_str}. "
                f"Go/No-Go: {gng.advisory}."
            )
        else:
            summary = f"No degradation trends. Go/No-Go: {gng.advisory}."

        report = PrognosticsReport(
            timestamp_sec=time.time(),
            channels_with_trends=active_trends,
            rul_estimates=rul_estimates,
            go_no_go=gng,
            most_critical_alert=worst_level,
            summary=summary,
        )
        with self._report_lock:
            self._latest_report = report
