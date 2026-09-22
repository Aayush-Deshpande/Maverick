# USAvionix — Storytelling & Frontend Breakdown

**What this is:** an analysis of the USAvionix website (`usavionix.com`), studied to understand *why* it persuades so well, so ANUMAAN can pitch at the same level with its own story, assets and code.

**Evidence basis (2026-09-17):**
- **Watched the live site in Microsoft Edge**, scrolling through the entire landing experience and every product page. Captured frames are in [`usavionix_frames/`](usavionix_frames/) (internal study only).
- Page copy extracted from the archived copy in `avionix/`; scene identifiers, libraries and asset files verified in the archived bundles.
- Statements taken only from the earlier teardown notes (`avionix/README.md`), not observed directly, are marked *(teardown notes)*.

> ⚠️ **Study only.** The site, its 3D models, textures, shaders, animations, copy, frames and branding belong to USAvionix. Do not ship, deploy or adapt any of those files in ANUMAAN, and do not publish the reference frames. Learn the techniques and story structure, then build everything ourselves.

---

## 1. What USAvionix Is

A US defence-technology company selling **autonomous jet-powered ISR drones** plus the AI software that runs them. Its website is the sales pitch: one cinematic landing experience and a set of short product pages.

| Page | Product/idea | One-line positioning (their copy) |
|---|---|---|
| Home | The whole system | "Securing the skies with autonomous intelligence" |
| Delta | Hardware: jet-powered VTOL ISR drone | "A subsonic, jet-powered ISR drone built for speed, autonomy, and real-time intelligence over ranges of 300 to 500+ kilometers." |
| Phalanx AI | Command layer | "The AI command layer that unifies sensor data, coordinates autonomous fleets, and turns real-time intelligence into action." |
| Athena | Data & learning layer | "The intelligence and data foundation … built to understand the environment, extract meaning, and continuously learn." |
| SARA | Natural-language mission control | "Natural-language mission control that converts plain-English commands into real-time autonomous execution." |
| About | Why this company, why now | "Advancing autonomy to protect nations, strengthen resilience…" |
| Partners | Who should buy, and why | "Securing a large area is a problem of speed over distance." |

**Important observation:** the site does not demonstrate a working product. Detection confidences, counts and alerts are **scripted**, and the call to action is "Request Access" / "Join the waitlist". The website's job is to make you *believe the product exists and matters*, and it does that extremely well.

---

## 2. The Landing Experience, Scene by Scene

The home page is **one continuous mission told as a film**. Scrolling moves time forward, and each scroll gesture **snaps to the next scene** (observed: scroll jumps in 500-screen-height steps). The runway is 6,600 screen-heights long (verified: `6600dvh`). Scene IDs below are verified in the site bundles.

### 2.1 What you actually see

