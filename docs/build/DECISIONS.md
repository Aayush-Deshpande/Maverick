# Decision Register

*New here? Read [`MENTAL_MODEL.md`](MENTAL_MODEL.md) first for orientation.*

Every architectural decision the build depends on, in one place. Each entry records what was decided, why, the evidence, what it supersedes, and whether it is implemented yet. **If a document elsewhere contradicts this register, this register wins, unless the actual code and passing tests prove otherwise** — a decision recorded here that the code has since diverged from is a bug in the code or in this file, not a reason to silently pick one.

Status: **DONE** (implemented and tested) · **PARTIAL** · **DECIDED** (not built yet) · **ROADMAP** (deliberately deferred)

| ID | Decision | Status |
|---|---|---|
| D01 | Target engines and configs | PARTIAL |
| D02 | Advisory-only system, deterministic core | DECIDED |
| D03 | The twin is an estimator, not a generator | DECIDED |
| D04 | Plant ≠ twin; ground truth isolated | PARTIAL |
| D05 | One pipeline, many sources; live = replay at 1× | DECIDED |
| D06 | ISO 13374 / OSA-CBM layering | PARTIAL |
| D07 | The engine cycle is the unit of analysis | DECIDED |
| D08 | Sampling plan: 51.2 kHz vibration, crank edges timestamped | DECIDED |
| D09 | FADEC effort is a primary health signal; Kit 0 first | DECIDED |
| D10 | Peer referencing across cylinders | DECIDED |
| D11 | Detectors are evidence; a Bayesian network decides; conformal thresholds | DECIDED |
| D12 | Role of the fly-brain methods | PARTIAL |
| D13 | Jev excluded from runtime | DECIDED |
| D14 | LLM optional, grounded, not Chinese-origin | DONE (B0.2, 24 Sep; Ollama tags for sarvam/bharatgen unconfirmed) |
| D15 | Federated learning: hierarchical cross-silo, robust, personalised | DECIDED |
| D16 | Edge node as a separately constrained process | PARTIAL |
| D17 | Eight-layer security architecture | PARTIAL |
| D18 | Dual-path prognostics with conformal intervals | PARTIAL |
| D19 | Mission reliability as a computed probability; risk-based Go/No-Go | PARTIAL |
| D20 | Maintenance autonomy L1–L4 with human approval | DECIDED |
| D21 | Evaluation discipline | PARTIAL |
| D22 | Datasets enter at the layer they validate | DECIDED |
| D23 | Software only for now; hardware is roadmap | DECIDED |
| D24 | Indigenous and supply-chain rules | DECIDED |
| D25 | 3D visualisation shows estimated state; no further investment | DECIDED |
| D26 | Build vertical slices; stop broad brainstorming | DECIDED |
| D27 | Engine-universal by profile: selecting an engine drives everything; no engine/cylinder/redline literals in inference, twin, service or UI | DECIDED (not built; ratchet enforced) |
| D28 | Every model/dataset artifact carries a provenance sidecar; artifacts without one are untrusted | DECIDED (not built) |
| D29 | Multi-engine runtime: every profile simulates concurrently with cheap tier-0/1 detectors; **heavy inference runs only for the dropdown-selected engine** (or on escalation) | DECIDED (amended 24 Sep) |
| D30 | Fault/lever layering L1-L4; every injection logged with an origin; manual levers excluded from KPIs; direct reading override only in a test bench | DECIDED (not built) |
| D31 | Detector strategy: engine-calibrated residuals + cheap classical detector; universal classifier with per-engine override | DECIDED (evidence: E17, simulation) |
| D32 | SUPERSEDED by D36: fly line kept as the innovation tier (FlyHash tier-0 + connectome-initialised reservoir tier-1) | SUPERSEDED |
| D33 | Jev/OpenJev: not on the 20 Hz path; tier-2 text-serialised ground contender + advisory ranker (D37) | AMENDED |
| D36 | Fly innovation tier: FlyHash/FBF tier-0 (Pi 5), connectome-initialised reservoir + ridge tier-1 (selected engine), GPU tier-2; claims limited to E17/E19 | DECIDED (evidence: E19) |
| D37 | Jev/open-Jev on DRDO-class GPU: selected-engine tier-2 contender on HealthFrame-as-text + maintenance ranker; kept only if it wins a bake-off (W10) | DECIDED (test owed) |
| D34 | Waveform -> edge (Pi-5-class, emulated) -> persistence-gated scalars pipeline | DECIDED (not built) |
| D35 | Third-party code needs a present, permissive licence; unlicensed repos are excluded | DECIDED |

