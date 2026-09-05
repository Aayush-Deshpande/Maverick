# Rotax 912 iS MALE UAV Digital Twin & Health Monitoring System
**DRDO / iDEX Problem Statement ID: 26054**

High-fidelity 3D Digital Twin, Real-Time Health Monitoring, AI Diagnostic Reasoning, and Fault Visualization Framework for the **Rotax 912 iS Sport Aero-Engine** (standard propulsion system for Indian MALE UAVs including TAPAS-BH-201 and Rustom-II).

---

## 📁 Repository Structure

```
3d_engine/
│
├── 📁 3d_models/                      # Master 3D CAD & Production Assets
│   ├── rotax_912_is_sport.blend       # Master Blender 5.2 scene (109 meshes, PBR shaders, 60 FPS orbit)
│   ├── rotax_912_is_sport.fbx         # Unity FBX export with hierarchies
│   ├── rotax_912_is_sport_packed.glb  # Universal glTF 2.0 CAD with embedded 2K PBR textures
│   ├── Rotax_912_iS_Sport_3D_Model.zip# Distribution archive (144.6 MB)
│   └── 📁 textures/                   # 2K PBR texture maps (Albedo, Normal, Emissive)
│
├── 📁 apps/                           # Native Application Runtimes & Frontends
│   ├── 📁 blender_twin/               # Native Blender 5.2 3D Digital Twin & Flight Simulation
│   │   ├── standalone_canyon_flight_app.py # 120 FPS Top Gun Dynamic Canyon Flight Simulation
│   │   ├── standalone_digital_twin_app.py  # 3D Engine CAD Viewport HUD & real-time telemetry modal
│   │   └── verify_app.py             # Headless geometry & fault target audit
│   └── 📁 desktop_gcs/                # Hardware-Accelerated Standalone Desktop GCS (Pygame)
│       └── standalone_gui_app.py      # Turntable engine, live gauges, AI reasoner
│
├── 📁 Models/                         # High-Resolution Operational Flight Worlds
│   └── terrain.blend                  # Real Copernicus DEM Ladakh terrain & Canyon Corridor
│
├── 📁 scripts/                        # Automation, Pipeline & Tooling Scripts
│   ├── 📁 blender/                    # Rigging, camera orbit, material upgrades, exports
│   │   ├── apply_master_blend_upgrade.py
│   │   ├── apply_realistic_materials.py
│   │   ├── bake_stationary_model_camera_orbit.py
│   │   ├── build_complete_blender_scene.py
│   │   ├── export_clean_glb.py
│   │   ├── export_hq.py
│   │   ├── export_unity_fbx.py
│   │   ├── fix_camera_distance.py
│   │   ├── inspect_and_render_blend.py
│   │   ├── inspect_viewport.py
│   │   ├── reassign_all_materials.py
│   │   ├── rebuild_master_blend.py
│   │   ├── save_as_blend.py
│   │   ├── set_rendered_shading.py
│   │   ├── set_viewport_shading.py
│   │   ├── setup_blender_digital_twin_markers.py
│   │   ├── setup_camera_orbit_60fps.py
│   │   ├── setup_camera_orbit_90fps.py
│   │   ├── setup_solid_colors.py
│   │   ├── test_blender_import.py
│   │   └── update_wide_camera.py
│   ├── 📁 rendering/                  # Turntable & batch rendering pipeline
│   │   ├── render_dark_silver.py
│   │   ├── render_deep_shadows.py
│   │   ├── render_exact_component_grades.py
│   │   ├── render_fault_snapshots.py
│   │   ├── render_normal_silver_dark_green.py
│   │   ├── render_turntable.py
│   │   └── test_render.py
│   └── 📁 utils/                      # Color sampling, inspection, HDR/EXR conversion
│       ├── analyze_components.py
│       ├── check_dims.py
│       ├── check_scene.py
│       ├── convert_exr.py
│       ├── convert_to_hdr.py
│       ├── copy_hdris.py
│       ├── sample_bg.py
│       ├── sample_components_exact.py
│       └── sample_green.py
│
├── 📁 unity_bridge/                   # Unity 3D Engine Integration C# Package
│   ├── DigitalTwinSceneBuilder.cs     # Automated Unity scene constructor
│   ├── DigitalTwinUIManager.cs        # Unity GCS HUD manager
│   ├── EngineDigitalTwinManager.cs    # Component highlighter & shader controller
│   ├── HolographicLeaderLine.cs       # 3D world-space leader lines & callouts
│   ├── OrbitCameraController.cs       # Smooth Cinemachine orbit & focus controller
│   ├── ProceduralSparkline.cs         # Live telemetry graph renderers
│   ├── TelemetryData.cs               # Telemetry data contracts & structures
│   ├── TelemetrySimulator.cs          # Standalone telemetry test generator
│   ├── UnityDigitalTwinBridge.cs      # HTTP/MCP receiver & state synchronizer
│   └── XRayMaterialManager.cs         # Ghosting & semi-transparent X-ray shader
│
├── 📁 renders/                        # Validation & Presentation Renders
│   ├── 📁 fault_snapshots/            # High-res DRDO fault renders
│   └── *.png                          # Presentation and validation renders
│
├── 📁 reverse_engineering_suite/      # Raw cipher, extraction & reverse-engineering archive
│
├── 📁 docs/                           # Master Engineering Documentation Suite
│   ├── README.md                      # Navigation Hub & Reading Order Guide
│   ├── 01_problem_statement_and_analysis.md # DRDO PS-26054 & Defense Analysis
│   ├── 02_system_architecture_and_boundaries.md # Dual-Plane Design, ML/Agent & Datalink
│   ├── 03_telemetry_physics_and_dataset_strategy.md # 27-Param Data Dictionary & Physics Twin
│   ├── 04_rag_and_mission_knowledge_graph.md # Vector RAG & Mission Knowledge Graph
│   └── 05_master_build_guide.md       # Step-by-Step Master Implementation Roadmap
│
├── .gitignore                         # Git ignore configuration
├── launch_standalone_app.bat          # 1-Click root Windows batch launcher
├── run_app.py                         # Universal interactive Python launcher
├── requirements.txt                   # Project Python dependencies
└── README.md                          # Master project documentation (this file)
```

