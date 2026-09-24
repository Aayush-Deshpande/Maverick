"""Characterization tests (B0.9): backend/evaluation/{conformal,damage_accumulation,prognostic_metrics}.

These pin CURRENT behaviour. They are not a statement that the numbers are right.
"""
import math
import random

import pytest

from backend.evaluation.conformal import (
    AdaptiveConformal, SplitConformalRUL, coverage_curve, empirical_coverage,
)
from backend.evaluation.damage_accumulation import (
    CoffinManson, Cycle, DamageAccumulator, ShockCoolingLaw,
    accumulate_from_series, extract_turning_points, rainflow_cycles,
)
from backend.evaluation.prognostic_metrics import PrognosticSeries, evaluate


# ---- rainflow / damage ----------------------------------------------------

ASTM_SERIES = [-2, 1, -3, 5, -3, 3, -4, 4, -2]


def test_rainflow_astm_series_cycle_count():
    """NOTE (B0.9 finding): BACKLOG cites '5.0 cycles' for the ASTM series; the
    9-point ASTM E1049 series has 8 ranges, hence exactly 4.0 cycles. A 5.0
    total needs 11 turning points. The invariant total = (n_points-1)/2 is pinned."""
    cycles = rainflow_cycles(ASTM_SERIES)
    assert sum(c.count for c in cycles) == pytest.approx(4.0)
    assert sorted((c.range, c.count) for c in cycles) == sorted(
        [(3.0, 0.5), (4.0, 0.5), (8.0, 0.5), (6.0, 1.0), (9.0, 0.5), (8.0, 0.5), (6.0, 0.5)])
    assert all(c.count in (0.5, 1.0) for c in cycles)


def test_rainflow_total_is_half_the_number_of_ranges():
    pts = [0, 5, -3, 8, 1, 9, -2, 4, 0, 7, -1]   # 11 alternating turning points
    assert sum(c.count for c in rainflow_cycles(pts)) == pytest.approx(5.0)


def test_rainflow_deterministic_and_simple_cases():
    assert rainflow_cycles(ASTM_SERIES) == rainflow_cycles(list(ASTM_SERIES))
    assert rainflow_cycles([]) == [] or sum(c.count for c in rainflow_cycles([])) == 0
    # one up-down-up ramp = 2 half cycles of range 10
    cs = rainflow_cycles([0, 10, 0])
    assert sum(c.count for c in cs) == pytest.approx(1.0)
    assert all(c.range == 10.0 for c in cs)


def test_turning_points_collapse_monotone_runs():
    assert extract_turning_points([0, 1, 2, 3, 2, 1, 2]) == [0, 3, 1, 2]


def test_coffin_manson_threshold_and_monotonic():
    cm = CoffinManson()
    assert cm.cycles_to_failure(12.0) == float("inf")
    assert cm.damage(Cycle(range=5.0, mean=0.0, count=1.0)) == 0.0
    n50, n100 = cm.cycles_to_failure(50.0), cm.cycles_to_failure(100.0)
    assert n50 > n100 > 0
    assert n50 == pytest.approx(1e9 * 50.0 ** -2.6)
    assert cm.damage(Cycle(100.0, 0.0, 1.0)) == pytest.approx(1.0 / n100)
    assert cm.damage(Cycle(100.0, 0.0, 0.5)) == pytest.approx(0.5 / n100)


def test_shock_cooling_only_when_cooling_faster_than_limit():
    s = ShockCoolingLaw()
    assert s.damage_rate(+100.0) == 0.0
    assert s.damage_rate(-28.0) == 0.0
    assert s.damage_rate(-56.0) == pytest.approx(4.0 / 3.0e5)
    assert s.damage_rate(-80.0) > s.damage_rate(-40.0) > 0


def test_accumulator_damage_grows_with_swing_and_is_deterministic():
    times = list(range(0, 400, 1))

    def sortie(amp):
        return [150 + amp * math.sin(2 * math.pi * t / 100) for t in times]

    small = accumulate_from_series("h", times, sortie(5.0))
    big1 = accumulate_from_series("h", times, sortie(60.0))
    big2 = accumulate_from_series("h", times, sortie(60.0))
    assert small.thermal_lcf == 0.0          # swings under 12 C threshold
    assert big1.thermal_lcf > 0.0
    assert big1.thermal_lcf == big2.thermal_lcf
    assert big1.counted_cycles > 0
    d = big1.as_dict()
    assert isinstance(d, dict) and d["component"] == "h"
    assert 0.0 <= big1.life_remaining_fraction <= 1.0


def test_accumulator_shock_cooling_streaming():
    acc = DamageAccumulator("cht")
    temps = [300 - 2.0 * i for i in range(60)]   # 2 C/s = 120 C/min cooling
    for i, T in enumerate(temps):
        acc.update(float(i), T)
    assert acc.state.shock_cooling > 0.0
    acc2 = DamageAccumulator("cht")
    for i in range(60):
        acc2.update(float(i), 200.0)
    assert acc2.state.shock_cooling == 0.0


