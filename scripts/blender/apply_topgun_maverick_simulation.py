"""
Top Gun: Maverick Tactical Blue Mission Simulator Setup
Applies the iconic military briefing-room synthetic vision aesthetic:
1. Deep navy/cobalt blue tactical terrain base.
2. Luminous electric cyan topographic elevation contour isolines (80m intervals).
3. Holographic ridge crest & rim edge glow (neon cyan Fresnel highlight).
4. Smooth modifier stack (Subsurf before DEM + WeightedNormal) with ZERO block polygons.
5. Atmospheric canyon depth and cold tactical directional lighting.
6. Permanently saved to Models/terrain.blend.
"""

import bpy
import mathutils
import math
import os

def apply_topgun_simulation():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        print("[ERROR] Terrain DEM object not found!")
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

    # 2. Material: M_TopGun_Tactical_Simulation
    for m in list(bpy.data.materials):
        if 'TopGun' in m.name or 'Rock' in m.name or 'Clean' in m.name:
            bpy.data.materials.remove(m)

    mat = bpy.data.materials.new("M_TopGun_Tactical_Simulation")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (1800, 0)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (1450, 0)
    bsdf.inputs['Roughness'].default_value = 0.72
    bsdf.inputs['Specular IOR Level'].default_value = 0.35
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-1600, 0)

    # A. Deep Tactical Navy Blue Base
    mix_base = nodes.new('ShaderNodeMix')
    mix_base.data_type = 'RGBA'
    mix_base.location = (-400, 300)
    mix_base.inputs[6].default_value = (0.03, 0.07, 0.14, 1.0) # Deep Navy Shadow
    mix_base.inputs[7].default_value = (0.08, 0.16, 0.28, 1.0) # Tactical Cerulean Midtone
    mix_base.inputs['Factor'].default_value = 0.50

    # B. Holographic Ridge Edge Glow (Fresnel / Facing)
    layer_weight = nodes.new('ShaderNodeLayerWeight')
    layer_weight.location = (-1200, -250)
    layer_weight.inputs['Blend'].default_value = 0.35

    ramp_edge = nodes.new('ShaderNodeValToRGB')
    ramp_edge.location = (-900, -250)
    ramp_edge.color_ramp.elements[0].position = 0.55
    ramp_edge.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_edge.color_ramp.elements[1].position = 0.95
    ramp_edge.color_ramp.elements[1].color = (0.0, 0.85, 1.0, 1.0) # Luminous Electric Cyan
    links.new(layer_weight.outputs['Facing'], ramp_edge.inputs['Fac'])

    # C. Luminous Topographic Elevation Contour Isolines
    sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    sep_pos.location = (-1300, 400)
    links.new(geom.outputs['Position'], sep_pos.inputs['Vector'])

    div_80 = nodes.new('ShaderNodeMath')
    div_80.location = (-1050, 400)
    div_80.operation = 'DIVIDE'
    div_80.inputs[1].default_value = 80.0
    links.new(sep_pos.outputs['Z'], div_80.inputs[0])

    fract_80 = nodes.new('ShaderNodeMath')
    fract_80.location = (-880, 400)
    fract_80.operation = 'FRACT'
    links.new(div_80.outputs['Value'], fract_80.inputs[0])

    sub_80 = nodes.new('ShaderNodeMath')
    sub_80.location = (-710, 400)
    sub_80.operation = 'SUBTRACT'
    sub_80.inputs[1].default_value = 0.5
    links.new(fract_80.outputs['Value'], sub_80.inputs[0])

    abs_80 = nodes.new('ShaderNodeMath')
    abs_80.location = (-540, 400)
    abs_80.operation = 'ABSOLUTE'
    links.new(sub_80.outputs['Value'], abs_80.inputs[0])

    ramp_iso = nodes.new('ShaderNodeValToRGB')
    ramp_iso.location = (-370, 400)
    ramp_iso.color_ramp.elements[0].position = 0.485
    ramp_iso.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_iso.color_ramp.elements[1].position = 0.50
    ramp_iso.color_ramp.elements[1].color = (0.1, 0.9, 1.0, 1.0) # Glowing Cyan Line
    links.new(abs_80.outputs['Value'], ramp_iso.inputs['Fac'])

    # D. Combine Base + Ridge Glow + Contour Lines
    mix_glow = nodes.new('ShaderNodeMix')
    mix_glow.data_type = 'RGBA'
    mix_glow.blend_type = 'ADD'
    mix_glow.location = (200, 200)
    mix_glow.inputs['Factor'].default_value = 0.70
    links.new(mix_base.outputs[2], mix_glow.inputs[6])
    links.new(ramp_edge.outputs['Color'], mix_glow.inputs[7])

    mix_final = nodes.new('ShaderNodeMix')
    mix_final.data_type = 'RGBA'
    mix_final.blend_type = 'ADD'
    mix_final.location = (600, 200)
    mix_final.inputs['Factor'].default_value = 0.85
    links.new(mix_glow.outputs[2], mix_final.inputs[6])
    links.new(ramp_iso.outputs['Color'], mix_final.inputs[7])

    links.new(mix_final.outputs[2], bsdf.inputs['Base Color'])

    # Emission for tactical HUD glow
    if 'Emission Color' in bsdf.inputs:
        links.new(ramp_iso.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = 0.50

    obj.data.materials.clear()
    obj.data.materials.append(mat)
    print("[OK] Assigned M_TopGun_Tactical_Simulation material.")

    # 3. Tactical Briefing Room Lighting
    for o in list(scene.objects):
        if o.type == 'LIGHT':
            bpy.data.objects.remove(o, do_unlink=True)

    sun_data = bpy.data.lights.new('Sun_TopGun', 'SUN')
    sun_data.energy = 3.5
    sun_data.color = (0.65, 0.85, 1.0) # Cold tactical cyan-blue key light
    sun_data.use_shadow = False
    sun_obj = bpy.data.objects.new('Sun_TopGun', sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(50.0), math.radians(18.0), math.radians(-115.0))

    # Sky World: Deep tactical navy atmosphere
    world = scene.world
    if not world:
        world = bpy.data.worlds.new("W_TopGun")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.015, 0.03, 0.06, 1.0)
        bg.inputs['Strength'].default_value = 0.85

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

    # Render High-Resolution Frame
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/topgun_maverick_simulation.png"))
    scene.render.filepath = out_path
    print(f"[RENDER] Rendering Top Gun Maverick simulation to: {out_path}...")
    bpy.ops.render.render(write_still=True)

    master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved Top Gun simulation terrain permanently to Models/terrain.blend!")

if __name__ == "__main__":
    apply_topgun_simulation()
