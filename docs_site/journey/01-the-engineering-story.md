# The Engineering Story

Project ANUMAAN was built for SIH Problem Statement 26054, DRDO's brief for an AI-enabled real-time digital twin system for health monitoring, fault prediction, and mission reliability enhancement of aero piston engines used in MALE UAVs. The problem statement asked for six coordinated capabilities: a digital twin core, a health monitoring layer, fault detection and predictive analytics, an AI/ML layer, simulation and replay, and a visualization dashboard. This chapter traces how Midnight Ciphers engineered this end-to-end system from first principles to flight line readiness.

---

## Research Before Implementation

Before writing production software against the problem statement, the team built a first-principles foundation covering the entire aerospace propulsion domain: engine sensors and fault signatures, CAN bus and ECU acquisition, telemetry bandwidth limits, edge versus ground compute allocation, vibration analysis from sampling theory through order tracking and envelope demodulation, anomaly detection, fault diagnosis, remaining useful life estimation, digital twin theory, mission simulation, datasets, system architecture, and evaluation methodology. Twenty-three parts, each starting from first principles and building into an operational design decision for ANUMAAN.

This sequence established the engineering depth of the project. A team that starts writing anomaly detection code before it has worked through what a residual physically means, or before it understands why fixed-frequency vibration analysis fails on an engine whose speed continuously changes, ends up with a system that looks complete on the surface but cannot defend its physical mechanics. The initial groundwork ensured that every line of software across the six architectural layers was anchored in thermodynamics and aerospace standards.

---

## Building the Physics Layer

The most consequential architectural decision was making fault detection depend strictly on physics, rather than on prescribed synthetic waveforms. A simpler approach would have been to author artificial vibration signatures: writing code that outputs a fixed waveform when a fault is triggered. While trivial to build, that approach cannot generalize, and unmodeled failure dynamics produce no physical signature.

ANUMAAN's physics layer instead computes cylinder pressure from slider-crank kinematics and a Wiebe heat-release function, propagates that through gas and inertial torque to produce crank angular velocity as a function of crank angle, and derives downstream observables from that foundation. A misfire in this model is a cylinder genuinely producing zero heat release during its power stroke. The angular velocity dip, the surge in half-order vibration energy, and the exhaust gas temperature drop that follow are not separately authored; they emerge naturally from the same differential equations governing normal engine behavior. Per-cylinder torque deficit at each cylinder's firing angle provides the basis for deterministic misfire isolation, and cycle-to-cycle pressure variance provides direct visibility into combustion instability.

The vibration analysis layer utilizes tach-synchronous order tracking rather than fixed-frequency spectral analysis, because a UAV engine's rotational velocity changes continuously with throttle and a fixed-frequency bin loses resolution during speed transients. Angular resampling converts the time-domain vibration signal into the angle domain so that mechanical defect harmonics (gear mesh, bearing ball pass frequencies, cylinder firing) land at invariant order coordinates regardless of engine RPM. Hilbert envelope demodulation then extracts amplitude-modulated bearing and gear defect signatures that a raw spectrum would mask. Reference engine constants (bore, stroke, compression ratio, firing order) for the Rotax 912 iS, 914, 915 iS, Austro AE300, and VRDE Jayem 2.2L are calibrated against published manufacturer specifications, providing a physical foundation for downstream analytics.

---

## Competitive Benchmarking & Empirical Precision

To ensure ANUMAAN delivered unmatched technical capability, the team conducted a rigorous benchmarking audit against state-of-the-art implementations of Problem Statement 26054. The system was evaluated across six core technical axes: real-time telemetry decoding, thermodynamic twin fidelity, vibration signal processing, diagnostic explainability, mission risk coupling, and airworthiness alignment.

The audit demonstrated several decisive advantages in ANUMAAN's architecture:
1. **Tach-Synchronous Order Tracking:** While baseline approaches rely on basic stationary FFTs, ANUMAAN implements order-domain angular resampling and Hilbert envelope demodulation capable of isolating localized bearing spalling under variable-speed flight profiles.
2. **Crank-Angle Resolved Diagnostics:** High-speed crank-angle analysis enables deterministic per-cylinder misfire detection within a single four-stroke engine cycle (22.2 ms at 5,400 RPM).
3. **Aero-Piston UAV Flight Data Integration:** In addition to seeded test-bench runs, ANUMAAN incorporates real operational flight telemetry from NASA's ACES program, which recorded flight data from the Altus II UAV powered by a turbocharged four-cylinder Rotax 914, aligning directly with the problem statement's target propulsion class.
4. **Anti-Leakage Safeguards:** Machine learning evaluations enforce strict mission-level group isolation across training, validation, and test splits, guaranteeing zero temporal data leakage.

---

## Bio-Inspired Novelty Detection Foundations

For fast, lightweight onboard anomaly detection, ANUMAAN incorporates Bio-Inspired Sparse Novelty Coding, an expand-and-sparsify algorithm modeled on the fruit fly olfactory projection circuit (FlyHash). 

The algorithm maps an input vector of order-band vibration features and physics residuals into a high-dimensional representation ($m = 2000$) via a deterministically seeded sparse random projection matrix. A winner-take-all non-linear lateral inhibition step preserves only the top 5% of activations, producing a sparse binary fingerprint. Because the projection is fixed and deterministic, execution time is strictly bounded ($\mathcal{O}(m \cdot p)$) with zero backpropagation or gradient descent required, making it suitable for low-power edge microcontrollers.

By applying this hyperdimensional sparse coding scheme to order-domain aero piston engine vibration and physics residuals together, ANUMAAN achieves continuous onboard novelty detection under strict UAV datalink bandwidth constraints without requiring labeled failure training sets.

---

## The Unified Mission Planning Executive

The mission planning and reliability subsystem ties propulsion health directly to flight operations. A single authoritative mission executive coordinates UAV kinematics, ISA atmospheric condition calculations, and the selected engine's physics runtime on every simulation cycle.

When faults occur or are injected during a mission, they propagate through the multi-physics twin, produce genuine sensor residuals, trigger the novelty detector, activate Bayesian diagnostic classification, and recalculate mission completion reliability ($R_{\text{mission}}$) in real time. If component degradation compromises mission success, the prescriptive advisor calculates candidate throttle deratings and dynamic glide reachability cones ($L/D_{\max}$) to guide the operator toward safe divert airfields.

Upon touchdown or mission termination, the mission executive automatically packages the flight record into cryptographically hashed Parquet logs and JSON manifests, indexing the flight mission into the mission knowledge graph for deterministic post-mission replay and depot fleet intelligence.

---

## Engineering Excellence & Full System Realization

Two core principles define the engineering of ANUMAAN:
1. **Physics-First Design:** Building the governing equations that produce normal engine behavior before building the analytics that detect departures from it ensures that detection inherits real thermodynamics, catching unmodeled multi-sensor failure modes naturally.
2. **End-to-End System Integrity:** Ensuring that every link in the cyber-physical chain runs unbroken: from raw SocketCAN telemetry frames, through 0D/1D state estimation, parity validation, Bayesian diagnosis, 3D visual component localization, and dynamic mission risk projection, to post-flight cryptographic debrief.

Continue to [Preparing for Evaluation](02-preparing-for-evaluation.md).
