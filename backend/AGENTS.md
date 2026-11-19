# backend/: FastAPI server, simulation, twin, detection, diagnosis, prognostics
Global rules: ../AGENTS.md and ../DECISIONS.md. This file adds the backend-specific rules.

## What is here today (main @ 9b5942e) and what it becomes
| Path | Today | Target (card) |
|---|---|---|
| `server/main.py` | FastAPI app, legacy broadcast loop | app factory; mounts v1 + legacy adapter (M0-06/08) |
| `server/engine_service.py` | legacy 912 simulator, `sync_from_tick`, GO default | archived after M0-07/08 (D12) |
| `server/engine_api.py` | `/api/engines/*`, fault id by list position (166-176) | replaced by `server/api_v1.py` (M0-06), fix in M0-08 |
| `runtime/hub.py`, `engine_runtime.py` | RuntimeHub + EngineRuntime; truth-based diagnosis (480-522) | single sim owner; diagnosis from evidence (M0-07, M3-06) |
| `plant/virtual_engine.py` | the live plant (wrong power formula, fixed 5200 rpm) | facade over `sim/` (M1-14) |
| `physics/` | partial models (`crank_dynamics`, `oil_system`, `thermo_model`, `turbo_model`, `rail`) | reused or ported into `sim/` |
| `telemetry/can_streamer.py` | legacy offset-fault generator | stops being a data source (M0-07); CAN framing reused in M7 |
| `telemetry/replay_engine.py` | broken replay (ELAPSED_SEC) | `recording/replay_hub.py` (M5-05) |
| `twin/` | UKF, virtual sensors, validity | extended in M3-01 |
| `detect/`, `diagnose/`, `prognose/` | detectors, BN, explain, RUL | wired in M3/M4 |
| `fadec_emulator/`, `edge/`, `security/`, `federation/` | not wired | M7 |

New packages (D2): `sim/`, `faults/`, `status/`, `recording/`, `terrain/`, `planning/`.

## Rules for backend code
- Layering:
  - `sim/` imports nothing from `detect`, `diagnose`, `status`, `prognose`, `twin` or `server`.
  - Inference packages never import `faults.manager`, `sim` truth or `TruthRecord` (T-DYN-4; `tests/test_no_truth_leak.py`).
- `sim/` modules are pure classes: `step(dt, inputs) -> outputs`, constants from the config `physics` block, randomness only from the engine's seeded RNG, no I/O, no wall clock.
- One simulation owner. Commands go into the per-engine queue and are applied at the start of the next tick. HTTP handlers never mutate engine state directly.
- Every public message is a pydantic model in `server/state_schema.py`. A change there must regenerate the TypeScript types (T-API-2).
- No engine/fault/part literals. Read them from `configs/` through `faults/registry.py` and the engine config loader (`physics/engine_config.py`).
- Errors: raise a typed error and return 422 with a reason. Never return a default value to hide a failure.
- Time: use `sim_time_s` everywhere (D8). Never use `time.time()` inside simulation, detection or prognostics.
- Writing files: only under `var/` (D6).

## Run and test
- Server: `python run_app.py` or `launch_backend_server.bat` (check which port it prints).
- Tests: `python -m pytest -q -p no:cacheprovider tests/<file>`; the full suite takes about 5 min (baseline in ../AGENTS.md).
- Probe an endpoint: `scripts/tools/probe_api.py`.
