"""
Applies object scale to Copernicus DEM terrain in Models/terrain.blend.
Normalizes the 100,000:1 non-uniform scale matrix to (1.0, 1.0, 1.0),
eliminating normal inversion singularities and permanently removing
the black diamond/hexagon spots from the terrain.
"""

import bpy
import mathutils
import os

def apply_scale_fix():
    scene = bpy.context.scene
    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        print("[ERROR] Terrain object not found!")
        return

    print("Before fix - Object scale:", obj.scale)
    print("Before fix - Dimensions:", obj.dimensions)

    # Select object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Apply Object Scale -> (1.0, 1.0, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    print("After fix - Object scale:", obj.scale)
    print("After fix - Dimensions:", obj.dimensions)

    # Ensure smooth shading on all polygons
    mesh = obj.data
    for p in mesh.polygons:
        p.use_smooth = True

    # Re-evaluate mesh normals
    mesh.update()

    # Configure EEVEE settings to prevent shadow/raytracing acne
    scene.eevee.use_fast_gi = False
    scene.eevee.use_raytracing = False

    # Render verification frame
    out_p = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/scale_fixed_terrain.png"))
    scene.render.filepath = out_p
    print(f"[RENDER] Rendering scale-fixed verification to: {out_p}...")
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    # Also overwrite master final render
    master_p = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_p
    bpy.ops.render.render(write_still=True)

    # Save permanently to Models/terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved scale-fixed terrain permanently to Models/terrain.blend!")

if __name__ == "__main__":
    apply_scale_fix()
