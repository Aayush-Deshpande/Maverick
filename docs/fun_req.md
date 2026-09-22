# Project ANUMAAN — Functional Requirements (Explicitly Stated in PS-26054)

**Scope of this file:** only what the official problem statement _explicitly_ states. No interpretation, no assumptions, no implementation choices. Wording is kept as close to the PS as possible.

- Verbatim PS: [00_official_problem_statement.md](00_official_problem_statement.md)
- Plain-language meaning of each item: [01_problem_statement_breakdown.md](01_problem_statement_breakdown.md)
- Current implementation status and what is still needed per item: [gap_plan.md](gap_plan.md)

Source-text OCR errors corrected, meaning unchanged: "Defection" → Detection, "Coding degradation" → Cooling degradation, "logit" → logic, "far anomaly" → for anomaly, "AE/ML" → AI/ML.

### Obligation levels (the PS's own words)

| Level             | PS wording                                                                       | Meaning for us                                                               |
| ----------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **MUST**          | "shall", "required", "expected solution should include", "deliverables expected" | Must be built and demonstrated                                               |
| **SHOULD**        | "should", "should be capable of", "should support"                               | Treat as mandatory; the PS lists these as the system's expected capabilities |
| **MAY**           | "may utilize"                                                                    | Allowed implementation options, not mandatory                                |
| **ENCOURAGED**    | "participants are encouraged to explore"                                         | Optional innovation; earns credit, not required                              |
| **UNDERSTANDING** | "teams are expected to demonstrate understanding of"                             | Must be evident in the solution and documentation                            |

**Totals:** 83 MUST/SHOULD items · 7 deliverables · 7 MAY options · 8 ENCOURAGED areas · 9 UNDERSTANDING areas.

---

## 1. Overall System

| ID     | Requirement                                                                                   | Level  | PS section        |
| ------ | --------------------------------------------------------------------------------------------- | ------ | ----------------- |
| SYS-01 | Develop a **Digital Twin system** for an **aero piston engine used in MALE UAV** applications | SHOULD | Description       |
| SYS-02 | The system is **scalable**                                                                    | SHOULD | Description       |
| SYS-03 | The system is **modular**                                                                     | SHOULD | Description       |
| SYS-04 | The system **shall create a real-time virtual representation of the engine**                  | MUST   | Description       |
| SYS-05 | Framework is **indigenous**                                                                   | SHOULD | Background        |
| SYS-06 | Suitable for **deployment in MALE UAV ground control and health monitoring architecture**     | SHOULD | Background        |
| SYS-07 | Designed considering **future deployment in defence-grade Ground Control Stations (GCS)**     | SHOULD | Expected Solution |
| SYS-08 | Designed considering **future deployment in engine test rigs**                                | SHOULD | Expected Solution |
| SYS-09 | Designed considering **future deployment in fleet-level health monitoring infrastructures**   | SHOULD | Expected Solution |

## 2. Integration Inputs: the virtual representation is created by integrating

| ID     | Requirement                                 | Level  | PS section        |
| ------ | ------------------------------------------- | ------ | ----------------- |
| INT-01 | **Engine sensor data**                      | MUST   | Description       |
| INT-02 | **Thermodynamic behavior models**           | MUST   | Description       |
| INT-03 | **Engine performance maps**                 | MUST   | Description       |
| INT-04 | **Failure/degradation logic**               | MUST   | Description       |
| INT-05 | **AI/ML-based predictive analytics**        | MUST   | Description       |
| INT-06 | Synchronized using **live telemetry**       | SHOULD | Expected Solution |
| INT-07 | Synchronized using **physics-based models** | SHOULD | Expected Solution |
| INT-08 | Synchronized using **operational history**  | SHOULD | Expected Solution |
| INT-09 | Synchronized using **AI-driven analytics**  | SHOULD | Expected Solution |

## 3. System Capabilities: "the proposed system should be capable of"

| ID     | Requirement                                                             | Level  | PS section  |
| ------ | ----------------------------------------------------------------------- | ------ | ----------- |
| CAP-01 | **Real-time engine parameter visualization**                            | SHOULD | Description |
| CAP-02 | **Monitoring of engine health indicators**                              | SHOULD | Description |
| CAP-03 | **Detection of abnormal operating conditions**                          | SHOULD | Description |
| CAP-04 | **Predicting probable failures before occurrence**                      | SHOULD | Description |
| CAP-05 | **Estimating degradation trends**                                       | SHOULD | Description |
| CAP-06 | **Estimating Remaining Useful Life (RUL)**                              | SHOULD | Description |
| CAP-07 | **Simulating engine behavior under different mission profiles**         | SHOULD | Description |
| CAP-08 | **Simulating engine behavior under different environmental conditions** | SHOULD | Description |
| CAP-09 | **Supporting post-flight analysis**                                     | SHOULD | Description |
| CAP-10 | **Supporting mission replay**                                           | SHOULD | Description |
| CAP-11 | **Real-time engine state estimation**                                   | SHOULD | Background  |
| CAP-12 | **Anomaly detection**                                                   | SHOULD | Background  |
| CAP-13 | **Degradation tracking**                                                | SHOULD | Background  |
| CAP-14 | **Fault prediction**                                                    | SHOULD | Background  |
| CAP-15 | **Mission replay capability**                                           | SHOULD | Background  |

## 4. A. Digital Twin Core Framework

"The digital twin core framework **shall** act as the central intelligence layer that continuously mirrors the real aero-piston engine operating onboard the MALE UAV."

| ID     | Requirement                                                                                  | Level  | PS section        |
| ------ | -------------------------------------------------------------------------------------------- | ------ | ----------------- |
| DTC-01 | Core framework acts as the **central intelligence layer**                                    | MUST   | Expected Solution |
| DTC-02 | **Continuously mirrors** the real aero piston engine operating onboard the UAV               | MUST   | Expected Solution |
| DTC-03 | Establishes a **dynamic and continuously synchronized virtual representation** of the engine | SHOULD | Expected Solution |
| DTC-04 | **Virtual engine model synchronized with live engine data**                                  | MUST   | A                 |
| DTC-05 | **Modular architecture for future scalability**                                              | MUST   | A                 |
| DTC-06 | **Real-time data ingestion capability**                                                      | MUST   | A                 |

## 5. B. Health Monitoring System

"The health monitoring system **shall** continuously assess the condition of engine sub-systems and generate health indices for predictive maintenance. Monitoring of following engine parameters are **required**."

| ID     | Requirement                                                 | Level | PS section |
| ------ | ----------------------------------------------------------- | ----- | ---------- |
| HMS-01 | **Continuously assess the condition of engine sub-systems** | MUST  | B          |
| HMS-02 | **Generate health indices for predictive maintenance**      | MUST  | B          |
| HMS-03 | Monitor **RPM**                                             | MUST  | B          |
| HMS-04 | Monitor **Cylinder Head Temperature (CHT)**                 | MUST  | B          |
| HMS-05 | Monitor **Exhaust Gas Temperature (EGT)**                   | MUST  | B          |
| HMS-06 | Monitor **Oil Pressure**                                    | MUST  | B          |
| HMS-07 | Monitor **Oil Temperature**                                 | MUST  | B          |
| HMS-08 | Monitor **Fuel flow**                                       | MUST  | B          |
| HMS-09 | Monitor **Vibration signatures**                            | MUST  | B          |
| HMS-10 | Monitor **Battery / Alternator health**                     | MUST  | B          |
| HMS-11 | Monitor **Injection timing parameters**                     | MUST  | B          |

## 6. C. Fault Detection & Predictive Analytics

"The system **should transition from conventional threshold-based monitoring to intelligent predictive diagnostics**. The detection/prediction of following parameters are **required**."

| ID     | Requirement                                                                               | Level  | PS section |
| ------ | ----------------------------------------------------------------------------------------- | ------ | ---------- |
| FDP-01 | **Intelligent predictive diagnostics** instead of conventional threshold-based monitoring | SHOULD | C          |
| FDP-02 | Detect/predict **misfire conditions**                                                     | MUST   | C          |
| FDP-03 | Detect/predict **injector abnormalities**                                                 | MUST   | C          |
| FDP-04 | Detect/predict **cooling degradation**                                                    | MUST   | C          |
| FDP-05 | Detect/predict **lubrication issues**                                                     | MUST   | C          |
| FDP-06 | Detect/predict **sensor drift / failure**                                                 | MUST   | C          |
| FDP-07 | Detect/predict **combustion instability**                                                 | MUST   | C          |
| FDP-08 | Detect/predict **overheating trends**                                                     | MUST   | C          |
| FDP-09 | Detect/predict **abnormal vibration patterns**                                            | MUST   | C          |

## 7. D. AI/ML Layer

"The AI/ML layer **shall** provide adaptive learning capability for predictive diagnostic and intelligent maintenance planning. Following parameters are **required** to be captured."

| ID     | Requirement                                   | Level | PS section |
| ------ | --------------------------------------------- | ----- | ---------- |
| AIM-01 | **Adaptive learning capability**              | MUST  | D          |
| AIM-02 | Supports **predictive diagnostics**           | MUST  | D          |
| AIM-03 | Supports **intelligent maintenance planning** | MUST  | D          |
| AIM-04 | **Anomaly detection algorithms**              | MUST  | D          |
| AIM-05 | **Remaining Useful Life (RUL) estimation**    | MUST  | D          |
| AIM-06 | **Trend analysis**                            | MUST  | D          |
| AIM-07 | **Predictive maintenance recommendations**    | MUST  | D          |

## 8. E. Simulation & Replay Capability

"The system **should include simulation tools to reproduce engine behavior and analyse mission scenarios**. Following parameters are **required** to be captured."

| ID     | Requirement                                                      | Level  | PS section |
| ------ | ---------------------------------------------------------------- | ------ | ---------- |
| SIM-01 | **Simulation tools to reproduce engine behavior**                | SHOULD | E          |
| SIM-02 | **Analyse mission scenarios**                                    | SHOULD | E          |
| SIM-03 | **Replay of historical mission data**                            | MUST   | E          |
| SIM-04 | **Environmental condition simulation**                           | MUST   | E          |
| SIM-05 | Engine behavior simulation during **high altitude**              | MUST   | E          |
| SIM-06 | Engine behavior simulation during **endurance mission**          | MUST   | E          |
| SIM-07 | Engine behavior simulation during **hot-weather operation**      | MUST   | E          |
| SIM-08 | Engine behavior simulation during **rapid throttle transitions** | MUST   | E          |

