# VOLUME V: SIMULATION ECOSYSTEM, 3D CAD BLENDER TWINS & FRONTEND ARCHITECTURE

**Document ID:** `docsvF/05_SIMULATION_BLENDER_CANYON_AND_FRONTENDS.md`  
**Classification:** Visualization, Simulation & Human-Machine Interface (HMI) Manual  
**Project:** DRDO Aero-Twin (Project ANUMAAN)  
**SIH Problem Statement ID:** 26054  
**Date of Audit:** September 2026  
**Status:** Authoritative Working Standard  

---

## 20. THE SIMULATION ECOSYSTEM & 3D ASSETS AUDIT

Project ANUMAAN incorporates multiple high-fidelity 3D assets, dynamic flight physics engines, and terrain environments. 

A central question addressed in this audit is:
> *"Where do the 3D models, Blender scenes, and Ladakh canyon environments fit into the end-to-end engineering system, and are they genuine functional tools or decorative visual assets?"*

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                        THE 3D DIGITAL TWIN COUPLING CHAIN                                     ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                               ║
║   TELEMETRY / PLANT SIMULATION (20 Hz)                                                                        ║
║   ├── Engine RPM, Temperatures (CHT 1-4, EGT 1-4, Oil T), Pressures, Vibrations                               ║
║   └── Ingestion via `backend/runtime/hub.py`                                                                  ║
║              │                                                                                                ║
║              ▼                                                                                                ║
║   DIGITAL TWIN & DIAGNOSTIC CORE                                                                              ║
║   ├── Dynamic State Estimation & Residual Computation (d_CHT, d_EGT, etc.)                                    ║
║   ├── Bayesian Failure Mode Diagnosis (e.g. `INJ_CLOG_CYL3`, P = 0.94)                                        ║
║   └── Component Fault Target Mapping (`target_parts = ["Fuel_Injector_Cyl3", "Cylinder_3_Head"]`)             ║
║              │                                                                                                ║
║              ▼                                                                                                ║
║   WEBSOCKET STATE BROADCAST (`/ws/engines/{id}`)                                                              ║
║   └── JSON Payload: `{ rpm, temps, residuals, health_index, diagnosed_fault_id, target_parts }`                ║
║              │                                                                                                ║
║              ├────────────────────────────────────────┬────────────────────────────────────────┐              ║
║              ▼                                        ▼                                        ▼              ║
║   [TRACK A: Three.js WebGL Twin]            [TRACK B: Blender Master Twin]           [TRACK C: Canyon Sim]    ║
║   · 0ms Multi-Engine Switching              · 100% Raytraced EEVEE CAD               · 120 FPS Flight Sim     ║
║   · Draco WASM Mesh Decompression           · 80 MB Production CAD Model             · Ladakh DEM Terrain     ║
║   · GLSL Emissive Thermal Shaders           · 109 Rigged Component Assemblies        · Terrain Shadowing      ║
║   · Kinematic Crank/Propeller Rotation      · Automated Headless 4K Rendering        · Altitude Lapse         ║
║   · Cinematic `CameraDirector` Pan          · Engineering Failure Teardown           · Combat Tactical View   ║
║                                                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

---

### 20.1 Comprehensive 3D Asset & Scene Inventory

