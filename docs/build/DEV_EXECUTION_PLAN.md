# Development Execution Plan — How the Build Will Be Run

*24 Sep 2026. Written for any engineer or LLM continuing the work. Companion to `BACKLOG.md` (what), `DECISIONS.md` (why), `VERIFICATION_CHECKLIST.md` (how to check). This file is the **how we operate** document. Every operation touching the working directory is listed with a risk level; nothing marked "ask" is done without the owner's yes.*

## 1. Operations on the working directory (do these first)

| # | Operation | Why | Risk | Rule |
|---|---|---|---|---|
| O1 | **Commit the current pile in logical chunks** (docs/build + audit; backend core/sources/detect; tests; experiments; Datasets tooling; config JSONs). Branch `maverick-main`, Conventional-Commit messages, no `git add -A` | ~100 modified/deleted files are uncommitted; one bad command loses days | low | Do before any deletion |
| O2 | **Tag a safety point**: `git tag pre-dev-2026-09-24` after O1 | one-command rollback | none | |
| O3 | **Safe-tier cleanup** from `DEAD_CODE_AUDIT.md` §6.1: `.blend1` backups, `scratch/`, root `.mp4`, Blender `test_*` experiments, add `*.blend1` to `.gitignore` | removes noise judges/LLMs trip on | low | `git mv` to `archive/`, never `rm` on first pass |
| O4 | **Archive tier**: harvesters, TB3/PD170 pipeline, legacy CSVs with foreign paths → `archive/` | reversible | low | `git mv` |
| O5 | **Free ~9 GB** (`vendor/Qwen3-4B`, duplicate NASA tarballs) | disk + clone size | medium | **ask** (deletes data); hash-check duplicates first |
| O6 | **LFS reality check**: 39 pointer stubs. `git lfs pull` if the remote has them, else strip references | build scripts silently broken | medium | **ask** (network, size) |
| O7 | **Never delete** the 15 orphan libraries (4,235 lines) before B0.9 + wiring | they are the designed replacements | — | policy |
| O8 | **Regenerate, don't hand-edit**, `docs/evaluation/*.json` (E17, E19, reachability) | reproducibility | none | scripts are the source |
| O9 | Retry blocked datasets (`Datasets/download_all.py --only marine,road --connections 1`) in background | Zenodo throttling | low | one connection only |
| O10 | Re-run `scripts/tools/audit_reachability.py --json` after each milestone | progress meter (orphan lines → 0) | none | |

## 2. Branching, commits, CI

- **Branches:** `maverick-main` is integration. One short-lived branch per slice (`slice/w1-detector`, `slice/r1-runtime`) merged after its checks pass. `main` is only updated at milestones.
- **Commit size:** one backlog row ≈ one commit; message names the row ID (`feat(detect): W1 calibrated residual detector`).
- **Gate on every commit:** `python -m pytest -q` green (currently 163), ratchet tests green (`test_engine_agnostic_ratchet`, `test_no_truth_leak`), no new file over 5 MB, no secrets, no new third-party import without a licence entry (D35).
- **Add a pre-commit / CI script** (`scripts/tools/precommit_check.py`): runs the ratchets, the AST truth-leak scan, the provenance check, and refuses `.blend`/model binaries outside LFS. (Backlog B0.6.)
- **Do not** amend or force-push; never skip hooks.

## 3. Slice-based build order (each slice ends runnable + tested + documented)

