"""Federated Aggregator with Differential Privacy and Canary Validation Gate (W7, INN-04, D28).

Implements:
1. Federated Averaging (FedAvg) weighted by base sample counts.
2. Differential privacy Laplace/Gaussian perturbation for privacy bounds.
3. Canary Validation Gate: evaluates candidate global model on a holdout benchmark before releasing to fleet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

from backend.federation.colony import ColonyModelDelta


@dataclass
class AggregationResult:
    round_id: int
    num_participating_colonies: int
    total_samples: int
    global_weights: Dict[str, np.ndarray]
    canary_passed: bool
    canary_holdout_loss: float
    message: str


class FederatedAggregator:
    """Central / HQ orchestrator for cross-base federated model learning."""

    def __init__(
        self,
        canary_holdout_features: np.ndarray,
        canary_holdout_labels: np.ndarray,
        canary_loss_threshold: float = 1.0,
        enable_dp: bool = False,
        dp_epsilon: float = 1.0,
    ) -> None:
        self.canary_x = canary_holdout_features
        self.canary_y = canary_holdout_labels
        self.canary_threshold = canary_loss_threshold
        self.enable_dp = enable_dp
        self.dp_epsilon = dp_epsilon

        self.current_global_weights: Dict[str, np.ndarray] = {
            "w1": np.zeros((13, 32), dtype=np.float32),
            "b1": np.zeros(32, dtype=np.float32),
        }
        self.best_loss = float("inf")

    def aggregate_round(self, round_id: int, deltas: List[ColonyModelDelta]) -> AggregationResult:
        """Perform FedAvg over incoming base updates with canary gating."""
        if not deltas:
            return AggregationResult(
                round_id=round_id,
                num_participating_colonies=0,
                total_samples=0,
                global_weights=self.current_global_weights,
                canary_passed=False,
                canary_holdout_loss=self.best_loss,
                message="No colony updates submitted",
            )

        total_samples = sum(max(1, d.num_samples) for d in deltas)

        # FedAvg weighted sum
        candidate_weights: Dict[str, np.ndarray] = {}
        first_delta = deltas[0]
        for k in first_delta.weights:
            candidate_weights[k] = np.zeros_like(first_delta.weights[k])

        for d in deltas:
            weight_factor = max(1, d.num_samples) / total_samples
            for k in candidate_weights:
                candidate_weights[k] += weight_factor * d.weights[k]

        # Differential privacy noise if enabled
        if self.enable_dp:
            for k in candidate_weights:
                noise = np.random.laplace(0.0, 1.0 / (self.dp_epsilon * total_samples), size=candidate_weights[k].shape)
                candidate_weights[k] += noise.astype(candidate_weights[k].dtype)

        # --- Canary Validation Gate ---
        canary_loss = self._evaluate_canary(candidate_weights)
        canary_passed = bool(canary_loss <= self.canary_threshold)

        if canary_passed:
            self.current_global_weights = candidate_weights
            self.best_loss = min(self.best_loss, canary_loss)
            msg = f"Canary passed (loss={canary_loss:.4f} <= {self.canary_threshold}). Global model updated."
        else:
            msg = f"Canary REJECTED candidate update (loss={canary_loss:.4f} > threshold {self.canary_threshold}). Retained previous weights."

        return AggregationResult(
            round_id=round_id,
            num_participating_colonies=len(deltas),
            total_samples=total_samples,
            global_weights=self.current_global_weights,
            canary_passed=canary_passed,
            canary_holdout_loss=canary_loss,
            message=msg,
        )

    def _evaluate_canary(self, weights: Dict[str, np.ndarray]) -> float:
        if len(self.canary_x) == 0:
            return 0.0
        hidden = np.tanh(self.canary_x @ weights["w1"] + weights["b1"])
        preds = np.mean(hidden, axis=1)
        return float(np.mean((preds - self.canary_y) ** 2))
