# Verification Checklist — Run This Before You Write, and Again Before You Say "Done"

*Every item exists because that exact mistake was found in this repository. If you are an LLM (or human) changing code here, copy this list into your working notes and tick it. Where a check is automated, the command is given; where it is a judgement, the failure it prevents is named. Written 24 September 2026; extend it whenever you find a new class of mistake (see the last section).*

---

## A. Before you write code

| # | Check | How | Failure it prevents |
|---|---|---|---|
| A1 | **Is the file you're about to extend the current one or the old half of a pair?** | Open `SUPERSEDED_VS_CURRENT.md`; search for the filename. | Extending `spectral_analyser.py`, `fault_classifier.py`, `rul_estimator.py`, `can_streamer.py` (all old halves). |
| A2 | **Is it on the live path, harness-only, or orphaned?** | `CURRENT_STATE.md` module table; or `grep -rn "<module>" backend/server` and trace importers. | Building on code the demo never runs, or "wiring" something that is already wired. |
| A3 | **Is the decision already made?** | Search `DECISIONS.md` (D01–D35) for the topic. | Re-litigating settled choices (engine class, LLM provider, Jev, fly-brain role, sampling rate). |
| A4 | **What schema must I emit/consume?** | `INTERFACES.md` — `Frame`, `TruthRecord`, `CycleHealthVector`, config schema. | Inventing a parallel data shape. |
| A5 | **Which backlog item is this, and are its dependencies done?** | `BACKLOG.md` row + `Deps`. | Building E5 things before the E1 pipeline exists. |
| A6 | **Does the module I'm about to wire have tests?** | `grep -rl "<module>" tests` | Wiring untested code and inheriting its unknown defects (found 24 Sep: most research modules have **zero** tests). If none: write the characterization test first (B0.9). |

## B. Universality — must hold for every change (decision D27)

| # | Check | How |
|---|---|---|
| B1 | **No engine name, cylinder index or redline literal in inference/twin/service/UI code.** Everything comes from the selected `EngineProfile`/`EngineConfig`. | `python tests/test_engine_agnostic_ratchet.py` prints the current counts; `pytest tests/test_engine_agnostic_ratchet.py` **fails if any count rose**. If you refactored something out, run `… --update` to lock the lower baseline (it refuses to raise). |
| B2 | **Works for n_cyl ≠ 4, SI and CI, NA and turbo.** A new detector/feature must be parameterised by `n_cyl`, not loop over `range(1,5)` or name `CHT_2`. | Run it against at least two profiles (e.g. `rotax_914` and `vrde_jayem_2_2l`) — both must produce valid output. |
| B3 | **New limits/thresholds carry provenance** (PUBLIC / MANUAL / ASSUMED / PLACEHOLDER) and live in config, not code. | `EngineConfig.unlabelled_numeric_fields()` must be empty; `pytest tests/test_engine_config_provenance.py`. |
| B4 | **No manufacturer/model names in class or function names** (`RotaxX`). | grep your diff. |

## C. Truth, honesty and claims (decisions D04, D21)

| # | Check | How | Failure it prevents |
|---|---|---|---|
| C1 | **No ground-truth read on the inference path** (`FAULT_ID`, `HEALTH_INDEX`, `RUL_HOURS`, plant `truth()`). | `pytest tests/test_no_truth_leak.py` (AST scan of `backend/ml`, `twin`, `detect`, `sources`). | The FlyHash label leak. |
| C2 | **Does the docstring/label/test-name match what the code does?** Read the body. If a name says "conformal", "calibrated", "verified", "guarantee", confirm there is a calibration set / measurement behind it. | Read it; search the file for the quantity being claimed. | `get_conformal_rul()` claimed a coverage guarantee, was a fixed 12 % margin, and its test only checked ordering. |
| C3 | **Every number you quote has a source and an evidence class:** SIMULATION, PUBLIC_PROXY or REAL_FLIGHT — never merged. | `INTERFACES.md` §12; dataset `MANIFEST.json`. | Presenting a proxy result as an engine result. |
| C4 | **False-alarm and detection claims have a sample size and an interval.** Zero alarms in T hours ⇒ upper bound 3/T. | Compute the bound before you write "0 false alarms". | "0 false alarms/hr" over 3 hours (bound ≈ 1/hr). |
| C5 | **Units are stated, and a unit you cannot confirm is labelled unconfirmed.** | Field docs; `ACES_PROVENANCE["unit_caveat"]`. | Reporting ACES EGT in °C when the scale is unconfirmed. |
| C6 | **Assumed engine constants are not presented as specifications.** | `cfg.provenance_status(path)`; check before quoting. | VRDE config read as a manufacturer spec. |

## D. Data, models and freshness (decision D28)

