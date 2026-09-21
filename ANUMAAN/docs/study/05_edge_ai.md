# Part V — Edge AI and Onboard Analytics

*Why "Edge AI" appears in the PS, what it actually solves, and how small a useful model can be.*

---

## 5.1 The five processing levels

Every computation in this system happens at exactly one of five places. Assigning them correctly is most of the architecture.

```
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 1 — SENSOR / ECU                                                 │
│ Where: on the engine                                                   │
│ Compute: fixed-function, microseconds                                  │
│ Does: transduction, conditioning, ADC, calibration, CAN publishing     │
│ We control: ❌ nothing. This is vendor firmware                        │
└────────────────────────────────────────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 2 — FLIGHT / ONBOARD COMPUTER                                    │
│ Where: in the airframe                                                 │
│ Compute: deterministic, single-digit ms, hard real-time                │
│ Does: CAN ingest, validity checks, time alignment, logging,            │
│       physics residuals, threshold safety nets                         │
│ We control: ✅ fully. MUST work with the datalink dead                 │
└────────────────────────────────────────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 3 — EDGE AI MODULE                                               │
│ Where: same box or a co-processor                                      │
│ Compute: 10–100 ms, soft real-time                                     │
│ Does: vibration feature extraction, anomaly scoring, event generation, │
│       telemetry prioritisation                                         │
│ We control: ✅ fully. THE BANDWIDTH REDUCER                            │
└────────────────────────────────────────────────────────────────────────┘
                     ▼ ~25 kbit/s, ~1.5 s latency, lossy
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 4 — GROUND CONTROL STATION                                       │
│ Where: the ground station                                              │
│ Compute: seconds, plenty of CPU/GPU, interactive                       │
│ Does: digital twin state, fault classification, RUL, mission sim,      │
│       RAG/advisory, dashboard, replay                                  │
│ We control: ✅ fully. This is where most of our project lives          │
└────────────────────────────────────────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 5 — OFFLINE / DEPOT                                              │
│ Where: maintenance server, after the flight                            │
│ Compute: unbounded — hours or days                                     │
│ Does: model retraining, fleet trending, per-airframe baselines,        │
│       deep post-flight analysis on the FULL onboard log                │
│ We control: ✅ fully. NEVER in the flight loop                         │
└────────────────────────────────────────────────────────────────────────┘
```

**The allocation rule:** a function belongs at the *highest-numbered level that can still meet its deadline and data needs*. Ground compute is cheap and unconstrained; onboard compute is expensive in power, weight and certification burden. So push work to the ground — **unless** it needs data that cannot cross the link, or must act faster than the link allows, or must survive link loss.

Exactly three categories fail that test and must stay onboard:

1. **Anything consuming high-rate data** (vibration) — it cannot be transmitted.
2. **Anything needing sub-second reaction** — the link adds ~1.5 s.
3. **Anything that must work when jammed** — the link may be gone entirely.

---

## 5.2 The five problems edge AI actually solves

### Problem 1 — Bandwidth

From [Part II](02_engine_sensors.md) and [Part IV](04_telemetry_and_comms.md): one raw accelerometer at 10 kHz is ~160 kbit/s; the entire Ku C2 link is ✅ ~122 kbit/s or less.

Edge processing is a **data reduction engine**:

```
10,000 samples/s  ──[FFT, order analysis, statistics]──▶  ~40 floats/s

160 kbit/s  ──────────── ~4,000× reduction ────────────▶  ~1.3 kbit/s
```

🔶 **INFERENCE** — this ratio is what makes vibration monitoring possible at all on a UAV. Without it, vibration simply cannot participate in ground-based health monitoring.

### Problem 2 — Latency

✅ SATCOM adds ~1–1.5 s each way. A protective response — derate, switch ECU lane, alert the autopilot — that must occur within a second cannot be decided on the ground. It must be onboard.

### Problem 3 — Intermittent connectivity and loss

Links drop: terrain masking, antenna pointing during manoeuvres, weather, handover. ✅ Bandwidth can degrade severely due to weather, geography or jamming.

If the health monitor lives entirely on the ground, then **the aircraft is unmonitored precisely when it is most stressed** — often during the same manoeuvres that break the link. An onboard detector keeps working and buffers its findings.

### Problem 4 — Jamming and contested environments

🔶 **INFERENCE** — for a defence UAV, the link must be assumed to be deniable. A system whose safety function depends on the link having a single point of failure that an adversary controls. Onboard autonomy removes it.

### Problem 5 — Autonomy

