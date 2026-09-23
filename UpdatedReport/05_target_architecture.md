# 05 — Target Defense-Grade Architecture & Subsystem Specification

**Standard Reference:** ISO 13374 (Condition Monitoring & Diagnostics of Machines) / MIMOSA OSA-CBM  
**Aviation Standards:** STANAG 4586 (UAS Control System Interoperability) LOI 2 / DO-178C (Software Considerations)  
**Target Platform:** Indian MALE UAV (TAPAS-BH-201 / Archer-NG Class)  
**Propulsion Systems Supported:** Rotax 912 iS (Spark-Ignition) & Austro AE300 / VRDE-Jayem 2.2L (Common-Rail Turbo-Diesel)  

---

## 1. The Six-Layer ISO 13374 / MIMOSA OSA-CBM Architecture

The target architecture replaces ad-hoc hackathon structures with the internationally accepted standard for military and aerospace condition-based maintenance: **ISO 13374** (MIMOSA Open Systems Architecture for Condition-Based Maintenance - OSA-CBM).

```
═══════════════════════════════════════════════════════════════════════════════════════
                      LAYER 6: ADVISORY GENERATION (AG)
   Multi-Role HMI: Operator Glass Cockpit │ Engineer Deep-Dive │ Ground Crew CBM
   ATA Chapter Directives │ Emergency Checklists │ Flight Vector Intent Commands
═══════════════════════════════════════════════════════════════════════════════════════
                                      ▲
                                      │ (Action Directives / Risk Metrics)
═══════════════════════════════════════════════════════════════════════════════════════
                    LAYER 5: PROGNOSTIC ASSESSMENT (PA)
   Conformalized Degradation Extrapolation (p10/p50/p90) │ Prognostic Horizon
   Rainflow Cycle Counting + Palmgren-Miner Linear Damage Accumulation
   Mission Go/No-Go Feasibility Evaluator │ Dynamic Range / Glide Margin Penalties
═══════════════════════════════════════════════════════════════════════════════════════
                                      ▲
                                      │ (Degradation Slopes / Damage Fractions)
═══════════════════════════════════════════════════════════════════════════════════════
                     LAYER 4: HEALTH ASSESSMENT (HA)
   Multi-Class Fault Isolation (Random Forest with "UNKNOWN" OOD Rejection)
   Subsystem Health Indices (Propulsion, Fuel, Electrical, Thermal, Mechanical)
   Causal Propagation Graph Reasoning │ Local Vector RAG Knowledge Retrieval
═══════════════════════════════════════════════════════════════════════════════════════
                                      ▲
                                      │ (Isolated Fault Signatures / Health Indices)
═══════════════════════════════════════════════════════════════════════════════════════
                      LAYER 3: STATE DETECTION (SD)
   Dual-Plane Anomaly Detection: Residual Autoencoder Loss + Mahalanobis Distance
   Order-Tracked Gearbox Harmonic Peaks │ Sub-Threshold Trend Drift Flags
   Threshold Baseline Comparator (Early Detection Lead Time Measurement)
═══════════════════════════════════════════════════════════════════════════════════════
                                      ▲
                                      │ (Normalized Residual Vectors: Actual - Expected)
═══════════════════════════════════════════════════════════════════════════════════════
                     LAYER 2: DATA MANIPULATION (DM)
   Extended Kalman Filter (EKF) State Estimation & Sensor Noise Whitening
   Analytical Parity Space Sensor Validation & Cross-Sensor Residual Shielding
   1D First-Principles Thermodynamic Virtual Observer (Rotax 912 iS & AE300)
═══════════════════════════════════════════════════════════════════════════════════════
                                      ▲
                                      │ (Calibrated Telemetry Frames @ 20 Hz / MAVLink)
═══════════════════════════════════════════════════════════════════════════════════════
                    LAYER 1: DATA ACQUISITION (DA)
   ONBOARD EDGE SBC (Deterministic Linux / RTOS / SocketCAN)
   Dual-Redundant CANaerospace Bus (500 kbps) │ Crank-Angle Optical Trigger (60-2)
   10 kHz Piezoelectric Accelerometer Edge DSP │ MAVLink SATCOM Streamer (25 kbps)
═══════════════════════════════════════════════════════════════════════════════════════
```

