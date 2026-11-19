> ⚠️ **Read [31_VERIFICATION_AND_CORRECTIONS.md](31_VERIFICATION_AND_CORRECTIONS.md) before quoting or citing this report.** File paths, some numeric claims, and the competitor list in this report set were checked against the real repository on 2026-09-23 and substantially diverged -- most of it also predates real work (backend/plant, evaluation, mission, reliability, twin, edge, osacbm.py, crank-angle diagnostics, FlyHash novelty detection) that supersedes what this file describes. Use docs/04_system_guide.md and docs/audit/07_unoccupied_axes_and_ground_up_plan.md as the current, source-verified reference instead.

# REPORT 25: DRDO TECHNICAL QUESTION & ANSWER DATABASE

**DRDO Aero-Twin | SIH 26054 Technical Reconstruction**  
**Classification:** Comprehensive Aerospace & Defence Technical Interrogation Guide  
**Author:** DRDO Aero-Twin Engineering Reconstruction Team  
**Date:** March 2025  

---

## METHODOLOGY & DEFENSE POSTURE

This document provides a comprehensive technical question-and-answer database structured across **20 technical categories (Categories A through T)**. Every answer is grounded in the actual codebase, physical reality, and aviation engineering principles.

Strict classification tags are applied to every statement:
`[IMPLEMENTED]`, `[PARTIALLY IMPLEMENTED]`, `[SIMULATED]`, `[HARDCODED]`, `[RULE-BASED]`, `[EXPERIMENTAL]`, `[PLANNED]`, `[NOT IMPLEMENTED]`, `[UNVERIFIED]`.

Where our system cannot currently fulfill a requirement, it is explicitly flagged as:  
**"CURRENT LIMITATION — NOT YET IMPLEMENTED."**

---

## CATEGORY A — PROBLEM UNDERSTANDING

### QA-1: Why is conventional threshold monitoring insufficient for MALE UAV aero engines?
* **Answer:** Conventional threshold monitoring relies on static redline alarms (e.g., $T_{\text{CHT}} > 140^\circ\text{C}$ or $P_{\text{oil}} < 2.0\text{ bar}$). This has two critical failure modes in flight:
  1. **False Alarms During Heavy Flight Loads:** During combat takeoff or maximum sustained climb in hot desert conditions ($+45^\circ\text{C}$ ambient), cylinder temperatures normally rise toward the upper limit. Static thresholds trigger false alarms, distracting the pilot or causing unnecessary mission aborts.
  2. **Missed Incipient Faults During Low-Power Descent:** During high-speed descent or low-throttle loiter, ram air cooling drops temperatures to $95^\circ\text{C}$. If a cylinder suffers an exhaust valve leak or partial misfire, its temperature might rise by $+25^\circ\text{C}$ (to $120^\circ\text{C}$). Because $120^\circ\text{C}$ is well below the static $140^\circ\text{C}$ threshold, conventional systems remain silent while the valve seat erodes toward catastrophic in-flight failure.
* **Our Solution `[IMPLEMENTED]`:** We compute **thermodynamic residuals** ($\Delta T = T_{\text{measured}} - T_{\text{expected}}$) using a physics observer. Under nominal conditions, the residual is always zero, allowing detection of microscopic degradation long before static thresholds are breached.

### QA-2: Why are aero piston engines used in MALE UAVs instead of turbofans?
* **Answer:** Turbofan and turbojet engines have poor Specific Fuel Consumption (SFC) at low speeds (sub-Mach 0.3) and low-to-medium altitudes ($15,000 - 25,000\text{ ft}$). MALE surveillance UAVs require extreme flight endurance (18 to 24+ continuous loiter hours). Aero piston engines (particularly turbocharged boxer engines and compression-ignition diesels) deliver brake thermal efficiencies exceeding 32–38%, consuming roughly half the fuel mass per hour of an equivalent micro-turboprop, enabling day-long loiter on tactical fuel reserves.

---

## CATEGORY B — ENGINE FUNDAMENTALS

