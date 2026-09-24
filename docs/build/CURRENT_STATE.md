# Current State of the Code

*Snapshot on 23 September 2026, updated 24 September 2026 after CORE, WAVEFORM, TWIN, DIAG, EDGELINK, FLEET, DATA, and FOUNDATION builds. The import graph was traced from `backend/server/engine_service.py` and all modules, and `pytest` was run (**316 passed, 1 strict xfail**, was 129 at start).*

## 0a. Measured reachability (24 Sep; `scripts/tools/audit_reachability.py`)

| Class | Modules | Lines |
|---|---|---|
| LIVE (import-reachable from the app/server) | 56 | 14,180 |
| HARNESS-only | 25 | 3,812 |
| TEST-only | 35 | 6,390 |
| ORPHAN libraries | **0** | **0** |
| Unreferenced scripts/apps | 27 | 13,846 |

**All research and new capability modules have been wired into either the live runtime, evaluation harness, or comprehensive test suites.** Evaluation artifacts generated and verified: `E20_runtime_end_to_end.json`, `E21_twin_estimation.json`, `E22_diag_prognostics.json`, `E23_edgelink_security.json`, `E24_fleet_des.json`, `E25_foundation_bakeoff.json`.

Details and actions: [`DEAD_CODE_AUDIT.md`](DEAD_CODE_AUDIT.md). New since the last snapshot: `experiments/E17_detector_bakeoff_plant.py` (harness-only), `scripts/tools/audit_reachability.py`. Runtime today is a single-engine singleton with cosmetic levers (F23, F24) - target in [`MULTI_ENGINE_ARCHITECTURE.md`](MULTI_ENGINE_ARCHITECTURE.md).

## 0. Single-engine coupling (second structural problem)

The live system is a Rotax 912 iS / 4-cylinder simulator: no engine-selection path exists, and engine-specific literals are counted (286 cylinder-index, 78 brand, 37 model-number) by `tests/test_engine_agnostic_ratchet.py`. Trained ML models are dated 2 Sep and predate the redesign. Full evidence, target design and artifact freshness table: [`UNIVERSALITY_AUDIT.md`](UNIVERSALITY_AUDIT.md). Backlog tier E12.

## 1. The two stacks (the main structural problem)

