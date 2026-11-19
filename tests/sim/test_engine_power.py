"""M1-06 friction + brake power + calibration (R 21.5): T-PHY-1/2 for the naturally aspirated engines.
Turbo engines are calibrated in M1-10 (boost), the diesels in M1-11; they are not claimed here."""
import pytest

from backend.physics.engine_config import available_engines, load_engine_config
from backend.sim.atmosphere import Atmosphere
from backend.sim.engine import MeanValueEngine

NA = [e for e in available_engines() if load_engine_config(e).induction == "NATURALLY_ASPIRATED"]
SL = Atmosphere.at(0)


@pytest.mark.parametrize("engine_id", NA)
def test_t_phy_1_take_off_power_and_plausible_efficiency(engine_id):
    cfg = load_engine_config(engine_id)
    m = MeanValueEngine(cfg)
    p = m.steady_point(100, cfg.rated_rpm, SL)
    assert p.brake_w == pytest.approx(cfg.rated_power_kw * 1000, rel=0.02)
    assert 0.30 <= m.combustion.eta_i <= 0.43              # physical SI indicated efficiency (Heywood ch. 5)
    assert 0.75 <= p.brake_w / p.indicated_w <= 0.92       # mechanical efficiency at WOT rated speed


@pytest.mark.parametrize("engine_id", NA)
def test_t_phy_2_max_continuous_within_3_percent(engine_id):
    cfg = load_engine_config(engine_id)
    p = MeanValueEngine(cfg).steady_point(100, cfg.max_continuous_rpm, SL)
    assert p.brake_w == pytest.approx(cfg.max_continuous_power_kw * 1000, rel=0.03)


@pytest.mark.parametrize("engine_id", NA)
def test_bsfc_emerges_in_the_si_band(engine_id):              # T-PHY-8 (rated point; cruise check in M1-14)
    cfg = load_engine_config(engine_id)
    assert 220 <= MeanValueEngine(cfg).steady_point(100, cfg.rated_rpm, SL).bsfc_g_kwh <= 330


@pytest.mark.parametrize("engine_id", NA)
def test_na_power_falls_with_altitude_and_heat(engine_id):
    cfg = load_engine_config(engine_id)
    m = MeanValueEngine(cfg)
    powers = [m.steady_point(100, cfg.rated_rpm, Atmosphere.at(h)).brake_w for h in (0, 5000, 10000, 15000)]
    assert all(b < a for a, b in zip(powers, powers[1:]))
    hot = m.steady_point(100, cfg.rated_rpm, Atmosphere.at(0, isa_dev_c=30)).brake_w
    assert hot < powers[0] * 0.95


@pytest.mark.parametrize("engine_id", NA)
def test_part_throttle_and_filter_reduce_power(engine_id):
    cfg = load_engine_config(engine_id)
    m = MeanValueEngine(cfg)
    wot = m.steady_point(100, cfg.rated_rpm, SL).brake_w
    assert m.steady_point(40, cfg.rated_rpm, SL).brake_w < 0.7 * wot
    assert m.steady_point(100, cfg.rated_rpm, SL, filter_factor=8).brake_w < wot * 0.97     # F13
