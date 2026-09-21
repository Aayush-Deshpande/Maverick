# Part XII — The Complete Data Pipeline

*Every stage: input, output, format, rate, latency, computation, storage, failure modes, and behaviour under link loss.*

---

## 12.1 The full pipeline

```
 [1] PHYSICAL ENGINE
      │  heat, pressure, rotation, vibration
      ▼
 [2] SENSORS
      │  mV, Ω, mA, pulses, AC waveform
      ▼
 [3] SIGNAL CONDITIONING + ADC
      │  digital counts
      ▼
 [4] ECU / DAQ
      │  engineering units
      ▼
 [5] CAN BUS  ───────────────────── [5b] VIBRATION DAQ (separate, 2–10 kHz)
      │  frames @10–50 Hz                 │  raw waveform
      ▼                                   │
 [6] FLIGHT COMPUTER  ◀──────────────────┘
      │
      ├─▶ [7]  VALIDATION           → validity flags
      ├─▶ [8]  TIME SYNC            → common timebase
      ├─▶ [9]  FEATURE EXTRACTION   → ~40 vibration features/s
      ├─▶ [10] PHYSICS RESIDUALS    → regime-independent deltas
      ├─▶ [11] EDGE ANOMALY         → health score, events
      ├─▶ [12] ONBOARD LOG          → full rate, stays aboard
      └─▶ [13] TELEMETRY ENCODER    → downlink frames
                   │
                   ▼
 [14] RF / SATCOM DATALINK  ~25 kbit/s, ~1.5 s, lossy
                   │
                   ▼
 [15] GCS INGESTION           → decoded frames
 [16] TIME ALIGNMENT + GAPS   → ordered, gap-marked series
 [17] VALIDATION (again)      → transport-level integrity
 [18] STORAGE                 → time-series DB
 [19] TWIN STATE UPDATE       → authoritative state object
 [20] ANOMALY DETECTION       → score
 [21] FAULT CLASSIFICATION    → label + evidence
 [22] RUL ESTIMATION          → hours + interval
 [23] MISSION SIMULATION      → go/no-go
 [24] DASHBOARD + ALERTS      → operator
 [25] REPLAY STORE            → post-flight
                   │
                   ▼
 [26] OFFLINE / DEPOT         → retraining, fleet trending
```

---

## 12.2 Stage-by-stage specification

⬜ Rates and latencies are our design assumptions unless marked ✅.

### Onboard stages

| # | Stage | Input | Output | Format | Rate | Latency | Failure mode | On link loss |
|---|---|---|---|---|---|---|---|---|
| 1 | Engine | — | Physical quantities | — | continuous | — | The thing we monitor | Unaffected |
| 2 | Sensors | Physical | Electrical | mV/Ω/mA/pulse/AC | continuous | µs | Drift, open circuit, detachment | Unaffected |
| 3 | Conditioning + ADC | Electrical | Digital counts | int12–16 | fs | µs | **Aliasing if no AA filter**, saturation | Unaffected |
| 4 | ECU / DAQ | Counts | Engineering units | float | 10–50 Hz | <1 ms | Lane failure, firmware fault | Unaffected |
| 5 | CAN bus | ECU values | CAN frames | ≤8 data bytes ✅ | 10–50 Hz | <1 ms | Bus-off, wiring, termination | Unaffected |
| 5b | Vibration DAQ | Accelerometer | Raw waveform | int16 array | 2–10 kHz | — | Aliasing, mount loosening | Unaffected |
| 6 | Flight computer | CAN + vib + flight data | Unified records | struct | 20 Hz | ~1 ms | Reboot, overload | **Keeps running** |
| 7 | Validation | Raw records | Records + validity flags | struct+flags | 20 Hz | <1 ms | False rejection of good data | Keeps running |
| 8 | Time sync | Multi-source records | Aligned records | struct | 20 Hz | ~1 frame | Clock drift between domains | Keeps running |
| 9 | Feature extraction | Vibration windows | ~40 features | float array | ~1–10 Hz | ~10 ms | Speed change during window | Keeps running |
| 10 | Physics residuals | Measured + context | Residual vector | float array | 20 Hz | <1 ms | **Model error mimics fault** | Keeps running |
| 11 | Edge anomaly | Residuals + features | Score + events | float + msgs | 20 Hz | <1 ms | False alarms | **Keeps running — the point** |
| 12 | Onboard log | Everything | Log file | Parquet/binary | full rate | — | Storage full, corruption | **Keeps recording** |
| 13 | Telemetry encoder | Selected values | Frames | MAVLink-style | 20 Hz | <1 ms | Encoding error | Buffers for later |

