# TEI-PD170 Turbodiesel Aviation Engine — 360° Visual Reference & Blueprint Dataset

This dataset provides the definitive 360-degree multi-angle visual reference and orthographic blueprint suite for the **TEI-PD170** 2.1-liter turbodiesel aircraft engine (powering the Bayraktar TB3, TAI Anka-S, and TAI Aksungur MALE UAVs). It establishes the visual benchmark and structural ground truth for 3D modeling, high-fidelity rendering, and fault highlight animations.

---

## 1. Master 4K UHD Reference Blueprint
- **File**: [`tei_pd170_360_master_blueprint.jpg`](file:///e:/backup-llm/backup-no-llm/3d_engine/ANUMAAN/Models_Images/TEI%20PD170/360_reference/tei_pd170_360_master_blueprint.jpg) (3840 x 2160, 4K UHD)
- **Interactive Viewer**: [`tei_pd170_360_reference_viewer.html`](file:///e:/backup-llm/backup-no-llm/3d_engine/ANUMAAN/Models_Images/TEI%20PD170/360_reference/tei_pd170_360_reference_viewer.html)

---

## 2. 360° View Angle Catalog

| Angle / View | File Name | Resolution | Key Components & Visual Features Visible |
| :--- | :--- | :--- | :--- |
| **0° Front Gearbox Orthographic** | [`tei_pd170_360_front_ortho.jpg`](file:///e:/backup-llm/backup-no-llm/3d_engine/ANUMAAN/Models_Images/TEI%20PD170/360_reference/tei_pd170_360_front_ortho.jpg) | 2048 x 2048 (1:1) | Conical reduction gearbox with radial stiffening ribs; 6-bolt propeller hub flange with black central spigot; hydromechanical prop governor with hydraulic line; circular oil level sight glass; bottom safety-wired drain plug; TEI data placard; top timing cover with thermal braided bypass hose and blue 90° silicone elbow. |
| **90° Right Profile (Intake & Electrics)** | [`tei_pd170_360_front_right_hero.jpg`](file:///e:/backup-llm/backup-no-llm/3d_engine/ANUMAAN/Models_Images/TEI%20PD170/360_reference/tei_pd170_360_front_right_hero.jpg) | 1920 x 1080 (16:9) | Dual vertically stacked 4.5 kW 28V DC alternators with gold/yellow slotted ventilating housings and heavy terminal cables; cylindrical silver ASAS diesel fuel filter canister; horizontal spin-on oil filter; billet finned aluminum oil cooler box; cast intake plenum runner; blue silicone coolant hoses; dense wiring harness with yellow heat-shrink branch labels. |
| **180° Rear Flywheel Orthographic** | [`tei_pd170_360_rear_ortho.jpg`](file:///e:/backup-llm/backup-no-llm/3d_engine/ANUMAAN/Models_Images/TEI%20PD170/360_reference/tei_pd170_360_rear_ortho.jpg) | 2048 x 2048 (1:1) | Precision machined steel flywheel with starter ring gear teeth; starter motor pinion engagement port; outer bell housing perimeter with alignment dowel holes; rear cylinder head coolant outlet neck and temperature sensor; 4x ribbed elastomer engine vibration isolator mounts; exhaust downpipe outlet (lower left); dual yellow alternators (right). |
| **270° Left Profile (Twin Turbochargers)** | [`tei_pd170_360_left_turbo_hero.jpg`](file:///e:/backup-llm/backup-no-llm/3d_engine/ANUMAAN/Models_Images/TEI%20PD170/360_reference/tei_pd170_360_left_turbo_hero.jpg) | 1920 x 1080 (16:9) | Two-stage sequential turbochargers (HP primary + LP secondary) with cast aluminum compressor housings and cast iron turbine scrolls; cast exhaust crossover duct; dual wastegate actuators (black canister + red billet anodized TiAL-style actuator with linkage rod); heavy-duty V-band clamps; stainless steel exhaust downpipe angled downwards; dimpled metallic thermal insulation blanket; black starter motor; deep ribbed cast aluminum oil sump pan. |
| **Top Plan Orthographic View** | [`tei_pd170_360_top_ortho.jpg`](file:///e:/backup-llm/backup-no-llm/3d_engine/ANUMAAN/Models_Images/TEI%20PD170/360_reference/tei_pd170_360_top_ortho.jpg) | 2048 x 2048 (1:1) | Propeller flange (bottom) to flywheel housing (top); cylinder head valve cover with oil filler cap and lifting eyelet lugs; long yellow anodized bracket supporting high-pressure Common Rail; 4 individual precision-bent steel injector hard lines to common-rail injectors; intake plenum runner on left; twin sequential turbos and crossover pipe on right; Mil-Spec harness routing with yellow tags. |
| **360° Master Turnaround Sheet** | [`tei_pd170_360_turnaround_sheet.jpg`](file:///e:/backup-llm/backup-no-llm/3d_engine/ANUMAAN/Models_Images/TEI%20PD170/360_reference/tei_pd170_360_turnaround_sheet.jpg) | 1920 x 1080 (16:9) | 4-view studio alignment: Front Gearbox View, Right Intake View, Left Turbo View, Three-Quarter Perspective View with component callout text. |
| **Rear & Top Plan 3-View Sheet** | [`tei_pd170_360_rear_top_sheet.jpg`](file:///e:/backup-llm/backup-no-llm/3d_engine/ANUMAAN/Models_Images/TEI%20PD170/360_reference/tei_pd170_360_rear_top_sheet.jpg) | 1920 x 1080 (16:9) | 3-view technical alignment: Rear Orthographic, Top Plan Orthographic, and Front-Left Three-Quarter Perspective. |

---

## 3. Subsystem Breakdown & Fault Highlight Mapping

The visual reference defines 11 distinct physical sub-assemblies matching the benchmark of the Rotax 912iS digital twin, designed for individual highlighting during fault simulation:

1. **Reduction Gearbox (Prop Drive)**
   - *Visual Features*: Conical cast casing, 6-bolt propeller hub, sight glass, safety-wired drain plug, TEI nameplate.
   - *Fault Modes*: Gearbox oil pressure drop, oil contamination, flange bearing excessive play, propeller shaft seal leak.

2. **Hydraulic Propeller Governor**
   - *Visual Features*: Hydromechanical actuator block on lower right of gearbox, hydraulic hard line with banjo fittings, control cable/sensor connector.
   - *Fault Modes*: Propeller pitch control failure, overspeed governor unfeathering failure, hydraulic line rupture.

3. **Two-Stage Sequential Turbochargers (HP & LP)**
   - *Visual Features*: Primary high-pressure turbocharger, secondary low-pressure turbocharger, cast crossover exhaust pipe, braided oil supply lines.
   - *Fault Modes*: Turbocharger overboost, compressor surge/stall, turbine bearing oil leak, boost loss at high altitude (>20,000 ft).

4. **Dual Wastegate Actuators**
   - *Visual Features*: Black primary pneumatic canister with linkage arm, red billet anodized secondary actuator with threaded adjustment rod and lock-nut, blue silicone control lines.
   - *Fault Modes*: Wastegate actuator diaphragm puncture, wastegate valve flap sticking open (underboost) or sticking shut (catastrophic overboost).

5. **Exhaust Downpipe & Thermal Insulation**
   - *Visual Features*: Angled stainless steel exhaust downpipe, heavy-duty V-band clamp, dimpled metallic heat shield wrap over exhaust manifold.
   - *Fault Modes*: Exhaust manifold thermal crack, V-band clamp loosening, exhaust gas temperature (EGT) sensor deviation.

6. **Dual 4.5 kW 28V DC Alternators**
   - *Visual Features*: Two vertically stacked gold/yellow rotor housings with perimeter cooling slots, black brush caps, heavy insulated 28V bus cables with yellow strain relief boots.
   - *Fault Modes*: Alternator 1 diode bridge failure, Alternator 2 voltage regulator trip, stator winding thermal runaway.

7. **Common Rail High-Pressure Diesel Injection**
   - *Visual Features*: Yellow common rail bracket, 4 rigid steel high-pressure injector lines with vibration dampening clamps, 4 electrical solenoid injectors.
   - *Fault Modes*: Rail pressure relief valve leak, injector #3 solenoid circuit fault, common rail pressure sensor drift.

8. **Fuel & Oil Conditioning (ASAS & Oil Cooler)**
   - *Visual Features*: Cylindrical silver ASAS diesel filter canister, horizontal spin-on oil filter canister, finned aluminum oil cooler heat exchanger box.
   - *Fault Modes*: Fuel filter differential pressure alarm (fuel starvation), oil filter bypass valve open, oil cooler external debris blockage.

9. **Cooling Circuit & Silicone Plumbing**
   - *Visual Features*: Royal blue silicone radiator/coolant hoses with stainless steel jubilee clamps, thermal braided fire-sleeved bypass tubes with blue anodized AN fittings.
   - *Fault Modes*: Coolant hose clamp separation, cylinder head overheating, coolant temperature sensor out-of-range.

10. **Flywheel & Engine Mount Isolators**
    - *Visual Features*: Machined steel flywheel with starter ring gear teeth, starter pinion gear interface, 4x ribbed aluminum elastomer vibration isolator mounts.
    - *Fault Modes*: Starter ring gear tooth wear, engine mount isolator degradation, excessive airframe vibration harmonics.

11. **Aerospace Mil-Spec Wiring Harness & EECU**
    - *Visual Features*: Expandable black braided loom, Mil-Spec P-clamps, yellow heat-shrink identification sleeves on every connector branch, top electrical connector rail.
    - *Fault Modes*: CAN bus communication loss, sensor 5V reference short to ground, intermittent FADEC channel A/B failover.

---

## 4. Usage in 3D Modeling & Rendering
- **Orthographic Alignment**: Import `tei_pd170_360_front_ortho.jpg`, `tei_pd170_360_rear_ortho.jpg`, and `tei_pd170_360_top_ortho.jpg` directly into Blender viewport background reference images for 1:1 scale matching.
- **Material Matching**: Use `tei_pd170_360_front_right_hero.jpg` and `tei_pd170_360_left_turbo_hero.jpg` as shading/PBR texture references (cast aluminum roughness 0.35-0.45, brushed stainless downpipe roughness 0.25, gold alternator anodization metallic 0.9, blue silicone roughness 0.5).
- **Component Naming Hierarchy**: Name Blender objects according to the 11 sub-assemblies outlined above to enable automated shader node highlighting for digital twin fault states.
