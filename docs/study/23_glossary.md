# Part XXIII — Glossary

*Every acronym and term used in this course, with the part where it is explained.*

---

## Aircraft and UAV

| Term | Meaning |
|---|---|
| **MALE** | Medium Altitude Long Endurance — UAV class flying ~20–30,000 ft for 18–24 h. [Part I](01_big_picture.md) |
| **UAV / UAS** | Unmanned Aerial Vehicle / Unmanned Aircraft System (the aircraft plus ground segment) |
| **GCS** | Ground Control Station — where operators sit. [Part IV](04_telemetry_and_comms.md) |
| **ISR** | Intelligence, Surveillance, Reconnaissance — the typical MALE mission |
| **TAPAS-BH-201** | DRDO's MALE UAV, formerly Rustom-II. ✅ ~250 km range, 18–24 h endurance, ~28–30,000 ft |
| **DEAL** | Defence Electronics Application Laboratory — ✅ DRDO lab that developed the TAPAS datalink |
| **ADE** | Aeronautical Development Establishment — DRDO lab developing TAPAS |
| **Sortie** | One flight from takeoff to landing |
| **LOI** | Level of Interoperability — ✅ STANAG 4586's five levels. [Part IV §4.4](04_telemetry_and_comms.md) |
| **Density altitude** | Pressure altitude corrected for temperature — the altitude the engine "feels". [Part XI §11.2](11_mission_simulation.md) |
| **ISA** | International Standard Atmosphere — the reference used for deviations |
| **OAT** | Outside Air Temperature |
| **IAS / TAS** | Indicated / True Airspeed |

## Engine

| Term | Meaning |
|---|---|
| **CHT** | Cylinder Head Temperature — metal temperature of the head. [Part II §2.2](02_engine_sensors.md) |
| **EGT** | Exhaust Gas Temperature — per-cylinder combustion window. [Part II §2.3](02_engine_sensors.md) |
| **MAP** | Manifold Absolute Pressure — air charge delivered |
| **ECU** | Engine Control Unit — the engine's computer. ✅ The Rotax 912 iS has two lanes |
| **FADEC** | Full Authority Digital Engine Control |
| **SFC** | Specific Fuel Consumption — fuel per unit power; a clean efficiency-degradation indicator |
| **Lane A / Lane B** | ✅ Redundant ECU channels; divergence between them indicates a sensor fault |
| **BTDC** | Before Top Dead Centre — ignition/injection timing reference |
| **Misfire** | A cylinder failing to combust — detectable via 0.5-order vibration and crank speed. [Part II §2.1](02_engine_sensors.md) |
| **Thermal mass** | Why CHT changes slowly — and why a fast jump means a sensor fault |

## Buses and protocols

| Term | Meaning |
|---|---|
| **CAN** | Controller Area Network — multi-master broadcast bus, ✅ ≤8 data bytes per frame. [Part III](03_ecu_can_acquisition.md) |
| **CAN_H / CAN_L** | ✅ The differential pair, ✅ 120 Ω terminated at both ends |
| **Dominant / recessive** | ✅ CAN's wired-AND bit states that make arbitration non-destructive |
| **Arbitration** | ✅ Lowest CAN ID wins, without corrupting the winner's message |
| **DLC** | Data Length Code — how many data bytes in a CAN frame |
| **CANaerospace** | ✅ Aeronautical higher-layer protocol over CAN, 4-byte header, used on UAVs |
| **SocketCAN** | ✅ Linux subsystem exposing CAN as a network interface. [Part III §3.2](03_ecu_can_acquisition.md) |
| **vcan** | Virtual CAN interface — develop without hardware |
| **DBC** | CAN database file defining signal position, byte order, scale and offset |
| **ARINC 429** | ✅ Commercial avionics bus, 32-bit words, 12.5/100 kbit/s, point-to-point |
| **MIL-STD-1553** | ✅ Military command/response bus, 1 Mbit/s, Manchester encoded |
| **J1939** | ✅ Heavy-duty vehicle CAN protocol with 29-bit IDs and PGNs |
| **MAVLink** | ✅ Lightweight UAV protocol. v2 magic ✅ 0xFD, ✅ 12–280 byte packets. [Part IV §4.5](04_telemetry_and_comms.md) |
| **CRC_EXTRA** | ✅ MAVLink checksum over the message *definition* — catches version mismatch |
| **STANAG 4586** | ✅ NATO UAV control system interoperability standard. [Part IV §4.4](04_telemetry_and_comms.md) |
| **CUCS** | ✅ Core UCS — the standardised, aircraft-agnostic control station core |
| **VSM** | ✅ Vehicle Specific Module — adapter converting non-compliant interfaces to STANAG messages |
| **DLI** | ✅ Data Link Interface — standard messages between VSM and CUCS |
| **CCISM** | ✅ Command and Control Interface Specific Module — bridges to legacy C4I systems |

