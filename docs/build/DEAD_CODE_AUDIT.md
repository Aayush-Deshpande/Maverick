# Dead & Stale Code Audit — What We Do Not Want Here

*Audit date 24 September 2026. Method: a static import-graph analysis ([`scripts/tools/audit_reachability.py`](../../scripts/tools/audit_reachability.py), re-runnable; raw output [`../evaluation/reachability_audit.json`](../evaluation/reachability_audit.json)) plus direct inspection of files, git-LFS state and sizes. **Nothing has been deleted.** Every row carries a recommended action and the reason, so you can approve in bulk. Companion to [`SUPERSEDED_VS_CURRENT.md`](SUPERSEDED_VS_CURRENT.md) (duplicate implementations) and [`UNIVERSALITY_AUDIT.md`](UNIVERSALITY_AUDIT.md) (engine-specific code and stale models).*

**Limits of the method (be honest):** dynamic imports, `.bat`-launched `python -m` entry points and Blender-side scripts are not traced. "Nothing imports it" means *verify, then act* — not proof.

---

## 1. The picture in numbers (backend, 69 modules)

| Class | Modules | Lines | Meaning |
|---|---|---|---|
| **LIVE** (import-reachable from the FastAPI app) | 42 | 12,595 | ⚠️ "import-reachable", not "executed by default": `plant/adapter.py` imports the independent plant and its physics modules, but the adapter is **off by default** |
| **HARNESS-only** | 6 | 1,596 | evaluation harness + experiments (includes this session's `core/frame`, `sources`) |
| **TEST-only** | 6 | 1,649 | only pytest imports them |
| **ORPHAN library** | 15 | **4,235** | imported by nothing — but see §3: mostly *the new design awaiting wiring*, not trash |
| **Scripts/apps not imported by anything** | 55 | 24,832 (scripts 18,404 · apps 6,428) | entry points or dead — §4 |

## 2. Decision table — backend

| Item | Lines | Class | Recommended action | Why |
|---|---|---|---|---|
| `ml/fault_classifier.py` (`RotaxFaultClassifier`) | 251 | TEST-only | **DELETE with its two tests** once B5.3 lands (or now — nothing live calls it) | Dead duplicate of `DetectionPipeline._classify()`; copy-pasted thresholds diverge silently (S04) |
| `telemetry/rotax_dataset_generator.py` | 484 | TEST-only | **RETIRE with the old RF** (U8) | Generates the *circular* RF training data (S01); Rotax-named |
| `telemetry/dataset_fusion_engine.py` | 311 | TEST-only | **RETIRE** (replace by `backend/datasets/`, B7.1) | Imports the deprecated streamer; fuses proxies into one headline set (violates "never merge") |
| `telemetry/parsers/{garmin,nasa_prognostics}_parser.py` | 314 | TEST-only | ARCHIVE; re-derive as loaders in `backend/datasets/` | Feed the fusion engine |
| `telemetry/aces_loader.py` | 289 | TEST-only | **KEEP** (fixed 24 Sep) → wrap as `ReplaySource` (B1.2) | Real-flight anchor |
| `ml/spectral_analyser.py` | 279 | LIVE | **REPLACE** by `dsp/` (B3.4) | 20 Hz premise cannot see its target (S05) |
| `ml/rul_estimator.py` | 217 | LIVE | **REPLACE** (B6.1) | Hardcoded lifetimes; fake conformal (S03, S07) |
| `telemetry/can_streamer.py` | 512 | LIVE | **RETIRE** after R1/B1.5 | Circular source; 8 cylinder-pinned faults; 912 iS mesh names (S01, S02) |
| `physics/thermo_model.py` | 418 | LIVE | **REPLACE** (B4.1) | Hardcoded Rotax constants (S06) |
| `plant/adapter.py` | 187 | LIVE (flag off) | **DELETE after B1.4** | Stopgap blend |
| `ml/anomaly_detector.py`, RF `.joblib`, AE `.json` | 410 + models | LIVE | keep as *contenders only*; models are **stale** (2 Sep, circular) | UNIVERSALITY_AUDIT §7 |
| `agent/llm_engine.py` etc. | ~1,700 | LIVE | KEEP (optional; default disabled) | B0.2 |

## 3. The orphan libraries — do **not** delete (4,235 lines)

`edge/compressor` 272 · `evaluation/{conformal, damage_accumulation, prognostic_metrics, validation}` 1,090 · `mission/{reliability, prescriptive}` 611 · `osacbm` 291 · `physics/exposure` 229 · `reliability/{fmeca, isolability}` 742 · `telemetry/{mavlink_efi, socketcan_bridge}` 391 · `twin/{integrity, validity}` 609.

These are **the designed replacements** for the live legacy code above. They are unwired *and untested* (FINDINGS F10). The action is **B0.9 (characterization tests) → wire**, not removal. Treat deleting them as the single most expensive mistake available here.

## 4. Scripts and apps (55 unreferenced entry points)

| Group | Files (lines) | Recommended action | Reason |
|---|---|---|---|
| **Blender experiments** | `scripts/test_{angles_wireframe, bomb_parenting, gear_constraint, hero_angle, keyframe_behavior, transform_constraint, wing_fold_driver, wireframe_fdda, wireframe_perfect}` (~766) + `stamp_wireframe_text` 40 + `render_comparison_gallery` 62 | **DELETE** | One-off experiments; misleadingly named `test_*` but not pytest; unrelated to PHM |
| **UAV image/dataset harvesters** | `harvest_all_uavs` 798, `run_fast_uav_harvester` 757, `collect_uav_datasets` 514, `harvest_all_uav_categories` 481, `harvest_parallel_uavs` 465, `harvest_all_uavs_clean` 419 (**~3,430**) | **ARCHIVE or DELETE** | Six overlapping web-scrapers for reference images (a past session fixed their hardcoded paths — sunk effort, still low value). Keep the *output* (`assets/model_images`), not the tools |
| **Bayraktar TB3 / TEI PD170 asset pipeline** | `build_bayraktar_tb3` 1,545, `build_tb3_digital_twin` 1,559, `generate_tb3_*` ×3 987, `generate_clean_pbr_textures` 214, `tb3_ui_controller` 206, `build_tei_pd170` 1,445, `pd170/*` 450 (**~6,400**) | **ARCHIVE** to `archive/asset_pipeline/` | Their outputs are LFS stubs; there is no physics config for PD170; TB3/PD170 are outside the requested dropdown scope (Rotax family + Austro AE300). Revive only if U1 adds `tei_pd170` |
| **Austro AE330 asset pipeline** | `build_austro_ae330` 2,374 + `_details` 1,178 (3,552) | **KEEP** | Produces the one real non-Rotax asset (needed for the AE300 dropdown entry) |
| **Shared Blender libs** | `scripts/lib/anumaan_{blender,cad,twin_controller}_lib` ~1,430 | KEEP while any build script is kept | |
| **PHM-relevant scripts** | `test_socketcan_mavlink_bridge` 131, `simulate_missions` 153, `ingest_rag_docs` 573, `populate_engine_references` 50, `tools/*` | KEEP | `test_socketcan_mavlink_bridge` is a real bridge test → convert to pytest |
| **Demo apps** | `canyon_flight_app` 2,366, `digital_twin_app` 1,408, `desktop_gcs` 521, `mission_graph` 1,151+426 | **KEEP, FREEZE** (D25) | Presentation surface; canyon sim is peripheral to PHM — do not invest further |

## 5. Assets, data and repo weight

| Item | Size / state | Action |
|---|---|---|
| **39 git-LFS pointer stubs** — incl. `assets/blender/bayraktar_tb3_digital_twin.blend`, `assets/models/airframes/bayraktar_tb3.blend`, and the entire Rotax 912 iS STEP CAD folder (`engine-rotax-912is-1.snapshot.15/*.stp`) | 131–133 bytes each; **not real files** | `git lfs pull` if wanted; otherwise remove references. The UI/build scripts that name them are silently broken |
| `.blend1` Blender auto-backups (8) | ~ | **DELETE**, add `*.blend1` to `.gitignore` |
| `vendor/Qwen3-4B` | 7.6 GB | **DELETE / move out** (LLM disabled by default, B0.2) |
| `Dataset/*.tar` (1.3 GB) duplicating `data/telemetry/nasa_aces/raw/*.tar` | 1.3 GB | **DELETE one copy** after hashing |
| `Datasets/` | 41 GB | Keep essentials; **N-CMAPSS (15.8 GB) optional**; no loader reads any of it yet (E7) |
| `competitors/` | 892 MB | Exclude from repo/CI (already gitignored) |
| `data/telemetry/rotax912_{train,val,test}_dataset.csv`, `train/ val/ test/`, manifest with **another machine's paths** | 8 MB | **ARCHIVE**; regenerate from the plant per profile (D28) |
| `report_dump/mission_*`, `data/telemetry/live_sorties/*.csv` | runtime output | **gitignore** (B0.6) |
| `scratch/` (one-off Python, audio experiments, screenshots, validation md/json), root `WhatsApp Video….mp4` | small/MB | **DELETE / move to `archive/`** |
| Frontend | 0 unused components | ✅ clean |

## 6. Recommended clean-up order (safe → risky)

1. **Safe now:** `.blend1` backups; `scratch/`; the root video; Blender `test_*` experiments; `*.blend1` in `.gitignore`.
2. **Archive (reversible):** harvesters; TB3/PD170 pipeline; legacy dataset files with foreign paths.
3. **Free 9 GB:** Qwen weights; duplicate NASA tarballs.
4. **Delete after replacement exists:** `fault_classifier`, `rotax_dataset_generator`, `dataset_fusion_engine`, `plant/adapter`, then `can_streamer`, `spectral_analyser`, `rul_estimator`, `thermo_model` (per the SUPERSEDED table).
5. **Never:** the orphan libraries (§3) before B0.9 + wiring.

Merge this into backlog **B0.6** (hygiene); `git mv` to `archive/` rather than deleting on the first pass, so any surprise is one revert away.

## 7. Keep this audit honest

Re-run `python scripts/tools/audit_reachability.py --json docs/evaluation/reachability_audit.json` after any wiring milestone; the LIVE/HARNESS/ORPHAN counts above are the progress meter for tier E1 (orphan lines should fall toward zero as B1.x/B4.x/B5.x/B6.x land).
