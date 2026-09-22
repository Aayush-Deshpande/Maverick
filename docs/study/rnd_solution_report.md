# Independent R&D Report — PS-26054, examined from first principles

*Written as if we were the engineering team starting today, with no obligation to the architecture already in this folder. Existing study material was read, then deliberately set aside and re-derived. Where I reach the same conclusion, I say so and say why. Where I disagree, I say that too.*

**Evidence labels** follow this folder's convention: ✅ sourced · 🔶 my engineering inference · ⬜ my proposal · ❌ recommend against.

---

## 0. The finding that should change our strategy

Before any architecture discussion, one empirical result.

✅ **Other SIH teams are building this problem statement in public, and they have independently converged on the same architecture this folder recommends.** I read their repositories:

| Team repo | Stack | Models | Physics | RUL |
|---|---|---|---|---|
| [sih26054-digital-twin](https://github.com/Mehak2513kaur/sih26054-digital-twin) | FastAPI · React · TimescaleDB · WebSocket | IsolationForest + RandomForest + feature-attribution XAI | Rotax 914/915 thermodynamic "expected state" → residuals | vs. 500 h TBO with thermal/vibration acceleration factors |
| [TwinProp-DX](https://github.com/Monika-Srinithi/TwinProp-DX) | Physics-informed DT platform | fault diagnosis + RUL | Rotax 914 F | mission replay |
| [AEROTWIN-AI](https://github.com/Ash180905/AEROTWIN-AI) | real-time DT | predictive maintenance | aero piston | in-flight mission reliability |
| Several more | FastAPI/React/MQTT | IsolationForest | Rotax-class | TBO-based |

Compare against [`22_final_recommendation.md`](22_final_recommendation.md): Rotax 912 iS class · residuals from a thermodynamic model · EWMA/Mahalanobis/PCA → ensemble + autoencoder · Random Forest classifier · TimescaleDB · FastAPI + WebSocket → React + Three.js.

**These are the same system.** That is not a criticism of the reasoning in this folder — the reasoning is sound, and its soundness is precisely why everyone lands there. It is the *correct convergent baseline*. But a correct convergent baseline is, by definition, not a differentiator. Eight teams demoing the same dashboard to the same panel is a coin-flip.

🔶 **Strategic conclusion:** treat the existing architecture as the **floor, not the plan**. It must be built, because without it we have no system. Everything that decides the outcome sits in what we add on top of it, and this report is mostly about that.

---

## 1. What the problem statement is actually asking

### 1.1 Explicit requirements (non-negotiable)

Directly enumerated in [the PS](../00_official_problem_statement.md): DT core framework · health monitoring over 8 named parameter groups · fault detection over 8 named fault targets · AI/ML layer (anomaly, RUL, trend, maintenance recommendation) · simulation & replay (4 named mission regimes) · visualization dashboard. Deliverables: working prototype · architecture design · engine simulation model · anomaly detection module · dashboard · demonstration on simulated *or real* data · documentation + deployment roadmap.

### 1.2 What is implicit but expected

These are not in the requirement list, and they are where marks are quietly won or lost.

**"Indigenous framework."** ✅ The PS background says the aim is to "develop an indigenous Digital Twin framework." 🔶 This implies no hard dependency on foreign cloud services and an ability to run air-gapped. ⬜ Our system should run entirely offline on one machine, and we should say so explicitly. This is nearly free for us and is a real procurement consideration.

**Three deployment targets, not one.** ✅ The PS says the framework should be designed "considering future deployment in defence-grade Ground Control Stations (GCS), **engine test rigs**, and **fleet-level** health monitoring infrastructures." 🔶 This is the most-ignored sentence in the document. A test rig has no telemetry link and unlimited bandwidth; a GCS has a kbps lossy link; fleet level has many engines and cross-engine baselines. If our core only works in the single-UAV-over-a-bad-link case, we have satisfied one of three stated deployment contexts. ⬜ The twin core must therefore be decoupled from the transport and from the assumption of a single engine — an architectural requirement, not a feature.

**"Transitions from conventional threshold-based monitoring."** ✅ Section C's wording. 🔶 This is an implicit instruction to *compare against that baseline*, which almost nobody will do. See §9.

**Sensor drift/failure is listed alongside seven engine faults.** 🔶 It is categorically different from the other seven and the PS does not flag that. See §5.2 — I consider this the single highest-value technical insight in this report.

### 1.3 Genuine ambiguities, and how I would resolve them

| Ambiguity | Resolution | Why |
|---|---|---|
| No engine named | ⬜ Rotax 912 iS / 914 class, explicitly labelled as our assumption | ✅ Rotax 912 series is documented publicly and is genuinely used in military UAVs ([Rotax 912](https://en.wikipedia.org/wiki/Rotax_912)). 🔒 TAPAS's actual engine bus is not public and we must never assert it |
| "Real-time" undefined | ⬜ Define it per-loop with numbers: 20 Hz twin update, <100 ms edge detection latency, <1 s dashboard refresh | An undefined "real-time" claim is unfalsifiable; a numeric one is testable |
| "Simulated or real datasets" permitted | ⬜ Simulated primary, but validate *methods* on real public data | See §8.3 — this is our main credibility hedge |
| Cloud vs local | ⬜ Local. See "indigenous" above | |

### 1.4 ⚠️ A factual item to verify before anyone presents it

🔶 The 135 °C CHT limit used in [`01_big_picture.md`](01_big_picture.md) needs a primary-source citation. Public Rotax material indicates the CHT measurement configuration *changed*: ✅ a maximum of 150 °C under the old sender configuration, moving to a 120 °C coolant-temperature limit with newer cylinder heads ([SB-912-066 / sender position change](https://rotaxnews.net/?p=927), [Rotax service instruction](https://legacy.rotaxowner.com/si_tb_info/serviceinfo/si-912-020-r10.pdf)). Depending on variant and sender location, 135 °C may or may not be the right number. A propulsion engineer on the panel will know this cold. **Action: cite the specific operators' manual for the specific variant, or change the number.**

---

## 2. State of the field — what I found, and what is newly possible

### 2.1 Established and mature (do not claim as novel)

- ✅ **Analytical redundancy for sensor fault detection** — comparing a sensor against a model-based reconstruction rather than a duplicate sensor. Dates to NASA work on jet engines ([NASA TM 1984](https://ntrs.nasa.gov/api/citations/19840016517/downloads/19840016517.pdf)), matured into Kalman-filter-bank approaches that explicitly *distinguish sensor faults from component faults* ([bank of Kalman filters](https://www.researchgate.net/publication/24285913_Aircraft_Engine_SensorActuatorComponent_Fault_Diagnosis_Using_a_Bank_of_Kalman_Filters)), and still an active area ([online learning FDIR for aero-engine sensors, 2025](https://www.sciencedirect.com/science/article/abs/pii/S1270963825003128)).
- ✅ **Gas-path/residual-based diagnostics, sparse coding, HDC** — already correctly documented as mature in [`20_novelty_and_research.md`](20_novelty_and_research.md). That self-correction is good work; keep it.
- ✅ **Physics-informed ML for turbine digital twins** — a review-level field already ([Physics-Informed ML for Gas Turbine Digital Twins review, 2025](https://www.preprints.org/manuscript/202509.1360)).

### 2.2 Recently practical — the genuine opportunities

**⬜ Conformal prediction for RUL intervals.** ✅ Conformal prediction gives *distribution-free, finite-sample coverage guarantees* — the predicted interval contains the true RUL with a pre-specified probability under mild assumptions. It is now well-published for exactly our task: [Conformal Prediction Intervals for RUL](https://papers.phmsociety.org/index.php/ijphm/article/view/3417), [uncertainty-aware bearing RUL via CP (2026)](https://papers.phmsociety.org/index.php/phme/article/view/4902), and [isotonic-calibrated split-CP validated on C-MAPSS (2026)](https://www.sciencedirect.com/science/article/pii/S0951832026005740). 🔶 This matters because this folder already asserts that "RUL without an uncertainty bound is decoration" — conformal prediction is the principled way to produce that bound, and crucially it produces a **measurable** claim: empirical coverage vs. nominal coverage on held-out data. That is a number a panel can check.

**⬜ Time-series foundation models as a baseline to beat.** ✅ Chronos, TimesFM, Moirai are production-viable zero-shot forecasters as of 2026, with anomaly-detection derivatives ([ChronosAD](https://arxiv.org/pdf/2606.01300), [zero-shot multivariate TSAD](https://arxiv.org/html/2607.12454), [TimesFM for predictive maintenance](https://blog.pebblous.ai/report/timesfm-industrial-forecasting/en/)). 🔶 **Caution:** running a TSFM on telemetry generated by our own physics simulator and reporting a good score proves nothing — the simulator is smooth and learnable. ⬜ The rigorous use is as a **strong generic baseline our physics-informed approach must outperform**. "Our hybrid beat a 2026 foundation model on detection lead time" is a real experimental result; "we used a foundation model" is a buzzword.

**⬜ Mission-aware RUL.** ✅ Published and directly on point: RUL "should be considered as dependent on how a system is expected to be used," and critically, *missions of similar duration but different command characteristics produce substantially different RUL* ([Mission-Aware RUL, PHM Society European Conference](https://papers.phmsociety.org/index.php/phme/article/view/4888)). See §4 — this is the centrepiece of my recommendation.

**⬜ Differentiable physics.** 🔶 Not new as a technique, but newly trivial to adopt. See §3.2.

---

## 3. Architecture — where I agree, and the one place I do not

The eight-layer decomposition in [`15_system_architecture.md`](15_system_architecture.md) is well-reasoned and I would keep its shape. Three modifications.

### 3.1 ⬜ Modification 1 — elevate sensor validation to its own layer

Currently sensor drift/failure is one of eight classifier outputs, behind a "validity gate." 🔶 That is backwards. Every downstream conclusion — residual, anomaly score, health index, RUL — is computed *from* sensor values. If a thermocouple drifts and we route that into the twin, the twin confidently reports an engine fault that does not exist. **A false "overheating" alarm that aborts a sortie is a mission kill caused by our own system.**

⬜ Sensor validation must therefore sit **between ingestion and the twin**, as a first-class layer with its own output: a per-channel trust state (`VALID / SUSPECT / FAILED / RECONSTRUCTED`). Method: ✅ analytical redundancy — reconstruct each channel from the others plus the physics model, and compare. A drifting CHT#2 is distinguishable from a genuinely hot cylinder #2 because a real cooling fault *also* perturbs EGT#2, coolant ΔT, and the cylinder's vibration signature, whereas a drifting sensor perturbs exactly one channel with no physical correlate.

That last sentence is the whole system in miniature, and it is a genuinely strong demo (§9, S3).

### 3.2 ⬜ Modification 2 — make the physics model differentiable

This is my main technical disagreement with [`16_tech_stack.md`](16_tech_stack.md), which chooses NumPy/SciPy.

🔶 Write the thermodynamic model in **JAX or PyTorch** instead. The model stays the same equations, the same pure function, the same explainability — but it becomes differentiable, and three capabilities fall out for almost no extra work:

1. **Per-tail-number calibration by gradient descent.** Fit the model's constants (cooling effectiveness, volumetric efficiency, thermal masses) to *this specific engine's* first hours of healthy data. 🔶 This is what "digital twin" actually means — a twin of *this* engine, not of the engine type. Without it we have a generic simulator with a live data overlay, which is what the convergent baseline is. Hand-tuning constants does not scale and is not defensible; optimising them is both.
2. **Sensitivity analysis for free.** ∂residual/∂parameter tells us which physical parameter best explains an observed deviation — which is *physically grounded* fault isolation, not feature attribution over abstract columns.
3. **A clean path to hybrid physics+ML.** A learned residual term trained jointly with the physics, rather than bolted on.

⬜ Cost: the model must be written in array-style with no Python control flow on data. That is a mild discipline, not a rewrite. Recommend JAX for `grad``jit` ergonomics, with NumPy fallback if the team finds it awkward.

### 3.3 ⬜ Modification 3 — add a mission-reliability layer above RUL

See §4. RUL is an input to it, not the final output.

### 3.4 The resulting stack

```
L9  OPERATOR / DECISION      go–no-go · advisory · replay · reports
L8  PRESENTATION             dashboard · 3D diagnostic view · alerts        (zero logic)
L7  MISSION RELIABILITY  ★   mission-conditioned survival P · limiting factor · what-if
L6  PHM ANALYTICS            anomaly ensemble · fault isolation · health indices
                             RUL + CONFORMAL interval
L5  DIGITAL TWIN CORE    ★   differentiable physics · residuals · state estimate
                             per-tail calibration · degradation history · uncertainty
L4  SENSOR VALIDATION    ★   analytical redundancy · per-channel trust state
L3  INGESTION                adapters · canonical schema · time align · gap marking
L2  COMMUNICATION            framing · configurable latency/loss/bandwidth
L1  EDGE                     vibration features · residuals · light anomaly · log · events
                             MUST RUN WITH L2 DEAD
L0  DATA SOURCE              synthetic generator │ CAN replay │ live CAN
★ = my additions/changes relative to the existing design
```

---

## 4. The differentiator: mission reliability as the system's actual output

✅ The PS title is "*Health Monitoring, Fault Prediction and **Mission Reliability Enhancement***." 🔶 Every implementation I looked at — including ours — treats the first two as the product and the third as a dashboard label. The third is the one in the title.

### 4.1 The reframe

| Conventional output | What a commander can do with it |
|---|---|
| "RUL = 47 flight hours" | Not much. Is that enough for tonight's sortie? Depends on the sortie |
| ⬜ "P(complete this 18 h Ladakh ISR profile without propulsion-limiting event) = **0.83**, 80% CI [0.71, 0.91]. Limiting factor: cylinder-3 cooling margin during the 04:00–07:00 climb segment. Same engine on the 6 h coastal profile: **0.98**" | That is a decision |

✅ This is supported, not invented: mission-aware RUL research finds that *missions of similar duration but different command characteristics produce substantially different degradation*. ✅ And the PS itself names the four regimes to evaluate — high altitude, endurance, hot weather, rapid throttle transitions — which is effectively a specification for mission descriptors.

### 4.2 ⬜ How to build it

1. **Mission descriptor** — encode a planned sortie as a time-series of operating points (altitude, OAT, power setting, throttle-transition rate, duty cycle), not a scalar duration.
2. **Roll the twin forward** under that profile using the *same* physics model (this is why L7 and L5 must share code — a separate simulator would be a second source of truth and a guaranteed inconsistency).
3. **Propagate degradation**, not just state: current degradation parameters evolve along the profile at profile-dependent rates.
4. **Propagate uncertainty** via Monte Carlo over the calibrated parameter posterior + conformal RUL intervals → a *distribution* of outcomes, not one trajectory.
5. **Output**: P(success), the binding constraint, and the flight-time at which margin is first violated.

🔶 **Why this is defensible rather than a gimmick:** it is the literal PS title, it is grounded in published mission-aware prognostics, it reuses the physics model we already need, and it converts our output from a number an engineer must interpret into a decision an operator can take. It is also *very* hard to fake, which is exactly what we want in a differentiator.

---

## 5. Component-level reasoning

### 5.1 Physics / twin core

| | |
|---|---|
| **Does** | Computes expected engine state given operating point; maintains per-tail calibrated parameters; emits residuals with uncertainty |
| **Inputs** | Validated telemetry, operating point (alt/OAT/RPM/MAP/throttle), calibrated parameters |
| **Outputs** | `TwinState`: expected values, residuals, parameter estimates + covariance, staleness, provenance |
| **Approach** | ⬜ **Hybrid.** Physics (differentiable, JAX) as the backbone; a small learned correction term for effects we do not model well. Not pure-ML (unexplainable, needs data we lack), not pure-physics (will not match a real engine's quirks) |
| **Data** | Our synthetic generator; ✅ Rotax published performance data for sanity-checking curves |
| **Validation** | Residuals on healthy data must be zero-mean and within sensor noise. If they are not, the model is wrong and every downstream number is contaminated. ⬜ This should be a CI test, not a one-off check |
| **Difficulty** | Medium-high. The highest-leverage work in the project |

### 5.2 Sensor validation — the underrated component

| | |
|---|---|
| **Does** | Decides, per channel, whether to trust the measurement; reconstructs failed channels |
| **Approach** | ✅ Analytical redundancy: model-based reconstruction + cross-channel physical consistency. 🔶 A Kalman-filter bank is the classical solution; a simpler residual-consistency test is likely adequate at our fidelity and far easier to explain |
| **Why it matters** | Without it, a drifting sensor produces a confident false engine-fault. With it, we produce the *correct and much more impressive* output: "CHT#2 sensor is drifting; engine is healthy; here is the reconstructed value" |
| **Difficulty** | Medium. Disproportionate credibility return |

### 5.3 Anomaly detection

⬜ Layered, and I agree with the existing design here: always-on statistical baseline (EWMA/Mahalanobis on residuals) + learned layer (autoencoder/ensemble) on top, with the statistical layer as the fallback when the learned layer is unavailable or out of distribution. 🔶 Operating on **residuals rather than raw values** is the single most important choice and this folder already makes it — it is what makes detection altitude- and power-invariant.

⬜ Add: an explicit **UNKNOWN / novel-anomaly** path. A classifier forced to choose among 8 known faults will confidently mislabel the 9th. Being able to say "anomalous, not matching any known signature" is both honest and, for a defence panel, reassuring.

### 5.4 RUL

⬜ **Tiered, ship the baseline first:**
1. **Baseline** — degradation-trend extrapolation with conformal intervals. Boring, robust, explainable, and it *works*.
2. **Particle filter** — physics-state-based degradation propagation; naturally produces distributions; handles nonlinear degradation.
3. **Learned (GRU/Transformer)** — ⬜ only adopt if it beats the baseline on a properly split validation set. ✅ Multi-sensor-fusion transformer RUL for UAV engines is current ([Drones 2026](https://www.mdpi.com/2504-446X/10/9/705)), so it is a legitimate option — but a learned model that loses to trend extrapolation and gets shipped anyway is a failure of engineering discipline.

⬜ **In all tiers: conformal intervals**, and report empirical coverage. See §2.2.

### 5.5 Explainability

❌ **Do not ship SHAP-over-feature-columns as the explanation.** 🔶 "Feature 14 contributed 0.31" is meaningless to a propulsion engineer.

⬜ Explanations must be **physical**: named component, named cylinder, named engine order, with the corroborating evidence chain. Target output format:

> **Cooling degradation, cylinder 3, medium severity (confidence 0.86).**
> Evidence: CHT#3 residual +31 °C (others < ±6 °C) · coolant ΔT across #3 reduced 18% · order-2 vibration +2.7 dB · onset gradual over 41 min.
> Ruled out: sensor drift (EGT#3 and coolant ΔT corroborate, so not a single-channel fault).
> Recommended: reduce MAP to 26 inHg; expected CHT#3 recovery 12 °C within 4 min.

🔶 That "ruled out" line is what separates a diagnostic system from a classifier.

---

## 6. Simulation and visualization

### 6.1 The simulator is the ceiling — treat it as the primary technical risk

🔶 Every number we present is downstream of the generator. If the ML learns the simulator's artifacts rather than engine physics, we have built a very sophisticated tautology. [`17_simulation_design.md`](17_simulation_design.md)'s core rule — *faults modify physical parameters, never output signals* — is exactly right and is the main defence. ⬜ I would add four more:

1. **Hold out severities and operating points**, not just time windows. Train on mild+severe, test on moderate; train at low altitude, test at high.
2. **Train on sim-A, test on sim-B** — a second generator configuration with perturbed engine constants, different noise characteristics, different sensor placement. Generalising across that gap is evidence the model learned physics.
3. **Realistic sensor imperfection**: quantisation, thermocouple lag, cold-junction error, CAN dropouts, clock skew. A model trained on clean data will fail on real data in ways we will not have predicted.
4. **Validate detectors on real public data too** — see §8.3.

### 6.2 Visualization — my call on Blender

⬜ **Blender is the right authoring tool and the wrong runtime.** Use it offline to model/bake the engine, exploded views, and animation clips; export GLB; run it in the browser with Three.js / react-three-fiber. Reasons: the GCS must run on an operator's machine in a browser at interactive framerate alongside charts, with no Blender install and no render farm. ✅ The repo already contains `three.min.js` and GLB assets under `site/`, so this is already the de facto direction — I would make it explicit and rule out Blender-in-the-loop at runtime. 🔶 Exception: pre-rendered cinematic shots for the pitch video, where Blender genuinely wins.

### 6.3 What the 3D view must show to earn its place

🔶 **The test: if the 3D view shows nothing the charts cannot, it is decoration and the panel will read it as decoration.** A rotating engine is decoration.

⬜ It earns its place by showing *spatial* information that is genuinely hard to read from time series:

- **Per-cylinder residual colour mapping** — not absolute temperature (that is just a gauge), but *residual*, so a cylinder glows only when it deviates from what physics expects at this altitude and power. A pilot's "which cylinder" question answered instantly.
- **Fault localisation highlight** — the classifier's output rendered onto the actual component (that baffle, that injector, that bearing).
- **Degradation ghost** — a translucent overlay showing predicted state at mission end vs. now, so degradation *rate* becomes visible spatially.
- **Sensor trust overlay** — failed/suspect sensors visibly marked on the engine, which makes the §5.2 capability legible at a glance.
- **Mission-conditioned replay** — scrub the mission timeline and watch thermal state and degradation evolve over the 3D model.

⬜ Normal vs. degraded should differ in *behaviour*, not just colour: vibration amplitude in the animation, exhaust pulse regularity for misfire, coolant flow visualisation for cooling faults.

---

## 7. Backend

🔶 The existing choices (FastAPI, WebSocket, TimescaleDB→Parquet, UDP for the simulated link, explicit rejection of Kafka) are sound and well-argued. I would not relitigate them; they are boring in the right way. Three additions:

1. ⬜ **Twin state as an explicit versioned schema** with provenance and staleness on every field, not an ad-hoc dict. Everything consumes it, so it is the system's real API.
2. ⬜ **Deterministic replay as a first-class capability** — same input log + same model versions ⇒ bit-identical output. This is required for post-flight analysis to be trustworthy (the PS asks for replay), and it makes our own debugging tractable.
3. ⬜ **Signed telemetry frames.** ✅ "Secure telemetry architecture" is a listed innovation area. 🔶 A spoofed or replayed health feed is a genuine attack surface on a UAV — an adversary who can inject "all nominal" defeats the entire system. HMAC per frame + sequence-window replay rejection is perhaps 40 lines and demos in 20 seconds (inject a forged frame, watch it get rejected). Very high credibility-per-hour.

---

## 8. Risks, honestly

| Risk | Severity | ⬜ Mitigation |
|---|---|---|
| **Models learn the simulator, not the engine** | **Critical** | §6.1's four rules; sim-A→sim-B generalisation test; validate methods on real public data |
| Convergent architecture = no differentiation | **Critical** | §4 mission reliability; §5.2 sensor validation; §9 quantified baseline comparison |
| Panel asks "how do you know this works on a real engine?" | High | Answer honestly and in advance: we do not, and we say so. We show (a) method validated on real public datasets, (b) physics validated against published Rotax curves, (c) a stated plan for test-rig validation. ✅ The PS explicitly permits simulated data |
| Scope sprawl (LLM copilot, voice, RAG) | High | §10 — cut or constrain |
| 135 °C and similar unsourced constants | Medium | §1.4 — audit every numeric claim for a primary source |
| Learned RUL underperforms trend baseline but ships anyway | Medium | Pre-commit to the selection rule: baseline ships unless the learned model wins on a properly split set |
| Demo hardware fails on the day | Medium | §11 — hardware is strictly optional and swaps out to pure software |
| Over-claiming novelty | Medium | [`20_novelty_and_research.md`](20_novelty_and_research.md) already handles this well. Keep that discipline |

### 8.3 ⬜ The credibility hedge worth building

🔶 Our biggest structural weakness is that we generate our own data and then score well on it. The strongest available answer: **run the same detection and RUL methods, unchanged, on real public datasets** — ✅ C-MAPSS for RUL method validation ([NASA PCoE](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/)), bearing datasets for vibration methods, SKAB for multivariate anomaly detection. We then say precisely: *"the machine is simulated; the methods are validated on real data."* That sentence survives hostile questioning. "Our accuracy is 99% on our own simulator" does not.

---

## 9. Demonstration design — make it measurable, not pretty

🔶 The panel has seen dashboards. The scarce thing is *evidence*. Every scenario below produces a number, and the baseline is the PS's own straw man: the threshold comparator.

| # | Scenario | What it proves | Metric |
|---|---|---|---|
| **S1** | Nominal high-altitude cruise, extended run | We do not cry wolf | **False alarms per flight hour** (the metric nobody shows) |
| **S2** | Slow cooling degradation to limit | Predictive, not reactive | **Detection lead time vs. threshold baseline** — "detected 23 min before the comparator would have." This is the money metric and it is exactly what the PS asks for |
| **S3** | **Sensor drift on CHT#2, engine healthy** | We distinguish sensor from engine | We say SENSOR; **baseline false-alarms and would abort the sortie.** The strongest single moment in the demo |
| **S4** | Link blackout mid-fault, then restore | The edge split is real | Edge keeps detecting through blackout; GCS backfills from onboard log on reconnect |
| **S5** | Same engine, two mission profiles | Mission reliability (the PS title) | Different P(success) and different limiting factors from identical engine state |
| **S6** | Rapid throttle transitions (PS-named) | Context-awareness | No false alarm on transient; baseline trips |
| **S7** | Novel fault not in training set | Honesty under novelty | Flags UNKNOWN rather than confidently mislabelling |

⬜ **Metrics to report** (these signal domain literacy immediately): prognostic horizon · α-λ accuracy · asymmetric RUL score (late penalised harder, per PHM08 convention) · macro-F1 with UNKNOWN · false alarms/hour · **empirical coverage of conformal intervals vs. nominal**.

⬜ **Ablation table** — physics-only vs. ML-only vs. hybrid, on the same scenarios. This demonstrates the hybrid choice was *tested*, not assumed, and it is the kind of table that reads as engineering rather than marketing.

---

## 10. What to cut or constrain

🔶 More features is not a better solution. Three candidates in the current repo:

**Voice interface** (`backend/voice`, `Voice/`) — ❌ **Cut.** Not requested anywhere in the PS. Operationally dubious in a noisy GCS. Consumes effort and adds no engineering credibility. The strongest argument for it is that it demos well, which is the weakest kind of argument in front of a technical panel.

**LLM copilot / RAG** (`backend/agent`, `Qwen3-4B`) — 🔶 **Constrain sharply, do not cut.** ✅ "Autonomous maintenance advisory systems" *is* a listed innovation area, so an advisory generator is defensible. But free-form generation about maintenance actions on a defence platform is a hallucination liability that a sharp panel member will probe immediately. ⬜ Make it **retrieval-only with mandatory citation**: it surfaces and quotes the relevant maintenance-manual passage and the matching historical mission, and the *advisory text itself* comes from templates driven by the deterministic diagnosis. "The LLM retrieves and cites; it does not decide" is a defensible sentence. "The LLM recommends maintenance" is not.

**Federated learning** — 🔶 **Architect, do not implement.** ✅ Listed as an innovation area, and the motivation is real (run-to-failure data is scarce and operators will not share raw telemetry). But with one simulated engine there is nothing to federate. ⬜ Build the *hook* — per-tail-number local models, a described and documented aggregation protocol, a demo across N simulated tails — and describe it honestly as **"federation-ready."** Claiming "federated learning" for a single-node system is the kind of overclaim this folder has rightly avoided elsewhere.

---

## 11. Hardware — my call

**You asked me to decide. Here is the decision and the reasoning.**

✅ **The PS category is "Software" and the deliverable is a "functional prototype / software demonstrator."** ✅ But §6 expects demonstrated understanding of "Embedded systems" and "CAN communication," and the innovation areas list "Edge AI for UAV applications" and "Lightweight onboard analytics."

⬜ **Decision: software-first, with exactly one optional physical edge node. No sensors, no engine, no custom electronics.**

| Tier | What | Justification |
|---|---|---|
| **Core — build this** | Everything in pure software. Virtual CAN (`vcan0`), simulated link with injected latency/loss, edge process as a separate OS process. Runs on one laptop | Satisfies the PS completely. Zero demo risk. This *is* the deliverable |
| **⬜ Optional — if ≥2 days spare** | **One Raspberry Pi as the edge node**, reading **real CAN** (MCP2515 HAT, ~₹800, or a USB-CAN adapter). Laptop runs engine sim + ECU emitter → real CAN wire → Pi runs edge stack → UDP downlink → laptop runs GCS | Converts "we have an edge layer" from a slide claim into a physical fact. **The unplug test**: pull the network cable mid-fault, the Pi keeps detecting and logging, plug it back in, the GCS backfills. No pure-software competitor can reproduce that moment |
| **❌ Do not** | Build sensor hardware, buy/instrument an engine, design PCBs | Outside the PS category, consumes the entire timeline, and a panel will not award points for an instrumented engine that is not the *actual* UAV engine anyway |

🔶 **Risk control, which is the whole reason this is tiered:** the Pi path must be a **swap-in behind the same `TelemetrySource` interface**, with `vcan0` as the default. If the hardware misbehaves on demo day, we change one flag and nothing else. **The demo must never depend on it.** Hardware at a hackathon is a liability unless it is optional by construction.

🔶 Net: roughly ₹5,000 and one day of integration buys the single most memorable 30 seconds of the demonstration, with a bounded downside. That is a good trade. If the schedule is tight, drop it without hesitation — the software system is the deliverable and it stands alone.

---

## 12. Priorities

**Core — without these we have not answered the PS**
Differentiable physics twin + residuals · sensor validation layer · layered anomaly detection on residuals · 8-fault classifier with UNKNOWN · baseline RUL with conformal intervals · replay · dashboard with a 3D view that shows residuals · synthetic generator with parameter-level fault injection · simulated degraded link · edge process surviving link loss.
*Justification: this is the PS requirement list, plus the two things (sensor validation, calibrated uncertainty) without which the outputs are not trustworthy.*

**Advanced — technical depth that will be visibly noticed**
Per-tail-number calibration by gradient descent · particle-filter RUL · mission-descriptor roll-forward · analytical-redundancy reconstruction of failed channels · quantified comparison against the threshold baseline · ablation table · sim-A→sim-B generalisation test · methods validated on real public datasets.
*Justification: each converts an assertion into a measurement.*

**Differentiating — why we win rather than tie**
**Mission-reliability output (P(success), limiting factor, per-profile)** · the **sensor-drift-vs-engine-fault demo (S3)** · the **link-blackout edge demo (S4)** · **physical explanations with ruled-out alternatives** · signed telemetry.
*Justification: the first is the PS title and nobody builds it; the middle three are the moments a panel remembers; the last is cheap and shows defence-mindedness.*

**Experimental — only with genuine slack**
Foundation-model baseline comparison · learned RUL if it beats the baseline · federation across N simulated tails · differentiable-physics sensitivity analysis for fault isolation · test-rig deployment mode (the second of the PS's three named deployment contexts).

---

## 13. Summary of where I differ from the existing study material

| # | Existing position | My position |
|---|---|---|
| 1 | Architecture in `22_final_recommendation.md` is the plan | ✅ It is the *floor* — competitors independently built it. The plan is what sits on top |
| 2 | NumPy/SciPy physics | ⬜ **Differentiable** physics (JAX/PyTorch) → per-tail calibration, sensitivity, hybrid path |
| 3 | Sensor drift = one of 8 fault classes | ⬜ Its own **layer before the twin**. Highest credibility-per-hour item in the project |
| 4 | Mission simulation is a feature | ⬜ **Mission reliability is the headline output** — it is the PS title, and it is published research |
| 5 | RUL with "uncertainty bounds" | ⬜ Specifically **conformal prediction**, and report empirical coverage as a checkable metric |
| 6 | Novelty framed around sparse-coding/HDC | ⬜ Novelty sits in mission-conditioned reliability + sensor/engine disambiguation under a kbps link. The `20_*` self-correction was right; go further and move the claim entirely |
| 7 | Demo = working system | ⬜ Demo = **quantified comparison against the threshold baseline**, which is what the PS's own framing invites |
| 8 | Voice / LLM / FL as features | ⬜ Cut voice · constrain LLM to retrieval-with-citation · "federation-ready," not federated |
| 9 | 135 °C CHT limit | ⚠️ Verify against the variant's operators' manual — public sources indicate 150 °C (old config) / 120 °C coolant (new heads) |

---

## Sources

[Mission-Aware RUL (PHM Society)](https://papers.phmsociety.org/index.php/phme/article/view/4888) · [Conformal Prediction Intervals for RUL](https://papers.phmsociety.org/index.php/ijphm/article/view/3417) · [Uncertainty-Aware Bearing RUL via Conformal Prediction (2026)](https://papers.phmsociety.org/index.php/phme/article/view/4902) · [Isotonic-calibrated split conformal RUL on C-MAPSS (2026)](https://www.sciencedirect.com/science/article/pii/S0951832026005740) · [Multi-Sensor Fusion RUL for UAV Engines, Drones (2026)](https://www.mdpi.com/2504-446X/10/9/705) · [Sensor Failure Detection for Jet Engines Using Analytical Redundancy (NASA)](https://ntrs.nasa.gov/api/citations/19840016517/downloads/19840016517.pdf) · [Aircraft Engine Sensor/Actuator/Component Fault Diagnosis Using a Bank of Kalman Filters](https://www.researchgate.net/publication/24285913_Aircraft_Engine_SensorActuatorComponent_Fault_Diagnosis_Using_a_Bank_of_Kalman_Filters) · [Online learning FDIR for aero-engine sensors (2025)](https://www.sciencedirect.com/science/article/abs/pii/S1270963825003128) · [Physics-Informed ML for Gas Turbine Digital Twins — review](https://www.preprints.org/manuscript/202509.1360) · [Hybrid As-Operated Digital Twin of an Aircraft Brake](https://papers.phmsociety.org/index.php/phme/article/view/5050) · [ChronosAD](https://arxiv.org/pdf/2606.01300) · [Zero-shot foundation models for multivariate TSAD](https://arxiv.org/html/2607.12454) · [TimesFM for predictive maintenance](https://blog.pebblous.ai/report/timesfm-industrial-forecasting/en/) · [NASA PCoE dataset repository](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/) · [Rotax 912](https://en.wikipedia.org/wiki/Rotax_912) · [Rotax CHT sender position change SB-912-066](https://rotaxnews.net/?p=927) · [Rotax SI-912-020R10](https://legacy.rotaxowner.com/si_tb_info/serviceinfo/si-912-020-r10.pdf) · Competing SIH implementations: [sih26054-digital-twin](https://github.com/Mehak2513kaur/sih26054-digital-twin), [TwinProp-DX](https://github.com/Monika-Srinithi/TwinProp-DX), [AEROTWIN-AI](https://github.com/Ash180905/AEROTWIN-AI)

---

*Independent R&D report. Existing study material in this folder was read and then re-derived from first principles; §13 lists every point of divergence. Companion to [`proposal.md`](proposal.md) and the numbered study parts.*
