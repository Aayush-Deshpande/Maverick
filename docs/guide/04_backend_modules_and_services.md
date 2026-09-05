# ⚙️ Backend Modules & Core Services
**DRDO / iDEX Problem Statement ID: 26054**  
*Backend Architecture, Service Catalog, API Specifications & Module Dependencies*

---

## 1. Backend Architecture Overview

The `backend/` directory houses the authoritative simulation engine, physics shadow, analytical machine learning pipeline, local RAG vector store, and FastAPI server.

```
backend/
├── server/           # FastAPI web application, WebSocket broadcaster, Pydantic data schemas
├── physics/          # 1D Thermodynamic Otto cycle equations & Sensor Sanity validator
├── telemetry/        # 50 Hz CAN streamer, fault injector, multi-source dataset parsers
├── ml/               # 9-Stage inference pipeline, Autoencoder, Random Forest, FFT, Trend RUL
├── agent/            # Diagnostic Agent, Mission Copilot, Local 4-bit Qwen3-4B LLM Engine
├── knowledge/        # Offline document loaders (PDF/Docx/TXT) & Semantic Reranking retrieval
└── graph/            # In-memory property graph for CBM history & Markdown debrief generator
```

---

## 2. Service Catalog & Module Specifications

### 2.1. `backend/server/` — Real-Time API & Authoritative State Engine

#### 📄 `backend/server/main.py`
* **Purpose:** FastAPI entry point. Hosts the asynchronous 50 FPS WebSocket broadcast loop and REST endpoints for UI control, health diagnostics, and AI Copilot inquiries.
* **Key Components:**
  * `lifespan(app)`: Initializes `EngineStateService` and starts the background `broadcast_telemetry_loop`.
  * `broadcast_telemetry_loop(service)`: Continuous 50 Hz async task pushing state JSON to `active_web_sockets` and `active_blender_sockets`.
* **REST Endpoints:**
  * `GET /`: Service metadata and API discovery directory.
  * `GET /api/health`: High-level operational readiness, connected client counts, active sortie ID, and fault state.
  * `GET /api/state`: Instant snapshot of `UnifiedTelemetryState`.
  * `POST /api/control`: Dispatches `ControlCommand` payloads (throttle, altitude, OAT, region, fault activation).
  * `POST /api/debrief`: Triggers CBM post-flight debrief generation and exports markdown reports.
  * `GET /api/ai/status`: Reports GPU device info and local Qwen3-4B loading state (`NOT_LOADED`, `LOADING`, `READY`, `ERROR`).
  * `POST /api/ai/warmup`: Pre-loads Qwen3-4B weights into VRAM without waiting for fault onset.
  * `POST /api/ai/ask`: Free-text operator query dispatched via `asyncio.to_thread` to `MissionCopilot.ask`.
* **WebSocket Endpoints:**
  * `WS /ws/telemetry`: Bidirectional stream for Web / Mobile GCS clients.
  * `WS /ws/blender`: High-speed stream for Blender 3D CAD visualization client.

#### 📄 `backend/server/engine_service.py`
* **Purpose:** Central singleton maintaining the authoritative physical, analytical, and diagnostic state of the propulsion system at 50 Hz.
* **Key Components:**
  * `EngineStateService.get_instance()`: Thread-safe singleton accessor.
  * `_run_loop()` & `_tick(dt)`: Deterministic 50 Hz execution loop coordinating streamer updates, sensor validation, physics baseline, ML pipeline, prognostics, health indices, and state assembly.
  * `handle_command(cmd)`: Thread-safe command dispatcher handling `START_ENGINE`, `STOP_ENGINE`, `SET_FAULT`, `CLEAR_FAULT`, `SET_THROTTLE`, `SET_ALTITUDE`, `SET_OAT`, `SET_REGIME`, and `EXPORT_DEBRIEF`.
  * `_launch_ai_diagnosis(fault_id, directive, snapshot)`: Decoupled background thread launcher for Qwen3-4B causal reasoning.
  * `FAULT_TARGET_PARTS`: Dictionary mapping fault IDs 1..8 to specific Blender CAD component mesh names.

#### 📄 `backend/server/schemas.py`
* **Purpose:** Authoritative Pydantic data schemas and API contracts.
* **Key Models:**
  * `EngineTelemetry`: 27-parameter flight propulsion telemetry (RPM, CHT 1-4, EGT 1-4, Oil Press/Temp, Fuel Flow, MAP, Gearbox Vibration, Bus Voltage, Battery Current, Altitude, OAT, TAS, Phase, Theater).
  * `AnalyticsState`: 14 physics residuals, Autoencoder anomaly score, Random Forest fault diagnosis, confidence, target 3D meshes, ATA chapter, severity, root cause, prescriptive action, SOP checklist, RUL P10/P50 hours, sensor sanity report, early warning trend, dynamic subsystem health indices, and RAG/Qwen AI diagnosis state.
  * `UnifiedTelemetryState`: Single source of truth containing timestamp, sortie ID, engine state, telemetry, and analytics.
  * `ControlCommand`: Payload structure for operator control actions.

