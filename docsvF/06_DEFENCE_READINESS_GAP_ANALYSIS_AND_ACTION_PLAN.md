# VOLUME VI: DEFENCE READINESS, ARCHITECTURAL DECISIONS & PRIORITIZED ACTION PLAN

**Document ID:** `docsvF/06_DEFENCE_READINESS_GAP_ANALYSIS_AND_ACTION_PLAN.md`  
**Classification:** Strategic Engineering Roadmap & Compliance Audit  
**Project:** DRDO Aero-Twin (Project ANUMAAN)  
**SIH Problem Statement ID:** 26054  
**Date of Audit:** September 2026  
**Status:** Authoritative Working Standard  

---

## 24. DEFENCE & AEROSPACE READINESS GAP ANALYSIS

To determine whether Project ANUMAAN is genuinely deployable in a military operational environment (e.g. integrated into a DRDO Ground Control Station), we evaluated the codebase against standard defence engineering criteria:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DEFENCE & AEROSPACE GAP ANALYSIS MATRIX                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   DIMENSION                 CURRENT REALITY              DEFENCE TARGET (TRL 7+)       │
│                                                                                        │
│   1. Safety & Fail-Safe     Read-only advisory (LOI 2)   Isolated DAL-C boundary       │
│   2. Determinism            6.1 ms per 50 ms tick        Hard real-time RTOS edge      │
│   3. Datalink Loss          Store-and-forward queue      Auto-resilient SATCOM sync    │
│   4. Cybersecurity          CAN IDS + Merkle logs        mTLS + Hardware Enclave / HSM │
│   5. Verification           309 tests passing            DO-178C MC/DC formal coverage │
│   6. Sensor Resilience      Sanity gating + shielding    Dual-lane voting redundancy   │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 24.1 Detailed Compliance Gap Assessment

