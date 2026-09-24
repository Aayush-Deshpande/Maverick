# Handoff Prompt — paste this to the next LLM

*Written 24 Sep 2026 at the end of a long build session. Everything below is verified against the repository at commit `166cb3a` plus the uncommitted work-in-progress listed in §4. When this file and the code disagree, trust the code and fix this file.*

---

## PROMPT (copy from here)

You are taking over an in-flight engineering project: **ANUMAAN** — an AI-enabled real-time digital twin for health monitoring, fault prediction and mission-reliability of aero piston engines on MALE UAVs (Smart India Hackathon 2026, problem statement **PS-26054**, DRDO). Repo: `E:\backup-llm\backup-no-llm\3d_engine` (Windows 11, Git Bash + PowerShell, Python 3.12, NVIDIA GPU with CUDA torch, branch `maverick-main`). The owner wants a technically serious, DRDO-integrable system — not a demo. They value: proactive autonomous work (act, decide, research beyond the repo; do not ask them to teach you or to choose), honesty about what is real vs simulated, and many concrete implementation paths for novel ideas instead of objections. **Frontend work is out of scope for now** (spec exists: `docs/build/FRONTEND_SPEC.md`).

### Step 0 — read, in this order (about 45 minutes; do not skip)
1. `docs/build/README.md` (index) → `MENTAL_MODEL.md` → `DECISIONS.md` (D01–D37; D32 and D33 are superseded/amended by D36/D37) → `INTERFACES.md` → `VERIFICATION_CHECKLIST.md` → `CURRENT_STATE.md` → `SUPERSEDED_VS_CURRENT.md` (S01–S08: which old code NOT to build on) → `FINDINGS.md` (F01–F35: verified facts and mistakes) → `BACKLOG.md` (the ordered work breakdown; rows carry ✅/🟡 status notes) → `DEV_EXECUTION_PLAN.md` (how the build is run) → `AGENT_BRIEF.md` (rules for parallel build agents; **you obey them too**).
2. Then, as needed: `DETECTOR_DECISION.md`, `FLY_100_WAYS.md` (fly/connectome ideas + the E19 result), `MULTI_ENGINE_ARCHITECTURE.md`, `UNIVERSALITY_AUDIT.md`, `DEAD_CODE_AUDIT.md`, `IDEAS_AND_GAPS_SWEEP.md`, `FRONTEND_SPEC.md`, `docs/audit/08–12`, `docs/IMPLEMENTATION_LOG.md` (session history), `docs/evaluation/*.json` (E17, E19, E20 results, reachability audit).

