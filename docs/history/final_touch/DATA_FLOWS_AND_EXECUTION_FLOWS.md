# ANUMAAN — End-to-End Data Flows & Execution Lifecycles
**DRDO / SIH Problem Statement ID: 26054**

---

## 1. The 20 Hz Telemetry & Anomaly Detection Pipeline

This sequence captures the core operational loop that executes 20 times per second across all active engines:

```mermaid
sequenceDiagram
    autonumber
    participant Plant as VirtualEngine (PlantSource)
    participant Hub as RuntimeHub
    participant Det as ResidualDetector (Tier 0)
    participant Gate as PersistenceGate (3/5)
    participant Res as Reservoir / Classifier (Tier 1)
    participant Svr as FastAPI WebSocket Hub
    participant UI as React Ground Control Station

    loop 20 Ticks Per Second (50 ms interval)
        Plant->>Plant: Advance thermodynamics 1 simulated second
        Plant->>Hub: Yield Frame (t, rpm, map, cht[4], egt[4], oil_p, bus_v)
        Hub->>Det: Ingest Frame
        Det->>Det: Compute residuals: z = TailCalibration.z(frame)
        Det->>Det: Evaluate scorers: {fly_bloom, mahalanobis, max_abs_z}
        Det->>Det: Compare against Split-Conformal Thresholds
        Det->>Gate: Pass raw_alarm boolean
        Gate->>Gate: Update sliding window (k=3, n=5)
        alt Confirmed Alarm (>= 3 of last 5 frames tripped)
            Gate-->>Det: Confirmed Alarm = True
            Det->>Res: Trigger heavy candidate classification
            Res->>Res: Readout reservoir state -> candidate fault mode
            Det->>Hub: Return DetectionResult (scores, ratios, top_channels, candidate)
        else Normal Operation
            Gate-->>Det: Confirmed Alarm = False
            Det->>Hub: Return DetectionResult (scores, ratios, top_channels, NOMINAL)
        end
        Hub->>Svr: Broadcast EngineStatePayload to /ws/engines/{id} and /ws/fleet
        Svr->>UI: JSON Telemetry & Alarm Stream
        UI->>UI: Update Primary Flight Display, Gauge Needle, and Alert Banner
    end
```

---

## 2. High-Speed Crank-Angle Waveform & DSP Processing Flow

For failure modes invisible to scalar telemetry (such as injector coking, needle valve bounce, and piston slap), the high-rate waveform pipeline operates on individual engine four-stroke cycles:

```mermaid
flowchart TD
    subgraph WaveformAcq["1. Waveform Acquisition & Indexing"]
        ToothSens["Crankshaft 60-2 Reluctor Wheel<br/>Tooth Trigger Pulses (≤ 25 ns timing)"]
        CamSens["Camshaft Phase Sensor<br/>(Cylinder #1 TDC Compression Index)"]
        PressureSens["In-Cylinder Acoustic / Pressure Transducers<br/>(fs = 50 kHz - 100 kHz)"]
        
        ToothSens --> CycleBlock["CycleBlock Assembler (backend/core/cycle_block.py)<br/>Bins continuous time-series into 720° Crank-Angle Window"]
        CamSens --> CycleBlock
        PressureSens --> CycleBlock
    end

    subgraph DSPProcessing["2. Digital Signal Processing & Feature Extraction"]
        CycleBlock --> CA_Domain["Crank-Angle Domain Transformation<br/>p(θ), where θ ∈ [0°, 720°]"]
        CA_Domain --> IMEP_Calc["Indicated Mean Effective Pressure (IMEP):<br/>IMEP = (1 / Vd) ∮ p(θ) dV"]
        CA_Domain --> HRR_Calc["Rate of Heat Release (ROHR):<br/>dQ/dθ = (γ / γ-1) p dV/dθ + (1 / γ-1) V dp/dθ"]
        CA_Domain --> Knock_Filter["Bandpass Filtering (4 kHz - 8 kHz):<br/>Maximum Resonant Amplitude Metric"]
    end

    subgraph HealthVector["3. Cycle Health Synthesis"]
        IMEP_Calc --> CHV["CycleHealthVector (backend/core/cycle_block.py)<br/>• imep_per_cylinder [bar]<br/>• work_peer_ratio [-]<br/>• ca10, ca50, ca90 [° ATDC]<br/>• peak_pressure_angle [° ATDC]<br/>• knock_intensity_index [-]"]
        HRR_Calc --> CHV
        Knock_Filter --> CHV
    end

    subgraph Prognostics["4. Advanced Combustion Diagnostics"]
        CHV --> CombustCheck{"Combustion Peer Ratio Check"}
        CombustCheck -->|Cyl #1 Work < 85% Peer Average| ClogAlert["Flag INJECTOR_COKING (ATA 73-10)"]
        CombustCheck -->|ca50 Retarded > 8° BTDC| MisfireAlert["Flag IGNITION_TIMING_DRIFT (ATA 74-00)"]
        CombustCheck -->|Knock Index > Threshold| DetonationAlert["Flag CRITICAL_KNOCK / OCTANE_DEGRADE"]
    end
```

---

## 3. Deterministic ATA-Chapter Fault Diagnosis & Emergency Advisory Flow

When an anomaly is confirmed, ANUMAAN executes an immediate, deterministic diagnostic resolution mapped to aerospace standard ATA chapters:

