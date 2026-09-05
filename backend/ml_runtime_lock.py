"""
Process-Wide First-Import Lock for `transformers`-Dependent Engines.
DRDO / iDEX Problem Statement ID: 26054

This backend lazy-loads independent heavy ML engines from background worker
threads: the RAG embedding model (backend/knowledge/retrieval/embedding_index.py)
and the Kokoro TTS engine (backend/voice/tts_engine.py). Both transitively import
HuggingFace `transformers`, and can each be triggered for the FIRST time on a
different thread (e.g. the fault-onset AI diagnosis thread and an incoming API
request racing each other right after server startup). The Qwen3-4B copilot
(backend/agent/llm_engine.py) used to be a third participant here when it ran
in-process via transformers/BitsAndBytes; it now talks to a local Ollama server
over HTTP instead and no longer touches `transformers` at all, so it no longer
needs this lock.

`transformers` populates its top-level lazy-module symbol table (which class lives
in which submodule) incrementally as different symbols are first accessed, and that
population is not thread-safe: two threads pulling different symbols (e.g.
`AutoModel` via sentence-transformers, `AlbertModel` via Kokoro) while `transformers`
is still mid-import can corrupt that table, causing an unrelated later import to
fail with a spurious `ImportError: cannot import name 'X' from 'transformers'` — this
was reproduced directly during voice-integration testing. Once fully imported once,
`transformers` is safe to use concurrently, so this lock only needs to be held around
each engine's *first* load, never around later inference calls.

This module is also the one guaranteed choke point both engines import before they
ever touch `transformers` (see the `with TRANSFORMERS_FIRST_IMPORT_LOCK:` blocks in
each), which makes it the right place to set backend-selection env vars that must be
in place before transformers' own first import. In particular: if a `tensorflow`
install happens to be present on the machine (pulled in by some unrelated package —
nothing in this repo imports it), `transformers.modeling_utils` eagerly imports it
purely to register TF loss-function utilities, which drags in Keras and even
`google-api-core`/`googleapiclient` along the way. Measured on this project's own
dev machine: `import kokoro` alone went from ~12s to ~8s once this was set (the
remaining time is torch/transformers/phonemizer themselves, not TF). Both engines
here are PyTorch-only, so it's always safe to disable.
"""

import os
import threading

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")

TRANSFORMERS_FIRST_IMPORT_LOCK = threading.Lock()
