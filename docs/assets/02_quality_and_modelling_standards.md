# 3D Modelling, Visual Quality & Performance Standards

**Source of truth:** these standards are reverse-engineered from the two existing baseline assets (`build_tb3_digital_twin.py`, `rotax_912_is_sport.blend` + `standalone_digital_twin_app.py`), not invented. Where a value is proposed rather than observed, it is marked 🟦.

---

## 1. Quality Tiers

Seven airframes and six engines cannot all reach baseline quality in the available time ([doc 00 §4.1](00_asset_program_overview.md)). Tier assignment is therefore an explicit decision per platform, made up front and acceptance-tested.

| Tier | Visual standard | Twin integration | Use for |
|---|---|---|---|
| **T1 — Hero** | Full TB3 standard: 4K PBR, integrated decals, all display modes, full camera set | **Full** — all faults bound, live telemetry, HUD | 1 platform. The one that gets demoed live |
| **T2 — Complete** | Accurate geometry, 2K PBR, decals, PBR + ghost modes (no wireframe/clay) | **Full** — all faults bound | 2 platforms. Prove the fleet/multi-platform claim |
| **T3 — Fleet** | Accurate silhouette and proportions, simple material zones, no decal work | **Partial** — health indices + top 3 faults only | Remaining platforms. Populate fleet views, pre-flight comparisons |
| **T4 — Deferred** | Not modelled | Manifest + physics model only | Platforms where the physics is demonstrable without geometry |

> **T4 is a legitimate deliverable, not a failure.** A platform with a working parameterized engine model and no 3D asset still satisfies PS-26054's health-monitoring, RUL, and simulation requirements. A platform with a beautiful 3D asset and no physics satisfies none of them.

---

## 2. Scene Structure Standard (observed from TB3)

Every airframe `.blend` must conform:

```text
Scene (METRIC, length_unit = METERS, scale_length = 1.0)
└── <Platform>_Root                     (Empty, ARROWS, display size 1.5, at 0,0,0)
    └── <Platform> collection
        ├── Airframe            ├── Wings           ├── Tail
        ├── Propulsion          ├── Landing_Gear    ├── Sensors_Payload
        ├── Internal_Systems    ├── Cameras         ├── Lighting
        └── Environment
```

**Rules:**

- **Ground contact at Z = 0.000 m.** The TB3 achieves this with an explicit `Z_OFFSET` constant (1.020 m) applied to the whole build. The bottom of the wheels sits exactly on the floor plane — not approximately.
- **Real-world scale in metres.** Wingspan in the file must match published wingspan (e.g. TB2 = 12.0 m). This is non-negotiable: the twin's camera framing distances (`target_distance` in the fault manifest) assume real units.
- **`Internal_Systems` hidden by default** — the engine, avionics and fuel cells live here and are revealed by X-ray/internal inspection modes. Keeping them hidden preserves viewport framerate.
- **One root empty per platform.** Fleet views position platforms by moving roots, never by moving meshes.

---

## 3. Mesh Naming Contract ⚠️ CRITICAL

The fault-visualization system addresses meshes **by exact name string**. Naming is not cosmetic — it is the integration surface. Observed convention from the Rotax 912 baseline:

```text
{Component}_M_{Material}_{Index}

Gearbox_Type_2_M_Steel_0
Oil_Tank_M_Steel_0
Wiring_Harness_M_Copper_0
Exhaust_System_M_SteelDark_0
Covers_Theme_M_PlasticTheme_0
Cooling_Air_Baffle_M_PlasticWhite_0
```

**Requirements for all new assets:**

1. Every fault-addressable component gets its own named mesh object. A component that cannot be selected by name cannot be highlighted when it faults.
2. Component names must match the taxonomy in the platform manifest ([doc 03](03_twin_integration_spec.md)) exactly — no trailing spaces, no case drift, no Blender `.001` duplicates.
3. Names must be **engine-appropriate**. A diesel has no `Spark_Plug_*`; it has `Common_Rail_*`, `HP_Fuel_Pump_*`, `Glow_Plug_Controller_*`, `Turbocharger_*`, `Intercooler_*`. Component taxonomy comes from the annotated manufacturer diagrams in the reference library (see [audit §2.2](01_current_state_audit.md)).
4. **CAD-imported names must be renamed before the asset is accepted.** `Patrubok voda 1` is not a bindable name.

