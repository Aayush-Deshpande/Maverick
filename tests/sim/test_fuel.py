"""M1-11 fuel systems + diesel calibration (P 1.3l-m; F05-F10 parameter effects; T-PHY-1/4 for the diesels)."""
import pytest

from backend.physics.engine_config import available_engines, load_engine_config
from backend.sim.atmosphere import Atmosphere
from backend.sim.engine import MeanValueEngine

SL = Atmosphere.at(0)
ALL = available_engines()
CI = [e for e in ALL if load_engine_config(e).ignition_mode == "COMPRESSION_IGNITION"]
INJECTED_SI = [e for e in ALL if load_engine_config(e).fuel_system == "PORT_INJECTION"]


@pytest.fixture(scope="module")
def engines():
    return {e: MeanValueEngine(load_engine_config(e)) for e in ALL}


def test_fuel_system_kind_comes_from_config(engines):
    for e, m in engines.items():
        assert m.fuel.kind == load_engine_config(e).fuel_system


@pytest.mark.parametrize("engine_id", CI)
def test_t_phy_1_diesels_meet_take_off_power(engines, engine_id):
    m = engines[engine_id]
    assert m.steady_point(100, m.cfg.rated_rpm, SL).brake_w == pytest.approx(m.cfg.rated_power_kw * 1000, rel=0.02)


@pytest.mark.xfail(strict=True, reason="Question for Prasad: the ASSUMED/PLACEHOLDER diesel full-load lambda (1.55/1.52) "
                   "and max boost (190/195 kPa) give too little air for the rated power: eta_i 0.56-0.58 (CI is ~0.42-0.50) "
                   "and BSFC 163-168 g/kWh (config 235/218, VRDE brochure ~215). Needs sourced lambda/boost or OK to "
                   "derive them from BSFC.")
@pytest.mark.parametrize("engine_id", CI)
def test_diesel_calibration_is_physically_plausible(engines, engine_id):
    m = engines[engine_id]
    assert 0.40 <= m.combustion.eta_i <= 0.50
    assert 195 <= m.steady_point(100, m.cfg.rated_rpm, SL).bsfc_g_kwh <= 250


def test_vrde_flat_rated_to_its_critical_altitude_then_falls(engines):        # T-PHY-4 (VRDE part)
    for e in CI:
        m = engines[e]
        crit = m.cfg.turbo.critical_altitude_ft
        sl = m.steady_point(100, m.cfg.rated_rpm, SL).brake_w
        at = m.steady_point(100, m.cfg.rated_rpm, Atmosphere.at(crit)).brake_w
        above = m.steady_point(100, m.cfg.rated_rpm, Atmosphere.at(crit + 4000)).brake_w
        assert at >= 0.97 * sl and above < at


@pytest.mark.parametrize("engine_id", INJECTED_SI + CI)
def test_injector_faults_act_on_their_own_cylinder(engines, engine_id):        # F05/F06/F07/F08
    m = engines[engine_id]
    n = m.n_cyl
    base = m.steady_point(80, m.cfg.max_continuous_rpm, SL)
    clog = [1.0] * n
    clog[1] = 0.6
    p = m.steady_point(80, m.cfg.max_continuous_rpm, SL, injector=clog)
    assert p.cyl_fuel_kg_s[1] < 0.7 * base.cyl_fuel_kg_s[1]
    assert p.cyl_fuel_kg_s[0] == pytest.approx(base.cyl_fuel_kg_s[0], rel=1e-6)
    assert p.brake_w < base.brake_w
    shut = [1.0] * n
    shut[2] = 0.0
    assert m.steady_point(80, m.cfg.max_continuous_rpm, SL, injector=shut).cyl_indicated_w[2] == 0.0
    leak = [1.0] * n
    leak[3] = 1.5
    assert m.steady_point(80, m.cfg.max_continuous_rpm, SL, injector=leak).cyl_fuel_kg_s[3] > base.cyl_fuel_kg_s[3]


@pytest.mark.parametrize("engine_id", CI)
def test_rail_decay_is_compensated_until_the_pulse_width_limit(engines, engine_id):   # F09
    m = engines[engine_id]
    base = m.steady_point(100, m.cfg.rated_rpm, SL)
    mild = m.steady_point(100, m.cfg.rated_rpm, SL, fuel_health={"rail_health": 0.8})
    severe = m.steady_point(100, m.cfg.rated_rpm, SL, fuel_health={"rail_health": 0.3})
    assert mild.fuel_pressure_bar < base.fuel_pressure_bar
    assert mild.brake_w == pytest.approx(base.brake_w, rel=1e-6)          # ECU stretches the pulse width
    assert m.fuel.pulse_width_factor(mild.fuel_pressure_bar) > 1.0
    assert severe.brake_w < 0.9 * base.brake_w                            # past the pulse-width limit


@pytest.mark.parametrize("engine_id", INJECTED_SI)
def test_low_supply_pressure_leans_port_injected_engines(engines, engine_id):          # F10
    m = engines[engine_id]
    base = m.steady_point(100, m.cfg.rated_rpm, SL)
    low = m.steady_point(100, m.cfg.rated_rpm, SL, fuel_health={"supply_health": 0.6})
    assert low.fuel_pressure_bar < base.fuel_pressure_bar
    assert low.cyl_lambda[0] > base.cyl_lambda[0] and low.mdot_fuel_kg_s < base.mdot_fuel_kg_s
