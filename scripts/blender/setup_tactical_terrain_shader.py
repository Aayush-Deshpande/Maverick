"""
Tactical FLIR / DTED Reconnaissance Mountain Shader & Scene Setup
Recreates the exact military tactical canyon aesthetic from the reference image:
- Slate-charcoal matte rock with vertical cliff stratification
- Dual-tier topographic elevation contour lines (80m minor + 400m major index lines)
- Razor-edge ridge crest highlights
- Deep crevice ambient occlusion / cavity shading
- High-frequency procedural rock crag normal mapping
- Directional raking sun lighting & cool moody atmospheric world
"""

import bpy
import mathutils
import math
import os
import numpy as np

def create_tactical_mountain_material():
    mat = bpy.data.materials.get("M_Tactical_Ladakh_Terrain")
    if not mat:
        mat = bpy.data.materials.new(name="M_Tactical_Ladakh_Terrain")
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # 1. Material Output
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_output.location = (1800, 200)

    # 2. Principled BSDF
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (1500, 200)
    bsdf.inputs['Roughness'].default_value = 0.82
    bsdf.inputs['Specular IOR Level'].default_value = 0.32
    if 'Sheen Roughness' in bsdf.inputs:
        bsdf.inputs['Sheen Roughness'].default_value = 0.5
    links.new(bsdf.outputs['BSDF'], node_output.inputs['Surface'])

    # 3. Geometry Node (World-space Position & Normal)
    geom = nodes.new(type='ShaderNodeNewGeometry')
    geom.location = (-1400, 0)

    # -------------------------------------------------------------
    # A. PROCEDURAL ROCK BUMP & CLIFF STRATIFICATION
    # -------------------------------------------------------------
    # Strata Noise (stretched vertically for cliff erosion channels)
    map_strata = nodes.new(type='ShaderNodeMapping')
    map_strata.location = (-1100, 700)
    map_strata.inputs['Scale'].default_value = (0.005, 0.005, 0.0012)
    links.new(geom.outputs['Position'], map_strata.inputs['Vector'])

    noise_strata = nodes.new(type='ShaderNodeTexNoise')
    noise_strata.location = (-850, 700)
    noise_strata.inputs['Scale'].default_value = 1.0
    noise_strata.inputs['Detail'].default_value = 14.0
    noise_strata.inputs['Roughness'].default_value = 0.72
    noise_strata.inputs['Lacunarity'].default_value = 2.15
    links.new(map_strata.outputs['Vector'], noise_strata.inputs['Vector'])

    # Voronoi Crags (Chipped rock faces and fractured cliff slabs)
    map_crags = nodes.new(type='ShaderNodeMapping')
    map_crags.location = (-1100, 350)
    map_crags.inputs['Scale'].default_value = (0.015, 0.015, 0.007)
    links.new(geom.outputs['Position'], map_crags.inputs['Vector'])

    voronoi_crags = nodes.new(type='ShaderNodeTexVoronoi')
    voronoi_crags.location = (-850, 350)
    voronoi_crags.feature = 'F1'
    voronoi_crags.distance = 'EUCLIDEAN'
    voronoi_crags.inputs['Scale'].default_value = 1.0
    links.new(map_crags.outputs['Vector'], voronoi_crags.inputs['Vector'])

    # Micro scree noise (Fine surface grain)
    map_micro = nodes.new(type='ShaderNodeMapping')
    map_micro.location = (-1100, 0)
    map_micro.inputs['Scale'].default_value = (0.08, 0.08, 0.08)
    links.new(geom.outputs['Position'], map_micro.inputs['Vector'])

    noise_micro = nodes.new(type='ShaderNodeTexNoise')
    noise_micro.location = (-850, 0)
    noise_micro.inputs['Scale'].default_value = 1.0
    noise_micro.inputs['Detail'].default_value = 8.0
    noise_micro.inputs['Roughness'].default_value = 0.75
    links.new(map_micro.outputs['Vector'], noise_micro.inputs['Vector'])

    # Bump chain
    bump_macro = nodes.new(type='ShaderNodeBump')
    bump_macro.location = (-550, 400)
    bump_macro.inputs['Strength'].default_value = 0.75
    bump_macro.inputs['Distance'].default_value = 18.0
    links.new(noise_strata.outputs['Fac'], bump_macro.inputs['Height'])

    bump_crags = nodes.new(type='ShaderNodeBump')
    bump_crags.location = (-300, 400)
    bump_crags.inputs['Strength'].default_value = 0.50
    bump_crags.inputs['Distance'].default_value = 8.0
    links.new(voronoi_crags.outputs['Distance'], bump_crags.inputs['Height'])
    links.new(bump_macro.outputs['Normal'], bump_crags.inputs['Normal'])

    bump_micro = nodes.new(type='ShaderNodeBump')
    bump_micro.location = (-50, 400)
    bump_micro.inputs['Strength'].default_value = 0.25
    bump_micro.inputs['Distance'].default_value = 2.0
    links.new(noise_micro.outputs['Fac'], bump_micro.inputs['Height'])
    links.new(bump_crags.outputs['Normal'], bump_micro.inputs['Normal'])

    links.new(bump_micro.outputs['Normal'], bsdf.inputs['Normal'])

    # -------------------------------------------------------------
    # B. BASE ROCK COLOR & SLOPE DIFFERENTIATION
    # -------------------------------------------------------------
    # Slope determination (Normal Z: 0 = cliff, 1 = flat valley)
    sep_normal = nodes.new(type='ShaderNodeSeparateXYZ')
    sep_normal.location = (-1100, -300)
    links.new(geom.outputs['Normal'], sep_normal.inputs['Vector'])

    slope_ramp = nodes.new(type='ShaderNodeValToRGB')
    slope_ramp.location = (-850, -300)
    # Darker, stratified slate on steep cliffs; medium charcoal on plateaus
    slope_ramp.color_ramp.elements[0].position = 0.30
    slope_ramp.color_ramp.elements[0].color = (0.16, 0.18, 0.21, 1.0) # Deep cliff slate
    slope_ramp.color_ramp.elements[1].position = 0.85
    slope_ramp.color_ramp.elements[1].color = (0.28, 0.32, 0.36, 1.0) # Valley floor / plateau
    links.new(sep_normal.outputs['Z'], slope_ramp.inputs['Fac'])

    # Ambient Occlusion (Inky crevice shading)
    ao_node = nodes.new(type='ShaderNodeAmbientOcclusion')
    ao_node.location = (-850, -600)
    ao_node.inputs['Distance'].default_value = 60.0
    ao_node.samples = 16

    mix_ao = nodes.new(type='ShaderNodeMix')
    mix_ao.data_type = 'RGBA'
    mix_ao.blend_type = 'MULTIPLY'
    mix_ao.location = (-550, -300)
    mix_ao.inputs['Factor'].default_value = 0.85
    links.new(slope_ramp.outputs['Color'], mix_ao.inputs[6])
    links.new(ao_node.outputs['Color'], mix_ao.inputs[7])

    # -------------------------------------------------------------
    # C. RIDGE CREST & RIM HIGHLIGHTS (Curvature / Edge Glow)
    # -------------------------------------------------------------
    layer_weight = nodes.new(type='ShaderNodeLayerWeight')
    layer_weight.location = (-850, -850)
    layer_weight.inputs['Blend'].default_value = 0.38

    ridge_ramp = nodes.new(type='ShaderNodeValToRGB')
    ridge_ramp.location = (-550, -850)
    ridge_ramp.color_ramp.elements[0].position = 0.50
    ridge_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ridge_ramp.color_ramp.elements[1].position = 0.92
    ridge_ramp.color_ramp.elements[1].color = (0.75, 0.82, 0.90, 1.0) # Cool chalky crest rim
    links.new(layer_weight.outputs['Facing'], ridge_ramp.inputs['Fac'])

    mix_ridge = nodes.new(type='ShaderNodeMix')
    mix_ridge.data_type = 'RGBA'
    mix_ridge.blend_type = 'SCREEN'
    mix_ridge.location = (-250, -300)
    mix_ridge.inputs['Factor'].default_value = 0.55
    links.new(mix_ao.outputs[2], mix_ridge.inputs[6])
    links.new(ridge_ramp.outputs['Color'], mix_ridge.inputs[7])

    # -------------------------------------------------------------
    # D. DUAL-TIER TOPOGRAPHIC CONTOUR ISOLINES
    # -------------------------------------------------------------
    sep_pos = nodes.new(type='ShaderNodeSeparateXYZ')
    sep_pos.location = (-550, -1150)
    links.new(geom.outputs['Position'], sep_pos.inputs['Vector'])

    # 1. Minor Contours (every 75 meters)
    div_minor = nodes.new(type='ShaderNodeMath')
    div_minor.location = (-300, -1150)
    div_minor.operation = 'DIVIDE'
    div_minor.inputs[1].default_value = 75.0
    links.new(sep_pos.outputs['Z'], div_minor.inputs[0])

    fract_minor = nodes.new(type='ShaderNodeMath')
    fract_minor.location = (-100, -1150)
    fract_minor.operation = 'FRACT'
    links.new(div_minor.outputs['Value'], fract_minor.inputs[0])

    ramp_minor = nodes.new(type='ShaderNodeValToRGB')
    ramp_minor.location = (100, -1150)
    ramp_minor.color_ramp.elements[0].position = 0.0
    ramp_minor.color_ramp.elements[0].color = (0.65, 0.78, 0.90, 1.0) # Delicate cool contour line
    ramp_minor.color_ramp.elements[1].position = 0.035
    ramp_minor.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
    links.new(fract_minor.outputs['Value'], ramp_minor.inputs['Fac'])

    # 2. Major Index Contours (every 375 meters, slightly bolder)
    div_major = nodes.new(type='ShaderNodeMath')
    div_major.location = (-300, -1450)
    div_major.operation = 'DIVIDE'
    div_major.inputs[1].default_value = 375.0
    links.new(sep_pos.outputs['Z'], div_major.inputs[0])

    fract_major = nodes.new(type='ShaderNodeMath')
    fract_major.location = (-100, -1450)
    fract_major.operation = 'FRACT'
    links.new(div_major.outputs['Value'], fract_major.inputs[0])

    ramp_major = nodes.new(type='ShaderNodeValToRGB')
    ramp_major.location = (100, -1450)
    ramp_major.color_ramp.elements[0].position = 0.0
    ramp_major.color_ramp.elements[0].color = (0.90, 0.95, 1.0, 1.0) # Prominent index contour
    ramp_major.color_ramp.elements[1].position = 0.030
    ramp_major.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
    links.new(fract_major.outputs['Value'], ramp_major.inputs['Fac'])

    # Combine minor + major contours
    mix_contour_tiers = nodes.new(type='ShaderNodeMix')
    mix_contour_tiers.data_type = 'RGBA'
    mix_contour_tiers.blend_type = 'ADD'
    mix_contour_tiers.location = (400, -1300)
    mix_contour_tiers.inputs['Factor'].default_value = 1.0
    links.new(ramp_minor.outputs['Color'], mix_contour_tiers.inputs[6])
    links.new(ramp_major.outputs['Color'], mix_contour_tiers.inputs[7])

    # Overlay Contours on Rock Surface
    mix_final_color = nodes.new(type='ShaderNodeMix')
    mix_final_color.data_type = 'RGBA'
    mix_final_color.blend_type = 'ADD'
    mix_final_color.location = (750, -300)
    mix_final_color.inputs['Factor'].default_value = 0.42 # Crisp, visible tactical contour overlay
    links.new(mix_ridge.outputs[2], mix_final_color.inputs[6])
    links.new(mix_contour_tiers.outputs[2], mix_final_color.inputs[7])

    # Connect Final Base Color to BSDF
    links.new(mix_final_color.outputs[2], bsdf.inputs['Base Color'])

    return mat