### Ground stages

| # | Stage | Input | Output | Format | Rate | Latency | Failure mode | On link loss |
|---|---|---|---|---|---|---|---|---|
| 14 | Datalink | Frames | Frames | RF | ~25 kbit/s ⬜ | ✅ ~1–1.5 s | Loss, jamming, weather | **This is the failure** |
| 15 | Ingestion | RF frames | Decoded records | struct | 20 Hz | ~1 ms | CRC fail, version mismatch | Nothing arrives |
| 16 | Time align + gaps | Records | Ordered series + gap markers | time series | 20 Hz | buffered | Reordering, duplicates | Marks gap explicitly |
| 17 | Validation | Series | Validated series | series+flags | 20 Hz | <1 ms | — | — |
| 18 | Storage | Series | Persisted rows | TimescaleDB/Parquet | 20 Hz | ~ms | Disk, write contention | Nothing to store |
| 19 | Twin update | Series + context | Twin state | state object | 20 Hz | ~1 ms | Model divergence | **Shows STALE, widening σ** |
| 20 | Anomaly detection | Twin state | Score | float | 20 Hz | ~1 ms | Threshold mis-set | Suspended |
| 21 | Fault classification | Flagged windows | Label + evidence | struct | on event | ~10 ms | Misclassification | Suspended |
| 22 | RUL | Health history | Hours + interval | struct | ~1/min | ~100 ms | Trend extrapolation error | Frozen, marked stale |
| 23 | Mission sim | Twin + profile | Trajectory + verdict | struct | on demand | ~1 s | Model error | Uses last known state |
| 24 | Dashboard | All outputs | UI | WebSocket/JSON | 1–10 Hz | ~ms | — | **Shows degraded status** |
| 25 | Replay store | All | Indexed archive | Parquet + index | continuous | — | Storage growth | Nothing to add |
| 26 | Offline | Full logs | Retrained models | model artefacts | per flight | hours | Data leakage in splits | Unaffected |

---

## 12.3 The three critical rate boundaries

```
 kHz DOMAIN            │  Hz DOMAIN              │  MINUTE DOMAIN
 2–10 kHz              │  10–50 Hz               │  0.01–1 Hz
 ───────────────────────────────────────────────────────────────
 Vibration waveform    │  Engine scalars         │  RUL, trends
 MUST stay onboard     │  Downlinked             │  Ground, on demand
 ───────────────────────────────────────────────────────────────
        ▲                       ▲                         ▲
        │                       │                         │
   Stage 9 reduces         Stage 13 selects         Stage 22 aggregates
   4,000× here             what fits here           over hours here
```

**Each boundary is a deliberate reduction**, and each is where information is irreversibly lost. Knowing *what* is lost at each is the difference between a designed system and an accidental one:

- **kHz → Hz:** the waveform is gone; only the chosen features survive. Choose them well ([Part VI](06_vibration_analysis.md)) — you cannot recover a feature you did not extract, except from the onboard log after landing.
- **Hz → downlink:** only selected channels cross. What you did not select, the operator never sees in flight.
- **Hz → minutes:** trends smooth away transients. A brief excursion may vanish from the trend while remaining in the stored series.

