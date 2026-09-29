# 05 — Frontend Product & UX Architecture

**DRDO / iDEX PS-26054 — AI-Enabled Real-Time Digital Twin for Health Monitoring, Fault
Prediction and Mission Reliability of Aero Piston Engines in MALE UAVs.**

Status: audit + proposed architecture. No implementation performed.
Audit method: source read of all three frontends, plus a live backend run
(`uvicorn backend.server.main:app`) with real payloads captured from
`/api/engines/rotax_912is/state` in nominal and injected-fault states.

---

## 1. Current UI Audit

### 1.1 There is not one frontend. There are three.

| Surface | Stack | Telemetry source | Design language | Role today |
|---|---|---|---|---|
| `frontend/` | React 18 + TS + Tailwind + Vite | `/ws/telemetry` **and** `/ws/engines/{id}` | Neutral dark, `#0e0e10`, one blue accent | The product |
| `apps/threejs_twin/index.html` | 2,702-line single HTML file, vanilla Three.js | `/ws/engines/{id}` | Cyan/amber HUD, glow | The 3D twin, embedded by **iframe** |
| `web/site/` | Vanilla JS modules, own Three.js scene | `js/telemetry/sim-engine.js` — **client-side fake** | Cyan glow, `--shadow-cyan-glow`, Outfit/Syne | Pitch microsite |

`frontend/src/App.tsx` exposes these as a three-way toggle: `runtime | twin | legacy`.
That toggle is the honest signature of the problem — it is not a navigation choice a user
would ever want to make. It asks the operator to pick which third of the product they want.

### 1.2 The React app contains three generations of itself

- **`workspace='runtime'`** (the default landing view) — `EngineRuntimeConsole`, built on the
  newer multi-engine `/api/engines/*` API. Architecturally the best code in the repo. Fleet
  strip, 4 KPI tiles, detector-ratio bars, scenario levers, fault injection, raw channel grid.
- **`workspace='twin'`** — a bare `<iframe src="{serverUrl}/apps/threejs_twin/">`. Zero shared
  state with React. Cross-document; no props, no selection sync, no design continuity.
- **`workspace='legacy'`** — six tabs (Operator / Propulsion / Maintenance / AI Diagnostics /
  Voice Copilot / Mission Replay) on the older single-engine `/ws/telemetry` stream.

### 1.3 What the 3D twin actually does

Better than expected, and genuinely wired to the backend:

- Five Draco-compressed GLBs (`rotax_912is/914/915is`, `austro_ae300`, `vrde_jayem_2_2l`),
  EXR environment lighting, contact-shadow plane, lighting auto-fit to model bounds.
- Station dock: per-station camera presets with eased transitions (`easeInOut`, 1350–2200 ms),
  ghost-out of non-inspected meshes, per-station spec cards.
- Exploded view with smoothed radial animation, wireframe toggle.
- **Propeller rotation is genuinely RPM-driven**: `propRpm = telemetryData.rpm / 2.43`,
  integrated per-frame with real `deltaSeconds` (index.html:2563-2576). Falls back to 1600 rpm
  when offline, and the comment says so honestly.
- Fault highlighting driven by the **live detector**, not just by manual injection:
  `setFaultVisual(mode, 'detector', evidence)` fires off the WebSocket frame, highlights target
  meshes, ghosts the rest, animates the camera to a computed fault view, and drops a pulsing
  3D locator ring when no mesh matches.
- Audio synth pitched from RPM; FPS counter; snapshot capture.

### 1.4 What the 3D twin fakes

**The thermal heatmap carries no telemetry.** `getThermalConfig(name)` (index.html:1538)
colours every mesh by *string matching on its name* against hardcoded temperature bands:
`includes('exhaust')` → red at "800–920°C", `includes('cylinder')` → amber at "120–180°C".
Live `cht[]` and `egt[]` are never consulted. The legend states temperature ranges that are
constants in a switch statement.

This is the one element of the whole system that is *representationally dishonest*: it looks
like the thermal state of the engine and is a lookup table. On a health-monitoring problem
statement it is also the most likely thing a DRDO evaluator will probe. Fixing it is cheap —
the data is already in the frame — and it converts the weakest feature into the strongest.

### 1.5 States

Handled: loading screen with progress, `PanelErrorBoundary` per panel, disconnected banner,
`ConnectionModal` for host config, WS reconnect with backoff on all three sockets, REST
fallback polling at 1 Hz when the socket is down, "Profile calibrating" for the ~10 s warmup.

Missing: stale-data handling (no frame-age display anywhere — a frozen stream renders as
confident live numbers), empty states beyond "Waiting for…", and any visual distinction
between LIVE / SIMULATED / HISTORICAL / PREDICTED beyond two text chips.

---

## 2. Current Codebase Mental Model

### 2.1 React app

```
main.tsx → App.tsx  (workspace toggle + role/tab state, all local useState)
  hooks/
    useTelemetrySocket.ts   → /ws/telemetry        (legacy, single engine, 20 Hz)
    useEngineRuntime.ts     → /api/engines/*, /ws/engines/{id}, /ws/fleet  (multi-engine)
    useMissionReplay.ts     → /api/replay/*
  components/  17 components, no shared primitives layer
  types/telemetry.ts        legacy stream types (rich)
  index.css + tailwind.config.js   the design system
```

No router (conditional rendering only). No state library. No shared `Metric`, `Panel`,
`StatusPill` or chart primitive — every panel re-implements its own label/value markup.

### 2.2 Backend contract (verified live)

```
GET  /api/engines                     catalog: 5 engines, per-engine valid fault list
POST /api/engines/select
GET  /api/engines/{id}/state          full frame
GET  /api/engines/{id}/schema         channels+units, operating_limits, provenance_summary
POST /api/engines/{id}/faults         {mode, cylinder?, severity, ramp_sec}
DEL  /api/engines/{id}/faults
POST /api/engines/{id}/levers         {throttle_pct, altitude_ft, oat_c}
WS   /ws/engines/{id}                 that frame, 20 Hz
WS   /ws/fleet                        compact per-engine status, 20 Hz
        + legacy /ws/telemetry, /api/state, /api/replay/*, /api/ai/*, /api/voice/*, /api/cbm/*
```

### 2.3 The central finding

`EngineRuntime.payload()` (backend/runtime/engine_runtime.py:519) publishes **20 top-level
fields** at 20 Hz. The frontend's `EngineFrame` interface
(`frontend/src/hooks/useEngineRuntime.ts:29`) declares **9**. Verified live payload:

| Field | Live content (captured) | Rendered in runtime console? |
|---|---|---|
| `channels` | 30 channels incl. `vib_order_*`, `virt_*` | partially (flat grid) |
| `cht` / `egt` | `[98.5, 96.0, 98.5, 96.0]` / `[534, 536, 525, 523]` | max only |
| `detection` | mahalanobis/max_abs_z/fly_bloom + ratios + `top_channels` with σ | yes — done well |
| `heavy` | tier-1 reservoir scores | yes, honestly labelled |
| **`prognostics`** | `rul_point 17.97 h`, `rul_p_lower/upper` (conformal, 95%), fatigue `damage_total`, `counted_cycles`, `life_remaining_fraction` | **no** |
| **`reliability`** | `mission_reliability 0.9968`, `limiting_component "fuel_pump"`, `mission_hours 18` | **no** |
| **`validity`** | `TWIN_TRUSTWORTHY`, `TWIN_CONFIDENCE`, `TWIN_ATTRIBUTION`, NIS vs chi² bounds, residual whiteness, biased channels, `TWIN_REASONS[]` | **no** |
| **`sanity`** | quarantined channels, `suppressed_anomaly`, advisory text | **no** |
| **`diagnosis`** | `fault_name`, `ata_chapter`, `manual_reference`, `subsystem`, **`target_3d_mesh`**, `root_cause_explanation`, `causal_chain[]`, `prescriptive_action`, `emergency_checklist[]`, `maintenance_order`, `confidence` | **no** |
| **`glide`** | L/D 27.3, range 40.4 nm, time aloft 36.8 min, 4 real Ladakh airfields (VILH Leh, VI82 Thoise, VIKG Kargil, VIAW Awantipur) with `alt_margin_ft` and reachability | **no** |
| **`vibration_orders`** | `1X, 2X, 3X_prop, sub_whirl, gear_mesh, bpfo, total_rms` | **no** |
| **`virtual_sensors`** | `P_max_bar 86.5`, `TIT_degC 547.8`, `h_min_um 10.7`, `P_ind_kw 68.0` | **no** |
| `ukf` | NIS + estimated params | no |

