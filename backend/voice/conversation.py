"""
Voice Conversation State Manager.
DRDO / iDEX Problem Statement ID: 26054

Keeps a short rolling per-session dialogue history so the voice Mission Copilot
can resolve follow-up questions ("why is that?", "what should I do about it?")
naturally, the way a human co-pilot would, instead of treating every utterance
as an isolated one-shot query. Purely in-memory: sessions are ephemeral (one
flight/browser tab), never persisted, and never touch the deterministic engine.
"""

import threading
import time
from collections import OrderedDict
from typing import Dict, List, Optional

MAX_TURNS_PER_SESSION = 8       # user+assistant pairs kept for LLM context
MAX_ACTIVE_SESSIONS = 32        # evict oldest session past this to bound memory


class VoiceConversationManager:
    """Thread-safe, in-memory, LRU-bounded per-session dialogue history."""

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: "OrderedDict[str, List[Dict[str, str]]]" = OrderedDict()

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        with self._lock:
            history = self._sessions.get(session_id, [])
            return list(history)

    def append_turn(self, session_id: str, role: str, content: str):
        with self._lock:
            if session_id not in self._sessions:
                if len(self._sessions) >= MAX_ACTIVE_SESSIONS:
                    self._sessions.popitem(last=False)  # evict least-recently-used
                self._sessions[session_id] = []
            else:
                self._sessions.move_to_end(session_id)

            self._sessions[session_id].append({"role": role, "content": content, "ts": time.time()})
            # Keep only the most recent turns (2 messages per turn: user + assistant)
            max_messages = MAX_TURNS_PER_SESSION * 2
            if len(self._sessions[session_id]) > max_messages:
                self._sessions[session_id] = self._sessions[session_id][-max_messages:]

    def reset(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)
