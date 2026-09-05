"""
Adjusts Snow Coverage to ~30-35% (Peak Crests & Glacial Saddles only):
1. Raises Elevation Threshold to 0.72 (~6,300m AMSL) so only high mountain crests receive snow.
2. Raises Slope Threshold to 0.75 (< 41 deg slope) so steep mountain rock faces remain exposed.
3. Renders both chase and recon views to verify the rock, hillshade, and mountain textures are dominant.
"""

import bpy
import os

def adjust_snow(elev_thresh=0.72, slope_thresh=0.75):
    terrain = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not terrain or not terrain.material_slots:
        print("[ERROR] Terrain object not found!")
        return

    mat = terrain.material_slots[0].material
    nodes = mat.node_tree.nodes

    math_elev = nodes.get('Math_Elevation_Mask')
    if math_elev:
        math_elev.inputs[1].default_value = elev_thresh
        print(f"[OK] Elevation Threshold updated: {elev_thresh} (Only above ~{2925 + elev_thresh * 4691:.0f}m)")

    math_slope = nodes.get('Math_Slope_Mask')
    if math_slope:
        math_slope.inputs[1].default_value = slope_thresh
        print(f"[OK] Slope Threshold updated: {slope_thresh} (Only slopes < 41 deg)")

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved updated snow thresholds to Models/terrain.blend!")

    # Render Verification Frames
    scene = bpy.context.scene
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080

    # 1. Recon Overview
    cam_recon = bpy.data.objects.get('Camera_Canyon_Recon')
    if cam_recon:
        scene.camera = cam_recon
        out_recon = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/snow_coverage_recon.png"))
        scene.render.filepath = out_recon
        print(f"Rendering recon overview to: {out_recon}...")
        bpy.ops.render.render(write_still=True)

    # 2. Chase View
    scene.frame_set(550)
    cam_chase = bpy.data.objects.get('Camera_UAV_Chase')
    if cam_chase:
        scene.camera = cam_chase
        out_chase = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/snow_coverage_chase.png"))
        scene.render.filepath = out_chase
        print(f"Rendering chase view to: {out_chase}...")
        bpy.ops.render.render(write_still=True)

    print("[OK] Snow coverage test renders complete!")

if __name__ == "__main__":
    adjust_snow(elev_thresh=0.72, slope_thresh=0.75)
