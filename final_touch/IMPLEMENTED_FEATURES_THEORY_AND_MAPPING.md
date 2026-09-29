# ANUMAAN — Implemented Features, Theory & DRDO Alignment
**DRDO / SIH Problem Statement ID: 26054**

---

## Executive Feature Traceability Matrix

The table below correlates every implemented software feature in the repository with its theoretical foundations, implementation files, and the official DRDO Problem Statement requirement it fulfills:

| Feature Name | Theoretical / Engineering Foundation | Primary Implementation Files | DRDO PS-26054 Clause |
|---|---|---|---|
| **1D Thermodynamic Otto Cycle Twin** | First-principles 4-stroke thermodynamics, ICAO standard atmosphere derating, heat rejection balances | [`backend/physics/thermo_model.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/physics/thermo_model.py), [`engine_model.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/physics/engine_model.py) | §2 (Thermodynamic behavior models) |
| **Independent Virtual Plant (`VirtualEngine`)** | Physical model mismatch, stochastic build variation, sensor transfer functions, non-linear turbo dynamics | [`backend/plant/virtual_engine.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/plant/virtual_engine.py), [`adapter.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/plant/adapter.py) | §3.A (Synchronized virtual representation) |
| **Split-Conformal Residual Detector** | Split-conformal prediction quantiles, Locality Sensitive Hashing (FlyBloom), Mahalanobis metric | [`backend/detect/detector.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/detect/detector.py), [`scorers.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/detect/scorers.py), [`calibration.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/detect/calibration.py) | §2 & §3.C (Predictive anomaly detection) |
| **Multi-Engine Configuration Catalog** | Dimensionless scaling, bore/stroke geometry tables, SI vs. CI fuel injection, turbo maps | [`configs/engines/`](file:///e:/backup-llm/backup-no-llm/3d_engine/configs/engines), [`backend/physics/engine_config.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/physics/engine_config.py) | §2 (Scalable and modular digital twin) |
| **DRDO 8-Class Neural Fault Classifier** | Multi-class supervised pattern recognition, FMECA cross-correlation matrices | [`backend/ml/detection_pipeline.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/ml/detection_pipeline.py), [`fault_classifier.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/ml/fault_classifier.py) | §3.C (Fault Detection & Predictive Analytics) |
| **Deterministic ATA-Chapter Diagnostic Agent** | Aerospace ATA 71–80 chapters, deterministic expert rule graphs, prescriptive checklists | [`backend/agent/diagnostic_agent.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/agent/diagnostic_agent.py) | §3.C (SOP-grounded prescriptive action) |
| **Statistically Bound Conformal RUL** | Conformal calibration coverage bounds, non-conformity quantiles | [`backend/evaluation/conformal.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/evaluation/conformal.py), [`backend/ml/rul_estimator.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/ml/rul_estimator.py) | §2 & §3.D (Remaining Useful Life estimation) |
| **Cumulative Damage Accumulation Model** | Arrhenius reaction kinetics (thermal degradation) + Palmgren-Miner linear fatigue damage | [`backend/evaluation/damage_model.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/evaluation/damage_model.py) | §2 (Degradation trends and life-cycle) |
| **High-Rate 20 Hz WebSocket Server** | Asynchronous IO, pub/sub WebSocket channels, atomic state caching | [`backend/server/main.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/server/main.py), [`engine_api.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/server/engine_api.py) | §3.A (Real-time data ingestion capability) |
| **React Ground Control Station (GCS)** | Cyber-physical telemetry HUD, glass-cockpit instruments, dynamic fault injection levers | [`frontend/src/`](file:///e:/backup-llm/backup-no-llm/3d_engine/frontend/src) | §2 (Dashboard/HMI for operators) |
| **Blender 3D Viewport Digital Twin** | Procedural thermal shaders, hierarchical CAD meshes, camera transition math | [`apps/blender_twin/`](file:///e:/backup-llm/backup-no-llm/3d_engine/apps/blender_twin) | §2 (Real-time engine parameter visualization) |
| **Canyon Flight Simulation (Ladakh)** | Digital Elevation Model (DEM) terrain rendering, waypoint navigation simulation | [`assets/models/terrain.blend`](file:///e:/backup-llm/backup-no-llm/3d_engine/assets/models/terrain.blend), [`launch_canyon_simulation.bat`](file:///e:/backup-llm/backup-no-llm/3d_engine/launch_canyon_simulation.bat) | §2 (Simulating behavior under mission profiles) |
| **Offline RAG Knowledge Copilot** | Vector embeddings, sentence-transformers, FlashRank reranking, local Ollama LLMs | [`backend/knowledge/`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/knowledge), [`backend/agent/copilot.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/agent/copilot.py) | §3.D (Intelligent maintenance planning) |
| **Local STT / TTS Voice Assistant** | Offline OpenAI Whisper STT, Kokoro-82M neural TTS, zero-cloud audio pipeline | [`backend/voice/stt_engine.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/voice/stt_engine.py), [`tts_engine.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/voice/tts_engine.py) | §2 (Pilot/operator hands-free interface) |
| **Mission Knowledge Graph Database** | Graph theory, NetworkX, temporal sortie persistence, anomaly-to-maintenance linking | [`backend/graph/`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/graph), [`apps/mission_graph_viewer/`](file:///e:/backup-llm/backup-no-llm/3d_engine/apps/mission_graph_viewer) | §2 & §3.A (Post-flight analysis & operational history) |
| **High-Rate Crank Waveform DSP** | High-resolution timestamping (≤ 25 ns), indicated work integration, knock filtering | [`backend/core/cycle_block.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/core/cycle_block.py), [`backend/plant/sensors_hr.py`](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/plant/sensors_hr.py) | §3.B (Combustion instability & injection timing) |
| **Privacy-Preserving Federated Learning** | Federated Averaging (FedAvg / FedProx), Differential Privacy (DP), gradient quantization | [`FedNeMo/v1/fednemo/`](file:///e:/backup-llm/backup-no-llm/3d_engine/FedNeMo/v1/fednemo) | §3 (Fleet-level health monitoring infrastructure) |
| **Autonomous Mission Flight Planning** | Dynamic obstacle avoidance, terrain-following, energy-optimal climb/descent profiles | [`mission-planning/`](file:///e:/backup-llm/backup-no-llm/3d_engine/mission-planning) | §1 & §2 (Mission reliability enhancement & planning) |

---

## Detailed Feature Engineering Deep-Dives

### 1. 1D Thermodynamic Otto Cycle Physics Model
- **Theory & Mathematics:**
  The engine power and heat generation are governed by the four-stroke Otto thermodynamic cycle with altitude derating:
  $$P_{\text{indicated}} = \frac{V_d \times \text{RPM} \times \text{MAP} \times \eta_v}{120} \times \left[ 1 - \frac{1}{r^{\gamma - 1}} \right]$$
  Where $V_d = 1.352\text{ L}$, $r = 10.8$, and $\gamma = 1.35$.
  Ambient air density at altitude $h$ is modeled using the standard ISA barometric equations:
  $$T_{\text{amb}} = 288.15 - 0.0019812 \times h_{\text{ft}}, \quad P_{\text{amb}} = 101.325 \times \left( \frac{T_{\text{amb}}}{288.15} \right)^{5.25588}$$
  $$\sigma = \frac{\rho_{\text{amb}}}{\rho_{\text{sea-level}}}$$
  The expected CHT baseline is derived by balancing heat generation against forced air convection:
  $$\text{CHT}_{\text{expected}} = T_{\text{OAT}} + 85.0 \times \left( \frac{\text{TPS}}{100} \right)^{0.75} \times \left( \frac{\text{RPM}}{5000} \right)^{0.5}$$
- **Why It Was Implemented:** To establish a physics-grounded reference state that enables anomaly detection based on physical residuals ($y - \hat{y}$) rather than raw arbitrary sensor thresholds.

---

### 2. Independent Virtual Plant (`VirtualEngine`)
- **Theory & Engineering:**
  In a real manufacturing environment, no two engines are identical. `VirtualEngine` implements stochastic build variation:
  $$\text{Variation} = \{ \eta_{v,\text{scale}} \sim \mathcal{N}(1.0, 0.02), \quad f_{\text{friction}} \sim \mathcal{N}(1.0, 0.06), \quad h_{\text{transfer}} \sim \mathcal{N}(1.0, 0.045) \}$$
  Sensors do not measure reality instantly; they exhibit first-order low-pass thermal lag and bias:
  $$\frac{dT_{\text{sensor}}}{dt} = \frac{1}{\tau} (T_{\text{actual}} - T_{\text{sensor}}) + \beta_{\text{drift}}$$
- **Why It Was Implemented:** Closes architectural flaw G01. Guarantees that diagnostic algorithms are tested against genuine model mismatch and sensor imperfections rather than checking their own generator.

---

### 3. Split-Conformal Residual Anomaly Detector (Tier 0)
- **Theory & Mathematics:**
  Given a sequence of nominal calibration frames $F_1, \dots, F_n$, the detector extracts 13 residual features $z_i = (x_i - \mu_i) / \sigma_i$ and evaluates three non-conformity scorers:
  1. **Max Absolute Z-Score:** $s_1 = \max_j |z_j|$
  2. **Mahalanobis Distance:** $s_2 = \sqrt{z^T \Sigma^{-1} z}$
  3. **FlyBloom LSH Scorer:** Random sparse projection into 256 Kenyon cell activations, checking novel bit density.
  For a designated false-alarm significance level $\alpha$ (e.g. $\alpha = 0.01$), the conformal threshold $\tau$ is computed as the finite-sample quantile:
  $$\tau = \text{Quantile}\left( \frac{\lceil (n + 1)(1 - \alpha) \rceil}{n}, \; \{ s(F_i) \}_{i=1}^n \right)$$
  To eliminate spurious false alarms from flight turbulence, a `PersistenceGate` confirms the alarm only if $\ge 3$ of the last 5 ticks exceed $\tau$.
- **Why It Was Implemented:** Solves the notorious false-alarm problem in defense condition monitoring, providing a mathematically guaranteed upper bound on false-alarm rates during combat sorties.

---

### 4. Deterministic ATA-Chapter Diagnostic Directives
- **Theory & Engineering:**
  Aerospace operations require certification under FAA/EASA and DRDO SOPs. An emergency flight directive cannot depend on a generative model that might hallucinate non-existent valves or incorrect airspeeds.
  The engine maps the 8 DRDO fault modes to deterministic directives:
  - **Mode 1 (Cylinder #2 Overheat):** ATA 72-00 $\to$ Throttle back to 4,600 RPM, enrich fuel trim +12%, descend 3,000 ft.
  - **Mode 2 (Injector #1 Clog):** ATA 73-10 $\to$ Verify rail pressure, force FADEC to Lane B backup schedule, engage auxiliary boost pump.
  - **Mode 3 (Ignition Misfire):** ATA 74-00 $\to$ Toggle ignition lanes (Lane A $\to$ Lane B), stabilize at loiter RPM.
  - **Mode 4 (Oil Pressure Loss):** ATA 79-00 $\to$ Immediate critical warning; throttle to minimum safe glide power, initiate emergency landing sequence.
- **Why It Was Implemented:** Provides instantaneous, 100% reproducible, airworthiness-compliant pilot instructions during mission-critical propulsion emergencies.

---

### 5. Conformal-Calibrated Remaining Useful Life (RUL) & Mission Reliability ($R_m$)
- **Theory & Mathematics:**
  Predicting a single number for RUL (e.g. "300 hours") is dangerous in aviation because point estimates provide no uncertainty bound.
  ANUMAAN combines cumulative Arrhenius thermal aging with Palmgren-Miner fatigue:
  $$D_{\text{total}} = \sum_{i} \frac{n_i}{N_i} + \int A \cdot \exp\left( -\frac{E_a}{R \cdot T(t)} \right) dt$$
  Applying split-conformal calibration on run-to-failure historical engines yields a bounded confidence interval:
  $$[\text{RUL}_{\text{lower}}, \; \text{RUL}_{\text{upper}}] = [\widehat{\text{RUL}} - q_{1-\alpha}, \; \widehat{\text{RUL}} + q_{1-\alpha}]$$
  The Mission Reliability $R_m$ for an upcoming planned sortie duration $t_{\text{mission}}$ is then computed using the conservative lower bound:
  $$R_m = \exp\left( - \left( \frac{t_{\text{mission}}}{\text{RUL}_{\text{lower}}} \right)^\beta \right)$$
  If $R_m < 0.90$, the system automatically issues a prescriptive mission abort / flight plan divert directive.
- **Why It Was Implemented:** Directly fulfills DRDO Problem Statement §1 & §2: enhancing mission reliability and preventing in-flight asset loss.
