# Digital Twin Integration, Telemetry & Fault Visualization Spec

**Purpose:** define exactly how a 3D platform asset connects to the ANUMAAN backend, so that telemetry, health, fault predictions and RUL drive what the operator sees. This is the contract that turns a model into a twin.

**Governing principle** (from [01_problem_statement_breakdown.md §14](../01_problem_statement_breakdown.md)): the 3D asset contains **zero intelligence**. It reads state and renders it. Every decision (anomaly, fault class, RUL) is made in the backend. If you delete the 3D view, every capability must still exist as data.

---

## 1. Current Integration Architecture (as built, Rotax 912 only)

```text
can_streamer.py ──► thermo_model.py ──► detection_pipeline.py / fault_classifier.py
   (sensor sim)      (expected state,      (anomaly score, fault_id,
                      residuals)            confidence, RUL p10/p50/p90)
        │                                          │
        └───────────────► engine_service.py ◄──────┘
                          UnifiedTelemetryState @ 20 Hz
                                   │
      ┌────────────────────────────┼─────────────────────────────┐
      ▼                            ▼                             ▼
 GET /api/state            WS /ws/blender                 WS /ws/telemetry
 (HTTP polling)            (push stream + commands)       (web dashboard)
      │
      ▼
 standalone_digital_twin_app.py
   FAULT_DATABASE (hardcoded) ──► target_parts[] ──► ghost / emission / camera
```

**Control path back to the backend:** `POST /api/control` (or a message on `/ws/blender`) with `ControlCommand.action` ∈ `START_ENGINE | STOP_ENGINE | SET_FAULT | CLEAR_FAULT | SET_THROTTLE | SET_ALTITUDE | SET_OAT | SET_REGIME | EXPORT_DEBRIEF`.

**Replay path:** `GET /api/replay/manifests`, `/api/replay/{mission_id}/manifest`, `/api/replay/{mission_id}/frame?time_sec=` served by `backend/telemetry/replay_engine.py` from `report_dump/mission_*/`.

---

## 2. Blocking Gaps for Multi-Platform

Verified by code inspection. None of these are modelling problems; all block every new platform.

| # | Gap | Where | Effect |
|---|---|---|---|
| G1 | **No platform identity in the state.** `UnifiedTelemetryState` has `sortie_id` but no `platform_id` or `engine_type` | `backend/server/schemas.py:115` | A client cannot know which airframe/engine the stream describes. Two platforms cannot coexist |
| G2 | **Fault IDs hard-limited to 0..8** | `schemas.py` field docs; `can_streamer.py` raises `ValueError("Must be 0..8")` | Diesel fault sets cannot be expressed |
| G3 | **Fault→mesh binding hardcoded in the Blender client** | `standalone_digital_twin_app.py:44` `FAULT_DATABASE` | Every new engine needs a code edit to the client. Does not satisfy the PS's "modular architecture for future scalability" |
| G4 | **Duplicate binding source.** Backend `DRDO_FAULT_DEFINITIONS[].target_mesh` also names meshes | `can_streamer.py:17` | Two sources of truth that can silently disagree |
| G5 | **Telemetry schema is Rotax-912-shaped** (see §4) | `thermo_model.py:29` `EnginePhysicalState` | Diesel and turbo engines cannot report their real vital signs |
| G6 | **Identity inconsistency.** Mission graph defaults `uav_tail_number = "TAPAS-BH-201-AF01"` while telemetry is Rotax 912 | `backend/graph/mission_graph.py:31` | Mission reports attribute Rotax 912 data to an airframe that does not fly that engine |
| G7 | **TB3 client has no twin binding at all** | `3d_models/tb3_digital_twin_controller.py` | See [audit §3.2](01_current_state_audit.md) |

---

## 3. Target Architecture: Platform Manifests

🟦 **Our design decision.** Replace hardcoded fault tables with one declarative manifest per platform, loaded by both backend and clients. This is the concrete answer to the PS's modularity requirement: adding a platform becomes adding a file, not editing three codebases.

