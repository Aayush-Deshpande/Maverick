# Rigging, Animation, Engine Behaviour & Mission Simulation Spec

**Purpose:** define how each platform moves, how each engine behaves physically, and how missions are simulated and replayed. Covers the parts of PS-26054 §E (Simulation & Replay) that the 3D assets must support, and the physics generalization that every new engine depends on.

Labels: ✅ verified from code/references · 🟦 our proposal · ❓ unverified, must be confirmed in Phase 0.

---

## 1. Rigging & Animation

### 1.1 What the TB3 baseline does today ✅

| Mechanism | Implementation (`build_tb3_digital_twin.py`) |
|---|---|
| Wing fold | Control empty `CTRL_Wing_Fold`; its Z location drives the fold via constraints. Z location is **keyframed on the global timeline** at frames 1/120/170/210/250 |
| Gear retract | Control empty `CTRL_Gear_Retract`, keyframed at frames 1/40/60/80/100 |
| Propeller | `pivot_prop.rotation_euler` keyframed frame 1 → 250 (fixed rotation, not RPM-driven) |
| UI control | Panel properties `tb3_wing_fold` / `tb3_gear_retract` write the control empty's location; the separate controller (`tb3_digital_twin_controller.py`) instead calls `scene.frame_set(60)` / `frame_set(180)` |

Validation scripts exist for this rig: `test_wing_fold_driver.py`, `test_gear_constraint.py`, `test_transform_constraint.py`, `verify_kinematics.py`.

### 1.2 Defect: mechanisms are coupled to the global timeline ❌

Three problems follow directly from the keyframed-control-empty approach:

1. **Replay collision.** Mission replay (§4) needs to scrub time. Any change to `scene.frame_current` re-evaluates the keyframes and silently folds wings or moves gear to whatever the demo animation had at that frame. The aircraft visibly does things the telemetry never said.
2. **Two competing controllers.** The panel writes `ctrl.location.z` directly, but the F-curve overwrites it on the next frame change. The second controller moves the timeline instead. Which one "wins" depends on call order.
3. **Propeller is decorative.** A fixed 250-frame rotation cannot represent `PROP_RPM`, so the one continuously visible indicator of engine state is disconnected from the engine.

### 1.3 Rigging requirements for all platforms 🟦

| # | Requirement |
|---|---|
| R1 | **Mechanism state is driven by named custom properties through drivers, never by global-timeline keyframes.** The timeline is reserved for replay time |
| R2 | One authoritative source per mechanism: the twin state (live or replay). UI sliders write the same property the twin writes |
| R3 | Normalized 0.0–1.0 inputs per mechanism (`gear_retract`, `wing_fold`, `flap_deflection`), mapped to real angles inside the driver |
| R4 | Propeller rotation computed per frame from `PROP_RPM` and elapsed wall/replay time, not keyframed |
| R5 | Above a threshold (🟦 ~300 prop RPM) swap blades for a translucent blur disc. Real prop speeds alias badly at 30–60 FPS (wagon-wheel effect) and look *wrong*, not fast |
| R6 | Control surfaces rigged at hinge lines with real deflection limits (❓ per platform) |
| R7 | Mechanism list declared in the platform manifest (`mechanisms: [...]`, doc 03 §3.2); the client builds no UI for mechanisms a platform does not have |
| R8 | Rig pivots in real units at real hinge positions; the rig must survive the Z-offset ground alignment |
| R9 | **No internal engine animation** (pistons, valves, crank). Not a PS requirement, costly, and invisible at inspection distances. Prop shaft rotation is the only moving engine part |

**Fix for the existing TB3:** convert `CTRL_Wing_Fold`, `CTRL_Gear_Retract` and `pivot_prop` from keyframes to property drivers; delete the `frame_set` calls in `tb3_digital_twin_controller.py`. This is part of Phase 2.

### 1.4 Per-platform mechanism matrix ❓ confirm against orthographic references in Phase 0

