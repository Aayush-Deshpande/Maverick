# Build Backlog

*Before ANY change run [`VERIFICATION_CHECKLIST.md`](VERIFICATION_CHECKLIST.md). New here? Read [`MENTAL_MODEL.md`](MENTAL_MODEL.md) and [`SUPERSEDED_VS_CURRENT.md`](SUPERSEDED_VS_CURRENT.md) first — several items below reference a specific "old/new pair" (Sxx) from that second file, and wiring the wrong half produces nothing.*

The complete, ordered work breakdown. **An agent should take the first unblocked item, build it, meet its acceptance criteria, log it in [`../IMPLEMENTATION_LOG.md`](../IMPLEMENTATION_LOG.md), update [`CURRENT_STATE.md`](CURRENT_STATE.md), and move on.**

- **ID** `Bx.y`. **Deps** are backlog IDs that must be done first.
- **PS** refs are requirement IDs from [`../fun_req.md`](../fun_req.md): SYS, INT, CAP, DTC, HMS, FDP, AIM, SIM, VIS, DEL, OPT, INN, TEX.
- **Design** points to the document section that specifies the behaviour. Contracts are in [`INTERFACES.md`](INTERFACES.md); decisions in [`DECISIONS.md`](DECISIONS.md).
- **Done** means: code + tests + acceptance met + log entry with *Verified* and *Unproven* sections + no regression in `pytest`.

**Critical path for a demonstrable system:** E0 → E1 → (E2 ∥ E7.1–7.2) → E3 → E4 → E5 → E6 → E11. E8–E10 can run in parallel once E1 is done.

---

## E0 — Truth and hygiene (do first; small)

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| B0.1 | ✅ **DONE** (2026-09-24). Removed the ground-truth leak. FlyHash now calibrates on a frame-count startup window, not `actual.FAULT_ID`. Guard test added. | `backend/ml/detection_pipeline.py:391`, `backend/ml/flyhash_novelty.py`, `tests/test_no_truth_leak.py` | — | Test fails on the pre-fix code, passes post-fix; 131/131 (was 129) | FDP-01 | 08 §5.D |
| B0.2 | ✅ **DONE** (2026-09-24). LLM is now a pluggable provider: `none` (default, disabled) / `sarvam` / `bharatgen` / `qwen` (opt-in only) / `local-other`. All user/reviewer-facing "Qwen3-4B" text updated. | `backend/agent/llm_engine.py`, `backend/agent/copilot.py`, `backend/server/main.py`, `requirements.txt`, `frontend/src/components/{DiagnosticCard,VoiceCopilot}.tsx`, `tests/test_llm_provider_default.py` | — | App runs with `provider=none`; copilot uses its deterministic fallback; no Chinese-origin model referenced by default; 134/134 (was 131) | SYS-05 | D14, 10 §2.6 |
| B0.3 | ✅ **DONE** (2026-09-24). Fixed the binding: `find_channel()` now requires a start-of-string match (the name-matrix bleed-through was the real bug — see IMPLEMENTATION_LOG). Added EGT_3/EGT_4/CHT aliases. **The numeric scale (C vs F) remains genuinely unconfirmed** — do not report EGT/CHT in °C until the real ACES PDF is obtained; tracked as a B7.5 follow-on. | `backend/telemetry/aces_loader.py`, `tests/test_aces_channel_binding.py` | — | EGT_1 median far above the old ~170 mis-binding value; 5/5 new tests; 152/152 total (was 147) | CAP-11, DEL-06 | IMPL_LOG S1/S4/S5 |
| B0.4 | ✅ **DONE** (2026-09-24). Added per-field `provenance` to `EngineConfig` (INTERFACES §8). All 5 configs fully labelled; `vrde_jayem_2_2l.json` relabelled (mostly ASSUMED/PLACEHOLDER, "specification" wording removed, unsourced Archer-NG platform claim dropped); `rotax_915is.json` added for the Heron Mk II. | `configs/engines/*.json`, `backend/physics/engine_config.py`, `tests/test_engine_config_provenance.py` | — | All configs load; 13/13 new tests pass; 147/147 total (was 134) | SYS-02/03, INT-03 | D01 |
| B0.9 | **Characterization tests for the research modules -- before wiring any of them.** Verified 24 Sep: NONE of `evaluation/{conformal,damage_accumulation,prognostic_metrics,validation,threshold_baseline,harness}`, `mission/*`, `reliability/*`, `edge/compressor`, `twin/{validity,integrity,residual_detector}`, `plant/virtual_engine`, `physics/{crank_dynamics,turbo_model,injector_faults,oil_system,fuel_thermal,induction,exposure}`, `telemetry/mavlink_efi`, `osacbm` has pytest coverage; their "Verified" entries in IMPLEMENTATION_LOG were ad-hoc runs. Pin each documented headline result as a regression test (e.g. ASTM rainflow series counts 5.0 cycles; conformal coverage 0.902 +/- SE on the seeded synthetic set; healthy 4-cyl order-2 dominance; misfire rate recovered 6.0/14.0/40.7 %; Wilson interval endpoints; isolability 55 % -> 95 %). | `tests/test_*.py` (one per module family) | -- | Every headline number in IMPLEMENTATION_LOG Sessions 1-4 is reproduced by a test that fails if the module regresses | DEL-01 | 08 s6.6, D21 |
| B0.10 | **Reachability audit as a progress meter.** Keep `scripts/tools/audit_reachability.py` running in CI; record LIVE/HARNESS/TEST/ORPHAN line counts per milestone (orphan lines should fall toward zero as E1/E4/E5/E6 land). Act on `DEAD_CODE_AUDIT.md` in the safe-to-archive order. | `scripts/tools/`, `docs/evaluation/reachability_audit.json`, `archive/` | B0.6 | Counts committed per milestone; safe-tier deletions done | DEL-01 | `DEAD_CODE_AUDIT.md` |
| B0.5 | **Archive stale reports.** Move `UpdatedReport/00–30` to `archive/UpdatedReport/`, keep 31 with its §2.2 corrected (VRDE engine is publicly reported), and update the links. **Also (FINDINGS F20):** fix or remove every reference to the non-existent `analysis/` folder (root `README.md`, `docs/README.md`, `docs/00_*`, `docs/01_*`, `docs/fun_req.md`, `docs/audit/06/07/09`). | `UpdatedReport/`, `archive/` | — | No link in `docs/` points to archived files except via the archive note | DEL-07 | 08 §6.7 |
| B0.6 | **Repository hygiene** per [`../audit/06_repo_cleanup_plan.md`](../audit/06_repo_cleanup_plan.md): gitignore `report_dump/mission_*`, `data/telemetry/live_sorties/*.csv`, `scratch/`, root videos; move stray files to an attic. | `.gitignore` | — | `git status` is clean after a demo run | — | 08 §5.K |
| B0.7 | **CI.** GitHub Actions on Windows and Ubuntu: `pytest`, ruff, and a small evaluation smoke run. | `.github/workflows/ci.yml` | — | Green on both | DEL-01 | 08 §6.2 |
| B0.8 | **Evidence skeleton.** `experiments/run_all.py` runs registered experiments and writes `docs/evaluation/<id>.json` + `.md` (INTERFACES §12). Port the existing harness report into it. | `experiments/`, `docs/evaluation/` | B0.7 | `python experiments/run_all.py` regenerates `detection_report.*` byte-identically except for timestamps | DEL-06 | D21 |