---

### D01 — Target engines

- **Decision:** engine class is configuration. Configs in scope:

| Config | Why | Provenance quality |
|---|---|---|
| `vrde_jayem_2_2l` (**primary**) | The indigenous TAPAS BH-201 engine: 2.2 L inline-4, turbocharged CRDi, FADEC, 180 hp at 11,000 ft, operable to 32,000 ft, VRDE with JAYEM | ✅ Those facts are public (Indian Defence News, idrw, Aug 2025). ⚠️ **Every other value in the existing file (bore 85, stroke 96, CR 17.2, 3,800 rpm, 1,850 bar, firing order, turbo map) is an assumption** but is labelled as a "specification". **Relabelled per field on 24 Sep (B0.4):** only the handful of public facts are `PUBLIC`; the rest are `ASSUMED`/`PLACEHOLDER`. |
| `rotax_914` | Heron Mk I; the engine in NASA ACES (the only real MALE piston flight data) | ✅ Manuals in `docs/reference/` |
| `rotax_915is` (**added 24 Sep, B0.4**) | **Heron Mk II in IAF/Army service**: 1,352 cc turbo, 141 hp take-off, TBO 1,200 h | ✅ Janes / IAI public data |
| `austro_ae300` | Earlier TAPAS prototypes; licensed Mercedes OM640; the best *public* proxy for a CRDi aero diesel | ✅ Public |
| `rotax_912is` | Legacy; what the original code was written for | ✅ Public |

- **Why:** the PS says "injection timing parameters", "MALE" (altitude, so turbo) and "indigenous". For a CRDi engine, **injection health, not misfire, is the primary combustion diagnostic**.
- **Supersedes:** the Rotax-912-only codebase, [`audit/07`](../audit/07_unoccupied_axes_and_ground_up_plan.md) Part II ("switch to AE300"), and the claim in [`UpdatedReport/31`](../../UpdatedReport/31_VERIFICATION_AND_CORRECTIONS.md) §2.2 that the VRDE figures are unsourced.
- **Sources:** [`audit/08`](../audit/08_deployable_system_blueprint.md) §0 and [`audit/10`](../audit/10_red_team_readiness_review.md) §2.8.

### D02 — Advisory-only, deterministic core

- **Decision:** the system advises and never commands. The deterministic core (DSP, physics estimators, thresholds) is verifiable. ML outputs are *evidence*, gated by runtime monitors.
- **Why:** CEMILAC certifies all military airborne software; DO-178C has no accepted route for learned models in control paths; EASA's AI Concept Paper Issue 2 treats Level 1 (assistance) systems this way.
- **Sources:** [`audit/07`](../audit/07_unoccupied_axes_and_ground_up_plan.md) Part III.4 · [`audit/09`](../audit/09_full_depth_architecture.md) §10 · [`audit/11`](../audit/11_entire_ps_software_only.md) §3.5

### D03 — The twin is an estimator

- **Decision:** the digital twin is a dynamic lumped-parameter model plus **joint state/parameter estimation** (UKF, particle filter, differentiable calibration). Health means *estimated physical parameters with uncertainty*: per-cylinder injector efficiency, cooling effectiveness, turbo efficiency, sensor biases.
- **Why:** it is asset-specific, calibrated and predictive, which is the definition of a twin; a class label is not.
- **Supersedes:** [`thermo_model.py`](../../backend/physics/thermo_model.py)'s algebraic steady-state expectation as the twin.
- **Sources:** [`audit/08`](../audit/08_deployable_system_blueprint.md) §3.4 · [`audit/09`](../audit/09_full_depth_architecture.md) §5 · [`audit/11`](../audit/11_entire_ps_software_only.md) §3.1

### D04 — Plant ≠ twin; ground truth isolated