| Platform | Prop config | Engine count | Gear | Special mechanisms |
|---|---|---|---|---|
| Bayraktar TB3 | Pusher | 1 | Retractable (modelled) | **Folding wings** (carrier ops, modelled) |
| TAPAS BH-201 | ❓ Tractor, wing-mounted | ❓ **Believed 2** | ❓ | ❓ |
| Bayraktar TB2 | Pusher | 1 | ❓ | — |
| MQ-1 Predator | Pusher | 1 | ❓ | Ventral fin |
| IAI Heron Mk II | Pusher | 1 | ❓ | Twin tail booms |
| TAI ANKA | Pusher | 1 | ❓ | — |
| CASC CH-4 | Pusher | 1 | ❓ | — |

> ⚠️ **If TAPAS BH-201 is twin-engine, it contradicts the central narrative of the existing docs** ("MALE UAVs rely on a single engine... if it fails the aircraft is lost", `docs/guide/01_problem_statement_and_analysis.md`), which currently names TAPAS as a target platform. It also means the TAPAS twin needs *two* engine instances, per-engine telemetry streams, and asymmetric-thrust fault scenarios. Resolve this before any TAPAS modelling. See [doc 05 §4](05_deliverables_validation_acceptance.md).

---

## 2. Engine Behaviour & Physics Generalization

### 2.1 Current physics model ✅

`backend/physics/thermo_model.py`, module-level constants:

```python
DISPLACEMENT_CC       = 1352.0   # Rotax 912 iS
BORE_MM               = 84.0
STROKE_MM             = 61.0
COMPRESSION_RATIO     = 10.8
GEAR_REDUCTION_RATIO  = 2.43
volumetric_efficiency = 0.82 + 0.08 * (throttle_norm ** 0.5)   # throttled SI engine
```

This is a **throttled, naturally aspirated, spark-ignition** formulation. `backend/physics/sensor_validator.py` rate-of-change limits are likewise "Rotax 912 iS thermal response data". The ML models are trained exclusively on `rotax912_*_dataset.csv`.

### 2.2 Engine parameter matrix

Sources: ✅ = from `Models_Images/*/descr.md` or `thermo_model.py`; ❓ = commonly published figure, **not yet verified against a primary source**.

| Parameter | Rotax 912 iS | Rotax 914 F | Rotax 915 iS | TEI PD170 | Austro AE330 | Lark HFE |
|---|---|---|---|---|---|---|
| Serves | TB2 | MQ-1 | Heron Mk II | TB3, ANKA | TAPAS ❓ | CH-4 |
| Cycle | Spark (SI) | Spark (SI) | Spark (SI) | **Diesel (CI)** ✅ | **Diesel (CI)** ✅ kerosene | **Diesel (CI)** ✅ heavy fuel |
| Layout | Boxer-4 | Boxer-4 | Boxer-4 | Inline-4 ✅ | Inline-4 ❓ | 4-cyl ✅ |
| Displacement | 1,352 cc ✅ | 1,211 cc ❓ | 1,352 cc ❓ | 2,100 cc ✅ | 1,991 cc ✅ | ❓ |
| Aspiration | Natural | Turbo ❓ | Turbo + IC ❓ | 2-stage sequential turbo + IC ✅ | Turbo ❓ | Turbo + IC ✅ |
| Max power | 100 hp ❓ | 115 hp ❓ | 141 hp ❓ | 172 hp TO / 170 hp MCP ✅ | 180 hp TO / 171 hp MCP ✅ | 150 hp ✅ |
| Max torque | ❓ | ❓ | ❓ | ❓ | 550 Nm ✅ | ❓ |
| Prop RPM (max) | ~2,388 (5,800 ÷ 2.43) ❓ | ❓ | ❓ | 2,300 ✅ | 2,300 ✅ | ❓ |
| Altitude rating | Derates from sea level | ❓ | ❓ | 170 hp to 20,000 ft; 130 hp at 30,000 ft ✅ | ❓ | ❓ |
| Compression ratio | 10.8 ✅ | ❓ | ❓ | ❓ | ❓ | ❓ |
| Fuel system | Port injection, dual FADEC | Carburettor ❓ | Port injection ❓ | HPCR direct injection ✅ | Common rail ✅ (callout diagram) | HPCR ✅ |
| Fuel consumption | ~18.5 L/h cruise (model default) | ❓ | ❓ | BSFC 207 g/kWh @ MSL ✅ | 39 L/h @100%, 21 L/h @60% ✅ | ~20% below gasoline equiv. ✅ |
| Electrical | 14 V (model default) | ❓ | ❓ | 28 V, 2 × 4.5 kW ✅ | ❓ | ❓ |
| Dry weight | ❓ | ❓ | ❓ | 162 kg ✅ | 186 kg ✅ | 98 kg ✅ |
| TBO | ❓ | ❓ | ❓ | 3,600 h ✅ | ❓ | 2,000 h ✅ |

