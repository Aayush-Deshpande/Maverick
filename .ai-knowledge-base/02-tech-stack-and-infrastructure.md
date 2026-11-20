# 02. Tech Stack & Infrastructure

## 1. System Technology Matrix

### Backend Runtime & Intelligence (`backend/`)
| Component | Technology | Version | Purpose in Ecosystem |
|---|---|---|---|
| **API & Socket Server** | FastAPI / Starlette | >= 0.109.0 | High-concurrency async REST and WebSocket server broadcasting at 20 Hz |
| **ASGI Web Server** | Uvicorn | >= 0.27.0 | Lightning-fast ASGI event server hosting endpoints on `0.0.0.0:8000` |
| **Schema Validation** | Pydantic v2 | >= 2.6.0 | Strict contracts for telemetry ingestion, analytics states, and commands |
| **Scientific Compute** | NumPy / SciPy | >= 1.26.0 | Vectorized matrix operations, thermodynamic calculations, and FFT orders |
| **Machine Learning** | Scikit-Learn | >= 1.4.0 | Random Forest multi-class fault classification (`joblib` model serialization) |
| **Speech-to-Text** | Faster-Whisper / Whisper | Local | Zero-latency local speech transcription for tactical pilot copilot |
| **Text-to-Speech** | Kokoro-ONNX | Local | Lightweight local neural voice synthesis for emergency auditory advisories |
| **Document Ingestion** | PyPDF, python-docx, python-pptx | Standard | Air-gapped parsing of OEM flight manuals and technical orders |
| **Testing Harness** | Pytest / Pytest-Asyncio | >= 8.0.0 | Unit and regression test suite spanning 11 test modules in `tests/` |

### Frontend & Ground Control Station (`frontend/`)
| Component | Technology | Version | Purpose in Ecosystem |
|---|---|---|---|
| **Core UI Library** | React | 18.3.1 | Component rendering, concurrent UI updates, and error boundary isolation |
| **Type Safety** | TypeScript | 5.4.5 | Strict interface definitions for 27-parameter telemetry & state |
| **Build & Bundler** | Vite | 5.3.1 | Ultra-fast HMR and optimized production asset compilation |
| **Client State** | Zustand | 4.5.7 | High-performance, un-opinionated store managing 20 Hz socket state |
| **3D Engine** | Three.js | 0.169.0 | WebGL 3D rendering of engine assemblies and fault-highlighted meshes |
| **Declarative 3D** | @react-three/fiber | 8.18.0 | React wrapper for Three.js scene graphs and render loops |
| **3D Helpers** | @react-three/drei | 9.122.0 | Orbit controls, environment maps, and GLTF asset loaders |
| **Styling & Design** | Tailwind CSS | 3.4.4 | Tactical dark-mode UI, aerospace HUD design tokens |
| **Icons & Visuals** | Lucide-React | 0.395.0 | Tactical iconography across pilot and engineering dashboards |
| **Scientific Visuals** | D3-Scale / D3-Shape | 4.0.2 / 3.2.0 | High-fidelity real-time degradation curve plots and trend charting |

### Desktop Native Viewports (`apps/`)
| Component | Technology | Purpose |
|---|---|---|
| **Blender CAD Twin** | Blender 3.6+ / 4.x (EEVEE) | Real-time viewport driven via `bpy` sockets, highlighting fault components |
| **Canyon Simulation** | Blender Game/Logic Loop | Ladakh DEM digital elevation model flight profile simulation |
| **Hardware HUD** | Pygame 2.5+ | Ultra-low-resource native HUD for embedded tactical field screens |

---

## 2. Infrastructure, Build & Deployment

### Build & Execution Pipeline
1. **Universal Python CLI (`run_app.py`)**:
   - `python run_app.py server` -> Launches FastAPI backend (`http://127.0.0.1:8000`)
   - `python run_app.py blender` -> Initializes Blender master scene with socket client
   - `python run_app.py canyon` -> Boots Ladakh terrain mission simulation
   - `python run_app.py pygame` -> Launches hardware-accelerated desktop HUD
   - `python run_app.py verify` -> Runs automated asset, scene, and math audits
2. **Frontend Build**:
   ```bash
   cd frontend
   npm install
   npm run build    # executes: tsc && vite build -> dist/
   npm run preview  # previews production bundle on port 4173
   ```
3. **Containerization (`Dockerfile`)**:
   - Alpine/Debian-based Python slim container encapsulating backend dependencies, exposing port 8000.
4. **Cloud & Edge Targets**:
   - **Local / Bare-Metal**: Windows/Linux laptop acting as GCS host.
   - **PaaS Deployment**: Configuration profiles present for Railway (`railway.json`), Render (`render.yaml`), and Firebase (`firebase.json`).

---

## 3. Environment Variables & Operating Prerequisites

| Variable Name | Default Value | Description |
|---|---|---|
| `PYTHONUTF8` | `1` | **Critical on Windows:** Prevents legacy cp1252 UnicodeEncodeError crashes during startup |
| `ANUMAAN_USE_INDEPENDENT_PLANT` | `0` | Set to `1` to route nominal flight and faults 1–4 through `VirtualEngine` independent plant |
| `FASTAPI_HOST` | `127.0.0.1` | Binding host IP address (use `0.0.0.0` for LAN GCS broadcast) |
| `FASTAPI_PORT` | `8000` | HTTP and WebSocket binding port |
| `VITE_API_URL` | `http://127.0.0.1:8000` | Backend REST URL for React frontend |
| `VITE_WS_URL` | `ws://127.0.0.1:8000/ws/telemetry` | Authoritative 20 Hz telemetry WebSocket endpoint |
| `FEDNEMO_MODEL_PATH` | Optional | Custom path to local Nemotron-4B / Qwen weights |