> A useful test: the manifest is written *first*, from the engine's real component list; the model is then built to satisfy it. Building geometry first and naming it afterward reliably produces meshes that faults cannot address cleanly.

---

## 4. Material & Shading Standard

Three material systems, observed from the TB3 baseline. T1/T2 require systems 1 and 3; T1 additionally requires system 2.

### 4.1 Tactical PBR (primary)

| Property | Baseline value |
|---|---|
| Base colour (untextured fallback) | `(0.135, 0.145, 0.160)` dark graphite |
| Metallic | 0.02 (airframe composite) |
| Roughness | 0.38 |
| IOR | 1.50 |
| Normal map strength | 0.75 |
| Texture set | diffuse + roughness + normal |
| Resolution | 4K (T1) · 2K (T2) · none/procedural (T3) |

### 4.2 Wireframe Clay (inspection)

Warm clay base `(0.68, 0.65, 0.60)`, roughness 0.44, metallic 0.0, wireframe overlay size 0.90 in dark line colour `(0.10, 0.10, 0.11)`. Used for topology review and the "engineering drawing" presentation mode.

### 4.3 X-Ray Hologram (twin inspection) ⚠️ required for fault visualization

Fresnel (IOR 1.30) blended with emission `(0.05, 0.85, 1.0)` at strength 3.5 and transparency `(0.85, 0.95, 1.0)`, driven by a **named value node `XRayFactor`** so the controller can set opacity programmatically (0.0 normal → 0.85 ghost → 1.0 internal-only).

**The `XRayFactor` node name is part of the contract** — `tb3_digital_twin_controller.py` looks it up by name. New assets that omit or rename it will not respond to inspection-mode switching.

### 4.4 Material slot discipline

Multi-material objects use ordered slots (observed on MAM-L munitions: slot 0 body, slot 1 hazard ring, slot 2 seeker lens). Fault highlighting swaps or drives material properties per object; predictable slot ordering keeps that logic simple.

---

## 5. Decal & Markings Standard

**Zero floating quads.** The TB3 baseline integrates all roundels, flags, serials, stencils and hazard banding directly into the mesh UVs. Floating decal planes are rejected because they z-fight, break on subdivision, and are visible as separate objects in exploded/X-ray views.

- T1/T2: markings baked into the diffuse map, correctly UV-placed
- T3: hazard banding and national markings optional; silhouette accuracy takes priority

---

## 6. Topology & Polycount

**Measured baselines (Blender 5.2.1):** TB3 airframe = **14,530 tris** at viewport (subsurf 0; smoothness comes from 36 Subsurf + 35 Bevel modifiers at render). Rotax 912 iS engine = **2,016,171 tris**, no modifiers.

| Asset class | Viewport budget | Notes |
|---|---|---|
| Airframe (T1) | ≤ 150 k tris at subsurf-0 | ~10× TB3, to allow the realism detail the TB3 lacks |
| Airframe (T2) | ≤ 80 k tris | |
| Airframe (T3) | ≤ 30 k tris | Silhouette fidelity only |
| Engine LOD0 (standalone inspection) | ≤ 2.5 M tris | Rotax 912 baseline is 2.0 M |
| Engine LOD1 (mounted in airframe / fleet) | ≤ 400 k tris | Same object names as LOD0, separate file |
| Full scene (airframe + LOD1 engine + environment) | ≤ 1 M tris | Must sustain the framerate target in §8 |

**Topology rules:**

- Quad-dominant on all subdivision surfaces. The wireframe inspection mode displays topology directly — triangle soup from CAD import is visible to anyone who switches modes.
- Subdivision: viewport level 0, render level 2, Optimal Display on.
- No n-gons on curved airframe surfaces (they shade incorrectly under subdivision).
- Internal components invisible in all inspection modes should not be modelled at all.

---

## 7. Dimensional Accuracy

