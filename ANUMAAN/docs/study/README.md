# ANUMAAN Study & System Design Course
**A ground-up technical course on UAV aero-piston-engine PHM, and the architecture we should build for DRDO SIH PS-26054.**

---

## Who this is for

Someone competent in Python and AI, but new to aerospace, avionics, engine telemetry, vibration analysis, and prognostics. Every part starts from first principles, defines its jargon, and then connects forward into the system we are designing.

## How this document is organised

Read in order. Each part assumes the previous ones. Parts I–VI build the physical and data foundations. Parts VII–XI build the intelligence. Parts XII–XXIII turn it into an implementable system.

| # | File | What it teaches |
|---|---|---|
| I | [01_big_picture.md](01_big_picture.md) | Why this problem exists, the whole system in one view |
| II | [02_engine_sensors.md](02_engine_sensors.md) | Every engine parameter: sensor, signal type, rate, faults it reveals |
| III | [03_ecu_can_acquisition.md](03_ecu_can_acquisition.md) | CAN bus from zero, ECU data paths, SocketCAN, Rotax reality |
| IV | [04_telemetry_and_comms.md](04_telemetry_and_comms.md) | LOS/BLOS, C-band, Ku SATCOM, STANAG 4586, MAVLink, bridging |
| V | [05_edge_ai.md](05_edge_ai.md) | Why compute must be split, TinyML, quantisation, the 5 levels |
| VI | [06_vibration_analysis.md](06_vibration_analysis.md) | Sampling → Nyquist → FFT → orders → envelope → features |
| VII | [07_anomaly_detection.md](07_anomaly_detection.md) | Control charts to autoencoders, and where each belongs |
| VIII | [08_fault_diagnosis.md](08_fault_diagnosis.md) | Classification methods, benchmark numbers and why they mislead |
| IX | [09_rul_prognostics.md](09_rul_prognostics.md) | RUL from first principles, LSTM→Transformer→GNN, uncertainty |
| X | [10_digital_twin.md](10_digital_twin.md) | Shadow vs twin, what makes ours real, state estimation |
| XI | [11_mission_simulation.md](11_mission_simulation.md) | Flight/environment/mission parameters and what-if simulation |
| XII | [12_data_pipeline.md](12_data_pipeline.md) | Every stage: input, output, format, rate, latency, failure modes |
| XIII | [13_edge_vs_ground_split.md](13_edge_vs_ground_split.md) | The compute-split table and its reasoning |
| XIV | [14_datasets.md](14_datasets.md) | Real datasets, proxies, and what each can honestly be used for |
| XV | [15_system_architecture.md](15_system_architecture.md) | The layered architecture we should build |
| XVI | [16_tech_stack.md](16_tech_stack.md) | Technology choices, each argued for and against |
| XVII | [17_simulation_design.md](17_simulation_design.md) | How to build a physically honest synthetic telemetry generator |
| XVIII | [18_roadmap.md](18_roadmap.md) | Phase 1→10, each with deliverable, dataset, model, metric |
| XIX | [19_evaluation.md](19_evaluation.md) | PHM metrics, asymmetric RUL scoring, why late is worse |
| XX | [20_novelty_and_research.md](20_novelty_and_research.md) | The bio-inspired idea, assessed honestly against literature |
| XXI | [21_end_to_end_scenario.md](21_end_to_end_scenario.md) | One full mission, with the actual data at every stage |
| XXII | [22_final_recommendation.md](22_final_recommendation.md) | What to build, and what is real vs simulated vs assumed |
| XXIII | [23_glossary.md](23_glossary.md) | Every acronym and term |

Related: the datasets themselves are catalogued in [`Datasets/`](../../../Datasets/README.md) at the repository root.

---

## Evidence labels — read this before anything else

Aerospace work fails when a guess gets quoted as a fact. Every non-obvious claim in these documents carries one of four labels:

| Label | Meaning |
|---|---|
| ✅ **VERIFIED** | Traceable to a cited public source (standard, manual, peer-reviewed paper, official documentation) |
| 🔶 **INFERENCE** | Engineering reasoning from verified facts. Plausible, but not directly sourced |
| ⬜ **ASSUMPTION** | A design choice we made for the prototype. Not required by the PS, not claimed to be what DRDO does |
| 🔒 **PROPRIETARY** | Genuinely not public. Do not guess it, and do not present a guess as fact |

**The single most important rule in this whole course:** DRDO does not publish the internals of TAPAS-BH-201's engine bus, its datalink waveform, or its health-monitoring parameter list. Anything we say about those is 🔶 or ⬜, never ✅. A judge who knows the domain will immediately spot a fabricated claim, and it destroys credibility for everything else you said.

