# 08 — The Deployable Version: Target System, Honest Audit, Execution Plan

*Fourth audit pass, 23 September 2026. Docs 01–07 asked what the PS wants, what competitors do, and what nobody else is working on. This one asks a harder question: **what would a system look like that DRDO could actually pick up, and how far is this repository from it?***

**Method.** The Sep 21–23 conversations were recovered from session logs, so §0 records what we actually said, not what anyone remembers. The live code path was traced import by import from `backend/server/engine_service.py`. The full test suite was run (**129 passed**). External facts were re-checked by web search on the day of writing. Every code claim below links to a file.

**Relationship to earlier docs.** [`07_unoccupied_axes_and_ground_up_plan.md`](07_unoccupied_axes_and_ground_up_plan.md) (F31–F68) stays the feature plan of record. This document does not add features. It says **how to make the features that exist into one system that someone outside the team could trust**.

---

## 0. What we discussed, recovered

| Thread | When | Where it landed | State today |
|---|---|---|---|
| **Fruit-fly connectome** | Sep 21 | Not as a replacement for the Random Forest on 14 residual features, because at that dimensionality it is neither cheaper nor more accurate. It **is** a strong fit as a novelty layer on *high-dimensional* input, and its explanation comes from the same forward pass. What we were actually borrowing is the mushroom-body circuit (FlyHash / Fly Bloom Filter), not the whole brain. | [`flyhash_novelty.py`](../../backend/ml/flyhash_novelty.py) built and wired into the live pipeline, but on residuals only, not on the spectrum. It also has a label leak (§5.D). |
| **The waveform** | Sep 21 | The live "vibration" is a 20 Hz RMS scalar. Real HUMS practice uses kHz waveforms and order analysis, and that high-dimensional regime is where fly-style sparse coding pays off. | Crank-angle chain F01–F06 built and verified ([`crank_dynamics.py`](../../backend/physics/crank_dynamics.py), [`crank_diagnostics.py`](../../backend/ml/crank_diagnostics.py)). It runs only in the evaluation harness. |
| **Jev (TypeSafe AI)** | Sep 22 | A "System One" model: typed decisions with calibrated probabilities, no text generation. Closed and hosted only, so it cannot run offline and is disqualified for a DRDO deliverable. Community open reproductions exist. Its proper scope is advisory at the GCS, never the detection path. | Nothing built, which was the right call. See §4.4. |
| **`mk-jev-fly-brain`** | cloned locally | *Model Kombat*: a 12,000-neuron maleCNS subgraph fights Jev in mk.js. Thirteen documented experiments, including the failures. | Its code is not useful to us. Its **experimental method** is (§4.3). |
| **Engine reframe** | Sep 22 | Rotax 912 iS → **Rotax 914** as primary (the global MALE standard, and the engine in NASA ACES), plus a CI heavy-fuel config for the Indian platform. | [`configs/engines/`](../../configs/engines/) has 912iS / 914 / AE300. [`thermo_model.py`](../../backend/physics/thermo_model.py) still ignores them. |
| **Competitors** | Sep 22 | 23 repositories catalogued, 9 cloned. Dronanetra and PRAHARI are the strongest. The whole field does residuals → IsolationForest/RF → dashboard, and nobody does real vibration processing. | [`01`](01_competitive_audit.md), [`05`](05_expanded_survey.md), [`../COMPETITOR_ARCHITECTURE_BREAKDOWN.md`](../COMPETITOR_ARCHITECTURE_BREAKDOWN.md) |
| **F31–F68 build** | Sep 22–23 | 41 of 65 features implemented, per [`IMPLEMENTATION_LOG.md`](../IMPLEMENTATION_LOG.md). | This document audits how much of that is actually integrated. |

### Corrections carried forward

1. **The indigenous TAPAS engine is publicly described, and [`UpdatedReport/31`](../../UpdatedReport/31_VERIFICATION_AND_CORRECTIONS.md) §2.2 is wrong to say it isn't.** Indian Defence News (Aug 2025) describes it as *"a 2.2L, 4-cylinder inline turbocharged CRDi engine"*: 180 HP at 11,000 ft, operable to 32,000 ft, with FADEC, developed by **VRDE with JAYEM Automotives**. idrw (Aug 2025) confirms a 180 hp VRDE engine for the TAPAS BH-201 production variant, replacing the Austro/NPO-Saturn engines used on prototypes. The one figure that remains unsourced is the **17.5:1 compression ratio**, which belongs to the AE300/OM640. **This makes the CI config more important, not less. The engine DRDO actually cares about is a CRDi turbo-diesel inline-4.**
2. **OpenJev.** The Sep 22 session cited a "DiffusionGemma 3B-A4B, Apache 2.0" reproduction from a guide site. Several community reproductions do exist (`razorback16/openjev`, `zhangcy122/OpenJev`, `Heman10x-NGU/Verdict-open-jev`). All of them are weeks old and unaudited, and each one's licence and base model has to be checked in its own repository before use.
3. **"FlyHash is cheaper than the RF."** This was claimed and then retracted within the Sep 21 session. At 14 input features it is not cheaper. The retraction stands.

---

## 1. The verdict

This is not a vibe-coded project in the sense of being fake. The research modules are careful work, and several of them document the failures that shaped their final design. The real problem is structural.

### You have two systems, and they don't talk to each other

