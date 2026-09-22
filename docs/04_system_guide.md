# ANUMAAN — Current System Guide

*What is actually built, as of 22 September 2026. Written by reading the source, not the older documentation — where this and [`03_implemented_features_technical_deep_dive.md`](03_implemented_features_technical_deep_dive.md) disagree, trust this one and re-verify.*

---

## 1. What the system is

A ground-station digital twin for a **Rotax 912 iS Sport** aero-piston engine on a MALE UAV. It ingests 27-parameter telemetry at 20 Hz, computes what a healthy engine *should* be doing at the same operating point, and acts on the difference — detecting anomalies, isolating one of eight faults, tracking degradation, estimating RUL, and issuing a mission go/no-go.

**Roughly 12,000 lines of Python** across 9 backend packages, an 18-file React GCS, three standalone desktop apps, and an 11-file pytest suite.

---

## 2. Running it

| Entry point | Starts |
|---|---|
| `run_app.py` | Unified launcher — canyon sim, Blender twin, pygame GCS, system audit |
| `launch_backend_server.bat` | FastAPI server (the GCS backend) |
| `launch_web_dashboard.bat` | React dashboard |
| `launch_canyon_simulation.bat` | → `apps/blender_twin/standalone_canyon_flight_app.py` |
| `launch_standalone_app.bat` | → `apps/blender_twin/standalone_digital_twin_app.py` |
| `launch_mission_graph.bat` | `scripts/simulate_missions.py`, then the mission-graph viewer |
| `launch_anumaan_site.bat` | Static WebGL presentation site (`site/`) |
| `launch_public_tunnel.bat` | cloudflared/ngrok tunnel |
| `pytest` | `pytest.ini` → `testpaths = tests` (11 test files) |

---

## 3. Backend architecture

### 3.1 The core: a 9-stage pipeline at 20 Hz

`backend/ml/detection_pipeline.py` (632 lines) is the heart of the system. Every telemetry frame passes through nine stages with a **stated budget of <20 ms total**:

```
        CAN / synthetic telemetry frame  (20 Hz, 27 params)
                          │
 Stage 1  Sensor Sanity ──────────────────────────  <0.1 ms
          rate limits · frozen-ADC · cross-channel      backend/physics/sensor_validator.py
                          │
 Stage 2  Physics Residuals ──────────────────────  <0.5 ms
          expected state from 1-D thermo model          backend/physics/thermo_model.py
          residual = actual − expected
                          │
 Stage 3  Anomaly Score ──────────────────────────  <2 ms
          autoencoder reconstruction ⊕ Z-score max      backend/ml/anomaly_detector.py
                          │
 Stage 4  Gearbox FFT ────────────────────────────  <2 ms
          3rd-harmonic spectral tracking, 1 s window    backend/ml/spectral_analyser.py
                          │
 Stage 5  Channel Score Buffer ───────────────────  <0.1 ms
          write to shared ScoreBuffer                   backend/ml/trend_analyser.py
                          │
 Stage 6  Fault Isolation ────────────────────────  <5 ms
          RandomForest — ONLY if score > ANOMALY_GATE    backend/ml/fault_classifier.py
                          │
 Stage 7  Majority Vote ──────────────────────────  <0.1 ms
          debounce buffer, suppresses single-frame flaps
                          │
 Stage 8  Trend Summary ──────────────────────────  <0.1 ms
          read latest from PrognosticsWorker
                          │
 Stage 9  JSON Event Emit ────────────────────────  <0.5 ms
          on_diagnostic_event callback → GCS
```

🔶 **Two design choices worth knowing:**
- **Stage 6 is gated.** The RandomForest only runs when the anomaly score clears `ANOMALY_GATE`. The expensive model is not on the hot path for healthy flight.
- **Stage 7 exists because Stage 6 is noisy.** A `MajorityVoteBuffer` debounces, so a single odd frame cannot raise an alert.

### 3.2 Threading model

| Thread | Rate | Job |
|---|---|---|
| Main | 20 Hz | `pipeline.process_frame()` — the 9 stages above |
| `PrognosticsWorker` (daemon) | every 20 s | Reads the shared `ScoreBuffer`, runs degradation trend fitting and RUL |

