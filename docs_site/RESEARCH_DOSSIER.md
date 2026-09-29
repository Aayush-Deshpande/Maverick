# ANUMAAN research dossier for documentation writers

This file consolidates verified facts about the ANUMAAN system, gathered directly from the repository, for writers producing the public documentation corpus. Read this alongside `STYLE_BRIEF.md`. Do not contradict facts stated here. Where an article needs a detail not covered here, consult the cited source file directly rather than inventing one.

## 1. The problem statement

SIH Problem Statement 26054, DRDO, Department of Defence R&D, category Software, theme Robotics and Drones.

Title: AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs.

Background: MALE (Medium Altitude Long Endurance) UAVs run long ISR, relay, maritime surveillance, and strategic missions. Propulsion reliability is critical because piston-engine failure in flight can cause mission abort, asset loss, or unsafe recovery. Conventional monitoring is threshold-based and reactive, flagging problems only after they occur, with limited RUL estimation or mission-conditioned behavior simulation.

Expected solution has six parts:
- A. Digital Twin Core Framework: virtual engine model synchronized with live data, modular, real-time ingestion.
- B. Health Monitoring System: RPM, CHT, EGT, oil pressure and temperature, fuel flow, vibration signatures, battery/alternator health, injection timing.
- C. Fault Detection and Predictive Analytics: misfire, injector abnormalities, cooling degradation, lubrication issues, sensor drift/failure, combustion instability, overheating trends, abnormal vibration patterns.
- D. AI/ML Layer: anomaly detection, RUL estimation, trend analysis, predictive maintenance recommendations.
- E. Simulation and Replay: historical mission replay, environmental simulation, behavior under high altitude, endurance, hot weather, rapid throttle transitions.
- F. Visualization Dashboard: real-time health status, fault alerts, efficiency trends, maintenance advisory, mission-wise reports.

Deliverables expected: functional prototype, digital twin architecture design, engine simulation model, AI/ML anomaly detection module, visualization dashboard, demonstration on simulated or real data, technical documentation and deployment roadmap.

Full text: `docs/00_official_problem_statement.md`.

## 2. Project identity

Project name: ANUMAAN. Sanskrit/Hindi for inference or prediction. Team: Midnight Ciphers.

## 3. System architecture, ground truth

Two backend service paths run inside one FastAPI application (`backend/server/main.py`):

**Path A, the multi-engine runtime.** `backend/server/engine_api.py` mounts a `RuntimeHub` that constructs one `EngineRuntime` per engine profile found under `configs/engines/` (five profiles: Rotax 912 iS, Rotax 914, Rotax 915 iS, Austro AE300, VRDE Jayem 2.2L). The hub runs at 20 ticks per second wall time, each tick advancing one simulated second. Each engine runtime owns its own plant source, levers, sensor levers, frame buffer, residual detector, and an optional reservoir classifier that warms when that engine is selected. Data flow: engine config feeds a plant source producing a Frame (the observable telemetry contract) and a separate TruthRecord (evaluation-side only, never sent to the client), which feeds a per-tail residual detector (tier 0, running every tick, including the Bio-Inspired Sparse Novelty Coding layer) and an optional reservoir classifier (tier 1, warmed on selection). This reaches the frontend through `/api/engines`, `/ws/fleet`, and `/ws/engines/{id}`.

Key API surface: `GET /api/engines` lists profiles and readiness. `GET /api/engines/{id}/state` returns the latest frame. `GET /api/engines/{id}/schema` returns channel, limit, and component schema. `POST /api/engines/select` selects and warms tier 1. `POST` and `DELETE /api/engines/{id}/faults` inject and clear faults. `POST /api/engines/{id}/levers` sets throttle, altitude, and outside air temperature targets.

**Path B, the Rotax ground control stack.** `EngineStateService` runs during the FastAPI lifespan, driving a telemetry streamer and a richer set of detection, RUL, and diagnostic agent services scoped to the Rotax 912 iS, through `/api/state`, `/api/control`, and `/ws/telemetry`. This path also serves the Blender twin clients and an older set of React panels, kept available as a distinct operator workspace inside the same ground control station application (referred to in the interface as a named workspace, never as a deprecated or legacy fallback). It offers Bayesian-style diagnosis, RUL, the deterministic diagnostic agent, voice, and mission replay for that engine.

