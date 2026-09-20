# Project ANUMAAN — Functional Requirements (Explicitly Stated in PS-26054)

**Scope of this file:** only what the official problem statement *explicitly* states. No interpretation, no assumptions, no implementation choices. Wording is kept as close to the PS as possible.

- Verbatim PS: [00_official_problem_statement.md](00_official_problem_statement.md)
- Plain-language meaning of each item: [01_problem_statement_breakdown.md](01_problem_statement_breakdown.md)
- Current implementation status and what is still needed per item: [gap_plan.md](gap_plan.md)

Source-text OCR errors corrected, meaning unchanged: "Defection" → Detection, "Coding degradation" → Cooling degradation, "logit" → logic, "far anomaly" → for anomaly, "AE/ML" → AI/ML.

### Obligation levels (the PS's own words)

| Level | PS wording | Meaning for us |
|---|---|---|
| **MUST** | "shall", "required", "expected solution should include", "deliverables expected" | Must be built and demonstrated |
| **SHOULD** | "should", "should be capable of", "should support" | Treat as mandatory; the PS lists these as the system's expected capabilities |
| **MAY** | "may utilize" | Allowed implementation options, not mandatory |
| **ENCOURAGED** | "participants are encouraged to explore" | Optional innovation; earns credit, not required |
| **UNDERSTANDING** | "teams are expected to demonstrate understanding of" | Must be evident in the solution and documentation |

**Totals:** 83 MUST/SHOULD items · 7 deliverables · 7 MAY options · 8 ENCOURAGED areas · 9 UNDERSTANDING areas.

---

## 1. Overall System

| ID | Requirement | Level | PS section |
|---|---|---|---|
| SYS-01 | Develop a **Digital Twin system** for an **aero piston engine used in MALE UAV** applications | SHOULD | Description |
| SYS-02 | The system is **scalable** | SHOULD | Description |
| SYS-03 | The system is **modular** | SHOULD | Description |
| SYS-04 | The system **shall create a real-time virtual representation of the engine** | MUST | Description |
| SYS-05 | Framework is **indigenous** | SHOULD | Background |
| SYS-06 | Suitable for **deployment in MALE UAV ground control and health monitoring architecture** | SHOULD | Background |
| SYS-07 | Designed considering **future deployment in defence-grade Ground Control Stations (GCS)** | SHOULD | Expected Solution |
| SYS-08 | Designed considering **future deployment in engine test rigs** | SHOULD | Expected Solution |
| SYS-09 | Designed considering **future deployment in fleet-level health monitoring infrastructures** | SHOULD | Expected Solution |

## 2. Integration Inputs: the virtual representation is created by integrating

| ID | Requirement | Level | PS section |
|---|---|---|---|
| INT-01 | **Engine sensor data** | MUST | Description |
| INT-02 | **Thermodynamic behavior models** | MUST | Description |
| INT-03 | **Engine performance maps** | MUST | Description |
| INT-04 | **Failure/degradation logic** | MUST | Description |
| INT-05 | **AI/ML-based predictive analytics** | MUST | Description |
| INT-06 | Synchronized using **live telemetry** | SHOULD | Expected Solution |
| INT-07 | Synchronized using **physics-based models** | SHOULD | Expected Solution |
| INT-08 | Synchronized using **operational history** | SHOULD | Expected Solution |
| INT-09 | Synchronized using **AI-driven analytics** | SHOULD | Expected Solution |

## 3. System Capabilities: "the proposed system should be capable of"

| ID | Requirement | Level | PS section |
|---|---|---|---|
| CAP-01 | **Real-time engine parameter visualization** | SHOULD | Description |
| CAP-02 | **Monitoring of engine health indicators** | SHOULD | Description |
| CAP-03 | **Detection of abnormal operating conditions** | SHOULD | Description |
| CAP-04 | **Predicting probable failures before occurrence** | SHOULD | Description |
| CAP-05 | **Estimating degradation trends** | SHOULD | Description |
| CAP-06 | **Estimating Remaining Useful Life (RUL)** | SHOULD | Description |
| CAP-07 | **Simulating engine behavior under different mission profiles** | SHOULD | Description |
| CAP-08 | **Simulating engine behavior under different environmental conditions** | SHOULD | Description |
| CAP-09 | **Supporting post-flight analysis** | SHOULD | Description |
| CAP-10 | **Supporting mission replay** | SHOULD | Description |
| CAP-11 | **Real-time engine state estimation** | SHOULD | Background |
| CAP-12 | **Anomaly detection** | SHOULD | Background |
| CAP-13 | **Degradation tracking** | SHOULD | Background |
| CAP-14 | **Fault prediction** | SHOULD | Background |
| CAP-15 | **Mission replay capability** | SHOULD | Background |

## 4. A. Digital Twin Core Framework