## 9. F. Visualization Dashboard

"The dashboard **shall** provide an intuitive operational interface for UAV operators, propulsion engineers and maintenance team."

| ID     | Requirement                                 | Level  | PS section |
| ------ | ------------------------------------------- | ------ | ---------- |
| VIS-01 | **Intuitive operational interface**         | MUST   | F          |
| VIS-02 | Serves **UAV operators**                    | MUST   | F          |
| VIS-03 | Serves **propulsion engineers**             | MUST   | F          |
| VIS-04 | Serves **maintenance team**                 | MUST   | F          |
| VIS-05 | Displays **real-time engine health status** | SHOULD | F          |
| VIS-06 | Displays **fault alerts**                   | SHOULD | F          |
| VIS-07 | Displays **engine efficiency trends**       | SHOULD | F          |
| VIS-08 | Displays **maintenance advisory**           | SHOULD | F          |
| VIS-09 | Displays **mission-wise health reports**    | SHOULD | F          |

---

## 10. Deliverables Expected from Teams

| ID     | Deliverable                                               | Level |
| ------ | --------------------------------------------------------- | ----- |
| DEL-01 | **Functional prototype / software demonstrator**          | MUST  |
| DEL-02 | **Digital twin architecture design**                      | MUST  |
| DEL-03 | **Engine simulation model**                               | MUST  |
| DEL-04 | **AI/ML-based anomaly detection module**                  | MUST  |
| DEL-05 | **Visualization dashboard**                               | MUST  |
| DEL-06 | **Demonstration using simulated or real engine datasets** | MUST  |
| DEL-07 | **Technical documentation and deployment roadmap**        | MUST  |

---

## 11. Permitted Implementation Options: "the system may utilize" (not mandatory)

| ID     | Option                                                | Level                             |
| ------ | ----------------------------------------------------- | --------------------------------- |
| OPT-01 | CAN bus / SocketCAN-based engine data acquisition     | MAY                               |
| OPT-02 | ECU/FADEC communication interfaces                    | MAY                               |
| OPT-03 | Edge computing architecture                           | MAY                               |
| OPT-04 | Cloud or local server-based analytics                 | MAY                               |
| OPT-05 | AI/ML algorithms for anomaly detection                | MAY (also required as AIM-04)     |
| OPT-06 | Physics-informed modelling approaches                 | MAY                               |
| OPT-07 | Dashboard/HMI for operators and maintenance engineers | MAY (also required as VIS-01..04) |

## 12. Desired Innovation Areas (encouraged, not mandatory)

| ID     | Area                                      | Level      |
| ------ | ----------------------------------------- | ---------- |
| INN-01 | Physics-informed AI                       | ENCOURAGED |
| INN-02 | Edge AI for UAV applications              | ENCOURAGED |
| INN-03 | Lightweight onboard analytics             | ENCOURAGED |
| INN-04 | Hybrid thermodynamic + data-driven models | ENCOURAGED |
| INN-05 | Federated learning approaches             | ENCOURAGED |
| INN-06 | Explainable AI for fault diagnosis        | ENCOURAGED |
| INN-07 | Secure telemetry architecture             | ENCOURAGED |
| INN-08 | Autonomous maintenance advisory systems   | ENCOURAGED |

## 13. Technical Expectations: understanding teams must demonstrate

| ID     | Area                    | Level         |
| ------ | ----------------------- | ------------- |
| TEX-01 | IC engine fundamentals  | UNDERSTANDING |
| TEX-02 | UAV propulsion systems  | UNDERSTANDING |
| TEX-03 | Sensor fusion           | UNDERSTANDING |
| TEX-04 | Embedded systems        | UNDERSTANDING |
| TEX-05 | CAN communication       | UNDERSTANDING |
| TEX-06 | AI/ML analytics         | UNDERSTANDING |
| TEX-07 | Data visualization      | UNDERSTANDING |
| TEX-08 | Simulation modelling    | UNDERSTANDING |
| TEX-09 | Reliability engineering | UNDERSTANDING |

---

## 14. What the PS Does _Not_ Explicitly Require

Listed so no one treats these as PS requirements. They may still be useful, but they need their own justification:

- A specific engine model (e.g. Rotax 912 iS) or a specific UAV platform
- Multiple engines or UAV platforms (the PS says "an aero piston engine")
- 3D visualization or 3D models of the engine or airframe
- Photorealistic rendering, terrain, or flight animation
- A chatbot, RAG copilot, or voice interface
- Specific update rates, accuracy figures, or RUL horizons
- Use of real (non-simulated) engine data
- Actual CAN hardware (CAN/SocketCAN is a "may")

---

## 15. Requirement Tracker

Mark each item when it is **demonstrable**, with evidence (demo step, file, or screenshot).

| Group                   | IDs             | Done | Evidence |
| ----------------------- | --------------- | ---- | -------- |
| Overall system          | SYS-01 … SYS-09 | ☑    | `can_streamer.py`, `thermo_model.py`, `engine_service.py`, `tests/test_fun_req_compliance.py` |
| Integration inputs      | INT-01 … INT-09 | ☑    | `lookup_performance_map`, decoupled plant differential ODEs, `test_rotax_performance_maps_and_injection` |
| Capabilities            | CAP-01 … CAP-15 | ☑    | Real-time 20 Hz state estimation, physics residuals, conformal RUL, replay engine |
| A. DT core              | DTC-01 … DTC-06 | ☑    | Decoupled plant model (`plant_rpm`, `plant_map`, `plant_cht_1..4`), dynamic operator throttle drive |
| B. Health monitoring    | HMS-01 … HMS-11 | ☑    | All 14 telemetry channels + `INJ_TIMING_BTDC`, `INJ_PULSE_WIDTH_MS`, `IGN_TIMING_BTDC`, `LAMBDA_AFR`, 2 kHz DFT vibration |
| C. Fault detection      | FDP-01 … FDP-09 | ☑    | Rolling sensor drift detection, residual shielding (`F14`), conventional threshold comparator & lead-time (`F13`) |
| D. AI/ML                | AIM-01 … AIM-07 | ☑    | Pure ML fault classification without shortcut fake echoes, conformal RUL ($P_{10}$, $P_{50}$, $P_{90}$) |
| E. Simulation & replay  | SIM-01 … SIM-08 | ☑    | 4 canonical mission regimes (`LADAKH`, `THAR_DESERT`, `ENDURANCE_LOITER`, `RAPID_THROTTLE_TRANSIENTS`), bisect replay |
| F. Dashboard            | VIS-01 … VIS-09 | ☑    | 3 dedicated role views: Operator (`App.tsx`), Propulsion (`PropulsionEngineerPanel.tsx`), Maintenance (`MaintenanceDashboardPanel.tsx`) |
| Deliverables            | DEL-01 … DEL-07 | ☑    | Full Python FastAPI backend, React + Tailwind GCS, 105 unit/integration tests passing |
| Technical understanding | TEX-01 … TEX-09 | ☑    | Otto thermodynamic cycle, Arrhenius RUL, SAE J1349 aero-piston power lapse, Hann-windowed FFT |

ANUMAAN — PS-26054 End-to-End Coverage Matrix
Verification basis: code read on 2026-09-22 against E:/backup-llm/backup-no-llm/3d_engine/. The existing docs/gap_plan.md audit is dated 2026-09-17; I re-verified every claim in it. Nothing has changed in the code since that audit — backend/evaluation/ still does not exist, drift_detected is still hardcoded, no injection-timing channels exist, no performance maps exist. The gap_plan's statuses are still accurate, plus I found three findings it does not record (listed in §6).

PART 1 — The full requirement set
The requirements are already extracted canonically in E:/backup-llm/backup-no-llm/3d_engine/docs/fun_req.md as 83 MUST/SHOULD items with stable IDs (SYS-01…09, INT-01…09, CAP-01…15, DTC-01…06, HMS-01…11, FDP-01…09, AIM-01…07, SIM-01…08, VIS-01…09) plus DEL-01…07, OPT-01…07, INN-01…08, TEX-01…09. I use those IDs below rather than re-deriving them. Source text: docs/00_official_problem_statement.md §3.A–F, §4, §5, §6. Plain-language interpretation: docs/01_problem_statement_breakdown.md (note §15's mandatory/optional table and §18's "common misinterpretations" list, which is effectively a self-imposed honesty standard).

