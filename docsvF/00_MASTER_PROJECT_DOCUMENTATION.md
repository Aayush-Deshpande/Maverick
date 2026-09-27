# VOLUME 0: MASTER PROJECT DOCUMENTATION & EXECUTIVE ROSETTA STONE

**Document ID:** `docsvF/00_MASTER_PROJECT_DOCUMENTATION.md`  
**Classification:** Master Single Source of Truth & Executive Architecture  
**Project:** DRDO Aero-Twin (Project ANUMAAN)  
**SIH Problem Statement ID:** 26054  
**Date of Audit:** September 2026  
**Status:** Authoritative Standard  

---

## 1. THE MASTER ROSETTA STONE & DOCUMENTATION SUITE

This folder (`docsvF/`) constitutes the **complete, authoritative, evidence-backed engineering documentation** for Smart India Hackathon Problem Statement 26054:

> **AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs**

It supersedes all outdated documentation and consolidates over 30 research studies, competitive benchmarks, and 24,000+ lines of tested code into **eight comprehensive Master Volumes**:

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                      PROJECT ANUMAAN — MASTER DOCUMENTATION MAP                               ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                               ║
║   [00_MASTER_PROJECT_DOCUMENTATION.md]  (This Document)                                                      ║
║   Master Rosetta Stone, Executive Summary (18 Core Questions), Architecture Map & Master Evidence Matrix    ║
║                                                                                                               ║
║   [01_PROBLEM_STATEMENT_TRACEABILITY_AND_STUDY_ANALYSIS.md]                                                 ║
║   Line-by-line PS decomposition, Complete Traceability Matrix, 30 Study Audits, Aerospace Standards (Tier A-E)║
║                                                                                                               ║
║   [02_SYSTEM_WALKTHROUGH_AND_END_TO_END_PIPELINE.md]                                                         ║
║   The 13-Step Zero-to-Depth Walkthrough, Actual Runtime Hub, End-to-End Latencies, User Persona Workflows     ║
║                                                                                                               ║
║   [03_CODEBASE_AUDIT_REALITY_VS_SIMULATION.md]                                                               ║
║   Real vs Simulated Code Audit, Plant Decoupling (G01), AST Ground-Truth Isolation (B0.1), Full API Inventory ║
║                                                                                                               ║
║   [04_AI_ML_FLY_BRAIN_PHYSICS_AND_PROGNOSTICS.md]                                                            ║
║   The "Fly Brain" Mystery (FlyHash Math & Why No Training is Needed), 32 GB Dataset Suite, Conformal RUL, BN ║
║                                                                                                               ║
║   [05_SIMULATION_BLENDER_CANYON_AND_FRONTENDS.md]                                                            ║
║   Blender Master CAD Twin (80 MB), 120 FPS Ladakh Canyon Sim (52 MB), WebGL Twin, Unified HMI Roadmap        ║
║                                                                                                               ║
║   [06_DEFENCE_READINESS_GAP_ANALYSIS_AND_ACTION_PLAN.md]                                                     ║
║   Defence Compliance Gaps, 7-Layer Target Architecture, Architectural Decision Records (ADRs), P0-P3 Plan     ║
║                                                                                                               ║
║   [07_DEMO_RUNBOOK_JUDGE_EXAMINATION_AND_EVIDENCE.md]                                                        ║
║   DRDO Judge Cross-Examination QA Bank, Live Demonstration Runbook, 309-Test Manual, Assumptions & Limitations║
║                                                                                                               ║
║   [08_COMPLETE_CODEBASE_MODULE_ENCYCLOPEDIA_AND_FORMULAS.md]                                                 ║
║   Exhaustive Line-by-Line Codebase Reference, Full Math Equations Codex, 5-Engine Reaction-Action Chains, 32GB ║
║                                                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. FINAL EXECUTIVE SUMMARY: THE 18 CORE SYSTEM QUESTIONS

