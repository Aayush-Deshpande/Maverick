"""M3-04 autoencoder novelty scorer with an EVT (peaks-over-threshold, Generalized Pareto) threshold: the tail fit
hits the false-alarm target beyond what the held-out sample can resolve, broken normal structure scores high,
the scorer is deterministic, and in the detector it is a side channel that never changes the main alarm."""
import numpy as np
from sklearn.metrics import roc_auc_score

from backend.detect import ResidualDetector
from backend.detect.autoencoder import AutoencoderScorer
from backend.detect.cusum import load_detect_config
from backend.sources import PlantSource

CFG = load_detect_config()["autoencoder"]


def _structured(rng, n):
    """13 features driven by 3 latent factors + small noise: the kind of structure an autoencoder can learn."""
    mix = np.random.default_rng(0).normal(size=(3, 13))
    return rng.normal(size=(n, 3)) @ mix + 0.05 * rng.normal(size=(n, 13))


def test_evt_threshold_meets_a_rate_below_the_holdout_resolution():
    """alpha = 1e-4 from 2000 held-out scores (an empirical quantile needs >= 10000): exceedance on 400k fresh
    samples from the same heavy-tailed law stays within a factor of 2 of alpha."""
    ae, alpha = AutoencoderScorer(CFG), 1e-4
    rng = np.random.default_rng(1)
    h = ae.evt_threshold(rng.lognormal(0.0, 0.6, 2000), alpha)
    fresh = np.random.default_rng(1001).lognormal(0.0, 0.6, 400_000)
    rate = float(np.mean(fresh > h))
    assert alpha / 2 <= rate <= 2 * alpha, rate
    assert ae.gpd["p_u"] > 0 and ae.gpd["scale"] > 0


def test_broken_structure_scores_high_and_fit_is_deterministic():
    train = _structured(np.random.default_rng(2), 3000)
    a, b = AutoencoderScorer(CFG).fit(train), AutoencoderScorer(CFG).fit(train)
    test_nom = _structured(np.random.default_rng(1002), 500)
    test_bad = test_nom.copy()
    test_bad[:, 4] += 1.0 * train[:, 4].std()          # one feature leaves the learned subspace
    s_nom, s_bad = a.score(test_nom), a.score(test_bad)
    auc = roc_auc_score(np.r_[np.zeros(500), np.ones(500)], np.r_[s_nom, s_bad])
    assert auc > 0.95, auc
    assert np.array_equal(s_nom, b.score(test_nom))


def test_detector_novelty_is_a_side_channel():
    src = PlantSource("rotax_914", seed=3)
    frames = []
    for i in range(700):
        f, _ = src.step(5.0, throttle_pct=60 if (i // 60) % 2 == 0 else 75, altitude_ft=9000, oat_c=10)
        if i >= 24:
            frames.append(f)
    det = ResidualDetector.calibrate(frames, alpha=0.01)
    assert det.thresholds["ae_evt"] > 0
    f, _ = src.step(5.0, throttle_pct=60, altitude_ft=9000, oat_c=10)
    r = det.score(f)
    assert set(r.novelty) == {"score", "ratio", "raw", "alarm"}
    assert "ae_evt" not in r.scores                     # not one of the scorers OR-ed into the raw alarm
