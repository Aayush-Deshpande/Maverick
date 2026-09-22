# Project ANUMAAN — Problem Statement Breakdown
**Plain-language explanation of DRDO PS-26054, for anyone with zero background in Digital Twins, aero engines, UAVs, or AI/ML.**

> This is not a paraphrase of the official PS. It is an explanation of what each requirement *actually means* and *actually requires us to build*. The verbatim official text lives in [00_official_problem_statement.md](00_official_problem_statement.md) — read this document to understand it, read that one to quote it.

---

## How to Read This Document

Every technical term below follows the same pattern so nothing is left as unexplained jargon:

> **Term → Simple meaning → Why it matters here → How we could implement it**

Every claim below is also labeled so we never confuse "the PS says this" with "we decided this":

| Label | Meaning |
|---|---|
| 🟩 **STATED** | Explicitly written in the official PS text |
| 🟨 **IMPLIED** | Not written directly, but logically required for the stated parts to work |
| 🟦 **OUR CHOICE** | An assumption or implementation decision we made for concreteness — not required by the PS |
| ⬜ **OPTIONAL** | Mentioned by the PS as something we "may" do, or an enhancement we're proposing on top |

---

## Quick-Reference Term Table

| Term | One-line meaning |
|---|---|
| MALE UAV | A drone that flies medium-high, for a very long time, on its own |
| Digital Twin | A live virtual copy of the real engine that updates itself in real time |
| RUL | How much longer a part can run before it's likely to fail |
| CHT / EGT | Cylinder Head Temperature / Exhaust Gas Temperature — two key "vital signs" of the engine |
| FADEC | The engine's own onboard computer that controls fuel and ignition |
| CAN bus / SocketCAN | The wiring standard/protocol used to move sensor data around a vehicle |
| Anomaly detection | Software that notices "this doesn't look normal" without being told the exact rule in advance |
| Physics-informed model | A prediction model that knows the actual laws of thermodynamics, not just patterns in data |
| Edge computing | Running the analysis on the UAV itself, not waiting to send data to a far-away server |
| Mission replay | Re-playing a past flight's recorded data through the twin, after the fact |

---

## 1. Problem Statement

**Official title:** *"AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs."*

In plain words: **build a smart, self-updating virtual copy of a drone's engine that watches it constantly, notices problems before they become failures, tells you how much life is left in it, and lets you replay and simulate its behavior — instead of just sounding an alarm after something already breaks.**

---

## 2. The Problem in One Paragraph

Long-range surveillance drones (MALE UAVs) have only **one engine** — unlike an airliner, if it fails mid-flight, there's no backup, and the drone is lost. Right now, the way these engines are monitored is basically a smoke alarm: sensors check numbers like temperature and pressure, and if a number crosses a hard-coded red line, an alert fires. The problem is that by the time the red line is crossed, damage is usually already happening — there is no advance warning, no explanation of *why*, and no way to know how much longer things can be pushed before real failure. DRDO wants a system that instead builds a continuously-updated virtual copy of the engine — one that combines live sensor readings, the actual physics of how the engine works, and AI trained on failure patterns — so it can catch problems while they're still small, explain what's wrong, predict how much useful life remains, and let operators simulate "what if we fly this mission" before ever taking off.

---

## 3. Why This Problem Exists

**🟩 MALE UAVs.** *Medium Altitude Long Endurance* drones fly for very long single sorties (often 18+ hours) at altitudes well above normal aircraft-avoidance airspace, used for border surveillance, maritime patrol, and communication relay. They are uncrewed, so there's no pilot on board to notice a strange smell, a weird vibration, or a subtle change in engine sound the way a human pilot would in a small aircraft.

**🟩 Why engine reliability is the single most important factor.** These UAVs use one piston engine (similar in principle to a small aircraft engine, not a jet). There is no second engine to fall back on. If it fails over hostile or remote terrain, the aircraft is gone — not just an inconvenience, but a lost strategic asset and a failed mission (border watch, ISR feed, whatever it was doing).

