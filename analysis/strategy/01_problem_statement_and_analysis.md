# Project ANUMAAN — Strategic Engineering Analysis
**DRDO / iDEX Problem Statement ID: 26054**
*AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs*

> For the verbatim official problem statement, see [00_official_problem_statement.md](../../docs/00_official_problem_statement.md).

---

## 📌 Executive Overview

| Field | Official Detail |
|---|---|
| **Problem Statement ID** | `26054` |
| **Title** | AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs |
| **Organization** | Defence Research and Development Organisation (**DRDO**) |
| **Department** | Department of Defence Production / **iDEX** (Innovations for Defence Excellence) |
| **Target Engine** | **Rotax 912 iS Sport** (100 HP, 4-Cylinder, Fuel-Injected, Dual FADEC) |
| **Target Platforms** | Indian MALE UAVs including **TAPAS-BH-201** and **Rustom-II** |
| **Category & Theme** | Software / Robotics and Drones / Aerospace Propulsion Diagnostics |

---

## 1. Operational Background & Strategic Defense Context

Medium Altitude Long Endurance (**MALE**) UAVs are deployed for continuous strategic defence, Intelligence, Surveillance, and Reconnaissance (**ISR**), border patrol, and maritime monitoring missions lasting **18 to 30+ continuous hours**.

### The Critical Vulnerability: Single-Engine Propulsion
Unlike commercial airliners or twin-engine military aircraft that have redundant powerplants to divert safely if one engine fails, MALE UAVs rely on a **single 4-cylinder aero piston engine**. 
* If the engine seizes or experiences unrecoverable power loss mid-sortie over contested borders (e.g., high-altitude Ladakh or Thar Desert), **the aircraft is permanently lost**.
* Propulsion availability and predictive reliability are the single highest determinants of UAV mission success.

### Why Conventional Threshold Monitoring Fails (The "Threshold Trap")
Conventional UAV engine monitoring systems are strictly **reactive and threshold-based**:
```
CONVENTIONAL THRESHOLD MONITORING (REACTIVE):
   [Sensor Reading] ──► [Normal Zone] ──► [Exceeds 135°C Limit!] ──► [ALARM RINGS!] ──► [Engine Seizes / Crash]
   * No predictive horizon. Warning fires when irreversible metallurgical/mechanical damage has already started.

AI-ENABLED DIGITAL TWIN (PREDICTIVE):
   [Sensor Reading] ──► [AI Detects +0.4°C Drift Residual] ──► [RUL Recalculated: 45 min left] ──► [Prescriptive Action Issued]
   * Identifies micro-trends 30-60 min early. Advises pilot to derate throttle or switch to Lane B, saving the UAV.
```

---

## 2. DRDO Scope of Work & Deliverables

As defined by DRDO PS-26054, the system must deliver a modular, cyber-physical virtual twin integrating:
1. **Engine Sensor Data Ingestion:** Live CAN bus / SocketCAN and Dual FADEC telemetry streaming at 10–50 Hz.
2. **Thermodynamic Behavior Models & Physics Baseline:** 4-stroke Otto cycle 1D thermodynamic differential equations and altitude/temperature derating performance maps.
3. **AI/ML-Based Predictive Analytics:** Unsupervised anomaly scoring, 8-fault classification, and Remaining Useful Life (RUL) degradation estimation.
4. **Mission Simulation & Historical Replay:** High-altitude thin air (Ladakh), extreme desert heat (Thar), and post-flight mission replay.
5. **Interactive 3D Digital Twin GCS Dashboard:** 60 FPS 3D CAD visualization with dynamic leader lines, animated fault hooks, and explainable AI diagnostic cards.

---

## 3. The 4 Operational Pillars of Mission Reliability

```
                       ┌─────────────────────────────────────────────────────────┐
                       │     MISSION RELIABILITY ENHANCEMENT (DRDO PS-26054)     │
                       └────────────────────────────┬────────────────────────────┘
                                                    │
        ┌─────────────────────────┬─────────────────┴───────────────┬─────────────────────────┐
        ▼                         ▼                                 ▼                         ▼
┌───────────────┐       ┌───────────────────┐             ┌───────────────────┐     ┌───────────────────┐
│ 1. Pre-Flight │       │ 2. In-Flight      │             │ 3. Automated      │     │ 4. "What-If"      │
│ Mission Go /  │       │ Early Degradation │             │ Pilot/GCS Action  │     │ Mission Profile   │
│ No-Go Check   │       │ Trending (RUL)    │             │ Recommendations   │     │ Simulation        │
└───────────────┘       └───────────────────┘             └───────────────────┘     └───────────────────┘
```