**System A, the one that runs and that judges see:**
`engine_service` → [`can_streamer.TelemetryStreamer`](../../backend/telemetry/can_streamer.py) (sensor data generated from the twin's own equations plus an injected fault) → [`DetectionPipeline`](../../backend/ml/detection_pipeline.py) (sanity check → algebraic residuals → autoencoder → a DFT of a 20 Hz RMS scalar → Random Forest on 14 residuals → hand-written rules tied to specific cylinders) → [`RULEstimator`](../../backend/ml/rul_estimator.py) (hardcoded component lifetimes) → LLM copilot and voice → React GCS and Blender.

**System B, the one that produces every defensible number:**
[`VirtualEngine`](../../backend/plant/virtual_engine.py) plant, crank dynamics and diagnostics, [`ResidualDetector`](../../backend/twin/residual_detector.py), damage accumulation, conformal prediction, PHM metrics, twin validity, physics integrity, FMECA and isolability, mission reliability, prescriptive advisory, and the edge compressor. **It is reachable only from tests and from one harness script.**

Tracing imports from the service confirms this. Of the 41 "implemented" plan features, **three touch the live path**: F14 residual shielding; FlyHash, which has a label leak; and the independent plant adapter, which is **off by default** (`ANUMAAN_USE_INDEPENDENT_PLANT=0`).

**Both systems also run on data the team wrote itself.** The repository holds no real engine waveform. Its one real flight dataset (NASA ACES, Rotax 914) has a known-wrong EGT channel binding. Of the public proxy benchmarks catalogued in [`Datasets/`](../../Datasets/README.md), only one C-MAPSS training file is on disk.

### What is actually blocking "deployable"

Missing features are not the blocker. In order of importance, the blockers are:

1. **Integration.** There has to be one pipeline, and the system that gets measured has to be the system that gets demonstrated.
2. **Real data.** At minimum: real healthy flight hours for the false-alarm rate, and one real engine producing real combustion waveforms.
3. **A real twin core.** A digital twin is a *state and parameter estimator* fitted to one specific engine. Nothing in `backend/` estimates anything; there is no Kalman, UKF or particle filter anywhere.
4. **Evidence at statistical scale.** The current results are eight scenarios, one run each.

Everything else is secondary.

---

## 2. What "DRDO could integrate" actually means

### 2.1 Who would pick it up

| Organisation | Role | What they would want from us |
|---|---|---|
| **VRDE** (Ahmednagar) | Developer of the 2.2 L CRDi TAPAS engine; runs engine test beds | **A test-cell health-monitoring tool.** The PS names "engine test rigs" as a deployment context. This is the most realistic first user. |
| **ADE** (Bengaluru) | TAPAS BH-201 integrator; owns the GCS | A component with a defined interface (ICD) that plugs into their GCS, and does not replace it |
| **CEMILAC** | Airworthiness certification for all military airborne software, including UAVs, under IMTAR-21 / IMTAR V2.0 | A clear safety position: advisory-only, deterministic core, ML confined to advisory outputs |
| **Operators** (Heron / Rotax 914 fleets) | Maintenance | Fewer "no fault found" removals, and earlier warning |

🔶 None of these organisations will adopt a hackathon repository as-is. Three things do transfer:

1. **A method with evidence.**
2. **A component with defined interfaces.**
3. **A validation protocol they can run on their own data without that data leaving their building.**

The third is the one competitors will not think of, and it answers the question "your data is synthetic, ours is classified."

### 2.2 Non-negotiable constraints

| Constraint | What it implies | Where we are |
|---|---|---|
| Air-gapped, on-premises, indigenous | No hosted APIs, permissive licences, reproducible builds | Mostly OK. The LLM runs locally through Ollama. **Jev's API is out.** |
| Their data stays with them | They must be able to recalibrate and retrain without us; the pipeline must not care where data comes from | ❌ The RF is trained on our generator, and there is no retraining path for a new engine |
| Advisory-only | Deterministic, explainable core; ML only on advisory outputs; low design-assurance level | ❌ The architecture does not separate the deterministic core from the optional AI |
| Engine class is CRDi turbo-diesel inline-4 | A VRDE-class config; injector and rail faults as the primary fault family | 🟠 An AE300 config exists, but the physics model is hardcoded to the 912 |
| FADEC CAN and GCS interfaces | DBC-defined messages and Interface Control Documents | 🟡 A J1939 bridge (used only by a script) and MAVLink decoding (tested only in-process); no DBC, no ICD |
| Evidence in their units | False alarms per flight hour, detection probability, lead-time distributions, sim-to-real error | 🟠 n = 1 per scenario |

### 2.3 Technology readiness

- **Today: about TRL 3.** Analytical and simulated proof of concept.
- **Target for the SIH finale: TRL 4.** Components validated on real hardware in a lab (§6.4, the lab engine rig).
- **What DRDO would fund next: TRL 5.** Validated in a relevant environment, which means the VRDE test cell.

Saying this plainly, in the deployment roadmap, is itself a credibility signal.

---

## 3. The target system

### 3.1 Governing principle: one pipeline, many data sources

```
 SOURCES                      ONE CANONICAL FRAME               ONE PIPELINE (OSA-CBM / ISO 13374)
 ───────                      ───────────────────               ──────────────────────────────────
 Physics plant (Monte Carlo) ┐
 ACES replay (real flight)   │   engine-agnostic channels,       EDGE NODE      LINK        GCS TWIN        FLEET / DEPOT
 ArduPilot SITL (MAVLink)    ├─► units, timestamps, source,  ─►  DA·DM·SD   ─► health  ─►  SD·HA·PA·AG  ─►  per-tail registry
 Lab engine rig              │   quality flags                   (determin-     frames      (estimator,     maintenance feedback
 VRDE test cell              │   NO ground-truth field           istic)         + events    diagnosis,      federated updates
 Flight                      ┘   (truth goes to a separate                                  prognosis,
                                  stream only the evaluator reads)                          advisory)
```

**The same code and the same config run on every source. "Live" is simply replay at 1×.** That single rule makes the demo and the evidence the same thing. It closes the System A / System B split, and it lets DRDO point the pipeline at their own data.

### 3.2 Onboard edge node (an engine health unit next to the FADEC)

**Inputs**

| Signal | Source | Rate | Why it matters |
|---|---|---|---|
| RPM, rail pressure, per-cylinder injection timing and quantity, MAP, boost, fuel and oil temperatures | FADEC CAN | 10–100 Hz | A CRDi FADEC already computes most of what we want. We read it; we don't re-derive it. |
| **Crank tooth timestamps** | **The FADEC's own crank-position sensor** (trigger wheel) | Per tooth, a few kHz | **Per-cylinder ω(θ) diagnostics without adding a sensor.** This is how automotive OBD misfire monitors already work, so it is established and certifiable, not exotic. |
| Crankcase and gearbox accelerometer | IEPE accelerometer (new sensor) | 20–25.6 kHz | Order spectrum, gear-mesh orders, bearing envelope |
| CHT/EGT per cylinder, oil pressure and temperature, fuel flow | Existing sensors | 1–10 Hz | Thermal twin |
| Oil debris (inductive) | Optional | Event-driven | Direct measurement of material loss |

**Processing** (deterministic, fixed compute budget, no LLM, and eventually no Python on the hot path)

1. Tach-synchronous angular resampling → ω(θ) and a(θ)
2. Per-cylinder work attribution → combustion and **injection health per cylinder** (for a CRDi engine this is the primary fault family: coking/IDID, needle stick, timing drift)
3. Order spectrum (a few hundred bins), gear-mesh orders, envelope spectrum
4. Thermal residuals against a reduced onboard model
5. **Novelty: FlyHash plus a Fly Bloom Filter over the order spectrum**, with memory conditioned on operating regime (RPM/load/phase bins) and time decay
6. Sensor-validity and physics-integrity gate
7. Compression to the 29-byte health frame at 1 Hz, plus **event-triggered raw-waveform capture** (a few seconds either side of an anomaly) to onboard storage for post-flight download. This is how HUMS does it.
8. Link-loss autonomy: keep monitoring, queue results, and raise local alerts through the autopilot

### 3.3 Datalink

- MAVLink 2 `EFI_STATUS` (#225) plus one custom health message, with **MAVLink 2 message signing**
- Budget: about 1–2 kbit/s. The compressor already measures 0.232 kbit/s.
- Everything is specified in an ICD, not only in code

### 3.4 GCS twin server: the actual digital twin

> **The twin is an estimator, not a generator.** This is the most important architectural change in this document.

- **A dynamic lumped-parameter model.** Per-cylinder thermal RC networks (head, liner, coolant/air side), the oil circuit, the turbocharger, and fuel/rail dynamics. Its **health parameters** θ are: per-cylinder cooling effectiveness, per-cylinder injector delivery, rail leakage, turbo efficiency, oil-pump efficiency, and sensor biases.
- **Joint state and parameter estimation.** A UKF with θ as slow random-walk states, or a particle filter where the degradation is strongly nonlinear. NASA structures its prognostics framework (ProgPy) exactly this way: model, state estimator, predictor. Its structure is worth copying, and its code is worth adopting if the licence permits.
- **Health is θ̂ with its covariance, not a class label.** With that in place:
  - **Detection** = a statistically significant change in θ̂ or in the innovations (GLR/CUSUM), with thresholds set by conformal calibration to a target false alarms per flight hour.
  - **Isolation** = *which* parameter moved. This is the isolability matrix from [`isolability.py`](../../backend/reliability/isolability.py), made probabilistic.
  - **Prognosis** = θ̂'s trajectory propagated forward by Monte Carlo, cross-checked against physics-of-failure damage accumulation (F38 dual path).
  - **Per-tail calibration** = the converged θ̂ from acceptance and early flights, stored per engine serial number. That is what makes it a twin *of this engine*.
  - **Twin validity** = NIS and whiteness tests on the estimator's innovations. [`twin/validity.py`](../../backend/twin/validity.py) was designed for exactly this and just needs an estimator to monitor.
- **Diagnostic reasoning.** FMECA → signature matrix → **a diagnostic Bayesian network**. Its evidence comes from parameter changes, per-cylinder crank features, novelty, classifier posteriors, and oil lab results. Its output is ranked hypotheses with probabilities and **explicit ambiguity groups**, for example: *"needle stick in cylinder 2 or combustion loss in cylinder 2 — not separable with current sensors; a rail-pressure trace would separate them."* That sentence is what a propulsion engineer trusts.
- **Decision.** Mission reliability computed from live θ̂ and damage state; prescriptive derating; ISA-18.2 alarm management; typed advisories.
- **Explanation.** A physics causal chain plus case retrieval with citations. The LLM is optional, grounded in retrieval, and **never in the decision path**.

### 3.5 Fleet and depot

- A per-tail registry: serial number, calibrated θ, exposure accumulator, damage state
- **A maintenance feedback loop.** Every advisory → work order → finding (confirmed, or no fault found) → a label. The no-fault-found rate is a KPI.
- **Federated learning across tails and bases.** FlyNN-FL (Bloom-filter bit arrays merged by OR, which suits low-bandwidth links) or FedAvg for small models. Models are versioned, signed, and **frozen in flight**.
- Ingestion of SOAP oil-analysis lab results

### 3.6 Test-cell mode

The same software runs on VRDE's dynamometer, which adds in-cylinder pressure (ground truth for combustion) and measured torque. Seeded-fault campaigns there produce labelled data that **DRDO owns**, and that data calibrates everything above. This is the deployment roadmap's first rung.

---

## 4. The AI/ML layer: where the fly brain, the Random Forest and Jev actually belong

### 4.1 The honest comparison

| Method | Input regime where it works | Strengths | Weaknesses | Verdict | Runs on |
|---|---|---|---|---|---|
| **Random Forest / LightGBM** on engineered residuals | 14–40 tabular features | Accurate on tabular data, mature, TreeSHAP available | Closed-set (a retrain to add a class); no cheap federated learning; **learns our generator** | Keep as the closed-set baseline | GCS |
| **FlyHash + Fly Bloom Filter** (novelty) | **High-dimensional input: order spectrum, hundreds of bins** | One pass, no labels, µs-scale, memory is a bit array, time-decay built in, explanation is "which bins" | A fixed random projection can't learn; weak on 14 dimensions | **Edge novelty layer, fed the spectrum** | Edge |
| **FlyNN** (FlyHash + one Fly Bloom Filter per class) | Same | **Adds a fault class from a few examples without retraining**; federated by OR-merging bit arrays; can be differentially private; matches kNN accuracy across 70 OpenML datasets | kNN-level accuracy, which RF often beats on tabular data | **The real head-to-head against the RF.** Likely wins on open-set and fleet learning, not on closed-set accuracy. | GCS + fleet |
| BioHash (learned sparse code) | High-dimensional | Learns the projection | More complex | Stretch goal | — |
| Small 1D-CNN on spectrum or angular waveform | Raw, high-dimensional | Strong with enough data | Needs labelled data we don't have | Benchmark contender | GCS |
| Zero-shot time-series foundation model (Chronos / TimesFM / Moirai) | Time series | Never saw our simulator, so it works as a **control** | Heavy | Control experiment only | GCS |
| **Jev** (TypeSafe) | Typed decisions over a state | Fast, typed, calibrated | Closed, hosted US API | **Disqualified** | — |
| OpenJev-class (self-hosted) | Typed decisions | Runs on-premises | Weeks old, unaudited, never validated for engineering use | Optional ranking of advisory actions, or distil it (§4.4) | GCS |
| Spiking connectome simulation (maleCNS / FlyWire) | Sensorimotor control | Great demo | No fit to PHM; Model Kombat's own rewired control showed the competence came from the readout and curriculum | Visualisation at most | — |

### 4.2 What would make "the fly beats the RF" true, and how to test it

**The testable hypothesis:**
> On order-domain vibration input, an expand-and-sparsify detector/classifier achieves equal or better detection at a fixed false-alarm rate, at lower edge cost, **and** supports incremental fault classes and federated fleet learning that the RF cannot.

**The protocol:**

- **Data.**
  - (a) Simulation Monte Carlo with build and environment randomisation
  - (b) CWRU and Paderborn bearing data (method validity only)
  - (c) The public 3500-DEFault diesel dataset (crankshaft torsional-vibration and cylinder-pressure features). Check how it was generated before quoting any result from it.
  - (d) Our own lab-rig recordings (§6.4)
- **Contenders.** FlyHash-FBF, FlyNN, **a same-budget dense Gaussian random projection with the same winner-take-all (the null model)**, PCA-Mahalanobis, IsolationForest, the existing small autoencoder, RF, LightGBM, and a 1D-CNN.
- **Inputs.** Both the 14-residual vector *and* the order spectrum, so the regime effect is visible rather than argued.
- **Metrics.**
  - Detection at a fixed false-alarm rate per flight hour; AUROC and AUPRC
  - **Open-set detection** (a whole fault family held out of training)
  - Time to detect; edge latency and memory
  - **Incremental-class accuracy with k = 1, 5 and 10 examples**
  - Federated communication in bytes
- **Splits.** By engine build, day, and operating point. Never by random frames.
- **Decision rule** (already agreed in [`../study/20_novelty_and_research.md`](../study/20_novelty_and_research.md) §20.5): adopt it if it wins. If it loses, **publish the negative result.**

### 4.3 What `mk-jev-fly-brain` actually teaches us

Its code is a game. Its experimental discipline is the most useful thing in that folder.

| Their finding | How it transfers to this project |
|---|---|
| **Jev distilled into a 168-weight softmax** agreed with Jev on 93 % of the calls Jev was confident about, answered in 4 µs, and *beat the model it copied* by acting sooner. A hybrid (local speed, Jev correcting live) beat both. | **An edge/ground learning loop.** Heavy ground-side models (ensembles, a time-series foundation model, the Bayesian network) label the data. Tiny distilled edge models (a linear readout over the FlyHash code, or a small tree) act at kHz cadence. The ground corrects and re-distils after each flight. Report agreement *on confident calls*, not overall accuracy. |
| **The rewired control.** Same neurons, degrees and weights with the connections shuffled still learned to beat the rule bot. The competence came from the readout, reward and curriculum; the wiring only improved hit quality. | Every "bio-inspired" claim needs a null model: a same-budget dense random projection. **If FlyHash ties the null, the gain came from the order features. Say so.** |
| **A five-line rule bot matched Jev.** | Strong simple baselines: the debounced threshold monitor (already built), Mahalanobis distance on residuals, and an OBD-style crank-speed misfire counter. Beat all three or don't claim anything. |
| Learning only worked after adding an **efference copy** and a **reward baseline**. | Online adaptation needs two things. (a) Knowing the regime and action at the time: condition the novelty memory on RPM/load/phase. That is the efference copy. (b) A running baseline, so a streak of bad flights doesn't suppress everything. The "dopamine" signal is the **maintenance outcome** (confirmed fault versus no fault found). |
| **The order of opponents decided the outcome**, and a transferred brain beat longer training. | Simulation → public proxies → lab rig → test cell → flight. Carry the calibrated models forward rather than retraining from scratch at each stage. |
| **Information asymmetry made the comparison illustrative, not fair.** | Compare methods on identical inputs, and never let one detector see a feature the others can't. **That is precisely the live FlyHash bug** (§5.D). |

### 4.4 Where Jev-style typed decisions fit

The GCS already emits typed decisions: GO / CAUTION / NO_GO, a derate level, a maintenance action from a fixed ATA list, an alarm priority. These must come from **deterministic, auditable logic** (the reliability computation plus rules), with calibrated probabilities from the estimator and the Bayesian network.

A typed-decision model (OpenJev-class, on-premises) can be justified in one role only: an assistant that *ranks* maintenance actions from the fixed list given the evidence. Its output is logged and never acted on automatically. Better still, follow Model Kombat's first lesson: **distil its decisions into a transparent policy and ship the policy, not the model.** A certifier can read a 168-weight policy.

---

## 5. Audit: the current repository against the target

**Legend:** ✅ live and sound · 🟡 built but not integrated · 🟠 live but weak or superficial · ❌ missing · ⚠️ wrong or misleading

### A. Architecture and integration

| Item | Status | Evidence |
|---|---|---|
| One pipeline serving both the demo and the evaluation | ⚠️ | Two stacks (§1). The service imports none of `evaluation/`, `twin/`, `mission/`, `reliability/`, `edge/`, or the crank chain. |
| Live data source independent of the twin | 🟠 | [`engine_service.py:20`](../../backend/server/engine_service.py) uses `TelemetryStreamer` (circular). The plant adapter is opt-in and covers faults 1–4 only. |
| OSA-CBM architecture | 🟡 | [`osacbm.py`](../../backend/osacbm.py) *documents* the six layers; nothing *executes* through it |
| Edge / GCS process separation | ❌ | Everything runs in one Python process alongside the LLM, voice and UI |
| Canonical frame schema with provenance and no ground truth | ❌ | `EnginePhysicalState` carries `FAULT_ID` ([`thermo_model.py:78`](../../backend/physics/thermo_model.py)) into the detection path |

### B. Data

| Item | Status | Evidence |
|---|---|---|
| The RF's 97.5 % accuracy | ⚠️ | Split by mission, but every mission comes from the same generator the residuals are computed against. It measures the generator. |
| ACES real flight data | 🟠 | Loads correctly, but the EGT binding reads 170 °C ([`IMPLEMENTATION_LOG`](../IMPLEMENTATION_LOG.md), session 4). No sim-to-real number exists yet. |
| Real engine waveforms | ❌ | None |
| Public proxy benchmarks | ❌ | [`Datasets/`](../../Datasets/README.md) holds only READMEs; `data/telemetry/source2_nasa_benchmarks/` holds one C-MAPSS training file |
| Labelled seeded-fault data from any real engine | ❌ | — |

### C. Twin core and physics

| Item | Status | Evidence |
|---|---|---|
| Expectation model | 🟠 | [`thermo_model.py`](../../backend/physics/thermo_model.py): algebraic steady state, Rotax 912 iS constants, no dynamics, doesn't read `engine_config` |
| State and parameter estimation | ❌ | No Kalman, UKF or particle filter anywhere in `backend/` |
| Per-tail calibration | 🟠 | A frozen offset in [`residual_detector.py`](../../backend/twin/residual_detector.py). The right idea in its minimal form, and harness-only. |
| Subsystem physics (turbo, injectors, oil, fuel thermal, induction, crank) | 🟡 | Composed in the *plant* ([`virtual_engine.py`](../../backend/plant/virtual_engine.py)), absent from the *twin* |
| VRDE-class 2.2 L CRDi config | ❌ | Configs exist for 912iS, 914 and AE300 only |
| Constants traceable to a source | 🟠 | Placeholders, honestly labelled in each `source` field |

### D. Detection and diagnosis

| Item | Status | Evidence |
|---|---|---|
| Fault taxonomy | ⚠️ | Nine classes defined by the generator. The fallback rules hardcode cylinders: fault 1 is *CHT_2* only, fault 3 is *EGT_2* only, fault 6 is *EGT_3* only ([`detection_pipeline.py:553-579`](../../backend/ml/detection_pipeline.py)). **An overheat on cylinder 3 is not a class.** The FMECA in [`fmeca.py`](../../backend/reliability/fmeca.py) should define the taxonomy (mode × location), not the generator. |
| **FlyHash in the live pipeline** | ⚠️ | [`detection_pipeline.py:391`](../../backend/ml/detection_pipeline.py) calibrates on `actual.FAULT_ID == 0`, **the injected ground-truth label**, which real telemetry never carries. It also runs on 26-dimensional residuals with the order slots left at zero, the regime §4.1 says it is weakest in. |
| "Gearbox FFT" | 🟠 | A DFT of the 20 Hz RMS scalar (Nyquist 10 Hz). The live path's "vibration analysis" isn't vibration analysis. |
| Crank chain F01–F06 | 🟡 | Real and verified; harness-only |
| Residual detector with sensor-vs-engine discrimination | 🟡 | Harness-only |
| NoveltyGate, physics integrity, twin validity | 🟡 | Not wired |
| FMECA and isolability | 🟡 | Produce documents; don't drive isolation |
| Alarm logic | 🟠 | An 8-of-10-frame majority vote; no alarm rationalisation |

### E. Prognostics

| Item | Status | Evidence |
|---|---|---|
| Live RUL | 🟠 | [`rul_estimator.py`](../../backend/ml/rul_estimator.py): hardcoded lifetimes (450 h, 600 h…) × stress multipliers. It is not a prognostic. |
| Damage accumulation, conformal prediction, PHM metrics | 🟡 | Built, unconnected to each other, never run on an actual RUL trajectory |
| Dual-path RUL (F38) | ❌ | — |
| Any run-to-failure validation, even C-MAPSS as a method check | ❌ | — |

### F. Evaluation

| Item | Status | Evidence |
|---|---|---|
| Scenario coverage | 🟠 | 8 scenarios × **one run each** ([`detection_report.md`](../evaluation/detection_report.md)) |
| "Median lead time 7.92 min" | ⚠️ | A median of **one** value. Oil-pressure loss is the only scenario where both the twin and the baseline fired. |
| "0 false alarms per hour" | 🟠 | Over 3 nominal hours. By the rule of three, the 95 % upper bound is **1.0 per hour**, which cannot be told apart from a bad detector. |
| **What the harness measures** | ⚠️ | It evaluates `ResidualDetector` + `CrankDiagnostics`, **not** the live `DetectionPipeline`. **The system being demonstrated is not the system being measured.** |
| Point-adjust inflation instrument (F62) | ✅ | Good, and rare in the field |
| ROC curves, Monte Carlo campaigns, confidence intervals, ablations, null models, blind fault injection | ❌ | — |

### G. Interfaces

| Item | Status | Evidence |
|---|---|---|
| MAVLink `EFI_STATUS` | 🟡 | Decoded from a message built in-process; never run against SITL or hardware |
| SocketCAN / J1939 | 🟡 | [`socketcan_bridge.py`](../../backend/telemetry/socketcan_bridge.py) is used only by one script; `python-can` isn't in `requirements.txt` |
| DBC, vcan end-to-end, SITL, ICD | ❌ | — |

### H. Edge, I. Security, J. HMI, K. Engineering

| Item | Status | Evidence |
|---|---|---|
| Edge budget arithmetic | 🟡 | [`compressor.py`](../../backend/edge/compressor.py): sound, and a real differentiator |
| Edge latency | 🟠 | Python on a development laptop; no target hardware, no WCET analysis, no fixed-point code |
| Security | 🟡 / ❌ | Physics integrity built but not wired; no MAVLink signing, threat-model document, or model signing |
| HMI | 🟠 | Fifteen React components, a Blender twin, a desktop GCS, a site and a voice copilot: a lot of presentation surface. No ISA-18.2 alarm management, and no uncertainty shown anywhere. **The 3D model is a visualisation, not the twin.** |
| Tests | ✅ | 129 pass, but most new modules are tested only in isolation |
| CI, typed ICDs, one command to regenerate every number | ❌ | — |
| Documentation | ✅ / ⚠️ | [`IMPLEMENTATION_LOG.md`](../IMPLEMENTATION_LOG.md), `docs/study/` and `docs/audit/` are genuinely good. [`UpdatedReport/`](../../UpdatedReport/) 00–30 contain known-false file paths and remain the most "presentable" documents; Report 31 contains the wrong VRDE correction (§0). |
| Repository hygiene | 🟠 | `report_dump/mission_001…067`, 15 untracked live-sortie CSVs, a WhatsApp video at the root, `scratch/`, and 1.3 GB of ACES tarballs (including `.opdownload` partials) next to 1.9 GB of extracted data |

---

## 6. What I would change, dimension by dimension

### 6.1 Approach: stop counting features, ship vertical slices

"41 of 65 features, 63 %" measures typing, not capability. **A slice is done only when it runs sensor → edge → link → twin → diagnosis → advisory in the UI, in the live service, measured by a Monte Carlo campaign with confidence intervals, and validated on at least one real data source.**

| Slice | Content | Why this order |
|---|---|---|
| **1. Per-cylinder injection and combustion health** | The crank chain end to end | The strongest differentiator (0 of 23 competitors), relevant to the CRDi engine, and needs no new sensor on a real FADEC |
| **2. Cooling and lubrication health** | UKF parameter estimation → RUL → mission reliability | Makes the twin a twin, and turns the PS title into a computed number |
| **3. Sensor versus engine, and integrity** | Validity, integrity, and shielding live | Trust layer. It is largely built already. |

**Freeze Blender and UI work** except for wiring existing panels to the new outputs. **Every number in every document must be generated** from a JSON artefact that one command produces.

### 6.2 Architecture and code

1. **A canonical `Frame` schema.** Engine-agnostic channel names, units, timestamp, source, and quality flags. **No ground-truth field.** Truth goes to a separate stream that only the evaluator can read, and a test enforces this.
2. **Source adapters:** `PlantSource` (VirtualEngine, Monte Carlo), `ReplaySource` (Parquet, `.tlog`, ACES), `MavlinkSource` (SITL or real), `CanSource` (DBC). `TelemetryStreamer` becomes a legacy source, then is deleted.
3. **The pipeline as typed OSA-CBM stages** (DA → DM → SD → HA → PA → AG), using the [`osacbm.py`](../../backend/osacbm.py) registry as the *execution graph*. Each stage declares its cadence: crank per engine cycle, thermal at 1–10 Hz, prognostics at about 0.05 Hz.
4. **Separate processes:** `edge_node` (DA/DM/light SD, deterministic, minimal dependencies) → a message bus (MAVLink over UDP, or ZeroMQ) → `twin_server` (SD/HA/PA/AG) → `ui`. The LLM and voice become an optional separate service.
5. **`EvaluationHarness` drives the same pipeline object the service runs.** A bit-exact replay test proves it.
6. **Engine config consumed everywhere.** Add `vrde_2p2_crdi.json`, with every unknown parameter marked `"source": "UNKNOWN — to be supplied by VRDE"`. That is honest, and it shows DRDO exactly what we would need from them.
7. **A model registry.** Versioned, hashed, signed artefacts, each with a manifest of the data it was trained on.
8. **CI:** tests, a small evaluation smoke run, and a linter.

### 6.3 Algorithms

1. **Twin core.** A dynamic model plus UKF joint estimation. Start thermal-only: a first- or second-order RC per cylinder head, with cooling effectiveness ηᵢ as the parameter. Then the oil circuit, then the turbocharger.
2. **Detection.** GLR/CUSUM on normalised innovations and on θ̂ drift. Thresholds are set by conformal calibration (already built in [`conformal.py`](../../backend/evaluation/conformal.py)) to a target false-alarm rate per flight hour.
3. **Isolation.** A diagnostic Bayesian network built from [`fmeca.json`](../reliability/fmeca.json) and [`isolability.json`](../reliability/isolability.json), reporting ambiguity groups.
4. **Crank chain live** at per-cycle cadence. Its order features feed FlyHash/FBF (with time decay and regime conditioning) and FlyNN.
5. **The classifier bake-off (§4.2).** Retrain the RF on Monte Carlo plant data with build variation. Classes become FMECA modes, with the **cylinder index as a separate output** (fault type × location) instead of cylinder names baked into the classes.
6. **Prognostics.** Per-cylinder damage accumulation plus extrapolation of θ̂'s trajectory. Conformal intervals, with ACI to cope with shift. A disagreement alarm between the two paths. C-MAPSS as the method sanity check, scored with the standard PHM metrics.
7. **Decision.** Mission reliability computed from live θ̂ and damage state; prescriptive derating; an alarm rationalisation table.
8. **Distillation loop.** Ground-side heavy models → edge-sized models, with agreement on confident calls reported after every flight.

### 6.4 Data pipeline

**What each tier can honestly prove:**

| Tier | What it proves | What it cannot prove |
|---|---|---|
| Simulation Monte Carlo | Pipeline correctness; operating curves *under our assumptions* | Anything about real engines |
| Public proxies (CWRU, Paderborn, C-MAPSS, 3500-DEFault) | That the methods work on someone else's real data | Anything about this machine class |
| **ACES, fixed** | Thermal-model sim-to-real error on a real Rotax 914. **The false-alarm rate on tens of real healthy flight hours:** every flight completed safely, so every alarm raised on it is a false alarm. | Fault detection (there are no faults) |
| **Lab engine rig** | **Real combustion waveforms with seeded faults; per-cylinder attribution on metal** | Altitude and flight effects |
| VRDE test cell | The real thing | — (this is the roadmap) |

**The lab rig** is the single highest-value step from "portfolio" to "technically serious." Many Indian mechanical-engineering departments have a computerised single-cylinder CI engine test setup. These are commonly fitted with a crank-angle encoder and a piezoelectric in-cylinder pressure sensor, and it is the same combustion class as the VRDE engine. Add an IEPE accelerometer and a DAQ. Seed faults you can produce safely:

- Injector restriction, or a change in injection pressure
- Injection timing offset (many such rigs allow it)
- Air-filter restriction
- Load steps
- Reduced coolant flow

The limitation is that one cylinder allows no cross-cylinder attribution, so use a multi-cylinder rig if one is available. With no lab rig, the fallback is a used multi-cylinder four-stroke engine on a stand with a trigger wheel and Hall sensor, where misfire is induced by disabling one coil or injector. Either way, **real in-cylinder pressure is ground truth for the entire crank chain**, which no competitor will have.

**Formats and discipline.**

- Parquet for low-rate channels and HDF5/NPZ for waveforms, each with a manifest: hash, rig, date, operating point, fault seeded, severity, operator.
- Splits by session, never by frame.
- **Fix the ACES bindings** from the ACES dataset documentation first. That unlocks two real-data numbers in about a day.

### 6.5 Simulation

- **Keep the plant and the twin independent, and make them more so.** The plant already has build variation and a sensor model. Add unmodelled dynamics, meaning the twin must never share the plant's functional forms. If the team is large enough, have a second person write a second plant.
- **A Monte Carlo campaign runner:** seeds × scenarios × environments × fault onset, severity and rate, run in parallel, emitting JSON. **To claim a false-alarm rate ≤ 0.01 per hour with zero alarms observed, you need about 300 nominal hours (rule of three: 3/T).** Simulated hours are cheap, so run them.
- **A fault library aligned to the FMECA**, plus CRDi rail and injection-timing faults for the VRDE config.
- **Mission profiles:** 18 h ISR at 28 kft, Ladakh cold, Thar hot and dusty, coastal salt.
- **ArduPilot SITL with EFI** → MAVLink → our pipeline. The demo then runs on a real autopilot stack.
- **Blender:** keep it as a visualisation *of the estimated per-cylinder state*, and stop investing in it.

### 6.6 Validation (a V&V plan with numbers)

**Proposed acceptance targets.** These are to be agreed as a team. They are not results.

| Requirement | Proposed target | Measured on |
|---|---|---|
| Nominal false-alarm rate | ≤ 0.05 per flight hour (95 % upper bound) | Simulation Monte Carlo (≥ 60 h per condition) **and** ACES real flight |
| Detection probability, FMECA Category I/II modes | ≥ 0.9 at severity ≥ S within T min of onset | Simulation Monte Carlo, ≥ 30 runs per mode |
| Isolation | Correct mode, or correct ambiguity group, ≥ 0.9 | Simulation Monte Carlo |
| Lead time over the debounced threshold baseline | Reported as median with IQR | ≥ 30 runs per mode |
| Per-cylinder fault attribution | ≥ 0.95 | **Lab rig** |
| RUL | α-λ pass at α = 0.2 | C-MAPSS (method) and simulation |
| Interval coverage | Within ±2 % of nominal | Held-out simulation |
| Edge latency and power | p99 below budget; power ≤ X W | Target board |

**Also required:**

- Ablations and null models (§4.3)
- **Blind fault injection by a teammate who doesn't write the detector**
- Reproducibility: one command regenerates the V&V report

### 6.7 Documentation

Replace the sprawl with a controlled set that a defence reviewer recognises:

| Document | Contents |
|---|---|
| System Requirements Specification | Every PS line → a requirement → a verification method (automate the existing [`fun_req.md`](../fun_req.md) compliance test) |
| Architecture Description | OSA-CBM layers, the process split, data flow; generated from the registry |
| Interface Control Documents | CAN DBC, MAVLink messages, the 29-byte health frame, REST/WebSocket APIs |
| FMECA and isolability | Already exists in [`../reliability/`](../reliability/) |
| V&V plan and report | The report is generated, never hand-written |
| Safety and certification position | Advisory-only, deterministic core, ML confined to advisory outputs, the CEMILAC / IMTAR-21 path |
| Data management plan | Tiers, provenance, what each tier may be used to claim |
| Deployment roadmap | TRL 3 → 4 (lab rig) → 5 (VRDE test cell) → 6 (flight) |

**Move `UpdatedReport/` 00–30 to an archive.** They are a liability in front of a panel. Correct Report 31's VRDE statement.

### 6.8 Edge hardware

Prototype the edge node on a Raspberry Pi 5 or Jetson Orin Nano-class board, or an STM32H7/i.MX RT-class MCU for the DSP alone. Port the DSP hot path to numba first and to C later. **Measure latency and power on the board.** "Edge AI" should be a measurement, not a word.

---

## 7. Execution plan, with gates

Assuming 3–4 people. If the timeline is shorter, **the order is still right**. Phases 0–1 plus Slice 1 matter more than everything after them.

| Phase | Work | Exit gate (measurable) | Rough effort |
|---|---|---|---|
| **0 — Truth** | Fix the FlyHash label leak; fix ACES bindings; correct Report 31; archive `UpdatedReport/`; clean the repository; CI; one evaluation command that emits JSON | A test proves no detector can reach a ground-truth field; ACES EGT reads plausibly; CI is green | ~1 week |
| **1 — One pipeline** | Frame schema, source adapters, OSA-CBM stage graph; the harness runs the live pipeline; the plant is the default source; the crank chain runs live at per-cycle cadence; the Monte Carlo runner | Bit-exact replay test passes (service ≡ harness); a Monte Carlo report with CIs over ≥ 30 runs per scenario and ≥ 300 nominal hours | 2–3 weeks |
| **2 — Real waveform + ML bake-off** | Order-spectrum features; FlyHash/FBF on the spectrum; FlyNN; the bake-off (§4.2); proxy datasets; **lab-rig capture** | The bake-off table with CIs is published, winner or negative result; at least one real-engine recording has gone through the crank chain | ~3 weeks (overlaps) |
| **3 — The real twin** | UKF thermal parameter estimation; GLR detection; Bayesian-network isolation; dual RUL; conformal intervals; validity monitor live; VRDE config | Estimated cooling effectiveness tracks the plant's true degradation within its CI; RUL passes α-λ; the **ACES false-alarm number exists** | 3–4 weeks |
| **4 — Interfaces + edge** | DBC + vcan; SITL EFI end to end; the process split; the edge port; message signing; integrity checks live | SITL → edge → link → twin → UI runs; latency and power measured on the target board | 2–3 weeks |
| **5 — Operator + evidence pack** | ISA-18.2 alarm table; UI shows uncertainty and ambiguity groups; generated V&V report; certification position; roadmap to the VRDE test cell | Someone outside the team runs one command and gets the evidence report | ~2 weeks |

**What to cut first if time runs short:** further Blender work, voice, LLM features, the F19–F30 extras, and fleet-UI polish.

---

## 8. What the pitch becomes

> "We don't hand you a model trained on our own simulator. We hand you four things:
>
> 1. **A twin that estimates your engine's physical health parameters, with uncertainty**, and says when it no longer trusts itself.
> 2. **Per-cylinder injection health from the crank sensor your FADEC already has**, analysed onboard because the waveform physically cannot be downlinked.
> 3. **A validation kit that runs on your test-cell data without the data leaving your lab.**
> 4. **Evidence:** the false-alarm rate on real healthy flight hours, detection curves over thousands of simulated runs, and per-cylinder attribution measured on a real engine."

Every clause in that paragraph maps to a phase gate in §7. None of it is true today, and all of it can be.

---

## 9. Risks, and what would change this plan

| Risk | Response |
|---|---|
| No lab rig obtainable | Fall back on ACES plus public proxies, and state explicitly that combustion diagnostics are validated only in simulation and on proxies |
| FlyHash/FlyNN loses the bake-off | Ship the winner and publish the negative result (per [`study/20`](../study/20_novelty_and_research.md) §20.5) |
| Some parameters are unobservable to the UKF (for example cooling effectiveness confounded with sensor bias) | That is an isolability finding. Document it and propose the sensor that separates them. |
| DRDO will not share data | The validation-kit approach (§2.1) is the answer by design |
| The team reverts to adding features | Re-read §1 |

---

## Sources (checked 23 September 2026)

- TAPAS BH-201 indigenous engine: [Indian Defence News, Aug 2025](https://www.indiandefensenews.in/2025/08/tapas-bh-201-uav-equipped-with.html) · [idrw, Aug 2025](https://idrw.org/ade-informs-parliamentary-standing-committee-tapas-bh-201-set-for-first-flight-with-indigenous-engine/) · [defenceguru](https://www.defenceguru.co.in/news/tapas-bh-201-uav-to-begin-flight-trials-with-indigenous-engine/)
- Fly Bloom Filter: Dasgupta, Sheehan, Stevens, Navlakha, [*A neural data structure for novelty detection*, PNAS 2018](https://www.pnas.org/doi/10.1073/pnas.1814448115)
- FlyNN / FlyNN-FL: Ram & Sinha, [*Federated Nearest Neighbor Classification with a Colony of Fruit-Flies*, AAAI 2022](https://arxiv.org/abs/2112.07157) · [KDD 2021 FlyNN](https://dl.acm.org/doi/10.1145/3447548.3467246)
- FlyHash: Dasgupta, Stevens, Navlakha, *Science* 2017; [Ryali et al., ICML 2020 (BioHash)](https://proceedings.mlr.press/v119/ryali20a.html)
- Jev: [TypeSafe AI blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev) · community reproductions: [razorback16/openjev](https://github.com/razorback16/openjev), [zhangcy122/OpenJev](https://github.com/zhangcy122/OpenJev/tree/main), [Verdict-open-jev](https://github.com/Heman10x-NGU/Verdict-open-jev)
- Diesel fault dataset: [3500-DEFault, Mendeley Data](https://data.mendeley.com/datasets/k22zxz29kr/1) · [IEEE DataPort](https://ieee-dataport.org/documents/diesel-engine-faults-features-dataset-default)
- Certification: [DRDO certification services (CEMILAC)](https://drdo.gov.in/drdo/en/offerings/schemes-and-services/certification-services) · [CEMILAC–DGCA, IMTAR V2.0](https://idrw.org/cemilac-and-dgca-collaborate-on-unified-uav-certification-framework-leveraging-imtar-v2-0/)
- Model Kombat: `mk-jev-fly-brain/README.md` and `EXPERIMENTS.md` (local clone)

*Audit set: [`README.md`](README.md) · [`01`](01_competitive_audit.md) · [`02`](02_self_audit.md) · [`03`](03_the_actual_solution.md) · [`04`](04_feature_spec.md) · [`05`](05_expanded_survey.md) · [`06`](06_repo_cleanup_plan.md) · [`07`](07_unoccupied_axes_and_ground_up_plan.md) · this document.*