**🟩 Problems with conventional monitoring.** Today's systems work like this: *"Is Cylinder Head Temperature above 135°C? No? Then everything is fine."* That single check tells you nothing about whether the temperature has been climbing steadily for the last 20 minutes, or whether it's completely stable. It only reacts once a hard limit is crossed.

**Why reactive monitoring is insufficient (Term → Meaning → Why it matters → How to fix):**

> **Reactive monitoring** → checking "has a limit been crossed *right now*" → by definition it cannot warn you *before* the limit is crossed, because that's the only thing it's watching for → the fix is to also watch *trends* (is a healthy-looking number moving toward the limit faster than normal?) which is what lets you warn early.

**Why prediction is needed.** Real damage (metal fatigue, seal wear, bearing wear) starts *before* a sensor reading breaks a threshold — by the time the alarm fires, the damage has already begun, and depending on the failure mode, there may only be seconds to minutes to react at 20,000+ feet with no place to land. A predictive system that catches a *trend* 30–60 minutes early gives the operator time to change the mission (throttle back, switch redundant systems, return to base) instead of just watching a light turn red.

---

## 4. What Is a Digital Twin?

**Simple analogy first:** think of a fitness tracker (like a Fitbit or an Apple Watch) paired with a health app. It doesn't just show your heart rate *right now* — it also notices "your resting heart rate has been drifting up over the last 3 days, that's unusual for you," and it can show you a replay of your run from yesterday, minute by minute. The watch + app together form a live, evolving model of *your* body specifically — not a generic textbook body, but *yours*, based on your actual data over time.

**Technical meaning in this PS:** A Digital Twin is software that keeps a continuously-updated virtual model of *this specific physical engine*, built from three ingredients combined together:

1. **Live sensor data** — what the real engine is doing right now (temperatures, pressures, RPM, vibration...).
2. **Physics-based models** — the actual mathematical laws of how a 4-stroke piston engine burns fuel, generates heat, and loses power at altitude — this is *not* guesswork, it's the same thermodynamics used to design the engine.
3. **AI/ML trained on failure history** — patterns learned from past examples of engines failing, so the system recognizes early warning signs a pure physics equation wouldn't catch (e.g. a specific vibration signature that precedes a bearing failure).

> **Digital Twin** → a live virtual copy of the real engine that updates itself continuously → it matters here because it's the *one system* that has to combine raw sensor data, the physics of combustion, and AI predictions into a single coherent picture of engine health → we implement it as a backend service that ingests telemetry, runs it through both a physics model and ML models in parallel, and publishes a unified "engine state" that everything else (dashboard, alerts, replay) reads from.

**Critical distinction to hold onto for the rest of this document:** *a 3D picture of an engine on a screen is NOT a digital twin.* The 3D model is just one possible way to *look at* the twin's data. The twin itself is the data and the models underneath — see [Section 14](#14-what-the-3d-visualization-is-responsible-for).

---

## 5. What Are They Actually Asking Us to Build?

Breaking the PS into individual requirements, each as: **What they said → What it actually means → What our system needs to do.**

### A. Digital Twin Core Framework 🟩

| What they said | What it actually means | What our system needs to do |
|---|---|---|
| "Virtual engine model synchronized with live engine data" | The twin's numbers must track the real engine's numbers continuously, not be a one-time snapshot | Keep an in-memory "current state" object that is overwritten/updated every time new telemetry arrives |
| "Modular architecture for future scalability" | Don't hard-wire everything into one giant script — different engines/sensors/fault types should be pluggable later | Separate the system into independent services/modules (ingestion, physics, ML, dashboard) that communicate over a defined data format (e.g. JSON messages), not by directly calling into each other's internals |
| "Real-time data ingestion capability" | The system must be able to receive a continuous stream of sensor readings, not just load a file once | Build a data ingestion layer that can accept a live stream (from CAN bus, or a simulator standing in for one) and push each new reading into the pipeline as it arrives |

