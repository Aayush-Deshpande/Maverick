"""Characterization tests (B0.9): backend/evaluation/{validation,threshold_baseline}.py"""
from pathlib import Path

import numpy as np
import pytest

from backend.evaluation.threshold_baseline import (
    Limit, ROTAX_914_LIMITS, ThresholdMonitor, compare_detection, false_alarm_rate,
)
from backend.evaluation.validation import (
    NoveltyGate, ResidualShield, ad_scores, validate_against_aces,
)


# ---- ThresholdMonitor -----------------------------------------------------

def test_threshold_debounce_and_levels():
    m = ThresholdMonitor()
    assert m.update(0.0, {"CHT": 140.0}) == []          # exceeded but not yet persistent
    assert m.update(1.0, {"CHT": 140.0}) == []
    new = m.update(2.0, {"CHT": 140.0})                  # persisted 2 s -> both levels
    assert sorted(a.level for a in new) == ["CAUTION", "WARNING"]
    assert m.update(3.0, {"CHT": 140.0}) == []          # latched, no re-alarm
    assert m.first_alarm().t_sec == 2.0
    assert m.first_alarm("WARNING").limit == 135.0
    assert m.first_alarm("WARNING").direction == "HIGH"
    d = m.first_alarm().as_dict()
    assert d["channel"] == "CHT" and d["t_sec"] == 2.0


def test_threshold_glitch_does_not_alarm_and_rearms():
    m = ThresholdMonitor()
    m.update(0.0, {"CHT": 200.0})
    m.update(1.0, {"CHT": 100.0})                        # back inside -> pending cleared
    m.update(2.5, {"CHT": 200.0})
    assert m.alarms == []
    m.update(5.0, {"CHT": 200.0})
    assert len(m.alarms) == 2
    m.update(6.0, {"CHT": 100.0})
    m.update(7.0, {"CHT": 200.0}); m.update(9.5, {"CHT": 200.0})
    assert len(m.alarms) == 4                            # re-armed after clearing
    m.reset()
    assert m.alarms == [] and m.first_alarm() is None


def test_threshold_low_limits_and_unknown_channels():
    m = ThresholdMonitor()
    for t in (0.0, 3.0):
        m.update(t, {"OIL_PRESS": 1.0, "UNKNOWN": 1e9, "CHT": None})
    levels = sorted((a.channel, a.level, a.direction) for a in m.alarms)
    assert levels == [("OIL_PRESS", "CAUTION", "LOW"), ("OIL_PRESS", "WARNING", "LOW")]
    assert set(ROTAX_914_LIMITS) == {"CHT", "EGT", "OIL_TEMP", "OIL_PRESS", "ENGINE_RPM", "BUS_VOLTAGE"}
    assert ROTAX_914_LIMITS["EGT"].warning_high == 900.0


def test_threshold_custom_limits():
    m = ThresholdMonitor({"X": Limit("X", warning_high=1.0, persistence_sec=0.0)})
    assert len(m.update(0.0, {"X": 2.0})) == 1


def test_compare_detection_lead_time():
    r = compare_detection(100.0, 700.0, failure_t=1000.0, fault_onset_t=90.0)
    assert r["lead_time_sec"] == 600.0 and r["lead_time_min"] == 10.0
    assert r["twin_warning_before_failure_sec"] == 900.0
    assert r["baseline_warning_before_failure_sec"] == 300.0
    assert r["twin_detection_latency_sec"] == 10.0
    assert r["twin_detected"] and r["baseline_detected"]
    assert not r["twin_only"] and not r["baseline_only"]
    assert compare_detection(100.0, None)["twin_only"] is True
    assert compare_detection(None, 5.0)["baseline_only"] is True
    assert compare_detection(None, None)["lead_time_sec"] is None


def test_false_alarm_rate():
    r = false_alarm_rate(2, 10.0)
    assert r["false_alarms_per_hour"] == pytest.approx(0.2)
    assert r["hours_between_false_alarms"] == pytest.approx(5.0)
    assert false_alarm_rate(0, 3.0)["hours_between_false_alarms"] == float("inf")
    with pytest.raises(ValueError):
        false_alarm_rate(1, 0.0)


# ---- ResidualShield -------------------------------------------------------

def test_shield_quarantine_recovery_dwell():
    s = ResidualShield(recovery_sec=100.0)
    s.quarantine("a", 0.0)
    assert s.is_quarantined("a") and s.quarantined == {"a"}
    s.report_clean("a", 10.0)
    s.report_clean("a", 109.0)
    assert s.is_quarantined("a")                         # dwell not yet met
    s.report_clean("a", 110.0)
    assert not s.is_quarantined("a")
    s.report_clean("never", 0.0)                         # no-op


