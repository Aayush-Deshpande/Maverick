"""
Local LLM Reasoning Engine — served via Ollama (GGUF, GPU-offloaded)
DRDO / iDEX Problem Statement ID: 26054

Runs a local model fully on-device (no cloud, no API keys) through a local
Ollama server, which wraps llama.cpp's quantized GPU kernels.

Pluggable provider, defaulting to DISABLED (B0.2). This file previously
hardcoded Qwen3-4B (Alibaba) as both the class name and the only supported
model. For a DRDO deliverable that is a real defect, not a style choice: the
Indian Army cancelled contracts for 400 drones in 2025 specifically over
Chinese-origin components (see docs/audit/10_red_team_readiness_review.md
Sec 2.6), and shipping a Chinese model as the *default* AI component of this
system is exactly that failure mode. The engine now:

  * defaults to ANUMAAN_LLM_PROVIDER=none -- the LLM never starts, never talks
    to Ollama, and the copilot falls back to its deterministic templated
    answers (backend/agent/copilot.py already has this fallback path for
    every caller, since the engine was always allowed to be unavailable);
  * requires an explicit, informed opt-in to select a provider, preferring
    Indian open-weight models (Sarvam, Apache-2.0; BharatGen Param2) over
    anything else; Qwen remains selectable (ANUMAAN_LLM_PROVIDER=qwen) for
    local dev/offline use, but is never the default and must never be shipped
    as the default in a DRDO-facing build;
  * keeps every other property of the original design: lazy-loaded, fails
    soft, blocking-by-design, external Ollama dependency.

See docs/build/DECISIONS.md D14 for the standing decision this implements.

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
    the selected provider's model already pulled (see the provider registry
    below). This class does not manage the Ollama process itself, only talks
    to its REST API.
"""

import json
import os
import threading
import time
import logging
from typing import Callable, Optional

import httpx

logger = logging.getLogger("LocalLLMEngine")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# Provider registry: Ollama model tag per provider. "none" (the default) never
# resolves to a tag and the engine never contacts Ollama at all. Pull the
# corresponding model yourself before selecting a provider, e.g.:
#   ollama pull sarvam-30b            # Sarvam-30B, Apache-2.0 (sarvam)
#   ollama pull param2                # BharatGen Param2, MoE-17B (bharatgen)
#   ollama pull qwen2.5:1.5b          # dev/offline only -- never the default (qwen)
# ANUMAAN_LLM_MODEL_ID overrides the tag for any provider, including "local-other"
# for a self-hosted/self-pulled model not in this registry.
LLM_PROVIDER_MODELS = {
    "none": None,
    "sarvam": "sarvam-30b",
    "bharatgen": "param2",
    "qwen": "qwen2.5:1.5b",
    "local-other": None,  # resolved entirely from ANUMAAN_LLM_MODEL_ID below
}
ANUMAAN_LLM_PROVIDER = os.environ.get("ANUMAAN_LLM_PROVIDER", "none").lower()
if ANUMAAN_LLM_PROVIDER not in LLM_PROVIDER_MODELS:
    logger.warning(
        f"[LocalLLMEngine] Unknown ANUMAAN_LLM_PROVIDER={ANUMAAN_LLM_PROVIDER!r}, "
        f"falling back to 'none' (disabled). Valid: {sorted(LLM_PROVIDER_MODELS)}"
    )
    ANUMAAN_LLM_PROVIDER = "none"
QWEN_MODEL_ID = os.environ.get(
    "ANUMAAN_LLM_MODEL_ID",
    os.environ.get("QWEN_MODEL_ID") or LLM_PROVIDER_MODELS[ANUMAAN_LLM_PROVIDER] or "",
)  # QWEN_MODEL_ID kept as a fallback env var name for anyone with it already set
QWEN_MAX_NEW_TOKENS = int(os.environ.get("QWEN_MAX_NEW_TOKENS", "320"))
# 262144-token native context windows are wildly oversized for this diagnostic-assistant
# use case — asking Ollama to allocate a KV cache for the full window fails outright
# (observed: a 37GB buffer allocation error) on a 6GB laptop GPU. 4096 comfortably covers
# a system prompt + retrieved manual excerpts + conversation history + reply for every
# prompt this app constructs.
QWEN_NUM_CTX = int(os.environ.get("QWEN_NUM_CTX", "4096"))
# Hybrid "thinking" reasoning preambles are disabled by default: the extra latency isn't
# needed for this diagnostic-assistant use case.
QWEN_ENABLE_THINKING = os.environ.get("QWEN_ENABLE_THINKING", "0") == "1"
# Keeps the model resident in VRAM between turns instead of reloading on every request —
# reloading is fast on Ollama (~1-3s) but still needless overhead for an active session.
QWEN_KEEP_ALIVE = os.environ.get("QWEN_KEEP_ALIVE", "30m")


