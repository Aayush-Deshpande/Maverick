"""M1-09 vibration orders from cylinder torque imbalance (P Part 4 Step 1.3i, R 21.4)."""
import pytest

from backend.physics.engine_config import available_engines, load_engine_config
from backend.sim.vibration import Vibration


@pytest.mark.parametrize("engine_id", available_engines())
def test_misfire_raises_half_and_first_order_at_least_3x(engine_id):     # P 1.3i test
    cfg = load_engine_config(engine_id)
    v = Vibration.for_engine(cfg)
    n = cfg.cylinder_count
    healthy = v.orders([1.0] * n, torque_fraction=0.8, prop_rpm=2300)
    torques = [1.0] * n
    torques[1] = 0.0
    misfire = v.orders(torques, torque_fraction=0.6, prop_rpm=2300)
    assert misfire["0.5X"] >= 3 * healthy["0.5X"] and misfire["1X"] >= 3 * healthy["1X"]
    assert misfire["rms"] > healthy["rms"]


def test_firing_order_scales_with_torque_and_faults_hit_their_own_order():
    cfg = load_engine_config(available_engines()[0])
    v = Vibration.for_engine(cfg)
    n = cfg.cylinder_count
    lo, hi = v.orders([1.0] * n, 0.3, 2300), v.orders([1.0] * n, 1.0, 2300)
    assert hi["firing"] > lo["firing"] * 2
    base = v.orders([1.0] * n, 0.8, 2300)
    prop = v.orders([1.0] * n, 0.8, 2300, prop_imbalance=1.0)
    gear = v.orders([1.0] * n, 0.8, 2300, gear_damage=1.0)
    mount = v.orders([1.0] * n, 0.8, 2300, mount_degradation=1.0)
    assert prop["prop_1X"] > 5 * base["prop_1X"] and prop["gear_mesh"] == pytest.approx(base["gear_mesh"])
    assert gear["gear_mesh"] > 5 * base["gear_mesh"] and gear["prop_1X"] == pytest.approx(base["prop_1X"])
    assert all(mount[k] > base[k] for k in ("firing", "prop_1X", "gear_mesh"))      # all orders rise together


def test_order_frequencies_follow_rpm():
    cfg = load_engine_config(available_engines()[0])
    f = Vibration.for_engine(cfg).frequencies_hz(engine_rpm=6000, prop_rpm=2400)
    assert f["1X"] == pytest.approx(100.0) and f["0.5X"] == pytest.approx(50.0)
    assert f["firing"] == pytest.approx(100.0 * cfg.cylinder_count / 2) and f["prop_1X"] == pytest.approx(40.0)