The natural endpoint: if the aircraft can detect its own engine degradation, it can make degraded-mode decisions (reduce power, abort to a recovery point) without waiting for an operator who may be unreachable. ⬜ Out of scope for our prototype to *act*, but the architecture should not preclude it.

---

## 5.3 Why a small model can be enough

The instinct is that a small model is a worse model. For this specific job, that is not so, for two structural reasons.

**The edge job is easier than the ground job.** The edge only has to answer *"is this different from normal?"* — a one-class problem, learnable from healthy data alone, of which you have abundant quantities. Naming the fault and predicting time-to-failure are much harder problems requiring labelled faults and run-to-failure trajectories, and they belong on the ground where you have the compute and the fleet history.

**The features do the heavy lifting.** After proper order analysis and envelope processing ([Part VI](06_vibration_analysis.md)), a bearing fault is often plainly visible as elevated energy in a specific band. The classifier's job on top of good features is comparatively trivial. **Most of the intelligence in vibration monitoring is in the signal processing, not the model.**

✅ Published edge results support this. A quantised TinyML model achieved an F1 of approximately 0.92 with a 3× smaller memory footprint and 60% lower energy consumption; an edge-based anomaly detection system reported 86% accuracy, 86% recall, 87% precision. ([Edge AI / TinyML sources](https://www.sciencedirect.com/science/article/pii/S2666827025001380), [STM32 vibration anomaly detection](https://github.com/Shafqat-16/stm32-edge-ai-vibration-anomaly-detection))

⚠️ **Caveat** — those are different machines and different datasets. They demonstrate *feasibility of the approach class*, not the accuracy we would get on an aero piston engine. See [Part VIII §8.6](08_fault_diagnosis.md) on why benchmark numbers do not transfer.

---

## 5.4 TinyML techniques

### Quantisation

Floating-point weights (32-bit) are converted to 8-bit integers.

```
float32:  0.0271828  →  int8: 7   (with a scale factor per tensor)
```

Gains: 4× smaller, integer arithmetic (much faster on a CPU without an FPU, and far lower energy), better cache behaviour. Cost: a small accuracy loss, usually under a percent for well-behaved models, and recoverable with quantisation-aware training.

✅ Real pipelines use exactly this — an int8-quantised MLP is a standard component of production TinyML vibration pipelines. ([STM32 pipeline](https://github.com/Shafqat-16/stm32-edge-ai-vibration-anomaly-detection))

### Pruning

Remove weights near zero. Networks are typically heavily over-parameterised; 50–90% of weights can often be removed with modest accuracy loss. Combined with quantisation this compounds.

### Feature-first design

The biggest win is not a model technique at all. Feeding a model 40 well-chosen features instead of a 2,048-sample raw window shrinks the input by ~50× and lets a tiny model succeed where a large one would otherwise be needed. **Spend your effort on [Part VI](06_vibration_analysis.md), not on model architecture.**

---

## 5.5 Hardware options

✅ **VERIFIED** figures:

| Platform | Power | AI capability | Notes |
|---|---|---|---|
| **Jetson Orin Nano** | ~5 W idle, 8–12 W inference, up to ~25 W peak (MAXN) | Up to 40 TOPS INT8; series up to 67 TOPS | 1024 CUDA cores + tensor cores. Fastest and most energy-efficient of the compared options |
| **Raspberry Pi 5 / CM-class** | ~3–5 W | No ML-oriented GPU acceleration | VideoCore GPU "never designed for machine learning workloads" |
| **STM32 / ESP32 class MCU** | milliwatts | int8 MLP after DSP | Proven for FFT + quantised MLP vibration pipelines |

([Jetson vs Pi comparisons](https://thinkrobotics.com/blogs/learn/nvidia-jetson-orin-nano-vs-raspberry-pi-5-the-ultimate-edge-computing-showdown), [Jetson power consumption](https://edgeaistack.ai/blog/jetson-orin-nano-power-consumption/), [STM32 pipeline](https://github.com/Shafqat-16/stm32-edge-ai-vibration-anomaly-detection))

⬜ **Our recommendation:**

- **Development/demo:** a Raspberry Pi 5 or CM4 is entirely sufficient. Our edge workload is FFT plus a small model — it does not need a GPU, and saying so honestly is better engineering than specifying a Jetson to sound impressive.
- **If we add CNN-on-spectrogram inference:** then a Jetson Orin Nano becomes justified.
- **A real airborne unit** would face DO-178C/DO-254-class certification questions that are entirely out of our scope. 🔶 Worth acknowledging in the presentation; do not pretend our Pi is flight-certified.

**The honest framing:** "our edge workload is a few FFTs and a sub-100 kB model per second, which a Pi-class board handles comfortably; a Jetson would only be needed if we moved CNN inference onboard."

---

## 5.6 What runs onboard in our design

⬜ **ASSUMPTION** — our proposed edge workload, with 🔶 estimated budgets:

| Function | Rate | Est. cost | Why onboard |
|---|---|---|---|
| CAN ingest + decode | 20 Hz | negligible | Source of data |
| Validity / plausibility checks | 20 Hz | negligible | Must catch sensor faults before they propagate |
| Vibration acquisition | 2–10 kHz | DMA, negligible CPU | Cannot be transmitted |
| Windowing + FFT | ~10 Hz (windows/s) | ~1 ms per 2048-pt FFT | Cannot be transmitted |
| Order analysis + features | ~10 Hz | ~1 ms | The 4,000× reduction step |
| Physics residuals | 20 Hz | <1 ms | Needed by the edge detector |
| Edge anomaly score | 20 Hz | <1 ms | Must survive link loss |
| Event generation | on trigger | negligible | Prioritises scarce bandwidth |
| Full-rate logging | continuous | I/O bound | Post-flight truth |
| Telemetry encode | 20 Hz | negligible | Output |

🔶 Total: a few percent of one core on a Pi-class board. **The edge layer is not computationally demanding. It is architecturally essential.** Those are different things, and conflating them leads to over-specified hardware.

---

## 5.7 Event-driven telemetry — using scarce bandwidth well

A fixed-rate stream wastes bandwidth when nothing is happening and starves you when something is. ⬜ A better pattern:

| Tier | Contents | Rate |
|---|---|---|
| **Continuous** | Core scalars, health indices | 20 Hz (or lower in cruise) |
| **Periodic** | Vibration feature vector | 1 Hz |
| **On event** | Anomaly detected, threshold crossed, state change | As it happens, high priority |
| **On request** | A burst of detailed data around an event | Operator-initiated |
| **Never** | Raw waveforms, full logs | Recovered after landing |

**The "on request" tier is the elegant part.** The edge detects something, sends a compact event, and the operator can then ask for a detailed snapshot around that timestamp — spending bandwidth *only* on the moment that turned out to matter. 🔶 This mirrors how bandwidth-constrained systems generally work, and it demos extremely well.

---

## 5.8 The federated learning angle

✅ **VERIFIED** — "Federated learning approaches" is explicitly listed in the PS's §5 Desired Innovation Areas. It is encouraged, not required.

✅ There is solid published work applying federated learning to aircraft-engine RUL: it lets multiple operators train a collective prognostic model without centrally sharing data, with reported accuracy matching or exceeding centralised deep learning while raw sensor data never leaves the local device. Motivations include commercial data sensitivity and the scarcity of run-to-failure samples at any single operator. ([Federated RUL framework](https://www.sciencedirect.com/science/article/pii/S0167739X25002407), [Federated ML in jet engine PdM](https://arxiv.org/pdf/2502.05321), [Personalised FL for industrial analytics](https://arxiv.org/pdf/2604.19451))

🔶 **INFERENCE — why this fits a defence context particularly well.** Run-to-failure data for a specific military engine type is scarce and classified. Federated learning is a natural answer: each base trains locally, only model updates are shared, raw telemetry never leaves the unit.

⬜ **Our position, and a deliberate safety stance:** adaptation should happen **on the ground, between sorties, from confirmed-healthy flights only.** The in-flight model stays frozen.

🔶 **INFERENCE** — the reasoning: a model that changes its own behaviour in flight is extremely difficult to certify or to reason about after an incident. Airworthiness authorities are cautious about non-deterministic in-flight behaviour. I did not find a specific source for CEMILAC's position, so treat this as engineering judgment, not a cited requirement — but it is the defensible default, and stating it shows maturity.

---

## 5.9 Summary

| Question | Answer |
|---|---|
| Why does the PS list Edge AI? | Because link bandwidth makes vibration monitoring impossible otherwise ✅ |
| What must run onboard? | Anything using high-rate data, needing sub-second response, or surviving link loss |
| Is a small model enough? | For *detection*, yes — it is a one-class problem and the features carry the load |
| What hardware? | ⬜ Pi-class is honestly sufficient for our workload; Jetson only if CNNs move onboard |
| Where does the heavy AI live? | Level 4 (GCS) — classification, RUL, simulation, advisory |
| Where does training live? | Level 5 (offline), never in flight ⬜ |

---

**Next:** [Part VI — Vibration Analysis from Zero](06_vibration_analysis.md)
