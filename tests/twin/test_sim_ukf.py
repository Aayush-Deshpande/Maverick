"""M3-01 state observer: UKF on the M1 thermal model with measured inputs. Health parameters stay near 1 on a
healthy tail and move on the right component when a cooling fault is injected (the observer never sees the fault)."""
import numpy as np
import pytest

from backend.physics.engine_config import available_engines
from backend.sources import PlantSource
from backend.twin.sim_ukf import SimThermalUKF


def fly(engine_id, fault=None, cylinder=None, seconds=1200, inject_at=300, seed=3, every=5):
    src = PlantSource(engine_id, seed=seed)
    ukf = SimThermalUKF(src.cfg)
    nis = []
    for i in range(seconds):
        if fault and i == inject_at:
            src.inject_fault(fault, cylinder=cylinder, severity=1.0, ramp_sec=60)
        f, _ = src.step(1.0, throttle_pct=70, altitude_ft=5000, oat_c=15)
        if i % every == 0 and ukf.ready(f):
            nis.append(ukf.step(f))
    return ukf, {(p.name, p.location): p for p in ukf.get_parameter_estimates(f.t)}, nis


@pytest.mark.parametrize("engine_id", available_engines())
def test_healthy_tail_parameters_near_one_and_nis_in_band(engine_id):
    ukf, est, nis = fly(engine_id)
    for p in est.values():
        assert 0.85 < p.mean < 1.15, (p.name, p.location, p.mean)       # build spread only
    assert 0.2 < float(np.mean(nis[20:])) < 3 * (ukf.n + 2)            # NIS ~ measurement dimension, not exploding


def test_radiator_blockage_is_located_on_the_radiator():
    _, est, _ = fly("austro_ae300", fault="F21")
    rad = est[("eta_radiator", "radiator")].mean
    others = [p.mean for k, p in est.items() if k != ("eta_radiator", "radiator")]
    assert rad < 0.8 and rad < min(others) - 0.15


def test_one_cylinder_cooling_loss_is_located_on_its_cylinder():
    _, est, _ = fly("rotax_914", fault="F19", cylinder=2)
    cyl = {k[1]: p.mean for k, p in est.items() if k[0] == "eta_cool"}
    assert min(cyl, key=cyl.get) == "cyl2"


def test_quarantined_and_missing_channels_are_not_used():
    src = PlantSource("rotax_912is", seed=1)
    ukf = SimThermalUKF(src.cfg)
    for i in range(60):
        f, _ = src.step(1.0, throttle_pct=70, altitude_ft=5000, oat_c=15)
        if i % 5 == 0:
            ukf.step(f)
    before = ukf.x.copy()
    f.cht[0] = f.cht[0] + 80.0                                          # a wild reading on a quarantined channel
    ukf.step(f, skip={"cht_1"})
    assert abs(ukf.x[0] - before[0]) < 10.0
    f.fuel_flow = None
    assert not ukf.ready(f)                                             # no measured input -> no prediction
