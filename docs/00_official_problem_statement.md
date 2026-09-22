# 🇮🇳 Project ANUMAAN
**AI-Enabled Digital Twin for Predictive Health Monitoring & Mission Reliability of Aero Piston Engines**
*Smart India Hackathon (SIH) — Official Problem Statement Documentation*

> **अनुमान (ANUMAAN)** — Sanskrit/Hindi for *"inference" / "prediction"*. Chosen because the core of this system is exactly that: inferring the future health of an engine from its present signals, before failure occurs.

---

## 📌 Official Problem Statement Details

| Field | Detail |
|---|---|
| **Problem Statement ID** | `26054` |
| **Problem Statement Title** | AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs |
| **Organization** | Defence Research and Development Organisation (**DRDO**) |
| **Department** | Department of Defence R&D |
| **Category** | Software |
| **Theme** | Robotics and Drones |

*This document reproduces the official SIH problem statement as published, with only obvious source-text OCR artifacts silently corrected for readability (e.g. "Defection" → "Detection", "coding degradation" → "cooling degradation", "logit" → "logic"). No requirement has been added, removed, or reinterpreted. For the team's own engineering interpretation, target-platform assumptions, and architecture, see [01_problem_statement_and_analysis.md](../analysis/strategy/01_problem_statement_and_analysis.md).*

---

## 1. Background

Medium Altitude Long Endurance (MALE) UAVs are increasingly being deployed for long-duration Intelligence, Surveillance, and Reconnaissance (ISR), communication relay, maritime surveillance, and strategic defence missions. Reliability and availability of propulsion systems are critical for mission success, because piston-engine failures during flight may lead to mission abort, asset loss, or unsafe recovery conditions.

Conventional engine monitoring systems used in UAVs are primarily **threshold-based and reactive** in nature. These systems generally indicate failures only after an abnormality has already occurred. Present approaches also have limited capability to estimate Remaining Useful Life (RUL), predict degradation trends, or simulate mission-wise engine behavior under varying environmental and operating conditions.

A Digital Twin (DT) framework for aero piston engines can significantly improve predictive maintenance, operational reliability, mission planning, and life-cycle management by creating a continuously synchronized virtual representation of the physical engine using real-time sensor data, physics-based models, and AI/ML techniques.

The proposed problem aims to develop an indigenous Digital Twin framework suitable for deployment in MALE UAV ground control and health monitoring architecture. The solution should support real-time engine state estimation, anomaly detection, degradation tracking, fault prediction, and mission replay capability.

---

## 2. Description

Develop a scalable and modular Digital Twin system for an aero piston engine used in MALE UAV applications. The system shall create a real-time virtual representation of the engine by integrating:

- Engine sensor data
- Thermodynamic behavior models
- Engine performance maps
- Failure/degradation logic
- AI/ML based predictive analytics

### The proposed system should be capable of:
- Real-time engine parameter visualization
- Monitoring of engine health indicators
- Detection of abnormal operating conditions
- Predicting probable failures before occurrence
- Estimating degradation trends and Remaining Useful Life (RUL)
- Simulating engine behavior under different mission profiles and environmental conditions
- Supporting post-flight analysis and mission replay

### The system may utilize:
- CAN bus / SocketCAN-based engine data acquisition
- ECU/FADEC communication interfaces
- Edge computing architecture
- Cloud or local server-based analytics
- AI/ML algorithms for anomaly detection
- Physics-informed modelling approaches
- Dashboard/HMI for operators and maintenance engineers

---

## 3. Expected Solution

The Digital Twin core framework shall act as the central intelligence layer that continuously mirrors the real aero-piston engine operating onboard the MALE UAV. The framework should establish a dynamic and continuously synchronized virtual representation of the engine using live telemetry, physics-based models, operational history, and AI-driven analytics. The framework should be designed considering future deployment in defence-grade Ground Control Stations (GCS), engine test rigs, and fleet-level health monitoring infrastructures.

### A. Digital Twin Core Framework
- Virtual engine model synchronized with live engine data
- Modular architecture for future scalability
- Real-time data ingestion capability