- **Decision:** synthetic data comes only from [`backend/plant/virtual_engine.py`](../../backend/plant/virtual_engine.py), whose physics differs from the twin's. Ground truth goes to a **separate truth stream** that only evaluators may read; **no detector may access a truth field** (enforced by a test).
- **Fixed 24 Sep (B0.1):** the FlyHash calibration no longer reads `actual.FAULT_ID`; `tests/test_no_truth_leak.py` enforces it. **Still open:** the live service runs on `EnginePhysicalState` (which carries `FAULT_ID`) and the circular streamer; `Frame`/`TruthRecord` (B1.1) exist but are not on the live path yet.
- **Sources:** [`IMPLEMENTATION_LOG.md`](../IMPLEMENTATION_LOG.md) G01 · [`audit/08`](../audit/08_deployable_system_blueprint.md) §5.D

### D05 — One pipeline, many sources

- **Decision:** a single pipeline object serves the live service *and* the evaluation harness. Sources (plant, replay, MAVLink/SITL, CAN) are adapters. **Live = replay at 1×.** A bit-exact replay test proves that the service and the harness produce identical outputs.
- **Why:** today the demonstrated system (`DetectionPipeline`) is not the measured one (`ResidualDetector` in the harness).
- **Source:** [`audit/08`](../audit/08_deployable_system_blueprint.md) §1, §3.1

### D06 — ISO 13374 / OSA-CBM layering

- **Decision:** stages are typed DA → DM → SD → HA → PA → AG, and [`backend/osacbm.py`](../../backend/osacbm.py) becomes the *execution* graph, not only documentation.
- **Source:** [`audit/07`](../audit/07_unoccupied_axes_and_ground_up_plan.md) Part III.1 · [`ARCHITECTURE_OSACBM.md`](../ARCHITECTURE_OSACBM.md)

### D07 — The engine cycle is the unit of analysis

- **Decision:** process in the crank-angle domain. One engine cycle (720°) is one observation. Output: the **Cycle Health Vector** (see [`INTERFACES.md`](INTERFACES.md) §4).
- **Source:** [`audit/09`](../audit/09_full_depth_architecture.md) §0, §4

### D08 — Sampling plan

| Channel | Rate |
|---|---|
| Block/head/gearbox accelerometers | **51.2 kHz** (usable band 20 kHz) |
| Turbo accelerometer | 102.4 kHz, or a speed sensor |
| Rail pressure | ≥ 30 kHz |
| Crank/cam/prop-shaft edges | **Timestamped** at ≤ 25 ns |
| FADEC CAN | 10–100 Hz |
| Thermal channels | 1–10 Hz |

- **Why:** combustion-chamber acoustic modes (Draper) lie between about 5.6 and 20 kHz for 79–85 mm bores; 2.56 × 20 kHz = 51.2 kHz.
- **Supersedes:** "2–10 kHz" in [`study/02`](../study/02_engine_sensors.md), [`06`](../study/06_vibration_analysis.md), [`24`](../study/24_combustion_cycle_and_crank_dynamics.md), [`26`](../study/26_order_tracking_and_envelope.md) and [`proposal.md`](../study/proposal.md).
- **Source:** [`audit/09`](../audit/09_full_depth_architecture.md) §2
- In software-only mode (D23) these rates apply to the *synthesised* signals.

### D09 — FADEC effort is a primary health signal; Kit 0 first

- **Decision:** a CRDi FADEC's cylinder-balancing corrections and drift-adaptation values *mask* injector faults from the temperature channels, so **monitoring the corrections is the earliest injector-health signal**.
- **Deployment order:** Kit 0, software reading existing FADEC data (CAN broadcast, UDS diagnostics, XCP measurement), comes before any new sensor.
- **Sources:** [`audit/09`](../audit/09_full_depth_architecture.md) §4.4 · [`audit/10`](../audit/10_red_team_readiness_review.md) §2.5 · [`audit/11`](../audit/11_entire_ps_software_only.md) §4

### D10 — Peer referencing

- **Decision:** per-cylinder features are expressed relative to the median of the other cylinders *in the same cycle*. Common-mode effects (altitude, load, fuel) cancel; a cylinder-specific fault stands out.
- **Source:** [`audit/09`](../audit/09_full_depth_architecture.md) §0 principle 3, §4.2

