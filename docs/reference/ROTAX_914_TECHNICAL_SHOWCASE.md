# ROTAX 914 F Turbo — Engineering Digital Twin Showcase

**Project:** ANUMAAN Aero-Propulsion Health Monitoring Platform (DRDO SIH PS-26054)  
**Target Engine:** Rotax 914 F Turbocharged 4-Stroke Aero-Engine (115 HP)  
**Standard:** High-Definition CAD-Accurate Assembly with 3D Holographic Telemetry Overlays  

---

## 1. Engine Architecture & Core Specifications

| Engineering Metric | Specification | Verification Source |
|---|---|---|
| **Engine Configuration** | 4-Cylinder, 4-Stroke Horizontally Opposed Boxer | Rotax 914 Type Certificate Data Sheet |
| **Displacement** | 1,211 cm³ (74.0 cu.in) | Bore: 79.5 mm (3.13 in) \| Stroke: 61.0 mm (2.40 in) |
| **Compression Ratio** | 9.0 : 1 | OEM Technical Specification |
| **Take-off Power** | 84.5 kW (115 HP) @ 5,800 RPM (5 min limit) | MAP: 1.39 bar (41 in.Hg) |
| **Continuous Power** | 73.5 kW (100 HP) @ 5,500 RPM | MAP: 1.25 bar (37 in.Hg) |
| **Dry Weight** | 78.0 kg (including turbo, exhaust, and airbox) | Certified Mass |
| **Reduction Gearbox** | Ratio 1:2.43 (Prop RPM: 2,387 @ 5,800 Crank RPM) | Integrated Spur Gear & Dog Clutch |
| **Fuel Induction** | Dual BING 64 Constant Depression Carburetors | Pressure-Equalized Composite Airbox |
| **Thermal System** | Liquid-Cooled Heads, Ram-Air Cooled Barrels | Max CHT: 135°C (275°F) |
| **Exhaust System** | AISI 321 Stainless 4-into-1 Tuned Headers | Max EGT: 950°C (1,742°F) |
| **Turbocharger** | Garrett T25 with TCU Electronic Wastegate | Max Turbo Speed: 160,000 RPM |

---

## 2. Technical Inspection Stations

### Station 1: Architecture & Airframe Integration
- **Camera:** Front 3/4 beauty view.
- **Content:** Full assembly bounding envelope ($661 	imes 575 	imes 518	ext{ mm}$), total weight ($78.0	ext{ kg}$), and tactical UAV compatibility (MQ-1 Predator, Bayraktar TB2/TB3, Heron UAV).

### Station 2: Propeller Drive & Reduction Gearbox
- **Camera:** Front nose close-up.
- **Content:** 1:2.43 spur gear reduction unit, AND20010 8-bolt propeller drive flange with hollow central control bore, and integrated dog-clutch torsional vibration damper.

### Station 3: Fuel Induction & Composite Airbox Plenum
- **Camera:** Port side intake manifold tracking.
- **Content:** Dual BING 64 constant-depression carburetors, carbon-composite boost-equalized airbox, altitude mixture compensation, and cross-flow intake runners.

### Station 4: Thermal Management & Exhaust System
- **Camera:** Low underbelly perspective.
- **Content:** Liquid-cooled cylinder heads with ram-air cooled cylinders, dual spark ignition (8 plugs total) under crimson rocker covers, and 4-into-1 AISI 321 tuned stainless steel exhaust manifold.

### Station 5: Turbocharging & TCU Boost Regulation
- **Camera:** Starboard aft turbo unit focus.
- **Content:** Garrett T25 exhaust turbine and cast-aluminum compressor, Turbo Control Unit (TCU) electric servo wastegate, and manifold pressure boost envelope up to $15,000	ext{ ft}$ critical altitude.

### Station 6: ANUMAAN Digital Twin Telemetry Suite
- **Camera:** Master high 3/4 beauty overview.
- **Content:** 8 real-time diagnostic telemetry channels mapped directly to physical casing ports:
  - **S1:** Manifold Absolute Pressure (MAP) Sensor
  - **S2:** Dual Engine RPM Pickups (Flywheel)
  - **S3:** EGT Thermocouples (Runners 1–4)
  - **S4:** CHT Sensors (Cylinder Heads #2 & #3)
  - **S5:** Oil Pressure Transducer (Pump Base)
  - **S6:** Oil Temperature Probe (Return Sump)
  - **S7:** Coolant Temperature Sensor (Outlet Manifold)
  - **S8:** TCU Wastegate Position Feedback

---

## 3. Generated Showcase Artifacts

- **Showcase Blend Scene:** `assets/blender/rotax_914_showcase.blend`
- **6-Station Contact Sheet:** `assets/renders/engines/rotax_914/rotax_914_showcase_contact_sheet.png`
- **Station Beauty Stills:** `assets/renders/engines/rotax_914/stations/`
  - `station_01_architecture_overview.png`
  - `station_02_gearbox_reduction.png`
  - `station_03_induction_airbox.png`
  - `station_04_thermal_exhaust.png`
  - `station_05_turbo_wastegate.png`
  - `station_06_telemetry_sensor_suite.png`
- **Master Animation Frames:** `assets/renders/engines/rotax_914/cinematic_showcase/`

---
*ANUMAAN Digital Twin Core Team — Aero-Propulsion Engineering Division.*
