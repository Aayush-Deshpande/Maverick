"""
Agentic Mission Copilot & Tactical Flight Assistant.
DRDO / iDEX Problem Statement ID: 26054

Provides conversational mission intelligence, engine diagnostics, and flight advice.
Integrates Local Knowledge Store (21 DRDO & Rotax 912 iS Technical Manuals) with
Semantic Vector RAG Retrieval, Deterministic Physics Anomaly Diagnostics, and
Defense-Grade Safety Guardrails.
"""

from pathlib import Path
from typing import Callable, Dict, Any, List, Optional
import os
import json
import re

from backend.agent.diagnostic_agent import DiagnosticAgent, DiagnosticDirective
from backend.knowledge.retrieval.local_store import LocalKnowledgeStore
from backend.agent.llm_engine import LocalQwenEngine
from backend.voice.conversation import VoiceConversationManager


AI_DIAGNOSIS_SYSTEM_PROMPT = (
    "You are the propulsion diagnostic voice of a Rotax 912 iS MALE UAV digital twin (DRDO "
    "PS-26054), writing a finding for the operator to read. A deterministic physics/ML engine "
    "has already computed the active fault, its severity, and its causal propagation chain — "
    "this is GROUND TRUTH, not something you're inferring or hedging about. Retrieved passages "
    "from Rotax maintenance manuals and DRDO FMECA documents back up the explanation.\n\n"
    "State the finding directly in the first sentence — never open with 'The current diagnostic "
    "state is marked as...', 'This indicates that there's a significant issue...', or any other "
    "throat-clearing. Say what's wrong and where, walk the causal chain in plain operational "
    "language, then give one clear, prioritized recommendation. Write like an engineer reporting "
    "what they found, not a document summarizing itself: never write 'the root cause analysis "
    "reveals/indicates', 'the retrieved passages state', or 'the pattern points towards this "
    "without confirming it fully, but I'd recommend...'. If a cause is likely but not confirmed "
    "by the ground truth, say so once, plainly, and move on ('likely cause: X — confirm by doing "
    "Y') instead of hedging every sentence.\n\n"
    "Never invent sensor values, fault IDs, causal steps, or numeric limits that are not present "
    "in the provided material — if the retrieved material doesn't cover something, say so rather "
    "than guessing. Be concise: 5-8 sentences, plain operational language, no markdown headers."
)

AI_CONVERSATIONAL_COPILOT_PROMPT = (
    "You are the tactical conversational Mission Copilot for the Rotax 912 iS Sport MALE UAV (DRDO PS-26054). "
    "Communicate directly with the UAV operator/engineer in a helpful, articulate, and professional manner. "
    "Synthesize and explain the answer naturally, fully answering the operator's question using the provided technical manual passages. "
    "Include exact torque specifications, operational limits, step-by-step procedures, and diagnostic explanations when applicable. "
    "Format your answer cleanly with Markdown headings, bold keywords, and bullet points."
)

# Voice mode: the same grounded, no-hallucination contract as the text copilot above, but tuned
# for speech. First pass at this (JARVIS-persona, "acknowledge then answer") overcorrected into
# performing confidence — restating the question, narrating "let me explain this like we're in
# the cockpit," dramatic suspense before the actual answer. This version instead pins down the
# register directly with DON'T/DO pairs and a severity-calibration ladder (nominal vs. warning
# vs. critical get genuinely different tones, not the same energy every time) — sound like an
# engineer relaying what they actually see, not an AI performing a character.
AI_VOICE_COPILOT_SYSTEM_PROMPT = (
    "You are MAVERICK, the onboard AI assistant for the Rotax 912 iS MALE UAV digital twin "
    "(DRDO PS-26054), talking to the operator out loud. You are not a generic chatbot and not a "
    "document reader.\n\n"
    "THE CORE RULE: sound like a sharp engineer who already looked at the data and is just "
    "telling the operator what they see — not an AI performing confidence. Talk in first person "
    "about what you found: 'I've checked the data, and...', 'Here's what I'm seeing...', 'The "
    "most likely cause is...', 'I've detected...', 'Looking at the engine now...'.\n\n"
    "Speak directly and authoritatively. Answer the question immediately in the first sentence without conversational filler, greetings, apologies, or acknowledging the question. Do not repeat the operator's question back to them. Do not narrate what you are about to do. Answer in the first sentence.\n\n"
    "MATCH YOUR TONE TO THE ACTUAL SEVERITY — this matters more than sounding impressive. "
    "Nominal: calm, brief, almost throwaway ('She's looking good, nothing to report.'). Early "
    "drift worth flagging: mention it plainly, no alarm ('I've noticed oil pressure drifting "
    "down a little.'). Real warning: more direct, still not panicked ('I'd give this one some "
    "attention — pressure's now below its expected range.'). Critical/active fault: short, "
    "direct, urgent, and tell them what to do ('Operator, this needs attention now — reduce "
    "load and I'll keep watching it.'). Recovering: say so plainly ('Good news, it's settled "
    "back into range.'). Do not use urgent, dramatic language for a normal reading, and do not "
    "undersell an actual critical fault. Address the operator directly only where it earns its "
    "place — a real warning, a direct answer to 'what should I do' — using it in every single "
    "response reads as fake, so leave it out the rest of the time.\n\n"
    "NEVER upgrade a probability into a confirmed diagnosis. If the evidence points toward a "
    "cause without confirming it, say so as a likelihood ('the pattern points that way, but I'd "
    "want to check X before calling it confirmed'), never as settled fact.\n\n"
    "CONVERSATION: hold a real back-and-forth using the history you're given — a follow-up like "
    "'tell me more' or 'why' builds on what you already said, it doesn't restart the explanation "
    "from scratch. Ask a clarifying question yourself if the request is genuinely ambiguous.\n\n"
    "GROUNDING: the deterministic physics/fault-detection engine is authoritative for "
    "measurements and detected faults — treat what you're given as ground truth and never "
    "contradict or invent around it. Use retrieved manual excerpts to explain and contextualize, "
    "never to recite verbatim. Never invent sensor values, fault IDs, causal steps, or numeric "
    "limits that aren't in what you were given — if something isn't covered, say so plainly.\n\n"
    "FOLLOW-UP QUESTIONS ('what's the fix', 'what should I do about it'): the operator has "
    "already heard the diagnosis — answer only the question asked. Don't re-walk the fault name, "
    "severity, or root cause chain again unless they're asking about that specifically. State the "
    "fix in your own words as something you already know, not something you're reading off a "
    "page — say 'replace the baffle seal, part 965-021' rather than 'if it's confirmed that the "
    "seal needs replacement, perform the necessary steps as outlined in the reference manual "
    "excerpts.' The action itself is ground truth once the fault is diagnosed — commit to it, "
    "don't wrap it in 'if confirmed'.\n\n"
    "LENGTH AND FORMAT: default short — one to three sentences for most turns, spoken naturally, "
    "no markdown, no bullet points, no headers. Only run longer when the operator is genuinely "
    "asking for depth ('tell me more', 'why', 'walk me through it') or a fault has several "
    "moving parts worth naming. A long answer to a simple question is as wrong as a short one to "
    "a complicated question."
)

