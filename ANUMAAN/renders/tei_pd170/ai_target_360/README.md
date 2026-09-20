# TEI-PD170 — 360° Render Set Matched to the `ai-tagert` Reference

Renders of `ANUMAAN/Models/engines/tei_pd170.blend` shot at the camera angles
defined by `ANUMAAN/Models_Images/ai-tagert/TEI PD170/`, for 1:1 comparison
against that reference dataset.

## How it was produced
```
E:\Blender\blender.exe -b ANUMAAN/Models/engines/tei_pd170.blend \
    -P ANUMAAN/scripts/tools/render_ai_target_360.py -- <out_dir>
python ANUMAAN/scripts/tools/compose_ai_target_sheets.py <out_dir> "<ai-tagert/TEI PD170>"
```
- Blender 5.2.1 LTS, EEVEE Next, 192 TAA samples, AgX/Punchy, exposure +0.55
- The `.blend`'s authored studio lights and `Environment` collection are
  suppressed; a 4-light rig is re-solved per camera so every azimuth is lit
  the same way.
- `film_transparent` is on — plates ship with alpha, and `flat/` holds the same
  plates flattened onto the reference's `#F1F1F1` studio grey.
- Framing is auto-fit: 33,340 sampled world-space vertices are projected through
  the camera and the distance (or `ortho_scale`) is solved until the silhouette
  fits with a fixed margin, so all plates are consistently sized.

## Plates
| File | Type | Content |
| :--- | :--- | :--- |
| `tei_pd170_render_front_ortho.png` | 2048² ortho | Reduction snout, prop hub flange, governor block |
| `tei_pd170_render_rear_ortho.png` | 2048² ortho | Flywheel housing, starter interface, mount isolators |
| `tei_pd170_render_turboside_ortho.png` | 2048² ortho | Two-stage sequential turbos, wastegate, exhaust, sump |
| `tei_pd170_render_accessoryside_ortho.png` | 2048² ortho | Stacked 28V alternators, drive pulleys, filters |
| `tei_pd170_render_top_ortho.png` | 2048² ortho | Common rail spine, injector hard lines, harness |
| `tei_pd170_render_three_quarter_hero.png` | 1920×1080 | Hero 3/4, 85 mm |
| `tei_pd170_render_turbo_hero.png` | 1920×1080 | Turbo-side hero, 85 mm |
| `tei_pd170_render_accessory_hero.png` | 1920×1080 | Accessory-side hero, 85 mm |

## Sheets
- `tei_pd170_render_turnaround_sheet.jpg` — 4-view, mirrors the reference turnaround layout
- `tei_pd170_render_rear_top_sheet.jpg` — 3-view rear / top / turbo hero
- `tei_pd170_render_vs_reference.jpg` — reference over render, same four angles

## Two deviations from the reference, both in the asset rather than the render

1. **Handedness is mirrored.** The reference calls the turbo bank the *left*
   side and the alternator bank the *right*. In `tei_pd170.blend` the turbos sit
   at **+X** and the alternators at **−X**, i.e. the opposite hand. Plates are
   therefore named by content (`turboside` / `accessoryside`) rather than by
   left/right, so nothing is silently mislabelled. Fixing this means mirroring
   the asset, not re-shooting.

2. **The materials carry almost none of the reference's colour story.** The
   reference shows royal-blue silicone hoses, saturated yellow alternator
   housings, a yellow common-rail bracket, a red anodised wastegate actuator and
   braided lines. The model renders as near-monochrome cast aluminium with pale
   yellow accents. Geometry, proportion and component placement match well —
   shading does not. This is a material-authoring gap in the `.blend`; the
   comparison sheet is the clearest view of it.
