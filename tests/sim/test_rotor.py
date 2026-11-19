"""M1-03 rotor + propeller + constant-speed governor (P Part 4 Step 1.3b, T-PHY-9 governor part)."""
import math

import pytest

from backend.physics.engine_config import available_engines, load_engine_config
from backend.sim.atmosphere import Atmosphere
from backend.sim.rotor import Rotor

DT = 0.05


def _ids(governed):
    return [e for e in available_engines() if bool(load_engine_config(e).propeller_governor) == governed]


def _run(rotor, power_w, atm, seconds, tas_kt=None):
    trace = []
    for _ in range(int(seconds / DT)):
        q = power_w / max(rotor.omega, 1.0)
        rotor.step(DT, engine_torque_nm=q, atm=atm, tas_kt=tas_kt)
        trace.append(rotor.engine_rpm)
    return trace


@pytest.mark.parametrize("engine_id", _ids(False))
def test_fixed_pitch_absorbs_rated_power_at_rated_rpm_and_speeds_up_in_thin_air(engine_id):
    cfg = load_engine_config(engine_id)
    r = Rotor.for_engine(cfg)
    sl = Atmosphere.at(0)
    rpm_sl = _run(r, cfg.rated_power_kw * 1000, sl, 20)[-1]
    assert rpm_sl == pytest.approx(cfg.rated_rpm, rel=0.01)            # calibration point
    r2 = Rotor.for_engine(cfg)
    rpm_hi = _run(r2, cfg.rated_power_kw * 1000, Atmosphere.at(10000), 20)[-1]
    # same power, thinner air: P = Cp rho n^3 D^5 -> n rises (fixed pitch)
    assert rpm_hi > rpm_sl * 1.05


@pytest.mark.parametrize("engine_id", _ids(True))
def test_governor_holds_setpoint_after_20_percent_power_step(engine_id):        # T-PHY-9
    cfg = load_engine_config(engine_id)
    r = Rotor.for_engine(cfg)
    sl = Atmosphere.at(0)
    p = cfg.rated_power_kw * 1000 * 0.75
    _run(r, p, sl, 15)
    assert r.engine_rpm == pytest.approx(cfg.rated_rpm, abs=20)
    pitch_before = r.pitch
    trace = _run(r, p * 1.2, sl, 4)
    settle = next((i * DT for i in range(len(trace)) if all(abs(x - cfg.rated_rpm) <= 20 for x in trace[i:])), None)
    assert settle is not None and settle < 2.0, f"settle {settle}"
    assert max(trace) <= cfg.rated_rpm * 1.03                              # overshoot < 3 %
    assert r.pitch > pitch_before                                         # more power -> coarser pitch


def test_torque_loss_slows_a_fixed_pitch_engine():
    cfg = load_engine_config(_ids(False)[0])
    r = Rotor.for_engine(cfg)
    sl = Atmosphere.at(0)
    rpm_full = _run(r, cfg.rated_power_kw * 1000, sl, 20)[-1]
    rpm_3cyl = _run(r, cfg.rated_power_kw * 1000 * 0.75, sl, 20)[-1]   # one of four cylinders lost
    assert rpm_3cyl < rpm_full * 0.95
