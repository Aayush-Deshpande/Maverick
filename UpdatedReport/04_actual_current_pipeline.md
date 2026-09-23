# 04 — Actual Current Data Pipeline & Real-Time Flow Reconstruction

**Scope:** The exact step-by-step execution path of every telemetry frame through the active codebase.  
**Telemetry Frequency:** 20 Hz (50.0 ms nominal frame budget)  
**Authoritative Ingestion Coordinator:** [`backend/server/engine_service.py`](file:///d:/Programming/PS054/backend/server/engine_service.py)  
**Analytical Pipeline:** [`backend/ml/detection_pipeline.py`](file:///d:/Programming/PS054/backend/ml/detection_pipeline.py)  

---

## 1. End-to-End Pipeline Stage-by-Stage Architecture

The diagram below maps the **actual operational pipeline** running in code today, explicitly annotating the modules, data structures, and timing at each stage:

```
[STAGE 1: GENERATION / PLANT SIMULATION]
backend/telemetry/can_streamer.py (TelemetryStreamer.generate_frame)
  │  • Solves decoupled 1st-order ODE lags (RPM, MAP, CHT, EGT, Oil Press, Oil Temp)
  │  • Adds Gaussian sensor jitter (e.g. CHT σ=0.18°C, EGT σ=1.2°C, RPM σ=10 RPM)
  │  • Injects active DRDO fault dynamics (1..8) with 8.0s progressive ramp
  │  • Synthesizes 256-sample 2 kHz vibration burst buffer
  ▼  Outputs: actual (EnginePhysicalState), expected (EnginePhysicalState), residuals (ResidualVector)
     Latency: ~0.85 ms

[STAGE 2: SYNCHRONIZATION & AMBIENT DERATING]
backend/physics/thermo_model.py (RotaxThermoModel.compute_expected_state)
  │  • Takes actual altitude_ft, oat_c, tps, tas_knots, flight_phase
  │  • Evaluates ISA barometric pressure lapse & air density derating: ρ(h, OAT)
  │  • Solves 1D thermodynamic equilibrium for target AFR, volumetric efficiency,
  │    convective cooling balance, and nominal oil/fuel pressure curves
  ▼  Outputs: theoretical expected (EnginePhysicalState)
     Latency: ~0.42 ms

[STAGE 3: RESIDUAL VECTOR CALCULATION]
backend/physics/thermo_model.py (RotaxThermoModel.compute_residuals)
  │  • Computes raw arithmetic deltas: d_X = actual.X - expected.X
  │  • Normalizes across 14 channels into Z-scores: z_i = |d_X_i| / σ_i
  │  • Computes composite score: Z_comp = 0.65 · max(z) + 0.35 · rms(z)
  │  • Evaluates non-linear anomaly index: score = 1.0 - exp(-0.45 · Z_comp)
  ▼  Outputs: ResidualVector (14 deltas, anomaly_score, is_anomaly)
     Latency: ~0.15 ms

[STAGE 4: SENSOR SANITY & SHIELDING]
backend/physics/sensor_validator.py (SensorSanityValidator.validate)
  │  • Step 4a: Range Validation (hard physical limits, e.g. CHT < 180°C, Oil P < 8 bar)
  │  • Step 4b: Frozen ADC Check (rolling variance across last 20 frames < 1e-4)
  │  • Step 4c: Rate-of-Change Limit (checks |dX/dt| against physical slew thresholds)
  │  • Step 4d: Cross-Sensor Parity Check (CHT_2 / OIL_TEMP / EGT_2 triad)
  │  • Step 4e: Residual Shielding (zeros out residuals for failed channels)
  ▼  Outputs: SanityReport (all_sensors_valid, failed_channels, suppressed_anomaly)
     Latency: ~0.18 ms

[STAGE 5: DUAL-PATH ANOMALY DETECTION]
backend/ml/detection_pipeline.py (DetectionPipeline.process_frame)
  │  • Path A (Learned): 14-8-4-8-14 ResidualAutoencoder scores reconstruction error
  │  • Path B (Spectral): GearboxSpectralAnalyser computes 3rd harmonic ratio
  │  • Composite Score Fusion: composite_score = max(AE_score, physics_Z_score)
  │  • Blends gearbox vibration peak if elevated: max(composite, spectral · 0.8)
  ▼  Outputs: composite_score, channel_scores dict
     Latency: ~1.45 ms

[STAGE 6: HISTORICAL SCORE BUFFERING]
backend/ml/trend_analyser.py (ScoreBuffer.append)
  │  • Pushes (now, composite_score, channel_scores) into ScoreBuffer(maxlen=7200)
  │  • Thread-safe circular buffer representing rolling 6.0-minute history at 20 Hz
  ▼  Outputs: In-memory sliding window for background prognostics worker
     Latency: ~0.04 ms

[STAGE 7: GATED FAULT ISOLATION (CLASSIFIER)]
backend/ml/detection_pipeline.py (DetectionPipeline._classify)
  │  • Gating: Runs ONLY if composite_score > ANOMALY_GATE (0.35)
  │  • Primary Path: 100-tree Random Forest (`rotax_random_forest.joblib`)
  │  • Fallback Path: Physics boundary heuristic rules with sigmoid confidence
  │  • Gating Check: Accepts prediction only if confidence ≥ 0.55
  ▼  Outputs: fault_id (0..8), confidence (0.0..1.0)
     Latency: ~3.10 ms (when active), 0.01 ms (when nominal)

[STAGE 8: MAJORITY VOTE SMOOTHING]
backend/ml/detection_pipeline.py (MajorityVoteBuffer.update)
  │  • Buffers predictions over a 10-frame window (500 ms at 20 Hz)
  │  • Requires ≥ 80% consensus (8/10 frames) to confirm fault transition
  │  • Prevents transient false alarms from noise spikes
  ▼  Outputs: confirmed_fault_id (0..8)
     Latency: ~0.02 ms

[STAGE 9: ASYNCHRONOUS PROGNOSTICS & RUL]
backend/ml/trend_analyser.py (PrognosticsWorker / ProbabilisticRULEstimator)
  │  • Runs in separate daemon thread every 20 seconds
  │  • Fits Linear, Exponential, and Power-Law models to buffer history
  │  • Computes SSE and selects optimal curve via Akaike Information Criterion (AIC)
  │  • Solves Time-to-Threshold via binary search over future 480 minutes
  │  • 500-sample Monte Carlo perturbation produces p10, p50, p90 RUL hours
  ▼  Outputs: TrendReport, RULEstimate, MissionGoNoGoAdvisory
     Latency: ~8.50 ms (executed asynchronously on background thread)

[STAGE 10: ATA REASONING & KNOWLEDGE GRAPH LOGGING]
backend/agent/diagnostic_agent.py & backend/graph/mission_graph.py
  │  • Maps confirmed fault to ATA Chapter (72, 73, 74, 79, 80)
  │  • Edge-triggered (logs once on fault onset, not every 20 Hz tick):
  │    - Records AnomalyEventNode in MissionKnowledgeGraph
  │    - Generates MaintenanceActionNode with RUL p10/p50 hours
  │    - Fires background daemon thread for Local Qwen3-4B LLM diagnosis
  ▼  Outputs: DiagnosticDirective, updated fleet_graph.json
     Latency: ~0.35 ms (LLM runs decoupled on background thread)

[STAGE 11: UNIFIED STATE AGGREGATION & BROADCAST]
backend/server/main.py (broadcast_telemetry_loop)
  │  • Assembles EngineTelemetry + AnalyticsState into UnifiedTelemetryState
  │  • Serializes to JSON via Pydantic model_dump_json()
  │  • Broadcasts across active_web_sockets (GCS) and active_blender_sockets (3D CAD)
  │  • Writes telemetry row to disk CSV at ~2 Hz (every 10th tick)
  ▼  Outputs: Network frames to Web & Blender clients, live_sorties/<id>.csv
     Latency: ~1.20 ms
```

---

## 2. Quantitative Pipeline Characteristics Matrix

The table below provides the quantitative engineering characteristics for every stage in the operational pipeline:

| Stage # | Pipeline Stage | Primary Technology & Module | Input Data & Shape | Output Data & Format | Underlying Algorithm | Latency (Typical) | Memory & Storage Destination |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **01** | **Plant Simulator** | Python / NumPy (`can_streamer.py`) | Environmental inputs: altitude, OAT, throttle, fault command. | `actual_state` (27 scalars) + 2 kHz vib buffer. | 1st-order differential ODEs ($\tau = 0.3 - 6.0\,\text{s}$) + Gaussian noise. | $0.85\,\text{ms}$ | Process RAM (`TelemetryStreamer`). |
| **02** | **Observer Twin** | 1D Physics (`thermo_model.py`) | Altitude (ft), OAT (°C), RPM, TPS, TAS (kts). | `expected_state` (27 nominal scalars). | ISA barometric lapse + Otto thermodynamic equilibrium equations. | $0.42\,\text{ms}$ | Process RAM (`EnginePhysicalState`). |
| **03** | **Residual Vector** | Normalized Delta Math (`thermo_model.py`) | `actual_state` and `expected_state`. | `ResidualVector` (14 deltas, anomaly score). | $z_i = \|d_i\| / \sigma_i$; exponential composite score: $1 - e^{-0.45 Z}$. | $0.15\,\text{ms}$ | Process RAM (`ResidualVector`). |
| **04** | **Sanity & Shield** | Parity Gating (`sensor_validator.py`) | Current & previous `actual_state`, `dt_sec`. | `SanityReport` + shielded `ResidualVector`. | Range limits, rolling variance (frozen ADC), rate limits, thermal parity. | $0.18\,\text{ms}$ | Rolling deque (20 frames) in validator. |
| **05** | **Anomaly Detection** | NumPy NN + FFT (`anomaly_detector.py`) | 14-dim residual vector + gearbox RMS. | `ae_score` ($0..1$), `spectral_score` ($0..1$). | 14-8-4-8-14 Autoencoder reconstruction loss + 3rd harmonic ratio. | $1.45\,\text{ms}$ | Autoencoder weights in memory (`rotax_autoencoder.json`). |
| **06** | **Score Buffering** | Circular Buffer (`trend_analyser.py`) | Timestamp, composite score, channel scores. | Rolling sliding window. | Circular deque push (`maxlen = 7200`). | $0.04\,\text{ms}$ | In-memory circular buffer (`ScoreBuffer`). |
| **07** | **Fault Classifier** | Scikit-Learn RF (`fault_classifier.py`) | 14-dim residual feature vector. | `fault_id` (0..8), `confidence` ($0..1$). | 100-tree Random Forest (`rotax_random_forest.joblib`) with sigmoid fallback. | $3.10\,\text{ms}$ (gated) | Loaded joblib model in RAM (2.14 MB). |
| **08** | **Majority Voting** | Consensus Filter (`detection_pipeline.py`) | Instantaneous frame `fault_id`. | `confirmed_fault_id` (0..8). | Rolling 10-frame consensus buffer (requires $\ge 80\%$ agreement). | $0.02\,\text{ms}$ | Internal 10-element deque. |
| **09** | **Prognostics & RUL** | Monte Carlo (`trend_analyser.py`) | Rolling 6-minute score buffer history. | `RULEstimate` (p10, p50, p90 hours), Go/No-Go. | OLS fitting (linear/exp/power), AIC model selection, 500-draw Monte Carlo. | $8.50\,\text{ms}$ (bg) | Thread-safe `latest_report` object. |
| **10** | **ATA & Graph Log** | Knowledge Graph (`mission_graph.py`) | Confirmed fault ID, severity, timestamp. | CBM nodes, ATA directives, maintenance orders. | Edge-triggered state machine; JSON graph serialization. | $0.35\,\text{ms}$ | `data/graph_db/fleet_graph.json` on disk. |
| **11** | **State Broadcast** | FastAPI / WebSockets (`main.py`) | `UnifiedTelemetryState` object. | JSON string over TCP WebSockets. | Pydantic JSON serialization + async WebSocket broadcast. | $1.20\,\text{ms}$ | Network TCP socket buffers + `live_sorties/<id>.csv`. |

---

## 3. Bottleneck Analysis, Overheads & Circularities

### 3.1 Circular Feedback Path Between Generator & Inference
The single most significant architectural vulnerability in the current pipeline is that **Stage 1 (Generation)** and **Stage 2 (Observer Twin)** share the same code:
$$\text{Actual} = \text{RotaxThermoModel}(\text{Inputs}) + \text{Dynamics} + \text{FaultDelta} + \text{Noise}$$
$$\text{Expected} = \text{RotaxThermoModel}(\text{Inputs})$$
$$\text{Residual} = \text{Actual} - \text{Expected} = \text{Dynamics} + \text{FaultDelta} + \text{Noise}$$
Because the base physics cancel out exactly, the residuals are purely the injected dynamics and offsets. The classifier is evaluated on its ability to detect offsets that were explicitly added by code in the same repository. While this proves the downstream pipeline functions without software leakage, it does not demonstrate diagnostic capability on real engine data.

### 3.2 The 20 Hz Telemetry Nyquist Bottleneck
The telemetry stream updates at 20 Hz, imposing a strict Nyquist ceiling of $10.0\,\text{Hz}$ on all downlinked scalar signals:
* **Propeller Shaft Frequency:** At 5,000 engine RPM ($i = 2.43$), $f_{\text{prop}} = 34.3\,\text{Hz}$.
* **3rd Harmonic Gear Meshing:** $3 \times 34.3\,\text{Hz} = 102.8\,\text{Hz}$.
* **Consequence:** True FFT spectral peak tracking cannot physically be performed over 20 Hz telemetry. The codebase recognizes this limitation in `spectral_analyser.py:175` by falling back to RMS envelope tracking. In the target architecture, high-frequency FFT must execute on the Edge SBC prior to downlinking.

### 3.3 Memory & Serialization Overhead
* The unified state frame (`UnifiedTelemetryState`) contains 27 telemetry channels, 14 residuals, 5 subsystem health scores, sensor sanity metadata, RUL estimates, ATA directives, and emergency checklists.
* Serializing this large nested dictionary to JSON via Pydantic requires $\sim 0.6\,\text{ms}$ per tick. While acceptable on a modern desktop CPU, this overhead would be prohibitive on a low-power avionics microcontroller. The final edge layer must utilize binary serialization (Protocol Buffers, FlatBuffers, or MAVLink framing) to fit within satellite bandwidth constraints.