---

## 2. Granular Layer Specifications & Interface Contracts

### 2.1 Layer 1: Data Acquisition (DA) — The Onboard Edge Layer
* **Deployment Hardware:** Dedicated airborne Edge Single-Board Computer (SBC) (e.g., BeagleBone AI, Raspberry Pi Compute Module 4, or DO-254 certifiable FPGA/ARM SoC) physically installed in the UAV avionics bay.
* **Bus Interfaces:** Dual-redundant CAN bus (CAN 2.0B / CANaerospace / ARINC 825) operating at 500 kbps interfacing with the engine FADEC/ECU (Lane A and Lane B).
* **High-Rate Vibration Acquisition:**
  * Single-axis casing piezoelectric accelerometer sampled at **10.0 kHz** with an analog hardware anti-aliasing filter ($f_c = 4.0\,\text{kHz}$).
  * Tachometer-synchronized crank pulse input (60-2 tooth trigger wheel) providing angular resolution $\Delta \theta = 6^\circ$.
* **Local Edge Processing (Survives SATCOM Link Loss):**
  * Computes 1024-point Fast Fourier Transform (FFT) and envelope demodulation locally.
  * Extracts order-tracked harmonics ($1\times, 2\times, 3\times f_{\text{prop}}$), vibration RMS, crest factor, and kurtosis.
  * Buffers full-rate 10 kHz data to onboard NVMe flash storage for post-flight maintenance depot downloads.
* **Air-to-Ground Telemetry Encoder:**
  * Encapsulates 27 calibrated physical parameters + 4 vibration features into standard **MAVLink / STANAG 4586** messages.
  * Bandwidth: $\approx 24.8\,\text{kbps}$ at 20 Hz. Tolerates 5% packet drop and 1.2-second latency over satellite link.

### 2.2 Layer 2: Data Manipulation (DM) — The Real-Time Digital Twin Observer
* **Deployment Environment:** Ground Control Station (GCS) telemetry server or edge-gateway node.
* **Extended Kalman Filter (EKF) State Estimator:**
  * Reconstructs unmeasured or noisy engine internal states: cylinder charge mass, scavenging ratio, and instantaneous combustion chamber temperature.
  * State Vector: $\mathbf{x} = [RPM, P_{\text{MAP}}, \dot{m}_{\text{air}}, T_{\text{cyl1..4}}, T_{\text{oil}}, P_{\text{oil}}, V_{\text{bus}}]^T$.
* **Analytical Redundancy Parity Space (Sensor Validation):**
  * Evaluates cross-sensor analytical parity:
    $$\epsilon_{\text{parity}} = \mathbf{V} \cdot \mathbf{y}_{\text{measured}} - \mathbf{C} \cdot \hat{\mathbf{x}}$$
  * Discriminate between sensor failure (thermocouple open circuit, transducer drift) and real engine degradation.
  * **Residual Shielding:** If sensor channel $i$ is flagged as drifting or failed, dynamically zero its corresponding residual ($r_i = 0$) to shield downstream AI anomaly detectors from false alarms.
* **First-Principles Thermodynamic Virtual Model:**
  * Solves instantaneous mass and energy balances based on density altitude derating $\rho(h, \text{OAT})$.
  * Dual-configuration support:
    1. **Rotax 912 iS (SI):** Naturally aspirated Otto cycle, port injection timing, and cooling baffle convection.
    2. **Austro AE300 / VRDE 2.2L (CI):** Turbocharger compressor/turbine match maps, common-rail direct injection timing (up to 1,600 bar), and intercooler effectiveness.
  * Generates the 14-channel normalized **Residual Vector**:
    $$r_i = \frac{y_{i, \text{measured}} - y_{i, \text{expected}}}{\sigma_{i, \text{nominal}}}$$

