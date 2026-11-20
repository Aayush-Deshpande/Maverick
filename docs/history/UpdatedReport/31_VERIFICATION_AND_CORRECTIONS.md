# REPORT 31: VERIFICATION AGAINST THE ACTUAL REPOSITORY — CORRECTIONS TO REPORTS 00–30

**Classification:** Evidence-based correction layer. Every claim below was checked by reading the actual file on disk or running a command against the actual repository on **2026-09-23**, not by re-describing the earlier reports.

**Why this file exists:** Reports 00–30 mix genuinely correct, verifiable claims with file paths, dependencies, and competitor repositories that **do not exist in this codebase**, and in several cases appear nowhere in an independent, extensive multi-round search. Some of this is precisely right (§1). Some of it is wrong in a way that would be caught immediately if presented to a technical panel (§2). This file exists so nobody quotes the wrong half.

**⚠️ Update, 2026-09-23 (same day, later pass):** substantial real work has landed since this file's first version, on top of what §4 already documented as underway. This section records it precisely so the gap between "what Reports 00–30 describe" and "what the repository actually does" is tracked as it widens, not left to compound silently.

### 0. What changed after this file's first version

**Fixed — the live 3D fault highlighting.** The detection-pipeline honesty fix described in §3 below (genuine ML diagnosis, no commanded-label echo) had a side effect nobody had checked: it also silently broke mesh highlighting. `target_parts` — what the Blender client actually highlights — was tied unconditionally to the genuine, independently-*detected* fault, not the operator-*commanded* one, so clicking a fault in the UI panned the camera correctly (camera framing already prioritised commanded-first) but highlighted nothing until the classifier independently re-confirmed the same fault, which can lag several seconds or never cross its confidence gate at low severity. Fixed in `backend/server/engine_service.py` by giving `target_parts` the same commanded-first priority the camera logic already had, without touching the genuine `diagnosed_fault_id`/confidence fields. Verified against the real 109-object scene via headless Blender (`E:\Blender\blender.exe --background`) — one stale mesh name was found in the process (`Cooling_Air_Baffle_M_PlasticCable_0`, present in two duplicated fault-target lists, no such object in the current `.blend`) and removed from both. `apps/blender_twin/verify_app.py`'s own fault-target check only required `>0` targets found per fault, not *all* of them — exactly the gap that let a partially-stale list through silently; strengthened to require every declared target to exist. Regression test added at the real API level (`tests/test_server_api.py::test_commanded_fault_highlights_immediately`).

**Fixed — three more stale-path bugs**, same class as §2.1 below: `verify_app.py` itself still pointed at `3d_models/rotax_912_is_sport.blend` (pre-restructure path) and wrote its output render to a stray top-level `renders/` instead of `assets/renders/`; `launch_standalone_app.bat` pointed at the same pre-restructure blend path; five `scripts/harvest_*.py` files hardcoded an absolute path to a `...\3d_engine\ANUMAAN\Models_Images` directory that has not existed since the ANUMAAN→root restructure. All four re-derive their path relative to the repository root or `__file__` now, so they survive the next restructure instead of needing to be individually re-found.

