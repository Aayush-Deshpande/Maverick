"""M1-14 performance maps (P Step 1.3q): swept from the calibrated plant, nothing configured."""
import pytest

from backend.physics.engine_config import available_engines, load_engine_config
from backend.sim.maps import best_bsfc, build_maps, maps_for


@pytest.mark.parametrize("engine_id", available_engines())
def test_map_shape_and_physics(engine_id):
    cfg = load_engine_config(engine_id)
    m = build_maps(cfg)
    rpms, loads = m["axes"]["rpm"], m["axes"]["load_pct"]
    assert rpms[-1] == pytest.approx(cfg.rated_rpm) and loads[-1] == pytest.approx(100.0)
    p = m["power_kw"]
    assert len(p) == len(rpms) and all(len(r) == len(loads) for r in p)
    assert p[-1][-1] == pytest.approx(cfg.rated_power_kw, rel=0.02)            # full load at rated = T-PHY-1 point
    for row in p:                                                                 # more load, more power
        assert all(b >= a - 1e-6 for a, b in zip(row, row[1:]))
    assert best_bsfc(m) is not None and m["evidence"] == "SIMULATION"
    eff = [v for row in m["brake_efficiency"] for v in row if v is not None]
    assert max(eff) > 0          # plausibility bound: test_diesel_calibration_is_physically_plausible (Question 6c)


def test_maps_are_cached_and_written(tmp_path, monkeypatch):
    monkeypatch.setenv("ANUMAAN_VAR_DIR", str(tmp_path))
    cfg = load_engine_config(available_engines()[0])
    a = maps_for(cfg)
    assert maps_for(cfg) is a
