"""T-PRG-3 (M4-06): the adaptive baseline never learns while status is not GO (or GO for less than the hold time),
while CUSUM > h/2, during a detector or novelty alarm, or with an open work order; learned versions move a channel
by at most the step limit, and rollback restores an earlier version."""
from types import SimpleNamespace

import numpy as np
import pytest

from backend.detect.adaptive import AdaptiveBaseline
from backend.detect.cusum import load_detect_config

CFG = load_detect_config()["adaptive"]
HOLD = CFG["hold_go_s"]["value"]


class FakeCal:
    def __init__(self):
        self.intercept = np.zeros(2)
        self.sigma = np.ones(2)

    def channel_names(self):
        return ["a", "b"]


def det(z=(0.3, -0.2), drift=0.0, novelty=False, confirmed=False):
    return SimpleNamespace(z_raw=np.array(z), drift={"ratio": drift}, novelty={"raw": novelty},
                           confirmed=confirmed, raw_alarm=confirmed)


@pytest.fixture
def ab(tmp_path):
    return AdaptiveBaseline(FakeCal(), "T1", path=tmp_path / "b.json")


def test_guards_block_learning(ab):
    assert not ab.update(0.0, "CAUTION", det())                       # not GO
    for t in range(1, int(HOLD)):
        assert not ab.update(float(t), "GO", det())                   # GO, but not long enough
    t = HOLD + 1
    assert ab.update(t, "GO", det())                                  # all guards pass
    assert not ab.update(t + 1, "GO", det(drift=CFG["cusum_fraction"]["value"] + 0.1))
    assert not ab.update(t + 2, "GO", det(novelty=True))
    assert not ab.update(t + 3, "GO", det(confirmed=True))
    assert not ab.update(t + 4, "GO", det(), open_orders=1)
    assert not ab.update(t + 5, "ADVISORY", det())
    assert not ab.update(t + 6, "GO", det())                          # the hold restarts after a non-GO frame
    assert ab.status()["reason"] == "GO for less than the hold time"


def test_commit_is_step_limited_and_rollback_restores(ab):
    t = 0.0
    for _ in range(int(HOLD) + 1):
        ab.update(t, "GO", det(z=(0.0, 0.0)))
        t += 1.0
    big = (10.0, 0.0)                                                 # a fault-sized shift on channel a
    while ab.status()["version"] == 0:
        ab.update(t, "GO", det(z=big))
        t += 1.0
    step = CFG["offset_step_limit_sigma"]["value"]
    assert ab.cal.intercept[0] <= step + 1e-9                         # never more than the step limit per version
    assert ab.cal.sigma[0] <= CFG["sigma_step_limit"]["value"] + 1e-9
    ab.rollback(0)
    assert np.allclose(ab.cal.intercept, 0.0) and np.allclose(ab.cal.sigma, 1.0)
    assert ab.status()["note"] == "rollback to v0" and ab.path.exists()