```text
ANUMAAN/manifests/
├── engines/
│   ├── rotax_912is.json      ├── rotax_914f.json     ├── rotax_915is.json
│   ├── tei_pd170.json        ├── austro_ae330.json   └── lark_hfe.json
└── platforms/
    ├── bayraktar_tb3.json    ├── tapas_bh201.json    ├── bayraktar_tb2.json
    ├── mq1_predator.json     ├── heron_mk2.json      ├── tai_anka.json
    └── casc_ch4.json
```

**Split rationale:** engines and airframes are separate manifests because the PD170 serves two airframes (TB3, ANKA). Engine fault bindings are defined once and reused.

### 3.1 Engine manifest schema

```jsonc
{
  "engine_id": "tei_pd170",
  "display_name": "TEI PD170",
  "blend_file": "Models/engines/tei_pd170.blend",
  "cycle": "compression_ignition",          // spark_ignition | compression_ignition
  "aspiration": "two_stage_turbo",          // natural | turbo | two_stage_turbo
  "cooling": "liquid",                      // air_oil | liquid
  "layout": "inline_4",                     // boxer_4 | inline_4
  "physics_params": { "displacement_cc": 2100, "...": "see doc 04 §2" },
  "telemetry_channels": ["ENGINE_RPM", "PROP_RPM", "COOLANT_TEMP", "BOOST_PRESS", "..."],
  "limits": { "COOLANT_TEMP": { "caution": 105, "warning": 115, "unit": "degC" } },
  "components": {
    "turbocharger_lp": {
      "meshes": ["Turbocharger_LP_M_Steel_0", "Turbocharger_LP_M_Cobalt_0"],
      "inspect_pose": { "center": [0.0, 0.0, 0.0], "angle_deg": -90, "elevation_deg": 25, "distance": 1.2 }
    }
  },
  "faults": [
    {
      "fault_id": 101,
      "key": "TURBO_UNDERBOOST",
      "title": "LP Turbocharger Underboost",
      "severity": "MAJOR",                  // CRITICAL | MAJOR | MINOR
      "component": "turbocharger_lp",
      "trigger_channels": ["BOOST_PRESS", "EGT_MEAN", "FUEL_FLOW"],
      "recommended_action": "Reduce altitude below critical altitude; schedule turbo inspection."
    }
  ]
}
```

### 3.2 Platform manifest schema

```jsonc
{
  "platform_id": "tapas_bh201",
  "display_name": "TAPAS BH-201 (Rustom-II)",
  "operator": "DRDO / Indian Armed Forces",
  "engine_id": "austro_ae330",
  "engine_count": 2,                        // BELIEVED twin-engine, unverified: doc 05 U1. Clients must support N engine instances
  "blend_file": "Models/airframes/tapas_bh201.blend",
  "quality_tier": "T1",                     // doc 02 §1
  "dimensions_m": { "wingspan": null, "length": null, "height": null },   // null until Phase 0 verifies
  "engine_mount": { "collection": "Internal_Systems", "location": [0, 0, 0], "rotation_deg": [0, 0, 0] },
  "mechanisms": ["gear_retract", "prop_spin", "control_surfaces"],
  "cameras": ["Cam_Beauty_Orbit", "Cam_Front_Sensor", "Cam_Engine_Prop", "Cam_Undercarriage"],
  "reference_sources": ["path or URL, with triage grade"]
}
```

### 3.3 Fault ID namespacing

🟦 To remove gap G2 without breaking the existing Rotax dataset and trained models:

| Range | Family |
|---|---|
| `0` | Nominal |
| `1–8` | **Existing** Rotax 912 iS set, unchanged (training data labels depend on it) |
| `100–199` | Compression-ignition diesel faults (PD170, AE330, Lark HFE) |
| `200–299` | Turbocharged spark-ignition faults (914F, 915iS) |
| `900–999` | Sensor/data-integrity faults, engine-agnostic |

