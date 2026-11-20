"""M1-07 thermal / coolant / oil / gearbox (T-PHY-6, T-PHY-7, fault parameter effects) for calibrated engines."""
import pytest

from backend.physics.engine_config import available_engines, load_engine_config
from backend.sim.atmosphere import Atmosphere
from backend.sim.engine import MeanValueEngine

NA = [e for e in available_engines() if load_engine_config(e).induction == "NATURALLY_ASPIRATED"]
HOT = Atmosphere.at(0, isa_dev_c=15)
OUTPUT = {"oil_t": lambda t: t.oil_c, "coolant_t": lambda t: t.coolant_c, "egt": lambda t: max(t.egt),
          "cht": lambda t: max(t.cht), "gearbox_t": lambda t: t.gearbox_c}


@pytest.fixture(scope="module", params=NA)
def eng(request):
    return MeanValueEngine(load_engine_config(request.param))


def _limits(cfg):
    import json
    from pathlib import Path
    return json.loads((Path(__file__).resolve().parents[2] / "configs" / "engines" / f"{cfg.engine_id}.json")
                      .read_text(encoding="utf-8"))["limits"]


def test_t_phy_6_max_continuous_isa_plus_15_inside_limits_with_margin(eng):
    t = eng.settle_thermal(100, eng.cfg.max_continuous_rpm, HOT, seconds=2400)
    checked = 0
    for key, lim in _limits(eng.cfg).items():
        if key not in OUTPUT:
            continue
        v = OUTPUT[key](t)
        if "normal" in lim:
            assert lim["normal"][0] <= v <= lim["normal"][1], (key, v)
        if "warning_high" in lim:
            assert v <= 0.95 * lim["warning_high"], (key, v)          # >= 5 % margin
        checked += 1
    assert checked >= 2


def test_take_off_hot_day_stays_below_warning(eng):
    t = eng.settle_thermal(100, eng.cfg.rated_rpm, HOT, seconds=2400)
    for key, lim in _limits(eng.cfg).items():
        if key in OUTPUT and "warning_high" in lim:
            assert OUTPUT[key](t) < lim["warning_high"], key


def test_cruise_altitude_stays_in_normal_bands_thanks_to_thermostats(eng):
    t = eng.settle_thermal(60, 0.86 * eng.cfg.rated_rpm, Atmosphere.at(9000), seconds=3000)
    lim = _limits(eng.cfg)
    if "normal" in lim.get("oil_t", {}):
        assert lim["oil_t"]["normal"][0] - 5 <= t.oil_c <= lim["oil_t"]["normal"][1]


def test_t_phy_7_oil_pressure_follows_the_rpm_rule_and_relief_caps(eng):
    rule = _limits(eng.cfg)["oil_p"]
    th = eng.thermal
    hot = 100.0
    if "rpm_rule" in rule:
        r = rule["rpm_rule"]
        for rpm in (r["above_rpm"], eng.cfg.max_continuous_rpm, eng.cfg.rated_rpm):
            assert r["normal"][0] <= th.oil_pressure_bar(rpm, hot) <= r["normal"][1], rpm
        assert th.oil_pressure_bar(eng.cfg.idle_rpm, hot) >= r["below_min"]
    assert th.oil_pressure_bar(eng.cfg.rated_rpm, 20.0) <= rule.get("warning_high", 99)    # cold: relief caps it


def test_cooling_degradation_heats_only_its_cylinder(eng):          # F19 acts on cooling effectiveness
    base = eng.settle_thermal(100, eng.cfg.max_continuous_rpm, HOT, seconds=1800)
    cht0 = list(base.cht)
    eff = [1.0] * eng.n_cyl
    eff[1] = 0.3
    t = eng.settle_thermal(100, eng.cfg.max_continuous_rpm, HOT, seconds=1800, health={"cooling_eff": eff})
    assert t.cht[1] > cht0[1] + 5
    assert abs(t.cht[0] - cht0[0]) < (t.cht[1] - cht0[1]) / 2


def test_oil_pump_loss_lowers_pressure_and_heats_the_oil(eng):     # F23 seizure chain
    lim = _limits(eng.cfg)["oil_p"]
    p_min = lim.get("rpm_rule", {}).get("normal", [lim.get("warning_low", 1.0)])[0]
    base = eng.settle_thermal(100, eng.cfg.max_continuous_rpm, HOT, seconds=1800)
    oil0, p0 = base.oil_c, base.oil_bar
    t = eng.settle_thermal(100, eng.cfg.max_continuous_rpm, HOT, seconds=1800,
                           health={"pump_health": 0.3, "oil_p_min_bar": p_min})
    assert t.oil_bar < p0 * 0.5
    assert t.oil_c > oil0 + 1 and t.friction_multiplier > 1.0


def test_oil_cooler_blockage_raises_oil_temperature(eng):           # F25
    base = eng.settle_thermal(100, eng.cfg.max_continuous_rpm, HOT, seconds=2400).oil_c
    hot = eng.settle_thermal(100, eng.cfg.max_continuous_rpm, HOT, seconds=2400, health={"oil_cooler": 0.4}).oil_c
    assert hot > base + 10


def test_cht_responds_in_minutes_not_seconds(eng):                  # T-PHY-9
    eng.settle_thermal(60, eng.cfg.max_continuous_rpm, HOT, seconds=2400)
    start = eng.thermal.cht[0]
    eng.settle_thermal(100, eng.cfg.rated_rpm, HOT, seconds=10)
    assert abs(eng.thermal.cht[0] - start) < 0.5 * abs(eng.settle_thermal(100, eng.cfg.rated_rpm, HOT, seconds=2400).cht[0] - start)
