"""M1-13 sensor layer S01-S07: only the faulty channel changes; seeded per-channel noise."""
import pytest

from backend.physics.engine_config import available_engines
from backend.sim.sensors import SensorLayer

ENG = available_engines()[0]
TRUE = {"cht[1]": 100.0, "cht[2]": 101.0, "oil_p": 4.0, "rpm": 5000.0, "fuel_flow": 18.0}


def f(effect, channel="cht[2]", severity=1.0, t0=0.0):
    return {"fault_id": "S", "channel": channel, "severity": severity, "t0_s": t0, "effects": [effect]}


def test_noise_is_seeded_per_channel_and_independent():
    a, b = SensorLayer(ENG, 1), SensorLayer(ENG, 1)
    assert a.measure(TRUE, 0) == b.measure(TRUE, 0)
    c = SensorLayer(ENG, 1)
    noisy = c.measure(TRUE, 0, [f("noise", "oil_p")])
    ref = SensorLayer(ENG, 1).measure(TRUE, 0)
    assert noisy["cht[1]"] == ref["cht[1]"]                       # other channels untouched


@pytest.mark.parametrize("effect", ["bias", "drift", "out_of_range"])
def test_offset_faults_move_only_their_channel(effect):
    s, ref = SensorLayer(ENG, 3), SensorLayer(ENG, 3)
    m, r = s.measure(TRUE, 600.0, [f(effect)]), ref.measure(TRUE, 600.0)
    assert abs(m["cht[2]"] - r["cht[2]"]) > 3.0
    assert m["cht[1]"] == r["cht[1]"] and m["oil_p"] == r["oil_p"]


def test_freeze_holds_and_dropout_is_null_never_a_default():
    s = SensorLayer(ENG, 4)
    first = s.measure(TRUE, 0, [f("freeze")])["cht[2]"]
    moved = dict(TRUE, **{"cht[2]": 140.0})
    assert s.measure(moved, 1, [f("freeze")])["cht[2]"] == first
    assert s.measure(TRUE, 2, [f("dropout")])["cht[2]"] is None


def test_drift_grows_with_time_and_lane_split_publishes_lane_b():
    s = SensorLayer(ENG, 5)
    early = s.measure(TRUE, 60, [f("drift")])["cht[2]"] - TRUE["cht[2]"]
    late = SensorLayer(ENG, 5).measure(TRUE, 600, [f("drift")])["cht[2]"] - TRUE["cht[2]"]
    assert late > early + 5
    m = SensorLayer(ENG, 6).measure(TRUE, 0, [f("lane_split", "oil_p")])
    assert abs(m["oil_p.lane_b"] - m["oil_p"]) > 0.1