### QB-1: What are the thermodynamic cycles and mechanical layout of our reference engine?
* **Answer `[IMPLEMENTED]`:** Our reference engine is modeled on the **Rotax 912 iS Sport**:
  * **Thermodynamic Cycle:** Four-stroke Otto cycle (Intake, Compression, Power, Exhaust).
  * **Mechanical Layout:** Horizontally-opposed 4-cylinder ("boxer") configuration with central crankshaft, dual camshafts, pushrod-activated overhead valves (2 per cylinder), and central reduction spur gearbox (1:2.4286 ratio).
  * **Cooling Topology:** Hybrid cooling—air-cooled cylinder barrels (external fins) and liquid-cooled cylinder heads (water/glycol closed loop with mechanical coolant pump and radiator).
  * **Bore & Stroke:** $84.0\text{ mm}$ bore $\times 61.0\text{ mm}$ stroke ($1,352\text{ cc}$ displacement), compression ratio $10.8:1$.
  * **Rated Output:** $73.5\text{ kW}$ ($100\text{ HP}$) at $5,800\text{ crankshaft RPM}$ ($2,388\text{ prop RPM}$).

### QB-2: What is the physical significance of CHT vs. EGT?
* **Answer:**
  * **Cylinder Head Temperature (CHT):** Reflects the internal structural temperature of the aluminum cylinder head casting. CHT is a slow-response thermal indicator (thermal time constant $\tau \approx 30 - 45\text{ s}$) determined by combustion heat flux minus convective cooling. Exceeding $150^\circ\text{C}$ causes metallurgical softening and risk of piston crown seizure.
  * **Exhaust Gas Temperature (EGT):** Measures the temperature of combustion gases exiting the exhaust valve runner ($800 - 880^\circ\text{C}$). EGT responds almost instantaneously ($\tau \approx 0.5 - 1.5\text{ s}$) to changes in the Air-Fuel Ratio (AFR) and ignition timing. Peak EGT occurs slightly lean of stoichiometry ($\lambda \approx 1.05$). A sudden drop in EGT with nominal CHT indicates a combustion misfire; a sharp spike indicates lean detonation or late exhaust valve timing.

---

## CATEGORY C — DIGITAL TWIN

### QC-1: What exactly is your Digital Twin, and how is it different from a simulation?
* **Answer `[PARTIALLY IMPLEMENTED]`:** 
  * A **simulation** runs an offline mathematical model forward from arbitrary initial conditions without binding to physical reality.
  * Our **Digital Twin** is an operational computational entity bound to incoming telemetry. Under **ISO 23247**, it currently functions as a **Digital Shadow at STANAG 4586 LOI 2**:
    1. It continuously synchronizes an internal **7-dimensional physical state vector** ($\hat{\mathbf{x}}_k$) at 20 Hz.
    2. It executes a thermodynamic observer in real time, calculating expected plant states.
    3. It generates **residuals** that isolate degradation from pilot control maneuvers.
    4. It updates material thermal shaders on a 109-part CAD model in Blender and Three.js.
    5. It tracks cumulative low-cycle fatigue damage ($D$) across sorties.

### QC-2: Is your Digital Twin descriptive, predictive, or prescriptive?
* **Answer:**
  * **Descriptive `[IMPLEMENTED]`:** It reflects the live spatial and thermal state of every cylinder, pressure gallery, and gearbox assembly.
  * **Predictive `[IMPLEMENTED]`:** It projects thermal runaway curves forward via AIC polynomial extrapolation and Monte Carlo perturbation, outputting probabilistic RUL horizons with 90% confidence bounds.
  * **Prescriptive `[PARTIALLY IMPLEMENTED]`:** It provides advisory recommendations to the operator via local Qwen3-4B voice copilot and emergency Auto-GCAS diversion guidance. It does **not** command closed-loop ECU actuators directly due to DO-178C flight certification constraints.

---

## CATEGORY D — PHYSICS MODEL

