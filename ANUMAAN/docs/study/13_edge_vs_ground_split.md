# Part XIII — Edge versus Ground Compute Split

*The allocation table, the reasoning behind every row, and how the system degrades.*

---

## 13.1 The allocation rule

> A function runs at the **highest level** (furthest from the aircraft) that can still meet its data needs, its deadline, and its availability requirement.

Ground compute is abundant, cheap, upgradeable, and carries no weight, power or certification burden. Onboard compute is the opposite. So the default is *ground*, and each function must **earn** its place onboard by failing one of three tests:

| Test | Question | If it fails |
|---|---|---|
| **Data test** | Does it need data that cannot cross the link? | Must be onboard |
| **Deadline test** | Must it act faster than ~1.5 s? ✅ | Must be onboard |
| **Availability test** | Must it work when the link is jammed or lost? | Must be onboard |

---

## 13.2 The allocation table

| Function | Onboard | GCS | Offline | Reasoning |
|---|---|---|---|---|
| **Sensor acquisition** | ✅ **Required** | ❌ | ❌ | Physically located at the engine |
| **Signal conditioning / ADC** | ✅ **Required** | ❌ | ❌ | Analog domain ends here |
| **Anti-alias filtering** | ✅ **Required** | ❌ | ❌ | ✅ Cannot be done after sampling — irreversible |
| **CAN decode** | ✅ **Required** | ❌ | ❌ | Source of data |
| **Sensor validity checks** | ✅ **Primary** | 🔶 repeat | ❌ | Must gate data before it propagates; must survive link loss |
| **Time synchronisation** | ✅ **Primary** | 🔶 re-align | ❌ | Earliest possible timestamping |
| **Vibration acquisition** | ✅ **Required** | ❌ | ❌ | **Data test** — 160 kbit/s exceeds the link |
| **Vibration feature extraction** | ✅ **Required** | ❌ | ❌ | **Data test** — this IS the 4,000× reduction |
| **Physics residuals** | ✅ **Primary** | ✅ also | ❌ | Cheap; needed by the edge detector; also recomputed at GCS |
| **Anomaly detection** | ✅ **Lightweight** | ✅ **Full** | ❌ | **Availability test** — must run when jammed |
| **Fault classification** | 🔶 optional | ✅ **Primary** | ❌ | Needs labelled models + compute; not time-critical |
| **RUL estimation** | ❌ | ✅ **Primary** | ✅ refine | Operates on hours of history; no deadline |
| **Digital twin state** | 🔶 **Reduced** | ✅ **Full** | ❌ | Full twin at GCS; reduced onboard for autonomy |
| **Mission simulation** | ❌ | ✅ **Primary** | ✅ | Interactive, operator-driven, compute-heavy |
| **Model training** | ❌ **Never** | 🔶 rarely | ✅ **Always** | ⬜ Safety and certification — see [Part V §5.8](05_edge_ai.md) |
| **Replay** | ❌ | ✅ | ✅ | Post-hoc by definition |
| **Full-rate logging** | ✅ **Required** | ❌ | ✅ analyse | Only place the full data exists |
| **Dashboard / HMI** | ❌ | ✅ | ✅ | ✅ PS: explicitly for people at the GCS |
| **Alert generation** | ✅ **Local** | ✅ **Primary** | ❌ | Onboard for autonomy, GCS for the operator |
| **RAG / advisory** | ❌ | ✅ | ✅ | Needs document corpus and a language model |
| **Fleet trending** | ❌ | 🔶 | ✅ **Primary** | Cross-aircraft, cross-sortie |

Legend: ✅ primary location · 🔶 secondary/optional · ❌ not here

---

## 13.3 Why each contested row landed where it did

### Anomaly detection — deliberately in both places

This is the most important row, and the split is intentional rather than redundant.

```
ONBOARD (lightweight)                  GCS (full)
─────────────────────                  ──────────
EWMA + Mahalanobis on residuals        Ensemble: autoencoder + isolation
+ small quantised autoencoder          forest + statistical + fusion
on vibration features

Runs at 20 Hz, <1 ms                   Runs at 20 Hz, unconstrained
Survives jamming ✅                     Richer, better calibrated
Coarse but always available            Precise but link-dependent
```

