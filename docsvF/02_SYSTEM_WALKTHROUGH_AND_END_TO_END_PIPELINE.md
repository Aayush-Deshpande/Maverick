# VOLUME II: SYSTEM WALKTHROUGH, RUNTIME ARCHITECTURE & END-TO-END DATA FLOW

**Document ID:** `docsvF/02_SYSTEM_WALKTHROUGH_AND_END_TO_END_PIPELINE.md`  
**Classification:** Core System Engineering Manual  
**Project:** DRDO Aero-Twin (Project ANUMAAN)  
**SIH Problem Statement ID:** 26054  
**Date of Audit:** September 2026  
**Status:** Authoritative Working Standard  

---

## 4. THE COMPLETE 13-STEP SYSTEM WALKTHROUGH

*This walkthrough teaches the system from physical mechanics to mathematical execution. After reading this section, an engineer with zero prior knowledge of the codebase can explain the complete system without opening the code.*

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                        THE 13-STEP LIFECYCLE OF A TELEMETRY FRAME                              ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                               ║
║   [Step 1: Physical Engine] ──▶ [Step 2: Sensor/Sim Generation] ──▶ [Step 3: Ingestion & Validation]          ║
║                                                                                   │                           ║
║   [Step 6: Digital Twin State] ◀── [Step 5: State Estimation (UKF)] ◀── [Step 4: Preprocessing & Filtering]   ║
║              │                                                                                                ║
║              ├──▶ [Step 7: Physics Residual Generation]                                                       ║
║              │             │                                                                                  ║
║              │             ▼                                                                                  ║
║              └──▶ [Step 8: AI/ML & FlyHash Gating] ──▶ [Step 9: Anomaly Detection & Diagnosis]                 ║
║                                                                  │                                            ║
║   [Step 12: Visualization HUD] ◀── [Step 11: Mission Reliability] ◀── [Step 10: Conformal Prognostics (RUL)]   ║
║              │                                                                                                ║
║              ▼                                                                                                ║
║   [Step 13: Cryptographic Storage & Post-Mission Replay]                                                     ║
║                                                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

---

### Step 1 — What is the Physical System?

The monitored physical system is the internal combustion propulsion unit of a **Medium-Altitude Long-Endurance (MALE) Unmanned Aerial Vehicle (UAV)**.
* **The Airframe Context:** The reference airframe is based on the **DRDO TAPAS-BH-201** (formerly Rustom-II). It features a wingspan of $20.6\text{ m}$, gross takeoff weight of $1,800\text{ kg}$, maximum operating ceiling of $28,000\text{--}30,000\text{ ft}$, operational radius of $250\text{ km}$ (extendable to $>1,000\text{ km}$ via satellite datalink), and endurance of $18\text{--}24\text{ hours}$.
* **The Engine Architecture:** The primary baseline powerplant is the **Rotax 912 iS Sport / 915 iS**, supplemented by configurations for the **Austro Engine AE300** (turbodiesel) and **VRDE Jayem 2.2L** (heavy-fuel CI). The Rotax 912 iS is a 4-cylinder, 4-stroke liquid/air-cooled opposed boxer engine with redundant electronic fuel injection and dual ignition (FADEC). It produces $73.5\text{ kW}$ ($100\text{ HP}$) at $5,800\text{ RPM}$ with a displacement of $1,352\text{ cm}^3$ and an integrated reduction gearbox ratio of $i = 2.43$ (propeller spins at $2,387\text{ RPM}$).
* **Sensor Instrumentation:**
  * 4 $\times$ Cylinder Head Temperature (CHT) thermocouples (Cyl 1–4, typ. Type J or PT100).
  * 4 $\times$ Exhaust Gas Temperature (EGT) thermocouples (Cyl 1–4, typ. K-type placed $100\text{ mm}$ downstream of exhaust valves).
  * 1 $\times$ Manifold Absolute Pressure (MAP) piezoresistive transducer ($20\text{--}115\text{ kPa}$).
  * 1 $\times$ Oil Pressure sensor ($0\text{--}10\text{ bar}$) & 1 $\times$ Oil Temperature thermistor ($-20\text{ to }150^\circ\text{C}$).
  * 1 $\times$ Fuel Flow turbine transducer ($0\text{--}40\text{ L/h}$) & Fuel Rail Pressure sensor ($3.0\pm 0.2\text{ bar}$).
  * 1 $\times$ High-bandwidth tri-axial piezoelectric accelerometer mounted on the engine crankcase/gearbox flange ($\pm 50\text{ g}, 10\text{ kHz}$).
  * Dual crank-angle VR/Hall-effect pickup sensors ($36-2$ tooth reluctor wheel for crank-synchronized injection/ignition timing).