## E1 — One pipeline (the structural fix)

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| B1.1 | ✅ **DONE** (2026-09-24). `Frame` + `TruthRecord` (+ `frame_from_plant`/`truth_from_plant`); forbidden-field rejection; truth-leak scan extended to `backend/sources/`. The temporary `EnginePhysicalState` adapter is **not** built — the live service does not consume `Frame` until B1.3/B1.4. | `backend/core/frame.py`, `tests/test_frame_and_plant_source.py` | B0.1 | 9 new tests; 161/161 total | DTC-06 | INTERFACES §1–2 |
| B1.2 | 🟡 **PARTIAL** (2026-09-24). `PlantSource` done (current independent plant → `(Frame, TruthRecord)`; S01 WIRE side). **Still to do:** `ReplaySource` (Parquet/CSV/ACES/.tlog), `MavlinkSource` (wrap `mavlink_efi.py`), `CanSource` (python-can + cantools), and retiring `TelemetryStreamer` → `LegacySource`. | `backend/sources/plant_source.py` (done); rest new | B1.1 | Each source yields valid Frames; ACES replays at 1× and at max speed | OPT-01, DTC-06, SIM-03 | D05 |
| B1.3 | **OSA-CBM stage executor**: stages register layer + cadence (per-frame, per-cycle, periodic); the executor runs a DAG at the declared rates. Existing stages are wrapped. | `backend/osacbm.py`, new `backend/core/pipeline.py` | B1.1 | The layering-violation check (exists) passes on the executed graph; stage timings logged | DTC-05, SYS-03 | D06 |
| B1.4 | **Service and harness share the pipeline.** `engine_service.py` hosts `Pipeline`; `evaluation/harness.py` drives the same object. | `backend/server/engine_service.py`, `backend/evaluation/harness.py` | B1.2, B1.3 | **Bit-exact replay test**: the same recorded run gives identical diagnostics through service and harness | DEL-01 | 08 §3.1 |
| B1.5 | **Plant as default; full fault library.** VirtualEngine covers all FMECA modes in scope (not only faults 1–4), with the taxonomy as *mode × location* (no cylinder-hardcoded classes). Delete the `ANUMAAN_USE_INDEPENDENT_PLANT` flag. | `backend/plant/`, `backend/reliability/fmeca.py`, `tests/` | B1.4 | Every FMECA mode is injectable at any valid location; nominal Frames carry no truth | FDP-02…09 | 08 §5.D |
| B1.6 | **Crank chain live** at per-cycle cadence (`crank_signal()` → `CrankDiagnostics`) → CycleHealthVector v0 (per-cylinder work, order spectrum) | `backend/plant/virtual_engine.py`, `backend/ml/crank_diagnostics.py` | B1.3, B1.5 | Live service shows per-cylinder ratios; the misfire and injector-coking scenarios are detected through the live path | FDP-02/03/07 | D07 |
| B1.7 | **Monte Carlo campaign runner**: seeds × scenarios × environments × onset/severity/rate; parallel; outputs ROC, detection probability, lead-time distribution, false alarms per flight hour with 95 % upper bound | new `backend/evaluation/campaign.py`, `experiments/E00_sim_campaign.py` | B1.4, B1.5, B0.8 | ≥ 30 runs per mode and ≥ 300 nominal hours in the report; runtime < 2 h on a laptop | CAP-03/04, DEL-06 | 08 §6.5–6.6 |

