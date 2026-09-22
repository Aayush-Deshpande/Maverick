# Part I — The Big Picture

*Why this problem exists, what the system is, and how every later part connects.*

---

## 1.1 The operational problem, stated physically

A MALE (Medium Altitude Long Endurance) UAV flies an 18–24 hour sortie at 20,000–30,000 ft on **one piston engine**. There is no second engine and no pilot aboard. If the engine stops, the aircraft is lost, along with the mission and a strategic asset.

✅ **VERIFIED** — DRDO's TAPAS-BH-201 is reported at 250 km mission range (up to ~1,000 km command range via satellite), 18–24 h endurance, ~28,000–30,000 ft ceiling, ~350 kg payload, 20.6 m wingspan, ~225 km/h max speed. DRDO demonstrated satellite-relayed beyond-line-of-sight control in June 2023. ([TAPAS-BH-201](https://en.wikipedia.org/wiki/TAPAS-BH-201), [TAPAS decoded](https://www.kodainya.com/blogs/tapas-bh-201-the-rustom2))

Now consider what a human pilot in a light aircraft actually does. They hear the engine note change. They smell hot oil. They feel a new vibration through the airframe. They notice the CHT needle creeping up over twenty minutes even though it is still in the green. **An uncrewed aircraft has none of that.** Everything a pilot would sense must be reconstructed from sensor numbers, or it is simply lost.

That is the real problem statement, underneath the formal one: *rebuild the pilot's situational awareness of engine health, from telemetry, at a ground station 250 km away, over a link that can carry only a few kilobits per second.*

## 1.2 Why threshold monitoring is not enough

Conventional engine monitoring is a comparator:

```python
if CHT > 135:
    alert()
```

This fails for three structural reasons, not merely because it is crude.

**It has no memory.** A CHT of 128 °C that has been stable for an hour and a CHT of 128 °C that has climbed 9 °C in twenty minutes are the same number to a threshold, and completely different engines to an engineer. The information lives in the *derivative*, which a threshold never computes.

**It has no context.** The expected CHT at 25,000 ft over Ladakh at −20 °C ambient is genuinely different from the expected CHT at sea level in Rajasthan at +45 °C. A single fixed limit must be set conservatively enough for the worst case, which makes it blind in every other case.

**It fires after the damage.** A limit is placed where the component is already being harmed. By construction, a system that only watches for limit crossings cannot warn you before one.

The PS is explicit that this reactive approach is what it wants replaced. ✅ **VERIFIED** — the official text describes conventional systems as "threshold-based and reactive" and says they "indicate failures only after an abnormality has already occurred."

## 1.3 The four capability levels

These words get used interchangeably and are not interchangeable. Each is strictly harder than the one before.

| Level | Question answered | Example output | Difficulty |
|---|---|---|---|
| **Monitoring** | What is the value now? | "CHT #2 is 128 °C" | Trivial |
| **Detection** | Is this abnormal? | "CHT #2 is behaving unusually for this flight condition" | Moderate — needs a normal baseline |
| **Diagnosis** | Why is it abnormal? | "Consistent with cooling baffle leak on cylinder 2" | Hard — needs labelled fault signatures |
| **Prognosis** | What happens next, and when? | "Reaches limit in ~40 min at current rate" | Hardest — needs degradation trajectories |

The PS asks for all four. Most of the engineering difficulty, and almost all of the evaluation difficulty, lives in the last two. See [Part IX](09_rul_prognostics.md) for why prognosis is disproportionately hard.

## 1.4 What a Digital Twin actually is here

Strip away the marketing. A digital twin, in this system, is one specific computational object:

> A continuously-updated estimate of the state of **this particular engine**, formed by combining live sensor data with a physics model of how the engine *should* behave under the current conditions, such that the difference between them is meaningful.

That difference is called the **residual**, and it is the single most important quantity in the entire system:

```
residual  =  measured value  −  physics-model expected value (given altitude, OAT, RPM, throttle)
```

A residual of +34 °C on CHT #2 means something regardless of altitude, weather, or power setting, because the expectation already accounted for all of those. This is what makes the twin more than a dashboard. See [Part X](10_digital_twin.md).

**A 3D render of an engine is not a digital twin.** It is a view onto one. The test: if you deleted the 3D view entirely, would the system still detect and predict faults? It must.

## 1.5 The physical chain, which is what most of this course is about

Everything downstream depends on understanding what physically happens to a measurement. This chain runs through Parts II, III, IV and XII:

```
Physical quantity        Cylinder head is at 128 °C
     ↓
Transducer               K-type thermocouple produces ~5.2 mV
     ↓
Signal conditioning      Amplify, cold-junction compensate, linearise
     ↓
ADC                      Becomes a 12–16 bit integer
     ↓
ECU / DAQ                Scaled to engineering units: 128.4 °C
     ↓
CAN frame                Packed into 8 bytes with other values, sent at 10–50 Hz
     ↓
Flight computer          Read via SocketCAN, validity-checked, timestamped
     ↓
Edge analytics           Residual computed, anomaly score updated
     ↓
Telemetry encoder        Selected values packed into a downlink frame
     ↓
RF / SATCOM              Travels 250+ km at a few kbps, with latency and loss
     ↓
GCS ingestion            Decoded, reordered, gap-filled
     ↓
Digital twin state       Authoritative "what this engine is doing" object
     ↓
Analytics + dashboard    Detection, diagnosis, RUL, advisory, replay
```

