# Project ANUMAAN — Mission Planning & Simulation Architecture

**Document ID:** ARCH-2026-MP-001  
**Author:** Antigravity (Advanced Agentic Coding)  
**Date:** September 2026  
**Status:** Architecture Blueprint & Implementation Specification (Audit & Design Phase)  
**Problem Statement:** DRDO / iDEX PS-26054 (AI-Enabled Digital Twin for Aero Piston Engines)

---

## 1. Executive Summary & System Philosophy

Project ANUMAAN is an indigenous cyber-physical digital twin architecture for monitoring, diagnosing, and enhancing the mission reliability of aero-piston engines powering India's MALE UAV fleet (TAPAS-BH-201, Archer-NG).

While the propulsion physical modeling, residual anomaly detection, Bayesian diagnosis, and 3D engine twin visualization are fully operational across all 5 supported engine platforms, the **Mission Planning and Mission Simulation layer is currently missing as an integrated web capability**.

### Core Philosophy
1. **Engineering Simulation, Not Tactical Flight Dispatch**: The Mission Planner is an engineering and prognostics evaluation tool designed to answer three operational questions:
   - *Pre-flight:* Can this specific engine serial number, given its cumulative damage and health history, complete this planned sortie in this theater?
   - *In-flight:* Given newly detected degradation, what is the updated probability of mission completion, and what operational adjustments (throttle derating, altitude change, divert, RTB) preserve the airframe?
   - *Post-flight:* What was the total life consumption over the actual flight profile, and what maintenance actions are required before the next sortie?
2. **100% Web-Native Execution**: The entire mission planning and execution loop must run inside the single-page GCS web application (React + Three.js WebGL). No external desktop simulators (Blender GUI, command-line scripts) are permitted in production operations.
3. **No Decorative Placeholders or AI Slop**: Every plotted number, gauge reading, residual score, and 3D flight path must derive from authoritative mathematical models (aerodynamic kinematics, standard ISA atmosphere, convective thermofluid dynamics, Weibull hazard models, and FlyHash novelty encoding).

---

## 2. Comprehensive Codebase Audit

