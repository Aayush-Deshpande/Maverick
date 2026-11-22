# apps/: standalone clients (not the main web app)
Global rules: ../AGENTS.md and ../DECISIONS.md.

| App | What it is | Plan |
|---|---|---|
| `threejs_twin/` | old 3D page (`index.html`, vendored 2021 three.js) | Retired (`git mv` to `archive_tracked/threejs_twin`) per D10, D12, D75; `/app` redirects to React Three Fiber twin `/#twin`. |
| `blender_twin/standalone_digital_twin_app.py` | Blender viewport twin | M0-10: read `/api/v1` state, highlight by exact node names from the message, remove the private 1-8 fault ids and the offline sine telemetry (show OFFLINE). |
| `blender_twin/standalone_canyon_flight_app.py` | canyon flight in Blender | M5-09: remove the "dive to cool" bug (sets `fault_overheat=True`), the private engine model and the throttle-speed table; make it a viewer of the mission executive, or retire it. |
| `blender_twin/standalone_fault_diagnostic_app.py`, `flight_mission_recorder.py` | duplicate HUD helpers and private fault specs | read the registry; shared helpers go to `scripts/lib` (M8-02) |
| `desktop_gcs/`, `mission_graph_viewer/` | small desktop tools | leave alone unless a card names them |

## Rules
- Apps are CLIENTS. They never simulate engines, never invent telemetry, and never hold their own fault lists or part maps. Everything comes from `/api/v1`, the state message and `configs/`.
- Blender apps run inside Blender 5.2 (`D:\Blender\blender.exe`). Test them headless where possible. Visual checks need Prasad.
- Never save over a master `.blend` from an app or script.
