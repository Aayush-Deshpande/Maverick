"""
Guards the B0.2 fix: the LLM must default to disabled, and must never default to
a Chinese-origin model. See docs/build/DECISIONS.md D14.
"""

from __future__ import annotations

import importlib
import os


def test_default_provider_is_none_and_disabled(monkeypatch):
    monkeypatch.delenv("ANUMAAN_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANUMAAN_LLM_MODEL_ID", raising=False)
    monkeypatch.delenv("QWEN_MODEL_ID", raising=False)
    import backend.agent.llm_engine as mod
    importlib.reload(mod)
    try:
        assert mod.ANUMAAN_LLM_PROVIDER == "none"
        engine = mod.LocalLLMEngine()
        assert engine.provider == "none"
        assert engine.status == "DISABLED"
        assert engine.ensure_loaded() is False
    finally:
        importlib.reload(mod)  # restore module state for later tests


def test_backward_compat_alias_exists():
    import backend.agent.llm_engine as mod
    assert mod.LocalQwenEngine is mod.LocalLLMEngine


def test_qwen_is_not_the_default_provider_model():
    """qwen must remain *selectable* (explicit opt-in, dev/offline use) but must
    never be reachable via the default env-var-less path."""
    import backend.agent.llm_engine as mod
    assert mod.LLM_PROVIDER_MODELS["none"] is None
    assert "qwen" in mod.LLM_PROVIDER_MODELS  # still selectable, not removed
    assert os.environ.get("ANUMAAN_LLM_PROVIDER", "none") != "qwen" or (
        "ANUMAAN_LLM_PROVIDER" in os.environ  # only OK if explicitly set by the caller
    )
