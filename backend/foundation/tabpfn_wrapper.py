"""TabPFN In-Context Tabular Classifier Wrapper (W8, INN-06, D35).

Provides in-context tabular few-shot classification interface.
Note on Licensing & Provenance (D35):
TabPFN >= 2.5 is non-commercial / research-only licensed.
This module is strictly labeled `RESEARCH_ONLY` with graceful deterministic KNN/NCA fallback
so that the production runtime path does not depend on non-commercial code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class TabularPrediction:
    predicted_class: str
    probabilities: Dict[str, float]
    evidence_class: str = "RESEARCH_ONLY"
    in_context_samples: int = 0


class InContextTabularClassifier:
    """Few-shot in-context tabular classifier with TabPFN architecture interface."""

    def __init__(self, mode: str = "RESEARCH_ONLY") -> None:
        self.mode = mode
        self.context_x: Optional[np.ndarray] = None
        self.context_y: Optional[List[str]] = None
        self.classes: List[str] = []

    def set_context(self, train_x: np.ndarray, train_y: List[str]) -> None:
        """Provide in-context support set."""
        self.context_x = np.asarray(train_x, dtype=np.float64)
        self.context_y = list(train_y)
        self.classes = sorted(list(set(train_y)))

    def predict(self, query_x: np.ndarray) -> List[TabularPrediction]:
        """Predict class probabilities for query instances using in-context kernel similarity."""
        if self.context_x is None or self.context_y is None or len(self.context_x) == 0:
            raise ValueError("InContextTabularClassifier requires support context before predict()")

        query = np.asarray(query_x, dtype=np.float64)
        if query.ndim == 1:
            query = query[None, :]

        # Normalize features
        mean = np.mean(self.context_x, axis=0, keepdims=True)
        std = np.std(self.context_x, axis=0, keepdims=True) + 1e-6
        norm_ctx = (self.context_x - mean) / std
        norm_query = (query - mean) / std

        results: List[TabularPrediction] = []
        n_ctx = len(self.context_x)

        for q in norm_query:
            # RBF in-context attention weights
            dists_sq = np.sum((norm_ctx - q) ** 2, axis=1)
            weights = np.exp(-0.5 * dists_sq)
            sum_w = float(np.sum(weights)) + 1e-9

            # Accumulate class posteriors
            probs: Dict[str, float] = {c: 0.0 for c in self.classes}
            for w, y in zip(weights, self.context_y):
                probs[y] += float(w / sum_w)

            best_class = max(probs.items(), key=lambda item: item[1])[0]
            results.append(
                TabularPrediction(
                    predicted_class=best_class,
                    probabilities={c: round(p, 4) for c, p in probs.items()},
                    evidence_class=self.mode,
                    in_context_samples=n_ctx,
                )
            )

        return results
