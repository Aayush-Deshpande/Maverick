# 10 — Red-Team Review: Is It Enough?

*A hostile read of docs [07](07_unoccupied_axes_and_ground_up_plan.md), [08](08_deployable_system_blueprint.md) and [09](09_full_depth_architecture.md), measured against three things: every line of the problem statement, DRDO's actual situation, and what an SIH panel of DRDO scientists will score and ask. Written 23 September 2026. Web-verified facts carry sources at the end.*

---

## Verdict

| Question | Answer |
|---|---|
| Is the **technical depth** enough to impress DRDO engineers? | **Yes.** Combustion, vibration, estimation and diagnosis are designed at research-lab depth, well beyond both the PS text and the field. More brainstorming on those layers has diminishing returns. |
| Does it cover **all aspects**? | **Not yet.** Eleven blind spots remain (§2). Two are named explicitly in the PS (battery/alternator health; engine efficiency trends). One is a red flag a defence panel would catch: **the copilot runs a Chinese-origin model (Qwen)**. |
| Will we **solve the PS for real**? | **Not alone, and nobody can.** A real solution needs VRDE's engine constants, FADEC data access, test-cell time and CEMILAC clearance. What we *can* do is reach TRL 4 on real hardware and hand DRDO a credible, specific path to TRL 5–6. That is what solving it looks like at this stage, and §4 makes the path concrete. |
| What is the **biggest risk now**? | **Execution, not ideas.** Nothing in doc 09 is built yet. ✅ The SIH grand finale is a 36-hour build in which judges favour a stable, working prototype over an ambitious one with incomplete functionality, and feasibility is scored explicitly. A brilliant document with a fragile demo loses to a modest document with a solid one. |

---

## 1. The problem statement, line by line

Status: **Deep** (designed beyond the ask) · **Adequate** · **Shallow** (mentioned, not designed) · **Missing**

| PS item | Status | Where |
|---|---|---|
| **§2 Integrate:** sensor data, thermodynamic models, failure/degradation logic, AI/ML | Deep | 09 §4–§8 |
| §2 **Engine performance maps** | Shallow | Turbo map only. A CI power/BSFC map needs VRDE data (§2.2). |
| §2 Capabilities: visualisation, health indicators, abnormal conditions, failure prediction, RUL | Deep | 09 §4–§7, §11 |
| §2 Simulate under mission profiles and environments; post-flight analysis and replay | Deep | 07, 08, 09 §2.4 (full-sortie raw recording), §12 |
| §2 May use: CAN, ECU/FADEC, edge, local analytics, physics-informed AI, HMI | Deep | 09 §3, §5, §9 |
| **§3A** Virtual engine synchronised with live data; modular; real-time ingestion | Deep | 08 §3.1, 09 §5 |
| **§3B** RPM, CHT, EGT, oil P/T, fuel flow, vibration, injection timing | Deep | 09 §1.2, §4 |
| §3B **Battery / alternator health** | **Missing** | §2.1 below. Flight-critical for a FADEC diesel. |
| **§3C** Misfire, injector, cooling, lubrication, sensor drift/failure, combustion instability, overheating trends, abnormal vibration | Deep | 09 §1.2, §4, §6 |
| **§3D** Anomaly detection, RUL, trend analysis, maintenance recommendations | Deep | 09 §6–§8 |
| **§3E** Replay, environments, high altitude, endurance, hot weather | Deep | 07 Parts VI/X, 09 §12 |
| §3E **Rapid throttle transitions** | Shallow | §2.3 below |
| **§3F** Health status, alerts, maintenance advisory, mission-wise reports | Deep | 09 §7, §11 |
| §3F **Engine efficiency trends** | **Shallow** | §2.2 below |
| **§4** Prototype, architecture, simulation model, AI/ML module, dashboard, demo on simulated or real data, documentation and deployment roadmap | Adequate → Deep once built | 08 §7, 09 §15 |
| **§5** Physics-informed AI, edge AI, lightweight onboard analytics, hybrid models, federated learning, XAI, secure telemetry, autonomous maintenance advisory | Deep | 09 §5.4, §6.3, §8, §9, §10 |
| **§6** IC engines, propulsion, sensor fusion, embedded, CAN, AI/ML, visualisation, simulation, reliability | Deep | across 07–09 |

