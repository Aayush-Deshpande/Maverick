# Deliverables, Validation & Acceptance Criteria

**Purpose:** define what gets produced, where it lives, and the objective tests that decide whether it is done. Also records every assumption, limitation and open question found during the audit, so none of them is silently treated as fact.

---

## 1. Deliverables per Platform

A platform is **done** only when every row applicable to its tier ([doc 02 §1](02_quality_and_modelling_standards.md)) passes its gate in §3.

| Deliverable | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
| Triaged reference set + `TRIAGE.md` | ✅ | ✅ | ✅ | ✅ |
| Engine manifest (components, channels, limits, faults) | ✅ | ✅ | ✅ | ✅ |
| Engine physics parameters, calibrated | ✅ | ✅ | ✅ | ✅ |
| Platform manifest | ✅ | ✅ | ✅ | ✅ |
| Engine `.blend`, fault-addressable meshes | ✅ | ✅ | top 3 faults | — |
| Airframe `.blend` | ✅ 4K | ✅ 2K | ✅ simple | — |
| Build script (reproducible) | ✅ | ✅ | ✅ | — |
| Display modes: PBR / ghost / wireframe-clay | all 3 | PBR + ghost | PBR + ghost | — |
| Driver-based mechanisms (doc 04 §1.3) | ✅ | ✅ | prop only | — |
| Simulated sorties: 1 nominal + 1 per demoed fault | ✅ | ✅ | nominal + 1 | nominal + 1 |
| Acceptance render set (§3.4) | ✅ | ✅ | silhouette only | — |
| Validation report (`validate_asset.py` output) | ✅ | ✅ | ✅ | manifest-only |

---

## 2. Proposed Folder Structure 🟦

```text
ANUMAAN/
├── docs/
│   ├── 00_official_problem_statement.md
│   ├── 01_problem_statement_breakdown.md
│   └── assets/                          ← this specification set
├── manifests/
│   ├── engines/<engine_id>.json
│   └── platforms/<platform_id>.json
├── Models/
│   ├── source/                          raw third-party / CAD, never edited
│   │   ├── rotax_914_parasolid/         (currently engine-rotax-914-1.snapshot.2)
│   │   ├── rotax_912is_step/            (currently engine-rotax-912is-1.snapshot.15)
│   │   └── rotax_915/                   (currently Rotax_915.FBX, 915_complete.max)
│   ├── engines/<engine_id>.blend        generated, twin-ready
│   ├── airframes/<platform_id>.blend    generated, twin-ready
│   └── textures/<platform_id>/{4k,2k}/
├── Models_Images/<platform>/
│   └── TRIAGE.md                        human-graded, replaces auto REFERENCE_CATALOG.md
├── scripts/
│   ├── build/build_<id>.py
│   └── validate/validate_asset.py       Gate C automation
├── missions/profiles/<mission_id>.json  doc 04 §3.2 format
└── renders/<platform_id>/acceptance/
```

**Migration rules:**