> The ✅ figures for the diesels are enough to **calibrate** a first-order model (power, fuel burn, altitude derate). The ❓ cells must be filled before a model can be called validated.

### 2.3 What changes physically between engine classes

This is why "parameterize the constants" is necessary but **not sufficient**:

| Behaviour | Spark NA (912 iS) | Spark turbo (914F / 915iS) | Diesel turbo (PD170 / AE330 / Lark) |
|---|---|---|---|
| Load control | Throttle restricts air → MAP falls at part throttle | Throttle + wastegate | **Unthrottled.** Load = injected fuel quantity. MAP ≈ boost, *not* a throttle proxy |
| Altitude behaviour | Power falls steadily with density from sea level | Flat to critical altitude, then falls | Flat to critical altitude (PD170: 20,000 ft ✅), then falls |
| Air-fuel ratio | Near-stoichiometric | Near-stoichiometric, enriched at high boost | **Always lean**, varies widely with load |
| Primary thermal indicator | CHT per cylinder | CHT per cylinder | **Coolant temp**; per-cylinder EGT |
| EGT behaviour | High; leaning raises EGT | High; turbo inlet temp limit matters | Lower at part load, climbs steeply with load ❓ |
| Combustion fault language | Misfire, detonation | Detonation / knock at high MAP | Injector spray degradation, timing drift, combustion noise |
| Cold start | Normal | Normal | **Glow plugs** |

### 2.4 Required physics refactor 🟦

```text
backend/physics/
├── engine_model.py           EngineModel (abstract): compute_expected_state(ctx) -> state
├── cycles/
│   ├── spark_ignition.py     current RotaxThermoModel logic, moved not rewritten
│   └── compression_ignition.py
├── aspiration/
│   ├── natural.py            density-ratio derate
│   └── turbo.py              flat-rated to critical altitude; single or two-stage
├── cooling/
│   ├── air_oil.py            CHT-based
│   └── liquid.py             coolant loop + thermostat regulation
└── thermo_model.py           kept as a thin shim → EngineModel.from_manifest("rotax_912is")
```

**Constraints:**

1. **Regression lock on the 912 iS.** After refactor, the 912 iS path must reproduce existing expected states and residuals on `rotax912_test_dataset.csv` exactly (tolerance ≈ float rounding). Trained ML models and every recorded mission depend on it.
2. **All parameters come from the engine manifest** (doc 03 §3.1). No engine-specific constants in code.
3. `sensor_validator.py` rate-of-change limits move into the manifest per channel.
4. `EnginePhysicalState` gains the class-specific channels from doc 03 §4.2; channels an engine does not have are `null`, **not** zero. A zero coolant temperature is a fault signal.

### 2.5 Fault taxonomies per engine class 🟦 proposed, to be validated against engine literature

The existing 8 faults are Rotax 912 specific. Mapping PS-26054 §C requirements onto each class:

