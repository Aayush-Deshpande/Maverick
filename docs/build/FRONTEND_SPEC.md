# Frontend Specification — What the ANUMAAN Ground Console Must Show

*Target specification created 24 Sep 2026; implementation status reconciled 27 Sep 2026. The React app now defaults to `EngineRuntimeConsole` and consumes `/api/engines`, `/api/engines/{id}/schema`, `/ws/engines/{id}`, `/ws/fleet`, and modern fault/lever APIs. The six legacy role views remain under “Legacy GCS” and still consume the old single-engine `/ws/telemetry` path. See the status tracker below before treating any target screen as shipped.*

## 0. Implementation status (27 Sep 2026)

| Slice | Status | What is actually present |
|---|---|---|
| Engine selection / fleet strip | **Implemented** | Backend catalog and fleet stream power a five-profile tile strip and selector; selected engine controls the primary stream and warms tier 1 |
| Operator telemetry | **Implemented, first slice** | Modern frame channels, evidence class, profile metadata/schema units, max cylinder temperatures, detector ratios and persistence gate |
| Scenario controls | **Implemented, first slice** | Profile-filtered fault modes, cylinder choice, severity, clear, and throttle/altitude/OAT commands use modern backend routes |
| Tier 1 display | **Implemented with qualification** | Shows reservoir output when present, names it a simulated randomized reservoir classifier, not a connectome or confirmed diagnosis |
| 3D fault visualization | **Integrated view** | Existing three.js twin is available in the React console; Rotax uses the legacy stream and other profiles use modern runtime routes |
| Legacy role views | **Retained** | Operator/propulsion/maintenance/AI/voice/replay still run against legacy state; do not mix their results with the modern stream |
| Residual trends, schema limits, cylinder residual heat map | **Not implemented** | Target sections below; current UI shows raw scalar channels and score ratios |
| Bayesian root cause, calibrated RUL/mission probability, maintenance work package | **Not on modern live path** | Code/evaluation artifacts exist in separate packages, not connected to modern API/UI |
| Waveform detection / waveform replay | **Not on modern live path** | Source/recorder code and tests exist, but are disconnected from the live runtime and frontend |
| Edge evidence / research bake-off | **Not implemented in UI** | Simulation evaluation artifacts exist; no evidence dashboard yet |

## 1. Design principles (why it looks the way it does)

1. **Answer three questions in under five seconds:** *Is this engine healthy? What is wrong / going wrong? What do I do, and how sure are we?* Everything else is one click deeper.
2. **Evidence is visible.** Every value shows its **evidence class** (`SIMULATION` / `PUBLIC_PROXY` / `REAL_FLIGHT`) and every alarm shows *why* (top residual channels). No black-box red lights. This is the differentiator against cloud/black-box competitors and it is how DRDO reviewers trust it.
3. **Residuals, not raw numbers.** Raw CHT is meaningless across engines; the primary view is the calibrated z-residual per channel. Raw values are secondary.
4. **Engine-agnostic by construction.** Channel lists, cylinder counts, valid faults and limits come from the profile (`GET /api/engines`), never from constants in JSX. A 6-cylinder or diesel profile must render without code changes.
5. **Edge-first honesty.** Show what the edge sent (bytes, gate state) versus what a cloud design would have sent. Offline-capable: no CDN fonts/scripts, no external calls; runs on an air-gapped GCS laptop and a phone on the flight line.
6. **Operator actions are labelled.** Anything the user injects is flagged `MANUAL` and excluded from KPI panels (D30).
7. **Calm in nominal, loud only when confirmed.** Raw alarms are shown as a subtle tick; only persistence-gated (confirmed) alarms change the page state.

## 2. Global shell (always visible)