---

## The mental model — the whole system in one picture

```
   ┌──────────────────────────────────────────────────────────────────────┐
   │                      ONBOARD THE UAV (airborne)                      │
   │                                                                      │
   │   ENGINE            The physical 4-cylinder aero piston engine       │
   │     │               Burns fuel, makes heat, vibration, torque        │
   │     ▼                                                                │
   │   SENSORS           Thermocouples, RTDs, pressure transducers,       │
   │     │               Hall/pulse pickups, accelerometers               │
   │     │               → analog volts / resistance / pulse trains       │
   │     ▼                                                                │
   │   ECU / DAQ         Digitises, linearises, applies calibration       │
   │     │               → engineering-unit numbers                       │
   │     ▼                                                                │
   │   CAN BUS           Numbers travel as CAN frames at 10–50 Hz         │
   │     │               (+ a separate high-rate vibration channel)       │
   │     ▼                                                                │
   │   EDGE PREPROCESS   Validity checks, unit conversion, time align     │
   │     │                                                                │
   │     ▼                                                                │
   │   FEATURE EXTRACT   Vibration → orders, RMS, kurtosis, band energy   │
   │     │               THIS is where kHz data is reduced to numbers     │
   │     ▼                                                                │
   │   EDGE DETECTOR     Small, cheap anomaly model. Runs even when the   │
   │     │               datalink is dead. Emits a health score + events  │
   │     ▼                                                                │
   │   TELEMETRY ENCODER Packs scalars + features + events into frames    │
   │     │               Full-rate raw data stays onboard in a log        │
   └─────┼────────────────────────────────────────────────────────────────┘
         │
         ▼   ~kbps, lossy, jammable, ~1–1.5 s latency on SATCOM
   ╔═════════════════════════════════════════════════════════════════════╗
   ║   RF DATALINK      C-band line-of-sight  /  Ku-band SATCOM beyond   ║
   ╚═════╤═══════════════════════════════════════════════════════════════╝
         │
   ┌─────┼────────────────────────────────────────────────────────────────┐
   │     ▼                GROUND CONTROL STATION                          │
   │   INGESTION         Decode frames, CRC check, timestamp, reorder     │
   │     │                                                                │
   │     ▼                                                                │
   │   VALIDATION        Range, rate-of-change, cross-sensor plausibility │
   │     │               Separates a broken SENSOR from a broken ENGINE   │
   │     ▼                                                                │
   │   DIGITAL TWIN      Physics model computes what SHOULD be happening. │
   │     │               Residual = actual − expected. THIS is the twin.  │
   │     ▼                                                                │
   │   ANOMALY DETECT    "Something is off"  (unsupervised, no fault name)│
   │     │                                                                │
   │     ▼                                                                │
   │   FAULT CLASSIFY    "It is specifically an injector fault"  (named)  │
   │     │                                                                │
   │     ▼                                                                │
   │   RUL / PROGNOSIS   "≈3.4 flight hours left, 80% CI [2.1, 5.0]"      │
   │     │                                                                │
   │     ▼                                                                │
   │   MISSION SIM       "An 18 h sortie exceeds that. Recommend NO-GO."  │
   │     │                                                                │
   │     ▼                                                                │
   │   DASHBOARD         Operator sees health, alerts, advisory, replay   │
   └─────┼────────────────────────────────────────────────────────────────┘
         │
         ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │   OFFLINE / DEPOT   Full onboard logs recovered after landing.       │
   │                     Model retraining, fleet trending, per-airframe   │
   │                     baselines. Never in flight.                      │
   └──────────────────────────────────────────────────────────────────────┘
```

### The four sentences that explain the whole design

1. **Signals become numbers early.** By the time anything reaches the ground it is already digital scalars, not waveforms. The analog world ends at the ECU.
2. **Bandwidth is the binding constraint.** The link carries kilobits, not megabits. Anything high-rate must be reduced onboard or it never leaves the aircraft.
3. **Residuals, not raw values, carry the signal.** 130 °C CHT is fine at sea level and alarming at altitude in cold air. The twin's job is to know the difference.
4. **Detection, diagnosis and prognosis are three different problems** of increasing difficulty, and they need different models, different data, and different evaluation metrics.

---

*Part of the ANUMAAN documentation suite. The official problem statement is in [00_official_problem_statement.md](../00_official_problem_statement.md); the team's plain-language reading of it is in [01_problem_statement_breakdown.md](../01_problem_statement_breakdown.md).*