### What the system is (one screen)
- **One pipeline, one contract.** A canonical `Frame` (`backend/core/frame.py`: per-cylinder `cht/egt` lists + scalars; **no field for fault id, health index or RUL**) flows source → pipeline → detectors. Ground truth lives only in `TruthRecord` (evaluation-only; `origin` SCRIPTED/MANUAL; `kpi_eligible`). `tests/test_no_truth_leak.py` AST-scans inference packages so a detector cannot read truth. Live = replay at 1× (D05).
- **Plant ≠ twin (D04).** `backend/plant/virtual_engine.py` is the independent simulated engine (build variation, sensor lag/noise/bias, faults injected only here). It is now class-aware (rpm schedule, EGT class table SI/CI [ASSUMED], oil pressure, fuel flow from the profile). `backend/sources/plant_source.py` wraps it to `(Frame, TruthRecord)`; `recorder.py` records/replays with a sha256 manifest.
- **Engine-agnostic by profile.** `configs/engines/{rotax_912is,rotax_914,rotax_915is,austro_ae300,vrde_jayem_2_2l}.json` with per-field `provenance` (PUBLIC/MANUAL/ASSUMED/PLACEHOLDER — never quote ASSUMED/PLACEHOLDER as fact). `tests/test_engine_agnostic_ratchet.py` only lets brand/cylinder literals go **down** (baseline 267/74/36).
- **Detection stack (`backend/detect/`)**: `TailCalibration` (nominal-only operating-point regression → z-residuals → 13 n_cyl-agnostic features; **calibration is per tail — a different tail's nominal frames trip alarms >20 %, F32**), scorers (`FlyBloomScorer` [own FlyHash + frequency memory, `merge` = federated colony merge], `Mahalanobis`, `MaxAbsZ`), `ResidualDetector` (split-conformal thresholds, `PersistenceGate`, top-channel evidence), `Reservoir` (frozen sparse ESN + ridge readout; connectome init optional). Decision D36: fly tiers ship as the innovation tier because they are edge-cheap and ≥ RF, **not** because fly wiring is better — E19 showed the real connectome ties its shuffled and random-ESN controls while any reservoir beats windowed RF by ~4–5 macro-F1 points. Never claim biological superiority.
- **Runtime (`backend/runtime/`)**: `EngineRuntime` (own plant, levers with first-order dynamics, detector, ring buffer), `RuntimeHub` (all engines tick concurrently; only the **selected** engine gets the heavy tier — D29), fault registry per profile (`registry.py`; injector/rail/turbo-bearing faults are **waveform-only**, invisible to scalars, F22). API: `backend/server/engine_api.py` (`/api/engines`, `/api/engines/{id}/{state,faults,levers}`, `/ws/engines/{id}`, `/ws/fleet`). The legacy `EngineStateService` singleton and `/ws/telemetry` still exist and still feed the old UI — retire only after the frontend moves.
- **Edge**: `backend/edge/node.py` persistence-gated scalar downlink with bytes/latency accounting; Pi 5 profile is **EMULATED** (label it until a real board benchmark exists).
- **Evidence so far (all SIMULATION):** E17 (detector bake-off; Mahalanobis AUROC ≈ 0.97, FlyHash ≈ 0.83–0.85, RF macro-F1 ≈ 0.90 per engine), E19 (connectome reservoir vs controls), E20 (end-to-end through the product path: every scalar-visible fault detected in every run on 5 engines × 3 tails, 0 confirmed false alarms in 300 nominal ticks; median delays: misfire 8–10 s, cooling degradation 47–71 s, oil-pressure loss 7–10 s). Real-flight anchor: NASA ACES (units unconfirmed; do not quote °C). Never present simulator accuracy as field performance.
- **Tests:** 275 pass + 1 strict xfail (`exposure.py` counts one continuous brownout as N events) at `9a5c001`. Run `python -m pytest -q` (~2.5 min). Characterization tests (`tests/test_char_*.py`) pin the previously untested research modules; they revealed doc drift (F33: rainflow 4.0 not 5.0 cycles; FMECA isolability is 100 %, not 55→95 %).

### Step 1 — verify your understanding before coding
Run: `git status`, `git log --oneline | head`, `python -m pytest -q`, `python scripts/tools/audit_reachability.py`, then re-run `python experiments/E20_runtime_end_to_end.py` and confirm it reproduces `docs/evaluation/E20_runtime_end_to_end.json` within noise. State in one paragraph what you believe is real/live/wired vs orphaned, and compare with `CURRENT_STATE.md`. If they differ, investigate and correct the docs.

### Step 2 — pick up the interrupted parallel build (see §3–§4 of this file)
Seven track agents were launched in isolated git worktrees and **stopped mid-work when the session ended**: WAVEFORM, TWIN, DIAG, EDGELINK, FLEET, DATA, FOUNDATION. Their worktrees are empty (verified), so re-launch them from the specs in §3 (the full original prompts are in this session's transcript; the summary table plus `AGENT_BRIEF.md` and the BACKLOG rows are sufficient to rebuild them). Then wave 2 (§5).

### Rules that override convenience
Truth isolation; engine-agnostic (no literals); provenance labels on every constant; evidence class on every number; **no claim without a null control and multiple seeds**; train/test seeds disjoint (test offset ≥ 1000); no fabricated numbers, sources or licences (write `UNVERIFIED`); third-party code needs a present permissive licence (D35: `clembarr/ffbf` has none — excluded; `rithram/fbfc` MIT; TabPFN ≥ 2.5 and Moirai are non-commercial → research-only labels); library code in `backend/`, never in experiment scripts; every module tested and deterministic; no LLM in any detection path (the LLM provider defaults to `none`); never call sklearn one row at a time on the live path (11.5 ms/row trap); edit shared docs only as integrator; commit in logical chunks with the trailer `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`; before any destructive git/file operation run `git status` and stash/commit first.

## END OF PROMPT

---

## 3. The seven stopped tracks (specs)

Each was created with `isolation: worktree` → worktree under `.claude/worktrees/agent-<id>` on branch `track/<name>`, told to read `AGENT_BRIEF.md`, to write `docs/build/tracks/<TRACK>.md`, to add experiments `E21+`, and to end with a structured report. **Verified after the stop: all seven worktrees have zero changed files and no new commits — the tracks produced nothing, so re-launch them from scratch** (`track/foundation` points at an old ancestor commit `a63c0f6`, not new work; recreate branches from current `maverick-main`).

| Track | Branch | Rows | Owns (new packages) | Experiment |
|---|---|---|---|---|
| WAVEFORM | `track/waveform` | B2.1–B2.5, W3-waveform | `backend/physics/{rail,…}`, `backend/plant/{acoustics,sensors_hr}.py`, `backend/core/cycle_block.py`, `backend/sources/waveform.py` | prove injector/rail/turbo-bearing faults visible in waveforms while the 13 scalars stay nominal |
| TWIN | `track/twin` | B4.1, B4.2, B4.4, B4.5, B4.6 (B4.3 deferred) | `backend/twin/{thermofluid,ukf,…}` (NumPy + PyTorch agree) | E21 twin estimation |
| DIAG | `track/diag` | B5.1-partial, B5.2–B5.6, B6.1–B6.3 | `backend/{diagnosis,prognosis,alarms}/`, mission additions | E22 |
| EDGELINK | `track/edgelink` | B2.6, B2.7, B8.1, B9.1, W9 | `backend/{fadec,link,security}/`, edge process, `configs/mavlink/` | E23 |
| FLEET | `track/fleet` | B10.1, B10.2, V7-backend, R9, R10, R11 | `backend/{performance,maintenance,fleet}/`, `mission/profiles.py` | E24 |
| DATA | `track/data` | B7.1–B7.7 (+U9-data, W7-ACES) | `backend/{datasets,federated}/` (data at `E:\…\3d_engine\Datasets`, read-only) | E03–E11 |
| FOUNDATION | `track/foundation` | W10, W8 | `backend/foundation/` (Jev-style text classifier, Chronos/TimesFM, TabPFN research-only) | E25 |

## 4. Uncommitted work-in-progress on `maverick-main` (integrator lane, "CORE")

Interrupted mid-way; verify then finish or discard:
- `backend/physics/engine_config.py`: added `operating_limits` + `unlabelled_limits()`; the five `configs/engines/*.json` now carry `operating_limits` with provenance (SI: 135/850/0.8/130 ASSUMED from legacy literals — **not re-verified against the manuals**; CI: PLACEHOLDER). Provenance tests passed.
- New, **untested**: `backend/core/pipeline.py` (B1.3 stage executor with OSA-CBM layer ordering + timing), `backend/core/channels.py` (U2 channel registry from profile), `backend/core/limits.py` (U3 redline check).
- **Not written (the write was interrupted):** `backend/core/profile.py` (U1: `EngineProfile` joining config + asset manifest [alias `austro_ae300` → `austro_ae330`] + channels + faults + provenance summary; `load_profile`, `load_all_profiles`).
- Planned next in this lane: refactor `EngineRuntime.tick` onto `Pipeline` with a `replay/ingest(frame)` path and a bit-exact live-vs-replay test; `/api/engines/{id}/schema`; sensor-fault levers R7 (bias/drift/stuck/dropout as Frame-level wrappers, origin MANUAL); runtime isolation/load test R8; B1.4 harness on the pipeline; B1.7 Monte Carlo campaign runner; W2 classifier registry + U8 model registry with provenance sidecars; W7 E17 with CIs; B0.5–B0.8 (archive stale `UpdatedReport/`, hygiene, CI workflow, `experiments/run_all.py`).

## 5. Remaining after the tracks merge (wave 2)

DSP (B3.1–B3.10: crank tooth capture + wheel-error learning, inverse crank dynamics → IMEP, COT resampling/TSA/peer referencing, order spectrum + OFSC/kurtogram envelope, virtual cylinder pressure, rail-wave analysis, electrical, efficiency, transients, CycleHealthVector v1) — needs WAVEFORM's `CycleBlock`; B4.3 per-cylinder combustion estimator; remaining B5.1 detectors; W5/W6 waveform bake-off + injector-fault demonstration (E18); B1.5/B1.6 (plant default, crank chain live); wiring every merged library into `EngineRuntime`/API and retiring legacy paths (`can_streamer`, `spectral_analyser`, `rul_estimator`, `thermo_model`, `plant/adapter`, the Rotax-only RF) **after** the frontend moves; U5/U6-UI, B11.x and V1–V10 are frontend.

## 6. Environment and pitfalls (learned the hard way)
- The Bash tool breaks on heredocs containing apostrophes/unbalanced quotes → write such files with the file-write tool, or put the script in a file and run it.
- The Bash tool can fail with "auto mode classifier unavailable" — retry; read-only tools still work.
- Zenodo throttles parallel downloads (403); use `Datasets/download_all.py --only marine,road --connections 1`. Datasets are gitignored (metadata only); `Datasets/CAN_ECU/syncan` and `Anomaly_Benchmarks/skab` are nested clones (ignored).
- Git LFS: 39 pointer stubs in the repo (not real files); `assets/models/*.blend` are LFS. `vendor/Qwen3-4B` (7.6 GB) and duplicate NASA tarballs are deletable but need the owner's yes. Stale dead code is in `archive_tracked/` (tracked) and `archive/` (ignored, local).
- `tests/test_engine_agnostic_ratchet.py --update` may only lower the baseline.
- New inference packages must be added to the AST scan list in `tests/test_no_truth_leak.py` and to the ratchet's guarded modules.
- Blender is at `E:\Blender\blender.exe`; the asset for the Austro AE330 is real, the TB3/PD170 pipelines were archived.

## 7. First 30 minutes checklist for you
1. Read §Step 0 docs. 2. `git status` + `git worktree list`; for each `track/*` worktree run `git -C <path> status --short | head` and `git log --oneline -3`. 3. Run the test suite. 4. Decide per track: resume (SendMessage to the old agent id if your harness supports it, or re-launch with the same spec) or re-do. 5. Finish §4 (create `profile.py`, test `pipeline/channels/limits`), commit. 6. Merge finished track branches one at a time into `maverick-main`, run the full suite after each, then update `BACKLOG.md`, `CURRENT_STATE.md`, `FINDINGS.md`, `DECISIONS.md`, `IMPLEMENTATION_LOG.md` from the `docs/build/tracks/*.md` notes.
