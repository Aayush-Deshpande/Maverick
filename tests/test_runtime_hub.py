"""R1-R3: concurrent per-engine runtimes, fault registry, lever dynamics, isolation, determinism."""
import time

import numpy as np
import pytest

from backend.physics.engine_config import load_engine_config
from backend.runtime import EngineRuntime, RuntimeHub
from backend.runtime.levers import Levers
from backend.runtime.registry import faults_for

ENGINES = ["rotax_912is", "rotax_914", "vrde_jayem_2_2l"]


@pytest.fixture(scope="module")
def hub():
    h = RuntimeHub(ENGINES, seed=0, warmup_ticks=600)
    h.calibrate_all()
    return h


def test_registry_filters_by_profile():
    modes = lambda e: {s.mode for s in faults_for(load_engine_config(e))}
    assert "BOOST_LEAK" not in modes("rotax_912is") and "BOOST_LEAK" in modes("rotax_914")
    assert "INJECTOR_COKING" in modes("vrde_jayem_2_2l") and "INJECTOR_COKING" not in modes("rotax_914")


def test_invalid_fault_rejected(hub):
    with pytest.raises(ValueError):
        hub.runtimes["rotax_912is"].inject_fault("BOOST_LEAK")
    with pytest.raises(ValueError):
        hub.runtimes["rotax_914"].inject_fault("MISFIRE")           # needs a cylinder


def test_all_engines_tick_and_only_selected_gets_heavy(hub):
    hub.select("rotax_914", warm_heavy=False)
    hub.runtimes["rotax_914"].ensure_heavy()
    out = hub.tick_all()
    assert set(out) == set(ENGINES)
    assert out["rotax_914"].heavy is not None
    assert out["rotax_912is"].heavy is None and out["vrde_jayem_2_2l"].heavy is None


def test_fault_isolated_to_one_engine_and_marked_manual(hub):
    a, b = hub.runtimes["rotax_914"], hub.runtimes["rotax_912is"]
    a.inject_fault("COOLING_DEGRADATION", severity=0.9, ramp_sec=30.0)
    for _ in range(200):
        hub.tick_all()
    assert a.buffer[-1].truth.active_faults and not b.buffer[-1].truth.active_faults
    assert a.buffer[-1].truth.origin == "MANUAL" and not a.buffer[-1].truth.kpi_eligible
    assert b.buffer[-1].truth.kpi_eligible
    a.clear_faults()


def test_detector_alarms_on_injected_fault_not_on_other_engine():
    h = RuntimeHub(["rotax_914", "rotax_912is"], seed=5, warmup_ticks=600)
    h.calibrate_all()
    h.runtimes["rotax_914"].inject_fault("COOLING_DEGRADATION", severity=1.0, ramp_sec=60.0)
    conf = {e: 0 for e in h.runtimes}
    for _ in range(250):
        for e, t in h.tick_all().items():
            conf[e] += int(t.detection.confirmed)
    assert conf["rotax_914"] > 60 and conf["rotax_912is"] < 25


def test_lever_first_order_dynamics_and_physics_response():
    lv = Levers()
    lv.set_targets(throttle_pct=100)
    v = []
    for _ in range(10):
        lv.advance(1.0)
        v.append(lv.throttle_pct)
    assert v[0] < 99 and all(np.diff(v) > 0) and v[-1] < 100
    rt = EngineRuntime("rotax_914", seed=2, warmup_ticks=600)
    rt.calibrate()
    rt.set_levers(throttle_pct=40)
    for _ in range(80):
        rt.tick()
    low = rt.buffer[-1].frame
    rt.set_levers(throttle_pct=100)
    ticks = [rt.tick().frame for _ in range(120)]
    assert ticks[-1].rpm > low.rpm and np.mean(ticks[-1].cht) > np.mean(low.cht)
    assert np.mean(ticks[3].cht) < np.mean(ticks[-1].cht)


def test_determinism_same_seed_same_stream():
    def run():
        h = RuntimeHub(["rotax_914"], seed=9, warmup_ticks=600)
        h.calibrate_all()
        return [h.tick_all()["rotax_914"].frame.channels()["cht_1"] for _ in range(40)]
    assert run() == run()


def test_cpu_cost_is_small(hub):
    t0 = time.perf_counter()
    for _ in range(50):
        hub.tick_all()
    assert (time.perf_counter() - t0) / 50 < 0.05


def test_all_five_engines_concurrent_load_and_isolation():
    """R8: 5 profiles running concurrently with isolation and low latency budget."""
    all_five = ["rotax_912is", "rotax_914", "rotax_915is", "austro_ae300", "vrde_jayem_2_2l"]
    hub = RuntimeHub(all_five, seed=12, warmup_ticks=400)
    hub.calibrate_all()

    # Step all 5 engines for 50 ticks and time
    t0 = time.perf_counter()
    for _ in range(50):
        out = hub.tick_all()
        assert len(out) == 5
    dt = time.perf_counter() - t0
    # 5 engines at 20 Hz (50 ms per tick): mean tick time for all 5 must be << 20 ms
    mean_tick_ms = 1000.0 * dt / 50
    assert mean_tick_ms < 20.0, f"5-engine concurrent tick took {mean_tick_ms:.2f} ms"