## E2 — Waveform-grade simulation and emulators (software stand-ins for hardware)

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| B2.1 | **CI combustion model**: ignition-delay correlation, double-Wiebe heat release, pilot/main/post injection; config-driven SI/CI switch | `backend/physics/crank_dynamics.py` (+ new `combustion_ci.py`) | B0.4 | CI p(θ) peak 120–180 bar class at full load (🔶 assumed range, labelled); ignition delay responds to charge temperature; misfire/partial-injection faults act on injection parameters | TEX-01, HMS-11 | 09 §5.2 |
| B2.2 | **Rail hydraulics + injector integration** (pump, pressure-control valve, rail volume, per-injection draw → pressure waves) | `backend/physics/injector_faults.py`, new `rail.py` | B2.1 | The rail-pressure trace shows a per-injection drop proportional to quantity; injector faults change that injector's drop/recovery | FDP-03 | 09 §4.4 |
| B2.3 | **Acoustics and structure**: Draper chamber modes excited by dp/dθ; modal transfer (≥ 3 modes per path per cylinder); impact sources (needle open/close, valve seating, piston slap) at their kinematic angles | new `backend/physics/structure.py` | B2.1 | The spectrum of synthesised 51.2 kHz acceleration contains the Draper-band content, which moves with gas temperature; impacts land in the correct angle windows | HMS-09, FDP-09 | 09 §2.2, §12 |
| B2.4 | **Other sources**: bearing defects with slip, gear mesh with tooth faults, turbo rotor (imbalance, whirl), torsional chain with damper, alternator ripple | `structure.py`, `turbo_model.py` | B2.3 | Each fault produces its textbook signature (defect orders in the envelope; sidebands; 0.4–0.5× whirl; missing ripple pulses) | FDP-09, HMS-10 | 09 §12, 10 §2.1 |
| B2.5 | **Sensor chain**: IEPE response, mounted resonance, anti-alias filter, 24-bit quantisation, trigger-wheel tooth errors, timer quantisation, bias and failure modes → `CycleBlock` | new `backend/plant/sensors_hr.py` | B2.3 | Tooth-error-free vs tooth-error signals differ exactly by the injected error; quantisation measured | FDP-06 | 09 §2.3 |
| B2.6 | **FADEC emulator**: cylinder-balancing and drift-adaptation loops (masking faults from EGT); J1939 broadcast per **our DBC**; UDS (0x19 DTCs, 0x31 routines: cut-out, rail step, SOI sweep); XCP variable read | new `backend/fadec_emulator/`, `configs/can/anumaan_fadec.dbc` | B2.1, B1.2 | On `vcan0` (or python-can virtual bus on Windows): cantools decodes all signals; an injected injector fault raises its trim while EGT stays within noise (**masking reproduced**); UDS cut-out routine executes | OPT-01/02, TEX-05 | 11 §4, D09 |
| B2.7 | **Link emulator + MAVLink 2** (bandwidth 1–20 kbit/s, latency, loss, jamming windows) with signing; `ANUMAAN_HEALTH` dialect | new `backend/link/`, `configs/mavlink/anumaan.xml` | B1.2 | Health frames arrive within budget; forged/replayed frames rejected; link loss → store-and-forward drain in priority order | INN-07, OPT-03 | 11 §3.3, §3.6 |

## E3 — Signal intelligence core (per-cycle DSP)

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| B3.1 | Tooth-period capture + **wheel-error learning** | new `backend/dsp/crank.py` | B2.5 | Learned tooth errors within 10 % of the injected ones; residual speed noise reduced | FDP-02 | 09 §4.1 |
| B3.2 | **Inverse crank dynamics + per-cylinder pressure deconvolution** (regularised LS) → IMEP, compression index | `backend/dsp/crank.py` | B3.1, B2.1 | IMEP per cylinder within 5 % of plant truth; compression loss on one cylinder isolated | FDP-03/07 | 09 §4.1 |
| B3.3 | COT resampling; TSA per cycle; TSA residual; **angle-window features**; **peer referencing** | new `backend/dsp/angle.py` | B2.3 | Features land in the correct windows; peer ratios ≈ 1 when healthy | FDP-09 | 09 §4.2 |
| B3.4 | Order spectrum; **OFSC / cyclic modulation spectrum**; fast kurtogram → envelope order spectrum; **gear CIs FM0/FM4/NA4/NB4**; also run on CWRU/Paderborn (E08) | `backend/dsp/spectral.py` (replaces the 20 Hz `spectral_analyser.py` path) | B3.3 | Defect orders recovered on CWRU; gear CIs rise with an injected tooth fault | FDP-09 | 09 §4.2 |
| B3.5 | **Virtual cylinder pressure** (crank low-pass + vibration inverse-FRF high-pass) → SOC, CA10/50/90, pmax, dp/dθ, ignition delay | new `backend/dsp/virtual_pressure.py` | B3.2, B3.4 | In simulation: SOC within ±1° CA, CA50 within ±2°; ignition delay tracks injected changes | HMS-11, FDP-03 | 09 §4.3 |
| B3.6 | Rail-wave analysis per injection; **FADEC trim/adaptation monitor** (level + rate) | new `backend/dsp/injection.py` | B2.2, B2.6 | Injector coking detected via trim growth while EGT is still within noise | FDP-03, HMS-11 | 09 §4.4 |
| B3.7 | **Electrical**: alternator ripple order analysis; battery equivalent-circuit EKF; start-impedance test; restart-readiness index | new `backend/dsp/electrical.py` | B2.4 | Open-diode fault detected; battery R_int trend recovered; validated on NASA battery (E10) | HMS-10 | 10 §2.1 |
| B3.8 | **Load path and efficiency**: shaft-twist torque → brake power → BSFC, FMEP = IMEP − BMEP; prop orders | new `backend/dsp/efficiency.py` | B3.2, B2.4 | FMEP rises with an injected friction increase; BSFC trend per regime | VIS-07 | 10 §2.2 |
| B3.9 | **Transient identification** on throttle steps (turbo τ, overshoot, thermal τ, rail recovery) | new `backend/dsp/transients.py` | B1.6 | Identified turbo τ tracks an injected bearing-drag fault | SIM-08 | 10 §2.3 |
| B3.10 | **CycleHealthVector v1** assembly + bit-exact test vectors (reference NumPy implementation) | new `backend/dsp/chv.py`, `tests/vectors/` | B3.1–B3.9 | Schema per INTERFACES §4; vectors frozen; ≈ 33 CHV/s at 4,000 rpm within the edge budget | DTC-02 | 09 §4.7 |