---

## 12.4 Time synchronisation

Four independent clock domains feed this system:

| Source | Clock | Typical rate |
|---|---|---|
| Engine ECU / CAN | ECU internal | 10–50 Hz |
| Vibration DAQ | Its own sampling clock | 2–10 kHz |
| Flight computer | System clock, possibly GPS-disciplined | varies |
| GCS | Its own clock | varies |

**Why this is a real problem, not bookkeeping.** Cross-sensor correlation ([Part VII §7.5](07_anomaly_detection.md)) is how we distinguish sensor faults from engine faults. If CHT and EGT are misaligned by 200 ms, their correlation is corrupted and the discrimination degrades. Order tracking ✅ *requires* vibration and tach to be acquired synchronously — a misaligned tach makes angular resampling wrong in a way that silently smears the spectrum.

⬜ **Our approach:**

1. **Timestamp at the earliest possible point** — the onboard computer stamps on receipt, not at the GCS on arrival.
2. **One monotonic master clock onboard**, GPS-disciplined where available.
3. **Hardware-synchronise vibration and tach** — this cannot be fixed in software afterwards.
4. **Carry the onboard timestamp in the telemetry frame** so the GCS orders by *acquisition* time, not arrival time.
5. **Resample to a common 20 Hz grid** at stage 8, with explicit interpolation flags so downstream code knows what was measured and what was filled.

---

## 12.5 Handling gaps and loss

✅ Packet loss is routine on these links, not exceptional.

⬜ Rules, in priority order:

| Rule | Rationale |
|---|---|
| **Mark gaps explicitly.** Never silently interpolate | A model trained on interpolated data learns the interpolator's artefacts |
| **Short gaps (<1 s): interpolate, flagged** | Thermal signals are slow; linear interpolation is physically reasonable |
| **Long gaps (>1 s): do not interpolate** | Mark the region unknown. The twin propagates on the model with widening uncertainty |
| **Never let a gap look like a value** | A frozen display during link loss is actively dangerous |
| **Use sequence numbers to measure loss** | ✅ MAVLink's per-component sequence counter exists for exactly this |
| **Backfill from the onboard buffer when the link returns** | Bandwidth permitting, reconcile the timeline |

**The design principle:** *the system must always know the difference between "the value is X", "the value was X 47 seconds ago", and "we do not know the value".* Conflating these is how monitoring systems mislead operators.

---

## 12.6 Failure modes and responses

| Failure | Detection | Response | Severity |
|---|---|---|---|
| Single sensor fails | Validity checks ([Part VII §7.5](07_anomaly_detection.md)) | Exclude it, degrade affected health indices, alert | Medium |
| ECU lane fails | Lane divergence / dropout | ✅ Switch to remaining lane, alert | Medium |
| CAN bus-off | No frames | Attempt recovery, alert, fall back to available data | High |
| Vibration DAQ fails | No windows / implausible features | Disable vibration-dependent detectors, state reduced capability | Medium |
| Onboard computer reboot | Heartbeat gap | Restart, resume logging, flag discontinuity | High |
| **Datalink lost** | Heartbeat timeout | **Onboard continues; GCS shows STALE; buffer for backfill** | Medium |
| Storage full | Capacity monitor | Ring-buffer the oldest raw data; **never drop event records** | Medium |
| Physics model divergence | Healthy residual bias grows across the fleet | Flag for recalibration, do not report as a fault | High (insidious) |
| GCS down | — | Onboard unaffected; recover from the log after landing | Low for safety |

**The last-but-one is the insidious one.** If the physics model drifts — wrong parameters, an unmodelled installation effect — every engine shows a bias and the system quietly generates false alarms or, worse, desensitises operators. 🔶 Mitigation: continuously monitor the *fleet-wide distribution* of healthy residuals. If it shifts systematically, the model is wrong, not the engines.

---

## 12.7 Storage design

