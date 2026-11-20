# assets/: Blender sources, 3D models, renders, textures
Global rules: ../AGENTS.md and ../DECISIONS.md. Full cleanup plan: P Part 5. Blender work list: A section 4.

## Absolute rules
- NEVER delete a `.blend` file (D1). Duplicates are moved with `git mv` to `assets/blender/_archive/` and recorded in `_archive/ARCHIVE_REGISTER.csv` (original path, new path, md5, size, date, reason).
- Before any move, record md5s of all assets (card C-01). After moves, every original md5 must still exist (T-REPO-1).
- Never save over a master `.blend`. Scripts save to `<name>_work.blend`, Prasad checks it in Blender, then it replaces the master.
- Lock before editing (after card C-03): `git lfs lock <file>.blend`, and unlock after committing.
- `*.blend1` files are Blender backups. They are not tracked: move them to `assets/blender/_archive/blend1_backups/` (gitignored, stays local), never into Git (D42).
- GLB files are build outputs of the export pipeline (C-05). Do not hand-edit or hand-copy them.

## Current layout (done in card P0-06, 19 Nov 2026)
- `assets/blender/engines/<engine_id>/<engine_id>.blend` is the MASTER for each engine. Next to it: `variants/` (showcase, lod1) and `import/` (FBX, CAD `cad/` with .stp/.rar).
- `assets/blender/reference/tei_pd170/`: reference geometry, not an engine we model.
- `assets/blender/airframes/bayraktar_tb3/`, `assets/blender/terrain/terrain_N34E077.blend`, `assets/blender/scenes/anumaan_master_twin.blend`.
- `assets/blender/_archive/`: duplicates, with `ARCHIVE_REGISTER.csv` (md5 for every moved file). `blend1_backups/` there is local only (gitignored).
- `assets/ASSET_REGISTER.csv`: one row per master (object/mesh/triangle counts, geometry status, manifest, web GLB).
- `assets/web/engines/<engine_id>.glb` becomes the ONLY committed web copy in card P0-07.
- Masters, all verified to open headless in Blender 5.2: 912 iS Sport 109 meshes (REAL, confirmed by Prasad); 914 590 meshes; 915 iS 16 meshes (mostly one merged mesh); AE300 165 meshes (AE330 shape, REPRESENTATIVE); VRDE 432 meshes (TEI PD170 shape, REPRESENTATIVE).

## Known facts (md5-verified)
- Archived duplicates:
  - `_archive/rotax_915.blend` is byte-identical to the 915 iS master;
  - `_archive/bayraktar_tb3_digital_twin.blend` is byte-identical to `airframes/bayraktar_tb3/variants/bayraktar_tb3_digital_twin.blend`;
  - `_archive/rotax_914_f.blend` has the same content as the 914 master (594 objects, 490,617 triangles, same names; D25).
- `web/site/assets/models/rotax_915is.glb` is byte-identical to the 912 GLB (wrong model shipped; fixed by P0-07).
- Git LFS tracks `*.blend`. GLB/FBX/EXR stay in normal Git (D28).
- Inspect any .blend read-only with: `D:\Blender\blender.exe -b <file> --python scripts/blender/inspect_blend.py`.

## Pipeline (C-05)
`blender -b <master> --python scripts/blender/export_engine.py` -> `scripts/blender/validate_nodes.py` against `configs/components/<id>.json` -> `gltf-transform optimize` (Draco/Meshopt, KTX2/WebP, NO join/flatten of mapped nodes) -> validate again -> `assets/web/`.
