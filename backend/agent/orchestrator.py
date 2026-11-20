"""Copilot orchestrator (Phase 8b, D45): answers "what is going on / why / what do I do" from the LIVE system.

Flow: tools (backend/agent/tools.py, read-only) -> the same 7-section answer every time:
  1 what is happening   2 why (physics + evidence)   3 immediate mitigation   4 fix / maintenance
  5 prognosis and mission impact   6 confidence and unknowns   7 sources
With no LLM (ANUMAAN_LLM_PROVIDER=none, the default) the sections are filled from the tool results by templates.
With Ollama or Gemini the model runs a tool loop (max MAX_TOOL_CALLS calls) and writes the sections; two guards keep
it honest: (a) number grounding - a sentence with a number that appears in no tool result is dropped; (b) section 1
must name the live status level, otherwise the template text is used. The LLM never decides status or diagnosis:
those come from the deterministic pipeline through the tools.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Protocol

from backend.agent.tools import CopilotTools

MAX_TOOL_CALLS = 8
SECTIONS = [("what", "What is happening"), ("why", "Why"), ("mitigation", "Immediate mitigation"),
            ("fix", "Fix / maintenance"), ("prognosis", "Prognosis and mission impact"),
            ("confidence", "Confidence and unknowns"), ("sources", "Sources")]
CONFIDENT = 0.7                     # hypothesis posterior treated as a diagnosis (configs/status.json uses 0.7 too)
NUMBER = re.compile(r"(?<![A-Za-z_])-?\d+(?:\.\d+)?")
SYSTEM_PROMPT = (
    "You are the ANUMAAN engine-health copilot for a UAV piston engine. Use the tools to read the live engine. "
    "Never invent a number: every number you write must come from a tool result. Never contradict the status level "
    "or the diagnosis the tools report. Reply with ONLY a JSON object with the keys what, why, mitigation, fix, "
    "prognosis, confidence (plain-English strings, 1-3 sentences each). The engine id is {engine_id}.")


class Provider(Protocol):
    name: str

    def step(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """One model turn -> {"content": str, "tool_calls": [{"name": str, "args": dict}]}."""


# -- deterministic answer --------------------------------------------------------------------------------------
def _fmt(v: Any, unit: str = "") -> str:
    if v is None:
        return "NO DATA"
    return f"{v:g} {unit}".strip() if isinstance(v, (int, float)) else str(v)


def template_answer(tools: CopilotTools, engine_id: str, results: Dict[str, Any]) -> Dict[str, str]:
    state = results.get("get_engine_state") or tools.call("get_engine_state", {"engine_id": engine_id})
    if state.get("available") is False:
        msg = state["reason"]
        return {k: msg if k == "what" else "" for k, _ in SECTIONS}
    hyps = [h for h in (results.get("get_hypotheses") or tools.call("get_hypotheses", {"engine_id": engine_id}))
            .get("hypotheses") or [] if h.get("fault_id")]          # NOMINAL has no fault id
    prog = results.get("get_prognosis") or tools.call("get_prognosis", {"engine_id": engine_id})
    orders = (results.get("get_work_orders") or tools.call("get_work_orders", {"engine_id": engine_id})).get("work_orders") or []
    status = state.get("status") or {}
    level = status.get("level") or "UNKNOWN"
    reasons = [r.get("text") for r in status.get("reasons") or [] if r.get("text")]
    top = hyps[0] if hyps else None
    know = tools.call("get_fault_knowledge", {"fault_id": top["fault_id"]}) if top else {}
    if top:
        results["get_fault_knowledge"] = know           # sources cite the diagnosed fault, not an earlier lookup
    readings = state.get("readings") or {}

    def reading(ch: str) -> Dict[str, Any]:            # residual names cht_1, reading names cht[1]
        return readings.get(ch) or readings.get(re.sub(r"_(\d+)$", r"[\1]", ch)) or {}
    ev = (top or {}).get("supporting") or []
    ev_txt = ", ".join(f"{e['channel']} {_fmt(reading(e['channel']).get('value'), reading(e['channel']).get('unit') or '')}"
                       f" (z {_fmt(e.get('z'))})" for e in ev[:3] if e.get("channel"))
    confident = bool(top and (top.get("posterior") or 0) >= CONFIDENT)
    name = (know.get("name") or (top or {}).get("fault_id") or "").replace("_", " ").lower()

    what = f"Status {level}." + (f" {' '.join(reasons[:2])}" if reasons else " All readings are inside their limits.")
    why = (f"{know.get('physics_explanation', '')} Evidence: {ev_txt}." if confident and ev_txt else
           f"{know.get('physics_explanation', '')}" if confident else
           "No fault is confidently diagnosed; the readings match the healthy-engine model.")
    mit = ((know.get("mitigation_inflight") or {}).get("text") if confident else None) or \
        ("No action needed." if level == "GO" else "Monitor the readings named above; follow the status reasons.")
    open_wo = [w for w in orders if w.get("status") != "SIGNED_OFF"]
    fix = (f"{(know.get('maintenance_action') or {}).get('text', '')} (ATA {know.get('ata_chapter')})." if confident
           else "No maintenance action from the diagnosis.")
    if open_wo:
        fix += " Open work order(s): " + "; ".join(f"{w.get('id')} {w.get('title')}" for w in open_wo[:3]) + "."
    rul = (prog or {}).get("rul") or {}
    ttl = (prog or {}).get("time_to_limit") or []
    rel = (prog or {}).get("reliability") or {}
    prognosis = (f"Remaining useful life {_fmt(rul.get('rul_h'))} h (95 % band {_fmt(rul.get('rul_lower_h'))}-"
                 f"{_fmt(rul.get('rul_upper_h'))} h)." if rul.get("rul_h") is not None else
                 f"Remaining useful life not available ({rul.get('reason') or rul.get('status') or 'no model'}).")
    if ttl:
        t = ttl[0]
        prognosis += f" {t.get('channel')} reaches its limit in about {_fmt(round((t.get('time_to_limit_s') or 0) / 60, 1))} min."
    if rel.get("mission_reliability") is not None:
        prognosis += f" Mission reliability {_fmt(rel.get('mission_reliability'))}."
    second = hyps[1] if len(hyps) > 1 else None
    conf = (f"{(top or {}).get('fault_id')} {name} at posterior {_fmt((top or {}).get('posterior'))}"
            + (f"; next {second.get('fault_id')} at {_fmt(second.get('posterior'))}" if second else "") + "."
            if top else "No hypothesis above the noise.")
    quarantined = [k for k, r in readings.items() if r.get("quality") not in (None, "OK")]
    if quarantined:
        conf += " Readings not fully trusted: " + ", ".join(quarantined[:4]) + "."
    conf += f" Evidence class {state.get('evidence_class') or 'SIMULATION'}."
    return {"what": what, "why": why.strip(), "mitigation": mit, "fix": fix, "prognosis": prognosis,
            "confidence": conf}


def sources_for(results: Dict[str, Any], tools: CopilotTools, engine_id: str) -> List[str]:
    out = [f"tool:{name}" for name in results]
    know = results.get("get_fault_knowledge") or {}
    for key in ("mitigation_inflight", "maintenance_action"):
        src = (know.get(key) or {}).get("source")
        if src:
            out.append(f"registry {know.get('id')} {key}: {src}")
    limits = tools.call("get_limits", {"engine_id": engine_id}).get("limits") or {}
    out += sorted({f"limit {ch}: {v.get('ref')}" for ch, v in limits.items() if isinstance(v, dict) and v.get("ref")})[:6]
    return out


# -- guards ----------------------------------------------------------------------------------------------------
def grounded_numbers(results: Dict[str, Any], question: str) -> List[float]:
    return [float(x) for x in NUMBER.findall(json.dumps(results) + " " + question)]


def ground(text: str, allowed: List[float]) -> tuple:
    """Drop every sentence holding a number that no tool result contains (within rounding). -> (text, dropped)."""
    def ok(n: float) -> bool:
        return any(abs(n - a) <= max(0.051, 0.01 * abs(a)) for a in allowed)
    kept, dropped = [], 0
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        if all(ok(float(n)) for n in NUMBER.findall(sentence)):
            kept.append(sentence)
        else:
            dropped += 1
    return " ".join(kept), dropped


# -- orchestration ---------------------------------------------------------------------------------------------
def answer(tools: CopilotTools, engine_id: str, question: str, provider: Optional[Provider] = None) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    calls: List[Dict[str, Any]] = []
    llm_text: Optional[Dict[str, str]] = None
    error = None
    if provider is not None:
        messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT.format(engine_id=engine_id)},
                                          {"role": "user", "content": question}]
        try:
            for _ in range(MAX_TOOL_CALLS + 1):
                out = provider.step(messages, tools.schemas())
                if not out.get("tool_calls"):
                    llm_text = _parse_sections(out.get("content") or "")
                    break
                messages.append({"role": "assistant", "content": out.get("content") or "", "tool_calls": out["tool_calls"],
                                 "raw": out.get("raw")})
                for call in out["tool_calls"]:
                    if len(calls) >= MAX_TOOL_CALLS:
                        break
                    res = tools.call(call["name"], call.get("args") or {})
                    results[call["name"]] = res
                    calls.append({"name": call["name"], "args": call.get("args") or {}})
                    messages.append({"role": "tool", "tool_name": call["name"], "content": json.dumps(res)})
        except Exception as exc:                                  # provider down: fall back, say so
            error = f"{type(exc).__name__}: {exc}"
            llm_text = None
    for name in ("get_engine_state", "get_hypotheses", "get_prognosis", "get_work_orders"):
        results.setdefault(name, tools.call(name, {"engine_id": engine_id}))
    base = template_answer(tools, engine_id, results)
    level = ((results["get_engine_state"].get("status") or {}).get("level")) or ""
    allowed = grounded_numbers(results, question)
    sections, dropped = {}, 0
    for key, _title in SECTIONS[:-1]:
        text = (llm_text or {}).get(key) or ""
        if text:
            text, d = ground(text, allowed)
            dropped += d
        if key == "what" and level and level not in text:
            text = ""                                             # must name the live status level
        sections[key] = text or base[key]
    sections["sources"] = "; ".join(sources_for(results, tools, engine_id))
    return {"engine_id": engine_id, "question": question,
            "mode": "llm" if llm_text else "deterministic",
            "provider": getattr(provider, "name", "none"), "provider_error": error,
            "sections": [{"key": k, "title": t, "text": sections[k]} for k, t in SECTIONS],
            "tool_calls": calls, "grounding": {"sentences_dropped": dropped}}


def _parse_sections(content: str) -> Optional[Dict[str, str]]:
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return {k: str(v) for k, v in data.items() if isinstance(v, (str, int, float))} if isinstance(data, dict) else None


# -- providers -------------------------------------------------------------------------------------------------
class OllamaProvider:
    """Ollama /api/chat tool calling (docs.ollama.com/capabilities/tool-calling, checked 20 Nov 2026): tools as
    JSON-schema functions; reply message.tool_calls[].function.{name, arguments (object)}; results go back as
    {"role": "tool", "tool_name", "content"}."""
    name = "ollama"

    def __init__(self, client: Any, model: str, num_ctx: int):
        self.client, self.model, self.num_ctx = client, model, num_ctx

    def step(self, messages, tools):
        msgs = [{k: v for k, v in m.items() if k in ("role", "content", "tool_name")} | (
            {"tool_calls": [{"function": {"name": c["name"], "arguments": c.get("args") or {}}} for c in m["tool_calls"]]}
            if m.get("tool_calls") else {}) for m in messages]
        resp = self.client.post("/api/chat", json={
            "model": self.model, "messages": msgs, "stream": False, "think": False,
            "tools": [{"type": "function", "function": t} for t in tools],
            "options": {"num_ctx": self.num_ctx, "temperature": 0.2}})
        resp.raise_for_status()
        msg = resp.json().get("message") or {}
        return {"content": msg.get("content") or "",
                "tool_calls": [{"name": c["function"]["name"], "args": c["function"].get("arguments") or {}}
                               for c in msg.get("tool_calls") or []]}


class GeminiProvider:
    """google-genai generate_content with function declarations (SDK 1.73.1: types.FunctionDeclaration
    parameters_json_schema, GenerateContentConfig(tools, automatic_function_calling disabled), response.function_calls,
    types.Part.from_function_response)."""
    name = "gemini"

    def __init__(self, client: Any, model: str):
        self.client, self.model = client, model

    def step(self, messages, tools):
        from google.genai import types
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = []
        for m in messages:
            if m["role"] == "user":
                contents.append(types.Content(role="user", parts=[types.Part(text=m["content"])]))
            elif m["role"] == "assistant" and m.get("raw") is not None:
                contents.append(m["raw"])
            elif m["role"] == "assistant":
                parts = [types.Part(function_call=types.FunctionCall(name=c["name"], args=c.get("args") or {}))
                         for c in m.get("tool_calls") or []] or [types.Part(text=m.get("content") or "")]
                contents.append(types.Content(role="model", parts=parts))
            elif m["role"] == "tool":
                contents.append(types.Content(role="user", parts=[types.Part.from_function_response(
                    name=m["tool_name"], response=json.loads(m["content"]))]))
        config = types.GenerateContentConfig(
            system_instruction=system, temperature=0.2,
            tools=[types.Tool(function_declarations=[types.FunctionDeclaration(
                name=t["name"], description=t["description"], parameters_json_schema=t["parameters"]) for t in tools])],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
        resp = self.client.models.generate_content(model=self.model, contents=contents, config=config)
        calls = [{"name": c.name, "args": dict(c.args or {})} for c in resp.function_calls or []]
        raw = resp.candidates[0].content if resp.candidates else None   # replayed as-is: it carries thought signatures
        return {"content": "" if calls else (resp.text or ""), "tool_calls": calls, "raw": raw}


def configured_provider() -> Optional[Provider]:
    """The provider chosen by ANUMAAN_LLM_PROVIDER (D31), warmed through LocalLLMEngine; None when off or down."""
    from backend.agent.llm_engine import QWEN_NUM_CTX, LocalLLMEngine
    engine = LocalLLMEngine.get_instance()
    if engine.provider == "none" or not engine.ensure_loaded():
        return None
    if engine.provider == "gemini":
        return GeminiProvider(engine._gemini_client, engine.model_id)       # client built by ensure_loaded()
    return OllamaProvider(engine._client, engine.model_id, QWEN_NUM_CTX)