class LocalLLMEngine:
    """Singleton client for a locally-served LLM (via Ollama). Disabled by default
    (ANUMAAN_LLM_PROVIDER=none) -- see the module docstring and
    docs/build/DECISIONS.md D14 for why the default must never be a Chinese-origin
    model."""

    _instance: Optional["LocalLLMEngine"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "LocalLLMEngine":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._gen_lock = threading.Lock()   # serializes concurrent generate() calls
        self._load_lock = threading.Lock()  # guards the one-time warm-load
        self.provider = ANUMAAN_LLM_PROVIDER
        self.status = "DISABLED" if self.provider == "none" else "NOT_LOADED"
        # NOT_LOADED | LOADING | READY | ERROR | DISABLED
        self.load_error: Optional[str] = (
            None if self.provider != "none"
            else "No LLM provider selected (ANUMAAN_LLM_PROVIDER=none, the default); "
                 "the copilot uses its deterministic templated answers instead."
        )
        self.device_info: str = ""
        self.model_id = QWEN_MODEL_ID
        self._client = httpx.Client(base_url=OLLAMA_HOST, timeout=180.0)

    @property
    def is_ready(self) -> bool:
        return self.status == "READY"

    def ensure_loaded(self) -> bool:
        """Warms the model into Ollama's VRAM on first call. Thread-safe and idempotent."""
        if self.provider == "none":
            return False  # disabled by configuration -- never touch the network
        if self.status == "READY":
            return True
        # ask()/ask_voice()/diagnose_with_ai() always attempt real generation now (no
        # pre-checked is_ready gate — see backend/agent/copilot.py), so keep this engine
        # fast-failing under pytest (PYTEST_CURRENT_TEST is set by pytest itself for the
        # run's duration) rather than depending on a real Ollama server being reachable in
        # every test environment — callers exercise their fail-soft fallback path instead.
        if "PYTEST_CURRENT_TEST" in os.environ:
            self.status = "ERROR"
            self.load_error = "LLM engine disabled under pytest (PYTEST_CURRENT_TEST set)"
            return False
        with self._load_lock:
            if self.status == "READY":
                return True
            if self.status == "ERROR":
                return False
            self.status = "LOADING"
            try:
                t0 = time.time()
                logger.info(f"[LocalLLMEngine] Warming {self.model_id} via Ollama at {OLLAMA_HOST} ...")
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
                    logger.warning(f"[LocalLLMEngine] Decode warm-up call failed (non-fatal): {warm_e}")

                self.device_info = "Ollama (GPU-offloaded)"
                self.status = "READY"
                logger.info(f"[LocalLLMEngine] {self.model_id} ready in {time.time() - t0:.1f}s")
                return True
            except Exception as e:
                self.status = "ERROR"
                self.load_error = str(e)
                logger.error(f"[LocalLLMEngine] Failed to reach/load {self.model_id} via Ollama: {e}", exc_info=True)
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
            raise RuntimeError(f"LLM engine unavailable: {self.load_error}")

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
            raise RuntimeError(f"LLM engine unavailable: {self.load_error}")

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
            raise RuntimeError(f"LLM engine unavailable: {self.load_error}")

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
            "provider": self.provider,
            "model_id": self.model_id or None,
            "device": self.device_info or None,
            "error": self.load_error,
            "enable_thinking": QWEN_ENABLE_THINKING,
        }


# Backward-compat alias: earlier code/branches import LocalQwenEngine by name.
# Prefer LocalLLMEngine in new code.
LocalQwenEngine = LocalLLMEngine
