# Project ANUMAAN — Implementation Gap Plan

**Purpose:** for every requirement in [fun_req.md](fun_req.md), record whether the current system implements it *genuinely*, what is missing, and exactly what to build so that each officially stated requirement is met in good faith, not just in name.

**Audit date:** 2026-09-17. **Method:** code reading and targeted checks of `backend/`, `frontend/src/`, `apps/`, `data/`, `tests/`. Non-LLM test suites run: `pytest tests/test_physics_and_telemetry.py tests/test_ml_classifier.py tests/test_analytical_pipeline.py tests/test_causal_propagation.py tests/test_dataset_fusion.py tests/test_rotax_dataset.py tests/test_server_api.py`. **Result: 73 passed.**

> Passing tests prove the code does what it was written to do. They do not prove the twin solves the PS. Several gaps below are exactly that difference.

---

## 1. Status Legend

| Status | Meaning |
|---|---|
| ✅ **GENUINE** | Implemented, wired into the live system, and does what the requirement asks |
| 🟨 **PARTIAL** | Real implementation exists but is incomplete, unvalidated, or narrower than the requirement |
| 🟥 **NOT GENUINE** | Appears implemented (UI, API or name exists) but does not actually deliver the requirement |
| ⬛ **MISSING** | No implementation found |
| ❔ **NOT VERIFIED** | Not checked in this audit |

**Global caveat:** every live data path currently depends on gap **G01**. Items marked GENUINE work correctly *on the data they receive*, but that data is not yet an independent engine.

---

## 2. What Already Works (keep and build on)

| Capability | Evidence |
|---|---|
| 9-stage real-time detection pipeline at 20 Hz | [backend/ml/detection_pipeline.py](../backend/ml/detection_pipeline.py) |
| Unsupervised residual autoencoder (pure numpy) | [backend/ml/anomaly_detector.py](../backend/ml/anomaly_detector.py) |
| Fault classifier (Random Forest on physics residuals), mission-isolated train/val/test split, leakage audit | [backend/ml/fault_classifier.py](../backend/ml/fault_classifier.py), [backend/ml/models/model_metrics.json](../backend/ml/models/model_metrics.json) |
| Degradation trend analysis + Monte Carlo RUL (p10/p50/p90) in a background worker | [backend/ml/trend_analyser.py](../backend/ml/trend_analyser.py), [backend/ml/rul_estimator.py](../backend/ml/rul_estimator.py) |
| Pre-flight Go/No-Go advisory | `MissionGoNoGoAdvisory` in `rul_estimator.py` |
| Sensor sanity checks (unphysical rate, isolated spike, frozen sensor) | [backend/physics/sensor_validator.py](../backend/physics/sensor_validator.py) |
| 8 fault scenarios with progressive, causally coupled onset ramps | [backend/telemetry/can_streamer.py](../backend/telemetry/can_streamer.py) |
| Unified 20 Hz state over REST and WebSocket | [backend/server/main.py](../backend/server/main.py), [backend/server/schemas.py](../backend/server/schemas.py) |
| Mission replay engine + UI scrubber | [backend/telemetry/replay_engine.py](../backend/telemetry/replay_engine.py), `frontend/src/components/MissionReplayScrubber.tsx` |
| Mission debriefs, mission reports, knowledge graph, graph viewer | `backend/graph/`, `backend/reports/`, `apps/mission_graph_viewer/` |
| Condition-based maintenance: work orders with one-time sign-off, fleet summary, region comparison | `/api/cbm/maintenance`, `/api/cbm/fleet`, `/api/cbm/regions` |
| Time-accelerated long-mission bundle generation | [scripts/simulate_missions.py](../scripts/simulate_missions.py) |
| Dashboard: readings, fault matrix, diagnostic card, subsystem health, mission readiness, calculations | `frontend/src/components/` |
| Desktop GCS and 3D Blender twin client | `apps/desktop_gcs/`, `apps/blender_twin/` |

---

## 3. Gap Register