### 3.4 Required backend changes (not modelling work)

1. Add `platform_id` and `engine_id` to `UnifiedTelemetryState` (G1).
2. Replace the `0..8` validation with "fault_id exists in the active engine manifest" (G2).
3. Load `DRDO_FAULT_DEFINITIONS` and the client `FAULT_DATABASE` **from the same manifest** (G3, G4).
4. Add `SET_PLATFORM` to `ControlCommand.action`.
5. Make mission-graph tail number derive from the active platform (G6).

---

## 4. Telemetry & Monitoring Requirements

### 4.1 PS-mandated parameter coverage

PS-26054 §B requires 8 parameter groups. Mapping against the current 27-parameter `EnginePhysicalState`:

| PS parameter | Current field(s) | Status |
|---|---|---|
| RPM | `ENGINE_RPM`, `PROP_RPM` | ✅ |
| Cylinder Head Temperature | `CHT_1..4` | ✅ Rotax · ⚠️ **not meaningful on liquid-cooled diesels**: use `COOLANT_TEMP` + per-cylinder where instrumented |
| Exhaust Gas Temperature | `EGT_1..4` | ✅ (ranges differ strongly by cycle, see doc 04) |
| Oil Pressure & Temperature | `OIL_PRESS`, `OIL_TEMP` | ✅ |
| Fuel flow | `FUEL_FLOW` | ✅ |
| Vibration signatures | `VIB_GEARBOX_RMS` | ⚠️ single RMS value, no spectrum. A "signature" implies frequency content |
| Battery / Alternator health | `BUS_VOLTAGE`, `BATTERY_CURRENT` | ⚠️ 14 V nominal hardcoded; PD170 is **28 V** with dual 4.5 kW alternators |
| **Injection timing parameters** | **none** | ❌ **Missing for every engine, including the Rotax 912 baseline.** This is an explicit PS requirement |

> The injection-timing gap exists today, independent of this program. It should be closed on the Rotax 912 first, because that is the platform currently demoed.

### 4.2 Engine-class-specific channels

| Channel | Spark NA (912iS) | Spark turbo (914F/915iS) | Diesel turbo (PD170/AE330/Lark) |
|---|---|---|---|
| `CHT_1..4` | Required | Required | N/A (liquid-cooled) |
| `COOLANT_TEMP` | Partial (912 heads are liquid-cooled) | Partial | **Required** |
| `MAP` | Required | Required | Required |
| `BOOST_PRESS` / wastegate position | N/A | **Required** | **Required** (per stage on PD170) |
| `TURBO_RPM` | N/A | Optional | Recommended |
| `INTERCOOLER_OUT_TEMP` | N/A | Optional | **Required** |
| `FUEL_RAIL_P` | ~3 bar (port injection) | ~3 bar / carb | **~1,600–2,000 bar HPCR**: different sensor, different fault physics |
| `INJ_TIMING_DEG` / `INJ_PULSE_MS` | **Required (PS)** | **Required (PS)** | **Required (PS)**, plus pilot/main injection split |
| `IGNITION_TIMING_DEG` | Required | Required | N/A |
| `GLOW_PLUG_STATE` | N/A | N/A | Required (cold start) |
| `BUS_VOLTAGE` nominal | 14 V | 14 V | 28 V |
| `FADEC_ACTIVE_LANE` | Required | Required | Required |

🟦 Diesel rail-pressure range is a typical HPCR figure, **not verified** for these specific engines. Flag for Phase 0 verification.

### 4.3 Rates

Observed: state broadcast at **20 Hz** (`schemas.py:116`). Adequate for thermal, pressure and electrical channels. **Not adequate for vibration signatures**: spectral fault detection (e.g. the existing "3rd harmonic of prop reduction shaft") needs raw sampling in the kHz range, processed on the edge, with only derived features (band energies, harmonic peaks) streamed at 20 Hz. The 3D client never needs raw vibration.