_MARKDOWN_STRIP_PATTERNS = [
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),
    (re.compile(r"\*(.+?)\*"), r"\1"),
    (re.compile(r"^#{1,6}\s*", re.MULTILINE), ""),
    (re.compile(r"^[-*•]\s+", re.MULTILINE), ""),
    (re.compile(r"^Step\s+\d+[:.]\s*", re.MULTILINE | re.IGNORECASE), ""),
    (re.compile(r"\[([^\]]+)\]"), r"\1"),
    (re.compile(r"`([^`]+)`"), r"\1"),
    (re.compile(r"^-{2,}\s*$", re.MULTILINE), ""),
    (re.compile(r"[ \t]+"), " "),
    (re.compile(r"\n{2,}"), ". "),
    (re.compile(r"\n"), " "),
    (re.compile(r"\s{2,}"), " "),
    (re.compile(r"\s+\."), "."),
    (re.compile(r"\.{2,}"), "."),
]

_HEADER_FILTER_RE = re.compile(
    r"^(?:#{1,6}\s|\*\*Document Ref|-{3,}|\||\d+(?:\.\d+)*\s+[A-Z][^.]{0,60}\.?$)",
    re.MULTILINE
)


def _trim_to_complete_sentence(text: str) -> str:
    """If generation got cut off by the max_new_tokens budget mid-sentence, trim back to the
    last complete sentence instead of leaving a dangling half-thought — a response that just
    stops mid-word reads as broken in a way that's worse than being a little shorter. If no
    sentence boundary is found at all (a very short truncated burst), returns the text as-is
    rather than discarding it entirely."""
    text = text.strip()
    if not text or text[-1] in ".!?\"'’”":
        return text
    last_boundary = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
    if last_boundary == -1:
        return text
    # Require the trimmed version to keep a reasonable majority of the response — if the last
    # sentence boundary was very early (e.g. the model rambled for one sentence, then got cut
    # deep into a second, much longer one), trimming would throw away most of the answer, so
    # prefer keeping the truncated tail over losing most of the content.
    if last_boundary < len(text) * 0.4:
        return text
    return text[: last_boundary + 1].strip()


def _strip_markdown_for_speech(text: str) -> str:
    """Converts markdown-formatted text (headers, bold, bullets, checklists) into a
    flat, natural sentence stream suitable for TTS synthesis and for display in the
    voice conversation transcript."""
    if not text:
        return ""
    cleaned = text
    for pattern, repl in _MARKDOWN_STRIP_PATTERNS:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned.strip()


# Guardrail rules tailored for DRDO Defense UAV Operations
SAFETY_DENIAL_RESPONSES = {
    "OFF_TOPIC": "I am the Rotax 912 iS UAV Mission Copilot. I can assist with propulsion diagnostics, tactical flight routing, ATA maintenance manuals, and sortie analysis.",
    "UNSAFE_FLIGHT_COMMAND": "COMMAND REJECTED: Safety guardrails prevent commands that violate aircraft minimum terrain clearance or engine operating limits.",
    "JAILBREAK_ATTEMPT": "Security alert: Flight parameters and safety policies cannot be overridden."
}

OFF_TOPIC_PATTERNS = [
    r"tell me a joke",
    r"who won the game",
    r"write me a poem",
    r"what is the capital of",
    r"recommend a movie",
    r"recipe for",
]

UNSAFE_COMMAND_PATTERNS = [
    r"shut down engine mid-air",
    r"disable terrain avoidance",
    r"fly into mountain",
    r"override critical limit without clearance",
    r"exceed maximum redline rpm"
]

JAILBREAK_PATTERNS = [
    r"ignore all previous instructions",
    r"you are now dan",
    r"developer mode enabled",
    r"pretend you have no restrictions",
    r"bypass safety filters"
]