| PS §C requirement | Spark (existing 1–8, + 2xx) | Diesel (1xx) |
|---|---|---|
| Misfire conditions | `3` Ignition misfire | `101` Per-cylinder combustion failure (injector or compression) |
| Injector abnormalities | `2` Injector #1 clog | `102` Injector nozzle coking / spray degradation · `103` HPCR rail pressure loss |
| Cooling degradation | `1` CHT overheat (baffle) | `104` Coolant loss / thermostat stuck · `105` Intercooler fouling |
| Lubrication issues | `4` Oil pressure loss | `106` Oil pressure decay |
| Sensor drift / failure | `8` FADEC lane drift | `900`-range, engine-agnostic |
| Combustion instability | `6` EGT imbalance · `203` Detonation / knock | `107` Injection timing drift (**also covers PS "injection timing parameters"**) |
| Overheating trends | `1` | `104` |
| Abnormal vibration | `5` Gearbox vibration | `108` Reduction gearbox vibration |
| *(turbo-specific)* | `201` Wastegate stuck · `202` Turbo bearing wear | `109` LP/HP stage underboost |
| *(electrical)* | `7` Alternator sag | `110` 28 V bus sag / single-alternator loss |

**Each fault requires, before it is accepted:** trigger channels, a physically justified signature (which residuals move, in which direction, at what rate), an onset ramp model for the simulator, a target component in the engine manifest, and a recommended action.

### 2.6 ML implications ❌ unresolved risk

- The existing classifier and anomaly models **must not** be applied to other engines. They have learned Rotax 912 residual distributions.
- There is **no real telemetry** for any of the new engines. Training data for them will be simulator-generated from §2.4 physics with injected §2.5 faults.
- A model trained on synthetic data from the same simulator it is tested against will score well and prove little. Doc 05 therefore requires a **held-out fault-parameter split** (different onset rates and severities in test than in train) and requires the demo to state that non-Rotax engines are synthetic-data validated.

---

## 3. Mission Simulation

### 3.1 Current simulator ✅

`CANStreamer.get_flight_context()` in `backend/telemetry/can_streamer.py`:

| Region | Altitude | OAT | RPM | Phase |
|---|---|---|---|---|
| `LADAKH` | 18,500 ± 3,500 ft (sinusoid) | ≈ −22 °C | ≈ 5,150 | `CRUISE_LOITER` |
| `THAR_DESERT` | 4,500 ± 2,000 ft | ≈ +44 °C | ≈ 5,050 | `CRUISE_LOITER` |
| default | 10,000 ft | 5 °C | 5,000 | `CRUISE_LOITER` |

**Gaps against PS-26054 §E and [breakdown §12](../01_problem_statement_breakdown.md):**

- **Every region returns the single phase `CRUISE_LOITER`.** No takeoff, climb, descent, approach or landing exists, so the PS's "rapid throttle transitions" and phase-dependent behaviour cannot be demonstrated.
- RPMs are Rotax crankshaft values (~5,000). Diesel prop RPM tops out at 2,300; these profiles are wrong for 4 of 6 engines.
- Altitude varies sinusoidally with no platform ceiling or endurance limit.
- (Minor) the function is annotated as returning a 5-tuple and returns 6 values.

### 3.2 Requirements 🟦

**Mission profile model:** a mission is an ordered list of phases, each with duration, target altitude, throttle/power schedule, and environment:

```jsonc
{
  "mission_id": "SIM_LADAKH_ISR_01",
  "platform_id": "tapas_bh201",
  "seed": 42,                                   // reproducible demos
  "environment": { "region": "LADAKH", "isa_deviation_c": -10 },
  "phases": [
    { "phase": "TAXI",     "duration_s": 300,  "power_pct": 15 },
    { "phase": "TAKEOFF",  "duration_s": 60,   "power_pct": 100, "target_alt_ft": 11500 },
    { "phase": "CLIMB",    "duration_s": 1500, "power_pct": 90,  "target_alt_ft": 25000 },
    { "phase": "LOITER",   "duration_s": 54000,"power_pct": 55 },
    { "phase": "THROTTLE_TRANSIENT", "duration_s": 30, "power_from": 55, "power_to": 100 },
    { "phase": "DESCENT",  "duration_s": 1800, "power_pct": 25,  "target_alt_ft": 11500 },
    { "phase": "LANDING",  "duration_s": 120,  "power_pct": 30 }
  ],
  "injected_faults": [ { "fault_id": 104, "onset_s": 20000, "ramp_s": 3600, "severity": 0.7 } ]
}
```

