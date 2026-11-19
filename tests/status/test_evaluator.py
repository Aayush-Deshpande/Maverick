"""M2-01 status evaluator (P Part 4 Step 2.2, D4): T-STS-3..5. T-STS-1 (fault -> registry level) needs the M3
diagnosis hypotheses; T-STS-2 (nominal hour all GO) comes with the held physics batch (PROGRESS Questions 9)."""
from types import SimpleNamespace

import pytest

from backend.physics.engine_config import available_engines, load_engine_config
from backend.sources import PlantSource
from backend.status.evaluator import StatusEvaluator, load_status_config

ENGINE = "rotax_912is"          # its limits carry an rpm rule, a time limit and normal bands (OM-912 i)


def frame(**kw):
    base = dict(rpm=5000.0, prop_rpm=None, map_kpa=None, coolant_t=85.0, oil_p=3.5, oil_t=100.0, fuel_flow=None,
                fuel_p=3.0, fuel_t=None, rail_p=None, gearbox_t=None, bus_v=None, cht=[100.0] * 4, egt=[800.0] * 4)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
def ev():
    return StatusEvaluator(load_engine_config(ENGINE))


def test_t_sts_3_every_non_go_level_has_a_reason(ev):
    seq = [frame(oil_p=3.5), frame(oil_p=1.5), frame(oil_p=0.5, rpm=3000.0), frame(oil_t=125.0), frame(egt=[960.0] * 4)]
    for i, f in enumerate(seq):
        st = ev.evaluate(float(i), f, engine_state="RUNNING")
        if st.level != "GO":
            assert st.reasons and all(r.text for r in st.reasons), st
    assert ev.evaluate(10.0, frame(), engine_state="FAILED").reasons[0].code == "ENGINE_FAILED"


def test_bands_and_engine_state(ev):
    assert ev.evaluate(0, frame(), engine_state="RUNNING").level == "GO"
    assert ev.evaluate(1, frame(oil_p=1.5), engine_state="RUNNING").level == "CAUTION"      # below normal above 3500
    st = ev.evaluate(2, frame(oil_p=0.5, rpm=3000.0), engine_state="RUNNING")            # below the minimum
    assert st.level == "NO-GO" and st.reasons[0].limit == 0.8
    assert ev.evaluate(3, frame(), engine_state="OFF").level == "ENGINE_OFF"


def test_time_limited_rpm(ev):
    t = 0.0
    for _ in range(300):                                   # 5800 rpm is allowed for 5 min (OM take-off)
        assert ev.evaluate(t, frame(rpm=5750.0), engine_state="RUNNING").level == "GO"
        t += 1.0
    st = ev.evaluate(t + 1.0, frame(rpm=5750.0), engine_state="RUNNING")
    assert st.level == "CAUTION" and st.reasons[0].code == "TIME_LIMIT"


def test_t_sts_4_sensor_quarantine_is_advisory_not_no_go(ev):
    one = ev.evaluate(0, frame(), engine_state="RUNNING", quarantined=["cht_2"])
    assert one.level == "ADVISORY" and one.reasons[0].channel == "cht[2]"
    two = ev.evaluate(1, frame(), engine_state="RUNNING", quarantined=["cht_2", "cht_3"])
    assert two.level == "CAUTION"
    # a quarantined channel's out-of-limit reading is not used: still ADVISORY, never NO-GO
    fresh = StatusEvaluator(load_engine_config(ENGINE))          # (the two-sensor CAUTION holds for its exit time)
    bad_reading = fresh.evaluate(2, frame(cht=[100.0, 300.0, 100.0, 100.0]), engine_state="RUNNING",
                                 quarantined=["cht_2"])
    assert bad_reading.level == "ADVISORY"


def test_t_sts_5_hysteresis_and_latch(ev):
    cfg = load_status_config()
    hold = cfg["exit_hold_s"]["value"]
    # CAUTION enters immediately on crossing below the normal oil-pressure band (2.0-5.0 bar above 3500 rpm)
    assert ev.evaluate(0.0, frame(oil_p=1.9), engine_state="RUNNING").level == "CAUTION"
    # back inside but not by the 2 % margin (0.06 bar): stays CAUTION
    for t in range(1, 30):
        assert ev.evaluate(float(t), frame(oil_p=2.03), engine_state="RUNNING").level == "CAUTION"
    # inside by the margin: clears only after the hold time
    t0 = 30.0
    assert ev.evaluate(t0, frame(oil_p=2.5), engine_state="RUNNING").level == "CAUTION"
    assert ev.evaluate(t0 + hold - 1, frame(oil_p=2.5), engine_state="RUNNING").level == "CAUTION"
    assert ev.evaluate(t0 + hold + 0.5, frame(oil_p=2.5), engine_state="RUNNING").level == "GO"
    # NO-GO latches: cause cleared but not acknowledged -> still NO-GO; acknowledged but cause present -> NO-GO
    t = 100.0
    assert ev.evaluate(t, frame(oil_t=135.0), engine_state="RUNNING").level == "NO-GO"
    ev.acknowledge()
    assert ev.evaluate(t + 1, frame(oil_t=135.0), engine_state="RUNNING").level == "NO-GO"
    for k in range(2, 40):
        st = ev.evaluate(t + k, frame(oil_t=100.0), engine_state="RUNNING")
    assert st.level == "NO-GO" and st.latched and st.reasons[0].code == "LATCHED"
    ev.acknowledge()
    assert ev.evaluate(t + 41, frame(oil_t=100.0), engine_state="RUNNING").level == "GO"