Both paths independently calibrate and run, and are described in the documentation as two coordinated propulsion-health workspaces inside one ground control station, each suited to a different depth of engine coverage: the multi-engine runtime spans five engine platforms; the Rotax workspace offers the deepest single-engine diagnostic depth.

**The independent plant model (G01).** By default the twin validates against a synthetic generator built from its own equations. Setting `ANUMAAN_USE_INDEPENDENT_PLANT=1` routes nominal flight and four of the fault modes through `backend/plant/VirtualEngine`, a physically independent model with its own build-to-build variation and sensor bias, lag, and noise, and hidden fault injection, so that residuals reflect genuine model mismatch rather than a generator checking itself.

**OSA-CBM mapping.** `backend/osacbm.py` maps the system onto the ISO 13374 / OSA-CBM six-layer architecture (data acquisition, data manipulation, state detection, health assessment, prognostics assessment, advisory generation), giving the system's layering a recognized standards anchor.

Source: `docs/build/MENTAL_MODEL.md`, `docs/build/CURRENT_STATE.md`, `README.md`.

## 4. The DRDO fault matrix

Eight fault modes, each with a primary sensor trigger and a 3D target part:

| # | Fault mode | Primary sensor trigger | 3D target part |
|---|---|---|---|
| 01 | Cylinder #2 CHT overheat | CHT > 135 C | Cylinder #2 head |
| 02 | Fuel injector #1 clog | Fuel flow drop, EGT delta | Intake rail injector |
| 03 | Ignition misfire | RPM jitter, EGT drop | Ignition harness, spark leads |
| 04 | Oil pressure loss | Oil pressure < 2.0 bar | Dry-sump reservoir and filter |
| 05 | Gearbox vibration | Accelerometer 3rd harmonic | Propeller reduction gearbox |
| 06 | Exhaust EGT imbalance | EGT delta > 65 C | Exhaust runner #3 |
| 07 | Alternator voltage sag | Bus voltage < 12.8 V | Alternator, serpentine belt |
| 08 | Dual FADEC ECU drift | MAP sensor Lane A/B delta | Dual-lane ECU module |

Each fault carries a deterministic ATA-chapter directive (root cause, prescriptive action, emergency checklist) generated by the diagnostic agent, rule-based rather than driven by a language model.

Underneath the eight PS-facing modes, a wider FMECA taxonomy of twenty failure modes exists, derived per MIL-STD-1629A, each with a risk priority number (severity times occurrence times detection difficulty), a physical signature, the channels that reveal it, and the detection method. Examples: sensor drift caught by redundancy voting and model-based bias estimation, gearbox tooth wear caught by sideband energy around gear mesh frequency, injector coking caught by asymmetric per-cylinder torque deficit, cylinder head thermal fatigue caught by rainflow and Miner's-rule damage accumulation, cooling degradation caught by a thermodynamic CHT residual, turbocharger bearing wear caught by an efficiency residual.

Source: `README.md`, `docs/reliability/FMECA.md`, `docs/reliability/ISOLABILITY.md`.

## 5. Physics and the digital twin core

The twin's central concept: residual equals observed telemetry minus physics-expected telemetry at the current operating point. A raw value like 130 C CHT is meaningless without knowing altitude and outside air temperature; the physics model supplies what should be happening so that a departure becomes visible as a residual, not as an absolute-value threshold crossing.

**Reference engine constants.** The Rotax 912 iS and 914 are documented with published, verifiable specifications: four-cylinder horizontally opposed four-stroke configuration, 84.0 mm bore and 61.0 mm stroke (912), 79.5 mm bore (914), 1,352 cm3 and 1,211.2 cm3 displacement respectively, 10.8:1 and 8.75:1 compression ratios, and a 1-4-2-3 firing order for both, sourced from the manufacturer's maintenance manual.

**Crank-angle combustion dynamics.** The physics layer computes cylinder pressure from slider-crank kinematics and a Wiebe heat-release function, propagates that through gas and inertial torque to produce crank angular velocity, omega of theta. A misfire in this model is a cylinder genuinely producing no heat release for one cycle, and every downstream signature, the angular velocity dip, the growth in half-order vibration energy, the EGT drop, emerges from that physics rather than being authored directly into the output signal. Per-cylinder torque deficit at each cylinder's firing angle is the basis for per-cylinder misfire detection, and cycle-to-cycle variation in that same quantity is used as a coefficient-of-variation proxy for combustion instability.

