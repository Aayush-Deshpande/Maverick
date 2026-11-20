"""M4-03: the in-service RUL reports UNAVAILABLE (with the training command) when no fleet model exists, and with a
trained model it returns a point estimate inside its conformal interval from the twin's residual features."""
import numpy as np

from backend.evaluation.sim_rul import fleet, train_and_save
from backend.prognose.rul_service import RULService


def test_unavailable_without_a_model(tmp_path):
    s = RULService("rotax_912is", path=tmp_path / "none.pkl")
    s.update(0.0, np.zeros(3), True)
    assert s.latest["status"] == "UNAVAILABLE" and "sim_rul" in s.latest["reason"]


def test_trained_model_predicts_with_interval(tmp_path, monkeypatch):
    monkeypatch.setenv("ANUMAAN_VAR_DIR", str(tmp_path))
    X, y, g = fleet("rotax_912is", 6)
    path = train_and_save("rotax_912is", X, y, g)
    s = RULService("rotax_912is", path=path)
    for k in range(s.bundle["sample_every"]):
        s.update(float(k), X[0, :-1], True)
    r = s.latest
    assert r["status"] == "OK" and r["rul_lower_h"] <= r["rul_h"] <= r["rul_upper_h"]