**Net result:** 3 explicitly-named items are shallow or missing. Everything else is at or beyond the ask.

---

## 2. Blind spots, each with a design

### 2.1 Electrical system: flight-critical, PS-named, and missing

✅ A FADEC needs electrical power to run the engine. If neither the alternator nor the batteries can supply it, **the engine quits**. Diesel installations carry ECU backup batteries for this reason (one type-specific example: backup batteries powering the ECUs for about 30 minutes after alternator failure), and there are accident reports of total power loss traced to the electrical system. On a spark-ignition engine with magnetos, electrical health is a convenience. **On the TAPAS diesel it is propulsion health.**

**Design.** It reuses the machinery we already have:

| Signal | Method | Why it is ours |
|---|---|---|
| Bus voltage and current at 51.2 kHz (same ADC as §2.3 of doc 09) | **Alternator ripple order analysis.** 🔶 Pulley ≈ 2.5 and 6 pole pairs give a 6-pulse rectifier ripple of about 4.5–6 kHz at 3,000–4,000 rpm. That ripple is an **engine order**, because the alternator is engine-driven. An open diode removes pulses from the pattern, the electrical analogue of a misfire, and the same angle-domain tools find it. | Same resampling and order machinery |
| Regulator field duty | **Controller effort** (principle 4): a regulator working harder to hold voltage is an early warning | Same principle as FADEC trims |
| Starter current and voltage during every start | **Every start is a battery impedance test** (ΔV/ΔI at crank). Trend internal resistance, temperature-compensated. | "Free tests" (09 §4.1) |
| Battery V/I/T in flight | Equivalent-circuit EKF for state of charge and state of health; capacity derating with cold soak at altitude | Same estimator family (09 §5) |
| FADEC backup battery | Periodic self-test; age and temperature model | — |

**Outputs**

- **P(FADEC power available until landing)**, which enters mission reliability as its own term
- A **restart-readiness index** for an in-flight or post-loiter restart at altitude. It combines battery state at cold soak, fuel temperature versus cloud point (F42), ignition delay trend (09 §4.3) and glow-system health, and answers the question MALE operators actually worry about after a long cold loiter.

### 2.2 Load path and efficiency trends (PS §3F)

- **Brake torque from shaft twist.** Doc 09 already adds a prop-shaft pickup: the twist between crank and propeller, times the coupling stiffness, gives torque. **Brake power = torque × speed.**
- **BSFC** = fuel flow ÷ brake power, trended per operating regime. This is the "engine efficiency trend" the PS asks for.
- **FMEP = IMEP − BMEP.** IMEP comes from the virtual cylinder pressure (09 §4.3) and BMEP from measured torque, so their difference is **friction**. A rising FMEP is a direct physical measure of bearing, ring and lubrication condition. 🔶 Very few monitoring systems anywhere report friction in flight.
- **Volumetric and turbo efficiency** from MAP, charge temperature and air mass, against the compressor map.
- **Propeller.** Prop-order bookkeeping (prop order = engine order ÷ gear ratio):
  - 1P (once per propeller revolution) signals imbalance
  - Blade-order changes signal damage or tracking
  - Governor hunting shows as slow rpm oscillation

  Separating propeller-caused from engine-caused vibration prevents a whole class of misdiagnosis.
- **Performance maps.** Build the CI power and BSFC map from test-cell data (VRDE) and refine it per tail by estimation. Until then, keep it as a parametrised map with labelled placeholder values.

### 2.3 Rapid throttle transitions: treat every one as an experiment (PS §3E)