Every platform's manifest records authoritative published dimensions; the model is validated against them ([doc 05](05_deliverables_validation_acceptance.md)).

Example, from the TB2 reference catalog: wingspan 12.0 m, length 6.5 m, height 2.2 m, MTOW 700 kg.

**Tolerance:** 🟦 ±2% on wingspan, length and height for T1/T2; ±5% for T3.

**Blocking dependency:** dimensional accuracy requires orthographic reference. Four of six platforms currently have none ([audit §2.1](01_current_state_audit.md)). For those platforms, dimensional accuracy is *unachievable* until Phase 0 completes — modelling them earlier means rebuilding them later.

---

## 8. Performance & LOD Requirements

The digital twin is an **interactive** application — the operator orbits, switches modes, injects faults and scrubs replay in real time. Framerate is a functional requirement, not polish.

| Requirement | Target | Source |
|---|---|---|
| Viewport framerate, single platform | ≥ 60 FPS sustained (TB3 script targets 120) | Observed baseline intent |
| Render engine, interactive | EEVEE with GTAO + SSR | Observed |
| Render engine, hero stills | Cycles | Observed (renders/ folder) |
| Colour management | AgX view transform, "Medium High Contrast" look | Observed |
| Mode-switch latency | 🟦 < 200 ms | Proposed |
| Fault highlight → visible response | 🟦 < 1 frame after state update | Proposed |
| Fleet view (all platforms loaded) | 🟦 ≥ 30 FPS | Proposed |

**LOD strategy:**

- `Internal_Systems` hidden until an inspection mode requests it — the single largest framerate lever, already used by the baseline.
- Subsurf viewport 0 during interaction; raise only for stills.
- 🟦 For fleet views, link platforms at T3 detail rather than loading T1 assets N times.
- 🟦 Textures: 4K on the inspected platform only; 2K or lower elsewhere.

---

## 9. Camera Standard

Named cameras are part of the integration contract — the controller switches by name string.

**Measured in the TB3 file:** `Cam_Beauty_Orbit` (48 mm), `Cam_Front_Sensor` (65 mm), `Cam_Hero_Image_PNG` (41 mm), `Cam_Wireframe_FDDA` (29 mm), each with a `Target_*` empty and TRACK_TO constraint. `tb3_digital_twin_controller.py` references `Cam_Engine_Prop`, `Cam_Wing_Fold` and `Cam_Undercarriage`, **which do not exist in the file**. Required set for new assets:

| Camera | Purpose |
|---|---|
| `Cam_Hero` | Default presentation still |
| `Cam_Beauty_Orbit` | Orbit / presentation view |
| `Cam_Front_Sensor` | EO/IR turret detail |
| `Cam_Engine_Bay` | Powerplant and propeller |
| `Cam_Undercarriage` | Landing gear |
| `Cam_Wireframe` | Topology presentation |
| `Cam_Wing_Fold` | Only on platforms with folding wings |

Plus, per fault, a **computed inspection pose** rather than a fixed camera: the Rotax twin stores `target_center` / `target_angle` / `target_elevation` / `target_distance` per fault and drives the orbit camera to it, so a newly added fault needs no new camera object. New platforms follow this pattern ([doc 03 §2](03_twin_integration_spec.md)).

---

## 10. Build Method: Procedural vs Sculpted

The TB3 is **procedurally generated from a 1,500-line Python script**, not hand-modelled. This has real consequences worth stating explicitly:

**Advantages (why the baseline works this way):** the asset is reproducible, diffable, version-controllable as a 219 KB text-driven file rather than a 78 MB binary; parameters (Z offset, chord, rib counts) are editable; the build is deterministic.

**Costs:** organic surface refinement is far harder than in direct modelling; the script is the source of truth, so the `.blend` must never be hand-edited and re-saved or the two diverge.

🟦 **Recommendation:** keep the procedural approach for airframes (they are largely lofted surfaces and parametric solids, which suit it). For CAD-derived engines, the source is imported geometry — there the script's job is import, cleanup, renaming, material assignment and manifest binding, not generation. Document per platform which method produced it.
