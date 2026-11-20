"""M3-02 two-sided CUSUM on residual z-scores: slow drifts that never cross a one-frame threshold are caught."""
import numpy as np

from backend.detect.cusum import TwoSidedCusum
from backend.detect.detector import conformal_threshold

K = 0.5
N_CH = 13


def nominal(rng, n):
    return rng.normal(size=(n, N_CH))


def test_threshold_from_nominal_and_low_false_alarms():
    rng = np.random.default_rng(0)
    c = TwoSidedCusum(N_CH, K)
    h = conformal_threshold(c.run(nominal(rng, 2000)), 0.01)
    fresh = c.run(nominal(np.random.default_rng(1), 2000))
    assert np.mean(fresh > h) < 0.05


def test_sustained_one_sigma_shift_is_caught_quickly():
    rng = np.random.default_rng(2)
    c = TwoSidedCusum(N_CH, K)
    h = conformal_threshold(c.run(nominal(rng, 2000)), 0.01)
    z = nominal(np.random.default_rng(3), 200)
    z[:, 4] += 1.0                                                  # one channel, +1 sigma, never alone beyond ~3.5
    stats = c.run(z)
    first = int(np.argmax(stats > h))
    assert stats.max() > h and first < 60


def test_slow_drift_below_any_one_frame_threshold_accumulates():
    rng = np.random.default_rng(4)
    c = TwoSidedCusum(N_CH, K)
    h = conformal_threshold(c.run(nominal(rng, 2000)), 0.01)
    z = nominal(np.random.default_rng(5), 600)
    z[:, 7] -= np.linspace(0.0, 1.2, 600)                           # creeping cooling-type drift, downward
    assert c.run(z).max() > h
    c.reset()
    for row in z:
        c.update(row)
    name, val = c.top([f"ch{i}" for i in range(N_CH)], 1)[0]
    assert name == "ch7" and val < 0                                # the drifting channel, signed down


def test_shielded_channel_adds_nothing():
    c = TwoSidedCusum(3, K)
    for _ in range(100):
        stat = c.update(np.array([0.0, 0.0, 0.0]))
    assert stat == 0.0
