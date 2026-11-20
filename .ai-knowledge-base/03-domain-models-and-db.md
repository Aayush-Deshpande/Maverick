# 03. Domain Models, Data Schemas & Persistence

## 1. Core Domain Entities & Schemas

### Entity 1: `UnifiedTelemetryState` & `EngineTelemetry`
* **File:** `backend/server/schemas.py`
* **Role:** The atomic single source of truth broadcast across the system at 20 Hz.
* **Fields & Shape:**
  * **Kinematics:** `ENGINE_RPM` (0–5800), `PROP_RPM` (0–2400 via 2.43:1 gear reduction), `TPS` (Throttle Position 0–100%).
  * **Thermodynamics (°C):** Per-cylinder head temperatures (`CHT_1` through `CHT_4`), per-runner exhaust gas temperatures (`EGT_1` through `EGT_4`).
  * **Fluids & Pressures:** `OIL_PRESS` (bar), `OIL_TEMP` (°C), `FUEL_FLOW` (L/h), `FUEL_RAIL_P` (bar), `MAP` (Manifold Absolute Pressure in kPa).
  * **Mechanical & Electrical:** `VIB_GEARBOX_RMS` (mm/s), `BUS_VOLTAGE` (V), `BATTERY_CURRENT` (A), `FADEC_ACTIVE_LANE` (`LANE_A` | `LANE_B`).
  * **Operational Context:** `ALTITUDE_FT`, `OAT_C`, `TAS_KNOTS`, `FLIGHT_PHASE` (`CRUISE_LOITER`, `CLIMB`, `DESCENT`), `THEATER` (`LADAKH` | `THAR_DESERT`).
  * **Engine Management:** `INJ_TIMING_BTDC`, `INJ_PULSE_WIDTH_MS`, `IGN_TIMING_BTDC`, `LAMBDA_AFR`, `BSFC_G_KWH`, `POWER_KW`, `THERMAL_EFFICIENCY`.
* **Lifecycle:** Instantiated and updated every 50 ms by `EngineStateService.process_frame()`, encoded to JSON, and pushed via WebSocket to ground stations.

### Entity 2: `AnalyticsState`
* **File:** `backend/server/schemas.py`
* **Role:** Real-time inferential state encapsulating physics residuals, diagnostics, and prognostics.
* **Key Fields:**
  * `residuals`: 14 continuous residual values ($y_{\text{actual}} - y_{\text{expected}}$).
  * `anomaly_score`: Continuous L2 autoencoder reconstruction error ($0.0 - 1.0$).
  * `health_index`: Normalized system health metric ($0.0 - 1.0$).
  * `diagnosed_fault_id` (0..8) & `diagnosed_fault_name`: Gated classifier output.
  * `ata_chapter`, `severity`, `root_cause`, `prescriptive_action`: Deterministic ATA-chapter flight directives.
  * `emergency_checklist`: Array of immediate DRDO Standard Operating Procedure (SOP) actions.
  * `go_no_go` (`GO` | `CAUTION` | `NO-GO`) & `limiting_component`.
  * `rul_p10_hours`, `rul_p50_hours`: Probabilistic Remaining Useful Life percentiles.
  * `conformal_rul`: Statistical coverage intervals calculated via distribution-free calibration.
  * `causal_chain`: Multi-step physical causal propagation sequence explaining fault escalation.

### Entity 3: `MissionKnowledgeGraph` Fleet Entities
* **File:** `backend/graph/mission_graph.py`
* **Role:** Graph models representing multi-sortie health, accumulated stress, and Condition-Based Maintenance (CBM) records.
* **Nodes & Schema:**
  * **`SortieNode`**:
    * `sortie_id`, `uav_tail_number` (e.g. `TAPAS-BH-201-AF01`), `region`, `start_timestamp`, `end_timestamp`, `flight_hours`, `final_health_index`, `status` (`ACTIVE` | `COMPLETED` | `ABORTED`).
  * **`SubsystemNode`**:
    * `subsystem_id`, `name`, `ata_chapter`, `target_mesh`, `current_health`, `cumulative_stress_hours`, `last_inspected_epoch`.
  * **`AnomalyEventNode`**:
    * `event_id`, `sortie_id`, `subsystem_id`, `timestamp_epoch`, `fault_id`, `fault_name`, `severity`, `anomaly_score`, `ata_chapter`, `recommended_action`, `trend_note`.
  * **`MaintenanceActionNode`**:
    * `action_id`, `sortie_id`, `subsystem_id`, `ata_chapter`, `description`, `status` (`OPEN` | `SIGNED_OFF`), `rul_p10_hours`, `limiting_component`, `signoff_epoch`, `signoff_inspector`.

### Entity 4: `DiagnosticDirective` (Deterministic ATA Directives)
* **File:** `backend/agent/diagnostic_agent.py`
* **Role:** Zero-hallucination aerospace guidance binding fault IDs (0 through 8) directly to ATA chapters:
  * Fault 1: Cylinder #2 Overheat -> **ATA 72-30** (Cylinder Assembly & Baffles)
  * Fault 2: Fuel Injector #1 Clog -> **ATA 73-10** (Fuel Injection & Distribution)
  * Fault 3: Ignition Misfire -> **ATA 74-10** (Dual Spark Ignition & Harness)
  * Fault 4: Oil Pressure Loss -> **ATA 79-20** (Dry Sump Lubrication & Scavenge Pump)
  * Fault 5: Gearbox Vibration -> **ATA 72-10** (Propeller Reduction Gearbox)
  * Fault 6: Exhaust Imbalance -> **ATA 78-10** (Exhaust Collector & Runners)
  * Fault 7: Alternator Sag -> **ATA 24-30** (DC Power Generation & Charging)
  * Fault 8: Dual FADEC ECU Drift -> **ATA 73-20** (Dual-Lane Engine Control Unit)

---

## 2. Persistence Layer & Database Topology

### Graph Database (`data/graph_db/fleet_graph.json`)
* **Architecture:** Air-gapped, zero-dependency JSON property graph.
* **Mechanism:** Serialized via `MissionKnowledgeGraph.save()` and hydrated on server boot via `MissionKnowledgeGraph.load()`.
* **Integrity Guarantee:** Uses standard JSON encoding (`dataclasses.asdict`) rather than Python `pickle` to guarantee security and human inspectability.
* **Relational Mappings (Edges):**
  * `sortie_anomalies`: Maps `sortie_id` -> `List[event_id]`
  * `subsystem_anomalies`: Maps `subsystem_id` -> `List[event_id]`
  * `sortie_actions`: Maps `sortie_id` -> `List[action_id]`

### Offline Knowledge Store (`data/documents/`)
* **Storage:** Local document repository storing technical manuals (`.pdf`, `.docx`, `.pptx`, `.txt`, `.md`).
* **Semantic Indexing:** Chunks indexed into in-memory embedding arrays with cosine similarity thresholding (`_SEMANTIC_MIN_SCORE = 0.28`) and cross-document reranking (`backend/knowledge/retrieval/reranker.py`).

### Mission Reports & Debriefs (`report_dump/`)
* **Storage:** Exported JSON bundles and structured Markdown dossiers (`MISSION_xxx_DEBRIEF.md`) containing flight telemetry history, degradation plots, and maintenance work orders.