def setup_scene_and_lighting():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    
    if hasattr(scene, 'eevee'):
        scene.eevee.use_shadows = True
        try:
            scene.eevee.shadow_resolution_scale = 2.0
            scene.eevee.shadow_ray_count = 4
            scene.eevee.shadow_step_count = 16
        except Exception:
            pass

    # World: Moody dark slate military atmosphere
    world = bpy.data.worlds.get("W_Tactical_Mountain")
    if not world:
        world = bpy.data.worlds.new("W_Tactical_Mountain")
    scene.world = world
    world.use_nodes = True
    wnodes = world.node_tree.nodes
    wlinks = world.node_tree.links
    wnodes.clear()
    
    w_out = wnodes.new(type='ShaderNodeOutputWorld')
    w_bg = wnodes.new(type='ShaderNodeBackground')
    w_bg.inputs['Color'].default_value = (0.012, 0.018, 0.025, 1.0) # Inky atmospheric navy-slate
    w_bg.inputs['Strength'].default_value = 0.65
    wlinks.new(w_bg.outputs['Background'], w_out.inputs['Surface'])

    # Color Management: AgX / High Contrast
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.view_settings.exposure = 0.35

    # Key Directional Sun Light (Low raking angle casting long, dramatic ridge shadows)
    sun_obj = bpy.data.objects.get("Sun_Tactical")
    if not sun_obj:
        sun_data = bpy.data.lights.new(name="Sun_Tactical", type='SUN')
        sun_obj = bpy.data.objects.new(name="Sun_Tactical", object_data=sun_data)
        scene.collection.objects.link(sun_obj)
    
    sun_obj.data.energy = 4.8
    sun_obj.data.color = (0.90, 0.95, 1.0) # Crisp cold white daylight
    sun_obj.data.angle = math.radians(1.2) # Sharp shadow edges
    # Angled across canyon to highlight ridges
    sun_obj.rotation_euler = (math.radians(48.0), math.radians(15.0), math.radians(-125.0))

    # Ambient Fill Sun
    fill_obj = bpy.data.objects.get("Sun_Fill")
    if not fill_obj:
        fill_data = bpy.data.lights.new(name="Sun_Fill", type='SUN')
        fill_obj = bpy.data.objects.new(name="Sun_Fill", object_data=fill_data)
        scene.collection.objects.link(fill_obj)
    
    fill_obj.data.energy = 0.75
    fill_obj.data.color = (0.40, 0.50, 0.60) # Cool shadow fill
    fill_obj.rotation_euler = (math.radians(115.0), math.radians(-25.0), math.radians(55.0))

    return sun_obj

