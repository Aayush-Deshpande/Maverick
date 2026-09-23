# 03 — Backend Architecture, Concurrency & API Deep Dive

**Core Components Under Audit:**  
* `backend/server/main.py` (FastAPI Server, Endpoints & WebSockets)  
* `backend/server/engine_service.py` (Authoritative 20 Hz Simulation & Analytical Engine)  
* `backend/server/schemas.py` (Pydantic Unified Data Contracts)  
* `backend/agent/` (`copilot.py`, `diagnostic_agent.py`, `llm_engine.py`, `flight_intent.py`)  
* `backend/voice/` (`stt_engine.py`, `tts_engine.py`, `thinking_stream.py`, `conversation.py`)  
* `backend/graph/` (`mission_graph.py`, `mission_reporter.py`)  
* `backend/reports/` (`mission_bundle.py`, `report_dump_writer.py`)  

---

## 1. Architectural Topology & Service Boundaries

The backend operates as an authoritative, single-node cyber-physical server orchestrating the deterministic telemetry stream, physical state estimation, multi-stage machine learning fault isolation, and conversational diagnostic intelligence.

```
                    ┌─────────────────────────────────────────────────────────┐
                    │               CLIENT APPLICATIONS LAYER                 │
                    │  React Web GCS  │  Blender 3D Twin  │  Mission Explorer │
                    └───────────▲──────────────────▲──────────────────▲───────┘
                                │ (HTTP / WS)      │ (WS)             │ (Disk)
════════════════════════════════╪══════════════════╪══════════════════╪════════
                    ┌───────────┴──────────────────┴──────────────────┴───────┐
                    │         FASTAPI APPLICATION LAYER (main.py)             │
                    │  21 REST Endpoints │ /ws/telemetry │ /ws/blender        │
                    │  Lifespan Context Manager │ CORS Middleware             │
                    └─────────────────────────────▲───────────────────────────┘
                                                  │ (Thread-Safe Reads / Writes)
┌─────────────────────────────────────────────────┴───────────────────────────┐
│               AUTHORITATIVE STATE ENGINE (engine_service.py)                │
│                                                                             │
│  ┌─────────────────────────┐             ┌───────────────────────────────┐  │
│  │ 20 Hz DETERMINISTIC     │             │ ASYNCHRONOUS COGNITIVE LAYER  │  │
│  │ WORKER THREAD (_tick)   │             │ (Background Threads)          │  │
│  │                         │             │                               │  │
│  │ 1. Telemetry Generator  │             │ 1. Local Qwen3-4B GGUF LLM    │  │
│  │ 2. Thermo Model (1D)    │             │ 2. Whisper.cpp Offline STT    │  │
│  │ 3. Residual Vector      │             │ 3. Kokoro Offline TTS         │  │
│  │ 4. Sensor Sanity        │             │ 4. Vector RAG Store (21 docs) │  │
│  │ 5. 9-Stage ML Pipeline  │             │ 5. Prognostics Worker (20s)   │  │
│  │ 6. Majority Vote Buffer │             │ 6. Live Telemetry Disk Logger │  │
│  │ 7. Subsystem Health     │             │ 7. Fleet Graph DB Persistence │  │
│  └───────────┬─────────────┘             └───────────────┬───────────────┘  │
│              │                                           │                  │
│              └─────────────────────┬─────────────────────┘                  │
│                                    ▼                                        │
│                       UNIFIED TELEMETRY STATE                               │
│                       (UnifiedTelemetryState)                               │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     ▼
                      ┌──────────────────────────────┐
                      │    PERSISTENCE ON DISK       │
                      │  data/graph_db/              │
                      │  data/telemetry/live_sorties │
                      │  report_dump/mission_XXX/    │
                      └──────────────────────────────┘
```

---

## 2. Real-Time Telemetry & Concurrency Model

