"""M1-14 SimSource: the backend/sim plant behind the Frame/TruthRecord contract (P Step 1.4), plus the closed-form
steady MAP solver used for speed at 20x/60x."""
import dataclasses
import math
import random
import time
from types import SimpleNamespace

import pytest

from backend.core.frame import Frame, TruthRecord
from backend.physics.engine_config import available_engines, load_engine_config
from backend.sim.induction import Induction
from backend.sim.source import SimSource, registry

DT = 0.05


def _bisect_map(ind, frac, p_up, t_k, rpm):
    lo, hi = 0.0, p_up
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if ind.throttle_flow(frac, p_up, t_k, mid) > ind.cylinder_flow(mid, t_k, rpm):
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def test_closed_form_map_equals_bisection():
    ind = Induction.for_engine(load_engine_config(available_engines()[0]))
    rnd = random.Random(3)
    for _ in range(3000):
        frac, p = rnd.choice([0.0, rnd.random()]), rnd.uniform(3e4, 2.5e5)
        t, rpm = rnd.uniform(220, 330), rnd.choice([0.0, rnd.uniform(100, 6500)])
        assert ind._steady_map(frac, p, t, rpm) == pytest.approx(_bisect_map(ind, frac, p, t, rpm), rel=1e-9, abs=1e-6)


def test_steady_flow_satisfies_the_filter_balance():
    ind = Induction.for_engine(load_engine_config(available_engines()[0]))
    mdot, map_pa = ind.steady_flow(0.7, 101325.0, 288.15, 5000.0, filter_factor=3.0)
    p_up = 101325.0 - ind.k_filter * 3.0 * mdot ** 2
    assert map_pa == pytest.approx(ind._steady_map(0.7, p_up, 288.15, 5000.0), rel=1e-9)
    assert mdot == pytest.approx(ind.cylinder_flow(map_pa, 288.15, 5000.0), rel=1e-9)


@pytest.mark.parametrize("engine_id", available_engines())
def test_emits_frame_and_separate_truth(engine_id):
    s = SimSource(engine_id, seed=1)
    frame, truth = s.step(DT, throttle_pct=60, altitude_ft=5000, oat_c=10)
    assert isinstance(frame, Frame) and isinstance(truth, TruthRecord)
    assert len(frame.cht) == len(frame.egt) == s.n_cylinders
    assert frame.rpm and frame.map_kpa and frame.oil_p and frame.vibration_orders
    assert truth.is_nominal and not truth.failed


def test_fault_reaches_truth_never_the_frame():
    s = SimSource("rotax_912is", seed=2)
    s.inject_fault("F01", cylinder=3, severity=1.0, ramp_sec=1.0)
    for _ in range(40):
        frame, truth = s.step(DT, 60, 5000, 10)
    assert [(f.mode, f.location) for f in truth.active_faults] == [("F01", 3)]
    assert "f01" not in repr(dataclasses.asdict(frame)).lower()
    assert frame.egt[2] < min(frame.egt[0], frame.egt[1], frame.egt[3]) - 200     # misfiring cylinder runs cold


def test_each_fault_keeps_its_own_ramp():
    s = SimSource("rotax_912is", seed=4)
    f = SimpleNamespace(fault_id="F23", cylinder=None, channel=None, severity=1.0, ramp_s=100.0, t0_s=s.now())
    s.apply(f)
    for _ in range(int(50 / DT)):
        s.step(DT, 60, 5000, 10)
    s.inject_fault("F01", cylinder=1, severity=1.0, ramp_sec=1.0)      # adding a fault must not restart F23's ramp
    assert f.t0_s == 0.0 and s.faults[0] is f


def test_sensor_fault_changes_only_the_measurement():
    a, b = SimSource("rotax_914", seed=5), SimSource("rotax_914", seed=5)
    b.inject_fault("S05", channel="oil_t", severity=1.0, ramp_sec=1.0)
    for _ in range(60):
        fa, _ = a.step(DT, 60, 5000, 10)
        fb, _ = b.step(DT, 60, 5000, 10)
    assert fb.oil_t is None and fa.oil_t is not None
    assert fb.cht == fa.cht and fb.rpm == fa.rpm                      # the engine itself is unchanged


def test_build_variation_is_per_tail_and_deterministic():
    def run(seed):
        s = SimSource("rotax_914", seed=seed)
        for _ in range(400):
            f, _ = s.step(DT, 75, 5000, 15)
        return s.variation, f.cht
    v1, c1 = run(11)
    v1b, c1b = run(11)
    v2, c2 = run(12)
    assert v1 == v1b and c1 == c1b
    assert v1 != v2 and c1 != c2


def test_legacy_mode_names_resolve_through_the_registry():
    s = SimSource("rotax_914", seed=0)
    spec = s._resolve("OIL_PRESSURE_LOSS")
    assert spec.raw.get("plant_mode_legacy") == "OIL_PRESSURE_LOSS" and spec.id.startswith("F")
    with pytest.raises(ValueError):
        s._resolve("NOT_A_FAULT")


def test_step_cost_budget():                                          # T-PHY-11 (one engine step <= 2 ms)
    for e in available_engines():
        s = SimSource(e, seed=0)
        for _ in range(40):
            s.step(DT, 70, 8000, 5)
        t0 = time.perf_counter()
        for _ in range(200):
            s.step(DT, 70, 8000, 5)
        assert (time.perf_counter() - t0) / 200 < 2e-3, e