An exhaustive audit of the repository reveals the exact current state across all relevant subsystems:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PROJECT ANUMAAN AUDIT MAP                         │
├───────────────────────────────┬─────────────────────────────────────────────┤
│ SUBSYSTEM                     │ CURRENT REPOSITORY STATUS                   │
├───────────────────────────────┼─────────────────────────────────────────────┤
│ 1. Engine Physical Modeling   │ REAL: 5 profiles in PlantSource/RuntimeHub  │
│ 2. Residual Detectors         │ REAL: Calibrated sigma-spreads, conformal   │
│ 3. Bayesian Diagnosis         │ REAL: DiagnosticBayesianNetwork + Explainer │
│ 4. Mission Reliability Engine │ REAL: Weibull hazard + PrescriptiveAdvisor  │
│ 5. Three.js Engine 3D Twin    │ REAL: 5 high-res Draco GLBs, Station graphs │
│ 6. Historical Replay Engine   │ REAL: CSV playback with event marker seek   │
├───────────────────────────────┼─────────────────────────────────────────────┤
│ 7. Mission Profiles / Phases  │ PARTIAL: profiles.py has phase definitions  │
│ 8. FlyHash Novelty Gate       │ PARTIAL: Tested algorithm, uncalled in loop │
│ 9. UAV 3D Airframe Assets     │ PARTIAL: delta-pbr.glb in marketing site    │
│ 10. Terrain 3D Assets         │ PARTIAL: terrain.glb (2.09MB) in web/site   │
├───────────────────────────────┼─────────────────────────────────────────────┤
│ 11. Canyon Flight Simulator   │ DEMO/DESKTOP: Standalone script in Blender  │
│ 12. Mission Film / Story      │ DEMO: 18-scene scripted presentation        │
│ 13. Mission Knowledge Graph   │ DEMO/DESKTOP: Native Blender 3D node viewer │
├───────────────────────────────┼─────────────────────────────────────────────┤
│ 14. Mission Planner UI        │ NOT IMPLEMENTED: No route/phase builder     │
│ 15. Time-Stepped Mission Exec │ NOT IMPLEMENTED: No dynamic profile driver  │
│ 16. Web 3D Canyon Flight Twin │ NOT IMPLEMENTED: No WebGL flight viewer     │
│ 17. Automated Sortie Exporter │ NOT IMPLEMENTED: No sim-to-replay pipeline  │
└───────────────────────────────┴─────────────────────────────────────────────┘
```

### Detailed Subsystem Breakdown

#### A. `backend/mission/`
- **`profiles.py`**: Defines `MissionPhase` enum (`TAXI_OUT`, `TAKEOFF`, `CLIMB`, `CRUISE_TRANSIT`, `LOITER_RECON`, `DASH`, `DESCENT`, `APPROACH_LAND`, `TAXI_IN`, `SHUTDOWN`), `MissionSegment`, and `MissionProfile`. Provides `sample_at(t_sec)` returning `(phase, altitude_m, throttle_pct, tas_mps, aux_load_kw)`. **Limitation**: Static offline library; not hooked into `RuntimeHub` or WebSocket delivery.
- **`reliability.py`**: Defines a parallel `MissionPhase` dataclass (`name`, `duration_hours`, `altitude_ft`, `power_fraction`, `oat_c`, `dust_mg_m3`, `over_water`), `ComponentHazard`, and `MissionReliabilityEngine`. Provides analytical and Monte Carlo survival $R(t)$ over `ISR_18H_PROFILE`.
- **`prescriptive.py`**: Contains `PrescriptiveAdvisor` and `DerateOption`. Calculates trade-offs between throttle derating (100% down to 75%), reliability gain, and station endurance penalty (lost transit time).
- **`engine_components.py`**: Maps specific physical components and hazard rates for all 5 engine configurations.

#### B. `apps/blender_twin/standalone_canyon_flight_app.py`
- Native Blender desktop script (2,367 lines) launched via `launch_canyon_simulation.bat`.
- Uses `terrain.blend` containing a high-resolution DEM mesh of the Ladakh Nubra/Shyok river confluence (elevation 3,097m to 5,400m AMSL).
- Implements:
  - Flight kinematics (pitch, roll, yaw, 3x ground speed multiplier).
  - Raycast/heightfield ground-proximity radar and Auto-GCAS (2.5G pull-up).
  - Spring-damper chase camera with horizon leveling.
  - Convective CHT cooling in canyon gorge.
- **Limitation**: Strictly requires a local desktop Blender installation (`bpy`, `gpu`, `blf`). It cannot run inside a browser, cannot be embedded into React, and communicates only via a file drop (`runtime/flight_intent_command.json`).

#### C. Web 3D Models in `web/site/assets/models/`
- **`delta-pbr.glb`** (964 KB): Authentic tactical MALE UAV delta airframe with PBR metallic-roughness textures, landing gear, and control surfaces.
- **`terrain.glb`** (2.09 MB): Optimized triangulated Draco GLB mesh of the Ladakh canyon terrain with textured topography.
- **`drone-animations.glb`** (16 KB): Keyframed animation tracks for propellers and control surfaces.
- **Status**: These web-ready assets already exist in the repository, perfectly sized for sub-second web delivery, but are completely unused by the active GCS frontend (`frontend/src/`).

#### D. `backend/ml/flyhash_novelty.py`
- Implements fruit-fly olfactory-inspired sparse random projection (expand ~20x to 512 Kenyon cells, 5% winner-take-all sparsity) for one-pass novelty detection.
- Operates on a 26-dimensional dense vector: 13 physics residuals (`d_CHT_1..4`, `d_EGT_1..4`, `d_OIL_PRESS`, `d_OIL_TEMP`, `d_FUEL_FLOW`, `d_MAP`, `d_VIB_RMS`) and 13 crank vibration order features.
- Fully verified in `tests/test_flyhash_novelty.py`.
- **Limitation**: Currently disconnected from the live 20 Hz tick loop in `backend/runtime/engine_runtime.py`.

#### E. `backend/telemetry/replay_engine.py` & Historical Sorties
- Scans `data/telemetry/` for CSV sorties, parses metadata, extracts event markers, and serves interpolation frames via `/api/replay/{id}/frame`.
- `scripts/simulate_missions.py` produces batch runs of `EngineStateService` (Rotax 912 iS only) and dumps them into `report_dump/mission_NNN`.
- **Limitation**: The sortie replay is limited to pre-packaged historical files. When an operator runs a live simulation, there is no automated bridge to save it as an official sortie that immediately populates the Replay dropdown.

---

## 3. Mission Planning Product Definition

The integrated Mission Planning system establishes a closed-loop engineering workflow:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       END-TO-END MISSION WORKFLOW                           │
└─────────────────────────────────────────────────────────────────────────────┘

  [1. MISSION PLANNER]
        │ Operator defines Waypoints, Theater, Profile, Engine, Fault Schedule
        ▼
  [2. PRE-FLIGHT RELIABILITY GATE]
        │ MissionReliabilityEngine evaluates R(Sortie); Checks Go / No-Go
        ▼
  [3. EXECUTE MISSION]
        │ Time-stepped Mission Executive starts (1x, 2x, 5x, 10x sim rate)
        ├──▶ [4A. WEB 3D CANYON TWIN]
        │         UAV flies route in Three.js WebGL (altitude, bank, terrain)
        │
        └──▶ [4B. PROPULSION DIGITAL TWIN]
                  Interpolated (Alt, OAT, Throttle) injected into EngineRuntime
                  (All 5 Engines: Rotax 912/914/915, Austro AE300, VRDE 2.2L)
                        │
                        ▼
  [5. SENSOR TELEMETRY & PHYSICAL RESIDUALS]
        │ Frame channels (CHT, EGT, RPM, MAP, Pressures, Vibrations)
        ▼
  [6. FLYHASH NOVELTY & RESIDUAL DETECTORS]
        │ FlyHash sparsifies residuals/orders; Conformal anomaly gate fires
        ▼
  [7. BAYESIAN ROOT-CAUSE DIAGNOSIS]
        │ Causal network isolates failure mode, component, ambiguity group
        ▼
  [8. IN-FLIGHT MISSION RELIABILITY & OPERATOR DECISION]
        │ PrescriptiveAdvisor computes derate schedule and endurance penalty
        │ Operator chooses: CONTINUE / DERATE / DIVERT / RTB / ABORT
        ▼
  [9. MISSION COMPLETION]
        │ UAV touches down; Post-flight debrief generated
        ▼
  [10. AUTONOMOUS SORTIE PACKAGING]
        │ Writes telemetry CSV, event log, PHM summary to data/telemetry/
        ▼
  [11. HISTORICAL MISSION REPLAY & AUDIT]
        │ Instantly scrubbable and playable in Mission Replay tab
```

