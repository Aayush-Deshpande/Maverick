"""M1-08 electrical: alternators, regulator, battery SOC, loads (P Part 4 Step 1.3h; F32-F34 parameter effects)."""
import pytest

from backend.physics.engine_config import available_engines
from backend.sim.electrical import Electrical

DT = 1.0


def run(e, rpm, seconds, **health):
    for _ in range(int(seconds / DT)):
        e.step(DT, rpm, **health)
    return e


@pytest.mark.parametrize("engine_id", available_engines())
def test_running_engine_holds_the_regulated_bus_and_charges(engine_id):
    e = Electrical.for_engine(engine_id)
    e.soc = 0.8
    run(e, 5000, 60)
    assert e.bus_v == pytest.approx(e.regulator_v, abs=0.05)
    assert e.battery_a > 0 and e.soc > 0.8                         # charging
    assert e.alternator_a > 0


def test_alternator_failure_discharges_and_voltage_sags_on_its_curve():   # F32
    e = Electrical.for_engine(available_engines()[0])
    run(e, 5000, 10)
    v = [run(e, 5000, 600, alternator_health=0.0).bus_v for _ in range(6)]
    assert e.battery_a < 0
    assert v[0] < e.regulator_v and all(b < a for a, b in zip(v, v[1:]))    # falls as SOC falls


def test_below_cut_in_the_battery_carries_the_load():
    e = Electrical.for_engine(available_engines()[0])
    run(e, 500, 60)
    assert e.alternator_a == 0 and e.battery_a < 0


def test_regulator_fault_drives_the_bus_voltage():                      # F33
    e = Electrical.for_engine(available_engines()[0])
    assert run(e, 5000, 30, regulator_offset_v=1.5).bus_v > e.regulator_v + 1.0


def test_battery_degradation_sags_more_under_load():                    # F34
    a, b = Electrical.for_engine(available_engines()[0]), Electrical.for_engine(available_engines()[0])
    run(a, 0, 300)
    run(b, 0, 300, battery_health=0.3)
    assert b.bus_v < a.bus_v - 0.1


def test_912_has_two_generators():
    assert len(Electrical.for_engine("rotax_912is").alternators) == 2
