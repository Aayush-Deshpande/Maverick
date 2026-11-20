"""D61: one physical sensor feeding several channels (the accelerometer's vibration orders) is ONE sensor-fault
hypothesis, so a single raised order points at a mechanical fault, not at a sensor offset."""
import numpy as np

from backend.diagnose.isolator import BayesianIsolator


def test_vibration_orders_share_one_accelerometer_hypothesis():
    chans = ["oil_p", "vib_1X", "vib_gear_mesh", "vib_firing"]
    iso = BayesianIsolator("rotax_912is", chans)
    sensors = [h[3] for h in iso.hyp if h[1] == "SENSOR"]
    assert "oil_p" in sensors and "vibration accelerometer" in sensors
    assert not any(s.startswith("vib_") for s in sensors)
    iso.update(np.array([0.0, 6.0, 0.0, 0.0]))                  # only the 1X order rises
    top = iso.posterior(coupling=np.eye(4))[0]
    assert top.kind != "SENSOR"
