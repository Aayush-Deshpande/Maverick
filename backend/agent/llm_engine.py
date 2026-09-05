"""
Local Qwen3-4B Reasoning Engine — served via Ollama (GGUF Q4_K_M, GPU-offloaded)
DRDO / iDEX Problem Statement ID: 26054

Runs Qwen3-4B fully on-device (no cloud, no API keys) through a local Ollama
server, which wraps llama.cpp's quantized GPU kernels. This replaced an earlier
transformers + BitsAndBytes 4-bit implementation: both run the same model at the
same ~4-bit precision, but llama.cpp's kernels are dramatically faster for this
kind of consumer-GPU inference — benchmarked in this repo at ~8-10 tok/s under
transformers/BitsAndBytes vs. ~64 tok/s under Ollama on the same RTX 4050 Laptop
GPU (6GB VRAM), turning a 30-90s reply into single-digit seconds.

Design constraints (do not relax without re-reading the caller):
  * Lazy-loaded: the model is only pulled into Ollama's VRAM (via a no-op "warm"
    request) on first real use, never at server import/startup time, so the 20 Hz
    deterministic engine and the "1-click" launcher are unaffected if Ollama is
    busy, absent, or the feature is never used.
  * Fails soft: any connection or generation error is captured into `self.status`
    / `self.load_error` and raised as a plain RuntimeError to the caller — it
    must NEVER crash the FastAPI process or the 20 Hz engine thread.
  * Blocking by design: `generate()`/`generate_chat()` run synchronous HTTP calls
    that block on GPU-bound inference server-side. Callers MUST invoke them from
    a worker thread (`asyncio.to_thread` from a route handler, or a plain
    `threading.Thread` from the engine tick) — never from the asyncio event loop
    or the engine's `state_lock` critical section.
  * External dependency: requires an Ollama server running locally (`ollama
    serve`, or the Windows/Mac app, which runs it as a background service) with
    the model already pulled (`ollama pull qwen3:4b-instruct-2507-q4_K_M`). This
    class does not manage the Ollama process itself, only talks to its REST API.
"""

import json
import os
import threading
import time
import logging
from typing import Callable, Optional

import httpx

logger = logging.getLogger("QwenEngine")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
QWEN_MODEL_ID = os.environ.get("QWEN_MODEL_ID", "qwen2.5:1.5b")
QWEN_MAX_NEW_TOKENS = int(os.environ.get("QWEN_MAX_NEW_TOKENS", "320"))
# Qwen3's native context window (262144 tokens per `ollama show`) is wildly oversized for
# this diagnostic-assistant use case — asking Ollama to allocate a KV cache for the full
# window fails outright (observed: a 37GB buffer allocation error) on a 6GB laptop GPU.
# 4096 comfortably covers a system prompt + retrieved manual excerpts + conversation
# history + reply for every prompt this app constructs.
QWEN_NUM_CTX = int(os.environ.get("QWEN_NUM_CTX", "4096"))
# Qwen3's hybrid thinking mode is disabled by default: the <think>...</think> reasoning
# preamble adds latency this diagnostic-assistant use case doesn't need.
QWEN_ENABLE_THINKING = os.environ.get("QWEN_ENABLE_THINKING", "0") == "1"
# Keeps the model resident in VRAM between turns instead of reloading on every request —
# reloading is fast on Ollama (~1-3s) but still needless overhead for an active session.
QWEN_KEEP_ALIVE = os.environ.get("QWEN_KEEP_ALIVE", "30m")