## E4 — The twin: estimator hierarchy

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| B4.1 | **Differentiable thermofluid model** (PyTorch; NumPy reference), config-driven, dynamic (RC network per cylinder, oil, coolant, turbo) replacing the algebraic expectation | new `backend/twin/model.py` | B0.4, B1.3 | Matches `VirtualEngine` nominal trajectories within stated error; gradients verified by finite differences | INT-02, INN-01/04 | 11 §3.1 |
| B4.2 | **UKF joint state + parameter estimation**; per-tail calibration; the validity monitor on innovations (reuse `twin/validity.py`) | new `backend/twin/ukf.py` | B4.1 | Estimated `eta_cool[i]` tracks an injected cooling degradation within its 95 % interval; NIS within bounds when healthy | CAP-11, DTC-02/04 | 09 §5.3 |
| B4.3 | **Per-cylinder combustion estimator** (k_inj, dSOI, c_comp) from the CHV | new `backend/twin/combustion_est.py` | B3.10, B2.1 | Recovers injected per-cylinder parameter changes within CI | FDP-03, HMS-11 | 09 §5.2 |
| B4.4 | **Degradation particle filter** over the physics-of-failure models; **SINDy** identification of degradation laws | new `backend/twin/degradation.py` | B4.2, B4.3 | SINDy recovers the plant's injected law (terms correct, coefficients within 10 %) | CAP-05/13, INN-01 | 09 §5.1, 11 §3.1 |
| B4.5 | **Hierarchical fleet priors** (per-tail from the fleet distribution) | `backend/twin/priors.py` | B4.2 | A new tail's θ̂ converges faster with priors than without (measured) | SYS-09 | 09 §5.5 |
| B4.6 | Grey-box learned residual terms (bounded, trained only on confirmed-nominal data, frozen) | `backend/twin/model.py` | B4.1, B7.5 (ACES) | Innovation whiteness on ACES improves over physics-only | INN-04 | 09 §5.4 |

## E5 — Detection and diagnosis

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| B5.1 | Four detectors: GLR/CUSUM on θ̂; peer detector; **FlyHash + regime-conditioned, time-decaying Fly Bloom Filter** on spectrum + CHV + embedding; recogniser (winner of E06) | `backend/detect/` (move `flyhash_novelty.py` here, extended) | B3.10, B4.2, B7.2 | Each emits `Evidence` (INTERFACES §7); unit tests on synthetic cases | AIM-04, FDP-01 | 09 §6.1, §6.3 |
| B5.2 | **Conformal thresholds** to a false-alarm-per-hour target (reuse `evaluation/conformal.py`) | `backend/detect/thresholds.py` | B5.1, B1.7 | Realised false-alarm rate on held-out nominal hours ≤ target (95 % bound) | FDP-01 | 09 §6.2 |
| B5.3 | **Diagnostic Bayesian network** generated from `fmeca.json` + `isolability.json`; ambiguity groups | new `backend/diagnose/bn.py` | B5.1 | Blind-injected faults → correct mode or correct ambiguity group ≥ 0.9 in the Monte Carlo campaign | FDP-02…09, AIM-02 | 09 §6.4 |
| B5.4 | **Active diagnosis**: expected-information-gain test selection using the twin as hypothesis simulator; issues UDS routine requests to the FADEC emulator (approval required) | `backend/diagnose/active.py` | B5.3, B2.6 | For the ambiguous pairs in `isolability.json` (e.g. misfire ≡ needle stick), the selected test resolves them in simulation | FDP-03 | 09 §6.5 |
| B5.5 | **Explanations by audience** + explanation metrics (faithfulness, stability, **explanation-to-cylinder agreement**) | `backend/diagnose/explain.py` | B5.3 | The metrics are computed in the campaign report | INN-06, VIS-02…04 | 11 §3.5 |
| B5.6 | Sensor-vs-engine and integrity gate live (reuse `twin/integrity.py`, residual shielding) | `backend/detect/integrity.py` | B5.1 | The sensor-drift scenario is classified SENSOR_FAULT; a spoofed MAP value is rejected | FDP-06, INN-07 | 07 Part IX |