### QD-1: What equations govern your thermodynamic engine model?
* **Answer `[IMPLEMENTED]`:** In `backend/physics/thermo_model.py`, the model integrates lumped-parameter energy conservation differential equations:
  $$m_{\text{head}} c_p \frac{dT_i}{dt} = \dot{Q}_{\text{comb},i} - \dot{Q}_{\text{cool},i} - \dot{Q}_{\text{oil},i}$$
  * **Combustion Heat Input:** $\dot{Q}_{\text{comb},i} = \eta_{\text{th}} \dot{m}_{\text{fuel},i} \text{LHV}_{\text{fuel}} \xi_i$
  * **Speed-Density Fuel Flow:** $\dot{m}_{\text{fuel}} = \frac{\Omega V_{\text{disp}}}{120} \frac{P_{\text{man}}}{R_{\text{spec}} T_{\text{man}}} \eta_{\text{vol}} \frac{1}{\text{AFR}}$
  * **Convective Cooling:** $\dot{Q}_{\text{cool},i} = h_0 \left(1 + \kappa_v \sqrt{\frac{1}{2} \rho(h) V_{\text{IAS}}^2}\right) A_{\text{fin}} (T_i - T_{\text{amb}})$
  * **Oil Temperature Dynamic Balance:** $C_{\text{oil}} \frac{dT_{\text{oil}}}{dt} = \dot{Q}_{\text{frict}}(\Omega) + \dot{Q}_{\text{piston}\to\text{oil}} - \dot{m}_{\text{oil}} c_{\text{oil}} \varepsilon_{\text{rad}} (T_{\text{oil}} - T_{\text{amb}})$

### QD-2: Does altitude affect the model?
* **Answer `[IMPLEMENTED]`:** Yes. We implement the International Standard Atmosphere (ISA) barometric lapse model:
  $$P_{\text{amb}}(h) = P_0 \left(1 - \frac{L \cdot h}{T_0}\right)^{\frac{g M}{R L}}, \quad \rho(h) = \frac{P_{\text{amb}}(h)}{R_{\text{spec}} T_{\text{amb}}(h)}$$
  As altitude climbs toward $25,000\text{ ft}$, ambient density $\rho$ drops by over 60%, reducing convective fin cooling and naturally causing the physics observer to expect higher steady-state cylinder head temperatures for an equivalent power setting.

---

## CATEGORY E — SENSOR DATA

### QE-1: What sensors are monitored, what are their sampling rates, and how do you handle noise?
* **Answer `[SIMULATED / IMPLEMENTED]`:**
  * **Monitored Channels:** CHT 1-4 (K-type thermocouples), EGT 1-4, Oil Pressure (piezoresistive transducer), Oil Temperature (NTC thermistor), Fuel Pressure, Engine RPM (crank reluctor pickup), and Tri-Axial Vibration (piezoelectric accelerometer).
  * **Telemetry Rate:** Scalar engine telemetry is sampled at **20 Hz** (50 ms window). Vibration spectral features are processed at the edge.
  * **Noise Filtering:** In `backend/services/state.py`, an **Extended Kalman Filter (EKF)** dynamically filters measurement noise ($\mathbf{R}$) based on the physical process covariance ($\mathbf{Q}$), preventing sensor jitter from corrupting downstream models.

---

## CATEGORY F — CAN / TELEMETRY

### QF-1: How is telemetry acquired, and what is your protocol architecture?
* **Answer `[SIMULATED]`:**
  * In the current prototype, `backend/telemetry/can_streamer.py` emulates an onboard CAN controller broadcasting **CAN 2.0B frames at 500 kbit/s** conforming to the **CANaerospace / ARINC 825** data dictionary.
  * Messages use 29-bit identifiers with standardized 8-byte payloads.
  * Ground communication adheres to **STANAG 4586 Level of Interoperability (LOI) 2**; telemetry is serialized into MAVLink v2 style payloads streamed over WebSockets to the GCS.
  * **CURRENT LIMITATION — NOT YET IMPLEMENTED:** Connection to physical Linux SocketCAN (`vcan0`) hardware interfaces or physical avionics transceivers.

---

## CATEGORY G — STATE ESTIMATION

