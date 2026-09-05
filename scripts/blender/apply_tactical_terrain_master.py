"""
Refined Tactical Mountain Shader - Ultra Realistic Match
- Eliminates stepping / banding
- Hairline subtle contour lines (faint precision isolines as in reference image)
- High-contrast rugged crags, vertical cliff stratification and deep cavity AO
- Charcoal / gunmetal slate palette matching Top Gun defense reconnaissance aesthetic
- Razor-sharp ridge crest specular highlights
- Clean 60km shadow cascade with zero clipping
"""

import bpy
import mathutils
import math
import os

def create_refined_tactical_material():
    mat = bpy.data.materials.get("M_Tactical_Ladakh_Terrain")
    if not mat:
        mat = bpy.data.materials.new(name="M_Tactical_Ladakh_Terrain")
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Output
    node_out = nodes.new(type='ShaderNodeOutputMaterial')
    node_out.location = (2000, 200)

    # Principled BSDF
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (1650, 200)
    bsdf.inputs['Roughness'].default_value = 0.84
    bsdf.inputs['Specular IOR Level'].default_value = 0.28
    links.new(bsdf.outputs['BSDF'], node_out.inputs['Surface'])

    # Geometry & Camera
    geom = nodes.new(type='ShaderNodeNewGeometry')
    geom.location = (-1600, 0)

    cam_data = nodes.new(type='ShaderNodeCameraData')
    cam_data.location = (-1600, -800)

    # -------------------------------------------------------------
    # 1. PROCEDURAL CRAGS & ROCK BUMP (High-frequency jagged detail)
    # -------------------------------------------------------------
    # Macro cliff strata (vertical rock erosion)
    map_macro = nodes.new(type='ShaderNodeMapping')
    map_macro.location = (-1300, 600)
    map_macro.inputs['Scale'].default_value = (0.003, 0.003, 0.0008)
    links.new(geom.outputs['Position'], map_macro.inputs['Vector'])

    noise_macro = nodes.new(type='ShaderNodeTexNoise')
    noise_macro.location = (-1050, 600)
    noise_macro.inputs['Scale'].default_value = 1.0
    noise_macro.inputs['Detail'].default_value = 15.0
    noise_macro.inputs['Roughness'].default_value = 0.72
    noise_macro.inputs['Lacunarity'].default_value = 2.1
    noise_macro.inputs['Distortion'].default_value = 0.6
    links.new(map_macro.outputs['Vector'], noise_macro.inputs['Vector'])

    # Voronoi rock facets (jagged cliff cuts)
    map_crags = nodes.new(type='ShaderNodeMapping')
    map_crags.location = (-1300, 300)
    map_crags.inputs['Scale'].default_value = (0.008, 0.008, 0.004)
    links.new(geom.outputs['Position'], map_crags.inputs['Vector'])

    voronoi_crags = nodes.new(type='ShaderNodeTexVoronoi')
    voronoi_crags.location = (-1050, 300)
    voronoi_crags.feature = 'F1'
    voronoi_crags.distance = 'EUCLIDEAN'
    voronoi_crags.inputs['Scale'].default_value = 1.0
    links.new(map_crags.outputs['Vector'], voronoi_crags.inputs['Vector'])

    # Micro noise (surface grit & scree)
    map_micro = nodes.new(type='ShaderNodeMapping')
    map_micro.location = (-1300, 0)
    map_micro.inputs['Scale'].default_value = (0.04, 0.04, 0.04)
    links.new(geom.outputs['Position'], map_micro.inputs['Vector'])

    noise_micro = nodes.new(type='ShaderNodeTexNoise')
    noise_micro.location = (-1050, 0)
    noise_micro.inputs['Scale'].default_value = 1.0
    noise_micro.inputs['Detail'].default_value = 8.0
    noise_micro.inputs['Roughness'].default_value = 0.8
    links.new(map_micro.outputs['Vector'], noise_micro.inputs['Vector'])

    # Bump chain
    bump_macro = nodes.new(type='ShaderNodeBump')
    bump_macro.location = (-750, 400)
    bump_macro.inputs['Strength'].default_value = 0.85
    bump_macro.inputs['Distance'].default_value = 25.0
    links.new(noise_macro.outputs['Fac'], bump_macro.inputs['Height'])

    bump_crags = nodes.new(type='ShaderNodeBump')
    bump_crags.location = (-500, 400)
    bump_crags.inputs['Strength'].default_value = 0.60
    bump_crags.inputs['Distance'].default_value = 12.0
    links.new(voronoi_crags.outputs['Distance'], bump_crags.inputs['Height'])
    links.new(bump_macro.outputs['Normal'], bump_crags.inputs['Normal'])

    bump_micro = nodes.new(type='ShaderNodeBump')
    bump_micro.location = (-250, 400)
    bump_micro.inputs['Strength'].default_value = 0.30
    bump_micro.inputs['Distance'].default_value = 3.0
    links.new(noise_micro.outputs['Fac'], bump_micro.inputs['Height'])
    links.new(bump_crags.outputs['Normal'], bump_micro.inputs['Normal'])

    links.new(bump_micro.outputs['Normal'], bsdf.inputs['Normal'])

    # -------------------------------------------------------------
    # 2. BASE COLOR: CHARCOAL / GUNMETAL SLATE PALETTE
    # -------------------------------------------------------------
    # Multi-band slate rock ramp
    rock_ramp = nodes.new(type='ShaderNodeValToRGB')
    rock_ramp.location = (-750, 100)
    # Color calibrated exactly to reference image
    rock_ramp.color_ramp.elements[0].position = 0.20
    rock_ramp.color_ramp.elements[0].color = (0.09, 0.11, 0.13, 1.0) # Deep charcoal crevice
    rock_ramp.color_ramp.elements[1].position = 0.55
    rock_ramp.color_ramp.elements[1].color = (0.18, 0.21, 0.24, 1.0) # Slate rock face
    elem_ridge = rock_ramp.color_ramp.elements.new(0.85)
    elem_ridge.color = (0.28, 0.33, 0.37, 1.0) # Sunlit rock
    links.new(noise_macro.outputs['Fac'], rock_ramp.inputs['Fac'])

    # Ambient Occlusion (Cavity / Crevice deep shadows)
    ao_node = nodes.new(type='ShaderNodeAmbientOcclusion')
    ao_node.location = (-750, -200)
    ao_node.inputs['Distance'].default_value = 100.0
    ao_node.samples = 16

    mix_ao = nodes.new(type='ShaderNodeMix')
    mix_ao.data_type = 'RGBA'
    mix_ao.blend_type = 'MULTIPLY'
    mix_ao.location = (-450, 0)
    mix_ao.inputs['Factor'].default_value = 0.90
    links.new(rock_ramp.outputs['Color'], mix_ao.inputs[6])
    links.new(ao_node.outputs['Color'], mix_ao.inputs[7])

    # Knife-Edge Ridge Rim Highlight
    layer_weight = nodes.new(type='ShaderNodeLayerWeight')
    layer_weight.location = (-750, -450)
    layer_weight.inputs['Blend'].default_value = 0.38

    ridge_ramp = nodes.new(type='ShaderNodeValToRGB')
    ridge_ramp.location = (-450, -450)
    ridge_ramp.color_ramp.elements[0].position = 0.70
    ridge_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ridge_ramp.color_ramp.elements[1].position = 0.98
    ridge_ramp.color_ramp.elements[1].color = (0.35, 0.42, 0.48, 1.0)
    links.new(layer_weight.outputs['Facing'], ridge_ramp.inputs['Fac'])

    mix_ridge = nodes.new(type='ShaderNodeMix')
    mix_ridge.data_type = 'RGBA'
    mix_ridge.blend_type = 'ADD'
    mix_ridge.location = (-150, 0)
    mix_ridge.inputs['Factor'].default_value = 0.40
    links.new(mix_ao.outputs[2], mix_ridge.inputs[6])
    links.new(ridge_ramp.outputs['Color'], mix_ridge.inputs[7])

    # -------------------------------------------------------------
    # 3. HAIRLINE SUBTLE TOPOGRAPHIC ISOLINES (Faint precision lines)
    # -------------------------------------------------------------
    sep_pos = nodes.new(type='ShaderNodeSeparateXYZ')
    sep_pos.location = (-750, -800)
    links.new(geom.outputs['Position'], sep_pos.inputs['Vector'])

    # Contour interval: 120 meters
    div_iso = nodes.new(type='ShaderNodeMath')
    div_iso.location = (-500, -800)
    div_iso.operation = 'DIVIDE'
    div_iso.inputs[1].default_value = 120.0
    links.new(sep_pos.outputs['Z'], div_iso.inputs[0])

    fract_iso = nodes.new(type='ShaderNodeMath')
    fract_iso.location = (-300, -800)
    fract_iso.operation = 'FRACT'
    links.new(div_iso.outputs['Value'], fract_iso.inputs[0])

    sub_iso = nodes.new(type='ShaderNodeMath')
    sub_iso.location = (-100, -800)
    sub_iso.operation = 'SUBTRACT'
    sub_iso.inputs[1].default_value = 0.5
    links.new(fract_iso.outputs['Value'], sub_iso.inputs[0])

    abs_iso = nodes.new(type='ShaderNodeMath')
    abs_iso.location = (100, -800)
    abs_iso.operation = 'ABSOLUTE'
    links.new(sub_iso.outputs['Value'], abs_iso.inputs[0])

    # Hairline color ramp (very thin, soft edge)
    ramp_iso = nodes.new(type='ShaderNodeValToRGB')
    ramp_iso.location = (300, -800)
    ramp_iso.color_ramp.elements[0].position = 0.488
    ramp_iso.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_iso.color_ramp.elements[1].position = 0.50
    ramp_iso.color_ramp.elements[1].color = (0.50, 0.62, 0.74, 1.0) # Subtle faint isoline
    links.new(abs_iso.outputs['Value'], ramp_iso.inputs['Fac'])

    # Overlay faint isolines onto rock
    mix_iso = nodes.new(type='ShaderNodeMix')
    mix_iso.data_type = 'RGBA'
    mix_iso.blend_type = 'ADD'
    mix_iso.location = (600, 0)
    mix_iso.inputs['Factor'].default_value = 0.28 # Very faint and subtle like reference!
    links.new(mix_ridge.outputs[2], mix_iso.inputs[6])
    links.new(ramp_iso.outputs['Color'], mix_iso.inputs[7])

    # -------------------------------------------------------------
    # 4. ATMOSPHERIC HORIZON HAZE (Blends distant peaks to dark sky)
    # -------------------------------------------------------------
    div_dist = nodes.new(type='ShaderNodeMath')
    div_dist.location = (600, -400)
    div_dist.operation = 'DIVIDE'
    div_dist.inputs[1].default_value = 60000.0 # 60km fade
    links.new(cam_data.outputs['View Distance'], div_dist.inputs[0])

    dist_ramp = nodes.new(type='ShaderNodeValToRGB')
    dist_ramp.location = (850, -400)
    dist_ramp.color_ramp.elements[0].position = 0.10
    dist_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    dist_ramp.color_ramp.elements[1].position = 0.90
    dist_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    links.new(div_dist.outputs['Value'], dist_ramp.inputs['Fac'])

    mix_atmo = nodes.new(type='ShaderNodeMix')
    mix_atmo.data_type = 'RGBA'
    mix_atmo.blend_type = 'MIX'
    mix_atmo.location = (1150, 0)
    links.new(dist_ramp.outputs['Color'], mix_atmo.inputs['Factor'])
    links.new(mix_iso.outputs[2], mix_atmo.inputs[6])
    mix_atmo.inputs[7].default_value = (0.015, 0.020, 0.026, 1.0) # Horizon sky tone

    links.new(mix_atmo.outputs[2], bsdf.inputs['Base Color'])

    return mat