## E6 — Prognostics and decision

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| B6.1 | **Dual-path RUL** + conformal intervals (ACI) + disagreement alarm; retire `ml/rul_estimator.py` | `backend/prognose/` | B4.4 | α-λ pass at α = 0.2 in simulation and on C-MAPSS (E03); coverage within ±2 % | CAP-06, AIM-05 | 09 §7.1 |
| B6.2 | **Mission reliability** from θ̂ and damage, with an electrical-power term; risk-based Go/No-Go; prescriptive derate; in-flight contingency | `backend/mission/` | B6.1, B3.7 | Decision ladder reproduced with estimated (not placeholder) inputs; limiting component named | SIM-02, AIM-07 | 09 §7.2 |
| B6.3 | **ISA-18.2 alarm management**: rationalisation table, priorities, shelving, flood suppression | new `backend/alarms/` | B5.3 | Alarm rate per hour on nominal campaigns ≤ target; every alarm has cause/consequence/action | VIS-06 | 07 Part III.5 |

## E7 — Datasets, experiments and the learning system

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| B7.1 | `backend/datasets/` base, records, provenance; **3500-DEFault conversion to Parquet** (mat-io, conversion only) | per 12 §3.2–3.3, `scripts/convert_3500_default.py` | B0.8 | Loaders return typed records with group keys and SHA-256 | DEL-06 | 12 §3 |
| B7.2 | **E06: fly-vs-RF bake-off** on 3500-DEFault (+ dense-projection null, noise levels, open-set, few-shot, per-cylinder localisation) | `experiments/E06_*.py` | B7.1 | Result JSON with CIs; decision recorded in DECISIONS D12 (adopt / ensemble / negative result) | INN-02/06, FDP-03 | 12 §4 |
| B7.3 | **E03 / E04 / E05 on C-MAPSS**: RUL + PHM metrics; **federated** (FD001–4 as operators; poisoning + defences + canary gate); SINDy | `experiments/E03–E05` | B7.1, B6.1 (E03), B7.7 (E04) | Result JSONs; attack success with and without defences reported | AIM-05, INN-05, INN-01 | 11 §3.4 |
| B7.4 | **E08 on CWRU / Paderborn**: DSP chain, artificial → real transfer, latency under edge caps | `experiments/E08_*` | B3.4, B8.1 | Defect-order detection rate; transfer accuracy; p99 latency | FDP-09, INN-02/03 | 12 §4 |
| B7.5 | **E01/E02 ACES** (sim-to-real + **false alarms per hour on real flight**), **E11 ALFA**, **E10 battery**, **E12 ROAD/SynCAN**, **E07 marine diesel** | `experiments/` | B0.3, B1.2, B3.7, B9.1 | Each result JSON, evidence class REAL_FLIGHT or PUBLIC_PROXY | DEL-06, INN-07, HMS-10 | 12 §4 |
| B7.6 | **Self-supervised engine-cycle encoder** (masked angle-frequency patches; cylinder-equivariance; temporal consistency); distillation → INT8 edge student; **shadow mode** | `backend/learn/` | B3.10 | Embedding improves novelty AUROC over raw features (measured); student within stated loss of the teacher | AIM-01, INN-02 | 09 §8.2 |
| B7.7 | **Federation service** (Flower): hierarchical silos, five shared objects, robust aggregation + personalisation, **canary gate**, secure aggregation, DP option, async rounds, federated conformal | `backend/federation/` | B7.1 | E04 and E14 run end to end; the gate rejects a failure-masking update | INN-05, SYS-09 | D15 |

## E8 — Edge runtime

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| B8.1 | `edge_node` process under OS caps (container: 1 CPU, 512 MB); mixed-criticality scheduler; cascade tiers 0–2; ONNX INT8 inference; value-of-information telemetry; store-and-forward; ARM64 build + tests | new `edge/` package + `docker/edge.Dockerfile` | B1.3, B3.10, B2.7 | Tier 0–1 deadline misses = 0 per flight hour under load; graceful shedding demonstrated; ARM64 test pass; bytes per hour within link budget | OPT-03, INN-02/03, TEX-04 | 11 §3.3 |

## E9 — Security

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| B9.1 | Pluggable crypto module (AES-256-GCM default; PQC hybrid ML-KEM/ML-DSA option); key management; **hash-chained, Merkle-sealed flight logs**; mTLS + RBAC + audit; **CAN IDS** (timing/ID/payload) combined with physics integrity; SBOM generation | new `backend/security/`, CI step for SBOM | B2.7, B5.6 | Tampered log detected; forged/replayed frames rejected; CAN IDS results on ROAD/SynCAN (E12) with point-wise and point-adjusted F1 | INN-07 | 11 §3.6 |

## E10 — Maintenance and fleet

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| B10.1 | Task library from FMECA; work packages; **CP-SAT scheduler** (OR-Tools); spares forecast from RUL distributions; outcome capture → BN counts; no-fault-found KPI; tail-to-mission assignment | `backend/maintenance/` (extend `reports/`, `graph/`) | B5.3, B6.1 | Work packages carry expected finding + confirm test + evidence | AIM-03/07, INN-08 | 11 §3.7 |
| B10.2 | **Fleet discrete-event simulation**: 12 tails × 3 bases × 1 year; policies: fixed-interval / reactive / ANUMAAN | `experiments/E15_fleet_des.py` | B10.1, B1.7 | Availability, aborts, unscheduled removals, NFF and spares cost compared with CIs | SYS-09, INN-08 | 11 §3.7 |