| # | Frame | Scene | Headline & caption | Visual | HUD (bottom-right, monospace) |
|---|---|---|---|---|---|
| 0 | — | **Loader** | — | Flat dark silhouette of the drone on near-black | — |
| 1 | `home_001` | `intro-scene` | **"Securing the skies with autonomous intelligence"** · "The first agent in the air, built with the speed, range, and onboard intelligence to search vast areas on its own." · pill button **Scroll To Explore ↓** | Photoreal flying-wing drone over dramatic mountain terrain, low-contrast golden-grey grade | — |
| 2 | `home_002` | `delta-drone` (label **SPECS**) | — | Camera moves to **top-down**; drone centred with **thin leader lines** to four spec callouts: *VTOL Architecture · Multi-Sensor Payload Suite · 400 km/h Top Speed · Onboard AI Compute*, each a title plus one sentence | — |
| 3 | `home_003` | `swarm-scene` (**SWARM**) | **"Understanding the Swarm System"** · "Fully autonomous ISR platform that operates and coordinates without human oversight…" | Three drones with **ID tags** (`DSA011`, `DSA012`, `DSA013`) linked by dashed lines | Key-value table: *Autonomy · Scalability · Collaboration · Coverage* |
| 4 | `home_004` | `mission-preset` (**MISSION**) | **"Mission preset"** · "Monitor a wide operational area continuously to identify tactical threats, environmental hazards, and early-stage anomalies…" · button **Start Mission ↓** | Three drones in formation over terrain | — |
| 5 | `home_005` | `flock-scene` (**SYNC**) | "Coordinated in real time, Delta units share intelligence and respond as one synchronized system." | **World changes:** terrain dissolves into a **dark tactical grid** with dozens of drone glyphs linked in a mesh network | `BOOT SEQUENCE_ · THERMAL / LIDAR / RGB / IR [ONLINE] · AI: 2 AGENTS / DUAL GPU [ACTIVE] · LINK: PHALANX SYSTEM [ESTABLISHED]` |
| 6 | `home_006` | `real-time-detection` (**DETECTION**) | **"Real-time detection"** · "Real-time detection and classification of tens of thousands of objects across the battlespace." | Back to photoreal terrain; drone flies over it while **yellow computer-vision bounding boxes** pop up with labels and confidences (`PERSON 90%`, `ROAD BLOCK 95%`, `CAMPFIRE 93%`, `POWER LINE 87%`) | `SCAN MODE: ACTIVE · COORD · ALT 1,240M │ SPEED 74 KM/H · 32 CAR / 4 TRUCK / 1 PERSON / 2 UAV` |
| 7 | `home_007` | `thermal-irregularity` | **"Thermal irregularity detected"** · "Thermal sensors detect an abnormal heat pattern and smoke, prompting an automatic alert to authorities." | Side view of the drone; a **sensor cone** projects onto the ground and connects to an **inset thermal camera feed** with a temperature scale (148 °C → 0 °C) | `ALERT: THERMAL ANOMALY · COORD · TARGET ZONE LOCKED · EMERGENCY AGENCIES NOTIFIED` |
| 8 | `home_008` | `ignition-verified` | **"Ignition verified"** · "The Delta drone reaches the anomaly and confirms active flames on the coordinates area." | Top-down photoreal settlement and roads (city terrain) | `ALERT: THERMAL ANOMALY · COORD · SIG INTENSITY: 87% · CLASSIFICATION: POTENTIAL THREAT` |
| 9 | `home_009` | `phalanx-ai` | **"Phalanx AI"** · "AI-powered command layer for autonomous drone operations and synchronized mission intelligence." | **World changes again:** abstract region outline on a dark grid, **amber** tag `SURVEY AREA`, three **amber pulsing hotspots** | `SURVEY AREA · COORD · SIG INTENSITY: 87% · ALERT: POTENTIAL THREATS` (amber) |
| 10 | `home_010` | `analysis-evaluation` (**SYS ANALYSIS**) | **"Analysis & evaluation"** · "…Delta drones can scan the area, predicting the fire spread." | Same map; white drone glyphs arrive over the hotspots | `2 DRONES ASSIGNED TO TARGET AREA · 2 WILDFIRES + 1 ROADBLOCK DETECTED` (counts in **red**) |
| 11 | `home_011` | `integrated-notifications` (**INT ALERTS**) | **"Integrated notifications"** · "Automatically notifies authorities through its integrations, keeping ground teams informed." | Hotspots turn **cyan**; tag becomes cyan `SERVICES ON SITE` | `AUTHORITIES CONTACTED · AREA STATUS: SECURED` (**cyan**) |
| 12 | `home_012` | `interdrone-coordination` (**COORDINATION**) | **"Inter-drone coordination"** · "Autonomous coordination between agents to expand coverage and reinforce critical zones." | Camera pans wider: a second region appears with **amber** `SENSITIVE AREA` | Status stack carried over from previous scene |
| 13 | `home_013` | `extra-support` | "The swarm detects the need for extra support and deploys another drone to stabilize and secure the zone." | Region turns **red** `ALERT AREA`; a **red 3D power-station model** rises from the map; a drone flies in | `DRONE ASSIGNED TO TARGET AREA · CONFIRMED ON LOCATION · WILDFIRE NEAR ELECTRICAL STATION` (**red**) |
| 14 | `home_014` | `multi-threat-response` (**RESPONSE**) | **"Multi-threat response"** · "Complete awareness across entire area of a complex multi-site threat…" | Zoom out: five regions, all **cyan** — `ZONE STABILIZED`, `AREA SECURED`, `AREA CONTAINED`, `SERVICES ON SITE` | — |
| 15 | `home_015` | Scenario cards → globe | "One platform, many missions": image cards *Wildfire Cascade · Border Storm · Critical Infrastructure in Crisis* → **"USAvionix covers vast areas and long distances across real-world missions, proving its versatility in critical operations."** | Dark **wireframe globe** with a single cyan marker `FLOOD AREA SECURED` | — |
| 16 | `home_016` | Credibility | "Founded by leaders from SpaceX, Apple, Tesla, Palantir, JPL, and elite military units…" | Logo wall (SpaceX, Apple, Tesla, Palantir, Skycatch, Navy SEAL insignia, Google, JPL) | — |
| 17 | `home_017` | Close | **"Ready to talk to us?"** · **Contact Us →** | Giant outlined wordmark behind a top-down **3D render of the drone standing on its VTOL legs** | — |

