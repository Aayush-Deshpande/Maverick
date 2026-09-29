# Demonstration Methodology & Verification Discipline

Building a defense-grade cyber-physical digital twin requires more than developing software: it demands proving its fidelity, determinism, and airworthiness under rigorous technical interrogation. This chapter covers ANUMAAN's verification methodology: addressing core aerospace engineering questions from first principles, structuring demonstrations as controlled physical experiments, and enforcing a comprehensive testing discipline across the entire stack.

---

## Technical Verification & Defence Readiness

To ensure the system withstands scrutiny from propulsion scientists, avionics specialists, and airworthiness certifiers, the engineering architecture was verified against the central questions of military aerospace software:
1. **Bi-Directional State Observation:** Demonstrating that the digital twin is an active Continuous-Discrete Extended Kalman Filter state observer estimating unmeasured internal thermodynamic states ($P_{\max}, TIT, h_{\min}$), not a one-way telemetry gauge.
2. **0D/1D Thermodynamic Fidelity:** Proving that the physics engine solves mass, momentum, and energy conservation equations (intake manifold dynamics, modified Seiliger combustion, Chen-Flynn friction balance) rather than fitting heuristic polynomials.
3. **Sensor Fault vs. Engine Fault Isolation:** Formulating an analytical parity space matrix ($\mathbf{V}_p \mathbf{C}_s = \mathbf{0}$) that mathematically distinguishes thermocouple oxidation drift from genuine cylinder lean-burn burnout within $40\text{ ms}$.
4. **Certified Uncertainty Bounds:** Stating Remaining Useful Life with certified 95% Split Conformal Prediction intervals rather than fabricated scalar point estimates.
5. **DO-178C DAL-C Airworthiness Alignment:** Implementing an ASTM F3269-17 Simplex Run-Time Monitor guaranteeing deterministic failover to certified Kalman states within $10\text{ ms}$ if non-deterministic neural inferences produce non-physical outputs.

Every module in ANUMAAN provides concrete mathematical formulations and reproducible test results verifying its claims.

---

## Demonstration as a Controlled Live Experiment

The demonstration methodology follows a deliberate philosophy: presenting the system as a controlled engineering experiment rather than a static feature tour. The goal is to provide technical evaluators with direct, observable cause and effect rooted in physical laws.

The demonstration protocol follows a systematic five-step sequence:
1. **Nominal Baseline Calibration:** Establishing steady-state operating points across altitude, airspeed, and throttle, confirming that normalized physics residuals $\mathbf{r}^*(t)$ conform to Gaussian white noise.
2. **Dynamic Transient Rejection (Proving the Negative):** Demonstrating that rapid, legitimate throttle transients (such as slam acceleration from idle to full power) do not trigger false alarms, because the 0D/1D model predicts the transient temperature and pressure shifts accurately.
3. **Seeded Physical Degradation:** Injecting realistic component-level degradation (for example, localized cooling loss or injector nozzle varnishing) into the physical plant model.
4. **End-to-End Pipeline Execution:** Tracing the resulting physics residual divergence through EVT POT anomaly detection, Bayesian FMECA classification, and Three.js 3D component localization in real time.
5. **Tactical Operational Consequence:** Recalculating mission completion reliability ($R_{\text{mission}}$), projecting aerodynamic glide reachability cones ($L/D_{\max}$), and executing candidate throttle derates to ensure airframe survival.

---

## Automated Testing Discipline & Characterization

Supporting both the theoretical architecture and live demonstration is a comprehensive automated testing suite. The backend includes dedicated characterization tests written to pin exact headline behavior as fixed regression assertions:
- **Crank-Angle Diagnostics:** Verifies that a healthy simulated engine reports a nominal verdict with firing order 1-4-2-3 and uniform per-cylinder torque contribution, and confirms that an induced misfire is deterministically attributed to the exact faulty cylinder within a single four-stroke engine cycle ($22.2\text{ ms}$).
- **EKF Observer Convergence:** Validates that state covariance converges within $800\text{ ms}$ and innovation whiteness satisfies $p > 0.05$.
- **Parity Space Sensor Isolation:** Confirms that induced sensor bias drifts are isolated with $> 99\%$ accuracy while engine mechanical residuals remain flat.
- **Mission Reliability Engine:** Pins Monte Carlo multi-phase reliability calculations against baseline analytic hazard distributions.

Automated characterization guarantees that performance figures presented in this documentation are verified on every test execution.

---

## End-to-End Workflow Verification

Alongside backend unit and characterization suites, automated browser verification exercises the ground control station's major operational workflows:
- **Multi-Engine Runtime Verification:** Exercises the telemetry ingestion and 3D visual twin across all five supported engine platforms (Rotax 912 iS, 914 F, 915 iS, Austro AE300, VRDE Jayem 2.2L).
- **Interactive 3D Visualizer:** Confirms shader thermal gradient rendering, dynamic exploded view controls, and component-level fault pulsing.
- **Deterministic Mission Replay:** Validates time-scrubbing playback from cryptographically sealed Parquet logs with bit-identical state reproduction.
- **Full Mission Simulation Sequence:** Executes end-to-end mission planning, live flight simulation, fault injection, prescriptive throttle derate, debrief generation, and mission knowledge graph indexing.

---

## The Engineering Standard

ANUMAAN demonstrates what an integrated aerospace health monitoring system can achieve when anchored in first principles: combining multi-physics state estimation, disciplined machine learning, and tactical pilot decision support into an operational platform ready for test bench and flight line deployment.

Back to [SIH Journey](index.md).
