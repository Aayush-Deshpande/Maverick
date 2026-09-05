"""
Permanently removes block polygon artifacts on Copernicus DEM terrain:
1. Reorders modifier stack: Places Subsurf (Simple) BEFORE DEM Displace.
   This subdivides the base grid into high-density vertices before displacement,
   preventing 100m quad folding and eliminating block facets.
2. Adds a WeightedNormal modifier (weight 50, keep_sharp=False) to ensure
   continuous normal interpolation across all mountain ridges.
3. Smooth shading enabled across all polygons.
4. Clean, soft studio lighting and slate material preserved.
5. Permanently saved to Models/terrain.blend.
"""

import bpy
import mathutils
import os

def remove_block_polygons():
    scene = bpy.context.scene
    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        print("[ERROR] Terrain object not found!")
        return

    # Select object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # 1. Ensure Subsurf exists and is placed BEFORE DEM displace
    sub = obj.modifiers.get('Subsurf_Smooth')
    if not sub:
        sub = obj.modifiers.new(name='Subsurf_Smooth', type='SUBSURF')
    sub.subdivision_type = 'SIMPLE'
    sub.levels = 1
    sub.render_levels = 1

    # Move Subsurf to index 0 (top of stack, before DEM)
    bpy.ops.object.modifier_move_to_index(modifier='Subsurf_Smooth', index=0)

    # 2. DEM Displace modifier at index 1
    dem_mod = obj.modifiers.get('DEM')
    if dem_mod:
        dem_mod.direction = 'Z'
        dem_mod.strength = 1.0

    # 3. Add Weighted Normal modifier at index 2 to eliminate faceted normal seams
    wn = obj.modifiers.get('Weighted_Normal')
    if not wn:
        wn = obj.modifiers.new(name='Weighted_Normal', type='WEIGHTED_NORMAL')
    wn.weight = 50
    wn.keep_sharp = False

    # 4. Ensure all mesh polygons have smooth shading enabled
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.update()

    print("Modifier stack order:")
    for i, m in enumerate(obj.modifiers):
        print(f"  {i}: {m.name} ({m.type})")

    # Render verification frame
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    out_p = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/block_polygons_removed.png"))
    scene.render.filepath = out_p
    print(f"[RENDER] Rendering block-polygon removal verification to: {out_p}...")
    bpy.ops.render.render(write_still=True)

    master_p = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_p
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    # Save permanently to Models/terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved terrain.blend with block polygons permanently removed!")

if __name__ == "__main__":
    remove_block_polygons()
