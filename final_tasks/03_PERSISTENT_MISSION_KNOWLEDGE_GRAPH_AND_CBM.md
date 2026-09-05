# 🕸️ Track 03: Persistent Mission Knowledge Graph & CBM Plan
**DRDO / iDEX Problem Statement ID: 26054**  
*Disk-Persistent Property Graph, Fleet Condition-Based Maintenance & Regional Analytics*

---

## 📌 1. Module Overview & Goals

This module upgrades the **Mission Knowledge Graph** from a transient in-memory Python dictionary into a **persistent, disk-backed SQLite graph database** (`data/graph_db/mission_graph.db`), enabling multi-sortie fleet intelligence, regional wear comparisons, and automated maintenance work orders across restarts.

### Target Files & Scope
* **Graph Engine:** [backend/graph/mission_graph.py](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/graph/mission_graph.py)
* **Debrief Reporter:** [backend/graph/mission_reporter.py](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/graph/mission_reporter.py)
* **Server Integration:** [backend/server/engine_service.py](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/server/engine_service.py) & [main.py](file:///e:/backup-llm/backup-no-llm/3d_engine/backend/server/main.py)
* **Database Target:** `data/graph_db/mission_graph.db`
* **Output Debriefs:** `data/mission_reports/*.md`

---

## 🏗️ 2. Detailed Technical Architecture & Graph Schema

```
┌────────────────────────────────────────────────────────────────────────┐
│                   INTERCONNECTED FLEET KNOWLEDGE GRAPH                 │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   [Region / Climate Nodes]                                             │
│   • Ladakh (High Altitude 22k ft, Sub-zero -28°C, Thin Air)            │
│   • Thar Desert (Low Altitude, +48°C Extreme Heat, Airborne Sand)      │
│                        │                                               │
│                        ▼ LOCATED_IN                                    │
│   [Sortie Nodes] (SORTIE-2026-LADAKH-042, SORTIE-2026-THAR-112)        │
│                        │                                               │
│                        ▼ EXPERIENCED                                   │
│   [Anomaly Event Nodes] (ANOM-001: CHT #2 Thermal Drift)               │
│                        │                                               │
│            ┌───────────┴───────────┐                                   │
│            ▼                       ▼                                   │
│   [AFFECTED_SUBSYSTEM]    [RESOLVED_BY_ACTION]                         │
│   • Cylinder #2 Head      • MAINT-001: Baffle Seal Inspection          │
│   • Fuel Injection Rail   • MAINT-002: Synthetic Oil Flush            │
│   • Lubrication Circuit   • Status: OPEN / SIGNED_OFF                  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ 3. SQLite Graph Schema & Tables

```sql
-- 1. Sortie Records Table
CREATE TABLE IF NOT EXISTS sorties (
    sortie_id TEXT PRIMARY KEY,
    tail_number TEXT DEFAULT 'TAPAS-BH-201',
    region TEXT NOT NULL,
    start_timestamp REAL NOT NULL,
    end_timestamp REAL,
    flight_hours REAL DEFAULT 0.0,
    final_health_index REAL DEFAULT 1.0,
    status TEXT DEFAULT 'ACTIVE'
);

-- 2. Subsystem Degradation & Wear Table
CREATE TABLE IF NOT EXISTS subsystems (
    subsystem_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ata_chapter TEXT NOT NULL,
    target_mesh TEXT NOT NULL,
    current_health REAL DEFAULT 1.0,
    cumulative_stress_hours REAL DEFAULT 0.0,
    last_inspected_epoch REAL DEFAULT 0.0
);

-- 3. Anomaly Events Table
CREATE TABLE IF NOT EXISTS anomaly_events (
    event_id TEXT PRIMARY KEY,
    sortie_id TEXT NOT NULL,
    subsystem_id TEXT NOT NULL,
    timestamp_epoch REAL NOT NULL,
    fault_id INTEGER NOT NULL,
    fault_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    anomaly_score REAL NOT NULL,
    ata_chapter TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    FOREIGN KEY(sortie_id) REFERENCES sorties(sortie_id),
    FOREIGN KEY(subsystem_id) REFERENCES subsystems(subsystem_id)
);

-- 4. Maintenance Work Orders Table
CREATE TABLE IF NOT EXISTS maintenance_actions (
    action_id TEXT PRIMARY KEY,
    sortie_id TEXT NOT NULL,
    subsystem_id TEXT NOT NULL,
    ata_chapter TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'OPEN', -- 'OPEN' | 'SIGNED_OFF'
    signoff_epoch REAL,
    signoff_inspector TEXT,
    FOREIGN KEY(sortie_id) REFERENCES sorties(sortie_id)
);
```

---

## 📊 4. Cross-Regional Fleet Wear Analytics

The persistent graph provides analytical queries comparing wear signatures across operational environments:

### Query 1: Regional Thermal vs Lubrication Stress
* **Ladakh Sorties:** Evaluates total thermal drift anomalies on Cylinder #2 vs total flight hours. Shows accelerated baffle seal aging under extreme $-28^\circ\text{C}$ to $+950^\circ\text{C}$ combustion thermal gradients.
* **Thar Desert Sorties:** Evaluates oil pressure decays and high oil temperatures under $+48^\circ\text{C}$ ambient heat. Tracks synthetic oil viscosity loss across desert sorties.

### Query 2: Fleet Condition-Based Maintenance (CBM) Summary
Returns:
1. Total cumulative flight hours across all fleet UAVs.
2. Health score ($0.0\text{ to }1.0$) for all 8 Rotax 912 iS subsystems.
3. Count of currently `OPEN` maintenance orders requiring ground crew sign-off before the next dispatch.

---

## 📝 5. Automated Debrief Report Generation (`MISSION_xxx.md`)

Each sortie export produces an official debrief document matching the rich DRDO specification:
* Embedded YAML frontmatter with sortie ID, tail number, ambient climate, and Parquet log path.
* Narrative chronological timeline with anomaly detection timestamps.
* Prescriptive pilot directives executed in flight.
* Actionable maintenance checklist with checkboxes (`- [ ]`, `- [x]`) and RUL degradation adjustments.

---

## 🛠️ 6. Step-by-Step Implementation Steps

1. **Step 1:** Implement SQLite database initialization and schema migration in `backend/graph/mission_graph.py`.
2. **Step 2:** Refactor `MissionKnowledgeGraph` to persist all node and edge additions to SQLite.
3. **Step 3:** Add cross-regional analytical query methods (`get_regional_wear_comparison()`, `get_open_work_orders()`).
4. **Step 4:** Expose REST endpoints in `backend/server/main.py`:
   * `GET /api/cbm/summary` -> Overall fleet health and open work orders.
   * `GET /api/cbm/regional-analysis` -> Ladakh vs Thar wear statistics.
   * `POST /api/cbm/maintenance/{action_id}/signoff` -> Sign off ground maintenance order.
5. **Step 5:** Enhance `backend/graph/mission_reporter.py` to generate the complete DRDO debrief schema.
6. **Step 6:** Test persistence across server restarts and verify zero data loss.
