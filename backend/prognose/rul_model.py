"""Remaining-useful-life model with split-conformal intervals (cards M4-03 / M4-07, idea text I-08, D18).

Point model: gradient-boosted trees (scikit-learn HistGradientBoostingRegressor) from health features to RUL.
Interval: split conformal. Calibration data are WHOLE trajectories (units / missions) held out from training, so the
exchangeability unit is the trajectory, not the sample (samples of one trajectory are strongly correlated). With
nonconformity scores s_i = |y_i - f(x_i)| / scale(x_i) on the calibration trajectories,
    q = the ceil((n+1)(1-alpha))/n quantile of s,   interval = f(x) +- q * scale(x)
where scale(x) grows with the predicted RUL (far-from-failure predictions are less certain). Coverage is guaranteed
only for exchangeable trajectories from the same distribution; it is MEASURED on disjoint test trajectories and
reported, per regime where regimes exist.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Sequence

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor


@dataclass
class RULInterval:
    point: np.ndarray
    lower: np.ndarray
    upper: np.ndarray


class ConformalRUL:
    def __init__(self, alpha: float = 0.05, scale_floor: float = 10.0, random_state: int = 7,
                 model_params: Optional[Dict] = None) -> None:
        self.alpha = alpha
        self.scale_floor = scale_floor            # RUL units: scale(x) = max(floor, predicted RUL) * ...
        self.model = HistGradientBoostingRegressor(random_state=random_state, **(model_params or {}))
        self.q: Optional[float] = None

    def _scale(self, pred: np.ndarray) -> np.ndarray:
        return np.maximum(pred, self.scale_floor)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "ConformalRUL":
        self.model.fit(X, y)
        return self

    def calibrate(self, X_cal: np.ndarray, y_cal: np.ndarray) -> float:
        pred = self.model.predict(X_cal)
        s = np.sort(np.abs(y_cal - pred) / self._scale(pred))
        n = len(s)
        k = min(n, int(math.ceil((n + 1) * (1.0 - self.alpha))))
        self.q = float(s[k - 1])
        return self.q

    def predict(self, X: np.ndarray) -> RULInterval:
        p = np.maximum(self.model.predict(X), 0.0)
        half = self.q * self._scale(p)
        return RULInterval(p, np.maximum(p - half, 0.0), p + half)


def split_groups(groups: Sequence, fractions=(0.6, 0.2, 0.2), seed: int = 0):
    """Disjoint train / calibration / test group ids (whole trajectories)."""
    ids = np.array(sorted(set(groups)))
    rng = np.random.default_rng(seed)
    rng.shuffle(ids)
    a = int(len(ids) * fractions[0])
    b = a + int(len(ids) * fractions[1])
    return set(ids[:a]), set(ids[a:b]), set(ids[b:])
