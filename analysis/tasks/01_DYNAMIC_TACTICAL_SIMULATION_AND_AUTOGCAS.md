# 🎬 Track 01: Dynamic Tactical Simulation & Auto-GCAS Implementation Plan
**DRDO / iDEX Problem Statement ID: 26054**  
*Autonomous 3D Dynamic Pathfinding, Natural Language Copilot, and Real-Time Ground Collision Avoidance*

---

## 📌 1. Module Overview & Goals

This module upgrades the standalone canyon tactical flight simulation from a pre-baked animation into an **autonomous, physics-driven, map-independent guidance system**.

### Target Files & Scope
* **Primary Flight Script:** [apps/blender_twin/standalone_canyon_flight_app.py](../../apps/blender_twin/standalone_canyon_flight_app.py)
* **Launcher File:** [launch_canyon_simulation.bat](../../launch_canyon_simulation.bat)
* **Intent Engine Hook:** [backend/agent/copilot.py](../../backend/agent/copilot.py)
* **3D Environment:** `Models/terrain.blend`

---

## 🏗️ 2. Detailed Technical Architecture & Components

```
┌────────────────────────────────────────────────────────────────────────┐
│                   TACTICAL GUIDANCE LOOP (60-120 FPS)                  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  1. SENSING: Multi-Ray 3D Radar Probing (Blender ray_cast)             │
│     • Forward Center (300m), Forward Left (45°), Forward Right (45°)   │
│     • Downward (AGL Altitude), Down-Left, Down-Right                   │
│                                                                        │
│  2. REASONING: Potential Field & Cost Solver                           │
│     • Hazard Repulsion = sum( (1 / ray_dist)^2 * -ray_normal )         │
│     • Command Attraction = Target Maneuver Vector                      │
│     • Thermal Cooling Gain = Density Gradient * Descent Airspeed       │
│                                                                        │
│  3. SAFETY GATE: Auto-GCAS Margin Solver                               │
│     • Recovery Distance = (Airspeed)^2 / (2 * Max Climb Accel)         │
│     • Time-To-Impact (TTI) = Distance / Forward Velocity               │
│     • If TTI < 3.0s and Copilot ON -> Auto 2.5G Pull-Up                │
│     • If Dist <= 0.5m and Copilot OFF -> Trigger 3D Crash Screen       │
│                                                                        │
│  4. EXECUTION: Aircraft Kinematics & GPU HUD Rendering                 │
│     • Smooth banking (max 28°), pitch control (-18° to +15°)           │
│     • Render Tactical HUD tapes, AGL tape, and Crash Card              │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🧩 3. Data Structures & Class Design

### 3.1 `TacticalSensorArray` (3D Radar Raycaster)
```python
class TacticalSensorArray:
    """Probes 3D terrain mesh using native Blender BVH raycasting."""
    def __init__(self, terrain_obj_name="Landscape"):
        self.lookahead_dist = 350.0  # meters
        self.ray_offsets = [
            (0.0, 0.0),    # Forward Center
            (-0.35, 0.0),  # Forward Left 20 deg
            (0.35, 0.0),   # Forward Right 20 deg
            (-0.70, 0.0),  # Lateral Left 40 deg
            (0.70, 0.0),   # Lateral Right 40 deg
            (0.0, -0.60),  # Downward AGL
            (-0.35, -0.40),# Down-Left Canyon Floor
            (0.35, -0.40), # Down-Right Canyon Floor
        ]

    def probe_terrain(self, uav_pos, uav_forward, uav_up, uav_right) -> dict:
        """Fires all rays and returns minimum distance, collision normals, and AGL."""
