# REPORT 29: DEMONSTRATION METHODOLOGY & EXPERIMENTAL PROTOCOL

**DRDO Aero-Twin | SIH 26054 Technical Reconstruction**  
**Classification:** Live Demonstration Script, Scientific Experiment Walkthrough & Evaluation Guide  
**Author:** DRDO Aero-Twin Engineering Reconstruction Team  
**Date:** March 2025  

---

## 1. DEMONSTRATION PHILOSOPHY: AN ENGINEERING EXPERIMENT, NOT A UI TOUR

A critical mistake in hackathon demonstrations is presenting the software as a passive "UI tour" (e.g., *"Here is our dashboard, here is our 3D model, here are some buttons"*). DRDO evaluators and senior aerospace scientists are not impressed by generic web pages.

To win SIH 26054, **our demonstration must be conducted as a controlled, live scientific engineering experiment**:
1. We set up physical boundary conditions (altitude, temperature, throttle).
2. We establish a baseline nominal state, proving that the thermodynamic physics observer eliminates false alarms.
3. We inject a realistic, progressive mechanical fault (e.g., Cylinder #2 exhaust valve leak and thermal runaway).
4. We trace the mathematical reaction step-by-step through the residual layer, the unsupervised autoencoder, the Random Forest classifier, and the Monte Carlo RUL engine.
5. We demonstrate the mission-level impact in our 6-DOF canyon flight simulator, showing Auto-GCAS execute an emergency terrain avoidance maneuver when engine power degrades.
6. We conclude with our offline AI voice copilot giving tactical recommendations and generating an airworthiness certificate.

---

## 2. THE FOURTEEN-STEP LIVE EXPERIMENTAL PROTOCOL

```
THE 14-STEP SCIENTIFIC DEMONSTRATION FLOW
[Step 01] Cold-Start Initialization & Clean Air-Gapped Verification
    ↓
[Step 02] Mission Profile & Environmental Setup (Hot & High Scenario)
    ↓
[Step 03] Telemetry Stream Launch (20 Hz Synthetic CAN Bus)
    ↓
[Step 04] EKF State Estimation & Digital Twin Synchronization
    ↓
[Step 05] Tactical Maneuver Stress Test (Proving False Alarm Immunity)
    ↓
[Step 06] Controlled Fault Injection: Cylinder #2 Thermal Runaway
    ↓
[Step 07] Thermodynamic Residual Divergence & Z-Score Escalation
    ↓
[Step 08] Unsupervised Anomaly Detection (NumPy Autoencoder in 62 μs)
    ↓
[Step 09] Supervised Fault Diagnosis & Explainability (Random Forest)
    ↓
[Step 10] Probabilistic RUL Extrapolation (AIC Fit + 500 Monte Carlo)
    ↓
[Step 11] Mission Reliability Impact & 6-DOF Auto-GCAS Canyon Escape
    ↓
[Step 12] Air-Gapped AI Voice Copilot Tactical Consultation
    ↓
[Step 13] Post-Flight Telemetry Bundling & PDF Airworthiness Audit
    ↓
[Step 14] 3D Spatial Trajectory Replay in Blender
```

---

### STEP 01: COLD-START INITIALIZATION & AIR-GAPPED VERIFICATION
* **Input:** System boot on a standalone laptop. Disconnect Wi-Fi and Ethernet in front of the judges.
* **Expected Behavior:** Backend server boots locally on port 8000; React frontend connects to `ws://localhost:8000/api/v1/telemetry/stream`.
* **Actual Implementation:** FastAPI `lifespan` handler initializes SQLite database, loads ML model weights into RAM, and starts the 20 Hz state thread.
* **Expected Output:** Terminal shows: `[INFO] Aero-Twin Engine State Service started at 20 Hz. Models loaded: Autoencoder, RandomForest, TrendAnalyser. Whisper/Qwen offline AI initialized.`
* **What the Judge Sees:** A clean, military-dark tactical ground station showing green connection status with zero internet access.
* **Technical Concept Demonstrated:** **Military Operational Security & Air-Gapped Independence.** Proves that the platform has zero cloud API dependencies.
* **Code Producing It:** `backend/main.py`, `backend/services/state.py`.

---

### STEP 02: MISSION PROFILE & ENVIRONMENTAL SETUP (HOT & HIGH SCENARIO)
* **Input:** Set mission profile parameters via UI slider: Altitude = $18,000\text{ ft}$, Ambient Temperature = $+38^\circ\text{C}$ (tactical desert envelope), Airspeed = $105\text{ kts}$.
* **Expected Behavior:** Atmospheric density $\rho$ drops to $0.62\text{ kg/m}^3$; ambient pressure drops to $50.6\text{ kPa}$.
* **Actual Implementation:** `RotaxThermoModel` updates its ISA barometric lapse and convective cooling coefficients ($h_{\text{conv}}$).
* **Expected Output:** Gauges adjust nominal operating baselines to reflect thin air cooling characteristics.
* **What the Judge Sees:** Environmental readout widgets update to display current air density and ISA deviation.
* **Technical Concept Demonstrated:** **Environmental Compensation.** Shows that the system models real atmospheric physics rather than assuming sea-level conditions.
* **Code Producing It:** `backend/physics/thermo_model.py`.

---

### STEP 03: TELEMETRY STREAM LAUNCH (20 Hz SYNTHETIC CAN BUS)
* **Input:** Click `"Engage Telemetry Feed"`.
* **Expected Behavior:** CAN streamer broadcasts 20 frames per second over simulated CAN 2.0B bus.
* **Actual Implementation:** `can_streamer.py` packs engine parameters into binary frames; `_ingest_frame()` decodes them via DBC bitmasks.
* **Expected Output:** RPM needle sweeps smoothly to $5,200\text{ RPM}$; CHT 1-4 stabilize at $110^\circ\text{C}$; Oil Pressure registers $4.2\text{ bar}$.
* **What the Judge Sees:** High-density analog dials and digital tapes animating at a rock-solid 60 FPS.
* **Technical Concept Demonstrated:** **Avionics Bus Ingestion & High-Frequency Streaming.**
* **Code Producing It:** `backend/telemetry/can_streamer.py`, `backend/services/state.py`.

---

### STEP 04: EKF STATE ESTIMATION & DIGITAL TWIN SYNCHRONIZATION
* **Input:** Continuous telemetry stream.
* **Expected Behavior:** Extended Kalman Filter filters sensor noise; Three.js WebGL engine model mirrors the physical state.
* **Actual Implementation:** EKF updates internal state vector $\hat{\mathbf{x}}_k$; WebGL fragment shaders render all four cylinder heads in nominal cool cyan.
* **Expected Output:** Clean state graphs with zero jitter; 3D engine model rotating smoothly.
* **What the Judge Sees:** The operator drags the 3D model with the mouse, zooms into the cylinders, and inspects the reduction gearbox.
* **Technical Concept Demonstrated:** **Digital Twin Spatial Synchronization (ISO 23247 / LOI 2).**
* **Code Producing It:** `backend/services/state.py`, `frontend/src/components/ThreeD/EngineCanvas.tsx`.

---

### STEP 05: TACTICAL MANEUVER STRESS TEST (PROVING FALSE ALARM IMMUNITY)
* **Input:** Command rapid throttle advance from $65\% \to 100\%$ (simulating combat climb).
* **Expected Behavior:** RPM spikes to $5,800$; raw CHT climbs rapidly from $110^\circ\text{C} \to 128^\circ\text{C}$.
* **Actual Implementation:** The physics observer calculates expected nominal climb temperature ($\hat{T}_{\text{exp}} = 127.5^\circ\text{C}$). The **residual remains near zero** ($r_i^* < 0.8\sigma$).
* **Expected Output:** Anomaly score remains low ($0.012$); **NO FALSE ALARM IS TRIGGERED**.
* **What the Judge Sees:** Temperatures spike on the dials, but the Master Alarm remains green (`NOMINAL CRUISE CLIMB`).
* **Technical Concept Demonstrated:** **Thermodynamic Residual Generation (Core Differentiator).** Proves that our system does not sound false alarms during aggressive tactical maneuvers.
* **Code Producing It:** `backend/physics/thermo_model.py`, `backend/services/detection_pipeline.py`.

---

### STEP 06: CONTROLLED FAULT INJECTION: CYLINDER #2 THERMAL RUNAWAY
* **Input:** Click `"Inject Fault: F02 Exhaust Valve Leak / Thermal Runaway"`.
* **Expected Behavior:** Progressive mechanical degradation is injected onto Cylinder #2. Temperature begins climbing at $+0.8^\circ\text{C/s}$.
* **Actual Implementation:** `can_streamer.py` applies a thermal generation offset simulating combustion gas leakage past the exhaust valve seat into the aluminum head.
* **Expected Output:** Cylinder Head #2 begins climbing ($112^\circ\text{C} \to 125^\circ\text{C} \to 138^\circ\text{C} \to 145^\circ\text{C}$). Cylinders 1, 3, and 4 remain completely nominal.
* **What the Judge Sees:** The white needle for CHT 2 on the multi-channel bar graph starts creeping upward away from the other three cylinders.
* **Technical Concept Demonstrated:** **Realistic Progressive Mechanical Failure Injection.**
* **Code Producing It:** `backend/ml/generator.py`, `backend/telemetry/can_streamer.py`.

---

### STEP 07: THERMODYNAMIC RESIDUAL DIVERGENCE & Z-SCORE ESCALATION
* **Input:** Live fault progression.
* **Expected Behavior:** Physics observer continues to expect $110^\circ\text{C}$ based on cruise airspeed and throttle. The raw residual for Cylinder #2 surges: $r_2 = 138.0 - 110.0 = +28.0^\circ\text{C}$.
* **Actual Implementation:** `DetectionPipeline` computes normalized z-score: $r_2^* = \frac{+28.0}{5.5} = +5.09\sigma$.
* **Expected Output:** The live residual stream graph shows the Cyan baseline line flat, while the Red Cylinder #2 residual line surges into the danger zone.
* **What the Judge Sees:** The residual chart exposes the fault while the absolute temperature is still within the normal operating limits ($138^\circ\text{C} < 150^\circ\text{C}$).
* **Technical Concept Demonstrated:** **Incipient Fault Observability Before Static Redline Breaches.**
* **Code Producing It:** `backend/services/detection_pipeline.py`.

---

### STEP 08: UNSUPERVISED ANOMALY DETECTION (NUMPY AUTOENCODER IN 62 μs)
* **Input:** Normalized residual vector $\mathbf{r}_k^* = [0.1, 5.09, -0.2, 0.1, 0.4, \dots]^T$.
* **Expected Behavior:** Autoencoder fails to reconstruct the unfamiliar +5.09σ spike on Cylinder #2.
* **Actual Implementation:** Pure NumPy forward pass: $\mathbf{r}^* \to \mathbf{h}_1 \to \mathbf{z} \to \mathbf{h}_2 \to \hat{\mathbf{r}}^*$.
* **Expected Output:** Reconstruction loss breaches threshold: $J_{\text{AE}} = 0.082 > 0.050$. Anomaly flag asserts in **0.062 milliseconds**.
* **What the Judge Sees:** The Master Anomaly status flashes amber: `ANOMALY DETECTED (CONFIDENCE: 99.4%)`.
* **Technical Concept Demonstrated:** **Sub-Millisecond Edge Anomaly Detection.**
* **Code Producing It:** `backend/ml/autoencoder.py`.

---

### STEP 09: SUPERVISED FAULT DIAGNOSIS & EXPLAINABILITY (RANDOM FOREST)
* **Input:** Anomaly trigger routes residual vector to `FaultClassifier`.
* **Expected Behavior:** Random Forest isolates the multi-variable pattern and classifies the fault.
* **Actual Implementation:** 100 trees evaluate decision splits. Majority vote latches over 3 frames.
* **Expected Output:** Classification output:  
  `DIAGNOSIS: FAULT F02 (CYLINDER #2 OVERHEAT / VALVE BLOWOUT) | CONFIDENCE: 98.2%`  
  `PRIMARY CONTRIBUTING FEATURE: CHT_2 RESIDUAL (68.4% FEATURE IMPORTANCE)`
* **What the Judge Sees:** A critical red alert banner locks onto the screen. In the 3D WebGL viewport, the Cylinder #2 CAD head turns incandescent glowing red, while the other three cylinders remain cool blue.
* **Technical Concept Demonstrated:** **Explainable Multi-Class Failure Diagnostics & 3D Spatial Binding.**
* **Code Producing It:** `backend/ml/classifier.py`, `frontend/src/components/ThreeD/EngineCanvas.tsx`.

---

### STEP 10: PROBABILISTIC RUL EXTRAPOLATION (AIC FIT + 500 MONTE CARLO)
* **Input:** Rolling history of the CHT #2 residual slope.
* **Expected Behavior:** AIC polynomial regression fits the degradation trajectory and projects time to $150^\circ\text{C}$ critical failure.
* **Actual Implementation:** 500-sample Monte Carlo perturbation simulates parameter variance. Rainflow counting updates cumulative fatigue damage $D = 0.042$.
* **Expected Output:** UI RUL Widget displays:  
  `REMAINING USEFUL LIFE: 18.4 MINUTES`  
  `90% CONFIDENCE INTERVAL: [14.8 MIN — 22.1 MIN]`  
  `FATIGUE DAMAGE ACCUMULATION: 4.2% CONSUMED`
* **What the Judge Sees:** A probabilistic confidence band gauge showing the failure horizon with statistical error bars.
* **Technical Concept Demonstrated:** **Mathematically Defensible Prognostics (Conformal Monte Carlo RUL).**
* **Code Producing It:** `backend/ml/trend_analyser.py`.

---

### STEP 11: MISSION RELIABILITY IMPACT & 6-DOF AUTO-GCAS CANYON ESCAPE
* **Input:** Power degradation reduces shaft power from $73.5\text{ kW} \to 42.0\text{ kW}$.
* **Expected Behavior:** The 6-DOF flight model in `standalone_canyon_flight_app.py` recalculates rate of climb. The UAV enters an uncommanded descent ($V_z = -1.8\text{ m/s}$) into a mountain canyon.
* **Actual Implementation:** Terrain raycasting detects canyon wall proximity. Time-to-impact drops to $\text{TTI} = 2.1\text{ s} < 2.5\text{ s}$. Auto-GCAS triggers an emergency 3.5g terrain fly-up maneuver and commands an evasive 45° bank toward the widest valley opening.
* **Expected Output:** The UAV levels its wings, pulls maximum positive G, clears the jagged canyon ridge with $42\text{ meters}$ of clearance, and establishes a safe glide cone toward an emergency diversion runway.
* **What the Judge Sees:** A stunning 3D simulation in Blender showing the tactical UAV avoiding a fatal mountain crash caused by engine power loss.
* **Technical Concept Demonstrated:** **Propulsion-to-Mission Coupling & Autonomous Collision Avoidance.**
* **Code Producing It:** `apps/blender_twin/standalone_canyon_flight_app.py`.

---

### STEP 12: AIR-GAPPED AI VOICE COPILOT TACTICAL CONSULTATION
* **Input:** Press spacebar on the GCS and speak into the microphone:  
  *"Copilot, what is our engine status and tactical recommendation?"*
* **Expected Behavior:** Local Whisper.cpp transcribes the voice; local Qwen3-4B queries RAG manuals; local Kokoro TTS responds with spoken audio.
* **Actual Implementation:** All inference runs on the local CPU/GPU with zero internet packets transmitted.
* **Expected Output:** The headset speaks aloud in $<800\text{ ms}$:  
  *"Warning: Cylinder Two head temperature is 142 degrees Celsius, 32 degrees above thermodynamic baseline. Exhaust valve leak diagnosed with 98 percent confidence. Remaining useful life is 18 minutes. Recommend reducing throttle to 65 percent, rich mixture, and initiating immediate diversion to Waypoint Charlie."*
* **What the Judge Sees:** A seamless, natural language spoken tactical consultation executed 100% offline.
* **Technical Concept Demonstrated:** **Tactical Pilot Decision Support & Air-Gapped Small Language Models.**
* **Code Producing It:** `backend/services/voice/`, `backend/services/rag/`.

---

### STEP 13: POST-FLIGHT TELEMETRY BUNDLING & PDF AIRWORTHINESS AUDIT
* **Input:** Command flight touchdown and engine shutdown. Click `"Generate Sortie Audit Report"`.
* **Expected Behavior:** The entire 20 Hz mission history is bundled and a formal cryptographic PDF airworthiness report is generated.
* **Actual Implementation:** `mission_bundle.py` serializes telemetry; `pdf_generator.py` compiles the PDF.
* **Expected Output:** A formal PDF opens showing:
  * Sortie Duration: 14.2 minutes
  * Peak CHT: 144.2°C (Cylinder #2)
  * Cumulative Fatigue Damage: $D = 0.042$
  * Mandatory Maintenance Action: *"Mandatory borescope inspection of Cylinder #2 exhaust valve and seat prior to next flight."*
* **What the Judge Sees:** A professional, publication-quality military airworthiness certificate.
* **Technical Concept Demonstrated:** **Data Provenance, Fleet Integrity & Automated Maintenance Records.**
* **Code Producing It:** `backend/reports/mission_bundle.py`, `backend/reports/pdf_generator.py`.

---

### STEP 14: 3D SPATIAL TRAJECTORY REPLAY IN BLENDER
* **Input:** Open `standalone_mission_graph_app.py` in Blender.
* **Expected Behavior:** Ingests the mission bundle and renders the 3D flight trajectory as a continuous spatial curve.
* **Actual Implementation:** Converts GPS and altitude coordinates into a 3D NURBS spline. Color-codes vertices by engine health (Green $\to$ Yellow $\to$ Red).
* **Expected Output:** The 3D viewport shows the flight path in green during takeoff and climb, transitioning to bright red at the exact geographic coordinates where the valve failed in the canyon.
* **What the Judge Sees:** A photorealistic 3D spatial reconstruction of where and why mechanical degradation occurred.
* **Technical Concept Demonstrated:** **Post-Flight Spatial Incident Reconstruction.**
* **Code Producing It:** `apps/mission_graph_viewer/standalone_mission_graph_app.py`.

---

## 3. DEMONSTRATION VERDICT & EVALUATION IMPACT

By following this 14-step experimental protocol, our presentation proves:
1. **Zero Fake Demos:** Everything is driven by live physics equations, active machine learning models, and real-time sockets.
2. **Scientific Rigor:** Evaluators see the exact equations, residual z-scores, and Monte Carlo confidence intervals.
3. **Mission Value:** Evaluators see how engine health directly saves the aircraft through Auto-GCAS terrain avoidance.
4. **Air-Gapped Readiness:** Evaluators witness offline voice intelligence operating with physical network cables disconnected.