PART 2 — Requirement → implementation → verdict
A. Digital Twin Core Framework (DTC-01…06)
ID Evidence Verdict
DTC-01 central intelligence layer backend/server/engine_service.py → EngineStateService.\_tick() (line 233), singleton via get_instance(), 20 Hz authoritative loop \_run_loop() (line 218) FULLY
DTC-02 continuously mirrors the real engine backend/telemetry/can_streamer.py → TelemetryStreamer.generate_frame() builds "actual" as expected_state.<field> + random.gauss(...) (lines 175–204). The plant is the twin. NOT IMPLEMENTED (structurally circular)
DTC-03 dynamic synchronized representation Same as above PARTIAL
DTC-04 synchronized with live engine data No external data path exists NOT IMPLEMENTED
DTC-05 modular architecture Real package split: physics/ ml/ telemetry/ server/ agent/ graph/ knowledge/ reports/ voice/; but no engine_id/platform_id anywhere, Rotax constants are module-level in thermo_model.py lines 13–25, fault IDs hardcoded 0..8 PARTIAL
DTC-06 real-time data ingestion Only in-process generator. `grep python-can socketcan
B. Health Monitoring (HMS-01…11) — the 8 monitored parameter groups
ID Parameter Evidence Verdict
HMS-01/02 subsystem assessment + health indices engine_service.py:463-507 computes subsystem_health = propulsion/fuel_system/electrical/thermal/mechanical from residuals FULLY
HMS-03 RPM EnginePhysicalState.ENGINE_RPM/PROP_RPM, thermo_model.py:32-33 FULLY
HMS-04 CHT CHT_1..4, per-cylinder, residuals d_CHT_1..4 FULLY
HMS-05 EGT EGT_1..4, residuals d_EGT_1..4 FULLY
HMS-06/07 Oil pressure & temp OIL_PRESS, OIL_TEMP FULLY
HMS-08 Fuel flow FUEL_FLOW (+ FUEL_RAIL_P) FULLY
HMS-09 Vibration signatures Single scalar VIB_GEARBOX_RMS @ 20 Hz. backend/ml/spectral_analyser.py:176 → use_rms_fallback = target_hz > nyquist_hz is always True at 20 Hz (3× prop order ≈ 106 Hz vs 10 Hz Nyquist). The DFT code in \_compute_dft_magnitudes() never executes. PARTIAL — one scalar, no spectrum
HMS-10 Battery/alternator BUS_VOLTAGE, BATTERY_CURRENT only. No SoH, no internal resistance, no alternator capacity model PARTIAL
HMS-11 Injection timing grep -rn "INJ_TIMING|injection_timing|IGN_TIMING|spark_advance|pulse_width" across backend/ frontend/src apps/ scripts/ tests/ → zero hits NOT IMPLEMENTED
C. Fault Detection & Predictive Analytics (FDP-01…09)
Detector stack: backend/ml/detection_pipeline.py → DetectionPipeline.process_frame() (9 stages), \_classify() (line 399, RF + physics-boundary fallback), MajorityVoteBuffer (line 98), plus backend/ml/fault_classifier.py → RotaxFaultClassifier.classify().

The 8 PS fault targets do not map 1:1 onto the 8 implemented faults in can_streamer.py DRDO_FAULT_DEFINITIONS:

PS target Implemented as Verdict
FDP-02 Misfire Fault 3 IGNITION_MISFIRE — EGT_2 drop + RPM flutter (can_streamer.py:237-247). No per-cylinder, no crank-angle. Worst class in metrics (recall 0.836) PARTIAL
FDP-03 Injector abnormalities Fault 2 FUEL_INJECTOR_1_CLOG (can_streamer.py:224-235) PARTIAL (clog only; no timing drift, no response delay)
FDP-04 Cooling degradation Fault 1 CYLINDER_2_CHT_OVERHEAT PARTIAL — shares one fault with FDP-08
FDP-05 Lubrication issues Fault 4 OIL_PRESSURE_LOSS PARTIAL (pressure loss only)
FDP-06 Sensor drift/failure sensor_validator.py catches RATE_SPIKE / FROZEN_ADC / isolated spike. Drift is hardcoded off: sensor_validator.py:263 drift_detected=False, # populated by trend analyser, not here; detection_pipeline.py:313 and :620 also literal False; engine_service.py:457 literal False; frontend/src/hooks/useTelemetrySocket.ts:62 literal false. Nothing populates it. NOT IMPLEMENTED (field exists, always False)
FDP-07 Combustion instability Only Fault 6 EXHAUST_EGT_IMBALANCE. No COV-of-IMEP, no cycle-to-cycle variance PARTIAL
FDP-08 Overheating trends Fault 1 again + trend_analyser.DegradationTrendAnalyser PARTIAL
FDP-09 Abnormal vibration Fault 5 GEARBOX_VIBRATION on scalar RMS PARTIAL
FDP-01 transition away from thresholds Real: physics residuals + autoencoder + RF + majority vote. But never measured against a threshold baseline — `grep threshold_baseline	lead_time` → zero hits
Extra faults not in the PS list: Fault 7 ALTERNATOR_VOLTAGE_SAG, Fault 8 DUAL_FADEC_ECU_DRIFT.

D. AI/ML Layer (AIM-01…07)
ID Evidence Verdict
AIM-01 adaptive learning `grep partial_fit retrain
AIM-02 predictive diagnostics Pipeline exists; no lead-time evidence PARTIAL
AIM-04 anomaly detection backend/ml/anomaly_detector.py → ResidualAutoencoder (14→8→4→8→14, pure-Python, train() line 162, score() line 331, percentile threshold calibration line 314). Composite = max(ae_score, residuals.anomaly_score) at detection_pipeline.py:335 FULLY (algorithm); PARTIAL (validation)
AIM-05 RUL backend/ml/trend_analyser.py → ProbabilisticRULEstimator.estimate() (line 461), 500-sample Monte Carlo over fit uncertainty → p10/p50/p90. Trend models: linear / exponential / power-law with AIC selection (\_least_squares_linear, \_fit_exponential, \_fit_power_law, \_aic). Runs in PrognosticsWorker background thread (line 616) FULLY (mechanism); PARTIAL (unvalidated — no RUL error measured)
AIM-06 trend analysis DegradationTrendAnalyser.analyse() (line 267), \_time_to_breach() (line 403) FULLY
AIM-07 maintenance recommendations DetectionPipeline.PRESCRIPTIVE_ACTIONS (line 183), backend/agent/diagnostic_agent.py → DiagnosticAgent.diagnose() returning ATA chapter + manual ref + emergency checklist + maintenance order FULLY
AIM-03 maintenance planning ProbabilisticRULEstimator.go_no_go() (line 546); CBM work orders mission_graph.get_work_orders() / sign_off_action(); API /api/cbm/maintenance, /api/cbm/maintenance/{id}/signoff FULLY (API); no UI
E. Simulation & Replay (SIM-01…08) — including the 4 named regimes
ID Evidence Verdict
SIM-03 historical replay backend/telemetry/replay_engine.py → ReplayEngine.list_manifests/get_manifest/get_frame (bisect-indexed, reads report_dump/mission_NNN/). API /api/replay/\* in main.py:253-276. UI frontend/src/components/MissionReplayScrubber.tsx + hooks/useMissionReplay.ts. 54 mission bundles exist in report_dump/. FULLY
SIM-04 environmental simulation RotaxThermoModel.get_ambient_properties() (ISA barometric) + compute_expected_state() are genuinely altitude/OAT-dependent. But SET_ALTITUDE/SET_OAT (engine_service.py:631-639) only set display fields applied at \_tick step 3 (lines 256-257) — the sensor values come from streamer.get_flight_context()'s own sinusoid. PARTIAL
SIM-05 High Altitude LADAKH region preset (18,500 ft) in can_streamer.py:113-120 and SET_REGIME snapping at engine_service.py:646-648 PARTIAL — a region preset, not a mission regime
SIM-06 Endurance Only via scripts/simulate_missions.py (MISSION_PROFILES — 10–18 h sorties, time-accelerated by driving \_tick() directly). Not selectable live. PARTIAL
SIM-07 Hot-weather THAR_DESERT preset (4,500 ft / +44 °C) PARTIAL
SIM-08 Rapid throttle transitions Not in the live twin at all. get_flight_context() returns CRUISE_LOITER for every region (can_streamer.py:120,128,135). Throttle transients exist only offline in backend/telemetry/rotax_dataset_generator.py throttle_pattern="GUST_TRANSIENTS" / "STEP_LOITER" (lines 122-133), with real first-order dynamics (τ_map 0.15 s, τ_rpm 0.40 s, τ_ff 0.20 s, lines 143-155) and CLIMB→CRUISE_LOITER→DESCENT_RECOVERY phases. NOT IMPLEMENTED live / PARTIAL offline
SIM-01/02 scripts/simulate_missions.py runs the real tick loop headless PARTIAL
Worth flagging for your plan: the higher-fidelity plant you need for G01 already exists in rotax_dataset_generator.py — thermal lags, RPM inertia, phase sequencing, throttle patterns. It just isn't the thing the live twin watches.

F. Visualization Dashboard (VIS-01…09)
frontend/src/App.tsx has exactly 4 tabs: PILLAR_1 | AI_DIAGNOSTICS | VOICE_COPILOT | MISSION_REPLAY.

ID Evidence Verdict
VIS-01 intuitive interface React + Tailwind, PanelErrorBoundary per panel FULLY
VIS-02 operators EngineControls.tsx, FaultMatrix.tsx, MissionReadinessCard.tsx FULLY
VIS-03 propulsion engineers No dedicated view. CalculationsPanel.tsx + ReadingsPanel.tsx show residuals, but no spectra, no feature attribution, no timing PARTIAL
VIS-04 maintenance team No UI at all — work orders are API-only NOT IMPLEMENTED (API exists, no view)
VIS-05 health status SubsystemHealthCard.tsx (5 subsystems) FULLY
VIS-06 fault alerts FaultMatrix.tsx, DiagnosticCard.tsx FULLY
VIS-07 efficiency trends grep -rni "bsfc|specific*fuel|efficiency_trend|engine_efficiency" → zero hits in backend and frontend NOT IMPLEMENTED
VIS-08 maintenance advisory DiagnosticCard.tsx renders prescriptive_action + maintenance_order + emergency_checklist FULLY
VIS-09 mission-wise reports backend/reports/mission_bundle.py → build_and_write_mission_bundle() emits 7 categories; backend/graph/mission_reporter.py; 54 bundles in report_dump/; 100+ markdown debriefs in data/mission_reports/ FULLY
Deliverables (DEL-01…07)
ID Evidence Verdict
DEL-01 prototype run_app.py, 7 launch*_.bat, FastAPI server, React GCS, 3 standalone apps FULLY
DEL-02 architecture design analysis/engineering/02*system_architecture_and_dual_plane.md, analysis/strategy/02*_ — but written pre-audit PARTIAL
DEL-03 engine simulation model thermo_model.py (steady-state algebra, no dynamics/estimator) + rotax_dataset_generator.py (has dynamics) PARTIAL
DEL-04 AI/ML anomaly module anomaly_detector.py + fault_classifier.py + rotax_random_forest.joblib (2.1 MB) FULLY (module); PARTIAL (validation)
DEL-05 dashboard frontend/src/ FULLY
DEL-06 demonstration with datasets See §5 — source1_avionics_logs/ is empty (0 files) PARTIAL
DEL-07 documentation & roadmap 8 docs/\*.md + 6 docs/audit/ + 27 docs/study/ + 6 docs/assets/ + analysis/. No deployment roadmap document found PARTIAL
Desired Innovation Areas (INN-01…08)
ID Verdict Evidence
INN-01 Physics-informed AI FULLY — the entire ML stack operates on physics residuals, never raw values
INN-02 Edge AI DOCUMENTED-ONLY — docs/study/05_edge_ai.md, 13_edge_vs_ground_split.md. No separate edge process; grep "edge_ai|federated" → zero code hits
INN-03 Lightweight onboard analytics PARTIAL — anomaly_detector.py is pure-Python/numpy-free (genuinely lightweight, deliberate); latency test at tests/test_ml_classifier.py:70
INN-04 Hybrid thermo + data-driven FULLY — physics baseline + RF + AE
INN-05 Federated learning NOT IMPLEMENTED — zero hits anywhere
INN-06 Explainable AI PARTIAL — DiagnosticDirective.causal_chain (agent/diagnostic_agent.py:30) is a hand-authored per-fault string list, not model-derived. Real XAI = feature_importances in model_metrics.json (offline only, not surfaced in UI). No SHAP/attribution
INN-07 Secure telemetry NOT IMPLEMENTED — no HMAC/signing/encryption anywhere
INN-08 Autonomous maintenance advisory FULLY — DiagnosticAgent + CBM work orders + MissionCopilot.diagnose_with_ai() (RAG + Qwen3-4B)
Technical Expectations (TEX-01…09)
ID Verdict Evidence
TEX-01 IC engine fundamentals FULLY — Otto cycle, VE, AFR, density altitude in thermo_model.py; docs/study/24_combustion_cycle_and_crank_dynamics.md
TEX-02 UAV propulsion FULLY — Rotax 912 iS geometry, i=2.43 gearbox, docs/study/02, 03
TEX-03 Sensor fusion PARTIAL — 14-channel residual vector; dataset_fusion_engine.py fuses 3 sources; but no Kalman/observer (G17), no redundancy voting
TEX-04 Embedded systems DOCUMENTED-ONLY — docs/study/03_ecu_can_acquisition.md; no embedded code
TEX-05 CAN communication DOCUMENTED-ONLY — module is named can_streamer.py but contains no CAN: no frames, no IDs, no DBC, no python-can dependency
TEX-06 AI/ML analytics FULLY
TEX-07 Data visualization FULLY
TEX-08 Simulation modelling PARTIAL
TEX-09 Reliability engineering PARTIAL — Arrhenius thermal, cubic vibration wear laws in rul_estimator.py:60-94; FMECA doc in data/documents/; no FMEA-in-code, no MTBF
§3 — backend/ml/models/model_metrics.json in detail

