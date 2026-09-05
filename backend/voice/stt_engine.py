"""
Local Whisper.cpp Speech-to-Text Engine — ggml-tiny.en (CPU, offline).
DRDO / iDEX Problem Statement ID: 26054

Transcribes operator speech captured in the browser (any container ffmpeg can
demux: webm/opus, ogg, wav, mp3, ...) into text for the existing Mission Copilot
RAG pipeline. Uses the `Voice/ggml-tiny.en.bin` model already present in the repo
via `pywhispercpp` (Python bindings around whisper.cpp).

Design constraints (mirrors backend/agent/llm_engine.py — do not relax without
re-reading the caller):
  * Lazy-loaded: the whisper.cpp context is only built on first real use, never
    at server import/startup time.
  * Fails soft: any load, decode, or transcription error is captured into
    `self.status` / `self.load_error` and raised as a plain RuntimeError to the
    caller — it must NEVER crash the FastAPI process or the 20 Hz engine thread.
  * Blocking by design: `transcribe()` runs synchronous CPU-bound inference.
    Callers MUST invoke it from a worker thread (`asyncio.to_thread` from a route
    handler) — never from the asyncio event loop.
  * CPU-only and small (~75MB): unlike the Qwen3-4B engine, this does not
    require or reserve any GPU VRAM, so it can safely load in parallel with the
    Qwen engine on the same laptop GPU without contention.
"""

import os
import re
import subprocess
import threading
import time
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("VoiceSTT")

_DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "Voice" / "ggml-tiny.en.bin"
WHISPER_MODEL_PATH = os.environ.get("WHISPER_MODEL_PATH", str(_DEFAULT_MODEL_PATH))
WHISPER_SAMPLE_RATE = 16000

# whisper.cpp emits bracketed non-speech markers ("[BLANK_AUDIO]", "[SILENCE]", "(MUSIC)") as
# ordinary segment text when a clip carries no speech. Left in, they read as a real transcript:
# the caller's `if not transcript` check passes, the copilot answers the "question" [BLANK_AUDIO]
# by inventing something from whatever manual chunks retrieval happened to return, and that
# phantom exchange is written into the session's dialogue history where it skews later turns.
# Continuous listening mode hits this constantly — every VAD-bounded silence gap produces one.
_WHISPER_NON_SPEECH_RE = re.compile(
    r"[\[(\*]\s*(BLANK_AUDIO|BLANK|INAUDIBLE|SILENCE|MUSIC|SOUND|NOISE|APPLAUSE|"
    r"NO_SPEECH|CLICK|BEEP)[^\])\*]*[\])\*]",
    re.IGNORECASE,
)


def _find_ffmpeg() -> str:
    """Resolves an ffmpeg executable: system PATH first, else the self-contained
    static binary bundled by the `imageio-ffmpeg` package (no system install
    required, keeping this feature usable on an air-gapped defense laptop)."""
    import shutil
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


