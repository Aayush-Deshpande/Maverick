# Part XXII — Final Recommended Architecture

*If you were starting this project today, exactly what to build.*

---

## 22.1 The answer in one page

| Component | Decision |
|---|---|
| **Data source** | ⬜ Physics-based synthetic generator → `vcan0` (SocketCAN). Real CAN is a one-line swap |
| **Reference engine** | ⬜ Rotax 912 iS class — documented publicly, 🔒 CAN mapping is not |
| **Onboard bus** | ✅ CAN / CANaerospace at 500 kbit/s, ⬜ our own documented DBC |
| **Vibration** | ⬜ Dedicated channel, 10 kHz, hardware anti-alias filter, tach-synchronised |
| **Telemetry** | ✅ MAVLink-style framing over UDP, ⬜ ~25 kbit/s budget, ✅ ~1.2 s latency, lossy |
| **Standards posture** | ✅ STANAG 4586 **LOI 2** — telemetry consumer, never a controller |
| **Edge** | ⬜ Pi-class. Features + residuals + lightweight anomaly + logging. Survives link loss |
| **Physics** | ⬜ Our thermodynamic model, NumPy/SciPy, pure function |
| **Preprocessing** | Validity gate → residuals → order tracking → envelope → features |
| **Anomaly** | Layered: EWMA + Mahalanobis + PCA (edge) → ensemble + autoencoder (GCS) |
| **Classification** | Random Forest on residuals + vibration features, with "UNKNOWN" allowed |
| **RUL** | Trend extrapolation + intervals (baseline) → particle filter → GRU only if it wins |
| **Twin** | `TwinState` with residuals, uncertainty, staleness, degradation history |
| **Simulation** | Same physics model, hypothetical inputs, go/no-go with lower-bound planning |
| **Storage** | TimescaleDB (hot/warm) + Parquet (cold) |
| **Dashboard** | FastAPI + WebSocket → React + uPlot + Three.js |
| **Evaluation** | Split by airframe; false alarms/hour; macro F1; prognostic horizon; asymmetric RUL score |
| **Benchmarks** | ✅ C-MAPSS (RUL), Paderborn/CWRU (vibration), XJTU-SY (vibration RUL), SKAB (multivariate) |

---

## 22.2 The complete architecture

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  ONBOARD  (separate process, ideally separate hardware)                   ║
║                                                                           ║
║  ⬜ Synthetic generator ──┐                                                ║
║  🔶 CAN replay ───────────┼──▶ vcan0 ──▶ [python-can decode via our DBC]  ║
║  ❌ Live CAN (roadmap) ───┘                        │                      ║
║                                                    ▼                      ║
║  ⬜ Vibration @10 kHz ──▶ [window · FFT · order    [validity gate]        ║
║     + tach sync            track · envelope · stats]    │                 ║
║                                    │                    ▼                 ║
║                                    │            [physics residuals]       ║
║                                    │                    │                 ║
║                                    └──────┬─────────────┘                 ║
║                                           ▼                               ║
║                            [EWMA + Mahalanobis + small AE]                ║
║                                           │                               ║
║                    ┌──────────────────────┼──────────────────┐            ║
║                    ▼                      ▼                  ▼            ║
║           [full-rate log]        [event generator]   [local advisory]     ║
║            stays aboard                   │                               ║
║                                           ▼                               ║
║                                 [telemetry encoder]                       ║
╚═══════════════════════════════════════════╤═══════════════════════════════╝
                                            ▼
                    ✅ ~25 kbit/s · ~1.2 s · 2% loss · outages
╔═══════════════════════════════════════════╤═══════════════════════════════╗
║  GROUND CONTROL STATION                   ▼                               ║
║                              [adapter → canonical schema]                 ║
║                                           │                               ║
║                              [time align · gap marking]                   ║
║                                           │                               ║
║                    ┌──────────────────────┼──────────────────┐            ║
║                    ▼                      ▼                  ▼            ║
║           [TimescaleDB hot]      ★ TWIN CORE ★        [Parquet cold]      ║
║                                  physics · residuals                      ║
║                                  Kalman · staleness                       ║
║                                  degradation history                      ║
║                                           │                               ║
║        ┌────────────┬─────────────────────┼───────────┬──────────────┐    ║
║        ▼            ▼                     ▼           ▼              ▼    ║
║   [anomaly     [fault             [health       [RUL +         [mission   ║
║    ensemble]    classifier]        indices]      interval]      sim]      ║
║        │            │                     │           │              │    ║
║        └────────────┴──────────┬──────────┴───────────┴──────────────┘    ║
║                                ▼                                          ║
║                      [FastAPI + WebSocket]                                ║
║                                │                                          ║
║                                ▼                                          ║
║          [React dashboard · charts · 3D · alerts · advisory · replay]     ║
╚═══════════════════════════════════════════════════════════════════════════╝
                                            │
                                            ▼
                    [OFFLINE: retraining · fleet trending · baselines]
                     ⬜ ground only, between sorties, human in the loop