### D11 — Detectors are evidence; a Bayesian network decides

- **Decision:** four detectors produce *evidence*:
  1. Parameter change (GLR/CUSUM on θ̂)
  2. Peer detector
  3. Novelty (FlyHash / Fly Bloom Filter)
  4. Recogniser (FlyNN / GBM)

  A **diagnostic Bayesian network built from the FMECA** turns the evidence into ranked hypotheses with **ambiguity groups**. Thresholds are set by **conformal calibration to a target false-alarm rate per flight hour**.
- **Active diagnosis:** when hypotheses remain ambiguous, the twin requests the FADEC test with the highest expected information gain (cylinder cut-out, rail step, SOI sweep…).
- **Source:** [`audit/09`](../audit/09_full_depth_architecture.md) §6

### D12 — The fly-brain methods

- **Decision:**
  - FlyHash plus a regime-conditioned, time-decaying **Fly Bloom Filter** is the **edge novelty layer**, fed the *order spectrum and Cycle Health Vector*, not 14 residuals.
  - **FlyNN** is the recogniser for **open-set, few-shot and federated** use.
  - Both are adopted **only through the bake-off** (E06) against a **dense-random-projection null**, RF, LightGBM, MLP and PCA-Mahalanobis. A negative result is published, not hidden.
  - Spiking connectome simulations (maleCNS, FlyWire, Model Kombat) are **not** used for diagnosis.
- **Why:** at 14 dimensions FlyHash is neither cheaper nor more accurate than an RF (21 Sep 2026 analysis). Expand-and-sparsify works in high dimensions. FlyNN-FL federates by OR-merging bit arrays.
- **Do not claim** the algorithm is novel. It is published (Dasgupta et al. *Science* 2017, *PNAS* 2018; Ram & Sinha AAAI 2022).
- **Sources:** [`study/20`](../study/20_novelty_and_research.md) · [`audit/08`](../audit/08_deployable_system_blueprint.md) §4 · [`audit/09`](../audit/09_full_depth_architecture.md) §6.3 · [`audit/12`](../audit/12_dataset_implementation.md) E06

### D13 — Jev excluded from runtime

