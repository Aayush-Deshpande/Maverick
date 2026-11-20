"""M3-04/M3-08 model-informed residual (backend/detect/reference.py + calibration.py): a varied-lever nominal flight
stays (almost) free of confirmed alarms, the tail's air-path factor is identified from fuel flow, and a biased input
sensor is told apart from a real change through the channels the model predicts from it."""

import numpy as np
import pytest

from backend.evaluation.tail import calibrated
from backend.sources import PlantSource

LEGS = [(60, 9000, 10), (75, 12000, 10), (55, 5000, 10)]       # lever changes and climbs, 10 min each
EPISODE_BUDGET = 1                                              # Phase 3 checkpoint: < 1 false alarm per flight hour


@pytest.mark.parametrize("engine_id", ["rotax_912is", "rotax_914"])
def test_varied_lever_nominal_flight_has_no_false_alarm_episodes(engine_id):
    src, det = calibrated(engine_id, 1002)
    episodes, prev = 0, False
    for thr, alt, oat in LEGS:
        for _ in range(600):
            f, _ = src.step(1.0, throttle_pct=thr, altitude_ft=alt, oat_c=oat)
            r = det.score(f)
            episodes += r.confirmed and not prev
            prev = r.confirmed
    assert episodes <= EPISODE_BUDGET


def test_tail_air_path_factor_is_identified():
    src, det = calibrated("rotax_914", 1001)
    true_ve = PlantSource("rotax_914", seed=1001).variation["volumetric_efficiency"]   # test-side truth only
    assert det.cal.tail["volumetric_efficiency"] == pytest.approx(true_ve, abs=0.01)


def test_biased_oil_temperature_sender_moves_the_predicted_oil_pressure():
    src, det = calibrated("rotax_912is", 1001)
    f, _ = src.step(1.0, throttle_pct=70, altitude_ft=7000, oat_c=15)
    det.score(f)
    C = det.cal.sensor_coupling(f)
    names = det.cal.channel_names()
    col = C[:, names.index("oil_t")]
    assert col[names.index("oil_t")] == 1.0
    assert abs(col[names.index("oil_p")]) > 0.0                 # oil pressure is predicted from the measured oil_t
    assert np.allclose(C[:, names.index("cht_1")], np.eye(len(names))[:, names.index("cht_1")])
