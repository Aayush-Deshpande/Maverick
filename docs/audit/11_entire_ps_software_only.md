# 11 — The Entire Problem Statement, Software Only

*Written 23 September 2026. **Scope rule for this document: no hardware.** Every clause of PS-26054 (the background, §2 "integrate / capable of / may utilize", §3 A–F, §4 deliverables, §5 innovation areas and §6 technical expectations) is turned into a software component that runs on a laptop or server and can be demonstrated and measured in software. Where docs [09](09_full_depth_architecture.md)/[10](10_red_team_readiness_review.md) assumed sensors or boards, this document replaces them with emulators, simulators and **real public datasets, now downloaded** (§7).*

**Why this document exists.** Docs 07–10 went deep on the title and the sensing physics. The PS's §5 innovation areas were each given a line and never designed:

- **Physics-informed AI**
- **Edge AI for UAV applications**
- **Lightweight onboard analytics**
- **Hybrid thermodynamic + data-driven models**
- **Federated learning approaches**
- **Explainable AI for fault diagnosis**
- **Secure telemetry architecture**
- **Autonomous maintenance advisory systems**

§3 designs each of them in depth.

---

## 1. The software system

Everything below is a process, a container or a library. The "aircraft" is software too.

```
 ┌──────────────── TAIL SIMULATOR × N (one per UAV) ────────────────┐
 │ plant (thermo + turbo + crank + CI combustion + faults + build     │
 │ variation) → sensor models (noise, bias, lag, quantisation, 51.2   │
 │ kHz synthesised vibration) → FADEC EMULATOR (balancing trims,      │
 │ drift adaptation, DTCs) → vcan (J1939 broadcast · UDS · XCP)        │
 └───────────────────────────────┬───────────────────────────────────┘
                                 │  CAN frames + high-rate stream (shared memory)
 ┌───────────────────────────────▼───────────────────────────────────┐
 │ EDGE NODE × N — separate process, hard resource caps               │
 │ (e.g. 1 CPU core, 512 MB, no GPU): DSP · estimators · cascade      │
 │ detectors · INT8 models · compression · store-and-forward          │
 └───────────────────────────────┬───────────────────────────────────┘
                                 │  MAVLink 2, signed + encrypted, over a LINK EMULATOR
                                 │  (bandwidth 1–20 kbit/s, latency, loss, jamming windows)
 ┌───────────────────────────────▼───────────────────────────────────┐
 │ GCS TWIN SERVER (per base): estimator hierarchy · diagnosis BN ·    │
 │ prognostics · mission reliability · alarm management · replay       │
 ├──────────────┬──────────────────────┬──────────────────────────────┤
 │ FEDERATION   │ MAINTENANCE SERVICE  │ HMI (operator / engineer /    │
 │ SERVER       │ (work packages,      │ maintainer / fleet)           │
 │ (per service │  scheduling, spares) │                               │
 │  / DRDO)     │                      │                               │
 └──────────────┴──────────────────────┴───────────────────────────────┘
 All on-premises and air-gapped: docker compose (or k3s), no public cloud, no foreign API.
```

**Data sources, all software:**

- The physics plant (synthetic, with ground truth kept in a separate stream)
- **Real public datasets** (§7)
- NASA ACES real Rotax 914 flight data (replayed as live)
- ArduPilot SITL (MAVLink)
- The FADEC emulator

"Live" is always replay at 1× (08 §3.1), so the demo and the evidence are the same code path.

---

## 2. Every clause of the PS → a software component