**Fixed — root `README.md` was the worst offender in the entire repository.** It documented `3d_models/`, `Models/`, `unity_bridge/` (a Unity C# integration package — confirmed via headless Blender/filesystem check: **does not exist anywhere in this repo**), `scripts/blender/`, `scripts/rendering/`, `scripts/utils/` (≈50 named files across all of these, none present), and linked to `docs/01_problem_statement_and_analysis.md` through `docs/05_master_build_guide.md`, which live under `analysis/strategy/` now, not `docs/`. This is the file anyone opening the repository reads first. Rewritten to match the actual current tree.

**Built — the G01 plant-circularity fix is now genuinely wired, not just present.** `backend/plant/virtual_engine.py` (`VirtualEngine`) existed as a correct, independent plant model, exactly as this file originally described, but `backend/server/engine_service.py` still imported the old circular `TelemetryStreamer` — the fix existed and was never connected. `backend/plant/adapter.py` now bridges them: for nominal flight and DRDO faults 1–4 (the four `VirtualEngine` actually models — mapped by reading each fault's real delta block in `can_streamer.py`, not guessed), the live service sources core thermal/pressure/RPM channels from the independent plant instead of the twin's own equations; faults 5–8 and every other channel (vibration, injection timing, efficiency context) are untouched. Opt-in via `ANUMAAN_USE_INDEPENDENT_PLANT=1`, **off by default** — the published 0.9751 classifier accuracy was measured against the old, circular distribution and has not been re-validated against the new one. 12 new isolated tests (`tests/test_independent_plant_adapter.py`) confirm nominal residuals are now genuinely structured rather than near-zero noise, all four mapped faults move the correct channel directionally, and all four unmapped faults pass through byte-for-byte unchanged.

**Found and fixed along the way — a real Windows file-locking bug.** Wiring the plant in surfaced (via more frequent anomaly-triggered autosaves — structured residuals trip the anomaly path sooner than the old near-zero ones did) a pre-existing `PermissionError`/`WinError 32` in `backend/graph/mission_graph.py::save()`: `os.replace()` under concurrent multi-process file access is atomic on Windows but not lock-free, unlike POSIX. Fixed with a short bounded retry.

**Built — FlyHash sparse-coding novelty detection**, applying a published technique (Dasgupta, Stevens & Navlakh, *Science* 2017; Ryali et al., ICML 2020) to order-domain vibration + physics-residual features under this project's edge constraints — explicitly **not** claimed as a novel algorithm; see `docs/study/20_novelty_and_research.md`'s own correction of an earlier over-claim in this exact family, and `backend/ml/flyhash_novelty.py`'s module docstring for the full attribution. Complementary to, not a duplicate of, the existing `NoveltyGate` (F17) in `backend/evaluation/validation.py`: that distrusts a confident-but-wrong classifier posterior; this distrusts a feature pattern the system has never seen before, upstream of and independent from any classifier. Wired as an additive Stage 2c in the live 20 Hz pipeline (residuals-only for now — order-domain features await `crank_diagnostics.py` itself being wired into the live pipeline, which it is not yet either; see §4). 11 new tests confirm correct sparsity, near-duplicate inputs cluster while unrelated ones don't, outliers are flagged only after calibration, and per-frame latency stays under 5 ms.

**Repository hygiene**: `__pycache__`/`.pyc` cleared (already gitignored, none were committed), three stray editor backup files (`apps/blender_twin/standalone_canyon_flight_app.py.backup_pre_*`, `.checkpoint_golden` — verified against git history that the live tracked file supersedes them) moved to an attic outside the repository rather than deleted, and `*.backup_pre_*`/`*.checkpoint_*` added to `.gitignore` so the pattern doesn't recur.

**Test count: 97 → 129, all passing, zero regressions**, verified by full-suite runs before and after each change in this pass.

---

## 1. What Reports 00–30 got exactly right (verified independently)

| Claim | Where | Verification |
|---|---|---|
| Rotax CAD model is **78.5 MB** | Report 00 §1.1 | `assets/blender/rotax_912_is_sport.blend` = **78,522,778 bytes** exactly. Precisely correct. |
| RF validation accuracy **97.5%** | Report 00 §7 | `backend/ml/models/model_metrics.json`: held-out test accuracy **0.9751**. Correct. |
| Sensor-vs-engine discrimination via rate-of-change (`dT/dt ≤ 1.5 °C/s` physical vs `>10 °C/s` artifact) | Report 00 §12, Report 11 §3 (VIKASHL25/twinguard comparison) | `backend/physics/sensor_validator.py` `RATE_LIMITS`: CHT physical 1.5 °C/s, fault flag >10 °C/s. Correct, and the same principle several competitors independently converged on. |
| Autoencoder is a small NumPy MLP, not a heavy framework | Report 00 §7 | `backend/ml/anomaly_detector.py::ResidualAutoencoder` — pure Python/NumPy 14→8→4→8→14. Correct in substance. |
| `atharv20s/sih-26` (PRAHARI) has a real PINN with a Fourier/Newton thermal loss and a PPO DRL agent | Report 11 Competitor 3 | Independently confirmed by direct source reading (`src/pinn/pinn_model.py`, `src/drl/drl_agent.py`) — the loss formula and learnable α/β conductivity parameters are real. |
| `VIKASHL25/SIH-26` has a real `.dbc` CAN file and a Simulink/UDP bridge | Report 11 Competitor 6 | Independently confirmed: `can_layer/engine_can.dbc` and `simulink/udp_can_bridge.py` are real files in that repo. |
| The 8 fault modes and the general residual→autoencoder→RF→trend pipeline shape | Report 00 §2, §4 | Matches the actual 9-stage `DetectionPipeline` in substance (naming differs — see §2). |

**Conclusion of this section:** whoever or whatever produced Reports 00–30 had *some* genuine access to this repository and to real competitor code. The problem is not that it is worthless — it is that it cannot be trusted uniformly, which is worse, because the correct parts lend false credibility to the incorrect parts.

---

## 2. What does not exist — verified by direct inspection

### 2.1 File paths that are not in this repository

| Report claims | Reality (checked 2026-09-23) |
|---|---|
| `backend/services/state.py` | **Does not exist.** `backend/services/` is not a directory in this repo at all. |
| `backend/services/detection_pipeline.py` | The real file is **`backend/ml/detection_pipeline.py`**. |
| `backend/services/voice/` | The real path is **`backend/voice/`** (top-level package, not under `services/`). |
| `backend/ml/autoencoder.py` | The real file is **`backend/ml/anomaly_detector.py`**. |
| `backend/ml/classifier.py` | The real file is **`backend/ml/fault_classifier.py`**. |
| `backend/ml/generator.py` | The real file is **`backend/telemetry/can_streamer.py`** (also `backend/telemetry/rotax_dataset_generator.py`). |
| File links to `file:///d:/Programming/PS054/...` (Report 14, throughout) | **This machine's repository is at `E:\backup-llm\backup-no-llm\3d_engine`.** `d:/Programming/PS054/` does not correspond to this project on this machine. Either this was written against a different clone, on a different machine, or the paths were never checked against a real filesystem. |
| `web/site/js/main.js::simulateEngineTelemetry()` (claimed as fake/disconnected) | Not independently re-verified in this pass — flagged for someone to check before repeating the claim, since the surrounding paths in the same report were wrong. |

🔶 **Why this matters practically:** if a judge asks "show me `backend/services/state.py`" during a technical review, it will not be found, in front of the panel. That is a worse outcome than not making the claim at all.

### 2.2 Dependencies and interfaces claimed but not present

| Report claims | Verification |
|---|---|
| Real CAN FD ingestion via `cantools` + `python-can`, UDP multicast, `engine_can.dbc` (Reports 00 §2, 11 §4, 14 ACT-07) | `requirements.txt` contains **no `cantools` or `python-can` dependency**. `find . -iname "*.dbc"` in this repo (excluding cloned competitors) returns **nothing**. `backend/telemetry/can_streamer.py` — despite its name — contains **no CAN frames, no arbitration IDs, no DBC parsing**. This is aspirational, matching item **F47** in the real, current plan ([`docs/audit/07_unoccupied_axes_and_ground_up_plan.md`](../docs/audit/07_unoccupied_axes_and_ground_up_plan.md) Part VII) — which correctly lists it as **not yet built**. |
| "Extended Kalman Filter tracking a 7D physical state vector" (Report 00 §2) | No `backend/services/state.py` exists to contain this. No Kalman filter implementation was found anywhere in `backend/` in this pass. If this exists, it is not where the report says it is. |
| DRDO/VRDE 2.2L common-rail turbo-diesel preset with named HP/altitude derating figures (Reports 00, 11, 14) | **Partially true, differently named.** `backend/physics/engine_config.py` (real, F31 "engine class as configuration") does support multiple engine configurations, and the real, current plan ([`07_unoccupied_axes_and_ground_up_plan.md`](../docs/audit/07_unoccupied_axes_and_ground_up_plan.md) Part II, item F31/F41) independently proposes exactly this reframe — using the **Austro AE300**, the engine actually flown on TAPAS-BH-201 per public sources, not a "DRDO VRDE 2.2L". The specific "VRDE 2.2L, 180 HP, CR 17.5:1" figures in Reports 00/11/14 do not match any public source found across this project's research and should not be repeated until sourced. |

### 2.3 Competitors that could not be independently found

This project has now run **two independent, extensive competitor searches**: (a) a multi-round web search across this conversation that found and catalogued **23 repositories** ([`docs/audit/01_competitive_audit.md`](../docs/audit/01_competitive_audit.md), [`05_expanded_survey.md`](../docs/audit/05_expanded_survey.md)), later verified against **actual cloned source code** for 9 of them; and (b) a separate, legitimate video-based intelligence pass in this repo itself ([`docs/COMPETITOR_ARCHITECTURE_BREAKDOWN.md`](../docs/COMPETITOR_ARCHITECTURE_BREAKDOWN.md), which cites real YouTube URLs and cross-references the same cloned repos under `competitors/`).

**Neither search found any of the following**, named as specific competitors with specific code excerpts in Report 11:

- `Ocramnaig94/digital-twin-for-aircraft-engine-maintenance`
- `sumitrajapure1308/DRDO-UAV-EngineTwin`
- `SabareeshChinta/Drone-Saver`
- `vijayasainandipati/TITAN`

**What is independently confirmed real** (present in both this project's own cloned `competitors/` directory and the video-based breakdown): `atharv20s/sih-26` (PRAHARI), `VIKASHL25/SIH-26`, and Dronanetra (as a real GitHub repo `Jyotirmoy-006/Dronanetra` *and* a real YouTube demo).

🔶 This does not prove the four unconfirmed repositories don't exist — absence of evidence from two independent searches is not proof of absence. But it is a clear signal to **verify each one directly (open the URL, confirm it exists, confirm the cited code excerpt is really in it) before ever naming them to a DRDO panel.** Citing a specific competitor's specific code to a judge, and being wrong about it existing, is a severe and avoidable credibility risk — precisely the failure mode this whole project's documentation discipline (✅/🔶/⬜/🔒 evidence labels) exists to prevent.

**The "500 university teams" figure** (Report 11 §1) is stated with no source and should be treated as unverified until one is found.

---

## 3. The most consequential finding: two contradictory claims about the same bug

Report 00 §4 and §16 claim **"Digital Shadow, Not Digital Twin [PARTIALLY IMPLEMENTED]"** and separately claims an Extended Kalman Filter is "IMPLEMENTED." Independently, this project's own real, current gap analysis ([`docs/audit/07_unoccupied_axes_and_ground_up_plan.md`](../docs/audit/07_unoccupied_axes_and_ground_up_plan.md) Part I) identifies the actual structural problem precisely:

> ⚠️ Currently *the same model* as the twin (gap G01) — the core credibility problem

This is **the real bug**, verified directly: `backend/server/engine_service.py` imports `from backend.telemetry.can_streamer import TelemetryStreamer` — the "actual" sensor stream is generated from the same physics model the twin uses as its "expected" baseline. Residuals are therefore close to pure injected-fault-plus-noise, and detection accuracy figures measure the generator, not a diagnosis.

**The good news, precisely stated:** a fix for exactly this problem has already been built. `backend/plant/virtual_engine.py` is a genuinely independent plant model — its own docstring states the problem and the fix in almost the same words as this project's own audit:

> "The single most damaging structural problem in this project has been that the 'actual' sensor readings were generated from the twin's own expected state plus noise... This module is the plant. It stands in for the real engine and it is deliberately *not* the twin."

**The remaining gap, verified 2026-09-23:** `backend/server/engine_service.py` does **not yet import from `backend.plant`**. The fix exists as a module; it is **not yet wired into the live pipeline**. This is a precise, checkable, one-line-import-away state — not "closed" and not "missing," but **built and disconnected**. State this exact way if asked; do not round it up to "fixed" or down to "not done."

---

## 4. What is actually the authoritative source of truth right now

This repository currently contains **two parallel plans that mostly agree with each other and should be read together, not as competitors**:

1. **`UpdatedReport/` (this folder, Reports 00–30)** — narrative, presentation-oriented, dated "March 2025" (a date that does not match this project's actual timeline and should be corrected before use), written with some verified and some unverified/incorrect specifics.
2. **`docs/audit/` (Reports 01–07)** — the evidence-labelled, source-verified audit and feature-planning series this project has been building throughout its actual working sessions, ending in [`07_unoccupied_axes_and_ground_up_plan.md`](../docs/audit/07_unoccupied_axes_and_ground_up_plan.md) (features F31–F68).

**Git history confirms `docs/audit/07`'s plan is the one actually being executed.** The following commits, in order, implement F01–F68 almost exactly as specified:

| Commit | Implements |
|---|---|
| `fd77805`, `2fc2c6d` | F01–F06 — crank-angle dynamics, per-cylinder combustion diagnostics |
| `37acded` | F12, F13, F31, F32, F36, F48, F60 — damage accumulation, conformal RUL, threshold baseline, engine configs, turbo model, ACES loader, PHM metrics |
| `970ef68` | F33, F35 — FMECA fault taxonomy, isolability analysis |
| `2fc4cbb` | F51, F54 — twin validity monitoring, physics-constrained telemetry integrity |
| `df8fea3` | F34, F46 — OSA-CBM architecture mapping, MAVLink `EFI_STATUS` ingestion |
| `7819c13` | F40, F41, F56, F57 — environment degradation chain, CI injector faults, mission reliability, prescriptive advisory |
| `9962bf9` | Independent virtual plant (`backend/plant/virtual_engine.py`) — **built, not yet wired**, per §3 above |
| `819aa2f` | F08, F67, F68 — edge feature compression, bandwidth/power/latency accounting |
| `d71e1e7` | F14, F16, F17, F62, F63 — validation instruments |

**This is substantial, real, well-reasoned progress** — independently spot-checked in this pass (`backend/ml/crank_diagnostics.py`, `backend/plant/virtual_engine.py`, `backend/evaluation/conformal.py` were all read directly and are genuine, correctly-reasoned implementations, not stubs). Treat `docs/audit/07`'s feature list and its build order (Part XIII) as the current plan of record. Where `UpdatedReport/`'s narrative reports disagree with it on a specific fact, re-verify before trusting either — but lead with `docs/audit/`.

---

## 5. What to do with this folder

⬜ **Recommended, in order:**

1. **Do not present Report 11's four unverified competitor deep-dives to anyone external** until each is opened and confirmed to exist with the claimed content. Still open.
2. **Correct or remove every `backend/services/`, `backend/ml/autoencoder.py`, `backend/ml/classifier.py`, and `d:/Programming/PS054/` reference** in Reports 00–30 before this folder is shown to anyone outside the team. Not attempted — the volume (≈160 occurrences across 18 files) and, more importantly, the fact that the underlying *content* describes an architecture several real packages (`plant/`, `evaluation/`, `mission/`, `reliability/`, `twin/`, `edge/`, `osacbm.py`) have since superseded, means a path-level find/replace would produce documents that read as accurate without being accurate. All 20 remaining files were banner-tagged pointing here instead, which is the honest version of "corrected" available without re-authoring the whole set.
3. **Fix the date.** "March 2025" predates this project's actual working history and will be the first thing a careful reader notices. Still open.
4. ✅ **DONE.** `backend/plant/adapter.py` now wires `VirtualEngine` into `engine_service.py` for nominal flight and faults 1–4, opt-in via `ANUMAAN_USE_INDEPENDENT_PLANT=1`. See §0.
5. **Treat [`docs/audit/07_unoccupied_axes_and_ground_up_plan.md`](../docs/audit/07_unoccupied_axes_and_ground_up_plan.md) and [`docs/04_system_guide.md`](../docs/04_system_guide.md) as the plan of record and current architecture reference respectively.** Still the right call, more so now than when this line was first written — see §4 and §0.

---

*This file does not replace Reports 00–30. It is a verification pass over specific, checkable claims, run against the actual repository on 2026-09-23. Where this file and an earlier report disagree, this file is the one backed by a command run against the real filesystem — check the command, not the authority of either document.*
