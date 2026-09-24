"""
ResidualDetector -- calibrated-residual detector with split-conformal thresholds and a persistence gate
(backlog W1, decisions D31/D36).

Pipeline per frame:  Frame -> TailCalibration.z -> 13 features -> {fly_bloom, mahalanobis, max_abs_z}
scores -> per-scorer conformal threshold -> alarm if ANY scorer exceeds its threshold ("raw alarm") ->
PersistenceGate (k of the last n frames) -> confirmed alarm.  Evidence = the top |z| channels, so every
alarm is explainable without a model.

Thresholds are split-conformal quantiles of scores on held-out NOMINAL calibration frames: for a
per-scorer target false-alarm rate ``alpha`` the raw false-alarm rate on exchangeable nominal frames is
<= alpha (finite-sample quantile ceil((n+1)(1-alpha))/n).  This is a guarantee about nominal frames of the
same tail and distribution only; it is not a guarantee against distribution shift.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Sequence

import numpy as np

from backend.core.frame import Frame
from backend.detect.calibration import TailCalibration
from backend.detect.scorers import FlyBloomScorer, MaxAbsZ, Mahalanobis


@dataclass
class DetectionResult:
    t: float
    scores: Dict[str, float]
    ratios: Dict[str, float]           # score / threshold (>1 means over)
    raw_alarm: bool
    confirmed: bool
    top_channels: List[tuple]          # [(channel, z)] largest |z| first
    evidence_class: str = "SIMULATION"  # set by the caller's source; PLANT frames -> SIMULATION


class PersistenceGate:
    """Confirm only when >= k of the last n raw alarms fired (edge downlink gate, D34)."""

    def __init__(self, k: int = 3, n: int = 5) -> None:
        if not 1 <= k <= n:
            raise ValueError("need 1 <= k <= n")
        self.k, self.n = k, n
        self._buf: Deque[bool] = deque(maxlen=n)

    def update(self, raw: bool) -> bool:
        self._buf.append(bool(raw))
        return sum(self._buf) >= self.k

    def reset(self) -> None:
        self._buf.clear()


class ResidualDetector:
    def __init__(self, calibration: TailCalibration, scorers: Sequence, thresholds: Dict[str, float],
                 alpha: float, gate: PersistenceGate | None = None) -> None:
        self.cal = calibration
        self.scorers = {s.name: s for s in scorers}
        self.thresholds = dict(thresholds)
        self.alpha = alpha
        self.gate = gate or PersistenceGate()

    # ---- training ------------------------------------------------------------------------
    @classmethod
    def calibrate(cls, nominal_frames: Sequence[Frame], alpha: float = 0.01,
                  holdout_frac: float = 0.3, gate: PersistenceGate | None = None) -> "ResidualDetector":
        """Fit tail calibration + scorers on the first (1-holdout) of the nominal frames (in order) and
        conformal thresholds on the rest.  Frames must be nominal -- the caller certifies that (e.g. first
        flight-line run-up, or plant frames with no injected fault); nothing here can check it."""
        frames = list(nominal_frames)
        cut = int(len(frames) * (1.0 - holdout_frac))
        if cut < 50 or len(frames) - cut < int(math.ceil(1.0 / alpha)):
            raise ValueError(f"need >= 50 fit frames and >= {int(math.ceil(1.0 / alpha))} holdout frames "
                             f"for alpha={alpha}; got {len(frames)} total")
        cal = TailCalibration.fit(frames[:cut])
        Ztr = np.vstack([cal.features(cal.z(f)) for f in frames[:cut]])
        Zho = np.vstack([cal.features(cal.z(f)) for f in frames[cut:]])
        scorers = [FlyBloomScorer(Ztr.shape[1]).fit(Ztr), Mahalanobis().fit(Ztr), MaxAbsZ().fit(Ztr)]
        thr = {s.name: conformal_threshold(s.score(Zho), alpha) for s in scorers}
        return cls(cal, scorers, thr, alpha, gate)

    # ---- inference -----------------------------------------------------------------------
    def score(self, frame: Frame, top_k: int = 3) -> DetectionResult:
        z = self.cal.z(frame)
        feat = self.cal.features(z)[None, :]
        scores = {n: float(s.score(feat)[0]) for n, s in self.scorers.items()}
        ratios = {n: scores[n] / max(self.thresholds[n], 1e-12) for n in scores}
        raw = any(r > 1.0 for r in ratios.values())
        names = self.cal.channel_names()
        order = np.argsort(-np.abs(z))[:top_k]
        return DetectionResult(frame.t, scores, ratios, raw, self.gate.update(raw),
                               [(names[i], float(z[i])) for i in order])


def conformal_threshold(nominal_scores: np.ndarray, alpha: float) -> float:
    """Split-conformal upper quantile: ceil((n+1)(1-alpha))/n-th order statistic of nominal scores."""
    s = np.sort(np.asarray(nominal_scores, dtype=float))
    n = len(s)
    k = min(n, int(math.ceil((n + 1) * (1.0 - alpha))))
    return float(s[k - 1])
