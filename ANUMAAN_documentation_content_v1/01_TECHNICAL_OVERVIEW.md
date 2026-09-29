# Technical Overview

## 1. Problem

SIH 26054 asks for an AI-enabled real-time Digital Twin for health monitoring, fault prediction, and mission reliability enhancement of aero-piston engines used in MALE UAVs.

The engineering challenge is not simply to display engine telemetry or a 3D model. The system must maintain a synchronized computational representation of engine state and use that state to reason about abnormal behaviour and future risk.

## 2. Core methodology

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart LR
    A[Telemetry / Plant Simulation]
    B[Validation]
    C[Physics Baseline]
    D[Residual Vector]
    E[Anomaly Detection]
    F[Fault Diagnosis]
    G[Degradation / RUL]
    H[Mission Consequence]
    I[Operator GCS]

    A --> B --> C --> D --> E --> F --> G --> H --> I
```

## 3. Key engineering idea

The central loop is:

**operating context → expected physical behaviour → observed minus expected residuals → diagnosis → degradation trajectory → mission consequence**

Physics establishes what the engine should do under the current operating point. Data-driven and probabilistic layers then reason about departures from that expected behaviour.

## 4. Current implementation posture

| Capability | Documentation status |
|---|---|
| Engine physical modelling | Implemented / tested in the current software environment |
| Real-time telemetry streaming | Implemented at the documented simulation rate |
| Physics residual generation | Implemented |
| Sensor validation / residual shielding | Implemented |
| Bayesian / supervised diagnosis | Implemented in the current backend |
| Degradation and RUL analytics | Implemented as analytical/prototype components |
| FlyHash novelty detector | Implemented and tested; live-loop integration must be described separately |
| Historical replay | Implemented |
| Browser 3D engine twin | Implemented for available web assets |
| Integrated browser mission planner | Roadmap / integration work |
| Physical engine or flight-data validation | Not currently claimed |

## 5. Reader promise

Every page in this documentation should answer four questions:

1. What enters the subsystem?
2. What mathematical or software transformation occurs?
3. What leaves the subsystem?
4. What evidence proves the current implementation?