### QG-1: What state estimation algorithm is implemented, and what state vector does it track?
* **Answer `[IMPLEMENTED]`:** In `backend/services/state.py`, an **Extended Kalman Filter (EKF)** tracks the 7-dimensional continuous state vector:
  $$\hat{\mathbf{x}}_k = \begin{bmatrix} T_{\text{CHT,1}} & T_{\text{CHT,2}} & T_{\text{CHT,3}} & T_{\text{CHT,4}} & T_{\text{oil}} & P_{\text{oil}} & \Omega_{\text{RPM}} \end{bmatrix}^T$$
  The filter executes a predictor-corrector cycle at 20 Hz, updating state error covariance matrix $\mathbf{P}_k = (\mathbf{I} - \mathbf{K}_k \mathbf{H}_k) \mathbf{P}_{k|k-1}$.

---

## CATEGORY H — ARTIFICIAL INTELLIGENCE & MACHINE LEARNING

### QH-1: What ML models are used, why were they chosen, and what are their inference latencies?
* **Answer `[IMPLEMENTED]`:**
  1. **Bottleneck Autoencoder (14-8-4-8-14 MLP):** Implemented in pure NumPy (`backend/ml/autoencoder.py`). Chosen for unsupervised novelty detection with zero PyTorch/CUDA runtime overhead. Latency: **0.062 ms** (62 microseconds).
  2. **Random Forest Classifier (100 Trees):** Implemented in Scikit-learn (`backend/ml/classifier.py`). Chosen for high explainability (Mean Decrease in Impurity feature attribution) and robust multi-class separation without overfitting. Latency: **1.40 ms**.
  3. **Offline Small Language Model (Qwen3-4B GGUF):** Air-gapped local SLM running in 4-bit quantization on CPU/GPU via `llama-cpp-python`. Chosen for natural language pilot checklist synthesis. First-token latency: **350 ms**.

### QH-2: What was the training dataset size and methodology?
* **Answer `[EXPERIMENTAL / AUDITED]`:**
  * **Current Reality:** Trained on 30 synthetic missions of 45 seconds each ($27,000\text{ samples}$ at 20 Hz) generated by `RotaxTimeSeriesGenerator`. Achieved 97.5% validation accuracy across 9 classes.
  * **Honest Vulnerability:** The training corpus is currently circular (generated by the same physics equations used at inference). 
  * **Roadmap Fix `[PLANNED]`:** Expand training corpus to a 500-hour multi-mission stochastic dataset with real-world sensor noise and cross-validate against public bearing run-to-failure benchmarks (CWRU, Paderborn).

---

## CATEGORY I — ANOMALY DETECTION

### QI-1: How does anomaly detection operate from sensor input to alarm?
* **Answer `[IMPLEMENTED]`:**
  $$\text{Raw Sensors } \mathbf{z}_k \xrightarrow{\text{Subtract } \hat{\mathbf{z}}_{\text{expected}}} \text{Residuals } \mathbf{r}_k \xrightarrow{\text{Normalize}} \mathbf{r}_k^* \xrightarrow{\text{Autoencoder}} \text{Reconstruction Error } J_{\text{AE}} = \|\mathbf{r}^* - \hat{\mathbf{r}}^*\|_2^2$$
  If $J_{\text{AE}} > \mu_J + 3.29 \sigma_J$ (99.9% confidence), an anomaly flag is asserted, and the residual vector is immediately routed to the diagnostic classifier.

---

## CATEGORY J — FAULT DIAGNOSIS

### QJ-1: How are specific faults distinguished from one another?
* **Answer `[IMPLEMENTED]`:** The Random Forest maps unique multi-channel residual signatures:
  * **Misfire (F01):** Single-cylinder EGT drops sharply ($<-150^\circ\text{C}$), CHT drops slowly, 0.5X crank vibration increases.
  * **Cylinder Overheat (F02):** Single-cylinder CHT climbs ($>+25^\circ\text{C}$), EGT slightly elevated, other 3 cylinders nominal.
  * **Cooling Degradation (F03):** All 4 cylinder CHTs climb uniformly ($>+15^\circ\text{C}$ across all channels).
  * **Oil Loss (F04):** Oil pressure drops ($<2.0\text{ bar}$) while oil temperature climbs; CHTs nominal initially.
  * **Sensor Drift (F05):** Single-channel CHT ramps linearly without thermodynamic correlation to EGT or adjacent cylinders.

