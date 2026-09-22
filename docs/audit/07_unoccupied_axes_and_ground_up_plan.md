# Unoccupied Axes & Ground-Up Feature Plan

*Third audit pass. The first two asked "what are we missing against the PS" and "what are competitors doing." This one asks a different question: **what is nobody in this field even looking at, that the PS actually rewards?***

**Method:** external research against the global state of the art in UAV propulsion, PHM, and military airworthiness — deliberately **not** grounded in our codebase. The codebase was read only to establish what currently exists so this plan does not re-propose it. Every claim below carries a source.

**Relationship to prior docs:** [`03_the_actual_solution.md`](03_the_actual_solution.md) found one empty axis (crank-angle vibration). It was right, and it survives intact. This document finds **eleven more**, one of which reframes the project.

---

## Part I — The mental model: what this repo is

| Layer | What exists | Why it exists |
|---|---|---|
| **The ask** | SIH PS `26054`, DRDO / Dept. of Defence R&D — AI digital twin for aero piston engines in MALE UAVs. 83 decomposed requirements in [`fun_req.md`](../fun_req.md) | The contract. Everything is scored against it |
| **Physics** | `backend/physics/` — Rotax 912 iS thermodynamic model, 27-parameter state, residual vector, performance maps, injection/ignition timing | The twin's "expected" engine |
| **Plant** | `backend/telemetry/can_streamer.py` — generates "actual" sensor frames with 8 injectable faults | ⚠️ Currently *the same model* as the twin (gap G01) — the core credibility problem |
| **Detection** | `backend/ml/` — 9-stage 20 Hz pipeline, numpy autoencoder, RF classifier, trend analyser, Monte Carlo RUL, Go/No-Go | The PS's §C and §D |
| **Persistence** | `backend/graph/`, `backend/reports/` — knowledge graph, sortie history, mission debriefs, CBM work orders | The PS's "operational history" and maintenance advisory |
| **Presentation** | `frontend/` React GCS + role panels, `apps/` desktop GCS and Blender 3D twin | The PS's §F |
| **Data** | Synthetic sorties (`data/telemetry/live_sorties/`), C-MAPSS turbofan, **0 real piston-engine files** | ⚠️ Gap G18 — the honesty problem |
| **Study** | `docs/study/` Parts I–XXVII — sensors, vibration DSP, edge AI, fault diagnosis, conformal prediction | Research that *predicted the vibration gap and was not acted on* |

**The two structural problems already known:** the plant and the twin are one model (G01), and validation is circular (G03). Nothing below replaces those — they remain prerequisite.

---

## Part II — The reframe: we are modelling the wrong engine

> 🔶 **This is the single highest-leverage finding in this document.**

We model a **Rotax 912 iS** — 100 hp, spark-ignition, AVGAS, naturally aspirated.