```

---

## 22.3 Component specifications

### Sensors and data sources

| Item | Specification |
|---|---|
| Scalar channels | ~30 at 20 Hz — 8 PS groups plus flight context |
| Vibration | 1 accelerometer, 10 kHz, ±50 g, anti-alias filtered, tach-synchronised |
| Crank/tach | Required for order tracking — ✅ must be acquired synchronously |
| Redundancy | ✅ Dual ECU lane where available, for divergence-based sensor validation |

### Data formats

| Interface | Format |
|---|---|
| Onboard bus | ✅ CAN 2.0A/B, ⬜ our DBC, 500 kbit/s |
| Internal canonical | `TelemetryRecord` — onboard timestamp, values, validity, source, sequence |
| Downlink | ✅ MAVLink-style: magic, length, flags, seq, sysid, compid, msgid, payload, CRC |
| Hot storage | TimescaleDB hypertables |
| Cold storage | Parquet, columnar |

### Communication assumptions ⬜

| Parameter | Value |
|---|---|
| Bandwidth | 25 kbit/s allocation (✅ within a ~122 kbit/s Ku C2 link) |
| Latency | 1,200 ms ± 200 ms jitter |
| Packet loss | 2% nominal, configurable to 20% |
| Outages | Scheduled, for demonstration |
| Protocol posture | ✅ STANAG 4586 LOI 2 semantics; MAVLink on the wire |

---

## 22.4 The model stack

| Stage | Model | Input | Output | Where |
|---|---|---|---|---|
| Sensor validity | Rule-based | Raw values | Valid/invalid flags | Edge |
| Physics | Thermodynamic | Measured + context | Expected values | Edge + GCS |
| Residual | Subtraction | Measured − expected | Residual vector | Edge + GCS |
| Vibration features | DSP | 10 kHz waveform | ~40 features | **Edge** |
| Anomaly (edge) | EWMA + Mahalanobis + quantised AE | Residuals + features | Score | **Edge** |
| Anomaly (GCS) | Ensemble + PCA + IsoForest + AE | Residuals + features | Fused score + attribution | GCS |
| Classification | Random Forest | Residuals + features | Label + confidence + evidence | GCS |
| Health index | Weighted composite | Residuals + features | 0–100 per subsystem | Both |
| RUL | Extrapolation → particle filter | Health history | Hours + interval | GCS |
| Advisory | Rules + RAG | Fault + RUL + context | Recommended action | GCS |

⬜ **Optional research component** ([Part XX](20_novelty_and_research.md)): an expand-and-sparsify novelty detector on **spectrum-level** input, as an ensemble member, benchmarked against the quantised autoencoder. Adopted only if it wins on detection at equal false-alarm rate, or on cost/latency. A documented negative result is an acceptable outcome.

---

## 22.5 Evaluation commitments

| Task | Primary metric | Secondary |
|---|---|---|
| Anomaly detection | **False alarms per flight hour** | Detection latency distribution, missed-detection rate per fault |
| Classification | **Macro F1** | Per-class recall, confusion matrix, UNKNOWN rate |
| RUL | ✅ **Prognostic horizon** | RMSE, MAE, ✅ asymmetric score, interval coverage |
| System | **Edge availability under outage** | Latency, bandwidth used, replay determinism |

**Splitting:** by simulated airframe, with unseen degradation rates and environments in test. Never by row.

**Benchmarks reported alongside:** ✅ C-MAPSS, Paderborn, XJTU-SY, SKAB.

---

## 22.6 Real / simulated / assumed / public / proprietary

This table is the one to have ready when questioned.

### ✅ Real

- SocketCAN kernel interface and the CAN toolchain
- MAVLink framing, sequence numbers, CRC
- All algorithms — DSP, statistical, ML
- Public benchmark datasets and their published results
- The dashboard, 3D rendering, replay software
- The bandwidth arithmetic — ✅ ~160 kbit/s raw vs ✅ ~122 kbit/s link
- Standards facts: ✅ STANAG 4586 LOI definitions, CAN frame structure, Ku-band allocations

### ⬜ Simulated

- Engine telemetry (our physics generator)
- Vibration waveforms (synthesised with correct spectral structure)
- The radio link (impairments modelled with ✅ realistic parameters)
- Degradation and all 8 fault modes
- The airframe and the mission

### ⬜ Assumed (our design choices, not PS requirements)

- Rotax 912 iS as reference engine
- 20 Hz telemetry rate, 10 kHz vibration
- 25 kbit/s telemetry budget
- CAN frame layout (our own DBC)
- Health-index definition and failure thresholds
- Pi-class edge hardware
- Ground-only model adaptation
- STANAG LOI-2 advisory-only scope

### ✅ Publicly documented

- Rotax operator's manuals, EASA TCDS
- ✅ 912/915 iS CAN parameter list: RPM, MAP, oil P/T, coolant temp, EGT ×4, ECU voltage, engine hours
- ✅ Dual ECU lanes using CAN Aerospace, with lane failover
- ✅ TAPAS-BH-201 performance figures; DEAL developed the datalink; BLOS demonstrated June 2023
- ✅ STANAG 4586, MAVLink, CAN, ARINC 429, MIL-STD-1553 specifications
- All benchmark datasets and PHM literature cited

### 🔒 Proprietary or unknown

- **Rotax CAN ID-to-signal mapping** — 🔒 not public; community requests go unanswered
- **DRDO datalink specifics** — waveform, frequencies, encryption, message set
- **TAPAS onboard bus architecture**
- **Any real engine run-to-failure data**
- Detailed manufacturer performance maps

> **The rule:** never fabricate anything in the 🔒 list. Saying "that is proprietary, so we designed against an abstraction that accepts it when available" is a strong engineering answer. A fabricated CAN ID is an unforced error that a knowledgeable evaluator may catch.

---

## 22.7 What to build first

⬜ If you have one week:

1. **Days 1–2:** Phase 1 — generator → vcan0 → UDP link with impairments → GCS → plot. Include the impairment simulator from the start.
2. **Days 3–4:** Phase 2 — physics model and residuals. **Gate: healthy residuals ≈ 0 in every regime.**
3. **Day 5:** Phase 4 — EWMA + Mahalanobis anomaly detection on residuals. Measure false alarms per hour.
4. **Day 6:** Phase 5 — inject 3–4 faults, Random Forest classification, evidence trail.
5. **Day 7:** Dashboard showing live health, residuals, alerts, and the link-loss degradation behaviour.

That is a coherent, honest, demonstrable system. Vibration (Phase 3), RUL (Phase 6) and mission simulation (Phase 8) extend it — and vibration is the highest-value extension, because ✅ three of the eight PS faults depend on it and most teams will not attempt it.

---

## 22.8 The five things that make this defensible

1. **The bandwidth argument is arithmetic, not opinion.** ✅ One accelerometer exceeds the whole link. Everything about the edge architecture follows from that, and it can be verified on a whiteboard.

2. **Physics residuals make detection regime-independent.** The system works the same at sea level and at 25,000 ft because the expectation already accounts for both — ✅ which is what "physics-informed" actually means.

3. **It keeps working when jammed.** Demonstrable by unplugging a cable. ✅ A ground-only architecture cannot do this, and this is a defence application.

4. **Every claim is labelled.** ✅ verified, 🔶 inferred, ⬜ assumed, 🔒 proprietary. This survives hostile questioning in a way confident assertion does not.

5. **The evaluation is honest.** Split by airframe, false alarms per flight hour, prognostic horizon, public benchmarks alongside synthetic results, limitations stated first. 🔶 In a field where ✅ 97%+ lab accuracies are routine and largely artefactual, being the team that explains why is itself distinguishing.

---

## 22.9 The closing position

> "We built a bandwidth-driven PHM architecture for aero piston engines. High-rate vibration is analysed onboard because it physically cannot be downlinked — one accelerometer exceeds the entire control link. A thermodynamic model turns raw telemetry into regime-independent residuals, so the same detector works at sea level and at 25,000 ft. The system keeps monitoring when the link is jammed. The algorithms are established ones, applied under constraints and to a machine class where we did not find prior published work. We validate methods on public benchmarks and integration on physics-based simulation, and we label every claim as verified, inferred, or assumed — because no public run-to-failure dataset exists for this engine class, and pretending otherwise would not survive the first serious question."

---

**Next:** [Part XXIII — Glossary](23_glossary.md)
