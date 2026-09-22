# ANUMAAN — Pitch & Storytelling Blueprint

**Purpose:** how to pitch ANUMAAN at the storytelling and frontend quality level of USAvionix, adapted for a DRDO/SIH technical evaluation. Read [01_usavionix_breakdown.md](01_usavionix_breakdown.md) first.

**The one rule that separates us from a marketing site:**

> **Cinematic, but every number is real.** Each value shown in the story comes from ANUMAAN itself, from a live run or a recorded replay of the system, never typed into the frontend.

USAvionix can script "87%" because it is selling. DRDO evaluators are testing. A beautiful story built on real system output is both more impressive and impossible to dismiss.

---

## 1. What We Are Actually Pitching

### 1.1 The core message

**Headline options** (pick one; all ≤ 8 words):

| Option | Angle |
|---|---|
| "Know the engine will fail — before it does." | Prediction |
| "Every failing engine whispers first. ANUMAAN listens." | Early signal |
| "The engine's twin sees what gauges can't." | Twin vs thresholds |

**Supporting sentence:** *"An indigenous digital twin that watches every aero piston engine in India's MALE UAV fleet, predicts failures hours ahead, and tells the operator what to do."*

### 1.2 The single idea the audience must remember

**Thresholds say "normal" until it's too late. The twin sees the gap between what the engine *is* doing and what it *should* be doing, and that gap opens hours earlier.**

Every scene either builds towards, shows, or proves this idea.

### 1.3 The hidden-problem challenge

USAvionix's threats are visible: fire, vehicles, intruders. Engine degradation is **invisible**, happening inside metal. The story needs visual devices that make internal state visible:

| Device | What it shows |
|---|---|
| **Real vs Twin split** | Photoreal engine (reality) beside a holographic ghost engine (the twin's model) |
| **Residual trace** | A line that should sit at zero, the gap between actual and expected, rising before any limit |
| **Threshold gauge vs twin score** | The same moment shown twice: gauge green "NORMAL", twin amber "ANOMALY" |
| **Thermal overlay** | CHT/EGT mapped as colour onto cylinders, so one cylinder visibly runs different |
| **Fault highlight** | The failing component glows; everything else goes translucent |
| **RUL band** | Time remaining as a shrinking band compared against distance to base |

### 1.4 Their devices → our equivalents

Each device observed on USAvionix ([breakdown §3.4](01_usavionix_breakdown.md)) has a direct ANUMAAN counterpart:

| USAvionix device | ANUMAAN equivalent |
|---|---|
| Photoreal world ↔ tactical grid world | **Photoreal engine/aircraft ↔ holographic twin world** (engine schematic on a dark grid: subsystems as outlined blocks, sensors as points, oil/fuel/coolant flows as animated lines) |
| Leader-line spec callouts on the aircraft | Leader lines from Rotax 912 iS parts to specs (dual-lane FADEC, dry-sump oil tank, 2.43 gearbox, per-cylinder CHT/EGT sensors) |
| Entity ID tags (`DSA011`) | Tail numbers on fleet aircraft; sensor channel IDs on the engine (`CHT_3`, `OIL_PRESS`) |
| Bounding boxes with confidence % | **Residual badges on sensors**: each sensor point shows actual vs expected and a deviation score |
| Sensor cone + inset thermal feed | Line from a component to an **inset live trace** (oil pressure, EGT₃) with its limit band |
| Pulsing amber hotspot | The degrading component pulsing amber in the twin world |
| 3D power station rising from the map (escalation) | The failing **cylinder #3 lifting out of the engine** (exploded view) as the diagnosis locks in |
| Accumulating status-stack HUD | Accumulating **diagnostic log**: first signal → classification → RUL → advisory |
| Mid-story `Start Mission` button | **`Inject fault` button**: a real call to the backend, then the story continues on live data |
| Globe with one marker | **India map** with MALE UAV bases and fleet health dots |
| Logo wall of famous employers | **Evidence wall**: DRDO PS-26054, 83 traced requirements, USAF accident report, Rotax datasheet, evaluation metrics |
| Hero product render on legs (close) | Aircraft on the ground at base, engine glowing cyan (healthy), "Ready for next sortie" |

---

## 2. The Story Script

A single mission, told as a film, driven by **recorded ANUMAAN output**. It is inspired by the real 2011 MQ-1B Djibouti loss ([textbook Ch. 1 §1.4](../../compiled_tb/01_the_problem_and_mission.md)), where erratic oil pressure preceded engine seizure by ~2 h 47 min.

Placeholders like `{{EVAL.lead_time_cyl3}}` must be filled from the evaluation harness ([gap plan G03](../gap_plan.md)). **Do not replace them with invented numbers.**

| # | Scene ID | Story beat | Visual | HUD / narration (draft) | Data source |
|---|---|---|---|---|---|
| 0 | `boot` | **The twin comes online** | Dark screen, engine wireframe assembling | `ANUMAAN TWIN · BOOT` · `ENGINE: ROTAX 912 iS · LINK ESTABLISHED` · `27 CHANNELS @ 20 Hz` · `PHYSICS MODEL: SYNCED` | Static config + live `api/health` |
| 1 | `promise` | **The promise** | MALE UAV over Himalayan terrain at dawn | Headline + supporting sentence (§1.1) | — |
| 2 | `stakes` | **Why it matters** | Camera pulls back to a map; long sortie track | `SINGLE ENGINE` · `24–45 h SORTIES` · `POWER PLANT: 41% OF MILITARY UAV FAILURES` (cite source on screen) | Textbook Ch. 1 references |
| 3 | `aircraft` | **Meet the aircraft** | Airframe fly-by; skin turns to X-ray | `ALT 25,000 FT` · `OAT −31 °C` · `T+14:02 INTO SORTIE` | Replay frame |
| 4 | `engine` | **Meet the engine** | Zoom into engine; subsystem callouts | `100 hp · 1,352 cc · DUAL-LANE FADEC · TBO 2,000 h` | Rotax datasheet |
| 5 | `twin` | **Two engines: one real, one virtual** | Split screen: photoreal ↔ holographic twin, residual line flat at zero | "They should agree. When they don't, something is changing." | Live/replay residuals |
| 6 | `normal` | **All normal** | Calm cruise; subsystem health rings full | `HEALTH 0.98` · `ANOMALY 0.04` · `GO` | Replay |
| 7 | `whisper` | **The first whisper** *(key money shot)* | Oil pressure dips momentarily. Left: threshold gauge **green**. Right: twin residual rising | `THRESHOLD: NORMAL` vs `TWIN: ANOMALY {{EVAL.score}}` | Replay at first detection |
| 8 | `diagnosis` | **It's cylinder 3** | Cylinder #3 glows; others go ghost; EGT₃ trace drops while MAP, RPM, oil pressure shift | `CYL #3 COMBUSTION LOSS` · `CONFIDENCE {{EVAL.conf}}` · trigger signals listed | Classifier output + trigger signals |
| 9 | `prediction` | **How long do we have?** | RUL band shrinking; distance-to-base arc beside it | `RUL p50 {{EVAL.rul_p50}} · p10 {{EVAL.rul_p10}}` · `BASE: 1 h 50 min` | Prognostics output |
| 10 | `decision` | **What should we do?** | Advisory card; route redraws to a nearer airfield | `ADVISORY: REDUCE POWER · DESCEND · DIVERT` | Recommendation output |
| 11 | `resolution` | **Aircraft recovered** | Landing; engine cools; work order printed | `ASSET RECOVERED` · `WORK ORDER #… · INSPECT CYL #3 · OIL SYSTEM DEBRIS CHECK` | Maintenance module |
| 12 | `counterfactual` | **Without the twin** | Same timeline in greyscale; threshold alarm fires only at the end | "Threshold alarm: {{EVAL.threshold_time}}. Twin warning: {{EVAL.twin_time}}. **{{EVAL.lead_time}} earlier.**" | Threshold baseline from evaluation harness |
| 13 | `replay` | **Every flight is evidence** | Timeline scrubber; jump to "first detectable signal" marker | `FIRST SIGNAL T−{{EVAL.lead_time}}` | Replay engine |
| 14 | `before_flight` | **Tomorrow's mission, tested tonight** | Same engine simulated on Ladakh cold/high vs Thar hot/low profiles | `LADAKH 30 h: GO` · `THAR 30 h: CAUTION: COOLING MARGIN` | Mission simulation |
| 15 | `fleet` | **Every engine in the fleet** | Grid of aircraft tiles, health-coloured | "87 indigenous MALE drones approved. Every one with an engine that has no service history yet." | Fleet view + Ch. 1 references |
| 16 | `architecture` | **How it works** | Named layers assemble (§3) | 5 layers, one line each | — |
| 17 | `proof` | **Measured, not claimed** | Metric cards | `LEAD TIME vs THRESHOLDS` · `FALSE ALARMS / 10 FH` · `RUL INTERVAL COVERAGE` · `83 PS REQUIREMENTS TRACED` | Evaluation report |
| 18 | `live` | **Now, live** | Button → the real ANUMAAN dashboard | "Launch the live twin" | Live backend |

### 2.1 Two worlds and fixed layout

Assign every scene to one world, as USAvionix does:

| World | Scenes | Look |
|---|---|---|
| **Physical** | 1–4, 11 | Photoreal aircraft, engine and Himalayan terrain; cinematic grade |
| **Twin** | 0, 5–10, 12–17 | Near-black grid, outlined engine schematic, glowing sensor points, animated flow lines, monospace data |
| **Live system** | 18 | The real ANUMAAN dashboard, styled with the same design system |

The switch into the twin world at scene 5 is the pitch's thesis made visual: *"this is the engine as the twin sees it."*

Keep the observed layout in **every** scene: section label with progress ticks (top-centre), large 2–5-word headline (top-left), visual centre stage, one caption sentence (bottom-left), monospace HUD block of 3–4 lines (bottom-right).

### 2.2 Narrative rules

1. **Scene 7 is the heart of the pitch.** Rehearse it; give it the most time.
2. **Always show the counterfactual** (scene 12). The value of prediction is only visible against what would have happened.
3. **Cite sources on screen** for real-world numbers (scene 2, scene 15): small footnote text, like a documentary.
4. **Separate real-world facts from demo data** visually, e.g. a `RECORDED REPLAY · SYNTHETIC ENGINE` tag while synthetic data is used. Honesty increases credibility with technical judges.
5. **End in the live system** (scene 18). The cinematic part earns attention; the live system earns belief.

---

## 3. Named Architecture Layers

Following the Delta/Phalanx/Athena/SARA pattern, give each ANUMAAN layer a memorable name. **These are suggestions only**; agree on names as a team before using them anywhere public.

| Layer | Suggested name | Meaning | Maps to |
|---|---|---|---|
| Data acquisition & telemetry | **NADI** | "Pulse" | Ingestion, CAN, telemetry stream |
| Physics & performance model | **TATTVA** | "Fundamental principle" | Thermodynamic model, performance maps |
| Detection, diagnosis, RUL | **ANUMAAN** (core) | "Inference" | Anomaly detection, classifier, prognostics |
| Simulation | **KALPANA** | "Imagination" | Mission profiles, what-if simulation |
| Memory, replay, fleet learning | **SMRITI** | "Memory" | Replay engine, mission history, adaptive learning |
| Advisory & copilot | **SAARTHI** | "Guide / charioteer" | Recommendations, maintenance advisory, copilot |

Product-page template for each layer (same as USAvionix): **Name · one sentence · three pillars.**

---

## 4. Pitch Formats

The same scene system should produce four outputs, so the story is built once:

| Format | Use | How |
|---|---|---|
| **Presenter mode** | Live pitch to judges | Full-screen web app; ← / → keys step scenes; each scene plays its transition then holds; `P` pauses; `L` jumps to live dashboard |
| **Scroll mode** | Shareable link, portfolio | Same scenes on a scroll runway, like USAvionix |
| **Video** | Backup if the venue laptop/GPU fails; submission video | Screen-record presenter mode, or render scenes from Blender with Cycles |
| **Slides** | Fallback and printed handout | Export one still per scene with its HUD text |

**Why presenter mode first:** scrolling through a 3D experience on a projector while talking is awkward and error-prone. Judges see a controlled film with a narrator. Scroll mode is a bonus.

### 4.1 Suggested pitch timing (adjust to the actual round format)

| Time | Content | Scenes |
|---|---|---|
| 0:00–0:30 | Hook: promise and stakes | 0–2 |
| 0:30–1:15 | The system: aircraft, engine, twin | 3–6 |
| 1:15–3:15 | The incident | 7–12 |
| 3:15–4:00 | Replay and pre-flight simulation | 13–14 |
| 4:00–4:45 | Fleet, architecture, proof | 15–17 |
| 4:45–end | **Live system**: inject a fault, watch the twin catch it | 18 |

---

## 5. Frontend Architecture

### 5.1 Two surfaces, one design system

```text
┌──────────────────────────────┐    ┌──────────────────────────────┐
│  STORY  (new)                │    │  OPERATIONS  (existing       │
│  Presenter / scroll film     │    │  frontend/, extended)        │
│  Scenes · camera · HUD       │    │  Live dashboard, role views  │
└──────────────┬───────────────┘    └──────────────┬───────────────┘
               │   shared: design tokens, HUD components, telemetry types,
               │   3D engine/airframe viewer, fault-visual contract
               └────────────────────┬──────────────────────────────┘
                                    ▼
                      ANUMAAN backend (live /api/state, /ws)
                      Recorded replays (api/replay/…) → story timelines
```

- **Story** is a new app (e.g. `frontend-story/`), or a route in the existing app.
- **Operations** is the current `frontend/` (React 18 + Vite + Tailwind, no 3D yet). It gains an embedded 3D twin viewer that reuses the story's 3D components.
- Both import the same **HUD component library** and **telemetry TypeScript types**, so a value looks identical in the film and in the live dashboard. That continuity is what makes scene 18 land.

### 5.2 Recommended stack

| Need | Choice | Notes |
|---|---|---|
| App | **Vite + React + TypeScript** | Matches the existing frontend; no need for Next.js since there's no SEO/server rendering requirement |
| 3D | **three.js + React Three Fiber + drei** | With React 18 use **R3F v8 / drei v9**; R3F v9 requires React 19 |
| Scroll mode | **Lenis** (package `lenis`) | Same smooth-scroll approach as USAvionix |
| Timeline & tweening | **GSAP**, or a small custom timeline driven by scene progress | Presenter mode needs time-based playback, not only scroll |
| State | **Zustand** | Scene progress, active scene, replay cursor |
| Post-processing | `@react-three/postprocessing` (bloom, vignette, noise) | Use sparingly; bloom for fault glow |
| Charts in HUD | Lightweight SVG/Canvas (hand-rolled or visx) | Residual traces, RUL bands |
| Offline | All assets and fonts served locally | **Evaluation venues may have no internet** |

### 5.3 Scene configuration (one source for all four formats)

```jsonc
// story/scenes.json
[
  {
    "id": "whisper",
    "title": "The first whisper",
    "weightVh": 500,                         // scroll mode length
    "durationSec": 12,                       // presenter mode length
    "cameraClip": "cam_whisper",             // clip name in camera-animations.glb
    "cameraClipMobile": "cam_whisper_m",
    "visual": { "engineMode": "split_real_twin", "highlight": null, "thermalOverlay": true },
    "hud": [
      { "type": "gauge", "label": "OIL PRESS", "bind": "replay.telemetry.OIL_PRESS", "threshold": "limits.OIL_PRESS" },
      { "type": "score", "label": "TWIN ANOMALY", "bind": "replay.analytics.anomaly_score" }
    ],
    "timeline": { "replay": "story_cyl3_oil_debris", "fromSec": 49320, "toSec": 49410 },
    "caption": "Threshold says normal. The twin disagrees.",
    "sources": []
  }
]
```

`bind` paths read from a **recorded replay** exported by the backend. The frontend never contains hand-typed telemetry values.

### 5.4 Story data pipeline

```text
Evaluation scenario (virtual engine + injected fault, fixed seed)
        │
        ▼
ANUMAAN backend processes it exactly as in live operation
        │
        ▼
report_dump/<mission>/  (readings, analytics, faults, predictions, actions)
        │  export script: select window, downsample to 10–20 Hz, add event markers
        ▼
story/timelines/story_cyl3_oil_debris.json   (versioned, reproducible)
        │
        ▼
Story app HUD + 3D fault visuals bind to it
```

**Dependency:** the numbers are only meaningful once gaps **G01–G03** are closed (independent virtual engine, controls driving physics, evaluation harness). Build the story app in parallel, but lock scene 7–12 numbers only from post-G03 evaluation runs.

---

## 6. 3D Asset Pipeline: Blender → Web

### 6.1 Pipeline

```text
1. Source .blend (existing)          rotax_912_is_sport.blend, bayraktar_tb3.blend,
                                     tei_pd170.blend, austro_ae330.blend, terrain.blend
        │
2. Web variant (script, never by hand)
   ├─ Decimate to web budget (§6.2), keep fault-addressable object names
   ├─ Bake AO/lighting for static parts; bake terrain to unlit textures
   ├─ Merge non-fault parts to reduce draw calls
   ├─ Add custom properties (twin_component, twin_sensor_channel)
        │
3. Export glTF binary (.glb) from Blender
   ├─ +Y up, apply modifiers, materials, include Custom Properties → glTF "extras"
   └─ separate exports: model GLBs, camera-animation GLBs (desktop + mobile)
        │
4. Optimize with glTF-Transform (CLI)
   ├─ prune, dedup, weld, resample animations
   ├─ geometry compression: meshopt or Draco
   └─ textures: WebP (or KTX2) at web resolutions
        │
5. Validate
   ├─ glTF Validator: no errors
   ├─ size budget check
   └─ name check: every fault target in the manifest exists as a node name (same rule as rendering_guide C1)
        │
6. Load in React Three Fiber (useGLTF), set MeshoptDecoder/DRACOLoader
   └─ custom properties arrive in object.userData
```

Verify exact glTF-Transform command flags with `gltf-transform --help`, as options change between versions.

### 6.2 Web budgets (proposed)

| Asset | Triangles | GLB size | Notes |
|---|---|---|---|
| Hero engine (Rotax 912 iS) | ≤ 300 k | ≤ 6 MB | Source is 2.0 M tris; must decimate non-fault parts aggressively |
| Airframe | ≤ 100 k | ≤ 4 MB | |
| Terrain (Himalaya / Ladakh) | ≤ 200 k | ≤ 4 MB | Baked unlit; 2–4K texture |
| Camera/animation GLBs | — | ≤ 100 KB each | Animation-only files |
| **Whole initial load** | — | **≤ 20 MB** | USAvionix ≈ 13.7 MB; lazy-load later scenes |

### 6.3 Animation authoring

- Author camera moves in Blender on **empties**, one action per scene, named to match `cameraClip` in `scenes.json`.
- Export animation-only GLBs; the web app sets the clip's time from scene progress (scroll) or playback time (presenter).
- Author a **mobile variant** for portrait framing if scroll mode must work on phones.
- Mechanisms (gear, propeller) follow the rendering guide's rule: driven by properties, not the global timeline.

### 6.4 Fault visuals on the web (same contract as Blender)

| Twin state | Web implementation |
|---|---|
| Fault highlight | Clone the target mesh's material, set `emissive` colour/intensity by severity; bloom picks it up |
| Ghost mode | Non-target meshes: transparent fresnel material, depth-write off |
| Sensor suspect | Striped/flickering material on `Sensor_*` meshes only |
| Thermal overlay | Vertex-colour or shader uniform mapping CHT/EGT to a colour ramp per cylinder |

Use the object names from the engine manifest (`manifests/engines/*.json` once created). The web viewer and the Blender controller then share one fault-to-mesh mapping.

### 6.5 Fallbacks

- Pre-render key scenes in Blender (Cycles) as **image sequences (AVIF/WebP)** and **MP4**.
- Presenter mode detects low frame rate and swaps to the pre-rendered sequence for that scene.
- Keep the full pitch video on the presentation laptop's local disk.

---

## 7. Visual Design System

### 7.1 Colour as story state

USAvionix uses colour only for state and changes a region's colour as the story progresses (amber → red → cyan). Use the same idea, aligned with cockpit alerting conventions that aerospace judges read instinctively:

| State | Colour | Use only for | Story progression example |
|---|---|---|---|
| Neutral / structure | White / light grey | Outlines, labels, values | Engine schematic at rest |
| Healthy / resolved | **Cyan** | Nominal twin, "asset recovered", fault cleared | Scene 6, scene 11 |
| Caution | **Amber** | Degradation, anomaly, early warning | Scene 7 (first whisper) |
| Warning | **Red** | Critical fault, immediate action | Scene 8–9 (diagnosis, short RUL) |
| GO / NO-GO labels | Green / red text only | Pre-flight readiness badges | Scene 14 |
| Base | Near-black blue-grey | Backgrounds | All twin-world scenes |

The failing component should visibly travel **cyan → amber → red → cyan** across the pitch. That colour journey alone tells the story.

**Brand accent:** do **not** use saffron or orange as a decorative brand colour; it collides with caution-amber. Express Indian identity through the programme context, typography of the name (अनुमान), and terrain (Ladakh, Thar), not through alert-like colours.

### 7.2 Typography

- **Display/headlines:** a clean grotesk sans, large, tight tracking (similar weight to USAvionix's).
- **HUD/telemetry:** a monospace font with tabular numerals so digits don't jitter as values change.
- **Devanagari:** one typeface for the "अनुमान" wordmark only.
- Self-host all fonts (offline venues).

### 7.3 HUD language

- Uppercase, terse, units always shown: `OIL PRESS 2.1 BAR`, `CYL #3 EGT −46 °C Δ`.
- Timestamps as mission time: `T+14:02:37`.
- Confidence and uncertainty always shown with predictions: `RUL p50 2 h 10 m (p10 1 h 25 m)`.
- One idea per HUD block; no paragraphs.

### 7.4 Projector reality

- Dark UIs wash out on projectors. Test on an actual projector; raise contrast and text size (HUD text ≥ 18 px at 1080p).
- Thin 1 px lines disappear; use ≥ 2 px for traces and outlines.
- Avoid meaning carried only by red vs green; add icons/labels for colour-blind viewers.

---

## 8. What Not To Do

| Don't | Why |
|---|---|
| Copy USAvionix assets, shaders, animations, copy or layout wholesale | Not ours; recognizable; undermines "indigenous" |
| Show any number not produced by our system | Technical judges will ask; one fabricated number discredits everything |
| Spend 5 minutes of cinematics before showing the working system | The PS requires a functional prototype; keep the film short and end live |
| Depend on internet, CDNs or a remote GPU at the venue | Venues are unpredictable |
| Rely on scroll-jacking during a live pitch | Use presenter mode |
| Put 3D polish ahead of G01–G03 | A stunning story about an unproven twin is a liability under questioning |
| Claim ANUMAAN "would have saved" the 2011 Predator | Unknowable. Say it shows the pattern ANUMAAN is designed to catch |

---

## 9. Build Plan

| Phase | Deliverable | Depends on |
|---|---|---|
| **S1 Story lock** | Final script, scene list, headline, layer names; storyboard sketches per scene | Team agreement |
| **S2 Design system** | Colour tokens, fonts, HUD components (gauge, score, trace, RUL band, advisory card) in a shared package; applied to the existing dashboard | S1 |
| **S3 3D web viewer** | Rotax 912 iS web GLB + R3F viewer with fault highlight, ghost, thermal overlay, driven by live `api/state` | Asset pipeline §6 |
| **S4 Presenter app** | Scene engine (keys, playback), camera clips from Blender, HUD bound to a sample timeline | S2, S3 |
| **S5 Real timelines** | Story timelines exported from evaluation runs | **Gaps G01–G03** |
| **S6 Scenes polish** | Terrain, airframe, split real/twin view, counterfactual scene, proof cards | S4, S5 |
| **S7 Fallbacks & rehearsal** | Pre-rendered sequences, pitch video, projector test, timed rehearsals | S6 |
| **S8 Scroll mode** (optional) | Lenis runway version for sharing | S6 |

### 9.1 Definition of done for the pitch

- [ ] Story runs fully offline on the presentation laptop at ≥ 50 FPS
- [ ] Every on-screen number traceable to a timeline file produced by the backend
- [ ] Scene 7 (threshold vs twin) and scene 12 (counterfactual) use evaluation-harness results
- [ ] Transition from scene 18 to the live dashboard works in one keypress
- [ ] Live fault injection demo rehearsed with a fallback replay if the live run misbehaves
- [ ] Pitch video exported and stored locally
- [ ] Tested on a projector; text readable from the back of a room
- [ ] Every real-world statistic on screen shows its source