---

## 4. Canonical Mission Models

### 4.1 Canonical `MissionDefinition`
The mission definition contains strictly what is required to execute the flight profile, environment, and physical plant:

```python
@dataclass
class Waypoint:
    id: str
    name: str
    lat: float                     # Decimal degrees (e.g. 34.2500)
    lon: float                     # Decimal degrees (e.g. 77.5800)
    alt_msl_m: float               # Target altitude above sea level in meters
    airspeed_ktas: float           # Commanded true airspeed in knots
    loiter_radius_m: float = 0.0   # > 0 indicates loiter waypoint
    loiter_duration_sec: float = 0.0
    terrain_alt_m: float = 0.0     # Ground elevation below waypoint

@dataclass
class ScheduledEvent:
    trigger_time_sec: float        # Mission elapsed time for event trigger
    action: str                    # "INJECT_FAULT", "WEATHER_CHANGE", "THROTTLE_BURST"
    fault_mode: Optional[str] = None      # e.g. "COOLING_DEGRADATION", "BOOST_LEAK"
    cylinder: Optional[int] = None        # None for engine-wide, 1-4 for per-cylinder
    severity: float = 0.8                 # 0.1 to 1.0
    ramp_sec: float = 10.0                # Time to reach full severity
    target_value: Optional[float] = None  # For weather/throttle transients

@dataclass
class EnvironmentalConditions:
    theater_name: str              # "LADAKH_HIGH_COLD", "THAR_HOT_HIGH", "COASTAL_MARITIME"
    qnh_hpa: float                 # Sea level pressure (default: 1013.25 hPa)
    isa_temp_offset_c: float       # Deviation from standard temperature (e.g. -20C or +30C)
    base_elevation_m: float        # Airfield ground elevation (Ladakh: 3,300m, Coastal: 15m)
    ambient_wind_kt: float         # Steady wind speed
    wind_direction_deg: float      # Wind direction
    dust_density_mg_m3: float      # Ingested particulate concentration

@dataclass
class MissionDefinition:
    mission_id: str                # e.g. "MSN-2026-LADAKH-001"
    name: str                      # "Ladakh High-Altitude Deep Canyon Reconnaissance"
    engine_id: str                 # "rotax_912is", "rotax_914", "rotax_915is", "austro_ae300", "vrde_jayem_2_2l"
    airframe_id: str               # "TAPAS-BH-201"
    planned_duration_sec: float    # Nominal sortie time (e.g. 14,400s / 4h or 64,800s / 18h)
    environment: EnvironmentalConditions
    waypoints: List[Waypoint]
    scheduled_events: List[ScheduledEvent] = field(default_factory=list)
```

### 4.2 Canonical `MissionState`
The mission state represents the single authoritative snapshot published at 10–20 Hz during simulation:

```python
@dataclass
class MissionState:
    mission_id: str
    status: str                    # DRAFT, READY, RUNNING, PAUSED, COMPLETED, ABORTED
    phase: str                     # PREFLIGHT, TAKEOFF, CLIMB, TRANSIT, CRUISE, LOITER, DESCENT, APPROACH, LANDED
    time_elapsed_sec: float
    time_remaining_sec: float
    time_scale: float              # 1.0, 2.0, 5.0, 10.0
    
    # Kinematics & Navigation
    pos_x_m: float                 # Local Easting (m) relative to theater datum
    pos_y_m: float                 # Local Northing (m) relative to theater datum
    pos_z_m: float                 # Altitude AMSL (m)
    ground_elevation_m: float      # Terrain surface elevation immediately below UAV
    agl_m: float                   # Height above ground (pos_z_m - ground_elevation_m)
    ground_speed_mps: float
    true_airspeed_ktas: float
    indicated_airspeed_kias: float
    heading_deg: float
    pitch_deg: float
    roll_bank_deg: float
    current_waypoint_idx: int
    waypoint_distance_remaining_m: float
    path_progress_fraction: float  # 0.0 to 1.0 along current leg
    
    # Atmospheric Condition at UAV Altitude
    ambient_oat_c: float
    ambient_pressure_hpa: float
    density_altitude_ft: float
    
    # Commanded Propulsion Demand
    commanded_throttle_pct: float
    effective_engine_load_pct: float
    
    # Propulsion State (from EngineRuntime)
    engine_id: str
    rpm: float
    max_cht_c: float
    max_egt_c: float
    oil_press_bar: float
    fuel_flow_kg_h: float
    
    # PHM & Anomaly State
    active_faults: List[Dict[str, Any]]
    residual_alarm: bool
    confirmed_anomaly: bool
    top_divergent_channel: Optional[str]
    flyhash_novelty_score: float
    is_novel_pattern: bool
    top_diagnostic_hypothesis: Optional[str]
    diagnostic_confidence: float
    limiting_component: str
    mission_reliability: float     # Analytic P(Survival) for remainder of sortie
    prescriptive_advisory: str
```