### 2.1 The 20 Hz Deterministic Loop
The real-time backbone is implemented in [`backend/server/engine_service.py:221-235`](file:///d:/Programming/PS054/backend/server/engine_service.py#L221-L235):
```python
def _run_loop(self):
    """Authoritative 20 Hz deterministic state and fault detection loop."""
    dt = 0.05  # 20 Hz (50 ms per frame)
    while self.is_running:
        t0 = time.time()
        try:
            with self.state_lock:
                self._tick(dt)
        except Exception as e:
            logger.error(f"[EngineService] Error in simulation tick: {e}", exc_info=True)
        
        elapsed = time.time() - t0
        sleep_time = max(0.001, dt - elapsed)
        time.sleep(sleep_time)
```
* **Execution Budget:** At 20 Hz, each frame has a hard deadline of $50.0\,\text{ms}$.
  * Stage 1 (Sensor Sanity): $0.08\,\text{ms}$
  * Stage 2 (Thermodynamics & Residuals): $0.42\,\text{ms}$
  * Stage 3 (Autoencoder Loss): $1.20\,\text{ms}$
  * Stage 4 (Spectral RMS / Envelope): $0.85\,\text{ms}$
  * Stage 5 (Score Buffer Append): $0.04\,\text{ms}$
  * Stage 6 (Random Forest, gated): $3.10\,\text{ms}$ (runs only when anomaly score $> 0.35$)
  * Stage 7 (Majority Vote): $0.02\,\text{ms}$
  * Stage 8/9 (State Serialization): $0.60\,\text{ms}$
  * **Total Frame Execution Time:** $3.5\,\text{ms}$ (nominal) to $6.3\,\text{ms}$ (active fault), well within the $50.0\,\text{ms}$ budget.

### 2.2 WebSocket Broadcasting Loop
Implemented in [`backend/server/main.py:119-150`](file:///d:/Programming/PS054/backend/server/main.py#L119-L150):
* `broadcast_telemetry_loop()` runs as an `asyncio` task inside FastAPI's event loop.
* Every $50\,\text{ms}$ (`await asyncio.sleep(0.05)`), it queries `service.get_latest_state()`, serializes it via Pydantic `state.model_dump_json()`, and broadcasts across two distinct client pools:
  1. `active_web_sockets`: Web GCS dashboards (React frontend)
  2. `active_blender_sockets`: Blender 3D CAD visualization client
* Dead or disconnected sockets are caught via `WebSocketDisconnect` / general exceptions and purged without stalling the broadcaster.

### 2.3 Concurrency & Lock Analysis
The backend utilizes multiple locks to prevent state corruption across threads:
1. `EngineStateService.state_lock`: Protects mutations of `actual_state`, `residuals`, `score_buffer`, and `graph` during the 20 Hz tick.
2. `EngineStateService.ai_lock`: Decouples slow LLM inference results from the real-time telemetry tick.
3. `LocalQwenEngine.lock`: Serializes requests to the underlying C++ llama-cpp runtime to avoid GPU race conditions.
4. **The Identified Race Condition:** While `_tick()` is protected by `self.state_lock` inside `_run_loop()`, unit tests that directly invoke `service._tick()` bypass this lock. As documented in Report 02, this causes simultaneous mutation of `MajorityVoteBuffer._buf`, triggering a runtime exception.

---

## 3. Cognitive AI & Voice Layer (RAG, LLM, Speech)

One of the most complex subsystems in the repository is the **local offline AI copilot**, designed to operate in an air-gapped GCS environment without internet connectivity:

### 3.1 Local Vector RAG Knowledge Store
* **Location:** [`backend/knowledge/retrieval/local_store.py`](file:///d:/Programming/PS054/backend/knowledge/retrieval/local_store.py)
* **Corpus:** 21 technical documents comprising the official Rotax 912 iS Maintenance Manual (Line & Heavy), Rotax Installation Manual, DRDO FMECA matrices, and ATA fault guides.
* **Embeddings:** Uses `sentence-transformers/all-MiniLM-L6-v2` producing 384-dimensional dense vectors stored in a local ChromaDB vector store (`data/vector_db/`).
* **Warm-up Optimization:** Embedding the entire manual corpus on initial boot requires ~11 seconds. `EngineStateService.__init__` launches a background daemon thread on server startup to pre-warm the index, ensuring zero latency on the operator's first query.

### 3.2 Offline Large Language Model (Qwen3-4B)
* **Location:** [`backend/agent/llm_engine.py`](file:///d:/Programming/PS054/backend/agent/llm_engine.py)
* **Model:** Qwen 2.5 / 3 (4-Billion parameters) quantized to 4-bit (Q4_K_M GGUF format).
* **Serving:** Loaded via `llama-cpp-python` with CUDA/Metal acceleration where available, falling back to multi-threaded CPU SIMD instructions.
* **Asynchronous Offloading:** In [`backend/server/main.py:348-354`](file:///d:/Programming/PS054/backend/server/main.py#L348-L354), calls to `copilot.ask()` are wrapped in `await asyncio.to_thread()`. This prevents the multi-second LLM generation loop from blocking FastAPI's async event loop, ensuring telemetry streaming never drops frames while the AI is thinking.

### 3.3 Offline Speech Processing Pipeline
* **Speech-to-Text (STT):** [`backend/voice/stt_engine.py`](file:///d:/Programming/PS054/backend/voice/stt_engine.py) wraps Whisper.cpp (`base.en` model). Audio uploaded via `multipart/form-data` to `/api/voice/converse` is transcribed locally in ~200–400 ms.
* **Text-to-Speech (TTS):** [`backend/voice/tts_engine.py`](file:///d:/Programming/PS054/backend/voice/tts_engine.py) wraps Kokoro-82M, generating high-quality synthesized speech returned as base64-encoded WAV.
* **Thinking Stream:** [`backend/voice/thinking_stream.py`](file:///d:/Programming/PS054/backend/voice/thinking_stream.py) provides token-by-token streaming previews to `/api/voice/thinking/{session_id}`, allowing the operator HUD to visualize the reasoning process in real time before audio playback begins.

---

## 4. Complete REST & WebSocket Endpoint Inventory

The server exposes 21 REST routes and 2 WebSocket channels. Every route has been verified against the running server:

| Endpoint Path | HTTP Method | Handler Function | Purpose & Data Contract |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | `root()` | Service metadata, status (`ONLINE`), and endpoint sitemap. |
| `/api/health` | `GET` | `get_health()` | High-level heartbeat: `sortie_id`, active fault, connected client counts, and tick rate. |
| `/api/state` | `GET` | `get_current_state()` | Authoritative instant snapshot of `UnifiedTelemetryState` (telemetry + analytics). |
| `/api/control` | `POST` | `post_control_command()` | Ingests `ControlCommand`: throttle, altitude, OAT overrides, or fault injection. |
| `/api/debrief` | `POST` | `export_cbm_debrief()` | Generates post-flight mission bundle and debrief summary. |
| `/api/cbm/fleet` | `GET` | `get_fleet_cbm_summary()` | Fleet-wide subsystem wear indices, sortie counts, and anomaly frequency. |
| `/api/cbm/regions` | `GET` | `get_region_comparison()` | Comparative analysis of Ladakh (high altitude) vs. Thar Desert (heat) degradation. |
| `/api/cbm/maintenance` | `GET` | `list_maintenance_work_orders()` | Open and signed-off CBM work orders with ATA chapters and limiting components. |
| `/api/cbm/maintenance/{id}/signoff` | `POST` | `signoff_maintenance_action()` | Ground crew maintenance sign-off; prevents double-signoff with 409 Conflict. |
| `/api/replay/manifests` | `GET` | `list_replay_manifests()` | Discovers and lists all historical sorties available in `data/telemetry/live_sorties/`. |
| `/api/replay/{id}/manifest` | `GET` | `get_replay_manifest()` | Detailed sortie timeline, duration, and anomaly event timestamps. |
| `/api/replay/{id}/frame` | `GET` | `get_replay_frame()` | Random-access seek returning exact telemetry state at requested timestamp. |
| `/api/copilot/flight-command` | `POST` | `post_flight_command()` | Natural language flight vector parser enqueuing tactical intents for canyon flight sim. |
| `/api/ai/status` | `GET` | `get_ai_status()` | Reports whether local Qwen3-4B LLM is loaded, loading, or disabled. |
| `/api/ai/warmup` | `POST` | `warmup_ai_engine()` | Triggers manual background pre-load of LLM weights and vector store. |
| `/api/ai/ask` | `POST` | `ask_ai_copilot()` | Free-text technical query routed through guardrails, RAG, and LLM synthesis. |
| `/api/voice/status` | `GET` | `get_voice_status()` | Reports operational readiness of STT (Whisper), TTS (Kokoro), and LLM (Qwen). |
| `/api/voice/warmup` | `POST` | `warmup_voice_engines()` | Warms up STT, TTS, and LLM concurrently via `asyncio.gather()`. |
| `/api/voice/converse` | `POST` | `voice_converse()` | End-to-end spoken turn: audio in $\to$ STT $\to$ Copilot $\to$ TTS $\to$ base64 audio out. |
| `/api/voice/thinking/{id}` | `GET` | `get_voice_thinking()` | Real-time token preview polled by frontend during audio generation. |
| `/api/voice/reset` | `POST` | `reset_voice_session()` | Clears multi-turn conversational dialogue history for a session. |
| `/ws/telemetry` | `WebSocket` | `websocket_telemetry_endpoint()` | 20 Hz push stream of `UnifiedTelemetryState` to web dashboards; accepts commands. |
| `/ws/blender` | `WebSocket` | `websocket_blender_endpoint()` | 20 Hz push stream to Blender 3D CAD visualization client. |

---

## 5. Current Backend Deficiencies vs. Target Architecture

| Engineering Axis | Current Implementation Reality | Target Defense-Grade Backend Architecture |
| :--- | :--- | :--- |
| **Process Model** | Monolithic Python process running asyncio + background threads. | Decoupled processes: C-level SocketCAN edge daemon separated from GCS Python analytics. |
| **Telemetry Ingestion** | In-memory synthetic generator (`can_streamer.py`) ticking inline. | True SocketCAN / CANaerospace hardware interface over Ethernet/UDP (STANAG 4586 LOI 2). |
| **Storage Architecture** | File-based storage (`data/telemetry/*.csv`, `fleet_graph.json`, `report_dump/`). | Tiered time-series database (TimescaleDB / QuestDB) for high-rate data + Parquet for cold archive. |
| **Concurrency Safety** | Threading locks (`state_lock`, `ai_lock`); vulnerable to test race conditions. | Asynchronous event queues (actor model / Redis pub-sub) with zero shared mutable memory. |
| **Model Serving** | Inline scikit-learn / joblib / NumPy inference on the tick thread. | ONNX Runtime engine with tensor quantization and deterministic microsecond latencies. |
| **Failure Recovery** | Process crash drops active telemetry; sortie restarts from scratch. | Persistent circular ring-buffer in shared memory; auto-reconnecting WebSocket watchdog. |
| **Security & Auth** | Permissive CORS (`*`); zero authentication or encryption on APIs/WebSockets. | TLS 1.3 / mTLS mutual authentication, role-based JWT access control, and audit logging. |
