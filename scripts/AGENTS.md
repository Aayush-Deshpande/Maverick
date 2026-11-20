# scripts/: tooling, Blender scripts, generators (not imported by the server)
Global rules: ../AGENTS.md and ../DECISIONS.md.

## What is here
- `lib/`: shared Blender/CAD helpers (`anumaan_blender_lib.py`, `anumaan_cad_lib.py`, `anumaan_twin_controller.py`).
- `tools/`: Blender build/render/export scripts (`export_all_engine_glbs.py`, `inspect_blend.py`, `render_*.py`, `build_*.py`) and `probe_api.py`.
- `validate/validate_asset.py`.
- `blueprint_builder/`, `dt_builder/`, `intent_builder/`: document generators (old docs workflow).
- Knowledge-base builders, audit scripts, `.ps1` health checks, `simulate_missions.py`, `run_15_step_verification_demo.py`.

## Rules
- Blender scripts run headless: `D:\Blender\blender.exe -b <file> --python <script> -- <args>`. They save to a new file (`*_work.blend`), never over the input, and print a table of what they changed.
- They never delete `.blend` files.
- Duplicate helpers (`create_pbr_material` in 3 files, HUD helpers in the Blender apps) are merged into `lib/` (M8-02). Do not add new copies.
- Generators that write docs or configs must be deterministic and write only their stated output paths.
- New pipeline tools go in `scripts/blender/` (export, node validation, bpy helpers) and `scripts/assets/` (optimize, md5 registers) per D20. The root `tools/` folder is gitignored and holds only local binaries such as ngrok.exe.
- The launchers (`launch_*.bat` at the root) move to `scripts/launchers/` in card C-04.