🔶 The split is deliberate: trend fitting over long windows is far too slow for a 20 Hz loop, so it runs asynchronously and Stage 8 simply reads the most recent result. `ml_runtime_lock.py` (45 lines) guards shared model access.

---

## 4. Module reference

### `backend/physics/` — 577 lines · the twin's foundation

| File | Lines | What it does |
|---|---|---|
| `thermo_model.py` | 300 | 1-D thermodynamic model of the Rotax 912 iS. ISA atmosphere, density derating, Otto-cycle relations, per-cylinder heat balance with first-order thermal lag, oil viscosity coupling. Produces `EnginePhysicalState` (27 params) and `ResidualVector` |
| `sensor_validator.py` | 274 | Distinguishes a **bad sensor from a bad engine**. Per-channel rate limits derived from real thermal response (CHT 1.5 °C/s physical vs >10 °C/50 ms artifact; EGT 8.0 °C/s because combustion responds faster), frozen-ADC detection via variance floor, cross-channel correlation |

✅ The engine constants are correct against manufacturer data: 1,352 cm³, 84 mm bore, 61 mm stroke, 10.8:1 compression, 2.43:1 reduction.

### `backend/ml/` — 2,450 lines · the intelligence

| File | Lines | What it does |
|---|---|---|
| `detection_pipeline.py` | 632 | The 9-stage orchestrator (§3.1) |
| `trend_analyser.py` | 755 | `DegradationTrendAnalyser`, `PrognosticsWorker`, `ScoreBuffer`, `RULEstimate`, `GoNoGoAdvisory`, `PrognosticsReport`. The 20-second background analytics |
| `anomaly_detector.py` | 410 | `ResidualAutoencoder` (hand-rolled, JSON weights) + Z-score. Operates on **residuals**, not raw values |
| `spectral_analyser.py` | 252 | `GearboxSpectralAnalyser` — tracks the 3rd harmonic of the propeller reduction shaft for early gear micro-pitting. ⚠️ See §8 |
| `fault_classifier.py` | 251 | `RotaxFaultClassifier` — RandomForest over 8 classes, with `NOMINAL_FLIGHT` and `UNSPECIFIED_ANOMALY_DRIFT` fallbacks |
| `rul_estimator.py` | 141 | Component-level RUL across six subsystems with Arrhenius thermal acceleration above 115 °C; emits `MissionGoNoGoAdvisory` with a `limiting_subsystem` |

**Trained artifacts** in `backend/ml/models/`: `rotax_random_forest.joblib` (2.1 MB), `rotax_autoencoder.json`, `model_metrics.json`, `autoencoder_metrics.json`.

### `backend/telemetry/` — 1,671 lines · data in

| File | Lines | What it does |
|---|---|---|
| `rotax_dataset_generator.py` | 484 | Physics-correlated synthetic time-series generator — the primary data source |
| `can_streamer.py` | 352 | 20 Hz 27-parameter stream with sensor jitter + **fault injector** |
| `dataset_fusion_engine.py` | 311 | Fuses three sources: Garmin G3X/G1000 real avionics logs · NASA C-MAPSS / CWRU benchmarks · physics-informed Rotax sorties |
| `replay_engine.py` | 203 | Indexes and serves past sorties for the GCS replay scrubber |
| `parsers/garmin_parser.py` | 168 | Garmin flight-log parser |
| `parsers/nasa_prognostics_parser.py` | 146 | C-MAPSS/CWRU parser |

### `backend/server/` — 1,492 lines · the API

| File | Lines | What it does |
|---|---|---|
| `engine_service.py` | 764 | `EngineStateService` — singleton holding authoritative twin state; `set_fault()`, `clear_fault()`, `handle_command()`, `export_debrief()`, `get_latest_state()` |
| `main.py` | 566 | FastAPI app — 21 REST routes + 2 WebSockets |
| `schemas.py` | 158 | Pydantic contracts |

### `backend/agent/` — 1,950 lines · advisory

| File | Lines | What it does |
|---|---|---|
| `copilot.py` | 1,190 | `MissionCopilot` — conversational orchestration. Regex guardrails (jailbreak / unsafe-command / off-topic), scans for a local `.gguf`/`.onnx` model |
| `diagnostic_agent.py` | 309 | **Fully deterministic, zero LLM.** Hardcoded ATA-chapter directives for faults 1–8 — root cause, prescriptive action, emergency checklist, target 3D mesh |
| `llm_engine.py` | 299 | `LocalQwenEngine` — local inference wrapper |
| `flight_intent.py` | 149 | Natural-language flight-command parsing |