* **Mission Context:** The UAV operates alone with zero inflight human maintenance access. Single-engine failure guarantees loss of the multi-crore aircraft or forced ditching in hostile terrain.

---

### Step 2 — Where Does the Data Come From?

Telemetry enters the system through three mutually exclusive channels:
1. **The Independent Plant Simulator (`backend/plant/virtual_engine.py`):**
   * A standalone physics plant model that simulates internal combustion dynamics, cylinder-by-cylinder thermal ODEs, manifold fluid flow, and progressive physical wear.
   * *Critical Decoupling:* It is mathematically isolated from the Digital Twin. The plant generates the "true" sensor readings with physical thermal inertia, transducer lag, and stochastic noise.
2. **Synthetic Telemetry Streamer (`backend/telemetry/can_streamer.py`):**
   * Lightweight 20 Hz frame generator producing synthetic FADEC frames with scriptable multi-fault injections (misfire, cooling degradation, oil leak, sensor drift).
3. **Historical / Replay Files (`backend/datasets/` & `backend/security/merkle_log.py`):**
   * Pre-recorded flight logs from benchmark sources (NASA ACES real flight data from Altus II with Rotax 914 Turbo, ALFA fixed-wing UAV flights, C-MAPSS run-to-failure degradation files).

---

### Step 3 — How Does Data Enter Our Platform?

