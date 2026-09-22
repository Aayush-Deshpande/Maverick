# 🖥️ Frontend Dashboards & Ground Control Stations
**DRDO / iDEX Problem Statement ID: 26054**  
*React Web GCS, Blender Raytraced Viewport, Canyon Flight Sim & Unity Integration*

---

## 1. Multi-Client Visualization Ecosystem

The Digital Twin supports 5 distinct visualization and control runtimes, all synchronized to the authoritative laptop backend server:

```
                                  ┌─────────────────────────────────────┐
                                  │   AUTHORITATIVE BACKEND (Port 8000) │
                                  └──────────────────┬──────────────────┘
                                                     │
         ┌───────────────────┬───────────────────────┼───────────────────────┬───────────────────┐
         ▼                   ▼                       ▼                       ▼                   ▼
┌─────────────────┐ ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐ ┌─────────────────┐
│ Web Ground GCS  │ │ Blender 3D CAD  │     │ Ladakh Canyon   │     │ Pygame Desktop  │ │ Unity 3D Bridge │
│ (React / Vite)  │ │ (EEVEE Raytrace)│     │ Sim (120 FPS)   │     │ GCS (Hardware)  │ │ (C# Scripts)    │
└─────────────────┘ └─────────────────┘     └─────────────────┘     └─────────────────┘ └─────────────────┘
```

---

## 2. Web Ground Control Station (React + Vite + Tailwind)

Located in `frontend/`, the Web GCS is a high-density aerospace tactical dashboard providing real-time controls, telemetry dials, and AI Copilot interaction.

```
frontend/src/
├── App.tsx                     # Main layout & navigation tabs (Flight Deck, Grid, AI Diagnostics)
├── hooks/
│   └── useTelemetrySocket.ts   # 50 Hz WebSocket hook with auto-reconnect & round-trip latency
├── components/
│   ├── Header.tsx              # Tactical status bar (Sortie ID, Latency, Go/No-Go, FADEC Lane)
│   ├── EngineControls.tsx      # Throttle slider, Start/Stop, Altitude/OAT, Theater selector
│   ├── FaultMatrix.tsx         # 8-button tactical fault injection dock
│   ├── TelemetryGrid.tsx       # Live 20 Hz avionics gauges (RPM, CHT, EGT, Pressures, Vib)
│   ├── SubsystemHealthCard.tsx # 5 physical health bars (Propulsion, Fuel, Elec, Therm, Mech)
│   ├── DiagnosticCard.tsx      # Go/No-Go, RUL P10/P50, SOP checklist, Causal chain, Copilot Chat
│   ├── AerospaceMarkdown.tsx   # Custom markdown parser with aerospace warning badges
│   └── ConnectionModal.tsx     # Server host URL configurator & link watchdog
└── types/
    └── telemetry.ts            # TypeScript interfaces matching backend Pydantic schemas
```

### Key UI Features
* **Avionics Grid (`TelemetryGrid.tsx`):** Real-time animated scalar dials and SVG sparkline history graphs for all 27 flight parameters.
* **Interactive SOP Checklist (`DiagnosticCard.tsx`):** Step-by-step clickable checkboxes for DRDO emergency procedures (e.g., Step 1: Throttle back, Step 2: Switch to Lane B).
* **Copilot Chat Assistant (`DiagnosticCard.tsx`):** Allows operators to ask natural language questions ("What is the minimum oil pressure in Ladakh?") directly against the local RAG engine.

---

## 3. Blender 5.2 Standalone 3D CAD Viewport Client

Located in `apps/blender_twin/standalone_digital_twin_app.py`, this client renders the Rotax 912 iS CAD model (109 individual meshes) directly inside Blender’s native EEVEE real-time raytracing engine.

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                         BLENDER 3D DIGITAL TWIN CLIENT FEATURES                          │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ • 60 FPS Delta-Time Orbit: Revolve around stationary engine center (1.93, 61.65, -35.32) │
│ • Slot-Based Material Swapping: Replaces default PBR shader with pulsating emissive glow │
│ • Pulsing Red Emissive Alarm: Oscillates target fault mesh at 3.0 Hz upon fault onset    │
│ • X-Ray Holographic Ghosting: Turns non-faulted engine body semi-transparent blue        │
│ • Precision Component Framing: Glides camera directly in front of target mesh on fault  │
│ • Real-Time HUD Overlay: BLF text and 2D GPU shader gauges rendered over 3D viewport    │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Top Gun 120 FPS Ladakh Canyon Flight Simulator

Located in `apps/blender_twin/standalone_canyon_flight_app.py`, this client renders a high-speed dynamic flight simulation through a real **Copernicus DEM Ladakh Canyon Corridor**:

* **Rendering Engine:** 120 FPS silky-smooth viewport animation.
* **Independent Chase Camera:** Trailing world-space camera with gyro-stabilized horizon.
* **4-Phase Mission Profile:**
  1. *Phase 1 (Frames 1–260):* High-Altitude Cruise (~5,750m AMSL / FL190).
  2. *Phase 2 (Frames 261–460):* CHT Overheat & Tactical Dive into canyon gorge.
  3. *Phase 3 (Frames 461–820):* Low-Altitude Canyon Sprint with high-speed convective cooling.
  4. *Phase 4 (Frames 821–1200):* Power restored $\rightarrow$ pitch-up re-climb out of canyon.

---

## 5. Hardware-Accelerated Pygame Desktop GCS

Located in `apps/desktop_gcs/standalone_gui_app.py`:
* **Resolution:** Dedicated 1280x760 dark-mode aerospace GCS window.
* **Turntable Engine:** 120-frame raytraced EEVEE turntable with inertial drag physics.
* **Hardware Gauges:** Real-time analog needle dials (RPM, CHT, Oil Press, Fuel Flow, MAP, EGT, Bus Voltage, Vibration).
* **Hotkeys:** <kbd>1</kbd>–<kbd>8</kbd> to trigger DRDO fault scenarios, <kbd>Space</kbd> to orbit, <kbd>X</kbd> for X-ray mode.

---

## 6. Unity 3D Engine Bridge C# Package

Located in `unity_bridge/`:
* `UnityDigitalTwinBridge.cs`: HTTP/WebSocket telemetry client polling state from backend.
* `EngineDigitalTwinManager.cs`: Dynamic shader controller and component mesh highlighter.
* `HolographicLeaderLine.cs`: World-space 3D holographic leader lines connecting 3D engine parts to floating UI cards.
* `OrbitCameraController.cs`: Cinemachine smooth camera orbit and target focusing controller.
* `DigitalTwinSceneBuilder.cs`: Editor script automatically constructing lighting, orbit rigs, and UI canvases in Unity.