### 2.2 The narrative arc

```text
LOADER ─► PROMISE ─► HERO SPECS ─► SCALE (swarm) ─► MISSION ASSIGNED ─► SYSTEM SYNC
   ─► DETECTION ─► ANOMALY ─► CONFIRMATION ─► BRAIN REVEAL ─► ANALYSIS
   ─► HUMANS NOTIFIED (resolved) ─► NEW THREAT ─► ESCALATION HANDLED
   ─► EVERYTHING SECURED ─► "WORKS EVERYWHERE" ─► WHO WE ARE ─► CALL TO ACTION
```

A classic **problem → tension → resolution** arc where the "character" is the system and each plot beat *is* a product capability. The viewer never reads a feature list; they watch the features resolve a crisis. The tension even **escalates twice** (thermal anomaly, then wildfire near a power station) before the final resolution.

### 2.3 Product pages: one fixed template

Observed on Delta, Phalanx AI, Athena and SARA:

- **Left column:** large product name → one bold sentence → one supporting paragraph → **three pillars** as a two-column table (two-word title | one sentence)
- **Right side:** a single visual that *demonstrates* the idea
  - Delta: top-down studio render of the aircraft
  - Phalanx AI: monochrome drone network on a grid map
  - Athena: drones over a map with **tracked-entity labels** (`EVENT E-17 · RENDEZVOUS FORMING · CONF 0.90`, `VEHICLE B7 · 44KM/H NW`, `INTRUDERS (5) · HOLDING`)
  - SARA: a **chat UI carousel** ("Show me the most likely targets" → answer with coordinate chips)
- **Footer:** "Ready to talk to us?" + Contact Us

Naming each architecture layer (Delta, Phalanx, Athena, SARA) turns an abstract stack into a cast of characters people can remember.

### 2.4 About page: the "why now" argument

A night-city photo with the drone, and three rows:

| Heading | Argument | Pattern |
|---|---|---|
| **The Economics** | Covering large areas with crews scales with every square mile; autonomy doesn't | *The old way costs more every year* |
| **The Inflection** | Onboard compute can now run serious models in the air | *Something just became possible* |
| **The Flywheel** | Every flight feeds Athena; the system gets smarter with every deployment | *We improve faster than anyone else* |

### 2.5 Partners page: problem framing

"When Conventional Coverage Breaks Down" lists the buyer's *own* pain as bullets; "Where It Works" shows eight use-case chips; the call to action is "Join the waitlist" with scarcity ("a handful of founding partners").

---

## 3. The Visual Grammar

This is what makes the site feel expensive and coherent. All of it was observed directly.

### 3.1 Two worlds

| World | Scenes | Look | Meaning |
|---|---|---|---|
| **Physical world** | 1–4, 6–8 | Photoreal terrain, photoreal aircraft, cinematic grade | *What is really out there* |
| **System world** | 5, 9–14, globe | Near-black background, fine grid, thin white outlines, glowing points, glyph-style drones | *How the system understands it* |

The story **cuts between them** at meaningful moments: into the system world when the fleet syncs, back to reality for detection, and into the system world for good once the AI takes command. This duality is the single most transferable idea for ANUMAAN: **real engine ↔ digital twin**.