Every one of these **is** rendered — but only in the **legacy** workspace, off the older
single-engine stream (`MissionReadinessCard` has glide + reliability, `PropulsionEngineerPanel`
has validity + vibration orders + virtual sensors, `DiagnosticCard` has the causal chain and
ATA references). So:

> The analytically richest UI runs on the oldest stream, behind a tab labelled "Legacy",
> while the default landing view runs on the best stream and shows the least.

That single sentence is the brief for this redesign.

### 2.4 Verified drift and defects

1. **No charts exist anywhere.** `grep -rl 'svg|canvas|polyline|sparkline' frontend/src` returns
   nothing. No time axis in the entire product. Every temporal question — drift rate, RUL trend,
   threshold approach, "what changed" — is rendered as a number or a sentence.
2. **`rt.buffer` is a 3600-tick deque** (3 min @ 20 Hz) already on the server, with **no endpoint
   exposing it.** One `GET /api/engines/{id}/history` unlocks every chart below.
3. **Engine-list drift**: backend serves 5 engines; `ENGINE_ORDER` in the twin lists 3
   (index.html:789) though all 5 GLBs ship.
4. **Default-engine mismatch**: backend `selected: austro_ae300`; `useEngineRuntime` hardcodes
   `useState('rotax_912is')`.
5. **`target_3d_mesh` is duplicated logic.** The backend names the mesh to highlight
   (`"Wiring_Harness_M_Copper_0"` — verified present in `rotax_912is.glb`, 106 nodes). The twin
   ignores it and uses its own hardcoded `ENGINE_FAULT_TARGETS` table (index.html:808).
6. **`schema.components` is `[]`** — which is *why* the twin hardcodes that table. Fix upstream.
7. **Mojibake in backend strings**: `validity.explanation` contains `â€”` and `causal_chain`
   contains `Â°C` — UTF-8 read as cp1252. Will render literally.
8. **Conflicting signals in one frame, unreconciled.** On injected `MISFIRE` cyl 3, the frame
   simultaneously reported `sanity: quarantined EGT_3, CHT_3 … suppressed_anomaly: true`
   (i.e. "sensor fault, evidence shielded") **and** `validity.attribution: ENGINE_FAULT`.
   The detector's `top_channels` then pointed at `rpm`/`oil_p` — *away* from cylinder 3 — because
   the channels carrying the real evidence had been quarantined. The UI must never silently pick
   one of these; showing "Nominal" while `suppressed_anomaly` is true is the dangerous case.
9. **Diagnosis text is not cylinder-aware**: injecting on cylinder 3 produced narrative text
   reading "drops EGT **#2** sharply". Backend bug, jury-visible.
10. **`reliability` is not coupled to the active fault**: a confirmed misfire moved
    `mission_reliability` 0.9968 → 0.9967 and left `limiting_component: fuel_pump`.

### 2.5 The 3D geometry constraint (decisive for Phase 8)

Parsed the GLB node tables directly:

| Model | Nodes | Grouping | Per-cylinder meshes |
|---|---|---|---|
| `rotax_912is` (flagship) | 106 | 21 **subsystem** groups (ECU, Exhaust_System, Fuel_Pump, Gearbox_Type_2, Oil_Tank, Wiring_Harness, Water_Hoses…) | **none** |
| `rotax_914` | 590 | per-part | `Cylinder_Head_2..5` (note: 2–5, not 1–4; `Cylinder_Bank_1` is the bank) |
| `austro_ae300` | 163 | per-part | one merged `Cylinder_Head_M_CastAluminium_0` |

**The flagship engine model physically cannot show a per-cylinder fault.** Its meshes are split
by material and subsystem. So the plan below does *not* promise per-cylinder 3D: it makes a 2D
cylinder instrument the primary per-cylinder view (always correct, all engines, driven straight
off the `cht[]`/`egt[]` arrays) and uses 3D for subsystem-level localisation, which is exactly
what the geometry supports.

---

## 3. What Works / What Doesn't

### KEEP — do not touch

- **The design system.** `tailwind.config.js` + `index.css` already do the Phase 15/16 work, with
  the reasoning in the comments: layered neutral surfaces, one blue accent, flat semantic status
  colours, elevation-not-illumination shadows, one 200 ms `fade-in`, and a documented refusal of
  `backdrop-filter` on telemetry panels for measured compositing reasons. This is better than
  most of the reference sites in Phase 14 and better than what a redesign would produce.
- **Provenance honesty.** The runtime console labels tier-1 output "readout scores, not
  probabilities", marks injected faults MANUAL, and carries a footer stating what is *not* live.
  Preserve this tone exactly; it is the project's credibility.
- **Detector-evidence panel** — ratio-to-threshold bars with σ per channel. Correct instrument.
- **Multi-engine runtime hook + fleet socket.** The right data architecture; build on it.
- **Twin's camera/station/fault-focus system**, RPM-driven prop, exploded view, GLB pipeline.
- **`PanelErrorBoundary`**, WS reconnect + REST fallback.
- **Legacy panels' analytical content** (glide, vibration orders, virtual sensors, causal chain).

### IMPROVE

- `EngineRuntimeConsole` — correct instincts, but it is one 200-line JSX return with 6+ panels
  and no time dimension. Decompose and add history.
- Raw channel grid — 30 undifferentiated tiles. Group by subsystem; add limits and sparklines.
- Twin's HUD typography/colour → adopt the React token set.

### REWORK

- **The `runtime | twin | legacy` toggle** → replace with real information architecture (§8).
- **The twin's iframe boundary** → the twin must become a component receiving the same frame.
- **Role switching** (`OPERATOR / PROPULSION_ENGINEER / MAINTENANCE_CREW`) — the right idea,
  wrong mechanism: it currently duplicates whole page layouts. Make it a density/emphasis lens
  over one shared frame.

### REPLACE

- **The thermal heatmap** (§1.4) — same feature, driven by `cht[]`/`egt[]` + `operating_limits`.
- **`ENGINE_FAULT_TARGETS`** hardcoded table → `diagnosis.target_3d_mesh` + `schema.components`.
- **Prose-as-chart.** `MissionReadinessCard` explains degradation trends in a paragraph
  ("No component is currently showing a fitted degradation trend (R² ≥ 0.55 over a 2/10/30-minute
  window)"). That is a chart described in words.

### REMOVE

- `web/site/js/telemetry/sim-engine.js` — a second, client-side, fabricated telemetry source.
  It is the single largest credibility risk in the repo: a 3D UAV scene animating from invented
  numbers while a real backend exists. Keep `web/site` **only** if it is explicitly a marketing
  microsite, and label it as such; never demo it as the product.
- Duplicated Three.js vendor trees (`web/site/js/vendor/` vs `apps/threejs_twin/js/vendor/`).
- Dead `activeRole`/`workspace` branches once IA lands.

### MISSING

1. **Time.** No charts, no history, no trends, no "what changed". The largest gap.
2. **Surfacing of `prognostics`, `reliability`, `validity`, `sanity`, `diagnosis`, `glide`,
   `vibration_orders`, `virtual_sensors` on the primary stream.**
