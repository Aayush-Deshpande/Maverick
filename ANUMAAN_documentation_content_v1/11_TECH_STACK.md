# Technology Stack

## Application layers

| Layer | Technologies / components | Role |
|---|---|---|
| Web UI | React / Vite / Tailwind / Three.js | Operator GCS and 3D visualization |
| Backend | Python / FastAPI | Runtime services and APIs |
| Realtime | WebSockets | Telemetry / state streaming |
| Digital Twin | Physics models + state estimation | Expected engine behaviour and state tracking |
| AI / ML | FlyHash-style novelty coding, diagnosis, prognostics, RAG components | Detection, diagnosis, forecasting, operator assistance |
| 3D | Blender + GLB / Draco assets | Authoring and web visualization |
| Data | CSV / dataset loaders / planned persistent telemetry store | Replay, calibration, experiments |
| Testing | Pytest / characterization / integration tests | Software verification |

## Architecture rule

Do not turn the technology stack into a logo wall.

For each technology, explain **why it exists in the system** and **which requirement it satisfies**.
