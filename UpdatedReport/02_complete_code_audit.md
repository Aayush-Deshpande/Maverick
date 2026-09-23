# 02 — Complete Codebase Audit & Functional Verification

**Scope:** Entire repository (`backend/`, `frontend/`, `apps/`, `web/`, `assets/`, `scripts/`, `tests/`, `data/`)  
**Method:** Static code analysis + runtime test verification + model artifact inspection  
**Classification Taxonomy:**  
* **REAL:** Actually implemented, mathematically sound, and integrated end-to-end.  
* **PARTIAL:** Core logic exists, but edge cases, full parameterization, or system integration is incomplete.  
* **SIMULATED:** Functioning physics-based or data-driven synthetic simulation based on technical formulas.  
* **MOCKED:** Returns fabricated dummy objects or static responses purely to fulfill an API contract.  
* **HARDCODED:** Fixed scalar constants or deterministic formulas substituted for real computational processing.  
* **UI-ONLY:** Frontend visual elements that suggest capabilities with no supporting backend implementation.  
* **PLACEHOLDER:** Stubs or docstrings created to reserve architectural namespace without functioning code.  
* **BROKEN:** Code exists in runtime path but fails during execution due to bugs, syntax, or missing dependencies.  
* **EXPERIMENTAL:** Standalone research scripts, Jupyter notebooks, or offline prototypes not integrated into production.  

---

## 1. Comprehensive Subsystem Audit & Classification Table

