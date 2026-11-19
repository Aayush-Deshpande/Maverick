"""Card M0-02: fault registry (configs/faults.json) loads, validates, and gates applicability per engine.
T-CFG-1 (broken registry refuses to load) and T-FLT-3 (inapplicable combinations rejected with a reason)."""
import json

import pytest

from backend.faults.registry import FaultRegistryError, FaultRejected, load_fault_registry
from backend.physics.engine_config import available_engines, load_engine_config


@pytest.fixture(scope="module")
def reg():
    return load_fault_registry()


def test_registry_has_all_44_faults(reg):
    ids = reg.ids()
    assert ids == [f"F{i:02d}" for i in range(1, 38)] + [f"S{i:02d}" for i in range(1, 8)]


def test_broken_registry_refuses_to_load(tmp_path):  # T-CFG-1
    data = load_fault_registry().as_dict()
    data["faults"][0]["scope"] = "NOT_A_SCOPE"
    bad = tmp_path / "faults.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(FaultRegistryError, match="scope"):
        load_fault_registry(bad)


def test_duplicate_ids_rejected(tmp_path):
    data = load_fault_registry().as_dict()
    data["faults"].append(dict(data["faults"][0]))
    bad = tmp_path / "faults.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(FaultRegistryError, match="duplicate"):
        load_fault_registry(bad)


@pytest.mark.parametrize("fault_id,applies,not_applies", [
    ("F01", ["rotax_912is", "rotax_914", "rotax_915is"], ["austro_ae300", "vrde_jayem_2_2l"]),   # SI misfire
    ("F05", ["rotax_912is", "rotax_915is"], ["rotax_914", "austro_ae300", "vrde_jayem_2_2l"]),  # port injection
    ("F06", ["austro_ae300", "vrde_jayem_2_2l"], ["rotax_912is", "rotax_914", "rotax_915is"]),  # CI common rail
    ("F12", ["rotax_914"], ["rotax_912is", "rotax_915is", "austro_ae300", "vrde_jayem_2_2l"]),  # carburettor
    ("F14", ["rotax_914", "rotax_915is", "austro_ae300", "vrde_jayem_2_2l"], ["rotax_912is"]),  # turbo
    ("F18", ["rotax_915is", "austro_ae300", "vrde_jayem_2_2l"], ["rotax_912is", "rotax_914"]),  # intercooler
    ("F35", ["austro_ae300", "vrde_jayem_2_2l"], ["rotax_912is", "rotax_914", "rotax_915is"]),  # glow plugs
    ("F37", ["austro_ae300", "vrde_jayem_2_2l"], ["rotax_912is", "rotax_914", "rotax_915is"]),  # governor
])
def test_applicability_per_engine(reg, fault_id, applies, not_applies):
    spec = reg.get(fault_id)
    for e in applies:
        assert spec.applicability(load_engine_config(e))[0], f"{fault_id} should apply to {e}"
    for e in not_applies:
        ok, reason = spec.applicability(load_engine_config(e))
        assert not ok and reason, f"{fault_id} must not apply to {e}"


def test_inapplicable_request_rejected_with_reason(reg):  # T-FLT-3
    with pytest.raises(FaultRejected, match="fuel_system"):
        reg.validate_request(load_engine_config("austro_ae300"), "F12")
    with pytest.raises(FaultRejected, match="ignition_mode"):
        reg.validate_request(load_engine_config("vrde_jayem_2_2l"), "F01", cylinder=2)


def test_cylinder_channel_severity_validation(reg):
    cfg = load_engine_config("rotax_912is")
    with pytest.raises(FaultRejected, match="cylinder"):
        reg.validate_request(cfg, "F01")
    with pytest.raises(FaultRejected, match="cylinder"):
        reg.validate_request(cfg, "F01", cylinder=5)
    with pytest.raises(FaultRejected, match="engine-level"):
        reg.validate_request(cfg, "F23", cylinder=1)
    with pytest.raises(FaultRejected, match="channel"):
        reg.validate_request(cfg, "S03")
    with pytest.raises(FaultRejected, match="severity"):
        reg.validate_request(cfg, "F23", severity=1.5)
    with pytest.raises(FaultRejected, match="unknown"):
        reg.validate_request(cfg, "F99")
    assert reg.validate_request(cfg, "F01", cylinder=2, severity=0.8, ramp_s=5).id == "F01"


def test_legacy_ids_map_by_registry_not_position(reg):
    assert reg.by_legacy_id(4).name == "OIL_PRESSURE_LOSS"
    assert reg.by_legacy_id(3).name == "IGNITION_MISFIRE"
    with pytest.raises(FaultRejected):
        reg.by_legacy_id(9)


def test_signature_resolution(reg):
    sig = reg.get("F01").resolved_signature(cylinder=3)
    assert {"egt[3]", "cht[3]", "rpm"} <= {s["channel"] for s in sig}
    sig_all = reg.get("F03").resolved_signature(n_cylinders=4)
    assert {"cht[1]", "cht[4]"} <= {s["channel"] for s in sig_all}
    assert reg.get("S03").resolved_signature(channel="cht[2]")[0]["channel"] == "cht[2]"


@pytest.mark.parametrize("engine_id", available_engines())
def test_every_engine_has_faults_in_every_ps_category(reg, engine_id):
    cats = set()
    for spec in reg.applicable(load_engine_config(engine_id)):
        cats.update(spec.raw["ps_categories"])
    for required in ["misfire", "injector abnormalities", "cooling degradation", "lubrication issues",
                     "sensor drift/failure", "combustion instability", "overheating trends", "abnormal vibration"]:
        # the carburetted 914 covers "injector abnormalities" through F10 fuel supply (applies to every engine)
        assert required in cats, f"{engine_id} has no applicable fault for PS category {required!r}"
