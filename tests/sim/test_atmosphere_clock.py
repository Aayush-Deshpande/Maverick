"""M1-01 (sim clock, D8 time scales) and M1-02 (ISA atmosphere + humidity, P Part 4 Step 1.3a)."""
import math

import pytest

from backend.sim.atmosphere import Atmosphere
from backend.sim.clock import SimClock, load_sim_settings

FT = 0.3048
# ISA table (ICAO Doc 7488): altitude m -> (T K, p Pa, rho kg/m3)
ISA = {0: (288.15, 101325.0, 1.2250), 1000: (281.65, 89874.6, 1.1117), 3000: (268.65, 70108.5, 0.9093),
       5000: (255.65, 54019.9, 0.7361), 8000: (236.15, 35599.8, 0.5252), 10000: (223.15, 26436.3, 0.4127)}


@pytest.mark.parametrize("h_m", sorted(ISA))
def test_isa_points_within_0_1_percent(h_m):
    T, p, rho = ISA[h_m]
    a = Atmosphere.at(altitude_ft=h_m / FT)
    assert a.temperature_k == pytest.approx(T, rel=1e-3)
    assert a.pressure_pa == pytest.approx(p, rel=1e-3)
    assert a.density_kg_m3 == pytest.approx(rho, rel=1e-3)


def test_isa_deviation_changes_temperature_and_density_not_pressure():
    std, hot = Atmosphere.at(altitude_ft=5000), Atmosphere.at(altitude_ft=5000, isa_dev_c=30)
    assert hot.temperature_k == pytest.approx(std.temperature_k + 30)
    assert hot.pressure_pa == pytest.approx(std.pressure_pa)
    assert hot.density_kg_m3 < std.density_kg_m3


def test_humidity_lowers_density():
    dry, wet = Atmosphere.at(altitude_ft=0, isa_dev_c=15), Atmosphere.at(altitude_ft=0, isa_dev_c=15, humidity_pct=100)
    assert wet.density_kg_m3 < dry.density_kg_m3
    assert 0 < (dry.density_kg_m3 - wet.density_kg_m3) / dry.density_kg_m3 < 0.03     # a few % at 30 C


def test_oat_input_is_an_alternative_to_isa_dev():
    a = Atmosphere.at(altitude_ft=10000, oat_c=-5.0)
    assert a.temperature_k == pytest.approx(268.15)


def test_clock_time_scales_come_from_config_and_substep():
    s = load_sim_settings()
    assert s["time_scales"] == [1, 5, 20, 60]                     # DECISIONS D8
    c = SimClock(internal_step_s=s["internal_step_s"], publish_period_s=1 / 20)
    for scale in s["time_scales"]:
        c.set_time_scale(scale)
        steps = c.steps_for_publish()
        assert steps * c.internal_step_s == pytest.approx(scale / 20)
    with pytest.raises(ValueError):
        c.set_time_scale(7)


def test_clock_advances_sim_time_exactly():
    c = SimClock(internal_step_s=0.01, publish_period_s=0.05)
    c.set_time_scale(20)
    for _ in range(10):
        for _ in range(c.steps_for_publish()):
            c.advance()
    assert c.sim_time_s == pytest.approx(10.0)
    assert math.isclose(c.sim_time_s, 10.0, abs_tol=1e-9)