### `backend/graph/` · `knowledge/` · `reports/` · `voice/`

| Package | Lines | What it does |
|---|---|---|
| `graph/` | 681 | `MissionKnowledgeGraph` — `SortieNode`, `SubsystemNode`, `AnomalyEventNode`, `MaintenanceActionNode`; `MissionReporter` |
| `knowledge/` | 582 | Offline RAG — PDF/office/text loaders, chunker, embedding index, local store, reranker |
| `reports/` | 655 | `mission_bundle.py`, `report_dump_writer.py` → `report_dump/` |
| `voice/` | 472 | STT, TTS, conversation, thinking-stream. ⚠️ Not required by the PS — [audit](audit/02_self_audit.md) recommends cutting |

---

## 5. API surface

**REST** (`/api/...`)

| Group | Endpoints |
|---|---|
| Core | `GET /api/health` · `GET /api/state` · `POST /api/control` · `POST /api/debrief` |
| CBM / fleet | `GET /api/cbm/fleet` · `/api/cbm/regions` · `/api/cbm/maintenance` · `POST /api/cbm/maintenance/{id}/signoff` |
| Replay | `GET /api/replay/manifests` · `/api/replay/{mission_id}/manifest` · `/api/replay/{mission_id}/frame` |
| AI | `GET /api/ai/status` · `POST /api/ai/warmup` · `POST /api/ai/ask` |
| Voice | `GET /api/voice/status` · `POST /api/voice/warmup` · `/reset` · `/converse` · `GET /api/voice/thinking/{session_id}` |
| Copilot | `POST /api/copilot/flight-command` |

**WebSocket**

| Endpoint | Purpose |
|---|---|
| `/ws/telemetry` | Live twin state → React GCS |
| `/ws/blender` | Live state → the Blender 3D twin |

🔶 Two separate sockets because the Blender client needs a different payload shape (mesh targets, fault-to-component mapping) than the dashboard.

---

## 6. Frontend and apps

**`frontend/` — React + TypeScript + Vite**, 18 source files.
`useTelemetrySocket.ts` and `useMissionReplay.ts` hooks; components: `ReadingsPanel`, `DiagnosticCard`, `FaultMatrix`, `SubsystemHealthCard`, `MissionReadinessCard`, `MissionReplayScrubber`, `EngineControls`, `CalculationsPanel`, `VoiceCopilot`, `AerospaceMarkdown`, `ConnectionModal`, `Header`, `PanelErrorBoundary`.

**`apps/` — three standalone desktop applications**

| App | Lines | What it is |
|---|---|---|
| `blender_twin/standalone_canyon_flight_app.py` | 2,366 | Ladakh-DEM canyon flight simulation |
| `blender_twin/standalone_digital_twin_app.py` | 1,405 | Blender EEVEE 3D engine viewport with HUD + diagnostics |
| `mission_graph_viewer/standalone_mission_graph_app.py` | 1,151 | Mission knowledge-graph viewer (+ `report_scanner`, `report_formatter`) |
| `desktop_gcs/standalone_gui_app.py` | 521 | Pygame hardware-accelerated GCS HUD |
| `blender_twin/flight_mission_recorder.py` | 483 | Records sorties |

**`site/`** — standalone WebGL presentation site (Three.js).

---

## 7. The eight faults

Each carries an ATA chapter, root cause, prescriptive action, emergency checklist and a target 3D mesh — all deterministic, from `diagnostic_agent.py`:

| # | Fault | ATA | Prescriptive action |
|---|---|---|---|
| 1 | Cylinder #2 CHT Overheat | 72-00 | Enrich fuel trim +12%, throttle back 15%, immediate RTB |
| 2 | Fuel Injector #1 Clog | 73-10 | Switch to Lane B ECU map, increase aux boost pump |
| 3 | Ignition Misfire (Lane A) | 74-20 | Force FADEC arbitration to Lane B coils |
| 4 | Oil Pressure Loss | 79-00 | Throttle to 4,200 RPM, precautionary landing |
| 5 | Gearbox Vibration & Clutch Wear | 72-10 | Limit transients, avoid harmonic band, schedule overhaul |
| 6 | Exhaust EGT Imbalance | 78-10 | Adjust cylinder #3 fuel trim |
| 7 | Alternator Voltage Sag | 24-00 | Shed ISR payload, engage backup bus |
| 8 | Dual FADEC ECU Drift | 76-00 | Force Lane B, flag Lane A MAP transducer |

