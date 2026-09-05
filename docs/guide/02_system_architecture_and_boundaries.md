# System Architecture, AI Boundaries & Defense Standards
**DRDO / iDEX Problem Statement ID: 26054**  
*Dual-Plane Aerospace Architecture, ML/Agent Boundary, Sensor Validation & Deployment*

---

## 📌 1. High-Level Dual-Plane System Architecture

To guarantee both **hard real-time safety** and **human-level cognitive explainability**, the system is structured as a **Dual-Plane Cyber-Physical Architecture**:

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    PLANE 1: REAL-TIME DETERMINISTIC ENGINE (Edge / Telemetry Loop: 10–50 Hz)       │
│                                                                                                   │
│  [Physical / CAN Sensors] ──► [Sensor Sanity Validator] ──► [1D Thermodynamic Twin (PINN)]        │
│                                                                        │                          │
│                                                            Calculates Physics Residuals           │
│                                                                        ▼                          │
│                                                        [Fast ML Diagnostic Engine]                │
│                                                        • Autoencoder (Anomaly Score)              │
│                                                        • XGBoost (8 DRDO Faults)                  │
│                                                        • FFT (Gearbox Harmonics)                  │
│                                                        • LSTM (RUL Estimation)                    │
└────────────────────────────────────────────────────────────────────────┬──────────────────────────┘
                                                                         │ Emits Structured JSON Event
                                                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    PLANE 2: COGNITIVE AGENTIC & RAG LAYER (Event-Driven / Decision Support)       │
│                                                                                                   │
│                                ┌──────────────────────────────────────────────┐                   │
│                                │       Main Mission Orchestration Agent       │                   │
│                                │   (Reasoning, Planning, Tool Dispatching)    │                   │
│                                └───────┬──────────────┬──────────────┬────────┘                   │
│                                        │              │              │                            │
│                    ┌───────────────────┴──┐   ┌───────┴──────────┐   └───┬──────────────────┐     │
│                    ▼                      ▼   ▼                  ▼       ▼                  ▼     │
│          [Diagnostic & XAI Agent]  [Simulation Agent]      [SOP & Safety Agent]    [3D Viewport]  │
│          • Root-cause analysis     • "What-If" scenarios   • Pilot emergency lists • Zoom camera  │
│          • Cross-sensor proof      • Ladakh/Thar replay    • Derating advisories   • Pulse mesh   │
│                    ▲                                             ▲                                │
│                    └──────────────────────┬──────────────────────┘                                │
│                                           ▼                                                       │
│                             [ LOCAL RAG VECTOR DATABASE ]                                         │
│                             • Rotax 912 iS Maintenance Manuals (MM) & IPC                         │
│                             • DRDO / UAV Flight Operating Limits & Envelope                       │
│                             • Emergency Checklists & FMECA Matrices                               │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. ML vs. Agentic Layer Boundary & Responsibility Matrix

$$\boxed{\textbf{Machine Learning Calculates Numbers} \quad\longleftrightarrow\quad \textbf{Agentic Layer Reasons with Context}}$$

* **Plane 1 (Fast ML & Physics):** Operates on high-speed continuous signals at **10–50 Hz** (< 20ms latency). Outputs mathematical state estimates, anomaly scores ($0.0 \rightarrow 1.0$), fault classifications, and RUL curves.
* **Plane 2 (Cognitive Agentic & RAG):** Operates **event-driven**. Ingests structured ML anomaly payloads, queries local engineering manuals via Vector RAG, orchestrates multi-step simulations, and controls 3D viewport actions.

### Side-by-Side Responsibility Matrix

| Subsystem / Task | **Machine Learning & Physics Plane** *(What ML Does)* | **Agentic & RAG Plane** *(What the Agent Does)* |
|---|---|---|
| **1. Sensor Telemetry & Ingestion** | • Ingests CAN frames at 10–50 Hz.<br>• Filters noise and validates sensor impedance. | *Hands off.* (Does not touch raw 50 Hz signals to prevent latency bottlenecks). |
| **2. Physics Baseline & Residuals** | • Computes thermodynamic theoretical baseline $P_{\text{thermo}}, T_{\text{thermo}}$.<br>• Computes residuals $\Delta = \text{Actual} - \text{Expected}$. | *Hands off.* Consumes only pre-calculated residuals. |
| **3. Anomaly Detection** | • **Autoencoders & Isolation Forests** compute continuous anomaly scores ($0.0 \rightarrow 1.0$). | • Evaluates anomaly severity in operational context (e.g. loitering over mountains vs. taxiing). |
| **4. Fault Classification** | • **XGBoost / 1D-CNN** classifies sensor residual patterns into Fault IDs (e.g., `Fault_02: Injector_Clog`, Conf: 94.2%). | • **Root-Cause Reasoner:** Queries RAG (Rotax Manuals) to explain *why* it's an injector clog and not a spark failure, citing specific mechanical sections. |
| **5. Mechanical Vibration** | • **FFT / Wavelet + SVM** tracks spectral peaks at shaft harmonics (e.g., 3rd harmonic dog-clutch peak). | • Interprets mechanical wear severity and cross-references historical maintenance logs to verify if clutch was recently serviced. |
| **6. Prognostics & RUL** | • **LSTM / GRU / PINNs** output a numerical Remaining Useful Life trajectory: $\text{RUL} = 14.2 \pm 1.1\text{ hrs}$. | • **Mission Go/No-Go Evaluator:** Compares RUL against planned sortie duration (e.g., planned 18h sortie > 14.2h RUL $\rightarrow$ issue **NO-GO** advisory). |
| **7. Emergency SOPs** | *Not suited.* (ML cannot read unstructured flight manuals or generate natural language checklists). | • Retrieves DRDO / OEM emergency procedures from RAG and formats direct pilot actions (e.g., *"Step 1: Throttle to 4,600 RPM; Step 2: Switch to Lane B ECU"*). |
| **8. "What-If" Simulation** | • Executes the thermodynamic differential equations and degradation physics engine. | • **Scenario Director:** Takes natural language user intent (*"Simulate 20k ft in Ladakh with Cyl #2 leak"*), configures simulation parameters, executes it as a tool, and synthesizes findings. |
| **9. 3D Digital Twin Viewport** | • Streams high-speed transform & scalar telemetry updates to gauges/dials. | • Invokes UI tools to highlight specific 3D meshes, animate cutaway views, and place interactive diagnostic callout badges. |