| # | Check | How |
|---|---|---|
| D1 | **Every model file has a sidecar**: generating script + git commit, engine profile(s), data source and hash, date, evaluation and its split rule. No sidecar ⇒ untrusted. | `ls backend/ml/models/*.json`; open the sidecar. |
| D2 | **Was the model trained on data from a source independent of what it is evaluated on?** (plant vs twin, group split by mission/engine/flight — never random frames). | Read the training script's split. |
| D3 | **Is the artifact older than the design it must serve?** Models dated before 23 Sep pre-date ACES, the configs and the plant → stale. | `ls -la --time-style=long-iso`; `docs/build/UNIVERSALITY_AUDIT.md` §7. |
| D4 | **No absolute or foreign-machine paths** in manifests/configs (`E:\TalentForge\...`, `d:/Programming/...`). | `grep -rnE "[A-Za-z]:[\\\\/]" configs data/*.json backend --include=*.json --include=*.py` |
| D5 | **A dataset is not "used" until a loader + an experiment reads it.** Downloaded ≠ integrated. | `grep -rn "<dataset dir>" backend experiments`. |
| D6 | **Large artifacts:** don't add multi-GB files; check `.gitignore`/LFS; delete vestigial ones (Qwen weights, tarball duplicates). | `du -sh` on what you added. |

## E. Security / supply chain (decisions D14, D17, D24)

| # | Check |
|---|---|
| E1 | No Chinese-origin model, library or component introduced as a default. New dependency → record origin and licence. |
| E2 | No hosted/foreign API in any default code path (air-gapped, on-prem). |
| E3 | Secrets, tokens and credentials never enter the repo or logs (an Earthdata token was once pasted into a chat — treat any such token as burned). |

## F. Testing and finishing (decision D26)

| # | Check | How |
|---|---|---|
| F1 | `pytest` from the repo root; **count did not drop**; you added tests for what you added. | `python -m pytest tests -q -p no:cacheprovider` |
| F2 | A test that cannot fail is not a test: for a bug fix, confirm the test **fails on the old code**. | `git stash` the fix, run the test, restore. |
| F3 | **Headline results are pinned as tests**, not left as a log entry. | B0.9. |
| F4 | Log the session in `docs/IMPLEMENTATION_LOG.md` in the *what was broken / what was done / verified / unproven* format. **Unproven may not be empty.** | |
| F5 | Update `BACKLOG.md` (✅/🟡), `CURRENT_STATE.md` (status column + test count), `SUPERSEDED_VS_CURRENT.md` if you touched a pair. | |
| F6 | New docs must be under a path that is **not gitignored** (`git check-ignore -v <file>`; `docs/build/` was silently ignored by a `build/` rule until fixed). | |
| F7 | If you are out of quota: leave the tree passing, mark half-done items 🟡 in the backlog with what remains, and log it. | `MENTAL_MODEL.md` §9. |

## G. The "am I fooling myself" pass (do this last)

1. Restate in one sentence what the live demo now does differently because of your change. If the answer is "nothing", say so plainly in the log — code that isn't on the live path is not delivered capability.
2. List what you did **not** verify.
3. Grep your own diff for the words *verified, tested, calibrated, guarantee, real, independent, validated*. Each one must be backed by something you ran.
4. Ask whether you wired an old half of a pair (A1) or added an engine-specific literal (B1).

## H. Runtime, detectors and experiments (added 24 Sep after the multi-engine audit)

| # | Check | How | Failure it prevents |
|---|---|---|---|
| H1 | **Probe whether a fault is even visible in the channels your detector reads** before claiming detection. | Inject on a plant, diff every channel against a same-seed nominal run (see `DETECTOR_DECISION` s4). | Building scalar detectors for injector faults that leave no scalar trace (F22). |
| H2 | **Do not quote cross-engine results from the plant until the plant is engine-class-aware** (R6); label them indicative. | Check EGT/rpm of every profile against its config envelope. | Reporting artefacts of a Rotax-shaped plant as engine performance (F21). |
| H3 | **Any lever must act through the plant or the sensor model and log its `origin`**; runs with manual origins are excluded from KPIs. | Read the injection path; check the truth record. | Cosmetic levers (F23) and evidence pollution. |
| H4 | **Never call a scikit-learn model one row at a time on a hot path**; gate, batch or compile. | Time it (`experiments/E17` latency block). | 11.5 ms per call x 100 calls/s (F27). |
| H5 | **Check a dependency's licence exists and is permissive before importing code.** No licence = excluded. | GitHub license API / LICENSE file. | Shipping `ffbf` (no licence) in a deliverable (D35). |
| H6 | **An experiment states its evidence class, split rule, seeds and limits, and has confidence intervals before it is quoted.** | `docs/evaluation/*.json`. | Quoting E17 magnitudes (single seed set, simulated). |
| H7 | **Check the asset is a real file, not a git-LFS pointer** (< 200 bytes starting `version https://git-lfs`). | `head -c 60 <file>` | Referencing 39 stub files as if they were assets (F25). |
| H8 | **Re-run the reachability audit after wiring** and record the counts. | `python scripts/tools/audit_reachability.py` | Believing something is wired because a file exists. |

## Keeping this list alive

Each row above corresponds to a finding in [`FINDINGS.md`](FINDINGS.md) (evidence and status there).

When you discover a new *class* of mistake — not an instance — add a row here with the failure it prevents and, if at all possible, an automated check (a test like `test_no_truth_leak.py` or the ratchet). A checklist that only grows by prose will be skipped; one that grows by tests will not.
