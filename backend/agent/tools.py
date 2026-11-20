"""Read-only tools for the copilot agent (Phase 8b, D45).

Every tool reads what the operator's screen already shows - the last state message of an engine
(services().channel(id).last_message) - or the configs (limits with their manual references, fault registry
knowledge). None of them can inject a fault, move a lever or change state, and none returns the injected-fault list:
the copilot explains the diagnosis, it never peeks at the answer (same no-truth-leak rule as detection, P Part 0 D4).
Results are plain JSON-able dicts so the same calls serve the LLM tool loop and the deterministic answer.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol

HIDDEN_KEYS = ("active_faults", "events_since")      # truth / injection history: never handed to the copilot


class StateSource(Protocol):
    def state(self, engine_id: str) -> Optional[Dict[str, Any]]: ...
    def config(self, engine_id: str) -> Dict[str, Any]: ...
    def fault(self, fault_id: str) -> Optional[Dict[str, Any]]: ...
    def work_orders(self, engine_id: str) -> List[Dict[str, Any]]: ...


def _round(v: Any) -> Any:
    if isinstance(v, float):
        return round(v, 3 if abs(v) < 10 else 1)
    if isinstance(v, dict):
        return {k: _round(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_round(x) for x in v]
    return v


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    fn: Callable[..., Dict[str, Any]]

    def schema(self) -> Dict[str, Any]:
        """JSON-schema function declaration (Ollama `tools` entry / Gemini parameters_json_schema)."""
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


_ENGINE = {"type": "object", "properties": {"engine_id": {"type": "string"}}, "required": ["engine_id"]}


class CopilotTools:
    def __init__(self, source: StateSource):
        self.src = source
        self.tools: Dict[str, Tool] = {t.name: t for t in (
            Tool("get_engine_state", "Engine status (GO/ADVISORY/CAUTION/NO-GO) with reasons, engine state, data "
                 "source and every live reading with unit and quality.", _ENGINE, self.get_engine_state),
            Tool("get_limits", "Operating limits of the engine (normal band, warning limits, rpm rules) with the "
                 "manual reference for each.", {"type": "object", "properties": {
                     "engine_id": {"type": "string"}, "channel": {"type": "string"}}, "required": ["engine_id"]},
                 self.get_limits),
            Tool("get_hypotheses", "Ranked fault hypotheses from the diagnosis, with posterior probability, cylinder "
                 "and the residual evidence for and against.", _ENGINE, self.get_hypotheses),
            Tool("get_fault_knowledge", "Registry entry for a fault id (F01..F37, S01..S07): physics mechanism, "
                 "in-flight mitigation, maintenance action, ATA chapter, status at full severity, sources.",
                 {"type": "object", "properties": {"fault_id": {"type": "string"}}, "required": ["fault_id"]},
                 self.get_fault_knowledge),
            Tool("get_prognosis", "Remaining useful life band, time-to-limit predictions and mission reliability.",
                 _ENGINE, self.get_prognosis),
            Tool("get_work_orders", "Open and closed maintenance work orders for the engine.", _ENGINE,
                 self.get_work_orders),
            Tool("search_manuals", "Search the real manufacturer manuals and standards.", {"type": "object",
                 "properties": {"query": {"type": "string"}}, "required": ["query"]}, self.search_manuals),
        )}

    # -- tools ---------------------------------------------------------------------------------------------------
    def _state(self, engine_id: str) -> Dict[str, Any]:
        st = self.src.state(engine_id)
        if st is None:
            return {"available": False, "reason": f"no live state for {engine_id} yet (engine calibrating or unknown)"}
        return {k: v for k, v in st.items() if k not in HIDDEN_KEYS}

    def get_engine_state(self, engine_id: str) -> Dict[str, Any]:
        st = self._state(engine_id)
        if st.get("available") is False:
            return st
        readings = {k: {"value": r.get("value"), "unit": r.get("unit"), "quality": r.get("quality")}
                    for k, r in (st.get("readings") or {}).items()}
        return _round({"engine_id": engine_id, "status": st.get("status"), "engine_state": st.get("engine_state"),
                       "source": st.get("source"), "evidence_class": st.get("evidence_class"),
                       "sim_time_s": st.get("sim_time_s"), "readings": readings})

    def get_limits(self, engine_id: str, channel: Optional[str] = None) -> Dict[str, Any]:
        limits = self.src.config(engine_id).get("operating_limits") or {}
        if channel:
            base = channel.split("[")[0]
            limits = {k: v for k, v in limits.items() if k in (channel, base)}
        return {"engine_id": engine_id, "limits": limits}

    def get_hypotheses(self, engine_id: str) -> Dict[str, Any]:
        st = self._state(engine_id)
        if st.get("available") is False:
            return st
        out = []
        for h in st.get("hypotheses") or []:
            out.append(h)
        return _round({"engine_id": engine_id, "hypotheses": out, "detections": st.get("detections")})

    def get_fault_knowledge(self, fault_id: str) -> Dict[str, Any]:
        f = self.src.fault(fault_id)
        if f is None:
            return {"available": False, "reason": f"unknown fault id {fault_id!r}"}
        keep = ("id", "name", "kind", "physics_explanation", "mitigation_inflight", "maintenance_action",
                "maintenance_steps", "ata_chapter", "status_at_full_severity", "description_for_ui")
        return {k: f.get(k) for k in keep if f.get(k) is not None}

    def get_prognosis(self, engine_id: str) -> Dict[str, Any]:
        st = self._state(engine_id)
        if st.get("available") is False:
            return st
        prog = st.get("prognostics") or {}
        return _round({"engine_id": engine_id, "rul": prog.get("rul"), "time_to_limit": prog.get("time_to_limit"),
                       "reliability": st.get("reliability")})

    def get_work_orders(self, engine_id: str) -> Dict[str, Any]:
        return {"engine_id": engine_id, "work_orders": self.src.work_orders(engine_id)}

    def search_manuals(self, query: str) -> Dict[str, Any]:
        return {"available": False, "reason": "manual search index not built yet (card AI-03: real OEM manuals "
                "only, D34/D44); use get_limits, which carries the manual page for every limit"}

    # -- dispatch ------------------------------------------------------------------------------------------------
    def call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.tools.get(name)
        if tool is None:
            return {"error": f"unknown tool {name!r}"}
        try:
            return tool.fn(**{k: v for k, v in (args or {}).items() if k in tool.parameters["properties"]})
        except TypeError as exc:
            return {"error": f"bad arguments for {name}: {exc}"}

    def schemas(self) -> List[Dict[str, Any]]:
        return [t.schema() for t in self.tools.values()]


class ServicesSource:
    """StateSource over the live API services (the single simulation owner)."""

    def __init__(self, services: Any, registry: Any):
        self.services, self.registry = services, registry

    def state(self, engine_id: str) -> Optional[Dict[str, Any]]:
        msg = self.services.channel(engine_id).last_message
        return json.loads(msg) if msg else None

    def config(self, engine_id: str) -> Dict[str, Any]:
        from backend.physics.engine_config import load_engine_config
        return load_engine_config(engine_id).to_dict()          # same view as GET /api/v1/engines/{id}/config

    def fault(self, fault_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.registry.get(fault_id).raw
        except Exception:                                    # FaultRejected for an unknown id
            return None

    def work_orders(self, engine_id: str) -> List[Dict[str, Any]]:
        return self.services.work_orders.list(engine_id, None)
