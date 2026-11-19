"""Card M0-05: versioned state message. T-API-2 (schema drift) and the null-not-default rule (D7)."""
import json
from pathlib import Path

import pytest

from backend.faults.manager import FaultManager, RuntimeAdapter
from backend.faults.registry import load_fault_registry
from backend.server.state_builder import build_state, resolve_fault_components
from backend.server.state_schema import StateMessage, state_json_schema

ROOT = Path(__file__).resolve().parents[2]


def test_committed_schema_matches_the_pydantic_model():  # T-API-2
    committed = json.loads((ROOT / "configs" / "schema" / "state.schema.json").read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(state_json_schema(), sort_keys=True)), \
        "run python scripts/assets/export_state_schema.py and npm run gen:types"


def test_generated_typescript_exists_and_names_the_message():
    ts = (ROOT / "frontend" / "src" / "api" / "state.ts").read_text(encoding="utf-8")
    assert "export interface StateMessage" in ts and "Do not edit" in ts


@pytest.fixture(scope="module")
def runtime_912():
    from backend.runtime.engine_runtime import EngineRuntime
    rt = EngineRuntime("rotax_912is", seed=11)
    return rt


def test_state_from_a_real_tick_validates_and_keeps_unknown_status(runtime_912):
    mgr = FaultManager(load_fault_registry(), runtime_912.cfg, RuntimeAdapter(runtime_912))
    mgr.inject("F01", cylinder=2, severity=0.8, ramp_s=1, source="test")
    tick = runtime_912.tick()
    msg = build_state(tick, seq=1, registry=mgr.registry, active_faults=mgr.active(), fault_events=mgr.history())
    StateMessage.model_validate(msg.model_dump())
    # M2-01: the evaluator's verdict from observables (never a hard-coded GO); non-GO always carries a reason
    assert msg.status.level in ("ENGINE_OFF", "GO", "ADVISORY", "CAUTION", "NO-GO")
    assert msg.status.level in ("GO", "ENGINE_OFF") or msg.status.reasons
    assert msg.readings["rpm"].unit == "rpm" and msg.readings["rpm"].value is not None
    assert "cht[1]" in msg.readings and msg.readings["oil_p"].unit == "bar"
    assert msg.active_faults[0].fault_id == "F01" and msg.active_faults[0].cylinder == 2
    assert msg.events_since[0].type == "FAULT_INJECTED"
    assert msg.highlights == []                               # not training mode: no INJECTED outline (D5)


def test_training_mode_shows_injected_outline_with_exact_nodes(runtime_912):
    mgr = FaultManager(load_fault_registry(), runtime_912.cfg, RuntimeAdapter(runtime_912))
    mgr.inject("F23", source="test")
    msg = build_state(runtime_912.tick(), seq=2, registry=mgr.registry, active_faults=mgr.active(),
                      training_mode=True)
    hl = [h for h in msg.highlights if h.component_id == "oil_tank"]
    assert hl and hl[0].level == "INJECTED" and hl[0].nodes and all(n.startswith("Oil_Tank_") for n in hl[0].nodes)


def test_missing_values_are_null_not_defaults(runtime_912):
    tick = runtime_912.tick()
    tick.frame.oil_p = None
    msg = build_state(tick, seq=3)
    assert "oil_p" not in msg.readings                        # absent, not a made-up number


def test_component_resolution_per_cylinder_and_marker():
    reg = load_fault_registry()
    ids, marker = resolve_fault_components(reg.get("F06").raw, "austro_ae300", 3, None)
    assert ids == ["injector_3", "fuel_line_3"] and marker is None
    ids, marker = resolve_fault_components(reg.get("F01").raw, "rotax_915is", 4, None)
    assert ids == ["main_engine_MERGED"] and marker == "cylinder 4"
    ids, marker = resolve_fault_components(reg.get("S03").raw, "vrde_jayem_2_2l", None, "egt[2]")
    assert ids == ["sensor_egt_2"]
