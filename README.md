# ANUMAAN — Rotax 912 iS MALE UAV Digital Twin & Health Monitoring System
**DRDO / SIH Problem Statement ID: 26054**

AI-enabled real-time digital twin for health monitoring, fault prediction and mission reliability
enhancement of aero piston engines used in MALE UAVs. Physics-based twin, ML fault detection,
per-cylinder crank-angle combustion diagnostics, conformal-calibrated RUL, computed mission
reliability, 3D CAD visualization, and a React ground control station.

**Start here if you're continuing this project (human or LLM):** [`docs/build/MENTAL_MODEL.md`](docs/build/MENTAL_MODEL.md)
— one read, tells you what's real, what's designed-but-unbuilt, and the traps (a large fraction of
this repo's code is disconnected from the live demo, not missing). Then
[`docs/build/SUPERSEDED_VS_CURRENT.md`](docs/build/SUPERSEDED_VS_CURRENT.md) before touching any
existing file, [`docs/build/UNIVERSALITY_AUDIT.md`](docs/build/UNIVERSALITY_AUDIT.md) for why this is still a one-engine simulator and how to fix it, [`docs/build/VERIFICATION_CHECKLIST.md`](docs/build/VERIFICATION_CHECKLIST.md) to run before/after every change, and [`docs/build/BACKLOG.md`](docs/build/BACKLOG.md) for the ordered task list.

**Start here for the general documentation index:** [`docs/README.md`](docs/README.md) — evidence-label
convention and where every part of the system is explained. [`docs/04_system_guide.md`](docs/04_system_guide.md)
covers the current (as-shipped) architecture end to end. [`docs/audit/`](docs/audit/README.md) has the
competitive audit and the full technical design (docs 07–12).

---

## Repository structure

```
3d_engine/
│
├── backend/                    Python backend — the system's actual intelligence
│   ├── physics/                 Thermodynamic twin, sensor validation, engine configs, turbo/fuel/injector models
│   ├── plant/                   Independent plant model (VirtualEngine) + the adapter wiring it into the live service
│   ├── ml/                      Detection pipeline, fault classifier, anomaly detector, RUL, crank-angle
│   │                             diagnostics, spectral analyser, FlyHash novelty detection
│   ├── evaluation/               Conformal prediction, threshold-baseline comparator, damage accumulation,
│   │                             PHM metrics, external validation, novelty/UNKNOWN handling
│   ├── mission/                  Computed mission reliability + prescriptive advisory
│   ├── reliability/              FMECA fault taxonomy, fault isolability analysis
│   ├── twin/                     Twin validity monitoring, physics-constrained telemetry integrity
│   ├── edge/                     Edge feature compression, bandwidth/power/latency accounting
│   ├── telemetry/                Synthetic telemetry generator, CAN-style streamer, dataset fusion, parsers
│   ├── server/                   FastAPI app — REST + WebSocket, the authoritative EngineStateService
│   ├── agent/                    Deterministic ATA-chapter diagnostic agent + conversational copilot
│   ├── graph/                    Mission knowledge graph, sortie/anomaly/maintenance persistence
│   ├── knowledge/                Offline RAG (PDF/office/text loaders, embedding index, reranker)
│   ├── reports/                  Mission bundle + report-dump writers
│   ├── voice/                    Local STT/TTS voice copilot (optional; see docs/audit/02_self_audit.md)
│   └── osacbm.py                 ISO 13374 / OSA-CBM six-layer architecture mapping
│
├── frontend/                    React + TypeScript + Vite ground control station dashboard
│
├── apps/                        Standalone desktop applications
│   ├── blender_twin/             Blender EEVEE 3D digital twin viewport, canyon flight simulation
│   ├── desktop_gcs/               Pygame hardware-accelerated GCS HUD
│   └── mission_graph_viewer/      Standalone mission knowledge-graph viewer
│
├── web/                         Static web deliverables
│   ├── site/                     Standalone WebGL presentation site (Three.js)
│   └── usavionix/                 Reference material for the web site's design (mirror + asset analysis)
│
├── assets/                      3D asset library (Git LFS)
│   ├── models/                    Engine + airframe CAD (Blender, FBX, STEP)
│   ├── blender/                   Working Blender scenes (Rotax 912 iS master scene, etc.)
│   ├── model_images/              Reference image libraries
│   ├── renders/                   Presentation and validation renders
│   └── manifests/                 Engine/platform asset manifests
│
├── docs/                        PRIMARY documentation — problem statement, 27-part study course,
│                                 competitive audit, asset program, pitch material. See docs/README.md.
├── analysis/                    Background/as-built documentation superseded by docs/ on conflict.
│                                 See analysis/README.md.
├── UpdatedReport/                Narrative project report set. ⚠️ See
│                                 UpdatedReport/31_VERIFICATION_AND_CORRECTIONS.md before quoting it —
│                                 some file paths and competitor claims in it do not match this repo.
│
├── Datasets/                     Dataset catalogue (metadata only; raw data untracked by design)
├── data/                         Live application data — missions, telemetry, graph DB, documents
├── report_dump/                  Generated mission report bundles
├── scripts/                      Build, asset-generation and data-harvesting scripts
├── tests/                        pytest suite
├── vendor/                       Large local-only dependencies (gitignored): local LLM weights, voice
│                                 models, third-party tools (cloudflared/ngrok/blender_mcp)
├── competitors/                  Cloned competitor repos for the audit (gitignored, not committed)
│
├── requirements.txt
├── pytest.ini
├── run_app.py                    Unified interactive launcher
└── launch_*.bat                  Windows one-click launchers (see below)
```

---

## Quick start

### Universal launcher (`run_app.py`)
```bash
python run_app.py                 # interactive menu
python run_app.py server          # FastAPI 20 Hz telemetry & control backend (port 8000)
python run_app.py blender         # Blender 3D viewport HUD
python run_app.py canyon          # Ladakh canyon flight simulation
python run_app.py pygame          # Hardware-accelerated Pygame desktop GCS
python run_app.py verify          # Automated scene verification & audit
```

The Three.js engine twin is served by the same FastAPI service: start `python run_app.py server`
and open `http://127.0.0.1:8000/app`. Engine selection, live telemetry, flight-condition
controls, and fault injection are available in the browser UI; no separate Three.js launcher is needed.

### Windows one-click launchers
- `launch_backend_server.bat` — FastAPI telemetry/control backend (`http://127.0.0.1:8000`, docs at `/docs`).
- `launch_standalone_app.bat` — starts the backend if not already running, then opens the native
  Blender 3D digital twin viewport (`assets/blender/rotax_912_is_sport.blend`).
- `launch_canyon_simulation.bat` — Ladakh canyon flight simulation (`assets/models/terrain.blend`).
- `launch_web_dashboard.bat` — builds and serves the React GCS dashboard.
- `launch_anumaan_site.bat` — serves the static presentation site (`web/site/`).
- `launch_mission_graph.bat` — simulates missions, then opens the mission graph viewer.
- `launch_public_tunnel.bat` — exposes the backend over a tunnel for off-network access.

### Web/mobile dashboard
```bash
launch_backend_server.bat     # start the telemetry backend first
launch_web_dashboard.bat      # then serve the dashboard
```
Open `http://localhost:5173` (laptop) or `http://<laptop-lan-ip>:5173` (phone on the same Wi-Fi).

### Opening the 3D twin directly in Blender
1. Open [`assets/blender/rotax_912_is_sport.blend`](assets/blender/rotax_912_is_sport.blend) in Blender.
2. Run [`apps/blender_twin/standalone_digital_twin_app.py`](apps/blender_twin/standalone_digital_twin_app.py) from the Scripting workspace.

---

## The independent plant (G01)

By default the twin validates against a synthetic generator built from its own equations. Set
`ANUMAAN_USE_INDEPENDENT_PLANT=1` before launching the backend to route nominal flight and DRDO
faults 1–4 through `backend/plant/VirtualEngine` instead — a physically independent model with its
own build-to-build variation, sensor bias/lag/noise, and hidden fault injection, so residuals reflect
genuine model mismatch rather than a generator checking itself. **Off by default**: the published
classifier accuracy was measured against the old distribution and has not yet been re-validated
against this one. See [`backend/plant/adapter.py`](backend/plant/adapter.py) for the exact scope
(faults 5–8 are not yet modelled in the plant and continue to run through the original generator).

```bash
set ANUMAAN_USE_INDEPENDENT_PLANT=1   # Windows
launch_backend_server.bat
```

---

## DRDO fault matrix (PS-26054)

| # | Fault mode | Primary sensor trigger | 3D target part |
|---|---|---|---|
| 01 | Cylinder #2 CHT Overheat | CHT > 135 °C | Cylinder #2 head |
| 02 | Fuel Injector #1 Clog | Fuel flow drop + EGT delta | Intake rail injector |
| 03 | Ignition Misfire | RPM jitter + EGT drop | Ignition harness / spark leads |
| 04 | Oil Pressure Loss | Oil press < 2.0 bar | Dry-sump reservoir & filter |
| 05 | Gearbox Vibration | Accelerometer 3rd harmonic | Propeller reduction gearbox |
| 06 | Exhaust EGT Imbalance | EGT delta > 65 °C | Exhaust runner #3 |
| 07 | Alternator Voltage Sag | Bus voltage < 12.8 V | Alternator / serpentine belt |
| 08 | Dual FADEC ECU Drift | MAP sensor Lane A/B delta | Dual-lane ECU module |

Each fault carries a deterministic ATA-chapter directive (root cause, prescriptive action, emergency
checklist) from `backend/agent/diagnostic_agent.py` — no LLM involved in the diagnosis itself.

---

## Tests

```bash
pytest tests/ -q
```

## Documentation

- [`docs/README.md`](docs/README.md) — full index, evidence-label convention (✅/🔶/⬜/🔒)
- [`docs/04_system_guide.md`](docs/04_system_guide.md) — current architecture, read from source
- [`docs/audit/README.md`](docs/audit/README.md) — competitive audit, self-audit, build plan
- [`docs/study/`](docs/study/README.md) — 27-part technical course, first principles to implementation