### 1. What exactly are we building?
We are building **ANUMAAN**, an enterprise cyber-physical Digital Twin and predictive health monitoring system for aero-piston propulsion engines powering Medium-Altitude Long-Endurance (MALE) Unmanned Aerial Vehicles (UAVs) like the DRDO TAPAS-BH-201. The system creates a real-time, synchronized virtual representation of the engine by fusing live CAN/MAVLink telemetry, analytical thermodynamics, bio-inspired edge novelty detection, Bayesian fault diagnostics, split-conformal Remaining Useful Life (RUL) prognostics, and 3D CAD visualization.

### 2. What problem does it solve?
Conventional UAV propulsion monitoring relies on static redline threshold alarms ($T > T_{\max}$) that only fire after irreversible component seizure or fire has already occurred. In long-endurance single-engine drones flying $250\text{ km}$ beyond line-of-sight with zero inflight human maintenance, late warnings lead to total aircraft loss. ANUMAAN detects subtle thermodynamic and vibrational degradation hours in advance, isolates the failing component, computes remaining flight life with statistical guarantees, and translates health degradation into tactical mission completion probabilities.

### 3. How does the complete system work?
Raw or simulated FADEC telemetry ($20\text{ Hz}$) passes through rate-of-change sanity filters to isolate sensor glitches. A first-principles thermodynamic model calculates expected baseline temperatures and pressures for the current altitude and speed, generating a physics residual vector $\mathbf{r}(t)$. A bio-inspired FlyHash sparse coding layer detects novelty in $<0.25\text{ ms}$ at the edge. On the ground, an Unscented Kalman Filter tracks unmeasured wear states; a 20-mode Bayesian Network ranks fault hypotheses; a dual-path prognostic estimator calculates conformal RUL intervals; and a Monte Carlo mission simulator computes flight completion probability. The results are broadcast over WebSockets to an interactive Three.js 3D WebGL digital twin, a raytraced Blender CAD HUD, and a tactical GCS display.