3. **Data-freshness / staleness model.** No frame age anywhere.
4. **Per-cylinder instrument.** `cht[]`/`egt[]` arrive as 4-element arrays and are reduced to
   `Math.max()`. The per-cylinder structure — the actual diagnostic signal for a piston engine —
   is discarded at the UI boundary.
5. **Event timeline.** Nothing records that something happened 90 seconds ago.
6. **Alert model.** No severity hierarchy, no acknowledgement, no history.
7. **Threshold bands.** `operating_limits` (`cht_max_c`, `egt_max_c`, `oil_p_min_bar`,
   `oil_t_max_c`) is fetched and unused. No reading is shown against its limit.
8. **Provenance display.** `provenance_summary {MANUAL: 17, ASSUMED: 4}` — per-parameter source
   credibility, fetched and unused. Free credibility with a DRDO audience.

---

## 4. Product & User Understanding

The system answers a chain, and the UI should be readable as that chain:

**Observe → Understand → Detect → Diagnose → Predict → Respond → Evaluate**

| Question | Field that answers it | Instrument |
|---|---|---|
| What is happening? | `channels`, `cht[]`, `egt[]` | cylinder instrument + grouped readings |
| Can I trust what I'm seeing? | `validity`, `sanity`, frame age | **trust gate, above everything** |
| Is it healthy? | `detection.ratios`, `operating_limits` | ratio bars, threshold bands |
| What changed? | history buffer | sparklines + event timeline |
| Why? | `diagnosis.causal_chain`, `root_cause_explanation` | evidence chain, not a chat bubble |
| Where? | `diagnosis.target_3d_mesh`, `subsystem` | 3D locator |
| What next? | `prognostics.rul` + conformal band, `damage` | RUL band chart |
| What does it mean for the mission? | `reliability`, `glide.reachable_airfields` | reliability + diversion |
| What do I do? | `prescriptive_action`, `emergency_checklist`, `maintenance_order` | action card |

**The trust gate is first, not last.** `validity.TWIN_TRUSTWORTHY` was `false` with
`TWIN_CONFIDENCE 0.0` in a freshly-started nominal run. A digital twin that says "do not believe
me" while the UI renders confident numbers is worse than one with fewer features. Surfacing this
is the most differentiating single change available — no competitor dashboard does it — but it
needs a three-state model, not a boolean: **WARMING** (first ~60 s, NIS not yet converged) /
**TRUSTWORTHY** / **INVALID + attribution**. Shipping the raw boolean would show "INVALID" on
every cold start.

### Users

Three, all real, all already in the code:

- **UAV Operator** — mission-time decisions. Needs: can I continue? Wants one screen, big
  readings, unambiguous severity, `glide` diversion options, `emergency_checklist`. Does not want
  mahalanobis distances.
- **Propulsion Engineer** — why is it doing that? Needs residuals, σ per channel,
  `vibration_orders`, `virtual_sensors`, `ukf` NIS, threshold bands, full history, fault injection.
- **Maintenance / CBM crew** — post-flight. Needs `damage`, `life_remaining_fraction`,
  `counted_cycles`, `ata_chapter`, `manual_reference`, `maintenance_order`, sign-off.

Plus an implicit fourth: the **SIH/DRDO evaluator**, who needs the causal chain to be legible in
3 minutes without narration (§18).

---

## 5. Functionality Map

Placement, not pages:

**Always visible (persistent shell)** — engine selector, fleet status strip, data-mode +
frame-age chip, twin-trust chip, active-alert count, clock/sortie.

**Primary dashboard** — trust gate · cylinder instrument · 4 KPIs with sparkline + limit ·
detector evidence · RUL band · 3D twin locator · event timeline · action card.

**Drill-down views** — Diagnostics (full residual matrix, vibration orders, virtual sensors,
UKF), Prognostics & CBM (damage, cycles, work packages), Mission (glide/diversion map,
reliability vs 18 h ISR profile), Replay.

**Contextual (inline, never a page)** — fault injection, levers, channel detail on hover,
per-mesh inspection, alert acknowledgement.

**Explicitly not pages**: "AI Insights" (AI belongs inside the fault it explains),
"Alerts" (timeline + inline), "Settings" (modal, already correct).

---

## 6–8. Information Architecture — Options, and the Recommendation

### Option A — Keep three workspaces, polish each
Cheapest; preserves the core defect. Rejected.

### Option B — Fleet → Engine → Diagnostics (asset hierarchy)
Honest to the multi-engine backend and scales. But it puts a fleet list between the operator and
the engine on every load, and for a demo the first screen would be a table. Adopt its *shape* as
a persistent strip, not as a landing page.

### Option C — Task-phase routes: Overview → Twin → Health → Prediction → Simulation → History
Mirrors the problem statement's vocabulary, which reads well to an evaluator. But it splits one
causal event across five routes: the operator sees the deviation on Overview, the location on
Twin, the significance on Health, the consequence on Prediction. Cause and effect — the thing the
UI most needs to convey — gets fragmented by navigation. Rejected as a primary IA.

### Option D — **One operational surface + role lens + drill-downs (recommended)**

```
┌─ AppShell ───────────────────────────────────────────────────┐
│  TopBar: engine ▾ | LIVE·20Hz·age 0.1s | TWIN: TRUSTWORTHY   │
│          | ⚠ 2 | role: Operator ▾ | sortie                   │
│  FleetStrip: 5 engines, status dot + rpm + max CHT           │
├──────────────────────────────────────────────────────────────┤
│  /            OPERATIONS   ← the product. 90% of time here.  │
│  /diagnostics ENGINEERING  residuals, orders, virtual sensors│
│  /prognostics CBM          damage, RUL, work packages        │
│  /mission     RELIABILITY  glide, diversion, 18 h profile    │
│  /replay      HISTORY      recorded sorties                  │
└──────────────────────────────────────────────────────────────┘
```

Four drill-downs, one operational home, one persistent shell. The **role selector changes
density and emphasis on `/`, not the route** — Operator sees big readings and actions, Engineer
sees residuals and σ expanded inline, Maintenance sees damage and cycles promoted.

**Tradeoffs, stated plainly.** Cost: `/` becomes the most complex screen in the app and needs
disciplined progressive disclosure or it becomes the wall of cards the brief warns against.
Benefit: one causal event — deviation → detector → 3D → alert → RUL → action — is visible
*simultaneously, in one viewport, without navigating*. For a system whose entire thesis is cause
and effect, and for a 3-minute demo, that is worth the complexity. Fault scenarios are also
better served: nobody navigates during an emergency. And it maps cleanly onto what exists —
`EngineRuntimeConsole` becomes `/`, the legacy tabs become the drill-downs.

---

## 9. Reference Analysis — principles taken, not visuals

- **Linear** — restraint in state transitions; one accent; nav that recedes. Take: the discipline
  of *removing* chrome. Reject: its marketing-page motion.
- **Vercel** — typographic hierarchy carrying structure without borders everywhere.
- **Stripe** — the important one: high information density that stays calm, charts as first-class
  citizens with real axes and hover that answers a question. This is the model for §15.
- **Datadog** — the operational model: threshold bands drawn on the series, event markers on the
  time axis, severity as a small consistent glyph rather than a colour wash, alert → graph →
  timeline continuity. Closest functional analogue to this product; study its *time axis*.
- **Palantir** — situational awareness: the decision and its supporting evidence co-located.
  Take the co-location. Reject the dark-ops theatrics, which is exactly the trap here.
- **Attio** — contextual information appearing where it is needed instead of on its own page.
- **Mesh3D / threejsresources / opencolin dashboard** — R3F patterns, data-driven materials,
  restrained post-processing. Relevant technique: driving material uniforms from live data —
  which is precisely the honest thermal shader in §14.

Anti-reference, to be explicit: this project must not look like the `web/site` microsite. Cyan
glow, `--shadow-cyan-glow`, Outfit/Syne display type and animated particle HUDs read as a defence
*advertisement*, not a defence *instrument*.

---

## 10. Visual Direction

