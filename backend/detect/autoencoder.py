"""Autoencoder novelty scorer with an Extreme Value Theory threshold (card M3-04, idea text I-03/I-04).

A small multilayer perceptron learns to reconstruct the nominal residual feature vector through a narrow bottleneck
(scikit-learn MLPRegressor, input -> hidden -> bottleneck -> hidden -> input). A frame that does not look like
normal flight reconstructs badly; the score is the mean squared reconstruction error.

Threshold (EVT, peaks over threshold): the nominal scores above the u-quantile are excesses y = s - u, fitted with a
Generalized Pareto distribution (scipy.stats.genpareto, location fixed at 0). For a per-frame false-alarm target
alpha the threshold is
    h = u + GPD.ppf(1 - alpha / p_u, c, 0, scale),     p_u = share of nominal scores above u
which extrapolates the tail instead of needing 1/alpha held-out frames (the conformal quantile's limit).
Settings in configs/detect.json autoencoder (ASSUMED). Deterministic (fixed random_state).
"""
from __future__ import annotations

import warnings
from typing import Dict

import numpy as np
from scipy.stats import genpareto
from sklearn.exceptions import ConvergenceWarning
from sklearn.neural_network import MLPRegressor


class AutoencoderScorer:
    name = "ae_evt"

    def __init__(self, cfg: Dict) -> None:
        self.hidden = int(cfg["hidden_units"]["value"])
        self.bottleneck = int(cfg["bottleneck_units"]["value"])
        self.max_iter = int(cfg["max_iter"]["value"])
        self.tail_q = float(cfg["evt_tail_quantile"]["value"])
        self.seed = int(cfg["random_state"]["value"])
        self.mu: np.ndarray | None = None
        self.sd: np.ndarray | None = None
        self.net: MLPRegressor | None = None
        self.gpd: Dict[str, float] = {}

    def fit(self, Z: np.ndarray) -> "AutoencoderScorer":
        self.mu, self.sd = Z.mean(0), Z.std(0) + 1e-9
        X = (Z - self.mu) / self.sd
        self.net = MLPRegressor(hidden_layer_sizes=(self.hidden, self.bottleneck, self.hidden), activation="tanh",
                                max_iter=self.max_iter, random_state=self.seed)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            self.net.fit(X, X)
        return self

    def score(self, Z: np.ndarray) -> np.ndarray:
        """Forward pass on the trained weights (tanh hidden layers, identity output: MLPRegressor's network); the
        same numbers as net.predict without its per-call validation overhead, which dominated one-frame scoring."""
        X = (np.atleast_2d(Z) - self.mu) / self.sd
        h = X
        last = len(self.net.coefs_) - 1
        for i, (w, b) in enumerate(zip(self.net.coefs_, self.net.intercepts_)):
            h = h @ w + b
            if i < last:
                h = np.tanh(h)
        return np.mean((h - X) ** 2, axis=1)

    def evt_threshold(self, nominal_scores: np.ndarray, alpha: float) -> float:
        """Peaks-over-threshold GPD fit on nominal scores; threshold at per-frame false-alarm rate alpha."""
        s = np.asarray(nominal_scores, dtype=float)
        u = float(np.quantile(s, self.tail_q))
        excess = s[s > u] - u
        p_u = len(excess) / len(s)
        if len(excess) < 10 or alpha >= p_u:
            return float(np.quantile(s, 1.0 - alpha))           # too few tail points: plain empirical quantile
        c, _, scale = genpareto.fit(excess, floc=0.0)
        self.gpd = {"u": u, "shape": float(c), "scale": float(scale), "p_u": p_u}
        return u + float(genpareto.ppf(1.0 - alpha / p_u, c, loc=0.0, scale=scale))
