"""
Standard PHM prognostic performance metrics — F60.

Reporting "RUL MAE = 12.4 hours" is not a prognostics result; it is a regression
result that happens to be computed on RUL. The PHM community settled this in
2008-2010: prognostics is judged on *when* a prediction becomes trustworthy and
*whether it stays* trustworthy as end-of-life approaches, which point error
cannot express.

Implements the four hierarchical metrics of Saxena, Celaya & Goebel, applied as
a waterfall — an algorithm that fails Prognostic Horizon has no business being
scored on the later metrics:

  1. Prognostic Horizon  — how far before EoL predictions first enter, and stay
                           within, the alpha cone.
  2. Alpha-Lambda        — is the prediction inside the cone at a specified
                           fraction lambda of the way through life.
  3. Relative Accuracy   — error relative to the true RUL at a given time.
  4. Convergence         — how quickly the error shrinks as EoL approaches.

Ported from the reference implementation in NASA's PrognosticsMetricsLibrary
(vendored at vendor/PrognosticsMetricsLibrary), which is MATLAB; this is a
dependency-free Python translation.

References
----------
Saxena, Celaya, Saha, Saha & Goebel (2010) "Metrics for Offline Evaluation of
    Prognostic Performance", Int. J. Prognostics and Health Management
Goebel & Saxena, "Prognostic Performance Metrics", ch. 5
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

__all__ = [
    "PrognosticSeries",
    "prognostic_horizon",
    "alpha_lambda",
    "relative_accuracy",
    "convergence",
    "evaluate",
]


@dataclass
class PrognosticSeries:
    """A single run-to-failure trajectory's predictions.

    times        : prediction times (same units as RUL, e.g. hours)
    predicted_rul: RUL predicted at each of those times
    end_of_life  : the true EoL time; true RUL at time t is (end_of_life - t)
    """

    times: Sequence[float]
    predicted_rul: Sequence[float]
    end_of_life: float

    def __post_init__(self) -> None:
        if len(self.times) != len(self.predicted_rul):
            raise ValueError("times and predicted_rul must be the same length")

    @property
    def true_rul(self) -> List[float]:
        return [max(0.0, self.end_of_life - t) for t in self.times]

    @property
    def start_time(self) -> float:
        return float(self.times[0]) if len(self.times) else 0.0

    def errors(self) -> List[float]:
        return [p - r for p, r in zip(self.predicted_rul, self.true_rul)]


def _alpha_bounds(true_rul: float, alpha: float) -> Tuple[float, float]:
    """The accuracy cone: +/- alpha as a fraction of true RUL (so it narrows)."""
    margin = alpha * true_rul
    return true_rul - margin, true_rul + margin


def prognostic_horizon(series: PrognosticSeries, alpha: float = 0.2) -> Optional[float]:
    """Time before EoL at which predictions first enter the cone and stay in it.

    Returns None when the trajectory never stabilises inside the cone — which is
    a meaningful, reportable outcome, not a failure to compute. A larger horizon
    is better: it is the usable warning time.
    """
    true_rul = series.true_rul
    first_valid: Optional[int] = None
    for i, (t, pred) in enumerate(zip(series.times, series.predicted_rul)):
        lo, hi = _alpha_bounds(true_rul[i], alpha)
        inside = lo <= pred <= hi
        if inside:
            if first_valid is None:
                first_valid = i
        else:
            first_valid = None  # must remain inside from here on
    if first_valid is None:
        return None
    return series.end_of_life - float(series.times[first_valid])


def alpha_lambda(
    series: PrognosticSeries, alpha: float = 0.2, lam: float = 0.5
) -> Optional[bool]:
    """Is the prediction inside the cone at lambda of the way from start to EoL?

    lam=0.5 is the conventional mid-life check. Binary by construction: this is
    a gate, not a score.
    """
    if not len(series.times):
        return None
    t_lambda = series.start_time + lam * (series.end_of_life - series.start_time)
    idx = min(
        range(len(series.times)),
        key=lambda i: abs(float(series.times[i]) - t_lambda),
    )
    true_rul = series.true_rul[idx]
    lo, hi = _alpha_bounds(true_rul, alpha)
    return bool(lo <= series.predicted_rul[idx] <= hi)


def relative_accuracy(series: PrognosticSeries, lam: float = 0.5) -> Optional[float]:
    """RA = 1 - |true - predicted| / true, evaluated at lambda. Higher is better."""
    if not len(series.times):
        return None
    t_lambda = series.start_time + lam * (series.end_of_life - series.start_time)
    idx = min(
        range(len(series.times)),
        key=lambda i: abs(float(series.times[i]) - t_lambda),
    )
    true_rul = series.true_rul[idx]
    if true_rul <= 0:
        return None
    return 1.0 - abs(true_rul - series.predicted_rul[idx]) / true_rul


def convergence(series: PrognosticSeries, metric: str = "abs_error") -> Optional[float]:
    """Euclidean distance from origin to the centroid of the error-vs-time curve.

    Smaller means the error collapses sooner. Two algorithms can share an average
    error while one converges early and the other only at the last moment; this
    is the metric that separates them.
    """
    times = [float(t) for t in series.times]
    if len(times) < 2:
        return None

    if metric == "abs_error":
        vals = [abs(e) for e in series.errors()]
    elif metric == "sq_error":
        vals = [e * e for e in series.errors()]
    else:
        raise ValueError(f"unknown metric {metric!r}")

    # Centroid of the area under the |error| curve, per Saxena et al.
    num_t = 0.0
    num_v = 0.0
    den = 0.0
    for i in range(len(times) - 1):
        dt = times[i + 1] - times[i]
        if dt <= 0:
            continue
        area = 0.5 * dt * (vals[i] + vals[i + 1])
        if area == 0:
            continue
        num_t += area * 0.5 * (times[i] + times[i + 1])
        num_v += area * 0.5 * (vals[i] + vals[i + 1])
        den += area
    if den == 0:
        return 0.0
    cx = num_t / den
    cy = num_v / den
    return ((cx - times[0]) ** 2 + cy ** 2) ** 0.5


def evaluate(
    series: PrognosticSeries, alpha: float = 0.2, lam: float = 0.5
) -> dict:
    """Run the full waterfall. Later metrics are reported as None if PH fails.

    That gating is deliberate and is part of the standard: an algorithm that
    never settles inside the cone should not be able to advertise a flattering
    mid-life relative accuracy.
    """
    ph = prognostic_horizon(series, alpha=alpha)
    passed = ph is not None
    return {
        "prognostic_horizon": None if ph is None else round(ph, 4),
        "ph_passed": passed,
        "alpha_lambda": alpha_lambda(series, alpha=alpha, lam=lam) if passed else None,
        "relative_accuracy": (
            round(ra, 4)
            if passed and (ra := relative_accuracy(series, lam=lam)) is not None
            else None
        ),
        "convergence": (
            round(cv, 4)
            if passed and (cv := convergence(series)) is not None
            else None
        ),
        "alpha": alpha,
        "lambda": lam,
        "n_predictions": len(series.times),
    }