| Subsystem / Component | Path & Line References | Classification | Technical Functionality & Implementation Reality | Evidence & Ground Truth Findings |
| :--- | :--- | :--- | :--- | :--- |
| **FastAPI REST Server** | [`backend/server/main.py:102-567`](file:///d:/Programming/PS054/backend/server/main.py#L102-L567) | **REAL** | Exposes 21 REST endpoints + 2 WebSockets; lifespan context manager; CORS middleware; thread-safe offloading. | Endpoints tested and responsive; `/api/health`, `/api/state`, `/api/control`, `/api/cbm/*` pass automated test suite. |
| **Telemetry WebSocket** | [`backend/server/main.py:499-530`](file:///d:/Programming/PS054/backend/server/main.py#L499-L530) | **REAL** | 20 Hz bidirectional WebSocket streaming JSON-serialized `UnifiedTelemetryState` to web clients; accepts incoming JSON control commands. | `broadcast_telemetry_loop()` ticks at 50 ms intervals; drops disconnected clients cleanly. |
| **Blender WebSocket** | [`backend/server/main.py:531-563`](file:///d:/Programming/PS054/backend/server/main.py#L531-L563) | **REAL** | Dedicated 20 Hz WebSocket feeding 3D Blender client; parses client heartbeats and commands. | Connects to `standalone_digital_twin_app.py`; drives material shaders in real time. |
| **Authoritative State Engine** | [`backend/server/engine_service.py:98-783`](file:///d:/Programming/PS054/backend/server/engine_service.py#L98-L783) | **REAL** | Singleton engine service running 20 Hz deterministic tick thread; coordinates physics, ML detection, prognostics, and graph logging under `state_lock`. | Central coordinator of the entire backend; 783 lines of fully functional orchestrator code. |
| **1D Thermodynamic Model** | [`backend/physics/thermo_model.py:117-407`](file:///d:/Programming/PS054/backend/physics/thermo_model.py#L117-L407) | **REAL / SIMULATED** | Solves 1D thermodynamic equations for Otto cycle: ISA pressure lapse, air mass flow, target AFR, CHT convection equilibrium, oil pressure curves, BSFC, and thermal efficiency. | First-principles equations based on Rotax 912 iS geometry (1352cc, 84mm bore, 61mm stroke). Produces 27 physical state channels. |
| **Physics Residual Calculator** | [`backend/physics/thermo_model.py:328-406`](file:///d:/Programming/PS054/backend/physics/thermo_model.py#L328-L406) | **REAL** | Computes 14-channel normalized delta vector: $\Delta = \text{Actual} - \text{Expected}$; computes composite Z-score and exponential anomaly score. | Evaluates $\text{score} = 1.0 - \exp(-0.45 \cdot Z_{\text{comp}})$. Healthy baseline exhibits systematic +9.75°C oil temp residual offset. |
| **Sensor Sanity Validator** | [`backend/physics/sensor_validator.py:110-258`](file:///d:/Programming/PS054/backend/physics/sensor_validator.py#L110-L258) | **REAL** | 4-stage validation: physical range checks, frozen ADC detection (rolling variance), rate-of-change limits, and cross-sensor thermal triad validation. | Prevents bad sensor data from falsely triggering mechanical engine fault alarms; returns `SanityReport`. |
| **Residual Autoencoder** | [`backend/ml/anomaly_detector.py:73-145`](file:///d:/Programming/PS054/backend/ml/anomaly_detector.py#L73-L145) | **REAL** | 14-8-4-8-14 fully connected neural network written in pure NumPy with tanh activations. Reconstructs residual vectors to compute unsupervised reconstruction loss. | Production weights committed in `rotax_autoencoder.json` (9,733 bytes); threshold calibrated at 0.0978 on validation data; achieves 94.3% nominal accuracy on held-out test missions. |
| **Random Forest Classifier** | [`backend/ml/fault_classifier.py:49-140`](file:///d:/Programming/PS054/backend/ml/fault_classifier.py#L49-L140) | **REAL / BROKEN (Silent Fallback)** | 100-tree scikit-learn classifier trained to isolate 8 canonical DRDO failure modes from 14 residual features. | Serialized model exists on disk (`rotax_random_forest.joblib`, 2.14 MB). If `scikit-learn` or `joblib` is missing, it catches `Exception` silently and falls back to heuristic rule thresholds without warning the operator. |
| **Detection Pipeline** | [`backend/ml/detection_pipeline.py:176-610`](file:///d:/Programming/PS054/backend/ml/detection_pipeline.py#L176-L610) | **REAL** | 9-stage real-time analytical pipeline ticking at 20 Hz (< 20 ms per frame): Sensor Sanity → Physics Residuals → AE Anomaly Score → Gearbox FFT → Score Buffer → Fault Isolation → Majority Vote → Trend Summary → JSON Event Emit. | Tightly integrated; gates expensive RF classification behind `ANOMALY_GATE = 0.35`; suppresses duplicate alerts with 30s holdoff. |
| **Spectral Analyser** | [`backend/ml/spectral_analyser.py:100-210`](file:///d:/Programming/PS054/backend/ml/spectral_analyser.py#L100-L210) | **PARTIAL** | Computes gearbox 3rd harmonic ratio ($3 \times f_{\text{prop}}$); self-timed 1.0s FFT window; envelope analysis. | Fully Nyquist-aware: recognizes 20 Hz sample rate aliases frequencies > 10 Hz and cleanly falls back to RMS envelope tracking. 2 kHz burst path is simulated in software. |
| **Degradation Trend Analyser** | [`backend/ml/trend_analyser.py:170-445`](file:///d:/Programming/PS054/backend/ml/trend_analyser.py#L170-L445) | **REAL** | Fits linear ($y = a + bt$), exponential ($y = a e^{bt}$), and power-law ($y = a t^b$) curves to rolling residual history. Selects optimal curve via Akaike Information Criterion (AIC). Solves Time-to-Breach via binary search. | Fully operational pure-Python math; computes drift rates per minute; warns of sub-threshold degradation hours in advance. |
| **Probabilistic RUL Estimator** | [`backend/ml/trend_analyser.py:447-545`](file:///d:/Programming/PS054/backend/ml/trend_analyser.py#L447-L545) | **REAL** | 500-sample Monte Carlo perturbation of fitted degradation slope and intercept based on parameter covariance and $R^2$; outputs empirical p10, p50, p90 remaining flight hours. | Live operational path backing `go_no_go` pre-flight advisory. True probabilistic interval generation. |
| **Secondary RUL Countdown** | [`backend/ml/rul_estimator.py:29-164`](file:///d:/Programming/PS054/backend/ml/rul_estimator.py#L29-L164) | **HARDCODED / DEAD CODE** | Decrements fixed initial lifetimes (e.g., Cylinder Head: 450h, Gearbox: 500h) using instantaneous Arrhenius thermal multipliers and cubic vibration powers. Pseudo-conformal RUL calculated by multiplying $p50 \times (\pm 12\%)$. | Exported from `backend/ml/__init__.py`; called in `engine_service.py` only for `conformal_rul` payload dictionary; fundamentally contradicts `trend_analyser.py` Monte Carlo RUL. |
| **CAN Telemetry Streamer** | [`backend/telemetry/can_streamer.py:75-513`](file:///d:/Programming/PS054/backend/telemetry/can_streamer.py#L75-L513) | **SIMULATED** | Autonomous 20 Hz plant simulation with decoupled differential ODE lags (thermal time constants $\tau = 6.0\,\text{s}$, throttle $\tau = 0.3\,\text{s}$). Injects 8 DRDO canonical faults with progressive onset ramps (8s). | Highly sophisticated dynamic simulator; generates realistic sensor noise and multi-regime environments (Ladakh high altitude, Thar desert heat). |
| **Rotax Dataset Generator** | [`backend/telemetry/rotax_dataset_generator.py:40-390`](file:///d:/Programming/PS054/backend/telemetry/rotax_dataset_generator.py#L40-L390) | **SIMULATED** | Generates 3-way partitioned datasets (10 train, 10 val, 10 test missions = 30 missions total) with mission-level group isolation, differing random seeds, and severe gust/thermal offsets. | Outputs CSVs with 27 sensor columns + 14 pre-computed residual columns + `FAULT_ID`. Injects faults via closed-form arithmetic deltas (`if fault_id == 1: CHT_2 += 42 * severity`). |
| **Dataset Fusion Engine** | [`backend/telemetry/dataset_fusion_engine.py:35-260`](file:///d:/Programming/PS054/backend/telemetry/dataset_fusion_engine.py#L35-L260) | **PARTIAL / MOCKED** | Ingests NASA C-MAPSS turbofan run-to-failure cycles and maps them to Rotax schema. Attempts to merge real Garmin G3X flight logs from `source1_avionics_logs/`. | NASA benchmark ingested into `fused_master/`; however, `source1_avionics_logs/` does not exist on disk (`source1_garmin_files: 0`). 100% of data is synthetic. |
| **Mission Replay Engine** | [`backend/telemetry/replay_engine.py:34-118`](file:///d:/Programming/PS054/backend/telemetry/replay_engine.py#L34-L118) | **REAL** | Scans and indexes `data/telemetry/live_sorties/*.csv`; provides manifest metadata and random-access seeking (`/api/replay/{id}/frame?time_sec=X`). | Fully functional backend replay; allows UI scrubber to step frame-by-frame through recorded missions. |
| **Diagnostic Agent (ATA Chapter)** | [`backend/agent/diagnostic_agent.py:18-120`](file:///d:/Programming/PS054/backend/agent/diagnostic_agent.py#L18-L120) | **REAL** | Maps detected fault IDs to standard civil/military ATA chapters (ATA 72-00, 73-10, 74-10, 79-20, 80-10); generates emergency checklists, root causes, and CBM maintenance orders. | Deterministic expert system providing military-grade prescriptive action directives; zero LLM dependency for flight safety. |
| **Mission Copilot (RAG + Qwen)** | [`backend/agent/copilot.py:23-450`](file:///d:/Programming/PS054/backend/agent/copilot.py#L23-L450) | **REAL** | Conversational AI copilot utilizing local Qwen3-4B GGUF LLM and local vector knowledge base (21 technical manuals). Provides voice and text mission advisory with guardrails. | Real RAG engine; embeds manuals using sentence-transformers; synthesizes answers grounded in live telemetry snapshot. |
| **Voice Interface (STT / TTS)** | [`backend/voice/`](file:///d:/Programming/PS054/backend/voice) | **REAL** | Local Whisper.cpp speech-to-text + Local Kokoro text-to-speech engine. Spoken dialogue loop with operator. | Fully functional local offline voice processing; streams intermediate thinking tokens to `/api/voice/thinking/{session_id}`. |
| **Mission Knowledge Graph** | [`backend/graph/mission_graph.py:50-380`](file:///d:/Programming/PS054/backend/graph/mission_graph.py#L50-L380) | **REAL** | NetworkX/dict-based knowledge graph storing Sortie nodes, Anomaly events, and Maintenance work orders. Persists fleet wear across server restarts to `data/graph_db/fleet_graph.json`. | Multi-sortie CBM memory; tracks cross-theater degradation (Ladakh vs. Thar Desert wear statistics); supports inspector sign-offs. |
| **Mission Debrief Generator** | [`backend/reports/mission_bundle.py:50-350`](file:///d:/Programming/PS054/backend/reports/mission_bundle.py#L50-L350) | **REAL** | Generates complete post-flight mission bundle containing `mission.json`, reading CSVs, health traces, anomaly timelines, and CBM work orders in `report_dump/mission_XXX/`. | 60 historical mission bundles generated on disk; fully populated with genuine telemetry metrics. |
| **React Web GCS Dashboard** | [`frontend/src/`](file:///d:/Programming/PS054/frontend/src) | **REAL** | Production Vite + React + Tailwind glass-cockpit dashboard: gauges, strip charts, diagnostic cards, voice assistant, CBM portal, and replay scrubber. | Connects to `ws://127.0.0.1:8000/ws/telemetry`; responsive and robust; complete operator interface. |
| **Anumaan 3D Web Portal** | [`web/site/`](file:///d:/Programming/PS054/web/site) | **REAL / PARTIAL** | 8-tab tactical web showcase using Three.js and OrbitControls: 18-scene mission film runway, GCS dashboard view, 6-layer architecture, and simulation overview. | Rich, stunning visual design; Three.js engine turntable viewer; some telemetry strips run off pre-canned nominal values. |
| **Blender 3D CAD Twin Client** | [`apps/blender_twin/standalone_digital_twin_app.py:1-1406`](file:///d:/Programming/PS054/apps/blender_twin/standalone_digital_twin_app.py) | **REAL** | Standalone Blender application subscribing to `ws://127.0.0.1:8000/ws/blender`. Frames components in 3D CAD (`rotax_912_is_sport.blend`) and swaps shaders to red pulsing emission upon fault detection. | 1,406 lines of immediate-mode GPU shader and camera code; maps 109 individual CAD parts to the 8 DRDO fault modes. |
| **Canyon Flight Simulator** | [`apps/blender_twin/standalone_canyon_flight_app.py:1-2367`](file:///d:/Programming/PS054/apps/blender_twin/standalone_canyon_flight_app.py) | **REAL / SIMULATED** | Full 3D aerodynamic UAV flight simulator inside Blender over a 52 MB Copernicus DSM DEM terrain of Ladakh canyon. Features Auto-GCAS, terrain proximity probing, chase camera, and flight intent polling. | 2,367 lines of Python kinematics; records flight telemetry directly to `report_dump/`; reads tactical commands from `runtime/flight_intent_command.json`. |
| **Mission Graph 3D Explorer** | [`apps/mission_graph_viewer/standalone_mission_graph_app.py:1-1152`](file:///d:/Programming/PS054/apps/mission_graph_viewer/standalone_mission_graph_app.py) | **REAL** | Native Blender application rendering `report_dump/` missions as a 3D glowing molecular node graph. Expanding a node reveals child reports (timeline, health, predictions) rendered directly in the 3D viewport. | 1,152 lines of immediate-mode GPU batch drawing; runs at 143 FPS; scans real disk folders dynamically. |
| **Desktop Pygame GCS** | [`apps/desktop_gcs/standalone_gui_app.py:1-522`](file:///d:/Programming/PS054/apps/desktop_gcs/standalone_gui_app.py) | **HARDCODED / DISCONNECTED** | Pygame desktop window rendering 120 pre-rendered EEVEE JPG turntable frames (`frame_000.jpg` to `frame_119.jpg`). Hardcoded telemetry values (`'rpm': 5120, 'cht': 148.6`). | Zero backend connection; does not call FastAPI or WebSockets; purely a static offline demonstration tool. |

---

## 2. Deep Investigation of Hardcoded, Fake, or Circular Logic

To ensure absolute credibility during DRDO technical scrutiny, every instance of synthetic, hardcoded, or circular logic in the codebase has been identified and documented below:

### 2.1 The Training Data Circularity Loop
```
backend/physics/thermo_model.py (RotaxThermoModel)
   ├── imported by rotax_dataset_generator.py:19 ──> Generates "actual" telemetry values
   ├── imported by can_streamer.py:14            ──> In-flight live streamer plant
   └── used at inference in detection_pipeline.py ──> Computes "expected" baseline values
```
* **The Finding:** The machine learning models (Residual Autoencoder and Random Forest) are trained on dataset CSVs generated by `RotaxTimeSeriesGenerator`. This generator imports the exact same `RotaxThermoModel` used by the runtime inference engine to compute expected states.
* **Impact:** The residuals ($RES\_d = Actual - Expected$) in the training data are pre-calculated by taking the difference between `RotaxThermoModel` plus an arithmetic offset and `RotaxThermoModel`. The machine learning models are essentially learning to invert closed-form arithmetic deltas created by the same software module.
* **Defence Posture:** This must be presented as a **physics-in-the-loop verification prototype**, proving that the multi-stage analytical pipeline is leak-free and mathematically separable. It must not be claimed as empirical proof of diagnostic accuracy on an actual physical Rotax engine.

### 2.2 Arithmetic Fault Injection Ladder
In [`backend/telemetry/rotax_dataset_generator.py:159-221`](file:///d:/Programming/PS054/backend/telemetry/rotax_dataset_generator.py#L159-L221) and [`backend/telemetry/can_streamer.py:371-450`](file:///d:/Programming/PS054/backend/telemetry/can_streamer.py#L371-L450):
```python
if self.active_fault_id == 1:
    temp_rise = 40.0 * ramp
    actual_state.CHT_2 = round(actual_state.CHT_2 + temp_rise, 2)
    actual_state.OIL_TEMP = round(actual_state.OIL_TEMP + (10.5 * ramp), 2)
    actual_state.EGT_2 = round(actual_state.EGT_2 + (24.0 * ramp), 2)
    actual_state.HEALTH_INDEX = round(max(0.2, 1.0 - 0.75 * ramp), 2)
    actual_state.RUL_HOURS = round(max(1.5, 500.0 - 480.0 * ramp), 1)
```
* **The Finding:** Faults are injected by adding direct scalar constants to specific sensor channels. Notice that `HEALTH_INDEX` and `RUL_HOURS` are also directly overwritten with hardcoded linear decay equations inside the streamer.
* **Why it matters:** In a live demo, if someone reads `actual_state.RUL_HOURS`, they are seeing a hardcoded formula (`500.0 - 480.0 * ramp`), NOT the output of the Monte Carlo RUL estimator. Fortunately, the authoritative API (`EngineStateService`) reads `self.prognostics.latest_report` for its analytical payload, but the presence of hardcoded RUL inside `actual_state` creates confusion and vulnerability under code review.

### 2.3 The Dead/Contradictory RUL Countdown Module
[`backend/ml/rul_estimator.py`](file:///d:/Programming/PS054/backend/ml/rul_estimator.py) (209 lines):
```python
self.component_rul = {
    "Cylinder_Head_Assembly": 450.0,
    "Fuel_Injection_Rail": 600.0,
    "Ignition_Harness_Coils": 400.0,
    ...
}
```
* **The Finding:** This file implements an empirical countdown model from fixed base hours using Arrhenius and cubic vibration multipliers. It also provides `get_conformal_rul()` which claims *"90% Conformal Calibration"* but simply calculates:
  $$\text{delta} = p50 \times (0.12 + 0.18 \times \text{anomaly\_score})$$
  $$\text{p10} = p50 - \text{delta}, \quad \text{p90} = p50 + \text{delta}$$
* **Impact:** There is no non-conformity score quantile calculation or calibration set. It is an arbitrary percentage bracket. Meanwhile, `trend_analyser.py` runs a legitimate 500-sample Monte Carlo extrapolation. Having two contradictory RUL modules in the codebase undermines technical credibility.

### 2.4 Missing Garmin Real Flight Logs
In `data/telemetry/fused_master/dataset_manifest.json`:
```json
"source1_garmin_files": 0,
"source1_total_rows": 0,
"source2_nasa_cmapss_rows": 2136,
"source3_drdo_synthetic_rows": 7600
```
* **The Finding:** While the documentation refers to a "Tri-Source Dataset Fusion Engine", the Garmin flight logs directory (`source1_avionics_logs/`) does not exist on disk. Furthermore, the trained Random Forest and Autoencoder models on disk were trained purely on `rotax912_train_dataset.csv`, which ignored the fused dataset entirely. 100% of the training data utilized by the active models is synthetic.

---

## 3. Concurrency Bug & Test Suite Deep Dive

Execution of the automated test suite revealed a critical threading race condition in the production backend:

### Bug Trace: `RuntimeError: deque mutated during iteration`
* **Location:** [`backend/ml/detection_pipeline.py:156`](file:///d:/Programming/PS054/backend/ml/detection_pipeline.py#L156) in `MajorityVoteBuffer.update()`
* **Mechanism:**
  1. When `EngineStateService()` is instantiated, line 217 immediately starts `self.worker_thread = threading.Thread(target=self._run_loop, daemon=True)`.
  2. This background worker thread continuously calls `self._tick(dt)` at 20 Hz, which in turn calls `self.pipeline.process_frame()` $\to$ `self._vote.update(fault_id)`.
  3. When an automated test (such as [`tests/test_fun_req_compliance.py:256`](file:///d:/Programming/PS054/tests/test_fun_req_compliance.py#L256)) creates an `EngineStateService` instance and directly calls `service._tick(0.05)` in the main test thread, **two concurrent threads are calling `_tick()` on the exact same pipeline instance**.
  4. In `MajorityVoteBuffer.update()`, one thread executes `self._buf.append(fault_id)` while the other thread executes `for fid in self._buf:`, causing Python's `collections.deque` to raise `RuntimeError: deque mutated during iteration`.
* **Fix:** Lock `_tick()` execution or protect `MajorityVoteBuffer` internal deque access with a mutex:
  ```python
  with self._lock:
      self._buf.append(fault_id)
      counts = collections.Counter(self._buf)
  ```

---

## 4. Summary Classification of Core Modules

| Module / Script | Lines of Code | Status | Integration Level | Primary Deficiency |
| :--- | :--- | :--- | :--- | :--- |
| `backend/server/main.py` | 567 | **REAL** | High | None (solid FastAPI implementation). |
| `backend/server/engine_service.py` | 783 | **REAL** | High | Concurrency race when ticked externally. |
| `backend/physics/thermo_model.py` | 419 | **REAL** | High | Healthy engine oil temp residual offset (+9.75°C). |
| `backend/physics/sensor_validator.py` | 382 | **REAL** | High | Cross-sensor checks asymmetric across cylinders. |
| `backend/ml/detection_pipeline.py` | 727 | **REAL** | High | Thread-safety in `MajorityVoteBuffer`. |
| `backend/ml/trend_analyser.py` | 756 | **REAL** | High | 6-minute history buffer vs. 30-minute requirement. |
| `backend/ml/rul_estimator.py` | 209 | **DEAD CODE** | Low | Arbitrary linear countdown; pseudo-conformal math. |
| `backend/agent/copilot.py` | 1,191 | **REAL** | High | Heavy GPU load on startup; requires local LLM. |
| `apps/blender_twin/standalone_canyon_flight_app.py` | 2,367 | **REAL** | Standalone / File Queue | Runs in Blender; communicates via file queue. |
| `apps/blender_twin/standalone_digital_twin_app.py` | 1,406 | **REAL** | High (WebSocket) | Batch file points to wrong file path in root. |
| `apps/desktop_gcs/standalone_gui_app.py` | 522 | **HARDCODED** | Disconnected | Completely isolated; hardcoded static frames. |
| `frontend/src/` | ~6,500 | **REAL** | High (WebSocket/REST) | Fully functional modern React GCS. |
