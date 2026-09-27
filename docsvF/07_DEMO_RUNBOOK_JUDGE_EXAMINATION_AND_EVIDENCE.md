# VOLUME VII: DEMO RUNBOOK, JUDGE CROSS-EXAMINATION & EVIDENCE MATRIX

**Document ID:** `docsvF/07_DEMO_RUNBOOK_JUDGE_EXAMINATION_AND_EVIDENCE.md`  
**Classification:** Operational Runbook, Defence Cross-Examination & Verification Evidence  
**Project:** DRDO Aero-Twin (Project ANUMAAN)  
**SIH Problem Statement ID:** 26054  
**Date of Audit:** September 2026  
**Status:** Authoritative Working Standard  

---

## 30. DRDO & SIH JUDGE CROSS-EXAMINATION QUESTION BANK

During final evaluations, technical evaluators from DRDO (Aeronautical Development Establishment, Gas Turbine Research Establishment, Vehicles Research & Development Establishment) and academic panels will scrutinize every design decision. 

Below are the most rigorous questions anticipated, paired with honest, verifiable answers and supporting code evidence.

---

### Question 1: *"Is this actually a Digital Twin, or just a 3D CAD model connected to synthetic telemetry?"*
* **What We Can Answer Today:**
  * It is an authenticated cyber-physical Digital Twin operating at **STANAG 4586 Level of Interoperability 2**. The 3D visualization is merely an output consumer.
  * The actual Digital Twin is an in-memory state-space thermodynamic model ([`backend/twin/model.py`](file:///d:/Programming/PS054/backend/twin/model.py)) coupled with a **Joint State/Parameter Unscented Kalman Filter (UKF)** ([`backend/twin/ukf.py`](file:///d:/Programming/PS054/backend/twin/ukf.py)).
  * The twin estimates unmeasured physical degradation states (e.g. radiator heat exchanger scaling factor, blow-by wear) in real time from measured temperatures, pressures, and RPM.
* **Evidence:**
  * [`backend/twin/model.py`](file:///d:/Programming/PS054/backend/twin/model.py) (lumped-capacitance energy equations).
  * [`backend/twin/ukf.py`](file:///d:/Programming/PS054/backend/twin/ukf.py) (sigma-point UKF implementation; validated in `E21` with mean normalized innovation squared of $0.9957$).
  * [`tests/test_char_twin.py`](file:///d:/Programming/PS054/tests/test_char_twin.py) (automated state-space convergence test).
* **What We Cannot Currently Answer:**
  * We cannot claim physical in-flight telemetry validation on an active DRDO TAPAS-BH-201 airframe because military flight data is classified and requires institutional memorandum of understanding (MoU).
* **Required Roadmap:**
  * Conduct a test-cell dynamometer campaign on an instrumented Rotax 912 iS with real thermocouples and accelerometers to calibrate UKF noise covariance matrices.

---

### Question 2: *"How can your Fly-Brain model predict anomalies correctly if you never trained it?"*
* **What We Can Answer Today:**
  * The **FlyHash algorithm** ([`backend/ml/flyhash_novelty.py`](file:///d:/Programming/PS054/backend/ml/flyhash_novelty.py)) is an expand-and-sparsify **Locality-Sensitive Hashing (LSH)** novelty detector based on Dasgupta et al. (*Science* 2017) and Ryali et al. (ICML 2020), modeling the *Drosophila* olfactory circuit.
  * It does **not** perform classification; it performs one-class novelty gating.
  * It maps a 26-dimensional residual vector into 520 high-dimensional Kenyon cells via a fixed sparse binary random projection ($k=6$). A Winner-Take-All inhibition selects only the top 5% (26 bits).
  * During the first 200 frames of healthy engine ground run-up, active bits are folded into a Bloom filter bitmask (`_seen |= code`) via simple bitwise OR. **No weights are learned; no backpropagation occurs.**
  * When a fault occurs, the physics residuals depart from the nominal hypersphere, activating novel Kenyon cells. If $\ge 60\%$ of active bits have never fired during calibration, it flags an anomaly in $<0.25\text{ ms}$.
* **Evidence:**
  * [`backend/ml/flyhash_novelty.py`](file:///d:/Programming/PS054/backend/ml/flyhash_novelty.py) (full source code with scientific attribution).
  * [`tests/test_flyhash_novelty.py`](file:///d:/Programming/PS054/tests/test_flyhash_novelty.py) (11 tests verifying sparsity, repeatability, and latency $<5\text{ ms}$).
  * [`tests/test_no_truth_leak.py`](file:///d:/Programming/PS054/tests/test_no_truth_leak.py) (proves FlyHash calibrates on frame count, with zero ground-truth leakage).
* **What We Cannot Currently Answer:**
  * Pure FlyHash cannot classify *which* fault occurred—it only flags novelty. Multi-class fault diagnosis must be handled downstream by the Bayesian Network or Random Forest.
* **Required Roadmap:**
  * Fuse order-domain vibration features directly into the online FlyHash input vector once hardware acquisition is deployed.

---

### Question 3: *"Where did you get your training data? Did you train on real UAV crash logs?"*
* **What We Can Answer Today:**
  * We state plainly: **There is no public run-to-failure dataset for aero-piston engines on MALE UAVs in the world.** Claiming otherwise would be false.
  * We use an honest, defensible **multi-tier data validation strategy**:
    1. *Proxy Benchmarks (32 GB Suite):* Validated RUL algorithms on NASA C-MAPSS / N-CMAPSS; vibration classification on Paderborn and CWRU; bearing run-to-failure on XJTU-SY and IMS; real flight telemetry on NASA ACES (Altus II UAV with Rotax 914 Turbo); real UAV anomalies on ALFA.
    2. *Physics-Based Decoupled Simulation:* High-fidelity virtual plant model ([`backend/plant/virtual_engine.py`](file:///d:/Programming/PS054/backend/plant/virtual_engine.py)) for closed-loop software integration.
* **Evidence:**
  * [`Datasets/download_all.py`](file:///d:/Programming/PS054/Datasets/download_all.py) (reproducible multi-tier dataset downloader).
  * [`backend/datasets/`](file:///d:/Programming/PS054/backend/datasets/) (standardized loaders for C-MAPSS, CWRU, ALFA, ACES).
  * [`Datasets/README.md`](file:///d:/Programming/PS054/Datasets/README.md) (honest data posture and licensing breakdown).
* **What We Cannot Currently Answer:**
  * Synthetic degradation wear rates ($\theta_{\text{wear}}$) are based on empirical wear equations rather than physical engine teardown measurements.
* **Required Roadmap:**
  * Partner with DRDO / ADE to ingest declassified ground run-up logs from the TAPAS-BH-201 test rig at Aeronautical Test Range (ATR) Chitradurga.

---

### Question 4: *"How does your system prevent false alarms caused by noisy or failing sensors?"*
* **What We Can Answer Today:**
  * We implement **Analytical Redundancy** and **Rate-of-Change Gating** in [`backend/physics/sensor_validator.py`](file:///d:/Programming/PS054/backend/physics/sensor_validator.py).
  * Heavy physical cylinder heads have significant thermal mass. In real operation, $|d\text{CHT}/dt| \le 1.5^\circ\text{C/s}$.
  * If a thermocouple wire loosens or shorts, CHT jumps by $+30^\circ\text{C}$ in a single $50\text{ ms}$ tick ($600^\circ\text{C/s}$). The validator flags **Sensor Glitch / Electrical Fault** rather than an engine over-temperature emergency.
  * When a sensor is declared invalid, its corresponding residual in $\mathbf{r}(t)$ is **zero-shielded**, preventing corrupted instrumentation from biasing the UKF state or triggering false alarms.
* **Evidence:**
  * [`backend/physics/sensor_validator.py`](file:///d:/Programming/PS054/backend/physics/sensor_validator.py) (rate-of-change and residual shielding implementation).
  * [`tests/test_fun_req_compliance.py::test_sensor_drift_detection_and_residual_shielding`](file:///d:/Programming/PS054/tests/test_fun_req_compliance.py).
* **What We Cannot Currently Answer:**
  * If two redundant sensors both drift simultaneously in identical directions, analytical rate checks alone cannot isolate the drift without cross-channel thermodynamic balancing.
* **Required Roadmap:**
  * Deploy dual-lane CAN FADEC divergence monitoring (comparing Lane A vs Lane B sensors).

---

### Question 5: *"What happens if the satellite datalink is jammed or severed during combat?"*
* **What We Can Answer Today:**
  * The system is explicitly architected with a **decoupled Edge-to-GCS split** ([`backend/edge/`](file:///d:/Programming/PS054/backend/edge/), [`backend/link/link_emulator.py`](file:///d:/Programming/PS054/backend/link/link_emulator.py)).
  * The deterministic edge layer (running on UAV avionics) runs autonomously. It extracts vibration features, computes fast physics residuals, executes FlyHash novelty gating, and writes all high-rate telemetry to an onboard non-volatile blackbox.
  * In the event of electronic warfare RF jamming, the **Store-and-Forward Datalink Queue** retains compressed state packets. Once the datalink is restored, packets are burst-transmitted and re-synchronized on the ground without data loss.
* **Evidence:**
  * [`backend/link/link_emulator.py`](file:///d:/Programming/PS054/backend/link/link_emulator.py) (RF jamming emulator with queue buffering).
  * [`tests/test_edgelink_stack.py`](file:///d:/Programming/PS054/tests/test_edgelink_stack.py) (verified 100% packet recovery across 3-second jamming blackouts in `E23`).
* **What We Cannot Currently Answer:**
  * Extended jamming lasting several hours will eventually saturate onboard volatile RAM buffers unless spooled to flash storage.
* **Required Roadmap:**
  * Implement automatic onboard flash memory spooling with dynamic compression throttling.

---

### Question 6: *"Can your AI model hallucinate an engine shutdown command?"*
* **What We Can Answer Today:**
  * **No. It is architecturally impossible.**
  * The system operates under strict **STANAG 4586 Level of Interoperability 2** (telemetry monitoring and decision support only).
  * There is **zero software feedback path from the AI diagnostic engine or Voice Copilot to the flight control computer or engine throttle actuators**.
  * The AI output is strictly read-only advisory. All critical actions (throttle derating, diversion) require explicit human flight commander confirmation.
* **Evidence:**
  * [`backend/server/engine_api.py`](file:///d:/Programming/PS054/backend/server/engine_api.py) (REST/WebSocket architecture provides zero actuator command endpoints).
  * [`backend/voice/copilot.py`](file:///d:/Programming/PS054/backend/voice/copilot.py) (Voice Copilot is strictly read-only RAG over documentation).
  * [`tests/test_voice_copilot.py`](file:///d:/Programming/PS054/tests/test_voice_copilot.py) (verifies copilot executes in isolated read-only sandbox).
* **What We Cannot Currently Answer:**
  * We cannot guarantee that an operator under extreme cognitive stress will always interpret advisory probabilities correctly without specialized training.
* **Required Roadmap:**
  * Implement standard military green/amber/red ISA-18.2 rationalized alarm annunciations to prevent cognitive overload.

---

## 31. END-TO-END SIH DEMONSTRATION RUNBOOK

*This runbook provides the exact, step-by-step procedure to execute the live demonstration before evaluation judges.*

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                        SIH LIVE DEMONSTRATION SEQUENCE                                        ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                               ║
║   STEP 1: PRE-FLIGHT SYSTEM INITIALIZATION                                                                    ║
║   ├── Run `launch_standalone_app.bat` or `python run_app.py server`                                           ║
║   ├── Open browser to `http://localhost:8000/` (WebGL Digital Twin)                                           ║
║   └── Confirm all 5 engines online; 20 Hz WebSocket connected; Health Scores = 100                            ║
║                                                                                                               ║
║   STEP 2: NOMINAL RUN-UP & MULTI-ENGINE SWITCHING (0ms)                                                       ║
║   ├── Advance throttle from 20% (Idle) to 85% (Climb)                                                         ║
║   ├── Observe kinematic crankshaft and propeller rotation spooling up dynamically                            ║
║   └── Switch active view from Rotax 912 iS -> Austro AE300 -> Rotax 915 iS (Demonstrating 0ms WebGL switch)   ║
║                                                                                                               ║
║   STEP 3: SENSOR GLITCH DISCRIMINATION (FDIR)                                                                 ║
║   ├── Inject Sensor Failure: Fault 10 (CHT 2 Thermocouple Open Circuit)                                       ║
║   ├── Point out: Rate-of-change filter ($dT/dt > 10^\circ C/s$) detects electrical glitch in 50 ms             ║
║   └── Residual is shielded; engine health remains green; proves system does not panic on bad sensors          ║
║                                                                                                               ║
║   STEP 4: PHYSICAL FAULT INJECTION & FLY-BRAIN GATING                                                         ║
║   ├── Inject Real Fault: Fault 1 (Cylinder 3 Fuel Injector Clogging)                                          ║
║   ├── Show: FlyHash novelty score jumps from 0.05 -> 0.82 (Zero-training biological edge gate fires)          ║
║   ├── Show: Residuals diverge ($d_CHT3 = +24^\circ C, d_EGT3 = -48^\circ C$)                                  ║
║   └── Show: Bayesian Ranker diagnoses `INJ_CLOG_CYL3` with 94% confidence                                     ║
║                                                                                                               ║
║   STEP 5: VISUAL ATTRIBUTION & CAMERA DIRECTOR                                                                ║
║   ├── Three.js CameraDirector smoothly pans and focuses directly on Cylinder 3 fuel injector                  ║
║   └── GLSL fragment shader pulses cylinder head in thermal emissive warning red                               ║
║                                                                                                               ║
║   STEP 6: PROGNOSTICS, MISSION IMPACT & PRESCRIPTIVE ADVISORY                                                 ║
║   ├── Show RUL: Conformal prediction interval drops from 520h -> [38.2, 49.5]h                                ║
║   ├── Show Mission Risk: Monte Carlo simulator calculates $P(completion)$ drops from 99.8% -> 42.1%           ║
║   └── Prescriptive Advisory: Displays throttle derate ladder (Derate to 64% restores safe recovery margin)    ║
║                                                                                                               ║
║   STEP 7: POST-FLIGHT FORENSIC AUDIT                                                                          ║
║   ├── Show Merkle flight ledger (`backend/security/merkle_log.py`)                                            ║
║   └── Demonstrate SHA-256 cryptographic tamper verification and ATA 100 maintenance work order                ║
║                                                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

### 31.1 Detailed Execution Commands

1. **Terminal 1: Start Authoritative FastAPI Backend Server**
   ```powershell
   python run_app.py server
   ```
   *Expected Output:*
   ```text
   ===========================================================================
   [RUN] LAUNCHING ROTAX DIGITAL TWIN LAPTOP BACKEND SERVER (0.0.0.0:8000)
         DRDO / iDEX Problem Statement ID: 26054
   ===========================================================================
   INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
   INFO:     Started server process [PID ...]
   INFO:     RuntimeHub initialized: 5 active engines clocked at 20 Hz
   ```

2. **Terminal 2: Launch Tactical Pygame Desktop GCS HUD (Optional Second Screen)**
   ```powershell
   python run_app.py pygame
   ```
   *Expected Output:* Hardware-accelerated SDL window opens displaying Primary Flight Display, real-time strip charts, and alarm annunciators.

3. **Terminal 3: Launch Ladakh Canyon 120 FPS Flight Simulation (High-Impact Visuals)**
   ```powershell
   python run_app.py canyon
   ```
   *Expected Output:* Blender opens maximized in Top Gun tactical chase view across the high-density Ladakh terrain model.

---

## 32. COMPREHENSIVE TESTING MANUAL & SYSTEM REPRODUCIBILITY

Every capability claimed in Project ANUMAAN is backed by automated tests:

### 32.1 Running the Complete Verification Suite
```powershell
pytest
```
*Current Verification Baseline:*
* **Total Tests:** 317 collected (309 passing, 8 skipped, 1 strict xfailed, 0 errors).
* **Execution Time:** $\approx 125\text{ seconds}$.

### 32.2 Targeted Subsystem Test Commands
* **Verify Zero Ground-Truth Leakage (AST Guard):**
  ```powershell
  pytest tests/test_no_truth_leak.py -v
  ```
* **Verify FlyHash Sparse Novelty Gating & Latency:**
  ```powershell
  pytest tests/test_flyhash_novelty.py -v
  ```
* **Verify Functional Requirements & Sensor Shielding:**
  ```powershell
  pytest tests/test_fun_req_compliance.py -v
  ```
* **Verify Independent Plant Decoupling:**
  ```powershell
  pytest tests/test_independent_plant_adapter.py -v
  ```
* **Verify Analytical Conformal RUL Pipeline:**
  ```powershell
  pytest tests/test_analytical_pipeline.py -v
  ```

---

## 33. TROUBLESHOOTING & OBSERVABILITY GUIDE

When running or demonstrating the platform, use the following quick-resolution decision tree:

| Symptom / Issue | Root Cause | Immediate Diagnostic Command | Corrective Action |
| :--- | :--- | :--- | :--- |
| **Telemetry not updating in WebGL UI** | WebSocket connection blocked or backend not started | Open Browser DevTools Console (F12) -> Check WS `ws://localhost:8000/ws/engines/rotax_912is` | Ensure `python run_app.py server` is running on port 8000; check firewall rules. |
| **Blender Twin throws `ModuleNotFoundError: bpy`** | Script executed with system Python instead of Blender executable | Check `python run_app.py verify` output | Blender scripts must be launched via `blender.exe --python script.py`. Set path in `run_app.py`. |
| **PermissionError / WinError 32 on save** | Windows multi-process file locking during concurrent mission graph saves | Check `task-*.log` in `.system_generated/` | Pre-existing Windows atomic replace issue; bounded retry wrapper in `backend/graph/mission_graph.py` resolves this automatically. |
| **FlyHash reports high novelty on healthy engine** | Calibration window was interrupted before 200 nominal frames elapsed | Check `calibrated: bool` in `/api/engines/{id}/diagnosis` | Allow engine to idle for at least 10 seconds (200 frames) before injecting faults. |
| **Voice Copilot fails to respond** | Missing OpenAI / Anthropic API Key in environment | Check `/api/copilot/query` response | System automatically falls back to deterministic local rule-based response. To enable full LLM, set `$env:OPENAI_API_KEY = "sk-..."`. |

---

## 34. MASTER ASSUMPTIONS REGISTER & FORMAL LIMITATIONS

To maintain total transparency with evaluators, all operational assumptions and current prototype limitations are formally registered:

### 34.1 Assumptions Register
1. **Reference Engine Baseline:** The physical models assume a Rotax 912 iS Sport baseline (100 HP, 1,352 cc, naturally aspirated) unless explicitly switched to Rotax 914, 915, Austro AE300, or VRDE 2.2L.
2. **Propeller Load Curve:** Absorbed propeller load is assumed to follow a standard cubic power curve: $P_{\text{prop}} \propto \rho_{\text{air}} \cdot \text{RPM}^3$.
3. **Ku-Band Datalink Allocation:** Telemetry downlink budget is assumed to be constrained to $25\text{--}30\text{ kbit/s}$ within a total tactical link capacity of $\approx 122\text{ kbit/s}$.
4. **ISA Atmosphere:** Ambient temperature and pressure lapse follow standard International Standard Atmosphere (ISA) equations with a configurable surface temperature offset ($\Delta T_{\text{ISA}}$).

### 34.2 Formal System Limitations
1. **Prototype Flight Validation:** The system has not yet flown on an active military UAV airframe; all validation is currently grounded in public benchmark datasets and decoupled physics simulation.
2. **Combustion Dynamics Resolution:** Crank-angle resolution is modeled down to $1^\circ$ CA; full 3D Computational Fluid Dynamics (CFD) in-cylinder combustion modeling is not performed in real time.
3. **Hardware Redundancy:** The prototype runs on standard commercial off-the-shelf (COTS) x86_64 / ARM hardware; formal dual-redundant lockstep avionic flight hardware has not yet been manufactured.