- **Live service:** `engine_service` → `can_streamer.TelemetryStreamer` (sensor data generated from the twin's own equations) → `DetectionPipeline` → `RULEstimator` → copilot/voice → React + Blender.
- **Research stack:** plant, crank chain, residual detector, evaluation, twin validity/integrity, reliability, mission and edge. It produces every defensible number but is **not reachable from the service**.

Fix: backlog E1 (one pipeline).

## 2. Module map

| Module | Lines | Status | What it is | Known issues | Action |
|---|---|---|---|---|---|
| `core/frame.py` | ~200 | TEST (new, not yet on the live path) | Canonical `Frame` + `TruthRecord`; forbidden-field rejection | Live service still runs on `EnginePhysicalState` | WIRE in B1.3/B1.4 |
| `sources/plant_source.py` | ~60 | TEST (new, not yet on the live path) | Current independent plant (`VirtualEngine`) as `(Frame, TruthRecord)` | Only faults the plant models (12 plant fault names); no ReplaySource/MavlinkSource/CanSource yet | EXTEND (B1.2 remainder) |
| `server/engine_service.py` | 812 | LIVE | Hosts the 20 Hz loop, WebSockets, fault commanding | Imports the circular `TelemetryStreamer`; plant adapter opt-in | EXTEND → host `Pipeline` (B1.4) |
| `server/main.py`, `schemas.py` | 566/171 | LIVE | FastAPI app, REST + WS | — | KEEP |
| `telemetry/can_streamer.py` | 512 | LIVE | "Actual" frames = twin equations + fault deltas; `DRDO_FAULT_DEFINITIONS` (8 faults, cylinder-hardcoded) | **Circular (G01)**; no CAN frames despite the name | RETIRE → `LegacySource` (B1.2) |
| `plant/virtual_engine.py` | 424 | HARNESS (+ LIVE via adapter, flag off) | Independent plant: crank, turbo, induction, fuel thermal, injectors, oil; build variation; sensor model; `truth()` separate | Models faults 1–4 of the 8 only | EXTEND (B1.5, E2) |
| `plant/adapter.py` | 187 | LIVE (flag `ANUMAAN_USE_INDEPENDENT_PLANT=0`) | Bridges the plant into the service for nominal + faults 1–4 | Stopgap | RETIRE after B1.4 |
| `physics/thermo_model.py` | 418 | LIVE | Algebraic steady-state "expected state" + `ResidualVector`; Rotax 912 iS constants; `EnginePhysicalState` (contains `FAULT_ID`) | Not dynamic; ignores `engine_config`; truth field in the state | REPLACE with `twin/model.py` (B4.1); `Frame` replaces the state (B1.1) |
| `physics/engine_config.py` + `configs/engines/*.json` | ~270 | TEST (turbo/plant use it) | Engine class as configuration: 912iS, 914, AE300, `vrde_jayem_2_2l`, **`rotax_915is`** | ~~VRDE file presents assumed values as a "specification"; no per-field provenance; no 915 iS~~ **fixed (B0.4)** — full per-field provenance on all 5 configs | KEEP |
| `physics/crank_dynamics.py` | 364 | HARNESS (via plant) | Wiebe → p(θ) → torque → ω(θ) → accelerometer (single damped resonance) | SI-only; single-mode structure; no chamber acoustics | EXTEND (B2.1, B2.3) |
| `physics/turbo_model.py`, `induction.py`, `fuel_thermal.py`, `injector_faults.py`, `oil_system.py` | 182–274 | HARNESS (via plant) | Subsystem physics; faults act on parameters | Placeholder coefficients (labelled) | KEEP / EXTEND |
| `physics/exposure.py` | 229 | ORPHAN | Environment exposure accumulator | Not wired | WRAP into the degradation PF (B4.4) |
| `physics/sensor_validator.py` | 376 | LIVE | Sanity checks, rate limits, residual shielding | — | KEEP (inside B5.6) |
| `ml/detection_pipeline.py` | 749 | LIVE | 9 stages at 20 Hz: sanity → residuals → FlyHash (2c) → autoencoder → "FFT" → RF → majority vote → baseline comparator → emit | ~~Line 391: FlyHash calibrates on `FAULT_ID`~~ **fixed (B0.1)**; rules hardcode cylinders (lines 553–585); "FFT" is a DFT of a 20 Hz RMS scalar | REPLACE by the staged pipeline (E1, E3, E5) |
| `ml/fault_classifier.py` + `models/rotax_random_forest.joblib` | 251 | LIVE (loaded by the pipeline) | RF, 100 trees, 14 residual features, 9 classes; 97.5 % on generator output | Circular accuracy; generator-defined classes | Keep only as a bake-off contender (E06) |
| `ml/anomaly_detector.py` | 410 | LIVE | NumPy autoencoder 14-8-4-8-14 | 66.5 % fault recall | Contender only |
| `ml/flyhash_novelty.py` | 237 | LIVE | FlyHash + "seen-bits" novelty | Residuals-only input; **truth-leak calibration FIXED (B0.1)** — now frame-count windowed; still no time decay or regime conditioning | EXTEND → `detect/` (B5.1) |
| `ml/spectral_analyser.py` | 279 | LIVE | Nyquist-aware DFT on the 20 Hz RMS scalar | Physically cannot see the target frequencies | REPLACE by `dsp/spectral.py` (B3.4) |
| `ml/crank_diagnostics.py` | 439 | HARNESS | Per-cylinder work attribution, order features, envelope | Verified in simulation (misfire rate recovered exactly) | WRAP into `dsp/` (B1.6, B3.x) |
| `ml/trend_analyser.py` | 755 | LIVE | Score buffer + 20 s prognostics worker | — | Review in E6 |
| `ml/rul_estimator.py` | 208 | LIVE | Hardcoded component lifetimes × stress multipliers | **Not a prognostic** | RETIRE (B6.1) |
| `twin/residual_detector.py` | 243 | HARNESS | Frozen per-tail offset calibration; sensor-vs-engine by relative corroboration | Three failed designs documented in the file | WRAP (B5.1) |
| `twin/validity.py` | 308 | ORPHAN (exported) | NIS, Ljung-Box, bias, envelope → NOMINAL / MODEL_DRIFT / ENGINE_FAULT / OUT_OF_ENVELOPE | `expected_sigma` set by hand | KEEP; feed it UKF innovations (B4.2) |
| `twin/integrity.py` | 301 | ORPHAN (exported) | Physics-constrained spoof detection with conformal thresholds; stale/frozen; lane disagreement | Tested only against synthetic frames built from the same relations | KEEP; wire in B5.6; test on ACES |
| `evaluation/harness.py` | 422 | — (script entry) | Plant vs twin vs threshold baseline over 8 scenarios | n = 1 per scenario; measures `ResidualDetector`, not the live pipeline | EXTEND → drives `Pipeline` (B1.4) + campaign (B1.7) |
| `evaluation/threshold_baseline.py` | 217 | HARNESS | Debounced caution/warning monitor with Rotax 914 limits | — | KEEP |
| `evaluation/conformal.py` | 237 | ORPHAN (exported) | Split conformal, normalised scores, ACI, coverage | Not wired | KEEP (B5.2, B6.1) |
| `evaluation/damage_accumulation.py` | 290 | ORPHAN (exported) | Rainflow + Miner, Coffin-Manson, shock cooling | Placeholder constants | KEEP (B4.4) |
| `evaluation/prognostic_metrics.py` | 206 | ORPHAN (exported) | PH, α-λ, RA, convergence (NASA library port) | Never run on a real RUL | KEEP (E03) |
| `evaluation/validation.py` | 357 | ORPHAN | Residual shielding, NoveltyGate/UNKNOWN, point-wise vs point-adjusted F1, sim-to-real | — | KEEP |
| `reliability/fmeca.py`, `isolability.py` + `docs/reliability/*.json` | 450/292 | DOC | 20 modes per MIL-STD-1629A; isolability 55 % → 95 % with the proposed sensors | Severity/occurrence by judgement | KEEP; drives the BN (B5.3) |
| `mission/reliability.py`, `prescriptive.py` | 347/264 | ORPHAN | Mission reliability with Wilson interval; derate ladder; re-planning | Placeholder hazards | EXTEND (B6.2) |
| `edge/compressor.py` | 272 | ORPHAN | 29-byte `EdgeFeatureFrame`; link budget; latency; power | — | KEEP (HealthFrame v1) |
| `telemetry/aces_loader.py` | ~245 | ORPHAN | Reads ACES `.mat`; 21 channels (+CHT/EGT_3/EGT_4); plausibility envelope | ~~EGT binding wrong (reads 170 °C)~~ **fixed (B0.3)** — binding verified against an independent competitor decode; **numeric scale (C vs F) still unconfirmed**, `ACES_PROVENANCE["unit_caveat"]` documents it | WRAP (B1.2) |
| `telemetry/mavlink_efi.py` | 209 | TEST/script | EFI_STATUS decode | Never run against SITL | WRAP (B1.2) |
| `telemetry/socketcan_bridge.py` | 182 | script | J1939 PGN pack/unpack; virtual bus | No DBC; `python-can` not in requirements | WRAP (B1.2, B2.6) |
| `telemetry/replay_engine.py`, `dataset_fusion_engine.py`, `rotax_dataset_generator.py`, `parsers/` | — | LIVE / script | Replay manifests; the training-set generator (circular) | Generator = circular | Replay: WRAP; generator: RETIRE |
| `osacbm.py` | 291 | DOC | Registry of 28 modules on the 6 layers + layering check | Not an executor | EXTEND (B1.3) |
| `agent/llm_engine.py`, `copilot.py` | ~360/1,190 | LIVE | Ollama-served RAG copilot, **provider-pluggable** (`LocalLLMEngine`; `LocalQwenEngine` alias kept) | ~~Chinese-origin default model~~ **fixed (B0.2)** — default is `ANUMAAN_LLM_PROVIDER=none`, disabled; `sarvam`/`bharatgen`/`qwen`(opt-in only)/`local-other` selectable; Ollama tags for sarvam/bharatgen unconfirmed | KEEP |
| `agent/diagnostic_agent.py` | 309 | LIVE | ATA-style directives per fault | Tied to the 8 generator faults | Replace by B10.1 |
| `graph/`, `reports/`, `knowledge/`, `voice/` | — | LIVE | Mission knowledge graph, debrief bundles, RAG store, STT/TTS | — | KEEP (optional features) |
| `frontend/src/` (15 components) | — | LIVE | React GCS panels | No uncertainty, no ambiguity groups, no evidence page | EXTEND (B11.1) |
| `apps/blender_twin/` etc. | — | LIVE | Blender 3D twin, canyon sim, desktop GCS, mission-graph viewer | — | Freeze (D25) |

## 3. Tests

- `tests/` holds 14 files and **129 tests, all passing** on 23 Sep 2026.
- **Corrected 24 Sep:** the newer research modules are **not tested at all** (previously described as "tested in isolation"). Verified by grepping `tests/`: no pytest file covers `evaluation/{conformal,damage_accumulation,prognostic_metrics,validation,threshold_baseline,harness}`, `mission/*`, `reliability/*`, `edge/compressor`, `twin/{validity,integrity,residual_detector}`, `plant/virtual_engine`, `physics/{crank_dynamics,turbo_model,injector_faults,oil_system,fuel_thermal,induction,exposure}`, `telemetry/mavlink_efi`, or `osacbm`. Their "Verified" entries in `IMPLEMENTATION_LOG.md` are records of ad-hoc runs. Tests that *do* exist target the legacy live stack plus this session's additions (truth-leak scan, LLM default, engine-config provenance, ACES binding, Frame/PlantSource).
- No test exercises the plant → pipeline → diagnosis path end to end. **B1.4's bit-exact replay test is the first.** **Write B0.9 (characterization tests) before wiring any of the untested modules.**

## 4. Data on disk

| Where | What | Notes |
|---|---|---|
| `data/telemetry/nasa_aces/` (1.9 GB) + `Dataset/` (1.3 GB tarballs) | NASA ACES, Rotax 914 on the Altus II | Real flight; EGT binding to fix |
| `data/telemetry/*.csv`, `train/val/test` | Generator output used for the RF | Circular |
| `Datasets/` | Public datasets from `Datasets/download_all.py`; `MANIFEST.json` holds SHA-256 + licence | Status: [`../audit/12_dataset_implementation.md`](../audit/12_dataset_implementation.md) §2. Zenodo items (marine, ROAD, MIMII) blocked by rate filtering — retry with `--only marine,road --connections 1` |
| `docs/reference/` | Rotax 914 installation and operator's manuals; MIL-STD-1629A | Source of `MANUAL` provenance |
| `vendor/PrognosticsMetricsLibrary/` | NASA MATLAB library (ported) | — |
| `mk-jev-fly-brain/` (gitignored) | Model Kombat clone | Method reference only (D13) |
| `competitors/` | 23 competitor repos cloned | See `docs/audit/01`, `05` |

## 5. Environment facts (for agents running commands)

- Windows 11. Shells: Git Bash and PowerShell 5.1. Python 3.12. Repository on `E:` (≈ 380 GB free).
- Blender: `E:\Blender\blender.exe` (headless `--background` works). UnRAR: `C:\Program Files\WinRAR\UnRAR.exe`.
- Backend: `uvicorn backend.server.main:app --host 0.0.0.0 --port 8000` (`launch_backend_server.bat`). Frontend: `launch_web_dashboard.bat` (Vite, in `frontend/`). Tests: `pytest`.
- **Network:** each connection to foreign hosts is throttled (~5–20 KB/s), while the aggregate line is ~800 KB/s. Use many parallel ranged connections (the downloader does this). **Zenodo blocks parallel traffic**: use a single connection.
- SocketCAN `vcan` needs Linux (WSL2 or CI on Ubuntu). On Windows, use python-can's `virtual` interface.
- Git LFS tracks large binaries (`.blend`, `.rar`, `.stp`, `.exe`). `Datasets/` content is gitignored except scripts and READMEs.

## 6. Build status snapshot (24 Sep 2026, after the S0-S4 slices)

| Area | State |
|---|---|
| Tests | 275 pass, 1 strict xfail (`exposure` brownout counting) |
| `backend/detect/` | calibration + FlyBloom/Mahalanobis/max-z + conformal thresholds + persistence gate + reservoir (tier-1) |
| `backend/runtime/` | EngineRuntime, RuntimeHub (all engines concurrent, heavy tier for the selected engine), fault registry, lever dynamics |
| `backend/server/engine_api.py` | `/api/engines`, `/api/engines/{id}/{state,faults,levers}`, `/ws/engines/{id}`, `/ws/fleet` (lazy hub; legacy routes unchanged) |
| `backend/edge/node.py`, `backend/sources/recorder.py` | gated downlink accounting (Pi 5 EMULATED), record/replay with hash manifest |
| Evidence | E17 (re-run on class-aware plant), E19, E20 - all SIMULATION |
| Not started | frontend F1-F10 (FRONTEND_SPEC), waveform channel (W5/W6), Jev bake-off (W10), real Pi 5 benchmark, ReplaySource for ACES/Parquet, MAVLink source |
| Legacy still live | `engine_service` singleton and old `/ws/telemetry` (the UI still uses them) - retire after frontend F1-F3 |