class LocalQwenEngine:
    """Singleton client for a Qwen3-4B model served locally by Ollama."""

    _instance: Optional["LocalQwenEngine"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "LocalQwenEngine":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._gen_lock = threading.Lock()   # serializes concurrent generate() calls
        self._load_lock = threading.Lock()  # guards the one-time warm-load
        self.status = "NOT_LOADED"          # NOT_LOADED | LOADING | READY | ERROR
        self.load_error: Optional[str] = None
        self.device_info: str = ""
        self.model_id = QWEN_MODEL_ID
        self._client = httpx.Client(base_url=OLLAMA_HOST, timeout=180.0)

    @property
    def is_ready(self) -> bool:
        return self.status == "READY"

    def ensure_loaded(self) -> bool:
        """Warms the model into Ollama's VRAM on first call. Thread-safe and idempotent."""
        if self.status == "READY":
            return True
        # ask()/ask_voice()/diagnose_with_ai() always attempt real generation now (no
        # pre-checked is_ready gate — see backend/agent/copilot.py), so keep this engine
        # fast-failing under pytest (PYTEST_CURRENT_TEST is set by pytest itself for the
        # run's duration) rather than depending on a real Ollama server being reachable in
        # every test environment — callers exercise their fail-soft fallback path instead.
        if "PYTEST_CURRENT_TEST" in os.environ:
            self.status = "ERROR"
            self.load_error = "Qwen engine disabled under pytest (PYTEST_CURRENT_TEST set)"
            return False
        with self._load_lock:
            if self.status == "READY":
                return True
            if self.status == "ERROR":
                return False
            self.status = "LOADING"
            try:
                t0 = time.time()
                logger.info(f"[QwenEngine] Warming {self.model_id} via Ollama at {OLLAMA_HOST} ...")
                # An empty prompt loads the model into VRAM and returns immediately
                # (done_reason: "load") without generating any tokens.
                resp = self._client.post("/api/generate", json={
                    "model": self.model_id,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": QWEN_KEEP_ALIVE,
                    "options": {"num_ctx": QWEN_NUM_CTX},
                })
                resp.raise_for_status()
                data = resp.json()
                if data.get("error"):
                    raise RuntimeError(data["error"])

                # The empty-prompt load above gets the model into VRAM and is enough on its
                # own for steady-state speed (confirmed: with this and the RAG index below both
                # warmed, the first real voice turn measured ~4s, same as every turn after it —
                # a suspected extra "first real decode" penalty turned out to actually be the
                # RAG embedding index's own one-time cold-start bleeding into that measurement,
                # not this engine; see engine_service.py's warm-up thread for the real fix).
                # This second call is just a cheap, realistically-shaped decode as extra
                # insurance against any residual one-time cost specific to this engine.
                # Best-effort: failure here doesn't fail the warm-up as a whole, since the
                # empty-prompt load above already proves the model is usable.
                try:
                    filler_system = (
                        "You are a helpful assistant. " * 40
                    )  # ~280 tokens, roughly the size of a real system prompt + context block
                    self._client.post("/api/chat", json={
                        "model": self.model_id,
                        "messages": [
                            {"role": "system", "content": filler_system},
                            {"role": "user", "content": "Say a short sentence about the weather."},
                        ],
                        "stream": False,
                        "think": False,
                        "keep_alive": QWEN_KEEP_ALIVE,
                        "options": {"num_ctx": QWEN_NUM_CTX, "num_predict": 64},
                    })
                except Exception as warm_e:
                    logger.warning(f"[QwenEngine] Decode warm-up call failed (non-fatal): {warm_e}")

                self.device_info = "Ollama (GPU-offloaded)"
                self.status = "READY"
                logger.info(f"[QwenEngine] {self.model_id} ready in {time.time() - t0:.1f}s")
                return True
            except Exception as e:
                self.status = "ERROR"
                self.load_error = str(e)
                logger.error(f"[QwenEngine] Failed to reach/load {self.model_id} via Ollama: {e}", exc_info=True)
                return False

    def _chat(self, messages: list, max_new_tokens: Optional[int], temperature: float, top_p: float) -> str:
        with self._gen_lock:
            resp = self._client.post("/api/chat", json={
                "model": self.model_id,
                "messages": messages,
                "stream": False,
                "think": QWEN_ENABLE_THINKING,
                "keep_alive": QWEN_KEEP_ALIVE,
                "options": {
                    "num_ctx": QWEN_NUM_CTX,
                    "num_predict": max_new_tokens or QWEN_MAX_NEW_TOKENS,
                    "temperature": temperature,
                    "top_p": top_p,
                    "repeat_penalty": 1.1,
                },
            })
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                raise RuntimeError(data["error"])
            return data["message"]["content"].strip()

    def _chat_stream(
        self,
        messages: list,
        max_new_tokens: Optional[int],
        temperature: float,
        top_p: float,
        on_delta: Optional[Callable[[str], None]],
    ) -> str:
        """Same request as _chat() but with stream: True, invoking on_delta(text_chunk) as
        each piece of the reply arrives so a caller can surface live "thinking" output (e.g.
        a voice UI showing the reply being composed instead of a silent multi-second wait).
        Still fully blocking/synchronous — the streaming is HTTP-level, not async — so this
        has the same worker-thread requirement as _chat(). Returns the full accumulated text,
        identical in content to what non-streaming _chat() would have returned."""
        with self._gen_lock:
            chunks: list = []
            with self._client.stream("POST", "/api/chat", json={
                "model": self.model_id,
                "messages": messages,
                "stream": True,
                "think": QWEN_ENABLE_THINKING,
                "keep_alive": QWEN_KEEP_ALIVE,
                "options": {
                    "num_ctx": QWEN_NUM_CTX,
                    "num_predict": max_new_tokens or QWEN_MAX_NEW_TOKENS,
                    "temperature": temperature,
                    "top_p": top_p,
                    "repeat_penalty": 1.1,
                },
            }) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("error"):
                        raise RuntimeError(data["error"])
                    delta = data.get("message", {}).get("content", "")
                    if delta:
                        chunks.append(delta)
                        if on_delta:
                            on_delta(delta)
                    if data.get("done"):
                        break
            return "".join(chunks).strip()

    def generate(self, system_prompt: str, user_prompt: str, max_new_tokens: Optional[int] = None) -> str:
        """
        Blocking single-turn generation. Must be called from a worker thread.
        Raises RuntimeError (never crashes) if the model is unavailable.
        """
        if not self.ensure_loaded():
            raise RuntimeError(f"Qwen engine unavailable: {self.load_error}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self._chat(messages, max_new_tokens, temperature=0.3, top_p=0.85)

    def generate_chat(self, system_prompt: str, history: list, user_prompt: str, max_new_tokens: Optional[int] = None) -> str:
        """
        Blocking multi-turn generation: system prompt + prior conversation turns + the
        current user turn. Used by the voice copilot so follow-up questions ("why is
        that?") resolve against what was actually said earlier in the conversation,
        rather than being re-synthesized from scratch. Must be called from a worker
        thread. Raises RuntimeError (never crashes) if the model is unavailable.

        Args:
            history: prior turns as [{"role": "user"|"assistant", "content": str}, ...],
                     oldest first. Does not include the current user_prompt.
        """
        if not self.ensure_loaded():
            raise RuntimeError(f"Qwen engine unavailable: {self.load_error}")

        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            role = turn.get("role")
            content = turn.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_prompt})

        return self._chat(messages, max_new_tokens, temperature=0.4, top_p=0.9)

    def generate_chat_stream(
        self,
        system_prompt: str,
        history: list,
        user_prompt: str,
        max_new_tokens: Optional[int] = None,
        on_delta: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Streaming counterpart to generate_chat() — identical message construction and
        return value, but calls on_delta(chunk) as text arrives instead of blocking silently
        until the full reply is done. Used by the voice copilot so the operator sees the
        reply being composed live rather than staring at a silent "thinking" state."""
        if not self.ensure_loaded():
            raise RuntimeError(f"Qwen engine unavailable: {self.load_error}")

        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            role = turn.get("role")
            content = turn.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_prompt})

        return self._chat_stream(messages, max_new_tokens, temperature=0.4, top_p=0.9, on_delta=on_delta)

    def status_payload(self) -> dict:
        return {
            "status": self.status,
            "model_id": self.model_id,
            "device": self.device_info or None,
            "error": self.load_error,
            "enable_thinking": QWEN_ENABLE_THINKING,
        }