Two facts about this chain drive nearly every architectural decision we will make:

**The analog world ends at the ECU.** ✅ By the time data reaches the ground it is scalars in engineering units, not waveforms. The only exception is vibration, which is fundamentally different — see [Part VI](06_vibration_analysis.md).

**The link is the bottleneck.** ✅ **VERIFIED** — one source characterises Ku-band SATCOM control links at roughly 122 kbps or less with ~1–1.5 s command-to-feedback latency. ([Data Links chapter](https://kstatelibraries.pressbooks.pub/unmannedaircraftsystems/chapter/chapter-13-data-links-functions-attributes-and-latency/)) You cannot stream a 2 kHz accelerometer to the ground. This single fact is why the PS lists "Edge AI" and "lightweight onboard analytics" as innovation areas, and why our architecture must split compute. See [Part V](05_edge_ai.md) and [Part XIII](13_edge_vs_ground_split.md).

## 1.6 What the PS actually requires

✅ **VERIFIED** from the official text. Eight monitored parameter groups:

RPM · CHT · EGT · oil pressure & temperature · fuel flow · vibration signatures · battery/alternator health · injection timing parameters

Eight fault targets:

misfire · injector abnormalities · cooling degradation · lubrication issues · sensor drift/failure · combustion instability · overheating trends · abnormal vibration patterns

Plus: anomaly detection, RUL estimation, trend analysis, maintenance recommendations, mission replay, environmental simulation, and an operator dashboard.

Innovation areas it *encourages* (not requires): physics-informed AI, edge AI, lightweight onboard analytics, hybrid thermodynamic + data-driven models, federated learning, explainable AI, secure telemetry, autonomous maintenance advisory.

**What the PS does not specify** — and this matters enormously, because it is where our design freedom lives:

🔒 No engine is named. 🔒 No sampling rates. 🔒 No bus beyond the phrase "CAN bus / SocketCAN" and "ECU/FADEC communication interfaces". 🔒 No telemetry protocol. 🔒 No accuracy target. 🔒 No specific UAV platform.

Everything in those gaps is ⬜ **ASSUMPTION** on our part, and must be labelled as such.

## 1.7 How the parts of this course connect

```
                    ┌─────────────────────────────┐
                    │  Part I — Big Picture (you) │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
  ┌───────────┐            ┌──────────────┐          ┌───────────────┐
  │ Part II   │            │  Part III    │          │   Part IV     │
  │ Sensors:  │───────────▶│  ECU + CAN:  │─────────▶│  Telemetry:   │
  │ what is   │            │  how numbers │          │  how they     │
  │ measured  │            │  are formed  │          │  reach ground │
  └───────────┘            └──────────────┘          └───────┬───────┘
                                                             │
                                   ┌─────────────────────────┤
                                   ▼                         ▼
                            ┌─────────────┐          ┌───────────────┐
                            │  Part V     │          │  Part VI      │
                            │  Edge AI:   │◀─────────│  Vibration:   │
                            │  what runs  │          │  why it needs │
                            │  onboard    │          │  the edge     │
                            └──────┬──────┘          └───────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
  ┌───────────┐            ┌──────────────┐          ┌───────────────┐
  │ Part VII  │            │  Part VIII   │          │   Part IX     │
  │ Anomaly   │───────────▶│  Fault       │─────────▶│   RUL /       │
  │ detection │  "off"     │  diagnosis   │  "named" │   prognosis   │
  └───────────┘            └──────────────┘          └───────┬───────┘
                                                             │
                            ┌────────────────────────────────┤
                            ▼                                ▼
                     ┌─────────────┐                 ┌───────────────┐
                     │  Part X     │                 │   Part XI     │
                     │  Digital    │────────────────▶│   Mission     │
                     │  Twin       │                 │   simulation  │
                     └──────┬──────┘                 └───────┬───────┘
                            │                                │
                            └────────────┬───────────────────┘
                                         ▼
                            ┌─────────────────────────┐
                            │  Parts XII–XXII:        │
                            │  pipeline, split,       │
                            │  datasets, architecture,│
                            │  stack, roadmap, eval   │
                            └─────────────────────────┘
```

## 1.8 Common misconceptions, stated up front

| Misconception | Reality |
|---|---|
| "The GCS receives raw sensor signals" | It receives digitised scalars in engineering units, already processed onboard |
| "We can stream vibration waveforms to the ground" | You cannot. Bandwidth is kbps. Vibration is analysed onboard |
| "A 3D model is the digital twin" | The twin is the state estimate and physics model. The 3D view is a consumer of it |
| "Higher accuracy on CWRU means it will work on our engine" | CWRU is lab bearings at constant speed. A piston engine is cyclic and variable. See [Part VIII](08_fault_diagnosis.md) |
| "RUL is just a number the model outputs" | RUL without a visible degradation trend and an uncertainty bound is decoration |
| "Anomaly detection and fault classification are the same" | One says "something is off" without labels, the other names a known fault. Different models, different data needs |
| "DRDO uses MIL-STD-1553 / MAVLink / X" | 🔒 Not public. Never assert this |

---

**Next:** [Part II — Engine Sensors and Data Representation](02_engine_sensors.md)
