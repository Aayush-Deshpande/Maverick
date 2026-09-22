# 🏗️ System Architecture & Dual-Plane Design
**DRDO / iDEX Problem Statement ID: 26054**  
*Dual-Plane Aerospace Architecture, Subsystem Boundaries, Threading Model & Topology*

---

## 1. High-Level System Architecture

To balance **hard real-time safety guarantees (< 20ms)** with **deep cognitive reasoning and technical manual explainability**, the system is structured as a **Dual-Plane Cyber-Physical Architecture**:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                      PLANE 1: REAL-TIME DETERMINISTIC ENGINE (Telemetry Loop: 20–50 Hz)                │
│                                                                                                        │
│  [27-Ch CAN Sensors] ──► [Sensor Sanity Validator] ──► [1D Thermodynamic Twin (PINN)]                 │
│                                                                  │                                     │
│                                                      14 Physics Residuals: Δ = Actual - Expected       │
│                                                                  ▼                                     │
│                                                      [Fast ML Diagnostic Pipeline]                     │
│                                                      • Autoencoder (Anomaly Score L2 Loss)             │
│                                                      • Random Forest (8 DRDO Fault Modes)              │
│                                                      • Gearbox FFT (3rd Harmonic Peak Tracking)        │
│                                                      • AIC Degradation Curve & Monte Carlo RUL         │
└───────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                    │
                                   Emits Unified State & JSON Event
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                      PLANE 2: COGNITIVE AGENTIC & RAG LAYER (Event-Driven / On-Demand)                 │
│                                                                                                        │
│                                    ┌────────────────────────────────────┐                              │
│                                    │        Mission Copilot Agent       │                              │
│                                    │  (Safety Guardrails & Orchestrator)│                              │
│                                    └───────┬────────────────────┬───────┘                              │
│                                            │                    │                                      │
│                   ┌────────────────────────┴────────┐  ┌────────┴──────────────────────┐               │
│                   ▼                                 ▼  ▼                               ▼               │
│         [Diagnostic Agent (XAI)]             [Local Vector RAG]             [Local Qwen3-4B Engine]    │
│         • Physical causal chains             • 21 Flight & MML Manuals      • 4-bit NF4 Quantization   │
│         • ATA Chapter mappings               • FlashRank / MiniLM Reranker  • GPU-Decoupled Reasoning  │
│         • Prescriptive SOP checklists        • Grounded Excerpt Retrieval   • Zero Hallucination Lock  │
└───────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                    │
                                  Pushes State & Visual Commands
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   MULTI-PLATFORM FRONTEND CLIENTS                                      │
│                                                                                                        │
│  ┌──────────────────────────┐  ┌──────────────────────────┐  ┌──────────────────────────┐             │
│  │   Web Ground Station     │  │   Blender 3D CAD Twin    │  │   Canyon Flight Sim      │             │
│  │ (React + Vite + Tailwind)│  │ (EEVEE Raytraced HUD/CAD)│  │ (120 FPS Top Gun View)   │             │
│  └──────────────────────────┘  └──────────────────────────┘  └──────────────────────────┘             │
│  ┌──────────────────────────┐  ┌──────────────────────────┐                                            │
│  │   Pygame Desktop GCS     │  │   Unity 3D Engine Bridge │                                            │
│  │ (Hardware Accelerated)   │  │ (C# Leaderlines/Shaders) │                                            │
│  └──────────────────────────┘  └──────────────────────────┘                                            │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. ML vs. Agent Boundary & Responsibility Matrix

$$\boxed{\textbf{Machine Learning Calculates Numbers} \quad\longleftrightarrow\quad \textbf{Agentic Layer Reasons with Context}}$$

* **Plane 1 (Fast ML & Physics):** Operates on continuous 27-channel telemetry streams at **20–50 Hz** (< 20ms per cycle). It calculates ISA air density, thermodynamic expected values, residuals, Autoencoder anomaly scores, Random Forest classification probabilities, and FFT spectral peaks.
* **Plane 2 (Cognitive Agent & RAG):** Operates **event-driven** or via operator chat requests. It consumes the pre-calculated ground-truth state, queries local engineering manuals via Vector RAG, orchestrates prescriptive SOP checklists, and synthesizes natural-language explanations strictly grounded in the causal chain.

| Functional Area | **Plane 1: Deterministic Physics & ML** | **Plane 2: Cognitive Agent & RAG** |
|---|---|---|
| **Sensor Ingestion** | Ingests CAN frames at 50 Hz, validates impedance and rate-of-change. | *Hands off* (no raw stream ingestion to protect latency). |
| **Physics Baseline** | Solves 1D thermodynamic differential equations for nominal CHT/EGT/MAP/Fuel Flow. | *Hands off* (consumes computed residuals). |
| **Anomaly Scoring** | Computes continuous Autoencoder L2 reconstruction loss and composite Z-score. | Evaluates operational severity against mission phase (e.g. loitering vs. takeoff). |
| **Fault Isolation** | Random Forest / Decision boundary outputs fault probabilities (e.g., F01 = 98.4%). | Explains *why* the fault occurred citing ATA 72-00 and DRDO FMECA documents. |
| **Vibration Analysis** | FFT sliding window tracks 3rd harmonic propeller shaft resonance. | Correlates vibration spikes with reduction gearbox maintenance history. |
| **Prognostics & RUL** | AIC model fitting (Linear/Exponential/Power-Law) + Monte Carlo RUL projection. | Evaluates Go/No-Go status (e.g., planned 18h sortie vs. 14.2h RUL $\rightarrow$ **NO-GO**). |
| **Checklist Execution**| *Not suited* (cannot parse unstructured text). | Formats step-by-step pilot SOP checklists from official Rotax manuals. |
| **3D CAD Animation** | Streams high-speed transform & scalar telemetry updates to gauges. | Dispatches visual camera focus commands, X-ray ghosting, and mesh highlighting. |

---

## 3. Threading & Concurrency Architecture

The backend operates 4 decoupled execution threads to ensure heavy AI/ML calculations never freeze real-time telemetry streaming:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   THREADING & CONCURRENCY MODEL                                        │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                        │
│  [ Thread 1: Authoritative Simulation Loop ] ── (Runs at 50 Hz / 20ms in background)                   │
│    • Updates streamer, evaluates sensor sanity, computes 14 residuals                                  │
│    • Runs 9-stage ML detection pipeline & majority vote buffer                                         │
│    • Assembles UnifiedTelemetryState under threading.Lock                                              │
│                                                                                                        │
│  [ Thread 2: Async FastAPI Event Loop ] ── (Uvicorn / asyncio)                                         │
│    • broadcast_telemetry_loop() pushes 50 FPS JSON frames to all connected WebSockets                 │
│    • Handles non-blocking REST endpoints (/api/state, /api/control, /api/health)                       │
│                                                                                                        │
│  [ Thread 3: Prognostics Worker Thread ] ── (Daemon thread, 10–20s interval)                           │
│    • Reads circular ScoreBuffer (7,200 frames)                                                         │
│    • Fits AIC degradation curves & runs Monte Carlo RUL calculations                                   │
│    • Writes latest PrognosticsReport into memory                                                       │
│                                                                                                        │
│  [ Thread 4: Local Qwen3-4B AI Worker Thread ] ── (Decoupled on-demand daemon)                         │
│    • Runs GPU-bound 4-bit causal LM inference (takes 2–4s) via asyncio.to_thread / threading.Thread    │
│    • Edge-triggered ONLY on fault onset or operator query                                              │
│    • Completely decoupled: GPU load NEVER delays or blocks 50 Hz telemetry frames                      │
│                                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Network Topology & Client-Server Communication

```
                         ┌─────────────────────────────────────────────────┐
                         │   AUTHORITATIVE BACKEND SERVER (FastAPI)        │
                         │   Port: 8000 (0.0.0.0) | Latency: < 15ms        │
                         └──────────────┬───────────────────┬──────────────┘
                                        │                   │
                  WebSocket State Push  │                   │ REST Control / Query
                  (/ws/telemetry & /ws/blender)             │ (/api/control, /api/ai/ask)
                                        │                   │
         ┌──────────────────────────────┼───────────────────┼──────────────────────────────┐
         ▼                              ▼                   ▼                              ▼
┌──────────────────┐           ┌──────────────────┐┌──────────────────┐           ┌──────────────────┐
│ Web Ground GCS   │           │ Blender 3D CAD   ││ Pygame GCS       │           │ Unity 3D Bridge  │
│ (React / Vite)   │           │ Viewport Client  ││ (Hardware GUI)   │           │ (C# Client)      │
│ • Live HUD Dials │           │ • 60 FPS Orbit   ││ • 120-frame EEVEE│           │ • Holographic HUD│
│ • Fault Dock     │           │ • Pulsing Glow   ││   Turntable      │           │ • 3D Leaderlines │
│ • AI Copilot Chat│           │ • X-Ray Ghosting ││ • Live Dials     │           │ • HTTP/MCP Ingest│
└──────────────────┘           └──────────────────┘└──────────────────┘           └──────────────────┘
```

### Protocol Summary
* **WebSockets (`/ws/telemetry`, `/ws/blender`):** Binary/Text JSON frames broadcast continuously at 50 Hz containing full kinematics, thermal states, 14 residuals, anomaly scores, active fault IDs, and causal chains.
* **REST APIs (`/api/*`):** Synchronous command dispatch (`/api/control`), health status (`/api/health`), snapshot retrieval (`/api/state`), post-flight CBM report export (`/api/debrief`), and AI copilot inquiries (`/api/ai/ask`).