---

### 2.2. `backend/physics/` — 1D Thermodynamic Twin & Sensor Sanity

#### 📄 `backend/physics/thermo_model.py`
* **Purpose:** First-principles thermodynamic physics virtual shadow of the Rotax 912 iS Otto cycle engine.
* **Key Classes & Methods:**
  * `EnginePhysicalState`: Dataclass capturing raw kinematics, thermal state, fluid pressures, electrical, and environmental context.
  * `ResidualVector`: Normalized residual vector ($\Delta = \text{Actual} - \text{Expected}$) with composite Z-score anomaly calculation.
  * `RotaxThermoModel.get_ambient_properties(altitude_ft, oat_c)`: Calculates ambient pressure ($P_{\text{amb}}$), temperature ($K$), and air density ($\rho$) using ISA barometric formulas.
  * `compute_expected_state(...)`: Solves volumetric efficiency, air mass flow, target AFR, expected CHT distribution, EGT curve, oil temperature, and manifold pressure.
  * `compute_residuals(actual, expected)`: Calculates 14 channel residuals and composite normalized anomaly score ($0.0 \rightarrow 1.0$).

#### 📄 `backend/physics/sensor_validator.py`
* **Purpose:** Distinguishes genuine thermodynamic ramps from sensor hardware faults (broken leads, frozen ADC, EMI noise).
* **Key Components:**
  * `RATE_LIMITS`: Maximum physical rate-of-change thresholds per channel (e.g. CHT max 1.5°C/s vs. sensor spike > 10°C in 50ms).
  * `NOISE_FLOOR_VARIANCE`: Minimum variance thresholds across rolling 200-frame history to detect frozen ADCs.
  * `SensorSanityValidator.validate(curr_state, dt_sec)`: Emits `SanityReport` flagging invalid channels so downstream ML ignores sensor electrical artifacts.

---

### 2.3. `backend/telemetry/` — Streaming, Fault Injection & Fusion

#### 📄 `backend/telemetry/can_streamer.py`
* **Purpose:** Simulates continuous CAN / FADEC telemetry at 10–50 Hz with multi-theater ambient profiles (Ladakh / Thar), realistic sensor jitter, and dynamic progressive ramp fault injection for all 8 DRDO failure modes.
* **Key Components:**
  * `DRDO_FAULT_DEFINITIONS`: Authoritative metadata for canonical faults 0 through 8.
  * `TelemetryStreamer.set_fault(fault_id, severity, ramp_duration_sec)`: Injects fault mode with smooth linear/exponential ramp.
  * `generate_frame(t_sec, region)`: Produces synchronized `(actual_state, expected_state, residual_vector)`.

#### 📄 `backend/telemetry/rotax_dataset_generator.py` & `dataset_fusion_engine.py`
* **Purpose:** Generates multi-hour synthetic mission datasets and fuses external logs (Garmin G3X CSVs, NASA C-MAPSS prognostics data).
* **Parsers:** `garmin_parser.py`, `nasa_prognostics_parser.py`.

---

### 2.4. `backend/ml/` — Detection Pipeline, Models & Prognostics

#### 📄 `backend/ml/detection_pipeline.py`
* **Purpose:** Integrated 9-stage real-time inference pipeline executing in < 20ms at 20/50 Hz.
* **Stages:**
  1. *Stage 1:* Sensor Sanity Validation.
  2. *Stage 2:* 1D Physics Residual Calculation.
  3. *Stage 3:* Autoencoder Anomaly Scoring (L2 reconstruction loss).
  4. *Stage 4:* Gearbox FFT Spectral Analyser (3rd harmonic tracking).
  5. *Stage 5:* Channel Score Buffer Update.
  6. *Stage 6:* Fault Classification (Random Forest / Physics boundary fallback).
  7. *Stage 7:* Majority Vote Buffer (10 frames, 80% consensus threshold).
  8. *Stage 8:* Prognostics Summary Read.
  9. *Stage 9:* Structured `DiagnosticEvent` JSON emission with 30s alert suppression holdoff.

#### 📄 `backend/ml/anomaly_detector.py` (`ResidualAutoencoder`)
* Evaluates non-linear multi-sensor cross-channel correlation loss across the 14-dimensional residual vector.

#### 📄 `backend/ml/fault_classifier.py` (`RotaxFaultClassifier`)
* Random Forest model (100 estimators) mapping 14 residual features to Fault IDs 0..8 with confidence probabilities.

#### 📄 `backend/ml/spectral_analyser.py` (`GearboxSpectralAnalyser`)
* Sliding-window DFT tracking 3rd harmonic propeller shaft resonance ($3 \times \text{Prop RPM} \approx 103\text{ Hz}$) to detect reduction gear dog-clutch tooth micro-pitting.