### 2.3 Layer 3: State Detection (SD) — Anomaly Detection & Baselining
* **Dual-Plane Anomaly Detection Ensemble:**
  * **Plane A (Multivariate Learned Autoencoder):** 14-8-4-8-14 fully connected network. Scores subtle cross-channel correlation shifts (e.g., CHT rising while fuel flow slightly drops).
  * **Plane B (Statistical Mahalanobis Distance):**
    $$D_M(\mathbf{r}) = \sqrt{(\mathbf{r} - \boldsymbol{\mu})^T \boldsymbol{\Sigma}^{-1} (\mathbf{r} - \boldsymbol{\mu})}$$
    Captures acute single-sensor departures with strict parameter covariance weighting.
  * **Fused Anomaly Metric:** $A_{\text{score}} = \max(\text{Loss}_{\text{AE}}, D_M / D_{\text{threshold}})$.
* **Threshold Baseline Comparator:**
  * Continuously evaluates conventional fixed avionics redlines (e.g., Rotax manual limits: $\text{CHT} > 135^\circ\text{C}$, $\text{Oil Press} < 2.0\,\text{bar}$).
  * Quantifies **Early Detection Lead Time** ($\Delta t_{\text{lead}} = t_{\text{conventional}} - t_{\text{twin}}$), demonstrating pre-damage warning.

### 2.4 Layer 4: Health Assessment (HA) — Diagnostic Isolation & Causal Reasoning
* **Multi-Class Fault Classifier with Open-Set Rejection:**
  * 100-estimator Random Forest trained on residual signatures.
  * **Rejection Boundary:** If maximum class posterior probability $P(\text{Fault}_k \mid \mathbf{r}) < 0.60$ or residual vector distance exceeds training hull, classify as **"UNKNOWN ANOMALY"**. This avoids misclassifying novel failures into predefined buckets.
* **Deterministic Subsystem Health Indexing:**
  * Calculates distinct health indices ($0.0 - 1.0$) for five key engine subsystems:
    1. Propulsion / Compression ($H_{\text{prop}}$)
    2. Fuel Injection & Rail ($H_{\text{fuel}}$)
    3. Electrical Generation & Bus ($H_{\text{elec}}$)
    4. Thermal & Heat Rejection ($H_{\text{therm}}$)
    5. Mechanical Drive & Lubrication ($H_{\text{mech}}$)
* **Causal Propagation Engine:**
  * Traverses directed dependency graphs (e.g., *Baffle leak $\to$ CHT surge $\to$ Oil temperature rise $\to$ Lubricant viscosity drop $\to$ Friction torque increase*).
  * Grounds technical explanations with retrieved ATA maintenance manual documentation via the local RAG engine.

### 2.5 Layer 5: Prognostic Assessment (PA) — Degradation & RUL
* **Conformalized Trend Extrapolation:**
  * Fits candidate degradation curves ($y = a + bt$, $y = a e^{bt}$, $y = a t^b$) selected via Akaike Information Criterion (AIC).
  * Applies **Split Conformal Prediction**:
    $$C_{1-\alpha}(\mathbf{x}) = [\hat{y} - \hat{q}_{1-\alpha}, \hat{y} + \hat{q}_{1-\alpha}]$$
    Provides rigorous finite-sample coverage guarantees ($90\%$ confidence) without making Gaussian noise assumptions.
  * Outputs Remaining Useful Life bounds: $\text{RUL}_{\text{p10}}$ (conservative), $\text{RUL}_{\text{p50}}$ (median), $\text{RUL}_{\text{p90}}$ (optimistic).
* **Physics-of-Failure (PoF) Damage Accumulation:**
  * Concurrently executes **Rainflow Cycle Counting** on the thermal and mechanical stress history.
  * Accumulates fatigue damage fractions using the **Palmgren-Miner Linear Damage Rule**:
    $$D = \sum_{k=1}^{M} \frac{n_k}{N_k(\Delta \sigma_k, T_m)}$$
  * Evaluates lifing usage independently of short-term sensor fluctuations.