- **Do not move existing baseline files yet.** `scripts/build_tb3_digital_twin.py:37` hardcodes `base_dir = r"e:\backup-llm\backup-no-llm\3d_engine"` and reads from `3d_models/`; the Blender twin app and backend reference current paths. Moving files first breaks both baselines.
- First make build scripts path-relative (resolve from the script's own location or a single config), *then* migrate.
- `.blend` outputs are **generated artefacts**: the build script plus manifest is the source of truth. Hand edits to a generated `.blend` are lost on rebuild.
- The 60 MB `914.rar` inside the Rotax 914 snapshot should be inspected before conversion work. It may be the complete assembly the loose `.x_t` parts come from.

---

## 3. Acceptance Gates

Gates are sequential per platform. A later gate never waives an earlier one.

### Gate A: Reference (exit criterion for Phase 0)

| # | Criterion | Method |
|---|---|---|
| A1 | ≥ 1 verified **top, side and front** orthographic view | Human review; recorded in `TRIAGE.md` |
| A2 | Wingspan, length, height from **≥ 2 independent sources**, agreeing within 2% | Sources cited in the platform manifest |
| A3 | Engine designation confirmed by a primary or authoritative source | Citation |
| A4 | **Engine count confirmed** | Citation. Critical for TAPAS, see §4.3 |
| A5 | Engine component reference sufficient to name every fault target | ≥ 1 annotated/callout image or cutaway |
| A6 | Every reference file graded: `USABLE-ORTHO`, `USABLE-DETAIL`, `CONTEXT-ONLY`, `REJECT` | `TRIAGE.md`. Auto-generated "CONFIRMED" grades are not accepted |

### Gate B: Physics & fault model (exit criterion for Phase 1, per engine)

| # | Criterion | Pass threshold |
|---|---|---|
| B1 | **Rotax 912 iS regression**: refactored model reproduces existing expected states/residuals on `rotax912_test_dataset.csv` | Max abs. difference ≤ 1e-6 per channel |
| B2 | Power vs altitude matches every ✅ spec point in [doc 04 §2.2](04_rigging_animation_simulation_spec.md) | Within 5% (e.g. PD170: 170 hp @ 20,000 ft, 130 hp @ 30,000 ft) |
| B3 | Fuel consumption matches ✅ spec points | Within 10% (e.g. AE330: 39 L/h @ 100%, 21 L/h @ 60%; PD170 BSFC 207 g/kWh @ MSL) |
| B4 | **False positives:** seeded nominal sortie across all mission phases | 0 fault classifications; anomaly flags ≤ 🟦 1% of frames |
| B5 | **Detection:** each manifest fault injected at held-out onset rate/severity | Detected and correctly classified |
| B6 | **Prediction lead time:** each progressive fault | Classified **before** the hard limit is crossed, lead time > 0 and reported |
| B7 | RUL monotonicity under steady degradation | p50 RUL non-increasing within noise; p10 ≤ p50 ≤ p90 always |
| B8 | Sensor-fault discrimination: `900`-range sensor fault injected | Flagged as sensor suspect, **not** as a component fault |
| B9 | Channels an engine lacks are `null`, never `0` | Schema check |

### Gate C: Asset (automated, `validate_asset.py`)

| # | Check |
|---|---|
| C1 | Every mesh named in the engine and platform manifests exists in the `.blend`, exactly once |
| C2 | No `.001`-style duplicate names on any manifest-referenced object |
| C3 | Ground contact: lowest vertex of landing gear within **±5 mm of Z = 0** |
| C4 | Wingspan / length / height within tier tolerance of manifest dimensions (±2% T1/T2, ±5% T3) |
| C5 | Required collections present (doc 02 §2) |
| C6 | `XRayFactor` value node present on every skin material |
| C7 | Required named cameras present (doc 02 §9, per manifest) |
| C8 | No standalone decal/marking plane objects |
| C9 | Triangle count at subsurf-0 within tier budget (doc 02 §6) |
| C10 | Texture resolution matches tier |
| C11 | **No keyframes on mechanism control objects or propeller pivots** (doc 04 R1) |
| C12 | Scene units metric, scale 1.0 |
| C13 | Build script regenerates a `.blend` passing C1–C12 from a clean checkout |

### Gate D: Twin integration

| # | Criterion | Method |
|---|---|---|
| D1 | Platform switch via `SET_PLATFORM` with **zero platform-specific client code** | Code review + live switch |
| D2 | Every manifest fault: inject → highlight visible on the state update that carries it | Frame capture |
| D3 | Inspect pose frames the target: component bounding box fully in viewport and ≥ 🟦 15% of viewport area | Automated screenshot bbox check |
| D4 | `CLEAR_FAULT` restores original materials exactly | Before/after material-assignment hash |
| D5 | Visual priority order (doc 03 §5.3) respected: sensor-suspect never renders as component fault | Inject sensor fault + real fault together |
| D6 | Degrading-but-unclassified state visibly distinct from nominal **before** fault classification | Frame capture during onset ramp |
| D7 | Engine inside airframe: ghost mode auto-engages and pose transforms through `engine_mount` | Visual check on the airframe, not the bare engine |
| D8 | **Kill the 3D client:** health, faults, RUL and recommendations remain available and unchanged via `/api/state` | Direct API check |
| D9 | ≥ 60 FPS single platform, ≥ 30 FPS fleet view on the demo machine | Measured, machine spec recorded |

### Gate E: Simulation & replay

| # | Criterion |
|---|---|
| E1 | Same mission JSON + seed → byte-identical telemetry across two runs |
| E2 | All phases in doc 04 S1 exercised by at least one profile per T1/T2 platform |
| E3 | Replay frame at time *t* equals the live state recorded at *t* |
| E4 | Scrubbing replay does not change any mechanism state not present in the recorded data |
| E5 | Re-detection (doc 04 P6) over an unchanged model produces an empty diff |
| E6 | Every fault event in replay shows its lead time |
| E7 | Comparative what-if runs one profile on ≥ 2 platforms and reports per-engine margins |

### Gate F: Demo readiness (hero platform)

Derived from [breakdown §17](../01_problem_statement_breakdown.md). Each must be demonstrable live, unscripted by hand-authored values:

| # | Scenario |
|---|---|
| F1 | Normal → abnormal → detection → diagnosis → prediction with lead time → warning → recommended action |
| F2 | Same throttle, two environments (e.g. Ladakh cold/high vs Thar hot/low) → visibly different engine behaviour |
| F3 | RUL visibly decreasing under progressive degradation, with uncertainty band |
| F4 | Load a past sortie, jump to a fault event, show when the twin first knew |
| F5 | Sensor failure correctly shown as bad data, not a component failure |
| F6 | Pre-flight Go/No-Go: planned mission vs current RUL |

### 3.4 Visual acceptance

"Pixel-perfect" is not objectively testable as stated. It is operationalized as:

1. Render the platform's acceptance camera set.
2. For each of ≥ 3 references graded `USABLE-DETAIL`, render at a matched camera angle and focal length.
3. Reviewer checklist per pair: silhouette overlay deviation · marking position and scale · material zone boundaries · landing gear and prop geometry · sensor turret placement.
4. Sign-off recorded in `renders/<platform_id>/acceptance/REVIEW.md`.

---

## 4. Assumptions, Limitations & Uncertainties

### 4.1 Assumptions (treated as true for planning; revisit if wrong)

| # | Assumption | If wrong |
|---|---|---|
| AS1 | The UAV↔engine pairings implied by `Models_Images/` folder names are correct | Physics and fault work targets the wrong engine |
| AS2 | Manufacturer spec figures in `descr.md` files are accurate | Gate B calibration targets are wrong |
| AS3 | The demo runs on a single workstation with the backend local (`127.0.0.1:8000`) | Rates and framerate budgets need revisiting |
| AS4 | Blender remains the 3D client; the web dashboard is a parallel consumer of the same state | Manifest design still holds; Gate C tooling changes |
| AS5 | Scoring weights PS-26054 functional capability over visual fidelity | Tier allocation should shift toward more T1 assets |

### 4.2 Limitations (known and accepted)

| # | Limitation | Consequence |
|---|---|---|
| L1 | **No real telemetry exists for any engine except via the Rotax 912 dataset**, itself partly synthetic (`source3_drdo_missions`) | Non-Rotax detection and RUL are validated on simulator data only. The demo must say so |
| L2 | All platform information is from public sources | Dimensions and internal layouts are approximations of real military systems, never authoritative |
| L3 | **Reference image licensing is unknown.** The TB3 set consists of TurboSquid commercial product renders; others are web-scraped | Use strictly as modelling reference. Never as textures, never redistributed, never shown in the submission as our own imagery |
| L4 | Engine CAD in `ANUMAAN/Models/` appears to be community-made (snapshot naming, Cyrillic part names), not manufacturer data | Geometrically plausible, not certified-accurate; licence must be checked before any redistribution |
| L5 | `915_complete.max` requires 3ds Max | Treat the FBX as the only usable source unless Max is available |
| L6 | Sub-second vibration spectra cannot be carried on the 20 Hz state stream | Vibration faults rely on edge-computed features (doc 03 §4.3) |

### 4.3 Open uncertainties (must be resolved; owner decides)

| # | Question | Blocks | Why it matters |
|---|---|---|---|
| **U1** | **Is TAPAS BH-201 single- or twin-engine?** Believed twin | TAPAS modelling, physics, fault set; the project narrative | Existing docs build the whole problem framing on single-engine vulnerability *and* name TAPAS as the target platform. If TAPAS is twin-engine, both cannot stand as written |
| **U2** | TAPAS engine designation: AE330, AE300, "E4" (folder name), or other? | TAPAS physics | Folder says `Austro_E4`; spec sheet covers AE300/AE330 |
| U3 | Which quality tier for which platform? | Phase 3 onward | Scope. Recommendation in doc 00 §4.1: one T1 |
| U4 | Build PD170 for the TB3, or re-label the TB3 airframe? | Phase 2 | Doc 01 §3.3 recommends building PD170 |
| U5 | Every ❓ cell in the engine matrix (doc 04 §2.2) | Gate B per engine | Calibration targets |
| U6 | Proposed diesel/turbo fault signatures (doc 04 §2.5) | Gate B | Currently engineering proposals, not literature-validated |
| ~~U7~~ | ~~Blender version~~ **RESOLVED:** Blender 5.2.1 LTS at `E:\Blender\blender.exe`. `'BLENDER_EEVEE'` is valid in this version | — | — |
| ~~U8~~ | ~~Baseline triangle counts~~ **RESOLVED:** TB3 14,530 (viewport), Rotax 912 iS 2,016,171. See audit §1 | — | — |
| U9 | Landing-gear type (fixed/retractable) and tail geometry per platform | Rigging | Doc 04 §1.4 |
| U10 | Contents of `914.rar` | Rotax 914 conversion estimate | May supersede loose parts |

### 4.4 Top risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Modelling starts before references exist → rebuilt airframes | High | High | Gate A is a hard block |
| Physics refactor breaks the working Rotax 912 demo | Medium | **Critical** | B1 regression lock; refactor on a branch; demo always runs from last passing commit |
| Seven platforms attempted at uniform quality → none finished | High | High | Explicit tier assignment (U3) before Phase 3 |
| Synthetic-only validation challenged by judges | High | Medium | State it openly; show held-out fault parameters (doc 04 §2.6) and physics calibration against real spec points |
| TAPAS single/twin-engine contradiction surfaces during judging | Medium | High | Resolve U1 in Phase 0 and correct the narrative docs |
| Reference licensing issue | Low–Medium | Medium | L3 usage rules |

---

## 5. Implementation Roadmap: Checklist View

Detailed rationale in [doc 00 §5](00_asset_program_overview.md).

**Phase 0: References & decisions**
- [ ] Resolve U1, U2 (TAPAS engine count and designation)
- [ ] Decide U3 (tier per platform) and U4 (TB3 engine)
- [ ] Triage all `Models_Images/` folders → `TRIAGE.md`
- [ ] Acquire orthographics: TAPAS, ANKA, CH-4, Heron (and MQ-1 beyond 3)
- [ ] Gate A pass for P0–P2 platforms

**Phase 1: Twin backbone**
- [ ] Make build scripts path-relative
- [ ] Engine + platform manifest schemas; migrate Rotax 912 and its 8 faults into manifests
- [ ] Add `platform_id` / `engine_id` to state; manifest-driven fault validation; `SET_PLATFORM`
- [ ] Physics refactor (doc 04 §2.4) with B1 regression lock
- [ ] Add injection-timing channels (PS gap, all engines including 912)
- [ ] Mission profile model with full phase set (doc 04 §3.2)

**Phase 2: TB3 becomes a twin**
- [ ] PD170 engine manifest, physics calibration (Gate B)
- [ ] PD170 engine `.blend` (Gate C)
- [ ] Replace Rotax 912 linkage in TB3 build
- [ ] Convert TB3 mechanisms to drivers (C11)
- [ ] Twin-bind TB3 client (Gate D)

**Phase 3: Hero platform:** TAPAS BH-201 + AE330, Gates A–F
**Phase 4: Tier-2:** TB2 + 912 iS, MQ-1 + 914F, Gates A–E
**Phase 5: Tier-3 / T4:** Heron, ANKA, CH-4
**Phase 6: Fleet validation:** comparative what-if (E7), fleet replay, final demo rehearsal (Gate F)