| # | Requirement | PS basis |
|---|---|---|
| S1 | Phases: `TAXI, TAKEOFF, CLIMB, CRUISE, LOITER, DESCENT, APPROACH, LANDING, THROTTLE_TRANSIENT` | §E rapid throttle transitions; breakdown §12 |
| S2 | ISA atmosphere with temperature deviation (hot day = positive deviation), not fixed OAT constants | §E environmental simulation, hot-weather operation |
| S3 | Profiles clamp to platform ceiling, endurance and engine limits from manifests | §E high altitude, endurance |
| S4 | Power expressed as % of rated power; the engine model converts to RPM/fuel/boost. Profiles stay engine-agnostic | Multi-platform |
| S5 | Deterministic seeded noise, so the demo run is identical every time | Demonstrability |
| S6 | **Comparative what-if:** run one profile across ≥ 2 platforms and report per-engine margin (temperatures vs limits, fuel, predicted RUL consumed) | "Mission reliability enhancement"; pre-flight Go/No-Go |
| S7 | Faster-than-real-time execution for long endurance missions (a 30 h sortie cannot be demoed live) | §E endurance mission |

### 3.3 What the 3D asset shows during simulation

| Signal | Visual |
|---|---|
| Phase | Gear state (down for taxi/takeoff/landing on retractable platforms), HUD phase label |
| `PROP_RPM` | Propeller rotation / blur disc (R4, R5) |
| Altitude / OAT | HUD only. **The aircraft does not need to fly through terrain** to satisfy the PS |
| Engine health and faults | Doc 03 §5 |

🟦 Flying the model over the Nubra terrain during simulation is explicitly a **non-goal** ([doc 00 §6](00_asset_program_overview.md)).

---

## 4. Mission Replay

### 4.1 Current replay ✅

`backend/telemetry/replay_engine.py` serves `list_manifests()`, `get_manifest(mission_id)` and `get_frame(mission_id, time_sec)` from `report_dump/mission_*/` (`readings/`, `faults/`, `health/`, `predictions/`, `timeline/`, `actions/`, `mission.json`), exposed at `/api/replay/*`. Manifests carry `uav_tail_number`. All recorded missions are Rotax 912 data.

### 4.2 Requirements 🟦

| # | Requirement | Why |
|---|---|---|
| P1 | Replay manifest records `platform_id`, `engine_id` and the manifest version used at record time | The client must load the correct airframe and engine and apply the fault bindings that were valid then |
| P2 | **One rendering path.** The 3D client consumes a replay frame through the same state → visual code as a live frame; only the source (`/api/state` vs `/api/replay/{id}/frame`) differs | Guarantees replay shows exactly what the operator saw live |
| P3 | Replay time is independent of Blender's global timeline mechanisms (§1.2 R1) | Otherwise scrubbing moves wings and gear |
| P4 | Scrub, pause, 1×/10×/60×/600× playback | 30 h endurance sorties |
| P5 | **Jump-to-event:** timeline markers for every anomaly onset, fault classification, severity change and recommended action | Post-flight analysis is about *when the twin knew* |
| P6 | **Re-detection mode:** re-run the current detection pipeline over recorded raw readings and diff the result against recorded faults | Shows detection is computed, not scripted. Also regression-tests model updates against history |
| P7 | Show **lead time** at each fault event: time between first degradation signal and threshold breach | This number *is* the PS's "predict before occurrence" claim |
| P8 | Fleet replay: two sorties side by side (same platform, different theatre, or two platforms) | Mission-wise health reports; fleet-level monitoring |

### 4.3 Data gap

No replayable sortie exists for any platform other than the Rotax 912 (or the TB3, whose recorded engine data is Rotax 912 by virtue of the wrong linkage). Each new platform needs at least one simulated nominal sortie and one per demoed fault, generated with the §3.2 simulator and recorded through the normal pipeline, **not** hand-authored JSON.