| Slice | Content (backlog rows) | Definition of done |
|---|---|---|
| **S0 Hygiene** | O1–O4, B0.6 | clean tree, tag, tests green |
| **S1 Safety net** | B0.9 characterization tests for orphan modules (rainflow, conformal, PHM metrics, Wilson, FMECA, crank order, misfire rate) | numbers pinned in tests, each orphan has ≥1 test |
| **S2 Detector core** | W1 `backend/detect/` calibrated-residual detector (n_cyl-agnostic, per-tail calibration sidecar, Mahalanobis + max\|z\|, conformal threshold); FlyHash tier-0 wrapped behind the same `score()` interface | reproduces E17 AUROC within tolerance from the library, not the experiment script |
| **S3 Reservoir tier** | W11 E19 LOEO + `detect/reservoir.py` (sparse ESN, connectome init, ridge head, per-tail readout) | beats RF LOEO by more than seed spread, else documented null (rule in `FLY_100_WAYS.md`) |
| **S4 Multi-engine runtime** | R1–R4: `RuntimeHub` with one `EngineRuntime` per profile, tier-0/1 for all, heavy tier for selected engine, WS routes per engine, hot switch | five engines concurrent, switch < 100 ms, seeded bit-identical replay |
| **S5 Plant honesty** | R6 plant class-awareness, R2/R3 real levers with dynamics, injector-fault waveform channel (W6) | levers change physics; `TruthRecord.origin` excludes manual levers from KPIs |
| **S6 Waveform + edge** | W3 recorder/replayer, W4 Pi-5 emulation profile, persistence-gated scalar downlink, W5 waveform bake-off | edge accounting in HealthFrame v2 |
| **S7 Ground tier** | W10 Jev bake-off, W8 foundation-model control, maintenance ranker | offline provider, gated by D37 |
| **S8 Surface** | V1–V10 visuals, engine dropdown UI, Blender bridge on the new pipeline | demo shows the new pipeline only (D05) |
| **S9 Evidence pack** | claims/evidence table, real-flight anchor (ACES), Pi 5 hardware benchmark, federated Bloom merge (W12) | `27_CLAIMS_AND_EVIDENCE.md` regenerated from artifacts |

Order rule: **wire one honest end-to-end path (plant → Frame → detect → fly tiers → API → UI) on the selected engine before broadening.** Anything not on that path waits.

## 4. Working method (per slice)

1. Read the backlog row, its decision, and the relevant `VERIFICATION_CHECKLIST` section.
2. Write the test first when the behaviour is already specified (characterization or ratchet); write the experiment first when the behaviour is a claim (E-series, pre-registered rule).
3. Implement in the library (`backend/…`), never in an experiment script.
4. Run tests + reachability audit + ratchets.
5. Update: `BACKLOG` status, `FINDINGS` (if anything surprised us), `DECISIONS` (if anything changed), `IMPLEMENTATION_LOG`, `CURRENT_STATE`.
6. Commit. Only then start the next slice.

**Parallelism:** independent research/benchmark slices (W10 Jev bake-off, dataset loaders, visual components) may be given to subagents in isolated worktrees; wiring slices (S4, S5) are done serially in the main tree because they touch shared runtime files.

## 5. Guardrails (learned from this project's own mistakes)

- Truth isolation: nothing under `backend/ml|twin|detect|sources` may read `FAULT_ID/HEALTH_INDEX/RUL_HOURS` (AST test).
- Engine-agnostic ratchet: literal counts may only fall.
- Provenance: every numeric config field labelled PUBLIC/MANUAL/ASSUMED/PLACEHOLDER; never quote ASSUMED numbers as fact.
- Evidence class on every number: SIMULATION / PUBLIC_PROXY / REAL_FLIGHT. Simulation accuracy is never presented as field performance.
- No claim without a null control (shuffled, random, or baseline) — the E19 pattern.
- Sklearn is never called one row at a time on the live path (11.5 ms/row trap).
- Third-party code needs a present, permissive licence (D35); TabPFN 2.5+ and Moirai are research-only.
- No LLM in a detection path; the LLM provider defaults to `none`.
- Unknown = say so and add a verification row, do not fill with plausible numbers.

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Demo still driven by the old circular pipeline | S8 only after S2–S5; D05 (one pipeline) enforced by test |
| Simulator-only evidence attacked by judges | S9: ACES real anchor, PUBLIC_PROXY datasets, explicit evidence classes, foundation-model zero-shot control (W8) |
| Reservoir advantage vanishes under LOEO | rule pre-registered; FlyHash + RF remain the shipped floor |
| Pi 5 numbers are emulated | S9 real-board benchmark; until then all edge numbers are labelled emulated |
| Repo weight / LFS stubs break builds | O5/O6 |
| Scope creep (V-tier visuals before core) | order rule in §3 |

## 7. What needs the owner's decision (only these)

O5 (delete large data), O6 (LFS pull from network), and any use of paid/cloud services. Everything else proceeds autonomously.