⬜ Three tiers, because the access patterns differ fundamentally:

| Tier | Contents | Format | Retention | Access pattern |
|---|---|---|---|---|
| **Hot** | Current flight, full rate | In-memory ring + TimescaleDB | Hours | High-frequency writes, live reads |
| **Warm** | Recent flights, downlinked data | TimescaleDB with compression | Weeks–months | Replay, comparison, trending |
| **Cold** | Full onboard logs, recovered after landing | Parquet on disk/object store | Years | Batch analytics, model training |

🔶 **Volume estimate** for one 18-hour sortie:

```
Downlinked scalars:  30 ch × 4 B × 20 Hz × 64,800 s  ≈  155 MB
Vibration features:  40 × 4 B × 1 Hz × 64,800 s      ≈   10 MB
Onboard raw vibration: 10 kHz × 2 B × 64,800 s       ≈  1.3 GB per channel
```

**The onboard raw vibration dominates by an order of magnitude.** ⬜ This justifies a policy: keep raw vibration only around flagged events plus periodic samples, not continuously — unless storage is cheap enough, which on an aircraft it may not be. This is the same trade-off as the downlink, one level down.

---

## 12.8 The model-training pipeline (offline)

Separate from the operational pipeline, and it must stay separate.

```
 Historical flights (full onboard logs, many aircraft)
        │
        ▼
 [Labelling]  ← maintenance records, inspection findings, seeded-fault tests
        │
        ▼
 [Split BY ENGINE / BY FLIGHT — never by row]   ◀── the critical step
        │
        ├──────────────┬──────────────┐
        ▼              ▼              ▼
     Train          Validate        Test
        │              │              │
        ▼              ▼              │
 [Feature extraction — fit scalers on TRAIN only]
        │                             │
        ▼                             │
 [Model training]                     │
        │                             │
        ▼                             │
 [Hyperparameter selection] ──────────┘
        │
        ▼
 [Final evaluation on TEST, once]
        │
        ▼
 [Model artefact + metrics + data card]
        │
        ▼
 [Deployment to GCS  →  then, only after validation, to edge]
```

**The three rules that prevent self-deception:**

1. **Split by engine or flight, never by row** ([Part VIII §8.7](08_fault_diagnosis.md)). Adjacent samples are near-duplicates.
2. **Fit scalers and PCA on training data only.** Fitting on the full dataset leaks test statistics into training.
3. **Touch the test set once.** Every peek and re-tune turns it into a validation set, and the reported number stops being an estimate of generalisation.

🔶 A fourth rule specific to our situation: **if the model is trained on synthetic data, it must be evaluated on something the generator did not produce** — or the result measures the model's ability to invert the simulator, not to diagnose an engine. See [Part XIV](14_datasets.md) and [Part XVII](17_simulation_design.md).

---

## 12.9 Latency budget

⬜ End to end, from physical event to operator awareness:

| Segment | Latency | Notes |
|---|---|---|
| Sensor → ECU | <1 ms | Negligible |
| ECU → CAN → flight computer | ~1–5 ms | Frame time plus scheduling |
| Edge processing | ~10 ms | Dominated by FFT |
| Telemetry encode | <1 ms | |
| **Datalink** | **✅ ~1,000–1,500 ms** | **Dominates everything** |
| GCS ingest → twin update | ~5 ms | |
| Analytics | ~10 ms | |
| Dashboard render | ~50 ms | |
| **Total** | **~1.1–1.6 s** | |

**The link is ~95% of the budget.** Optimising our code from 10 ms to 5 ms changes nothing an operator can perceive. 🔶 The engineering effort belongs in deciding *what to send* (and what to decide onboard), not in shaving milliseconds off ground-side processing. This is why [Part XIII](13_edge_vs_ground_split.md) is the consequential design document and micro-optimisation is not.

---

**Next:** [Part XIII — Edge versus Ground Compute Split](13_edge_vs_ground_split.md)
