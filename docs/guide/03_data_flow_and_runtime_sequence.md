# 🔄 Data Flow & Runtime Sequence
**DRDO / iDEX Problem Statement ID: 26054**  
*End-to-End Execution Sequence, Telemetry Tick Breakdown & State Lifecycle*

---

## 1. System Startup & Cold Boot Lifecycle

When the system is launched via `run_app.py server` or `launch_backend_server.bat`, it executes the following initialization sequence:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             SYSTEM STARTUP LIFECYCLE                                     │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
                                             ▼
  1. Process Entry (run_app.py / main.py)
     • Validates Python environment, dependencies, CUDA availability
     • Initializes FastAPI application with permissive CORS
                                             │
                                             ▼
  2. FastAPI Lifespan Context Trigger (lifespan)
     • Invokes EngineStateService.get_instance()
                                             │
                                             ▼
  3. EngineStateService Singleton Initialization
     • Generates unique Sortie ID: SORTIE-SRV-YYYYMMDD-HHMMSS
     • Initializes 1D Thermodynamic Model (RotaxThermoModel)
     • Initializes 50 Hz Telemetry Streamer & Fault Generator (TelemetryStreamer)
     • Initializes Circular Score Buffer (ScoreBuffer, maxlen=7200 frames = 60 min)
     • Loads ML models (Random Forest .joblib, Autoencoder .json)
     • Spawns Prognostics Worker background thread (PrognosticsWorker)
     • Initializes in-memory Mission Knowledge Graph (MissionKnowledgeGraph)
     • Scans and indexes local aerospace technical manuals (LocalKnowledgeStore)
     • Initializes Diagnostic Agent & Copilot (DiagnosticAgent, MissionCopilot)
     • Spawns authoritative 50 Hz deterministic physics simulation thread (_run_loop)
                                             │
                                             ▼
  4. Async Broadcaster Launch
     • Spawns broadcast_telemetry_loop(service) as async background task
     • Server binds to 0.0.0.0:8000 and begins listening for Web & Blender clients
```

---

## 2. The 50 Hz Authoritative Tick Execution Sequence

Every 20 milliseconds ($dt = 0.020\text{s}$), the simulation worker thread executes `_tick(dt)` inside `EngineStateService`:

```
                                  ┌─────────────────────────────────────┐
                                  │   SIMULATION TICK TRIGGER (50 Hz)   │
                                  └──────────────────┬──────────────────┘
                                                     │
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. STREAMER FRAME GENERATION                                                                           │
│    • Computes theater environmental context: Altitude (MSL), OAT (°C), TAS (knots), Base RPM, Phase.  │
│    • Injects Gaussian sensor jitter (thermocouple ~0.18°C, pressure ~0.03 bar, RPM ~12 RPM).          │
│    • If active fault commanded: applies progressive onset ramp ($t_{\text{ramp}} = 6.0\text{s}$).      │
└────────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                     │
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. SENSOR SANITY VALIDATION (Stage 1)                                                                  │
│    • Evaluates channel rate-of-change against physical limits ($dT/dt \le 1.5^\circ\text{C/s}$).       │
│    • Evaluates rolling variance over 200 frames to detect frozen ADC circuits.                        │
│    • Flags failed channels so downstream ML ignores sensor electrical artifacts.                      │
└────────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                     │
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. 1D THERMODYNAMIC PHYSICS SHADOW & RESIDUALS (Stage 2)                                               │
│    • Solves ambient density derating using barometric ISA lapse equations.                            │
│    • Computes theoretical expected values: $CHT_{\text{exp}}, EGT_{\text{exp}}, MAP_{\text{exp}}, FF$ │
│    • Computes 14-dimensional residual vector: $\Delta_i = \text{Actual}_i - \text{Expected}_i$.        │
└────────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                     │
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. FAST ML ANOMALY DETECTION & CLASSIFICATION (Stages 3 to 7)                                          │
│    • Autoencoder calculates L2 reconstruction loss on residual vector $\rightarrow$ Anomaly Score.     │
│    • FFT sliding window monitors 3rd harmonic propeller shaft resonance ($3 \times \text{Prop RPM}$).│
│    • Writes normalized channel scores to circular ScoreBuffer for prognostics worker.                  │
│    • If Anomaly Score > Gate (0.35): Random Forest / Decision Boundary classifies Fault ID (1..8).    │
│    • Majority Vote Buffer (10 frames, 80% threshold) confirms fault, eliminating false alarms.        │
└────────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                     │
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 5. PROGNOSTICS, SUBSYSTEM HEALTH & ATA REASONING                                                       │
│    • Ingests latest AIC trend analysis, Remaining Useful Life (RUL P10/P50), and Go/No-Go status.     │
│    • Computes physical Subsystem Health indices (Propulsion, Fuel, Electrical, Thermal, Mechanical).   │
│    • Retrieves authoritative ATA chapter directive, root cause, and SOP emergency checklist.          │
└────────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                     │
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 6. KNOWLEDGE GRAPH LOGGING & AI DIAGNOSIS DISPATCH                                                     │
│    • On fault onset edge (0 $\rightarrow$ Fault ID): logs anomaly & maintenance order to graph.       │
│    • Dispatches RAG retrieval & Qwen3-4B natural language reasoning onto background daemon thread.     │
└────────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                     │
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 7. UNIFIED STATE PACKAGING                                                                             │
│    • Serializes full telemetry, analytics, health, and causal chain into UnifiedTelemetryState.       │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Real-Time Telemetry Broadcast & Client Sync