| Element | Content | Data |
|---|---|---|
| **Engine dropdown** (header, left) | All profiles from `/api/engines`: Rotax 912 iS, 914, 915 iS, Austro AE300, VRDE/JAYEM 2.2 L; badge per engine: ready, health colour, confirmed-alarm dot. Switch is instant (streams already live; selection warms tier-1 on the server, D29) | `GET /api/engines`, `WS /ws/fleet`, `POST /api/engines/select` |
| **Role tabs** | Operator · Propulsion engineer · Maintenance (keep existing three, D17 RBAC later) | local |
| **Link/edge strip** | Source (PLANT/REPLAY/MAVLINK), evidence class chip, tail id, edge profile (`Pi 5 — EMULATED` / measured), downlink bps vs raw waveform bps, latency p99 | payload + `EdgeNode.report()` |
| **Mode switch** | LIVE · REPLAY (scrub a recording, same pipeline at 1×, D05) · TEST-RIG (later) | recorder API (W3) |
| **Global banner** | Confirmed-alarm banner with engine, top 3 channels, gate state; dismiss = acknowledge (logged), never hides the underlying state | `detection.confirmed` |

## 3. Screens

### 3.1 Fleet view (landing) — "all engines at once"
Five engine tiles (from `/ws/fleet`): name, rpm, max CHT/EGT, health colour, confirmed/raw alarm, top residual channel, a 5-minute residual sparkline. Click a tile = select engine and open its console. Shows that all simulators/detectors run concurrently (D29) and gives the DRDO "fleet of tails" picture.

### 3.2 Operator console (selected engine) — the demo screen
1. **Health header:** verdict (GO / CAUTION / NO-GO from mission module), confidence, evidence chip.
2. **Cylinder ring** (n_cyl from profile): per-cylinder *residual heat map* (CHT/EGT z), firing-order animation, the misfiring cylinder visibly skipping (V1/V2). Falls back to a bar strip when n_cyl > 8.
3. **Residual bars** for scalar channels (oil p/t, fuel, MAP, rpm) with ±3σ envelope and the conformal threshold line.
4. **Detector strip:** the three tier-0 scores as ratio-to-threshold gauges (fly-bloom novelty, Mahalanobis, max|z|) — over 1.0 = raw alarm; persistence-gate meter (k of n).
5. **Tier-1 panel:** reservoir class scores (NOMINAL vs each profile-valid fault), labelled `selected engine only`, with a "not warmed" state while it trains.
6. **What-if levers** (Dronanetra-style sandbox, V9): throttle / altitude / OAT sliders POSTing to `/levers`; the plot shows the target (dashed) and the first-order response — makes lever dynamics (R3) visible.
7. **Fault panel:** only the profile-valid faults (`profile.faults`), per-cylinder picker when required, severity, ramp; waveform-only faults carry a badge "invisible to scalars — needs waveform channel (W6)". Injected faults appear in an "operator actions (MANUAL)" log.

### 3.3 Propulsion-engineer console (depth)
- **Order-spectrum waterfall** (angle domain, 0.5–24 orders) and per-cylinder work/IMEP chart when crank chain data is present (V3).
- **Trends:** residual history per channel with lead-time markers, RUL cone with P10/P50/P90 and the `calibrated: false` honesty label until B6.1 lands.
- **Detector internals:** calibration card (tail id, n frames, σ per channel, last calibration time, holdout FAR target α), threshold table, **score distributions vs nominal calibration** so reviewers can see the separation.
- **Sensor trust overlay** (V4): stuck/drift flags from the integrity monitor.
- **Twin vs plant**: observed vs model-expected trace with residual (Nirvanaa-style dual trace).

### 3.4 Maintenance crew view
Ranked action list (FMECA-grounded; optional Jev-style ranker, D37, always "advisory"), ATA chapter, affected components (mesh names from the asset manifest), one-click **component inspector** (V10: click a part → sensor id, value, health, specs, corrective action), sortie debrief export, case retrieval (F66 later).

### 3.5 Edge & evidence view (the "not a simulation toy" screen)
- **Edge accounting:** bytes sent vs raw scalar stream vs raw 51.2 kHz waveform (log-scale bar), heartbeat vs alarm packets, latency histogram, power assumption. Profile chip `EMULATED` until a Pi 5 measurement lands.
- **Claims table:** each headline number with evidence class, dataset, seed count, file link (from `docs/evaluation/*.json`) — e.g. E20 detection delays and false-alarm rates per engine.
- **Detector bake-off card:** RF vs fly-bloom vs reservoir vs Mahalanobis (E17/E19/E20) with the shuffled-connectome null shown, so the honesty is on screen.
- **Federated panel (W12):** colony merge — per-tail Bloom memories merged with no raw data leaving the tail; show detection with local vs merged memory.