A throttle step is a **free step-response test**. From each one, identify:

- The turbo spool time constant and boost overshoot against the model
- Smoke-limiter or torque-limiter intervention by the FADEC (effort again)
- Thermal time constants per cylinder
- The rail-pressure controller's recovery

Track these as health parameters: a slowing turbo response is bearing drag or fouling, and a slower thermal response is cooling degradation. The angle-domain analysis stays valid during speed ramps because it is built on angle-time cyclostationarity (09 §4.2). Transient thermal damage is already counted (F36/F37).

### 2.4 Fuel and coolant subsystems

- **Fuel (low-pressure side).** Lift-pump pressure, filter ΔP, **water-in-fuel sensor** (standard on diesels), and fuel temperature. Water in Jet-A1 is a real operational hazard, and its effect on combustion shows up in ignition delay and cycle-to-cycle variability.
- **Coolant (liquid-cooled CRDi).** Pump, thermostat, radiator/intercooler fouling and coolant level. Each is a parameter of the thermofluid UKF (09 §5.3), for example "radiator effectiveness ↓" as opposed to "cylinder-3 head cooling ↓".

### 2.5 Size, weight and power (SWaP)

A health unit that costs endurance must pay for itself. Doc 08 measured the power cost (9.5 W ≈ 0.6 min over 18 h). **Weight is not yet budgeted**, and MALE programmes are weight-sensitive.

**The fix: tiered airborne kits, so DRDO can adopt without committing to new sensors.**

| Kit | Hardware added | Gets you | Certification burden |
|---|---|---|---|
| **Kit 0** | **None.** Software reading data the FADEC already has: CAN trims and commands, crank-tooth timing if exposed, rail pressure, bus V/I | Per-cylinder injection health (trims + crank), thermal twin, electrical health, the prognostics and decision layers | Lowest: a software and data-interface change |
| Kit 1 | + 1 block accelerometer + 1 prop-shaft pickup | + combustion timing, harshness, gear/bearing, torque, BSFC/FMEP | Moderate |
| Kit 2 | Full doc 09 §2.3 suite | Everything | Highest |

🔶 **Kit 0 is the most important idea in this section.** It turns "install our sensors" into "let us read your FADEC", which is an easier request and a faster yes.

### 2.6 Indigenous and supply-chain hygiene

- ✅ **The Army cancelled contracts for 400 drones in 2025 over Chinese components**, and a stringent no-Chinese-parts, no-malicious-code mechanism now applies to military drones. [`requirements.txt`](../../requirements.txt) and the copilot use **Qwen3-4B (Alibaba)**. In front of a DRDO panel, that is a self-inflicted wound.
  - **Fix:** make the LLM optional and swappable, and default it to an Indian open model. ✅ Sarvam released Apache-2.0 open-weight models in 2026 (30B, and a 105B MoE with about 10B active), and BharatGen released Param2 (17B MoE). Or ship no LLM in the deliverable at all, since the PS does not need one.
- **Software bill of materials (SBOM)** for every dependency, with origin, and no Chinese-origin components anywhere in the delivered stack.
- **Indigenous compute path.** ✅ C-DAC's VEGA AS2161 "DHRUV64" is a 1 GHz dual-core 64-bit RISC-V processor designed in India; SHAKTI (IIT Madras) targets strategic applications. 🔶 The 0.3 GFLOP/s DSP core (09 §9) is tight for DHRUV64 alone. The credible design is an **FPGA front end** (filtering, resampling, FFT) with **VEGA running the deterministic estimators and decision logic**. That lets us say the certifiable core runs on Indian silicon. The PS asks for an *indigenous* framework, and this is the strongest possible answer.

### 2.7 Who needs this first: the indigenous engine's qualification

