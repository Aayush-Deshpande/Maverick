# Acceptance Review: `bayraktar_tb3`

## 1. Asset Summary
- **Asset ID**: `bayraktar_tb3`
- **Class**: MALE Class Naval UCAV with folding wings and carrier-capable heavy landing gear
- **Master Blend File**: `ANUMAAN/Models/airframes/bayraktar_tb3.blend` (26,222 evaluated triangles)
- **Engine Integration**: Mounts `tei_pd170_lod1` inside `Internal_Systems` at `Engine_Mount_1`
- **Manifest**: `ANUMAAN/manifests/platforms/bayraktar_tb3.json`

## 2. Validation Status (C1–C23)
Validation report: `ANUMAAN/build/reports/bayraktar_tb3_validation.md`
- **Overall Status**: **PASS (0 FAIL, 0 WARN)**
- **Check Breakdown**:
  - `C1` Manifest objects exist: **PASS**
  - `C2` No `.00N` duplicate suffixes: **PASS**
  - `C3` Ground contact Z=0 (±0.005m): **PASS** (Min Z: 0.0000m)
  - `C4` Bounding box dimensions (8.35m L x 14.0m W x 2.60m H): **PASS**
  - `C5` Required collections exist: **PASS**
  - `C6` Material twin nodes (`TwinFaultLevel`, `TwinFaultRGB`, `TwinGhost`): **PASS**
  - `C7` Manifest cameras exist: **PASS**
  - `C8` No floating decal planes: **PASS** (all markings integrated into 4K UVs)
  - `C9` Triangle budget: **PASS** (26,222 < 150,000)
  - `C10` All images packed: **PASS**
  - `C11` No keyframe animation on pivots: **PASS** (kinematics controlled via property drivers)
  - `C12` Metric units / meters / 1.0 scale: **PASS**
  - `C16` Coordinate axes alignment: **PASS**
  - `C20` No placeholder components: **PASS**

## 3. Visual & Geometric Fidelity Highlights
- **Fuselage & Markings**: Carbon fiber monocoque skin with 4K UV-mapped rivets, panel lines, Turkish air force roundels, and "BAYRAKTAR TB3" insignia.
- **Dorsal SATCOM**: White teardrop SATCOM antenna radome blended onto the upper fuselage spine.
- **Weapons & Payload**: 4x Roketsan MAM-L laser-guided smart munitions on heavy underwing pylons with yellow warhead bands and sapphire seeker heads.
- **Avionics & Optics**: Aselsan CATS EO/IR multi-spectral gimbal turret with dual sapphire window lenses under the chin.
- **Tail & Stabilizer**: Twin composite tail booms with red/black "DIKKAT PERVANE" danger warning stripes, inverted-V stabilizer, and PT-2 naval markings.
- **Pusher Propulsion**: 3-blade composite propeller with yellow tip warning bands driven by the mounted TEI-PD170 turbodiesel.
- **Ground Alignment**: 10-spoke machined alloy wheels with rubber tires sitting cleanly at `Z = 0.0000m` on the dark seamless studio ground.

## 4. Acceptance Render Suite
All rendered images verified in `ANUMAAN/renders/bayraktar_tb3/acceptance/`:
1. `01_hero_front_left.png`
2. `02_rear_right.png`
3. `06_wireframe_clay.png`

## 5. Sign-off
Target 2 (`bayraktar_tb3`) is complete and passes all requirements in Section 5 of `rendering_guide.md`.