🔶 **Reasoning:** the onboard detector fails the *availability test* if it lives only on the ground — and the scenarios that break the link (manoeuvring, terrain masking, jamming) correlate with the scenarios that stress the engine. Meanwhile the GCS detector can afford an ensemble and better calibration. Running both and requiring agreement for high-severity alerts reduces false alarms ([Part VII §7.6](07_anomaly_detection.md)).

### Fault classification — ground, with an optional onboard subset

Classification fails none of the three tests: it consumes features that *do* cross the link, it is not sub-second critical, and if the link is down the onboard anomaly detector already covers the safety case.

🔶 It also benefits most from ground-side advantages: larger models, easy updates without touching flight software, and access to the fleet history and RAG corpus that make an advisory actionable.

⬜ The optional onboard subset: a very small classifier for the two or three faults that warrant *autonomous* action (e.g. severe overheat → recommend derate). Only if the concept of operations calls for autonomy.

### RUL — ground only

Fails no test. It operates on hours of history, updates about once a minute, and nothing about it needs to be airborne. Putting it onboard would add complexity and certification burden for zero operational gain.

### Model training — offline only, never onboard

⬜ This is our firm position, and it is a safety stance rather than a compute one.

🔶 **Reasoning:** a model that changes its own behaviour in flight is very hard to certify, and very hard to reason about after an incident — you cannot reproduce the failure because the model is no longer the same model. Airworthiness practice is conservative about non-deterministic in-flight behaviour. I did not find a specific published requirement to cite for the Indian context, so treat this as engineering judgment, not a sourced mandate — but it is the defensible default.

⬜ **Our adaptation policy:** per-airframe baselines update **on the ground, between sorties, from confirmed-healthy flights only**, with a human in the loop. The in-flight model is frozen for the duration of the sortie. ✅ This still engages the PS's federated-learning innovation area, because the *federation* happens between ground stations, which is exactly how the published aircraft-engine federated-RUL work is structured anyway.

### Digital twin — full at GCS, reduced onboard

⬜ The onboard "reduced twin" is just the physics model plus residuals — enough to support the edge detector autonomously. The full twin, with state estimation, degradation history, RUL and simulation, lives at the GCS.

🔶 This avoids duplicating complex state-management code in flight software while preserving the autonomy that matters.

---

## 13.4 Degradation behaviour

The architecture must be judged by how it behaves when things break, not only when everything works.

| Condition | Onboard | GCS | Overall capability |
|---|---|---|---|
| **Everything nominal** | Full edge stack | Full analytics | ✅ 100% |
| **Bandwidth reduced** | Unaffected | Lower rate, features prioritised | ✅ ~90% — trends intact, resolution reduced |
| **High packet loss** | Unaffected | Gaps marked, twin propagates on model | 🔶 ~75% — detection works, precision degraded |
| **Link lost entirely** | **Full edge stack continues; buffers** | **STALE; last known state** | 🔶 ~40% — aircraft still monitored, operator blind |
| **Link restored** | Backfills buffer | Reconciles timeline | ✅ Returns to 100%, with history recovered |
| **Vibration DAQ fails** | Scalar analytics only | Scalar analytics only | 🔶 ~60% — faults 1, 6, 8 lose their primary sensor |
| **One sensor fails** | Excluded, flagged | Affected indices degraded | ✅ ~90% |
| **Onboard computer fails** | ❌ nothing | Nothing arrives | ❌ Monitoring lost — but the ECU's own protections remain |
| **GCS fails** | Full edge stack continues | ❌ | 🔶 Aircraft protected; recover the log after landing |

**The two rows that justify the whole design:**

- **"Link lost entirely"** — the aircraft remains monitored. A ground-only architecture would drop to 0% here. That difference is the entire argument for edge AI, stated operationally rather than theoretically.
- **"Vibration DAQ fails"** — capability drops sharply because three of the eight PS faults depend on it. 🔶 This is worth knowing in advance: it tells you the accelerometer and its mounting are a single point of failure for a third of the fault coverage, and that redundancy there buys more than redundancy elsewhere.

---

## 13.5 What crosses the link

⬜ The concrete contract, with 🔶 estimated budgets:

### Continuously, at 20 Hz (~19 kbit/s)

Core scalars: RPM, CHT ×4, EGT ×4, oil pressure and temperature, fuel flow, MAP, bus voltage, alternator current, injection timing, throttle, altitude, OAT, IAS, plus per-sensor validity flags.

### At 1 Hz (~1.3 kbit/s)

Vibration feature vector: order band energies (0.5, 1, 2, 4, GMF and sidebands), envelope-band energies (BPFO/BPFI/BSF/FTF), RMS, kurtosis, crest factor.

### At 1 Hz (negligible)

Health indices per subsystem, edge anomaly score, twin residual summary.

### On event (sporadic, high priority)

Anomaly onset/clear, threshold crossings, sensor validity changes, ECU lane switch, edge fault hypothesis, link-quality change.

### On request (bounded burst)

A detailed window around a flagged event: higher-rate scalars, an order spectrum snapshot, possibly a short raw vibration segment if bandwidth permits.

### Never

Raw vibration waveforms. Full-rate logs. Model weights.

🔶 **Total ≈ 21 kbit/s continuous**, inside a ⬜ 25–30 kbit/s allocation, against ✅ a link characterised at ~122 kbit/s or less shared with everything else. Comfortable, with headroom for event bursts.

---

## 13.6 The "on request" tier

⬜ This deserves its own section because it is the most elegant part of the design and the best demo moment.

```
   t=0      Edge detects anomaly on cylinder 2
              │
              ▼   ~40 bytes
   t=1.5s   EVENT: {type: ANOMALY_ONSET, cyl: 2, score: 0.87, t: ...}
              │
              ▼
            Operator sees the alert, clicks "detail"
              │
              ▼   ~50 bytes
   t=4s     REQUEST: {detail_window, t_start, t_end, channels: [...]}
              │
              ▼   ~20 kB burst
   t=6s     Detailed snapshot: order spectrum, high-rate CHT/EGT,
            envelope spectrum around the event
```

**The principle:** spend bandwidth *retrospectively*, only on the moment that turned out to matter. Continuous high-rate streaming spends it on the 99.9% of the flight where nothing happens.

🔶 This works because the onboard log has everything — the data already exists, and the request is a retrieval, not a new measurement. It is the same logic as a flight recorder with a query interface.

---

## 13.7 The reduced onboard twin

⬜ What the onboard twin contains, and deliberately does not:

| Component | Onboard | Why |
|---|---|---|
| Physics model | ✅ Yes | Cheap; needed for residuals |
| Residual computation | ✅ Yes | The input to the edge detector |
| Current health indices | ✅ Yes | Simple weighted combination |
| Lightweight anomaly score | ✅ Yes | Availability test |
| Short degradation history | 🔶 Minutes only | Enough for trend onset, not for RUL |
| Kalman state estimation | 🔶 Simplified | Complementary filter suffices |
| Full degradation history | ❌ No | Needs persistent cross-sortie storage |
| RUL | ❌ No | No deadline; needs long history |
| Fault classification | 🔶 Optional | Only if autonomous action is required |
| Mission simulation | ❌ No | Interactive, operator-driven |

🔶 **Reasoning:** the onboard twin answers one question — *"is this engine deviating from expected behaviour right now?"* — and it must answer it without help. Everything requiring long history, large models, or human interaction belongs at the GCS.

---

## 13.8 Summary

| Question | Answer |
|---|---|
| What must be onboard? | Acquisition, anti-alias filtering, validity checks, vibration features, residuals, lightweight anomaly detection, logging |
| What must be at the GCS? | Full twin, classification, RUL, mission simulation, dashboard, replay, advisory |
| What must be offline? | Model training, fleet trending, per-airframe baselines |
| What is the split criterion? | Data test, deadline test, availability test — fail any one, it goes onboard |
| What happens when jammed? | Onboard keeps full local monitoring and buffers; GCS shows STALE, never a frozen value |
| How much crosses the link? | 🔶 ~21 kbit/s continuous, plus event bursts, inside a ⬜ 25–30 kbit/s allocation |
| What never crosses? | Raw vibration, full logs, model weights |

---

**Next:** [Part XIV — Datasets](14_datasets.md)