### 3.2 Fixed screen layout in every scene

```text
┌──────────────────────────────────────────────────────────────┐
│ SECTION LABEL + tick ruler (progress)            [Contact] ≡ │
│                                                              │
│ Headline                                                     │
│ (2–4 words, very large)                                      │
│                                                              │
│                  3D / visual centre stage                    │
│                                                              │
│ One caption sentence                     MONOSPACE HUD BLOCK │
│ (bottom-left)                            (bottom-right,      │
│                                           3–4 lines)         │
└──────────────────────────────────────────────────────────────┘
```

The viewer always knows where to look: **headline → visual → caption → data.**

### 3.3 Colour as story state

| Colour | Meaning on the site |
|---|---|
| White / grey | Neutral: structure, labels, normal |
| **Amber** | Attention: detected, survey area, sensitive area |
| **Red** | Critical: alert area, wildfire counts, near-infrastructure danger |
| **Cyan** | Resolved: services on site, area secured, zone stabilized |

The same region **changes colour as the story progresses** (amber → cyan, amber → red → cyan). Colour alone tells you whether the situation is getting better or worse.

### 3.4 Recurring visual devices

| Device | Where | Why it works |
|---|---|---|
| **Leader-line spec callouts** | Specs scene | Ties every claim to a physical part of the aircraft |
| **Entity ID tags** (`DSA011`) | Swarm | Makes units feel real and individually tracked |
| **Bounding boxes with confidence %** | Detection | Borrowed from real computer-vision UIs; instantly reads as "AI at work" |
| **Sensor cone + inset sensor feed** | Thermal | Connects the aircraft to what its sensor sees |
| **Pulsing hotspots** | System-world scenes | Draws the eye to exactly one thing |
| **3D object rising from the map** | Extra support | Escalation made physical |
| **Status-stack HUD** that accumulates lines | Scenes 9–13 | A running log that shows progress over time |
| **Mid-story button** (`Start Mission`) | Mission preset | Invites participation, not just watching |
| **Globe with one marker** | After the story | Scale beyond the single incident |
| **Logo wall** | Close | Borrowed credibility |
| **Hero product render on legs** | Footer | Ends on the tangible product |

### 3.5 Typography and tone

- Large, tightly set grotesk sans for headlines; small monospace uppercase for HUD
- Sentence-case captions, one sentence each
- Muted, desaturated photography; colour reserved almost entirely for state
- Generous negative space; nothing competes with the centre visual

---

## 4. Why It Persuades: Principles

| # | Principle | How USAvionix does it |
|---|---|---|
| P1 | **Show a mission, not features** | One incident carries every capability |
| P2 | **The viewer controls time, in fixed beats** | Scroll = time, but each gesture snaps to the next scene, so nobody gets lost mid-transition |
| P3 | **Never cut to a new page** | One continuous camera from hero to close |
| P4 | **Two worlds** | Reality vs the system's model (§3.1) |
| P5 | **Same layout every scene** | Headline, visual, caption, HUD (§3.2) |
| P6 | **Colour is state** | Amber → red → cyan (§3.3) |
| P7 | **Narrate with instrument text** | Terse monospace HUD, coordinates, percentages, IDs |
| P8 | **Quantify every claim** | Confidences, counts, speeds, temperatures |
| P9 | **Escalate before resolving** | Two escalations before "secured" |
| P10 | **Generalize at the end** | Scenario cards and globe prove breadth |
| P11 | **Named layers** | Delta / Phalanx / Athena / SARA |
| P12 | **Why now** | Economics, inflection, flywheel |
| P13 | **Ruthless copy economy** | Headlines 2–5 words, one caption sentence, three pillars |
| P14 | **Performance is part of the story** | Smooth, snapping 3D signals engineering quality |

---

## 5. How It Is Built

### 5.1 Stack (verified from the archive)