```mermaid
flowchart TD
    AnomalyTrigger["Residual Detector Confirms Anomaly<br/>(e.g., CHT_2 > 135°C & EGT_2 Delta > 45°C)"]
    
    subgraph FMECA_Engine["FMECA Isolability Matrix (backend/reliability/fmeca.py)"]
        MatchSignatures["Signature Correlator:<br/>Compare normalized residual vector against<br/>pre-computed fault isolability matrix"]
        IsolateFault["Fault Isolated: Mode #1 (Cylinder #2 CHT Overheat)"]
        MatchSignatures --> IsolateFault
    end

    subgraph DeterministicAgent["Deterministic ATA Reasoner (backend/agent/diagnostic_agent.py)"]
        Lookup["Retrieve Rotax Maintenance Manual Spec:<br/>ATA Chapter: ATA 72-00 (Engine Core & Cooling)<br/>Manual Citation: Rotax 912 iS MM Chapter 72-00-00, Sec 4.2"]
        GenerateChecklist["Synthesize Pilot Emergency Checklist:<br/>Step 1: Throttle back to 4,600 RPM (loiter power)<br/>Step 2: Command +12% fuel enrichment to lower CHT<br/>Step 3: Descend 3,000–5,000 ft into denser, cooler air<br/>Step 4: Vector toward nearest recovery waypoint"]
        GenerateWorkOrder["Generate Ground Maintenance Order:<br/>Inspect Cylinder #2 cooling shroud and baffle elastomeric seals"]
        Lookup --> GenerateChecklist
        Lookup --> GenerateWorkOrder
    end

    subgraph Distribution["Downstream Distribution"]
        FlightDisplay["React GCS Cockpit HUD:<br/>• Red Alert Banner on CHT Gauge<br/>• Instant 4-Step Pilot Checklist Modal"]
        ThreeJS_Viewport["Three.js / Blender 3D Twin:<br/>• Eases camera to Cylinder #2 Head<br/>• Illuminates mesh Covers_Theme_M_PlasticTheme_0"]
        MissionManager["Mission Reliability Engine:<br/>• Recalculates Rm from 0.98 -> 0.72<br/>• Triggers RTB (Return-to-Base) advisory"]
    end

    AnomalyTrigger --> MatchSignatures
    IsolateFault --> Lookup
    GenerateChecklist --> FlightDisplay
    GenerateChecklist --> ThreeJS_Viewport
    GenerateChecklist --> MissionManager
```

---

## 4. Conformal Prediction RUL & Cumulative Damage Fatigue Flow

To solve the DRDO requirement for honest, statistically bounded Remaining Useful Life (RUL) estimation:

```mermaid
flowchart LR
    subgraph OperationalHistory["Sortie Operational History"]
        Hist["Cumulative Engine Operational Profiles<br/>(RPM, Load, Thermal Cycles, Altitude)"]
    end

    subgraph PhysicsFatigue["Cumulative Damage Models (backend/evaluation/damage_model.py)"]
        Arrhenius["Arrhenius Thermal Degradation:<br/>k(T) = A • exp(-Ea / (R • T))<br/>Computes thermal oil & valve guide decay"]
        MinersRule["Palmgren-Miner Linear Damage Accumulation:<br/>D = ∑ (ni / Ni)<br/>Calculates piston crown & cylinder head fatigue"]
        Hist --> Arrhenius
        Hist --> MinersRule
    end

    subgraph ConformalCalibration["Split-Conformal Calibration Engine (backend/evaluation/conformal.py)"]
        Holdout["Held-Out Run-to-Failure Calibration Data"]
        NonConf["Compute Non-Conformity Scores:<br/>si = |RUL_true,i - RUL_predicted,i|"]
        Quantile["Conformal Quantile Calibration:<br/>q_val = Quantile(1 - alpha)"]
        Holdout --> NonConf --> Quantile
    end

    subgraph IntervalOutput["Statistical Output"]
        PointEst["Raw RUL Point Estimate: 340 Hours"]
        ApplyBound["Apply Statistically Bounded Margin:<br/>[RUL_low, RUL_high] = [340 - q_val, 340 + q_val]<br/>Coverage Guarantee: 95% Confidence"]
        PointEst --> ApplyBound
        Quantile --> ApplyBound
    end

    subgraph MissionDecision["Mission Reliability (backend/mission/)"]
        ApplyBound --> Rm_Calc["Mission Completion Reliability (Rm):<br/>Rm = exp(- (t_mission / RUL_low)^beta)<br/>If Rm < 0.90 -> Recommend Abort / Divert"]
    end

    Arrhenius --> PointEst
    MinersRule --> PointEst
```

---

## 5. Local RAG Copilot & Voice Stream Flow

For hands-free ground control station operation during emergency scenarios:

```mermaid
sequenceDiagram
    autonumber
    actor Pilot as UAV Ground Pilot / Maintenance Engineer
    participant Mic as Audio Input Stream
    participant STT as Local Whisper STT (backend/voice/stt_engine.py)
    participant Store as LocalKnowledgeStore (backend/knowledge/)
    participant LLM as Local LLM Engine (Sarvam-30B / BharatGen via Ollama)
    participant TTS as Local Kokoro-82M TTS (backend/voice/tts_engine.py)
    participant Headset as Operator Headset

    Pilot->>Mic: "Engine 1 CHT is high, what is the immediate recovery procedure?"
    Mic->>STT: Raw PCM Audio Waveform
    STT->>STT: In-process Whisper Transcription
    STT->>Store: Text Query: "CHT high recovery procedure"
    Store->>Store: Vector Similarity Search + FlashRank Reranker over Rotax MM PDFs
    Store-->>LLM: Top-3 Retrieved Context Passages (ATA 72-00 Cooling SOP)
    LLM->>LLM: Deterministic Context Injection + Local Model Inference
    LLM-->>TTS: Text Response: "Rotax ATA 72 directive: Throttle to 4600 RPM, enrich fuel trim by 12 percent, descend 3000 feet."
    TTS->>TTS: Kokoro-82M High-Speed Neural Speech Synthesis
    TTS->>Headset: Clear synthesized audio alert directly into operator headset
```