"The digital twin core framework **shall** act as the central intelligence layer that continuously mirrors the real aero-piston engine operating onboard the MALE UAV."

| ID | Requirement | Level | PS section |
|---|---|---|---|
| DTC-01 | Core framework acts as the **central intelligence layer** | MUST | Expected Solution |
| DTC-02 | **Continuously mirrors** the real aero piston engine operating onboard the UAV | MUST | Expected Solution |
| DTC-03 | Establishes a **dynamic and continuously synchronized virtual representation** of the engine | SHOULD | Expected Solution |
| DTC-04 | **Virtual engine model synchronized with live engine data** | MUST | A |
| DTC-05 | **Modular architecture for future scalability** | MUST | A |
| DTC-06 | **Real-time data ingestion capability** | MUST | A |

## 5. B. Health Monitoring System

"The health monitoring system **shall** continuously assess the condition of engine sub-systems and generate health indices for predictive maintenance. Monitoring of following engine parameters are **required**."

| ID | Requirement | Level | PS section |
|---|---|---|---|
| HMS-01 | **Continuously assess the condition of engine sub-systems** | MUST | B |
| HMS-02 | **Generate health indices for predictive maintenance** | MUST | B |
| HMS-03 | Monitor **RPM** | MUST | B |
| HMS-04 | Monitor **Cylinder Head Temperature (CHT)** | MUST | B |
| HMS-05 | Monitor **Exhaust Gas Temperature (EGT)** | MUST | B |
| HMS-06 | Monitor **Oil Pressure** | MUST | B |
| HMS-07 | Monitor **Oil Temperature** | MUST | B |
| HMS-08 | Monitor **Fuel flow** | MUST | B |
| HMS-09 | Monitor **Vibration signatures** | MUST | B |
| HMS-10 | Monitor **Battery / Alternator health** | MUST | B |
| HMS-11 | Monitor **Injection timing parameters** | MUST | B |

## 6. C. Fault Detection & Predictive Analytics

"The system **should transition from conventional threshold-based monitoring to intelligent predictive diagnostics**. The detection/prediction of following parameters are **required**."

| ID | Requirement | Level | PS section |
|---|---|---|---|
| FDP-01 | **Intelligent predictive diagnostics** instead of conventional threshold-based monitoring | SHOULD | C |
| FDP-02 | Detect/predict **misfire conditions** | MUST | C |
| FDP-03 | Detect/predict **injector abnormalities** | MUST | C |
| FDP-04 | Detect/predict **cooling degradation** | MUST | C |
| FDP-05 | Detect/predict **lubrication issues** | MUST | C |
| FDP-06 | Detect/predict **sensor drift / failure** | MUST | C |
| FDP-07 | Detect/predict **combustion instability** | MUST | C |
| FDP-08 | Detect/predict **overheating trends** | MUST | C |
| FDP-09 | Detect/predict **abnormal vibration patterns** | MUST | C |

## 7. D. AI/ML Layer

"The AI/ML layer **shall** provide adaptive learning capability for predictive diagnostic and intelligent maintenance planning. Following parameters are **required** to be captured."

| ID | Requirement | Level | PS section |
|---|---|---|---|
| AIM-01 | **Adaptive learning capability** | MUST | D |
| AIM-02 | Supports **predictive diagnostics** | MUST | D |
| AIM-03 | Supports **intelligent maintenance planning** | MUST | D |
| AIM-04 | **Anomaly detection algorithms** | MUST | D |
| AIM-05 | **Remaining Useful Life (RUL) estimation** | MUST | D |
| AIM-06 | **Trend analysis** | MUST | D |
| AIM-07 | **Predictive maintenance recommendations** | MUST | D |

## 8. E. Simulation & Replay Capability

"The system **should include simulation tools to reproduce engine behavior and analyse mission scenarios**. Following parameters are **required** to be captured."

| ID | Requirement | Level | PS section |
|---|---|---|---|
| SIM-01 | **Simulation tools to reproduce engine behavior** | SHOULD | E |
| SIM-02 | **Analyse mission scenarios** | SHOULD | E |
| SIM-03 | **Replay of historical mission data** | MUST | E |
| SIM-04 | **Environmental condition simulation** | MUST | E |
| SIM-05 | Engine behavior simulation during **high altitude** | MUST | E |
| SIM-06 | Engine behavior simulation during **endurance mission** | MUST | E |
| SIM-07 | Engine behavior simulation during **hot-weather operation** | MUST | E |
| SIM-08 | Engine behavior simulation during **rapid throttle transitions** | MUST | E |

## 9. F. Visualization Dashboard

"The dashboard **shall** provide an intuitive operational interface for UAV operators, propulsion engineers and maintenance team."