```

### 3.2 `AutoGCASController` (Ground Collision Avoidance System)
```python
class AutoGCASController:
    """Military-grade automatic terrain recovery gate."""
    def __init__(self):
        self.copilot_enabled = True
        self.max_climb_accel = 24.5  # m/s^2 (~2.5 Gs)
        self.warning_tti_sec = 6.0   # Amber warning threshold
        self.critical_tti_sec = 2.8  # Red auto-recovery threshold
        self.is_recovering = False

    def evaluate_safety(self, airspeed_ms, min_forward_dist, agl_m) -> tuple[str, float]:
        """
        Calculates dynamic recovery distance and Time-To-Impact (TTI).
        Returns (Status: 'NOMINAL' | 'WARNING' | 'CRITICAL' | 'IMPACT', TTI_seconds).
        """
```

### 3.3 `PotentialFieldNavigator` (Cost Function Optimizer)
```python
class PotentialFieldNavigator:
    """Calculates smooth 3D steering vector balancing command vs terrain repulsion."""
    def calculate_steering(self, current_heading, target_command, sensor_report) -> mathutils.Vector:
        """
        Combines attraction vector, obstacle repulsion vectors, and canyon floor cushion.
        Enforces maximum roll rate (15 deg/s) and bank limit (28 deg).
        """
```

---

## 💥 4. Dual-Mode Operation & Crash HUD Logic

### 4.1 Copilot ON (Auto-Recovery Active)
* When `TTI < 2.8 seconds`:
  1. `AutoGCASController.is_recovering = True`
  2. Overrides operator commands.
  3. Commands maximum pitch rate up to +18 degrees.
  4. Spools engine throttle to 5,500 RPM.
  5. Steers along the calculated open valley escape heading.
  6. HUD flashes green badge: `🛡️ COLLISION AVOIDED BY AUTO-COPILOT`.
  7. Once cleared of terrain and at safe altitude (AGL > 150m), hands control back to operator.

### 4.2 Copilot OFF (Manual Risk & Crash Sequence)
* When distance to mesh `<= 0.5 meters`:
  1. Set simulation state to `CRASHED`.
  2. Freeze UAV 3D transformation matrix immediately.
  3. Capture impact telemetry:
     * Impact Airspeed (KIAS)
     * Impact Altitude (Meters AMSL & Feet)
     * Impact Coordinates [X, Y, Z]
     * Angle of attack & bank angle at impact
  4. Render high-visibility center-screen Crash Card.
  5. Operator presses `[R]` to re-arm and reset flight.

---

## 🗣️ 5. Natural Language & Copilot Intent Integration

### Intent Mapping Table
| Natural Language Utterance | Parsed Intent | Commanded Flight Vector |
|---|---|---|
| *"Take a dive into the canyon"* | `DIVE_CONVECTIVE_COOL` | Pitch: -14 deg, Heading: Forward, Floor: 60m AGL |
| *"Dive left to cool down"* | `DIVE_LEFT_VALLEY` | Pitch: -14 deg, Bank: -22 deg (Left), Heading: -45 deg |
| *"Evade right, mountain ahead"* | `EVADE_RIGHT` | Bank: +26 deg (Right), Heading: +60 deg |
| *"Climb back to high cruise"* | `RE_CLIMB_CRUISE` | Pitch: +12 deg, Target Alt: 5,800m AMSL |
| *"Engage copilot auto safety"* | `SET_COPILOT_ON` | `copilot_enabled = True` |
| *"Disable copilot override"* | `SET_COPILOT_OFF` | `copilot_enabled = False` |

---

## 🛠️ 6. Step-by-Step Implementation Steps

1. **Step 1:** Implement `TacticalSensorArray` using `scene.ray_cast` inside `standalone_canyon_flight_app.py`.
2. **Step 2:** Build `AutoGCASController` with dynamic stopping distance math and the 3 safety zones.
3. **Step 3:** Implement `PotentialFieldNavigator` for dynamic steering and canyon corridor tracking.
4. **Step 4:** Add 3D collision detection and center-screen GPU Crash HUD overlay.
5. **Step 5:** Add `[C]` hotkey to toggle Copilot Mode (`ON` / `OFF`) with HUD status pill.
6. **Step 6:** Connect intent strings from `backend/agent/copilot.py` to the flight controller.
7. **Step 7:** Validate across multiple arbitrary terrain flight vectors in `Models/terrain.blend`.
