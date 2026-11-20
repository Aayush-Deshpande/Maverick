"""M2-03 alerts (P Step 2.4, U3): one alert per cause with first/last time and count, acknowledge, shelve with
automatic un-shelve, root-cause grouping, master warning/caution, an action on every alert."""
from types import SimpleNamespace

import pytest

from backend.physics.engine_config import load_engine_config
from backend.status.alerts import AlertManager
from backend.status.evaluator import StatusEvaluator

ENGINE = "rotax_912is"


def frame(**kw):
    base = dict(rpm=5000.0, prop_rpm=None, map_kpa=None, coolant_t=85.0, oil_p=3.5, oil_t=100.0, fuel_flow=None,
                fuel_p=3.0, fuel_t=None, rail_p=None, gearbox_t=None, bus_v=None, cht=[100.0] * 4, egt=[800.0] * 4)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
def pair():
    return StatusEvaluator(load_engine_config(ENGINE)), AlertManager()


def step(pair, t, f, **kw):
    ev, am = pair
    return am.update(t, ev.evaluate(t, f, engine_state="RUNNING", **kw))


def test_one_alert_per_cause_with_times_count_and_action(pair):
    a = step(pair, 0.0, frame(oil_p=1.5))
    assert len(a) == 1 and a[0].level == "CAUTION" and a[0].action and a[0].group == "lubrication"
    a = step(pair, 5.0, frame(oil_p=1.5))
    assert len(a) == 1 and a[0].first_s == 0.0 and a[0].last_s == 5.0 and a[0].count == 1
    for t in range(6, 30):                                          # clears after the hysteresis hold
        a = step(pair, float(t), frame(oil_p=3.5))
    assert a and not a[0].active                                    # stays listed until acknowledged
    a = step(pair, 31.0, frame(oil_p=1.5))
    assert a[0].active and a[0].count == 2                          # re-raised: second activation


def test_master_caution_and_warning_follow_acknowledge(pair):
    ev, am = pair
    step(pair, 0.0, frame(oil_p=1.5))
    assert am.master() == {"warning": False, "caution": True}
    am.acknowledge()
    assert am.master() == {"warning": False, "caution": False}
    step(pair, 1.0, frame(oil_t=135.0))
    assert am.master()["warning"] is True


def test_shelve_and_automatic_unshelve(pair):
    ev, am = pair
    a = step(pair, 0.0, frame(oil_p=1.5))[0]
    am.shelve(a.id, 0.0, 60.0)
    assert am.master()["caution"] is False
    step(pair, 30.0, frame(oil_p=1.5))
    assert am.alerts[a.id].shelved_until == 60.0
    step(pair, 61.0, frame(oil_p=1.5))
    assert am.alerts[a.id].shelved_until is None and am.master()["caution"] is True


def test_no_go_cannot_be_shelved_and_shelve_is_time_limited(pair):
    ev, am = pair
    a = step(pair, 0.0, frame(oil_t=135.0))
    nogo = next(x for x in a if x.level == "NO-GO")
    with pytest.raises(ValueError):
        am.shelve(nogo.id, 0.0, 60.0)
    caution = step(pair, 1.0, frame(oil_t=135.0, oil_p=1.5))
    c = next(x for x in caution if x.level == "CAUTION")
    assert am.shelve(c.id, 1.0, 10 ** 6).shelved_until == 1.0 + am.max_shelve_s


def test_cleared_and_acknowledged_alerts_leave_the_list(pair):
    ev, am = pair
    step(pair, 0.0, frame(oil_p=1.5))
    for t in range(1, 30):
        step(pair, float(t), frame(oil_p=3.5))
    am.acknowledge()
    assert step(pair, 31.0, frame(oil_p=3.5)) == []