---

## 5. Mission State Machine

The mission executive transitions through standard flight phases and enforces deterministic handling of anomalies:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MISSION STATE MACHINE                               │
└─────────────────────────────────────────────────────────────────────────────┘

 [DRAFT] ──(Validate)──▶ [READY] ──(Arm & Preflight)──▶ [PREFLIGHT]
                                                            │
                                                     (Throttle 100%)
                                                            ▼
                                                       [TAKEOFF]
                                                            │
                                                     (AGL > 100m)
                                                            ▼
                                                        [CLIMB]
                                                            │
                                                   (Alt >= Waypoint 1)
                                                            ▼
                                                       [TRANSIT]
                                                            │
                                                   (Reach Loiter WP)
                                                            ▼
                                                       [LOITER]
                                                            │
                                                   (Loiter Timer Expired)
                                                            ▼
                                                    [RETURN_TRANSIT]
                                                            │
                                                   (Reach IAF Point)
                                                            ▼
                                                       [DESCENT]
                                                            │
                                                   (AGL < 150m)
                                                            ▼
                                                       [LANDING]
                                                            │
                                                   (Ground Contact)
                                                            ▼
                                                      [COMPLETED]

 ═══════════════════════════════════════════════════════════════════════════════
                         ABNORMAL CONTINGENCY BRANCHES
 ═══════════════════════════════════════════════════════════════════════════════
   Any Phase ──(Residual / FlyHash Alarm)──▶ [ALERT_WARNING]
                                                    │
                             ┌──────────────────────┴──────────────────────┐
                             ▼                                             ▼
                      [DERATED_CONTINUE]                             [TACTICAL_DIVERT]
                    (Operator approves derate)                    (Divert to nearest runway)
                             │                                             │
                             └──────────────────────┬──────────────────────┘
                                                    ▼
                                            [EMERGENCY_RTB]
                                     (Immediate return to base)
                                                    │
                                                    ▼
                                            [MISSION_ABORT]
```

### Transition Specifications

| Current State | Event / Guard Condition | Target State | Action Taken |
| :--- | :--- | :--- | :--- |
| `DRAFT` | Validated route, elevations, limits | `READY` | Pre-flight reliability check calculated |
| `READY` | Operator commands START | `PREFLIGHT` | PlantSource engine run-up, calibration verify |
| `PREFLIGHT` | Checklist complete, spool up | `TAKEOFF` | Throttle to 100%, ground roll integration |
| `TAKEOFF` | $z_{AGL} \ge 100\text{ m}$ | `CLIMB` | Pitch $+8^\circ$, throttle 92%, high thermal stress |
| `CLIMB` | $z \ge z_{\text{cruise}} - 50\text{ m}$ | `TRANSIT` | Level off, throttle 75%, cruise airspeed |
| `TRANSIT` | Dist to Target $\le 500\text{ m}$ | `LOITER` | Enter orbit, throttle 60%, endurance mode |
| `LOITER` | Loiter duration elapsed | `RETURN_TRANSIT` | Turn to base heading, climb/cruise |
| `RETURN_TRANSIT`| Distance to IAF $\le 5\text{ km}$ | `DESCENT` | Throttle 35%, descent rate $500\text{ ft/min}$ |
| `DESCENT` | $z_{AGL} \le 150\text{ m}$ | `LANDING` | Full flaps, flare, touch down |
| `LANDING` | Ground velocity $\le 2\text{ kt}$ | `COMPLETED` | Engine shutdown, export sortie archive |
| **Any Active** | Confirmed Anomaly ($P(F\|E) > 0.85$) | `ALERT_WARNING` | Trigger chime, display prescriptive advisory |
| `ALERT_WARNING`| Operator accepts derate | `DERATED_CONTINUE`| Derate throttle by computed %, recalc ETA |
| `ALERT_WARNING`| $R(\text{Sortie}) < 0.60$ or catastrophic fault | `EMERGENCY_RTB` | Override waypoints with direct vector to base |

---

## 6. Route & Waypoint Coordinate System

### Coordinate Frame Transformation
To bridge real-world geospatial coordinates (WGS84 lat/lon) with the 3D WebGL rendering world without float precision degradation, the system uses a **Local Tangent Plane (LTP) East-North-Up (ENU)** projection centered on the theater datum.

#### Ladakh Theater Datum:
- **Reference Origin:** Latitude $34.2500^\circ\text{ N}$, Longitude $77.5800^\circ\text{ E}$, Elevation $3,097.64\text{ m}$ AMSL (Nubra/Shyok river confluence).
- **Transformation Equations:**
  $$\Delta \text{lat} = \text{lat} - \text{lat}_0, \quad \Delta \text{lon} = \text{lon} - \text{lon}_0$$
  $$X_{\text{local}} = \Delta \text{lon} \times \frac{\pi}{180} \times R_{\text{earth}} \times \cos(\text{lat}_0)$$
  $$Y_{\text{local}} = \Delta \text{lat} \times \frac{\pi}{180} \times R_{\text{earth}}$$
  $$Z_{\text{local}} = \text{alt}_{\text{AMSL}} - \text{elevation}_0$$

#### WebGL Three.js Scene Mapping:
In Three.js, $+X$ maps to East, $+Z$ maps to South, and $+Y$ maps to Altitude (Up).
$$\mathbf{P}_{\text{three}} = \begin{bmatrix} X_{\text{local}} \cdot s \\ (z_{\text{AMSL}} - z_{\text{datum}}) \cdot s \\ -Y_{\text{local}} \cdot s \end{bmatrix}$$
where $s = 0.001$ (1 Three.js unit = 100 meters).

```
   North (+Y_local)
        ▲
        │       WP2 (Loiter Target)
        │      /
        │     /   [Canyon Gorge Flight Corridor]
        │    /
        │   WP1 (Canyon Ingress)
        │  /
        │ /
        └────────────────────▶ East (+X_local)
      Datum Origin (Airfield Base)