**Adopt the existing `frontend/` token set as the single system**, extend it minimally, and
propagate it into the twin (which currently has its own).

Additions needed (only these):

```js
// surfaces: one more level, for charts sitting inside panels
'surface-inset': '#141417',
// data-mode semantics — the LIVE/SIM/HIST/PRED/STALE distinction of §22
'mode-live': '#4CD273',   'mode-sim':  '#3B9EFF',
'mode-hist': '#8E8E93',   'mode-pred': '#C084FC',  'mode-stale': '#FFB340',
// chart furniture
'grid-line': 'rgba(255,255,255,0.05)',
'limit-line': 'rgba(255,98,89,0.45)',
'band-predicted': 'rgba(192,132,252,0.14)',
```

Rules:
- Colour means state. Blue = accent/selection. Green = nominal. Amber = advisory/warning **and**
  stale. Red = critical. Purple = *predicted/model output only* — never decoration. Grey = history.
- Radius stays ≤ 4 px. No new shadows. No gradients except the predicted-interval fill, whose
  purpose is to say "this region is uncertain".
- Numbers are `tabular-nums` monospace, always; labels are 10–11 px uppercase with wide tracking.
  This is already the house style — keep it.
- Every displayed value carries unit and, where `operating_limits` provides one, its limit.
- One font. No display face.
- **No glow.** The twin's `emissiveIntensity` pulsing is the only exception and only for a
  confirmed fault locator, because there it encodes "attention here".

---

## 11. Motion Direction

Each animation must name the information it carries. The list, and nothing beyond it:

| Motion | Carries | Spec |
|---|---|---|
| Prop/crank rotation | actual RPM | keep; continue integrating real `deltaSeconds` |
| Camera transition to a fault | spatial continuity — "you are now looking *there*" | keep 1350–2200 ms `easeInOut` |
| Fault locator pulse | unresolved attention | keep, confirmed faults only |
| Chart line advance | time passing | translate the series, never re-animate from zero |
| Value change | a reading moved | 120 ms colour flash on the digit; no layout shift |
| Severity escalation | a threshold was crossed | 200 ms border-colour transition, no flashing |
| RUL band | growing uncertainty with horizon | band widens with the interval, not decoratively |
| Panel enter | continuity on drill-down | existing 200 ms `fade-in` |
| Exploded view | assembly relationships | keep |

Removed: orbit auto-rotation while a fault is active (it fights the operator — already partly
handled via `orbitAnimating = false`), beacon-ring spin, opacity sine breathing on idle elements,
any transition > 300 ms outside camera moves. Honour `prefers-reduced-motion`: freeze camera
easing and value flashes, keep chart advance.

---

## 12. Main Dashboard Concept & Wireframe — `/` OPERATIONS

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ ANUMAAN   [Rotax 912 iS ▾]   ● LIVE 20Hz age 0.1s   TWIN ✓TRUSTWORTHY 0.91   │
│                              ⚠2   [Operator ▾]   SORTIE-20260929-0804        │
├───────────────────────────────────────────────────────────────────────────────┤
│ ●912iS 5412rpm 98°  ●914 —  ●915iS 5100 102°  ●AE300 —  ●JAYEM 4800 94°      │  fleet
├───────────────────────────────────────────────────────────────────────────────┤
│ ⚠ SENSOR: EGT_3, CHT_3 quarantined — residual shielding active.               │  trust gate
│   Detector evidence for cylinder 3 is suppressed. Attribution: ENGINE_FAULT.   │  (only when
├───────────────────────────────────────────────────────────────────────────────┤  degraded)
│ ┌─── CYLINDERS ────────┐ ┌─── 3D TWIN ─────────────┐ ┌─ CONDITION ──────────┐ │
│ │  1    2    3    4    │ │                         │ │ RUL   17.6 h         │ │
│ │ CHT ▆▆  ▆▆  ▃▃  ▆▆   │ │   [engine, fault mesh   │ │ ├─────█──────┤ 95%   │ │
│ │  96  95  87! 96  °C  │ │    highlighted, rest    │ │ 17.3        17.8     │ │
│ │ EGT ▆▆  ▆▆  ▁   ▆▆   │ │    ghosted, camera on   │ │                      │ │
│ │ 520 523  46! 523 °C  │ │    the fault]           │ │ MISSION REL.  0.9968 │ │
│ │ ─── limit 130°C ──── │ │                         │ │ limiting: fuel_pump  │ │
│ │ cyl 3: EGT −477 Δ    │ │ [◱ station ▾][thermal]  │ │ DAMAGE 0.79%  34 cyc │ │
│ └──────────────────────┘ └─────────────────────────┘ └──────────────────────┘ │
├───────────────────────────────────────────────────────────────────────────────┤
│ RPM 5412 ▁▂▃▅▇ │ MAP 28.4" ▃▃▃▃▃ │ OIL_P 4.1 ▃▃▃▂▂ │ OIL_T 96 ▃▄▄▅▅        │  KPI+spark
│         6000 ↑         limit —          min 2.0 ⚠         max 130             │  +limit
├──────────────────────────────────┬────────────────────────────────────────────┤
│ DETECTOR EVIDENCE                │ EVENT TIMELINE            [ack all]        │
│ mahalanobis  1.65× ████████▌     │ 08:12:04 ⛔ MISFIRE confirmed · cyl 3      │
│ max_abs_z    1.00× █████         │ 08:12:01 ⚠  EGT_3 −477°C in 3 s           │
│ fly_bloom    0.60× ███           │ 08:11:58 ⚠  EGT_3 quarantined             │
│ top: rpm −10σ, oil_p −10σ        │ 08:04:10 ℹ  Profile calibrated            │
│ CONFIRMED (persistence gate)     │ ──── time axis, shared with charts ────    │
├──────────────────────────────────┴────────────────────────────────────────────┤
│ DIAGNOSIS  Ignition Misfire (Lane A) · ATA 74-20 · IGNITION_SYSTEM · conf 0.98 │
│ Lane-A coil degradation → intermittent combustion dropout.                     │
│ ① lead insulation breakdown → ② unburnt fuel drops EGT_3 → ③ RPM flutter →     │
│ ④ torque shock into gearbox (+1.45 mm/s)                                       │
│ ▸ ACTION Switch FADEC arbitration to Lane B    [3-step checklist ▾]            │
│ ▸ MAINT  Lead resistance test 4.5–5.5 kΩ; replace Lane A coil pack             │
└───────────────────────────────────────────────────────────────────────────────┘
        collapsed drawer ▴  SCENARIO: throttle / altitude / OAT · inject fault
