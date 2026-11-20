"""Two-sided CUSUM on the calibrated residual z-scores (card M3-02, P Part 4 M3, idea text section 6).

Per channel c, every frame:
  g+_c = max(0, g+_c + z_c - k)        g-_c = max(0, g-_c - z_c - k)
The statistic is max over channels of max(g+, g-). k (allowance, in sigmas) sets the smallest shift worth
accumulating: a sustained shift of 2k sigma is detected fastest. A slow drift that never crosses a one-frame
threshold (wear, fouling) still accumulates here - this is the step from threshold-based to predictive monitoring.
The alarm threshold h is set by the caller from nominal frames (ResidualDetector: conformal quantile on the held-out
nominal run; CUSUM values are autocorrelated, so the alpha there is approximate, not a guarantee).
A channel whose z is 0 (shielded / unmeasured) adds nothing and its sums decay by k per frame.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def load_detect_config() -> Dict:
    return json.loads((ROOT / "configs" / "detect.json").read_text(encoding="utf-8"))


class TwoSidedCusum:
    name = "cusum"

    def __init__(self, n_channels: int, k: float) -> None:
        self.k = float(k)
        self.pos = np.zeros(n_channels)
        self.neg = np.zeros(n_channels)

    def update(self, z: np.ndarray) -> float:
        z = np.asarray(z, dtype=float)
        self.pos = np.maximum(0.0, self.pos + z - self.k)
        self.neg = np.maximum(0.0, self.neg - z - self.k)
        return float(max(self.pos.max(initial=0.0), self.neg.max(initial=0.0)))

    def run(self, Z: np.ndarray) -> np.ndarray:
        """Statistic for each row of Z, from a reset state (calibration)."""
        self.reset()
        out = np.array([self.update(z) for z in Z])
        self.reset()
        return out

    def top(self, names: Sequence[str], n: int = 3) -> List[Tuple[str, float]]:
        """Channels with the largest accumulated drift, signed (+ up, - down)."""
        signed = np.where(self.pos >= self.neg, self.pos, -self.neg)
        order = np.argsort(-np.abs(signed))[:n]
        return [(names[i], float(signed[i])) for i in order if signed[i] != 0.0]

    def reset(self) -> None:
        self.pos[:] = 0.0
        self.neg[:] = 0.0
