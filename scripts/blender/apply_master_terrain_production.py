"""
Production Master Tactical Terrain Setup
- Completely eliminates Virtual Shadow Map page dropouts (the diamond/pixel artifacts)
- Smooth, continuous high-relief Himalayan mountain slopes with zero faceted polygons
- Delicate, hairline cyan-white topographic contour isolines (120m intervals)
- Authentic gunmetal/slate rock palette with fine erosion fluting
- Atmospheric depth haze fading into dark navy-slate horizon
- Pre-configured camera view and rendered viewport in Models/terrain.blend
"""

import bpy
import mathutils
import math
import os

def create_master_smooth_tactical_material():
    mat = bpy.data.materials.get("M_Tactical_Ladakh_Terrain")
    if not mat:
        mat = bpy.data.materials.new("M_Tactical_Ladakh_Terrain")
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # 1. Output & Principled BSDF
    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (2200, 200)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (1850, 200)
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Specular IOR Level'].default_value = 0.30
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-1600, 0)

    cam_data = nodes.new('ShaderNodeCameraData')
    cam_data.location = (-1600, -800)

    # -------------------------------------------------------------
    # 2. FINE PROCEDURAL ROCK GRAIN & VERTICAL STRATA BUMP
    # -------------------------------------------------------------
    # Macro vertical rock fluting (stretched along Z)
    map_strata = nodes.new('ShaderNodeMapping')
    map_strata.location = (-1300, 500)
    map_strata.inputs['Scale'].default_value = (0.0025, 0.0025, 0.0006)
    links.new(geom.outputs['Position'], map_strata.inputs['Vector'])

    noise_strata = nodes.new('ShaderNodeTexNoise')
    noise_strata.location = (-1050, 500)
    noise_strata.inputs['Scale'].default_value = 1.0
    noise_strata.inputs['Detail'].default_value = 10.0
    noise_strata.inputs['Roughness'].default_value = 0.70
    noise_strata.inputs['Lacunarity'].default_value = 2.0
    noise_strata.inputs['Distortion'].default_value = 0.4
    links.new(map_strata.outputs['Vector'], noise_strata.inputs['Vector'])

    # Micro surface grain
    map_grain = nodes.new('ShaderNodeMapping')
    map_grain.location = (-1300, 150)
    map_grain.inputs['Scale'].default_value = (0.035, 0.035, 0.035)
    links.new(geom.outputs['Position'], map_grain.inputs['Vector'])

    noise_grain = nodes.new('ShaderNodeTexNoise')
    noise_grain.location = (-1050, 150)
    noise_grain.inputs['Scale'].default_value = 1.0
    noise_grain.inputs['Detail'].default_value = 6.0
    noise_grain.inputs['Roughness'].default_value = 0.80
    links.new(map_grain.outputs['Vector'], noise_grain.inputs['Vector'])

    # Calibrated Bump Chain (Subtle relief without geometric terminator clamping)
    bump_strata = nodes.new('ShaderNodeBump')
    bump_strata.location = (-700, 350)
    bump_strata.inputs['Strength'].default_value = 0.40
    bump_strata.inputs['Distance'].default_value = 2.5
    links.new(noise_strata.outputs['Fac'], bump_strata.inputs['Height'])

    bump_grain = nodes.new('ShaderNodeBump')
    bump_grain.location = (-450, 350)
    bump_grain.inputs['Strength'].default_value = 0.20
    bump_grain.inputs['Distance'].default_value = 0.8
    links.new(noise_grain.outputs['Fac'], bump_grain.inputs['Height'])
    links.new(bump_strata.outputs['Normal'], bump_grain.inputs['Normal'])

    links.new(bump_grain.outputs['Normal'], bsdf.inputs['Normal'])

    # -------------------------------------------------------------
    # 3. BASE ROCK PALETTE (Calibrated Slate & Charcoal)
    # -------------------------------------------------------------
    rock_ramp = nodes.new('ShaderNodeValToRGB')
    rock_ramp.location = (-700, 0)
    rock_ramp.color_ramp.elements[0].position = 0.22
    rock_ramp.color_ramp.elements[0].color = (0.10, 0.12, 0.15, 1.0) # Deep charcoal slate
    rock_ramp.color_ramp.elements[1].position = 0.58
    rock_ramp.color_ramp.elements[1].color = (0.20, 0.24, 0.28, 1.0) # Mountain slate grey
    elem_high = rock_ramp.color_ramp.elements.new(0.86)
    elem_high.color = (0.30, 0.36, 0.42, 1.0) # Weathered crest highlight
    links.new(noise_strata.outputs['Fac'], rock_ramp.inputs['Fac'])

    # -------------------------------------------------------------
    # 4. SUBTLE PRECISION TOPOGRAPHIC ISOLINES
    # -------------------------------------------------------------
    sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    sep_pos.location = (-700, -350)
    links.new(geom.outputs['Position'], sep_pos.inputs['Vector'])

    div_iso = nodes.new('ShaderNodeMath')
    div_iso.location = (-480, -350)
    div_iso.operation = 'DIVIDE'
    div_iso.inputs[1].default_value = 120.0
    links.new(sep_pos.outputs['Z'], div_iso.inputs[0])

    fract_iso = nodes.new('ShaderNodeMath')
    fract_iso.location = (-300, -350)
    fract_iso.operation = 'FRACT'
    links.new(div_iso.outputs['Value'], fract_iso.inputs[0])

    sub_iso = nodes.new('ShaderNodeMath')
    sub_iso.location = (-120, -350)
    sub_iso.operation = 'SUBTRACT'
    sub_iso.inputs[1].default_value = 0.5
    links.new(fract_iso.outputs['Value'], sub_iso.inputs[0])

    abs_iso = nodes.new('ShaderNodeMath')
    abs_iso.location = (60, -350)
    abs_iso.operation = 'ABSOLUTE'
    links.new(sub_iso.outputs['Value'], abs_iso.inputs[0])

    ramp_iso = nodes.new('ShaderNodeValToRGB')
    ramp_iso.location = (250, -350)
    ramp_iso.color_ramp.elements[0].position = 0.488
    ramp_iso.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_iso.color_ramp.elements[1].position = 0.50
    ramp_iso.color_ramp.elements[1].color = (0.50, 0.64, 0.76, 1.0) # Delicate cool isoline
    links.new(abs_iso.outputs['Value'], ramp_iso.inputs['Fac'])

    # Mix rock color with subtle isolines
    mix_rock_iso = nodes.new('ShaderNodeMix')
    mix_rock_iso.data_type = 'RGBA'
    mix_rock_iso.blend_type = 'ADD'
    mix_rock_iso.location = (550, 0)
    mix_rock_iso.inputs['Factor'].default_value = 0.32
    links.new(rock_ramp.outputs['Color'], mix_rock_iso.inputs[6])
    links.new(ramp_iso.outputs['Color'], mix_rock_iso.inputs[7])

    # -------------------------------------------------------------
    # 5. ATMOSPHERIC HORIZON DEPTH HAZE
    # -------------------------------------------------------------
    div_dist = nodes.new('ShaderNodeMath')
    div_dist.location = (550, -350)
    div_dist.operation = 'DIVIDE'
    div_dist.inputs[1].default_value = 65000.0
    links.new(cam_data.outputs['View Distance'], div_dist.inputs[0])

    dist_ramp = nodes.new('ShaderNodeValToRGB')
    dist_ramp.location = (780, -350)
    dist_ramp.color_ramp.elements[0].position = 0.10
    dist_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    dist_ramp.color_ramp.elements[1].position = 0.90
    dist_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    links.new(div_dist.outputs['Value'], dist_ramp.inputs['Fac'])

    mix_atmo = nodes.new('ShaderNodeMix')
    mix_atmo.data_type = 'RGBA'
    mix_atmo.blend_type = 'MIX'
    mix_atmo.location = (1100, 0)
    links.new(dist_ramp.outputs['Color'], mix_atmo.inputs['Factor'])
    links.new(mix_rock_iso.outputs[2], mix_atmo.inputs[6])
    mix_atmo.inputs[7].default_value = (0.020, 0.028, 0.038, 1.0)

    links.new(mix_atmo.outputs[2], bsdf.inputs['Base Color'])

    return mat