### B. Health Monitoring System 🟩

The PS lists 8 specific parameter groups that must be tracked: RPM, Cylinder Head Temperature (CHT), Exhaust Gas Temperature (EGT), Oil Pressure & Temperature, Fuel Flow, Vibration Signatures, Battery/Alternator Health, Injection Timing Parameters.

*What it actually means:* these are the engine's "vital signs" — think of them as the engine's blood pressure, temperature, pulse, etc. Each one, tracked over time (not just as a single number), tells a different part of the health story: temperatures tell you about heat management, oil pressure tells you about lubrication, vibration tells you about mechanical wear, electrical health tells you whether the engine's own control systems have power.

*What our system needs to do:* for **each** parameter, don't just display the current value — compute a rolling trend (is it rising/falling/stable, and how fast?) and combine several parameters into a per-subsystem "health index" (e.g. a single 0–100 score for "cooling system health" derived from CHT + EGT + trend).

### C. Fault Detection & Predictive Analytics 🟩

The PS names 8 specific things to detect/predict: misfire, injector abnormalities, cooling degradation, lubrication issues, sensor drift/failure, combustion instability, overheating trends, abnormal vibration patterns.

*What it actually means:* this list is basically "the 8 most common ways a small aero piston engine dies in the field." Each one has a distinct sensor *signature* — a specific pattern across multiple sensors, not just one value crossing a line. For example, a misfire shows up as RPM jitter *combined with* a temperature drop on one specific cylinder, not as any single sensor alone.

*What our system needs to do:* for each of the 8 fault types, define what its signature looks like across the relevant sensors, and build a detector (rule-based, statistical, or ML-based) that recognizes that specific combination — not a single-sensor threshold check, since that's exactly the "conventional" approach the PS says is insufficient.

### D. AI/ML Layer 🟩

| What they said | What it actually means | What our system needs to do |
|---|---|---|
| "Anomaly detection algorithms" | Flag "this doesn't look like normal operation" even for problems we didn't explicitly program a rule for | Train a model (e.g. isolation forest, autoencoder, or simpler statistical control limits) on data from normal/healthy operation, so it can flag deviations without needing every fault type pre-defined |
| "Remaining Useful Life (RUL) estimation" | Estimate how much longer (in flight-hours or minutes) a component can keep operating before it's likely to fail | See [Section 11](#11-what-rul-means) |
| "Trend analysis" | Track whether health indicators are getting better, worse, or staying flat, and at what rate | Fit a simple slope/regression over a rolling time window per parameter |
| "Predictive maintenance recommendations" | Don't just say "something is wrong" — say what to do about it | Turn a detected fault/trend into a specific recommended action (e.g. "reduce RPM to X", "schedule inspection of part Y within Z flight hours") |

### E. Simulation & Replay Capability 🟩

*What it actually means:* the system should work not just live, but also (1) backward in time — replaying a past flight's actual recorded data — and (2) forward/hypothetically — simulating how the engine *would* behave under conditions it hasn't experienced yet (a hotter day, a higher-altitude mission).

*What our system needs to do:* keep every flight's telemetry stored in a replayable format, and make the physics model capable of running on *synthetic* inputs (a chosen altitude/temperature/mission profile), not only on live sensor data. See [Sections 12–13](#12-what-mission-simulation-means).

### F. Visualization Dashboard 🟩

*What it actually means:* a human-readable interface — this is explicitly for **people** (operators, engineers, maintenance crew), not a machine-to-machine interface.

*What our system needs to do:* surface the twin's computed outputs (health status, alerts, trends, advisories, mission reports) in a UI that a non-programmer can read at a glance during a live flight.

---

## 6. Required Inputs