def test_shield_dirty_again_resets_dwell():
    s = ResidualShield(recovery_sec=100.0)
    s.quarantine("a", 0.0)
    s.report_clean("a", 10.0)
    s.quarantine("a", 50.0)                              # misbehaves again
    s.report_clean("a", 120.0)
    assert s.is_quarantined("a")


def test_shield_shield_usable_health_index():
    s = ResidualShield()
    s.quarantine("b", 0.0)
    res = {"a": 0.5, "b": 99.0}
    assert s.shield(res) == {"a": 0.5, "b": 0.0}
    assert s.usable(res) == {"a": 0.5}
    h = s.health_index(res)
    assert h["health_index"] == pytest.approx(1.0)       # worst normalised 0.5 <= 1
    assert h["channels_used"] == 1 and h["channels_quarantined"] == 1
    h2 = s.health_index({"a": 3.0})
    assert h2["health_index"] == pytest.approx(1.0 / 3.0, abs=1e-4)
    s2 = ResidualShield(); s2.quarantine("a", 0.0)
    assert s2.health_index({"a": 1.0})["health_index"] is None


# ---- NoveltyGate ----------------------------------------------------------

def test_novelty_gate_decisions():
    g = NoveltyGate()
    ok = g.decide({"MISFIRE": 0.8, "STUCK": 0.1, "OK": 0.1}, distance_to_nearest=1.0)
    assert ok["label"] == "MISFIRE" and ok["confident"] is True
    low = g.decide({"A": 0.4, "B": 0.3, "C": 0.3})
    assert low["label"] == "UNKNOWN" and low["candidate"] == "A" and not low["confident"]
    ambiguous = g.decide({"A": 0.6, "B": 0.55})
    assert ambiguous["label"] == "UNKNOWN" and "ambiguous" in ambiguous["reason"]
    far = g.decide({"A": 0.9, "B": 0.05}, distance_to_nearest=5.0)
    assert far["label"] == "UNKNOWN" and "distance" in far["reason"]
    assert g.decide({})["label"] == "UNKNOWN"


# ---- ad_scores ------------------------------------------------------------

def test_ad_scores_point_adjust_inflates():
    labels = [0] * 10 + [1] * 20 + [0] * 10
    preds = [0] * 10 + [1] + [0] * 19 + [0] * 10       # a single hit inside a 20-long window
    r = ad_scores(preds, labels)
    assert r["point_wise"]["precision"] == 1.0
    assert r["point_wise"]["recall"] == pytest.approx(0.05)
    assert r["point_wise"]["f1"] == pytest.approx(0.0952, abs=1e-3)
    assert r["point_adjusted"]["recall"] == 1.0 and r["point_adjusted"]["f1"] == 1.0
    assert r["f1_inflation"] == pytest.approx(0.9048, abs=1e-3)


def test_ad_scores_perfect_none_and_length_check():
    y = [0, 1, 1, 0]
    assert ad_scores(y, y)["point_wise"]["f1"] == 1.0
    assert ad_scores([0, 0, 0, 0], y)["point_wise"]["f1"] == 0.0
    with pytest.raises(ValueError):
        ad_scores([0], [0, 1])


# ---- validate_against_aces (fake granule) ---------------------------------

class _Granule:
    path = Path("fake.mat")

    def __init__(self, rpm_ok=True):
        rng = np.random.default_rng(0)
        n = 400
        self._d = {
            "ENGINE_RPM": np.full(n, 4000.0) + rng.normal(0, 50, n),
            "ALTITUDE_FT": np.full(n, 5000.0),
            "OAT_C": np.full(n, 10.0),
            "EGT_1": 700.0 + rng.normal(0, 10, n),
        }
        if not rpm_ok:
            del self._d["ENGINE_RPM"]

    def available(self):
        return set(self._d)

    def series(self, name):
        return self._d.get(name)


class _Model:
    def expected(self, frame):
        return {"EGT_1": 690.0 + 0.0 * frame["ENGINE_RPM"]}


def test_validate_against_aces_fake_granule():
    r = validate_against_aces(_Granule(), _Model())
    assert r["in_flight_samples"] == 400
    (c,) = r["comparisons"]
    assert c["channel"] == "EGT_1->EGT_1"
    assert c["bias"] == pytest.approx(-10.0, abs=1.5)
    assert c["mae"] >= abs(c["bias"]) - 1e-6
    assert c["rmse"] >= c["mae"]
    assert "no faults" in r["caveat"]


def test_validate_against_aces_missing_rpm_reports_error():
    r = validate_against_aces(_Granule(rpm_ok=False), _Model())
    assert "error" in r