* **Protocols:** Automotive/aerospace CAN bus frames (emulated via [`configs/can/anumaan_fadec.dbc`](file:///d:/Programming/PS054/configs/can/anumaan_fadec.dbc)) and MAVLink telemetry packets ([`configs/mavlink/anumaan.xml`](file:///d:/Programming/PS054/configs/mavlink/anumaan.xml)).
* **Ingestion Layer:** [`backend/runtime/hub.py`](file:///d:/Programming/PS054/backend/runtime/hub.py) (`RuntimeHub`) hosts concurrent `EngineRuntime` instances for each active engine.
* **Sampling Rate:** Nominal rate is strictly clocked at **20 Hz** ($50\text{ ms}$ interval) for scalar telemetry, while the edge DSP layer samples vibration at **10 kHz**.
* **Framing & Timestamping:** Each telemetry frame is encapsulated in an immutable data structure containing a high-precision monotonic timestamp ($t_{\text{mono}}$), flight phase enum, sequence number, and sensor validity bitmask.
* **Synchronization:** Frames are ordered and buffered in a ring-buffer ($N = 1,200$ frames = 60 seconds). Out-of-order frames are sorted; duplicate frames are dropped.

---

### Step 4 — What Happens to the Raw Data?

Before any ML model or state estimator touches the telemetry, raw signals pass through the **Sensor Sanity Validator** ([`backend/physics/sensor_validator.py`](file:///d:/Programming/PS054/backend/physics/sensor_validator.py)):
1. **Range Validation:** Hard physical bounds check ($0 < \text{RPM} < 7000$, $-40^\circ\text{C} < \text{CHT} < 300^\circ\text{C}$). Values exceeding physical bounds flag an electrical open/short.
2. **Rate-of-Change Gating ($dT/dt$):**
   * Cylinder heads have significant thermal mass. In physical operation, $|d\text{CHT}/dt| \le 1.5^\circ\text{C/s}$.
   * If a thermocouple reports $\Delta T = +30^\circ\text{C}$ in a single $50\text{ ms}$ timestep ($600^\circ\text{C/s}$), the system flags **Sensor Glitch / Electrical Noise** rather than an engine explosion.
3. **Statistical Drift Detection:** A rolling window CUSUM and EWMA filter tests for slow transducer calibration drift.
4. **Residual Shielding:** If a sensor is marked `INVALID`, its corresponding residual in $\mathbf{r}(t)$ is zero-shielded, preventing faulty instrumentation from corrupting the thermodynamic engine state or triggering false engine shutdowns.

---

### Step 5 — How Do We Estimate Engine State?

* **The State Vector $\mathbf{x}(t)$:**
  $$\mathbf{x} = \begin{bmatrix} T_{\text{cyl1}}, & T_{\text{cyl2}}, & T_{\text{cyl3}}, & T_{\text{cyl4}}, & T_{\text{oil}}, & P_{\text{oil}}, & \omega_{\text{crank}}, & \theta_{\text{scaling}} \end{bmatrix}^T$$
  Where $\theta_{\text{scaling}}$ represents unmeasured component degradation (e.g. radiator heat transfer fouling factor, piston ring blow-by coefficient).
* **The Estimator:** Implemented as a **Joint State/Parameter Unscented Kalman Filter (UKF)** in [`backend/twin/ukf.py`](file:///d:/Programming/PS054/backend/twin/ukf.py).
* **Why UKF?** Engine thermodynamics (convective heat transfer $\propto v^{0.8}$, radiative heat transfer $\propto T^4$, and compressible manifold gas dynamics) are highly non-linear. The UKF uses deterministic sigma-point sampling to capture posterior mean and covariance to 3rd-order Taylor accuracy without requiring Jacobian derivations.
* **Normalized Innovation Squared (NIS):** The filter continuously tracks innovation residuals $\mathbf{\nu}_k = \mathbf{y}_k - \hat{\mathbf{y}}_k$. Validated in experiment `E21` with a mean NIS of $0.9957$, confirming near-optimal Gaussian filter tuning.

---

### Step 6 — What is the Digital Twin Doing?

The Digital Twin is **not** a visual 3D asset. The Digital Twin is an in-memory cyber-physical mathematical construct ([`backend/twin/model.py`](file:///d:/Programming/PS054/backend/twin/model.py)) tracking six distinct temporal states:
1. **Physical State:** Thermodynamic mass and energy conservation across coolant, oil, and gas paths.
2. **Operational State:** Current flight regime (Idle, Takeoff, Climb, Cruise, Loiter, Descent) and mechanical load.
3. **Health State:** Continuous subsystem health scores ($H_{\text{combustion}}, H_{\text{thermal}}, H_{\text{lubrication}}, H_{\text{mechanical}}$) on a $0\text{--}100$ scale.
4. **Degradation State:** Cumulative physical wear parameters recovered via Sparse Identification of Nonlinear Dynamics (SINDy in [`backend/twin/degradation.py`](file:///d:/Programming/PS054/backend/twin/degradation.py)).
5. **Environmental State:** Dynamic atmospheric context (Altitude lapse rate, Mach number, ambient temperature, ram-air recovery factor).
6. **Predicted State:** Forward projection of physical state under hypothetical future flight waypoints.

---

### Step 7 — Where Does Physics Come In?

Physics forms the bedrock of the entire diagnostic pipeline through **Analytical Redundancy** ([`backend/physics/thermo_model.py`](file:///d:/Programming/PS054/backend/physics/thermo_model.py)):
* **Expected State Generation:** Given current operational inputs (Throttle TPS, Ambient Pressure $P_{\text{amb}}$, Ambient Temp $T_{\text{amb}}$, RPM), the thermodynamic model calculates the expected physical behavior:
  $$\dot{Q}_{\text{in}} = \dot{m}_{\text{fuel}} \cdot \text{LHV}_{\text{fuel}}$$
  $$P_{\text{indicated}} = \eta_{\text{thermal}} \cdot \dot{Q}_{\text{in}}$$
  $$T_{\text{CHT, expected}}(t) = T_{\text{amb}} + \Delta T_{\text{combustion}}(\text{RPM}, \text{MAP}) \cdot \left(1 - e^{-t/\tau_{\text{thermal}}}\right)$$
* **Residual Generation:** The model subtracts expected from measured telemetry:
  $$\mathbf{r}(t) = \mathbf{y}_{\text{measured}}(t) - \mathbf{y}_{\text{expected}}(t)$$
* **Why this is critical:** Under nominal conditions, $\mathbf{r}(t) \approx \mathbf{0}$ across all altitudes and flight speeds. When a fault begins (e.g. coolant radiator blockage), $\mathbf{r}_{\text{CHT}}$ diverges positively, while raw CHT might still be below the static alarm threshold!

---

### Step 8 — Where Does AI/ML Come In?

AI/ML operates on the extracted features and residuals, not on raw sensor noise:

```
[Raw Telemetry] ──▶ [Thermodynamic Model] ──▶ [Residual Vector r(t)]
                                                     │
                                                     ▼
                                      ┌───────────────────────────────┐
                                      │    STAGE 1: NOVELTY GATE      │
                                      │  FlyHash Sparse Coding (5ms)  │
                                      └──────────────┬────────────────┘
                                                     │ Flagged as Unseen
                                                     ▼
                                      ┌───────────────────────────────┐
                                      │   STAGE 2: FAULT DIAGNOSIS    │
                                      │  Bayesian Network / RF Ranker │
                                      └──────────────┬────────────────┘
                                                     │ Most Likely Mode
                                                     ▼
                                      ┌───────────────────────────────┐
                                      │   STAGE 3: CONFORMAL RUL      │
                                      │  Split-Conformal Extrapolator │
                                      └───────────────────────────────┘
```

1. **FlyHash Sparse Novelty Detector ([`backend/ml/flyhash_novelty.py`](file:///d:/Programming/PS054/backend/ml/flyhash_novelty.py)):** Biological fruit fly olfactory circuit mapping 26-dim residuals into 520 sparse Kenyon cells. Detects novel unmodelled phenomena in $<5\text{ ms}$ without training.
2. **Random Forest & Bayesian Diagnostic Ranker ([`backend/ml/fault_classifier.py`](file:///d:/Programming/PS054/backend/ml/fault_classifier.py), [`backend/diagnose/bn.py`](file:///d:/Programming/PS054/backend/diagnose/bn.py)):** Evaluates residual signature patterns against 20 failure modes, outputting a ranked list of fault hypotheses with posterior probabilities $P(\text{Fault}_i \mid \mathbf{r})$.
3. **SINDy Wear Extrapolator ([`backend/twin/degradation.py`](file:///d:/Programming/PS054/backend/twin/degradation.py)):** Discovers nonlinear ordinary differential equations governing component degradation from data.

---

### Step 9 — How is a Fault Detected? (Representative Trace)

**Concrete Example: Cylinder 3 Fuel Injector Partial Clogging (Fault Mode 2)**
1. **Physical Onset:** Particulate contamination reduces fuel metering orifice area in Cylinder 3 by $25\%$.
2. **Physics Divergence:**
   * Cylinder 3 runs lean ($\lambda_3 > 1.2$).
   * Local combustion temperature in Cylinder 3 spikes initially, followed by localized misfire under high power.
   * CHT 3 rises by $+24^\circ\text{C}$ relative to the other three cylinders. EGT 3 drops by $-45^\circ\text{C}$ due to unburnt fuel / lean flame extinction.
3. **Signal Processing & Feature Extraction:**
   * Crank-angle angular velocity observer ([`backend/ml/crank_diagnostics.py`](file:///d:/Programming/PS054/backend/ml/crank_diagnostics.py)) detects torque deficit at crank angle $\theta = 360^\circ$ (Cyl 3 expansion stroke).
   * Crankshaft rotational speed fluctuations increase half-order ($0.5\times$) vibration harmonic magnitude.
4. **Residual Generator:** $\mathbf{r}_{\text{CHT3}} = +22.8^\circ\text{C}$, $\mathbf{r}_{\text{EGT3}} = -43.5^\circ\text{C}$, $\mathbf{r}_{\text{ORDER\_0.5}} = +0.18\text{ g}$.
5. **Novelty Detector:** FlyHash Kenyon cell activation pattern shifts; novelty score jumps from $0.05 \to 0.78$ ($> 0.60$ threshold).
6. **Bayesian Classifier:** Evaluates likelihood. Negative correlation between CHT and EGT isolated to a single cylinder matches signature `INJ_CLOG_CYL3`. Posterior probability jumps to $0.94$.
7. **Health Index Update:** $H_{\text{combustion}}$ drops from $98 \to 64$. System alert transitions from `NOMINAL` to `WARNING`.

---

### Step 10 — How Does Prediction Differ from Detection?

To prevent conflation of terminology:
* **Anomaly Detection:** Answering *"Is the engine behaving abnormally right now?"* (Binary decision: Normal vs Abnormal via Mahalanobis distance or FlyHash).
* **Fault Diagnosis:** Answering *"What specific mechanical/electrical failure mode is causing this anomaly?"* (Classification across 20 MIL-STD failure modes with posterior confidence).
* **Fault Progression:** Modeling *"How will this specific damage accumulate over time?"* (Tracking physical wear rates $\dot{D} = f(\text{load}, T, \text{vibration})$).
* **Prognosis & RUL:** Answering *"How many operational flight hours remain before this component reaches catastrophic failure threshold?"* (Calculating Remaining Useful Life distribution $[t_{\text{lower}}, t_{\text{upper}}]$ via split-conformal prediction intervals).

---

### Step 11 — How Does Engine Health Affect Mission Reliability?

The critical operational bridge in Project ANUMAAN connects engine health to tactical UAV flight:

$$\text{Engine Degradation} \implies \text{Propulsive Thrust Loss} \implies \text{UAV Flight Envelope Shrinkage} \implies \text{Mission Risk}$$

* **Causal Link:** Implemented in [`backend/mission/reliability.py`](file:///d:/Programming/PS054/backend/mission/reliability.py).
* **Glide Range Shrinkage:** If an oil leak degrades lubrication health to $H_{\text{lub}} < 40$, the engine faces imminent seizure within 45 minutes. The UAV's maximum ceiling drops from $25,000\text{ ft}$ to $12,000\text{ ft}$, and its maximum airspeed decreases by $30\%$.
* **Monte Carlo Mission Simulation:** 1,000 simulated flight rollouts evaluate whether the degraded aircraft can clear terrain obstacles (e.g. Ladakh mountain passes) and reach the planned destination or if it must divert.
* **Prescriptive Pilot Advisory:**
  1. *Throttle Derate Ladder:* Automatically recommends reducing continuous throttle from $85\% \to 62\%$ to reduce thermal dissipation by $38\%$, extending RUL from $42\text{ minutes}$ to $2.8\text{ hours}$.
  2. *Divert Runway Calculation:* Computes probability of reaching nearest emergency recovery airstrip (e.g. Leh AGB) vs. mission abort.

---

### Step 12 — How is Everything Visualized?

The system delivers real-time situational awareness across three synchronized interfaces:
1. **Three.js WebGL 3D CAD Twin ([`web/site/`](file:///d:/Programming/PS054/web/site/)):**
   * High-performance browser client using Draco WebAssembly mesh decompression ($<2\text{ MB}$ asset footprint).
   * Live kinematics: crankshaft, connecting rods, and propeller rotate synchronously with live RPM.
   * Thermal Heatmaps: Fragment shaders map physical cylinder temperatures directly onto 3D CAD engine surfaces.
   * Cinematic Camera Director: Automatically animates camera focus to faulted sub-assemblies when an alert triggers.
2. **Master Blender 3D CAD Digital Twin ([`assets/blender/anumaan_master_twin.blend`](file:///d:/Programming/PS054/assets/blender/anumaan_master_twin.blend)):**
   * Full-fidelity 100% raytraced EEVEE CAD visualization for propulsion engineering diagnostics.
3. **Tactical Desktop GCS ([`apps/desktop_gcs/standalone_gui_app.py`](file:///d:/Programming/PS054/apps/desktop_gcs/standalone_gui_app.py)):**
   * Hardware-accelerated Pygame heads-up display displaying avionic primary flight instruments, rolling strip-charts, RUL confidence bars, and ISA-18.2 rationalized alarm annunciators.

---

### Step 13 — What Happens After the Mission?

* **Cryptographic Tamper-Evident Flight Logging ([`backend/security/merkle_log.py`](file:///d:/Programming/PS054/backend/security/merkle_log.py)):**
  * Every ingested telemetry frame, residual vector, and diagnostic decision is hashed into a SHA-256 Merkle tree block.
  * Ensures legal and military forensic immutability: zero possibility of retroactive log tampering following an incident.
* **Deterministic Flight Replay:**
  * Ground engineers can rewind and replay the exact flight second-by-second, pausing at anomaly onset to inspect sensor correlations and classifier decision trees.
* **Automated Maintenance Work Packages ([`backend/maintenance/work_package.py`](file:///d:/Programming/PS054/backend/maintenance/work_package.py)):**
  * Automatically maps diagnosed faults and consumed component life into standard **ATA Chapter 100 / 24 / 72** maintenance work orders, specifying required ground support equipment, replacement part numbers, and estimated maintenance technician hours.

---

## 5. ACTUAL RECONSTRUCTED RUNTIME ARCHITECTURE

The actual runtime system is structured into modular layers governed by Python's `asyncio` loop and FastAPI server endpoints:

```
                                  ┌──────────────────────────────────────────────────────────┐
                                  │                  CLIENT VISUALIZATION                    │
                                  │  Three.js WebGL Twin (`web/site/`)  ·  Desktop Pygame GCS│
                                  └────────────────────────────▲─────────────────────────────┘
                                                               │ WebSockets (20 Hz) / REST
                                  ┌────────────────────────────┴─────────────────────────────┐
                                  │               SERVER & API ROUTING LAYER                 │
                                  │  FastAPI Application (`backend/server/main.py`)          │
                                  │  Engine Endpoints (`backend/server/engine_api.py`)       │
                                  └────────────────────────────▲─────────────────────────────┘
                                                               │
                                  ┌────────────────────────────┴─────────────────────────────┐
                                  │                CONCURRENT RUNTIME HUB                    │
                                  │  `backend/runtime/hub.py` (Multi-Engine Manager)         │
                                  │                                                          │
                                  │  ┌────────────────────────────────────────────────────┐  │
                                  │  │             EngineRuntime [engine_id]              │  │
                                  │  │  1. Physical Levers (throttle, altitude, OAT)      │  │
                                  │  │  2. Virtual Plant (`backend/plant/virtual_engine`) │  │
                                  │  │  3. Sensor Sanity Gating (`backend/physics/`)      │  │
                                  │  │  4. Dynamic Thermofluid Twin (`backend/twin/`)     │  │
                                  │  │  5. Residual Detector Bank (`backend/detect/`)     │  │
                                  │  │  6. Bayesian Diagnosis (`backend/diagnose/`)       │  │
                                  │  │  7. Split-Conformal RUL (`backend/prognose/`)      │  │
                                  │  │  8. Mission Reliability (`backend/mission/`)       │  │
                                  │  └────────────────────────────────────────────────────┘  │
                                  └──────────────────────────────────────────────────────────┘
```

### 5.1 Component Responsibilities & Lifecycles
1. **`backend/runtime/hub.py::RuntimeHub`:**
   * *Role:* Central execution orchestrator. Instantiates and concurrently steps multiple `EngineRuntime` instances (e.g. 5 active UAVs in a squadron).
   * *Inputs:* Operating commands (throttle, altitude, airspeed, fault injections) via REST API.
   * *Outputs:* Master 20 Hz state payloads broadcasted to WebSocket consumers.
   * *Lifecycle:* Initialized on FastAPI startup lifespan; maintains persistent background asyncio loop.
2. **`backend/plant/virtual_engine.py::VirtualEngine`:**
   * *Role:* Decoupled plant model standing in for the physical engine. Emits simulated "raw" physical telemetry.
   * *Inputs:* Commanded levers ($T_{\text{throttle}}, \text{Alt}, \text{OAT}, \text{Speed}$) and physical wear accumulation.
   * *Outputs:* `Frame` containing measured temperatures, pressures, RPM, fuel flow, vibration, and a decoupled `TruthRecord` for automated test evaluation.
3. **`backend/twin/model.py::ThermofluidTwin`:**
   * *Role:* Core Digital Twin model. Calculates expected physics baseline and updates internal energy state.
   * *Inputs:* Ingested sensor frame + ambient flight context.
   * *Outputs:* Expected sensor state $\mathbf{y}_{\text{expected}}$, physical residual vector $\mathbf{r}(t)$, and subsystem health scores.
4. **`backend/detect/bank.py::DetectorBank`:**
   * *Role:* Runs multi-stage anomaly detection across physics residuals and vibration harmonics.
   * *Inputs:* Physical residual vector $\mathbf{r}(t)$.
   * *Outputs:* Anomaly flag, composite anomaly score, attribution vector.
5. **`backend/diagnose/bn.py::BayesianDiagnosticRanker`:**
   * *Role:* Multi-fault hypothesis ranker using probabilistic graphical models.
   * *Inputs:* Residual vector, anomaly trigger, and active sensor validity mask.
   * *Outputs:* Ranked fault hypotheses with calibrated posterior probabilities $P(\text{Fault}_i \mid \mathbf{r})$.
6. **`backend/prognose/rul.py::DualPathPrognosticEstimator`:**
   * *Role:* Computes Remaining Useful Life using physics-of-failure damage counting and SINDy degradation trend extrapolation.
   * *Inputs:* Health index trajectory, operational stress cycles, component wear history.
   * *Outputs:* Point RUL (hours) and exact finite-sample Split-Conformal prediction intervals $[t_{\min}, t_{\max}]$.
7. **`backend/mission/reliability.py::MissionReliabilityEngine`:**
   * *Role:* Projects remaining engine life onto planned UAV mission waypoints and flight profiles.
   * *Inputs:* Current engine health state, remaining mission duration, route terrain profile.
   * *Outputs:* Mission completion probability $P(\text{completion})$, glide reachability polygon, throttle derate advisory.

---

## 6. END-TO-END DATA FLOW PIPELINE TRACE

The following table traces a single telemetry data packet through every stage of the pipeline as verified against active repository code:

| Stage ID | Pipeline Stage | Primary File / Module | Input Data | Output Data | Core Algorithm | Target Latency | Storage / Buffering | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **01** | **Plant Simulation / Acquisition** | [`backend/plant/virtual_engine.py`](file:///d:/Programming/PS054/backend/plant/virtual_engine.py) | Operating levers ($\text{Alt}, \text{OAT}, \text{TPS}$) | Raw physical frame | Coupled thermal ODEs + kinematic combustion | $0.85\text{ ms}$ | Ephemeral memory | **REAL** |
| **02** | **Datalink & Jamming Emulation** | [`backend/link/link_emulator.py`](file:///d:/Programming/PS054/backend/link/link_emulator.py) | Raw physical frame | MAVLink serialized packet | RF loss model + Store-and-forward queue | $1.20\text{ ms}$ | FIFO Transit Queue | **REAL** |
| **03** | **Sensor Sanity & Shielding** | [`backend/physics/sensor_validator.py`](file:///d:/Programming/PS054/backend/physics/sensor_validator.py) | Ingested sensor values | Cleaned values + Validity bitmask | Rate-of-change filter ($dT/dt$) + Range gating | $0.15\text{ ms}$ | Frame buffer | **REAL** |
| **04** | **Thermodynamic Expected Baseline** | [`backend/physics/thermo_model.py`](file:///d:/Programming/PS054/backend/physics/thermo_model.py) | Flight context ($\text{Alt}, \text{OAT}, \text{RPM}, \text{MAP}$) | Expected state $\mathbf{y}_{\text{expected}}$ | First-principles lumped-capacitance thermodynamics | $0.45\text{ ms}$ | In-memory cache | **REAL** |
| **05** | **Residual Generation** | [`backend/twin/model.py`](file:///d:/Programming/PS054/backend/twin/model.py) | Measured vs Expected | Residual vector $\mathbf{r}(t)$ | Vectorized difference + Covariance normalization | $0.05\text{ ms}$ | Circular ring buffer | **REAL** |
| **06** | **Edge Novelty Gating** | [`backend/ml/flyhash_novelty.py`](file:///d:/Programming/PS054/backend/ml/flyhash_novelty.py) | 26-dim residuals + order features | Novelty score ($0\text{--}1$) | Sparse random projection + Winner-Take-All | $0.22\text{ ms}$ | Bloom filter bitmask | **REAL** |
| **07** | **State Estimation (UKF)** | [`backend/twin/ukf.py`](file:///d:/Programming/PS054/backend/twin/ukf.py) | Measured sensors + Residuals | Filtered state $\hat{\mathbf{x}} + \mathbf{P}$ | Joint State/Parameter Unscented Kalman Filter | $1.80\text{ ms}$ | State covariance $\mathbf{P}$ | **REAL** |
| **08** | **Bayesian Fault Diagnosis** | [`backend/diagnose/bn.py`](file:///d:/Programming/PS054/backend/diagnose/bn.py) | Residual vector $\mathbf{r}(t)$ | Ranked fault hypotheses ($P_i$) | Exact Bayesian inference over DAG | $0.65\text{ ms}$ | Diagnostic ledger | **REAL** |
| **09** | **Conformal RUL Prognostics** | [`backend/prognose/rul.py`](file:///d:/Programming/PS054/backend/prognose/rul.py) | Health index history | RUL hours + $[t_{\min}, t_{\max}]$ | Rainflow cycle counting + Split-Conformal prediction | $2.10\text{ ms}$ | Prognostic record | **REAL** |
| **10** | **Mission Reliability Assessment** | [`backend/mission/reliability.py`](file:///d:/Programming/PS054/backend/mission/reliability.py) | RUL distribution + Waypoints | $P(\text{completion}) + \text{Advisory}$ | Monte Carlo flight risk projection | $3.50\text{ ms}$ | Mission state store | **REAL** |
| **11** | **Forensic Cryptographic Logging** | [`backend/security/merkle_log.py`](file:///d:/Programming/PS054/backend/security/merkle_log.py) | State frame + Decision output | Merkle leaf hash + Root | SHA-256 Chained Merkle Tree | $0.40\text{ ms}$ | Local audit file | **REAL** |
| **12** | **WebSocket Telemetry Broadcast** | [`backend/server/engine_api.py`](file:///d:/Programming/PS054/backend/server/engine_api.py) | Fused telemetry packet | JSON binary WebSocket frame | Asyncio WebSocket multiplexer | $0.30\text{ ms}$ | Network buffer | **REAL** |
| **13** | **Client Visualization Rendering** | [`web/site/`](file:///d:/Programming/PS054/web/site/) | WebSocket JSON frame | Interactive 3D WebGL render | Three.js WebGL / GLSL shaders / WASM Draco | $16.6\text{ ms}$ ($60\text{ FPS}$) | GPU Framebuffer | **REAL** |

---

## 7. USER PERSONAS & OPERATIONAL WORKFLOWS

### 7.1 UAV Pilot / Operator Workflow
* **Objective:** Ensure safe execution of active tactical reconnaissance sorties and prevent catastrophic aircraft loss.
* **Console View:** Tactical Heads-Up Display (Pygame Desktop GCS or Web HUD).
* **Operational Flow:**
  1. *Pre-Flight Verification:* Observes engine start and warm-up run-up. Confirms all 5 subsystem health scores are $\ge 95$. Gating check verifies sensor noise variance and dual FADEC lane parity.
  2. *In-Flight Ingress:* Monitors scalar telemetry and mission completion probability $P(\text{completion})$.
  3. *Alarm Event:* Ingests early warning alert (e.g. `WARNING: Coolant Radiator Debris Ingestion - 28% Margin Loss`).
  4. *Tactical Decision Support:* Reviews prescriptive advisory. System presents two clear options: (A) Maintain current airspeed and face forced abort in 35 minutes; (B) Adopt recommended throttle derate from $80\% \to 64\%$, climbing to $18,000\text{ ft}$ for colder ambient airflow, extending mission endurance by 4.2 hours and completing target surveillance.
  5. *Safe Recovery:* Operator confirms throttle adjustment; engine temperatures stabilize below critical redline; aircraft completes mission and returns to base.

### 7.2 Propulsion & Reliability Engineer Workflow
* **Objective:** Deep thermodynamic state estimation, sensor anomaly isolation, and model calibration.
* **Console View:** Master Blender CAD Twin + Engineering Analytics Console.
* **Operational Flow:**
  1. *Physical Diagnostic Drilldown:* Selects active engine from fleet list. Inspects 13-channel residual vector $\mathbf{r}(t)$ alongside raw measurements.
  2. *Sensor-vs-Engine Discrimination:* Checks Sensor Sanity Validator logs to determine whether an indicated CHT spike is a real cylinder overheating event or a loose thermocouple ground wire ($dT/dt > 10^\circ\text{C/s}$).
  3. *Degradation Trend Analysis:* Inspects SINDy wear coefficients $\theta_{\text{wear}}$ to evaluate inter-cylinder blow-by and oil cooler fouling rates across sorties.
  4. *Model Recalibration:* Triggers ground-only batch recalibration of thermodynamic baseline maps against newly logged nominal flight data.

### 7.3 Base Maintenance Technician Workflow
* **Objective:** Condition-Based Maintenance overhaul and rapid turnaround between sorties.
* **Console View:** Maintenance Work Order Portal.
* **Operational Flow:**
  1. *Post-Flight Ingestion:* Ingests Merkle forensic flight log from landed UAV flight data recorder.
  2. *Cryptographic Verification:* Validates SHA-256 Merkle root to confirm zero log corruption or missing packets.
  3. *Automated Work Package Review:* Reads generated ATA 100 maintenance work order (e.g. `ATA 73-10: Cylinder 3 Injector Replacement Required`).
  4. *Part Triage & Overhaul:* Reviews historical cumulative fatigue damage (Rainflow stress cycles counted on crankshaft). Determines if scheduled 100-hour major overhaul can be deferred based on low cumulative thermal stress.
  5. *Sign-Off & Reset:* Logs maintenance action; resets FlyHash calibration buffer for the replaced injector.