## E11 — HMI, evidence and documents

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| B11.1 | Role-based HMI: operator (rationalised alarms, mission reliability), **engineer (per-cylinder combustion view, p-θ reconstructions, trends, OFSC maps)**, maintainer (work packages), fleet; uncertainty and ambiguity groups shown; **Evidence page** linking capabilities → experiments | `frontend/src/` | B5.3, B6.2, B0.8 | Each VIS requirement demonstrably served; Evidence page reads the result JSONs | VIS-01…09, OPT-07 | 09 §11 |
| B11.2 | Blender/WebGL shows **estimated** per-cylinder state (colour by IMEP/SOC deviation; hypothesis location) | `apps/blender_twin/`, `backend/server/` | B4.3 | Clicking a hypothesis highlights its component | VIS-05 | D25 |
| B11.3 | Document set: SRS (traced to fun_req IDs, generated), architecture description (from registry), ICDs, safety & certification position, data management plan, deployment roadmap (Kit 0 → test cell → flight), user manuals | `docs/` | most | Every PS requirement ID traces to a component and an experiment | DEL-02/07 | 08 §6.7 |

---

### E11 additions from the docs sweep (see [`IDEAS_AND_GAPS_SWEEP.md`](IDEAS_AND_GAPS_SWEEP.md))

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| V1 | Per-cylinder **residual** heat map on the 3D engine (colour by z-residual, not absolute temperature) | `apps/blender_twin/`, `frontend/` | B4.3 / W1 | A cylinder glows only when it deviates from its calibrated expectation | VIS-05 | audit/04 F19 |
| V2 | Firing-order animation with the misfiring cylinder visibly skipping | `apps/blender_twin/` | B3.2 | Injected misfire shows on the correct cylinder within 1 s | VIS-05, FDP-02 | F20 |
| V3 | Live order-spectrum waterfall (fault appears while scalar RMS stays flat) | `frontend/` | B3.4 | Waterfall shows the 0.5-order line growing under misfire | VIS-03 | F21 |
| V4 | Sensor-trust overlay on the engine | `frontend/`, `apps/` | B5.6 | A stuck sensor is marked on its mesh | FDP-06 | F22 |
| V5 | Degradation ghost (predicted end-of-mission state overlaid) | `apps/` | B6.1 | Ghost differs when RUL differs | VIS-08 | F23 |
| V6 | Bandwidth meter (raw vs link capacity vs actual) | `frontend/` | B8.1 | Shows measured bytes/s per engine | OPT-03 | F24 |
| V7 | Impact/economics model with parametrised ranges and a sensitivity chart | `backend/economics/` | B10.2 | Output is a range with the assumptions listed, never a single figure | DEL-07 | audit/10 s2.9 |
| V8 | Portable ground diagnostic kit mode (cut-out test, cranking compression, battery test, vibration signature) | `backend/`, `frontend/` | B5.4, B3.7 | 15-minute scripted procedure yields a work package | SYS-08 | audit/10 s2.10 |
| V9 | What-if mission sandbox per engine (loiter hours, altitude, OAT, payload, fuel) -> thermal margins and mission reliability | `frontend/`, `backend/mission/` | B6.2, R3 | Sliders update reliability with an interval | SIM-02/06 | competitor breakdown |
| V10 | Interactive component inspector (click mesh -> sensor, value, health, spec, action) using the asset manifests | `apps/`, `frontend/` | U1, R5 | Works for every profile that has a manifest | VIS-05 | competitor breakdown |

## E12 — Engine universality (decision D27; evidence in [`UNIVERSALITY_AUDIT.md`](UNIVERSALITY_AUDIT.md))

Runs alongside E1-E6; U2 and U3 are best done *as part of* B1.x/B4.x/B5.x rather than after. The ratchet test (`tests/test_engine_agnostic_ratchet.py`, baseline 286 cylinder-index / 78 brand / 37 model literals) is the progress meter: each item should lower it.

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| U1 | `EngineProfile` loader unifying `configs/engines/<id>.json` + `assets/manifests/engines/<id>.json`; reconcile IDs (`austro_ae330` vs `austro_ae300`; add a `tei_pd170` physics config) and manifest schemas (faults dict vs list) | new `backend/physics/engine_profile.py`, `assets/manifests/`, `configs/engines/` | B0.4 | Every selectable engine has both halves; loader test over all profiles | SYS-02/03 | AUDIT s3-4 |
| U2 | Channel registry derived from `n_cyl` / `is_CI` / `has_turbo`; retire fixed `CHT_1..4` fields (start at `Frame` and adapters) | `backend/core/`, adapters | B1.1 | A 6-cylinder profile round-trips through `Frame` and a detector | DTC-05 | AUDIT s4 |
| U3 | `operating_limits` in the config schema **with provenance**; remove redline literals from `detection_pipeline.py` and the sensor validator | configs, `ml/detection_pipeline.py`, `physics/sensor_validator.py` | U1 | Ratchet drops; limits differ per profile in a test | HMS-01..11 | AUDIT s2 |
| U4 | Engine API: `GET /api/engines`, `GET /api/engines/{id}/schema`, `POST /api/engine/select`; pipeline rebuild on select | `backend/server/` | U1, B1.4 | Selecting `vrde_jayem_2_2l` changes channels, limits and fault list live | SYS-02/03 | AUDIT s4 |
| U5 | UI renders channels/cylinders/limits from the schema; engine dropdown in the header | `frontend/src/` | U4 | No `CHT_n`/`EGT_n` literals left in components | VIS-01..05 | AUDIT s4 |
| U6 | Fault list = FMECA mode x location filtered by the profile; component/mesh mapping from the manifest (replaces `DRDO_FAULT_DEFINITIONS`) | `backend/reliability/`, `backend/telemetry/` | U1, B5.3 | Overheat injectable at any cylinder of any profile | FDP-02..09 | S02 |
| U7 | RUL component graph from the profile (replaces the six hardcoded components) | `backend/prognose/` | U1, B6.1 | A diesel profile has no ignition-harness component | AIM-05 | S03 |
| U8 | Model registry with provenance sidecars (D28); retrain on multi-profile plant Monte Carlo; rename `Rotax*` classes | `backend/ml/`, `scripts/` | B1.7 | Every model has a sidecar; nothing older than the plant | AIM-01/04 | AUDIT s7 |
| U9 | E16 leave-one-engine-out experiment; add a 6-cylinder diesel proxy profile from 3500-DEFault | `experiments/E16_*.py` | U8, B7.1 | Generalisation gap reported with CIs | INN-02/04 | AUDIT s6 |
| U10 | Ratchet to zero: lower `tests/engine_agnostic_baseline.json` as modules are refactored (`--update` refuses to raise) | `tests/` | continuous | Baseline strictly decreasing | -- | D27 |