| PS clause | Software component | Demonstrated by | Measured by |
|---|---|---|---|
| Background: "threshold-based and reactive" | `evaluation/threshold_baseline.py` (exists), run head to head | Harness report | Lead time, detections, false alarms per flight hour |
| §2 integrate **engine sensor data** | Ingestion adapters: CAN/J1939, MAVLink `EFI_STATUS`, XCP, replay | Live dashboard from vcan | Frame loss, end-to-end latency |
| §2 **thermodynamic behaviour models** | Differentiable lumped thermofluid model (§3.1) | Twin tracking a replayed ACES flight | Sim-to-real error per channel |
| §2 **engine performance maps** | Parametrised power/BSFC/turbo maps, fitted from data and refined per tail | Map surface in the engineer view | Fit error; drift of the per-tail map |
| §2 **failure/degradation logic** | FMECA → degradation models → damage accumulation (exist) + Bayesian network | Fault injection → diagnosis | Isolation accuracy, ambiguity groups |
| §2 **AI/ML predictive analytics** | §3 | — | — |
| §2 real-time visualisation; health indicators | HMI + estimator outputs (θ̂ with uncertainty) | Dashboard | Update rate, UI latency |
| §2 abnormal conditions; failures before occurrence | Cascade detectors + prognostics | Blind fault injection | Detection probability, lead time |
| §2 degradation trends and RUL | Dual-path RUL + conformal (exists, not wired) | RUL panel | α-λ, PH, interval coverage |
| §2 simulate mission profiles and environments | Mission simulator on the plant: ISR 18 h / 28 kft, Ladakh, Thar, coastal | What-if panel | Mission reliability with interval |
| §2 post-flight analysis and mission replay | Flight-log store (hash-chained, §3.7) + scrubbable replay through the same pipeline | Replay of a recorded sortie | Bit-exact re-run |
| §2 may use **CAN / SocketCAN** | `vcan` + python-can + cantools with our **DBC** | Candump of the emulated FADEC | Decode correctness against the DBC |
| §2 may use **ECU/FADEC interfaces** | **FADEC emulator**: J1939 broadcast, **UDS (ISO 14229)** DTC read, **XCP (ASAM)** variable read (§4) | Reading balancing trims via XCP | — |
| §2 may use **edge computing architecture** | Edge-node process (§3.3) | Resource-capped container | Latency, memory, deadline misses |
| §2 may use **cloud or local server analytics** | On-prem compose/k3s; "cloud" means DRDO's private cloud | Deploy script | Air-gapped install test |
| §2 may use AI/ML anomaly detection; physics-informed modelling; HMI | §3.1–§3.5, §5 | — | — |
| **§3A** twin synchronised with live data; modular; real-time ingestion | Estimator hierarchy (09 §5) + plugin engine configs + message bus | Three engine configs, one pipeline | Latency; config-only engine swap |
| **§3B–§3D** health monitoring, fault detection, AI/ML layer | 09 §4–§8, in software; battery/alternator per 10 §2.1 | Fault library | See 08 §6.6 |
| **§3E** replay, environments, high altitude, endurance, hot weather, **rapid throttle transitions** | Mission simulator + transient identification (10 §2.3) | Scenario library | Per-scenario detection and false-alarm rate |
| **§3F** health status, alerts, **efficiency trends**, maintenance advisory, mission-wise reports | HMI + BSFC/FMEP trends (10 §2.2) + §3.8 + mission bundle (exists) | Dashboard, PDF reports | — |
| **§4 deliverables** | §6 | — | — |
| **§5 innovation areas** | **§3 (the core of this document)** | — | — |
| **§6 technical expectations** | §5 | — | — |

---

## 3. The §5 innovation areas, designed

Each subsection covers five things: what the PS asks, what the field does, the state of the art, our software design, and how it is proven in software.

### 3.1 Physics-informed AI

**Field:** a few teams train a PINN (a thermal loss term added to a network). PRAHARI is the strongest example.

**State of the art:** PINNs are one technique among several, and for systems described by a *known ODE with unknown terms* they are often not the best one. The more effective family is **differentiable simulation** and **universal differential equations** (neural terms *inside* the physics), plus **sparse identification of nonlinear dynamics (SINDy)**, which discovers interpretable equations from data.

**Our design: a differentiable digital twin.**

1. **Write the thermofluid, turbo and combustion models once, differentiably** (PyTorch or JAX; NumPy stays as the reference). Calibration is then gradient-based: per-tail parameters θ fit by minimising the prediction error over a nominal window, with uncertainty from the Hessian or Laplace approximation. The UKF (09 §5.3) runs on the same model.
2. **Universal-differential-equation terms only where physics is known to be incomplete.** For example, head-to-coolant heat transfer (a Woschni-like term) becomes `physics(x) + NN_φ(x)`, with the network small, bounded, trained only on confirmed-nominal data, and frozen in flight.
3. **SINDy for degradation laws.** Given estimated parameter trajectories (injector efficiency kᵢ(t), cooling effectiveness ηᵢ(t)), recover a sparse law such as `dk/dt = −a·k·T_tip^b`. It is an equation a reviewer can read, and it replaces placeholder damage constants with *identified* ones.
4. **Physics as a constraint**, not just a loss: monotonicity (EGT rises with fuel at a fixed air mass), conservation (energy balance across the cylinder), and sign constraints are enforced by architecture, not hoped for.

**Proof in software.**

| Experiment | Data | Pass condition |
|---|---|---|
| Gradient-based calibration recovers the plant's hidden parameters | Plant with build variation | θ̂ within its interval for ≥ 95 % of tails |
| **Extrapolation test:** train at ≤ 15 kft, test at 25–28 kft | Plant; ACES altitude bands | Hybrid error ≪ pure-ML error outside the training envelope. **This is the argument for physics-informed AI in one plot.** |
| SINDy recovers the injected degradation law | Plant (known ground truth) | Correct terms selected, coefficients within 10 % |
| SINDy on C-MAPSS health-index trajectories | C-MAPSS (downloaded) | An interpretable law, and its RUL scored with standard PHM metrics |
| ACES thermal UDE | ACES Rotax 914 real flight | Residual whiteness improves over physics-only (NIS inside bounds) |

