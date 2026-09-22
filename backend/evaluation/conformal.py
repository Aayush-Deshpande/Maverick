"""
Conformal prediction for RUL intervals — F12 / F53.

Every competing implementation ships a heuristic "90% confidence band" produced
by a Monte Carlo spread or a fitted sigma. Neither carries a coverage guarantee,
and none of them report whether the claimed level was achieved.

Split conformal prediction does carry one: given exchangeable calibration data,
an interval built from the (1-alpha) empirical quantile of held-out nonconformity
scores covers the truth with probability at least 1-alpha, distribution-free and
model-agnostic. The point of this module is therefore not the interval — it is
`empirical_coverage()`, which lets us state a claimed level and then show it was
met on data the estimator never saw.

`AdaptiveConformal` extends this to distribution shift (ACI, Gibbs & Candes):
the effective alpha is nudged after every observation so that long-run coverage
tracks nominal even when the engine, environment or fault regime moves away from
the calibration distribution. Split conformal's exchangeability assumption is
violated exactly in that case, which is the situation a deployed UAV lives in.

References
----------
Vovk, Gammerman & Shafer, "Algorithmic Learning in a Random World"
Lei et al. (2018) "Distribution-Free Predictive Inference for Regression"
Gibbs & Candes (2021) "Adaptive Conformal Inference Under Distribution Shift"
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Sequence, Tuple

__all__ = [
    "Interval",
    "SplitConformalRUL",
    "AdaptiveConformal",
    "empirical_coverage",
    "coverage_curve",
]


@dataclass(frozen=True)
class Interval:
    lower: float
    upper: float
    point: float
    alpha: float

    @property
    def nominal_coverage(self) -> float:
        return 1.0 - self.alpha

    @property
    def width(self) -> float:
        return self.upper - self.lower

    def contains(self, truth: float) -> bool:
        return self.lower <= truth <= self.upper

    def as_dict(self) -> dict:
        return {
            "rul_p_lower": round(self.lower, 4),
            "rul_point": round(self.point, 4),
            "rul_p_upper": round(self.upper, 4),
            "nominal_coverage": round(self.nominal_coverage, 4),
            "interval_width": round(self.width, 4),
        }


def _conformal_quantile(scores: Sequence[float], alpha: float) -> float:
    """The finite-sample corrected (1-alpha) quantile of nonconformity scores.

    The ceil((n+1)(1-alpha))/n order statistic is what supplies the guarantee;
    using the plain empirical quantile under-covers on small calibration sets,
    which is precisely the regime we are in with a few dozen held-out sorties.
    """
    n = len(scores)
    if n == 0:
        raise ValueError("cannot calibrate on an empty score set")
    k = math.ceil((n + 1) * (1.0 - alpha))
    if k > n:
        # Too few calibration points to certify this alpha at all.
        return float("inf")
    return sorted(scores)[k - 1]


class SplitConformalRUL:
    """Split-conformal intervals around any RUL point estimator.

    Absolute-residual scores give a constant-width band; normalised scores
    (residual divided by a per-sample difficulty estimate) give an adaptive one,
    which matters for RUL because early-life predictions are legitimately more
    uncertain than end-of-life ones and a constant band over-covers early and
    under-covers late.
    """

    def __init__(self, normalised: bool = True, min_scale: float = 1e-6) -> None:
        self.normalised = normalised
        self.min_scale = min_scale
        self._scores: List[float] = []
        self._calibrated = False

    def calibrate(
        self,
        predictions: Sequence[float],
        truths: Sequence[float],
        scales: Sequence[float] | None = None,
    ) -> "SplitConformalRUL":
        """Fit on held-out data the point estimator never trained on.

        `scales` is the per-sample difficulty estimate (e.g. the Monte Carlo
        spread the existing RUL estimator already produces). When omitted while
        `normalised` is set, the estimator falls back to unnormalised scores.
        """
        if len(predictions) != len(truths):
            raise ValueError("predictions and truths must be the same length")
        use_scale = self.normalised and scales is not None
        if use_scale and len(scales) != len(predictions):
            raise ValueError("scales must match predictions in length")

        self._scores = []
        for i, (p, y) in enumerate(zip(predictions, truths)):
            residual = abs(float(p) - float(y))
            if use_scale:
                residual /= max(float(scales[i]), self.min_scale)
            self._scores.append(residual)
        self._calibrated = True
        return self

    def interval(self, prediction: float, alpha: float = 0.1, scale: float | None = None) -> Interval:
        if not self._calibrated:
            raise RuntimeError("calibrate() before requesting an interval")
        q = _conformal_quantile(self._scores, alpha)
        if self.normalised and scale is not None:
            q *= max(float(scale), self.min_scale)
        return Interval(
            lower=max(0.0, prediction - q),  # RUL cannot be negative
            upper=prediction + q,
            point=float(prediction),
            alpha=alpha,
        )

    @property
    def n_calibration(self) -> int:
        return len(self._scores)


class AdaptiveConformal:
    """Online conformal with an alpha that adapts to realised coverage (ACI).

    alpha_t+1 = alpha_t + gamma * (alpha_target - err_t), where err_t is 1 when
    the last interval missed. Under shift the interval widens until coverage
    recovers, and narrows again once it is comfortable — so the reported level
    stays honest without recalibrating the underlying model.
    """

    def __init__(self, target_alpha: float = 0.1, gamma: float = 0.01) -> None:
        self.target_alpha = target_alpha
        self.gamma = gamma
        self.alpha_t = target_alpha
        self._base = SplitConformalRUL(normalised=False)
        self._errors: List[int] = []

    def calibrate(self, predictions: Sequence[float], truths: Sequence[float]) -> "AdaptiveConformal":
        self._base.calibrate(predictions, truths)
        return self

    def interval(self, prediction: float, scale: float | None = None) -> Interval:
        effective = min(max(self.alpha_t, 1e-4), 0.999)
        return self._base.interval(prediction, alpha=effective, scale=scale)

    def observe(self, interval: Interval, truth: float) -> None:
        """Report the realised outcome so the next interval can adapt."""
        err = 0 if interval.contains(truth) else 1
        self._errors.append(err)
        self.alpha_t = self.alpha_t + self.gamma * (self.target_alpha - err)
        self.alpha_t = min(max(self.alpha_t, 1e-4), 0.999)

    @property
    def realised_coverage(self) -> float:
        if not self._errors:
            return float("nan")
        return 1.0 - sum(self._errors) / len(self._errors)


# ---------------------------------------------------------------------------
# Reporting — the part that actually differentiates us
# ---------------------------------------------------------------------------


def empirical_coverage(intervals: Sequence[Interval], truths: Sequence[float]) -> dict:
    """Realised vs claimed coverage. This is the number to put on the slide."""
    if len(intervals) != len(truths):
        raise ValueError("intervals and truths must be the same length")
    if not intervals:
        return {"n": 0, "empirical_coverage": float("nan")}
    hits = sum(1 for iv, y in zip(intervals, truths) if iv.contains(y))
    widths = [iv.width for iv in intervals]
    nominal = intervals[0].nominal_coverage
    n = len(intervals)
    emp = hits / n
    # Binomial standard error, so a small-sample result is not over-read.
    se = math.sqrt(max(emp * (1.0 - emp), 1e-12) / n)
    return {
        "n": n,
        "nominal_coverage": round(nominal, 4),
        "empirical_coverage": round(emp, 4),
        "coverage_std_error": round(se, 4),
        "covered": hits,
        "missed": n - hits,
        "mean_interval_width": round(sum(widths) / n, 4),
        "median_interval_width": round(sorted(widths)[n // 2], 4),
        "within_one_se": bool(abs(emp - nominal) <= se),
    }


def coverage_curve(
    predictions: Sequence[float],
    truths: Sequence[float],
    calibration_predictions: Sequence[float],
    calibration_truths: Sequence[float],
    alphas: Sequence[float] = (0.01, 0.05, 0.1, 0.2, 0.3, 0.5),
) -> List[dict]:
    """Empirical vs nominal coverage across alpha — the calibration plot.

    A well-calibrated predictor traces the diagonal. Any competitor quoting a
    bare "95% CI" has no equivalent of this table.
    """
    cp = SplitConformalRUL(normalised=False).calibrate(calibration_predictions, calibration_truths)
    rows: List[dict] = []
    for alpha in alphas:
        ivs = [cp.interval(p, alpha=alpha) for p in predictions]
        row = empirical_coverage(ivs, truths)
        row["alpha"] = alpha
        rows.append(row)
    return rows
