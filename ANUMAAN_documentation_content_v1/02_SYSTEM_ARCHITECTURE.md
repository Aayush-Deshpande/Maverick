# System Architecture

## 1. Seven-layer conceptual architecture

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart TB
    L1[1. Deterministic Edge / Avionics]
    L2[2. Resilient Datalink]
    L3[3. Real-Time Digital Twin Core]
    L4[4. Cognitive AI & Diagnostics]
    L5[5. Mission & Decision Layer]
    L6[6. Forensic Data / Fleet Layer]
    L7[7. Visualization / HMI]

    L1 --> L2 --> L3 --> L4 --> L5
    L3 --> L6
    L3 --> L7
    L4 --> L7
    L5 --> L7
```

## 2. Runtime data path

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart LR
    T[Telemetry frame]
    V[Sensor validation]
    P[Physics model]
    R[Residuals]
    M[ML / diagnosis]
    Q[Prognostics]
    MR[Mission reliability]
    WS[WebSocket state]
    UI[Web GCS + 3D Twin]

    T --> V --> P --> R --> M --> Q --> MR
    MR --> WS
    M --> WS
    Q --> WS
    WS --> UI
```

## 3. Edge / ground split

The target architecture separates deterministic low-latency processing from heavier asynchronous reasoning.

### Deterministic path

- telemetry ingestion,
- physical feature extraction,
- fast residual generation,
- fast novelty screening,
- black-box / store-and-forward logging.

### Cognitive path

- state estimation,
- fault diagnosis,
- degradation analysis,
- RUL estimation,
- mission consequence analysis,
- retrieval-augmented operator assistance.

## 4. Why the split matters

AI inference should not block the time-sensitive telemetry path. The documentation should make this architectural boundary obvious instead of presenting every algorithm as if it executes inside the same real-time loop.

## 5. Repository-to-architecture mapping

Document the actual code paths here using links such as:

- `backend/runtime/`
- `backend/twin/`
- `backend/physics/`
- `backend/ml/`
- `backend/mission/`
- `backend/telemetry/`
- `backend/server/`
- `web/site/`
- `tests/`

Each mapping should be verified against the current repository before publication.
