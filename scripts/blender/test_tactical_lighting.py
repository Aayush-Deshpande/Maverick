"""
Canyon Recon View Angle Finder & Lighting Balancer
Tests lighting with Fast GI + 3-point fill to ensure shadow faces are dark slate,
and tests camera framing down the canyon.
"""

import bpy
import mathutils
import math
import os

import sys
sys.path.insert(0, os.path.dirname(__file__))

def setup_perfect_tactical_lighting():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    # EEVEE Fast GI (Ambient Light Bounces into Shadows)
    if hasattr(scene, 'eevee'):
        scene.eevee.use_shadows = True
        try:
            scene.eevee.use_fast_gi = True
            scene.eevee.fast_gi_distance = 15000.0 # 15km ambient bounce
        except Exception as e:
            pass

    # World: Atmospheric Navy/Slate
    world = scene.world
    if not world:
        world = bpy.data.worlds.new("W_Tactical")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.05, 0.07, 0.10, 1.0) # Cool ambient sky
        bg.inputs['Strength'].default_value = 1.4

    # 1. Key Sun (Upper right, raking across ridges)
    sun = bpy.data.objects.get("Sun_Tactical")
    if not sun:
        sun_data = bpy.data.lights.new("Sun_Tactical", 'SUN')
        sun = bpy.data.objects.new("Sun_Tactical", sun_data)
        scene.collection.objects.link(sun)
    sun.data.energy = 4.5
    sun.data.color = (0.92, 0.96, 1.0)
    sun.data.angle = math.radians(1.5)
    sun.data.shadow_cascade_max_distance = 75000.0
    sun.rotation_euler = (math.radians(45.0), math.radians(30.0), math.radians(-60.0))

    # 2. Shadow Fill Sun (Opposite side, fills shadows with slate tone)
    fill = bpy.data.objects.get("Sun_Fill")
    if not fill:
        fill_data = bpy.data.lights.new("Sun_Fill", 'SUN')
        fill = bpy.data.objects.new("Sun_Fill", fill_data)
        scene.collection.objects.link(fill)
    fill.data.energy = 1.6
    fill.data.color = (0.42, 0.52, 0.62) # Cool slate shadow fill
    fill.data.use_shadow = False # Diffuse bounce without hard secondary shadows
    fill.rotation_euler = (math.radians(120.0), math.radians(-20.0), math.radians(110.0))

    # 3. Top Ambient Skylight (Downward soft cool wash)
    sky_light = bpy.data.objects.get("Sun_SkyWash")
    if not sky_light:
        sky_data = bpy.data.lights.new("Sun_SkyWash", 'SUN')
        sky_light = bpy.data.objects.new("Sun_SkyWash", sky_data)
        scene.collection.objects.link(sky_light)
    sky_light.data.energy = 1.2
    sky_light.data.color = (0.35, 0.45, 0.55)
    sky_light.data.use_shadow = False
    sky_light.rotation_euler = (0, 0, 0) # Straight down

    # AgX Color Management
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.view_settings.exposure = 0.05

def render_view_test(cam_pos, target_pos, filename):
    scene = bpy.context.scene
    cam_obj = bpy.data.objects.get("Camera_Canyon_Recon")
    if not cam_obj:
        cam_data = bpy.data.cameras.new("Camera_Canyon_Recon")
        cam_obj = bpy.data.objects.new("Camera_Canyon_Recon", cam_data)
        scene.collection.objects.link(cam_obj)
    
    scene.camera = cam_obj
    cam_obj.data.lens = 38.0
    cam_obj.data.clip_start = 10.0
    cam_obj.data.clip_end = 250000.0

    cam_obj.location = cam_pos
    direction = target_pos - cam_pos
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../renders/{filename}"))
    scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    setup_perfect_tactical_lighting()
    
    # Let's restore the refined tactical material
    from apply_tactical_terrain_master import create_refined_tactical_material
    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if obj:
        mat = create_refined_tactical_material()
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
        # Apply Shade Smooth
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth()

    # Camera looking along canyon corridor
    # View 1: Looking down canyon from high ridge
    render_view_test(
        cam_pos=mathutils.Vector((-11200.0, 9600.0, 5700.0)),
        target_pos=mathutils.Vector((-6800.0, 14500.0, 4250.0)),
        filename="tactical_canyon_view1.png"
    )
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved terrain.blend with balanced tactical lighting and shader!")