| Layer | Evidence |
|---|---|
| **Next.js** | `_next/` bundle structure |
| **Three.js / WebGL** | GLB models loaded into full-screen canvas scenes |
| **Lenis** smooth scroll with scene snapping | `lenis` referenced in bundles; snapping observed live |
| **Draco** mesh compression | `draco/` decoder with a `.wasm` binary |
| **Web fonts** | 11 `.woff2` subsets |

### 5.2 Assets (verified file sizes)

| Asset | Size | Role (matched to observed scenes) |
|---|---|---|
| `terrain.glb` | 2.09 MB | Mountain terrain (scenes 1–4, 6–7) |
| `city-terrain.glb` + `city.webp` | 438 KB + 573 KB | Settlement in "Ignition verified" (scene 8) |
| `delta-pbr.glb` | 965 KB | Hero aircraft |
| `delta-lowpoly.glb` | small | Swarm/glyph drones |
| `loading-delta.glb` | 140 KB | Loader silhouette |
| `camera-animations.glb` / `-mobile.glb` | 28 KB / 17 KB | **Camera paths authored in Blender**, desktop and mobile framings |
| `drone-animations.glb` / `-mobile.glb` | 16 KB / 15 KB | Drone flight paths |
| `grid.glb`, `grid-city.glb` | ~33 KB each | System-world grid maps (scenes 9–14) |
| `power-station.glb`, `building.glb` | 20 KB, 11 KB | The red power station rising in scene 13 |
| `earth_outline.webp`, `earth_normal.webp` | 64 KB, 44 KB | Wireframe globe |
| `fire.webp`, `wind.webp`, `noise.webp` | 110–686 KB | Effects |
| `env.exr` | 149 KB | Environment lighting |
| `logos.webp` | 10 KB | Logo wall |
| 96 × `.avif` frames | ≈ 3.5 MB | Pre-rendered image sequence |

**Total ≈ 13.7 MB** for the whole cinematic experience *(teardown notes)*. That budget is one of the most transferable lessons.

### 5.3 Key techniques

| Technique | What it does | Why it matters |
|---|---|---|
| **Scroll runway + scene snapping** | A tall invisible spacer makes the page scrollable; a fixed full-screen canvas sits on top; scroll maps to per-scene progress and snaps to scene boundaries | Scroll becomes a controlled timeline |
| **Blender-authored animation scrubbing** | Camera and drone motion keyframed in Blender on empties, exported as tiny animation-only GLBs, scrubbed by scene progress | Cinematic control with almost no code; exactly repeatable |
| **Separate desktop/mobile camera rigs** | Different animation files per aspect ratio | Composition holds on phones |
| **Baked terrain lighting** | Lighting stored in textures *(teardown notes)* | Large landscapes render fast |
| **Compressed GLBs + WebP textures** | Draco geometry, compact textures | Small downloads |
| **Tiny, reusable props** | A 20 KB power station and 11 KB building do real storytelling work | Big narrative effect, negligible cost |
| **Screen-space grid & outline shaders** | Crisp system-world lines at any zoom *(teardown notes for shader details)* | The system world always looks clean |

---

## 6. What Does **Not** Transfer to ANUMAAN

| USAvionix context | ANUMAAN context | Consequence |
|---|---|---|
| Marketing site for buyers browsing alone | **SIH evaluation**: short timed sessions with judges, usually a laptop or projector | The story must be **presentable**: keyboard-driven, pausable, fits in minutes |
| Scripted confidences and counts are acceptable in advertising | **DRDO technical evaluators** probe whether the system works | **Every number on screen must come from our system**: live run or recorded replay |
| Demo gated behind "Request Access" | The PS requires a **functional prototype** | The story must **end in the live working system** |
| Visible threats: fire, vehicles, intruders | Engine degradation is **invisible**, inside metal | We need devices that make internal state visible (see blueprint §1.3) |
| Logo wall of famous employers | A student team | Credibility comes from **evidence**: DRDO requirement traceability, cited sources, measured evaluation results |
| Their assets, shaders, copy, frames, brand | Not ours | Build from our own Blender models (Rotax 912 iS, TB3, PD170, AE330) and our own code |

Continue with [02_anumaan_pitch_blueprint.md](02_anumaan_pitch_blueprint.md) for how to apply this to ANUMAAN.