## E13 - Multi-engine runtime (decisions D29, D30; design in [`MULTI_ENGINE_ARCHITECTURE.md`](MULTI_ENGINE_ARCHITECTURE.md))

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| R1 | `EngineRuntime` (PlantSource + injector registry + detector bank + ring buffer + tick) and `RuntimeHub` running every profile concurrently; deterministic seeds; no module-level engine state | new `backend/runtime/` | B1.1, U1 | 5 engines x 20 Hz for 1 h < 10 % of one core; a fault on engine A never alters engine B | SYS-02/03, DTC-05 | ARCH s1-3 |
| R2 | Fault/lever registry (`register_fault(mode, applies_to, apply, clear)`), L1-L3 layers, `TruthRecord.origin`, KPI exclusion of manual origins; API `POST /api/engines/{id}/faults`, `/levers` | `backend/runtime/`, `backend/core/frame.py`, `backend/evaluation/` | R1 | Only profile-valid faults are offered; a run with a manual lever is excluded from KPIs (test) | FDP-02..09, SIM-04 | D30 |
| R3 | **Close gap G02:** operating levers drive plant inputs with first-order dynamics; retire the cosmetic `SET_THROTTLE/ALTITUDE/OAT` overwrite | `backend/server/engine_service.py` -> runtime | R1 | Throttle 40 -> 100 % gives an rpm time constant and tens-of-seconds CHT/EGT rise; altitude lowers MAP/power; OAT raises CHT/oil temp - each asserted by a test | SIM-01/04/05/07/08 | gap_plan G02 |
| R4 | Engine API + `WS /ws/engines/{id}` + `WS /ws/fleet` + header dropdown; old routes alias the default engine | `backend/server/`, `frontend/src/` | R1, U4 | Dropdown switches the visible stream within one frame period, no reload; fleet view shows all engines | SYS-02/03, VIS-01..05 | ARCH s6 |
| R5 | Asset variant map per profile (Rotax 912i base + 914/915 fitting sets in one blend; AE330 blend as labelled AE300 proxy); Blender client subscribes per engine; resolve LFS stubs | `assets/manifests/`, `apps/blender_twin/` | U1 | Switching engine toggles the right object sets and re-binds fault->component meshes | VIS-05 | ARCH s8 |
| R6 | **Plant class-awareness (F21):** rpm map from `idle..rated`, thermal/EGT targets and limits from config, CI-appropriate EGT, mass-flow-limited cooling (F45); **characterization tests first (B0.9)** | `backend/plant/virtual_engine.py`, configs | B0.9 | Diesel EGT/rpm inside their configured envelopes; no engine exceeds rated rpm; harness numbers unchanged for the 914 or explicitly re-baselined | TEX-01/02 | FINDINGS F21 |
| R7 | Sensor-layer levers: bias, drift, stuck, noise, dropout, spoof-consistent and spoof-inconsistent | `backend/plant/`, runtime | R2 | Sensor-vs-engine discrimination scenario passes; truth logged with origin | FDP-06, INN-07 | D30 |
| R8 | Runtime load and isolation test | `tests/`, `experiments/` | R1..R4 | Acceptance criteria 1, 2, 5 of ARCH s9 | DEL-01 | ARCH s9 |
| R9 | **Performance maps** per profile (power, BSFC, boost vs rpm/throttle/altitude) with provenance, refined per tail | `configs/`, `backend/physics/` | B0.4, R6 | Map surface shown to engineers; PS INT-03 traceable | INT-03 | gap G07 |
| R10 | **Multi-phase mission profile library** (taxi/climb/cruise/loiter/descent; ISR 18 h @ 28 kft, Ladakh, Thar, coastal) with phase-conditioned baselines | `backend/mission/` | R1 | Every scenario is multi-phase; detectors use the phase | SIM-02/06 | gap G12 |
| R11 | Operational-history store (exposure, past faults, maintenance) feeding priors and RUL | `backend/twin/` | B4.5 | New tail vs old tail differ in prior; verified in a test | INT-08 | gap G21 |

