"""M1-10 turbo + boost control + intercooler; calibration of the turbocharged SI engines (T-PHY-1/2/3/4, F14-F18)."""
import pytest

from backend.physics.engine_config import available_engines, load_engine_config
from backend.sim.atmosphere import Atmosphere
from backend.sim.engine import MeanValueEngine

TURBO_SI = [e for e in available_engines()
            if load_engine_config(e).turbo is not None and load_engine_config(e).ignition_mode == "SPARK_IGNITION"]
SL = Atmosphere.at(0)


@pytest.fixture(scope="module", params=TURBO_SI)
def eng(request):
    return MeanValueEngine(load_engine_config(request.param))


def _mc_target(eng):
    t = eng.cfg.turbo
    return t.map_continuous_max_kpa * 1000 if t.map_continuous_max_kpa else None


def test_t_phy_1_take_off_and_plausible_efficiency(eng):
    p = eng.steady_point(100, eng.cfg.rated_rpm, SL)
    assert p.brake_w == pytest.approx(eng.cfg.rated_power_kw * 1000, rel=0.02)
    assert 0.30 <= eng.combustion.eta_i <= 0.43
    assert p.map_pa <= (eng.cfg.turbo.map_takeoff_max_kpa or eng.cfg.turbo.max_boost_kpa) * 1000 * 1.01


def test_t_phy_2_max_continuous(eng):
    p = eng.steady_point(100, eng.cfg.max_continuous_rpm, SL, map_target_pa=_mc_target(eng))
    assert p.brake_w == pytest.approx(eng.cfg.max_continuous_power_kw * 1000, rel=0.03)


def _t_phy_3(eng, deviations):
    rated = eng.cfg.rated_power_kw * 1000
    for alt in range(0, 25001, 5000):
        for dev in deviations:
            for thr in (40, 70, 100):
                assert eng.steady_point(thr, eng.cfg.rated_rpm, Atmosphere.at(alt, isa_dev_c=dev)).brake_w <= 1.05 * rated


def test_t_phy_3_never_above_105_percent_of_rated_isa_to_hot(eng):
    _t_phy_3(eng, (0, 15, 35))


def test_t_phy_3_cold_day_gain_is_only_air_density(eng):
    """D58: on a cold day a MAP-limited engine really makes more power (denser air at the same MAP; manufacturers
    correct for density altitude rather than cap it). The rule: never above 105 % of rated scaled by the ISA/actual
    temperature ratio, i.e. no gain beyond what the air density explains."""
    rated = eng.cfg.rated_power_kw * 1000
    for alt in range(0, 25001, 5000):
        isa, cold = Atmosphere.at(alt), Atmosphere.at(alt, isa_dev_c=-30)
        for thr in (40, 70, 100):
            limit = 1.05 * rated * isa.temperature_k / cold.temperature_k
            assert eng.steady_point(thr, eng.cfg.rated_rpm, cold).brake_w <= limit


def _t_phy_4(eng):
    t = eng.cfg.turbo
    alt = t.critical_altitude_takeoff_ft or t.critical_altitude_ft
    sl = eng.steady_point(100, eng.cfg.rated_rpm, SL).brake_w
    at = eng.steady_point(100, eng.cfg.rated_rpm, Atmosphere.at(alt)).brake_w
    above = [eng.steady_point(100, eng.cfg.rated_rpm, Atmosphere.at(alt + d)).brake_w for d in (2000, 4000, 6000)]
    assert at >= 0.97 * sl, f"{at / sl:.3f} of SL at the critical altitude"
    assert all(b < a for a, b in zip([at] + above, above))


@pytest.mark.parametrize("engine_id", [e for e in TURBO_SI if load_engine_config(e).turbo.intercooled])
def test_t_phy_4_intercooled_turbo_holds_power_to_critical_altitude(engine_id):
    _t_phy_4(MeanValueEngine(load_engine_config(engine_id)))


@pytest.mark.parametrize("engine_id", [e for e in TURBO_SI if not load_engine_config(e).turbo.intercooled])
def test_t_phy_4_non_intercooled_turbo_holds_power_to_critical_altitude(engine_id):
    _t_phy_4(MeanValueEngine(load_engine_config(engine_id)))


def test_boost_faults_act_through_parameters(eng):                  # F14-F18
    alt = Atmosphere.at(eng.cfg.turbo.critical_altitude_ft)          # where the turbo has no spare capacity
    base = eng.steady_point(100, eng.cfg.rated_rpm, alt)
    leak = eng.steady_point(100, eng.cfg.rated_rpm, alt, turbo_health={"boost_leak": 0.4})
    assert leak.brake_w < base.brake_w * 0.97                       # critical altitude comes down
    wg_open = eng.steady_point(100, eng.cfg.rated_rpm, SL, turbo_health={"wastegate_stuck": "OPEN"})
    healthy_sl = eng.steady_point(100, eng.cfg.rated_rpm, SL).brake_w
    assert wg_open.map_pa < 1.05 * SL.pressure_pa and wg_open.brake_w < 0.85 * healthy_sl
    wg_closed = eng.steady_point(100, eng.cfg.rated_rpm, SL, turbo_health={"wastegate_stuck": "CLOSED"})
    assert wg_closed.map_pa > (eng.cfg.turbo.map_takeoff_max_kpa or eng.cfg.turbo.max_boost_kpa) * 1000 * 1.05
    high = Atmosphere.at(eng.cfg.turbo.critical_altitude_ft + 3000)           # turbo capability binds here
    worn = eng.steady_point(100, eng.cfg.max_continuous_rpm, high, map_target_pa=_mc_target(eng),
                            turbo_health={"bearing_wear": 1.0})
    assert worn.brake_w < 0.97 * eng.steady_point(100, eng.cfg.max_continuous_rpm, high, map_target_pa=_mc_target(eng)).brake_w


def test_spool_lag_and_bearing_wear_slow_it(eng):                    # T-PHY-9 turbo spool 0.5-2 s
    def t63(health):
        tb = eng.turbo
        tb.p_charge = SL.pressure_pa
        target = tb.steady_charge(SL, 0.08, health=health)
        t, dt = 0.0, 0.01
        while tb.p_charge < SL.pressure_pa + 0.632 * (target - SL.pressure_pa):
            tb.step(dt, SL, 0.08, health)
            t += dt
        return t
    healthy = t63({})
    assert 0.5 <= healthy <= 2.0
    assert t63({"bearing_wear": 1.0}) > 1.5 * healthy


@pytest.mark.parametrize("engine_id", [e for e in TURBO_SI if load_engine_config(e).turbo.intercooled])
def test_intercooler_fouling_heats_the_charge(engine_id):          # F18
    tb = MeanValueEngine(load_engine_config(engine_id)).turbo
    p = 140e3
    assert tb.charge_temperature_k(SL, p, ic_fouling=0.8) > tb.charge_temperature_k(SL, p) + 10