## Communications

| Term | Meaning |
|---|---|
| **LOS / BLOS** | Line of Sight / Beyond Line of Sight. [Part IV §4.1](04_telemetry_and_comms.md) |
| **C-band / Ku-band** | ✅ LOS and SATCOM bands. Ku downlink 11.7–12.7 GHz, uplink 14–14.5 GHz |
| **SATCOM** | Satellite communications — ✅ adds ~1–1.5 s latency, ~122 kbps or less for C2 |
| **Uplink / Downlink** | Ground→aircraft (commands) / aircraft→ground (telemetry) |
| **C2 link** | Command and Control link — the mission-critical one |
| **Radio horizon** | 🔶 ≈ 4.12 × √(height in m) km |
| **Jitter** | Variation in latency |

## Signal processing

| Term | Meaning |
|---|---|
| **fs** | Sampling frequency. [Part VI §6.1](06_vibration_analysis.md) |
| **Nyquist frequency** | fs/2 — the highest representable frequency |
| **Aliasing** | High frequencies folding back and masquerading as low ones. **Irreversible** |
| **Anti-alias filter** | ✅ Analog low-pass **before** the ADC. Cannot be done in software afterwards |
| **FFT** | Fast Fourier Transform — O(N log N) frequency decomposition |
| **Δf** | Frequency resolution = fs/N |
| **PSD** | Power Spectral Density — normalised, comparable across window sizes |
| **STFT / Spectrogram** | Successive FFTs showing spectral evolution over time |
| **Window function** | Hann/Hamming taper reducing spectral leakage |
| **Order** | ✅ Multiple of shaft rotational frequency. [Part VI §6.5](06_vibration_analysis.md) |
| **Order tracking** | ✅ Angular resampling — synchronises the signal to shaft *angle* rather than time |
| **TSA / RSA** | ✅ Time/Rotor Synchronous Averaging — cancels non-synchronous content |
| **Envelope analysis** | ✅ Demodulating a resonance to reveal impact repetition rate. [Part VI §6.8](06_vibration_analysis.md) |
| **Hilbert transform** | How the envelope is computed |
| **BPFO / BPFI / BSF / FTF** | Bearing defect frequencies — outer race / inner race / ball spin / cage |
| **GMF** | Gear Mesh Frequency = teeth × shaft frequency |
| **RMS** | Root Mean Square — overall energy. A **late** indicator |
| **Kurtosis** | Fourth standardised moment — "peakiness". An **early** indicator, but non-monotonic |
| **Crest factor** | Peak / RMS — impulsiveness |

## PHM and machine learning