```
                         ┌───────────────────────────────────────────────┐
                         │   broadcast_telemetry_loop() (Asyncio Task)   │
                         └───────────────────────┬───────────────────────┘
                                                 │
                                                 ▼
                         Extracts latest state: service.get_latest_state()
                         Serializes to JSON: state.model_dump_json()
                                                 │
                        ┌────────────────────────┴────────────────────────┐
                        ▼                                                 ▼
             [ Active Web Sockets ]                            [ Active Blender Sockets ]
             • Web Ground Station (React)                      • Blender EEVEE Viewport Client
             • Mobile Phone HUD Controllers                    • Standalone 3D HUD & Gauges
                        │                                                 │
                        ▼                                                 ▼
             Updates React State @ 50 FPS                      Updates 3D Shaders & Orbit @ 50 FPS
             (Gauges, Cards, Health, Graphs)                   (Pulsing Red Emission & Ghosting)
```

---

## 4. Operator Command Execution Flow

When an operator changes throttle, triggers a fault scenario, or switches operational regions from the Web Dashboard or GCS:

```
┌────────────────────────┐
│ Operator Action in UI  │ (e.g. Clicks "Fault 01: Cyl #2 Overheat" or Adjusts Altitude to 22,000 ft)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ REST POST /api/control │ or WebSocket JSON Message {"action": "SET_FAULT", "fault_id": 1}
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ EngineStateService     │
│ .handle_command(cmd)   │
└───────────┬────────────┘
            │
            ├─► Acquires threading.Lock (Thread-Safe state mutation)
            ├─► Sets active_fault_id = 1, initiates fault ramp in TelemetryStreamer
            ├─► Resets ML detection pipeline & majority vote buffer
            ├─► Triggers immediate _tick(0.05) to instantly compute new state
            └─► Releases lock and returns {"status": "SUCCESS"}
```

---

## 5. Post-Flight Debrief & CBM Lifecycle Flow

At the conclusion of a mission sortie, the post-flight CBM reporting pipeline is triggered:

```
┌────────────────────────────────────────┐
│ Trigger: POST /api/debrief or CLI Exit │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ EngineStateService.export_debrief()    │
└──────────────────┬─────────────────────┘
                   │
                   ├─► Computes total flight hours: (T_end - T_start) / 3600.0
                   ├─► Marks SortieNode as COMPLETED in MissionKnowledgeGraph
                   ├─► Finalizes final health index & open maintenance action counts
                   │
                   ▼
┌────────────────────────────────────────┐
│ MissionReporter.generate_report()      │
└──────────────────┬─────────────────────┘
                   │
                   ├─► Compiles YAML frontmatter (Sortie metadata, region, flight hours, anomalies)
                   ├─► Synthesizes Section 1: Executive Summary
                   ├─► Compiles Section 2: Telemetry & Anomaly Event Log Table
                   ├─► Compiles Section 3: Pilot Prescriptive SOP Compliance Record
                   ├─► Compiles Section 4: Condition-Based Maintenance (CBM) Work Orders
                   │
                   ▼
┌────────────────────────────────────────┐
│ Saved to data/mission_reports/         │ -> Output: data/mission_reports/SORTIE-SRV-YYYYMMDD.md
└────────────────────────────────────────┘
```
