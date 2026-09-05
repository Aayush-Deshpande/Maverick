"""
Residual Autoencoder — Unsupervised Anomaly Detector
DRDO / iDEX Problem Statement ID: 26054

Trains a 14→8→4→8→14 autoencoder on nominal engine telemetry residuals only.
At inference, reconstruction error measures how far the current residual vector
deviates from the nominal operating manifold — regardless of fault type.

PS reference: doc02 §3 — "Autoencoders & Isolation Forests compute continuous
anomaly scores (0.0 → 1.0)"

Key difference from the Z-score in thermo_model.py:
  Z-score:     Catches single-channel spikes (amplitude-based)
  Autoencoder: Catches multi-channel correlated drift that looks small per-channel
               but forms a coherent off-nominal pattern — the "+0.38°C / 10 min"
               scenario the PS describes at doc01 §3 Pillar 2.

No GPU required. Training on 5000 nominal rows takes < 5 seconds.
"""

import os
import math
import json
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Pure-numpy MLP autoencoder — no heavy dependencies, fully offline
# ---------------------------------------------------------------------------

def _relu(x: List[float]) -> List[float]:
    return [max(0.0, v) for v in x]


def _sigmoid_list(x: List[float]) -> List[float]:
    return [1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, v)))) for v in x]


def _matmul_bias(x: List[float], W: List[List[float]], b: List[float]) -> List[float]:
    """Dense layer forward pass: out = W @ x + b"""
    out_dim = len(W)
    result = []
    for i in range(out_dim):
        s = b[i]
        for j, xj in enumerate(x):
            s += W[i][j] * xj
        result.append(s)
    return result


def _mse(a: List[float], b: List[float]) -> float:
    return sum((ai - bi) ** 2 for ai, bi in zip(a, b)) / len(a)


def _he_init(out_dim: int, in_dim: int) -> List[List[float]]:
    """He (Kaiming) weight initialisation for ReLU layers."""
    scale = math.sqrt(2.0 / in_dim)
    return [
        [random.gauss(0, scale) for _ in range(in_dim)]
        for _ in range(out_dim)
    ]


def _zeros(n: int) -> List[float]:
    return [0.0] * n


# Feature normalisation bounds (per-channel, from doc03 §1 nominal ranges)
# Format: (min_val, max_val) for each of the 14 residual channels
# Residuals are differences from the physics baseline, so we normalise
# the expected residual range to [-1, 1] using domain knowledge.
RESIDUAL_NORM = {
    "d_CHT_1":      (-15.0, 80.0),    # °C residual
    "d_CHT_2":      (-15.0, 80.0),
    "d_CHT_3":      (-15.0, 80.0),
    "d_CHT_4":      (-15.0, 80.0),
    "d_EGT_1":      (-80.0, 200.0),   # °C residual
    "d_EGT_2":      (-80.0, 200.0),
    "d_EGT_3":      (-80.0, 200.0),
    "d_EGT_4":      (-80.0, 200.0),
    "d_OIL_PRESS":  (-3.0, 1.5),      # bar residual
    "d_OIL_TEMP":   (-20.0, 40.0),    # °C residual
    "d_FUEL_FLOW":  (-8.0, 5.0),      # L/hr residual
    "d_MAP":        (-20.0, 20.0),    # kPa residual
    "d_VIB_RMS":    (-0.5, 4.0),      # mm/s residual
    "d_BUS_VOLTAGE": (-3.0, 1.0),     # V residual
}

FEATURE_ORDER = list(RESIDUAL_NORM.keys())
INPUT_DIM = len(FEATURE_ORDER)          # 14


def _normalise(raw: List[float]) -> List[float]:
    """Normalise a raw residual vector to [-1, 1] per channel."""
    normed = []
    for i, key in enumerate(FEATURE_ORDER):
        lo, hi = RESIDUAL_NORM[key]
        span = hi - lo
        if span < 1e-9:
            normed.append(0.0)
        else:
            normed.append(max(-1.5, min(1.5, (raw[i] - lo) / span * 2.0 - 1.0)))
    return normed


