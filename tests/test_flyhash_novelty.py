"""
Tests for backend.ml.flyhash_novelty -- the FlyHash sparse-coding novelty layer.

Verifies the algorithm does what it is supposed to (sparsity, similar-input
stability, calibration-driven novelty detection) and stays inside a real
edge-latency budget, independent of whether it is wired into the live
pipeline.
"""

import time

import numpy as np
import pytest

from backend.ml.crank_diagnostics import order_features
from backend.ml.flyhash_novelty import (
    FEATURE_ORDER,
    FlyHashEncoder,
    FlyNoveltyDetector,
    SparseRandomProjection,
    residual_and_order_features,
)
from backend.physics.thermo_model import ResidualVector


def test_feature_vector_has_documented_dimensionality():
    residuals = ResidualVector(d_CHT_1=5.0, d_OIL_PRESS=-0.3)
    vec = residual_and_order_features(residuals, order_feats=None)
    assert vec.shape == (len(FEATURE_ORDER),)
    assert vec[FEATURE_ORDER.index("d_CHT_1")] == 5.0
    assert vec[FEATURE_ORDER.index("d_OIL_PRESS")] == pytest.approx(-0.3)


def test_feature_vector_accepts_real_order_features():
    """Sanity: the real order_features() output plugs in without KeyErrors."""
    orders = list(np.arange(0.1, 6.0, 0.1))
    mags = list(np.abs(np.random.default_rng(1).normal(1.0, 0.3, len(orders))))
    feats = order_features(orders, mags)
    vec = residual_and_order_features(ResidualVector(), feats)
    assert vec.shape == (len(FEATURE_ORDER),)
    assert np.isfinite(vec).all()


def test_projection_row_fan_in_is_exact():
    proj = SparseRandomProjection(input_dim=26, expansion=20, fan_in=6)
    assert proj.weights.shape == (26 * 20, 26)
    nonzero_per_row = np.count_nonzero(proj.weights, axis=1)
    assert (nonzero_per_row == 6).all(), "every row must have exactly fan_in non-zero entries"


def test_encoder_sparsity_matches_target():
    encoder = FlyHashEncoder(input_dim=26, sparsity=0.05)
    rng = np.random.default_rng(0)
    x = rng.normal(size=26)
    code = encoder.encode(x)
    active_frac = code.sum() / code.size
    assert active_frac == pytest.approx(0.05, abs=0.01)


def test_similar_inputs_produce_similar_codes():
    """The defining LSH property: nearby inputs should land on substantially
    overlapping sparse codes, not unrelated ones."""
    encoder = FlyHashEncoder(input_dim=26, sparsity=0.05, seed=5)
    rng = np.random.default_rng(2)
    x = rng.normal(size=26)
    x_near = x + rng.normal(scale=0.01, size=26)   # tiny perturbation
    x_far = rng.normal(size=26)                     # unrelated point

    code_x = encoder.encode(x)
    code_near = encoder.encode(x_near)
    code_far = encoder.encode(x_far)

    overlap_near = np.sum(code_x & code_near) / max(1, code_x.sum())
    overlap_far = np.sum(code_x & code_far) / max(1, code_x.sum())

    assert overlap_near > overlap_far, (
        f"a near-duplicate input (overlap={overlap_near:.2f}) should share more "
        f"active bits than an unrelated one (overlap={overlap_far:.2f})"
    )
    assert overlap_near > 0.5


def test_detector_uncalibrated_never_flags_novel():
    detector = FlyNoveltyDetector(input_dim=26, calibration_frames=50)
    rng = np.random.default_rng(9)
    report = detector.score(rng.normal(size=26))
    assert report.calibrated is False
    assert report.is_novel is False, "must not flag novelty before calibration completes"


def test_detector_flags_genuine_outlier_after_calibration():
    """Calibrate on a tight nominal cluster, then confirm a point far outside
    that cluster is flagged, and points inside it are not."""
    detector = FlyNoveltyDetector(input_dim=26, calibration_frames=100,
                                  novelty_threshold=0.5, seed=11)
    rng = np.random.default_rng(11)
    nominal_center = rng.normal(scale=1.0, size=26)

    for _ in range(150):
        sample = nominal_center + rng.normal(scale=0.05, size=26)
        detector.observe_nominal(sample)

    assert detector.calibrated

    # In-distribution point: low novelty.
    in_dist = nominal_center + rng.normal(scale=0.05, size=26)
    report_in = detector.score(in_dist)
    assert report_in.is_novel is False, f"in-distribution novelty={report_in.novelty_score}"

    # Genuine outlier: large offset in a direction never seen during calibration.
    outlier = nominal_center + 50.0
    report_out = detector.score(outlier)
    assert report_out.is_novel is True, f"outlier novelty={report_out.novelty_score}"
    assert report_out.novelty_score > report_in.novelty_score


def test_reset_calibration_clears_state():
    detector = FlyNoveltyDetector(input_dim=26, calibration_frames=5)
    rng = np.random.default_rng(4)
    for _ in range(10):
        detector.observe_nominal(rng.normal(size=26))
    assert detector.calibrated
    detector.reset_calibration()
    assert not detector.calibrated
    assert detector.score(rng.normal(size=26)).calibrated is False


def test_edge_latency_budget():
    """One score() call must stay well inside a 20 Hz (50 ms) frame budget --
    in practice this needs to be a small fraction of that, since it shares
    the frame with the rest of the 9-stage pipeline. Budget set generously
    at 5 ms to be robust to slow CI machines while still catching a real
    regression (e.g. accidentally switching to a dense O(m log m) sort)."""
    detector = FlyNoveltyDetector(input_dim=26, calibration_frames=50)
    rng = np.random.default_rng(6)
    for _ in range(60):
        detector.observe_nominal(rng.normal(size=26))

    x = rng.normal(size=26)
    n = 200
    t0 = time.perf_counter()
    for _ in range(n):
        detector.score(x)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0 / n
    assert elapsed_ms < 5.0, f"mean score() latency {elapsed_ms:.3f} ms exceeds 5 ms budget"


def test_reproducible_with_fixed_seed():
    """Same seed must give the same projection -- calibration state is only
    meaningful if the encoding is deterministic across process restarts."""
    e1 = FlyHashEncoder(input_dim=26, seed=42)
    e2 = FlyHashEncoder(input_dim=26, seed=42)
    x = np.random.default_rng(0).normal(size=26)
    assert np.array_equal(e1.encode(x), e2.encode(x))


def test_fan_in_cannot_exceed_input_dim():
    with pytest.raises(ValueError):
        SparseRandomProjection(input_dim=4, fan_in=6)
