# ANUMAAN Repository Mental Model

*Verified against this checkout on 27 September 2026. This replaces older snapshots that described a one-engine-only UI, no multi-engine runtime, and no high-rate waveform code. Those descriptions became stale as code landed. Read this file together with `CURRENT_STATE.md`, `BACKLOG.md`, and `IMPLEMENTATION_LOG.md`.*

## 1. Mission and product claim

The project responds to SIH/DRDO PS-26054: an AI-enabled digital twin for predictive health monitoring and mission reliability of aero piston engines used in MALE UAVs. The demonstrable product should let a ground operator inspect a fleet, select an engine, see evidence behind an anomaly, investigate affected channels/components, and explore a controlled what-if scenario. Its strongest honest current pitch is **a multi-profile simulated propulsion health-monitoring prototype with per-tail residual anomaly detection, profile-valid fault injection, and an experimental selected-engine reservoir classifier**. It is not yet an aircraft-connected predictive-maintenance system: it has no live aircraft data adapter in the main UI, no surfaced/calibrated RUL or mission-completion probability, and no connected full-rate waveform diagnostic path.

The PS is the outcome target, not proof that each capability is implemented. Start at [`docs/00_official_problem_statement.md`](../00_official_problem_statement.md); trace specific requirements through [`docs/fun_req.md`](../fun_req.md). Do not pitch the entire research stack as live product behavior.

## 2. Runtime map: two concurrent pipelines

The backend currently exposes two genuinely distinct service paths. Treat them as separate until a deliberate migration joins them.

### A. Modern multi-engine health runtime — default React operator view

`backend/server/main.py` mounts `backend/server/engine_api.py`. The new router lazily constructs `RuntimeHub`; its background boot calibrates one `EngineRuntime` for every config under `configs/engines/`, selects the initial engine, then starts the hub at 20 wall-clock ticks/second. Each ready runtime owns its own `PlantSource`, levers, sensor levers, frame buffer, residual detector and optional reservoir. Each tick advances **one simulated second**, so the clock is accelerated roughly 20× relative to wall time.

The path is:

```text
engine config → PlantSource/VirtualEngine → Frame + isolated TruthRecord
             → per-tail ResidualDetector (tier 0) → optional selected-engine Reservoir (tier 1)
             → /api/engines + /ws/fleet + /ws/engines/{id}
             → React EngineRuntimeConsole
```

`Frame` is the observation contract and excludes fault labels/RUL; `TruthRecord` is simulator/evaluation metadata and is not included in public frame payloads. Tier 0 exposes detector scores, ratios, alarms and leading channels. Tier 1 is warmed on selection and classifies against a simulated training fault library. Read `backend/runtime/engine_runtime.py`, `backend/runtime/hub.py`, `backend/runtime/registry.py`, `backend/detect/`, `backend/sources/plant_source.py`, and `backend/core/frame.py` for implementation truth.

API details: `GET /api/engines` lists engine profiles/readiness/valid faults; `GET /api/engines/{id}/state` returns the latest frame; `GET /api/engines/{id}/schema` returns channel/limit/component/provenance schema; `POST /api/engines/select` selects and warms tier 1; `POST`/`DELETE /api/engines/{id}/faults` injects/clears a profile-valid plant fault; `POST /api/engines/{id}/levers` sets throttle/altitude/OAT targets; `/ws/fleet` and `/ws/engines/{id}` stream live state.

**Limits that matter to the UI:**

- Every current engine frame reports evidence class `SIMULATION`; fleet colors are detector state, not certified airworthiness judgments.
- `EngineRuntime.ensure_heavy()` creates `Reservoir.random(...)`; this is a randomized reservoir readout, **not** the connectome/fly-brain model. E19 tests real connectome vs shuffled/random controls and does not establish a connectome advantage. FlyHash is a separate novelty scorer.
- The selector's tier-1 label is a candidate class from simulated training scenarios, not an independently confirmed root-cause diagnosis.
- The registry has 12 physical/sensor fault modes, filtered for engine applicability. Some are marked waveform-only because the low-rate scalar path cannot observe them. Injection availability does not mean detection capability.
- Tier-0 is anomaly detection; the modern payload does not provide RUL, mission reliability, causal diagnosis, an evidence-calibrated health index, or maintenance work orders. Do not synthesize these in the frontend.
- The current React console now consumes this API by default. The 3D three.js page is a separate surface: Rotax 912 uses the legacy route; other engines use modern runtime endpoints. Keep this distinction visible when debugging discrepancies.

