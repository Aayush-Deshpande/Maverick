"""Phase 8b copilot orchestrator (D45): read-only tools, the 7-section answer, and the honesty guards."""
from backend.agent.orchestrator import SECTIONS, answer
from backend.agent.tools import CopilotTools

STATE = {
    "engine_id": "e1", "engine_state": "RUNNING", "source": "SIM", "evidence_class": "SIMULATION", "sim_time_s": 120.0,
    "status": {"level": "NO-GO", "reasons": [{"code": "LIMIT", "text": "Oil pressure 0.6 bar below 0.8 bar"}]},
    "readings": {"oil_p": {"value": 0.6, "unit": "bar", "quality": "OK"}, "rpm": {"value": 5400.0, "unit": "rpm", "quality": "OK"}},
    "hypotheses": [{"fault_id": "F23", "name": "OIL_PRESSURE_LOSS", "posterior": 0.82, "supporting": [{"channel": "oil_p", "z": -6.1}]},
                   {"fault_id": "F26", "name": "BEARING_WEAR", "posterior": 0.18, "supporting": []}],
    "prognostics": {"rul": {"status": "OK", "rul_h": 40.0, "rul_lower_h": 10.0, "rul_upper_h": 70.0}, "time_to_limit": []},
    "reliability": {"mission_reliability": 0.91},
    "active_faults": [{"fault_id": "F23", "source": "console"}],          # truth: must never reach the copilot
    "events_since": [{"type": "FAULT_INJECTED", "text": "F23 injected"}],
}
FAULTS = {"F23": {"id": "F23", "name": "OIL_PRESSURE_LOSS", "ata_chapter": "79",
                  "physics_explanation": "Pump capacity falls, so oil pressure drops.",
                  "mitigation_inflight": {"text": "Reduce power; land as soon as possible.", "source": "OM sec 4"},
                  "maintenance_action": {"text": "Inspect the oil pump.", "source": "ANUMAAN-authored"}}}


class Source:
    def state(self, engine_id):
        return dict(STATE)

    def config(self, engine_id):
        return {"operating_limits": {"oil_p": {"unit": "bar", "warning_low": 0.8, "ref": "OM-912 i p.2-3"}}}

    def fault(self, fault_id):
        return FAULTS.get(fault_id)

    def work_orders(self, engine_id):
        return [{"id": "WO-1", "title": "Oil pump inspection", "status": "OPEN"}]


class Scripted:
    """Mock provider: calls two tools, then answers with the given sections."""
    name = "mock"

    def __init__(self, final):
        self.final, self.turn = final, 0

    def step(self, messages, tools):
        self.turn += 1
        if self.turn == 1:
            return {"content": "", "tool_calls": [{"name": "get_engine_state", "args": {"engine_id": "e1"}},
                                                  {"name": "get_hypotheses", "args": {"engine_id": "e1"}}]}
        return {"content": self.final, "tool_calls": []}


def _sections(result):
    return {s["key"]: s["text"] for s in result["sections"]}


def test_deterministic_answer_has_all_seven_sections_from_live_tools():
    r = answer(CopilotTools(Source()), "e1", "What is going on?")
    s = _sections(r)
    assert [x["key"] for x in r["sections"]] == [k for k, _ in SECTIONS]
    assert r["mode"] == "deterministic" and all(s[k] for k in s)
    assert "NO-GO" in s["what"]
    assert "land as soon as possible" in s["mitigation"] and "ATA 79" in s["fix"] and "WO-1" in s["fix"]
    assert "40" in s["prognosis"] and "F23" in s["confidence"] and "0.82" in s["confidence"]
    assert "OM-912 i p.2-3" in s["sources"] and "OM sec 4" in s["sources"]


def test_tools_never_return_the_injected_fault_list():
    tools = CopilotTools(Source())
    for name, tool in tools.tools.items():
        out = repr(tools.call(name, {"engine_id": "e1", "fault_id": "F23", "query": "oil"}))
        assert "active_faults" not in out and "FAULT_INJECTED" not in out and "console" not in out, name


def test_llm_numbers_are_grounded_and_status_is_never_contradicted():
    final = ('{"what": "Engine is fine.", "why": "Oil pressure is 0.6 bar. The pump has lost 37 % of its flow.", '
             '"mitigation": "Reduce power.", "fix": "Inspect the pump.", "prognosis": "About 40 h left.", '
             '"confidence": "Fairly sure."}')
    r = answer(CopilotTools(Source()), "e1", "Why?", Scripted(final))
    s = _sections(r)
    assert r["mode"] == "llm" and [c["name"] for c in r["tool_calls"]] == ["get_engine_state", "get_hypotheses"]
    assert "0.6 bar" in s["why"] and "37" not in s["why"]               # invented number dropped, grounded kept
    assert r["grounding"]["sentences_dropped"] == 1
    assert "NO-GO" in s["what"]                                         # "fine" contradicts NO-GO -> template
    assert s["prognosis"] == "About 40 h left."


def test_provider_failure_falls_back_to_the_deterministic_answer():
    class Down:
        name = "down"

        def step(self, messages, tools):
            raise ConnectionError("ollama not running")
    r = answer(CopilotTools(Source()), "e1", "Status?", Down())
    assert r["mode"] == "deterministic" and "ollama not running" in r["provider_error"]
    assert "NO-GO" in _sections(r)["what"]


def test_unknown_engine_state_is_reported_not_invented():
    class Empty(Source):
        def state(self, engine_id):
            return None
    s = _sections(answer(CopilotTools(Empty()), "e1", "Status?"))
    assert "no live state" in s["what"]