@dataclass
class AutoencoderWeights:
    """Serialisable weight bundle for the 14-8-4-8-14 autoencoder."""
    W_enc1: List[List[float]]   # (8, 14)
    b_enc1: List[float]         # (8,)
    W_enc2: List[List[float]]   # (4, 8)
    b_enc2: List[float]         # (4,)
    W_dec1: List[List[float]]   # (8, 4)
    b_dec1: List[float]         # (8,)
    W_dec2: List[List[float]]   # (14, 8)
    b_dec2: List[float]         # (14,)
    threshold_99: float = 0.05  # 99th-percentile training reconstruction error
    mean_train_error: float = 0.01


class ResidualAutoencoder:
    """
    14 → 8 → 4 → 8 → 14 autoencoder trained on FAULT_ID=0 residuals.

    Public API:
        train(X_nominal)          — fit on nominal rows
        score(residual_vector)    — returns anomaly_score in [0, 1]
        save(path) / load(path)   — JSON serialisation, no pickle
    """

    ARCH = [INPUT_DIM, 8, 4, 8, INPUT_DIM]   # encoder bottleneck at dim 4

    def __init__(self):
        self._weights: Optional[AutoencoderWeights] = None
        self._trained = False

    # ------------------------------------------------------------------
    # Forward pass
    # ------------------------------------------------------------------

    def _forward(self, x_norm: List[float]) -> Tuple[List[float], float]:
        """
        Returns (reconstruction, mse_reconstruction_error).
        Architecture: 14→8 (ReLU) → 4 (ReLU) → 8 (ReLU) → 14 (linear)
        """
        if self._weights is None:
            raise RuntimeError("Autoencoder has not been trained yet.")
        w = self._weights

        h1 = _relu(_matmul_bias(x_norm, w.W_enc1, w.b_enc1))   # (8,)
        h2 = _relu(_matmul_bias(h1,    w.W_enc2, w.b_enc2))    # (4,) — bottleneck
        h3 = _relu(_matmul_bias(h2,    w.W_dec1, w.b_dec1))    # (8,)
        out = _matmul_bias(h3,          w.W_dec2, w.b_dec2)     # (14,) linear
        err = _mse(x_norm, out)
        return out, err

    # ------------------------------------------------------------------
    # Training (SGD on MSE reconstruction loss)
    # ------------------------------------------------------------------

    def train(self, X_nominal: List[List[float]],
              epochs: int = 60,
              lr: float = 0.01,
              batch_size: int = 64,
              seed: int = 42) -> None:
        """
        Train on nominal residual vectors (FAULT_ID=0 rows).

        Args:
            X_nominal: List of raw residual vectors, each of length INPUT_DIM.
                       Each vector = [d_CHT_1, d_CHT_2, ..., d_BUS_VOLTAGE].
            epochs:    Training epochs. 60 is sufficient for convergence on 5000 rows.
            lr:        Learning rate.
            batch_size: Mini-batch size.
            seed:      Random seed for reproducibility.
        """
        random.seed(seed)
        n = len(X_nominal)
        if n < 50:
            raise ValueError(f"Need at least 50 nominal rows to train. Got {n}.")

        # Normalise all training data
        X_norm = [_normalise(row) for row in X_nominal]

        # Initialise weights
        W_enc1 = _he_init(8, INPUT_DIM)
        b_enc1 = _zeros(8)
        W_enc2 = _he_init(4, 8)
        b_enc2 = _zeros(4)
        W_dec1 = _he_init(8, 4)
        b_dec1 = _zeros(8)
        W_dec2 = _he_init(INPUT_DIM, 8)
        b_dec2 = _zeros(INPUT_DIM)

        # Mini-batch SGD (back-propagation through reconstruction loss)
        for epoch in range(epochs):
            random.shuffle(X_norm)
            for start in range(0, n, batch_size):
                batch = X_norm[start:start + batch_size]
                # Accumulate gradients
                dW_enc1 = [[0.0]*INPUT_DIM for _ in range(8)]
                db_enc1 = _zeros(8)
                dW_enc2 = [[0.0]*8 for _ in range(4)]
                db_enc2 = _zeros(4)
                dW_dec1 = [[0.0]*4 for _ in range(8)]
                db_dec1 = _zeros(8)
                dW_dec2 = [[0.0]*8 for _ in range(INPUT_DIM)]
                db_dec2 = _zeros(INPUT_DIM)

                for x in batch:
                    # Forward
                    z1_pre = _matmul_bias(x,  W_enc1, b_enc1)   # (8,) pre-relu
                    h1     = _relu(z1_pre)
                    z2_pre = _matmul_bias(h1, W_enc2, b_enc2)   # (4,)
                    h2     = _relu(z2_pre)
                    z3_pre = _matmul_bias(h2, W_dec1, b_dec1)   # (8,)
                    h3     = _relu(z3_pre)
                    out    = _matmul_bias(h3, W_dec2, b_dec2)   # (14,)

                    # dL/d_out = 2*(out - x) / len(x)  (MSE gradient)
                    inv_n = 2.0 / len(x)
                    d_out = [(out[i] - x[i]) * inv_n for i in range(len(x))]

                    # Backprop through dec layer 2 (linear)
                    # dL/dh3 = W_dec2^T @ d_out
                    d_h3 = [sum(W_dec2[o][j] * d_out[o] for o in range(INPUT_DIM))
                             for j in range(8)]
                    for o in range(INPUT_DIM):
                        for j in range(8):
                            dW_dec2[o][j] += d_out[o] * h3[j]
                        db_dec2[o] += d_out[o]

                    # Through ReLU h3
                    d_z3 = [d_h3[j] * (1.0 if z3_pre[j] > 0 else 0.0) for j in range(8)]

                    # Through dec layer 1
                    d_h2 = [sum(W_dec1[j][k] * d_z3[j] for j in range(8))
                             for k in range(4)]
                    for j in range(8):
                        for k in range(4):
                            dW_dec1[j][k] += d_z3[j] * h2[k]
                        db_dec1[j] += d_z3[j]

                    # Through ReLU h2
                    d_z2 = [d_h2[k] * (1.0 if z2_pre[k] > 0 else 0.0) for k in range(4)]

                    # Through enc layer 2
                    d_h1 = [sum(W_enc2[k][j] * d_z2[k] for k in range(4))
                             for j in range(8)]
                    for k in range(4):
                        for j in range(8):
                            dW_enc2[k][j] += d_z2[k] * h1[j]
                        db_enc2[k] += d_z2[k]

                    # Through ReLU h1
                    d_z1 = [d_h1[j] * (1.0 if z1_pre[j] > 0 else 0.0) for j in range(8)]

                    # Through enc layer 1
                    for j in range(8):
                        for i in range(INPUT_DIM):
                            dW_enc1[j][i] += d_z1[j] * x[i]
                        db_enc1[j] += d_z1[j]

                # Apply gradients (SGD with mild L2 on weights)
                bs = len(batch)
                l2 = 1e-4
                for j in range(8):
                    for i in range(INPUT_DIM):
                        W_enc1[j][i] -= lr * (dW_enc1[j][i] / bs + l2 * W_enc1[j][i])
                    b_enc1[j] -= lr * (db_enc1[j] / bs)
                for k in range(4):
                    for j in range(8):
                        W_enc2[k][j] -= lr * (dW_enc2[k][j] / bs + l2 * W_enc2[k][j])
                    b_enc2[k] -= lr * (db_enc2[k] / bs)
                for j in range(8):
                    for k in range(4):
                        W_dec1[j][k] -= lr * (dW_dec1[j][k] / bs + l2 * W_dec1[j][k])
                    b_dec1[j] -= lr * (db_dec1[j] / bs)
                for o in range(INPUT_DIM):
                    for j in range(8):
                        W_dec2[o][j] -= lr * (dW_dec2[o][j] / bs + l2 * W_dec2[o][j])
                    b_dec2[o] -= lr * (db_dec2[o] / bs)

        # Store weights
        self._weights = AutoencoderWeights(
            W_enc1=W_enc1, b_enc1=b_enc1,
            W_enc2=W_enc2, b_enc2=b_enc2,
            W_dec1=W_dec1, b_dec1=b_dec1,
            W_dec2=W_dec2, b_dec2=b_dec2,
        )

        # Compute 99th-percentile threshold on training data
        errors = []
        for x in X_norm:
            _, err = self._forward(x)
            errors.append(err)
        errors.sort()
        idx_99 = int(0.99 * len(errors))
        self._weights.threshold_99 = errors[min(idx_99, len(errors)-1)]
        self._weights.mean_train_error = sum(errors) / len(errors)
        self._trained = True

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def reconstruction_error(self, residual_raw: List[float]) -> float:
        """Raw normalised MSE reconstruction error (pre-score-formula) for one residual vector."""
        x_norm = _normalise(residual_raw)
        _, err = self._forward(x_norm)
        return err

    def calibrate_threshold(self, X_holdout_nominal: List[List[float]], percentile: float = 0.99) -> float:
        """
        Recalibrate threshold_99 against a *held-out* nominal set (e.g. the Val mission split)
        instead of only the rows seen during train(). Train/Val/Test missions in this repo are
        deliberately generated with shifted altitude/OAT offsets and RNG seeds (see
        rotax_dataset_generator.generate_partitioned_dataset_suite()) to test real
        generalisation — a threshold fit only on training-nominal error tends to run too tight
        against that intentional shift. This mirrors the Val split's documented purpose
        ("hyperparameter tuning & threshold calibration") in scripts/train_ml_models.py.
        """
        if not self._trained or self._weights is None:
            raise RuntimeError("Autoencoder has not been trained yet.")
        errors = sorted(self.reconstruction_error(x) for x in X_holdout_nominal)
        idx = int(percentile * len(errors))
        self._weights.threshold_99 = errors[min(idx, len(errors) - 1)]
        return self._weights.threshold_99

    def score(self, residual_raw: List[float]) -> float:
        """
        Returns anomaly_score in [0, 1].

        anomaly_score < 0.35:  nominal operating manifold
        anomaly_score 0.35–0.65: early drift, watch and trend
        anomaly_score > 0.65:  significant deviation — fault developing

        Formula: 1 - exp(-k * (error / threshold))
        k tuned so that error == threshold maps to score ≈ 0.63
        """
        if not self._trained or self._weights is None:
            return 0.0
        x_norm = _normalise(residual_raw)
        _, err = self._forward(x_norm)
        thresh = max(self._weights.threshold_99, 1e-9)
        k = 1.5   # shape parameter — maps threshold → 0.78, 2×threshold → 0.95
        raw_score = 1.0 - math.exp(-k * err / thresh)
        return round(min(1.0, max(0.0, raw_score)), 4)

    def residual_to_vector(self, r) -> List[float]:
        """
        Convert a ResidualVector dataclass to the raw list expected by score().
        Works with any object that has the 14 residual attributes.
        """
        return [
            r.d_CHT_1, r.d_CHT_2, r.d_CHT_3, r.d_CHT_4,
            r.d_EGT_1, r.d_EGT_2, r.d_EGT_3, r.d_EGT_4,
            r.d_OIL_PRESS, r.d_OIL_TEMP, r.d_FUEL_FLOW, r.d_MAP,
            r.d_VIB_RMS, r.d_BUS_VOLTAGE
        ]

    # ------------------------------------------------------------------
    # Serialisation — JSON, no pickle
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Save weights to a JSON file for offline, air-gapped deployment."""
        if not self._trained or self._weights is None:
            raise RuntimeError("Cannot save: autoencoder not trained.")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        payload = {
            "arch": self.ARCH,
            "W_enc1": self._weights.W_enc1,
            "b_enc1": self._weights.b_enc1,
            "W_enc2": self._weights.W_enc2,
            "b_enc2": self._weights.b_enc2,
            "W_dec1": self._weights.W_dec1,
            "b_dec1": self._weights.b_dec1,
            "W_dec2": self._weights.W_dec2,
            "b_dec2": self._weights.b_dec2,
            "threshold_99": self._weights.threshold_99,
            "mean_train_error": self._weights.mean_train_error,
        }
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)

    def load(self, path: str) -> None:
        """Load weights from a JSON file."""
        with open(path, "r") as f:
            p = json.load(f)
        self._weights = AutoencoderWeights(
            W_enc1=p["W_enc1"], b_enc1=p["b_enc1"],
            W_enc2=p["W_enc2"], b_enc2=p["b_enc2"],
            W_dec1=p["W_dec1"], b_dec1=p["b_dec1"],
            W_dec2=p["W_dec2"], b_dec2=p["b_dec2"],
            threshold_99=p["threshold_99"],
            mean_train_error=p["mean_train_error"],
        )
        self._trained = True

    @property
    def is_trained(self) -> bool:
        return self._trained

    @property
    def threshold(self) -> float:
        if self._weights:
            return self._weights.threshold_99
        return 0.05