Methodology : "Strict Mission-Level Group Isolation (Train / Val / Test)"
Missions : 10 train / 10 val / 10 test (30 total)
Samples : 9,000 / 9,000 / 9,000
Validation : accuracy 0.9931 · macro-F1 0.9926
Held-out : accuracy 0.9751 · macro-F1 0.9748 ← the number to quote
Leakage : mission_overlap 0 · temporal_lookahead_leakage false · feature_engineering_causal true
Timestamp : 1788347972.75 (file mtime 2026-09-02)
Per-fault on held-out test (precision / recall / F1, support):

Class P R F1 n
FAULT_0 nominal 0.9646 0.9851 0.9747 4368
FAULT_1 CHT overheat 1.0000 0.8359 0.9106 579
FAULT_2 injector clog 0.9965 0.9965 0.9965 579
FAULT_3 misfire 0.9983 0.9914 0.9948 579
FAULT_4 oil press loss 1.0000 0.9775 0.9886 579
FAULT_5 gearbox vib 0.9847 1.0000 0.9923 579
FAULT_6 EGT imbalance 0.9316 0.9879 0.9589 579
FAULT_7 alternator sag 0.9914 0.9983 0.9948 579
FAULT_8 FADEC drift 0.9873 0.9378 0.9619 579
Confusion-matrix reading (row = true):

