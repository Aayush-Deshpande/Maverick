"""Tests for backend/core/pipeline.py, channels.py, limits.py, and profile.py (B1.3, U1, U2, U3)."""

import pytest
from backend.core.channels import channel_names, channel_specs
from backend.core.frame import Frame
from backend.core.limits import check_limits
from backend.core.pipeline import FunctionStage, Pipeline
from backend.core.profile import load_all_profiles, load_profile
from backend.osacbm import Layer
from backend.physics.engine_config import load_engine_config


def test_pipeline_layer_ordering():
    def dummy_proc(frame, res):
        return 1

    s_da = FunctionStage("da", Layer.DA, dummy_proc)
    s_dm = FunctionStage("dm", Layer.DM, dummy_proc)
    s_ha = FunctionStage("ha", Layer.HA, dummy_proc)

    # Valid ascending order
    p = Pipeline([s_da, s_dm, s_ha])
    assert len(p.stages) == 3

    # Invalid descending order
    with pytest.raises(ValueError, match="OSA-CBM layer"):
        Pipeline([s_ha, s_da])


def test_pipeline_unique_names():
    def dummy_proc(frame, res):
        return 1

    s1 = FunctionStage("same", Layer.DA, dummy_proc)
    s2 = FunctionStage("same", Layer.DM, dummy_proc)
    with pytest.raises(ValueError, match="unique"):
        Pipeline([s1, s2])


def test_pipeline_execution_and_cadence():
    calls_every1 = 0
    calls_every2 = 0

    def fn1(frame, res):
        nonlocal calls_every1
        calls_every1 += 1
        return "out1"

    def fn2(frame, res):
        nonlocal calls_every2
        calls_every2 += 1
        return f"out2_{res['s1']}"

    s1 = FunctionStage("s1", Layer.DA, fn1, every_n=1)
    s2 = FunctionStage("s2", Layer.SD, fn2, every_n=2)

    p = Pipeline([s1, s2])
    f = Frame(t=0.0, source="PLANT", engine_config_id="rotax_914", cht=[100.0, 100.0, 100.0, 100.0], egt=[600.0, 600.0, 600.0, 600.0])

    # Frame 1: s1 runs, s2 skipped
    r1 = p.push(f)
    assert r1 == {"s1": "out1"}
    assert calls_every1 == 1
    assert calls_every2 == 0

    # Frame 2: s1 and s2 both run
    r2 = p.push(f)
    assert r2 == {"s1": "out1", "s2": "out2_out1"}
    assert calls_every1 == 2
    assert calls_every2 == 1

    rep = p.timing_report()
    assert "s1" in rep and rep["s1"]["calls"] == 2
    assert "s2" in rep and rep["s2"]["calls"] == 1


def test_channel_registry():
    cfg_rotax = load_engine_config("rotax_912is")
    specs_rotax = channel_specs(cfg_rotax)
    names_rotax = channel_names(cfg_rotax)

    assert "cht_1" in names_rotax and "cht_4" in names_rotax
    assert "cht_5" not in names_rotax
    assert "rail_p" not in names_rotax  # SI NA engine has no rail_p

    cfg_diesel = load_engine_config("vrde_jayem_2_2l")
    specs_diesel = channel_specs(cfg_diesel)
    names_diesel = channel_names(cfg_diesel)

    assert "rail_p" in names_diesel
    assert "boost_target_kpa" in names_diesel


def test_limits_check():
    cfg = load_engine_config("rotax_914")
    # Redline for cht is 135 degC in operating_limits
    f_ok = Frame(
        t=1.0,
        source="PLANT",
        engine_config_id="rotax_914",
        rpm=4000.0,
        oil_p=3.0,
        cht=[120.0, 120.0, 120.0, 120.0],
        egt=[800.0, 800.0, 800.0, 800.0],
    )
    assert len(check_limits(f_ok, cfg)) == 0

    # Overheat on cyl 3
    f_over = Frame(
        t=2.0,
        source="PLANT",
        engine_config_id="rotax_914",
        rpm=4000.0,
        oil_p=3.0,
        cht=[120.0, 120.0, 140.0, 120.0],
        egt=[800.0, 800.0, 800.0, 800.0],
    )
    ex = check_limits(f_over, cfg)
    assert len(ex) == 1
    assert ex[0].limit == "cht_max_c"
    assert ex[0].channel == "cht_3"
    assert ex[0].value == 140.0

    # Low oil pressure while running
    f_low_oil = Frame(
        t=3.0,
        source="PLANT",
        engine_config_id="rotax_914",
        rpm=4000.0,
        oil_p=0.5,
        cht=[120.0, 120.0, 120.0, 120.0],
        egt=[800.0, 800.0, 800.0, 800.0],
    )
    ex_oil = check_limits(f_low_oil, cfg)
    assert any(e.limit == "oil_p_min_bar" for e in ex_oil)


def test_engine_profile():
    profiles = load_all_profiles()
    assert len(profiles) == 5
    assert "rotax_914" in profiles
    assert "austro_ae300" in profiles
    assert "vrde_jayem_2_2l" in profiles

    ae300_prof = profiles["austro_ae300"]
    assert ae300_prof.is_ci is True
    assert ae300_prof.is_turbo is True
    assert ae300_prof.asset_manifest is not None
    assert "Engine_Block" in ae300_prof.get_components()

    schema = ae300_prof.to_schema()
    assert schema["engine_id"] == "austro_ae300"
    assert "channels" in schema
    assert "operating_limits" in schema
    assert "components" in schema
    assert len(schema["components"]) > 0
    assert "PUBLIC" in schema["provenance_summary"]