| Input | What it is | Why it matters |
|---|---|---|
| Engine sensor data | Live readings from physical sensors on the engine (RPM, temperatures, pressures, etc.) | This is the ground truth of what the engine is actually doing right now — without it, the twin is just guessing |
| Telemetry | The stream/transport of that sensor data from the aircraft to the monitoring system (typically over CAN bus) | Defines *how* the data physically gets from engine to software; also carries timestamps needed for trend analysis |
| Engine performance maps | Reference charts showing how the engine *should* perform at a given RPM/altitude/temperature when healthy | Without a "what's normal" baseline, you can't tell a real anomaly from expected variation (e.g. power naturally drops at altitude — that's not a fault) |
| Thermodynamic information | The physics constants and equations governing combustion, heat transfer, and gas behavior in the engine | Lets the twin *calculate* what a reading *should* be, so it can compare "expected" vs "actual" instead of relying purely on historical data patterns |
| Failure/degradation history | Past examples of how sensor patterns looked before/during real (or simulated) failures | This is what the ML side learns from — without labeled failure examples, "predicting" a fault is just a guess |
| Environmental conditions | Altitude, ambient temperature, humidity, air density at the time of flight | Engine physics genuinely changes with environment (thinner air at altitude = less cooling, less oxygen for combustion); ignoring this causes false alarms |
| Mission information | What the current sortie is (planned duration, profile, load) | Needed for the "pre-flight Go/No-Go" check — you need to know what's being asked of the engine before you can say whether it can handle it |

---

## 7. Required Outputs

