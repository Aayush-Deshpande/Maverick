"""M1-12 ECU + engine state machine + dynamic plant (R 21.4, T-M0-4 basis, T-PHY-11, F04/F11/F36 effects)."""
import time

import pytest

from backend.physics.engine_config import available_engines, load_engine_config
from backend.sim.plant import CRANKING, FAILED, OFF, RUNNING, SimEngine

DT = 0.05


def run(s, seconds, health=None):
    o = None
    for _ in range(int(seconds / DT)):
        o = s.step(DT, health)
    return o


@pytest.mark.parametrize("engine_id", available_engines())
def test_stop_spins_down_on_the_ground_and_start_runs(engine_id):        # T-M0-4 (plant side)
    s = SimEngine(load_engine_config(engine_id))
    s.levers.tas_kt = 0.0
    s.warm_start(60)
    assert run(s, 5).state == RUNNING
    s.stop()
    o = run(s, 30)
    assert o.state == OFF and o.rpm < 100 and o.fuel_kg_h == 0.0
    s.levers.throttle_pct = 15
    s.start()
    o = run(s, 15)
    assert o.state == RUNNING and o.rpm > s.cfg.idle_rpm * 0.7


def test_diesel_cold_start_waits_for_the_glow_plugs():
    cfg = load_engine_config(next(e for e in available_engines() if load_engine_config(e).glow_plugs))
    s = SimEngine(cfg)
    s.core.thermal.coolant_c = 0.0
    s.levers.throttle_pct, s.levers.tas_kt = 15, 0.0
    s.start()
    early = run(s, s.sm["glow_preheat_s"] * 0.5)
    assert early.state == CRANKING and early.fuel_kg_h == 0.0
    assert run(s, 15).state == RUNNING


def test_oil_pump_loss_seizes_the_engine_and_clearing_does_not_unseize():   # F23 -> FAILED (R 19.4)
    s = SimEngine(load_engine_config(available_engines()[0]))
    s.warm_start(80)
    run(s, 5)
    o = run(s, s.sm["seize_time_s"] + 40, {"thermal": {"pump_health": 0.05}})
    assert o.state == FAILED and o.failure == "SEIZURE_LOW_OIL_PRESSURE" and o.power_kw < 1.0
    assert run(s, 5).state == FAILED                     # fault cleared, still seized
    s.reset()
    assert s.state == OFF


def test_overspeed_cuts_fuel():
    cfg = load_engine_config(available_engines()[0])
    s = SimEngine(cfg)
    s.warm_start(100)
    s.rotor.omega = (cfg.overspeed_rpm or cfg.rated_rpm) * 1.2 * 6.2832 / 60
    assert s.step(DT).fuel_kg_h == 0.0


@pytest.mark.parametrize("engine_id", [e for e in available_engines() if load_engine_config(e).ignition_mode == "SPARK_IGNITION"])
def test_si_lane_loss_slows_the_burn(engine_id):                          # F04 / F36
    s1, s2 = SimEngine(load_engine_config(engine_id)), SimEngine(load_engine_config(engine_id))
    s1.warm_start(80)
    s2.warm_start(80)
    a, b = run(s1, 10), run(s2, 10, {"lane_lost": True})
    assert b.cov_imep_pct > a.cov_imep_pct and b.power_kw < a.power_kw
    assert b.ign_timing_btdc != a.ign_timing_btdc


def test_timing_drift_is_published_and_costs_efficiency():                # F11: real timing, not a constant
    eid = available_engines()[0]
    s1, s2 = SimEngine(load_engine_config(eid)), SimEngine(load_engine_config(eid))
    s1.warm_start(80)
    s2.warm_start(80)
    a, b = run(s1, 10), run(s2, 10, {"timing_error_deg": 8.0})
    changed = (a.ign_timing_btdc, a.inj_timing_btdc) != (b.ign_timing_btdc, b.inj_timing_btdc)
    assert changed and b.power_kw < a.power_kw


def test_determinism_and_step_cost():                                     # T-DYN-7 (plant), T-PHY-11
    eid = available_engines()[0]
    outs = []
    for _ in range(2):
        s = SimEngine(load_engine_config(eid))
        s.warm_start(70)
        outs.append(run(s, 10))
    assert outs[0] == outs[1]
    s = SimEngine(load_engine_config(eid))
    s.warm_start(70)
    t0 = time.perf_counter()
    run(s, 10)
    assert (time.perf_counter() - t0) / (10 / DT) < 0.002                 # <= 2 ms per engine step
