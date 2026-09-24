# Universality & Freshness Audit — Is This One Engine's Simulator, or a Platform?

*Audit date 24 September 2026. Every number below was measured from the repository (grep counts, file timestamps, JSON contents), not estimated. Companion to `SUPERSEDED_VS_CURRENT.md` (duplicate implementations) — this file is about **single-engine hardcoding** and **stale artifacts**. Enforcement: `tests/test_engine_agnostic_ratchet.py`. Checklist for future work: `VERIFICATION_CHECKLIST.md`.*

> **Follow-ups (24 Sep):** the runtime design that consumes the profile is in [`MULTI_ENGINE_ARCHITECTURE.md`](MULTI_ENGINE_ARCHITECTURE.md); the detector decision in [`DETECTOR_DECISION.md`](DETECTOR_DECISION.md); a further finding - **the plant itself is Rotax-shaped** (F21: shared rpm map, SI-style EGT) - adds backlog item **R6**; and the Rotax blend is one 912i base plus 914/915 *fitting sets* (variants), see ARCH s8.

## 1. The question, and the honest answer

> "Are we using code that is engine-specific enough to make this look like a simulation of one engine? We need one codebase where selecting an engine from a dropdown drives everything."

**Answer: yes, today it is a Rotax 912 iS simulator with engine configs sitting beside it.** There is **no engine-selection path at all** — no API endpoint, no service parameter, no UI control (grep of `backend/server`, `frontend/src`, `apps` finds no use of `engine_id`, `load_engine_config` or `available_engines`; the only "engine_id" hits are Blender's *render* engine). The five engine configs exist and are read by the plant, the turbo model and the tests — but the twin, the live pipeline, the validators, the RUL model, the fault list, the copilot and the UI ignore them.

## 2. Evidence (measured)

Counted by `tests/test_engine_agnostic_ratchet.py` over 19 modules that *should* be engine-agnostic:

| Kind | Count | Meaning |
|---|---|---|
| `cyl` — fixed cylinder-index channel names (`CHT_1..4`, `EGT_1..4`) | **286** | The data model assumes exactly four cylinders. A 6-cylinder diesel (the 3500-DEFault engine) or a 2-cylinder engine cannot be represented. |
| `brand` — the words Rotax / Austro / AE300 | **78** | Prose and logic naming one manufacturer. |
| `model` — the numbers 912 / 914 / 915 | **37** | A specific engine model baked into logic. |

Worst offenders (count of all three kinds): `physics/sensor_validator.py` 72 · `telemetry/can_streamer.py` 69 · `physics/thermo_model.py` 61 · `ml/detection_pipeline.py` 33 · `server/engine_service.py` 32 · `agent/diagnostic_agent.py` 25 · `ml/fault_classifier.py` 24 · `PropulsionEngineerPanel.tsx` 22 · `agent/copilot.py` 20.

### The specific couplings, by layer

| Layer | Hardcoding found | Where |
|---|---|---|
| **Data model** | `EnginePhysicalState` has literal fields `CHT_1..CHT_4`, `EGT_1..EGT_4`. Cylinder count, firing order, ignition mode, turbo presence cannot vary. | `physics/thermo_model.py:37-44` |
| **Twin physics** | Rotax 912 iS constants at module level: bore 84, stroke 61, CR 10.8, gear 2.43, rpm limits 5800/5500/5000, displacement 1352. Ignores `engine_config`. | `physics/thermo_model.py:13-24` |
| **Alarm limits** | Redline literals inside the live pipeline: CHT > 135, EGT > 850, oil 2.0–5.5 bar, oil temp > 130, vib > 2.5, bus < 12. (Correct for a Rotax 912 family; wrong for a CI diesel, a Wankel, a different 12 V/28 V bus.) | `ml/detection_pipeline.py:468-478` |
| **Sensor validator** | Rate limits and noise floors tables keyed by the 4-cylinder channel names. | `physics/sensor_validator.py:28-63` |
| **Fault list** | 8 faults, each pinned to one cylinder ("fault 1 = cylinder 2 overheat") and to a **912 iS CAD mesh name** (`Rotax_912i_Base_M_PlasticGreen_0`, `Gearbox_Type_2_M_Steel_0`…). | `telemetry/can_streamer.py`, `DRDO_FAULT_DEFINITIONS` |
| **RUL model** | Six hardcoded component names/lifetimes (`Ignition_Harness_Coils: 400 h`…). A diesel has no ignition harness; a turboprop has no cylinder head. | `ml/rul_estimator.py:41-46` |
| **ML models** | Trained on the 912 iS generator only; feature names are 4-cylinder residuals. | `scripts/train_ml_models.py` → `backend/ml/models/*` |
| **UI** | Panels reference `CHT_1..4`, `EGT_1..4` and cylinder labels directly. | `ReadingsPanel.tsx`, `PropulsionEngineerPanel.tsx`, `CalculationsPanel.tsx` |
| **Copilot/agent** | Rotax-specific ATA directives and prompt text. | `agent/diagnostic_agent.py`, `agent/copilot.py` |
| **Class names** | `RotaxThermoModel`, `RotaxFaultClassifier`, `RotaxTimeSeriesGenerator`. | (naming smell — cosmetic but visible to a reviewer) |

**Would a reviewer read it as "a simulation of one engine"?** Yes. Two of the five configs could never run through the twin; switching engine is impossible; the demo's fault list is literally named after one engine's parts.

## 3. Where the universal mechanism *already* half-exists (reuse it, don't reinvent)

1. **`configs/engines/*.json` + `physics/engine_config.py`** — engine class as configuration (layout, ignition mode, induction, ratings, per-field provenance). `applicable_fault_modes()` already derives the fault list from the engine's own architecture. **Physics side of the profile: exists.**
2. **`assets/manifests/engines/*.json`** — per-engine 3D manifest: `class` (cycle/aspiration/cooling/layout), `components` (with inspect poses), `sensors` (channel → component → mesh objects), `faults` (fault → affected components → telemetry effect), `cameras`. **Presentation/component side of the profile: exists for two engines, disconnected from the backend.**
3. **`assets/manifests/platforms/`** — an airframe-level manifest (`bayraktar_tb3.json`). **Platform layer: a seed exists.**

**Defects in that seed that must be fixed before joining them:**

| Defect | Detail |
|---|---|
| **Engine IDs don't match** | Physics configs: `rotax_912is, rotax_914, rotax_915is, austro_ae300, vrde_jayem_2_2l`. Asset manifests: `austro_ae330, tei_pd170`. `austro_ae330 ≠ austro_ae300` and `tei_pd170` (a Turkish CI engine on MALE UAVs) has **no physics config**. No engine has both halves. |
| **Manifest schemas differ between engines** | `faults` is a dict in one manifest and a list in the other; `sensors` shapes differ. Not machine-joinable as-is. |
| **Asset trees are 1.6 GB** | `.blend` + `.blend1` backups for two engines; none for the engines the physics/ML side actually uses (Rotax 912/914/915, VRDE). |

## 4. Target design: the `EngineProfile` (one selection → everything derives)

**Principle (decision D27):** nothing in inference, twin, service or UI may name an engine, a cylinder index, or a redline. Everything is derived from the **selected profile**.

```
          ┌────────────── EngineProfile  (loaded by engine_id) ──────────────┐
 dropdown │ physics   ← configs/engines/<id>.json   (layout, class, ratings)  │
 (UI) ──► │ limits    ← config.operating_limits   (redlines, WITH provenance) │
 GET      │ channels  ← derived: n_cyl, has_turbo, is_CI  → channel registry  │
 /api/    │ faults    ← derived: applicable_fault_modes() ∩ FMECA (mode×loc)  │
 engines  │ components← config/manifest: subsystem graph → RUL components     │
 POST     │ assets    ← assets/manifests/engines/<id>.json (3D, sensors→mesh) │
 /api/    │ models    ← model registry keyed by (engine_class, n_cyl) + date  │
 engine/  │ provenance← per-field PUBLIC/MANUAL/ASSUMED/PLACEHOLDER           │
 select   └───────────────────────────────────────────────────────────────────┘
                     │ rebuilds ▼
   Pipeline(profile) → twin(profile) → detectors(profile) → RUL(profile) → UI schema(profile)
```

### Hook points (what each layer must read from the profile)

| Layer | Replace this | With this (from the profile) |
|---|---|---|
| Data model | `CHT_1..4` fields | `Frame.cht: List[float]` sized by `profile.n_cyl` (already done in `core/frame.py`) |
| Twin | module constants in `thermo_model.py` | dynamic model built from `profile.physics` (backlog B4.1) |
| Limits | literals in `detection_pipeline.py` | `profile.operating_limits[channel] = {caution, warning, source, provenance}` (schema addition; `threshold_baseline.py` already carries per-limit provenance for the 914 — generalise it) |
| Sensor validator | 4-cyl tables | limits/rates generated per channel from the registry |
| Faults | `DRDO_FAULT_DEFINITIONS` | FMECA mode × location, filtered by `applicable_fault_modes()`; mesh/component mapping from the asset manifest |
| RUL | six hardcoded components | component list from the manifest/config subsystem graph; lifetimes from `tbo_hours` + physics-of-failure |
| ML | one RF/AE on 912 iS | per-class models trained on plant Monte Carlo across several profiles; evaluated leave-one-engine-out (§6) |
| UI | literal channels | render from `GET /api/engines/{id}/schema` (channel list, cylinder count, units, limits) |
| Copilot | Rotax ATA text | retrieval over the selected engine's manuals; templates parameterised by profile |

### API (proposed; nothing exists yet)

`GET /api/engines` → list `{engine_id, display_name, class, n_cyl, provenance_summary}` · `GET /api/engines/{id}/schema` → channels, units, limits, fault modes, components · `POST /api/engine/select {engine_id, tail_id}` → rebuilds the pipeline; returns the new schema · `GET /api/engine/active`.

## 5. How universal is "universal"? (scope honesty)

| Scope | Feasible? | Notes |
|---|---|---|
| **All piston engines** (SI/CI, NA/turbo, boxer/inline/V, 2–8 cylinders) | **Yes — this is the PS scope and the achievable target.** | One physics/estimation framework parameterised by profile. |
| Rotary (Wankel, e.g. Hermes 450's UEL R902W) | Partially | Needs a different combustion/crank model behind the same interface; profile flag `cycle: rotary`. |
| Turboprop/turbofan MALE engines (PT6, TPE331…) | **Out of PS scope; interface-compatible later** | Requires a gas-path model. Keep an `EnginePhysics` protocol so a turbine implementation can plug in; do not claim it now. |
| Airframe/avionics/other subsystems | Seed exists (`platforms/`) | Battery, alternator, FADEC are already in scope of the PS (HMS-10). |

**Universal architecture ≠ universal accuracy.** Each engine still needs its own calibration and its own evidence. The honest claim is: *"the same code runs any engine that has a validated profile, and we show cross-engine generalisation with a leave-one-engine-out test"* — not *"it works on any engine."* Don't let a demo imply the second.

## 6. What the datasets make possible for universality (beneficial next uses)

| Dataset (on disk) | What it adds to the universality story | How to use it |
|---|---|---|
| **3500-DEFault** (6-cyl diesel, per-cylinder fault labels) | A real **non-4-cylinder, compression-ignition** engine — the direct test that `n_cyl` and `is_CI` are truly parameters | Add a `diesel_6cyl_proxy` profile; run the whole detector stack on it; report per-cylinder localisation with n=6 |
| **ACES** (Rotax 914, real flight) | Real anchor for one profile | Replay through `ReplaySource` with the 914 profile; false-alarm rate on real healthy hours |
| **Marine diesel** (after download) | A second real CI engine | Cross-engine transfer: train on one, test on the other |
| **CWRU / Paderborn** | Engine-agnostic DSP (bearings exist on every engine) | Validates the angle/order machinery independent of engine type |
| **C-MAPSS / N-CMAPSS** | A different **engine class (turbofan)** with 4 operating regimes | Proves the *prognostics/federation* layer is class-agnostic; do **not** use it to claim piston physics |
| **ALFA** | Airframe-level UAV faults | Seed for the platform layer |
| **NASA battery** | A generic electrical subsystem | Battery SOH plug-in usable on any platform |

**Recommended universality experiment (E16):** *leave-one-engine-out.* Generate plant Monte Carlo data for profiles {912iS, 914, 915iS, AE300, VRDE-class, 6-cyl diesel proxy}; train on five, test on the sixth; compare against a model trained on the sixth. The gap is the honest cost of universality, and reporting it is a stronger claim than any "works on all engines" slogan.

## 7. Freshness audit — models, datasets, artifacts (measured 24 Sep)

| Artifact | Date / source | Status | Action |
|---|---|---|---|
| `backend/ml/models/rotax_random_forest.joblib` (+ `model_metrics.json`) | **2 Sep 2026**; trained on `RotaxTimeSeriesGenerator` (912 iS, circular twin-based generator) | **STALE** — pre-dates ACES, the 914/915/VRDE configs, the independent plant, FMECA. 97.5 % is self-agreement (D04). 8 fault classes fixed to 4 cylinders. | Keep only as a bake-off contender (E06); replace via E12/U8 |
| `backend/ml/models/rotax_autoencoder.json` | 2 Sep 2026; same generator | **STALE** (66.5 % fault recall) | Contender only |
| `data/telemetry/rotax912_{train,val,test}_dataset.csv`, `train/ val/ test/` copies | Generator output, 912 iS, 10 missions × 900 samples per split | **STALE + circular**; `train/ val/ test/` folders appear to duplicate the `rotax912_*_dataset.csv` files (same sizes; not byte-compared) | Archive; regenerate from the plant per profile |
| `data/telemetry/rotax912_dataset_manifest.json` | Contains **absolute paths from another machine** (`E:\TalentForge\Clay\3d_engine\…`) | **BROKEN provenance** | Regenerate with repo-relative paths |
| `data/telemetry/nasa_aces/` (1.9 GB) + `Dataset/` (1.3 GB tarballs) | Real Rotax 914 flights | **CURRENT** data; tarballs are duplicates of extracted files | Keep extracted; delete tarballs after hashing |
| `Datasets/` (41 GB) | Downloaded 23 Sep | **CURRENT, unused** (no loaders — backlog E7) | Wire via E7; delete N-CMAPSS if unused |
| `vendor/Qwen3-4B` (7.6 GB) | Pre-B0.2 | **VESTIGIAL** — LLM is disabled by default now | Move out of the repo or delete |
| `configs/engines/*.json` | 23–24 Sep, provenance-labelled | **CURRENT** | Extend with `operating_limits` |
| `assets/manifests/engines/*.json`, `assets/models/engines/*.blend*` | AE330, PD170; `.blend1` backups | **CURRENT-ish but disconnected** (ID mismatch) | Reconcile IDs; drop backups |
| `assets/blender/rotax_912_is_sport.blend` (78 MB) + canyon/terrain | Original demo assets | Current for the 912 iS only | Keep as one profile's asset |
| `competitors/` (892 MB) | Reference clones | Reference only, not our code | Exclude from the repo/CI |
| `report_dump/mission_*`, `data/telemetry/live_sorties/*.csv` | Runtime output | Ephemeral | gitignore (B0.6) |

**Rule going forward (decision D28):** every model or dataset artifact must carry a sidecar recording *what generated it, with which engine profile(s), on what date, from which git commit, and how it was evaluated*; anything without that is treated as untrusted until regenerated.

## 8. Work this creates (added to `BACKLOG.md` as tier E12)

| ID | Task | Depends |
|---|---|---|
| U1 | `EngineProfile` loader unifying `configs/engines/<id>.json` + `assets/manifests/engines/<id>.json`; reconcile IDs (`austro_ae330` vs `austro_ae300`; add a `tei_pd170` physics config) and manifest schemas | B0.4 |
| U2 | Channel registry derived from `n_cyl`/`is_CI`/`has_turbo`; retire `CHT_1..4` fields (start with `Frame`, then adapters) | B1.1 |
| U3 | `operating_limits` in the config schema **with provenance**; remove redline literals from `detection_pipeline.py` and the sensor validator | U1 |
| U4 | Engine API (`/api/engines`, `/api/engines/{id}/schema`, `POST /api/engine/select`) + pipeline rebuild on select | U1, B1.4 |
| U5 | UI renders channels/cylinders/limits from the schema; dropdown in the header | U4 |
| U6 | Fault list = FMECA mode × location filtered by the profile; component/mesh mapping from the manifest (replaces `DRDO_FAULT_DEFINITIONS`) | U1, B5.3 |
| U7 | RUL component graph from the profile (replaces the six hardcoded components) | U1, B6.1 |
| U8 | Model registry with sidecars (D28); retrain on multi-profile plant Monte Carlo; rename `Rotax*` classes | B1.7 |
| U9 | E16 leave-one-engine-out experiment; add a 6-cylinder diesel proxy profile from 3500-DEFault | U8, B7.1 |
| U10 | Ratchet to zero: lower `tests/engine_agnostic_baseline.json` as each module is refactored | continuous |