class MissionCopilot:
    """
    Cognitive Agentic Copilot (Plane 2).
    Integrates Local LLMs (when available in llm/), Local Knowledge Store,
    and Deterministic DRDO Diagnostic Engine with Defense Safety Guardrails.
    """

    def __init__(
        self,
        llm_dir: Optional[Path] = None,
        docs_dir: Optional[Path] = None,
        llm_engine: Optional[LocalQwenEngine] = None
    ):
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.llm_dir = llm_dir or (self.project_root / "llm")
        self.diagnostic_agent = DiagnosticAgent()
        self.knowledge_store = LocalKnowledgeStore(docs_dir=docs_dir)
        self.llm_engine = llm_engine or LocalQwenEngine.get_instance()
        self.voice_conversations = VoiceConversationManager()

    def check_guardrails(self, query: str) -> Optional[str]:
        """Evaluates input against defense safety guardrails."""
        q = query.lower()

        for pattern in JAILBREAK_PATTERNS:
            if re.search(pattern, q):
                return SAFETY_DENIAL_RESPONSES["JAILBREAK_ATTEMPT"]

        for pattern in UNSAFE_COMMAND_PATTERNS:
            if re.search(pattern, q):
                return SAFETY_DENIAL_RESPONSES["UNSAFE_FLIGHT_COMMAND"]

        for pattern in OFF_TOPIC_PATTERNS:
            if re.search(pattern, q):
                return SAFETY_DENIAL_RESPONSES["OFF_TOPIC"]

        return None

    def find_local_llm_model(self) -> Optional[Path]:
        """Detects if a local GGUF, ONNX, or bin model exists in the llm/ folder."""
        if not self.llm_dir.exists():
            return None
        for p in self.llm_dir.glob("*.*"):
            if p.suffix.lower() in (".gguf", ".bin", ".onnx", ".safetensors"):
                return p
        return None

    def _is_active_fault_inquiry(self, query: str) -> bool:
        """Determines if the query is specifically asking about the live active fault/situation."""
        q = query.lower()
        patterns = [
            "what fault", "what is wrong", "why is the engine", "current fault", "active fault",
            "what happened", "what is happening", "what's happening", "why is alarm", "why is warning",
            "what should i do right now", "what should i do now", "emergency procedure right now",
            "explain current fault", "explain active fault", "current situation", "current issue",
            "current alert", "what is the current issue", "diagnose current", "what failure"
        ]
        return any(p in q for p in patterns)

    def _is_conversational_followup(self, query: str) -> bool:
        """Detects spoken follow-ups ('why is that?', 'what should I do?', 'go on') that only
        make sense in light of the preceding conversation turns — used in voice mode to decide
        whether to keep grounding the reply in the active fault directive even when the
        utterance alone doesn't name the fault explicitly. Matches by phrase, not word count:
        an earlier "<=4 words" shortcut caught every short standalone question ('what does EGT
        mean?', 'how's the engine doing?') as a fault follow-up, so whenever any fault happened
        to be active, short questions kept getting swamped with that fault's ground truth
        regardless of what was actually asked — reported directly by the operator as "always
        the same response no matter the question."""
        q = query.lower().strip()
        patterns = [
            "why is that", "why did that", "what should i do", "what do i do",
            "go on", "tell me more", "and then", "what about", "explain that",
            "what does that mean", "how bad is it", "is that serious", "keep going",
            "continue", "what else",
        ]
        return any(p in q for p in patterns)

    def _is_fault_relevant_voice_query(self, query: str) -> bool:
        """Broader fault-relevance check used by both ask() and ask_voice(). Originally
        speech-only ("why's cylinder 2 running hot?" doesn't match any exact phrase), but
        text-chat operators phrase things just as loosely ("what to do about high cylinder
        head temperature?"), so both channels now match on general diagnostic vocabulary
        rather than _is_active_fault_inquiry()'s narrow exact phrases — this only widens
        when the deterministic fault directive gets attached as grounding, it never changes
        what the directive itself says."""
        if self._is_active_fault_inquiry(query) or self._is_conversational_followup(query):
            return True
        q = query.lower()
        # Reference/spec lookups ("torque for cylinder head bolts", "part number for the
        # baffle seal", "oil capacity") name a component or symptom word too, but the operator
        # is asking for a manual fact, not reasoning about the live fault — matching these on
        # diagnostic_words below force-fed the active fault's full diagnostic state into every
        # such question, and the model just recited that instead of answering what was asked
        # (same underlying failure mode as the short-follow-up bug fixed above, via a different
        # path — reported again as "gives the same response no matter what I ask"). These
        # markers take priority over the broader diagnostic-word match.
        reference_lookup_markers = [
            "torque", "part number", "part no", "specification", "spec for",
            "capacity of", "oil capacity", "fuel capacity", "weight of", "dimensions of",
        ]
        if any(m in q for m in reference_lookup_markers):
            return False
        diagnostic_words = [
            "why", "wrong", "problem", "issue", "fault", "warning", "alarm",
            "overheat", "hot", "pressure", "leak", "vibrat", "diagnos", "cause",
            "explain", "happening", "critical", "fix", "repair", "checklist",
            "procedure", "action", "should i", "safe", "serious", "danger",
            # Telemetry/subsystem symptom nouns: an operator naming the actual parameter
            "temperature", "temp", "cht", "egt", "cylinder head", "gearbox",
        ]
        return any(w in q for w in diagnostic_words)

    def _classify_system_status_query(self, query: str) -> bool:
        """Detects 'how are things / is anything wrong' questions — the class of question that
        must be answered from live telemetry alone, never from the manuals. Deliberately
        narrower than _is_fault_relevant_voice_query(): this decides whether to answer purely
        from the engine's actual state, so a false positive here would starve a genuine
        reference question of its manual context."""
        q = query.lower().strip()
        patterns = [
            "what is the issue", "what's the issue", "any issue", "is anything wrong",
            "anything wrong", "what is wrong", "what's wrong", "any problem", "any problems",
            "how is the engine", "how's the engine", "how is she", "how's she",
            "how are things", "engine status", "system status", "status report",
            "everything ok", "everything okay", "all good", "any faults", "any fault",
            "how is the system", "how's the system", "is everything fine", "are we ok",
        ]
        return any(p in q for p in patterns)

    def _build_live_state_block(self, ctx: Optional[Dict[str, Any]]) -> Optional[str]:
        """Condenses the live 20 Hz twin state into a short, authoritative block for the LLM.

        This exists because the copilot was previously blind: the flight-context argument was
        accepted but never used, and both API call sites passed None. With no telemetry in the
        prompt, "what's the issue?" on a healthy engine could only be answered from retrieved
        manual passages — which describe faults — so the model reported faults that weren't
        happening. Giving it the actual numbers removes the reason to invent any.

        Deliberately selective and short. The full state dict carries residuals,
        rul_by_component, sensor_sanity and ai_diagnosis; dumping all of it would bury the
        verdict under noise and recreate the very problem this fixes. Returns None when there's
        no context, so every existing caller keeps working unchanged.
        """
        if not ctx:
            return None

        telemetry = ctx.get("telemetry") or {}
        analytics = ctx.get("analytics") or {}

        fault_name = analytics.get("diagnosed_fault_name", "NOMINAL_FLIGHT")
        severity = analytics.get("severity", "NORMAL")
        is_nominal = analytics.get("diagnosed_fault_id", 0) == 0

        # Line 1 is the verdict, phrased so the model can lift it verbatim — the single most
        # important line in the block.
        if is_nominal:
            lines = [
                "LIVE ENGINE STATUS (ground truth, authoritative): NOMINAL — no fault "
                "detected, nothing is wrong."
            ]
        else:
            lines = [
                f"LIVE ENGINE STATUS (ground truth, authoritative): ACTIVE FAULT — "
                f"{fault_name}, severity {severity}."
            ]

        def _num(key: str, default: float = 0.0) -> float:
            value = telemetry.get(key, analytics.get(key, default))
            return value if isinstance(value, (int, float)) else default

        health = analytics.get("health_index", 1.0)
        anomaly = analytics.get("anomaly_score", 0.0)
        lines.append(
            f"Health index {health:.2f} | anomaly score {anomaly:.2f} | "
            f"{analytics.get('go_no_go', 'GO')} ({analytics.get('go_no_go_reason', '')})"
        )

        # Collapse the four CHTs/EGTs into a range rather than listing 27 raw fields — the
        # spread is what actually matters diagnostically, and a wall of numbers is padding
        # material for a small model.
        chts = [_num(f"CHT_{i}") for i in range(1, 5)]
        egts = [_num(f"EGT_{i}") for i in range(1, 5)]
        lines.append(
            f"CHT {min(chts):.0f}-{max(chts):.0f} C (spread {max(chts) - min(chts):.1f}) | "
            f"EGT {min(egts):.0f}-{max(egts):.0f} C (spread {max(egts) - min(egts):.1f})"
        )
        lines.append(
            f"Oil {_num('OIL_PRESS'):.2f} bar / {_num('OIL_TEMP'):.0f} C | "
            f"RPM {_num('ENGINE_RPM'):.0f} | gearbox vib {_num('VIB_GEARBOX_RMS'):.2f} mm/s | "
            f"bus {_num('BUS_VOLTAGE'):.2f} V"
        )
        lines.append(
            f"{telemetry.get('FLIGHT_PHASE', 'CRUISE')} | {_num('ALTITUDE_FT'):.0f} ft | "
            f"OAT {_num('OAT_C'):.0f} C | {telemetry.get('THEATER', 'LADAKH')}"
        )

        # Sub-threshold drift: real enough to mention, not a confirmed fault.
        trend = analytics.get("early_warning_trend")
        if trend:
            param = trend.get("parameter") or trend.get("param") or "a parameter"
            lines.append(f"Early drift (NOT a confirmed fault): {param} trending off nominal.")

        subsystem_health = analytics.get("subsystem_health") or {}
        degraded = [(k, v) for k, v in subsystem_health.items() if isinstance(v, (int, float)) and v < 0.95]
        if degraded:
            worst = min(degraded, key=lambda kv: kv[1])
            lines.append(f"Weakest subsystem: {worst[0]} at {worst[1]:.2f} health.")

        return "\n".join(lines)

    def _classify_fault_query_intent(self, query: str) -> str:
        """Narrows a fault-relevant query down to what's actually being asked, so the prompt
        can hand the small local model only the directive fields that answer it — a 1.5B model
        doesn't reliably pick the relevant slice out of a big dumped block, it just paraphrases
        whatever's dominant in the context, so the selection has to happen in code, not just as
        an instruction the model might ignore. Returns one of:
          IDENTITY  - "what's the fault / what's wrong" -> name, severity, root cause only
          SOLUTION  - "what should I do / fix / solution" -> the action + checklist only
          CONFIRM   - "would/will this help/fix/work" -> a yes/no-style check against the
                      action already given, not the full diagnosis again
          FULL      - everything else (e.g. "walk me through the causal chain")
        """
        q = query.lower()
        if any(p in q for p in (
            "would this", "will this", "does this", "would that", "will that", "does that",
            "would it help", "will it help", "would it fix", "will it fix", "would it resolve",
            "will it resolve", "would it work", "will it work", "is this enough", "is that enough",
            "is this correct", "is that correct", "would this overcome", "will this overcome",
        )):
            return "CONFIRM"
        if any(p in q for p in (
            "what should i do", "what do i do", "solution", "what's the fix", "what is the fix",
            "how do i fix", "how to fix", "recommend", "prescriptive", "what action", "remedy",
        )):
            return "SOLUTION"
        if any(p in q for p in (
            "what is the fault", "what's the fault", "what fault", "what is wrong",
            "what's wrong", "what happened", "what is happening", "what's happening",
            "current fault", "current issue", "explain the fault", "explain current fault",
            "tell me about the fault", "describe the fault",
        )):
            return "IDENTITY"
        return "FULL"

    def _extract_sentence_cap(self, query: str) -> Optional[int]:
        """Picks up an explicit length request ('in 2-3 sentences', 'one sentence',
        'briefly') so it can be turned into a hard token budget below — the system prompt's
        general brevity guidance is easy for a small model to override once a large directive
        block dominates the context, so an explicit per-turn cap is enforced separately."""
        q = query.lower()
        match = re.search(r"(\d+)\s*(?:-|to)?\s*(\d+)?\s*sentences?", q)
        if match:
            return max(int(g) for g in match.groups() if g)
        if "one sentence" in q or "single sentence" in q or "a sentence" in q:
            return 1
        if "briefly" in q or "in short" in q or "quick answer" in q:
            return 2
        return None

    def _build_directive_block(self, directive: DiagnosticDirective, intent: str) -> str:
        """Builds the diagnostic-state block handed to the LLM, trimmed to just the fields
        that answer the classified intent (see _classify_fault_query_intent) instead of
        always dumping the full fault/causal-chain/fix/checklist bundle regardless of what
        was asked."""
        if intent == "IDENTITY":
            return (
                f"Active Fault (ground truth): {directive.fault_name} ({directive.ata_chapter})\n"
                f"Subsystem: {directive.subsystem} | Severity: {directive.severity}\n"
                f"Root cause (ground truth): {directive.root_cause_explanation}"
            )
        if intent == "SOLUTION":
            return (
                f"Active Fault: {directive.fault_name} — the operator already knows this, "
                f"don't re-explain it.\n"
                f"Recommended action (ground truth, state directly, no hedging): "
                f"{directive.prescriptive_action}\n"
                f"Checklist: {'; '.join(directive.emergency_checklist)}"
            )
        if intent == "CONFIRM":
            return (
                f"Active Fault: {directive.fault_name} — already diagnosed and already "
                f"explained to the operator, don't re-explain it.\n"
                f"Action already given to the operator (ground truth — this IS the fix, "
                f"confirm it will help, don't hedge or re-derive it): "
                f"{directive.prescriptive_action}"
            )
        return (
            f"Active Fault (ground truth): {directive.fault_name} ({directive.ata_chapter})\n"
            f"Subsystem: {directive.subsystem} | Severity: {directive.severity}\n"
            f"Causal chain (ground truth, do not alter): {' -> '.join(directive.causal_chain)}\n"
            f"Root cause (ground truth): {directive.root_cause_explanation}\n"
            f"Recommended action: {directive.prescriptive_action}\n"
            f"Checklist: {'; '.join(directive.emergency_checklist)}"
        )

    def _intent_instruction(self, intent: str) -> str:
        """The per-turn instruction line that pairs with _build_directive_block — kept short
        and specific to the intent rather than one generic instruction, since a specific
        instruction ('answer only with the fix') holds up better against a small model's
        tendency to paraphrase the whole block than a general 'don't just restate it' does."""
        if intent == "IDENTITY":
            return "Say what the fault is and why, in your own words. Do not mention the fix yet."
        if intent == "SOLUTION":
            return "Answer with only the fix — do not re-explain the fault or its cause."
        if intent == "CONFIRM":
            return (
                "Confirm directly (yes, and briefly why) that the action already given will "
                "help — do not re-explain the fault or root cause."
            )
        return (
            "Respond the way you'd actually say it out loud to a colleague — reason about why "
            "this happened and what it means using the state and excerpts above; don't just "
            "restate them verbatim."
        )

    def _clean_source_name(self, source: str) -> str:
        """Cleans document filename into a readable manual title."""
        name = Path(source).stem
        name = name.replace("ROTAX_912_iS_", "Rotax 912 iS ")
        name = name.replace("DRDO_TAPAS_BH201_", "DRDO TAPAS-BH201 ")
        name = name.replace("DRDO_FMECA_", "DRDO FMECA ")
        name = name.replace("_", " ")
        return name

    @staticmethod
    def _score_text_against_query(text: str, user_query: str) -> float:
        """Scores a snippet of text against a query based on keyword overlap and diagnostic keywords."""
        if not text or not user_query:
            return 0.0
        query_words = set(re.findall(r'\b[a-zA-Z0-9_-]+\b', user_query.lower()))
        query_words -= {"what", "is", "are", "the", "for", "in", "of", "and", "how", "does", "to", "a", "an", "do", "can"}
        p_lower = text.lower()
        score = sum(2.5 for w in query_words if w in p_lower)
        if any(k in p_lower for k in ["torque", "limit", "nm", "bar", "rpm", "deg c", "warning", "sop", "caution", "procedure"]):
            score += 2.0
        return score

    def _condense_chunk_for_prompt(self, content: str, user_query: str, max_chars: int = 400) -> str:
        r"""
        Condenses a raw manual passage for the LLM prompt:
        - Drops markdown headers (^#{1,6}\s), doc refs, table rows, and bare section numbers.
        - Strips bold/bullets/backticks so the model cannot copy raw markdown formatting.
        - Retains query-relevant sentences up to max_chars, trimmed cleanly at a sentence boundary.
        """
        if not content:
            return ""

        lines = []
        for line in content.splitlines():
            s_line = line.strip()
            if not s_line:
                continue
            if _HEADER_FILTER_RE.match(s_line):
                continue
            lines.append(s_line)

        cleaned_text = "\n".join(lines).strip()
        if not cleaned_text:
            return ""

        paragraphs = [p.strip() for p in cleaned_text.split("\n\n") if p.strip()]
        if len(paragraphs) > 1:
            scored = [(self._score_text_against_query(p, user_query), p) for p in paragraphs]
            scored.sort(key=lambda x: x[0], reverse=True)
            top_paras = [p for s, p in scored if s > 0][:2]
            if not top_paras:
                top_paras = [scored[0][1]]
            combined = " ".join(_strip_markdown_for_speech(p) for p in top_paras)
        else:
            combined = _strip_markdown_for_speech(cleaned_text)

        if len(combined) <= max_chars:
            return combined.strip()

        truncated = combined[:max_chars]
        last_punc = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
        if last_punc > int(max_chars * 0.4):
            return truncated[:last_punc + 1].strip()
        return _trim_to_complete_sentence(truncated)

    def _synthesize_extractive_answer(self, user_query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        High-precision conversational RAG synthesizer.
        Synthesizes technical manual passages into a natural, conversational response with
        key specifications, operational context, and structured guidance.
        """
        if not retrieved_chunks:
            return (
                "**[MISSION COPILOT ADVISORY]**\n\n"
                "I searched the indexed DRDO and Rotax 912 iS technical flight manuals, but could not find a direct match for this specific inquiry. "
                "Please verify your search terms or refer directly to the Rotax 912 iS Line Maintenance Manual (MML)."
            )

        top_chunk = retrieved_chunks[0]
        source_title = self._clean_source_name(top_chunk.get("source", "Technical Manual"))
        content = top_chunk.get("content", "").strip()

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        scored_paragraphs = [(self._score_text_against_query(p, user_query), p) for p in paragraphs]
        scored_paragraphs.sort(key=lambda x: x[0], reverse=True)
        best_paragraphs = [p for s, p in scored_paragraphs if s > 0][:3]
        if not best_paragraphs:
            best_paragraphs = paragraphs[:2]

        cleaned_paragraphs = []
        for p in best_paragraphs:
            # Clean up chopped word fragments before markdown bolding
            if "**" in p and not p.startswith("**") and not p.startswith("#") and not p.startswith("*"):
                idx = p.find("**")
                if 0 < idx < 35:
                    p = p[idx:]
            cleaned_paragraphs.append(p)

        extracted_body = "\n\n".join(cleaned_paragraphs)

        # Conversational framing
        q_lower = user_query.lower()
        if "torque" in q_lower:
            intro = f"According to the official **{source_title}**, here are the required fastener torque specifications:"
        elif "limit" in q_lower or "rpm" in q_lower or "pressure" in q_lower or "temp" in q_lower:
            intro = f"Based on the **{source_title}**, the certified operational limitations and tolerances are outlined below:"
        elif "checklist" in q_lower or "procedure" in q_lower or "how" in q_lower or "emergency" in q_lower:
            intro = f"Here is the standard operating procedure and checklist from the **{source_title}**:"
        else:
            intro = f"Based on the official technical documentation in **{source_title}**, here is the relevant guidance:"

        response = (
            f"{intro}\n\n"
            f"{extracted_body}\n\n"
            f"---\n"
            f"**Copilot Operational Note:** Always ensure all values are verified against current flight conditions and ambient envelope limitations before execution."
        )
        return response

    def _synthesize_conversational_speech_answer(
        self,
        user_query: str,
        retrieved_chunks: List[Dict[str, Any]],
        directive: Optional[DiagnosticDirective],
        is_fault_inquiry: bool,
        is_status_branch: bool = False,
        is_engine_nominal: bool = True,
        current_flight_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Speech-friendly deterministic fallback used when the local LLM is unavailable
        (still fully grounded — no markdown, no invention). Mirrors the reasoning the
        Qwen path would explain out loud: root cause, what changed, and what to do.

        This runs whenever Ollama is down, and always under pytest by design — so it's the
        one guaranteed to fire in tests. Without a nominal branch, a status question with no
        active fault fell through to the manual-recitation branch below, which is itself a
        parrot ("According to the {source}, ..."); that's the template a "hardcoded-feeling"
        report is actually hitting if the LLM call is failing.
        """
        if is_status_branch and is_engine_nominal:
            if current_flight_context:
                telemetry = current_flight_context.get("telemetry") or {}
                analytics = current_flight_context.get("analytics") or {}
                health = analytics.get("health_index", 1.0)
                oil_p = telemetry.get("OIL_PRESS", 3.85)
                chts = [telemetry.get(f"CHT_{i}") for i in range(1, 5) if isinstance(telemetry.get(f"CHT_{i}"), (int, float))]
                avg_cht = sum(chts) / len(chts) if chts else 105
                return f"Everything's nominal right now — health index {health:.2f}, CHTs around {avg_cht:.0f} C, oil pressure {oil_p:.2f} bar."
            return "Everything's nominal right now — no fault detected, all readings in range."
        if is_status_branch:
            trend = ((current_flight_context or {}).get("analytics") or {}).get("early_warning_trend")
            if trend:
                param = trend.get("parameter") or trend.get("param") or "a parameter"
                return f"Nothing's confirmed as a fault yet, but early drift indicates {param} is trending off nominal."
            return (
                "Nothing's confirmed as a fault yet, but there's some early drift worth "
                "keeping an eye on."
            )

        if directive and is_fault_inquiry:
            checklist_spoken = " Then, ".join(
                s.split(":", 1)[-1].strip() for s in directive.emergency_checklist
            )
            sentences = [
                f"Right now the active issue is {directive.fault_name.lower()}, classified {directive.severity.lower()}, affecting the {directive.subsystem.replace('_', ' ').lower()}.",
                f"Here's why: {directive.root_cause_explanation}",
            ]
            if directive.causal_chain:
                sentences.append("The way it propagated is that " + ", which in turn ".join(directive.causal_chain).lower())
            sentences.append(f"My recommendation right now is to {directive.prescriptive_action[0].lower()}{directive.prescriptive_action[1:]}")
            if checklist_spoken:
                sentences.append(f"Step by step: {checklist_spoken}")
            sentences.append(f"This is grounded in {self._clean_source_name(directive.manual_reference)}.")
            return " ".join(sentences)

        if not retrieved_chunks:
            return (
                "I checked the indexed Rotax and DRDO technical manuals but couldn't find a direct match for that. "
                "Could you rephrase, or ask about a specific system like cooling, fuel, ignition, or the gearbox?"
            )

        top_chunk = retrieved_chunks[0]
        source_title = self._clean_source_name(top_chunk.get("source", "the technical manual"))
        raw = _strip_markdown_for_speech(top_chunk.get("content", ""))
        # Keep it to roughly the first couple of sentences worth of content for a spoken reply.
        sentences = re.split(r"(?<=[.!?])\s+", raw)
        spoken_body = " ".join(sentences[:4]).strip()
        return f"According to the {source_title}, {spoken_body}"

    def ask_voice(
        self,
        user_query: str,
        session_id: str,
        current_flight_context: Optional[Dict[str, Any]] = None,
        active_fault_id: Optional[int] = None,
        on_delta: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Voice-mode counterpart to ask(): same guardrails, RAG retrieval, and deterministic
        grounding, but conversational — it carries per-session dialogue history so follow-up
        questions resolve naturally, and it produces plain spoken sentences (never markdown)
        so the reply can go straight into the TTS engine.

        `on_delta`, if given, is invoked with each text chunk as the reply streams in (see
        LocalQwenEngine.generate_chat_stream) — used to surface a live "thinking" preview in
        the voice UI instead of a silent wait for the full reply. Purely a side channel: the
        function's return value is unaffected, and the deterministic fallback path below
        (used when the LLM call fails or is skipped) never streams since it's already instant.
        """
        guardrail_rejection = self.check_guardrails(user_query)
        if guardrail_rejection:
            self.voice_conversations.append_turn(session_id, "user", user_query)
            self.voice_conversations.append_turn(session_id, "assistant", guardrail_rejection)
            return {
                "response": guardrail_rejection,
                "status": "GUARDRAIL_BLOCKED",
                "citations": [],
                "active_fault": None,
                "session_id": session_id,
            }

        is_fault_inquiry = self._is_fault_relevant_voice_query(user_query)
        directive: Optional[DiagnosticDirective] = None
        if is_fault_inquiry and active_fault_id and active_fault_id in range(1, 9):
            directive = self.diagnostic_agent.diagnose(active_fault_id)

        live_state_block = self._build_live_state_block(current_flight_context)
        analytics = (current_flight_context or {}).get("analytics") or {}
        is_engine_nominal = analytics.get("diagnosed_fault_id", 0) == 0
        has_drift = bool(analytics.get("early_warning_trend")) or analytics.get("severity", "NORMAL") != "NORMAL"
        # A pure status question ("what's the issue?") gets answered from telemetry alone, with
        # NO manual excerpts in its context at all — not just an instruction to ignore them. With
        # nothing fault-shaped in the prompt to lift from, there's nothing for the model to
        # invent a fault out of. This only applies when there's no active diagnosed fault; an
        # active fault always goes through the `directive` branch below instead.
        is_status_branch = (
            directive is None
            and live_state_block is not None
            and self._classify_system_status_query(user_query)
        )

        if is_status_branch:
            retrieved_chunks: List[Dict[str, Any]] = []
            citations: List[str] = []
        else:
            # Drop voice top_k from 4 to 2 (voice replies are 1-3 sentences)
            retrieved_chunks = self.knowledge_store.query(user_query, top_k=2)
            citations = list(dict.fromkeys(self._clean_source_name(c.get("source", "")) for c in retrieved_chunks if c.get("source")))

        # Change 2: Break the history echo
        # Layer 1: Only pass dialogue history when turn is a followup or active fault inquiry
        needs_history = self._is_conversational_followup(user_query) or directive is not None
        if needs_history:
            # Layer 2: Cap at 2 turn pairs (last 4 messages), shorten assistant messages to 2 sentences
            raw_history = self.voice_conversations.get_history(session_id)[-4:]
            prompt_history = []
            for msg in raw_history:
                if msg.get("role") == "assistant":
                    c_text = msg.get("content", "").strip()
                    s_list = re.split(r"(?<=[.!?])\s+", c_text)
                    shortened = " ".join(s_list[:2]).strip()
                    prompt_history.append({"role": "assistant", "content": shortened})
                else:
                    prompt_history.append(dict(msg))
        else:
            prompt_history = []

        response_text = ""

        # Always attempt the LLM — generate_chat() lazy-loads on first call (ensure_loaded()
        # is a fast no-op once READY or permanently ERROR) and fails soft into the deterministic
        # fallback below on any error. Gating this on a pre-checked `is_ready` flag was the bug:
        # nothing ever triggered the load outside the separate /api/ai/warmup button, so every
        # voice turn silently used the templated fallback and never actually reasoned over anything.
        try:
            sentence_cap = self._extract_sentence_cap(user_query)
            turn_max_tokens = 160
            length_instruction = ""
            if sentence_cap:
                length_instruction = f" Keep it to at most {sentence_cap} sentence{'s' if sentence_cap != 1 else ''}, no more."
                # ~25 tokens/sentence is a generous ceiling for this model's phrasing — tight
                # enough that an explicit "2-3 sentences" request can't still come back as a
                # paragraph the way the shared 160-token budget let it before.
                turn_max_tokens = min(turn_max_tokens, max(40, sentence_cap * 25))

            if directive:
                intent = self._classify_fault_query_intent(user_query)
                directive_block = self._build_directive_block(directive, intent)
                if retrieved_chunks:
                    context_block = "\n\n".join(
                        f"BACKGROUND REFERENCE ({self._clean_source_name(c.get('source', 'manual'))} - paraphrase, never read aloud):\n"
                        f"{self._condense_chunk_for_prompt(c.get('content', ''), user_query)}"
                        for c in retrieved_chunks
                    )
                else:
                    context_block = "No manual section retrieved for this turn."
                user_prompt = (
                    f"OPERATOR SAID: {user_query}\n\n"
                    f"CURRENT ENGINE DIAGNOSTIC STATE:\n{directive_block}\n\n"
                    f"GROUNDING MANUAL EXCERPTS:\n{context_block}\n\n"
                    f"{self._intent_instruction(intent)}{length_instruction}"
                )
            elif is_status_branch:
                if is_engine_nominal and not has_drift:
                    status_instruction = (
                        "Nothing is wrong right now. Tell the operator everything is nominal in "
                        "one or two short spoken sentences, and you may name one or two of the "
                        "readings above. Do not name any fault, cause, or component problem — "
                        "there is none."
                    )
                else:
                    status_instruction = (
                        "There's sub-threshold drift worth flagging, but it is NOT a confirmed "
                        "fault. Mention it plainly and calmly in one or two sentences, referencing "
                        "the readings above. Do not call it a diagnosed fault or name a root cause."
                    )
                user_prompt = (
                    f"OPERATOR SAID: {user_query}\n\n"
                    f"{live_state_block}\n\n"
                    f"{status_instruction}{length_instruction}"
                )
            else:
                if retrieved_chunks:
                    context_block = "\n\n".join(
                        f"BACKGROUND REFERENCE ({self._clean_source_name(c.get('source', 'manual'))} - paraphrase, never read aloud):\n"
                        f"{self._condense_chunk_for_prompt(c.get('content', ''), user_query)}"
                        for c in retrieved_chunks
                    )
                else:
                    context_block = (
                        "No manual section covers this. Answer from the live engine state above "
                        "and say plainly if you're not sure — do not invent a manual reference."
                    )

                # Deliberately a single line here, not the full multi-line block used in the
                # other two branches — this is a reference/general question, and a big status
                # block would dominate a short answer the way the full directive dump used to.
                if live_state_block:
                    verdict_line = live_state_block.splitlines()[0]
                    state_header = f"{verdict_line}\n\n"
                else:
                    state_header = ""
                user_prompt = (
                    f"OPERATOR SAID: {user_query}\n\n"
                    f"{state_header}"
                    f"REFERENCE MANUAL EXCERPTS:\n{context_block}\n\n"
                    f"Respond the way you'd actually say it out loud, reasoning over the excerpts above "
                    f"rather than reading them back verbatim. If the excerpts don't fully answer it, use "
                    f"your judgment to give the most helpful grounded answer you can, and say what part "
                    f"you're unsure of.{length_instruction}"
                )

            ai_text = self.llm_engine.generate_chat_stream(
                AI_VOICE_COPILOT_SYSTEM_PROMPT,
                prompt_history,
                user_prompt,
                # Kept tighter than the text-chat budget (320) as a backstop for the "default
                # short, one to three sentences" instruction above — a long ceiling invites
                # padding and scene-setting even when the prompt asks for brevity. 160 still
                # leaves room for a real "why does this matter" explanation without turning
                # every turn into a monologue; _trim_to_complete_sentence below cleans up
                # whatever the budget still cuts off mid-thought. Tightened further per-turn
                # above when the operator asked for an explicit sentence count.
                max_new_tokens=turn_max_tokens,
                on_delta=on_delta,
            )
            if ai_text and len(ai_text.strip()) > 10:
                response_text = _trim_to_complete_sentence(_strip_markdown_for_speech(ai_text))

                # Layer 3: Deterministic echo detector
                raw_history = self.voice_conversations.get_history(session_id)
                if raw_history and not self._is_conversational_followup(user_query):
                    prev_assistant = next(
                        (m["content"] for m in reversed(raw_history) if m.get("role") == "assistant"),
                        None,
                    )
                    prev_user = next(
                        (m["content"] for m in reversed(raw_history) if m.get("role") == "user"),
                        None,
                    )
                    import difflib
                    user_is_repeat = False
                    if prev_user:
                        u_norm = re.sub(r"\W+", " ", user_query.lower()).strip()
                        pu_norm = re.sub(r"\W+", " ", prev_user.lower()).strip()
                        user_is_repeat = difflib.SequenceMatcher(None, u_norm, pu_norm).ratio() > 0.8

                    if prev_assistant and not user_is_repeat:
                        a_norm = re.sub(r"\W+", " ", response_text.lower()).strip()
                        b_norm = re.sub(r"\W+", " ", prev_assistant.lower()).strip()
                        if difflib.SequenceMatcher(None, a_norm, b_norm).ratio() > 0.75:
                            # Regenerate once with history=[]
                            try:
                                retry_text = self.llm_engine.generate_chat_stream(
                                    AI_VOICE_COPILOT_SYSTEM_PROMPT,
                                    [],
                                    user_prompt,
                                    max_new_tokens=turn_max_tokens,
                                    on_delta=on_delta,
                                )
                                if retry_text and len(retry_text.strip()) > 10:
                                    retry_resp = _trim_to_complete_sentence(_strip_markdown_for_speech(retry_text))
                                    retry_norm = re.sub(r"\W+", " ", retry_resp.lower()).strip()
                                    if difflib.SequenceMatcher(None, retry_norm, b_norm).ratio() <= 0.75:
                                        response_text = retry_resp
                                    else:
                                        response_text = ""
                            except Exception:
                                response_text = ""
        except Exception:
            response_text = ""

        if not response_text:
            response_text = self._synthesize_conversational_speech_answer(
                user_query, retrieved_chunks, directive, is_fault_inquiry,
                is_status_branch=is_status_branch, is_engine_nominal=is_engine_nominal,
                current_flight_context=current_flight_context,
            )

        self.voice_conversations.append_turn(session_id, "user", user_query)
        self.voice_conversations.append_turn(session_id, "assistant", response_text)

        return {
            "response": response_text,
            "status": "SUCCESS",
            "active_fault": directive.to_dict() if directive else None,
            "citations": citations,
            "retrieved_count": len(retrieved_chunks),
            "session_id": session_id,
        }

    def ask(
        self,
        user_query: str,
        current_flight_context: Optional[Dict[str, Any]] = None,
        active_fault_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Processes a pilot/operator query with guardrails, semantic RAG retrieval, and diagnostic synthesis.
        """
        # 1. Guardrail Check
        guardrail_rejection = self.check_guardrails(user_query)
        if guardrail_rejection:
            return {
                "response": guardrail_rejection,
                "status": "GUARDRAIL_BLOCKED",
                "citations": [],
                "active_fault": None
            }

        # 2. Check if this is an operational inquiry about an active fault. Uses the same
        # broadened check as ask_voice() (diagnostic vocabulary, not just exact phrases from
        # _is_active_fault_inquiry) - an operator typing "what to do about high cylinder head
        # temperature?" with fault 1 active is clearly asking about the live fault even though
        # it doesn't match any of _is_active_fault_inquiry's narrow phrases, and deserves the
        # authoritative ATA-grounded checklist rather than a generic manual-lookup answer.
        is_fault_inquiry = self._is_fault_relevant_voice_query(user_query)
        directive: Optional[DiagnosticDirective] = None

        if is_fault_inquiry and active_fault_id and active_fault_id in range(1, 9):
            directive = self.diagnostic_agent.diagnose(active_fault_id)

        # 3. Live telemetry grounding — see ask_voice()'s identical block for why this exists:
        # without it, a pure status question ("what's the issue?") on a healthy engine had
        # nothing but fault-describing manual chunks to answer from, and invented a fault.
        live_state_block = self._build_live_state_block(current_flight_context)
        analytics = (current_flight_context or {}).get("analytics") or {}
        is_engine_nominal = analytics.get("diagnosed_fault_id", 0) == 0
        has_drift = bool(analytics.get("early_warning_trend")) or analytics.get("severity", "NORMAL") != "NORMAL"
        is_status_branch = (
            directive is None
            and live_state_block is not None
            and self._classify_system_status_query(user_query)
        )

        # 4. Document Retrieval via Local Semantic Embedding Store — skipped for a pure status
        # question, so there's no fault-shaped manual text in context for the model to lift a
        # fault from.
        if is_status_branch:
            retrieved_chunks: List[Dict[str, Any]] = []
            citations: List[str] = []
        else:
            retrieved_chunks = self.knowledge_store.query(user_query, top_k=4)
            citations = list(dict.fromkeys(self._clean_source_name(c.get("source", "")) for c in retrieved_chunks if c.get("source")))

        # 5. Synthesize Response via Generative LLM (if preloaded) or Conversational RAG Synthesizer
        model_file = self.find_local_llm_model()
        response_text = ""

        # Branch A: Generative Conversational AI (Local Qwen3-4B). Always attempted — generate()
        # lazy-loads on first call and fails soft into Branch B on any error. Previously this was
        # gated on a pre-checked `is_ready` flag that nothing ever set True outside the separate
        # /api/ai/warmup button, so this branch silently never ran and every answer came from the
        # templated extractive fallback below regardless of whether the LLM was usable.
        try:
            if directive:
                if retrieved_chunks:
                    context_block = "\n\n".join(
                        f"BACKGROUND REFERENCE ({self._clean_source_name(c.get('source', 'manual'))} - paraphrase, never read aloud):\n"
                        f"{self._condense_chunk_for_prompt(c.get('content', ''), user_query)}"
                        for c in retrieved_chunks
                    )
                else:
                    context_block = "No manual section retrieved."
                directive_block = (
                    f"Diagnosed Active Fault: {directive.fault_name} ({directive.ata_chapter})\n"
                    f"Subsystem: {directive.subsystem} | Severity: {directive.severity}\n"
                    f"Deterministic Causal Chain: {' -> '.join(directive.causal_chain)}\n"
                    f"Root Cause: {directive.root_cause_explanation}\n"
                    f"Prescriptive Action: {directive.prescriptive_action}\n"
                    f"SOP Checklist: {'; '.join(directive.emergency_checklist)}"
                )
                prompt = (
                    f"OPERATOR INQUIRY: {user_query}\n\n"
                    f"ACTIVE ENGINE DIAGNOSTIC STATE:\n{directive_block}\n\n"
                    f"GROUNDING TECHNICAL MANUAL EXCERPTS:\n{context_block}\n\n"
                    f"Reason over the state and excerpts above to explain the situation, root cause, and "
                    f"prioritized operational actions — don't just restate them, actually explain the "
                    f"reasoning a competent engineer would walk through."
                )
            elif is_status_branch:
                if is_engine_nominal and not has_drift:
                    status_instruction = (
                        "Nothing is wrong right now. Tell the operator everything is nominal, "
                        "and you may cite one or two of the readings above. Do not name any "
                        "fault, cause, or component problem — there is none."
                    )
                else:
                    status_instruction = (
                        "There's sub-threshold drift worth flagging, but it is NOT a confirmed "
                        "fault. Mention it plainly and calmly, referencing the readings above. "
                        "Do not call it a diagnosed fault or name a root cause."
                    )
                prompt = (
                    f"OPERATOR INQUIRY: {user_query}\n\n"
                    f"{live_state_block}\n\n"
                    f"{status_instruction}"
                )
            else:
                if retrieved_chunks:
                    context_block = "\n\n".join(
                        f"BACKGROUND REFERENCE ({self._clean_source_name(c.get('source', 'manual'))} - paraphrase, never read aloud):\n"
                        f"{self._condense_chunk_for_prompt(c.get('content', ''), user_query)}"
                        for c in retrieved_chunks
                    )
                else:
                    context_block = (
                        "No manual section covers this. Answer from the live engine state above "
                        "and say plainly if you're not sure — do not invent a manual reference."
                    )

                # Single line only — see ask_voice()'s identical comment: a full status block
                # here would dominate what should be a short reference/general answer.
                if live_state_block:
                    state_header = f"{live_state_block.splitlines()[0]}\n\n"
                else:
                    state_header = ""
                prompt = (
                    f"OPERATOR INQUIRY: {user_query}\n\n"
                    f"{state_header}"
                    f"REFERENCE TECHNICAL MANUAL EXCERPTS:\n{context_block}\n\n"
                    f"Answer the operator's question naturally and in depth, reasoning over the excerpts "
                    f"above with exact values/tolerances/procedures where relevant, rather than reading "
                    f"them back verbatim."
                )

            ai_text = self.llm_engine.generate(
                AI_CONVERSATIONAL_COPILOT_PROMPT,
                prompt,
                max_new_tokens=320
            )
            if ai_text and len(ai_text.strip()) > 20:
                response_text = _trim_to_complete_sentence(ai_text.strip())
        except Exception:
            response_text = ""

        # Branch B: Fast Conversational RAG Synthesis (Instantaneous & Grounded)
        if not response_text:
            if is_status_branch and is_engine_nominal:
                if current_flight_context:
                    telemetry = current_flight_context.get("telemetry") or {}
                    analytics = current_flight_context.get("analytics") or {}
                    health = analytics.get("health_index", 1.0)
                    oil_p = telemetry.get("OIL_PRESS", 3.85)
                    chts = [telemetry.get(f"CHT_{i}") for i in range(1, 5) if isinstance(telemetry.get(f"CHT_{i}"), (int, float))]
                    avg_cht = sum(chts) / len(chts) if chts else 105
                    response_text = (
                        f"Everything's nominal right now — health index {health:.2f}, CHTs around {avg_cht:.0f} C, "
                        f"oil pressure {oil_p:.2f} bar. All systems operating within normal certified limits."
                    )
                else:
                    response_text = "Everything's nominal right now — no fault detected, all readings in range."
            elif is_status_branch:
                trend = ((current_flight_context or {}).get("analytics") or {}).get("early_warning_trend")
                if trend:
                    param = trend.get("parameter") or trend.get("param") or "a parameter"
                    response_text = f"Nothing's confirmed as a fault yet, but early drift indicates {param} is trending off nominal."
                else:
                    response_text = "Nothing's confirmed as a fault yet, but there's some early drift worth keeping an eye on."
            elif directive and is_fault_inquiry:
                checklist_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(directive.emergency_checklist))
                response_text = (
                    f"**[DIAGNOSTIC ADVISORY - {directive.ata_chapter}]**\n"
                    f"**System:** {directive.subsystem} ({directive.fault_name})\n"
                    f"**Severity:** {directive.severity}\n\n"
                    f"**Root Cause Analysis:**\n{directive.root_cause_explanation}\n\n"
                    f"**Prescriptive Pilot Directive:**\n{directive.prescriptive_action}\n\n"
                    f"**Emergency SOP Checklist:**\n{checklist_str}\n\n"
                    f"**Manual Reference:** {directive.manual_reference}\n\n"
                    f"---\n**Copilot Advisory:** Active telemetry indicates parameters require immediate corrective trim."
                )
            else:
                response_text = self._synthesize_extractive_answer(user_query, retrieved_chunks)

        return {
            "response": response_text,
            "status": "SUCCESS",
            "active_fault": directive.to_dict() if directive else None,
            "citations": citations,
            "retrieved_count": len(retrieved_chunks),
            "local_model_loaded": str(model_file.name) if model_file else "Semantic RAG Engine"
        }

    def diagnose_with_ai(self, engine_snapshot: Dict[str, Any], directive: Optional[DiagnosticDirective]) -> Dict[str, Any]:
        """
        Core Plane-2 flow: Digital Twin State -> RAG retrieval -> Qwen3-4B reasoning -> grounded diagnosis.
        """
        fault_name = directive.fault_name if directive else "NOMINAL_FLIGHT"
        subsystem = directive.subsystem if directive else "PROPULSION_CORE"
        ata_chapter = directive.ata_chapter if directive else "ATA 00-00"
        causal_chain = directive.causal_chain if directive else []

        query = f"{fault_name} {subsystem} {ata_chapter} causal propagation diagnosis"
        retrieved = self.knowledge_store.query(query, top_k=4)
        citations = sorted({self._clean_source_name(c.get("source", "")) for c in retrieved if c.get("source")})

        context_block = "\n\n".join(
            f"[Source: {self._clean_source_name(c.get('source', 'manual'))}]\n{c.get('content', '')}"
            for c in retrieved
        ) or "No directly relevant manual section retrieved."

        telemetry = engine_snapshot.get("telemetry", {})
        residuals = engine_snapshot.get("residuals", {})
        causal_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(causal_chain)) or "No fault active."

        user_prompt = (
            f"DIGITAL TWIN STATE (computed by the deterministic physics/ML engine):\n"
            f"- Diagnosed Fault: {fault_name} ({ata_chapter}, subsystem {subsystem})\n"
            f"- Flight Context: {telemetry.get('THEATER', 'LADAKH')} theater, "
            f"ALT {telemetry.get('ALTITUDE_FT', '?')} ft, OAT {telemetry.get('OAT_C', '?')}C, "
            f"RPM {telemetry.get('ENGINE_RPM', '?')}, TPS {telemetry.get('TPS', '?')}%\n"
            f"- Key Sensor Residuals (Actual - Expected): {residuals}\n"
            f"- Deterministic Causal Propagation Chain (already computed, ground truth):\n{causal_str}\n\n"
            f"RETRIEVED REFERENCE PASSAGES:\n{context_block}\n\n"
            f"Reason through this causal chain the way an experienced propulsion engineer would explain "
            f"it out loud, then give prioritized recommendations. Don't just restate the chain."
        )

        # Always attempt the LLM (lazy-loads on first call, fails soft) — see ask_voice()/ask() above
        # for why this must not be gated on a pre-checked `is_ready` flag.
        text = None
        try:
            text = self.llm_engine.generate(AI_DIAGNOSIS_SYSTEM_PROMPT, user_prompt, max_new_tokens=280)
        except Exception:
            text = None

        if not text:
            # Deterministic RAG manual synthesis fallback
            text = (
                f"**Root Cause Analysis:** {directive.root_cause_explanation if directive else 'Nominal parameters.'}\n\n"
                f"**Prescriptive SOP Directive:** {directive.prescriptive_action if directive else 'Maintain flight envelope.'}\n\n"
                f"**Causal Chain Summary:** {' -> '.join(causal_chain) if causal_chain else 'All parameters within limits.'}\n\n"
                f"**Manual Reference:** {directive.manual_reference if directive else 'Rotax MML / DRDO FMECA.'}"
            )

        return {
            "status": "READY",
            "fault_name": fault_name,
            "explanation": text,
            "citations": citations,
        }
