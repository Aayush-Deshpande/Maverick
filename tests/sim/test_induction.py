"""M1-04 induction: throttle orifice, manifold filling, air filter, real rpm (P Part 4 Step 1.3c, T-PHY-9 MAP part)."""
import math

import pytest

from backend.physics.engine_config import available_engines, load_engine_config
from backend.sim.atmosphere import Atmosphere
from backend.sim.induction import Induction

SL = Atmosphere.at(0)


def settle(ind, throttle, rpm, atm=SL, filter_factor=1.0, seconds=2.0, dt=0.05):
    for _ in range(int(seconds / dt)):
        ind.step(dt, throttle, rpm, atm, filter_factor=filter_factor)
    return ind.map_pa


@pytest.mark.parametrize("engine_id", available_engines())
def test_wot_rated_point_matches_calibration(engine_id):
    cfg = load_engine_config(engine_id)
    ind = Induction.for_engine(cfg)
    m = settle(ind, 100, cfg.rated_rpm)
    assert 0.94 * SL.pressure_pa < m < 0.98 * SL.pressure_pa       # wot_map_ratio 0.97 minus the clean filter drop


def test_map_follows_throttle_altitude_and_rpm():
    cfg = load_engine_config(available_engines()[0])
    ind = Induction.for_engine(cfg)
    wot, part = settle(ind, 100, 4500), settle(ind, 30, 4500)
    assert part < 0.8 * wot
    high = settle(Induction.for_engine(cfg), 100, 4500, Atmosphere.at(10000))
    assert high == pytest.approx(wot * Atmosphere.at(10000).pressure_pa / SL.pressure_pa, rel=0.03)
    assert settle(Induction.for_engine(cfg), 30, 2500) > settle(Induction.for_engine(cfg), 30, 5000)   # part throttle: more rpm, lower MAP


def test_filter_blockage_lowers_wot_map():                     # F13 acts on the filter coefficient
    cfg = load_engine_config(available_engines()[0])
    clean = settle(Induction.for_engine(cfg), 100, cfg.rated_rpm)
    blocked = settle(Induction.for_engine(cfg), 100, cfg.rated_rpm, filter_factor=8.0)
    assert blocked < clean - 3000                                 # several kPa


def test_map_time_constant_is_physical():                       # T-PHY-9: NA MAP step 0.05-0.3 s
    cfg = load_engine_config(available_engines()[0])
    ind = Induction.for_engine(cfg)
    rpm = 0.7 * cfg.rated_rpm
    start = settle(ind, 40, rpm)
    end = settle(Induction.for_engine(cfg), 80, rpm)
    t, dt = 0.0, 0.005
    while ind.map_pa < start + 0.632 * (end - start):
        ind.step(dt, 80, rpm, SL)
        t += dt
        assert t < 2
    assert 0.05 <= t <= 0.3, t


def test_stable_at_the_plant_step():                            # no oscillation at dt = 0.05 s
    cfg = load_engine_config(available_engines()[0])
    ind = Induction.for_engine(cfg)
    vals = []
    for _ in range(60):
        ind.step(0.05, 70, cfg.rated_rpm, SL)
        vals.append(ind.map_pa)
    assert all(b >= a - 1e-6 for a, b in zip(vals, vals[1:])) or all(b <= a + 1e-6 for a, b in zip(vals, vals[1:]))
    assert math.isfinite(vals[-1]) and vals[-1] > 0
