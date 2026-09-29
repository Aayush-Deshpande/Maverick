"""
Twin validity monitoring — F51 / F52.

Every digital twin in this field reports the engine's health. None of them
report their own. That is a gap with consequences: a model that has drifted away
from the engine it represents keeps producing confident residuals, and those
residuals are then fed to a classifier that has no way of knowing they are
meaningless.

This module makes the twin's own trustworthiness a first-class output, using
standard instruments from estimation theory rather than invented heuristics:

  * **Innovation consistency (NIS).** If the model and its uncertainty are
    correct, normalised squared residuals follow a chi-squared distribution with
    known degrees of freedom. Persistent excursion outside the confidence bounds
    means the model is wrong, not that the engine is sick.
  * **Residual whiteness.** A correct model leaves white residuals. Significant
    autocorrelation at non-zero lag means unmodelled dynamics — structure the
    twin is failing to capture.
  * **Bias detection.** A residual mean that is not zero is a calibration error,
    which is exactly what per-tail calibration (F50) exists to remove.
  * **Envelope / out-of-distribution check.** A twin validated over one operating
    envelope says nothing about behaviour outside it. Flying outside the
    validated envelope is a reason to lower confidence regardless of how good
    the residuals look.

The three-way attribution
-------------------------
The output that matters operationally is not "the twin is unwell", it is *which
of three things is happening*, because they demand opposite responses:

    MODEL_DRIFT   — the twin no longer matches the engine   -> recalibrate
    ENGINE_FAULT  — the engine has changed                  -> maintain
    SENSOR_FAULT  — the measurement has changed             -> quarantine channel

A system that cannot separate these will recalibrate away a real fault, which is
the single most dangerous failure mode an adaptive health monitor can have.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Sequence

__all__ = ["ValidityVerdict", "TwinValidityMonitor", "chi2_bounds"]


# Chi-squared 95% two-sided bounds, by degrees of freedom. Precomputed so the
# module stays dependency-free (scipy is optional elsewhere in the stack).
_CHI2_95 = {
    1: (0.001, 5.02), 2: (0.05, 7.38), 3: (0.22, 9.35), 4: (0.48, 11.14),
    5: (0.83, 12.83), 6: (1.24, 14.45), 7: (1.69, 16.01), 8: (2.18, 17.53),
    9: (2.70, 19.02), 10: (3.25, 20.48), 12: (4.40, 23.34), 15: (6.26, 27.49),
    20: (9.59, 34.17), 27: (14.57, 43.19), 30: (16.79, 46.98),
}


def chi2_bounds(dof: int) -> tuple[float, float]:
    """95% bounds on a chi-squared statistic, interpolating for unlisted dof."""
    if dof in _CHI2_95:
        return _CHI2_95[dof]
    keys = sorted(_CHI2_95)
    if dof < keys[0]:
        return _CHI2_95[keys[0]]
    if dof > keys[-1]:
        # Wilson-Hilferty normal approximation for large dof.
        a = 2.0 / (9.0 * dof)
        lo = dof * (1 - a - 1.96 * math.sqrt(a)) ** 3
        hi = dof * (1 - a + 1.96 * math.sqrt(a)) ** 3
        return (lo, hi)
    lower = max(k for k in keys if k <= dof)
    upper = min(k for k in keys if k >= dof)
    if lower == upper:
        return _CHI2_95[lower]
    t = (dof - lower) / (upper - lower)
    lo = _CHI2_95[lower][0] + t * (_CHI2_95[upper][0] - _CHI2_95[lower][0])
    hi = _CHI2_95[lower][1] + t * (_CHI2_95[upper][1] - _CHI2_95[lower][1])
    return (lo, hi)


@dataclass
class ValidityVerdict:
    trustworthy: bool
    confidence: float  # 0..1
    attribution: str  # NOMINAL | MODEL_DRIFT | ENGINE_FAULT | SENSOR_FAULT | OUT_OF_ENVELOPE
    nis: float
    nis_in_bounds: bool
    whiteness_p: float
    max_autocorr: float
    bias_channels: List[str] = field(default_factory=list)
    out_of_envelope: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        v_str = "VALID" if self.trustworthy else ("DEGRADED" if self.confidence > 0.3 else "INVALID")
        return {
            "TWIN_TRUSTWORTHY": self.trustworthy,
            "TWIN_CONFIDENCE": round(self.confidence, 4),
            "TWIN_ATTRIBUTION": self.attribution,
            "TWIN_NIS": round(self.nis, 4),
            "TWIN_NIS_IN_BOUNDS": self.nis_in_bounds,
            "TWIN_RESIDUAL_WHITENESS": round(self.whiteness_p, 4),
            "TWIN_MAX_AUTOCORR": round(self.max_autocorr, 4),
            "TWIN_BIASED_CHANNELS": self.bias_channels,
            "TWIN_OUT_OF_ENVELOPE": self.out_of_envelope,
            "TWIN_REASONS": self.reasons,
            # Dual-compatible contract aliases for frontend and API
            "verdict": v_str,
            "attribution": self.attribution,
            "nis_chi2": round(self.nis, 4),
            "whiteness_p_value": round(self.whiteness_p, 4),
            "explanation": self.sentence(),
        }

    def sentence(self) -> str:
        if self.trustworthy:
            return f"Twin consistent with the engine (confidence {self.confidence:.2f})."
        return (f"Twin confidence {self.confidence:.2f} — {self.attribution}: "
                + "; ".join(self.reasons))


class TwinValidityMonitor:
    """Continuous self-assessment of whether the twin still matches the engine."""

    def __init__(
        self,
        channels: Sequence[str],
        expected_sigma: Optional[Dict[str, float]] = None,
        window: int = 600,
        envelope: Optional[Dict[str, tuple[float, float]]] = None,
    ) -> None:
        self.channels = list(channels)
        # Expected residual standard deviation per channel when the twin is
        # correct. Wrong values here make NIS meaningless, so they should come
        # from the calibration flights, not from guesswork.
        self.expected_sigma = expected_sigma or {c: 1.0 for c in self.channels}
        self.window = window
        self.envelope = envelope or {}
        self._residuals: Dict[str, Deque[float]] = {
            c: deque(maxlen=window) for c in self.channels
        }
        self._nis_history: Deque[float] = deque(maxlen=window)

    # -- ingest -------------------------------------------------------------

    def update(self, residuals: Dict[str, float],
               operating_point: Optional[Dict[str, float]] = None) -> None:
        """Feed one frame of (measured - expected) residuals."""
        squared = 0.0
        dof = 0
        for c in self.channels:
            if c not in residuals or residuals[c] is None:
                continue
            r = float(residuals[c])
            self._residuals[c].append(r)
            sigma = max(self.expected_sigma.get(c, 1.0), 1e-9)
            squared += (r / sigma) ** 2
            dof += 1
        if dof:
            # Normalised innovation squared, per degree of freedom.
            self._nis_history.append(squared)
        self._last_operating_point = operating_point or {}

    # -- statistics ---------------------------------------------------------

    def _mean_nis(self) -> tuple[float, int]:
        if not self._nis_history:
            return (0.0, 0)
        dof = sum(1 for c in self.channels if self._residuals[c])
        return (sum(self._nis_history) / len(self._nis_history), dof)

    def _autocorrelation(self, series: Sequence[float], lag: int) -> float:
        n = len(series)
        if n <= lag + 2:
            return 0.0
        mean = sum(series) / n
        var = sum((x - mean) ** 2 for x in series)
        if var <= 0:
            return 0.0
        cov = sum((series[i] - mean) * (series[i + lag] - mean) for i in range(n - lag))
        return cov / var

    def _whiteness(self) -> tuple[float, float]:
        """Ljung-Box style check over the pooled residuals.

        Returns an approximate p-value and the largest absolute autocorrelation
        found. Low p means the residuals are structured, i.e. the twin is
        missing dynamics rather than merely being noisy.
        """
        worst = 0.0
        stat = 0.0
        n_used = 0
        for c in self.channels:
            series = list(self._residuals[c])
            n = len(series)
            if n < 30:
                continue
            n_used += 1
            for lag in (1, 2, 5, 10):
                if n <= lag + 2:
                    continue
                rho = self._autocorrelation(series, lag)
                worst = max(worst, abs(rho))
                stat += n * (n + 2) * rho * rho / max(n - lag, 1)
        if n_used == 0:
            return (1.0, 0.0)
        # Convert the Ljung-Box statistic to a rough p-value against chi2.
        dof = max(4 * n_used, 1)
        lo, hi = chi2_bounds(dof)
        p = 1.0 if stat <= hi else max(0.0, 1.0 - min(1.0, (stat - hi) / max(hi, 1e-9)))
        return (p, worst)

    def _biased_channels(self, threshold_sigma: float = 0.5) -> List[str]:
        """Channels whose residual mean is significantly non-zero."""
        out: List[str] = []
        for c in self.channels:
            series = list(self._residuals[c])
            if len(series) < 30:
                continue
            mean = sum(series) / len(series)
            sigma = max(self.expected_sigma.get(c, 1.0), 1e-9)
            stderr = sigma / math.sqrt(len(series))
            if abs(mean) > max(threshold_sigma * sigma, 2.0 * stderr):
                out.append(c)
        return out

    def _envelope_violations(self) -> List[str]:
        out: List[str] = []
        point = getattr(self, "_last_operating_point", {}) or {}
        for name, (lo, hi) in self.envelope.items():
            if name in point and point[name] is not None:
                v = float(point[name])
                if v < lo or v > hi:
                    out.append(f"{name}={v:.1f} outside [{lo:.1f}, {hi:.1f}]")
        return out

    # -- verdict ------------------------------------------------------------

    def assess(self, fault_suspected: bool = False,
               sensor_quarantined: Optional[Sequence[str]] = None) -> ValidityVerdict:
        """Judge the twin, and attribute the cause when it is not trustworthy.

        `fault_suspected` and `sensor_quarantined` come from the detection stack.
        They are inputs to attribution rather than to the statistics: the same
        statistical picture means different things depending on whether the
        detector has independently flagged something.
        """
        mean_nis, dof = self._mean_nis()
        lo, hi = chi2_bounds(max(dof, 1))
        in_bounds = (lo <= mean_nis <= hi) if dof else True
        whiteness_p, max_ac = self._whiteness()
        biased = self._biased_channels()
        envelope = self._envelope_violations()
        quarantined = list(sensor_quarantined or [])

        reasons: List[str] = []
        if not in_bounds:
            reasons.append(
                f"NIS {mean_nis:.1f} outside chi2 95% bounds [{lo:.1f}, {hi:.1f}]")
        if whiteness_p < 0.05:
            reasons.append(f"residuals not white (max autocorrelation {max_ac:.2f})")
        if biased:
            reasons.append(f"non-zero residual mean on {', '.join(biased)}")
        if envelope:
            reasons.append("outside validated envelope: " + "; ".join(envelope))

        # Attribution. Order matters: a quarantined sensor explains the picture
        # more parsimoniously than model drift, and an independently detected
        # fault explains it better than either.
        if envelope:
            attribution = "OUT_OF_ENVELOPE"
        elif quarantined:
            # When sensors are quarantined by the sanity validator / parity space:
            # If an engine fault is independently suspected on healthy (non-quarantined)
            # channels, engine fault is reported; otherwise, the quarantined sensor
            # explains the anomaly and avoids misattributing sensor glitch to engine.
            non_quarantined_biased = [b for b in biased if b not in quarantined]
            if fault_suspected and not in_bounds and len(non_quarantined_biased) > 0:
                attribution = "ENGINE_FAULT"
            else:
                attribution = "SENSOR_FAULT"
        elif fault_suspected and not in_bounds:
            attribution = "ENGINE_FAULT"
        elif (not in_bounds or whiteness_p < 0.05) and not fault_suspected:
            # Structured residuals with no independent fault indication is the
            # signature of a model that has drifted, not an engine that is sick.
            attribution = "MODEL_DRIFT"
        elif biased and not fault_suspected:
            attribution = "MODEL_DRIFT"
        else:
            attribution = "NOMINAL"

        penalties = 0.0
        if not in_bounds:
            penalties += 0.35
        if whiteness_p < 0.05:
            penalties += 0.25
        if biased:
            penalties += 0.15 * min(len(biased), 3)
        if envelope:
            penalties += 0.30
        confidence = max(0.0, min(1.0, 1.0 - penalties))
        trustworthy = confidence >= 0.6 and attribution in ("NOMINAL", "ENGINE_FAULT")

        return ValidityVerdict(
            trustworthy=trustworthy,
            confidence=confidence,
            attribution=attribution,
            nis=mean_nis,
            nis_in_bounds=in_bounds,
            whiteness_p=whiteness_p,
            max_autocorr=max_ac,
            bias_channels=biased,
            out_of_envelope=envelope,
            reasons=reasons or ["all consistency checks passed"],
        )

    def reset(self) -> None:
        for c in self.channels:
            self._residuals[c].clear()
        self._nis_history.clear()