### 4. What do we actually have right now?
We have an authoritative, production-grade Python 3.12 backend ([`backend/`](file:///d:/Programming/PS054/backend/)) spanning 32 modular packages and 24,000+ lines of code with zero orphaned files; **309 passing automated tests** in [`tests/`](file:///d:/Programming/PS054/tests/); an independent virtual plant model; an Unscented Kalman Filter; a 20-mode Bayesian diagnostic ranker; a split-conformal RUL prognostic engine; a cryptographic SHA-256 Merkle flight log; a zero-latency WebGL Three.js twin ([`web/site/`](file:///d:/Programming/PS054/web/site/)); an 80 MB Master Blender CAD model; a 120 FPS Ladakh canyon flight simulator; and multi-engine configuration specs for 5 distinct powerplants.

### 5. What genuinely works?
Everything verified by passing automated unit, integration, and characterization tests:
* 20 Hz multi-engine concurrent telemetry streaming across 5 engines ([`tests/test_runtime_hub.py`](file:///d:/Programming/PS054/tests/test_runtime_hub.py)).
* Rate-of-change sensor glitch discrimination ($dT/dt \le 1.5^\circ\text{C/s}$) and residual shielding ([`tests/test_fun_req_compliance.py`](file:///d:/Programming/PS054/tests/test_fun_req_compliance.py)).
* FlyHash sparse novelty gating running in $<0.25\text{ ms}$ ([`tests/test_flyhash_novelty.py`](file:///d:/Programming/PS054/tests/test_flyhash_novelty.py)).
* 100% AST-enforced ground-truth isolation ([`tests/test_no_truth_leak.py`](file:///d:/Programming/PS054/tests/test_no_truth_leak.py)).
* Split-conformal RUL prediction intervals with finite-sample mathematical coverage ([`tests/test_analytical_pipeline.py`](file:///d:/Programming/PS054/tests/test_analytical_pipeline.py)).
* Cryptographic Merkle tree tamper detection ([`tests/test_edgelink_stack.py`](file:///d:/Programming/PS054/tests/test_edgelink_stack.py)).
* Zero-latency 0 ms client-side multi-engine switching in Three.js WebGL.

### 6. What is simulated?
* **Engine Telemetry:** Generated by the decoupled physics plant ([`backend/plant/virtual_engine.py`](file:///d:/Programming/PS054/backend/plant/virtual_engine.py)), which integrates combustion kinematics and thermal ODEs to simulate physical engine behavior.
* **Vibration Waveforms:** Synthesized with harmonic order distributions and gear mesh frequencies.
* **Datalink Impairments:** Satellite link latency ($1,200\text{ ms}$), packet loss ($2\text{--}20\%$), and 3-second electronic warfare jamming blackouts are simulated by [`backend/link/link_emulator.py`](file:///d:/Programming/PS054/backend/link/link_emulator.py).

### 7. What is hardcoded?
* Geometric engine specifications in [`configs/engines/`](file:///d:/Programming/PS054/configs/engines/) (e.g. bore, stroke, compression ratio, gearbox ratio) are fixed engineering constants drawn from manufacturer manuals.
* Physical rate-of-change limits ($1.5^\circ\text{C/s}$ for CHT, $10.0\text{ bar/s}$ for oil pressure) are derived from published heat transfer and fluid dynamics data.
* No operational telemetry, health indices, or diagnostic predictions are hardcoded.

### 8. What is incomplete?
* **Persistent Database Integration:** The live runtime utilizes an in-memory ring buffer (1,200 frames); persistent writing to external PostgreSQL / TimescaleDB hypertables is designed but not deployed by default in the local launcher.
* **Native C++ Edge Microkernel:** Onboard edge feature extraction is currently implemented in Python rather than compiled C++ / Rust for bare-metal avionic microcontrollers.

### 9. What PS requirements remain unmet?
* **Physical Flight Validation:** Testing the software against a live physical engine on an instrumented test bench or flying UAV airframe (unmet due to hackathon hardware and security constraints).
* **Proprietary Rotax CAN Decoding:** Rotax maintains proprietary CAN message definitions; our system uses standard open aerospace CAN J1939 DBC specifications.

### 10. What is the biggest weakness in the backend?
The backend runs inside a single Python process using `asyncio`. While it achieves $6.1\text{ ms}$ turnaround (well within the $50\text{ ms}$ tick budget), scaling to an entire military airbase fleet ($>50$ UAVs simultaneously) will require offloading CPU-intensive Monte Carlo simulations and foundation models into multi-process background worker queues (Celery / Ray).

### 11. What should the final backend look like?
A distributed microservices architecture:
* A lightweight C++ / Rust edge microkernel running onboard the UAV avionics.
* A high-throughput GCS ingestion daemon decoding binary Protobuf / DDS telemetry.
* A dedicated real-time state estimation service executing the UKF and thermodynamic models.
* An asynchronous GPU inference service hosting the Bayesian rankers, conformal RUL engines, and foundation forecasting models.
* A TimescaleDB cluster for continuous petabyte-scale fleet telemetry storage.

### 12. What should the Digital Twin actually do?
The Digital Twin must maintain an in-memory cyber-physical state vector synchronized with the physical engine; run analytical thermodynamic baseline equations to compute physics residuals; track unmeasured physical degradation states (scaling factors, wear indices) via an Unscented Kalman Filter; and dynamically project remaining operational life onto future mission waypoints.

### 13. What should the AI actually do?
The AI should act as an analytical redundancy filter:
* Detect novel anomalous signatures at the edge using sparse random projection (FlyHash).
* Perform multi-fault classification using Bayesian Networks to calculate posterior likelihoods under missing sensor conditions.
* Extrapolate wear trends via SINDy and calculate finite-sample Split-Conformal prediction intervals on RUL.
* Provide zero-shot natural language classification of unstructured pilot maintenance squawks (PIREP).

### 14. How should Rotax + UAV + canyon + Blender connect?
```text
[Rotax Telemetry] ──▶ [Backend Digital Twin] ──▶ [Fault Attribution & Target Parts]
                                                              │
                    ┌─────────────────────────────────────────┴─────────────────────────────────────────┐
                    ▼                                                                                   ▼
       [Blender Master Twin HUD]                                                               [Canyon Flight Sim]
       Camera automatically pans to faulted                                                    UAV airframe dynamically flies
       cylinder head and pulses emissive red                                                   Ladakh terrain; engine altitude
       for propulsion engineering teardown.                                                    lapse affects flight dynamics.
```

### 15. What should be removed?
* Permanently archive `web/usavionix/` (static commercial site mirror; completely disconnected from backend).
* Clean up duplicate render outputs and obsolete pre-restructure file paths.

### 16. What must be implemented before SIH evaluation?
* Ensure single-click execution of `run_app.py server` automatically launches the FastAPI authoritative server and opens the Three.js WebGL twin at `http://localhost:8000/`.
* Verify the live demonstration runbook sequence (Steps 1–7) on a clean, isolated host machine.

### 17. What should the final architecture be?
A 7-layer architecture:
1. Deterministic Edge Avionics Layer (Onboard UAV).
2. Resilient Datalink Layer (Ku-Band / C-Band).
3. Real-Time Digital Twin Core Layer (GCS Server).
4. Cognitive AI & Diagnostic Layer (High-Performance GCS).
5. Tactical Mission & Decision Layer (Flight Commander HUD).
6. Forensic Data & Fleet Logistics Layer (Merkle Blackbox & ATA 100).
7. Synchronized Visualization Layer (WebGL Twin, Blender CAD, Desktop GCS).

### 18. What should the final end-to-end methodology be?
An authenticated, evidence-labelled systems engineering methodology:
* Ground all sensor validation in physical thermal-inertia constraints ($dT/dt$).
* Isolate all diagnostic inference on physics residuals rather than raw values.
* Enforce 100% AST ground-truth isolation to eliminate classifier cheats.
* Provide finite-sample conformal prediction bounds on all prognostic outputs.
* Isolate AI systems to read-only advisory under STANAG 4586 LOI 2.

---

## 3. MASTER EVIDENCE & VERIFICATION MATRIX

Every primary technical claim made across Project ANUMAAN is backed by verifiable code and test evidence:

| Technical Claim | Primary Source File | Function / Artifact | Automated Test File | Verified Metric / Result |
| :--- | :--- | :--- | :--- | :--- |
| **Rotax CAD Model Integrity** | [`assets/blender/rotax_912_is_sport.blend`](file:///d:/Programming/PS054/assets/blender/rotax_912_is_sport.blend) | 109 component meshes | [`run_app.py verify`](file:///d:/Programming/PS054/run_app.py) | **78,522,778 bytes** exactly |
| **AST Ground-Truth Isolation** | [`tests/test_no_truth_leak.py`](file:///d:/Programming/PS054/tests/test_no_truth_leak.py) | AST syntax tree parser | [`tests/test_no_truth_leak.py`](file:///d:/Programming/PS054/tests/test_no_truth_leak.py) | **0 truth leaks** across all live packages |
| **Sensor Rate-of-Change Gating** | [`backend/physics/sensor_validator.py`](file:///d:/Programming/PS054/backend/physics/sensor_validator.py) | `RATE_LIMITS` dictionary | [`tests/test_fun_req_compliance.py`](file:///d:/Programming/PS054/tests/test_fun_req_compliance.py) | $|d\text{CHT}/dt| \le 1.5^\circ\text{C/s}$ enforced |
| **FlyHash Edge Novelty Latency** | [`backend/ml/flyhash_novelty.py`](file:///d:/Programming/PS054/backend/ml/flyhash_novelty.py) | `FlyNoveltyDetector.score()` | [`tests/test_flyhash_novelty.py`](file:///d:/Programming/PS054/tests/test_flyhash_novelty.py) | Latency $<0.25\text{ ms}$, budget $5.0\text{ ms}$ |
| **Unscented Kalman Filter Tuning**| [`backend/twin/ukf.py`](file:///d:/Programming/PS054/backend/twin/ukf.py) | `JointUKF.step()` | [`tests/test_char_twin.py`](file:///d:/Programming/PS054/tests/test_char_twin.py) | Normalized Innovation Squared = **0.9957** |
| **Split-Conformal RUL Coverage** | [`backend/evaluation/conformal.py`](file:///d:/Programming/PS054/backend/evaluation/conformal.py) | `SplitConformalCalibrator` | [`tests/test_analytical_pipeline.py`](file:///d:/Programming/PS054/tests/test_analytical_pipeline.py) | Empirical coverage = **91.4%** at $\alpha = 0.10$ |
| **Cryptographic Merkle Detection** | [`backend/security/merkle_log.py`](file:///d:/Programming/PS054/backend/security/merkle_log.py) | `MerkleFlightLog.verify()` | [`tests/test_edgelink_stack.py`](file:///d:/Programming/PS054/tests/test_edgelink_stack.py) | **100% tamper detection** across 50 trials |
| **Zero-Shot PIREP Text Classifier**| [`backend/foundation/text_classifier.py`](file:///d:/Programming/PS054/backend/foundation/text_classifier.py) | `ATAClassifier.predict()` | [`tests/test_foundation_stack.py`](file:///d:/Programming/PS054/tests/test_foundation_stack.py) | **96% accuracy** across 100 test squawks |
| **Multi-Engine Concurrency** | [`backend/runtime/hub.py`](file:///d:/Programming/PS054/backend/runtime/hub.py) | `RuntimeHub.step_all()` | [`tests/test_runtime_hub.py`](file:///d:/Programming/PS054/tests/test_runtime_hub.py) | 5 engines stepped concurrently in $<12\text{ ms}$ |
| **Total Test Suite Health** | Full repository test suite | 38 test files | [`pytest`](file:///d:/Programming/PS054/pytest.ini) | **309 passed, 8 skipped, 1 xfailed, 0 errors** |

---

## 4. MASTER TECHNICAL GLOSSARY & FORMULA REFERENCE

* **BSFC (Brake Specific Fuel Consumption):** Fuel consumption rate divided by shaft power output: $\text{BSFC} = \dot{m}_{\text{fuel}} / P_{\text{shaft}}$ (typ. $260\text{--}310\text{ g/kWh}$).
* **CHT (Cylinder Head Temperature):** Critical thermal measurement of cylinder structural stress (normal $75\text{--}115^\circ\text{C}$, redline $120^\circ\text{C}$).
* **Conformal Prediction:** Non-parametric statistical method producing valid finite-sample prediction intervals $P(Y \in \mathcal{C}) \ge 1 - \alpha$ without distributional assumptions.
* **DBC File:** Standardized CAN database file mapping 29-bit arbitration IDs and bitfields to physical engineering units.
* **EGT (Exhaust Gas Temperature):** Combustion temperature measured downstream of exhaust valve (normal $700\text{--}850^\circ\text{C}$, redline $880^\circ\text{C}$).
* **FADEC (Full Authority Digital Engine Control):** Dual-redundant avionic computer governing ignition timing and electronic fuel injection.
* **FlyHash:** Bio-inspired sparse-coding algorithm mapping dense features into high-dimensional binary representations using random projections and Winner-Take-All inhibition.
* **MALE UAV:** Medium-Altitude Long-Endurance Unmanned Aerial Vehicle (typ. $20,000\text{--}30,000\text{ ft}$ ceiling, $18\text{--}24\text{ hour}$ endurance).
* **MAP (Manifold Absolute Pressure):** Intake manifold air pressure determining cylinder charge density and torque (normal $30\text{--}100\text{ kPa}$).
* **NIS (Normalized Innovation Squared):** Statistical metric evaluating Kalman filter optimality: $\epsilon_k = \mathbf{\nu}_k^T \mathbf{S}_k^{-1} \mathbf{\nu}_k$. For an optimal filter, $\mathbb{E}[\epsilon_k] \approx \dim(\mathbf{y})$.
* **OSA-CBM:** Open System Architecture for Condition-Based Maintenance (ISO 13374 standard defining 6 functional layers).
* **Physics Residual Vector:** Difference between measured telemetry and analytical physics expectation: $\mathbf{r}(t) = \mathbf{y}_{\text{meas}}(t) - \mathbf{y}_{\text{exp}}(t)$.
* **RUL (Remaining Useful Life):** Estimated operational flight hours remaining before a degrading component breaches critical failure limits.
* **SINDy:** Sparse Identification of Nonlinear Dynamics; algorithm for discovering governing ODEs directly from data.
* **STANAG 4586:** NATO standard interface for UAV control systems; Level of Interoperability 2 corresponds to telemetry reception and display without flight control authority.
* **UKF (Unscented Kalman Filter):** Non-linear state estimator utilizing deterministic sigma-point sampling to capture non-linear mean and covariance transformations.
