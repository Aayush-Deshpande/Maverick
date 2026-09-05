"""
Clean, Pure Tactical Digital Twin Terrain
Removes all rock noise, procedural crags, bump nodes, and dark patches.
Keeps the terrain sleek, smooth, and clean with pure topographic elevation isolines.
"""

import bpy
import mathutils
import math
import os

def create_pure_clean_material():
    mat = bpy.data.materials.get("M_Tactical_Ladakh_Terrain")
    if not mat:
        mat = bpy.data.materials.new("M_Tactical_Ladakh_Terrain")
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # 1. Material Output
    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (1200, 200)

    # 2. Principled BSDF - Clean, uniform slate surface
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (850, 200)
    bsdf.inputs['Roughness'].default_value = 0.82
    bsdf.inputs['Specular IOR Level'].default_value = 0.30
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    # 3. Geometry Position for Topographic Elevation Isolines
    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-800, 200)

    sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    sep_pos.location = (-550, 200)
    links.new(geom.outputs['Position'], sep_pos.inputs['Vector'])

    # 80-meter clean elevation isolines
    div_iso = nodes.new('ShaderNodeMath')
    div_iso.location = (-350, 200)
    div_iso.operation = 'DIVIDE'
    div_iso.inputs[1].default_value = 80.0
    links.new(sep_pos.outputs['Z'], div_iso.inputs[0])

    fract_iso = nodes.new('ShaderNodeMath')
    fract_iso.location = (-180, 200)
    fract_iso.operation = 'FRACT'
    links.new(div_iso.outputs['Value'], fract_iso.inputs[0])

    sub_iso = nodes.new('ShaderNodeMath')
    sub_iso.location = (-10, 200)
    sub_iso.operation = 'SUBTRACT'
    sub_iso.inputs[1].default_value = 0.5
    links.new(fract_iso.outputs['Value'], sub_iso.inputs[0])

    abs_iso = nodes.new('ShaderNodeMath')
    abs_iso.location = (150, 200)
    abs_iso.operation = 'ABSOLUTE'
    links.new(sub_iso.outputs['Value'], abs_iso.inputs[0])

    # Hairline clean isoline ramp
    ramp_iso = nodes.new('ShaderNodeValToRGB')
    ramp_iso.location = (320, 200)
    ramp_iso.color_ramp.elements[0].position = 0.486
    ramp_iso.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_iso.color_ramp.elements[1].position = 0.50
    ramp_iso.color_ramp.elements[1].color = (0.60, 0.75, 0.88, 1.0) # Clean tactical cyan-white line
    links.new(abs_iso.outputs['Value'], ramp_iso.inputs['Fac'])

    # 4. Clean Base Slate Color + Isolines (Zero noise, zero dark spots)
    mix_color = nodes.new('ShaderNodeMix')
    mix_color.data_type = 'RGBA'
    mix_color.blend_type = 'ADD'
    mix_color.location = (600, 200)
    # Sleek, uniform military slate base color
    mix_color.inputs[6].default_value = (0.19, 0.23, 0.28, 1.0)
    mix_color.inputs['Factor'].default_value = 0.45
    links.new(ramp_iso.outputs['Color'], mix_color.inputs[7])

    links.new(mix_color.outputs[2], bsdf.inputs['Base Color'])

    return mat

def apply_clean_pure_scene():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        print("[ERROR] Terrain DEM object not found!")
        return

    # 1. Texture interpolation & anti-aliasing
    dem_tex = bpy.data.textures.get('demText.003')
    if dem_tex:
        dem_tex.use_interpolation = True
        dem_tex.filter_size = 3.5

    # 2. Modifiers: DEM Displace + Smooth Subdivision
    dem_mod = obj.modifiers.get('DEM')
    if dem_mod:
        dem_mod.direction = 'Z'

    sub = obj.modifiers.get('Subsurf_Smooth')
    if not sub:
        sub = obj.modifiers.new(name='Subsurf_Smooth', type='SUBSURF')
    sub.subdivision_type = 'CATMULL_CLARK'
    sub.levels = 1
    sub.render_levels = 1

    for m in list(obj.modifiers):
        if m.name not in ['DEM', 'Subsurf_Smooth']:
            obj.modifiers.remove(m)

    for p in obj.data.polygons:
        p.use_smooth = True

    # 3. Clean up any temporary HUD overlays
    col = bpy.data.collections.get('HUD_Tactical_Overlays')
    if col:
        for o in list(col.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(col)

    # 4. Assign Pure Clean Material
    mat = create_pure_clean_material()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    print(f"[OK] Material '{mat.name}' configured with zero noise, zero rocks, zero black spots.")

    # 5. Candidate 1 Camera Framing
    cam_obj = bpy.data.objects.get("Camera_Canyon_Recon")
    if not cam_obj:
        cam_data = bpy.data.cameras.new("Camera_Canyon_Recon")
        cam_obj = bpy.data.objects.new("Camera_Canyon_Recon", cam_data)
        scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    cam_obj.data.lens = 38.0
    cam_obj.data.clip_start = 10.0
    cam_obj.data.clip_end = 250000.0

    cam_pos = mathutils.Vector((-16000.0, 10000.0, 6800.0))
    target_pos = mathutils.Vector((-10000.0, 16000.0, 3600.0))
    cam_obj.location = cam_pos
    direction = target_pos - cam_pos
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    # 6. Clean Lighting
    sun = bpy.data.objects.get("Sun_Tactical")
    if not sun:
        sun_data = bpy.data.lights.new("Sun_Tactical", 'SUN')
        sun = bpy.data.objects.new("Sun_Tactical", sun_data)
        scene.collection.objects.link(sun)
    sun.data.energy = 5.5
    sun.data.color = (0.92, 0.96, 1.0)
    sun.data.use_shadow = False
    sun.rotation_euler = (math.radians(52.0), math.radians(24.0), math.radians(-70.0))

    fill = bpy.data.objects.get("Sun_Fill")
    if not fill:
        fill_data = bpy.data.lights.new("Sun_Fill", 'SUN')
        fill = bpy.data.objects.new("Sun_Fill", fill_data)
        scene.collection.objects.link(fill)
    fill.data.energy = 1.6
    fill.data.color = (0.30, 0.38, 0.48)
    fill.data.use_shadow = False
    fill.rotation_euler = (math.radians(110.0), math.radians(-20.0), math.radians(110.0))

    world = scene.world
    if not world:
        world = bpy.data.worlds.new("W_Tactical")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.015, 0.022, 0.030, 1.0)
        bg.inputs['Strength'].default_value = 0.70

    # AgX High Contrast
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.view_settings.exposure = 0.12

    # Viewport configuration
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'RENDERED'
                        space.region_3d.view_perspective = 'CAMERA'

    # Render High-Resolution Frame
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/clean_pure_terrain.png"))
    scene.render.filepath = out_path
    print(f"[RENDER] Rendering clean pure terrain to: {out_path}...")
    bpy.ops.render.render(write_still=True)

    master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved clean terrain.blend successfully!")

if __name__ == "__main__":
    apply_clean_pure_scene()