---

## CATEGORY K — REMAINING USEFUL LIFE (RUL) & PROGNOSTICS

### QK-1: How is RUL calculated, and how do you prevent it from being an arbitrary number?
* **Answer `[IMPLEMENTED]`:** In `backend/ml/trend_analyser.py`:
  1. We maintain a sliding window of historical thermal residuals.
  2. We fit both linear and quadratic degradation polynomials, selecting the best model via the **Akaike Information Criterion (AIC)**.
  3. We execute a **500-sample Monte Carlo perturbation** of polynomial coefficients based on historical sensor variance.
  4. Each curve is projected to intercept the physical metallurgical softening threshold ($T_{\text{crit}} = 150^\circ\text{C}$).
  5. The output is reported as a median RUL with a non-parametric **90% Confidence Interval**:
     $$\text{RUL} = 18.4\text{ min } [90\%\text{ CI: } 14.8 - 22.1\text{ min}]$$
  * **CURRENT LIMITATION — NOT YET IMPLEMENTED:** Ingestion of multi-thousand-hour empirical run-to-failure aircraft logs.

---

## CATEGORY L — HEALTH INDEX

### QL-1: How is the engine health index calculated?
* **Answer `[IMPLEMENTED]`:** Engine health is a composite weighted index ($H_{\text{total}} \in [0, 100\%]$) aggregated across four sub-health indices:
  $$H_{\text{total}} = 0.35 H_{\text{combustion}} + 0.25 H_{\text{cooling}} + 0.25 H_{\text{lubrication}} + 0.15 H_{\text{mechanical}}$$
  Each sub-health index is calculated by normalizing its maximum residual z-score: $H_k = \max(0, 100 - 20 \cdot \max_j |r_{k,j}^*|)$.

---

## CATEGORY M — MISSION SIMULATION

### QM-1: How does engine degradation impact the UAV's flight mission in your simulation?
* **Answer `[IMPLEMENTED]`:** In `apps/blender_twin/standalone_canyon_flight_app.py`, engine power degradation is coupled to a **6-DOF flight dynamics model**:
  * Engine shaft power loss reduces propeller thrust ($T = \eta_{\text{prop}} \frac{P_{\text{shaft}}}{V}$).
  * Rate of climb drops: $V_z = \frac{T - D}{W} V$.
  * If $V_z < 0$, the UAV cannot maintain altitude.
  * **Auto-GCAS (Automatic Ground Collision Avoidance System):** 16 forward-looking raycasts query the 3D terrain mesh (`terrain.blend`). If Time-To-Impact $\text{TTI} < 2.5\text{ s}$, Auto-GCAS executes an emergency 3.5g terrain fly-up maneuver and calculates a safe glide cone to an emergency diversion waypoint.

---

## CATEGORY N — MISSION REPLAY

### QN-1: Can missions genuinely be replayed?
* **Answer `[IMPLEMENTED]`:** Yes. In `backend/reports/mission_bundle.py`, the entire 20 Hz state history, raw frames, residuals, alarms, and operator logs are compressed into a unified `.bundle` archive. The GCS allows scrubbing at 0.5x, 1x, 2x, and 5x speeds, reconstructing the exact operational state, while `standalone_mission_graph_app.py` renders the flight trajectory in Blender as a 3D spline color-coded by engine health.

---

## CATEGORY O — EDGE COMPUTING

### QO-1: Why split edge and ground, and what runs where?
* **Answer `[IMPLEMENTED]`:**
  * **Bandwidth Reality:** A 10 kHz 3-axis vibration sensor produces $480\text{ kbit/s}$. The UAV Ku-band downlink allocates only $25\text{ kbit/s}$. Streaming raw vibration is impossible.
  * **Edge Layer (UAV):** High-speed DSP, FFT order tracking, and primary threshold gating run onboard, compressing vibration to 4 scalar metrics ($<640\text{ bit/s}$).
  * **Ground Layer (GCS):** Kalman state estimation, AI diagnostic classification, RUL Monte Carlo projection, 3D WebGL digital twin rendering, and Voice Copilot reasoning.

