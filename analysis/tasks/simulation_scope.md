# 🎬 Tactical Mission Simulation & Auto-GCAS Engine Specification
**DRDO / iDEX Problem Statement ID: 26054**  
*Autonomous 3D Dynamic Pathfinding, Natural Language Copilot, and Real-Time Ground Collision Avoidance (Auto-GCAS)*

---

## 📌 1. Executive Overview & Core Philosophy

The **Tactical Mission Simulation Engine** is an interactive, physics-grounded 3D UAV guidance and survivability system. It moves beyond static scripted animations to provide **real-time spatial intelligence, natural language operator instruction, and autonomous terrain collision avoidance**.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                     TACTICAL FLIGHT SIMULATION ARCHITECTURE                   │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   [Natural Language / Operator Input] ──► [Local Intent & Action Engine]     │
│                                                          │                    │
│                                                          ▼                    │
│   [3D Terrain Radar / Raycast Probing] ─► [Dynamic Path & Cost Optimizer]     │
│                                                          │                    │
│                                                          ▼                    │
│   [Auto-GCAS Margin Solver] ────────────► [Flight Kinematics & 3D Drone]      │
│                                                          │                    │
│                                                          ▼                    │
│   [1D Thermodynamic Closed Loop] ───────► [2D GPU HUD & Debrief Logs]         │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Pillars
1. **Zero Hardcoded Paths:** The aircraft does not follow pre-recorded tracks. At every frame (60 to 120 FPS), it dynamically evaluates 3D terrain geometry, aircraft energy state, and collision risk.
2. **Map & Location Independent:** Operates on any 3D terrain mesh (`terrain.blend` or custom DEM elevation models) using real-time spatial raycasting.
3. **Cyber-Physical Closed Loop:** Couples the **engine's internal thermodynamic health** (Cylinder Head Temperature, cooling air density) directly with **3D aerodynamic flight maneuvers** (tactical dives into cold canyon gorges).
4. **Dual Safety Operating Modes:**
   * **Copilot ON:** Military-grade Auto-GCAS active. Issues terrain warnings and autonomously executes escape maneuvers at critical safety margins.
   * **Copilot OFF:** Full manual pilot risk. If the pilot fails to pull up before terrain impact, the UAV experiences a simulated catastrophic crash with center-screen telemetry debrief.

---

## 🧠 2. The 5 Core Intelligent Subsystems

---

### Subsystem 1: Natural Language & Voice Instruction Engine
* **Purpose:** Interprets natural language commands (spoken via Whisper STT or typed into the GCS console) and translates them into flight control vectors.
* **Component:** Local Intent Parser & Action Mapper (`backend/agent/copilot.py`).
* **Operational Flow:**
  1. Operator says: *"Take a dive to the left to cool the engine."*
  2. The intent engine parses the utterance into structured tactical parameters:
     ```json
     {
       "intent": "TACTICAL_MANEUVER",
       "action": "DIVE",
       "relative_heading_offset_deg": -45.0,
       "primary_objective": "CONVECTIVE_THERMAL_COOLING",
       "target_altitude_mode": "MINIMUM_SAFE_AGL",
       "copilot_safety_override": true
     }
     ```
  3. The flight guidance controller immediately ingests these constraints and plans the dynamic 3D descent.

---

### Subsystem 2: Dynamic 3D Pathfinding & Cost Function Optimizer
* **Purpose:** Solves the optimal, collision-free 3D flight trajectory in real time across rugged terrain.
* **Technology:** **Artificial Potential Fields (APF) + 3D Raycast Cost Evaluation**.
* **How It Works Every Frame:**
  * **Forward Probing:** Casts a multi-beam radar array (6 to 8 rays) forward, downward, and laterally to detect rock faces, canyon walls, and valley openings.
  * **Cost Function Formulation:**
    * **Hazard Cost:** Exponential penalty as distance to mountain mesh decreases.
    * **Direction Reward:** Bonus for aligning with the commanded vector (e.g. Left + Down).
    * **Cooling Reward:** Bonus for reaching lower, denser, colder atmospheric layers.
    * **Kinematic Penalty:** Penalty for excessive G-forces, over-banking (> 28 deg), or exceeding structural pitch limits.
  * **Trajectory Generation:** Steers the UAV toward the continuous valley corridor that minimizes total cost.

---