def configure_master_scene():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        print("[ERROR] Terrain DEM object not found!")
        return

    # 1. Bicubic Texture Interpolation with Anti-Aliasing Filter
    dem_tex = bpy.data.textures.get('demText.003')
    if dem_tex:
        dem_tex.use_interpolation = True
        dem_tex.filter_size = 4.0

    # 2. DEM Displace Modifier (Vertical Z Displacement)
    dem_mod = obj.modifiers.get('DEM')
    if dem_mod:
        dem_mod.direction = 'Z'

    # 3. Catmull-Clark Smoothing Modifier (eliminates low-poly ridge facets)
    sub = obj.modifiers.get('Subsurf_Smooth')
    if not sub:
        sub = obj.modifiers.new(name='Subsurf_Smooth', type='SUBSURF')
    sub.subdivision_type = 'CATMULL_CLARK'
    sub.levels = 1
    sub.render_levels = 1

    # Remove any other stray modifiers
    for m in list(obj.modifiers):
        if m.name not in ['DEM', 'Subsurf_Smooth']:
            obj.modifiers.remove(m)

    # 3. Global Smooth Shading
    bpy.context.view_layer.objects.active = obj
    for p in obj.data.polygons:
        p.use_smooth = True
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass

    # 4. Assign Material
    mat = create_master_smooth_tactical_material()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    print(f"[OK] Material '{mat.name}' assigned.")

    # 5. Tactical Lighting Rig (Clean Chiaroscuro without shadow map dropouts)
    # Key Sun
    sun = bpy.data.objects.get("Sun_Tactical")
    if not sun:
        sun_data = bpy.data.lights.new("Sun_Tactical", 'SUN')
        sun = bpy.data.objects.new("Sun_Tactical", sun_data)
        scene.collection.objects.link(sun)
    sun.data.energy = 5.6
    sun.data.color = (0.92, 0.96, 1.0)
    sun.data.use_shadow = False # Eliminates 92km VSM page dropout artifacts
    sun.rotation_euler = (math.radians(48.0), math.radians(26.0), math.radians(-65.0))

    # Ambient Fill Sun
    fill = bpy.data.objects.get("Sun_Fill")
    if not fill:
        fill_data = bpy.data.lights.new("Sun_Fill", 'SUN')
        fill = bpy.data.objects.new("Sun_Fill", fill_data)
        scene.collection.objects.link(fill)
    fill.data.energy = 1.8
    fill.data.color = (0.38, 0.48, 0.58)
    fill.data.use_shadow = False
    fill.rotation_euler = (math.radians(115.0), math.radians(-15.0), math.radians(115.0))

    # Downward Skylight Wash
    sky = bpy.data.objects.get("Sun_SkyWash")
    if not sky:
        sky_data = bpy.data.lights.new("Sun_SkyWash", 'SUN')
        sky = bpy.data.objects.new("Sun_SkyWash", sky_data)
        scene.collection.objects.link(sky)
    sky.data.energy = 1.4
    sky.data.color = (0.30, 0.40, 0.50)
    sky.data.use_shadow = False
    sky.rotation_euler = (0, 0, 0)

    # World Atmosphere
    world = scene.world
    if not world:
        world = bpy.data.worlds.new("W_Tactical")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.020, 0.028, 0.038, 1.0)
        bg.inputs['Strength'].default_value = 0.80

    # AgX High Contrast Color Management
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.view_settings.exposure = 0.12

    # 6. Active Camera Setup (Recon Canyon Flight Corridor)
    cam_obj = bpy.data.objects.get("Camera_Canyon_Recon")
    if not cam_obj:
        cam_data = bpy.data.cameras.new("Camera_Canyon_Recon")
        cam_obj = bpy.data.objects.new("Camera_Canyon_Recon", cam_data)
        scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    cam_obj.data.lens = 38.0
    cam_obj.data.clip_start = 10.0
    cam_obj.data.clip_end = 250000.0

    cam_pos = mathutils.Vector((-11400.0, 9200.0, 5550.0))
    target_pos = mathutils.Vector((-7200.0, 14000.0, 4200.0))
    cam_obj.location = cam_pos
    direction = target_pos - cam_pos
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    # Pre-configure 3D Viewport to Camera + Rendered
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'RENDERED'
                        space.region_3d.view_perspective = 'CAMERA'

    # Render Final 1080p Master Image
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = out_path
    print(f"[RENDER] Rendering master terrain output to: {out_path}...")
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved master terrain.blend successfully!")

if __name__ == "__main__":
    configure_master_scene()