class LocalWhisperSTT:
    """Singleton wrapper around a ggml whisper.cpp tiny.en model."""

    _instance: Optional["LocalWhisperSTT"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "LocalWhisperSTT":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._model = None
        self._ffmpeg_exe: Optional[str] = None
        self._transcribe_lock = threading.Lock()
        self._load_lock = threading.Lock()
        self.status = "NOT_LOADED"  # NOT_LOADED | LOADING | READY | ERROR
        self.load_error: Optional[str] = None
        self.model_path = WHISPER_MODEL_PATH

    @property
    def is_ready(self) -> bool:
        return self.status == "READY"

    def ensure_loaded(self) -> bool:
        """Loads the ggml whisper.cpp model on first call. Thread-safe and idempotent."""
        if self.status == "READY":
            return True
        with self._load_lock:
            if self.status == "READY":
                return True
            if self.status == "ERROR":
                return False
            self.status = "LOADING"
            try:
                if not os.path.exists(self.model_path):
                    raise RuntimeError(f"Whisper STT model not found at {self.model_path}")

                from pywhispercpp.model import Model

                t0 = time.time()
                logger.info(f"[VoiceSTT] Loading whisper.cpp model from {self.model_path} ...")
                self._model = Model(
                    model=self.model_path,
                    redirect_whispercpp_logs_to=None,
                    no_context=True,
                    single_segment=False,
                )
                self._ffmpeg_exe = _find_ffmpeg()
                self.status = "READY"
                logger.info(f"[VoiceSTT] Loaded in {time.time() - t0:.2f}s (CPU, ggml tiny.en)")
                return True
            except Exception as e:
                self.status = "ERROR"
                self.load_error = str(e)
                logger.error(f"[VoiceSTT] Failed to load whisper model: {e}", exc_info=True)
                return False

    def _decode_to_pcm16k(self, audio_bytes: bytes) -> np.ndarray:
        """Demuxes/resamples arbitrary input audio (webm/opus, ogg, wav, mp3, ...)
        into mono float32 PCM at the 16kHz whisper.cpp requires, via ffmpeg."""
        cmd = [
            self._ffmpeg_exe, "-hide_banner", "-loglevel", "error",
            "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", str(WHISPER_SAMPLE_RATE), "pipe:1",
        ]
        proc = subprocess.run(cmd, input=audio_bytes, capture_output=True, timeout=30)
        if proc.returncode != 0 or not proc.stdout:
            raise RuntimeError(f"Audio decode failed: {proc.stderr.decode(errors='ignore')[:300]}")
        pcm = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
        return pcm

    def transcribe(self, audio_bytes: bytes) -> str:
        """
        Blocking transcription of a raw audio clip (any container). Must be
        called from a worker thread. Raises RuntimeError (never crashes) if the
        engine or ffmpeg decode is unavailable.

        Returns "" for a clip that carried no actual speech — see
        _WHISPER_NON_SPEECH_RE above for why a silence marker must never be
        allowed to reach the copilot as if it were a question.
        """
        if not self.ensure_loaded():
            raise RuntimeError(f"Whisper STT engine unavailable: {self.load_error}")

        pcm = self._decode_to_pcm16k(audio_bytes)
        if pcm.size < WHISPER_SAMPLE_RATE * 0.15:
            # Shorter than ~150ms of audio — not enough signal for a meaningful transcript.
            return ""

        with self._transcribe_lock:
            segments = self._model.transcribe(pcm)

        text = " ".join(seg.text.strip() for seg in segments if seg.text.strip()).strip()
        return self._strip_non_speech(text)

    @staticmethod
    def _strip_non_speech(text: str) -> str:
        """Removes whisper's bracketed non-speech markers, returning "" if nothing
        speech-like survives. Marker-only clips ("[BLANK_AUDIO]") become empty; a clip
        that was partly marker and partly speech keeps the speech ("[SOUND] check the
        oil" -> "check the oil")."""
        if not text:
            return ""
        cleaned = _WHISPER_NON_SPEECH_RE.sub(" ", text)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        # Nothing alphanumeric left (bare punctuation, or a single stray character) means
        # there was no real utterance — treat it as silence rather than passing a fragment
        # through as a question.
        if len(cleaned) < 2 or not re.search(r"[A-Za-z0-9]", cleaned):
            return ""
        # tiny.en also hallucinates "Thank you." / "Thanks for watching!" / "you" on silence.
        # Suppress only on exact whole-transcript match (never substring), so a real "thank you"
        # utterance is only dropped if it was an artifact of silence.
        normalized_lower = cleaned.lower().rstrip(".!?,")
        if normalized_lower in ("thank you", "thanks for watching", "you", "thanks for watching!"):
            return ""
        return cleaned

    def status_payload(self) -> dict:
        return {
            "status": self.status,
            "model_path": self.model_path,
            "error": self.load_error,
        }
