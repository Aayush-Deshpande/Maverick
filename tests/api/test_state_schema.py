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


def test_residuals_carry_the_detector_z_vector_by_channel():
    """M6-03: the engineer view shows measured-vs-model residuals; the message carries every detector channel."""
    from backend.runtime.hub import RuntimeHub
    hub = RuntimeHub(engines=["rotax_912is"])
    hub.calibrate_all(parallel=False)
    for _ in range(5):
        hub.tick_all()
    tick = hub.latest["rotax_912is"]
    msg = build_state(tick, seq=1)
    det = tick.detection
    assert det is not None and msg.residuals
    assert list(msg.residuals) == det.channel_names
    top_name, top_z = det.top_channels[0]
    assert msg.residuals[top_name] == pytest.approx(top_z, abs=1e-3) or abs(msg.residuals[top_name]) >= abs(top_z)


def _tick_with(runtime, hypotheses, status_level):
    tick = runtime.tick()
    tick.hypotheses = hypotheses
    tick.status = {"level": status_level, "reasons": [{"code": "X", "text": "x"}]}
    return tick


def test_detected_fault_highlights_its_parts_without_training_mode(runtime_912):
    """D5 / T-3D-2: the 3D highlight comes from diagnosis + status. A confident hypothesis lights its registry
    components in the status colour; the injected list plays no part (no active_faults passed)."""
    reg = load_fault_registry()
    hyp = [{"fault_id": "F23", "name": "OIL_PRESSURE_LOSS", "kind": "PROCESS", "posterior": 0.9}]
    msg = build_state(_tick_with(runtime_912, hyp, "NO-GO"), seq=3, registry=reg)
    hl = [h for h in msg.highlights if h.component_id == "oil_tank"]
    assert hl and hl[0].level == "NO-GO" and hl[0].nodes and "F23" in hl[0].reason
    assert all(h.level != "INJECTED" for h in msg.highlights)


def test_unconfident_hypotheses_light_nothing(runtime_912):
    reg = load_fault_registry()
    hyp = [{"fault_id": "F23", "name": "OIL_PRESSURE_LOSS", "kind": "PROCESS", "posterior": 0.3}]
    assert build_state(_tick_with(runtime_912, hyp, "CAUTION"), seq=4, registry=reg).highlights == []


def test_sensor_hypothesis_highlights_in_the_sensor_style(runtime_912):
    reg = load_fault_registry()
    hyp = [{"fault_id": "S02", "name": "SENSOR_BIAS", "kind": "SENSOR", "channel": "oil_p", "posterior": 0.95}]
    msg = build_state(_tick_with(runtime_912, hyp, "ADVISORY"), seq=5, registry=reg)
    assert msg.highlights and all(h.level == "SENSOR" for h in msg.highlights)


def test_hypothesis_outside_the_registry_lights_nothing_and_does_not_break_the_message(runtime_912):
    hyp = [{"fault_id": "UNKNOWN_ANOMALY", "name": "UNKNOWN", "kind": "PROCESS", "posterior": 0.95}]
    msg = build_state(_tick_with(runtime_912, hyp, "CAUTION"), seq=6, registry=load_fault_registry())
    assert msg.highlights == []


def test_detected_highlight_has_hysteresis_so_it_does_not_flicker(runtime_912):
    """Enter at hypothesis_posterior_min, leave only below highlight_exit_posterior (a posterior hovering at the
    entry threshold must not blink the part on and off every isolation cycle)."""
    reg = load_fault_registry()
    held: set = set()
    lit = lambda p: bool(build_state(_tick_with(runtime_912, [{"fault_id": "F23", "name": "OIL_PRESSURE_LOSS",
                                                               "kind": "PROCESS", "posterior": p}], "CAUTION"),
                                     seq=7, registry=reg, highlight_hold=held).highlights)
    assert not lit(0.6)              # below entry, not held yet
    assert lit(0.75)                 # enters
    assert lit(0.6)                  # held between exit and entry
    assert not lit(0.4)              # leaves below exit
    assert not lit(0.6)              # and needs the entry level again