| Term | Meaning |
|---|---|
| **PHM** | Prognostics and Health Management |
| **HUMS** | Health and Usage Monitoring System |
| **Residual** | ✅ Measured − physics-expected. **The core quantity of the twin.** [Part X §10.3](10_digital_twin.md) |
| **Health index** | Composite 0–100 degradation indicator. [Part IX §9.3](09_rul_prognostics.md) |
| **RUL** | Remaining Useful Life. [Part IX](09_rul_prognostics.md) |
| **EoL** | End of Life |
| **Prognostic Horizon** | ✅ How far before EoL predictions stay within α-bounds. **The metric that matters** |
| **α-λ performance** | ✅ Is the prediction within an α-band at fraction λ of life? |
| **Convergence** | ✅ How fast RUL estimates settle |
| **Asymmetric scoring** | ✅ Late predictions penalised more than early. [Part XIX §19.5](19_evaluation.md) |
| **Anomaly detection** | Unsupervised "is this normal?" — trained on healthy data only |
| **Fault classification** | Supervised "which known fault?" — needs labelled faults |
| **EWMA / CUSUM** | Control charts accumulating small persistent deviations |
| **Mahalanobis distance** | Multivariate distance accounting for correlation. [Part VII §7.2.2](07_anomaly_detection.md) |
| **PCA** | Principal Component Analysis — reconstruction error as an anomaly score |
| **Isolation Forest** | Anomalies isolated in fewer random splits |
| **One-Class SVM** | Boundary enclosing healthy data |
| **Autoencoder** | Bottleneck network; reconstruction error indicates novelty |
| **Random Forest / XGBoost** | Tree ensembles — strong on small tabular feature sets |
| **1D CNN / Spectrogram CNN** | Deep learning on raw waveform / time-frequency image |
| **LSTM / GRU** | Recurrent networks for sequences |
| **Transformer** | Attention-based; data-hungry |
| **GNN** | Graph Neural Network |
| **SHAP / TreeSHAP** | Per-instance feature attribution; polynomial for trees |
| **Macro F1** | Unweighted mean F1 — rare classes count equally |
| **Class imbalance** | Why plain accuracy is useless here. [Part VIII §8.7](08_fault_diagnosis.md) |
| **Data leakage** | Test information reaching training — e.g. splitting by row instead of by engine |

## Bio-inspired methods

| Term | Meaning |
|---|---|
| **FlyHash** | ✅ LSH from the fly olfactory circuit — sparse high-dimensional codes. [Part XX](20_novelty_and_research.md) |
| **Expand-and-sparsify** | ✅ Random projection to high dimension, then winner-take-all |
| **Kenyon cells** | ✅ The fly's sparse-coding layer; ~5% active at a time |
| **Fly Bloom Filter** | ✅ Single-pass novelty detection derived from FlyHash |
| **BioHash** | ✅ Data-driven successor addressing FlyHash's inability to learn |
| **HDC** | Hyperdimensional Computing — ✅ the same family, already used in industrial edge anomaly detection |
| **Dictionary learning** | ✅ Learning waveform atoms for sparse representation — ✅ established in bearing diagnosis |
| **Connectome-constrained network** | ✅ Network whose topology comes from a measured connectome |

## Datasets

| Term | Meaning |
|---|---|
| **C-MAPSS** | ✅ NASA turbofan degradation simulation — the standard RUL benchmark. ✅ 21 sensors, 3 operational settings, FD001–FD004 |
| **N-CMAPSS** | ✅ Higher-fidelity successor |
| **CWRU** | ✅ Case Western bearing dataset, 12 kHz. Lab-controlled — results flatter |
| **Paderborn / KAt** | ✅ Bearing dataset with **naturally worn** as well as seeded faults |
| **XJTU-SY** | ✅ Bearing run-to-failure, 25.6 kHz — vibration **with** RUL |
| **FEMTO / PRONOSTIA** | ✅ Bearing run-to-failure, 25.6 kHz, IEEE PHM 2012 challenge |
| **IMS** | ✅ Cincinnati/NASA bearing dataset with natural defect history |
| **ALFA** | ✅ CMU UAV fault dataset — 47 flights, 23 sudden engine failures, labelled onset times |
| **MIMII** | ✅ Hitachi industrial machine sound dataset, ✅ CC BY-SA 4.0 |
| **SKAB** | ✅ Skoltech multivariate time-series anomaly benchmark |

## Evidence labels used in this course

| Label | Meaning |
|---|---|
| ✅ **VERIFIED** | Traceable to a cited public source |
| 🔶 **INFERENCE** | Engineering reasoning from verified facts |
| ⬜ **ASSUMPTION** | Our design choice — not a PS requirement, not what DRDO does |
| 🔒 **PROPRIETARY** | Genuinely not public. Never guessed |

---

**Back to:** [README and index](README.md) · **The mental model:** [README §The mental model](README.md)