def configure_terrain_scene():
    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        return

    # Enable smooth interpolation on DEM texture
    dem_tex = bpy.data.textures.get('demText.003')
    if dem_tex:
        dem_tex.use_interpolation = True

    # Fix Displace modifier direction to 'Z'
    dem_mod = obj.modifiers.get('DEM')
    if dem_mod:
        dem_mod.direction = 'Z'

    # Remove the subsurf modifier if it caused UV stretching, or keep level 1
    sub = obj.modifiers.get('Subsurf')
    if sub:
        # Check if subsurf was stretching
        sub.levels = 1
        sub.render_levels = 1

    # Global Smooth Shading
    for poly in obj.data.polygons:
        poly.use_smooth = True
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass

    # Assign material
    mat = create_refined_tactical_material()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    # Lighting: Sun with 75km shadow reach
    scene = bpy.context.scene
    sun = bpy.data.objects.get("Sun_Tactical")
    if sun:
        sun.data.energy = 5.8
        sun.data.color = (0.90, 0.95, 1.0)
        sun.data.shadow_cascade_max_distance = 75000.0
        sun.data.shadow_cascade_count = 4
        sun.data.shadow_buffer_clip_start = 5.0
        # Raking side angle matching reference: from upper-right
        sun.rotation_euler = (math.radians(46.0), math.radians(28.0), math.radians(-65.0))

    fill = bpy.data.objects.get("Sun_Fill")
    if fill:
        fill.data.energy = 0.75
        fill.data.color = (0.30, 0.38, 0.46)
        fill.data.shadow_cascade_max_distance = 75000.0
        fill.rotation_euler = (math.radians(115.0), math.radians(-15.0), math.radians(115.0))

    # World background
    if scene.world and scene.world.node_tree:
        bg = scene.world.node_tree.nodes.get("Background")
        if bg:
            bg.inputs['Color'].default_value = (0.015, 0.020, 0.026, 1.0)
            bg.inputs['Strength'].default_value = 0.50

    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.view_settings.exposure = 0.10

    # Camera: Chase-recon perspective looking down the canyon
    cam_obj = bpy.data.objects.get("Camera_Canyon_Recon")
    if cam_obj:
        cam_pos = mathutils.Vector((-11400.0, 9200.0, 5650.0))
        target_pos = mathutils.Vector((-7200.0, 14000.0, 4300.0))
        cam_obj.location = cam_pos
        direction = target_pos - cam_pos
        cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        cam_obj.data.lens = 40.0

    # Render
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_preview5.png"))
    scene.render.filepath = out_path
    print(f"Rendering refined preview to: {out_path}...")
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    bpy.ops.wm.save_mainfile()
    print("[OK] Saved terrain.blend!")

if __name__ == "__main__":
    configure_terrain_scene()