#### 📄 `backend/ml/trend_analyser.py` (`ScoreBuffer`, `PrognosticsWorker`)
* Dedicated background thread running every 10–20 seconds. Fits Linear, Exponential, and Power-Law models using Akaike Information Criterion (AIC) to detect sub-threshold drift and compute Monte Carlo Remaining Useful Life (RUL P10/P50).

---

### 2.5. `backend/agent/` — Diagnostic XAI, LLM Engine & Mission Copilot

#### 📄 `backend/agent/diagnostic_agent.py`
* **Purpose:** Deterministic Explainable AI (XAI) engine mapping diagnosed fault IDs to authoritative ATA chapter directives, root-cause explanations, physical causal propagation chains, and emergency SOP checklists.
* **Directives:** ATA 72-00 (Engine Core), ATA 73-10 (Fuel Injection), ATA 74-20 (Ignition), ATA 79-00 (Lubrication), ATA 72-10 (Reduction Gearbox), ATA 78-00 (Exhaust), ATA 24-00 (Electrical Power), ATA 73-20 (Dual FADEC).

#### 📄 `backend/agent/llm_engine.py` (`LocalQwenEngine`)
* **Purpose:** Singleton wrapper for local 4-bit NF4-quantized Qwen3-4B causal language model using BitsAndBytes on CUDA GPUs (RTX 4050/3060 Laptop GPUs, ~2.5 GB VRAM).
* **Key Features:** Lazy loading on first use, soft failure recovery (never crashes backend), thread-serialized blocking inference, disabled thinking preamble for fast tactical generation.

#### 📄 `backend/agent/copilot.py` (`MissionCopilot`)
* **Purpose:** Conversational Mission Copilot and tactical assistant.
* **Key Features:**
  * *Defense Safety Guardrails:* Rejects jailbreaks, off-topic prompts, and unsafe flight directives (e.g. "shut down engine mid-air").
  * *Dual-Branch Synthesis:* Generates answers via local Qwen3-4B (if available) or fast deterministic conversational RAG synthesis.
  * *`diagnose_with_ai(...)`:* Synthesizes RAG manual excerpts strictly over the deterministic causal chain to eliminate hallucinations.

---

### 2.6. `backend/knowledge/` — Air-Gapped Document Ingestion & RAG

#### 📄 `backend/knowledge/loaders/`
* `pdf_loader.py` (PyPDF / pypdf), `office_loader.py` (python-docx / python-pptx), `text_loader.py`, `chunker.py` (sliding window token chunking with overlap).

#### 📄 `backend/knowledge/retrieval/`
* `local_store.py` (`LocalKnowledgeStore`): Ingests 21 DRDO and Rotax manuals from `data/documents/`.
* `reranker.py` & `embedding_index.py`: Multi-tier semantic search using SentenceTransformers (`all-MiniLM-L6-v2`), FlashRank local ONNX cross-encoder, and deterministic lexical overlap fallback.

---

### 2.7. `backend/graph/` — CBM Mission Knowledge Graph & Reporter

#### 📄 `backend/graph/mission_graph.py` (`MissionKnowledgeGraph`)
* In-memory property graph modeling Sorties, Engine Subsystems, Anomaly Events, and Maintenance Action work orders.

#### 📄 `backend/graph/mission_reporter.py` (`MissionReporter`)
* Generates standardized post-flight engineering debrief documents (`data/mission_reports/SORTIE-xxx.md`) with YAML frontmatter.

---

## 3. Inter-Module Dependency & Communication Matrix

```
┌───────────────────────────┬────────────────────────────────────────────────────────────────────────────┐
│ Module                    │ Depends On / Imports From                                                  │
├───────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
│ server.main               │ server.engine_service, server.schemas, agent.llm_engine                    │
│ server.engine_service     │ physics.thermo_model, physics.sensor_validator, telemetry.can_streamer,    │
│                           │ ml.detection_pipeline, ml.trend_analyser, agent.diagnostic_agent,          │
│                           │ agent.copilot, graph.mission_graph, graph.mission_reporter, server.schemas │
│ ml.detection_pipeline     │ physics.thermo_model, physics.sensor_validator, ml.anomaly_detector,      │
│                           │ ml.spectral_analyser, ml.trend_analyser, agent.diagnostic_agent           │
│ agent.copilot             │ agent.diagnostic_agent, agent.llm_engine, knowledge.retrieval.local_store, │
│                           │ graph.mission_graph                                                        │
│ knowledge.retrieval       │ knowledge.loaders.chunker, knowledge.loaders.pdf_loader/office_loader      │
│ graph.mission_reporter    │ graph.mission_graph                                                        │
└───────────────────────────┴────────────────────────────────────────────────────────────────────────────┘
```