## E14 - Detector bank and waveform/edge pipeline (decisions D31-D34; design in [`DETECTOR_DECISION.md`](DETECTOR_DECISION.md) and ARCH s5, s7)

| ID | Task | Files | Deps | Acceptance | PS | Design |
|---|---|---|---|---|---|---|
| W1 | **Calibrated-residual detector** in `backend/detect/`: per-tail calibration -> 13 n_cyl-agnostic z-features -> Mahalanobis + max\|z\|, conformal thresholds; calibration sidecar per tail (D28). Promote from `experiments/E17` | new `backend/detect/` | B0.9, B1.1 | Reproduces E17 AUROC (0.97+) on the plant; runs for every engine; works for n_cyl != 4 | AIM-04, FDP-01 | DETECTOR s6 |
| W2 | **Classifier registry**: universal RF/GBM + engine-class flags default, per-engine override, gated + batched or compiled (ONNX/tree arrays), sidecars; retire the Rotax-only RF | `backend/detect/`, `backend/ml/` | W1, U8 | New engine gets diagnosis from nominal calibration only; no per-row sklearn call on the hot path | FDP-02..09 | DETECTOR s3, s6 |
| W3 | `WaveformSource` + `WaveformRecorder` (`.npz` + manifest with truth/origin, rate, seed, commit, SHA-256): plant crank/rail signal now; dataset replay (CWRU, Paderborn) | `backend/sources/` | B1.1 | A recorded run replays bit-exactly | SIM-03 | ARCH s7 |
| W4 | **EdgeNode emulation** with a Pi-5 profile (4 cores, memory cap, slowdown factor): tier-0 gate -> persistence -> tier-1 features -> `HealthFrame` v2 -> link emulator | new `edge/`, `backend/link/` | W3, B2.7 | Deadline held under the CPU cap; only persistent anomalies emit frames; bytes/h within budget | OPT-03, INN-02/03 | ARCH s7, D34 |
| W5 | **Waveform bake-off (E18):** FlyHash-FBF (own + `fbfc`) vs Mahalanobis vs Isolation Forest vs 1-D CNN on order-spectrum/waveform features (CWRU, Paderborn, plant crank, later 51.2 kHz plant, 3500-DEFault once decoded); split by bearing/run; CIs | `experiments/E18_*.py` | W3, B3.4 | Result JSON with CIs; decision recorded in D32 (adopt / keep Mahalanobis / negative result published) | INN-02/06 | DETECTOR s6 |
| W6 | **Injector-fault demonstration:** waveform channel detects coking/needle-stick while every scalar detector stays quiet | `experiments/`, `backend/dsp/` | B1.6, W1 | Documented run; scalar detectors below threshold, waveform alarm with the right cylinder | FDP-03, HMS-11 | DETECTOR s4 |
| W7 | E17 repeat with confidence intervals (>= 5 seed sets) after R6; add ACES healthy hours (false-alarm rate) and per-fault recall | `experiments/E17_*.py` | R6, B0.3 | Numbers quotable externally | DEL-06 | DETECTOR s7 |
| W8 | Zero-shot time-series foundation-model control added to W5 (F61) | `experiments/` | W5 | Reported beside the other contenders | INN-01/04 | F61 |
| W9 | Test-rig / HIL mode: a source reading a dyno/test-cell log; crank/cam signal emulator driving the real edge code (F49); real Raspberry Pi 5 benchmark on the roadmap | `backend/sources/`, `scripts/` | W4 | Same pipeline runs on a recorded test-cell log | SYS-08 | F49 |
| W10 | Jev/open-Jev tier-2 bake-off: HealthFrame-as-text classifier (ModernBERT-151M fine-tune, 27B few-shot) vs reservoir vs RF on selected engine; also maintenance ranker (D37) | E13 | ground GPU | macro-F1 at equal false-alarm rate + explanation review |
| W11 | E19 follow-up: leave-one-engine-out, all 5 engines, more seeds, lead-time metric, sub-circuit choice by conn2res memory capacity, int8 / Pi 5 latency (D36) | E13 | E19 | reservoir beats RF LOEO by more than seed spread, else documented null |
| W12 | Federated Bloom-filter merge across tails (D36, FLY_100_WAYS 32-33) | E13 | FBF | merged filter detection equals pooled-data filter |

## The minimum demonstrable slice (if time is short)

B0.1–B0.4, B0.9 → B1.1–B1.6 (+ U1–U4, R1–R4 so the demo shows an engine dropdown with every engine running live) → B2.1, B2.6 (FADEC masking) → B3.1, B3.2, B3.6, B3.10 (crank + trims) → B4.2, B4.3 → B5.1, B5.3, B5.4 (cut-out test) → B6.2 → B7.1–B7.2 (E06) + B7.5 (ACES false-alarm rate) → B11.1 (engineer and operator views).

**Demo script:** a judge secretly picks a fault and a cylinder. The plant masks it via FADEC balancing. The screen shows the trim growth and per-cylinder deviation, the hypothesis ranking with its ambiguity group, and the twin requesting a cut-out test. The test resolves the fault, RUL and mission reliability update, and a work package appears. The evidence page links to E06 and to the ACES false-alarm result.