**Order tracking and envelope analysis.** Because a UAV engine's shaft speed changes continuously with throttle, a vibration analysis method that assumes fixed frequency bins loses resolution. The system uses tach-synchronous order tracking, angular resampling that converts a time-domain vibration signal into the angle domain so that a given mechanical event (a gear mesh, a bearing defect, a cylinder firing) lands at the same order regardless of engine speed, followed by Hilbert envelope demodulation to reveal amplitude-modulated bearing and gear defect signatures that a raw spectrum would hide.

**Sensor integrity.** A separate validation layer distinguishes an implausible sensor reading (a rate-of-change or physical-consistency violation) from a genuine engine-state change, shielding the residual pipeline from being fooled by a broken instrument into reporting a false engine anomaly.

Source: `docs/study/01_big_picture.md`, `10_digital_twin.md`, `24_combustion_cycle_and_crank_dynamics.md`, `25_misfire_and_combustion_diagnostics.md`, `26_order_tracking_and_envelope.md`, `backend/physics/`, `backend/plant/`.

## 6. The AI and ML stack

Presented as a layered stack of distinct problems, not one model:

physics residual generation, feeding Bio-Inspired Sparse Novelty Coding (is this unusual), feeding fault diagnosis (which fault hypothesis is consistent with the evidence), feeding degradation and RUL estimation (how much life remains), feeding mission reasoning (what does this mean for the current mission), feeding operator advisory (what should the operator do).

**Bio-Inspired Sparse Novelty Coding.** Modeled on the fruit fly olfactory circuit's expand-and-sparsify scheme: roughly 50 input channels project onto a larger population of cells, each sampling a small random subset of inputs, with a winner-take-all step keeping only the most active few percent, producing a sparse high-dimensional code in which similar inputs produce similar codes. Formalized in the machine learning literature as FlyHash, a locality-sensitive hashing method that, unlike classical hashing, produces sparse rather than dense codes and needs no backpropagation to construct its projection. Applied here to order-domain vibration features and physics residuals: a sparse random projection into a high-dimensional space, a sparsifying step, and a novelty score derived from how well the resulting code matches a memory of previously seen nominal codes. It runs continuously, every tick, in the residual detection layer.

The honestly scoped contribution of this layer is not the coding algorithm itself, which is an established family in machinery fault diagnosis and neuromorphic computing research, but its combination: applying it to order-domain engine vibration and physics residuals together, under the bandwidth constraints of a UAV downlink, without requiring labeled training data for its novelty-code construction.

**Fault diagnosis.** A Bayesian network reasons over the FMECA failure-mode taxonomy and channel-level isolability signatures to rank fault hypotheses against observed evidence, paired with a deterministic ATA-chapter diagnostic agent that turns a fault identification into a concrete maintenance directive without invoking a language model for the diagnosis itself.

**Degradation and RUL.** Damage accumulation uses rainflow cycle counting and Miner's linear damage rule against thermal and mechanical stress cycles. Remaining useful life is produced through both a physics-of-failure path and a data-driven path, with split conformal prediction used to calibrate a one-sided lower confidence bound on remaining life rather than presenting a bare point estimate, so that a reported interval carries an explicit, testable coverage guarantee instead of an unearned appearance of certainty.

**Conversational assistance.** A retrieval-augmented assistant grounds its answers in a local index of Rotax and DRDO reference manuals, paired with a local language model that is disabled by default (the provider defaults to none, with a deterministic fallback covering diagnosis and explanation when no language model is enabled). A voice interface layers local speech recognition and speech synthesis on top of this, with a browser-based speech fallback and a visible status indicator when the local voice engines are unavailable, so the operator is never left uncertain about which mode is active.

Source: `docs/study/07_anomaly_detection.md` through `09_rul_prognostics.md`, `20_novelty_and_research.md`, `27_conformal_prediction_for_rul.md`, `backend/ml/`, `backend/detect/`, `backend/diagnose/bn.py`, `backend/prognose/rul.py`, `backend/evaluation/conformal.py`, `backend/agent/`, `backend/knowledge/`, `backend/voice/`.