---

## 5. Fault & Degradation Visualization Requirements

### 5.1 Behaviours the baseline already implements (must be preserved on every platform)

| Behaviour | Baseline mechanism |
|---|---|
| Faulted component highlighted | Pulsing emission on `target_parts` meshes (`update_pulsing_emission`) |
| Context de-emphasised | Ghost materials on all non-target meshes (`ensure_ghost_materials`, `apply_material_state`) |
| Operator attention directed | Camera eases to the fault's inspect pose (`update_camera_for_backend_fault`) |
| Fault catalogue visible | HUD "FAULT MATRIX (PS-26054)" panel |
| Fault injection for demo | HUD buttons → `SET_FAULT` / `CLEAR_FAULT` |
| Original look restorable | `save_original_materials` before any override |

### 5.2 Behaviours required but not yet implemented anywhere

These are the parts of PS-26054 the 3D layer can *show* but currently does not:

| Requirement | PS basis | Visual specification |
|---|---|---|
| **Severity, not just on/off** | Health indices, degradation tracking | Emission colour ramps with confidence/severity: green → amber → red. Binary highlight hides the "early warning" that is the PS's entire point |
| **Pre-fault degradation** | "Predicting probable failures *before occurrence*" | A component with falling health but no classified fault shows a **distinct** amber state. The twin must be visibly different *before* the fault fires |
| **Per-component health** | Health indices per subsystem | `rul_by_component` already exists in `engine_service.py`; colour components by it in an optional "health map" mode |
| **RUL at the component** | RUL estimation | Leader-line label from component to HUD: `RUL p50 42 h (p10 31 h)`. Show p10 as well as p50: a single number hides uncertainty |
| **Anomaly without classification** | Anomaly detection ≠ fault prediction | Distinct "UNCLASSIFIED ANOMALY" state (e.g. white/violet pulse on the whole engine) for high anomaly score with low fault confidence. Never force an anomaly into a fault colour |
| **Sensor fault vs real fault** | "Sensor drift/failure" | When the sensor validator flags a channel, render the *sensor* as suspect (hatched/flicker) and do **not** highlight the component. Otherwise the twin visually asserts a failure that is actually bad data |
| **Explainability** | Desired innovation: explainable AI | HUD lists `trigger_signals` and their residuals for the active fault (already returned by `fault_classifier.py`) |
| **Mechanical symptoms** | Vibration, misfire | Optional: amplitude-scaled shake on the component, prop RPM tied to `PROP_RPM`. Must never be the *only* indicator |

### 5.3 Visual state priority

When states conflict, render the highest:

```text
1. SENSOR_SUSPECT   (bad data must not be shown as a real fault)
2. CRITICAL fault
3. MAJOR fault
4. MINOR fault
5. UNCLASSIFIED anomaly
6. DEGRADING        (health below threshold, no fault)
7. NOMINAL
```

### 5.4 Airframe-level integration (closes G7)

The engine is inside the airframe's `Internal_Systems` collection. On an active fault the client must:

1. Switch the airframe to ghost mode (`XRayFactor` → 0.85) so the engine is visible.
2. Apply the fault visuals to the engine meshes.
3. Transform the engine-manifest `inspect_pose` from engine-local into airframe space using `engine_mount`. Poses authored against a free-floating engine will otherwise frame empty space.
4. Restore airframe opacity on `CLEAR_FAULT`.

---

## 6. Acceptance Hooks for This Spec

Each item below is verified in [doc 05](05_deliverables_validation_acceptance.md):

- Every mesh named in a manifest exists in the referenced `.blend` (automated check).
- Every fault in a manifest can be injected, rendered, and cleared with materials restored.
- Inspect poses frame the target component inside the viewport (screenshot check).
- The client runs with **no platform-specific code**: switching platform is a manifest change only.
- Removing the 3D client leaves all health/fault/RUL data available via `/api/state`.
