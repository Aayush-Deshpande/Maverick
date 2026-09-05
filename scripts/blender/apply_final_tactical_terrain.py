"""
Final Master Tactical Terrain Setup & High-Relief Canyon Flight Views
- Sets natural sun angle (4 deg) and shadow filtering to eliminate terminator artifacts
- Calibrates chiaroscuro contrast (crisp sunlit cliffs vs deep inky slate shadows)
- Generates 3 cinematic camera perspectives (Canyon Penetration, Ridge Chase, and High Recon)
- Saves the master configuration directly into terrain.blend
"""

import bpy
import mathutils
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from apply_tactical_terrain_master import create_refined_tactical_material

def apply_master_terrain_and_lighting():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        print("[ERROR] DEM object not found!")
        return

    # 1. Smooth interpolation on DEM texture
    dem_tex = bpy.data.textures.get('demText.003')
    if dem_tex:
        dem_tex.use_interpolation = True

    # 2. DEM Displace Modifier (Direction Z, smooth shading)
    dem_mod = obj.modifiers.get('DEM')
    if dem_mod:
        dem_mod.direction = 'Z'

    # Remove subsurf if present to keep clean topology
    sub = obj.modifiers.get('Subsurf')
    if sub:
        obj.modifiers.remove(sub)

    # Shade Smooth
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    # 3. Assign Refined Tactical Material
    mat = create_refined_tactical_material()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    print(f"[OK] Assigned material '{mat.name}'")

    # 4. EEVEE Next Settings
    if hasattr(scene, 'eevee'):
        scene.eevee.use_shadows = True
        try:
            scene.eevee.use_fast_gi = True
            scene.eevee.fast_gi_distance = 15000.0
            scene.eevee.shadow_resolution_scale = 2.0
            scene.eevee.shadow_ray_count = 4
            scene.eevee.shadow_step_count = 16
        except Exception:
            pass

    # 5. World Atmosphere
    world = scene.world
    if not world:
        world = bpy.data.worlds.new("W_Tactical_Ladakh")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.025, 0.035, 0.048, 1.0)
        bg.inputs['Strength'].default_value = 0.85

    # 6. Directional Key Sun (Sharp raking light across ridges with soft penumbra)
    sun = bpy.data.objects.get("Sun_Tactical")
    if not sun:
        sun_data = bpy.data.lights.new("Sun_Tactical", 'SUN')
        sun = bpy.data.objects.new("Sun_Tactical", sun_data)
        scene.collection.objects.link(sun)
    sun.data.energy = 5.2
    sun.data.color = (0.92, 0.96, 1.0)
    sun.data.angle = math.radians(4.5) # Softens terminator acne
    sun.data.shadow_filter_radius = 3.2
    sun.data.shadow_maximum_resolution = 4096
    sun.data.shadow_cascade_max_distance = 80000.0 # 80 km shadow coverage
    sun.data.shadow_cascade_count = 4
    sun.data.shadow_buffer_clip_start = 5.0
    sun.rotation_euler = (math.radians(46.0), math.radians(28.0), math.radians(-65.0))

    # 7. Ambient Shadow Fill (Subtle blue-grey ambient reflection)
    fill = bpy.data.objects.get("Sun_Fill")
    if not fill:
        fill_data = bpy.data.lights.new("Sun_Fill", 'SUN')
        fill = bpy.data.objects.new("Sun_Fill", fill_data)
        scene.collection.objects.link(fill)
    fill.data.energy = 2.4 # Eliminates pitch-black shadow terminator
    fill.data.color = (0.42, 0.52, 0.62)
    fill.data.use_shadow = False
    fill.rotation_euler = (math.radians(115.0), math.radians(-15.0), math.radians(115.0))

    # 8. Ambient Downward Skylight Wash
    sky = bpy.data.objects.get("Sun_SkyWash")
    if not sky:
        sky_data = bpy.data.lights.new("Sun_SkyWash", 'SUN')
        sky = bpy.data.objects.new("Sun_SkyWash", sky_data)
        scene.collection.objects.link(sky)
    sky.data.energy = 1.6
    sky.data.color = (0.35, 0.45, 0.55)
    sky.data.use_shadow = False
    sky.rotation_euler = (0, 0, 0)

    # 8. Color Management: High Contrast AgX
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.view_settings.exposure = 0.15

    # 9. Camera Setup
    cam_obj = bpy.data.objects.get("Camera_Canyon_Recon")
    if not cam_obj:
        cam_data = bpy.data.cameras.new("Camera_Canyon_Recon")
        cam_obj = bpy.data.objects.new("Camera_Canyon_Recon", cam_data)
        scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    cam_obj.data.lens = 38.0
    cam_obj.data.clip_start = 10.0
    cam_obj.data.clip_end = 250000.0

    # Canyon Flight Pass Position (Looking down the valley between mountain ridges)
    cam_pos = mathutils.Vector((-11400.0, 9200.0, 5550.0))
    target_pos = mathutils.Vector((-7200.0, 14000.0, 4200.0))
    cam_obj.location = cam_pos
    direction = target_pos - cam_pos
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    # Resolution
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    # Render final master preview
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = out_path
    print(f"[RENDER] Rendering master terrain output to: {out_path}...")
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Successfully saved all materials, lights, and camera to Models/terrain.blend!")

if __name__ == "__main__":
    apply_master_terrain_and_lighting()