```

---

## 7. Flight Profile Engine & Environmental Simulation

The Flight Profile Engine runs deterministically on the backend at 20 Hz, deriving instantaneous physical environmental inputs for `EngineRuntime`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FLIGHT PROFILE DRIVER                                │
└─────────────────────────────────────────────────────────────────────────────┘

    Mission Elapsed Time (t)
             │
             ├──▶ Waypoint Interpolator ──▶ (Lat, Lon, Alt, Heading, Groundspeed)
             │                                   │
             │                                   ├──▶ Atmospheric ISA Model
             │                                   │    · Outside Air Temp (OAT)
             │                                   │    · Ambient Pressure (MAP)
             │                                   │    · Density Altitude
             │                                   │
             │                                   └──▶ Flight Mechanics Model
             │                                        · Commanded Throttle %
             │                                        · Dynamic Headwind/Load
             │
             ▼
    EngineRuntime.set_levers(
        throttle_pct = commanded_throttle,
        altitude_ft  = altitude_ft,
        oat_c        = current_oat_c
    )
```

### Standard Mission Scenarios
The simulator natively provides four standardized defense operational presets:
1. **Ladakh High-Altitude Cold Reconnaissance**:
   - Base elevation: 3,300m AMSL (Leh).
   - Ingress altitude: 15,000 ft (canyon gorge flight).
   - Loiter altitude: 28,000 ft AMSL (high loiter over Karakoram).
   - OAT: $-35^\circ\text{C}$ to $-42^\circ\text{C}$.
   - Tests turbocharger pressure ratios, cold-soak oil viscosity, and high-altitude density derating.
2. **Thar Desert Hot-and-High Border Patrol**:
   - Base elevation: 350m AMSL (Jaisalmer).
   - Patrol altitude: 12,000 ft AMSL.
   - OAT: $+45^\circ\text{C}$ at ground, $+22^\circ\text{C}$ at altitude.
   - High dust ingestion ($2.5\text{ mg/m}^3$).
   - Tests cooling radiator margins, CHT limit breaches, and air filter blockages.
3. **18-Hour Endurance Maritime Loiter**:
   - Base elevation: 15m AMSL.
   - Loiter altitude: 18,000 ft AMSL, low power setting (55% MCP).
   - Tests cumulative wear, subtle parameter drift, and predictive RUL convergence over extended operational life.
4. **Tactical Canyon Low-Level Dash (Rapid Throttle Transients)**:
   - Rapid spooling from 35% to 100% throttle through winding terrain.
   - Tests thermal shock, turbo lag, and transient false-alarm suppression in residual detectors.

---

## 8. Web 3D Canyon & UAV Simulation Architecture

Rather than relying on desktop Blender, the Canyon Simulation is ported to a modern, high-performance WebGL environment:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WEB 3D CANYON FLIGHT ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────────────┘

  Three.js WebGL Scene (Canvas in Mission Tab)
  ├── Environment & Sky
  │   ├── Procedural Himalayan Atmospheric Fog / Rayleigh Scattering
  │   └── Directional Sun Light (tactical shadows, low grazing angle)
  │
  ├── Terrain Layer (Ladakh Mesh)
  │   ├── web/site/assets/models/terrain.glb (Draco-compressed DEM)
  │   ├── Tactical Topo Shader (Wireframe elevation contours, valley shading)
  │   └── Radar Heightfield Probing (GPU or CPU raycast for instantaneous AGL)
  │
  ├── Airframe Model
  │   ├── web/site/assets/models/delta-pbr.glb (Authentic MALE Tactical UAV)
  │   ├── Coordinated Banking Kinematics (Roll proportional to turn rate)
  │   ├── Propeller Spool Animation (RPM driven by backend engine state)
  │   └── Thermal Glow Shader (Engine cowl highlights hot cylinder heads)
  │
  ├── Mission Overlays
  │   ├── 3D Waypoint Pillars (Glowing cylindrical pylons with labels)
  │   ├── Active Corridor Ribbon (Polyline path showing flown vs. planned route)
  │   └── Auto-GCAS Warning Cone (Amber/Red projection when AGL < 80m)
  │
  └── Chase Camera Controller
      ├── Hero Chase View (Smooth spring-damper trailing UAV tail)
      ├── Tactical Top-Down Map View (Orthographic reconnaissance)
      └── Cockpit / Forward FLIR Gimbal View
