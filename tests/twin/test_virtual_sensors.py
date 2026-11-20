"""M1-17 virtual sensors (idea text section 15): physics from measured channels, None when an input is missing."""
import pytest

from backend.physics.engine_config import available_engines, load_engine_config
from backend.sim.source import SimSource
from backend.twin.virtual_sensors import VirtualSensorSynthesizer


def _frame(engine_id, throttle, alt=0.0, seconds=30.0):
    s = SimSource(engine_id, seed=0)
    f = None
    for _ in range(int(seconds / 0.05)):
        f, _ = s.step(0.05, throttle, alt)
    return f, s


@pytest.mark.parametrize("engine_id", available_engines())
def test_values_are_physical_and_follow_load(engine_id):
    cfg = load_engine_config(engine_id)
    vs = VirtualSensorSynthesizer(cfg)
    hi = vs.synthesize(_frame(engine_id, 100)[0])
    lo = vs.synthesize(_frame(engine_id, 40)[0])
    ci = cfg.is_compression_ignition
    assert (110 if ci else 40) < hi["P_max_bar"] < (200 if ci else 100)        # bar: Heywood ch. 9 ranges
    assert lo["P_max_bar"] < hi["P_max_bar"] and lo["P_ind_kw"] < hi["P_ind_kw"]
    assert hi["P_ind_kw"] > cfg.rated_power_kw * 0.9                             # indicated > brake
    assert 0.3 < hi["h_min_um"] < 25                                             # inside the radial clearance
    if cfg.is_turbocharged:
        f, _ = _frame(engine_id, 100)
        assert hi["TIT_degC"] < sum(f.egt) / len(f.egt)                           # manifold loses heat
    else:
        assert hi["TIT_degC"] is None                                            # not applicable: no turbine


def test_missing_input_gives_none_not_a_number():
    cfg = load_engine_config(available_engines()[0])
    f, _ = _frame(cfg.engine_id, 70)
    f.fuel_flow = None
    v = VirtualSensorSynthesizer(cfg).synthesize(f)
    assert v["P_max_bar"] is None and v["P_ind_kw"] is None and v["h_min_um"] is None


def test_hot_thin_oil_lowers_the_film():
    cfg = load_engine_config(available_engines()[0])
    f, _ = _frame(cfg.engine_id, 90)
    vs = VirtualSensorSynthesizer(cfg)
    f.oil_t = 80.0
    cool = vs.synthesize(f)["h_min_um"]
    f.oil_t = 130.0
    assert vs.synthesize(f)["h_min_um"] < cool
