# 📚 Project ANUMAAN — Master Engineering Documentation Suite
**AI-Enabled Digital Twin for Predictive Health Monitoring & Mission Reliability of Aero Piston Engines**
*Smart India Hackathon — DRDO Problem Statement 26054 (Software / Robotics and Drones)*

---

## 🧭 Reader's Guide & Recommended Reading Paths

To help stakeholders navigate the system specifications without friction or folder nesting, the entire documentation suite is structured into **5 numbered master files**:

```
                  ┌────────────────────────────────────────────────────────┐
                  │              START HERE: docs/README.md                │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
         ┌───────────────────────────────────┼───────────────────────────────────┐
         ▼                                   ▼                                   ▼
┌─────────────────────────┐       ┌─────────────────────────┐       ┌─────────────────────────┐
│ 🎯 FOR DRDO EVALUATORS  │       │ 🏗️ FOR SYSTEM ARCHITECTS│       │ 💻 FOR AI/ML DEVELOPERS │
├─────────────────────────┤       ├─────────────────────────┤       ├─────────────────────────┤
│ 1. 01_problem_statement │       │ 1. 02_system_architect  │       │ 1. 03_telemetry_physics │
│ 2. 05_master_build_guide│       │ 2. 04_rag_and_graph     │       │ 2. 02_system_architect  │
│ 3. 02_system_architect  │       │ 3. 05_master_build_guide│       │ 3. 04_rag_and_graph     │
└─────────────────────────┘       └─────────────────────────┘       └─────────────────────────┘
```

---

## 📑 Master Documentation Suite

Each file is a self-contained, authoritative specification:

### 0. 🇮🇳 [00_official_problem_statement.md](../../docs/00_official_problem_statement.md)
* **Official SIH Problem Statement Documentation:**
  * Verbatim DRDO PS-26054 problem statement (ID, background, description, expected solution, deliverables).
  * Project name and rationale — **ANUMAAN**.
  * Requirement-to-component mapping table linking each official ask to the corresponding ANUMAAN module.

### 1. 🎯 [01_problem_statement_and_analysis.md](../../analysis/strategy/01_problem_statement_and_analysis.md)
* **Requirements & Strategic Defense Rationale:**
  * Official DRDO / iDEX PS-26054 scope, deliverables, and background.
  * MALE UAV operational realities & single-engine propulsion vulnerability.
  * The 4 Operational Pillars of Mission Reliability.
  * The 8 Canonical DRDO Fault Scenarios Matrix.

### 2. 🏗️ [02_system_architecture_and_boundaries.md](../../analysis/strategy/02_system_architecture_and_boundaries.md)
* **System Architecture, AI Boundaries & Defense Standards:**
  * Dual-Plane Cyber-Physical Architecture & multi-platform frontends (Blender, Pygame, WebGL, Unity).
  * Fast Deterministic ML (<20ms) vs. Cognitive Agent Plane & Event-Driven JSON Contracts.
  * Sensor Sanity Validation Layer (Distinguishing sensor drift/disconnect from real thermal ramps).
  * Flight Data Recorder (FDR) scrubbing, automated PDF maintenance debriefs, and Edge-to-GCS split.

### 3. 📊 [03_telemetry_physics_and_dataset_strategy.md](../../analysis/strategy/03_telemetry_physics_and_dataset_strategy.md)
* **Telemetry, Physics Modeling & Dataset Strategy:**
  * The Definitive 27-Parameter Master Data Dictionary (kinematics, thermal, fluids, vibration, electrical, environmental, ML targets).
  * 1D Thermodynamic Otto cycle physics modeling & real-time residual calculation.
  * High-frequency gearbox vibration & 3rd harmonic spectral peak tracking.
  * Tri-Source Dataset Acquisition Strategy (Real GA logs, NASA benchmarks, and synthetic DRDO generator).

### 4. 🧠 [04_rag_and_mission_knowledge_graph.md](../../analysis/strategy/04_rag_and_mission_knowledge_graph.md)
* **Knowledge Systems, RAG & Mission Knowledge Graph:**
  * Local air-gapped Vector RAG (Rotax 912 iS Maintenance Manuals ATA 72-79, IPC, DRDO SOPs).
  * Standardized Markdown Mission Records (`MISSION_xxx.md` schema with YAML frontmatter).
  * Interconnected Property Knowledge Graph (Geographic regions, climates, failure signatures, and maintenance actions).
  * Historical Mission Replay Flow (`Mission Record → Replay Engine → Digital Twin`) and Reasoning Sub-Agent.

### 5. 🚀 [05_master_build_guide.md](../../analysis/strategy/05_master_build_guide.md)
* **Master End-to-End Build Guide:**
  * Step-by-step master execution roadmap connecting Phase 1 (Data & Telemetry) through Phase 5 (Live 3D Visualization Hooks).
  * Complete 3-database store blueprint, graph schema, and production air-gapped deployment constraints.

### 6. 🎬 [simulation_scope.md](../../analysis/tasks/simulation_scope.md)
* **Tactical Mission Simulation & Auto-GCAS Engine:**
  * Autonomous 3D dynamic pathfinding & Artificial Potential Fields (APF).
  * Natural language copilot instruction parsing & maneuver mapping.
  * Real-time Ground Collision Avoidance System (Auto-GCAS) with dynamic recovery margins.
  * Dual-mode safety architecture (Copilot ON vs Copilot OFF manual crash simulation).
  * Thermodynamic closed-loop cooling and real-time 2D GPU HUD overlays.