```

---

## 9. Multi-Engine Propulsion Integration

The Mission Simulation drives the selected engine in the existing concurrent `RuntimeHub`. No engine is a placeholder.

| Engine Platform | Displacement & Induction | Mission Operating Envelope | Characteristic Degradation in Mission |
| :--- | :--- | :--- | :--- |
| **Rotax 912 iS Sport** | 1.35L Flat-4, Naturally Aspirated | Sea level to 16,000 ft; moderate altitude | Severe power fall-off in Ladakh climb; CHT overheat during high ambient summer sorties. |
| **Rotax 914 UL/F** | 1.21L Flat-4, Turbocharged | Up to 25,000 ft; turbo wastegate control | Wastegate stuck open limits max climb rate; boost leak causes EGT escalation and MAP loss. |
| **Rotax 915 iS** | 1.35L Flat-4, Turbo Intercooled | Up to 30,000 ft; high ceiling | Intercooler fouling reduces charge density at FL280; dual-ignition coil drift. |
| **Austro Engine AE300** | 2.0L Inline-4, Common Rail Diesel | Up to 28,000 ft; Jet-A1 / Diesel | HP pump cavitation under cold-soak; injector coking creates cylinder EGT spread. |
| **VRDE-Jayem 2.2L** | 2.2L Inline-4, High-Altitude Diesel | Up to 32,000 ft; Heavy Fuel UAV | Rail pressure decay during loiter; turbocharger bearing vibration under prolonged high load. |

When the operator switches the active engine in the Mission Planner, the backend automatically instantiates the correct plant source, calibrated limits, and fault library, while the UI binds the corresponding detailed Draco 3D asset.

---

## 10. Dual-Mode Fault & Event Scheduling Pipeline

The system provides identical diagnostic handling regardless of whether a fault was scheduled in advance or triggered live by the operator:

```
                   ┌──────────────────────────────────┐
                   │  SCHEDULED IN MISSION DEFINITION │
                   │  (e.g. T+1200s: INJECTOR_COKING) │
                   └────────────────┬─────────────────┘
                                    │
                                    │  [Same Dispatch Mechanism]
                                    ▼
┌───────────────────────┐   POST /api/engines/{id}/faults   ┌───────────────────────┐
│     OPERATOR LIVE     │──────────────────────────────────▶│  BACKEND PLANT MODEL │
│    FAULT INJECTION    │                                   │  (Combustion physics) │
└───────────────────────┘                                   └───────────┬───────────┘
                                                                        │
                                                                        ▼
                                                            Raw Sensor Telemetry
                                                                        │
                                                                        ▼
                                                            Calibrated Residuals
                                                                        │
                                                                        ▼
                                                            FlyHash Novelty Gate
                                                                        │
                                                                        ▼
                                                            Residual Detector Alarm
                                                                        │
                                                                        ▼
                                                            Bayesian Network Diagnosis
                                                                        │
                                                                        ▼
                                                            3D Component Localization
                                                                        │
                                                                        ▼
                                                            Prescriptive Derate Advisory
```

---

## 11. FlyHash Novelty Gate Integration

`backend/ml/flyhash_novelty.py` is integrated directly into the 20 Hz frame processing pipeline as an unsupervised first-line novelty filter:

```python
# Integration in EngineRuntime.ingest()
if self.detector is not None:
    # 1. Compute physics residuals
    res_vec = self.detector.cal.z(frame)
    
    # 2. Extract vibration order features
    order_feats = self.source.order_features()
    
    # 3. Dense 26-dim feature vector
    feat_26d = residual_and_order_features(res_vec, order_feats)
    
    # 4. FlyHash projection & sparsity check
    novelty_report = self.flyhash.score(feat_26d)
    
    # 5. Pass novelty flag to diagnosis and telemetry state
    tick.novelty = novelty_report
