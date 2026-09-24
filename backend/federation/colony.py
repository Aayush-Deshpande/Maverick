"""Federated Edge Colony Node and Local Update Extraction (W7, INN-04, D28).

Allows forward operating bases / UAVs to train locally and produce model parameter deltas
without centralizing sensitive flight telemetry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class ColonyModelDelta:
    colony_id: str
    round_id: int
    num_samples: int
    weights: Dict[str, np.ndarray]
    metrics: Dict[str, float] = field(default_factory=dict)


class ColonyNode:
    """Local base node managing local training and weight extraction."""

    def __init__(self, colony_id: str) -> None:
        self.colony_id = colony_id
        # Example local model: 2-layer linear projection / frequency memory
        self.local_weights = {
            "w1": np.zeros((13, 32), dtype=np.float32),
            "b1": np.zeros(32, dtype=np.float32),
        }
        self.sample_count = 0

    def local_train_step(self, features: np.ndarray, labels: np.ndarray, lr: float = 0.01) -> float:
        """Simple deterministic gradient step for local adaptation."""
        # features: (N, 13), labels: (N,)
        n = features.shape[0]
        self.sample_count += n

        # Forward
        hidden = np.tanh(features @ self.local_weights["w1"] + self.local_weights["b1"])
        preds = np.mean(hidden, axis=1)
        loss = float(np.mean((preds - labels) ** 2))

        # Gradient step on w1 and b1
        grad_out = (preds - labels)[:, None] / n
        grad_w1 = features.T @ (grad_out * (1.0 - hidden ** 2))
        grad_b1 = np.sum(grad_out * (1.0 - hidden ** 2), axis=0)

        self.local_weights["w1"] -= lr * grad_w1
        self.local_weights["b1"] -= lr * grad_b1
        return loss

    def get_model_delta(self, round_id: int) -> ColonyModelDelta:
        return ColonyModelDelta(
            colony_id=self.colony_id,
            round_id=round_id,
            num_samples=self.sample_count,
            weights={k: v.copy() for k, v in self.local_weights.items()},
            metrics={"sample_count": float(self.sample_count)},
        )

    def apply_global_weights(self, global_weights: Dict[str, np.ndarray]) -> None:
        for k, v in global_weights.items():
            if k in self.local_weights:
                self.local_weights[k] = v.copy()
