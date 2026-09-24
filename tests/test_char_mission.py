"""Characterization tests (B0.9): backend/mission/{reliability,prescriptive}.py"""
import pytest

from backend.mission.prescriptive import PrescriptiveAdvisor
from backend.mission.reliability import (
    DEFAULT_COMPONENTS, ISR_18H_PROFILE, ComponentHazard, MissionPhase,
    MissionReliabilityEngine, _wilson_interval,
)


def test_wilson_interval_values():
    lo, hi = _wilson_interval(90, 100)
    assert lo == pytest.approx(0.8256, abs=1e-3)
    assert hi == pytest.approx(0.9448, abs=1e-3)
    lo, hi = _wilson_interval(100, 100)          # does NOT collapse to zero width
    assert lo == pytest.approx(0.9630, abs=1e-3) and hi == pytest.approx(1.0)
    lo, hi = _wilson_interval(0, 100)
    assert lo == 0.0 and hi == pytest.approx(0.0370, abs=1e-3)
    assert _wilson_interval(0, 0) == (0.0, 1.0)
    for s in (0, 1, 50, 99, 100):
        lo, hi = _wilson_interval(s, 100)
        assert 0.0 <= lo <= s / 100 <= hi + 1e-9 and hi <= 1.0


def test_profile_and_stress_factor():
    assert ISR_18H_PROFILE.total_hours == pytest.approx(18.0)
    assert ISR_18H_PROFILE.truncated_to(5.0).total_hours == pytest.approx(5.0)
    d = ISR_18H_PROFILE.derated(0.9)
    assert d.total_hours == pytest.approx(18.0)
    assert [p.power_fraction for p in d.phases] == pytest.approx(
        [p.power_fraction * 0.9 for p in ISR_18H_PROFILE.phases])
    lo = MissionPhase("x", 1.0, power_fraction=0.5).stress_factor
    hi = MissionPhase("x", 1.0, power_fraction=0.9).stress_factor
    assert hi > lo > 0


def test_component_hazard_grows_with_damage():
    c = ComponentHazard("c", 1e-4, damage_exponent=3.0)
    h0 = c.hazard()
    c.damage_fraction = 0.5
    assert c.hazard() == pytest.approx(h0 * 8.0)
    c.damage_fraction = 5.0                       # clamped at 0.999
    assert c.hazard() == pytest.approx(h0 * (1 / 0.001) ** 3)
    c.damage_fraction = 0.5
    assert 0 < c.survival(10) < 1


def test_analytic_reliability_baseline():
    e = MissionReliabilityEngine(seed=1)
    a = e.analytic_reliability(ISR_18H_PROFILE)
    assert a["reliability"] == pytest.approx(0.99625, abs=2e-4)
    assert a["limiting_component"] == "turbocharger"
    assert a["mission_hours"] == pytest.approx(18.0)
    assert len(DEFAULT_COMPONENTS()) == 16
    assert "alternator" not in a["per_component_survival"]      # non-critical excluded
    allc = e.analytic_reliability(ISR_18H_PROFILE, critical_only=False)
    assert allc["reliability"] < a["reliability"]


def test_damage_lowers_reliability_and_derate_raises_it():
    e = MissionReliabilityEngine(seed=2)
    base = e.analytic_reliability(ISR_18H_PROFILE)["reliability"]
    e.set_damage({c.name: 0.8 for c in e.components})
    worn = e.analytic_reliability(ISR_18H_PROFILE)["reliability"]
    assert worn == pytest.approx(0.562, abs=0.01)
    assert worn < base
    e.set_damage({"nonexistent": 0.5})            # unknown names ignored
    fresh = MissionReliabilityEngine()
    derated = fresh.analytic_reliability(ISR_18H_PROFILE.derated(0.8))["reliability"]
    assert derated > fresh.analytic_reliability(ISR_18H_PROFILE)["reliability"]


def test_monte_carlo_seeded_determinism_and_agreement_with_analytic():
    r1 = MissionReliabilityEngine(seed=1).simulate(ISR_18H_PROFILE, n_trials=4000)
    r2 = MissionReliabilityEngine(seed=1).simulate(ISR_18H_PROFILE, n_trials=4000)
    assert r1 == r2
    assert r1["reliability"] == pytest.approx(0.9955, abs=1e-4)
    assert r1["ci_lower"] <= r1["reliability"] <= r1["ci_upper"]
    assert abs(r1["reliability"] - 0.99625) < 0.01
    assert r1["n_trials"] == 4000


def test_assess_verdicts():
    e = MissionReliabilityEngine(seed=1)
    assert e.assess(ISR_18H_PROFILE, 0.5, 2000)["verdict"] == "GO"
    r = e.assess(ISR_18H_PROFILE, 0.99999, 2000)
    assert r["verdict"] in ("MARGINAL", "NO-GO")
    assert "requirement of 1.00" in r["rationale"]


def test_prescriptive_derate_options_shape_and_monotone_cost():
    adv = PrescriptiveAdvisor(MissionReliabilityEngine(seed=3), 0.9, 1500)
    opts = adv.derate_options(ISR_18H_PROFILE)
    assert [o.power_scale for o in opts] == [1.0, 0.95, 0.90, 0.85, 0.80, 0.75]
    assert opts[0].damage_rate_ratio == pytest.approx(1.0)
    assert opts[0].endurance_penalty_min == 0.0
    ratios = [o.damage_rate_ratio for o in opts]
    pens = [o.endurance_penalty_min for o in opts]
    assert ratios == sorted(ratios, reverse=True)
    assert pens == sorted(pens)
    assert opts[1].endurance_penalty_min == pytest.approx(5.0, abs=0.2)
    assert opts[-1].damage_rate_ratio == pytest.approx(0.531, abs=0.01)


def test_prescriptive_advise_go_path():
    adv = PrescriptiveAdvisor(MissionReliabilityEngine(seed=3), 0.9, 1500)
    out = adv.advise(ISR_18H_PROFILE)
    assert out["assessment"]["verdict"] == "GO"
    assert out["replan"] is None
    assert "Sortie may be flown as planned." in out["advisory"]
    assert adv.recommend_derate(ISR_18H_PROFILE).power_scale == 1.0
    rp = adv.replan(ISR_18H_PROFILE)
    assert rp.achievable and rp.changes == []