### B. Health Monitoring System
Continuously assesses the condition of engine sub-systems and generates health indices for predictive maintenance. Monitored parameters:
- RPM
- Cylinder Head Temperature (CHT)
- Exhaust Gas Temperature (EGT)
- Oil Pressure & Temperature
- Fuel flow
- Vibration signatures
- Battery / Alternator health
- Injection timing parameters

### C. Fault Detection & Predictive Analytics
Transitions from conventional threshold-based monitoring to intelligent predictive diagnostics. Detection/prediction targets:
- Misfire conditions
- Injector abnormalities
- Cooling degradation
- Lubrication issues
- Sensor drift / failure
- Combustion instability
- Overheating trends
- Abnormal vibration patterns

### D. AI/ML Layer
Provides adaptive learning capability for predictive diagnostics and intelligent maintenance planning:
- Anomaly detection algorithms
- Remaining Useful Life (RUL) estimation
- Trend analysis
- Predictive maintenance recommendations

### E. Simulation & Replay Capability
Reproduces engine behavior and analyses mission scenarios:
- Replay of historical mission data
- Environmental condition simulation
- Engine behavior simulation during:
  - High Altitude operations
  - Endurance missions
  - Hot-weather operation
  - Rapid throttle transitions

### F. Visualization Dashboard
An intuitive operational interface for UAV operators, propulsion engineers, and maintenance teams, supporting:
- Real-time engine health status
- Fault alerts
- Engine efficiency trends
- Maintenance advisory
- Mission-wise health reports

---

## 4. Deliverables Expected from Teams
1. Functional prototype / software demonstrator
2. Digital Twin architecture design
3. Engine simulation model
4. AI/ML-based anomaly detection module
5. Visualization dashboard
6. Demonstration using simulated or real engine datasets
7. Technical documentation and deployment roadmap

---

## 5. Desired Innovation Areas
Participants are encouraged to explore:
- Physics-informed AI
- Edge AI for UAV applications
- Lightweight onboard analytics
- Hybrid thermodynamic + data-driven models
- Federated learning approaches
- Explainable AI for fault diagnosis
- Secure telemetry architecture
- Autonomous maintenance advisory systems

---

## 6. Technical Expectations from Participants
Teams are expected to demonstrate understanding of:
- IC engine fundamentals
- UAV propulsion systems
- Sensor fusion
- Embedded systems
- CAN communication
- AI/ML analytics
- Data visualization
- Simulation modelling
- Reliability engineering

---

## 7. Where ANUMAAN Maps to This Problem Statement

| SIH Requirement | ANUMAAN Component |
|---|---|
| Digital Twin Core Framework | Real-time engine state synchronization engine (see [02_system_architecture_and_boundaries.md](../analysis/strategy/02_system_architecture_and_boundaries.md)) |
| Health Monitoring System | 27-parameter telemetry pipeline (see [03_telemetry_physics_and_dataset_strategy.md](../analysis/strategy/03_telemetry_physics_and_dataset_strategy.md)) |
| Fault Detection & Predictive Analytics | 8 canonical fault-scenario ML classifiers (see [01_problem_statement_and_analysis.md](../analysis/strategy/01_problem_statement_and_analysis.md), §4) |
| AI/ML Layer (anomaly, RUL, trend, advisory) | Physics-informed prognostics stack (see [05_machine_learning_physics_prognostics.md](../analysis/engineering/05_machine_learning_physics_prognostics.md)) |
| Simulation & Replay | Mission replay engine & knowledge graph (see [04_rag_and_mission_knowledge_graph.md](../analysis/strategy/04_rag_and_mission_knowledge_graph.md)) |
| Visualization Dashboard | 3D Digital Twin GCS dashboard (see [07_frontend_and_gcs_clients.md](../analysis/engineering/07_frontend_and_gcs_clients.md)) |

---

*Document maintained as part of the ANUMAAN documentation suite. See [README.md](../analysis/engineering/README.md) for the full reading guide.*