The actual Indian MALE UAV this PS is written for — **TAPAS BH-201 / Rustom-2**, built by ADE, a DRDO lab — flies the **Austro Engine AE300: a turbocharged, common-rail, compression-ignition engine running Jet-A1 kerosene**, and the programme has demonstrated **28,000 ft with 18-hour endurance**. ([TAPAS-BH-201](https://en.wikipedia.org/wiki/TAPAS-BH-201), [DRDO Rustom](https://en.wikipedia.org/wiki/DRDO_Rustom), [Army Recognition](https://www.armyrecognition.com/archives/archives-aerospace-defense/aerospace-defense-2023/india-to-evaluate-tapas-bh-201-male-uav-intended-for-all-three-services))

### The three tells in the PS text itself

1. **"Injection timing parameters"** is listed as a monitored health parameter. On a port-injected SI engine, injection timing is a minor trim. On a **common-rail CI engine it is the primary control variable** — multiple injection events per cycle, and injector condition is the dominant failure mode.
2. **"MALE"** means medium *altitude*. 28,000 ft on a naturally-aspirated engine is not physically possible. **Turbocharging is mandatory**, and we model no induction/boost subsystem at all.
3. **Heavy fuel.** Defence single-fuel policies drive UAV propulsion to JP-5/JP-8/Jet-A1; the UAV engine industry is built around it ([Orbital UAV](https://www.unmannedsystemstechnology.com/company/orbital-corporation/), [RCV Engines](https://www.unmannedsystemstechnology.com/company/rcv-engines/)). An AVGAS spark engine is the wrong logistics answer for a battlefield UAV.

### Why this *strengthens* rather than threatens the crank-angle thesis

The worry would be "a diesel does not misfire, so F02 dies." The opposite is true:

- A CI engine's dominant fault modes — **injector nozzle coking / internal diesel injector deposits (IDID), needle sticking, rail-pressure decay, injection-timing drift** — all produce a **per-cylinder torque deficit**, which is exactly what the ω(θ) TDC-segmentation detector in F02 measures. Injector deposits "hinder the movement of critical moving parts, affecting the timing and quantity of fuel injection," beginning as cold-start difficulty and rough running before progressing to engine failure ([autotechnician](https://autotechnician.co.uk/common-rail-injector-failure-the-common-causes-and-signs/), [G2 Diesel](https://www.g2dieselproducts.com/blog-resources/common-rail-injector-failure-symptoms)).
- So the crank-angle chain stops being a misfire detector and becomes a **per-cylinder injection-health detector** — which is *the PS's named fault target* ("Injector abnormalities") *and* its named monitored parameter ("Injection timing parameters"), both of which our own gap register lists as unmet or shallow.

### What to do about it

⬜ **Not** "throw away the Rotax." Make **engine class a configuration, not a hardcoding**, and ship two configs: SI (Rotax 912 iS) and CI-HFE (AE300-class). That single move:

- turns SYS-02/SYS-03 ("scalable", "modular") from an assertion into a **demonstration** — two genuinely different engine architectures through one twin;
- puts us on the **actual DRDO platform's engine class**, which no competitor will have noticed;
- unlocks an entire fault library nobody else has (Part IV).

---

## Part III — Standards traceability: the credibility axis nobody occupies

Hackathon teams assert architectures. **Defence panels recognise standards.** Four of these are free — they are relabelling and documentation discipline over things we largely already have.

### III.1 · ISO 13374 / MIMOSA OSA-CBM — the six-layer architecture

The international standard for condition monitoring defines exactly six functional blocks: **Data Acquisition → Data Manipulation → State Detection → Health Assessment → Prognostic Assessment → Advisory Generation** ([MIMOSA](https://www.mimosa.org/mimosa-osa-cbm/), [PHM Society](https://papers.phmsociety.org/index.php/phme/article/download/1647/609)).

Read the PS's section headings again: data ingestion → signal processing → abnormal condition detection → health indices → RUL/degradation → maintenance advisory. **The PS is an unlabelled restatement of ISO 13374.** Mapping our modules onto the six blocks, with the standard's defined inter-block interfaces, costs days and produces an architecture diagram that a certification-literate reviewer recognises instantly.

### III.2 · MIL-STD-1629A FMECA — where the fault list comes from

Our 8 faults are chosen. They should be **derived**. MIL-STD-1629A "systematically evaluates and documents the potential impact of each functional or hardware failure on **mission success**, personnel and system safety, ... and maintenance requirements" ([everyspec](https://everyspec.com/MIL-STD/MIL-STD-1600-1699/MIL_STD_1629A_1556/), [FMECA overview](https://en.wikipedia.org/wiki/Failure_mode,_effects,_and_criticality_analysis)).

⬜ Build a FMECA table for the propulsion system → criticality ranking → **traceability matrix**: `failure mode → physical signature → sensor channel → detection algorithm → advisory action`. This answers the one question every panel asks and no team can answer: *"why these faults, and what about the ones you left out?"*

### III.3 · Standard prognostic metrics — stop inventing scoring

NASA/PHM Society define the accepted prognostics metrics: **Prognostic Horizon, α-λ accuracy, Relative Accuracy, Convergence**, applied as a hierarchical waterfall ([Saxena & Goebel](https://c3.ndc.nasa.gov/dashlink/static/media/publication/K11944_C005.pdf), [NTRS](https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/20100023445.pdf)) — and NASA publishes an open implementation ([nasa/PrognosticsMetricsLibrary](https://github.com/nasa/PrognosticsMetricsLibrary)).

Everyone, us included, reports ad-hoc RUL error. Reporting α-λ and Prognostic Horizon instead is a few hours' work against a NASA library and is immediately legible to anyone who works in PHM.

### III.4 · CEMILAC / DO-178C — the deployment roadmap that lands

**CEMILAC is a DRDO laboratory.** It certifies every system, LRU, component and **software** item on Indian military airborne platforms, explicitly including UAVs ([CEMILAC](https://en.wikipedia.org/wiki/Centre_for_Military_Airworthiness_and_Certification), [DRDO certification services](https://drdo.gov.in/drdo/en/offerings/schemes-and-services/certification-services)). DO-178C is the governing software standard, and is adopted as guidance for UAS airworthiness ([DO-178C](https://en.wikipedia.org/wiki/DO-178C)).

⬜ A deployment roadmap section that states: this is **advisory-only, not control-coupled**, therefore it sits at a low Design Assurance Level; the moment it commands anything the DAL jumps and the learned components become a certification problem, because DO-178C has no accepted route for non-deterministic learned models. Therefore: **deterministic physics in any future safety path, ML confined to the advisory path.** That paragraph, addressed to the organisation that owns CEMILAC, is worth more than another classifier.

### III.5 · ISA-18.2 — the HMI as an engineering discipline

Alarm management is a standardised engineering practice (ISA-18.2 / EEMUA 191): rationalisation, prioritisation, nuisance-alarm rate, flood prevention, shelving. Every team builds a dashboard; **nobody treats operator alerting as a discipline with measurable requirements.** For a GCS where a false abort costs a sortie, this is directly on-point — and it makes our false-alarm-rate work (G03) part of a recognised framework rather than a number we chose.

---

## Part IV — Physics of failure: how life is *actually* tracked

> Everyone in this field computes RUL as: health index degrades → fit curve → extrapolate to threshold. **That is not how aerospace tracks life.**

Military and aerospace practice counts **damage**: convert the load history into cycles via **rainflow counting**, then accumulate damage fractions via **Miner's rule** (Palmgren-Miner linear damage), where life usage per stress pair is a function of R-ratio, **metal temperature**, and peak stress ([ScienceDirect: rainflow](https://www.sciencedirect.com/topics/engineering/rainflow-counting-algorithm), [US7243042 — engine component life monitoring](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/7243042), [Miner's rule](https://fiveable.me/elements-mechanical-engineering-design/unit-7/cumulative-damage-miners-rule/study-guide/6wWhLJkKR4DqnT0i)).

### Why this is a differentiator, not an academic flourish

| Property | Curve-fit RUL (everyone) | Damage-accumulation RUL |
|---|---|---|
| Grounding | Statistical, on synthetic degradation | **Physical**, on thermal/mechanical cycles actually flown |
| Auditability | "the model said so" | **A maintenance authority can check the arithmetic** |
| Granularity | One engine-level number | **Per component, per cylinder** |
| Survives the synthetic-data objection | ❌ No | ✅ **Yes — the damage law is independent of our simulator** |

⬜ And it enables the strongest honesty instrument available: **two independent RUL paths — damage-accumulation and data-driven — that must agree.** When they diverge, that is itself a reportable signal ("the twin is no longer trustworthy"), and no competitor has anything like it.

**Concretely trackable for a piston aero engine:** per-cylinder thermal LCF from CHT cycles; **shock cooling** (CHT rate-of-change during descent — a real and well-known piston-aero damage mechanism); oil thermal aging; turbo hot-shutdown cycles; cold-soak/start cycles.

---

## Part V — The lubrication channel: 60 years of military practice, absent here

The PS names "**Lubrication issues**" as a fault target. We model **oil pressure loss**. The gap register's G15 proposes adding oil temperature and viscosity. All of that misses the actual technique.

Since the early 1960s the US military has run **SOAP — Spectrometric Oil Analysis Program** — to monitor aircraft engines, determining wear-metal quantity, elemental composition and **rate of wear with its source**, acting as an early-warning system before failures escalate ([AZoM](https://www.azom.com/article.aspx?ArticleID=16478), [Eurofins](https://www.eurofins.in/industrial-product-testing/spectro/industrial-services/automobile-products/petroleum-products-testing/spectrometric-oil-analysis/), [OSTI](https://www.osti.gov/biblio/229945)). Modern practice adds **online debris sensors** — inductive (MetalSCAN class), capacitive, optical, electrostatic — because offline sampling cannot catch abrupt wear ([in-situ capacitive sensor network](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8914893/), [impedance micro-sensor](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7913635/)).

### The insight that makes this a *diagnostic*, not a scalar

Wear metals **localise the fault by element**:

| Element | Source |
|---|---|
| Fe | rings, liner, camshaft |
| Al | pistons |
| Cu / Pb | bearings, bushings |
| Cr | rings, plating |
| **Si** | **ingested dust — i.e. a breached air filter** |

⬜ That last row is the hinge of Part VI. Oil stops being a pressure gauge and becomes a **wear fingerprint that names the wearing component** — and the only channel in the machine that gives a *direct measurement of material loss* rather than an inference from temperature.

Add **blow-by / crankcase pressure** and **oil consumption rate** and the ring/bore wear path is fully observable.

---

## Part VI — The Indian operating environment as a first-class model

The PS asks for "environmental condition simulation" and names High Altitude, Endurance, Hot Weather. Every team implements these as **sliders that change a number**. They are, physically, **degradation drivers with memory**.

### VI.1 · Dust — the Thar/desert chain

Desert operations are brutally hard on engines; in rotary-wing desert deployments increased wear reduced engine reliability by as much as 50%, and fine particles below ~10 µm defeat inertial separators entirely ([Aviation Week](https://aviationweek.com/knowledge-center/helicopter-engines-operational-impact-harsh-environments), [dust ingestion after sandstorms](https://www.sciencedirect.com/science/article/abs/pii/S1270963820307549), [NHESS global airports study](https://nhess.copernicus.org/articles/24/2263/2024/)).

⬜ The causal chain, fully modellable and fully observable:

```
dust exposure hours
   → air filter loading → ΔP across filter rises
   → MAP deficit at constant throttle  ← detectable, physics-based
   → [if filter breached] silica ingress
   → abrasive bore/ring wear
   → blow-by ↑ + oil consumption ↑ + Si in oil ↑   ← Part V confirms it
   → compression loss → power margin loss
```

**No competitor can tell that story**, and it is the single most India-relevant physical narrative available in this problem.

### VI.2 · Cold at altitude — the heavy-fuel killer

At 28,000 ft, ambient is around −40 °C. For a Jet-A1 CI engine this creates failure modes that do not exist for an AVGAS SI engine:

- **Fuel waxing.** Below the **cloud point**, paraffin wax crystallises; at the **CFPP (cold filter plugging point)** crystals block the fuel filter entirely and starve the injection system ([CDS](https://cdspros.com/preventing-wax-build-up-in-diesel-engines/), [VFI Diesel](https://vfidiesel.com/diesel-cold-start-problems/)). ⬜ A **live CFPP margin** — fuel temperature vs. cloud point, with filter ΔP as corroboration — is a genuinely novel, physically real, high-altitude-specific health indicator.
- **Cold-soaked injectors.** Common-rail injectors hold micron-level tolerances; cold metal contraction increases the hydraulic force needed to lift the needle off its seat, degrading injection quantity and timing ([autotechnician](https://autotechnician.co.uk/common-rail-injector-failure-the-common-causes-and-signs/)). This is a **restart risk after a long high-altitude loiter** — exactly the MALE endurance mission the PS names.
- Oil viscosity at cold-soak; battery capacity collapse in cold (and the FADEC depends on it).

### VI.3 · Hot-and-high

At altitude, cooling **mass flow** falls while required heat rejection does not. Combined with high OAT (Ladakh, or desert summer), the CHT margin shrinks from both sides simultaneously. ⬜ Model cooling as mass-flow-limited, not as a temperature offset — then "hot weather at altitude" becomes a *coupled* constraint rather than two independent sliders.

### VI.4 · Exposure accumulator

⬜ Persist cumulative **dust-hours, cold-soak cycles, hot-shutdown events, salt exposure** (maritime ISR is named in the PS background) per tail, and feed them into the Part IV damage rates. Result: *"this airframe flew 240 h in desert conditions; predicted filter and bore wear rates are 1.8× fleet baseline."* That is fleet-level health management, and it is what the PS means by "operational history."

---

## Part VII — Speak the interfaces a real UAV speaks

We invented a CAN schema. The world already has one.

- **MAVLink `EFI_STATUS` (#225)** carries RPM, cylinder head temperature, **injection timing**, engine load, fuel consumption rate, throttle position, atmospheric pressure and ECU voltage ([MAVLink common message set](https://mavlink.io/en/messages/common.html), [ArduPilot MAVLink messages](https://ardupilot.org/plane/docs/ArduPlane_MAVLink_Messages.html)). **That is very nearly the PS's monitored-parameter list, as a published standard.**
- **ArduPilot has a first-class EFI subsystem** with native support for real UAV ECUs including Currawong, and community CAN drivers publishing straight into `EFI_STATUS` ([AP_EFI](https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_EFI/AP_EFI.h), [Lua CAN EFI driver](https://discuss.ardupilot.org/t/lua-efi-driver-for-loweheiser-ecu-via-can-bus/144496)).

⬜ Ingesting `EFI_STATUS` from **ArduPilot SITL** costs little, is free to run, and converts "real-time data ingestion" (DTC-06, currently ⬛ MISSING) from a claim into a demonstration against the actual autopilot stack Indian UAV programmes use. Pair it with a real **DBC-defined CAN** path and the PS's "CAN bus / SocketCAN" and "ECU/FADEC communication interfaces" lines are satisfied literally rather than by analogy.

And it closes HMS-11 ("injection timing parameters", currently ⬛) **by standard message field** rather than by inventing a channel.

---

## Part VIII — A twin that knows what it does not know

### VIII.1 · Per-tail calibration is what makes it a *twin*

A model that is not fitted to **this specific engine** is a simulation, not a digital twin. Every engine differs — friction, volumetric efficiency, heat-transfer coefficients, injector delivery. ⬜ Identify per-tail parameters from confirmed-nominal flight data (joint state-parameter estimation, or Bayesian calibration), and the twin becomes asset-specific. This is the definitional property of a digital twin and essentially nobody in this field implements it.

### VIII.2 · Twin validity monitoring

⬜ A first-class output: **is the twin still trustworthy?** Standard instruments exist — innovation consistency tests (NIS/NEES) from estimation theory, residual whiteness, out-of-distribution detection on the operating envelope. Combined with the Part IV dual-RUL disagreement signal, the system can say *"my model no longer matches this engine"* instead of silently producing confident nonsense. **This is the most sophisticated honesty mechanism available and it is completely unoccupied.**

### VIII.3 · Separating drift from degradation

With per-tail parameters explicit, a slow change can be attributed: **parameter drift** (the engine changed) vs **state anomaly** (a fault is occurring) vs **sensor drift** (the measurement changed). That three-way separation is the rigorous version of gap G05.

---

## Part IX — Security as physics, not as cryptography

The PS names "**Secure telemetry architecture**" as an innovation area. The competitive answer is HMAC-signed telemetry. **Signing protects the link — it does nothing against a compromised sensor or spoofed ECU upstream of the signature.** CAN has no native authentication, and spoofing by impersonating a trusted node's identifiers is the standard attack ([CAN IDS research](https://arxiv.org/pdf/2503.21496)).

⬜ The elegant answer, which we are uniquely positioned for because we already have a physics model: **the twin is the intrusion detector.** Injected values must satisfy the engine's physical relationships — MAP against RPM and throttle against fuel flow against EGT. Physically inconsistent injections are rejected; attacks that ignore inter-channel structure "produce ghost data that spatiotemporal detectors reject." Recent work does exactly this with **conformal guarantees on the false-alarm rate** ([Physics-Constrained Digital Twins for Sensor Integrity with Conformal Guarantees, 2026](https://arxiv.org/html/2609.17635)) — which composes directly with our planned conformal work (F12).

One sentence available to us and to nobody else: *"cryptography tells you the frame arrived unaltered; physics tells you the frame was never true."*

---

## Part X — The PS title is a computable number, and nobody computes it

> **"...and Mission Reliability Enhancement"**

Every team ships a go/no-go heuristic. The title asks for **mission reliability** — a quantity with a definition: **P(complete the planned sortie without a propulsion-induced abort), given current component health, the planned mission profile, and forecast environment** — computed by Monte Carlo over the damage and failure models, reported with an interval.

⬜ And once it is a number, the prescriptive layer follows, which the literature already validates: prescriptive control that **progressively derates load to hold a constant damage rate** has been reported to extend useful life by **65%** and deliver **23% higher mission performance** than reactive baselines ([Reliability-Adaptive Control via Stochastic MPC](https://www.mdpi.com/2227-7390/14/4/737), [Prognostics-Aware Control for Extended RUL](https://papers.phmsociety.org/index.php/ijphm/article/view/3789)); and mission replanning is formally "a search or optimization problem that results in reduced use of the impaired component" ([Prognostics driven decision making, US11402833](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11402833)).

⬜ The three outputs that follow, in ascending value:

1. *"Mission reliability for the planned 18 h / 28,000 ft ISR sortie: **0.87 [0.81–0.92]**. Limiting component: cylinder 2 injector."*
2. *"Derate to 85% power: damage rate −40%, mission reliability 0.87 → **0.95**, endurance penalty 22 min."*
3. *"This sortie is not achievable as planned. **Achievable: 14 h at 22,000 ft** at reliability 0.93."*

That is the PS title, answered literally, in the operator's language.

---

## Part XI — Evaluation instruments that survive hostile questioning

| Instrument | What it kills |
|---|---|
| ⬜ **Zero-shot foundation-model baseline** — run Chronos-2 / TimesFM / Moirai-2, never trained on our data, as a control. Zero-shot TSFM anomaly detection is production-viable as of 2026 ([ChronosAD](https://arxiv.org/pdf/2606.01300), [THEMIS](https://arxiv.org/pdf/2510.03911), [2026 toolkit](https://machinelearningmastery.com/the-2026-time-series-toolkit-5-foundation-models-for-autonomous-forecasting/)) | *"You only beat your own simulator"* — a model that never saw our simulator either provides the control |
| ⬜ **Fault isolability / observability analysis** — formally determine which faults are *distinguishable* given the sensor set, and which are not | *"How do you know it isn't the other fault?"* — and it justifies the sensor suite instead of assuming it |
| ⬜ **Standard PHM metrics** (Part III.3) | *"MAE against what?"* |
| ⬜ **Physics validation against NASA ACES** — real Rotax 914 telemetry from the Altus II UAV | *"Is your physics real?"* — already identified in [`05_expanded_survey.md`](05_expanded_survey.md) |
| ⬜ **Correct AD evaluation protocol** — avoid point-adjust F1 inflation | *"Your F1 is inflated by the protocol"* |

---

## Part XII — The final feature list

Continues the numbering in [`04_feature_spec.md`](04_feature_spec.md) (F01–F30), which **survives intact**. Items marked ⬆ upgrade an existing feature rather than adding one.

### Tier A — Strategic reframe *(cheap, mostly design; changes everything downstream — do first)*

| # | Feature | Why | Effort |
|---|---|---|---|
| **F31** | **Engine class as configuration** — SI (Rotax 912 iS) + CI-HFE (AE300-class) configs through one twin | Part II. Proves SYS-02/03 by demonstration; puts us on the real DRDO engine class | Med |
| **F32** | **Turbocharged induction subsystem** — boost, wastegate/VGT, intercooler, surge margin | MALE altitude is impossible without it; entirely absent today | Med |
| **F33** | **FMECA-derived fault taxonomy** (MIL-STD-1629A) + traceability matrix | Part III.2. Answers "why these faults" | Low |
| **F34** | **OSA-CBM / ISO 13374 six-layer architecture mapping** | Part III.1. Free credibility; the PS *is* this standard | Low |
| **F35** | **Fault isolability & sensor-set justification** | Part XI. Rigorous, and unoccupied | Med |

### Tier B — Physics-of-failure life *(the second differentiator)*

| # | Feature | Why | Effort |
|---|---|---|---|
| **F36** | **Rainflow + Miner cumulative damage**, per component, per cylinder | Part IV. How aerospace actually tracks life | Med |
| **F37** | **Shock-cooling / thermal-transient damage accounting** | Real piston-aero mechanism; nobody models it | Low |
| **F38** | **Dual-path RUL + disagreement alarm** (damage-accumulation vs data-driven) | Part IV. Strongest honesty instrument available | Med |
| **F39** | **Oil system health** — wear-metal fingerprint, debris trend, blow-by, oil consumption | Part V. 60 years of military practice, absent from the entire field | Med |
| **F40** | **Environmental exposure accumulator** (dust-h, cold-soak, hot-shutdown, salt) | Part VI.4. Makes "operational history" consequential | Low |

### Tier C — HFE + environment fault library *(new physics, uniquely India-relevant)*

| # | Feature | Why | Effort |
|---|---|---|---|
| **F41** | **CI injector fault suite** — IDID/coking, needle stick, rail-pressure decay, timing drift | Part II. Closes PS HMS-11 + "injector abnormalities" properly | Med |
| **F42** | **Fuel thermal management** — cloud point / **CFPP margin**, waxing, filter ΔP, cold-soak restart | Part VI.2. Novel, physical, altitude-specific | Med |
| **F43** | **Induction path & dust chain** — filter ΔP → MAP deficit → silica → bore wear | Part VI.1. The India story no competitor can tell | Med |
| **F44** | **Turbo fault suite** — wastegate stick, overspeed, bearing wear, surge, intercooler fouling | Follows F32 | Med |
| **F45** | **Mass-flow-limited cooling model** (hot-and-high coupling) | Part VI.3. Makes two PS scenarios interact physically | Low |

### Tier D — Real interfaces *(converts claims into demonstrations)*

| # | Feature | Why | Effort |
|---|---|---|---|
| **F46** | **MAVLink `EFI_STATUS` (#225) ingestion + ArduPilot SITL** | Part VII. Free, real, standard; closes DTC-06 and HMS-11 | Med |
| **F47** | **CAN via real DBC** (SocketCAN/vcan + python-can), modelled on a real UAV ECU | PS names CAN/SocketCAN explicitly | Med |
| **F48** | **NASA ACES log-as-live + physics validation** on real Rotax 914 UAV telemetry | Part XI; already flagged in survey | Med |
| **F49** | **Test-rig / HIL mode** | The PS's second named deployment context (SYS-08, ⬛) | Med |

### Tier E — Twin validity & trust *(the most sophisticated unoccupied axis)*

| # | Feature | Why | Effort |
|---|---|---|---|
| **F50** | **Per-tail Bayesian calibration / joint state-parameter estimation** | Part VIII.1. This is what makes it a *twin* | High |
| **F51** | **Twin validity monitor** (NIS/NEES, residual whiteness, OOD envelope) | Part VIII.2. "I no longer match this engine" | Med |
| **F52** | **Drift vs degradation vs sensor-fault separation** | Part VIII.3. Rigorous G05 | Med |
| **F53** ⬆ | **Adaptive conformal under distribution shift** (upgrades F12) | Coverage must hold when conditions move | Low |

### Tier F — Security as physics

| # | Feature | Why | Effort |
|---|---|---|---|
| **F54** | **Physics-constrained false-data-injection detection with conformal false-alarm guarantee** | Part IX. PS-named innovation area; composes with F12 | Med |
| **F55** | **Threat model + lane-disagreement / replay / stale-frame detection** | Dual-lane FADEC is real; disagreement is a free diagnostic | Low |

### Tier G — Mission reliability & prescriptive *(the PS title)*

| # | Feature | Why | Effort |
|---|---|---|---|
| **F56** | **Computed mission reliability** — P(sortie completion) with interval, and limiting component | Part X. **The literal PS title, unoccupied** | Med |
| **F57** | **Damage-rate-budgeted prescriptive advisory** (derate ↔ life ↔ endurance trade) | Part X. Predictive → prescriptive | Med |
| **F58** | **Mission re-planning under degradation** — achievable endurance/radius | Part X. Operator-actionable | Med |
| **F59** | **Fleet tail-to-mission assignment** by health | SYS-09 fleet deployment, made concrete | Low |

### Tier H — Evaluation & honesty

| # | Feature | Why | Effort |
|---|---|---|---|
| **F60** | **Standard PHM metrics** (PH, α-λ, RA, convergence) via NASA library | Part III.3 | Low |
| **F61** | **Zero-shot TSFM baseline** (Chronos-2 / TimesFM / Moirai-2) as untrained control | Part XI. Kills the circularity objection | Low |
| **F62** | **Correct AD evaluation protocol** (no point-adjust inflation) | Part XI | Low |
| **F63** | **Sim2real gap report** vs ACES + domain randomisation over engine parameters | Part XI | Med |

### Tier I — HMI as engineering

| # | Feature | Why | Effort |
|---|---|---|---|
| **F64** | **ISA-18.2 alarm management** — rationalisation, prioritisation, nuisance rate, shelving | Part III.5. Unoccupied discipline | Low |
| **F65** | **Physics causal-chain explanation + counterfactual** | Beats SHAP bars: *"MAP nominal, fuel flow −4%, EGT₂ +38 °C → cylinder 2 lean; a sensor fault would not have moved CHT₂"* | Med |
| **F66** | **Case-based retrieval with citation** from the knowledge graph | Uses what we already built, safely (no free generation) | Low |

### Tier J — Edge systems engineering

| # | Feature | Why | Effort |
|---|---|---|---|
| **F67** | **Edge power/endurance budget** — watts of analytics vs minutes of endurance | Nobody accounts for their own system's cost on the platform | Low |
| **F68** | **Measured latency/WCET + quantised edge inference on target hardware** | Turns "edge AI" from a word into a measurement | Med |

---

## Part XIII — Build order

Dependencies respected; earliest items are cheap and make everything after them quotable.

```
Phase 0 — Decide the machine        F31, F33, F34, F35          (design/doc; reframes everything)
Phase 1 — Make it honest            G01 plant split, F46, F47, F50, F51
Phase 2 — Make it hear              F01–F08 (existing) + F41    ← crank-angle chain, now injection-health
Phase 3 — Make it count             F36, F37, F38, F39, F40
Phase 4 — Make it matter            F56, F57, F58  (+F32, F42, F43, F44, F45 as physics lands)
Phase 5 — Make it provable          F60, F61, F62, F63, F48, F12/F53, F13
Phase 6 — Make it trusted           F54, F55, F64, F65, F66, F67, F68
```

🔶 **Risk gates.** After Phase 0, F31 must produce two engine configs that both run before anything is built on the CI path. After Phase 2, the existing F01 gate still applies — a healthy engine must produce a physically plausible order spectrum, or the crank-angle chain stops and the 20 Hz pipeline remains.

---

## Part XIV — What the project becomes

> **Everyone else predicts a fault from eight slow numbers.**
>
> **ANUMAAN measures combustion cylinder-by-cylinder, counts the damage that actually consumes engine life, speaks the interfaces a real UAV already speaks, says plainly when it no longer trusts itself — and turns all four into the one number the problem statement asks for: the probability this sortie completes.**

Five defensible claims, on five axes, each independently unoccupied:

| Axis | Claim | Occupied by competitors? |
|---|---|---|
| **Sensing** | Crank-angle-resolved, per-cylinder combustion/injection diagnostics | ❌ 0 of 15 |
| **Life** | Physics-of-failure damage accumulation, auditable, dual-path | ❌ 0 of 15 |
| **Integration** | Real MAVLink/CAN/ECU interfaces; correct engine class for the actual DRDO platform | ❌ 0 of 15 |
| **Trust** | Per-tail calibration, twin validity monitoring, conformal coverage, physics-based spoof detection | ❌ 0 of 15 |
| **Decision** | Computed mission reliability + prescriptive damage-budgeted advisory | ❌ 0 of 15 |

---

*Audit set: [`README.md`](README.md) · [`01_competitive_audit.md`](01_competitive_audit.md) · [`02_self_audit.md`](02_self_audit.md) · [`03_the_actual_solution.md`](03_the_actual_solution.md) · [`04_feature_spec.md`](04_feature_spec.md) · [`05_expanded_survey.md`](05_expanded_survey.md) · [`06_repo_cleanup_plan.md`](06_repo_cleanup_plan.md) · this document.*