def setup_canyon_camera():
    scene = bpy.context.scene
    cam_obj = bpy.data.objects.get("Camera_Canyon_Recon")
    if not cam_obj:
        cam_data = bpy.data.cameras.new("Camera_Canyon_Recon")
        cam_obj = bpy.data.objects.new("Camera_Canyon_Recon", cam_data)
        scene.collection.objects.link(cam_obj)
    
    scene.camera = cam_obj
    cam = cam_obj.data
    cam.lens = 38.0 # 38mm wide-tele tactical framing
    cam.clip_start = 10.0
    cam.clip_end = 250000.0 # 250 km view distance

    # Position inside high-relief gorge at (X=10000, Y=0)
    # Looking down the mountain canyon corridor matching the reference screenshot angle
    cam_obj.location = (8200.0, -4200.0, 5400.0)
    cam_obj.rotation_euler = (math.radians(68.0), math.radians(0.0), math.radians(24.0))

    # Render settings
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    return cam_obj

def apply_and_render(output_image_path=None, save_blend=True):
    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        print("[ERROR] Terrain DEM object not found!")
        return
    
    mat = create_tactical_mountain_material()
    
    # Assign material
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    
    # Enable smooth shading for organic mountain look
    for poly in obj.data.polygons:
        poly.use_smooth = True
    
    print(f"[OK] Assigned material '{mat.name}' to '{obj.name}' with smooth shading.")
    
    setup_scene_and_lighting()
    cam = setup_canyon_camera()
    print("[OK] Scene, World, Lighting and Camera configured.")

    if output_image_path:
        os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
        bpy.context.scene.render.filepath = output_image_path
        print(f"[RENDER] Rendering tactical terrain preview to: {output_image_path}...")
        bpy.ops.render.render(write_still=True)
        print("[OK] Render complete!")

    if save_blend:
        blend_path = bpy.data.filepath
        if blend_path:
            bpy.ops.wm.save_mainfile(filepath=blend_path)
            print(f"[OK] Saved updated master scene to: {blend_path}")

if __name__ == "__main__":
    render_out = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_preview.png"))
    apply_and_render(output_image_path=render_out, save_blend=True)
