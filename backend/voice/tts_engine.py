"""
Local Kokoro-82M Text-to-Speech Engine (offline, GPU-accelerated when available).
DRDO / iDEX Problem Statement ID: 26054

Synthesizes the Mission Copilot's spoken response using the `Voice/Kokoro-82M`
weights already present in the repo (StyleTTS2-based `kokoro` package), entirely
on-device — no cloud TTS API.

Design constraints (mirrors backend/agent/llm_engine.py — do not relax without
re-reading the caller):
  * Lazy-loaded: the model is only built on first real use, never at server
    import/startup time.
  * Fails soft: any load or synthesis error is captured into `self.status` /
    `self.load_error` and raised as a plain RuntimeError to the caller — it
    must NEVER crash the FastAPI process or the 20 Hz engine thread.
  * Blocking by design: `synthesize()` runs synchronous inference (sub-second
    on GPU, a few seconds on CPU for a long reply). Callers MUST invoke it from
    a worker thread (`asyncio.to_thread`) — never from the asyncio event loop.
  * GPU-optional: unlike Qwen3-4B (hard CUDA requirement for 4-bit kernels),
    Kokoro is only 82M parameters and runs acceptably on CPU, so it degrades
    gracefully instead of refusing to load when no GPU is present.
"""

import os
import io
import threading
import time
import logging
from pathlib import Path
from typing import Optional

from backend.ml_runtime_lock import TRANSFORMERS_FIRST_IMPORT_LOCK

logger = logging.getLogger("VoiceTTS")

_DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "Voice" / "Kokoro-82M"
KOKORO_MODEL_DIR = Path(os.environ.get("KOKORO_MODEL_DIR", str(_DEFAULT_MODEL_DIR)))
KOKORO_REPO_ID = "hexgrad/Kokoro-82M"
KOKORO_SAMPLE_RATE = 24000
DEFAULT_VOICE = os.environ.get("KOKORO_DEFAULT_VOICE", "af_heart")


class LocalKokoroTTS:
    """Singleton wrapper around a locally-loaded Kokoro-82M StyleTTS2 pipeline."""

    _instance: Optional["LocalKokoroTTS"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "LocalKokoroTTS":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._pipeline = None
        self._gen_lock = threading.Lock()
        self._load_lock = threading.Lock()
        self.status = "NOT_LOADED"  # NOT_LOADED | LOADING | READY | ERROR
        self.load_error: Optional[str] = None
        self.device_info: str = ""
        self.model_dir = KOKORO_MODEL_DIR
        self.default_voice = DEFAULT_VOICE

    @property
    def is_ready(self) -> bool:
        return self.status == "READY"

    def list_voices(self) -> list:
        voices_dir = self.model_dir / "voices"
        if not voices_dir.exists():
            return []
        return sorted(p.stem for p in voices_dir.glob("*.pt"))

    def _resolve_voice_path(self, voice: str) -> str:
        """Accepts either a bare voice name (e.g. 'af_heart') matching a local
        voices/*.pt file, or an already-resolved path."""
        if os.path.exists(voice):
            return voice
        candidate = self.model_dir / "voices" / f"{voice}.pt"
        if candidate.exists():
            return str(candidate)
        raise RuntimeError(f"Unknown Kokoro voice '{voice}' (not found under {self.model_dir / 'voices'})")

    def ensure_loaded(self) -> bool:
        """Loads the Kokoro model on first call. Thread-safe and idempotent."""
        if self.status == "READY":
            return True
        with self._load_lock:
            if self.status == "READY":
                return True
            if self.status == "ERROR":
                return False
            self.status = "LOADING"
            try:
                config_path = self.model_dir / "config.json"
                weights_path = self.model_dir / "kokoro-v1_0.pth"
                if not config_path.exists() or not weights_path.exists():
                    raise RuntimeError(f"Kokoro model files not found under {self.model_dir}")

                import torch

                t0 = time.time()
                logger.info(f"[VoiceTTS] Loading Kokoro-82M from {self.model_dir} ...")

                # Serialized against LocalQwenEngine/embedding_index's first load — see
                # backend/ml_runtime_lock.py: `transformers`'s lazy top-level module isn't
                # safe against two threads pulling different symbols from it for the first
                # time concurrently (reproduced directly during voice-integration testing:
                # a concurrent sentence-transformers load corrupted this exact `from
                # transformers import AlbertModel` used inside `kokoro`).
                with TRANSFORMERS_FIRST_IMPORT_LOCK:
                    from kokoro import KModel, KPipeline
                    model = KModel(
                        repo_id=KOKORO_REPO_ID,
                        config=str(config_path),
                        model=str(weights_path),
                    )
                model.eval()
                if torch.cuda.is_available():
                    model = model.to("cuda")
                    self.device_info = torch.cuda.get_device_name(0)
                else:
                    self.device_info = "CPU"

                # lang_code='a' selects the American-English misaki grapheme-to-phoneme
                # front end, matching the af_*/am_* voice packs shipped in voices/.
                self._pipeline = KPipeline(lang_code="a", repo_id=KOKORO_REPO_ID, model=model)
                self.status = "READY"
                logger.info(f"[VoiceTTS] Loaded on {self.device_info} in {time.time() - t0:.1f}s")
                return True
            except Exception as e:
                self.status = "ERROR"
                self.load_error = str(e)
                logger.error(f"[VoiceTTS] Failed to load Kokoro model: {e}", exc_info=True)
                return False

    def synthesize(self, text: str, voice: Optional[str] = None, speed: float = 1.0) -> bytes:
        """
        Blocking speech synthesis. Must be called from a worker thread.
        Returns 16-bit PCM WAV bytes at KOKORO_SAMPLE_RATE. Raises RuntimeError
        (never crashes) if the engine is unavailable.
        """
        if not text or not text.strip():
            raise RuntimeError("Cannot synthesize empty text")
        if not self.ensure_loaded():
            raise RuntimeError(f"Kokoro TTS engine unavailable: {self.load_error}")

        import numpy as np
        import soundfile as sf

        voice_path = self._resolve_voice_path(voice or self.default_voice)

        with self._gen_lock:
            chunks = []
            for result in self._pipeline(text.strip(), voice=voice_path, speed=speed):
                if result.audio is not None:
                    chunks.append(result.audio.detach().cpu().numpy())

        if not chunks:
            raise RuntimeError("Kokoro produced no audio for the given text")

        audio = np.concatenate(chunks)
        buf = io.BytesIO()
        sf.write(buf, audio, KOKORO_SAMPLE_RATE, format="WAV", subtype="PCM_16")
        return buf.getvalue()

    def status_payload(self) -> dict:
        return {
            "status": self.status,
            "model_dir": str(self.model_dir),
            "device": self.device_info or None,
            "error": self.load_error,
            "default_voice": self.default_voice,
            "sample_rate": KOKORO_SAMPLE_RATE,
        }