### 3.2 Hybrid thermodynamic + data-driven models

"Hybrid" covers six distinct patterns, and each is used in exactly one place:

| Pattern | Where in ANUMAAN | Why there |
|---|---|---|
| **Serial / residual:** physics predicts, ML models the residual | Thermofluid twin (UDE terms) | Physics carries the structure; ML fixes known gaps |
| **Parallel ensemble:** physics and ML predict independently, then disagreement is checked | **Dual-path RUL** (F38) | Disagreement is itself an alarm |
| **Physics-derived features:** ML consumes physically named quantities | The Cycle Health Vector (09 §4.7) → recognisers | Features mean something; explanation is native |
| **Physics-generated training data:** simulate, randomise, pretrain | Self-supervised encoder curriculum (09 §8.2) | Faults are rare in reality and cheap in simulation |
| **Physics as constraint** | Monotone and bounded networks (§3.1) | No physically impossible output |
| **Physics as referee:** ML may propose, physics validates | Validity monitor + integrity checks gate every ML output | ML is never the last word |

**Rule:** ML never overrides physics. It corrects physics only where the validity monitor proves persistent structured error, and only on confirmed-nominal data.

### 3.3 Edge AI for UAV applications, and lightweight onboard analytics

**Field:** "edge AI" appears as a word on a slide. Nobody builds an edge runtime or measures one.