* **Mission Impact & Go/No-Go Feasibility:**
  * Compares $\text{RUL}_{\text{p10}}$ against planned sortie endurance ($t_{\text{mission}}$):
    $$\text{Margin} = \text{RUL}_{\text{p10}} - t_{\text{mission}}$$
  * Generates operational advisories: `GO` (Margin $> 2\,\text{h}$), `CAUTION` ($0 \le \text{Margin} \le 2\,\text{h}$), or `NO-GO` (Margin $< 0$).

### 2.6 Layer 6: Advisory Generation (AG) — Multi-Role Presentation
* **Operator View (Tactical Glass Cockpit):**
  * High-density tactical layout: RPM/MAP dials, thermal ladder gauges, alert annunciator, and Auto-GCAS / terrain warning cues.
  * Voice Copilot with streaming text and spoken turn synthesis.
* **Propulsion Engineer View (Diagnostic Deep-Dive):**
  * 14-channel residual strip charts, autoencoder reconstruction error spectra, sensor parity matrices, and Monte Carlo probability density functions.
* **Maintenance Depot View (CBM Work Orders):**
  * Fleet readiness dashboard, cross-theater wear statistics (Ladakh vs. Thar), component lifing ledgers, and formal inspector sign-off workflows.
* **3D Cyber-Physical Digital Twin (Blender / Three.js):**
  * True 1-to-1 CAD engine model dynamically highlighting damaged mechanical assemblies with red pulsing emission shaders mapped directly from Layer 4 diagnostic outputs.

---

## 3. Storage & Persistence Tier Architecture

The backend storage tier is split into three performance classes to handle high-frequency telemetry, multi-sortie analytics, and cold compliance archiving:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       STORAGE & PERSISTENCE TIER                            │
├────────────────────────┬──────────────────────────┬─────────────────────────┤
│ HOT TIER (Real-Time)   │ WARM TIER (Fleet State)  │ COLD TIER (Archival)    │
│                        │                          │                         │
│ • Circular Ring Buffer │ • SQLite / PostgreSQL    │ • Apache Parquet        │
│   in Shared Memory     │   Relational Store       │   Columnar Files        │
│ • 20 Hz Frame Cache    │ • Fleet Knowledge Graph  │ • Complete 20 Hz Frame  │
│   (Last 30 Minutes)    │   (fleet_graph.json)     │   Data Compressed       │
│ • Sub-millisecond read │ • CBM Work Orders, Sortie│ • Cryptographic SHA-256 │
│   latency for ML       │   Envelope & Anomalies   │   Tamper-Evident Hash   │
└────────────────────────┴──────────────────────────┴─────────────────────────┘
```

---

## 4. Architectural Interface Definitions

All inter-layer communication must follow strict, schema-validated contracts:

1. **Layer 1 $\to$ Layer 2 Interface:** `AirborneTelemetryPacket` (Binary MAVLink dialect over UDP / SocketCAN).
2. **Layer 2 $\to$ Layer 3 Interface:** `StateEstimateFrame` (Pydantic dataclass containing measured state, expected state, and normalized residual vector).
3. **Layer 3 $\to$ Layer 4 Interface:** `AnomalyReport` (Anomaly score, threshold exceedances, and FFT spectral harmonic ratios).
4. **Layer 4 $\to$ Layer 5 Interface:** `DiagnosticHypothesis` (Isolated fault ID, confidence, ATA chapter, and subsystem degradation rates).
5. **Layer 5 $\to$ Layer 6 Interface:** `PrognosticAdvisory` (RUL p10/p50/p90 bounds, Go/No-Go decision, and limiting component name).
6. **Layer 6 $\to$ External Clients:** `UnifiedTelemetryState` (JSON broadcast over WebSocket and HTTPS REST endpoints).