```

In the web interface, FlyHash is exposed as an **Early Anomaly Novelty Indicator** showing:
- Active Kenyon Cell Bit Density (nominally ~5%).
- Novel Bit Fraction ($0.0$ to $1.0$).
- Novelty Gate Status: `NOMINAL`, `UNPRECEDENTED_FEATURE_PATTERN`, `CONFIRMED_ANOMALY`.

---

## 12. Mission Decision & Prescriptive Response Loop

When degradation is detected during a mission, the system does not simply alert the operator; it provides actionable prescriptive derating options generated by `backend/mission/prescriptive.py`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PRESCRIPTIVE ADVISORY PANEL                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ ALERT: Cylinder #2 Injector Coking Detected (P = 0.94, ATA 73)              │
│ Status: Degradation rate +35%/hr. Limiting component: Injector 2            │
│ Unadjusted Sortie Reliability: 0.64 (NO-GO for remaining 6.5 hours)         │
├─────────────────────────────────────────────────────────────────────────────┤
│ RECOMMENDED OPERATOR ACTION:                                                │
│ "Derate to 85% MCP: damage rate reduces 40%, reliability 0.64 -> 0.92,       │
│  endurance penalty +14 min on station transit."                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ AVAILABLE ACTIONS:                                                          │
│  [ APPLY 85% DERATE ]  [ DIVERT TO LEH (28 NM) ]  [ EXECUTE IMMEDIATE RTB ] │
└─────────────────────────────────────────────────────────────────────────────┘
```

Clicking **APPLY 85% DERATE** immediately updates the Mission Executive's active profile, commanding the engine throttle down, extending component life, and updating the mission completion probability.

---

## 13. Generated Sorties & Autonomous Debrief Pipeline

Fabricated or static sortie CSVs are superseded by an automated generation pipeline. When a mission completes or is aborted:

1. **Telemetry Logging**: Every 20 Hz tick is recorded into a streaming in-memory buffer.
2. **Artifact Serialization**:
   - `data/telemetry/{mission_id}.csv`: Complete time-series with all 27 engine parameters, coordinates, and detector ratios.
   - `data/telemetry/{mission_id}_manifest.json`: Metadata containing route, waypoints, engine serial number, injected faults, and event markers with timestamps.
   - `report_dump/{mission_id}/debrief.md`: Formal engineering debrief report detailing timeline, exceedances, RUL consumption, and maintenance work orders.
3. **Instant Replay Integration**:
   - `ReplayEngine` immediately indexes the new sortie.
   - The user can click **"Open in Replay"** directly from the Mission Completion screen to scrub through the flight.

---

## 14. Web UI Screen Architecture

The Mission Planning and Simulation capability is integrated into the GCS navigation through a dedicated top-level tab: **"Mission / Operations"** (`MISSION_PLANNER`), accompanied by three operational sub-views:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MISSION OPERATIONS INTERFACE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ [ Sub-Tab 1: PLANNER ]      [ Sub-Tab 2: SIMULATION ]    [ Sub-Tab 3: DEBRIEF ]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────┐   ┌─────────────────────────────────┐  │
│  │ 3D CANYON FLIGHT VIEW           │   │ REAL-TIME PROPULSION TELEMETRY  │  │
│  │                                 │   │                                 │  │
│  │ [WebGL Three.js Canvas]         │   │ · RPM: 2,340      · MAP: 1.8 bar│  │
│  │ · Ladakh DEM Terrain Mesh       │   │ · CHT2: 142°C     · EGT2: 710°C │  │
│  │ · Delta UAV Flight Track        │   │ · Oil: 94°C       · Fuel: 18L/h │  │
│  │ · Waypoint Gate Overlays        │   │                                 │  │
│  │ · AGL Proximity HUD             │   │ [Live Residual / Sigma Chart]   │  │
│  │                                 │   │                                 │  │
│  └─────────────────────────────────┘   └─────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ MISSION TIMELINE & FLIGHT CONTROLS                                    │  │
│  │ [◀◀] [▶] [⏸] [▶▶ 2x] [▶▶ 5x]   T+02:14:35 / 06:00:00   Phase: LOITER   │  │
│  │ ─────────────────────────────────●─────────────────────────────────── │  │
│  │ WP1 (Climb) ──── WP2 (Ingress) ──── WP3 (Target Orbit) ──── WP4 (RTB) │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────┐   ┌─────────────────────────────────┐  │
│  │ MISSION RELIABILITY & ADVISORY  │   │ FLYHASH & DIAGNOSTIC DIRECTIVE  │  │
│  │ R(t=6h): 94.2%  Limiting: Inj 2 │   │ Novelty: 0.04 (Nominal)         │  │
│  │ Prescriptive: 85% Derate Rec.   │   │ Diagnosis: Normal combustion    │  │
│  └─────────────────────────────────┘   └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 15. Backend REST API Design