def test_accumulator_initial_damage_carried():
    acc = DamageAccumulator("x", initial_damage=0.25)
    acc.update(0.0, 100.0)
    assert acc.finalise().thermal_lcf == pytest.approx(0.25)


# ---- conformal ------------------------------------------------------------

def _synthetic(n, rng, sigma=5.0):
    pred = [rng.uniform(10, 100) for _ in range(n)]
    truth = [p + rng.gauss(0, sigma) for p in pred]
    return pred, truth


def test_split_conformal_coverage_on_seeded_set():
    rng = random.Random(0)
    cp, ct = _synthetic(2000, rng)
    tp, tt = _synthetic(5000, rng)
    cf = SplitConformalRUL(normalised=False).calibrate(cp, ct)
    ivs = [cf.interval(p) for p in tp]
    rep = empirical_coverage(ivs, tt)
    assert rep["n"] == 5000
    assert rep["nominal_coverage"] == pytest.approx(0.9)
    # measured 0.917 with this seed; conformal is conservative, never far below nominal
    assert rep["empirical_coverage"] == pytest.approx(0.917, abs=0.01)
    assert rep["empirical_coverage"] >= 0.89
    assert rep["mean_interval_width"] == pytest.approx(16.77, abs=0.05)
    assert cf.n_calibration == 2000


def test_conformal_interval_structure_and_monotonic_in_alpha():
    rng = random.Random(1)
    cp, ct = _synthetic(500, rng)
    cf = SplitConformalRUL(normalised=False).calibrate(cp, ct)
    w = [cf.interval(50.0, alpha=a).width for a in (0.5, 0.2, 0.1, 0.05, 0.01)]
    assert w == sorted(w) and w[0] < w[-1]
    iv = cf.interval(50.0)
    assert iv.lower < 50.0 < iv.upper
    assert iv.contains(50.0) and not iv.contains(1e6)
    assert iv.as_dict()["rul_point"] == 50.0


def test_conformal_uncalibrated_raises_and_length_mismatch():
    with pytest.raises(RuntimeError):
        SplitConformalRUL().interval(1.0)
    with pytest.raises(ValueError):
        SplitConformalRUL().calibrate([1, 2], [1])
    assert math.isnan(empirical_coverage([], [])["empirical_coverage"])


def test_coverage_curve_tracks_diagonal_roughly():
    rng = random.Random(2)
    cp, ct = _synthetic(1500, rng)
    tp, tt = _synthetic(1500, rng)
    rows = coverage_curve(tp, tt, cp, ct)
    assert [r["alpha"] for r in rows] == [0.01, 0.05, 0.1, 0.2, 0.3, 0.5]
    for r in rows:
        assert abs(r["empirical_coverage"] - (1 - r["alpha"])) < 0.06
    covs = [r["empirical_coverage"] for r in rows]
    assert covs == sorted(covs, reverse=True)


def test_adaptive_conformal_tracks_realised_coverage():
    rng = random.Random(3)
    cp, ct = _synthetic(300, rng)
    ac = AdaptiveConformal().calibrate(cp, ct)
    tp, tt = _synthetic(300, rng)
    for p, y in zip(tp, tt):
        iv = ac.interval(p)
        ac.observe(iv, y)
    assert 0.8 <= ac.realised_coverage <= 1.0


# ---- prognostic metrics ---------------------------------------------------

def test_prognostic_series_true_rul_and_validation():
    s = PrognosticSeries([0, 10, 20], [95, 85, 75], 100.0)
    assert list(s.true_rul) == [100.0, 90.0, 80.0]
    with pytest.raises(ValueError):
        PrognosticSeries([0, 1], [1], 10.0)


def test_evaluate_good_predictor_passes_waterfall():
    s = PrognosticSeries(list(range(0, 100, 10)),
                         [105, 92, 78, 71, 58, 49, 38, 29, 18, 9], 100.0)
    r = evaluate(s)
    assert r["ph_passed"] is True
    assert r["prognostic_horizon"] == pytest.approx(100.0)
    assert r["alpha_lambda"] is True
    assert r["relative_accuracy"] == pytest.approx(0.98, abs=0.005)
    assert r["convergence"] == pytest.approx(39.11, abs=0.05)
    assert r["n_predictions"] == 10


def test_evaluate_bad_predictor_gates_later_metrics():
    r = evaluate(PrognosticSeries([0, 50], [500, 500], 100.0))
    assert r["ph_passed"] is False
    assert r["prognostic_horizon"] is None
    assert r["alpha_lambda"] is None
    assert r["relative_accuracy"] is None and r["convergence"] is None