---

## 🚀 Quick Start Guide

### 1. Launching via Universal Launcher (`run_app.py`)
Run the unified multi-target launcher:
```bash
# Interactive selection menu
python run_app.py

# Or launch specific targets directly:
python run_app.py server      # FastAPI 20 Hz Telemetry & Control Backend (port 8000)
python run_app.py blender     # Native Blender 5.2 3D Viewport HUD
python run_app.py canyon      # 120 FPS Ladakh Canyon Flight Simulation
python run_app.py pygame      # Hardware-Accelerated Pygame Desktop GCS
python run_app.py verify      # Automated Scene Verification & Audit
```

### 2. Windows 1-Click Batch Launchers
- `launch_backend_server.bat` — FastAPI telemetry/control backend (`http://127.0.0.1:8000`, Swagger docs at `/docs`).
- `launch_standalone_app.bat` — starts the backend if it isn't already running, then opens the native Blender 3D Digital Twin viewport.
  - **Fault Matrix:** Press <kbd>1</kbd>–<kbd>8</kbd> or click the scenario dock to trigger DRDO fault states.
  - **Interactive Orbit:** Press <kbd>Spacebar</kbd> for 60 FPS turntable; drag mouse to orbit/pan/zoom.
  - **X-Ray & Mission Sim:** Press <kbd>X</kbd> for internal X-ray mode, <kbd>M</kbd> for automated mission flight profile, <kbd>0</kbd> or <kbd>Esc</kbd> to reset.
- `launch_canyon_simulation.bat` — Top Gun-style Ladakh canyon flight simulation.
- `launch_web_dashboard.bat` — builds and serves the mobile/web GCS dashboard on `http://<this-machine>:5173`.
- `launch_public_tunnel.bat` — exposes the backend over an `ngrok` HTTPS tunnel for cellular/off-network access.

---

### 3. Launching the Web/Mobile Dashboard
```bash
launch_backend_server.bat     # start the telemetry backend first
launch_web_dashboard.bat      # then serve the dashboard
```
Open your browser to **`http://localhost:5173`** (laptop) or `http://<laptop-lan-ip>:5173` (phone on the same Wi-Fi — see the in-app Settings/Telemetry Data Link dialog for connecting the dashboard to a non-default backend address).

---

### 4. Opening in Blender Directly
1. Open [`3d_models/rotax_912_is_sport.blend`](3d_models/rotax_912_is_sport.blend) in **Blender 5.2+**.
2. Run [`apps/blender_twin/standalone_digital_twin_app.py`](apps/blender_twin/standalone_digital_twin_app.py) from the Scripting workspace.

---

### 5. Integrating with Unity
1. Drag and drop [`3d_models/rotax_912_is_sport_packed.glb`](3d_models/rotax_912_is_sport_packed.glb) or [`3d_models/rotax_912_is_sport.fbx`](3d_models/rotax_912_is_sport.fbx) into your Unity `Assets/Models/` folder.
2. Attach [`unity_bridge/UnityDigitalTwinBridge.cs`](unity_bridge/UnityDigitalTwinBridge.cs) to a GameObject in your scene.
3. Connect Unity to the backend's `ws://<laptop-ip>:8000/ws/blender` telemetry stream for real-time state and fault triggers.

---

## ⚡ DRDO Fault Matrix (PS-26054)

| # | Fault Mode | Primary Sensor Trigger | 3D Target Part | Visual Twin Action |
|---|---|---|---|---|
| **01** | **Cylinder #2 Overheat** | CHT > 135°C | `Covers_Theme_M_PlasticTheme_0` | Camera zooms to Cyl #2; head pulses red; baffles ghost |
| **02** | **Fuel Injector #1 Clog** | Fuel Flow drop + EGT delta | `Rotax_912i_Base_M_PlasticGreen_0` | Focuses on intake rail injector; plenum ghosts |
| **03** | **Ignition Misfire** | RPM Jitter + EGT drop | `Wiring_Harness_M_Copper_0` | Sweeps to side spark leads; cooling fins ghost |
| **04** | **Oil Pressure Loss** | Oil Press < 2.0 bar | `Oil_Tank_M_Steel_0` | Zooms to silver dry-sump reservoir tank & filter |
| **05** | **Gearbox Vibration** | Accelerometer 3rd harmonic | `Gearbox_Type_2_M_Steel_0` | Flies to front propeller gearbox hub |
| **06** | **Exhaust EGT Imbalance**| EGT Delta > 65°C | `Exhaust_System_M_SteelDark_0` | Underside camera sweep; runner glows crimson |
| **07** | **Alternator Voltage Sag**| Bus Voltage < 12.8V | `External_Alternator_...` | Pans to alternator pulley and serpentine belt |
| **08** | **Dual FADEC Drift** | MAP sensor Lane A/B delta | `ECU_M_...` | Zooms to rear dual-lane ECU fuse module |
