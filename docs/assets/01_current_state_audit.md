# Current State Audit — Models, References, Code

**Purpose:** establish what actually exists today, verified by inspection rather than assumed from folder names. Several things that look complete are not, and one thing that looks missing is already done.

**Audit date:** 2026-09-16. **Method:** direct file inspection, script reading, image spot-checks.

---

## 1. 3D Model Inventory

| Asset | Location | Size | Format | Verdict |
|---|---|---|---|---|
| **Rotax 912 iS Sport** | `assets/blender/rotax_912_is_sport.blend` | 78 MB | Blender, textured, individually named meshes | ✅ **REUSE AS-IS** — production baseline |
| **Bayraktar TB3** | `assets/blender/bayraktar_tb3_digital_twin.blend` (⚠️ a second, unresolved copy also exists at `assets/models/bayraktar_tb3_digital_twin.blend` — still-unresolved duplication, see [`docs/audit/06_repo_cleanup_plan.md`](../audit/06_repo_cleanup_plan.md) §6) + `scripts/build_tb3_digital_twin.py` | 219 KB + 68 KB script | Procedurally generated Blender | ⚠️ **REUSE + MODIFY** — see §3 |

**Measured with Blender 5.2.1 (2026-09-16):**

| | TB3 | Rotax 912 iS |
|---|---|---|
| Mesh objects | 39 | 109 |
| Triangles (viewport, modifiers evaluated) | 14,530 (36 Subsurf + 35 Bevel modifiers, subsurf viewport 0) | 2,016,171 |
| Scale | Real metres, height 2.396 m, ground at Z = 0 | **Centimetre values in a metre scene** (bbox 71.3 × 108.5 × 80.8 units ≈ 0.71 × 1.09 × 0.81 m) |
| Collections | 10 named sub-collections | **None**, all objects in the scene root |
| Materials | 11 (`TB3_*`); `XRayFactor` only on `TB3_Tactical_PBR` | 31 (`M_*`); no `XRayFactor` |
| Textures | 3 × 4096² packed | 2 packed (1K, 2K) |
| Cameras | `Cam_Beauty_Orbit`, `Cam_Front_Sensor`, `Cam_Hero_Image_PNG`, `Cam_Wireframe_FDDA` | `MainCamera` |
| Animation | `CTRL_Gear_Retract`, `CTRL_Wing_Fold`, `Pivot_Propeller` keyframed; no drivers | None |
| Name hygiene | Clean | **15 duplicate `.00N` names**; `Cooling_Air_Baffle_M_PlasticCable_0` is targeted by `FAULT_DATABASE` but **does not exist** (37 of 38 fault targets resolve) |
| Rotax 912 iS CAD | `Models/engine-rotax-912is-1.snapshot.15/` | 374 MB | STEP / IGS / SLDASM | ⬜ **REDUNDANT** — .blend above already supersedes it. Keep as dimensional cross-reference only |
| Rotax 914 CAD | `Models/engine-rotax-914-1.snapshot.2/` | 147 MB | Parasolid `.x_t`, Cyrillic part names | ⚠️ **CONVERT REQUIRED** — raw CAD, no materials, no UVs, no twin-compatible naming |
| Rotax 915 | `Models/Rotax_915.FBX` + `915_complete.max` | 45 MB + 38 MB | FBX / 3ds Max | ⚠️ **CONVERT REQUIRED** — same caveats; FBX is the usable path |
| Nubra terrain | `Models/terrain.blend` | 52 MB | Blender | ⬜ Out of scope for this program (environment, not platform) |

### 1.1 What "CONVERT REQUIRED" actually costs

Raw CAD is **not** a 3D asset. STEP/Parasolid/FBX from CAD carries:

- NURBS or triangulated-at-import geometry with no quad topology and no subdivision control
- No UV unwrapping → no PBR texturing possible without a full unwrap pass
- No material assignment → every surface imports as one default grey
- Machine part names (`Patrubok voda 1.x_t`, `Koleno summatora 2.x_t`) → **incompatible with the fault-binding contract**, which addresses meshes by name (doc 03 §2)
- Full assembly detail including internal parts never visible → polycount vastly exceeding the LOD budget

**Estimate honestly:** converting a CAD engine dump into a twin-bound asset at Rotax-912 standard is comparable in effort to modelling it, not a shortcut. The one genuine saving is dimensional accuracy — the geometry is *correct*, which removes all guesswork about proportions.

### 1.2 Engines with no 3D source at all

**TEI PD170, Austro AE330, Lark HFE** — reference imagery only. These three are also the three diesels, i.e. the ones requiring new physics. They are the program's real content gap.

---

## 2. Reference Library Inventory

`Models_Images/` — 690 files across 10 folders. Category coverage per UAV:

| UAV | Ortho | Exterior | Engine | Prop | Sensors | Gear | Textures | Markings | Dims | CAD | Docs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Bayraktar TB2 | 13 | 43 | 24 | 0 | 5 | 1 | 0 | 0 | 0 | 0 | 0 |
| MQ-1 Predator | 3 | 66 | 6 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| IAI Heron Mk II | **0** | 26 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| TAI ANKA | **0** | **0** | 68 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CASC CH-4 | **0** | **0** | 36 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **TAPAS BH-201** | **0** | **0** | 71 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Standalone engine folders (flat, not categorized): **Austro AE330** (73), **Lark HFE** (38), **TEI PD170** (70), **Bayraktar TB3** (34, all TurboSquid product renders).

### 2.1 Three findings that change planning

**(a) Four of six UAVs have zero orthographic reference.** Orthographic top/side/front views are the single non-negotiable input for dimensionally accurate airframe modelling. Without them, an airframe is built by eyeballing perspective photos, which reliably produces wrong proportions — exactly the kind of error a domain-expert judge notices instantly.

**(b) Three UAVs have zero airframe imagery of any kind** (TAPAS, ANKA, CH-4). Their folders contain only engine photos. **The highest-priority platform, TAPAS BH-201, is in this group.** No amount of modelling skill substitutes for reference that does not exist.

**(c) The reference catalogs are machine-generated and unreliable.** `REFERENCE_CATALOG.md` files rate every asset "Source: Aviation Photography Archive / Confidence: **CONFIRMED** / Suitable for 3D: YES". Spot-check of `Bayraktar_TB2_01_Orthographic_013.png` — rated CONFIRMED, suitable for 3D — is **a world map of TB2 operator countries**. The catalogs are harvester boilerplate, not verified provenance.

> **Do not trust the reference counts in the table above as usable-asset counts.** They are file counts. A manual triage pass (Phase 0) must re-grade every file before any of it drives modelling.

### 2.2 Reference quality is not uniformly bad

Engine references are materially better than airframe references. `TAPAS_Austro_E4_ref_003.jpg` is an annotated manufacturer component-callout diagram labelling common rail, HP fuel pump, glow plug control unit, turbocharger, oil cooler, water pump, generator, gearbox and oil sump. That single image is directly usable as the **component taxonomy for the fault-binding manifest** — it names the exact parts a diesel fault model needs to address.

The `descr.md` spec sheets (TEI PD170, Lark HFE, Austro AE330) are likewise high-value: displacement, power curves, altitude ratings, TBO, fuel system type, FADEC configuration. These are the physics-model inputs for doc 04.

---

## 3. Code & Integration Audit

### 3.1 The Rotax 912 twin — functional baseline ✅

`apps/blender_twin/standalone_digital_twin_app.py` (1,405 lines) is the reference implementation of twin integration:

- `FAULT_DATABASE` — 8 faults, each binding `fault_id` → `target_parts[]` (exact mesh names) + camera pose (`target_center`, `target_angle`, `target_elevation`, `target_distance`)
- `TelemetryReceiverThread` — polls `http://127.0.0.1:8000/api/state`
- `HUDDrawer` — live fault matrix and system-health panels drawn over the viewport
- Ghost materials, pulsing fault emission, auto-camera focus on the faulted subsystem
- Interactive fault injection → `send_server_command("SET_FAULT")`

Backend side: `backend/telemetry/can_streamer.py` holds `DRDO_FAULT_DEFINITIONS` (ids 0–8) with a `target_mesh` string per fault; `backend/ml/fault_classifier.py` (251 lines) scores all 8 fault signatures and returns a `DiagnosticResult`.

**This is the contract every new asset must satisfy.** Formalized in doc 03.

### 3.2 The TB3 airframe — visual baseline, zero twin integration ⚠️

`scripts/build_tb3_digital_twin.py` sets a high structural standard: metric units, ground-contact `Z_OFFSET` constant, 10 named collections, root empty, three material systems (tactical PBR / wireframe clay / X-ray hologram with an `XRayFactor` value node), 4K PBR maps, decals integrated into mesh UVs, five named inspection cameras, subsurf viewport-0/render-2, EEVEE-first for viewport speed with AgX color management.

`assets/blender/tb3_digital_twin_controller.py` exposes: inspection modes, subsystem isolation, wing fold, gear retraction, camera navigation.

**What it does not contain, verified by grep:** no telemetry polling, no `api/state` client, no fault database, no health indices, no emission-based fault highlighting, no CHT/EGT/RPM binding of any kind. Every hit for "fault/telemetry/sensor/health" in the build script is a false positive (`default_value`, `Sensors_Payload` collection naming).

> **The TB3 is a high-quality static model with mechanical animation. It is not a digital twin.** Closing this gap is Phase 2 and is the single highest-leverage piece of work in the program, because it converts an existing asset into a demonstrable one.

### 3.3 TB3 has no engine, and its script targets the wrong one ❌

`build_tb3_digital_twin.py:40` points at `rotax_912_is_sport.blend` as the TB3's internal powerplant. **Measured:** the saved `.blend` contains no engine geometry at all. `Internal_Systems` holds a single empty, `Engine_Internal_Assembly`, with nothing under it.