### Pillar 1: Pre-Flight Mission "Go / No-Go" Validation
* Evaluates current engine health indices against the planned mission profile before takeoff.
* **Operational Scenario:** If a planned reconnaissance sortie requires 20 flight hours, but the AI prognostic models calculate an estimated **Remaining Useful Life (RUL) of only 13.5 hours** on the dry-sump scavenge pump or ignition harness, the system generates an immediate **"NO-GO / PRE-EMPTIVE MAINTENANCE REQUIRED"** advisory on the ground, preventing asset loss over remote terrain.

### Pillar 2: In-Flight Early Degradation Trending
* During long-duration loitering at 20,000 feet, thermal and mechanical micro-stresses develop gradually.
* **Operational Scenario:** A micro-leak in a cooling air baffle causes Cylinder #2 to increase in temperature at $+0.38^\circ\text{C}$ every 10 minutes. While the temperature is still in the "green zone" (e.g., 112°C vs 135°C static limit), the Digital Twin flags the **residual anomaly trend**, predicting a critical thermal breach in 42 minutes if uncorrected.

### Pillar 3: Real-Time Actionable Pilot & GCS Directives
The system moves beyond passive alarms to generate **prescriptive operational commands**:
1. **Dynamic Throttle Derating:** *"Reduce cruise RPM from 5,200 to 4,600 RPM to lower thermal load while maintaining minimum loiter airspeed."*
2. **Subsystem Redundancy Switching:** *"Ignition misfire detected on Lane A — force FADEC arbitration to redundant Lane B coil set."*
3. **Altitude & RTB Vectoring:** *"Descend 4,000 ft into denser ambient cooling air and initiate Return-to-Base (RTB) vector."*

### Pillar 4: "What-If" Environmental Simulation & Condition-Based Maintenance (CBM)
* **Harsh Climate Modeling:** Simulates performance across India's operational extremes: high-altitude thin air (Ladakh, up to 25,000 ft MSL), extreme desert heat (Thar Desert, $+48^\circ\text{C}$), and maritime salinity.
* **Condition-Based Maintenance (CBM):** Replaces fixed-hour overhauls with **true wear-based maintenance**, maximizing UAV fleet readiness and saving lifecycle costs.

---

## 4. The 8 Canonical DRDO Fault Scenarios (PS-26054 Matrix)

| # | Fault State | Target Subsystem / 3D Meshes | Primary Sensor Trigger | Fast ML Diagnostic Signature | Prescriptive Pilot / GCS Action |
|---|---|---|---|---|---|
| **01** | **Cylinder #2 CHT Overheat** | `Covers_Theme_M_PlasticTheme_0` | CHT > 135°C (148.6°C) | $\Delta \text{CHT}_2 > +25^\circ\text{C}$ thermal runaway slope; Cyl #1, #3, #4 nominal. | Enrich fuel trim +12%, throttle back 15%, initiate RTB vector. |
| **02** | **Fuel Injector #1 Clog** | `Rotax_912i_Base_M_PlasticGreen_0` | Fuel Flow drop + EGT delta | -20% fuel flow drop, $\text{EGT}_1$ divergence on Cyl 1 from lean combustion. | Switch to Lane B ECU backup map, activate auxiliary boost pump. |
| **03** | **Ignition Misfire** | `Wiring_Harness_M_Copper_0` | RPM Jitter + EGT drop | RPM flutter ($\pm 180\text{ RPM}$), cyclic EGT drop on affected runner. | Switch to redundant Lane B ignition coil set. |
| **04** | **Oil Pressure Loss** | `Oil_Tank_M_Steel_0` | Oil Press < 2.0 bar (1.8 bar) | Continuous linear decay curve in oil pressure; gradual oil temperature rise. | Throttle back to 4,200 RPM, initiate precautionary landing. |
| **05** | **Gearbox Vibration** | `Gearbox_Type_2_M_Steel_0` | Vibration RMS > 1.8 mm/s (3.45 mm/s)| Spectral energy peak at 3rd harmonic of propeller reduction shaft. | Limit rapid RPM transients, schedule post-flight clutch overhaul. |
| **06** | **Exhaust EGT Imbalance** | `Exhaust_System_M_SteelDark_0` | EGT Delta > 65°C (895°C) | Runner #3 temperature divergence from uneven air-fuel ratio distribution. | Adjust individual cylinder fuel trim on Cyl #3. |
| **07** | **Alternator Voltage Sag** | `External_Alternator_...` | Bus Voltage < 12.8V (12.4V) | DC Bus voltage drop under ISR avionics load; battery discharge current. | Shed non-essential ISR payload sensors, engage backup battery. |
| **08** | **Dual FADEC ECU Drift** | `ECU_M_...` | MAP sensor Lane A/B Delta > 8 kPa | Cross-channel disparity between Lane A and Lane B manifold transducers. | Force FADEC arbitration to Lane B, flag ECU for calibration. |
