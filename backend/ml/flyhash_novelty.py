"""
FlyHash sparse coding for vibration/residual novelty detection.

Not a novel algorithm, and this module does not claim to be one. The fruit
fly's olfactory circuit uses an expand-and-sparsify scheme: ~50 projection
neurons fan out onto ~2,000 Kenyon cells, each sampling roughly 6 of them, and
a single inhibitory neuron silences all but the most excited few percent,
producing a sparse binary code in which similar inputs yield similar codes.
Formalised as **FlyHash** -- a locality-sensitive hash that, unlike classical
LSH, uses sparse random projection plus a sparsifying nonlinearity rather than
dense projection -- and reported to outperform classical LSH in similarity
search (Dasgupta, Stevens & Navlakh, *Science* 2017; Ryali et al., ICML 2020,
https://proceedings.mlr.press/v119/ryali20a.html). A derived Bloom-filter-like
structure has been used for one-pass novelty detection, and this same family
(sparse coding / dictionary learning, hyperdimensional computing) is already
established and, in places, already deployed at the edge for machinery fault
diagnosis -- see docs/study/20_novelty_and_research.md, which found this
family published for over a decade and corrected an earlier claim in this
project that it was novel. Read that document before repeating any claim
about this module in front of a technical panel.

What is actually ours here is the *input*, not the algorithm: order-domain
vibration features (crank_diagnostics.order_features -- physical engine
orders, not abstract channels) fused with physics residuals, encoded and
scored for novelty at the edge under the same bandwidth/compute constraints
documented in docs/study/05_edge_ai.md. That combination -- this feature
set, this deployment constraint -- is the honest scope of the contribution.

Complementary to, not a duplicate of, backend.evaluation.validation.NoveltyGate
(F17). NoveltyGate distrusts a *confident classifier posterior* (low margin,
low top-probability, large distance to a known signature) -- it is downstream
of the Random Forest and needs one to run. This module distrusts a *feature
pattern that has never been seen before*, computed directly from residuals and
vibration order features, upstream of and independent from any classifier. A
compound or genuinely unprecedented fault that happens to produce a confident
(and wrong) single-fault posterior is exactly the case NoveltyGate cannot
catch and this can.

Pipeline: residuals + order features (dense, ~27-dim)
            -> sparse random projection (expand, ~20x, fixed fan-in per row)
            -> winner-take-all (keep the top ~5% of projected values active)
            -> sparse binary code (~m bits, ~5% active)
            -> novelty score: fraction of the code's active bits that were
               never active during the nominal calibration window.

Cost: one sparse matrix-vector product and a partial top-k selection per
frame -- see backend/edge/compressor.py for why that budget matters and
test_flyhash_novelty.py for a measured latency bound.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from backend.physics.thermo_model import ResidualVector

__all__ = [
    "FEATURE_ORDER",
    "residual_and_order_features",
    "SparseRandomProjection",
    "FlyHashEncoder",
    "NoveltyReport",
    "FlyNoveltyDetector",
]

# Fixed, documented feature order. The projection matrix's meaning depends on
# this ordering never changing silently -- if a field is added, append it,
# never insert, or every previously-calibrated detector's "seen" set becomes
# meaningless against the new dimensionality.
_RESIDUAL_FIELDS = (
    "d_CHT_1", "d_CHT_2", "d_CHT_3", "d_CHT_4",
    "d_EGT_1", "d_EGT_2", "d_EGT_3", "d_EGT_4",
    "d_OIL_PRESS", "d_OIL_TEMP", "d_FUEL_FLOW", "d_MAP", "d_VIB_RMS",
)
_ORDER_FIELDS = (
    "ORDER_0.5_MAG", "ORDER_0.5_FRAC", "ORDER_1_MAG", "ORDER_1_FRAC",
    "ORDER_2_MAG", "ORDER_2_FRAC", "ORDER_4_MAG", "ORDER_4_FRAC",
    "ORDER_PEAK", "ORDER_RMS", "ORDER_CREST_FACTOR", "ORDER_KURTOSIS",
    "ORDER_DOMINANT",
)
FEATURE_ORDER: tuple = _RESIDUAL_FIELDS + _ORDER_FIELDS  # 26-dim


def residual_and_order_features(
    residuals: ResidualVector,
    order_feats: Optional[Dict[str, float]] = None,
) -> np.ndarray:
    """Build the fixed-order dense feature vector this module operates on.

    ``order_feats`` is whatever ``crank_diagnostics.order_features()``
    returned for the current window; pass ``None`` when no vibration window
    is ready yet (e.g. still filling the buffer) and those slots are zero --
    the detector still runs on residuals alone, just with less discriminative
    power until vibration catches up.
    """
    order_feats = order_feats or {}
    res_dict = residuals.to_dict() if hasattr(residuals, "to_dict") else dict(residuals)
    vec = np.zeros(len(FEATURE_ORDER), dtype="float64")
    for i, name in enumerate(_RESIDUAL_FIELDS):
        vec[i] = float(res_dict.get(name, 0.0))
    offset = len(_RESIDUAL_FIELDS)
    for i, name in enumerate(_ORDER_FIELDS):
        vec[offset + i] = float(order_feats.get(name, 0.0))
    return vec


class SparseRandomProjection:
    """Fixed (never learned) sparse random projection: d -> m, ~k non-zero
    entries per output row. This is the "expand" half of expand-and-sparsify.

    m/d ~= 20 and k ~= 6 mirror the fly's own PN->KC fan-out ratio and per-KC
    in-degree (Dasgupta et al. 2017); nothing here requires those exact
    numbers, and they are exposed as constructor arguments rather than
    hardcoded so a different regime can be tried without editing this file.
    """

    def __init__(self, input_dim: int, expansion: int = 20, fan_in: int = 6,
                 seed: int = 20260101) -> None:
        if fan_in > input_dim:
            raise ValueError(f"fan_in ({fan_in}) cannot exceed input_dim ({input_dim})")
        self.input_dim = input_dim
        self.output_dim = input_dim * expansion
        rng = np.random.default_rng(seed)
        # Build as a dense (m, d) matrix of mostly zeros. m*d here is at most
        # a few thousand entries (26 * 20 * 26 ~= 13.5k floats, ~108 KB) --
        # a sparse matrix type would be the right call at a larger d, but at
        # this dimensionality dense is simpler and the cost is negligible.
        self.weights = np.zeros((self.output_dim, input_dim), dtype="float64")
        for row in range(self.output_dim):
            cols = rng.choice(input_dim, size=fan_in, replace=False)
            signs = rng.choice([-1.0, 1.0], size=fan_in)
            self.weights[row, cols] = signs

    def project(self, x: np.ndarray) -> np.ndarray:
        return self.weights @ x


class FlyHashEncoder:
    """Sparse random projection + winner-take-all. The "sparsify" half."""

    def __init__(self, input_dim: int, expansion: int = 20, fan_in: int = 6,
                 sparsity: float = 0.05, seed: int = 20260101) -> None:
        if not 0.0 < sparsity < 1.0:
            raise ValueError("sparsity must be in (0, 1)")
        self.projection = SparseRandomProjection(input_dim, expansion, fan_in, seed)
        self.sparsity = sparsity
        self._k = max(1, int(round(self.projection.output_dim * sparsity)))

    @property
    def output_dim(self) -> int:
        return self.projection.output_dim

    def encode(self, x: np.ndarray) -> np.ndarray:
        """Return a boolean array of length output_dim, ~sparsity fraction True."""
        y = self.projection.project(x)
        if self._k >= y.size:
            return np.ones_like(y, dtype=bool)
        # Partial selection (argpartition) rather than a full sort -- O(m)
        # rather than O(m log m), which matters at the edge-latency budget
        # this is meant to run inside.
        threshold_idx = np.argpartition(-y, self._k - 1)[: self._k]
        code = np.zeros_like(y, dtype=bool)
        code[threshold_idx] = True
        return code


@dataclass
class NoveltyReport:
    novelty_score: float          # fraction of active bits never seen during calibration
    is_novel: bool
    calibrated: bool              # False until enough nominal frames have been folded in
    calibration_frames_seen: int
    active_bits: int
    unseen_bits: int


class FlyNoveltyDetector:
    """Calibrate a "seen" activation pattern on nominal flight, then flag
    feature patterns that fall outside anything observed during calibration.

    This is deliberately not a classifier and produces no fault label -- it
    answers one question only: "has the machine ever looked like this
    before?" A `True` here with a confident RF fault label is corroboration;
    a `True` here with a confident RF *nominal* label is exactly the case
    NoveltyGate (F17) cannot see, because there is no classifier disagreement
    to distrust -- only a feature pattern the system has never encountered.
    """

    def __init__(self, input_dim: int = len(FEATURE_ORDER),
                 expansion: int = 20, fan_in: int = 6, sparsity: float = 0.05,
                 calibration_frames: int = 200, novelty_threshold: float = 0.6,
                 seed: int = 20260101) -> None:
        self.encoder = FlyHashEncoder(input_dim, expansion, fan_in, sparsity, seed)
        self.calibration_frames = max(1, calibration_frames)
        self.novelty_threshold = novelty_threshold
        self._seen = np.zeros(self.encoder.output_dim, dtype=bool)
        self._frames_seen = 0

    @property
    def calibrated(self) -> bool:
        return self._frames_seen >= self.calibration_frames

    def observe_nominal(self, x: np.ndarray) -> None:
        """Fold one confirmed-nominal frame's code into the calibration set.
        Call only on frames independently known to be healthy (e.g. the first
        N frames of a sortie, or ground-truth-nominal replay data) -- folding
        in a frame that is actually anomalous teaches the detector to ignore
        that anomaly.
        """
        code = self.encoder.encode(x)
        self._seen |= code
        self._frames_seen += 1

    def score(self, x: np.ndarray) -> NoveltyReport:
        code = self.encoder.encode(x)
        active = int(code.sum())
        if active == 0:
            return NoveltyReport(0.0, False, self.calibrated, self._frames_seen, 0, 0)
        unseen = int(np.sum(code & ~self._seen))
        novelty_score = unseen / active
        is_novel = self.calibrated and novelty_score >= self.novelty_threshold
        return NoveltyReport(
            novelty_score=round(novelty_score, 4),
            is_novel=is_novel,
            calibrated=self.calibrated,
            calibration_frames_seen=self._frames_seen,
            active_bits=active,
            unseen_bits=unseen,
        )

    def reset_calibration(self) -> None:
        self._seen[:] = False
        self._frames_seen = 0