Per the reference spec sheet in `Models_Images/TEI PD170/descr.md`, the TB3's actual engine is the **TEI PD170** — a 2.1 L inline-4 turbodiesel, 172 HP, liquid-cooled, HPCR direct injection, dual-redundant FADEC. The Rotax 912 iS is a 1.35 L air/oil-cooled naturally-aspirated spark-ignition **boxer**, 100 HP, fitted to the **TB2**.

These are not interchangeable: different cylinder layout, different cooling, different combustion cycle, different sensor set. A propulsion engineer on a judging panel would catch this immediately.

**Fix path:** either build the PD170 (correct, Phase 2) or re-label the airframe as TB2 (cheap, but TB2 and TB3 planforms differ — TB3 has folding wings for carrier operations, which the current model *does* implement). Recommend building the PD170.

### 3.4 The physics model is single-engine and hardcoded ❌

`backend/physics/thermo_model.py` — module-level constants:

```python
DISPLACEMENT_CC = 1352.0   # Rotax 912 iS, 4-cyl boxer
BORE_MM = 84.0
STROKE_MM = 61.0
```

The model is a naturally-aspirated, air-cooled, spark-ignition Otto-cycle formulation. It cannot represent any of the three diesels or either turbocharged Rotax without generalization. `backend/physics/sensor_validator.py` similarly encodes "Rotax 912 iS thermal response data" as its rate-of-change limits.

Consequences and the required generalization are specified in [04_rigging_animation_simulation_spec.md §2](04_rigging_animation_simulation_spec.md).

### 3.5 Harvesting infrastructure exists but is unvalidated

`scripts/` contains six UAV-harvesting scripts written today (`harvest_all_uavs.py`, `harvest_parallel_uavs.py`, `run_fast_uav_harvester.py`, `harvest_all_uav_categories.py`, `harvest_all_uavs_clean.py`, `collect_uav_datasets.py`) plus `scratch/` test files probing Bing/Google/DDG image search. The output of this tooling is the contaminated library described in §2.1.

**Verdict:** the acquisition problem is not "we need a scraper" — six exist. It is **relevance filtering and manual triage**, which no scraper solves. Phase 0 should assume human review, not another harvester iteration.

---

## 4. Reuse / Modify / Rebuild / Acquire — Summary Verdicts

| Item | Verdict | Notes |
|---|---|---|
| Rotax 912 iS `.blend` | **REUSE** | Meets both baselines. Reference implementation |
| Rotax 912 fault bindings + backend pipeline | **REUSE, then GENERALIZE** | Pattern is correct; hardcoding is not |
| TB3 airframe geometry & materials | **REUSE** | Meets visual baseline |
| TB3 engine linkage | **REBUILD** | Wrong engine (§3.3) |
| TB3 twin integration | **BUILD NEW** | Does not exist (§3.2) |
| `thermo_model.py` | **MODIFY — parameterize** | Blocks all new engines (§3.4) |
| `FAULT_DATABASE` (hardcoded in Blender app) | **MODIFY — externalize to manifests** | Does not scale to 7 platforms (doc 03) |
| Rotax 914 / 915 raw geometry | **CONVERT** | Dimensionally useful, structurally unusable as-is (§1.1) |
| PD170 / AE330 / Lark HFE geometry | **ACQUIRE or MODEL** | Nothing exists |
| Engine `descr.md` spec sheets | **REUSE** | Direct physics-model inputs |
| Annotated engine callout diagrams | **REUSE** | Direct fault-taxonomy inputs |
| Airframe reference library | **RE-ACQUIRE + TRIAGE** | Contaminated; 4/6 lack orthographics (§2.1) |
| Existing harvester scripts | **DO NOT EXTEND** | Six already exist; problem is triage, not collection (§3.5) |

---

## 5. Honest Assessment of the Visual Baseline

Reviewed `assets/blender/renders/render_01_hero_image_png.png` directly.

**What it achieves:** clean silhouette, correct proportions, integrated decals (roundels, Turkish flag, PT-2 stencils), red/yellow hazard banding, MAM-L munitions with distinct material slots, panel-line detail, competent studio lighting, no floating decal quads.

**Where it falls short of "pixel-perfect photorealism":** surfaces read as smooth CGI plastic rather than a weathered composite airframe — no rivet or fastener detail, no panel-gap occlusion, no edge wear, grime, streaking or environmental staining; some visible faceting on wing surfaces; uniform roughness across the airframe with no variation from handling or exhaust.

**Implication:** the script header claims "pixel-perfect"; the render is high-quality *product visualization*, one clear tier below photorealism. Two honest options:

1. **Adopt the real baseline** — define the standard as "clean product-viz with integrated decals" (what exists) and apply it consistently. Cheaper, uniform, defensible.
2. **Raise the baseline first** — add a surface-detail pass (rivets, wear masks, panel-gap AO) to the TB3, then hold new assets to the uplifted standard.

Doc 02 specifies option 1 as the default tier-1 standard, with the uplift itemized as an optional enhancement — because for PS-26054 scoring, surface weathering contributes nothing, while a missing fault binding costs a requirement.