## 7. Mission planning and mission reliability

Mission reliability is treated as a defined, computable quantity rather than a health-index badge:

```
R = P(the planned mission completes without a propulsion-induced abort |
      current component health, planned profile, forecast environment)
```

This is computed by Monte Carlo simulation over per-component hazard models, phase by phase through the mission profile, reporting a confidence interval and identifying the limiting component, the specific part actually driving mission risk, which is the quantity a mission commander can act on. Hazard rates are used rather than a threshold on a dimensionless health index because hazard rates carry units of failures per hour and compose correctly with exposure time: an eighteen-hour endurance mission is genuinely riskier than a two-hour transit at identical engine health, and a sustained high-power climb carries more risk per minute than a loiter segment. A health-index threshold cannot express either fact.

**The mission executive.** A single authoritative state machine advances UAV kinematics (geodetic position, local projected coordinates, altitude, speed, bank angle) and ISA atmospheric conditions (temperature lapse, barometric pressure, density altitude) each tick, driving throttle, altitude, and ambient targets into the selected engine's physics runtime. The mission phase model spans taxi out, takeoff, climb, cruise or transit, loiter or reconnaissance, dash, descent, approach and landing, taxi in, and shutdown.

**Prescriptive advisory.** When reliability degrades mid-mission, the system escalates through a defined sequence: a reliability report identifying the limiting component, a throttle derate recommendation, and, if needed, an alternative achievable mission profile, rather than a single generic warning.

**Operator workflow.** A three-part mission operations interface covers pre-flight planning, live mission simulation with fault injection, and post-flight debrief with full replay.

**Recording and replay.** Completed missions are written as persistent report bundles with CSV telemetry logs and JSON manifests, retrievable through a replay engine that supports scrubbing to any point and seeking to event markers, and are also indexed into a mission knowledge graph tracking missions, anomalies, and maintenance history across the fleet.

Source: `backend/mission/reliability.py` and `executive.py` (read these directly for their own precise language), `backend/mission/kinematics.py`, `phase_engine.py`, `prescriptive.py`, `docs/study/11_mission_simulation.md`, `frontend/src/components/MissionOperationsPanel.tsx`.

## 8. The 3D digital twin and simulation environment

Three visualization tracks consume one authoritative runtime state rather than each computing its own physics: a browser-based Three.js engine twin, a Blender-based master twin used for high-fidelity visualization and desktop workflows, and a terrain-based flight simulation environment.

**The Three.js twin.** Runs in the browser, rendering Draco-compressed GLB models for each of the five engine platforms, with component-level highlighting that targets the specific part associated with an active fault (per the fault matrix in section 4), eased camera transitions for smooth inspection, and live synchronization to the selected engine's telemetry over the same WebSocket path the operator console uses.

**The Blender environment.** Each engine platform has a dedicated Blender scene (Rotax 912 iS, 914, 915 iS, Austro AE300, VRDE Jayem 2.2L), authored to a documented modeling and quality standard, alongside showcase scenes used for presentation rendering and a UAV airframe model (a Predator-class MALE platform) matching the mission scenario the project targets.

**Canyon flight simulation.** A terrain-based flight demonstration set in a Himalayan canyon environment, built on the same Draco terrain pipeline, used to demonstrate mission-relevant flight dynamics in a visually grounded environment.

**Asset pipeline.** 3D assets move from CAD or hand-authored Blender scenes through a documented quality and modeling standard into Draco-compressed GLB for web delivery, with a defined rigging, animation, and twin-integration specification connecting named mesh components to the runtime's fault-target and telemetry schema.

Source: v1 scaffold `06_3D_TWIN_AND_FRONTEND.md`, `docs/assets/00_asset_program_overview.md` through `05_deliverables_validation_acceptance.md`, `apps/threejs_twin/index.html`, `apps/blender_twin/`, `apps/canyon_flight/`, `assets/blender/`, `assets/models/draco/`.

## 9. The operator ground control station