- **Decision:** TypeSafe's Jev (closed, hosted US API) is **not used**.
- Community "OpenJev" reproductions are weeks old and unaudited. The only allowed use is *ranking maintenance actions* on-prem, logged, never auto-actioned. Preferred alternative: **distil to a transparent policy** (Model Kombat's 168-weight lesson).
- The `mk-jev-fly-brain/` clone is reference material for **experimental method** (null controls, distillation, curriculum), not code.
- **Source:** [`audit/08`](../audit/08_deployable_system_blueprint.md) §4.3–4.4

### D14 — LLM

- **Decision:** the LLM is optional and retrieval-grounded; it *phrases* facts produced by deterministic components and never decides. **The default must not be a Chinese-origin model.**
- **Fixed 24 Sep (B0.2):** `backend/agent/llm_engine.py` now defaults to `ANUMAAN_LLM_PROVIDER=none` (disabled); Qwen remains an explicit opt-in only. The 7.6 GB Qwen weights in `vendor/` are vestigial.
- **Options:** Indian open models (Sarvam, Apache-2.0; BharatGen Param2), or no LLM in the deliverable.
- **Why:** the Army cancelled 400 drones in 2025 over Chinese components.
- **Source:** [`audit/10`](../audit/10_red_team_readiness_review.md) §2.6

### D15 — Federated learning

- **Decision:** hierarchical and **cross-silo**: aircraft never train; bases, labs and depots train on the ground; updates flow squadron → service → DRDO/VRDE.
- **Five shared objects:**
  1. Fleet parameter priors (sufficient statistics)
  2. Novelty memories and FlyNN filters (bitwise OR)
  3. Neural models with personalised heads
  4. Conformal calibration
  5. Bayesian-network counts
- **Robust aggregation + personalisation + a canary gate** (a candidate must still detect a seeded-fault suite) against failure-masking poisoning. Secure aggregation; client-level DP where classification requires; asynchronous buffered rounds; Flower (Apache-2.0).
- **Source:** [`audit/11`](../audit/11_entire_ps_software_only.md) §3.4

### D16 — Edge node

- **Decision:** a separate process under OS-enforced CPU and memory caps, with a mixed-criticality scheduler (DSP/physics > detectors > ML > compression) that degrades from the bottom.
  - Cascade inference: tier 0/1 every cycle; learned models only on trigger, at ≤ 5 % duty.
  - Compression: distillation → INT8 (ONNX Runtime).
  - Value-of-information telemetry; store-and-forward.
  - x86-64 and ARM64 builds.
  - Frozen in flight.
- **Source:** [`audit/11`](../audit/11_entire_ps_software_only.md) §3.3

### D17 — Security

**Eight layers:**

1. MAVLink 2 signing (authentication only)
2. AES-256-GCM through a pluggable crypto module
3. Key management
4. Post-quantum readiness (ML-KEM FIPS 203, ML-DSA FIPS 204)
5. CAN IDS: timing/ID/payload **plus** physics integrity (built: [`twin/integrity.py`](../../backend/twin/integrity.py))
6. Hash-chained, Merkle-sealed flight logs
7. mTLS + RBAC + audit log
8. SBOM + signed models + no Chinese-origin components

- **Source:** [`audit/11`](../audit/11_entire_ps_software_only.md) §3.6

### D18 — Prognostics

- **Decision:** dual-path RUL: physics-of-failure damage accumulation via a particle filter, plus data-driven parameter-trajectory extrapolation. Both carry **conformal intervals** (ACI under shift), and a **disagreement alarm** fires when they diverge. RUL is expressed in the maintainer's units (flight hours, sorties of a given profile).
- **Built but unconnected:** [`damage_accumulation.py`](../../backend/evaluation/damage_accumulation.py), [`conformal.py`](../../backend/evaluation/conformal.py), [`prognostic_metrics.py`](../../backend/evaluation/prognostic_metrics.py)
- **To be replaced:** [`rul_estimator.py`](../../backend/ml/rul_estimator.py), which uses hardcoded lifetimes
- **Source:** [`audit/09`](../audit/09_full_depth_architecture.md) §7.1

### D19 — Mission reliability and decisions

- **Decision:** mission reliability = P(no propulsion-induced abort | θ̂ posterior, damage, profile, environment), by Monte Carlo with an interval.
- Go/No-Go is chosen by **expected loss**, not a threshold. Prescriptive derating and in-flight contingency follow. Electrical power availability is a separate reliability term (FADEC diesels quit without power).
- **Built on placeholder hazards:** [`mission/reliability.py`](../../backend/mission/reliability.py), [`prescriptive.py`](../../backend/mission/prescriptive.py)
- **Sources:** [`audit/07`](../audit/07_unoccupied_axes_and_ground_up_plan.md) Part X · [`audit/10`](../audit/10_red_team_readiness_review.md) §2.1

### D20 — Maintenance autonomy

- **Decision:** L1 recommend → L2 work package → L3 CP-SAT schedule → L4 close the loop on outcomes (the no-fault-found KPI), with a human approving at every level. Evaluated by a one-year, 12-tail fleet discrete-event simulation under three policies.
- **Source:** [`audit/11`](../audit/11_entire_ps_software_only.md) §3.7

### D21 — Evaluation discipline

- **Keep separate:** simulation, public proxy and real flight.
- **Splits:** by unit, flight, bearing or engine only.
- **Anomaly detection:** report **point-wise and point-adjusted F1 side by side** (the instrument exists in [`validation.py`](../../backend/evaluation/validation.py)).
- **False-alarm rate per flight hour with the 95 % upper bound** (zero alarms in T hours ⇒ ≤ 3/T).
- Null models and ablations; blind fault injection by someone who didn't write the detector.
- **Every number in documents is generated by a script.**
- **Sources:** [`audit/08`](../audit/08_deployable_system_blueprint.md) §6.6 · [`study/19`](../study/19_evaluation.md)

### D22 — Datasets

- **Decision:** each public dataset enters **at the layer it validates**. Only flight telemetry (ACES, ALFA) is replayed through the full pipeline. Loaders return typed records with group keys and MANIFEST SHA-256 provenance. A proxy result is never presented as an engine result.
- **Source:** [`audit/12`](../audit/12_dataset_implementation.md)

### D23 — Software only for now

- **Decision (user directive, 23 Sep 2026):** build everything in software:
  - the plant simulator synthesises the high-rate signals
  - a FADEC emulator speaks J1939/UDS/XCP over vcan
  - a link emulator shapes the datalink
  - the edge node is a capped process
- **Kept as roadmap:** hardware sections of [`audit/09`](../audit/09_full_depth_architecture.md) §2.3–§3 and [`audit/10`](../audit/10_red_team_readiness_review.md) §2.5 (sensor kits, EHU, indigenous processors).

### D24 — Indigenous and supply chain

- No Chinese-origin software, models or components.
- Permissive licences; an SBOM with origins.
- On-prem and air-gapped deployment; no foreign cloud or API.
- Roadmap: deterministic core portable to Indian RISC-V (C-DAC VEGA / SHAKTI), with an FPGA front end.
- **Source:** [`audit/10`](../audit/10_red_team_readiness_review.md) §2.6

### D25 — 3D visualisation

- **Decision:** Blender/WebGL shows **estimated** per-cylinder state (IMEP/SOC deviation, hypothesis location), not decoration. **No further investment** beyond wiring it to estimator outputs.
- **Source:** [`audit/09`](../audit/09_full_depth_architecture.md) §11

### D26 — How to work

- **Decision:** no more broad brainstorming. Build **vertical slices** in [`BACKLOG.md`](BACKLOG.md) order. A slice is done only when it runs sensor → edge → link → twin → diagnosis → advisory **in the live service**, is measured by a Monte Carlo campaign with CIs, and is validated on at least one real dataset.
- **Source:** [`audit/08`](../audit/08_deployable_system_blueprint.md) §6.1 · [`audit/10`](../audit/10_red_team_readiness_review.md) §4

### D27 — Engine-universal by profile

- **Decision:** the product is one codebase in which selecting an engine (dropdown -> `POST /api/engine/select`) rebuilds the twin, limits, channel list, fault list, RUL components, ML models, 3D assets and UI schema from an **`EngineProfile`** (= `configs/engines/<id>.json` + `assets/manifests/engines/<id>.json` + model registry entry). Inference, twin, service and UI code may **not** name an engine, a cylinder index or a redline.
- **Why:** measured 24 Sep — the live system is a Rotax 912 iS simulator with configs beside it: 286 fixed-cylinder-index literals, 78 brand mentions and 37 model numbers in 19 modules that should be agnostic; no engine-selection path exists in API or UI; the fault list is named after one engine's CAD meshes. A DRDO reviewer would (rightly) read that as a single-engine simulation, and the PS itself asks for a "scalable and modular" framework (SYS-02/03, DTC-05).
- **Scope honesty:** universal across **piston** engines (SI/CI, NA/turbo, 2-8 cyl, boxer/inline/V) is the achievable target. Rotary and turbine classes plug in later behind an `EnginePhysics` interface; do not claim them now. Universal architecture is not universal accuracy: each profile needs its own calibration and evidence; the honest test is leave-one-engine-out (E16).
- **Enforcement:** `tests/test_engine_agnostic_ratchet.py` fails if any engine-specific literal count rises; baselines only go down.
- **Sources:** [`UNIVERSALITY_AUDIT.md`](UNIVERSALITY_AUDIT.md) (evidence, design, hook points), backlog tier E12.

### D28 — Artifact provenance sidecars

- **Decision:** every trained model and generated dataset ships a sidecar recording the generating script and git commit, engine profile(s), source data and hash, date, and evaluation (with its split rule). No sidecar => untrusted.
- **Why:** the current RF/autoencoder are dated 2 Sep (before ACES, the 914/915/VRDE configs, the independent plant and FMECA), were trained on the circular 912 iS generator, and the dataset manifest contains another machine's absolute paths.
- **Sources:** [`UNIVERSALITY_AUDIT.md`](UNIVERSALITY_AUDIT.md) sec. 7, [`VERIFICATION_CHECKLIST.md`](VERIFICATION_CHECKLIST.md) sec. D.

### D29 - Multi-engine concurrent runtime

- **Decision:** a `RuntimeHub` holds one `EngineRuntime` per engine profile (simulator + fault/lever registry + detector bank + ring buffer + edge node). **All run continuously.** The dropdown selects which engine's stream the UI/Blender subscribes to; a fleet stream shows every engine at once. Same seed + same script => bit-identical streams.
- **Why:** measured 24 Sep - the plant steps in 0.12-0.15 ms for every engine, so five engines at 20 Hz cost ~1.2 % of one core; concurrency is not the constraint, state isolation is. It also makes switching instantaneous and makes a fleet view possible (a differentiator).
- **Replaces:** the `EngineStateService` singleton and the engine-less `/ws/telemetry` (F24).
- **Source:** [`MULTI_ENGINE_ARCHITECTURE.md`](MULTI_ENGINE_ARCHITECTURE.md) sec. 1-3, 6.

### D30 - Fault injection and levers

- **Decision:** four layers - L1 operating levers (throttle, altitude, OAT, dust, regime) into plant *inputs*; L2 physical faults (mode x location x severity x ramp, registered per profile via `applicable_fault_modes()`); L3 sensor faults (bias, drift, stuck, noise, dropout, spoof) at the sensor model; L4 direct reading override **only** in a detector test-bench mode. Every injection is recorded in the `TruthRecord` with `origin in {SCENARIO, MANUAL_LEVER, TESTBENCH_OVERRIDE}`; runs with manual/test-bench origins are excluded from accuracy and false-alarm KPIs. Injectors register themselves (`register_fault(mode, applies_to, apply, clear)`).
- **Why:** a lever that edits a reading directly makes physically inconsistent frames and silently pollutes evidence; a lever that acts through the physics gives realistic transients and shows lead time live. Today's live levers are cosmetic (F23 / gap G02).
- **Source:** [`MULTI_ENGINE_ARCHITECTURE.md`](MULTI_ENGINE_ARCHITECTURE.md) sec. 4.

### D31 - Detector strategy

- **Decision:** (1) per-tail calibration on a nominal window -> z-scored residuals (engine-specific *data*, universal *method*); (2) universal detector on the residuals: Mahalanobis + max|z| with conformal thresholds; (3) fault isolation by a universal RF/GBM (with engine-class flags) by default and a per-engine model where labelled data exists; (4) a physics/waveform channel for faults scalars cannot see. RF is only called on flagged frames, batched or compiled.
- **Why (E17, simulation, 5 engines, unseen builds):** Mahalanobis AUROC 0.976 per-engine, 0.974 universal, 0.973 on a never-seen engine; RF macro-F1 0.904 per-engine vs 0.852 universal vs 0.840 on a new engine calibrated with nominal data only; normalisation is worth +4.6 points across engines; sklearn single-row RF costs 11.5 ms (trap).
- **Caveat:** simulation only; the plant is not engine-class-aware (F21); no confidence intervals yet.
- **Source:** [`DETECTOR_DECISION.md`](DETECTOR_DECISION.md).

### D32 - Fly-inspired methods (SUPERSEDED by D36, 24 Sep 2026)

> Reason: the first version dismissed the connectome using an M4-Pro-class hardware assumption and an all-engines-at-once assumption. Both were wrong (ground infra is A100-class; heavy inference is selected-engine only). E19 then tested connectome reservoirs directly.

- **Decision:** the connectome simulators (Shiu LIF model, flymsg, fly-brain forks) are not used. The fly-inspired **algorithm** (FlyHash + Fly-Bloom-Filter memory) is a candidate for the Raspberry Pi tier-0 gate on **waveform/spectral features only**, and takes that slot only if it beats Mahalanobis / Isolation Forest / a 1-D CNN on cost or detection at equal false-alarm rate (backlog W5). On 13 tabular features it scored AUROC 0.84 vs 0.976 (untuned). Implementation: our own (published algorithm), `fbfc` (MIT), or `ffbf` only if the author adds a licence.
- **Supersedes/refines:** D12. Never claim novelty of the algorithm (D12 stands).
- **Source:** [`DETECTOR_DECISION.md`](DETECTOR_DECISION.md) sec. 5.

### D33 - Jev / OpenJev (AMENDED by D37, 24 Sep 2026)

- **Decision:** not in any detection path. Allowed: on-prem advisory ranking of maintenance actions at the ground station, logged, never auto-actioned; preferably distilled into a transparent policy. Refines D13.
- **Why:** typed-decision language models need text input, cost tens of ms per decision on a GPU, are weeks old and unaudited; incompatible with 20 Hz x N engines and with the explainable evidence path (D02).

### D34 - Waveform and edge pipeline

- **Decision:** `WaveformSource` (plant crank/rail signal now; synthesised 51.2 kHz after E2; dataset replay of CWRU/Paderborn/3500-DEFault; recorded `.npz` + manifest) -> `EdgeNode` emulating a Raspberry Pi 5 (4 cores, memory cap, slowdown factor) -> tier-0 cheap gate -> persistence (M-of-N with hysteresis) -> tier-1 feature engineering **only on persistence** -> `HealthFrame` v2 scalars over the link emulator -> ground scalar detectors. Real Pi 5 benchmark is roadmap, not a claim.
- **Why:** injector, needle, rail and turbo-bearing faults leave zero trace on any scalar channel (F22), so a waveform channel is mandatory; sending only persistent-anomaly scalars keeps the downlink within budget (D16).
- **Source:** [`MULTI_ENGINE_ARCHITECTURE.md`](MULTI_ENGINE_ARCHITECTURE.md) sec. 7.

### D35 - Third-party licence gate

- **Decision:** a dependency or reference implementation may enter a deliverable only if its licence is present and permissive; no licence = all rights reserved = excluded. Record origin and licence in the SBOM (D24).
- **Why:** `clembarr/ffbf-novelty-detector` (attractive: Rust + Python, 4 us per score on 384-d by the author's claim) has **no licence** (GitHub API, 24 Sep); `rithram/fbfc` is MIT.

### D36 - Fly innovation tier

- **Decision:** (tier-0, all engines, Pi 5) FlyHash / Fly Bloom Filter novelty gate; (tier-1, selected engine) sparse reservoir + ridge readout initialised from the fly connectome (`mk-jev-fly-brain/mk/fly_circuit.js`, top-1000-degree subgraph); (tier-2, ground GPU, selected engine) larger reservoir / TabPFN (research use) / TimesFM-Chronos. RF stays as the reference baseline. Fly tiers ship because they are edge-cheap, explainable and at least as good as RF, **not** because the wiring is proven superior.
- **Evidence:** E19 (`docs/evaluation/E19_connectome_reservoir.json`, SIMULATION): macro-F1 rotax_914 0.951 vs RF 0.906; vrde 0.998 vs RF 0.949; shuffled connectome and random ESN tie the real one (0.941 / 0.955; 0.999 / 0.999). The reservoir pattern helps; the biology adds no measurable accuracy.
- **Claim discipline:** never say "fly wiring is better". Say: "we tested it against its own shuffled brain; the pattern wins, the wiring ties." Differentiator vs cloud competitors: edge-first, federated Bloom-filter merge, no cloud.
- **Source:** [`FLY_100_WAYS.md`](FLY_100_WAYS.md), [`DETECTOR_DECISION.md`](DETECTOR_DECISION.md) addendum.

### D37 - Jev / open-Jev on the ground GPU

- **Decision:** corrected premises: (a) only the selected engine gets heavy inference, (b) DRDO-class GPUs exist. Under these, an open Jev-style model (Open-Jev-27B, DiffusionGemma openjev, Verdict-open-jev ModernBERT-151M, ~35 ms per its author) is admissible as a **tier-2 ground contender**: HealthFrame v2 serialised as text -> class / severity / action. It also serves as the maintenance-action ranker. Never on the 20 Hz path; never auto-actions.
- **Gate:** stays only if it beats the reservoir tier and RF on macro-F1, or adds explanation value, at equal false-alarm rate (backlog W10); licence check per D35; offline provider only (`ANUMAAN_LLM_PROVIDER`).
- **Ways it can work:** fine-tune ModernBERT-151M on serialised windows; few-shot 27B with FMECA in context; distil into a transparent rule set; explain tier-1 alarms; retrieval-augmented case matcher (F66).