---

## 3. The Event-Driven JSON Data Contract

The ML layer communicates with the Agentic layer through a strictly validated JSON contract emitted upon anomaly trigger or state change:

```json
{
  "timestamp": "2026-08-28T20:25:00.120Z",
  "sortie_id": "SORTIE-2026-LADAKH-042",
  "flight_context": {
    "altitude_ft": 18200,
    "oat_celsius": -18.4,
    "flight_phase": "CRUISE_LOITER",
    "engine_rpm": 5150,
    "throttle_tps_percent": 68.0
  },
  "sensor_sanity": {
    "all_sensors_valid": true,
    "drift_detected": false
  },
  "ml_detection_payload": {
    "anomaly_score": 0.892,
    "primary_fault_id": 1,
    "fault_name": "CYLINDER_2_CHT_OVERHEAT",
    "confidence": 0.945,
    "trigger_residuals": {
      "CHT_2": {"actual": 142.8, "physics_expected": 108.5, "residual": 34.3, "unit": "deg_C"},
      "CHT_1": {"actual": 106.2, "physics_expected": 105.1, "residual": 1.1, "unit": "deg_C"}
    },
    "rul_prediction_hours": 3.4
  }
}
```

---

## 4. Sensor Sanity & Plausibility Validation (Sensor Drift vs. Real Engine Failure)

In military aviation, a sensor failure (e.g. thermocouple open circuit) must **never** be misdiagnosed as mechanical engine destruction.

```
                                  ┌───────────────────────────────────────────────┐
                                  │           INCOMING RAW SENSOR READING         │
                                  └──────────────────────┬────────────────────────┘
                                                         │
               ┌─────────────────────────────────────────┴────────────────────────────────────────┐
               ▼                                                                                  ▼
    ┌─────────────────────────────────────┐                            ┌─────────────────────────────────────┐
    │     PHYSICAL THERMODYNAMIC RAMP     │                            │     ELECTRICAL SENSOR ARTIFACT      │
    ├─────────────────────────────────────┤                            ├─────────────────────────────────────┤
    │ • Follows heat transfer equations   │                            │ • Instantaneous step change         │
    │ • Gradient $dT/dt \le 1.5^\circ\text{C/s}$│                      │ • Gradient $dT/dt > 10.0^\circ\text{C/s}$ (Unphysical)│
    │ • Correlates with adjacent CHT / Oil│                            │ • Zero Gaussian noise / flatline 0V │
    ├─────────────────────────────────────┤                            ├─────────────────────────────────────┤
    │  ==> TRUE ENGINE OVERHEAT FAULT     │                            │  ==> SENSOR FAILURE / OPEN CIRCUIT  │
    └─────────────────────────────────────┘                            └─────────────────────────────────────┘
```

1. **Rate-of-Change Limit ($\Delta x / \Delta t$):** If temperature jumps $+30^\circ\text{C}$ in a single 20ms frame, the validator flags a sensor fault.
2. **Cross-Sensor Correlation:** Real CHT increases produce subtle correlated increases in oil return temperature and neighboring exhaust runners.
3. **Noise Floor Analysis:** Real aviation transducers have natural analog ripple ($\pm 0.2^\circ\text{C}$). A perfectly flat reading indicates a frozen ADC buffer.

---

## 5. Edge-to-GCS Datalink & Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    ONBOARD UAV AIRFRAME (Edge Telemetry Processor: Jetson / CM4)                │
│                                                                                                 │
│  [CAN Bus / FADEC] ──► [Sensor Sanity Filter] ──► [Fast ML Anomaly Scoring & RUL Calc]          │
│                                                                │                                │
│                                                                │ Low-Bandwidth Telemetry Stream │
│                                                                ▼ (MAVLink / STANAG 4586)        │
│                                                   [RF / SATCOM DATALINK]                        │
└────────────────────────────────────────────────────────────────┼────────────────────────────────┘
                                                                 │
                                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    GROUND CONTROL STATION (GCS Laptop / Maintenance Server)                     │
│                                                                                                 │
│  [Telemetry Ingestion] ──► [60 FPS 3D Digital Twin HUD] ──► [Cognitive Agentic Orchestrator]    │
│                                                                        │                        │
│                                                            [Local Vector RAG & Graph DB]        │
│                                                                        ▼                        │
│                                                            [Pilot Directives & Debrief Reports] │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

* **Onboard Edge Unit:** Low-power deterministic C++/Python code ensuring continuous autonomous monitoring even if datalink is jammed.
* **Ground Control Station:** Full visual and cognitive power with 3D model rendering, RAG manual lookups, interactive knowledge graph, and deep mission replay.
* **100% Air-Gapped Operation:** All LLM, RAG, and database components run **100% locally and offline** on the GCS workstation without external cloud dependencies.