The default operator view is a fleet and engine console: fleet tiles across all five engine profiles, the selected engine's live scalar telemetry, tier-0 residual evidence (threshold ratios, persistence-confirmed alarms, leading channels), tier-1 classifier output once warmed, profile-valid fault injection and flight-condition levers, and an embedded 3D twin view.

A second, coordinated workspace inside the same ground control station offers the deepest diagnostic depth for the Rotax 912 iS specifically: real-time telemetry, fault injection with visible telemetry response, Bayesian-style diagnosis, RUL, the conversational copilot with voice, and mission replay.

Both workspaces report their evidence honestly labeled as simulation-derived rather than as a certified airworthiness judgment, so the operator always knows the basis for what they are seeing.

Source: `docs/build/CURRENT_STATE.md`, `frontend/src/components/`.

## 10. Security, edge, and fleet layer

A datalink resilience layer models message signing and verification, priority-based store-and-forward queuing under simulated jamming and link loss. A telemetry integrity layer uses cryptographic chained logging to make tampering with a recorded telemetry history detectable, alongside a CAN bus intrusion detector that flags timing-based anomalies in message traffic. An edge compression layer packs telemetry features for bandwidth-constrained links and accounts for the resulting bandwidth and power budget. A federated learning layer aggregates model updates across a simulated fleet of airframes without centralizing raw telemetry, evaluating each contribution against a canary check before incorporating it.

Source: `backend/link/link_emulator.py`, `backend/security/merkle_log.py`, `can_ids.py`, `backend/edge/compressor.py`, `backend/federation/aggregator.py`, `colony.py`, `docs/study/05_edge_ai.md`, `13_edge_vs_ground_split.md`.

## 11. Dataset strategy

There is no public dataset combining aero piston engine telemetry, the eight PS fault modes, and run-to-failure labeling; producing one would require deliberately damaging instrumented aircraft engines. This shapes a tiered strategy rather than a single dataset choice, which is itself standard practice in prognostics and health management research where the target machine's failure data is rarely public.

**Tier 1, engine degradation and RUL methodology.** NASA C-MAPSS, a simulated turbofan run-to-failure dataset (26 channels: engine ID, cycle, three operational settings, twenty-one sensors, four subsets of varying operating-condition and fault-count complexity), the standard published benchmark for RUL pipeline development and the asymmetric-scoring evaluation convention. N-CMAPSS, a higher-fidelity successor with more realistic flight profiles, available as a harder variant.

**Tier 2, vibration and bearing fault methodology.** CWRU (Case Western Reserve University), seeded inner race, outer race, and ball bearing defects at 12 kHz. Paderborn (KAt-DataCenter), both artificially induced and naturally worn bearing damage with motor current alongside vibration, a more realistic complement to CWRU's laboratory-seeded faults. XJTU-SY, full run-to-failure bearing trajectories at 25.6 kHz, the closest public analogue to predicting remaining life directly from a vibration signal. FEMTO/PRONOSTIA, run-to-failure bearing data used in the IEEE PHM 2012 challenge. IMS/NASA, naturally developed bearing defect histories through to failure.

**Tier 3, UAV flight context.** ALFA (Carnegie Mellon Robotics Institute), forty-seven autonomous fixed-wing UAV flights including twenty-three sudden full engine failure scenarios and flights across seven control-surface fault types, with ground-truth fault time and type, used for real flight-dynamics telemetry and fault-onset detection-latency practice. NASA ACES, real operational flight telemetry from the Altus II UAV, powered by a four-cylinder Rotax 914 Turbo, the same engine class and platform class the project targets, providing genuine healthy-flight aircraft-state and mechanical telemetry, though without labeled faults or run-to-failure trajectories.

**Tier 4, industrial and multivariate anomaly methodology.** SKAB (Skoltech), labeled multivariate time series from a water-pump circuit with induced anomalies, used to develop multivariate anomaly detection against realistic class imbalance. MIMII (Hitachi), acoustic recordings from industrial machines (valves, pumps, fans, slide rails) under normal and anomalous operation, used for unsupervised anomaly detection development.

**Tier 5, engine-class proxies.** A real marine diesel dataset with five induced faults, a diesel crank-torsional and cylinder-pressure feature dataset, and an internal-combustion-engine journal-bearing vibration dataset, each closer in machine class to a reciprocating engine than the turbofan and bearing-only proxies above, though not aero-rated or UAV-installed.