| Dimension | Engineering Requirement | Current Codebase Capability | Status | Remaining Military Gap | Path to TRL-7 Operational Readiness |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Safety & Fail-Safe** | Advisory isolation; software failure must never endanger airframe control. | Operates strictly as a read-only advisory system under STANAG 4586 LOI 2. Zero actuator feedback commands. | **COMPLIANT** | None for ground station; airborne unit requires hardware memory protection. | Formal software safety audit by CEMILAC certifying advisory-only data isolation. |
| **Deterministic Processing** | Predictable execution latency without memory allocation jitter. | Average frame pipeline latency is $6.1\text{ ms}$ (tested in [`tests/test_detect_stack.py`](file:///d:/Programming/PS054/tests/test_detect_stack.py)), well within $50\text{ ms}$ deadline. | **HIGH READINESS** | Python garbage collection introduces occasional micro-jitter ($\pm 2\text{ ms}$). | Port onboard edge DSP and FlyHash feature extraction to C++ / Rust on FreeRTOS or Zephyr. |
| **Network & Jamming Resilience** | Maintain operational integrity under electronic warfare RF jamming. | Store-and-forward buffer ([`backend/link/link_emulator.py`](file:///d:/Programming/PS054/backend/link/link_emulator.py)) tolerates 3-second blackouts with 100% recovery. | **VERIFIED** | Datalink loss $>10\text{ minutes}$ fills RAM buffer if unmanaged. | Spool high-rate edge logs to non-volatile onboard NVMe SSD during prolonged blackouts. |
| **Cybersecurity & Bus Integrity** | Detect adversarial bus injection, spoofing, and unauthorized telemetry tampering. | Real-time CAN IDS ([`backend/security/can_ids.py`](file:///d:/Programming/PS054/backend/security/can_ids.py)) + SHA-256 Merkle audit trail ([`backend/security/merkle_log.py`](file:///d:/Programming/PS054/backend/security/merkle_log.py)). | **VERIFIED** | Keys currently managed in software; no Hardware Security Module (HSM). | Integrate TPM 2.0 / HSM for hardware cryptographic signing of Merkle roots. |
| **Sensor Resilience & FDIR** | Isolate sensor failures to prevent false engine emergency shutdowns. | Rate-of-change filter ($dT/dt \le 1.5^\circ\text{C/s}$) and residual zero-shielding ([`backend/physics/sensor_validator.py`](file:///d:/Programming/PS054/backend/physics/sensor_validator.py)). | **COMPLIANT** | Single thermocouples per cylinder head; no triple-modular voting redundancy. | Integrate cross-channel analytical estimation to reconstruct missing sensor values. |
| **Model Uncertainty & Assurance** | Verifiable statistical confidence bounds on all prognostic outputs. | Finite-sample Split-Conformal prediction intervals on RUL ([`backend/evaluation/conformal.py`](file:///d:/Programming/PS054/backend/evaluation/conformal.py)). | **VERIFIED** | Calibration set currently utilizes synthetic degradation trajectories. | Calibrate non-conformity quantiles against physical engine dyno test runs. |

---

## 25. THE RECOMMENDED TARGET MULTI-LAYER ARCHITECTURE

Based on our complete audit, the recommended target architecture for Project ANUMAAN is organized into **seven distinct, decoupled architectural layers**:

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                        RECOMMENDED TARGET ARCHITECTURE                                        ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                               ║
║   1. DETERMINISTIC EDGE AVIONICS LAYER (Onboard UAV Hardware: ARM Cortex-A53 / Orin Nano)                    ║
║   ├── High-Rate Acquisition: CANaerospace (500 kbit/s) + 10 kHz Vibration ADC                                 ║
║   ├── Signal Processing: Fast Fourier Transform, Order Tracking, Kurtosis, RMS Extraction                     ║
║   ├── Sensor Integrity Gating: Rate-of-change filtering ($dT/dt$) and zero-shielding                          ║
║   ├── Edge Novelty Gate: FlyHash sparse coding ($<5\text{ ms}$, zero-training bitmask)                        ║
║   └── Telemetry Compression & Encryption: MAVLink framing $\le 21\text{ kbit/s}$ + AES-GCM-256                ║
║                                                                                                               ║
║   2. RESILIENT DATALINK LAYER (Line-of-Sight C-Band / Beyond-Line-of-Sight Ku-Band Satellite)                 ║
║   ├── Bandwidth Budget: Strictly constrained to $25\text{--}30\text{ kbit/s}$                                 ║
║   ├── Store-and-Forward Queue: Resilient packet retransmission across jamming blackouts                       ║
║   └── Tamper-Evident Transport: Sequence counter tracking and cryptographic CRC-32 validation                 ║
║                                                                                                               ║
║   3. REAL-TIME DIGITAL TWIN CORE LAYER (Ground Control Station Server)                                        ║
║   ├── State Ingestion: 20 Hz frame ordering and timestamp synchronization                                     ║
║   ├── Thermodynamic Plant Baseline: Analytical physics model computing expected values                       ║
║   ├── Physics Residual Generator: $\mathbf{r}(t) = \mathbf{y}_{\text{measured}} - \mathbf{y}_{\text{expected}}$║
║   └── Joint State Estimator: Unscented Kalman Filter (UKF) tracking unmeasured degradation parameters         ║
║                                                                                                               ║
║   4. COGNITIVE AI & DIAGNOSTIC LAYER (GCS High-Performance Tier)                                              ║
║   ├── Anomaly Fusion: Mahalanobis distance + EWMA + FlyHash consensus                                         ║
║   ├── Bayesian Failure Ranker: 20-mode MIL-STD-1629A hypothesis ranker under partial observations            ║
║   ├── Active Perturbation Testing: Information-gain selector resolving symptom ambiguities                   ║
║   └── Dual-Path Conformal Prognostics: Rainflow fatigue counting + SINDy wear trend extrapolation             ║
║                                                                                                               ║
║   5. TACTICAL MISSION & DECISION LAYER                                                                        ║
║   ├── Propulsion Degradation Linkage: Maps thermal wear to available propulsive thrust                        ║
║   ├── UAV Dynamic Flight Envelope: Evaluates ceiling, climb rate, and speed envelope shrinkage                ║
║   ├── Monte Carlo Reliability Simulation: 1,000-rollout mission completion probability $P(\text{completion})$ ║
║   └── Prescriptive Advisory: Throttle derate ladder recommendations and emergency glide divert polygons      ║
║                                                                                                               ║
║   6. FORENSIC DATA & FLEET LOGISTICS LAYER                                                                    ║
║   ├── Cryptographic Blackbox: SHA-256 chained Merkle tree forensic flight recorder                            ║
║   ├── High-Performance Storage: TimescaleDB time-series hypertables + Parquet cold archival                   ║
║   └── Automated Logistics: ATA 100 maintenance work package generation and parts provisioning                 ║
║                                                                                                               ║
║   7. SYNCHRONIZED VISUALIZATION LAYER                                                                         ║
║   ├── Tactical Operator HUD: Low-latency Primary Flight Display and alarm annunciator                          ║
║   ├── Interactive 3D WebGL Twin: Three.js client with live kinematics and thermal heatmaps                    ║
║   └── Master Engineering CAD Viewport: Headless/interactive raytraced component teardown HUD                  ║
║                                                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 26. ARCHITECTURAL DECISION RECORDS (ADRS)

Every major technology choice in Project ANUMAAN is grounded in aerospace systems engineering rationale:

### ADR-01: FastAPI for Authoritative Server Runtime
* **Decision:** Use FastAPI (Python 3.12) as the primary backend server framework.
* **Context:** Need a high-performance framework supporting asynchronous WebSockets (20 Hz telemetry) alongside typed REST endpoints.
* **Alternatives Evaluated:** Flask (lacks native async WebSocket concurrency), Django (excessive ORM overhead), Node.js / Express (requires bridging to Python scientific libraries).
* **Reasoning:** FastAPI natively integrates Python's `asyncio`, supports auto-generated OpenAPI documentation, uses Pydantic for strict schema validation, and allows direct in-process execution of NumPy and Scipy scientific models.
* **Consequence:** Single unified process for APIs, physics models, and WebSocket distribution.

### ADR-02: Three.js with Draco WASM for WebGL Visualization
* **Decision:** Use Three.js r128 with WebAssembly Draco geometry compression for the browser 3D client.
* **Context:** Need an interactive 3D digital twin that runs across any standard web browser without requiring local software installation or heavy graphics hardware.
* **Alternatives Evaluated:** Unity WebGL (massive 80 MB download size; long loading times; rigid canvas container), Unreal Engine Pixel Streaming (requires dedicated GPU server for every connected client; massive cloud cost).
* **Reasoning:** Three.js with Draco reduces 3D CAD assets from $78\text{ MB} \to <2.5\text{ MB}$, decompressing in $<300\text{ ms}$ in browser background worker threads. It allows custom GLSL fragment shaders for live thermal heatmaps and enables $0\text{ ms}$ multi-engine switching.
* **Consequence:** Fast, lightweight, zero-install 3D visualization accessible from any tactical workstation.

### ADR-03: FlyHash Sparse Coding for Edge Novelty Gating
* **Decision:** Implement the FlyHash expand-and-sparsify algorithm for onboard edge novelty detection.
* **Context:** Need an onboard edge anomaly detector running on low-power avionics hardware (e.g. Raspberry Pi / ARM Cortex) under strict microsecond latency constraints.
* **Alternatives Evaluated:** Quantized Autoencoder (requires backpropagation training; susceptible to catastrophic forgetting), Isolation Forest (high tree-traversal memory overhead on streaming data).
* **Reasoning:** FlyHash uses fixed sparse random projections ($k=6$) and Winner-Take-All selection. It executes in $<0.25\text{ ms}$ using integer addition and partial selection. It requires zero backpropagation training, calibrating via simple bitwise OR operations during ground run-up.
* **Consequence:** Ultra-low-power, deterministic novelty detection that never crashes due to optimizer instability.

### ADR-04: Split-Conformal Prediction for Remaining Useful Life (RUL)
* **Decision:** Wrap prognostic wear extrapolations in exact finite-sample Split-Conformal Prediction intervals.
* **Context:** Military operators cannot base mission decisions on single-point RUL estimates without knowing epistemic uncertainty.
* **Alternatives Evaluated:** Bayesian Neural Networks (computationally intractable at 20 Hz; sensitive to prior selection), Particle Filtering (susceptible to particle degeneracy and sample impoverishment during sudden flight transients).
* **Reasoning:** Split-conformal prediction provides a mathematically rigorous coverage guarantee ($P(Y \in \mathcal{C}) \ge 1 - \alpha$) in finite samples without requiring Gaussian or distributional assumptions.
* **Consequence:** Defensible, verifiable confidence intervals for UAV commanders.

### ADR-05: Merkle Tree Forensic Flight Logging
* **Decision:** Structure post-flight logs as a SHA-256 chained Merkle tree.
* **Context:** Military incident investigations require absolute proof of flight telemetry immutability.
* **Alternatives Evaluated:** Plain JSON / CSV logging (easily altered post-flight without detection), Centralized SQL database (vulnerable to database administrator tampering).
* **Reasoning:** Merkle trees cryptographically chain each state frame to previous frames. Altering a single sensor value in a 10-hour flight log instantly invalidates the root hash.
* **Consequence:** Military-grade forensic assurance with minimal computational overhead ($<0.4\text{ ms}$ per block).

---

## 27. DEPRECATION & REMOVAL REGISTRY

To keep the engineering codebase lean and maintainable, components that provide no functional or technical value have been flagged for retirement:

| Component / File Path | Current Classification | Technical Finding & Rationale | Recommended Action |
| :--- | :--- | :--- | :--- |
| **`web/usavionix/`** | **DECORATIVE / ARCHIVE** | Next.js static mirror of commercial website. Completely disconnected from backend telemetry and digital twin models. | **PERMANENTLY REMOVE / ARCHIVE** |
| **Pre-Restructure Path References** | **OBSOLETE CODE** | References to old paths (e.g. `3d_models/rotax_912_is_sport.blend`) in legacy batch scripts. | **CLEANED & RE-DERIVED** via `__file__` |
| **`backend/ml/rul_estimator.py`** | **LEGACY STUB** | Original heuristic linear RUL estimator; superseded by dual-path conformal estimator in [`backend/prognose/rul.py`](file:///d:/Programming/PS054/backend/prognose/rul.py). | **REPLACE REFERENCES** with `backend/prognose/` |
| **Root Level Renders** | **DUPLICATE ASSETS** | Stray render outputs in top-level directory. | **CONSOLIDATE** into `assets/renders/` |

---

## 28. PRIORITIZED ACTION PLAN (ROADMAP TO SIH EVALUATION)

All remaining engineering enhancements have been prioritized into four distinct urgency tiers:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        PRIORITIZED ACTION PLAN (P0 - P3)                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   [P0: CRITICAL]   Core Problem Statement & System Credibility Gaps                    │
│   [P1: HIGH]       Major Engineering Architecture Enhancements                         │
│   [P2: MEDIUM]     Operational Optimization & Refactoring                              │
│   [P3: LOW]        Visual Polish & Extended Documentation                              │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 28.1 P0 — Critical Priority (Must Be Ready for SIH Final Evaluation)
1. **P0-1: Unified Single-Click Platform Launcher**
   * *Target Module:* [`run_app.py`](file:///d:/Programming/PS054/run_app.py) & [`launch_standalone_app.bat`](file:///d:/Programming/PS054/launch_standalone_app.bat)
   * *Required Change:* Ensure executing a single command starts the FastAPI authoritative server and automatically opens the Three.js WebGL digital twin in the default browser at `http://localhost:8000/`.
   * *Validation:* Clean execution test on a fresh machine with zero manual path edits.
2. **P0-2: Maintain 100% AST Ground-Truth Isolation**
   * *Target Module:* [`tests/test_no_truth_leak.py`](file:///d:/Programming/PS054/tests/test_no_truth_leak.py)
   * *Required Change:* Ensure no new PR or commit introduces reads of `FAULT_ID` or `HEALTH_INDEX` on the live inference path.
   * *Validation:* Automated execution of `pytest tests/test_no_truth_leak.py` in pre-commit hook.
3. **P0-3: Demonstration Fault Injection Script Reliability**
   * *Target Module:* [`backend/server/engine_service.py`](file:///d:/Programming/PS054/backend/server/engine_service.py)
   * *Required Change:* Verify that injecting any of the 20 failure modes produces immediate physical-to-visual causal reaction in the 3D WebGL client (mesh highlighting + camera pan).
   * *Validation:* Run full automated API verification test suite (`pytest tests/test_server_api.py`).

### 28.2 P1 — High Priority (Major Engineering Enhancements)
1. **P1-1: Persistent TimescaleDB Hypertables**
   * *Target Module:* `backend/database/timescale.py`
   * *Required Change:* Add optional persistent storage adapter dumping 20 Hz telemetry frames to PostgreSQL / TimescaleDB hypertables for long-term fleet analytics.
   * *Validation:* Verify $>1,000\text{ inserts/sec}$ with zero telemetry frame drops.
2. **P1-2: Multi-Airframe Dynamic Glide Polygons**
   * *Target Module:* [`backend/mission/reliability.py`](file:///d:/Programming/PS054/backend/mission/reliability.py)
   * *Required Change:* Enhance glide reachability calculations by incorporating real-time wind vectors and digital elevation terrain shadowing.
   * *Validation:* Simulated mountain barrier avoidance during simulated engine seizure.

### 28.3 P2 — Medium Priority (Optimization & Performance)
1. **P2-1: Binary Telemetry Serialization (Protobuf)**
   * *Target Module:* [`backend/server/engine_api.py`](file:///d:/Programming/PS054/backend/server/engine_api.py)
   * *Required Change:* Provide binary Protocol Buffers encoding over WebSockets to reduce JSON CPU serialization overhead from $2.5\text{ ms} \to 0.3\text{ ms}$.
2. **P2-2: C++ / Rust Edge Micro-Kernel Port**
   * *Target Module:* `backend/edge/native/`
   * *Required Change:* Compile FlyHash and sensor rate gating to a standalone C++ binary for deployment on bare-metal microcontroller boards (STM32H7 / TI TMS570).

### 28.4 P3 — Low Priority (Polish & Documentation)
1. **P3-1: Archive Unused Web Mirrors**
   * *Action:* Move `web/usavionix/` to an archive branch to eliminate repository clutter.
2. **P3-2: Automated Video Demonstration Reel**
   * *Action:* Render high-resolution video walkthroughs of the 120 FPS Ladakh Canyon flight simulation and Blender CAD component teardowns.

---

## 29. MASTER CURRENT VS. REQUIRED MATRIX

The following comprehensive matrix benchmarks the current reality of the codebase against the final requirements for an operational military digital twin system:

| Operational Area | Current Codebase Reality | Code Evidence | Identified Gap | Required Final Production State | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Problem Statement Scope** | Implements all 8 required fault classes and 6 required functional modules | [`tests/test_fun_req_compliance.py`](file:///d:/Programming/PS054/tests/test_fun_req_compliance.py) | Full prototype; lacks real physical flight validation | Physical engine test bench validation campaign | **P1** |
| **Telemetry Ingestion** | 20 Hz synchronized frames over WebSockets and SocketCAN emulation | [`backend/runtime/hub.py`](file:///d:/Programming/PS054/backend/runtime/hub.py) | Proprietary Rotax CAN IDs are simulated via public DBC | Integration with physical FADEC acquisition hardware | **P1** |
| **Real-Time Performance** | Complete pipeline turnaround in $6.07\text{ ms}$ ($87\%$ CPU idle headroom) | [`tests/test_detect_stack.py`](file:///d:/Programming/PS054/tests/test_detect_stack.py) | Python runtime introduces occasional micro-jitter | Deterministic C++ micro-kernel on RTOS | **P2** |
| **Digital Twin Model** | Lumped-parameter thermofluid model + Joint UKF state estimation | [`backend/twin/model.py`](file:///d:/Programming/PS054/backend/twin/model.py), [`backend/twin/ukf.py`](file:///d:/Programming/PS054/backend/twin/ukf.py) | Spatial thermal gradients simplified to lumped nodes | 3D multi-node finite difference thermal mesh | **P2** |
| **Physics Redundancy** | Analytical expected baseline subtracting measured state to yield residuals | [`backend/physics/thermo_model.py`](file:///d:/Programming/PS054/backend/physics/thermo_model.py) | Steady-state maps; transient heat lag simplified | Full dynamic transient heat-sink transfer network | **P2** |
| **Sensor Validation** | Rate-of-change filtering ($dT/dt \le 1.5^\circ\text{C/s}$) + residual shielding | [`backend/physics/sensor_validator.py`](file:///d:/Programming/PS054/backend/physics/sensor_validator.py) | Single-sensor channels; no physical triple-voting | Triple-modular redundant (TMR) hardware sensor suite | **P1** |
| **Edge Novelty Gating** | FlyHash sparse coding ($26 \to 520$ KCs, $5\%$ WTA) running in $<0.25\text{ ms}$ | [`backend/ml/flyhash_novelty.py`](file:///d:/Programming/PS054/backend/ml/flyhash_novelty.py) | Operates on residuals only; order features pending wire | Direct high-rate order-tracking feature fusion | **P1** |
| **Fault Diagnosis** | 20-mode Bayesian Network ranker with active perturbation testing | [`backend/diagnose/bn.py`](file:///d:/Programming/PS054/backend/diagnose/bn.py) | Probability tables tuned on simulated FMECA data | Empirical tuning on seeded-fault test bench recordings | **P1** |
| **Prognostics (RUL)** | Dual-path Rainflow fatigue counting + SINDy with split-conformal intervals | [`backend/prognose/rul.py`](file:///d:/Programming/PS054/backend/prognose/rul.py) | SINDy wear coefficients calibrated on synthetic data | Overhaul correlation with physical teardown wear | **P1** |
| **Mission Simulation** | 1,000-rollout Monte Carlo flight completion and glide risk forecasting | [`backend/mission/reliability.py`](file:///d:/Programming/PS054/backend/mission/reliability.py) | Wind vectors modeled as static Gaussian turbulence | Live meteorological radar weather grid integration | **P2** |
| **Forensic Logging** | Cryptographic SHA-256 chained Merkle tree with 100% tamper detection | [`backend/security/merkle_log.py`](file:///d:/Programming/PS054/backend/security/merkle_log.py) | Stored as local JSON chunk files on host filesystem | Tamper-proof non-volatile crash-hardened solid-state memory | **P1** |
| **3D CAD Visualization** | Three.js WebGL twin (0 ms engine switch) + 80 MB Blender Master CAD twin | [`web/site/`](file:///d:/Programming/PS054/web/site/), [`assets/blender/`](file:///d:/Programming/PS054/assets/blender/) | WebGL shaders use simplified Phong reflection | Real-time WebGPU physically-based raytracing | **P3** |
| **Tactical GCS HUD** | Hardware-accelerated Pygame desktop display with ISA-18.2 alarms | [`apps/desktop_gcs/standalone_gui_app.py`](file:///d:/Programming/PS054/apps/desktop_gcs/standalone_gui_app.py) | Python SDL wrapper; standalone execution | STANAG 4586 compliant avionic GCS software console | **P1** |
