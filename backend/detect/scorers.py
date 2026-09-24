"""
Cheap anomaly scorers over calibrated feature vectors (backlog W1).

All share ``fit(Z)`` / ``score(Z)`` (rows = samples) so the bake-off, the runtime and the tests use one
interface.  ``FlyBloomScorer`` is our own minimal implementation of the published fly expand-and-sparsify
novelty idea (Dasgupta et al., Science 2017; Fly Bloom Filter, KDD 2021).  Third-party fly code is not
imported: rithram/fbfc is MIT, clembarr/ffbf has no licence (decision D35).
"""

from __future__ import annotations

import numpy as np

from backend.ml.flyhash_novelty import FlyHashEncoder


class FlyBloomScorer:
    """FlyHash code + frequency memory of nominal activations; score = 1 - mean familiarity."""

    name = "fly_bloom"

    def __init__(self, dim: int, expansion: int = 20, fan_in: int = 6, sparsity: float = 0.05,
                 f0: float = 0.05, seed: int = 7) -> None:
        self.enc = FlyHashEncoder(dim, expansion, fan_in, sparsity, seed)
        self.f0 = f0
        self.freq: np.ndarray | None = None

    def fit(self, Z: np.ndarray) -> "FlyBloomScorer":
        self.freq = np.array([self.enc.encode(z) for z in Z]).mean(0)
        return self

    def merge(self, other: "FlyBloomScorer", w_self: float, w_other: float) -> "FlyBloomScorer":
        """Federated colony merge (backlog W12): weighted mean of frequency memories, no raw data moved."""
        if self.freq is None or other.freq is None:
            raise ValueError("both scorers must be fitted")
        self.freq = (w_self * self.freq + w_other * other.freq) / (w_self + w_other)
        return self

    def score(self, Z: np.ndarray) -> np.ndarray:
        assert self.freq is not None, "fit() first"
        out = np.empty(len(Z))
        for i, z in enumerate(Z):
            fam = np.minimum(1.0, self.freq[self.enc.encode(z)] / self.f0)
            out[i] = 1.0 - fam.mean()
        return out


class Mahalanobis:
    name = "mahalanobis"

    def fit(self, Z: np.ndarray) -> "Mahalanobis":
        self.mu = Z.mean(0)
        self.P = np.linalg.pinv(np.cov(Z.T) + 1e-6 * np.eye(Z.shape[1]))
        return self

    def score(self, Z: np.ndarray) -> np.ndarray:
        d = Z - self.mu
        return np.sqrt(np.einsum("ij,jk,ik->i", d, self.P, d))


class MaxAbsZ:
    name = "max_abs_z"

    def fit(self, Z: np.ndarray) -> "MaxAbsZ":
        return self

    def score(self, Z: np.ndarray) -> np.ndarray:
        return np.abs(Z).max(1)