Priority: **P1** = credibility blocker (fix first; the solution is not convincing without it) · **P2** = explicitly required and missing or broken · **P3** = depth and strengthening.

Targets marked 🟦 are our proposed acceptance values. The PS states no numbers.

### G01: The simulated engine and the twin are the same model · **P1**

- **Finding:** each "actual" sensor reading is built as the twin's own *expected* state + Gaussian noise + injected fault offsets. The twin then compares actual against that same expected state, so residuals are always exactly noise + the injected fault, and detection cannot meaningfully fail.
- **Evidence:** [can_streamer.py:175-215](../backend/telemetry/can_streamer.py#L175-L215); consumed at [engine_service.py:239](../backend/server/engine_service.py#L239).
- **PS items:** SYS-01, SYS-04, INT-01, INT-06, DTC-02, DTC-03, DTC-04, CAP-03, CAP-12, DEL-03.
- **Build:**
  1. A separate **virtual engine** process: the plant that stands in for the real engine. Base it on the higher-fidelity ODE model in [rotax_dataset_generator.py](../backend/telemetry/rotax_dataset_generator.py) (thermal capacitance lags, crankshaft inertia, oil viscosity coupling), **not** on `thermo_model.py`.
  2. Give the virtual engine properties the twin does not know: engine-to-engine parameter variation, sensor bias, sensor lag, sensor noise, slow wear accumulation.
  3. The virtual engine publishes **only sensor frames** over a transport (G11). The twin never imports its internals.
  4. Faults are injected into the virtual engine only. The twin has no access to `active_fault_id`.
- **Done when:**
  - [ ] Twin and virtual engine run as separate processes; the twin has no import of the plant code
  - [ ] Nominal residuals are non-zero and structured (model mismatch), not pure white noise
  - [ ] The `FAULT_ID` ground-truth label is absent from anything the twin receives
  - [ ] All existing tests still pass or are updated with a written reason

### G02: Operator throttle/altitude/temperature commands do not affect physics · **P1**

- **Finding:** `SET_THROTTLE`, `SET_ALTITUDE` and `SET_OAT` only overwrite the displayed fields *after* the frame is generated from the region's sinusoidal profile. Temperatures, pressures and fuel flow do not respond. Only `SET_REGIME` changes the physics.
- **Evidence:** [engine_service.py:253-257](../backend/server/engine_service.py#L253-L257), commands at [engine_service.py:626-651](../backend/server/engine_service.py#L626-L651); profile in `CANStreamer.get_flight_context` ([can_streamer.py:108](../backend/telemetry/can_streamer.py#L108)).
- **PS items:** CAP-07, CAP-08, SIM-01, SIM-04, SIM-05, SIM-07, SIM-08.
- **Build:** route commanded throttle, altitude and OAT into the virtual engine (G01) as its inputs; add first-order dynamics (RPM response to throttle, thermal lag on CHT/EGT/oil) so a step change produces a transient, not an instant jump.
- **Done when:**
  - [ ] A throttle step 40% → 100% produces an RPM rise with a visible time constant and CHT/EGT rising over tens of seconds
  - [ ] Raising altitude at fixed throttle measurably reduces manifold pressure and power
  - [ ] Raising OAT at fixed throttle measurably raises CHT/oil temperature
  - [ ] Each of the above has an automated test asserting direction and non-zero time constant

### G03: No evidence the system predicts before failure; validation is circular · **P1**

- **Finding:** the classifier's 97.51% held-out accuracy is measured on data from the same generator and fault-signature code used for training. Metrics are per-frame classification only. Nothing measures warning lead time, false alarms over long nominal flights, RUL error, or improvement over threshold alarms.
- **Evidence:** [model_metrics.json](../backend/ml/models/model_metrics.json) (`held_out_test_missions_results`, 10 missions per split, one fault type per mission).
- **PS items:** CAP-04, CAP-05, CAP-06, CAP-13, CAP-14, FDP-01…09, AIM-02, AIM-04, AIM-05, DEL-04.
- **Build:** an evaluation harness `backend/evaluation/` that runs the twin against the virtual engine (G01) and reports:
  1. **Unseen conditions:** fault severities, onset rates, engine-variation seeds and regions **not** used in training.
  2. **Warning lead time** per fault: time from first twin warning to the moment a conventional fixed threshold would fire, and to functional failure.
  3. **Threshold baseline:** the same runs through a plain limit-check monitor, reported side by side. This directly evidences FDP-01's "transition from threshold-based monitoring".
  4. **False alarm rate** on long nominal flights, per flight hour.
  5. **RUL error:** predicted vs known time-to-failure (the virtual engine knows the truth), with p10–p90 interval coverage.
  6. **Sensor-fault discrimination:** sensor faults (G05) must not be reported as component faults.
  7. A generated report `docs/.../evaluation_report.md` with plots, reproducible from one command.
- **Done when:**
  - [ ] Report generated from one command with fixed seeds
  - [ ] 🟦 Every progressive fault warned before the conventional threshold (median lead time reported per fault)
  - [ ] 🟦 False alarms ≤ 1 per 10 nominal flight hours
  - [ ] 🟦 RUL p10–p90 interval contains true time-to-failure in ≥ 80% of runs
  - [ ] Results shown against the threshold baseline for every fault

### G04: "Vibration signatures" are a single RMS value at 20 Hz · **P2**

- **Finding:** vibration is one `VIB_GEARBOX_RMS` channel at 20 Hz. The spectral analyser correctly detects that the 3rd harmonic (~100 Hz at cruise) exceeds the 10 Hz Nyquist limit and falls back to RMS, so no spectral signature is actually analysed.
- **Evidence:** [spectral_analyser.py:176](../backend/ml/spectral_analyser.py#L176), sampling at [detection_pipeline.py:213](../backend/ml/detection_pipeline.py#L213).
- **PS items:** HMS-09, FDP-09.
- **Build:** the virtual engine synthesizes a vibration waveform at ≥ 2 kHz (shaft orders 1×/2×/3× prop, crank order, gear-mesh frequency, misfire impulses, bearing defect tones, noise). An edge feature extractor computes FFT/order spectra over short windows and publishes features (order amplitudes, band energies, kurtosis, crest factor) at 20 Hz. The twin consumes features; the dashboard shows a spectrum or order plot for engineers.
- **Done when:**
  - [ ] Gearbox wear raises the 3× prop-order amplitude before broadband RMS rises (plotted)
  - [ ] Misfire produces a distinct order signature distinguishable from gearbox wear
  - [ ] Features stream at 20 Hz; raw waveform never crosses the 20 Hz state link

### G05: Sensor drift detection is hardcoded off · **P2**

- **Finding:** `drift_detected` is always `False`. The validator's comment says the trend analyser populates it, but nothing does. Only spikes, unphysical rates and frozen values are detected.
- **Evidence:** [engine_service.py:457](../backend/server/engine_service.py#L457), [detection_pipeline.py:313](../backend/ml/detection_pipeline.py#L313), [detection_pipeline.py:620](../backend/ml/detection_pipeline.py#L620), [sensor_validator.py:263](../backend/physics/sensor_validator.py#L263).
- **PS items:** FDP-06.
- **Build:** slow-bias detection using (a) redundancy: 4 CHT and 4 EGT channels, FADEC Lane A vs Lane B MAP; (b) measured-vs-physics-expected bias estimation with CUSUM or a Kalman bias state. Inject sensor faults in the virtual engine: bias ramp, stuck value, noise growth, intermittent dropout.
- **Done when:**
  - [ ] A +0.5 °C/min bias ramp on one CHT is flagged as **sensor drift**, not cooling degradation
  - [ ] A real cooling fault on the same cylinder is flagged as a **component fault**, not sensor drift
  - [ ] `drift_detected` is computed, never a constant

### G06: Injection timing parameters are not tracked anywhere · **P2**

- **Finding:** no injection or ignition timing field exists in backend, frontend or apps. The 27-parameter `EnginePhysicalState` has no timing channel.
- **Evidence:** [thermo_model.py:29](../backend/physics/thermo_model.py#L29); schema [schemas.py](../backend/server/schemas.py); search for `injection_timing|pulse_width|ignition_timing|spark_advance` returns nothing.
- **PS items:** HMS-11.
- **Build:** channels `INJ_TIMING_DEG_1..4` (start of injection), `INJ_PULSE_MS_1..4`, `IGN_TIMING_DEG` for the 912 iS. Model their effect on EGT, power and fuel flow; add fault *injection timing drift / injector response delay*; show them on the dashboard and include them in the classifier features; extend the dataset schema.
- **Done when:**
  - [ ] Channels present end to end: virtual engine → state → dashboard → replay → dataset
  - [ ] Timing drift fault detected and distinguished from injector clog (fault 2)

### G07: Engine performance maps do not exist · **P2**

- **Finding:** the expected state comes from algebraic formulas (e.g. manifold pressure at [thermo_model.py:146](../backend/physics/thermo_model.py#L146)). No performance map tables are used.
- **PS items:** INT-03.
- **Build:** tabulated maps of power, fuel flow and manifold pressure vs RPM × throttle, with density-altitude correction, sourced from Rotax 912 iS operator/installation manual performance charts (source recorded in the data file). Bilinear interpolation in the twin's expected-state calculation.
- **Done when:**
  - [ ] Map data file with cited source
  - [ ] Twin expected power and fuel flow match the published chart points within 🟦 5%
  - [ ] Unit test for interpolation and out-of-range handling

### G08: No adaptive learning · **P3**

- **Finding:** no retraining, online updating or baseline adaptation exists. Models are trained once offline.
- **Evidence:** search for `partial_fit|retrain|incremental|adaptive` in `backend/` and `scripts/` finds nothing relevant.
- **PS items:** AIM-01.
- **Build:**
  1. Per-engine baseline adaptation: update residual normalization and anomaly thresholds using data from flights later confirmed nominal.
  2. Retraining pipeline from recorded sorties, using maintenance work-order sign-offs as ground-truth labels (the sign-off flow already exists).
  3. Model versioning with automatic before/after evaluation (G03 harness); promote only if not worse.
  4. Guard: never adapt on data from windows with open anomalies or unresolved work orders.
- **Done when:**
  - [ ] A deliberately different virtual engine (G01 variation) starts with higher false alarms, and after N nominal flights the rate drops (plotted)
  - [ ] A slow real fault is **not** absorbed into the baseline (test)
  - [ ] Model version recorded in every diagnostic event

### G09: Engine efficiency trends are absent · **P2**

- **Finding:** no efficiency metric in backend analytics or frontend. "Efficiency" appears only as volumetric efficiency inside the physics formula.
- **PS items:** VIS-07.
- **Build:** compute brake-specific fuel consumption (from mapped power, G07, and fuel flow), fuel flow vs expected at the same power, and power margin at altitude. Trend these within a sortie and across sorties/fleet; dashboard chart; include them in mission reports.
- **Done when:**
  - [ ] Injector clog and cooling degradation visibly shift the efficiency trend
  - [ ] Per-sortie and cross-sortie charts on the dashboard and in mission reports

### G10: One interface for three required audiences · **P2**

- **Finding:** the dashboard is a single operator-oriented view. Maintenance work orders exist in the API; no separate engineer or maintenance workflow view was found in `frontend/src/components/`.
- **PS items:** VIS-02, VIS-03, VIS-04.
- **Build:** three views or tabs:
  - **Operator:** health status, active alerts, recommended action, Go/No-Go.
  - **Propulsion engineer:** residuals, trends, spectra (G04), model explanations (trigger signals, feature contributions), timing (G06), efficiency (G09).
  - **Maintenance:** per-component RUL, work-order queue with sign-off, maintenance advisory history, mission-wise health reports.
- **Done when:**
  - [ ] Each view usable without the others; each shows only what its role needs
  - [ ] Work-order sign-off possible from the UI

### G11: No ingestion of data the twin did not generate itself · **P3** (P1 dependency of G01)

- **Finding:** the only data source is the in-process generator. There is no ingestion interface for an external stream. No CAN frame encoding exists (no python-can, DBC or frame packing found).
- **PS items:** DTC-06, INT-06, SYS-08, OPT-01, OPT-02, TEX-05.
- **Build:**
  1. A transport between the virtual engine and the twin: **virtual CAN** via python-can with a DBC message definition (works on Windows; real SocketCAN needs Linux/WSL `vcan`), with UDP as a fallback.
  2. A log-as-live mode: stream a recorded CSV into the same ingestion path at real or accelerated speed.
  3. An ingestion health view: frame rate, dropped frames, stale-channel detection.
- **Done when:**
  - [ ] The twin runs identically from virtual engine over CAN, from UDP, and from log-as-live
  - [ ] DBC file documented; message IDs and scaling listed in the docs
  - [ ] Stale or missing channels detected and shown

### G12: Missions have a single flight phase · **P2**

- **Finding:** every region returns `CRUISE_LOITER` with sinusoidal altitude. There is no takeoff, climb, descent, landing or throttle-transient scenario in live mode. Endurance is only covered by the time-accelerated bundle script.
- **Evidence:** [can_streamer.py:108-140](../backend/telemetry/can_streamer.py#L108-L140).
- **PS items:** CAP-07, SIM-02, SIM-05, SIM-06, SIM-07, SIM-08.
- **Build:** mission profile files (phase sequence, durations, target altitude, throttle schedule, ISA temperature deviation, seed); scenario presets **High Altitude**, **Endurance (time-accelerated, with wear accumulation)**, **Hot Weather**, **Rapid Throttle Transitions**; run them in live mode, replay and the evaluation harness.
- **Done when:**
  - [ ] The four named PS scenarios are selectable from the dashboard and runnable headless
  - [ ] Each shows distinct engine behaviour (plots in the evaluation report)
  - [ ] Faults can be injected at any phase

### G13: Cooling degradation and overheating trends share one fault · **P3**

- **Finding:** both PS items map onto fault 1 (Cyl #2 CHT overheat, baffle).
- **PS items:** FDP-04, FDP-08.
- **Build:** add slow cooling-efficiency loss over many flight hours (coolant/radiator/baffle degradation) distinct from an acute overheat; the trend analyser must predict it well before limits.
- **Done when:** [ ] Both are separately classified and separately reported with lead time (G03)

### G14: Combustion instability is represented only as EGT imbalance · **P3**

- **PS items:** FDP-07, FDP-02.
- **Build:** cycle-to-cycle variation (RPM and EGT fluctuation statistics, vibration impulses from G04) as a combustion-instability condition, distinct from both misfire and air-fuel imbalance.
- **Done when:** [ ] Misfire, instability and EGT imbalance are mutually distinguishable in the evaluation confusion matrix

### G15: Lubrication covers only oil pressure loss · **P3**

- **PS items:** FDP-05.
- **Build:** oil temperature rise at constant load, oil degradation (viscosity-driven pressure/temperature relationship drift), oil consumption.
- **Done when:** [ ] At least two lubrication conditions besides pressure loss detected and distinguished

### G16: Battery/alternator health is voltage sag only · **P3**

- **PS items:** HMS-10.
- **Build:** battery state-of-health estimate (charge/discharge response, internal resistance from voltage drop under load steps), alternator output capacity vs electrical load.
- **Done when:** [ ] A degrading battery is detected before bus voltage leaves limits

### G17: State estimation is sensor display, and the physics has no dynamics · **P3**

- **Finding:** the twin's expected state is steady-state algebra from current inputs; no estimator combines the model with measurements.
- **PS items:** CAP-11, INT-02, INT-07, DEL-03.
- **Build:** add thermal and rotational lag states to the twin's model and run a Kalman or observer-style estimator that fuses model prediction with (possibly faulty) sensor measurements. The result also provides unmeasured quantities (e.g. estimated power) and supports G05.
- **Done when:** [ ] Estimated state tracks the virtual engine's true internal state better than raw sensors during noise and single-sensor faults (plotted)

### G18: Dataset claims exceed the data present · **P2**

- **Finding:** `data/telemetry/source1_avionics_logs/` (real Garmin logs) contains **0 files**. Source 2 is NASA C-MAPSS `train_FD001.txt`, which is **turbofan** degradation data mapped onto a piston-engine schema at a fixed cruise baseline. Effectively all piston-engine data is synthetic.
- **PS items:** DEL-06.
- **Build:** either obtain real piston-engine logs (engine-monitor exports from general aviation aircraft with a documented licence) and parse them with the existing `garmin_parser.py`, or present all datasets explicitly as simulated with their generation method. Drop or clearly caveat the turbofan-derived RUL grounding.
- **Done when:** [ ] Every dataset claim in docs, UI and presentation matches the files actually present

### G19: Single-engine hardcoding limits scalability and fleet claims · **P3**

- **Finding:** no `platform_id` or `engine_id` in the state; fault IDs validated as 0..8; Rotax constants at module level; fleet summary aggregates sorties rather than distinct engines. Detailed in [assets/03_twin_integration_spec.md §2](assets/03_twin_integration_spec.md).
- **PS items:** SYS-02, SYS-03, SYS-09, DTC-05.
- **Build:** engine identity in state and records; engine parameters from a configuration file rather than code constants; fleet view listing multiple engine instances (two virtual engines with different variation seeds is sufficient).
- **Done when:** [ ] Two virtual engines run concurrently and appear as separate fleet members with separate health, RUL and history

### G20: Deployment roadmap and architecture documentation must match the real system · **P2**

- **PS items:** SYS-06, SYS-07, SYS-08, DEL-02, DEL-07.
- **Build:** architecture document regenerated from the actual code after G01/G11 (process boundaries, transports, rates); deployment roadmap covering edge vs GCS split, test-rig mode, fleet server, hardware path to real CAN/FADEC, security of telemetry (INN-07), and known limitations.
- **Done when:** [ ] Every component in the architecture diagram maps to a real module or is explicitly marked "roadmap"

### G21: Use of operational history in health and RUL · **P3** · ❔ NOT VERIFIED

- **Finding:** sorties, anomalies and maintenance actions persist in the knowledge graph (`data/graph_db/fleet_graph.json`), and fleet/region summaries use them. Whether RUL and health indices use cumulative engine hours, prior faults or maintenance history was **not verified**.
- **PS items:** INT-08.
- **Build (if absent):** RUL initialised from cumulative operating hours and prior degradation; maintenance sign-off resets or adjusts component wear state.
- **Done when:** [ ] RUL for the same engine differs correctly between a fresh engine and one with recorded prior wear

### G22: Hygiene · **P3**

- `data/telemetry/rotax912_dataset_manifest.json` stores absolute paths from another machine (`E:\TalentForge\Clay\...`). Make them relative.
- `_tick` docstring says 120 Hz; the state broadcast is 20 Hz ([engine_service.py:233](../backend/server/engine_service.py#L233), [schemas.py:116](../backend/server/schemas.py#L116)). Align the documentation with the real rate.

---

## 4. Requirement Coverage Matrix

Summary across the 83 requirements: **✅ 27 · 🟨 39 · 🟥 10 · ⬛ 6 · ❔ 1**

### Overall system

| ID | Requirement | Status | Gap |
|---|---|---|---|
| SYS-01 | Digital twin for an aero piston engine in MALE UAV | 🟨 | G01 |
| SYS-02 | Scalable | 🟨 | G19 |
| SYS-03 | Modular | 🟨 | G19 |
| SYS-04 | Real-time virtual representation | 🟥 | G01 |
| SYS-05 | Indigenous | ✅ | In-house models, runs fully offline |
| SYS-06 | Suitable for UAV GCS & health-monitoring architecture | 🟨 | G20 |
| SYS-07 | Future defence-grade GCS deployment | 🟨 | G20 |
| SYS-08 | Future engine test-rig deployment | ⬛ | G11, G20 |
| SYS-09 | Future fleet-level deployment | 🟨 | G19 |

### Integration inputs

| ID | Requirement | Status | Gap |
|---|---|---|---|
| INT-01 | Engine sensor data | 🟥 | G01 |
| INT-02 | Thermodynamic behaviour models | 🟨 | G17 |
| INT-03 | Engine performance maps | ⬛ | G07 |
| INT-04 | Failure/degradation logic | 🟨 | G13–G16 |
| INT-05 | AI/ML predictive analytics | ✅ | — |
| INT-06 | Live telemetry | 🟥 | G01, G11 |
| INT-07 | Physics-based models | 🟨 | G17 |
| INT-08 | Operational history | ❔ | G21 |
| INT-09 | AI-driven analytics | ✅ | — |

### Capabilities

| ID | Requirement | Status | Gap |
|---|---|---|---|
| CAP-01 | Real-time parameter visualization | ✅ | — |
| CAP-02 | Health indicator monitoring | ✅ | — |
| CAP-03 | Detection of abnormal conditions | 🟥 | G01, G03 |
| CAP-04 | Predicting failures before occurrence | 🟥 | G03 |
| CAP-05 | Degradation trends | 🟨 | G03 |
| CAP-06 | RUL | 🟨 | G03 |
| CAP-07 | Mission profile simulation | 🟨 | G02, G12 |
| CAP-08 | Environmental condition simulation | 🟨 | G02 |
| CAP-09 | Post-flight analysis | ✅ | — |
| CAP-10 | Mission replay | ✅ | — |
| CAP-11 | Real-time state estimation | 🟨 | G17 |
| CAP-12 | Anomaly detection | 🟨 | G01, G03 |
| CAP-13 | Degradation tracking | 🟨 | G03 |
| CAP-14 | Fault prediction | 🟨 | G03 |
| CAP-15 | Mission replay capability | ✅ | — |

### A. Digital twin core

| ID | Requirement | Status | Gap |
|---|---|---|---|
| DTC-01 | Central intelligence layer | ✅ | `engine_service.py` unified state |
| DTC-02 | Continuously mirrors the real engine | 🟥 | G01 |
| DTC-03 | Dynamic, continuously synchronized representation | 🟨 | G01 |
| DTC-04 | Synchronized with live engine data | 🟥 | G01, G11 |
| DTC-05 | Modular architecture for scalability | 🟨 | G19 |
| DTC-06 | Real-time data ingestion | ⬛ | G11 |

### B. Health monitoring

| ID | Requirement | Status | Gap |
|---|---|---|---|
| HMS-01 | Continuous subsystem assessment | ✅ | — |
| HMS-02 | Health indices | ✅ | — |
| HMS-03 | RPM | ✅ | — |
| HMS-04 | CHT | ✅ | — |
| HMS-05 | EGT | ✅ | — |
| HMS-06 | Oil pressure | ✅ | — |
| HMS-07 | Oil temperature | ✅ | — |
| HMS-08 | Fuel flow | ✅ | — |
| HMS-09 | Vibration signatures | 🟥 | G04 |
| HMS-10 | Battery/alternator health | 🟨 | G16 |
| HMS-11 | Injection timing parameters | ⬛ | G06 |

### C. Fault detection & predictive analytics

| ID | Requirement | Status | Gap |
|---|---|---|---|
| FDP-01 | Predictive diagnostics instead of thresholds | 🟥 | G03 |
| FDP-02 | Misfire | 🟨 | G03, G14 |
| FDP-03 | Injector abnormalities | 🟨 | G03, G06 |
| FDP-04 | Cooling degradation | 🟨 | G13 |
| FDP-05 | Lubrication issues | 🟨 | G15 |
| FDP-06 | Sensor drift/failure | 🟨 | G05 |
| FDP-07 | Combustion instability | 🟨 | G14 |
| FDP-08 | Overheating trends | 🟨 | G13 |
| FDP-09 | Abnormal vibration patterns | 🟨 | G04 |

### D. AI/ML layer

| ID | Requirement | Status | Gap |
|---|---|---|---|
| AIM-01 | Adaptive learning | ⬛ | G08 |
| AIM-02 | Predictive diagnostics | 🟨 | G03 |
| AIM-03 | Intelligent maintenance planning | ✅ | Go/No-Go, CBM work orders |
| AIM-04 | Anomaly detection algorithms | 🟨 | G03 |
| AIM-05 | RUL estimation | 🟨 | G03 |
| AIM-06 | Trend analysis | ✅ | — |
| AIM-07 | Predictive maintenance recommendations | ✅ | — |

### E. Simulation & replay

| ID | Requirement | Status | Gap |
|---|---|---|---|
| SIM-01 | Simulation tools reproducing engine behaviour | 🟨 | G01, G02 |
| SIM-02 | Mission scenario analysis | 🟨 | G12 |
| SIM-03 | Historical mission replay | ✅ | — |
| SIM-04 | Environmental condition simulation | 🟨 | G02 |
| SIM-05 | High altitude | 🟨 | G02, G12 |
| SIM-06 | Endurance mission | 🟨 | G12 |
| SIM-07 | Hot-weather operation | 🟨 | G02, G12 |
| SIM-08 | Rapid throttle transitions | 🟥 | G02, G12 |

### F. Visualization dashboard

| ID | Requirement | Status | Gap |
|---|---|---|---|
| VIS-01 | Intuitive operational interface | ✅ | — |
| VIS-02 | Serves UAV operators | ✅ | — |
| VIS-03 | Serves propulsion engineers | 🟨 | G10 |
| VIS-04 | Serves maintenance team | 🟨 | G10 |
| VIS-05 | Real-time health status | ✅ | — |
| VIS-06 | Fault alerts | ✅ | — |
| VIS-07 | Engine efficiency trends | ⬛ | G09 |
| VIS-08 | Maintenance advisory | ✅ | — |
| VIS-09 | Mission-wise health reports | ✅ | — |

### Deliverables

| ID | Deliverable | Status | Gap |
|---|---|---|---|
| DEL-01 | Functional prototype | ✅ | — |
| DEL-02 | Architecture design | 🟨 | G20 |
| DEL-03 | Engine simulation model | 🟨 | G01, G17 |
| DEL-04 | AI/ML anomaly detection module | 🟨 | G03 |
| DEL-05 | Visualization dashboard | ✅ | — |
| DEL-06 | Demonstration with datasets | 🟨 | G18 |
| DEL-07 | Documentation & deployment roadmap | 🟨 | G20 |

---

## 5. Execution Order

Each phase ends with all existing tests passing and new tests added for the phase.

| Phase | Gaps | Outcome |
|---|---|---|
| **1. Make the twin honest** | G01, G02, G11 (transport only), G22 | Independent virtual engine over a real transport; controls change physics |
| **2. Prove it predicts** | G03, G12, G18 | Evaluation report: lead time vs threshold alarms, false alarm rate, RUL error, on the four PS scenarios, with honest data labelling |
| **3. Close explicit gaps** | G06, G07, G04, G05, G09, G10 | Injection timing, performance maps, real vibration spectra, drift detection, efficiency trends, role views |
| **4. Depth** | G08, G13, G14, G15, G16, G17, G21 | Adaptive learning, full fault taxonomy separation, state estimator, history-aware RUL |
| **5. Scale & document** | G19, G20, G11 (log-as-live, ingestion health) | Multi-engine fleet, architecture and deployment roadmap matching the code |

**Re-run this audit** after each phase and update the status column in §4. A requirement moves to ✅ only when its gap's "Done when" boxes are all checked, with evidence.