| Method | Endpoint | Description | Request Body | Response Payload |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/missions/templates` | List standard mission presets | None | Array of `MissionDefinition` presets |
| `POST` | `/api/missions/validate` | Validate mission & compute preflight reliability | `MissionDefinition` | `{ valid: bool, reliability: float, limiting_component: str }` |
| `POST` | `/api/missions/start` | Launch real-time mission simulation | `MissionDefinition` | `{ session_id: str, status: "RUNNING" }` |
| `POST` | `/api/missions/pause` | Pause simulation clock | `{ session_id: str }` | `{ status: "PAUSED" }` |
| `POST` | `/api/missions/resume` | Resume simulation clock | `{ session_id: str, time_scale: float }` | `{ status: "RUNNING", time_scale: float }` |
| `POST` | `/api/missions/abort` | Abort mission and command RTB | `{ session_id: str, reason: str }` | `{ status: "ABORTING" }` |
| `POST` | `/api/missions/derate` | Apply prescriptive throttle derate | `{ session_id: str, power_scale: float }` | `{ applied_scale: float, updated_reliability: float }` |
| `GET` | `/api/missions/state` | Instantaneous mission state snapshot | None | `MissionState` JSON object |
| `POST` | `/api/missions/export` | Finalize simulation and package sortie | `{ session_id: str }` | `{ sortie_id: str, csv_path: str, debrief_path: str }` |

---

## 16. WebSocket Streaming Specification

### Endpoint: `/ws/mission`
Pushes binary/JSON frames at 20 Hz during mission execution.

#### Message Payload:
```json
{
  "type": "MISSION_FRAME",
  "t": 1425.05,
  "status": "RUNNING",
  "phase": "LOITER",
  "kinematics": {
    "pos": [4120.5, 7680.2, 4572.0],
    "agl_m": 1474.36,
    "speed_ktas": 140.2,
    "heading_deg": 38.4,
    "pitch_deg": 1.2,
    "roll_deg": -3.5
  },
  "atmosphere": {
    "oat_c": -28.4,
    "pressure_hpa": 571.2,
    "density_alt_ft": 16420.0
  },
  "engine": {
    "engine_id": "austro_ae300",
    "throttle_pct": 65.0,
    "rpm": 2180.0,
    "cht": [138.2, 139.1, 140.4, 137.9],
    "egt": [680.0, 685.2, 692.1, 678.4],
    "oil_press_bar": 4.15
  },
  "phm": {
    "residual_alarm": false,
    "flyhash_score": 0.03,
    "is_novel": false,
    "reliability": 0.948,
    "limiting_component": "injector_2"
  }
}
```

---

## 17. Phased Implementation Roadmap

```
PHASE 1: Core Mission Models & Executive Engine
├── Define MissionDefinition & MissionState schemas in backend/mission/
├── Implement MissionExecutive time-stepped simulation runner (1x to 10x)
└── Wire ISA atmospheric & waypoint interpolation models

PHASE 2: EngineRuntime & Lever Integration
├── Connect MissionExecutive outputs to EngineRuntime.set_levers()
├── Ensure all 5 engines (Rotax 912/914/915, Austro, VRDE) respond dynamically
└── Wire scheduled & live fault injection dispatch

PHASE 3: FlyHash & PHM Pipeline Wiring
├── Hook backend/ml/flyhash_novelty.py into EngineRuntime.ingest()
├── Wire residual detectors and Bayesian diagnosis to mission frame state
└── Compute dynamic mission reliability from actual flight damage

PHASE 4: Web 3D Canyon Flight Twin
├── Port canyon flight logic to Three.js canvas in frontend/
├── Load delta-pbr.glb, terrain.glb, and procedural sky
└── Implement flight kinematics, waypoint pillars, and Auto-GCAS HUD

PHASE 5: Mission Planner & Execution UI
├── Build MissionPlannerForm (waypoints, preset selection, fault schedule)
├── Build MissionCockpitView (3D flight canvas + instruments + timeline)
└── Build PrescriptiveAdvisoryCard (derate options + divert controls)

PHASE 6: Autonomous Sortie Packaging & Replay Bridge
├── Build SortieExporter serializing simulation runs to data/telemetry/*.csv
├── Auto-generate markdown engineering debrief in report_dump/
└── Link finished missions directly into MissionReplayScrubber

PHASE 7: Regression Testing & Full Verification
├── Backend pytest suite covering mission state machine and profile math
├── Playwright end-to-end tests verifying 5-engine mission simulation in browser
└── Visual verification of 3D WebGL flight and terrain rendering
```

---

## 18. Verification & Acceptance Criteria

1. **Multi-Engine Parity**: All 5 engine configurations must complete an accelerated 2-hour mission profile, streaming realistic physical telemetry matching their displacement and induction types.
2. **Dynamic Environmental Physics**: Flying the same engine profile under the Ladakh preset ($-35^\circ\text{C}$, 25,000 ft) versus the Thar preset ($+45^\circ\text{C}$, 12,000 ft) must produce measurably different CHT/EGT temperatures and cooling margins.
3. **End-to-End Fault Propagation**: An injected or scheduled fault (`COOLING_DEGRADATION` or `INJECTOR_COKING`) must cause:
   - Elevation in physical residuals.
   - Elevation in FlyHash novelty score.
   - Confirmation by residual detector.
   - Causal attribution by Bayesian network with correct ATA chapter.
   - Immediate drop in mission reliability $R(t)$.
   - Generation of actionable prescriptive derate recommendation.
4. **Interactive 3D WebGL Fidelity**: The WebGL canyon view must render `delta-pbr.glb` and `terrain.glb` at $\ge 60\text{ FPS}$ on desktop Chrome/Edge without any dependency on external Blender processes.
5. **Sortie Generation & Replay**: Immediately upon mission completion, the generated sortie must appear in the Mission Replay tab with fully scrubbable telemetry and accurate event markers.
