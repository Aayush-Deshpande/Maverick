"""
Applies the natural slate rock aesthetic matching the user reference:
1. Preserves the clean modifier stack (Subsurf before DEM + WeightedNormal) with ZERO block polygons.
2. Natural slate-grey rock base with diagonal strata striations and subtle mineral veins.
3. Soft studio illumination and ambient fill with zero harsh pitch-black shadow clamps.
4. Candidate 1 canyon camera framing.
5. Permanently saved to Models/terrain.blend.
"""

import bpy
import mathutils
import math
import os

def apply_final_rock_look():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        print("[ERROR] Terrain object not found!")
        return

    # Select object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # 1. Modifiers: Subsurf (Simple) -> DEM (Displace) -> WeightedNormal
    sub = obj.modifiers.get('Subsurf_Smooth')
    if not sub:
        sub = obj.modifiers.new(name='Subsurf_Smooth', type='SUBSURF')
    sub.subdivision_type = 'SIMPLE'
    sub.levels = 1
    sub.render_levels = 1
    bpy.ops.object.modifier_move_to_index(modifier='Subsurf_Smooth', index=0)

    dem_mod = obj.modifiers.get('DEM')
    if dem_mod:
        dem_mod.direction = 'Z'
        dem_mod.strength = 1.0

    wn = obj.modifiers.get('Weighted_Normal')
    if not wn:
        wn = obj.modifiers.new(name='Weighted_Normal', type='WEIGHTED_NORMAL')
    wn.weight = 50
    wn.keep_sharp = False

    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.update()

    # 2. Material: M_Terrain_Rock_Look
    for m in list(bpy.data.materials):
        if 'Clean' in m.name or 'Tactical' in m.name:
            bpy.data.materials.remove(m)

    mat = bpy.data.materials.new("M_Terrain_Rock_Look")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (1600, 0)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (1250, 0)
    bsdf.inputs['Roughness'].default_value = 0.88
    bsdf.inputs['Specular IOR Level'].default_value = 0.18
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    # UV Texture Coordinates
    tex_coord = nodes.new('ShaderNodeTexCoord')
    tex_coord.location = (-1500, 200)

    # Macro Rock Strata
    map_strata = nodes.new('ShaderNodeMapping')
    map_strata.location = (-1200, 400)
    map_strata.inputs['Scale'].default_value = (60.0, 180.0, 1.0)
    map_strata.inputs['Rotation'].default_value = (0.0, 0.0, math.radians(35.0))
    links.new(tex_coord.outputs['UV'], map_strata.inputs['Vector'])

    noise_strata = nodes.new('ShaderNodeTexNoise')
    noise_strata.location = (-900, 400)
    noise_strata.inputs['Scale'].default_value = 1.0
    noise_strata.inputs['Detail'].default_value = 10.0
    noise_strata.inputs['Roughness'].default_value = 0.70
    links.new(map_strata.outputs['Vector'], noise_strata.inputs['Vector'])

    # Fine Rock Grain
    map_grain = nodes.new('ShaderNodeMapping')
    map_grain.location = (-1200, 0)
    map_grain.inputs['Scale'].default_value = (240.0, 240.0, 1.0)
    links.new(tex_coord.outputs['UV'], map_grain.inputs['Vector'])

    noise_grain = nodes.new('ShaderNodeTexNoise')
    noise_grain.location = (-900, 0)
    noise_grain.inputs['Scale'].default_value = 1.0
    noise_grain.inputs['Detail'].default_value = 8.0
    noise_grain.inputs['Roughness'].default_value = 0.75
    links.new(map_grain.outputs['Vector'], noise_grain.inputs['Vector'])

    # Mix Strata and Grain
    mix_noise = nodes.new('ShaderNodeMix')
    mix_noise.data_type = 'FLOAT'
    mix_noise.location = (-600, 200)
    mix_noise.inputs['Factor'].default_value = 0.55
    links.new(noise_strata.outputs['Fac'], mix_noise.inputs[2])
    links.new(noise_grain.outputs['Fac'], mix_noise.inputs[3])

    # Color Ramp
    ramp_color = nodes.new('ShaderNodeValToRGB')
    ramp_color.location = (-300, 200)
    ramp_color.color_ramp.elements[0].position = 0.20
    ramp_color.color_ramp.elements[0].color = (0.24, 0.28, 0.32, 1.0) # Deep crevice
    ramp_color.color_ramp.elements[1].position = 0.58
    ramp_color.color_ramp.elements[1].color = (0.45, 0.50, 0.55, 1.0) # Slate rock midtone
    elem_vein = ramp_color.color_ramp.elements.new(0.85)
    elem_vein.color = (0.75, 0.80, 0.85, 1.0) # White chalk/strata vein
    links.new(mix_noise.outputs[0], ramp_color.inputs['Fac'])

    links.new(ramp_color.outputs['Color'], bsdf.inputs['Base Color'])

    obj.data.materials.clear()
    obj.data.materials.append(mat)
    print("[OK] Assigned M_Terrain_Rock_Look material.")

    # 3. Soft Studio Lighting
    sun = bpy.data.objects.get('Studio_Light')
    if not sun:
        sun_data = bpy.data.lights.new('Studio_Light', 'SUN')
        sun = bpy.data.objects.new('Studio_Light', sun_data)
        scene.collection.objects.link(sun)
    sun.data.energy = 1.8
    sun.data.color = (1.0, 1.0, 1.0)
    sun.data.use_shadow = False
    sun.rotation_euler = (math.radians(52.0), math.radians(20.0), math.radians(-65.0))

    # Ambient Sky
    world = scene.world
    if not world:
        world = bpy.data.worlds.new("W_Rock_Look")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.60, 0.65, 0.70, 1.0)
        bg.inputs['Strength'].default_value = 0.90

    # 4. Camera (Candidate 1 Canyon Recon)
    cam = bpy.data.objects.get('Camera_Canyon_Recon')
    if cam:
        cam.location = mathutils.Vector((-16000.0, 10000.0, 6800.0))
        cam_target = mathutils.Vector((-10000.0, 16000.0, 3600.0))
        dir_vec = cam_target - cam.location
        rot_quat = dir_vec.to_track_quat('-Z', 'Y')
        cam.rotation_euler = rot_quat.to_euler()
        cam.data.lens = 38.0
        scene.camera = cam

    # Viewport configuration
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'RENDERED'
                        space.region_3d.view_perspective = 'CAMERA'

    # Render High-Resolution Outputs
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/rock_reference_final.png"))
    scene.render.filepath = out_path
    print(f"[RENDER] Rendering rock reference final to: {out_path}...")
    bpy.ops.render.render(write_still=True)

    master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved rock reference terrain permanently to Models/terrain.blend!")

if __name__ == "__main__":
    apply_final_rock_look()
