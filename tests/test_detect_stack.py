"""W1/W11: calibrated-residual detector, conformal thresholds, persistence gate, reservoir tier."""
import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from backend.detect import (PersistenceGate, Reservoir, ResidualDetector, TailCalibration,
                            conformal_threshold)
from backend.sources import PlantSource

OPS = [(45, 2000, 25), (60, 9000, 10), (75, 12000, 0), (90, 18000, -15), (70, 5000, 30)]


def run(engine, seed, fault=None, n=260, dt=5.0, settle=24, src=None, run_seed=None):
    """One flight of tail ``seed`` (seed fixes build variation AND noise stream). Pass ``src`` to continue the
    same physical engine for a fresh flight; ``run_seed`` varies the operating-point schedule."""
    rng = np.random.default_rng(seed if run_seed is None else run_seed)
    src = src or PlantSource(engine, seed=seed)
    if fault:
        src.inject_fault(fault, cylinder=int(rng.integers(1, src.n_cylinders + 1)), severity=0.9, ramp_sec=240.0)
    op, out = OPS[0], []
    for i in range(n):
        if i % 30 == 0:
            op = OPS[int(rng.integers(len(OPS)))]
        f, _ = src.step(dt, throttle_pct=op[0], altitude_ft=op[1], oat_c=op[2])
        if i >= settle:
            out.append(f)
    return out


@pytest.fixture(scope="module")
def tail914():
    src = PlantSource("rotax_914", seed=0)
    frames = run("rotax_914", 0, n=700, src=src, run_seed=100)
    return src, ResidualDetector.calibrate(frames, alpha=0.01)


@pytest.fixture(scope="module")
def det914(tail914):
    return tail914[1]


def test_frames_carry_command_fields():
    f = run("rotax_914", 0, n=30)[-1]
    assert f.throttle is not None and f.alt is not None and f.oat is not None


def test_calibration_roundtrip(tmp_path, det914):
    p = tmp_path / "tail.json"
    det914.cal.save(p)
    cal2 = TailCalibration.load(p)
    f = run("rotax_914", 5, n=40)[-1]
    assert np.allclose(det914.cal.z(f), cal2.z(f))
    assert cal2.n_cyl == 4 and len(cal2.feature_names()) == 13


def test_conformal_threshold_quantile():
    s = np.arange(100, dtype=float)
    assert conformal_threshold(s, 0.1) == 90.0          # ceil(101*0.9)=91 -> 91st smallest = 90
    assert conformal_threshold(s, 0.5) == 50.0


def test_false_alarm_rate_bounded_on_fresh_nominal(tail914):
    src, det914 = tail914                      # same physical engine, later flight
    frames = run("rotax_914", 0, n=500, src=src, run_seed=101)
    raw = [det914.score(f).raw_alarm for f in frames]
    # three scorers OR-ed at alpha=0.01 each: union bound 3%, allow slack for finite sample
    assert np.mean(raw) < 0.08


def test_calibration_is_per_tail(tail914, det914):
    """A different tail (other build variation) is NOT covered by this tail's calibration: this is why
    the design is 'N calibrations, not N detectors' (D31) and why a new tail needs its own nominal run."""
    other = run("rotax_914", 999, n=300)
    far_other = np.mean([det914.score(f).raw_alarm for f in other])
    assert far_other > 0.2


@pytest.mark.parametrize("fault", ["MISFIRE", "COOLING_DEGRADATION", "OIL_PRESSURE_LOSS"])
def test_detects_faults_and_ranks_above_nominal(tail914, det914, fault):
    nom = run("rotax_914", 0, n=300, src=tail914[0], run_seed=200)
    bad = run("rotax_914", 0, fault=fault, n=300, run_seed=201)[60:]
    s = [max(det914.score(f).ratios.values()) for f in nom] + [max(det914.score(f).ratios.values()) for f in bad]
    y = [0] * len(nom) + [1] * len(bad)
    assert roc_auc_score(y, s) > 0.9


def test_gate_and_evidence(det914):
    det914.gate.reset()
    bad = run("rotax_914", 0, fault="MISFIRE", n=300, run_seed=301)
    res = [det914.score(f) for f in bad]
    assert any(r.confirmed for r in res)
    assert res[-1].top_channels and res[-1].top_channels[0][0].startswith(("cht", "egt"))


def test_persistence_gate():
    g = PersistenceGate(3, 5)
    assert [g.update(x) for x in (1, 0, 1, 0, 1)] == [False, False, False, False, True]


@pytest.mark.parametrize("engine", ["rotax_912is", "vrde_jayem_2_2l"])
def test_engine_agnostic_same_code_path(engine):
    src = PlantSource(engine, seed=3)
    d = ResidualDetector.calibrate(run(engine, 3, n=700, src=src, run_seed=1), alpha=0.01)
    bad = run(engine, 3, fault="COOLING_DEGRADATION", n=300, run_seed=401)[60:]
    nom = run(engine, 3, n=300, src=src, run_seed=402)
    s = [max(d.score(f).ratios.values()) for f in nom + bad]
    assert roc_auc_score([0] * len(nom) + [1] * len(bad), s) > 0.85


def test_rejects_too_few_frames():
    with pytest.raises(ValueError):
        ResidualDetector.calibrate(run("rotax_914", 0, n=80), alpha=0.01)


def test_reservoir_random_streams_and_separates():
    cal = TailCalibration.fit(run("rotax_914", 0, n=300))
    def seq(seed, fault=None):
        return np.vstack([cal.features(cal.z(f)) for f in run("rotax_914", 0, fault, n=200, run_seed=seed)])
    train = [seq(s) for s in (10, 11)] + [seq(s, "COOLING_DEGRADATION") for s in (12, 13)]
    r = Reservoir.random(13, n=300).fit(train, [0, 0, 1, 1])
    r.reset()
    labs = [r.predict_step(u)[0] for u in seq(20, "COOLING_DEGRADATION")]
    assert np.mean(np.array(labs[-60:]) == 1) > 0.7


def test_federated_fly_bloom_merge_equals_pooled():
    """W12: colony merge = weighted mean of frequency memories; no raw data leaves a tail."""
    from backend.detect import FlyBloomScorer
    rng = np.random.default_rng(0)
    A, B = rng.normal(size=(300, 13)), rng.normal(0.2, 1.1, size=(500, 13))
    a, b, pooled = FlyBloomScorer(13).fit(A), FlyBloomScorer(13).fit(B), FlyBloomScorer(13).fit(np.vstack([A, B]))
    a.merge(b, len(A), len(B))
    assert np.allclose(a.freq, pooled.freq)
    probe = rng.normal(size=(20, 13))
    assert np.allclose(a.score(probe), pooled.score(probe))