### B. Legacy Rotax ground-control stack — retained compatibility workspace

`backend/server/main.py` also starts `EngineStateService` during FastAPI lifespan. That path uses the singleton legacy state, `TelemetryStreamer`, the legacy detection/RUL/agent services, `/api/state`, `/api/control`, and `/ws/telemetry` (also used by legacy React screens and older Blender clients). Its synthetic telemetry and heuristics have different state, fault identifiers, outputs, and assumptions from the modern runtime. The “Legacy GCS” switch keeps existing React role views intact while the modern operator console becomes the default.

Do not assume selecting an engine in the modern UI changes the legacy engine, or that a legacy diagnosis corresponds to a modern detector result. A later migration should retire/alias old routes only after each retained panel has a clear modern data source.

## 3. Data and research layers

The repository contains more code than the running product. Classify capabilities by actual call path, not folder names or the implementation log's ✅ marks:

| Layer | Examples | Current relationship to default UI |
|---|---|---|
| Modern live simulated path | `runtime/`, `detect/`, `engine_api.py`, `sources/plant_source.py` | Used for selected-engine console/fleet/faults/levers |
| Legacy live path | `engine_service.py`, `telemetry/can_streamer.py`, `ml/detection_pipeline.py`, `ml/rul_estimator.py`, agent/voice/replay | Used by Legacy GCS and legacy APIs; not interchangeable with modern outputs |
| Separate/tested capability packages | `twin/`, `diagnose/`, `prognose/`, `alarms/`, `fadec_emulator/`, `link/`, `security/`, `federation/`, `maintenance/`, `economics/`, `performance/`, `foundation/` | Tests/evaluation and some internal integrations exist; generally not invoked by the modern HTTP/WebSocket path or default UI |
| High-rate acquisition/simulation | `core/cycle_block.py`, `plant/sensors_hr.py`, `sources/waveform.py` | Code and waveform-stack tests exist; this feed is separate from the current 20 Hz engine API and is not yet a live frontend detector input |
| Experiments/evidence | `experiments/`, `docs/evaluation/E*.json`, `docs/study/`, `docs/audit/` | Simulation/research results, useful for qualified evidence; not a live operational capability |
| Assets/showcases | `assets/`, `apps/threejs_twin/`, Blender apps, renders | Visual/product material; meshes, renders and a visualization do not imply a sensor-to-diagnosis connection |

**Dataset loaders need special care.** The adapters `backend/datasets/aces.py`, `alfa.py`, `cwru.py`, `cmapss.py`, and `battery.py` synthesize records with Python/NumPy rather than parsing the named public data files. Some manifests currently label those outputs `REAL_FLIGHT`/`PUBLIC_PROXY`, which overstates provenance. `telemetry/aces_loader.py` is a separate raw ACES `.mat` parser with a documented unit-scale caveat; neither it nor the named dataset directories are evidence that the generic adapters load real data. Until these adapters actually parse and validate source files, describe their output as synthetic demonstrations and keep their claims out of evaluation/pitch.

## 4. Fault and visualization mental model

There are three taxonomies with different purposes: PS-26054's eight broad requirement categories; legacy Rotax demo fault IDs; and modern registry modes in `backend/runtime/registry.py`. Do not map one to another by numeric position. In the modern flow, a fault mode is filtered by the selected engine's physical properties, may require a cylinder, drives the plant injector, and is tagged as a manual operator action. The detector only sees `Frame`; truth remains evaluation-side. For a visualization, show (1) the injected component/location only when the registry/asset map supports it, (2) observed residual evidence, and (3) detector confidence/gating as separate concepts. Do not glow a part solely because the operator selected a fault; that would depict the command as a diagnosis. Waveform-only faults must remain explicitly unobservable in scalar-only views.

