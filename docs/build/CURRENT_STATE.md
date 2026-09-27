# Current Implementation State

*Verified 27 September 2026 against the checked-out source. This file supersedes the 24 September reachability snapshot below it in Git history; the older one incorrectly said the app was one-engine-only and the newer backend stack was not in the service.*

## User-facing product today

The React app in `frontend/` now defaults to `EngineRuntimeConsole`. It connects to the newer multi-engine engine API, shows fleet telemetry, lets the operator select a profile, displays tier-0 residual score/threshold ratios and persistence alarm state, shows the selected engine's tier-1 reservoir scores when available, renders incoming profile channels, and posts profile-valid fault and flight-condition commands. Its **3D twin** view embeds the existing component highlight and camera presentation. Evidence and manual scenario state are labeled. Existing role-based views remain accessible using **Legacy GCS** and still use the old `/api/state`, `/api/control`, and `/ws/telemetry` path.

The page is a simulation demonstrator. The modern runtime payload currently reports `SIMULATION`; do not call its alarm airworthiness-certified or its reservoir label a confirmed diagnosis. It does not surface RUL, mission reliability, Bayesian diagnosis, maintenance work packages, or real aircraft measurements.

## Active server paths

`backend/server/main.py` includes `backend/server/engine_api.py` and also starts `EngineStateService` in the server lifespan. These are parallel APIs, not a single unified state machine.

| Path | Code | Used by | State |
|---|---|---|---|
| Multi-engine runtime | `RuntimeHub` → per-profile `EngineRuntime` → `PlantSource`/`VirtualEngine` → `Frame`/`ResidualDetector` → optional `Reservoir` | Default React console, modern 3D twin for non-912 profiles | Live, synthetic, 20 ticks/s wall time; each tick advances 1 simulated second; all five configs calibrate independently; tier 1 warms for selected engine |
| Legacy Rotax runtime | `EngineStateService` → `TelemetryStreamer` → legacy detection/RUL/diagnostics | React Legacy GCS, old API clients, Rotax three.js feed, Blender consumers | Live, separate singleton; Rotax 912-shaped synthetic model and legacy fault/result semantics |
| High-rate waveform path | `CycleBlock`, `sensors_hr.py`, `WaveformSource`/`WaveformRecorder` | waveform stack tests / experimental recording | Implemented and tested as code, but not connected to either live engine API or the React console |

Modern endpoints include `GET /api/engines`, `POST /api/engines/select`, `GET /api/engines/{id}/state`, `/schema`, `POST`/`DELETE /api/engines/{id}/faults`, `POST /api/engines/{id}/levers`, `WS /ws/engines/{id}`, and `WS /ws/fleet`. `Frame` is observable telemetry; `TruthRecord` stays simulator/evaluation-side. The five current profiles are Rotax 912 iS, 914, 915 iS, Austro AE300, and VRDE/JAYEM 2.2 L. AE300's visualization may use an AE330-labeled proxy asset; inspect its manifest before presenting as the same model.

## Detector and fault behavior

- Tier 0 (`backend/detect/ResidualDetector`) calibrates on simulated per-tail nominal frames and reports novelty/statistical scores, threshold ratios, raw alarm, persistence-confirmed alarm and leading channels.
- Tier 1 (`backend/detect/Reservoir`) is created using `Reservoir.random` and trained on simulated fault sequences only for the selected engine. It is a reservoir classifier, not the E19 connectome or an established production classifier.
- The 12-mode fault registry filters applicability per engine. It distinguishes physical vs sensor layer, cylinder specificity and scalar visibility. Some CI/turbo faults are waveform-only; because the waveform path is not live, injection currently cannot imply an observed/detected defect in the frontend.
- Eight PS categories, eight legacy demo IDs, and modern registry mode names are separate taxonomies. Numeric IDs must not be mapped by array index.
- Legacy fault 2 (Rotax injector clog) has no standalone injector mesh in its asset. Its live target is the `INJECTOR_1_LOCATOR` reference, not an inaccurate whole-engine highlight; the three.js view places that marker at the documented component location.

## Modules that exist but are not a connected live feature

The repository has tested and/or evaluated packages for the twin/UKF/degradation, Bayesian diagnosis and active testing, dual-path prognostics, alarm rationalization, FADEC emulation, edge/link, security, federation, maintenance, economics, performance, and foundation models. E21–E25 artifacts and other experiments are simulation evidence. Existence, tests, or a harness result does not mean the new multi-engine API calls the module, nor that the user sees it. Trace reachability before surfacing anything. `backend/agent/` and voice remain optional legacy-side functions.

The dataset adapters for ACES, ALFA, CWRU, C-MAPSS and NASA battery previously generated illustrative records while advertising public/real data provenance. They have been corrected to mark their output `SIMULATION` and disclose that the raw source files are not parsed. `backend/telemetry/aces_loader.py` is a distinct `.mat` parser; its raw ACES channel unit-scale caveat remains. Downloaded datasets on disk are still not validated ingestion.

## Frontend remaining work

The first end-to-end modern operator slice is connected. Remaining to reach the intended prototype pitch:

1. Render channel units/limits and cylinder layout from `/schema`; add a bounded residual trend and visible stale-age/calibration/reconnect states.
2. Give the API a ranked diagnosis response with supporting channels and uncertainty before calling a fault label a diagnosis.
3. Connect diagnosis/twin/prognostics/mission outputs through one tested runtime lifecycle; show calibration and evidence class alongside uncertainty.
4. Connect waveform source → recorder/replay → DSP/features → detector → API/UI; only then offer meaningful waveform-only fault detection.
5. Implement real dataset parsing/mapping and split-by-unit validation, with source, license, units and evidence provenance auditable in UI.
6. Finish explicit fault-to-component manifests and share the same evidence/location map with React and three.js; preserve eased camera transitions.
7. Implement aircraft/test-rig source adapters at the `Frame` boundary and validate on target hardware before implying deployment readiness.

## Verification and source-of-truth hierarchy

The frontend implementation should be verified with `npm run build` in `frontend/`, then a browser smoke on the connected backend: load fleet; switch each ready engine; confirm profile-valid fault options and channel changes; inject/clear a fault; apply levers; ensure disconnected/calibrating states remain clear. Run backend tests focused on API/runtime/dataset contracts and the full suite if the environment permits. Record actual results (not assumed counts) in `docs/IMPLEMENTATION_LOG.md`.

Use this snapshot for reachability, `MENTAL_MODEL.md` for architecture/claims, `BACKLOG.md` for work state, and the dated implementation log for changes/verification. Older audit, research and architecture documents may describe a prior code state; check their date and code references before repeating a status claim.
