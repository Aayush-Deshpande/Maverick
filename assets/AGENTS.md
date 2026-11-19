# assets/: Blender sources, 3D models, renders, textures
Global rules: ../AGENTS.md and ../DECISIONS.md. Full cleanup plan: P Part 5. Blender work list: A section 4.

## Absolute rules
- NEVER delete a `.blend` file (D1). Duplicates are moved with `git mv` to `assets/blender/_archive/` and recorded in `_archive/ARCHIVE_REGISTER.csv` (original path, new path, md5, size, date, reason).
- Before any move, record md5s of all assets (card C-01). After moves, every original md5 must still exist (T-REPO-1).
- Never save over a master `.blend`. Scripts save to `<name>_work.blend`, Prasad checks it in Blender, then it replaces the master.
- Lock before editing (after card C-03): `git lfs lock <file>.blend`, and unlock after committing.
- `*.blend1` files are Blender backups. They are not tracked: move them to `assets/blender/_archive/blend1_backups/` (gitignored, stays local), never into Git (D42).
- GLB files are build outputs of the export pipeline (C-05). Do not hand-edit or hand-copy them.

## Known facts (md5-verified on 9b5942e)
- Identical pairs: `rotax_915.blend` == `rotax_915is.blend`; `assets/blender/bayraktar_tb3_digital_twin.blend` == `assets/models/bayraktar_tb3_digital_twin.blend`.
- `rotax_914.blend` and `rotax_914_f.blend` are the same size but different content. Prasad decides which is master.
- VRDE model = TEI PD170 geometry; AE300 model = AE330 geometry. Label both "representative".
- `web/site/assets/models/rotax_915is.glb` is byte-identical to the 912 GLB (wrong model shipped).
- Git LFS tracks `*.blend`. GLB/FBX/EXR are not in LFS yet; add them for new commits only (no history rewrite).

## Target layout (P 5.2)
`assets/blender/engines/<engine_id>/<engine_id>.blend` (MASTER) + `variants/` + `import/`; `reference/`; `airframes/`; `terrain/`; `scenes/`; `_archive/`; `assets/web/engines/<engine_id>.glb` (the ONLY committed web copy); `assets/manifests/`; `ASSET_REGISTER.csv`.

## Pipeline (C-05)
`blender -b <master> --python scripts/blender/export_engine.py` -> `scripts/blender/validate_nodes.py` against `configs/components/<id>.json` -> `gltf-transform optimize` (Draco/Meshopt, KTX2/WebP, NO join/flatten of mapped nodes) -> validate again -> `assets/web/`.