| Output | What it is | How it's used |
|---|---|---|
| Real-time engine state | The current values + trend direction of every monitored parameter | Feeds the live dashboard and every downstream calculation |
| Health indicators | Aggregated per-subsystem scores (e.g. "cooling: 92/100") rather than raw sensor dumps | Lets a human grasp overall condition at a glance instead of reading 20 numbers |
| Anomaly detection | A flag/alert that current behavior deviates from learned-normal, with severity | Triggers operator attention before a fault has been fully diagnosed |
| Fault prediction | A specific fault type + confidence + estimated time-to-occurrence | Gives the operator/maintainer something actionable, not just "something's off" |
| Degradation tracking | The historical trend line of a health indicator over time (across one flight or across a component's whole life) | Basis for RUL and for deciding maintenance timing |
| Remaining Useful Life (RUL) | An estimated amount of remaining safe operating time/hours for a part or subsystem | Directly drives the pre-flight Go/No-Go decision and maintenance scheduling |
| Mission simulation results | Predicted engine behavior under a hypothetical mission profile/environment | Lets planners test "can this engine handle this mission" before committing |
| Mission replay | A reconstructed, scrubbable timeline of a past flight's twin state | Used for post-flight investigation, training, and validating that a fault was real |
| Operator visualization | The human-facing dashboard showing all of the above | The actual interface a person interacts with during and after a flight |

---

## 8. Core System Components

```text
Data Acquisition
        ↓
Data Processing
        ↓
Physics / Engine Model
        ↓
Digital Twin
        ↓
Health Monitoring
        ↓
Anomaly Detection
        ↓
Fault Prediction
        ↓
Degradation / RUL
        ↓
Mission Simulation
        ↓
Mission Replay
        ↓
Ground Control Interface
```

- **Data Acquisition** — receives raw sensor readings, over CAN bus/SocketCAN or a simulator standing in for real hardware.
- **Data Processing** — cleans and structures the raw stream: timestamps things consistently, filters obvious sensor glitches, converts raw units into engineering units.
- **Physics / Engine Model** — calculates what the engine's behavior *should* look like right now, using thermodynamics and performance maps, given current RPM/throttle/altitude/temperature.
- **Digital Twin** — merges the live sensor data with the physics model's expectation into one authoritative "current state of this specific engine."
- **Health Monitoring** — turns raw twin state into per-subsystem health indices and trend directions.
- **Anomaly Detection** — flags when live behavior deviates from what's normal/expected, even without a pre-defined fault rule.
- **Fault Prediction** — classifies a detected anomaly into one of the known fault types (or "unknown"), with a confidence and lead-time estimate.
- **Degradation / RUL** — tracks long-term trend of health indices and estimates remaining safe operating time.
- **Mission Simulation** — runs the physics + ML models on hypothetical (not live) inputs to answer "what if" questions about a planned mission.
- **Mission Replay** — re-feeds a previously recorded flight's data back through the same pipeline so it can be reviewed after the fact.
- **Ground Control Interface** — the human-facing dashboard/HMI that displays everything above and surfaces alerts/advisories.

---

## 9. What "Real-Time" Means

"Real-time" does **not** mean "instant" — it means *fast enough relative to how quickly the thing you're measuring actually changes.*

Different signals change at very different speeds, so they need different update rates:

- **Vibration** changes extremely fast (thousands of cycles per second) — it needs high-frequency raw sampling, but the *analysis result* ("is this vibration abnormal?") can be recomputed a few times per second.
- **Temperatures** (CHT/EGT) drift over tens of seconds to minutes — updating a few times per second is already far faster than the physical process itself, so nothing is lost by not sampling every millisecond.
- **RUL/degradation trends** change over many flight-hours — recomputing this every few seconds to a minute is more than sufficient.

There are actually three different "real-time" rates in this system, and they don't need to match each other:

1. **Sensor sampling rate** — how often the physical sensor is read (fastest).
2. **Twin update/sync rate** — how often the digital twin's internal state is recalculated from new sensor data.
3. **Dashboard refresh rate** — how often the human-facing display redraws (this can be the slowest, since human eyes don't need millisecond updates).

**🟦 OUR CHOICE:** we treat "real-time" as "the twin's state must never be more than a few seconds stale relative to the real engine," which is fast enough to catch every fault type in the PS's list while remaining practical to simulate/demo. The PS itself does not mandate a specific number of updates per second.

---

## 10. What "Predictive" Means

These four words get used loosely and interchangeably, but they are different capability levels, each one strictly harder than the last:

1. **Monitoring** — showing the current value of a parameter. *("CHT is 128°C right now.")*
2. **Detection** — noticing that a current value or pattern is abnormal. *("CHT is behaving unusually.")*
3. **Diagnosis** — explaining *why* it's abnormal / which fault is causing it. *("This looks like a cooling baffle leak on Cylinder #2.")*
4. **Prediction** — saying what will happen *next*, and roughly when, if nothing is done. *("At this rate, CHT will hit the critical limit in ~40 minutes.")*

The old "threshold-based" systems the PS is explicitly trying to replace only do step 1, arguably brushing step 2 (only once a hard limit is already crossed). **The PS is asking for all four steps**, with the last one (prediction) being the genuinely new and hardest capability.

---

## 11. What RUL Means

**Remaining Useful Life (RUL)** → *"how much longer can this part/engine keep running before it's likely to fail"* → it matters here because it's the difference between maintenance done *just in time* versus maintenance done *too early* (wasting good parts) or *too late* (in-flight failure) → it can be estimated by:

1. Picking a measurable signal that's known to worsen as a component wears out (a "degradation indicator" — e.g. a slowly rising vibration amplitude, or a slowly widening gap between Lane A and Lane B sensor readings).
2. Tracking that signal's trend over time (is it rising, and how fast?).
3. Knowing (from physics, historical failure data, or manufacturer limits) the threshold value at which the component is considered failed or unsafe.
4. Extrapolating: at the current rate of change, how much time until the trend line reaches that threshold?

This can be done with something as simple as fitting a straight line/curve through recent history and projecting forward, or as sophisticated as a trained ML model that's seen many past examples of "this exact pattern of degradation, and it failed N hours later." A simpler linear extrapolation is a reasonable, honest starting point — a black-box number with no visible degradation trend behind it is **not** RUL (see [Section 18](#18-common-misinterpretations)).

---

## 12. What Mission Simulation Means

The engine doesn't behave the same way in every flight phase or environment — a good digital twin has to know this, or its "normal" baseline will be wrong and it'll either miss real faults or cry wolf on healthy behavior.

| Condition | Why the engine behaves differently |
|---|---|
| Takeoff | Maximum throttle and RPM demand — highest thermal and mechanical stress in a short burst |
| Climb | Sustained high power output while air density is dropping — cooling gets harder as you climb |
| Cruise | Steady-state, moderate load — the "easiest" phase, most sensors should be flat and stable |
| Loiter | Long duration at reduced throttle, but for many hours — slow, gradual thermal/mechanical stress accumulates here even though nothing looks dramatic minute-to-minute |
| Descent | Reduced power, engine cools down — rapid cooling itself can also stress components (thermal shock) |
| Landing | Throttle changes rapidly again, similar stress profile to takeoff |
| High altitude | Thinner air = less oxygen for combustion (less power) and less air density for cooling — the same throttle position produces different temperatures than at sea level |
| High ambient temperature (desert heat) | Less effective cooling margin to begin with — the engine runs hotter for the same workload |
| Different engine loads | Directly changes fuel burn, heat generation, and mechanical stress |

*What it actually means:* the twin's physics model needs altitude, ambient temperature, and mission-phase/throttle as **inputs**, not constants — the "expected normal" value for CHT at 25,000 ft in the desert during climb is genuinely different from cruise at sea level, and the system must know that difference to avoid false alarms and to run believable "what-if" simulations for mission planning.

---

## 13. What Mission Replay Means

Mission replay means taking the *recorded* telemetry from a flight that already happened, and feeding it back through the exact same digital twin pipeline (physics model, health monitoring, anomaly detection) as if it were happening live again — just after the fact, and typically scrubbable (able to pause/rewind/fast-forward through the timeline).

*Why it's useful, distinct from a live twin:* after a flight, engineers need to answer questions like "did the system correctly catch that misfire, and how early?" or "walk me through exactly what happened in the 10 minutes before the alert" — this requires being able to step back through history, which a purely live system (that only shows "now") cannot do.

*What our system needs to do:* store every flight's telemetry stream (not just the final summary) in a format the pipeline can re-ingest, and provide a UI/control to play it back at variable speed, pause, and jump to specific timestamps — most usefully, jump directly to moments the twin flagged as anomalous during that flight.

---

## 14. What the 3D Visualization Is Responsible For

This is one of the most important distinctions to get right, because it's the easiest thing to accidentally over-invest in.

**Digital Twin intelligence** (the actual PS requirement) is:
- Ingesting sensor data
- Running physics + ML models
- Computing health, anomalies, faults, RUL, trends
- Producing all of this as **data** (numbers, flags, timestamps, structured messages)

**3D visualization** is:
- A *rendering layer* that **reads** that data and displays it — coloring a cylinder red when its CHT crosses a warning band, animating a "leak" effect when a fault fires, rotating a camera to focus on the affected subsystem.

The critical test: **if you deleted the entire 3D view, would the system still be able to prove it detects and predicts faults?** It must — because the 3D model contains zero intelligence of its own. It never decides anything; it only visualizes decisions that were already made upstream. If the 3D view were removed and the "intelligence" also disappeared, that's a sign the logic accidentally got baked into the visualization layer instead of the twin itself, which is a structural bug, not a feature.

**🟦 OUR CHOICE:** our existing Blender-based UAV/engine model sits *entirely* inside the "Ground Control Interface" block from [Section 8](#8-core-system-components) — it is one possible skin on top of the twin's outputs. It should be built to be replaceable by a plain 2D chart dashboard without losing a single bit of actual detection/prediction capability. The PS never requires 3D visualization specifically — see the next section.

---

## 15. Mandatory vs Optional

| Category | Meaning | Items |
|---|---|---|
| 🟩 **Explicitly required by the PS** | Directly named in the official text | Real-time virtual engine model · Modular architecture · Live data ingestion · Monitoring all 8 listed health parameters (RPM, CHT, EGT, oil P/T, fuel flow, vibration, battery/alternator, injection timing) · Detecting/predicting all 8 listed fault types · Anomaly detection · RUL estimation · Trend analysis · Predictive maintenance recommendations · Historical mission replay · Environmental condition simulation · Mission-phase behavior simulation (altitude, endurance, heat, throttle transients) · A visualization dashboard showing health status, fault alerts, efficiency trends, maintenance advisory, mission-wise reports |
| 🟨 **Strongly implied by the PS** | Not stated word-for-word, but the stated parts cannot function without it | A defined "normal/healthy" performance baseline to compare against · A thermodynamic/physics model of the engine (needed to know what's "expected" at a given altitude/load) · Persistent storage of telemetry (required for both trend analysis and replay) · Some way to simulate a synthetic or logged dataset, since real Rotax 912/UAV hardware is not available to us · A clear boundary between fast/deterministic checks and slower AI reasoning |
| 🟦 **Useful additions we can propose** | Not required, but genuinely strengthens the solution against the PS's own stated goals | Explainable AI (showing *why* a prediction was made, not just the prediction) · A natural-language RAG copilot for querying maintenance manuals/mission history · Federated learning / edge AI framing as a "desired innovation area" talking point · Automated PDF maintenance debrief generation |
| ⬜ **Purely cosmetic / at risk of scope creep** | Impressive-looking, but does not itself satisfy any PS requirement, and can consume disproportionate development time | High-fidelity photorealistic terrain (e.g. the Nubra Valley environment) · Cinematic camera choreography / drone flight animations (the kind of thing explored in the `avionix/` reference teardown) · Voice interface polish beyond basic functionality · Any 3D visual fidelity work once the dashboard already clearly displays health/alerts/RUL/trends |

**Why this table matters:** items in the last row are *not bad* — they make for a more impressive demo — but they should only be worked on **after** every 🟩 and 🟨 item is functionally proven, because a judge scoring against PS-26054 is checking for prediction accuracy and RUL logic, not rendering quality. Time spent polishing terrain while an 8th fault type has no detector is a losing trade.

---

## 16. What Would a Complete Solution Look Like?

- **UAV** — the airframe carrying a single piston engine, flying a long-duration ISR/surveillance mission with no onboard pilot to notice problems.
- **Engine** — a 4-cylinder aero piston engine (🟦 our reference assumption: Rotax 912 iS Sport, see [01_problem_statement_and_analysis.md](../analysis/strategy/01_problem_statement_and_analysis.md)) whose 8 monitored parameters are continuously produced.
- **Sensors** — instruments on the engine measuring RPM, CHT, EGT, oil pressure/temperature, fuel flow, vibration, electrical health, and injection timing, transmitting over CAN bus/SocketCAN.
- **Data pipeline** — ingests that raw stream, cleans it, timestamps it, and stores it.
- **Digital Twin** — the core service combining live data with a physics model to hold the authoritative current + expected state of the engine.
- **AI/ML** — anomaly detection, fault classification, trend analysis, and RUL estimation running continuously on the twin's state.
- **Simulation** — the same physics model, run on hypothetical mission/environment inputs instead of live data, for pre-flight planning.
- **Ground Control Station** — the physical/software station where the operator sits, receiving the dashboard, alerts, and advisories.
- **Operator** — the human who ultimately makes the Go/No-Go call, reacts to prescriptive recommendations, and reviews mission-replay reports post-flight.

---

## 17. What Would Judges Need to See?

Translating each PS requirement into a concrete, *demonstrable* moment — a judge should never have to take our word for a capability; they should watch it happen.

| PS Requirement | Demo must visibly show |
|---|---|
| "Detects abnormal engine behavior" | Normal engine running → inject/replay an abnormal condition → dashboard visibly flags it as anomalous, in view, in real time |
| "Predicts probable failures before occurrence" | Show the anomaly *starting small* while still inside the "safe" band → system raises a prediction with a specific fault type and estimated time-to-failure *before* any hard threshold is crossed |
| "Estimates degradation trends and RUL" | A visible trend line/chart for a chosen component, with a displayed RUL number that visibly *decreases* as the simulated degradation continues |
| "Simulates engine behavior under different mission profiles/environments" | Pick two different environment presets (e.g. sea-level temperate vs. high-altitude desert) and show the same throttle input producing genuinely different predicted temperatures/power |
| "Supports post-flight analysis and mission replay" | Load a previously completed flight, scrub the timeline, and jump directly to the moment a fault was flagged during that flight |
| "Prescriptive/maintenance recommendations" | When a fault is predicted, the dashboard shows a specific, human-readable recommended action — not just a red light |
| "Dashboard for operators/maintenance engineers" | A live view usable during flight (health/alerts) *and* a separate/switchable view usable after flight (mission-wise reports) |

**The through-line every scenario should follow:** *Normal engine → abnormal behavior → detection → diagnosis/prediction → warning → recommended action.* If a demo scenario can't be narrated in that sentence, it likely isn't demonstrating a real PS requirement.

---

## 18. Common Misinterpretations

Things that *look* like progress toward this PS but do not actually satisfy it:

- **A 3D model alone.** A beautifully rendered engine that just sits there, or only responds to mouse input, demonstrates nothing about health monitoring or prediction. See [Section 14](#14-what-the-3d-visualization-is-responsible-for).
- **A dashboard with fake/hardcoded sensor values.** If the numbers don't come from a real (or realistically simulated) data stream reacting to actual inputs, there is no "monitoring" happening — it's a picture of a dashboard, not a working one.
- **Simple threshold alerts.** `if temperature > 135: alert()` is *exactly* the "conventional, reactive" approach the PS explicitly says is insufficient. Reproducing it, even with a nicer UI around it, does not solve the stated problem.
- **A chatbot that talks about failures without actually computing anything.** Natural-language responses describing a plausible-sounding fault are not a prediction unless they're generated from real computed anomaly scores/trends — a conversational UI is a nice *presentation* layer, never a substitute for the underlying detection logic.
- **Random or hardcoded RUL numbers.** RUL must be traceable to an actual degradation trend in the data (see [Section 11](#11-what-rul-means)); a number with no visible underlying trend line behind it is decoration, not RUL.
- **A static simulation that doesn't respond to inputs.** If choosing "Ladakh, high altitude" vs "Thar Desert, high heat" produces the *same* output, it isn't simulating anything — it's replaying one pre-baked animation with a different label.
- **A "digital twin" that's really just a snapshot.** Loading a single fixed dataset once at startup and never updating is not "continuously synchronized" — the PS's core word, "real-time," specifically rules this out.

---

## 19. Our Interpretation

**We believe PS-26054 is asking us to build a continuously-updating software model of an aero piston engine that combines live sensor data with a real thermodynamic model and AI trained on failure patterns, in order to: (1) monitor the engine's key vital signs as trends rather than single values, (2) detect abnormal behavior earlier than a fixed threshold ever could, (3) classify that abnormality into a likely known fault and predict how much time remains before it becomes critical, (4) estimate ongoing Remaining Useful Life for maintenance planning, (5) let operators simulate how the engine would behave under a planned mission/environment before flying it, and (6) let engineers replay a completed flight's recorded twin state for post-mission analysis — all surfaced through an operator-facing dashboard that is a consumer of this intelligence, never the source of it.**

This is our working definition for the rest of development. Every module we build should be traceable back to one of the six numbered capabilities above; if it isn't, it belongs in the 🟦/⬜ rows of [Section 15](#15-mandatory-vs-optional), not the critical path.