The three.js engine is a presentation layer, not a separate source of physics. Verify its fault-to-component map and stream selection independently from the React path. For the Rotax injector-clog demo, the GLB has no separable injector mesh: three.js uses its documented orange location marker, and the legacy API now reports `INJECTOR_1_LOCATOR` instead of pretending the entire engine body is the injector. Other faults should highlight only validated meshes. For smooth transitions, camera movement should be eased/interpolated and robust to rapid selection changes; visualization must not block live telemetry.

## 5. User experience and honest demo story

The first five seconds should answer: which engine is selected, is telemetry arriving, what evidence is abnormal, and how does the operator reproduce/investigate it? The default screen now provides fleet tiles, selected engine, scalar telemetry, tier-0 threshold ratios and gate status, tier-1 candidate scores when warm, profile-valid scenario controls, and a manual-action marker. This is the defensible live story.

Next highest-value slices, in order:

1. Profile/schema-driven channel labels and units; live residual history/trends; stale/disconnected/calibrating states and API error visibility.
2. A diagnosis endpoint that consumes modern frames and returns ranked hypotheses with evidence/ambiguity; never present reservoir output as final diagnosis.
3. Wire tested twin/prognostics/mission modules into the same modern frame lifecycle with characterization and integration tests, then show uncertainty/provenance.
4. Connect waveform `CycleBlock` acquisition, recording/replay, DSP/detector, and UI; until then waveform-only modes are scenario demonstrations, not detected faults.
5. Fix dataset adapters and evidence provenance; parse real files with unit/engine mapping and split-by-unit evaluation before claiming external validation.
6. Add component/mesh traceability so React diagnosis and three.js orange/glow highlighting share an explicit manifest mapping.
7. Bridge a real source (MAVLink/EFI/CAN) behind the existing `Frame` seam, then validate timing, data quality, security, and failure states on hardware.

Pitch current prototype as a **simulation-backed, multi-engine condition-monitoring demonstrator** that exposes its residual evidence and allows reproducible operator scenarios. Pitch as future roadmap: validated aircraft integration, waveform diagnosis, explainable fault isolation, calibrated prognostics, mission reliability and maintenance recommendations. Do not claim those future functions are in the live frontend today.

## 6. Working rules / authoritative files

- [`CURRENT_STATE.md`](CURRENT_STATE.md) is the current reachability and implementation snapshot; old reachability tables elsewhere are historical unless refreshed.
- [`BACKLOG.md`](BACKLOG.md) tracks remaining accepted work; update it when a slice ships.
- [`IMPLEMENTATION_LOG.md`](../IMPLEMENTATION_LOG.md) records what changed, what was verified, and what remains unproven.
- [`INTERFACES.md`](INTERFACES.md), [`DECISIONS.md`](DECISIONS.md), [`SUPERSEDED_VS_CURRENT.md`](SUPERSEDED_VS_CURRENT.md), [`MULTI_ENGINE_ARCHITECTURE.md`](MULTI_ENGINE_ARCHITECTURE.md), [`DETECTOR_DECISION.md`](DETECTOR_DECISION.md) are useful design references, but check claims against code and recent commits because several were written before the modern runtime/UI landed.
- `docs/00_official_problem_statement.md` is the official scope. `docs/audit/`, `docs/study/`, `docs/evaluation/`, and competitors are support material, not runtime truth.
- Large `assets/`, renders, datasets, archives, scratch directories and local config are not automatically deliverables. Inspect Git tracking and `.gitattributes` before staging; preserve user-owned/untracked artifacts.
- Run the relevant frontend build, targeted backend integration checks, and live local browser smoke after UI/API changes. Do not claim verified until both the build and the relevant user flow have been exercised.