- ✅ Reporting on TAPAS repeatedly names the engine as a key weakness. The programme moved from a 115 hp Rotax to a 180 hp Austro from prototype AF-5, and the 180 hp VRDE CRDi is now entering flight trials.
- **A brand-new engine has no fleet history.** It is in its infant-mortality and qualification phase. The Day-1 user is therefore not a squadron. It is **VRDE's test cell and ADE's flight-test team**.
- 🔶 The pitch should lead with this: **"ANUMAAN helps the indigenous engine get qualified faster and fly its trials safer."**
  - Endurance-run monitoring with automatic anomaly capture
  - Per-cylinder combustion data for FADEC calibration
  - Flight-test telemetry watch

  Fleet health management is the follow-on once the engine is in service.

### 2.8 Platforms actually in Indian service

| Platform | Engine | Our config |
|---|---|---|
| TAPAS BH-201 (ADE) | VRDE 2.2 L CRDi, 180 hp ✅ | ❌ Add `vrde_2p2_crdi` (08 §6.2) |
| Heron Mk I (IAF/Army/Navy) | Rotax 914 ✅ | ✅ Exists |
| **Heron Mk II** (IAF in the northern sector; Army in the Tawang sector) | **Rotax 915 iS**: 1,352 cc turbo, 141 hp take-off, TBO 1,200 h ✅ | ❌ **Add `rotax_915is`.** It is the in-service piston MALE engine that a repository with a 914 config does not yet cover. |
| Archer-NG (ADE; maiden flight reported Oct 2025) | Not public | Config slot reserved |

**One twin, three engine classes in Indian service:** that is the "scalable and modular" requirement (SYS-02/03) demonstrated rather than claimed. 🔶 Beyond UAVs, VRDE's core business is military vehicles, so the same CRDi health core applies to vehicle and genset diesels. That is a scale-of-impact argument, clearly labelled as future scope.

### 2.9 Impact economics

SIH scores "scale of impact", and DRDO funds things with a cost case. We have no economic model yet. Build a **transparent, parametrised** one; DRDO fills in the real values:

- **Availability:** unscheduled removals avoided, and sorties saved
- **Asset risk:** P(engine-caused loss) × airframe-plus-payload value, before and after
- **No-fault-found reduction:** maintenance hours and spares
- **On-condition maintenance against fixed TBO** (for example the 915 iS's 1,200 h): overhauls driven by measured condition rather than the calendar

Every input is a labelled range, and the output is a sensitivity chart ("the case holds if X > …"), never a single invented figure.

### 2.10 The adoption path: ground first

| Step | Needs flight airworthiness clearance? | Instrument |
|---|---|---|
| 1. **Portable ground diagnostic kit.** Laptop + DAQ + clamp-on accelerometer + FADEC cable. Runs the cut-out test, cranking compression, battery test and vibration signature in about 15 minutes on the flight line. | **No** | Direct lab trial |
| 2. **Test-cell monitoring tool** at VRDE | **No** | Lab collaboration |
| 3. Airborne Kit 0 (software) | Software/data interface only | Programme change |
| 4. Airborne Kit 1/2 | Yes (CEMILAC) | Programme change |

**Funding after the hackathon.**

- ✅ **iDEX** grants up to ₹1.5 crore to startups and MSMEs.
- ✅ DRDO's **Technology Development Fund** covers up to 90 % of project cost (capped at ₹50 crore) for industry.

Both require an entity (a startup or MSME), which is a decision to make deliberately, not something to discover after winning.

### 2.11 The SIH format itself

- ✅ The grand finale is a **36-hour build and demo**. Judges score 1–20 across weighted criteria (novelty, complexity, clarity, feasibility, practicability, sustainability, impact, user experience, future potential) totalling 100, and they **favour a stable working prototype**.
- 🔶 **Our risk profile:** novelty and complexity are very high; feasibility and practicability will be *perceived* as risky unless the demo proves them. Everything that proves feasibility (HIL on a real board, one real-engine recording, a judge-driven blind test) is worth more points than any additional feature.
- **The 36 hours are for extending a working system**, not for building one. Arrive with the vertical slice done, and use the finale to add a fault family or run the judges' blind test live.

---

## 3. What the panel will ask, and whether we can answer

| Question | Answer | Evidence available |
|---|---|---|
| "Where is your real data?" | ACES real Rotax 914 flight (false-alarm rate on real healthy hours); public diesel/bearing sets; **our lab-rig recording**; the validation kit for their data | ACES now; the rest after S7 / 08 Phase 2 |
| "Will this work on *our* engine?" | Engine class is configuration; the VRDE config lists exactly which constants we need from them | After the config is written |
| "How do you get FADEC data?" | Kit 0 needs trims, crank timing, rail pressure and bus V/I on the FADEC's CAN or debug interface. **That is our ask.** | Design, and an ICD draft |
| "False-alarm rate?" | Per flight hour, with a 95 % upper bound, simulation Monte Carlo + ACES | After 08 Phase 1 |
| "Why not better thresholds?" | The P-F curve, plus our measured case: the FADEC masks injector faults from temperatures, and the trim and crank channels see them | Harness today; trim monitor after S1–S2 |
| "What does it weigh, and what does it cost in endurance?" | Kit 0 adds nothing; power cost measured | Needs the SWaP table (§2.5) |
| "Is it certifiable?" | Advisory-only; deterministic core; ML gated by runtime monitors; GSN safety case; low DO-178C level | Documented |
| "What if the link is jammed?" | Onboard analysis continues; events are queued; full raw record kept on the SSD | Built (edge) / design (SSD) |
| "Why trust the ML?" | ML is evidence, not the decision; physics parameters decide; shadow mode before promotion | Design |
| "What is new compared with rotorcraft HUMS?" | HUMS does drivetrain vibration. We add **combustion reconstruction, FADEC-effort monitoring, per-cylinder peer referencing and active diagnosis**, for a piston engine | Design; lab rig proves it |
| "Is anything Chinese in your stack?" | **Today: yes (Qwen). Must be fixed before any presentation.** | Fix is trivial |
| "What do you need from us?" | FADEC data interface (Kit 0), engine constants, test-cell access for pressure-transducer calibration | This list, in writing |

🔶 **The last row matters most.** A team that ends by asking for a specific, bounded collaboration is proposing a project. A team that ends on a demo is finishing a competition.

---

## 4. What to do with this

1. **Stop broad brainstorming.** The architecture is complete enough. Fold §2 into the build as addenda to 09, not as a new round of research.
2. **Fix the red flag now:** swap Qwen out of the default configuration.
3. **Add three engine configs:** `vrde_2p2_crdi` (with unknowns labelled), `rotax_915is`, and a reserved slot for Archer-NG.
4. **Build in the order of 08 §7 and 09 §15**, with two additions pulled forward: the **electrical channel** (cheap, PS-named, reuses the order machinery) and **Kit 0 as the headline deployment story**.
5. **Three answers from you decide the scope:**
   - (a) The exact SIH dates: submission, shortlisting, finale.
   - (b) Whether you can get time on an engine test rig (college IC-engine lab or similar).
   - (c) Team size and who owns which layer.

---

## Sources (checked 23 September 2026)

- SIH format and criteria: [SIH official](https://sih.gov.in/) · [SIH 2026 guide (finale format, judging)](https://reskilll.com/blogs/smart-india-hackathon-2026-complete-guide-registration-themes-winning/) · [SIH evaluation guideline (2023)](https://www.scribd.com/document/712193023/Evaluation-Guideline-for-Smart-India-Hackathon-2023) · [SIH 2025 guidelines](https://www.slideshare.net/slideshow/smartindiahackathonfor-2025-guidelines-s/282732503)
- FADEC electrical dependency: [PPRuNe — FADEC and battery](https://www.pprune.org/tech-log/310164-fadec-battery.html) · [General Aviation News — alternator off, total loss of engine power](https://generalaviationnews.com/2020/09/30/flying-with-alternator-switched-off-results-in-total-loss-of-engine-power/) · [AAIB report, DA42 NG G-HAKA](https://assets.publishing.service.gov.uk/media/60c229a68fa8f57cf12e6115/DA_42_NG_G-HAKA_07-21.pdf)
- Chinese components: [The Week, Jan 2025](https://www.theweek.in/news/defence/2025/01/29/no-chinese-parts-indian-army-signs-contract-to-secure-highly-advanced-reliable-indigenous-drones-from-ig-drones.html) · [Defense Mirror](https://defensemirror.com/news/38781) · [SSBCrack, Feb 2025](https://www.ssbcrack.com/2025/02/government-scraps-400-defence-drone-contracts-over-use-of-chinese-components.html) · [Inquirer](https://newsinfo.inquirer.net/1813810/india-bars-makers-of-military-drones-from-using-chinese-parts)
- Indian models: [Sarvam AI](https://en.wikipedia.org/wiki/Sarvam_AI) · [Sarvam-105B](https://www.buildfastwithai.com/blogs/sarvam-105b-india-s-open-source-llm-for-22-indian-languages-2026) · [BharatGen Param2 (Digit)](https://www.digit.in/features/general/bharatgen-param-2-sarvamai-and-the-rise-of-indian-llm-models-so-far.html)
- Indigenous processors: [VEGA AS2161 DHRUV64 (CNX)](https://www.cnx-software.com/2025/12/16/vega-as2161-dhruv64-a-1ghz-dual-core-64-bit-risc-v-microprocessor-designed-in-india/) · [C-DAC VEGA](https://vegaprocessors.in/) · [SHAKTI (Insights)](https://www.insightsonindia.com/2025/02/12/shakti-semi-conductor-chips/)
- TAPAS engine history: [DRDO Rustom (Wikipedia)](https://en.wikipedia.org/wiki/DRDO_Rustom) · [Air Power Asia](https://airpowerasia.com/2022/09/20/tapas-rustom-ii-indias-high-end-miltary-drone/) · [T2COM — India's UAV development struggles](https://oe.t2com.army.mil/product/indias-uav-development-struggles-to-take-off/)
- Heron Mk II: [Janes — IAF inducts Heron Mk II](https://www.janes.com/osint-insights/defence-news/air/indian-air-force-inducts-heron-mk-ii) · [IAI Heron (Wikipedia)](https://en.wikipedia.org/wiki/IAI_Heron) · [Indian Army inducts Heron Mk II](https://www.indiandefensenews.in/2022/09/indian-army-inducts-2-heron-mk-ii-uavs.html?m=1)
- Archer-NG: [idrw](https://idrw.org/archer-ng-indias-advanced-male-uav-gears-up-for-maiden-flight/) · [SSBCrack — maiden flight](https://ssbcrackexams.com/drdos-archer-ng-uav-achieves-maiden-flight-advancing-indias-indigenous-drone-development/)
- Funding: [iDEX](https://idex.gov.in/) · [DDP — iDEX](https://www.ddpmod.gov.in/offerings/schemes-and-services/idex) · [DRDO TDF](https://tdf.drdo.gov.in/)
- Competitor repositories confirmed by search today: [Mehak2513kaur](https://github.com/Mehak2513kaur/sih26054-digital-twin) · [Ash180905](https://github.com/Ash180905/AEROTWIN-AI) · [Dronanetra](https://github.com/Jyotirmoy-006/Dronanetra) · [atharv20s](https://github.com/atharv20s/sih-26) · [VIKASHL25](https://github.com/VIKASHL25/SIH-26) · [panditharshpandey1-gif/aerotwin-uav](https://github.com/panditharshpandey1-gif/aerotwin-uav) (not yet in `competitors/`)

*Audit set: [`README.md`](README.md) · [`08`](08_deployable_system_blueprint.md) (integration) · [`09`](09_full_depth_architecture.md) (full depth) · this document (red team).*