### Subsystem 3: Military-Grade Auto-GCAS (Ground Collision Avoidance System)
* **Purpose:** Calculates the exact minimum safety margin required to recover the aircraft and prevents Controlled Flight Into Terrain (CFIT).
* **The Dynamic Margin Calculation (Zero Hardcoding):**
  * The safety margin is **velocity and physics dependent**:
    * **Recovery Distance** = (Airspeed squared) / (2 * Max Climb Acceleration)
    * **Time-To-Impact (TTI)** = (Distance to Terrain Along Vector) / (Forward Closure Velocity)
* **The 3 Safety Zones:**
  1. **Green Zone (TTI > 6.0 seconds):**
     * Safe flying regime. Follows operator commands (diving, cruising, banking) with zero intervention.
  2. **Amber Zone (3.0 seconds <= TTI <= 6.0 seconds):**
     * **Advisory Warning:** Flashes amber HUD alert: `WARNING: TERRAIN PROXIMITY (320m) — PULL UP OR DIVERGE`.
     * Pilot retains full manual authority to steer away.
  3. **Red / Critical Horizon (TTI < 3.0 seconds):**
     * **Point of Safe Return:** The absolute last second where an emergency 2.5G pull-up can clear the rock face.
     * **If Copilot is OFF:** No intervention. The aircraft continues into the mountain and triggers a crash.
     * **If Copilot is ON:** Auto-GCAS immediately overrides manual controls, rolls wings level, pitches up to +18 degrees, accelerates throttle to 5,500 RPM, and climbs to safe ceiling.
     * Audio/HUD Alert: `COLLISION AVOIDED BY AUTO-COPILOT — RE-CLIMBING`.

---

### Subsystem 4: 1D Thermodynamic Closed-Loop Coupling
* **Purpose:** Links engine heat rejection to 3D flight profile.
* **Physics Coupling:**
  * In thin air at 19,000 ft (5,800m MSL), ambient cooling is poor. Cylinder #2 CHT drifts upward.
  * During the tactical dive into the canyon (down to 3,850m MSL), two physical phenomena occur:
    1. **Dynamic Air Density Increase:** Air density increases by +22%, providing significantly higher mass flow through the engine cooling shrouds.
    2. **Airspeed Acceleration:** Diving increases indicated airspeed from 122 knots to 142 knots.
  * **Convective Cooling Rate:**
    * Heat Dissipated = Heat Transfer Coeff(Airspeed, Density) * Baffle Area * (Cylinder Temp - Ambient Temp)
  * Once Cylinder #2 CHT drops below 102.0 deg C, the thermodynamic engine signals the autopilot that thermal recovery is complete, prompting the re-climb to high cruise.

---

### Subsystem 5: Dual-Mode Operation & Crash Simulation Sequence

```
                         [UAV Diving Toward Mountain Wall]
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
         [COPILOT MODE: OFF]                             [COPILOT MODE: ON]
                 │                                               │
  • Full manual pilot authority.                  • Real-time TTI radar active.
  • No automated override.                        • Warning at 300m (Amber).
                 │                                               │
  • Aircraft impacts rock face.                   • Critical Margin reached:
                 │                                  Auto-GCAS 2.5G pull-up!
                 ▼                                               │
  ┌─────────────────────────────┐                                ▼
  │💥 3D COLLISION TRIGGERED    │                 ┌─────────────────────────────┐
  │ • Kinematics freeze         │                 │🛡️ COLLISION AVOIDED         │
  │ • Red Center-Screen HUD:    │                 │ • Aircraft clears mountain  │
  │   "MISSION FAILED:          │                 │ • Re-climbs to safe ceiling │
  │    TERRAIN COLLISION"       │                 │ • Debrief log recorded      │
  │ • Telemetry at impact saved │                 └─────────────────────────────┘
  │ • [R] key to reset          │
  └─────────────────────────────┘
```

#### Center-Screen Crash HUD Layout (Copilot OFF)
When an impact occurs, the simulation halts and renders a high-visibility tactical debrief card:

```
╔══════════════════════════════════════════════════════════════════════════╗
║                   💥 MISSION FAILED: TERRAIN COLLISION                   ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Impact Velocity : 138.4 KIAS (Knots Indicated Airspeed)                 ║
║  Impact Altitude : 4,120 m AMSL (13,517 ft)                              ║
║  World Position  : [X: +245.2m,  Y: +890.1m,  Z: +412.0m]                ║
║  Casualty Cause  : Controlled Flight Into Terrain (CFIT)                 ║
║  Safety Status   : Copilot Safety Override was DISABLED                  ║
║  Impact Angle    : -16.2° Pitch  |  +18.4° Left Bank                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║              Press [R] to Reset Flight  |  Press [C] for Copilot ON      ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 🎛️ 3. Real-Time 2D GPU HUD & Operator Controls

The simulation runs a GPU-drawn 2D Tactical HUD (built with Blender's `gpu` and `blf` modules at 60–120 FPS):

### HUD Layout Elements
1. **Top Briefing Bar:** Mission phase, active frame, compass heading (000°–360°), Copilot Mode Badge (`[COPILOT: ACTIVE]` in green or `[COPILOT: MANUAL/OFF]` in red).
2. **Center Flight Instrument Tapes:**
   * **Airspeed Tape (Left):** Real-time KIAS.
   * **Altitude Tape (Right):** Dual display in Feet AMSL and Meters MSL.
   * **Radar Clearance Tape (Center-Bottom):** Exact height Above Ground Level (`AGL: 142m`).
   * **Artificial Horizon Reticle:** Pitch ladder and dynamic bank pointer.
3. **Left Propulsion Monitor (Rotax 912 iS):**
   * Engine RPM, Cylinder Head Temp (CHT), Coolant Temp, Oil Pressure gauge bars with dynamic color shifting.
4. **Right Tactical AI & Auto-GCAS Log:**
   * Real-time rolling chronological trace of AI intent, radar warnings, thermal cooling rates, and Auto-GCAS interventions.
5. **Interactive Controls:**
   * **[SPACE]:** Pause / Resume simulation.
   * **[C]:** Toggle Copilot Mode (`ON` / `OFF`).
   * **[1]:** Trigger Thermal Overheat & Command Canyon Dive.
   * **[2]:** Force Low Canyon Floor Sprint.
   * **[3]:** Command Re-Climb to High Cruise.
   * **[V]:** Switch Camera (Maverick Chase Camera vs Canyon Reconnaissance View).
   * **[R]:** Reset Simulation to Initial Flight State.
   * **[ESC]:** Clean Exit.

---

## 📋 4. Execution Logic & State Machine

```
                              [STATE 0: INITIALIZATION]
                                         │
                                         ▼
                              [STATE 1: HIGH CRUISE]
                        (19,000 ft AMSL, 122 KIAS, Nominal)
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
       [Trigger Overheat Event]                     [Operator Manual Command]
                   │                                           │
                   ▼                                           ▼
       [STATE 2: CANYON DESCENT] <─────────────────────────────┘
       • Throttle rolled back to 4,000 RPM
       • Airspeed accelerates into dive
       • Radar sweeps forward 3D terrain
                   │
                   ▼
       [STATE 3: AUTO-GCAS MONITORING & SPRINT]
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
  [Copilot: ON]       [Copilot: OFF]
         │                   │
  • TTI < 3.0s?       • Distance <= 0.5m?
  • Auto 2.5G pull-up!• IMPACT!
  • "Collision        • Trigger Crash Screen
    Avoided"                 │
         │                   ▼
         │            [STATE 6: CRASHED]
         │            (Simulation Halts)
         ▼
       [STATE 4: CONVECTIVE THERMAL EQUILIBRIUM]
       • CHT drops below 102°C in dense air
                   │
                   ▼
       [STATE 5: RE-CLIMB & RESTORATION]
       • Power restored to 5,200 RPM
       • Climb back to 19,000 ft cruise
```

---

## 📁 5. Implementation Roadmap & File Locations

* **Core Simulation Script:** [apps/blender_twin/standalone_canyon_flight_app.py](../../apps/blender_twin/standalone_canyon_flight_app.py)
* **Launcher Batch File:** [launch_canyon_simulation.bat](../../launch_canyon_simulation.bat)
* **3D Scene & Terrain Model:** `Models/terrain.blend`
* **Agentic Language Hook:** [backend/agent/copilot.py](../../backend/agent/copilot.py) and [diagnostic_agent.py](../../backend/agent/diagnostic_agent.py)
* **Thermodynamic Engine Coupling:** [backend/physics/thermo_model.py](../../backend/physics/thermo_model.py)
