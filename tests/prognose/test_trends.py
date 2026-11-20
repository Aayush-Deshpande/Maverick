"""T-PRG-1 (M4-02): ramped slow faults show a time-to-limit before the limit is reached, and the true crossing time
(noise-free plant value; test-side truth only) lies inside the predicted interval in >= 80 % of the predictions."""
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.stats import theilslopes

from backend.evaluation.tail import calibrated
from backend.prognose.trends import TrendTracker
from backend.status.evaluator import frame_readings

TRUE_ATTR = {"coolant_t": "coolant_c", "oil_t": "oil_c"}
RUNS = [("rotax_914", "F21", (85, 6000, 30), 1001), ("rotax_914", "F25", (85, 6000, 30), 1002),
        ("austro_ae300", "F21", (90, 6000, 30), 1002)]
RAMP_S = 1800


def _run(engine, fault, op, seed):
    src, det = calibrated(engine, seed)
    tr = TrendTracker(src.cfg.limits, det.cal.channel_names(), det.cal.sigma)
    for _ in range(300):
        f, _ = src.step(1.0, *op)
        tr.update(f.t, det.score(f).z_raw, frame_readings(f))
    src.apply(SimpleNamespace(fault_id=fault, cylinder=None, channel=None, severity=1.0, ramp_s=RAMP_S, t0_s=src.now()))
    preds, cross = [], {}
    for i in range(int(RAMP_S * 1.4)):
        f, _ = src.step(1.0, *op)
        tr.update(f.t, det.score(f).z_raw, frame_readings(f))
        for ch, attr in TRUE_ATTR.items():
            lim = (src.cfg.limits.get(ch) or {}).get("warning_high")
            if lim is not None and ch not in cross and getattr(src.last, attr) >= lim:
                cross[ch] = i
        if i % 60 == 0:
            preds += [(i, p) for p in tr.time_to_limit() if p["channel"] in TRUE_ATTR and p["channel"] not in cross]
    return cross, preds


def test_t_prg_1_time_to_limit_precedes_the_crossing_and_covers_it():
    covered = total = 0
    for engine, fault, op, seed in RUNS:
        cross, preds = _run(engine, fault, op, seed)
        assert cross, (engine, fault)                              # the scenario does reach a limit
        ch, t_cross = next(iter(cross.items()))
        before = [(i, p) for i, p in preds if p["channel"] == ch]
        assert before and before[0][0] < t_cross                   # warned before the limit
        covered += sum(i + p["low_s"] <= t_cross <= i + p["high_s"] for i, p in before)
        total += len(before)
    assert covered / total >= 0.8, (covered, total)


def test_flat_residual_gives_no_trend():
    tr = TrendTracker({"oil_t": {"warning_high": 130.0}}, ["oil_t"], [1.0])
    rng = np.random.default_rng(1)
    for k in range(400):
        tr.update(float(k), [rng.normal()], {"oil_t": 100.0 + rng.normal()})
    assert tr.time_to_limit() == []


def test_theilslopes_interval_is_the_documented_api():
    r = theilslopes([1.0, 2.0, 3.1, 4.0], [0.0, 1.0, 2.0, 3.0], alpha=0.95)
    assert r.low_slope <= r.slope <= r.high_slope
    assert r.slope == pytest.approx(1.0)
