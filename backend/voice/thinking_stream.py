"""
Live "Thinking" Preview Buffer for the Voice Copilot.
DRDO / iDEX Problem Statement ID: 26054

/api/voice/converse is a single request/response cycle (audio in, transcript + spoken
reply + TTS audio out) — there's no open connection for the frontend to read partial
LLM output from while a turn is still generating. Rather than restructure that endpoint
into a raw streaming HTTP response, this is a small in-memory scratch buffer that the
in-flight request writes into (via LocalQwenEngine.generate_chat_stream's on_delta
callback) and a lightweight polling endpoint reads from, so the voice UI can show the
reply being composed live — the same idea as a coding CLI agent's streaming output —
without changing the shape of the main request/response.

Keyed by session_id (one voice conversation = one session = one in-flight turn at a
time in practice), overwritten fresh on every new turn via start(), so there's no
separate expiry/cleanup needed at this app's scale (a handful of concurrent operators
at most).
"""

import threading
from typing import Dict, Tuple


class ThinkingStreamStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._buffers: Dict[str, str] = {}
        self._done: Dict[str, bool] = {}

    def start(self, session_id: str) -> None:
        with self._lock:
            self._buffers[session_id] = ""
            self._done[session_id] = False

    def append(self, session_id: str, delta: str) -> None:
        with self._lock:
            self._buffers[session_id] = self._buffers.get(session_id, "") + delta

    def finish(self, session_id: str) -> None:
        with self._lock:
            self._done[session_id] = True

    def read(self, session_id: str) -> Tuple[str, bool]:
        with self._lock:
            return self._buffers.get(session_id, ""), self._done.get(session_id, True)


THINKING_STREAM = ThinkingStreamStore()