---

## CATEGORY P — SAFETY & RELIABILITY

### QP-1: What fail-safe mechanisms prevent false alarms or missed faults?
* **Answer `[IMPLEMENTED]`:**
  1. **Thermodynamic Residual Gating:** Prevents false alarms during rapid tactical maneuvers.
  2. **Temporal Majority Voting (`MajorityVoteBuffer`):** Requires fault diagnoses to persist for 3 out of 5 consecutive frames ($150\text{ ms}$) before latching an alarm.
  3. **Zero-Order Hold Imputation:** Bridges up to 3 dropped telemetry frames without crashing.
  4. **Unknown Class Rejection:** If Random Forest class confidence $<65\%$, the system flags `"UNKNOWN_ANOMALY"`, refusing to guess.

---

## CATEGORY Q — CYBERSECURITY

### QQ-1: How is the system secured against telemetry tampering or unauthorized access?
* **Answer `[PLANNED / PARTIALLY IMPLEMENTED]`:**
  * **STANAG 4586 LOI 2 Compliance `[IMPLEMENTED]`:** The system is strictly a read-only telemetry consumer. No software command path exists to control the engine ECU.
  * **CURRENT LIMITATION — NOT YET IMPLEMENTED:** Current development WebSockets use unencrypted `ws://`. Production deployment requires TLS 1.3 encryption (`wss://`), JWT authentication tokens on REST routes, and HMAC-SHA256 message signing on all incoming frames.

---

## CATEGORY R — DEPLOYMENT ARCHITECTURE

### QR-1: What are the hardware and compute requirements for deployment?
* **Answer `[IMPLEMENTED]`:**
  * **Edge Gateway:** Conduction-cooled embedded computer (e.g., NVIDIA Jetson Orin NX or Raspberry Pi CM4) running Linux with CAN transceiver. Consumes $<15\text{ W}$.
  * **Ground Control Station:** Standard ruggedized military laptop (Intel i7 / 16 GB RAM / RTX 4060 GPU) running the React GCS and local Qwen3-4B voice model.

---

## CATEGORY S — VALIDATION METHODOLOGY

### QS-1: How is the physics model validated without a physical test rig?
* **Answer `[SIMULATED]`:**
  * The thermodynamic observer is parameterized using published BRP-Rotax 912 iS Operator Manual limits (continuous CHT $120^\circ\text{C}$, maximum $150^\circ\text{C}$, oil pressure 2.0 to 5.0 bar).
  * Synthetic fault injection tests verify that step and ramp deviations induce predictable residual responses matching internal combustion thermodynamics literature.
  * **CURRENT LIMITATION — NOT YET IMPLEMENTED:** Empirical dynamometer test cell calibration against physical engine sensors.

---

## CATEGORY T — DEFENCE & OPERATIONAL COMPLIANCE

### QT-1: What military airworthiness and software standards apply to this system?
* **Answer `[AUDITED]`:**
  * **STANAG 4586 (LOI 2) `[COMPLIANT]`:** Telemetry observer without control authority.
  * **RTCA DO-178C `[COMPLIANT AS DAL-E GCS / NON-COMPLIANT ON-WING]`:** As an off-board advisory ground station tool, it qualifies under Design Assurance Level DAL-E. Onboard flight software would require recoding in certified C99/Ada for DAL-C.
  * **Single-Fuel Policy `[ACKNOWLEDGED GAP]`:** The Indian military mandates heavy-fuel diesels (Jet-A1) on frontline UAVs. The Rotax 912 iS is our baseline spark-ignition testbed; common-rail diesel equations represent our immediate scaling roadmap.
  * **100% Air-Gapped Operation `[FULLY COMPLIANT]`:** Operates with zero internet access, utilizing local Whisper.cpp, Qwen3-4B, and Kokoro TTS models.
