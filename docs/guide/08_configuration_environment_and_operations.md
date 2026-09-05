# 🔧 Configuration, Environment & Operations Runbook
**DRDO / iDEX Problem Statement ID: 26054**  
*System Prerequisites, Environment Setup, Launcher Reference & Troubleshooting*

---

## 1. System Requirements & Prerequisites

| Requirement | Minimum Specification | Recommended Production Specification |
| :--- | :--- | :--- |
| **Operating System** | Windows 10/11 (64-bit) | Windows 11 Pro (64-bit) |
| **Processor (CPU)** | Intel Core i5 / AMD Ryzen 5 (4+ Cores) | Intel Core i7/i9 or AMD Ryzen 7/9 (8+ Cores) |
| **System RAM** | 16 GB DDR4/DDR5 | 32 GB DDR5 |
| **Graphics (GPU)** | NVIDIA GTX 1650 (4 GB VRAM) | NVIDIA RTX 4050 / 4060 / 3060 (6+ GB VRAM) |
| **Python** | Python 3.10 – 3.12 | Python 3.12.x (64-bit) |
| **Node.js** | Node.js v18.x LTS | Node.js v20.x LTS |
| **Blender** | Blender 4.2 LTS | Blender 5.2+ (EEVEE Next Engine) |

---

## 2. Installation & Environment Setup

### 2.1. Python Backend & ML Environment
```bash
# 1. Clone repository and navigate to root directory
cd 3d_engine

# 2. (Optional) Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install core Python dependencies
pip install -r requirements.txt

# 4. (Optional) Install PyTorch with CUDA support for local Qwen3-4B inference
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate bitsandbytes
```

### 2.2. Web Ground Control Station (Frontend)
```bash
# Navigate to frontend and install npm packages
cd frontend
npm install

# Start local Vite development server (Port 5173)
npm run dev
```

---

## 3. Application Launchers & Operating Modes

### 3.1. Unified Python Launcher (`run_app.py`)
Run the unified multi-target launcher from the project root:
```bash
# Interactive selection menu:
python run_app.py

# Direct target execution:
python run_app.py server    # Launch Authoritative Laptop Backend Server (Port 8000)
python run_app.py blender   # Launch Blender 5.2 EEVEE 3D Engine CAD Twin
python run_app.py canyon    # Launch 120 FPS Top Gun Ladakh Canyon Simulation
python run_app.py pygame    # Launch Hardware-Accelerated Desktop Pygame GCS
python run_app.py verify    # Run Headless Scene & Geometry Verification Audit
```

### 3.2. Windows 1-Click Batch Launchers
* `launch_backend_server.bat`: Starts the FastAPI server on `0.0.0.0:8000`.
* `launch_standalone_app.bat`: Opens Blender 5.2 and launches the 3D CAD Twin HUD.
* `launch_canyon_simulation.bat`: Starts the 120 FPS Ladakh Canyon flight simulation.
* `launch_public_tunnel.bat`: Spawns an Ngrok / Cloudflare tunnel for mobile phone connectivity.

---

## 4. Port Assignments & Network Topology

```
┌──────────┬─────────────────────────────┬───────────────────────────────────────────┐
│ Port     │ Service                     │ Protocol / Description                    │
├──────────┼─────────────────────────────┼───────────────────────────────────────────┤
│ **8000** │ FastAPI Laptop Server       │ HTTP REST & WebSockets (/ws/telemetry)    │
│ **5173** │ Vite Web GCS Dev Server     │ Local React Frontend development server   │
│ **8080** │ Web GCS Static Preview      │ Standalone Web Ground Control Station     │
└──────────┴─────────────────────────────┴───────────────────────────────────────────┘
```

---

## 5. Environment Variables Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ROTAX_BACKEND_URL` | `http://127.0.0.1:8000` | Target backend URL used by Blender and Web clients. |
| `QWEN_MODEL_ID` | `./Qwen3-4B` or `Qwen/Qwen3-4B` | Local filesystem path or Hugging Face model repository. |
| `QWEN_MAX_NEW_TOKENS` | `180` | Maximum token limit for Copilot natural language responses. |
| `QWEN_ENABLE_THINKING`| `0` | Set to `1` to enable Qwen3 thinking preambles; `0` for fast tactical mode. |

---

## 6. Automated Testing & Scene Verification

### 6.1. Running the Pytest Test Suite
The repository includes 78 unit and integration tests across physics, ML, RAG, and APIs:
```bash
# Run complete test suite
pytest

# Run specific test modules
pytest tests/test_physics_and_telemetry.py
pytest tests/test_ml_classifier.py
pytest tests/test_server_api.py
pytest tests/test_causal_propagation.py
```

### 6.2. 3D Model Geometry & Material Audit
Run headless 3D asset verification inside Blender:
```bash
python run_app.py verify
```

---

## 7. Operational Troubleshooting Guide

### ⚠️ Issue 1: "Blender executable could not be found"
* **Cause:** Blender is installed in a non-standard directory.
* **Resolution:** Ensure Blender 5.0+ is installed in `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe` or add Blender to your system `PATH`.

### ⚠️ Issue 2: "No CUDA GPU detected for Qwen3-4B"
* **Cause:** Running on a machine without an NVIDIA GPU or missing CUDA drivers.
* **Resolution:** The system automatically falls back to fast extractive RAG synthesis. Telemetry, physics, and ML classification are completely unaffected.

### ⚠️ Issue 3: "Datalink Disconnected" in Web GCS
* **Cause:** Backend server is not running on port 8000, or browser is blocking localhost access.
* **Resolution:** Run `python run_app.py server` and verify `http://127.0.0.1:8000/api/health` returns `ONLINE`. Click "Configure Host Link" in the web header if running over a LAN IP or tunnel.
