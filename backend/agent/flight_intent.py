"""
Natural-Language Flight-Vector Intent Engine (PRD F10).
DRDO / iDEX Problem Statement ID: 26054

Parses a short operator utterance ("take a dive to the left to cool the engine") into one of
the six canonical tactical-maneuver intents documented in
final_tasks/01_DYNAMIC_TACTICAL_SIMULATION_AND_AUTOGCAS.md §5, and hands it to the running
Blender canyon flight sim (apps/blender_twin/standalone_canyon_flight_app.py) through a small
file-based command queue.

Why a file, not a live socket/import: the flight sim runs inside Blender's own embedded Python
interpreter, launched as a separate OS process by launch_canyon_simulation.bat — it shares no
memory or module space with this backend process. A single atomically-written JSON file with a
monotonic sequence number is the simplest transport that is (a) trivially pollable from inside
Blender's existing 143 Hz modal timer with no new dependency, and (b) inherently only ever holds
the single most recent command, which matches how the sim already treats its hotkeys (a press is
a discrete, one-shot trigger, not a held state) — there is deliberately no multi-command backlog
to keep the consumer side (Blender) simple and race-free.

Parsing is deterministic (keyword/regex), not LLM-based, on purpose: this is a flight-safety
adjacent command channel (it can toggle copilot off, or command a terrain-hugging dive), and a
probabilistic model has no place deciding whether "dive" was actually said. The existing
LLM/RAG copilot (backend/agent/copilot.py) remains the right tool for open-ended diagnostic
conversation; this module only ever recognizes the fixed intent vocabulary below and returns
None for anything else, so callers can fall back to the conversational copilot for everything
this doesn't recognize.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import json
import os
import re
import time


# ─────────────────────────────────────────────────────────────────────────────
# Canonical intent vocabulary (final_tasks/01_DYNAMIC_TACTICAL_SIMULATION_AND_AUTOGCAS.md §5)
# ─────────────────────────────────────────────────────────────────────────────
DIVE_CONVECTIVE_COOL = "DIVE_CONVECTIVE_COOL"
DIVE_LEFT_VALLEY = "DIVE_LEFT_VALLEY"
DIVE_RIGHT_VALLEY = "DIVE_RIGHT_VALLEY"   # symmetric counterpart, not in the original table but
                                          # the same pattern with the opposite sign — omitting it
                                          # would make "dive right" silently fall through to
                                          # DIVE_CONVECTIVE_COOL, which is a worse experience than
                                          # supporting the obviously-implied mirror command.
EVADE_LEFT = "EVADE_LEFT"
EVADE_RIGHT = "EVADE_RIGHT"
RE_CLIMB_CRUISE = "RE_CLIMB_CRUISE"
SET_COPILOT_ON = "SET_COPILOT_ON"
SET_COPILOT_OFF = "SET_COPILOT_OFF"

_ALL_INTENTS = {
    DIVE_CONVECTIVE_COOL, DIVE_LEFT_VALLEY, DIVE_RIGHT_VALLEY,
    EVADE_LEFT, EVADE_RIGHT, RE_CLIMB_CRUISE, SET_COPILOT_ON, SET_COPILOT_OFF,
}


@dataclass
class FlightIntent:
    intent: str
    relative_heading_offset_deg: float
    utterance: str
    seq: int = 0          # filled in by write_flight_command()
    issued_epoch: float = 0.0


# Ordered so that more specific phrasings are checked first (e.g. "dive left" must win over the
# bare "dive" pattern). Each entry is (regex, intent, heading_offset_deg).
_PATTERNS = [
    (re.compile(r"\b(copilot|auto[\s-]?gcas)\b.*\b(on|arm|enable|engage)\b", re.I), SET_COPILOT_ON, 0.0),
    (re.compile(r"\b(engage|arm|enable)\b.*\b(copilot|auto[\s-]?gcas)\b", re.I), SET_COPILOT_ON, 0.0),
    (re.compile(r"\b(copilot|auto[\s-]?gcas)\b.*\b(off|disable|disengage|manual)\b", re.I), SET_COPILOT_OFF, 0.0),
    (re.compile(r"\b(disable|disengage|kill)\b.*\b(copilot|auto[\s-]?gcas)\b", re.I), SET_COPILOT_OFF, 0.0),

    (re.compile(r"\bclimb\b.*\b(cruise|back|high|safe|altitude)\b", re.I), RE_CLIMB_CRUISE, 0.0),
    (re.compile(r"\b(re-?climb|pull\s*up|return to cruise|resume cruise)\b", re.I), RE_CLIMB_CRUISE, 0.0),

    (re.compile(r"\b(evade|break|turn)\b.*\bleft\b", re.I), EVADE_LEFT, -60.0),
    (re.compile(r"\b(evade|break|turn)\b.*\bright\b", re.I), EVADE_RIGHT, 60.0),

    (re.compile(r"\bdive\b.*\bleft\b|\bleft\b.*\bdive\b", re.I), DIVE_LEFT_VALLEY, -45.0),
    (re.compile(r"\bdive\b.*\bright\b|\bright\b.*\bdive\b", re.I), DIVE_RIGHT_VALLEY, 45.0),
    (re.compile(r"\b(dive|descend|drop down)\b.*\b(canyon|gorge|valley|cool|cooling)\b", re.I), DIVE_CONVECTIVE_COOL, 0.0),
    (re.compile(r"\b(dive|descend)\b", re.I), DIVE_CONVECTIVE_COOL, 0.0),
]


def parse_flight_intent(text: str) -> Optional[FlightIntent]:
    """Returns a FlightIntent if `text` matches one of the six canonical maneuver commands,
    else None (caller should fall back to the conversational copilot for anything else)."""
    if not text or not text.strip():
        return None
    for pattern, intent, offset in _PATTERNS:
        if pattern.search(text):
            return FlightIntent(intent=intent, relative_heading_offset_deg=offset, utterance=text.strip())
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Command queue — single-slot, atomically-written JSON file with a monotonic seq
# ─────────────────────────────────────────────────────────────────────────────

def _repo_root() -> str:
    # backend/agent/flight_intent.py -> repo root is two levels up
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def default_queue_path() -> str:
    return os.path.join(_repo_root(), "runtime", "flight_intent_command.json")


def write_flight_command(cmd: FlightIntent, queue_path: Optional[str] = None) -> Dict[str, Any]:
    """Atomically writes the next command into the single-slot queue file, assigning it the
    next monotonic sequence number (read from the previous file, if any, so restarts of this
    backend process don't reset the counter and cause the Blender-side consumer to ignore a
    genuinely-new command because its seq looks stale/lower)."""
    target = queue_path or default_queue_path()
    os.makedirs(os.path.dirname(target), exist_ok=True)

    prev_seq = 0
    if os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as f:
                prev_seq = int(json.load(f).get("seq", 0))
        except Exception:
            prev_seq = 0

    cmd.seq = prev_seq + 1
    cmd.issued_epoch = time.time()

    payload = asdict(cmd)
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    os.replace(tmp, target)  # atomic on POSIX and Windows — the Blender-side poller never sees
                             # a half-written file, even if it reads mid-write on another process
    return payload


def handle_flight_command_text(text: str, queue_path: Optional[str] = None) -> Dict[str, Any]:
    """Convenience entry point for the REST layer: parse + enqueue in one call. Returns a dict
    with status='OK' and the enqueued command, or status='UNRECOGNIZED' if `text` didn't match
    any of the six canonical intents."""
    parsed = parse_flight_intent(text)
    if parsed is None:
        return {"status": "UNRECOGNIZED", "message": f"No flight-vector intent recognized in: {text!r}"}
    written = write_flight_command(parsed, queue_path=queue_path)
    return {"status": "OK", "command": written}