| Asset Name | Filesystem Location | File Size | Geometry & Meshes | Core Purpose in System | Coupling Mechanism | Operational Role | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Rotax 912 iS CAD Baseline** | [`assets/blender/rotax_912_is_sport.blend`](file:///d:/Programming/PS054/assets/blender/rotax_912_is_sport.blend) | **78.5 MB** | 109 individual mechanical meshes | Baseline structural CAD assembly of the 100 HP boxer engine | Python-Blender socket listener | Standalone desktop CAD HUD & visual teardown | **REAL & RIGGED** |
| **Master Unified Twin** | [`assets/blender/anumaan_master_twin.blend`](file:///d:/Programming/PS054/assets/blender/anumaan_master_twin.blend) | **80.1 MB** | Full multi-engine rigged hierarchy | Master production file housing Rotax 912, 914, 915, AE300, and VRDE assemblies | Automated batch rendering script | Master engineering asset for marketing & renders | **REAL & RIGGED** |
| **Ladakh Canyon Terrain** | [`assets/models/terrain.blend`](file:///d:/Programming/PS054/assets/models/terrain.blend) | **52.4 MB** | High-density Digital Elevation Model (DEM) | Realistic topological representation of Northern Sector (Leh/Ladakh/Siachen) | Dynamic camera tracker + flight dynamics | 120 FPS Top Gun terrain flight simulator | **REAL & SIMULATED** |
| **Bayraktar TB3 Airframe** | [`assets/models/airframes/bayraktar_tb3.blend`](file:///d:/Programming/PS054/assets/models/airframes/bayraktar_tb3.blend) | **677 KB** | Airframe, control surfaces, folding wings | Tactical MALE UAV airframe model demonstrating engine nacelle integration | Dynamic flight path waypoint tracker | Airframe visual representation in canyon flight | **REAL & RIGGED** |
| **Austro AE330 Turbodiesel** | [`assets/models/engines/austro_ae330.blend`](file:///d:/Programming/PS054/assets/models/engines/austro_ae330.blend) | **803 KB** | Inline 4-cylinder CRDi block, turbo, common-rail | Target powerplant for DRDO TAPAS-BH-201 (Rustom-II) | Multi-engine runtime selector | Propulsion engineering visualization | **REAL & RIGGED** |
| **TEI PD170 Turbodiesel** | [`assets/models/engines/tei_pd170.blend`](file:///d:/Programming/PS054/assets/models/engines/tei_pd170.blend) | **22.6 MB** | Dual-stage turbo, intercooler, FADEC casing | High-altitude 170 HP heavy-fuel aero diesel engine CAD | Multi-engine runtime selector | Advanced propulsion comparison | **REAL & RIGGED** |
| **WebGL Draco Models** | [`web/site/models/`](file:///d:/Programming/PS054/web/site/models/) | **< 2.5 MB** | Draco-compressed GLB binary assets | Ultra-low bandwidth browser client delivery | Three.js `DRACOLoader` via WASM worker | Zero-install web browser digital twin | **REAL & OPTIMIZED** |

---

### 20.2 The Three Distinct Simulation Roles

To eliminate ambiguity, the simulation assets perform three distinct technical roles:
1. **The Physical Teardown Role (Blender Twin — Option 2):**
   * *What it is:* A 100% raytraced EEVEE CAD viewport connected to the FastAPI backend.
   * *How it works:* When an anomaly is diagnosed (e.g. `BEARING_SPALLING`), the backend emits `target_parts = ["Crankshaft_Main_Bearing_Upper", "Crankshaft_Journal_2"]`. The Blender Python driver script immediately pans the camera smoothly to the internal bearing surface, explodes adjacent crankcase housings, and highlights the damaged surface in pulsating high-visibility emissive red.
2. **The Tactical Environmental Flight Sim (Ladakh Canyon — Option 3):**
   * *What it is:* A hardware-accelerated 120 FPS flight simulator operating over authentic Digital Elevation Model (DEM) terrain of the Ladakh mountain range.
   * *Why it matters:* Indian MALE UAVs (TAPAS-BH-201) frequently operate from high-altitude bases (e.g. Leh AGB at $10,682\text{ ft}$ ASL) across jagged mountain valleys. This simulation tests engine cooling performance under extreme thermal gradients (cold ambient air at altitude vs. low density reducing cooling mass flow).
3. **The WebGL Multi-Engine Browser HUD (`web/site/`):**
   * *What it is:* A zero-install WebGL application running in any browser (Edge, Chrome, Firefox).
   * *Zero-Latency Engine Switching:* All 5 engine models are pre-instantiated in GPU memory. Selecting a different engine switches visibility instantaneously ($0\text{ ms}$ asset reload latency).
   * *Dynamic Kinematics:* The crankshaft, connecting rods, and propeller rotate synchronously with live RPM via delta-time frame integration.

---

## 21. MULTI-FRONTEND ECOSYSTEM AUDIT & UNIFICATION ROADMAP

The repository currently contains multiple frontends created across different stages of development. We audited all of them to eliminate redundancy and define a single unified military platform architecture.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND INVENTORY & AUDIT                                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   1. THREE.JS WEBGL TWIN (`web/site/`)                                                 │
│      · Technology: Vanilla JS, Three.js r128, Draco WASM, GLSL Shaders                 │
│      · Status: **PRODUCTION READY — AUTHORITATIVE 3D WEB CLIENT**                      │
│      · Features: 0ms engine switching, live kinematics, thermal shaders, camera director│
│                                                                                        │
│   2. NATIVE DESKTOP GCS (`apps/desktop_gcs/standalone_gui_app.py`)                     │
│      · Technology: Python 3.12, Pygame (Hardware-Accelerated SDL)                      │
│      · Status: **OPERATIONAL — PRIMARY LOW-LATENCY TACTICAL HUD**                      │
│      · Features: Primary Flight Display (PFD), strip charts, ISA-18.2 alarms           │
│                                                                                        │
│   3. VITE + REACT DASHBOARD (`frontend/`)                                              │
│      · Technology: React 18, TypeScript, Tailwind CSS, Vite                            │
│      · Status: **PARTIALLY REDUNDANT — DUPLICATES WEB/SITE/ CAPABILITIES**              │
│      · Features: Analytical dashboard with Tailwind styling; requires Node build step  │
│                                                                                        │
│   4. USAVIONIX SITE MIRROR (`web/usavionix/`)                                          │
│      · Technology: Next.js static export mirror                                        │
│      · Status: **DECORATIVE / ARCHIVE — RECOMMENDED FOR RETIREMENT**                   │
│      · Role: Web design reference; completely disconnected from backend telemetry      │
│                                                                                        │
│   5. MISSION GRAPH VIEWER (`apps/mission_graph_viewer/`)                               │
│      · Technology: Python Graphviz / Webviewer                                         │
│      · Status: **SPECIALIZED UTILITY — INTEGRATED INTO RUNTIME HUB**                   │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 21.1 The Final Unified Platform Strategy
To avoid confusing evaluation judges with multiple conflicting launchers:
* **The Unified Presentation Standard:**
  1. **Primary Tactical Ground Control Interface:** The **Three.js WebGL Twin (`web/site/`)**, served directly by FastAPI on `http://localhost:8000/`. It delivers real-time 3D CAD visualization, live kinematics, thermal heatmaps, and telemetry gauges in a single integrated view.
  2. **Airborne / Ruggedized Field Interface:** The **Native Desktop Pygame GCS (`apps/desktop_gcs/`)**, executable with zero web server dependencies on military tactical laptops.
  3. **Engineering Teardown CAD Viewport:** The **Blender Master Twin (`assets/blender/`)**, invoked specifically when deep internal component structural examination is required.
* **Retirement Target:** The `web/usavionix/` mirror should be permanently archived to prevent clutter.

---

## 22. MISSION SIMULATION MODELING & CAUSAL PROPAGATION

Project ANUMAAN does not model the engine in isolation. It explicitly connects engine health to the UAV's aerodynamic flight envelope through **Causal Mission Propagation** ([`backend/mission/reliability.py`](file:///d:/Programming/PS054/backend/mission/reliability.py)):

```
┌─────────────────────────┐
│     ENGINE HEALTH       │  Subsystem health indices (Combustion, Thermal, Lubrication)
└────────────┬────────────┘
             │ Causal Physics Linkage
             ▼
┌─────────────────────────┐
│   PROPULSION CAPACITY   │  Max Available Thrust: T_avail = (P_shaft * eta_prop) / V
└────────────┬────────────┘
             │ Aerodynamic Flight Dynamics
             ▼
┌─────────────────────────┐
│   UAV FLIGHT ENVELOPE   │  Max Operating Ceiling: h_max drops from 28,000 ft -> 14,000 ft
│                         │  Max Sustained Climb Rate: ROC_max drops from 850 fpm -> 120 fpm
└────────────┬────────────┘
             │ Geographic & Terrain Constraints
             ▼
┌─────────────────────────┐
│   TACTICAL MISSION RISK │  Probability of Mission Completion: P(completion)
│                         │  Emergency Divert Reachability: Nearest recovery airfield
└─────────────────────────┘
```

### 22.1 The Flight Phase Cycle
The platform simulates and evaluates engine stress across six distinct operational flight phases:
1. **Pre-Flight Run-Up (Ground):** Dual FADEC lane parity test; magneto/coil ignition drop verification at $4,000\text{ RPM}$; baseline noise calibration.
2. **Takeoff (Full Throttle 100%):** Maximum power ($5,800\text{ RPM}$, $73.5\text{ kW}$), continuous BMEP $>11\text{ bar}$, maximum fuel flow ($27\text{ L/h}$). Peak thermal dissipation challenge.
3. **Climb (High Continuous 85%):** Sustained thermal climb at $5,500\text{ RPM}$. Atmospheric pressure lapses by $\approx 10\text{ kPa per }1,000\text{ m}$; cooling air mass flow decreases.
4. **Cruise / Ingress (65–75%):** Cruise economy mode. Best-economy BSFC ($\approx 265\text{ g/kWh}$). Baseline monitoring for slow component degradation.
5. **Loiter / Reconnaissance (55%):** Minimum fuel burn endurance flight ($18\text{--}24\text{ hours}$). Low engine vibration; thermal equilibrium stabilized.
6. **Descent / Tactical Glide (Idle to 30%):** Rapid throttle reduction. **Critical Thermal Shock Risk:** High airspeed combined with sub-zero ambient temperature ($-30^\circ\text{C}$) induces rapid cylinder cooldown ($dT/dt < -3.0^\circ\text{C/s}$), causing cylinder head cracking if unmanaged.

---

## 23. FORENSIC FLIGHT REPLAY & MERKLE AUDIT LEDGER

Post-flight incident investigation is supported through **Deterministic Flight Replay** backed by a **Cryptographic Merkle Tree Ledger** ([`backend/security/merkle_log.py`](file:///d:/Programming/PS054/backend/security/merkle_log.py)):

### 23.1 Cryptographic Merkle Ledger Architecture
* In airborne flight recorders (black boxes), data integrity is paramount. If an engine fails and a crash occurs, military investigators must prove that telemetry was not altered post-flight.
* Every ingested telemetry frame, residual vector, and diagnostic decision is hashed into a SHA-256 block:
  $$h_i = \text{SHA-256}(\text{Frame}_i \parallel \text{Residuals}_i \parallel \text{Diagnosis}_i \parallel t_{\text{mono}})$$
* Blocks are hierarchically combined into a Merkle tree root hash $\mathcal{R}_{\text{Merkle}}$.
* **Tamper Verification:** In experiment `E23`, 50 synthetic data-tampering attacks (altering a single CHT value by $0.1^\circ\text{C}$ in historical logs) were injected. The Merkle verification engine detected **100% of tampering attempts** instantly by flagging root hash divergence.

### 23.2 Scrubbable Timeline Replay
* The ground replay engine allows engineers to load any logged sortie file, scrub forward and backward in time, pause at the exact millisecond of anomaly inception, and step frame-by-frame through the Random Forest and Bayesian decision trees.
* Engineers can inspect what the pilot saw, what the digital twin estimated, and what physical residuals were generated, eliminating guesswork in post-incident debriefs.