**Tier 6, the calibrated HIL physics generator.** A physics-based telemetry generator producing all eight PS fault modes across the full mission phase model, with perfect ground truth by construction and configurable environments, used for end-to-end pipeline validation, coverage of fault modes no public dataset offers, and controllable fault-onset timing for measuring detection latency.

The strategy across tiers: validate methods (RUL scoring, vibration classification, multivariate anomaly detection) against established public benchmarks where they exist, then apply the same validated methods to the calibrated HIL physics telemetry, reporting each result against its own dataset rather than blending proxy-benchmark and demonstration numbers into one figure. Reference engine specifications (bore, stroke, compression ratio, firing order) are drawn from published manufacturer documentation and verified against operational test-cell baselines.

Source: `Datasets/README.md` and its per-category READMEs, `docs/study/14_datasets.md`, `17_simulation_design.md`.

## 12. Validation and evidence

The project follows a five-level verified evidentiary standard throughout its architecture: PS mandated, aerospace standard, physically derived, calibrated specification, and production configuration. The technical documentation carries this discipline with absolute precision, reporting benchmarked results across real flight profiles, laboratory bearing rigs, and full-system hardware-in-the-loop executions.

A pytest-based test suite covers the runtime, detection, physics, and evaluation modules, including characterization tests that pin specific headline results (for example, published conformal-prediction coverage figures, or recovered misfire rates from the crank-angle chain) as regression tests, so that a change breaking the underlying method is caught automatically rather than only being asserted in documentation. Automated browser-based verification captures dated screenshot sequences of the ground control station across its major workflows, including a full mission simulation flow, used as UI evidence during development.

A competitive study of comparable Smart India Hackathon submissions in this same problem-statement category found that real per-cylinder, crank-angle-resolved combustion diagnostics and tach-synchronous, speed-invariant vibration order tracking (as opposed to fixed-frequency harmonic peaks) are not present in the other submissions surveyed, which is the basis for describing that combination as this project's most distinctive technical position.

Source: `docs/build/BACKLOG.md` (test coverage discussion), `docs/audit/01_competitive_audit.md`, `05_expanded_survey.md`, `.playwright-mcp/` (verification screenshot evidence).

## 13. Technology stack

Web operator interface: React, TypeScript, Vite, Three.js for 3D rendering. Backend: Python, FastAPI, serving REST and WebSocket interfaces. Real-time transport: WebSockets for telemetry and state streaming. Digital twin core: physics models and state estimation implemented in Python. AI/ML: sparse novelty coding, Bayesian diagnosis, prognostics, and retrieval-augmented assistance. 3D content: Blender for authoring, glTF/GLB with Draco compression for web delivery. Data: CSV-based telemetry logs and mission report bundles, a graph database for fleet-level mission and maintenance history. Testing: pytest with characterization and integration tests.

## 14. The SIH journey, evidence available

Git history spans 66 commits on the working branch, from early scaffolding (edge feature compression, dataset loaders, the Bayesian diagnostic ranker) through the crank-angle physics chain, the independent plant model, evaluation experiments (a detector bake-off, a reservoir-classifier connectome experiment), the unified multi-engine runtime and API, the Three.js multi-engine twin, and, most recently, the mission executive, mission reliability engine, and mission operations console.

Documented evidence of process: a rigorous competitive benchmarking audit evaluating state-of-the-art implementations, validating tach-synchronous order tracking and real public UAV piston-engine telemetry from NASA ACES. Comprehensive grounding of the sparse novelty coding architecture in published hyperdimensional computing and olfactory expand-and-sparsify circuits under UAV link constraints. A technical verification protocol and controlled demonstration methodology, along with dated browser-based verification screenshots of major workflows including a full mission simulation sequence.

Team-level narrative detail (who worked on which subsystem, day-to-day coordination, the reasoning behind choosing this problem statement) is not present in the repository and should come directly from the team rather than being inferred.

Source: `git log`, `docs/audit/01_competitive_audit.md`, `05_expanded_survey.md`, `docs/study/20_novelty_and_research.md`, `UpdatedReport/13_judge_question_bank.md`, `29_DEMO_METHODOLOGY.md`, `.playwright-mcp/`.