Fault 1 → nominal: 95 of 579 (16.4 %) missed. This is the entire macro-F1 loss. Every Fault-1 error is a miss, never a misclassification — consistent with the onset ramp (severity < detection gate during early ramp). Note 04_feature_spec.md F02 targets exactly this class.
Fault 8 → nominal: 35 missed (6 %), + 1 → Fault 3.
Nominal false alarms: 65 of 4368 (1.49 %) — 42 of them into Fault 6, which is why Fault 6 precision (0.9316) is the lowest in the matrix.
Faults 2/3/4/5/7 are essentially perfectly separated (0–2 cross-class confusions).
Feature importances (14 residual channels, sum ≈ 1.0): RES_d_OIL_PRESS 0.1076 (top) · d_CHT_2 0.0915 · d_BUS_VOLTAGE 0.0825 · d_OIL_TEMP 0.0819 · d_EGT_3 0.0814 · d_EGT_2 0.0804 · d_VIB_RMS 0.0803 · d_CHT_1 0.0784 · d_MAP 0.0762 · d_EGT_1 0.0675 · d_CHT_3 0.0649 · d_CHT_4 0.0591 · d_FUEL_FLOW 0.0447 · RES_d_EGT_4 0.0036 (essentially unused — no fault targets cylinder 4's EGT).

Critical context the file does not state (from backend/telemetry/rotax_dataset_generator.py:390-484 + export_mission_to_csv):

Each "mission" is 45 simulated seconds @ 20 Hz = 900 rows. 30 missions = 22.5 minutes of total simulated data, not 30 sorties.
One fault type per mission, so "mission-level isolation" and "fault-level isolation" are the same partition — a real confound for the isolation claim.
Splits are genuinely domain-shifted: TRAIN = SMOOTH_LOITER, seeds 101–110, noise ×1.0; VAL = STEP_LOITER, alt ±2200 ft, OAT ±4.5 °C, seeds 201–210, noise ×1.2; TEST = GUST_TRANSIENTS, alt ±3000 ft, OAT ±7 °C, seeds 301–310, noise ×1.5. That shift is real and worth defending.
But the fault-signature code is identical across splits, which is exactly G03's circularity charge.
backend/ml/models/autoencoder_metrics.json is a separate companion file (1.3 KB) not covered here.
§4 — What the test suite in tests/ actually covers
71 test methods across 10 files. pytest.ini present. gap_plan.md records 73 passing (the 7 non-LLM files).

File n Covers Does not cover
test_analytical_pipeline.py (788 L, largest) 33 Sensor validator (5), autoencoder (6), spectral analyser (6), trend fitting (5), probabilistic RUL (4), ScoreBuffer incl. concurrency (3), MajorityVote (4), DetectionPipeline (4), PrognosticsWorker (2). Contains the only genuine PS-capability tests: TestPS_Pillar2_EarlyWarning::test_trend_detected_before_absolute_threshold and ::test_time_to_threshold_decreases_as_fault_develops (lines 638–747) Lead time vs a threshold monitor; false-alarm rate
test_physics_and_telemetry.py 10 ISA ambient for Ladakh/Thar, nominal baseline, near-zero nominal residual, faults 1/2/4/5/7 signature direction, flight-log generation Faults 3, 6, 8; transients; environment→physics response
test_ml_classifier.py 5 All 8 faults classify, Thar robustness, inference latency budget, Go/No-Go Uses the standalone RULEstimator, which is not the live estimator
test_server_api.py 6 /, /api/health, /api/state schema, fault activate/clear, throttle+env commands, engine stop/start, debrief export Asserts commands return SUCCESS, not that physics changed — this is exactly why G02 survived
test_causal_propagation.py 2 test_streamer_fault_causality (multi-channel coupling per fault), test_engine_service_dynamic_subsystems
test_rotax_dataset.py 4 10 sorties exist, cross-parameter coupling, fault divergence, serialized RF runtime inference
test_dataset_fusion.py 4 NASA C-MAPSS ingest, end-of-life labelling, tri-source merge, empty-source handling
test_agent_and_graph.py 9 ATA grounding, unknown-fault fallback, sortie lifecycle, report generation, graph persistence round-trip, region comparison
test_copilot_and_knowledge.py 8 Loader/chunker, store query, guardrails, diagnostic synthesis, live-state block, relevance threshold, Whisper non-speech strip
test_voice_copilot.py 10 Guardrails, fault grounding, follow-ups, session isolation/eviction, no-fault-echo
Coverage shape: strong unit coverage of every algorithm; zero end-to-end PS-outcome tests (no lead-time, no false-alarm rate, no RUL error, no threshold baseline, no scenario tests for the 4 named regimes). 27 of 71 tests (38 %) cover voice/copilot/knowledge — which the PS does not require (docs/fun_req.md §14).

§5 — Beyond-scope: code that exists but no requirement asks for
Per docs/fun_req.md §14, the PS requires none of: a specific engine, 3D models, rendering, terrain, chatbot/RAG/voice.

Component LOC / size PS status
backend/voice/ (stt*engine, tts_engine, conversation, thinking_stream) + VoiceCopilot.tsx (869 L) ~1,340 Zero PS basis. 04_feature_spec.md §6 says cut
backend/agent/ (copilot.py 1,190 L, llm_engine.py, flight_intent.py) + Qwen3-4B/ ~1,950 INN-08-adjacent; feature spec says constrain to retrieval-with-citation
backend/knowledge/ (loaders + embedding index + reranker) ~580 Supports the above
apps/blender_twin/standalone_canyon_flight_app.py 2,366 L Pure cinematics. 01_problem_statement_breakdown.md §15 lists this exact thing as ⬜ scope creep
apps/blender_twin/standalone_digital_twin_app.py + flight_mission_recorder.py 1,888 Legitimate GCS skin (VIS), correctly a data consumer
apps/mission_graph_viewer/ 1,577 Supports VIS-09
apps/desktop_gcs/standalone_gui_app.py 521 Alternative HMI
scripts/ UAV harvesting + texture generation (harvest_all_uavs\*.py, generate_tb3*_textures.py, build*bayraktar_tb3.py, build_tei_pd170.py, build_austro_ae330.py, render*_, 12 test\_\*.py Blender probes) ~large Entirely outside PS. Different aircraft/engines
web/usavionix, docs/pitch/usavionix_frames/ (23 webp) — Competitor site teardown
vendor/, compiled_tb/, build/, scratch/, Qwen3-4B/, Voice/, Datasets/ (11 categories) — 04_feature_spec.md §6: clean before anyone browses the repo
Feature-spec's own measurement: ~3,000 lines sit outside the PS while backend/physics/ — the module everything rests on — is the smallest core module at 577 lines (thermo_model.py 300 + sensor_validator.py 274). My count confirms it.

§6 — Documentation claiming what the code does not do
docs/02_comprehensive_audit_summary.md, docs/03_implemented_features_technical_deep_dive.md, docs/gap_plan.md and docs/audit/\* are honest — 03 even documents the drift_detected gap inline. The problems are elsewhere:

1. README.md is severely stale — highest-embarrassment item. It documents a tree that does not exist. Verified missing: 3d_models/, Models/, unity_bridge/ (10 named C# files), renders/, reverse_engineering_suite/, scripts/blender/ (21 named scripts), scripts/rendering/ (7), scripts/utils/ (9). It also points at docs/01_problem_statement_and_analysis.md … docs/05_master_build_guide.md, none of which are in docs/ (they live under analysis/strategy/). A judge opening the repo README first sees a manifest of ~50 files that aren't there.

2. ⚠️ NOT IN gap_plan.md — the live dashboard echoes the ground-truth fault label. backend/server/engine_service.py:330-334:

# If an active fault was commanded by operator, that is the authoritative active scenario

if self.active_fault_id > 0:
diag_fid = self.active_fault_id
diag_fname = DRDO_FAULT_DEFINITIONS[diag_fid]["name"]
diag_conf = max(0.95, p.get('confidence', 0.98))
When an operator injects a fault from FaultMatrix.tsx, analytics.diagnosed_fault_id and the ≥0.95 confidence shown on the dashboard are the commanded label passed straight through, not a classifier output. The RF/physics classifier path (:337-351) only runs when active_fault_id == 0. So the headline demo moment — "inject fault → system identifies it" — is not a detection. This is a distinct problem from G01 and is directly what 01_problem_statement_breakdown.md §18 calls out. It is the single most important thing to fix before a demo.

3. ⚠️ NOT IN gap_plan.md — two inconsistent "expected" states per tick. \_tick() computes residuals at line 265 against the expected returned by streamer.generate_frame() (built at the profile altitude/OAT), while pipeline.process_frame() at line 268 recomputes its own expected from actual.ALTITUDE_FT / actual.OAT_C (the operator-overridden values, set at lines 256-257). Moving the altitude slider therefore makes the pipeline's expected state diverge from sensor values that were never generated at that altitude — injecting a synthetic residual. docs/03 §2 explicitly claims a "deliberate single point of definition for what normal means right now"; there are two.

4. ⚠️ RULEstimator reads the ground-truth label. backend/ml/rul_estimator.py:89-94 branches on actual.FAULT_ID == 1/4/5 to accelerate wear. It is not wired into the live service (only tests/test_ml_classifier.py uses it; live uses ProbabilisticRULEstimator), but it is exported from backend/ml/**init**.py and will read as label leakage to anyone auditing.

5. "can_streamer.py" / "CAN / FADEC telemetry frames" (docstring lines 1-8, 76-79) — there is no CAN anywhere. Same for TEX-05 claims.

6. Docstring/rate mismatches. \_tick docstring: "one 120 Hz physical state update" (engine_service.py:234) while the loop is 20 Hz (:220). get_flight_context annotated -> Tuple[float,float,float,float,str] (5) but returns 6 values (can_streamer.py:108,137).

7. Dataset claims exceed data present (G18, confirmed). data/telemetry/source1_avionics_logs/ = 0 files, yet garmin_parser.py is titled "Source 1" and the fusion engine advertises tri-source. source2_nasa_benchmarks/ = 1 file (C-MAPSS train_FD001, turbofan data mapped onto a piston schema). source3_drdo_missions/ = 10 files, all synthetic. Also data/telemetry/rotax912_dataset_manifest.json contains absolute paths from another machine (E:\TalentForge\Clay\...) — G22.

§7 — docs/audit/ — what the earlier audit proposes (build on, don't duplicate)
docs/audit/README.md — three findings
We are second, not first. 21 repos found, 15 analysed, 11 in depth. PRAHARI (github.com/atharv20s/sih-26) leads at 85/100 — physics-informed NN + PPO controller + ablation studies + signed telemetry. ANUMAAN scores 79. Third place is one point behind.
The paradigm is saturated. All 11 teams built the identical stack (physics residuals → IsolationForest/RandomForest → health index → RUL vs TBO → dashboard). Both differentiators originally proposed in docs/study/rnd_solution_report.md (sensor validation, mission-conditioned RUL) were already built by competitors, some better. No incremental win exists inside this frame.
The opening: 0 of 11 teams do any real vibration signal processing. No order tracking, no envelope analysis, no kHz acquisition — everyone uses one scalar RMS, despite 5 of the PS's 8 fault targets living in the vibration spectrum. ANUMAAN already has the theory (docs/study/06_vibration_analysis.md), the bandwidth argument (05_edge_ai.md), and Nyquist-aware DFT code that is written and dormant.
Three self-corrections recorded (all in our favour): the spectral analyser is not buggy (Nyquist-aware and correct); we do use strict mission-level group isolation; evaluation rigour is our best axis, not our worst — we publish held-out metrics + per-class P/R/F1 + full confusion matrix while competitors quote bare accuracy. Net: 74→79, third→second.

docs/audit/04_feature_spec.md — 30 features, 5 tiers
Positioning: "ANUMAAN — the digital twin that measures combustion directly. Eight slow scalars tell you an engine is unwell. The crankshaft tells you which cylinder, on which cycle, and how often."

Tier 0 — Keep (11 items, no work). thermo_model, sensor_validator, fault_classifier, anomaly_detector, rul_estimator, trend_analyser, telemetry, FastAPI+WS+React, 3D/replay, and the evaluation harness ("best in field — publicise it").
Tier 1 — The differentiator (F01–F08), 0/11 competitors have any:
F01 crank-angle-resolved telemetry generator — Wiebe heat release → p(θ) → gas+inertial torque → ω(θ) → accelerometer a(t) @ 2–10 kHz. Rule: faults modify p(θ), never the output signal. Validation: healthy 4-cyl must show dominant order-2. Effort High — hardest item, everything depends on it, build first.
F02 per-cylinder misfire detector — TDC-to-TDC ω segmentation, torque deficit names the cylinder; no classifier. SAE 960039. "Highest payoff item in the project" — directly attacks the 0.8359-recall class.
F03 combustion instability — COV of per-cylinder IMEP. Low effort, reuses F02.
F04 tach-synchronous angular resampling (order tracking) — speed-invariant features. Medium.
F05 order-domain features — orders 0.5/1/2/4, GMF + sideband energy, spectral kurtosis, crest factor. Low.
F06 envelope analysis — bandpass → Hilbert → FFT → BPFO/BPFI bearing tones. Low (SciPy). Our own Part VI: worth more than any model-architecture choice.
F07 activate the dormant DFT — pass sample_rate_hz=10000. Trivial.
F08 edge feature compressor + bandwidth meter — kHz → ~200 bit/s. Low, very high demo value.
Tier 2 — Credibility (cheap, nobody has it): F12 conformal RUL (split-conformal, empirical-vs-nominal coverage plot; 0/11 have calibrated uncertainty; ~100 lines; highest credibility-per-hour in the plan) · F13 threshold-baseline comparator (lead time + FA/hr vs naive limit check; 0/11 measure this; do FIRST — makes everything quotable) · F14 residual shielding (zero residuals on quarantined channels; hours) · F15 edge/ground process separation + link-loss demo (0/11 demo link loss) · F16 C-MAPSS external validation · F17 UNKNOWN/novelty path · F18 ablation harness (physics-only vs ML-only vs hybrid).
Tier 3 — Visualisation (F19–F24), test: "does it show something the charts cannot?": per-cylinder residual heat map (not absolute temp) · firing-order animation with the misfiring cylinder visibly skipping ("the single most legible output in the whole system") · live order-spectrum waterfall · sensor-trust overlay · degradation ghost · bandwidth meter.
Tier 4 — only with slack: F25 JAX differentiable physics · F26 particle-filter RUL · F27 foundation-model baseline · F28 HMAC signed telemetry · F29 federation hooks · F30 test-rig mode.
§6 Cut/constrain: cut backend/voice; constrain backend/agent to retrieval-with-citation; trim backend/knowledge; clean scratch/, Qwen3-4B/, backups, 33 MB site assets.
Build order: F13 → F12 → F14 → F01 (risk gate) → F02 → F03 → F04/05/06/07 → F08 → F15 → F20/F21/F19 → F16 → F17/F18. If F01 fails to produce a plausible healthy order spectrum, stop — the existing 20 Hz pipeline already scores 79 on its own.
§8 — How the two plans relate (so you don't build twice)
gap_plan.md (G01–G22) and 04_feature_spec.md (F01–F30) were written independently and overlap on three items — do these once:

Do once gap_plan feature_spec
Threshold baseline + lead time G03 (part 3) F13
kHz vibration + order spectra G04 F01/F04/F05/F07
Edge/ground process split + transport G11 F15
Residual shielding on failed channels (implied by G05) F14
Only in gap_plan: G01 independent virtual engine · G02 controls→physics · G05 drift detection · G06 injection timing (HMS-11, a MUST with zero code) · G07 performance maps (INT-01, a MUST with zero code) · G09 efficiency trends (VIS-07, zero code) · G10 three role views · G12 the four named mission regimes (SIM-05…08) · G17 state estimator · G19 multi-engine · G20 architecture/roadmap doc.

Only in feature_spec: F02/F03 crank-angle diagnostics · F12 conformal RUL · F16 C-MAPSS external validation · F17 UNKNOWN class · F18 ablation · F19–F24 diagnostic visualisation.

My read of the tension: the feature spec optimises for competitive differentiation; the gap plan optimises for literal PS compliance. Three PS MUST items — HMS-11 injection timing, INT-03 performance maps, VIS-07 efficiency trends — have literally zero lines of code and appear nowhere in 04_feature_spec.md. A judge scoring against the requirement list will find those before they find your order spectrum. The cheapest path that serves both: F13 + F14 + F12 (days, from the feature spec) alongside G06 + G09 (days, closing two zero-code MUSTs), then the G01/F01 risk gate.

Agent "Map PS requirements to our implementation" finished
You've hit your session limit · resets 2:10pm (Asia/Kolkata)

I have enough evidence. Here is the audit.

Audit: three SIH PS‑26054 competitor repos
Bottom line up front: none of the three has crank‑angle‑resolved thermodynamics, none does real vibration DSP (zero FFT/Hilbert/envelope/order‑tracking anywhere in 45k+ lines across all three), and none does conformal prediction. They differ enormously in evaluation honesty: repo 1 and repo 3 have genuine group‑level splits and self‑reported negative results; repo 2's "RUL" is a hardcoded lookup table.

1. atharv20s/sih-26 — "PRAHARI"
   ~8,830 LOC (src/ + scripts/ + frontend/). Single commit 0a6fcea, 2026‑09‑15.

A) Physics — real but algebraic, not crank‑angle
E:\backup-llm\backup-no-llm\3d_engine\competitors\atharv20s\sih-26\src\sim\engine_sim.py (593 lines) is the only physics. EngineSim.\_sensor_step() is a set of closed‑form algebraic relations, fully vectorised over the whole run — no ODE integration, no cycle, no Wiebe, no cylinder pressure:

cht = 150 + heat*r_th*55 + 0.30*(rpm/2850)*10 (called "Fourier‑style" in the comment; it is a linear fit)
egt = 640 + heat*(1/eta_c)*45, map = 62*eta_v*(0.50+0.75*throttle), torque = 38*power*mu_f*3.0
Degradation is \_degradation_signals(): six mechanisms (eta_c, mu_f, r_th, eta_v, eta_lub, vib) as 1 ± c·loss^e with tuned coefficients. Health \_health_trajectory() is a logistic wear curve, and \_find_failure() is a first‑crossing scan over five hard limits. Crank angle is explicitly decorative: line 392–396 — seg["crank_pos"] = self.\_rng.uniform(0.0, 720.0), commented "decorative phase sensor for the dashboard", yet it is channel 10 of the 12 fed to every model.

The archetype failure_bias dict in generate_fleet() is honest engineering — four failure modes are steered by biasing coefficients so all four actually fire, with the tuning process documented against scripts/probe_sim.py.

B) ML — the PINN is real; the classifier is admitted broken
src\pinn\pinn_model.py (259 lines) — genuinely a PINN. total_loss() computes L_data + λ_f·L_fourier + λ_c·L_consistency:

compute_physics_targets() denormalises the window back to °C/L·h via registered norm_min/norm_max buffers, then forms g_fourier = softplus(log_alpha)*q_in − softplus(log_beta)*ΔT. α and β are learnable nn.Parameters.
fourier_loss() = MSE(pred_grad, g_fourier) + 0.5\*MSE(pred_grad, dcht_empirical) — a second head fc_grad predicts dT/dt and is grounded to both the empirical finite difference and the Fourier form.
consistency_loss() penalises relu(−dCHT·dEGT) — anti‑correlated thermal derivatives.
train_pinn.py::train_loop() ramps λ from 0→full over the first 30% of epochs (a legitimate PINN convergence fix, line 110–117).

Committed weights (5 files, 1,032 KB total): pinn_best.pt (725 KB), fault_classifier{,\_seed1,\_seed2}.pt (~95 KB each), drl_policy.pt (34 KB). DRL is real PPO (src\drl\drl_agent.py::train_drl_agent, GAE‑free discounted returns γ=0.98, clipped surrogate, ActorCritic(state_dim=18) matching engine_env.\_get_observation()).

Missing: cnn_pca_best.pt and cnn_raw_best.pt — the two ablation baselines train_pinn.py writes and the README's ablation table depends on — are not committed. The headline "physics loss helps" comparison is not reproducible from the repo.

C) Vibration — scalar RMS only
vibration_rms is one number per cycle: NOMINAL*vib*(0.70+0.55\*throttle). Zero DSP anywhere — a repo‑wide grep for fft|welch|hilbert|envelope|order.track|resampl|scipy.signal|kurtosis|crest returns only false positives on the word "envelope" (flight envelope). No sample rate exists; the unit is "cycles" at a nominal 10 Hz WebSocket tick.

D) Sensor validation — present, but weaker than advertised
src\agent\orchestrator.py::sensor_auditor_node() (line 131): NaN/inf check + boundary plausibility (val < lo*0.5 or val > hi*1.5) against NOMINAL_LIMITS. On failure it imputes last valid frame, else range midpoint. No rate limits, no stuck/frozen detection, no cross‑channel test.

src\agent\defense_layers.py (175 lines) is the good part — five clean pure functions: fuse_sensor_and_physics() (confidence‑weighted), vote_fault_classification() (N‑of‑M majority + agreement score), sign_packet()/verify_packet() (real HMAC‑SHA256 with hmac.compare_digest + 2‑second replay window), decide_action_mode() (safe‑mode gate), compute_trend_risk() (multi‑channel np.polyfit slope agreement).

fusion_node() only fuses cht and egt, and the "physics estimate" is np.mean(buffer[-6:-1]) — a 5‑sample moving average, described in the docstring as playing "the same role a Kalman filter's prior plays". No Kalman filter exists.

E) RUL + uncertainty — no uncertainty at all
PINN regresses a point RUL. pinn_engine_node() EMA‑smooths it (α=0.08) and emits predicted_rul. There is no interval, no quantile, no ensemble spread, no conformal, no coverage check. The audit_sample() "is_physically_valid" flag is a fixed residual_threshold=5.0.

F) Evaluation — the strongest integrity in the set
scripts\build_dataset.py assigns split per engine (line 138–146) — real group isolation. Normaliser and PCA fit on train windows only (line 179–228).
--early-life-frac 0.60 produces clf_early_life_mask.npy restricting the classifier to the first 60% of life, and the code prints a leakage WARNING if you set it to 1.0 (line 209–212).
src\eval\benchmarks.py::evaluate_classifier_ensemble() independently re‑scores all three checkpoints on the held‑out test split.
MODEL_CARD.md lines 73–91 report: PINN test MAE 37.07 / RMSE 66.95 cycles; classifier self‑reported 100.0% but independently re‑verified 46.7%, with ensemble mean agreement 100% — and explicitly concludes the three seeds "converged to the same leakage shortcut rather than 3 diverse hypotheses." That is a competitor publishing its own negative result. Rare and credible.
G) Notable engineering
LangGraph StateGraph with six real nodes (sensor_auditor → pinn_engine → fusion → fault_classifier → drl_prognostics → dispatcher, orchestrator.py:700–716). FastAPI + bcrypt/PyJWT auth (src/auth/), SQLAlchemy + Postgres persistence (src/db/models.py: User/Mission/FaultEvent). PPO with a PINN "safety shield" (engine_env.apply_pinn_safety_shield) clamping actions to the physical envelope.

H) Weaknesses / fakery
The "77.4% self-healing" figure is fabricated. It appears only in README.md:111, orchestrator.py:11, orchestrator.py:134 (docstring), and the PPT markdown. No code computes it. README calls it "Cross-sensor regression imputation" — the actual implementation is last‑value‑hold or midpoint. Same for "78.6% RUL prognostic accuracy" and "12.8 cycles MAE" in ppt-diagrammes/ideaforge_under_the_hood_architecture.md:273, which contradict the repo's own MODEL_CARD (37.07 MAE).
The live PINN path is broken on a fresh clone. orchestrator.py:93–101 loads norm_min/norm_max from data/processed/, which is gitignored and absent (.gitignore excludes \*.npy, data/processed/). Fallback is zeros(12)/ones(12), so norm_window = clip((frame − 0)/1.0, 0, 1) saturates every channel (RPM 2850 → 1.0). The model object itself gets correct stats from the checkpoint via set_norm_stats (server.py:365), but the input window is garbage. Live RUL will be a constant.
pinn_engine_node computes the whole scripted Arrhenius fallback (thermal_penalty, lube_penalty, …, lines 246–260) on every frame even when the model is active, and ships damage_factor from it in the payload. Line 300 is the unreadable if fallback_active if not model_active else not model_active:.
SimulationController.\_NON_ARCHETYPE_FAULTS (server.py:141) routes "NOMINAL CRUISE" to a hand-scripted steady state instead of the EngineSim physics, because the real physics looked too hot for the demo — honestly commented, but it means the nominal demo is not the model.
src/eval/benchmarks.py reads meta["engine"] and long_telemetry.parquet, which only src/data/build_dataset.py produces — not scripts/build_dataset.py (which emits run_id). Two divergent dataset builders; one path is dead.
src/vis/**init**.py is empty; there is no visualisation module. 2. Gagguverse/aero-twin-sih-2026
~22,700 LOC, but ~7,000 is dev-tools/ Puppeteer test scripts and ~2,600 is vendored OrbitControls.js. Core app is js/app.js (3,643), js/component-3d.js (1,922), js/engine-3d.js (1,566). Browser-only, Node static server.

A) Physics — ISA atmosphere + regression baselines, no thermodynamics
js\physics-engine.js (362 lines), AeroPhysicsModel.computeExpectedState(). The one genuinely correct piece of physics is the barometric formula, line 39: 29.92 * (1 - 6.875e-6*alt)^5.256, plus a density ratio (P/P0)\*(T0/T). Everything else is a linear/lookup baseline:

expectedEgt = 720 + normLoad*85 + hotWeatherDelta
expectedCht = 145 + normLoad*28 + coolingPenalty
expectedOilPress = 38 + (rpm/5000)*18 − (oilTemp−85)*0.12
Turbo model is a wastegate schedule: if alt <= 28000 && requiredBoost <= 28.0 inHg, MAP = demanded, else ambient + 28\*throttle.
computeResiduals() is the real contribution: actual − expected per channel, normalised by hardcoded nominalRanges, classified NORMAL/ELEVATED/LOW/CRITICAL. No crank angle, no Wiebe, no cylinder pressure, no energy balance.

B) ML — two real sklearn models, trivially separable data
scripts\train_models.py (358 lines) trains RandomForestClassifier(n_estimators=50, max_depth=9) and IsolationForest(n_estimators=50, max_samples=256, contamination=0.03) on 4,000 synthetic samples (1,000/class).

Committed artifacts: models/fault_classifier.pkl (112 KB), isolation_forest.pkl (720 KB), plus hand-rolled JSON tree exports (fault_classifier.json 175 KB, isolation_forest.json 1,003 KB) and a generated js/models-data.js bundle. verify_json_engine_parity() asserts 100% prediction + probability parity between the JSON evaluator and scikit‑learn on 100 test samples — a genuinely careful piece of engineering.

js\ai-diagnostic-net.js::\_inferRandomForest() and \_evalIsolationDepth() re-implement inference in the browser, including the correct c(n) = 2(ln(n−1)+γ) − 2(n−1)/n BST path-length correction and s(x,n) = 2^(−E(h)/c(256)). This is real inference, not a mock.

But the data is self-refuting. generate_synthetic_dataset() draws LUBRICATION_DEGRADATION oil pressure from uniform(18,30) while healthy is ≈38 + rpm/5000\*18 ≈ 52. The classes are non-overlapping boxes generated by the same formulas the physics engine uses as its baseline. model_metadata.json records test_accuracy: 0.99875 with a near-diagonal confusion matrix. train_test_split(test_size=0.2, stratify=y) on i.i.d. samples — no trajectories, so no temporal leakage, but also no realism and no group/mission split concept at all.

C) Vibration — scalar RMS plus a cosmetic fake spectrum
js\telemetry-engine.js:464–467: vibrationRms is a first-order lag toward a target — and note the two update lines are duplicated verbatim (copy-paste bug, double-stepping the filter).

updateFftVibration() (line 470–484) is the damning one. It allocates new Float32Array(64) called fftBins, then synthesises them from the scalar RMS:

let energy = 0.05 + Math.random()_0.03;
if (Math.abs(i - fundBin) <= 1) energy += 0.65 _ (this.state.vibrationRms / 2.0);
if (Math.abs(i - fundBin*2) <= 1) energy += 0.35 * (this.state.vibrationRms / 2.0);
No transform is computed. The 1× and 2× "peaks" are painted onto a noise floor. The dashboard shows a spectrum analyser that has never seen a time-domain signal. Telemetry runs at 10 Hz (js/app.js:117, setInterval in telemetry-engine.js:312) — Nyquist 5 Hz, i.e. it could not resolve a 70 Hz crank order even in principle.

D) Sensor validation — the strongest of the three, and clearly the project's thesis
js\sensor-trust.js (441 lines), SensorTrustEngine. 25-sample rolling window (~2.5 s @ 10 Hz). Three independent mechanisms:

Slew-rate limits — explicit per-channel maxSlew table (rpm 350/frame, cht 6.0 °C, egt 25.0, oilPress 12.0, oilTemp 3.0, …) enforced in \_evaluateSignalTrust().
Frozen-signal detection — \_evaluateOilPressureTrust(): if variance < 0.005 over ≥10 samples while isEngineDynamic (rpmVar > 4.0 ∥ loadVar > 1.5), trust → 0.28. This correctly requires engine dynamism as the discriminator.
Cross-channel corroboration — the money function: if oil pressure drops >18 PSI below expected but oilTemp < 95 && vibrationRms < 2.5 && rpm > 3500, it is declared a transducer fault, not a pump seizure. Symmetrically \_evaluateChtTrust(): chtDelta > 45 && egtDelta < 15 → thermistor drift.
Quarantined channels are substituted with physics-expected values into trustedState, and physics-engine.js:211 zeroes their residual (resOilPressEffective = isOilQuarantined ? 0.0 : raw) — explicit residual shielding, exactly what item D asks for. No Kalman filter.

E) RUL — entirely hardcoded; no model involvement whatsoever
js\ai-diagnostic-net.js::\_computePrognostics() (line 529–583) is a four-branch if/else on this.faultClass:

faultClass rulMin rulMax conf% range string
SENSOR_FAULT 182 880 85 "170–195 h"
THERMAL_DEGRADATION 48 64 74 "43–53 h"
LUBRICATION_DEGRADATION 6 12 52 "4–8 h"
else (nominal) 182 880 92 "172–192 h"
The rulRangeStr displayed on the dashboard is a string literal that doesn't even match rulMinHours/rulMaxHours. cumulativeThermalStress is incremented but only feeds degradationScore in one branch, capped at 65. There is no regression, no conformal, no coverage. The README's "probabilistic prognostic estimate" (§8) is unsupported.

F) Evaluation — no held-out rigour
One number (test_accuracy: 0.99875) from a random split of generated boxes. No ablations, no threshold baseline comparison, no group isolation. dev-tools/ contains ~30 Puppeteer scripts (test_mission_reliability_regression.js, full_system_audit.js, test-sensor-trust.js, …) — these are UI regression tests, not model evaluation. To their credit, README.md:9–12 carries an explicit "Synthetic Data & Decision Support Transparency Notice." README §5 claims "99.2% Accuracy, 99.1% Precision" — slightly different from the recorded 99.875%, so even the honest number is restated loosely.

G) Notable engineering
Zero-dependency browser ML runtime — scikit-learn forests exported to JSON, re-executed in JS, parity-asserted. Genuinely clever and the only one of the three that runs inference with no Python at runtime.
js\hardware-link.js + dev-tools\arduino_aero_engine_sensors.ino: Web Serial API at 115200 baud with a plausible real sensor BOM (MAX6675/MAX31855 K-type thermocouples, MPX4250AP MAP transducer, ADXL345, hall-effect RPM on an interrupt). A real (if minimal) hardware path.
Groq LLM assistant behind server.js with a domain-gate (isEngineeringQuery() regex whitelist) and a local analytical fallback when no key is present. .env.example is clean — no committed secrets.
Mapbox mission planner, immutable deepFreeze blackbox replay.
H) Weaknesses / fakery
updateFftVibration() is a fake spectrum (above). Most serious single item in this repo.
RUL is a lookup table (above).
Hardcoded narrative strings. ai-diagnostic-net.js:340 always prints "Engine Health Index preserved at 94/100" regardless of actual EHI; line 370 always concludes "EHI reduced to 64/100; RUL revised to 48 h." These are demo-script text, not computed values.
Duplicated vibrationRms update lines (telemetry-engine.js:464–467).
SENSOR_FAULT short-circuits everything: if (isSensorFaultPresent) at line 325 runs before the RF result is consulted, so any single quarantined channel suppresses all fault classification. A simultaneous sensor fault + real engine fault is unrepresentable.
A new.zip and a dist/index.html are committed alongside a 1.0 MB isolation_forest.json plus its duplicate in js/models-data.js. 3. VIKASHL25/SIH-26
~13,000 LOC Python + a Vite/React/TS frontend. The most engineered of the three.

A) Physics — the best of the three, and there are two disjoint models
Two separate generators, which matters:

(i) dataset_generator.py (1,225 lines) — produces the committed data/MALE_UAV_aero_piston_engine_final_100k.csv (22.6 MB, 100 missions × 1,000 rows @ 1 Hz). calculate_atmosphere() is a real ISA lapse model (101325*(T_std/288.15)^5.25588, ρ = P/(287.05·T)). RPM and fuel flow are np.interp over three anchor points explicitly sourced to Lycoming O‑235/O‑290 published data (line 30–40). Temperatures are linear regressions: egt = 650 + 140*load_fraction + 0.8*(T_amb−25) + 0.002*alt. Fault effects are constant offsets (cht += 35\*severity). This one is essentially curve-fits.

(ii) models\rul_prediction\data_simulator\RUL_Sim_300_engines.py (300 lines) — this is a genuine mean-value engine model, the only real dynamical system in any of the three repos:

BASE_ENGINE carries displacement (0.0020 m³), eta_v_max, afr_base, lhv_j_per_kg = 44e6, eta_th_base, eta_mech, crank inertia J, oil viscosity reference.
Air path: air_mass_flow = ρ · V_d · rpm/120 · η_v, with η_v reduced by a quadratic RPM-shape term and load.
Combustion: fuel_flow = air/AFR; shaft_power = fuel_flow·LHV·η_th·η_mech.
Crankshaft dynamics integrated: net_torque = T_engine − T_prop − T_friction + 0.02·(target−rpm), then dω = net_torque/J, ω += dω·DT. Propeller load ∝ rpm².
First-order thermal lags: α = 1 − exp(−DT/τ) with τ = 300 s (EGT), 600 s (CHT), 900 s (oil) — proper Newton-cooling relaxation toward equilibria, with cht_eq = T_amb + head_heat/(600·cooling_factor).
Oil viscosity: η_ref·exp(−0.012·(T_oil − T_ref)), feeding oil_pressure = 0.0032·rpm·η + 1.0 − 1.5·deg.
Degradation feeds back into eta_th, friction, cooling, and is driven by a composite stress of thermal/load/rpm/vibration/oil terms with a progress_life^1.65 base.
Still not crank-angle resolved. DT_MINUTES = 10 → the integration step is 600 seconds. There is no cycle, no Wiebe function, no p–θ diagram. Also: NUM_ENGINES = 150 despite the filename saying 300.

B) ML — 4 real trained XGBoost/PCA models with hash manifests
Model Artifact Size Features
Anomaly anomaly_pca_model.pkl + scaler.pkl 5.7 + 3.1 KB 51
Degradation xgb_degradation_model.json 9.6 MB 120
Fault (6-class) fault_detection_multiclass_xgb.json/.pkl 1.4 / 1.8 MB 55
RUL xgboost_rul_model.json ~9 MB 129 (file has 129 lines; docstrings say 60, README says 131)
Plus fault_detection_label_encoder.pkl and three training notebooks. backend\model_loader.py::\_verify_model_hash() SHA‑256s each artifact against models/model_hashes.json at load. No PINN is claimed and none exists — which is more honest than naming one.

Anomaly detection is PCA reconstruction error, not Isolation Forest: predict_anomaly() computes Σ(scaled − inverse_transform(transform(scaled)))², with 2-consecutive-sample debouncing (is_anomaly = raw and self.previous_anomaly_raw). src\train_anomaly_pca.py documents why it replaced IF ("IF's random-split mechanism degrades with many correlated features").

C) Vibration — scalar, and the synthesis contains dead code
Dataset vibration_rms is one scalar per 1 Hz row: 0.7 + 0.00045·|rpm−2250| + 0.15·load_fraction + fault offsets. In the RUL simulator it's an analytic closed form: sqrt(0.5·A² + 0.5·(0.3A)² + 0.04²) — the RMS of an assumed 1× + 0.3×2× harmonic pair. vibration_phase += 2π·rot_freq·DT is accumulated and then never used — dead code, the vestige of a time-domain signal that was never generated.

The only downstream vibration processing is a 30-sample z-score in simulation_engine.py:614–620. No FFT, no order tracking, no angular resampling, no envelope. Repo-wide grep for DSP terms: zero hits.

D) Sensor validation — real, and architecturally the cleanest
backend\diagnostics.py (336 lines) is a deterministic router explicitly built for "sensor fault vs engine fault":

\_sensor_consistency(sample) — counts how many of 6 independent channels corroborate an abnormal CHT (egt_residual, rpm_residual, oil_temp > 110, oil_press < 2.0, vib > 0.5) and returns supporting/checks.
\_is_possible_sensor_drift() — fires F05 "possible_sensor_drift_bias" when |cht_residual| > 10 and consistency < 0.34. Note the naming discipline: "possible", and the docstring says "This does NOT claim that sensor drift is proven."
\_thermal_event() — requires ≥2 independent thermal indicators before it will override a normal classifier output into F08 overheating.
The ordering is deliberate: sensor-vs-engine reasoning runs before overheating is accepted (comment at line 212–216), so an isolated CHT excursion becomes F05 even when the ML classifier says normal.
backend\fault_registry.py (204 lines) maps 8 fault IDs → subsystem + maintenance advisory. F05 scenario in set_fault_scenario() is deliberately {"cht_C": +30.0} alone — "Deliberately isolate CHT from the other engine signals. Used to test sensor-vs-engine reasoning." That's a purpose-built test for the feature.

No Kalman filter, no slew-rate limits on input (slew limiting is applied only to the RUL output).

E) RUL + uncertainty — heuristic bands, not conformal, coverage never checked
model_loader.py::predict_rul() (line 310):

XGBoost point prediction, clipped ≥0.
apply_temporal_filter() — EMA α=0.15, then slew-rate limiting (max +1.0 h/tick, −3.0 h/tick), plus terminal zeroing when degradation_index ≥ 0.98.
Uncertainty from boosting-round variance: predict at 10 iteration_range checkpoints, take np.std.
Then the fudge — adjusted_std = max(1.5, tree_std*0.25 + rul*0.03). The 0.25 shrink, the 3%-of-value inflation, and the 1.5 h floor are all unjustified constants.
P10/P90 = rul ∓ 1.645·adjusted_std — a Gaussian assumption on a non-Gaussian quantity.
records_required: 13 gates RUL until the buffer is warm (\_generate_rul_features returns None below 13 samples and on any NaN) — a nice guard. But there is no conformal calibration and no empirical coverage validation anywhere. The 90% interval is nominal, never verified.

F) Evaluation — the most rigorous of the three
Group isolation is real and everywhere. prepare*rul_training.py: splits on df["engine_id"].unique() 70/15/15, then asserts and prints zero overlap between the three engine sets, and checks for leakage columns (degradation, health_index). train_anomaly_pca.py::mission_level_split(): holds out 20% of missions stratified by mission_type. The fault-detection notebook uses the same mission-level split and an EXCLUDE_COLS list dropping fault_type, fault_severity, degradation, failure_flag, rul_hours, health_index.
evaluate_rul_metrics.py produces docs/rul_evaluation_report.json with overall + lifecycle-phase + per-fault-mode breakdowns — and the numbers are unflattering, which is the point: overall MAE 26.72 h, RMSE 37.26, R² 0.7369, MAPE 52.04%; early-life (>200 h) R² = −2.37 with a −46.5 h bias; late-life (<50 h) R² = −1.48, MAPE 116%; injector_degradation R² = −1.35. Publishing negative R² per stratum is genuinely rigorous.
Anomaly manifest: test ROC‑AUC 0.9943, precision 0.859, recall 0.982 at the 95th-percentile threshold, mean detection latency 2.43 timesteps after fault onset — but over only 7 fault missions.
No ablations. No threshold-baseline comparison — nothing anywhere compares the ML pipeline against a simple redline/limit detector, which is the obvious strawman a DRDO panel will ask about.
Fault classifier metrics are not meaningful despite a correct split. fault_detection_model_manifest.json reports macro ROC‑AUC 1.0, accuracy 99.95%. The split is honest, but dataset_generator.py maps mission_type → fault_type 1:1 and injects each fault as a constant offset (cht += 35·severity), so the classes are separable by construction. There are only 3 sensor_fault missions in the entire dataset — the held-out set contains ~1.
G) Notable engineering
Real CAN layer. can_layer/engine_can.dbc is an actual DBC file; can_codec.py maps 20 telemetry signals into 5 CAN messages (ENGINE_STATE / THERMAL / AIR_FUEL / …) via python-can + cantools.
Simulink/MATLAB integration is not vapour: simulink/simulink_udp_poc.slx, scripts/build_engine_simulink_model.m, simulink/udp_can_bridge.py, and MissionSimulationEngine.**init** accepts input_mode="simulink" wiring a CANInputReceiver on UDP multicast ff15:7079:... (the ASCII spells "pythondemomcast"). Six UDP/multicast test scripts.
5-service microservice split (api_gateway, telemetry_service, ml_inference_service, xai_service, mongodb_service) with X-Internal-Key service auth and a SlidingWindowRateLimiter(60/60s) in backend/security.py. TLS certs in certs/.
Real SHAP. explainability/shap_explainer.py (456 lines) caches shap.TreeExplainer instances on the frozen XGBoost boosters — not a fake importance heuristic.
Federated-learning FedAvg PoC over 4 simulated nodes (scripts/federated_learning_poc.py, Ridge).
H) Weaknesses / fakery
The anomaly threshold is wired to 0.0 — the detector fires permanently. config.py:31 defines ANOMALY_THRESHOLD = 19.5280 (the calibrated 95th percentile). But simulation_engine.py:82 hardcodes self.anomaly_threshold: float = 0.0, passes it at line 394, and ANOMALY_THRESHOLD is never imported into simulation_engine.py. predict_anomaly then evaluates anomaly_score >= 0.0, which is always true for a sum of squares. With 2-consecutive debouncing, is_anomaly becomes permanently True from the second frame of every mission. The most consequential live bug in any of the three repos.
rul_hours in the flagship 100k dataset is a row-index countdown. dataset_generator.py:911: rul_hours = max(1000 − time, 0)/3600 for degrading missions, NaN otherwise. Identical for every mission; max value 0.278 h (16.7 minutes). The RUL model is not trained on this — it's trained on the separate 150-engine physics sim — but the committed headline dataset's RUL column is meaningless, and data/degradation_data/realtime*\*.csv sit alongside it.
docs/EDGE_AI_BENCHMARK.md is stale and its script is broken. The doc reports "Anomaly Detection (Isolation Forest) — 5739.6 KB, 13 features, 41.679 ms." The shipped anomaly model is a 6 KB PCA with 51 features. scripts/benchmark_edge_ai.py:50 points at isolation_forest_model.pkl, which doesn't exist — get_file_size_kb logs a warning and returns 0.0. Every number in that table is unreproducible.
model_hashes.json is incomplete. It contains only fault_classification, anomaly_detection, anomaly_scaler_unverified. \_verify_model_hash is called for degradation_estimation and rul_prediction, finds no expected entry, and silently passes (if expected and expected != computed — expected is None). The two largest models (19 MB combined) are effectively unverified, and predict_all still returns "verified_integrity": True unconditionally.
Feature-count drift. feature_engine.py docstring says RUL = 60 features; predict_rul(df_60_features) parameter is named that; the actual file is 129 lines; README and generate_docs.py say 131. Three different numbers for one model.
scratch/ (5 ad-hoc test scripts) and backend/verify_microservices.py are committed dev detritus. model_loader.py's class docstring still says "Anomaly Detection (Isolation Forest + Scaler)".
Cross-repo comparison
atharv20s (PRAHARI) Gagguverse VIKASHL25
A. Physics Algebraic degradation curves; crank angle explicitly decorative ISA atmosphere + linear expected-value baselines Mean-value engine model w/ crank inertia ODE + 1st-order thermal lags (DT=600 s)
Crank-angle / Wiebe / p–θ ✗ ✗ ✗
B. PINN real? Yes — learnable α,β; Fourier + consistency loss terms n/a (none claimed) n/a (none claimed)
Trained weights 5 × .pt, 1.0 MB — ablation baselines missing 2 × .pkl + JSON exports, ~2 MB 4 models + scaler + encoder, ~21 MB, SHA-256 manifest
C. Vibration scalar RMS, no DSP scalar RMS + fabricated 64-bin "FFT"; 10 Hz scalar RMS + 30-sample z-score; 1 Hz data, dead vibration_phase
D. Sensor validation range + NaN, last-value imputation; HMAC; no rate limits Best: slew limits + frozen-variance + cross-channel + residual shielding Best-architected: cross-sensor consistency ratio, "possible" language, ordered before fault acceptance
E. RUL uncertainty None (point estimate only) Hardcoded lookup table Boosting-variance → heuristically rescaled Gaussian P10/P90
Conformal / coverage ✗ / ✗ ✗ / ✗ ✗ / ✗
F. Group split Yes, per-engine + early-life mask ✗ (i.i.d. samples) Yes, per-engine and per-mission stratified, overlap-asserted
Honest negative results Yes — publishes 46.7% vs self-reported 100% Partial (transparency notice) Yes — negative R² per lifecycle stratum
Threshold baseline ✗ ✗ ✗
G. Standout Learnable-parameter PINN; LangGraph; HMAC; PPO safety shield Browser-native forest inference w/ parity assert; Web Serial + Arduino CAN/DBC + Simulink UDP; 5 microservices; real SHAP
H. Worst finding "77.4%" fabricated; live PINN normalisation broken on clone Fake FFT; RUL is an if/else table Anomaly threshold hardwired to 0.0 → always-on alarm
If I had to rank by "what actually runs and means something": VIKASHL25 (breadth, real physics dynamics, rigorous splits, real SHAP/CAN/Simulink — undermined by the threshold bug and a meaningless headline dataset) > atharv20s (narrow but the only real PINN, and the most intellectually honest model card) > Gagguverse (best sensor-trust logic and slickest demo, but the two things the problem statement centres on — vibration and RUL — are a painted spectrum and a lookup table).

The gap all three leave open: no one does crank-angle-resolved combustion, no one does real vibration DSP at a meaningful sample rate, no one does conformal prediction with validated coverage, and no one compares against a redline-threshold baseline.
