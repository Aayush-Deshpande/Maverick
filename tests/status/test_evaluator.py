"""M2-01 status evaluator (P Part 4 Step 2.2, D4): T-STS-2..5. T-STS-1 (fault -> registry level) needs the M3
diagnosis hypotheses and is added with M3."""
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


@pytest.mark.parametrize("engine_id", available_engines())
def test_t_sts_2_one_nominal_hour_is_all_go(engine_id):
    """1 h of nominal cruise (default levers): zero non-GO frames."""
    src = PlantSource(engine_id, seed=2)
    ev = StatusEvaluator(src.cfg)
    bad = []
    for _ in range(3600):
        f, _ = src.step(1.0, throttle_pct=60.0, altitude_ft=9000.0, oat_c=10.0)
        st = ev.evaluate(f.t, f, engine_state=f.engine_state)
        if st.level != "GO":
            bad.append((round(f.t), st.level, [r.text for r in st.reasons]))
    assert not bad, bad[:5]


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


def test_d60_a_diagnosis_alone_is_graded_by_its_severity_estimate():
    """D60 (Prasad 20 Nov): a confident diagnosis is not automatically NO-GO. One level below the registry level until
    the severity estimate reaches hypothesis_grading; hazards flagged immediate_no_go stay NO-GO at once."""
    ev = StatusEvaluator(load_engine_config(ENGINE))
    g = load_status_config()["hypothesis_grading"]["value"]
    h = {"fault_id": "F23", "posterior": 0.9, "status_at_full_severity": "NO-GO"}
    assert ev.graded_level({**h, "severity": 1.0}) == "CAUTION"
    assert ev.graded_level({**h, "severity": g["no_go_at_severity"]}) == "NO-GO"
    assert ev.graded_level({**h, "severity": None}) == "CAUTION"
    assert ev.graded_level({**h, "severity": 0.2, "immediate_no_go": True}) == "NO-GO"
    c = {"fault_id": "F25", "posterior": 0.9, "status_at_full_severity": "CAUTION"}
    assert ev.graded_level({**c, "severity": g["advisory_below_severity"] / 2}) == "ADVISORY"
    assert ev.graded_level({**c, "severity": 1.0}) == "CAUTION"


@pytest.mark.slow
def test_desert_heat_is_expected_not_diagnosed_as_a_fault():
    """Environment-aware (Prasad 20 Nov): a healthy engine on an ISA+30 desert day runs hotter, and the twin expects
    it, so no fault is confidently diagnosed. Certified limits stay absolute (a red line is a red line)."""
    from backend.runtime.engine_runtime import EngineRuntime
    rt = EngineRuntime(ENGINE, seed=5)
    rt.calibrate()
    rt.set_levers(oat_c=45.0)                                      # Thar summer, near sea level
    confident = 0
    for _ in range(600):
        tick = rt.tick()
        min_p = load_status_config()["hypothesis_posterior_min"]["value"]
        confident += any(h.get("fault_id") and (h.get("posterior") or 0) >= min_p
                         for h in getattr(tick, "hypotheses", None) or [])
    assert confident == 0