---

## 8. What is real, and what is not

⚠️ **State this plainly; it is the question an evaluator will ask.**

| Component | Status |
|---|---|
| Physics model | ✅ Real first-principles thermodynamics, correct engine constants |
| Telemetry | ⬜ **Synthetic.** Physics-correlated generator; no real engine, no real CAN bus |
| Fault injection | ⬜ Synthetic, via `can_streamer` |
| Garmin / C-MAPSS / CWRU parsers | ✅ Real parsers for real datasets, wired through `dataset_fusion_engine` |
| Trained models | ✅ Real, trained on generated data |
| Metrics | ✅ **Honestly measured** — see below |

### Measurement discipline — the strongest thing in this codebase

`backend/ml/models/model_metrics.json` records:
- **"Strict Mission-Level Group Isolation (Train / Val / Test)"** — 30 missions, 10 per split, no mission spanning partitions
- Validation **0.9931** vs held-out test **0.9751**, reported separately — the ~1.8-point drop is published, not hidden
- Per-fault precision/recall/F1 with support, macro-F1, full 9×9 confusion matrix
- FAULT_1 recall **0.8359** against precision 1.0 — the system under-detects misfire and the metrics say so

🔶 Competing implementations quote bare "98%" and "99.2%" headlines on self-generated data. **We publish the confusion matrix.** That difference is worth stating out loud.

### Known limitations

| Limitation | Detail |
|---|---|
| ⚠️ **Vibration DFT path is dormant** | `spectral_analyser.py` is correctly Nyquist-aware: it computes `nyquist_hz`, tests `target_hz > nyquist_hz`, and falls back to an RMS envelope rather than producing a bogus DFT. But at the configured 20 Hz the 3rd harmonic (~103 Hz) is above the 10 Hz Nyquist limit, so **the DFT branch never executes**. The module's claimed early-warning advantage is not active. ⬜ Fix: pass `sample_rate_hz=10000` and feed a real kHz channel — see [Part XXVI](study/26_order_tracking_and_envelope.md) |
| No calibrated uncertainty | RUL emits point values and margins; no conformal intervals — [Part XXVII](study/27_conformal_prediction_for_rul.md) |
| No baseline comparison | The threshold comparator the PS asks us to beat is never measured against |
| Physics is the thinnest core module | 577 lines, versus 1,950 for the LLM copilot the PS never requested |
| Edge split is architectural only | Documented in study Parts V/XIII; no link-loss demonstration exists |
| `Voice/` and `Qwen3-4B/` are untracked | 8 GB of local weights, gitignored |

---

## 9. Data layer

| Path | Contents |
|---|---|
| `data/` | `missions/`, `telemetry/`, `graph_db/`, `documents/`, `nubra_raw_crop.npz` — **live, 22 code references** |
| `report_dump/` | Generated mission reports — **live, 18 code references**, 400 tracked files |
| `Datasets/` | Catalogue metadata only; raw data untracked by design |
| `backend/ml/models/` | Trained RF + autoencoder + metrics |
| `Models/`, `Models_Images/`, `3d_models/` | 3D assets (LFS) |

---

## 10. Where to go next

- **What to build and why** → [`audit/04_feature_spec.md`](audit/04_feature_spec.md) — 30 features, tiered, with build order
- **Where we stand** → [`audit/README.md`](audit/README.md) — 15 competitors analysed
- **Implementation references** → study [Parts XXIV–XXVII](study/README.md) — combustion/crank dynamics, misfire diagnostics, order tracking, conformal prediction
- **Repo cleanup** → [`audit/06_repo_cleanup_plan.md`](audit/06_repo_cleanup_plan.md)

---

*Derived from source on 22 September 2026. Line counts and route lists were read from the code, not copied from earlier documentation.*