```

**Why this layout.**

- **The trust gate is above the data**, collapsing to nothing when healthy. It is the only
  element allowed to push content down, because it is the only one that invalidates everything
  below it.
- **Cylinders, twin and condition share one row** — left/centre/right = *what*, *where*, *so
  what*. This is the causal triplet, readable in one glance without a saccade down the page.
- **The cylinder instrument is 2D and leads**, for the geometry reason in §2.5: it works on all
  five engines, shows all four cylinders at once with limits, and is where a misfire is actually
  legible. The 3D twin is the *locator*, which is what the geometry supports.
- **KPI row carries sparkline + limit**, not bare numbers — the minimum viable time dimension.
- **Detector and timeline are adjacent and share a time axis**, so "the score rose" and "then
  this happened" are one reading.
- **Diagnosis spans full width at the bottom** — it is the conclusion, and prose needs measure.
  It is not a chat panel and not a separate page.
- **Scenario controls are a collapsed drawer.** They are demo/test instruments; giving them a
  standing panel (as now) tells the viewer the whole thing is a toy.

Operator sees this. Engineer expands detector + KPI into the full residual matrix inline.
Maintenance promotes damage/cycles and collapses the twin.

---

## 13. Page-by-Page Architecture

### `/` Operations — *above.* Not here: raw 30-channel dump, replay scrubbing, work-package
sign-off, voice UI. States: calibrating (~10 s, skeletons + "profile calibrating") · live ·
stale (>2 s, amber, values dimmed + age) · disconnected (last frame greyed + timestamp, never
blank) · simulated (blue chip) · untrustworthy (gate expanded) · fault (gate + timeline + camera).

### `/diagnostics` Engineering
Purpose: why. User: propulsion engineer. Content: full residual matrix (z-score per channel with
σ bands), `vibration_orders` as an order spectrum (1X/2X/3X_prop/gear_mesh/bpfo/sub_whirl —
bar-per-order, the actual PHM instrument), `virtual_sensors` (`P_max_bar`, `TIT_degC`,
`h_min_um`, `P_ind_kw`) marked as **INFERRED** — these are unmeasurable quantities the twin
computes, which *is* the definition of a digital twin and is currently invisible; `ukf` NIS vs
chi² bounds; `validity` detail with `TWIN_REASONS[]`; channel provenance from
`provenance_summary`. 3D: optional, subsystem isolation. Not here: mission decisions, maintenance.

### `/prognostics` Prognostics & CBM
`damage` breakdown (`thermal_lcf`, `shock_cooling`, `thermal_stress`), `counted_cycles`,
`life_remaining_fraction`, RUL with conformal band over time, per-component table, work packages
(`/api/cbm/maintenance`, sign-off), `ata_chapter` + `manual_reference`. Not here: live telemetry.

### `/mission` Mission Reliability
`reliability` vs the 18 h ISR profile, limiting component and its survival, **glide/diversion**:
the four real Ladakh airfields with `alt_margin_ft`, `glide_range_nm` reachability ring,
`recommended_diversion`. This is the "mission reliability enhancement" half of the problem
statement title and has no UI at all today. Not here: component-level diagnostics.

### `/replay` History
Existing `MissionReplayScrubber` + `/api/replay/*`. All charts in HISTORICAL grey; scrubber
drives the twin and the cylinder instrument so replay looks identical to live but unmistakably
grey. Not here: fault injection, live controls.

---

## 14. Digital Twin UX

**Structural change: delete the iframe.** Port `apps/threejs_twin/index.html` to a React
Three Fiber component inside the app, receiving the same `EngineFrame` as every other panel.
Rationale: the iframe makes selection sync, shared alert state, unified design tokens and
`target_3d_mesh` handoff impossible, and forces a duplicate WebSocket to the same stream.

Port, do not rewrite: GLB/Draco/EXR loading, bounds-fitting lighting, station camera presets and
easing, exploded view, wireframe, fault-focus camera, locator ring, RPM-driven prop. All of it is
sound and hard-won.

Three changes of substance:

**1. Make the thermal view real.** Replace `getThermalConfig(name)` with a per-mesh temperature
resolved from live data:

```
mesh → component (schema.components / mesh group name)
     → channel  (cht_N / egt_N / oil_t)
     → t = channels[channel]
     → u = (t - limit_min) / (limit_max - limit_min)   // operating_limits
     → colour ramp; emissive only above u = 1.0
```
Meshes with no channel mapping render **neutral grey — explicitly "unmonitored"**, never
interpolated. That absence is information: it shows the sensor coverage of the real engine. The
legend becomes a live scale with the actual limit printed on it. Same feature, now an instrument.

**2. Take the fault target from the backend.** Use `diagnosis.target_3d_mesh` (verified to
resolve in the GLB) and `diagnosis.subsystem` as the authority; delete `ENGINE_FAULT_TARGETS`
once `schema.components` is populated. Keep the locator ring as the documented fallback for
unmatched meshes — with a visible "approximate location" label, since that is the honest reading.

**3. Per-cylinder degrades explicitly.** Where cylinder meshes exist (`rotax_914`,
`Cylinder_Head_2..5` → cylinders 1..4 via an explicit offset map) highlight the cylinder. Where
they do not (`rotax_912is`, `austro_ae300`) highlight the subsystem and let the 2D cylinder
instrument carry the cylinder identity. Never fake a cylinder mesh.

Interaction contract: click mesh → select component → filters residual matrix and timeline to
that component. Hover → name, mapped channel, live value, limit. Camera presets: Overview /
Station N / Fault / Thermal. Selection is bidirectional — clicking cylinder 3 in the 2D
instrument or a timeline event moves the camera.

Scene state by condition: nominal = neutral PBR, slow orbit permitted, prop at RPM.
Advisory = subsystem tinted amber, orbit continues. Warning = camera offers to focus (a button,
not a hijack). Critical = auto-focus once, ghost everything else, locator pulse, orbit stops.

Performance: single canvas, `dpr` capped at 2, pause `requestAnimationFrame` when not visible,
`InstancedMesh` for fastener groups (`rotax_914` is 590 nodes), decouple render loop from the
20 Hz stream — lerp toward the latest frame rather than re-render on message.

---

## 15. Data Visualization System

**Prerequisite (one backend endpoint):**
`GET /api/engines/{id}/history?channels=…&n=1200` off the existing `rt.buffer` deque — already
holds 3 min at 20 Hz. Without it every chart starts empty on load, which breaks the demo's first
15 seconds. Client keeps a rolling ring buffer (decimated to ~4 Hz for display) for continuation.

| Instrument | Question | Why this form |
|---|---|---|
| **Cylinder bar pair** (CHT/EGT × 4, limit rule) | Which cylinder is wrong, and by how much? | 4 discrete comparable items with a shared limit; a line chart hides the between-cylinder comparison that *is* the diagnosis |
| **KPI sparkline + limit tick** | Is this moving, and toward what? | Smallest honest time dimension in a KPI |
| **Multi-channel time series, threshold bands, event markers** | What changed, when, relative to limits? | The Datadog pattern; bands from `operating_limits`, markers from the timeline, shared x-axis, brush-to-zoom |
| **Residual strip (z-score per channel, ±2σ/±3σ bands)** | Which channels are anomalous *simultaneously*? | Co-occurrence is the signature; 30 sparklines cannot show it |
| **Detector ratio bars** | How close to alarm? | Already correct — keep |
| **Order spectrum** (1X/2X/3X_prop/gear_mesh/bpfo/sub_whirl) | Mechanical signature? | Order domain is the rotating-machinery convention; bar-per-order is the standard reading |
| **RUL band over time** | How long, how sure? | Line + conformal band; band widens with `interval_width`. Historical solid grey, predicted dashed purple over `band-predicted` fill, **hard vertical "now" rule** |
| **Damage stack** (LCF / shock-cooling / thermal-stress) | What is consuming life? | Stacked area — additive components of one total |
| **Reliability decay vs 18 h profile** | Will it finish the mission? | Line with mission-end marker; limiting component annotated |
| **Glide reachability** | Where can it reach? | Range ring + airfield markers coloured by `alt_margin_ft` — spatial question, spatial answer |
| **Cylinder × time heatmap** (optional) | Slow single-cylinder drift? | Only in `/diagnostics` |

Interaction rules, uniform: hover = crosshair + shared tooltip across every chart on the same
axis (value, unit, limit, Δ from limit, timestamp, mode). Click a timeline marker = all charts
scroll to it and the twin camera moves. Brush = zoom all synchronised charts. Drag on the time
axis = enter HISTORICAL mode (every chart greys, a "return to live" affordance appears).

Encoding of mode, everywhere, no exceptions: **LIVE** solid + green dot · **SIMULATED** solid +
blue chip · **HISTORICAL** grey, desaturated · **PREDICTED** dashed purple + band, always right
of the now-rule · **STALE** amber, last-good value dimmed with age in seconds.

Anomalies: amber dot on the series at the residual excursion, red at `confirmed`, with the
excursion region tinted — not the whole chart.

Charts to **not** build: a health-index donut (one number, no shape), engine-load gauges
duplicating a KPI, a fault-probability pie, anything 3D-decorative.

Library: this is ~8 chart archetypes with unusual requirements (synchronised axes, threshold
bands, prediction bands, 4 Hz updates, a shared crosshair). Recommend **`visx` or hand-rolled SVG
primitives over a chart library** — Recharts/Chart.js will fight the shared-axis and
prediction-band requirements. `d3-scale` + `d3-shape` for maths, React for rendering, one
internal `<TimeSeries>` that every instrument composes.

---

## 16. Alert & Fault UX

Four levels, each with a defined source in the payload — no level that isn't machine-derivable:

| Level | Source | Behaviour |
|---|---|---|
| **INFORMATION** | profile calibrated, engine selected, lever applied, fault cleared | timeline only |
| **ADVISORY** | `detection.raw_alarm && !confirmed`; `sanity.drift_detected`; `validity` degrading; reading >80% of limit | timeline + amber chip on the affected instrument. **No banner** |
| **WARNING** | `detection.confirmed`; `diagnosis.severity == 'WARNING'`; limit exceeded; `sanity.suppressed_anomaly` | timeline + instrument border + top-bar count + diagnosis card populates. Twin *offers* focus |
| **CRITICAL** | `diagnosis.severity` critical; `!validity.TWIN_TRUSTWORTHY` with `ENGINE_FAULT`; RUL below mission need; `reliability` below threshold | trust-gate row expands, twin auto-focuses once, timeline marker, requires acknowledgement |

Rules: nothing blocks the view; no modal, ever; no flashing; no toast stack. Severity is carried
by a 1 px border and one glyph, not a colour wash. Acknowledging silences the chrome and keeps
the timeline entry — acknowledgement is not resolution, and the two are distinct states.

**The conflicting-signal case is a first-class alert, not an edge case.** When
`sanity.suppressed_anomaly` is true the UI must say *"detector evidence is being suppressed for
these channels"* and must not render "Nominal". Verified live: `EGT_3/CHT_3` quarantined while
`validity.attribution` read `ENGINE_FAULT`. Both get shown, side by side, with the disagreement
named. A monitoring system that hides its own ambiguity is the failure mode that matters here.

Event propagation — one event, one identity, five surfaces:

```
channel excursion  →  cylinder instrument bar turns amber
detector ratio ≥1  →  ADVISORY, timeline marker, ratio bar amber
confirmed          →  WARNING, twin highlights target_3d_mesh, camera offers focus
diagnosis arrives  →  causal chain + action card populate, ATA reference
prognostics shift  →  RUL band steps down, damage stack grows
reliability shift  →  mission card + diversion options update
```
All five reference the same event id and the same timestamp on the shared time axis, so clicking
any one of them selects the others.

---

## 17. AI / Prediction UX

The AI content already exists and is good — `diagnosis.causal_chain`,
`root_cause_explanation`, `prescriptive_action`, `emergency_checklist`, `confidence`,
`ata_chapter`, `manual_reference`. Three rules for presenting it:

1. **The explanation lives inside the fault**, spanning the bottom of `/`. Not a sidebar, not a
   chatbot, not a route. Numbered causal chain, each step ideally linking to the channel that
   evidences it.
2. **Show uncertainty as a number and a shape.** `confidence 0.98` as text; the conformal RUL
   interval as a *band* — this project has genuine calibrated uncertainty
   (`nominal_coverage 0.95`), which is rare, and should be visible as geometry, not a footnote.
3. **Never assert more than the tier supports.** Preserve the existing labels exactly: tier-1
   reservoir output is "readout scores, not probabilities"; injected faults are MANUAL;
   `evidence_class: SIMULATION` is displayed. Add the same rigour to the new panels: RUL is
   labelled MODEL, virtual sensors INFERRED, reliability ANALYTIC.

Keep `VoiceCopilot` and the RAG `DiagnosticCard` — move them behind an explicit "Ask" affordance
on `/diagnostics` rather than a top-level tab. They are supporting tools, not the product's
front door.

Cleanups: fix the mojibake (`â€”`, `Â°C`) at source; make `causal_chain` cylinder-aware (it said
"EGT #2" for a cylinder-3 injection); couple `reliability.limiting_component` to the active fault
(a confirmed misfire must not leave `fuel_pump` as the limiter).

---

## 18. Mission Simulation UX & Demo Flow

The full causal chain **already works end to end** — verified live by injecting
`MISFIRE / cyl 3 / severity 0.9 / ramp 8 s`:

| t | Observed |
|---|---|
| 0 s | nominal: CHT `[98.5, 96.0, 98.5, 96.0]`, EGT `[534, 536, 525, 523]`, no alarm |
| +8 s | EGT_3 collapses 525 → 46 °C; CHT_3 96 → 87.5 °C |
| +8 s | `mahalanobis` 3.01 → 24.55, ratio 0.20 → **1.65×**, `raw_alarm` → `confirmed` |
| +8 s | `diagnosis`: "Ignition Misfire (Lane A)", ATA 74-20, subsystem IGNITION_SYSTEM, `target_3d_mesh: Wiring_Harness_M_Copper_0`, 4-step causal chain, 3-step checklist, conf 0.98 |
| +8 s | RUL 17.97 → **17.57 h**; fatigue damage 0.00059 → **0.0079** (13×) |
| +25 s | `DELETE /faults` → recovery |

Nothing needs inventing for the demo. It needs *rendering*. The UI's whole job in §12 is to make
these six rows simultaneously visible so causality is seen rather than narrated.

**Demo, 3.5 minutes, no verbal explanation required:**

1. **0:00–0:30 — What this is.** `/` healthy, one engine. Prop turning at real RPM. Trust chip
   green. Fleet strip shows five engines. All four cylinders even, inside limits.
2. **0:30–1:00 — What it monitors.** Hover a cylinder → channel, value, limit, provenance.
   Open the thermal view: colour now comes from live CHT (contrast this explicitly with the
   old name-matched version). Point at `virtual_sensors` — quantities no sensor measures.
3. **1:00–1:45 — A fault appears.** Inject misfire on cylinder 3 from the drawer. Watch, in one
   viewport: cylinder-3 EGT bar collapses → sparkline drops → detector ratio crosses 1.0 →
   ADVISORY, then CONFIRMED → twin highlights the ignition harness and the camera moves →
   timeline stamps it. No navigation. No clicks.
4. **1:45–2:30 — Why, and how sure.** Diagnosis card: ATA 74-20, four-step causal chain,
   confidence 0.98, manual reference. RUL steps 17.97 → 17.57 h with its 95% conformal band
   visibly widening. Damage stack grows.
5. **2:30–3:00 — What it means for the mission.** `/mission`: reliability against the 18 h ISR
   profile, glide range 40.4 nm, the four Ladakh airfields with altitude margins,
   recommended diversion.
6. **3:00–3:30 — Respond and recover.** Prescriptive action (switch to Lane B), run the 3-step
   checklist, clear the fault. Values recover, detector de-escalates, alert moves to
   acknowledged-in-history. Mission continues.

The honest close, and the strongest moment available: show the **trust gate** with a sensor fault
injected — the system declaring its own twin untrustworthy and naming why
(`TWIN_REASONS`: "NIS 31.8 outside chi² 95% bounds [1.2, 14.4]", "residuals not white"). No
competitor dashboard does this. It is the difference between a demo and an instrument.

---

## 19. Component Architecture

```
app/
  AppShell            layout, routes, keyboard, reduced-motion
  TopBar              engine select · DataModeChip · TrustChip · alerts · role · sortie
  FleetStrip          /ws/fleet; click = select engine
  RouteView           4 drill-downs

primitives/           ← the layer that does not exist today
  Panel               title, subtitle, severity, collapsible, right slot
  Metric              label, value, unit, limit, sparkline, mode, Δ, precision
  StatusPill / DataModeChip / SeverityGlyph
  ThresholdBar        value vs limit, one row
  Provenance          MANUAL | ASSUMED | INFERRED | MODEL badge

charts/
  TimeSeries          shared x-axis, bands, markers, brush, crosshair  ← all others compose this
  Sparkline · CylinderBars · ResidualStrip · RatioBars
  RULBand · DamageStack · OrderSpectrum · ReliabilityCurve · GlideMap

twin/
  TwinCanvas          R3F root, dpr cap, visibility pause
  EngineModel         GLB/Draco load, bounds fit, node index
  ThermalMaterial     live-data-driven colour ramp        ← replaces getThermalConfig
  FaultHighlight      target_3d_mesh, ghosting, locator fallback
  CameraDirector      overview/station/fault presets, easing  ← ported as-is
  StationDock · TwinLegend · MeshTooltip

domain/
  TrustGate           validity + sanity + frame age. The most important component.
  CylinderInstrument  cht[]/egt[] + limits + per-cylinder Δ
  DetectorEvidence    ratios + top_channels σ          ← exists, keep
  DiagnosisCard       causal chain, action, checklist, ATA
  EventTimeline       shared time axis, ack, selection
  ConditionSummary    RUL + reliability + damage
  ScenarioDrawer      levers + injection            ← exists, demote to drawer
  MissionReliability · GlideDiversion · WorkPackages · ReplayScrubber
```

Contracts for the three load-bearing components:

**`TrustGate`** — in: `validity`, `sanity`, `frameAgeMs`, `evidence_class`. Out: a single
`TrustState` (`warming | trustworthy | degraded | invalid`) consumed by the shell to decide
global presentation. Owns the three-state warmup model of §4 so no other component reads the raw
boolean. Renders nothing when trustworthy.

**`TimeSeries`** — in: `series[]` (each with `mode`), `limits`, `markers`, `domain`, `now`. Every
other chart is a preset over it. This is the single most reused new component; getting its axis
and mode semantics right once fixes the whole visualization system.

**`CylinderInstrument`** — in: `cht[]`, `egt[]`, `n_cylinders`, `operating_limits`,
`selectedCylinder`, `faultCylinder`. Out: `onSelectCylinder`, which drives the twin camera and
filters the residual strip. Carries the per-cylinder story on every engine regardless of GLB
topology.

---

## 20. Technical Architecture

Keep: **React 18 + TypeScript + Vite + Tailwind**, the existing token set, `lucide-react`,
`clsx`/`tailwind-merge`, the `PanelErrorBoundary` pattern, `react-markdown` (RAG answers only).

Add, with justification:

| Addition | Why | Alternative rejected |
|---|---|---|
| `react-router-dom` | 5 real destinations, deep-linkable for demo and bug reports | conditional rendering — already the source of the workspace toggle |
| `zustand` | one frame from one socket consumed by ~15 components incl. the twin; the iframe removal makes shared state mandatory | Context re-renders every consumer at 20 Hz; prop-drilling into R3F is unworkable |
| `@react-three/fiber` + `drei` | R3F so the twin is a component with props, not a document; drei for `OrbitControls`, `useGLTF`, `Environment` — already using the imperative equivalents | keeping the iframe — blocks §14 entirely |
| `d3-scale`, `d3-shape` + own SVG (or `visx`) | scales and path maths only; synchronised axes, threshold bands and prediction bands are where chart libraries fight back | Recharts/Chart.js/ECharts |

Explicitly **not** adding: GSAP (CSS transitions + R3F's loop cover every motion in §11),
Framer Motion (one 200 ms fade already exists in Tailwind), a component library (would displace
the disciplined token set), a data-fetching library (two sockets and six REST calls),
Next.js (no SSR need; Vite is correct for a LAN-served operator console).

Backend asks — small, high leverage:

1. `GET /api/engines/{id}/history?channels=&n=` from the existing `rt.buffer`. Unblocks §15.
2. Populate `profile.to_schema()['components']` and give each fault a `target_3d_mesh`, so the
   twin's hardcoded table can be deleted.
3. Fix the cp1252/UTF-8 mojibake in `validity.explanation` and `diagnosis.causal_chain`.
4. Make `causal_chain` cylinder-aware.
5. Couple `reliability` to the active fault.
6. Emit a monotonic event id + wall-clock timestamp per detection transition, so the timeline has
   stable identity instead of the client inferring events from frame deltas.

State layout:

```ts
useEngineStore   engineId, catalog, schema, profile        // REST, 3 s poll
useFrameStore    frame, frameAgeMs, history[], trustState  // /ws/engines/{id} @20Hz
useFleetStore    fleet[]                                   // /ws/fleet
useUIStore       role, selectedCylinder, selectedComponent,
                 timeMode(live|historical), brushDomain,
                 acknowledgedEvents, twinCamera
```
Selectors only — no component subscribes to the whole frame. Throttle store writes to ~10 Hz for
UI, keep the 20 Hz path for the ring buffer and the twin's lerp target.

---

## 21. Real-Time Data Architecture

`frameAgeMs = now - lastMessageAt`, computed in the store, available to every component:

| Age | Presentation |
|---|---|
| < 200 ms | LIVE, green dot |
| 0.2–2 s | LIVE, age shown |
| 2–10 s | **STALE** — amber, values dimmed, "last good 4.2 s ago" |
| > 10 s | **DISCONNECTED** — last frame retained and greyed with a timestamp, never blanked |

Handling: missing channel → `—`, never `0`; quarantined channel (`sanity.failed_channels`) →
struck through with the advisory, and any derived value marked degraded; sensor dropout →
last-good with age, and if `suppressed_anomaly` a WARNING per §16; rapid change → no animation
suppression, but Δ-badges on the instrument; out-of-envelope → clamp the chart axis and mark the
excursion rather than rescaling the whole chart; reconnect → refetch history and splice, so no
false flat line appears across the gap (a genuine trap: a gap rendered as a straight line is a
lie about the engine).

Mode is a property of every value, not of the app. Non-negotiable: a simulated or stale reading
must never render identically to a live one. `evidence_class: "SIMULATION"` is in every frame
today — carry it into every `Metric`.

---

## 22. Responsive Design

Primary target is a 1440–1920 px laptop/desktop; a large presentation screen is the demo case.

- **≥1920 (presentation)** — layout of §12 at larger type; twin gets more height; timeline
  expands. Nothing rearranges, so a rehearsed demo does not shift.
- **1440–1920 (primary)** — the reference layout.
- **1024–1440 (laptop)** — condition column moves under the twin; KPI row 4→2 columns; timeline
  and detector stack.
- **768–1024 (tablet)** — single column in causal order: trust gate → cylinders → KPIs →
  detector → diagnosis → twin (collapsed, tap to expand). Charts keep their time axis, lose the
  brush. Scenario drawer becomes a sheet.
- **<768 (phone)** — explicitly a monitoring-only view: trust gate, cylinder instrument, KPIs,
  active alert, diagnosis summary. Twin and fault injection hidden, not shrunk. The existing
  package name (`rotax-digital-twin-mobile-gcs`) suggests mobile mattered; scope it honestly
  rather than degrading everything.

Twin behaviour: `dpr` capped at 2 and lowered on small viewports; `<768` does not mount WebGL at
all. Charts: always keep axis + limit; drop gridlines, then markers, then the brush, in that order.

---

## 23. Implementation Roadmap

Ordered so that each phase is independently demo-able and nothing is half-migrated at any commit.

**Phase 0 — Backend unblocks (0.5 d).** `/history` endpoint; `schema.components` +
per-fault `target_3d_mesh`; mojibake fix; event ids. *Files:* `backend/server/engine_api.py`,
`backend/core/profile.py`, `backend/agent/diagnostic_agent.py`, `backend/runtime/engine_runtime.py`.
*Accept:* `/history?n=1200` returns 1200 decimated frames < 200 ms; `schema.components` non-empty
for all 5 engines; no `Â`/`â€”` in any payload string. *Test:* contract test asserting every
`target_3d_mesh` resolves against a node name in the matching GLB. *Risk:* low.

**Phase 1 — Types, store, primitives (1 d).** Complete `EngineFrame` to all 20 payload fields
(the largest single win in the project — 11 fields of computed intelligence become addressable).
Add zustand stores, `frameAgeMs`, `TrustState`. Build `Panel`, `Metric`, `StatusPill`,
`DataModeChip`, `ThresholdBar`, `Provenance`. *Accept:* `tsc --noEmit` clean (it is clean today —
keep it); a debug route renders every field of a live frame; stale/disconnect simulated by killing
the socket. *Risk:* low. Do not delete anything yet.

**Phase 2 — Shell and routes (1 d).** `AppShell`, `TopBar`, `FleetStrip`, router with 5 routes;
legacy tabs mounted unchanged at their new routes. *Accept:* every existing panel still reachable
and functional; the `runtime|twin|legacy` toggle is gone; deep links work. *Risk:* medium —
`useTelemetrySocket` and `useEngineRuntime` coexist here. Plan the legacy panels' migration to the
runtime frame as Phase 6; do not attempt it now.

**Phase 3 — `TimeSeries` + charts (2–3 d).** The single highest-value phase: it adds the missing
dimension. `TimeSeries` first with shared axis, bands, markers, brush, crosshair and mode
encoding; then `Sparkline`, `CylinderBars`, `ResidualStrip`, `RULBand`, `DamageStack`,
`OrderSpectrum`. *Accept:* charts populate from `/history` on load (no empty first 15 s); 4 Hz
updates hold 60 fps with 8 charts mounted; historical/predicted/stale visually distinct in a
screenshot with no legend. *Risk:* medium — perf. Mitigate: decimate to display resolution,
`requestAnimationFrame` batching, no per-point React nodes.

**Phase 4 — Operations dashboard (2 d).** `TrustGate`, `CylinderInstrument`, `ConditionSummary`,
`DiagnosisCard`, `EventTimeline`; demote scenario controls to a drawer; wire the role lens.
*Accept:* the six-row causal chain of §18 is visible in one viewport with no scrolling at 1440 px;
`suppressed_anomaly` never renders as "Nominal". *Risk:* medium — density. Mitigate: build at
1440 px, not 1920.

**Phase 5 — Twin as a component (3–4 d, the largest risk).** Port to R3F behind a feature flag
with the iframe still available; bring over loading, lighting fit, stations, easing, exploded,
wireframe, prop; then `ThermalMaterial` from live data; then `target_3d_mesh` highlighting;
then bidirectional selection. Delete the iframe and `ENGINE_FAULT_TARGETS` only when parity is
demonstrated. *Accept:* all 5 engines load; thermal colour provably tracks `cht[]` (change a lever
and see it move); unmapped meshes grey; ≥50 fps on the 590-node `rotax_914`; clicking a mesh
filters the residual strip. *Risk:* **high** — 2,700 lines of imperative Three.js, and
`rotax_914`'s node count. Mitigate: flag, port in the order above, keep the iframe until the end,
`InstancedMesh` for fasteners.

**Phase 6 — Mission, prognostics, legacy convergence (2 d).** `/mission` (reliability, glide,
diversion — currently zero UI), `/prognostics` (damage, cycles, work packages); migrate the
legacy panels onto the runtime frame and retire `useTelemetrySocket` once nothing reads it.
*Accept:* no component reads `/ws/telemetry`; `MissionReadinessCard`/`PropulsionEngineerPanel`
content preserved, now multi-engine. *Risk:* medium — field-name mapping between the two payload
shapes. Write the mapping table before touching components.

**Phase 7 — Motion, alerts, edge states (1–2 d).** The §11 motion list and nothing else; the §16
four-level model with acknowledgement; stale/disconnect/calibrating/empty on every route;
`prefers-reduced-motion`. *Accept:* every animation traceable to a row in §11; killing the
backend mid-demo degrades legibly on all 5 routes.

**Phase 8 — Responsive, perf, polish, demo (1–2 d).** Breakpoints per §22; remove
`web/site/js/telemetry/sim-engine.js` or relabel that site as marketing; delete dead workspace
branches; rehearse §18 end to end. *Accept:* the 3.5-minute flow runs with no navigation
dead-ends and no verbal explanation; 60 fps throughout; a cold start reaches a useful screen in
< 12 s (backend calibration is ~10 s — cover it with honest skeletons, not a spinner).

Total ≈ 14–18 working days. If time is short, **Phases 0, 1, 3, 4 alone** transform the product:
they surface the 11 hidden fields and add the time dimension. Phase 5 is the biggest risk and the
biggest visual payoff — schedule it where a slip cannot threaten the demo.

---

## 24. Acceptance Criteria

Product-level, checkable:

1. Every field in `EngineRuntime.payload()` is either rendered or has a written reason not to be.
2. No screen shows a value without its unit, and none shows one with a known `operating_limit`
   without that limit.
3. LIVE / SIMULATED / HISTORICAL / PREDICTED / STALE are distinguishable in a still screenshot
   with no legend.
4. Frame age is visible at all times; a killed socket never produces confident-looking numbers.
5. `validity` and `sanity` are surfaced before the data they qualify, with a three-state warmup
   model, and `suppressed_anomaly` never renders as "Nominal".
6. Injecting a fault makes telemetry → detector → 3D → alert → timeline → diagnosis → RUL →
   reliability update coherently, in one viewport, without navigation.
7. Every 3D visual encodes live state or is labelled as geometry. The thermal view derives from
   `cht[]`/`egt[]`; unmonitored meshes are explicitly unmonitored.
8. Per-cylinder condition is visible on all 5 engines; 3D per-cylinder highlighting appears only
   where the GLB supports it and degrades visibly where it does not.
9. Every animation maps to a row in §11.
10. Every alert has a machine-derivable source, a severity, a timeline entry, and an
    acknowledgement state distinct from resolution.
11. RUL is never a bare number — always with its conformal interval.
12. No duplicate implementation of anything: one telemetry hook, one chart primitive, one set of
    tokens, one fault-target authority (`diagnosis.target_3d_mesh`), one twin.
13. `tsc --noEmit` stays clean; every panel keeps an error boundary.
14. 60 fps at 1920×1080 with the twin and 8 charts mounted, on integrated graphics.
15. A first-time viewer can answer, unaided: what is happening, is it healthy, what changed,
    why, what is predicted, what it means for the mission, and what to do.

---

## 25. Open Questions & Assumptions

**Assumptions made** (each would change the plan if wrong):
1. `frontend/` is the product; `web/site/` is marketing. If `web/site/` is the SIH demo target,
   the plan changes substantially — say so before Phase 0.
2. The primary demo surface is a laptop/large screen, not a phone.
3. The five backend engines are all in scope; the twin's 3-engine list is drift, not intent.
4. `/ws/engines/{id}` is the strategic stream and `/ws/telemetry` is to be retired.
5. Backend changes are in scope. If the backend is frozen, Phase 3 needs a client-side-only
   history buffer (charts then start empty each load — acceptable but weaker) and the twin keeps
   its hardcoded fault table.

**Questions:**
1. Is `TWIN_TRUSTWORTHY: false / confidence 0.0` on a fresh nominal run expected warmup
   behaviour, or a calibration defect? The UI treatment differs completely. **Highest-priority
   question** — it gates the most differentiating feature in the product.
2. Is the sanity module supposed to quarantine `EGT_3/CHT_3` on a genuine misfire? It suppressed
   the evidence for the fault that was actually present. Design intent or bug?
3. Are `VoiceCopilot` and the RAG diagnostic demo-critical, or supporting? Affects whether they
   stay top-level.
4. Should `evidence_class` ever be anything but `SIMULATION` — i.e. is a hardware-in-the-loop
   path planned? Determines whether the LIVE/SIMULATED distinction is decorative or load-bearing.
5. Is there a recorded sortie dataset for `/replay`, or only synthetic manifests?
6. Fixed demo hardware, and does it have a discrete GPU? Sets the Phase 5 performance budget.