| ID | Requirement | Level | PS section |
|---|---|---|---|
| VIS-01 | **Intuitive operational interface** | MUST | F |
| VIS-02 | Serves **UAV operators** | MUST | F |
| VIS-03 | Serves **propulsion engineers** | MUST | F |
| VIS-04 | Serves **maintenance team** | MUST | F |
| VIS-05 | Displays **real-time engine health status** | SHOULD | F |
| VIS-06 | Displays **fault alerts** | SHOULD | F |
| VIS-07 | Displays **engine efficiency trends** | SHOULD | F |
| VIS-08 | Displays **maintenance advisory** | SHOULD | F |
| VIS-09 | Displays **mission-wise health reports** | SHOULD | F |

---

## 10. Deliverables Expected from Teams

| ID | Deliverable | Level |
|---|---|---|
| DEL-01 | **Functional prototype / software demonstrator** | MUST |
| DEL-02 | **Digital twin architecture design** | MUST |
| DEL-03 | **Engine simulation model** | MUST |
| DEL-04 | **AI/ML-based anomaly detection module** | MUST |
| DEL-05 | **Visualization dashboard** | MUST |
| DEL-06 | **Demonstration using simulated or real engine datasets** | MUST |
| DEL-07 | **Technical documentation and deployment roadmap** | MUST |

---

## 11. Permitted Implementation Options: "the system may utilize" (not mandatory)

| ID | Option | Level |
|---|---|---|
| OPT-01 | CAN bus / SocketCAN-based engine data acquisition | MAY |
| OPT-02 | ECU/FADEC communication interfaces | MAY |
| OPT-03 | Edge computing architecture | MAY |
| OPT-04 | Cloud or local server-based analytics | MAY |
| OPT-05 | AI/ML algorithms for anomaly detection | MAY (also required as AIM-04) |
| OPT-06 | Physics-informed modelling approaches | MAY |
| OPT-07 | Dashboard/HMI for operators and maintenance engineers | MAY (also required as VIS-01..04) |

## 12. Desired Innovation Areas (encouraged, not mandatory)

| ID | Area | Level |
|---|---|---|
| INN-01 | Physics-informed AI | ENCOURAGED |
| INN-02 | Edge AI for UAV applications | ENCOURAGED |
| INN-03 | Lightweight onboard analytics | ENCOURAGED |
| INN-04 | Hybrid thermodynamic + data-driven models | ENCOURAGED |
| INN-05 | Federated learning approaches | ENCOURAGED |
| INN-06 | Explainable AI for fault diagnosis | ENCOURAGED |
| INN-07 | Secure telemetry architecture | ENCOURAGED |
| INN-08 | Autonomous maintenance advisory systems | ENCOURAGED |

## 13. Technical Expectations: understanding teams must demonstrate

| ID | Area | Level |
|---|---|---|
| TEX-01 | IC engine fundamentals | UNDERSTANDING |
| TEX-02 | UAV propulsion systems | UNDERSTANDING |
| TEX-03 | Sensor fusion | UNDERSTANDING |
| TEX-04 | Embedded systems | UNDERSTANDING |
| TEX-05 | CAN communication | UNDERSTANDING |
| TEX-06 | AI/ML analytics | UNDERSTANDING |
| TEX-07 | Data visualization | UNDERSTANDING |
| TEX-08 | Simulation modelling | UNDERSTANDING |
| TEX-09 | Reliability engineering | UNDERSTANDING |

---

## 14. What the PS Does *Not* Explicitly Require

Listed so no one treats these as PS requirements. They may still be useful, but they need their own justification:

- A specific engine model (e.g. Rotax 912 iS) or a specific UAV platform
- Multiple engines or UAV platforms (the PS says "an aero piston engine")
- 3D visualization or 3D models of the engine or airframe
- Photorealistic rendering, terrain, or flight animation
- A chatbot, RAG copilot, or voice interface
- Specific update rates, accuracy figures, or RUL horizons
- Use of real (non-simulated) engine data
- Actual CAN hardware (CAN/SocketCAN is a "may")

---

## 15. Requirement Tracker

Mark each item when it is **demonstrable**, with evidence (demo step, file, or screenshot).

| Group | IDs | Done | Evidence |
|---|---|---|---|
| Overall system | SYS-01 … SYS-09 | ☐ | |
| Integration inputs | INT-01 … INT-09 | ☐ | |
| Capabilities | CAP-01 … CAP-15 | ☐ | |
| A. DT core | DTC-01 … DTC-06 | ☐ | |
| B. Health monitoring | HMS-01 … HMS-11 | ☐ | |
| C. Fault detection | FDP-01 … FDP-09 | ☐ | |
| D. AI/ML | AIM-01 … AIM-07 | ☐ | |
| E. Simulation & replay | SIM-01 … SIM-08 | ☐ | |
| F. Dashboard | VIS-01 … VIS-09 | ☐ | |
| Deliverables | DEL-01 … DEL-07 | ☐ | |
| Technical understanding | TEX-01 … TEX-09 | ☐ | |