### 3.6 3D digital twin (two surfaces, one data feed)
1. **Blender/desktop twin (existing):** `WS /ws/blender` continues to drive the Austro AE330 asset with fault colouring; add the per-cylinder residual heat and firing-order skip driven from the same payload (V1/V2). Selected engine swaps the loaded asset (Rotax/Austro).
2. **Web 3D (optional, later):** export the asset to glTF (LOD1) and render with three.js / react-three-fiber inside the console with mesh highlights from `top_channels`/component map. Only if time allows; Blender surface is the fidelity showcase, the web view is for phones.

## 4. Look and feel

- **Style:** dark, instrument-grade (existing Tailwind theme, `surface-panel` cards), high-contrast, colour used only for state (green nominal, amber raw alarm, red confirmed, grey unknown/stale). Colour-blind safe (shape + label with colour).
- **Type & density:** tabular figures for numbers, 12–14 px data text, no decorative animation except the physically meaningful ones (firing order, order waterfall).
- **States:** every panel must render `calibrating`, `stale (no frame > 3 s)`, `link lost`, `not applicable for this engine`, and `error` (existing `PanelErrorBoundary`) — the flight line is where demos die.
- **Responsive:** phone (GCS in the field) shows Fleet, health header, cylinder ring, alarm banner, levers; desktop shows everything.
- **Offline & security:** bundle fonts/icons locally; no telemetry to third parties; WS auth token and role gating before B9; never render any field the backend does not send (truth fields are structurally absent from payloads).

## 5. Technical plan

| Item | Decision |
|---|---|
| Stack | Keep React 18 + Vite + Tailwind. Add **uPlot** (tiny, fast time-series) for trends/spectra; optional **visx/d3** for the ring and order waterfall; no heavy chart suite |
| State | One `useEngineStream(engineId)` hook on `/ws/engines/{id}` + one `useFleet()` on `/ws/fleet`; a small store (zustand or context) keyed by engine id; 1–2 s ring buffers client-side for sparklines |
| Types | Generate TS types from the HealthFrame/payload schema (`INTERFACES.md`) — no hand-typed channel names; replace `EngineTelemetry` (CHT_1..4) with a profile-driven map |
| Compatibility | Old `/ws/telemetry` screens keep working (aliases to the default engine) until the new console reaches parity, then are removed (D05) |
| Tests | Vitest for hooks/reducers; **Playwright** smoke: dropdown switch < 100 ms shows new profile's faults; inject fault → banner within N ticks; fleet shows 5 tiles; offline build has no external requests |
| Performance | 20 Hz payloads throttled to 10 fps rendering; payload < 2 kB (channels + detection only) |

## 6. Build order (frontend slices, after backend R4)

| Slice | Content | Backlog |
|---|---|---|
| F1 | `useEngineStream`, `useFleet`, engine dropdown + fleet view; profile-driven channel rendering (delete `CHT_1..4` constants) | R4 |
| F2 | Operator console: health header, cylinder ring + residual heat, detector strip, banner with evidence | V1, V2 |
| F3 | Levers (what-if) + profile-valid fault panel + MANUAL action log | V9, R2/R3 |
| F4 | Tier-1 reservoir panel, calibration card, score distributions | W1/W11 |
| F5 | Edge & evidence view (bytes/latency, claims table, bake-off card, federated demo) | W4, W12, S9 |
| F6 | Propulsion depth: order waterfall, trends, sensor trust | V3, V4 |
| F7 | Maintenance view + component inspector | V10, B6.3 |
| F8 | Replay mode + scrubber on the new recorder | W3, D05 |
| F9 | Blender bridge parity (residual heat, firing order, engine swap) | V1/V2 |
| F10 | Phone layout, offline bundle audit, Playwright suite | B9.x |

## 7. What deliberately is *not* on the screen

- No fault ID / health index / RUL number that the backend did not compute from Frames (truth is structurally absent).
- No single "accuracy %" hero number from simulation. Show detection delay and false-alarm rate with counts and the evidence class.
- No LLM chat as the centrepiece; the copilot (default disabled, D33/D37) is an optional side drawer.