**State of the art:** quantisation (INT8) and distillation for tiny models; cascaded or early-exit inference; event-triggered and task-oriented communication (send what changes the receiver's decision); mixed-criticality scheduling; store-and-forward under link loss.

**Our design: an edge node that is a real, separately constrained program.**

1. **Hard resource caps enforced by the OS:** for example 1 CPU core, 512 MB RAM, no GPU. This is a container with CPU and memory limits, so every latency figure is measured *under the constraint*, not on a developer's laptop.
2. **Mixed-criticality scheduler.** Priority 1: DSP and physics estimators (must never miss a cycle). Priority 2: detectors. Priority 3: learned models. Priority 4: compression and logging. **Under overload, degrade from the bottom**: the ML tier is skipped and logged as such, while the physics tier keeps its deadline. The system is an *anytime* design, never "all or nothing".
3. **Cascade inference.** Almost every cycle is healthy, so almost every cycle should cost almost nothing:

```
tier 0  every cycle   physics checks + peer ratios + trim monitor          ~µs    (always)
tier 1  every cycle   FlyHash/Fly Bloom Filter novelty                     ~10 µs (always)
tier 2  on trigger    INT8 encoder + recogniser on the flagged cycles       ~ms    (duty ≤ 5 %)
tier 3  ground        full-depth analysis on the downlinked event snippet + post-flight raw
```

4. **Model compression pipeline.** Ground teacher (full-precision encoder / ensemble) → **distilled student** → **INT8 post-training quantisation** (ONNX Runtime) → optionally pruned. It is reported as a Pareto front of detection at a fixed false-alarm rate against size, latency and memory. This is Model Kombat's first lesson made rigorous (08 §4.3): *measure agreement on confident calls, and when the student acts sooner, measure whether acting sooner wins.*
5. **Value-of-information telemetry.** Health frames are sent at a base rate (1 Hz, 29 bytes, already built). **Events** are sent when a detector's posterior changes enough to alter the ground's decision. Raw snippets are sent only on request. The link emulator shows this staying inside 1–20 kbit/s.
6. **Store-and-forward.** During link loss or jamming windows the edge keeps analysing, queues events in a priority queue (safety-relevant first), and drains on reconnect in order of importance, with each event carrying its original timestamp.
7. **Portability.** The same code is built for **x86-64 and ARM64** (docker buildx or QEMU user-mode emulation), and the ARM build runs the test suite. That is software proof it runs on an ARM-class flight computer.
8. **Frozen in flight.** Model weights and novelty memories are read-only in flight; updates happen on the ground (§3.4) and are signed (§3.7).

**Proof in software.**

- p50/p99 latency per tier under the cap
- Deadline misses per flight hour (target 0 for tiers 0–1)
- Peak memory
- Bytes on the link per hour
- Detection delay versus the uncompressed model
- Graceful degradation under an injected CPU hog
- ARM64 test pass

**Real data used:** CWRU, Paderborn, IMS and FEMTO at their real sample rates (12–64 kHz) for DSP and novelty timing, plus plant-synthesised 51.2 kHz engine waveforms.

### 3.4 Federated learning approaches

**Field:** at most FedAvg on a toy split, or nothing.

**Why federated learning here is the right tool, not a buzzword.** India's MALE-engine data is spread across organisations that **cannot pool it**:

- VRDE: test-cell data
- ADE: flight-test data
- IAF, Army and Navy squadrons: operational data, at different classifications
- Depots: maintenance outcomes

Links between them are thin, engines differ build to build, and a compromised node is a realistic threat. Federated learning is the one family of methods designed for exactly those four facts.

**State of the art, all published 2025–2026:**

- ✅ Federated RUL for aircraft engines with heterogeneous clients (clustered federation)
- ✅ A federated C-MAPSS benchmark (FedCMAPSS)
- ✅ **Robust and personalised federated learning for aircraft-engine prognostics under benign *and adversarial* heterogeneity.** It includes **"failure-masking poisoning"**, where a compromised operator trains the shared model to hide failures. It finds that architectural personalisation beats aggregation-level fixes, and that stacking robust aggregation with personalisation restores robustness (attack success 2.8 %).
- ✅ Federated conformal prediction with valid coverage for non-IID clients
- ✅ FlyNN-FL (federated nearest-neighbour classification by OR-merging fly-hash Bloom filters)

**Our design.**

**(a) Topology: hierarchical and cross-silo, not cross-device.**

```
aircraft (edge)            inference only; no training in flight
   ▼ post-flight
base / squadron GCS        LOCAL TRAINING on that base's data (silo)
   ▼ updates only
service aggregator         IAF / Army / Navy
   ▼ updates only
DRDO / VRDE aggregator     + the test-cell silo
```

Aircraft never train. Silos train on the ground on their own data, and only updates move.

**(b) What gets federated.** Five different things, from most to least interpretable:

| # | Shared object | Mechanism | Size per round | Why |
|---|---|---|---|---|
| 1 | **Fleet priors of physical parameters** (μ, Σ of injector efficiency, cooling effectiveness, wear rates) | Federated sufficient statistics → hierarchical Bayes (09 §5.5) | Kilobytes | The most interpretable federated object possible: "the fleet's injectors degrade at 0.8 ± 0.2 %/100 h" |
| 2 | **Novelty memories and FlyNN class filters** | Bitwise OR / counts (FlyNN-FL) | Kilobytes | A new fault seen at one base becomes detectable everywhere, **with no retraining** |
| 3 | **Neural models** (self-supervised encoder, RUL head) | FedAvg/FedProx + **personalisation**: shared encoder, per-tail or per-base heads | Megabytes (compressed) | Heterogeneous engines need personal heads |
| 4 | **Conformal calibration** | Federated conformal prediction (weighted quantile aggregation) | Bytes–KB | Fleet-wide coverage guarantee without pooling calibration data |
| 5 | **Diagnostic network probabilities** | Federated counts of (evidence, confirmed finding) pairs | Kilobytes | The Bayesian network learns from every base's maintenance outcomes |

**(c) Robustness, because this is defence.**

- Robust aggregation (coordinate-wise median / trimmed mean / Krum family) combined with personalisation
- **A server-side canary gate:** every candidate model must still detect a fixed suite of seeded-fault cases (simulated, plus confirmed real ones) *before* it can be promoted. A failure-masking poisoner fails the canary by construction.
- Signed updates
- Anomaly scoring of updates (norm and direction outliers)
- Quarantine of a suspicious silo

**(d) Privacy.**

- Secure aggregation, so the aggregator sees only the sum
- **Client-level differential privacy** where classification demands it
- A **classification-aware policy**: a higher-classification silo may export only objects 1, 2, 4 and 5 (statistics, never gradients)

**(e) Connectivity.**

- **Asynchronous, buffered aggregation** (bases report when they can), with staleness weighting
- Update compression (quantisation and top-k sparsification)
- Per-round byte accounting

**(f) Governance.** A round produces a candidate. The candidate must pass the canary gate, a conformal-coverage check and a non-regression check against held-out silos. It then runs in **shadow mode**, and is promoted, versioned and signed only after that.

**Framework:** Flower (Apache 2.0) for simulation and deployment. ✅ Flower apps also run in the NVIDIA FLARE runtime unchanged, which gives an enterprise path with built-in secure aggregation and PKI. DP via Opacus.

**Proof in software (all on downloaded data):**

| Experiment | Clients | Compare | Metric |
|---|---|---|---|
| Federated RUL | **C-MAPSS FD001–FD004** as four "operators" with different conditions and fault modes (FedCMAPSS-style); N-CMAPSS when downloaded | Local-only vs centralised vs FedAvg vs **personalised federated** | RMSE, NASA score, α-λ |
| **Failure-masking attack** | Same, with 1–2 poisoned clients | FedAvg vs robust aggregation vs robust + personal vs **+ canary gate** | Attack success rate, clean accuracy |
| Domain-shift federation | **MIMII DG/DUE gearbox and bearing** (machines as clients); **Paderborn artificial vs real damage** as two silos | Local vs federated vs personalised | AUC on shifted domains |
| Fleet priors | Plant: 12 tails × 3 bases (Ladakh / Thar / coastal) | Pooled vs federated statistics vs local | Time to converge θ̂ on a new tail |
| FlyNN-FL | CWRU, Paderborn, plant | Centralised FlyNN vs OR-merged | Accuracy, bytes |
| Federated conformal | All of the above | Local vs federated calibration | Realised coverage vs nominal |

### 3.5 Explainable AI for fault diagnosis

**Field:** SHAP bar charts, or a "SHAP proxy". One competitor's demo showed *"TreeSHAP attribution unavailable"* during judging.

**State of the art and regulatory anchor:** ✅ EASA's *AI Concept Paper Issue 2* gives guidance for **Level 1** (assistance to humans) and **Level 2** (human-AI teaming) ML applications, built on *learning assurance*, *AI explainability* and ethics-based assessment. ANUMAAN is a Level 1 system (it advises; humans decide), and its explainability should be organised the way that framework organises it: by stakeholder need.

**Our design: explanations by audience, by layer, and measured.**

| Audience | What they need | What we give |
|---|---|---|
| Operator | What to do, how sure, how urgent | Rationalised alarm + action + confidence + time to act |
| Propulsion engineer | Why, physically | Causal chain in physical quantities + evidence plots (crank-angle windows, orders, trims) + counterfactual |
| Maintainer | What they'll find, and how to confirm it | Expected finding + disambiguation test (09 §6.5) + nearest past cases |
| Certifier / reviewer | Can it be trusted | Model card, data provenance (MANIFEST hashes), validation evidence, known limitations |

| Layer | Native explanation |
|---|---|
| Physics estimator | **The parameter that moved is the explanation** ("η₃ 1.00 → 0.87 ± 0.03") |
| FlyHash / Fly Bloom Filter | Active units → the orders and features they sample |
| Bayesian network | Evidence contributions; most-probable explanation; ambiguity group |
| GBM | TreeSHAP, computed **on alarm only**, not every frame |
| Neural encoder | Integrated gradients over the angle-domain input → **which crank-angle window, which cylinder** |
| Any | Counterfactual: the minimal physical change that would make the verdict nominal |

**Measured, not asserted:**

- **Faithfulness:** deletion and insertion tests. Removing the attributed evidence must change the verdict.
- **Stability:** similar inputs must give similar explanations.
- 🔶 **Explanation-to-physics agreement:** the fraction of neural attributions that land in the *correct cylinder's* crank-angle window for injected faults. It is measurable because the plant knows the truth, and we know of no competitor who could even define it.

### 3.6 Secure telemetry architecture

**Field:** HMAC-signed JSON, if anything.

**Our design: a threat model first, then eight layers.**

**Threat model (STRIDE per interface):** spoofed ECU or sensor on CAN; replay or injection on the datalink; eavesdropping; compromised GCS node; **poisoned federated update**; malicious dependency (supply chain); tampered flight log; insider.

| Layer | Mechanism | Notes |
|---|---|---|
| 1. Datalink authentication | ✅ **MAVLink 2 message signing**: SHA-256 truncated to 48 bits over key + header + payload + CRC + link ID + timestamp; 32-byte secret key; 48-bit timestamp in 10 µs units, monotonic per link, with replay rejection | ✅ **Signing authenticates but does not encrypt.** That is why layer 2 exists. |
| 2. Datalink confidentiality | AES-256-GCM over the payload or tunnel, through a **pluggable crypto module**, so DRDO-approved or indigenous ciphers drop in | Crypto-agility is itself a requirement |
| 3. Key management | Per-airframe keys, rotation, revocation, provisioning ceremony, and keys never in source control | — |
| 4. **Post-quantum readiness** | Hybrid key exchange (X25519 + **ML-KEM, FIPS 203**) and signatures (**ML-DSA, FIPS 204**) for ground-to-ground links and for signing models and configs | Long-lived defence data faces "harvest now, decrypt later" |
| 5. In-vehicle (CAN) intrusion detection | (a) **Physics integrity**: injected values must obey engine physics ([`twin/integrity.py`](../../backend/twin/integrity.py), exists). (b) **Protocol and timing IDS**: message timing, ID sequence and payload-field models. | Trained and tested on **ROAD** (real vehicle, fuzzing, fabrication and masquerade attacks) and **SynCAN** (both downloaded). Masquerade attacks are exactly where timing IDS fails and physics integrity is needed. |
| 6. Evidence integrity | Every flight log is **hash-chained**, and each sortie is sealed with a Merkle root, signed | Chain of custody for incident investigation. Tamper with one frame and verification fails. |
| 7. Service security | mTLS between services, role-based access (operator / engineer / maintainer / admin), append-only audit log | — |
| 8. Supply chain | SBOM for every dependency, pinned hashes, **no Chinese-origin components** (10 §2.6), signed models and configs, reproducible builds | — |

**Proof in software:**

- Replayed, forged and modified frames rejected on the emulated link, with rates reported
- The CAN IDS on ROAD/SynCAN reported with the point-wise **and** point-adjusted protocol side by side ([`validation.py`](../../backend/evaluation/validation.py) F62 already computes both)
- A tampered log detected
- A poisoned federated update stopped by the canary gate (§3.4)

### 3.7 Autonomous maintenance advisory systems

**Field:** a static "recommended action" string per fault.

**Our design: from recommendation to a closed loop, with a human approving each step.**

| Autonomy level | What the system does | Human role |
|---|---|---|
| L1 Recommend | Diagnosis → maintenance task (from the FMECA-derived task library), expected finding, confirmation test | Decides |
| L2 Plan | **Work package**: tasks, parts, tools, time, prerequisite ground test, evidence attached | Approves |
| L3 Schedule | **Constraint optimiser** (OR-Tools CP-SAT, Apache 2.0) over mission schedule, aircraft availability, spares, crew and maintenance windows. Output: *when* and *on which tail*. | Approves the schedule |
| L4 Close the loop | Captures the finding (confirmed / different / no fault found) → updates the Bayesian network (federated, §3.4), the task library and the **no-fault-found rate KPI** | Audits |

- **Spares forecasting** from the RUL distributions across the fleet (probabilistic demand per part per month).
- **Tail-to-mission assignment** (F59) by mission reliability.
- **Language:** an Indian open model (10 §2.6), used only to *phrase* the work package. Every fact comes from the optimiser, the rules and the evidence, and is cited.

**Proof in software: a fleet discrete-event simulation.** Twelve tails at three bases for one simulated year, with degradation, faults, missions, maintenance capacity and spares lead times. Compare three policies:

- (a) Fixed-interval maintenance
- (b) Reactive maintenance
- (c) **ANUMAAN-advised**

Report availability, mission aborts, unscheduled removals, the no-fault-found rate and spares cost. That turns "autonomous maintenance advisory" into a number for the PS's own "scale of impact".

### 3.8 The remaining §5 item: lightweight onboard analytics

Covered by §3.3. The explicit budget comes from doc 09 §9: the DSP and estimator core is about 0.3 GFLOP/s, with the cascade keeping learned models at ≤ 5 % duty.

---

## 4. The FADEC emulator: the software stand-in that makes Kit 0 real

Kit 0 (10 §2.5) reads data the FADEC already has. In software, a FADEC emulator attached to the plant provides it through the three interfaces a real ECU uses:

| Interface | Standard | Emulated content |
|---|---|---|
| Broadcast | CAN / **SAE J1939**-style PGNs, defined in **our DBC** | RPM, MAP, boost, temperatures, rail pressure, commanded SOI and quantity, bus V/I |
| Diagnostics | **UDS (ISO 14229)** | Diagnostic trouble codes, freeze frames, and **routine control for active tests** (cylinder cut-out, rail step: 09 §6.5) |
| Measurement | **XCP (ASAM MCD-1)** | Internal variables: **cylinder-balancing corrections, drift-adaptation values, controller duties**. This is how an engineer reads a real ECU's internals, and how Kit 0 gets principle 4's "FADEC effort". |

The emulator also runs the **balancing and drift-adaptation loops**, so faults are masked in EGT exactly as they would be in reality (09 §12). Our detectors must see through that masking.

---

## 5. §6 Technical expectations: how the software shows each one

| Expectation | Where the software demonstrates it |
|---|---|
| IC engine fundamentals | CI combustion model (ignition delay, double Wiebe, multi-injection), per-cylinder analysis, crank dynamics |
| UAV propulsion systems | Turbo/altitude model, propeller load and gearbox, mission profiles, restart readiness |
| Sensor fusion | UKF joint estimation; crank + vibration complementary fusion; peer referencing |
| Embedded systems | Edge node under hard caps, mixed-criticality scheduler, fixed-point reference DSP, ARM64 build |
| CAN communication | vcan + DBC + J1939 + UDS + XCP emulator; CAN IDS |
| AI/ML analytics | §3 |
| Data visualisation | Role-based HMI; crank-angle and order views; estimator states with uncertainty |
| Simulation modelling | Plant with build variation, fault library, Monte Carlo campaigns, fleet discrete-event simulation |
| Reliability engineering | FMECA, isolability, damage accumulation, mission reliability with intervals, RCM-style task library |

---

## 6. §4 Deliverables, as software artefacts

| Deliverable | Artefact |
|---|---|
| Functional prototype / demonstrator | `docker compose up`: N tail simulators + edge nodes + link emulator + GCS + federation + maintenance + HMI |
| Digital Twin architecture design | Architecture description generated from the OSA-CBM registry (exists) + ICDs (DBC, MAVLink, XCP variable list, health frame) |
| Engine simulation model | Plant with three engine configs (VRDE-class CRDi, Rotax 914, Rotax 915 iS) + documentation of every assumption |
| AI/ML-based anomaly detection module | Cascade detectors + bake-off report (08 §4.2) with nulls and CIs |
| Visualisation dashboard | HMI (§3.5 audiences) |
| Demonstration using simulated or real engine datasets | **Both.** Plant Monte Carlo *and* the real datasets of §7, reported separately and never merged into one headline |
| Technical documentation and deployment roadmap | The 08 §6.7 document set + this document + the tier/kit roadmap (10 §2.5, §2.10) |

---

## 7. Real datasets: what is downloaded and what each one proves

Downloaded by [`Datasets/download_all.py`](../../Datasets/download_all.py) (resumable, segmented; every file hashed in `Datasets/MANIFEST.json`). Tier A arrives first; the whole set takes several hours on the current link (§8).

| Dataset | Machine / content | Licence | Proves which PS item |
|---|---|---|---|
| **Marine Engine Fault** (Zenodo) | **Real marine diesel engine**: baseline + 5 induced fault/anomaly classes | CC-BY-4.0 | Anomaly detection and fault classification on **real diesel engine data**, the closest public match to the engine class |
| **3500-DEFault** (Mendeley) | Diesel: cylinder pressure + crankshaft torsional features; intake-pressure, compression and injected-fuel faults | CC-BY-4.0 | Injector and compression diagnostics from crank-torsional features (09 §4.1) |
| **Engine Journal Bearings** (Mendeley) | **IC engine** main journal bearings, tri-axial vibration, varied climate/operating conditions | CC-BY-4.0 | Lubrication/bearing faults on an IC engine; domain shift across conditions |
| **C-MAPSS** ✅ downloaded | Turbofan run-to-failure (4 sub-datasets) | US Gov | RUL, PHM metrics, **federated RUL (FD001–FD004 as operators)**, SINDy |
| N-CMAPSS | Realistic-flight turbofan degradation (15.8 GB) | US Gov | Federated RUL at scale; flight-profile conditioning |
| CWRU | Bearing faults, 12/48 kHz | Cite site | DSP, envelope, FlyHash/FBF bake-off, edge timing |
| Paderborn | Bearings, **artificial vs real** damage | Cite | Sim-to-real style shift; federated silos |
| IMS, FEMTO | Bearing run-to-failure | US Gov / cite | Vibration RUL, prognostic metrics |
| MIMII DG / DUE (gearbox, bearing) | Machine sound under **domain shift** | CC-BY / CC-BY-NC-SA | Domain generalisation, federated personalisation |
| **NASA Battery** (+ randomized usage) | Li-ion ageing | US Gov | **Battery health** (PS §3B battery/alternator; 10 §2.1): state of health and RUL methods |
| **ALFA** | **Real fixed-wing UAV flights, engine-failure and actuator faults** | CC-BY-4.0 | UAV-context anomaly detection, flight-phase conditioning |
| **ROAD**, **SynCAN** | CAN intrusion (real vehicle / synthetic) | CC-BY-4.0 / check | **Secure telemetry**: CAN IDS, masquerade vs physics integrity |
| SKAB | Multivariate anomaly (pump rig) | GPL-3.0 | Anomaly protocol, point-wise vs point-adjusted scoring |
| NASA ACES (already on disk) | **Real Rotax 914 on the Altus II UAV** | NASA | Thermal twin sim-to-real; **false-alarm rate on real healthy flight** |

🔶 **Still not public anywhere:** a labelled run-to-failure dataset for an aero piston engine on a MALE UAV. That is why the plant, the fleet simulator and the validation kit for DRDO's own data (08 §2.1) exist.

---

## 8. Build order (software only)

| Step | Content | Visible result |
|---|---|---|
| 1 | Fix the truth issues (08 Phase 0), swap Qwen out, one-pipeline refactor (08 Phase 1) | Replay test: service ≡ harness |
| 2 | FADEC emulator + DBC + vcan/UDS/XCP; link emulator; edge node under caps | "Aircraft" talking to the GCS over a throttled, signed link |
| 3 | Differentiable twin + UKF + SINDy; ACES and C-MAPSS experiments | Physics-informed AI numbers on real data |
| 4 | Cascade detectors + bake-off on CWRU/Paderborn/marine/3500-DEFault + plant | Detection report with nulls and CIs |
| 5 | Federation: Flower, hierarchical silos, personalisation, robust aggregation, canary gate, federated conformal | Federated RUL + attack results on C-MAPSS; MIMII/Paderborn shift results |
| 6 | Security layers + CAN IDS on ROAD/SynCAN + hash-chained logs | Attack-rejection report |
| 7 | Maintenance service + CP-SAT scheduler + fleet discrete-event simulation | One-year fleet comparison of three policies |
| 8 | HMI by audience + explanation metrics | The demo |

Each step ends in a generated report, so the evidence accumulates as the system does.

---

## Sources (checked 23 September 2026)

- Federated learning for engine prognostics: [Robust and personalised FL for aircraft-engine prognostics (failure-masking poisoning)](https://arxiv.org/abs/2608.04045) · [FL framework for collaborative RUL, aircraft-engine case](https://arxiv.org/html/2506.00499) · [FedCMAPSS benchmark](https://arxiv.org/pdf/2608.26433) · [Heterogeneity-aware personalised FL for industrial analytics](https://arxiv.org/pdf/2604.19451)
- Robust / asynchronous FL: [AFLGuard](https://dl.acm.org/doi/10.1145/3564625.3567991) · [SecureAFL](https://arxiv.org/pdf/2604.03862) · [Local model poisoning attacks (USENIX Sec 2020)](https://www.usenix.org/system/files/sec20summer_fang_prepub.pdf) · [EnCAgg](https://arxiv.org/pdf/2605.22506)
- Federated conformal: [FCP, ICML 2023](https://proceedings.mlr.press/v202/lu23i/lu23i.pdf) · [FedCP, non-IID](https://link.springer.com/chapter/10.1007/978-3-032-31141-2_21) · [Group-conditional FCP](https://arxiv.org/html/2603.14198v3)
- Frameworks: [Flower](https://arxiv.org/pdf/2007.14390) · [Flower + NVIDIA FLARE](https://arxiv.org/pdf/2407.00031) · [NVIDIA FLARE](https://arxiv.org/pdf/2210.13291) · [FL framework benchmark](https://www.researchgate.net/publication/397231654_Benchmarking_Federated_Learning_Frameworks_for_Medical_Imaging_Deployment_A_Comparative_Study_of_NVIDIA_FLARE_Flower_and_Owkin_Substra)
- FlyNN-FL: [Ram & Sinha, AAAI 2022](https://arxiv.org/abs/2112.07157)
- Explainability and assurance: [EASA AI Concept Paper Issue 2](https://www.easa.europa.eu/en/document-library/general-publications/easa-artificial-intelligence-concept-paper-issue-2) · [EASA news release](https://www.easa.europa.eu/en/newsroom-and-events/news/easa-publishes-artificial-intelligence-concept-paper-issue-2-guidance)
- MAVLink signing: [mavlink.io — message signing](https://mavlink.io/en/guide/message_signing.html)
- CAN IDS data: [ROAD (PLOS One)](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0296879) · [ROAD on Zenodo](https://zenodo.org/records/10462796) · [SynCAN](https://github.com/etas/SynCAN) · [CAN-MIRGU](https://www.ndss-symposium.org/wp-content/uploads/vehiclesec2024-43-paper.pdf)
- Datasets: [Marine Engine Fault](https://zenodo.org/records/19857425) · [3500-DEFault](https://data.mendeley.com/datasets/k22zxz29kr/1) · [Engine Journal Bearings](https://data.mendeley.com/datasets/3fcrrdjjvk/4) · [ALFA](https://kilthub.cmu.edu/articles/dataset/ALFA_A_Dataset_for_UAV_Fault_and_Anomaly_Detection/12707963) · [MIMII DG](https://zenodo.org/records/6529888) · [MIMII DUE](https://zenodo.org/records/4740355) · [CWRU](https://engineering.case.edu/bearingdatacenter) · [Paderborn](https://mb.uni-paderborn.de/kat/forschung/kat-datacenter/bearing-datacenter) · [NASA PCoE repository](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/) · [SKAB](https://github.com/waico/SKAB)
- Post-quantum standards: NIST FIPS 203 (ML-KEM) and FIPS 204 (ML-DSA), August 2024.

*Audit set: [`README.md`](README.md) · [`08`](08_deployable_system_blueprint.md) · [`09`](09_full_depth_architecture.md) · [`10`](10_red_team_readiness_review.md) · this document (software-only, entire PS).*
