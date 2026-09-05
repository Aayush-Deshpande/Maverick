"""
Tactical FLIR / Reconnaissance Terrain Visual Overhaul
Matches the reference defense simulation visual 1:1:
1. High-altitude oblique recon camera looking down into the canyon corridor
2. Aggressive, craggy multi-octave rock fracture shader (vertical striations, scree, ledges)
3. Precision topographic contour isolines + subtle tactical elevation grid
4. Low-altitude canyon floor atmospheric haze/fog filling the river trench
5. High-contrast military FLIR / Synthetic Vision color grading
"""

import bpy
import mathutils
import math
import os

def build_tactical_craggy_rock_material():
    mat = bpy.data.materials.get("M_Tactical_Ladakh_Terrain")
    if not mat:
        mat = bpy.data.materials.new("M_Tactical_Ladakh_Terrain")
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Output & Principled BSDF
    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (2400, 200)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (2050, 200)
    bsdf.inputs['Roughness'].default_value = 0.88
    bsdf.inputs['Specular IOR Level'].default_value = 0.35
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-2200, 200)

    cam_data = nodes.new('ShaderNodeCameraData')
    cam_data.location = (-2200, -800)

    # -------------------------------------------------------------------------
    # 1. PROCEDURAL ROCK FRACTURE & CLIFF STRATIFICATION (CRAGGY RELIEF)
    # -------------------------------------------------------------------------
    # Coordinate system based on world position
    # Macro vertical cliff striations (fluting)
    map_cliff = nodes.new('ShaderNodeMapping')
    map_cliff.location = (-1900, 600)
    map_cliff.inputs['Scale'].default_value = (0.003, 0.003, 0.0008)
    links.new(geom.outputs['Position'], map_cliff.inputs['Vector'])

    noise_cliff = nodes.new('ShaderNodeTexNoise')
    noise_cliff.location = (-1650, 600)
    noise_cliff.inputs['Scale'].default_value = 2.0
    noise_cliff.inputs['Detail'].default_value = 12.0
    noise_cliff.inputs['Roughness'].default_value = 0.65
    noise_cliff.inputs['Lacunarity'].default_value = 2.2
    noise_cliff.inputs['Distortion'].default_value = 0.6
    links.new(map_cliff.outputs['Vector'], noise_cliff.inputs['Vector'])

    # Meso rock fracture pattern (Voronoi crackle/crags)
    map_crag = nodes.new('ShaderNodeMapping')
    map_crag.location = (-1900, 250)
    map_crag.inputs['Scale'].default_value = (0.006, 0.006, 0.004)
    links.new(geom.outputs['Position'], map_crag.inputs['Vector'])

    voronoi_crag = nodes.new('ShaderNodeTexVoronoi')
    voronoi_crag.location = (-1650, 250)
    voronoi_crag.voronoi_dimensions = '3D'
    voronoi_crag.feature = 'DISTANCE_TO_EDGE'
    voronoi_crag.inputs['Scale'].default_value = 1.5
    links.new(map_crag.outputs['Vector'], voronoi_crag.inputs['Vector'])

    # Micro rocky surface grain & scree
    map_scree = nodes.new('ShaderNodeMapping')
    map_scree.location = (-1900, -100)
    map_scree.inputs['Scale'].default_value = (0.04, 0.04, 0.04)
    links.new(geom.outputs['Position'], map_scree.inputs['Vector'])

    noise_scree = nodes.new('ShaderNodeTexNoise')
    noise_scree.location = (-1650, -100)
    noise_scree.inputs['Scale'].default_value = 1.0
    noise_scree.inputs['Detail'].default_value = 8.0
    noise_scree.inputs['Roughness'].default_value = 0.85
    links.new(map_scree.outputs['Vector'], noise_scree.inputs['Vector'])

    # Combine Meso Crags + Macro Cliff into Rock Relief Factor
    mix_crags = nodes.new('ShaderNodeMix')
    mix_crags.data_type = 'FLOAT'
    mix_crags.blend_type = 'MIX'
    mix_crags.location = (-1350, 400)
    mix_crags.inputs['Factor'].default_value = 0.55
    links.new(noise_cliff.outputs['Fac'], mix_crags.inputs[2])
    links.new(voronoi_crag.outputs['Distance'], mix_crags.inputs[3])

    # -------------------------------------------------------------------------
    # 2. CALIBRATED CRAGGY NORMAL BUMP CHAIN
    # -------------------------------------------------------------------------
    bump_macro = nodes.new('ShaderNodeBump')
    bump_macro.location = (-1050, 400)
    bump_macro.inputs['Strength'].default_value = 0.55
    bump_macro.inputs['Distance'].default_value = 3.5
    links.new(mix_crags.outputs[0], bump_macro.inputs['Height'])

    bump_micro = nodes.new('ShaderNodeBump')
    bump_micro.location = (-800, 400)
    bump_micro.inputs['Strength'].default_value = 0.25
    bump_micro.inputs['Distance'].default_value = 1.0
    links.new(noise_scree.outputs['Fac'], bump_micro.inputs['Height'])
    links.new(bump_macro.outputs['Normal'], bump_micro.inputs['Normal'])

    links.new(bump_micro.outputs['Normal'], bsdf.inputs['Normal'])

    # -------------------------------------------------------------------------
    # 3. PHOTOREALISTIC SLATE & CRAGGY ROCK TEXTURE PALETTE
    # -------------------------------------------------------------------------
    ramp_rock = nodes.new('ShaderNodeValToRGB')
    ramp_rock.location = (-1050, 0)
    # Stop 0: Deep shadowy crevice slate
    ramp_rock.color_ramp.elements[0].position = 0.15
    ramp_rock.color_ramp.elements[0].color = (0.07, 0.085, 0.10, 1.0)
    # Stop 1: Weathered Himalayan gneiss midtone
    ramp_rock.color_ramp.elements[1].position = 0.50
    ramp_rock.color_ramp.elements[1].color = (0.16, 0.19, 0.22, 1.0)
    # Stop 2: Exposed granite ridge highlight
    elem_high = ramp_rock.color_ramp.elements.new(0.82)
    elem_high.color = (0.28, 0.33, 0.37, 1.0)
    links.new(mix_crags.outputs[0], ramp_rock.inputs['Fac'])

    # Scree contrast modulation
    mix_rock_color = nodes.new('ShaderNodeMix')
    mix_rock_color.data_type = 'RGBA'
    mix_rock_color.blend_type = 'MULTIPLY'
    mix_rock_color.location = (-750, 0)
    mix_rock_color.inputs['Factor'].default_value = 0.35
    links.new(ramp_rock.outputs['Color'], mix_rock_color.inputs[6])
    links.new(noise_scree.outputs['Fac'], mix_rock_color.inputs[7])

    # -------------------------------------------------------------------------
    # 4. ORGANIC TOPOGRAPHIC CONTOUR ISOLINES (Hugging Mountain Relief)
    # -------------------------------------------------------------------------
    sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    sep_pos.location = (-1900, -450)
    links.new(geom.outputs['Position'], sep_pos.inputs['Vector'])

    # Contour interval: 90 meters
    div_iso = nodes.new('ShaderNodeMath')
    div_iso.location = (-1650, -450)
    div_iso.operation = 'DIVIDE'
    div_iso.inputs[1].default_value = 90.0
    links.new(sep_pos.outputs['Z'], div_iso.inputs[0])

    fract_iso = nodes.new('ShaderNodeMath')
    fract_iso.location = (-1450, -450)
    fract_iso.operation = 'FRACT'
    links.new(div_iso.outputs['Value'], fract_iso.inputs[0])

    sub_iso = nodes.new('ShaderNodeMath')
    sub_iso.location = (-1250, -450)
    sub_iso.operation = 'SUBTRACT'
    sub_iso.inputs[1].default_value = 0.5
    links.new(fract_iso.outputs['Value'], sub_iso.inputs[0])

    abs_iso = nodes.new('ShaderNodeMath')
    abs_iso.location = (-1050, -450)
    abs_iso.operation = 'ABSOLUTE'
    links.new(sub_iso.outputs['Value'], abs_iso.inputs[0])

    ramp_iso = nodes.new('ShaderNodeValToRGB')
    ramp_iso.location = (-800, -450)
    ramp_iso.color_ramp.elements[0].position = 0.485
    ramp_iso.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_iso.color_ramp.elements[1].position = 0.50
    ramp_iso.color_ramp.elements[1].color = (0.55, 0.68, 0.78, 1.0) # Delicate tactical isoline
    links.new(abs_iso.outputs['Value'], ramp_iso.inputs['Fac'])

    # Overlay Topographic Isolines onto Rock Base
    mix_with_iso = nodes.new('ShaderNodeMix')
    mix_with_iso.data_type = 'RGBA'
    mix_with_iso.blend_type = 'ADD'
    mix_with_iso.location = (-450, 0)
    mix_with_iso.inputs['Factor'].default_value = 0.40
    links.new(mix_rock_color.outputs[2], mix_with_iso.inputs[6])
    links.new(ramp_iso.outputs['Color'], mix_with_iso.inputs[7])

    # -------------------------------------------------------------------------
    # 5. CANYON FLOOR TRENCH FOG / RIVERBED HAZE
    # Low-elevation mist filling the canyon trench (Z < 3800m)
    # -------------------------------------------------------------------------
    # Normalize Z elevation for canyon floor haze: 3000m to 4200m
    sub_canyon = nodes.new('ShaderNodeMath')
    sub_canyon.location = (-800, -800)
    sub_canyon.operation = 'SUBTRACT'
    sub_canyon.inputs[1].default_value = 3200.0
    links.new(sep_pos.outputs['Z'], sub_canyon.inputs[0])

    div_canyon = nodes.new('ShaderNodeMath')
    div_canyon.location = (-600, -800)
    div_canyon.operation = 'DIVIDE'
    div_canyon.inputs[1].default_value = 1000.0 # 3200 to 4200m transition
    links.new(sub_canyon.outputs['Value'], div_canyon.inputs[0])

    ramp_canyon_fog = nodes.new('ShaderNodeValToRGB')
    ramp_canyon_fog.location = (-380, -800)
    # Invert so lowest Z gets dense dark canyon haze
    ramp_canyon_fog.color_ramp.elements[0].position = 0.0
    ramp_canyon_fog.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    ramp_canyon_fog.color_ramp.elements[1].position = 1.0
    ramp_canyon_fog.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
    links.new(div_canyon.outputs['Value'], ramp_canyon_fog.inputs['Fac'])

    # Mix canyon haze into base color
    mix_canyon_fog = nodes.new('ShaderNodeMix')
    mix_canyon_fog.data_type = 'RGBA'
    mix_canyon_fog.blend_type = 'MIX'
    mix_canyon_fog.location = (-100, 0)
    mix_canyon_fog.inputs[7].default_value = (0.04, 0.06, 0.08, 1.0) # Deep shadowy trench tone
    links.new(ramp_canyon_fog.outputs['Color'], mix_canyon_fog.inputs['Factor'])
    links.new(mix_with_iso.outputs[2], mix_canyon_fog.inputs[6])

    # -------------------------------------------------------------------------
    # 6. DISTANCE ATMOSPHERE / HORIZON HAZE
    # -------------------------------------------------------------------------
    div_dist = nodes.new('ShaderNodeMath')
    div_dist.location = (-100, -450)
    div_dist.operation = 'DIVIDE'
    div_dist.inputs[1].default_value = 75000.0
    links.new(cam_data.outputs['View Distance'], div_dist.inputs[0])

    ramp_dist = nodes.new('ShaderNodeValToRGB')
    ramp_dist.location = (150, -450)
    ramp_dist.color_ramp.elements[0].position = 0.15
    ramp_dist.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_dist.color_ramp.elements[1].position = 0.95
    ramp_dist.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    links.new(div_dist.outputs['Value'], ramp_dist.inputs['Fac'])

    mix_final_atmo = nodes.new('ShaderNodeMix')
    mix_final_atmo.data_type = 'RGBA'
    mix_final_atmo.blend_type = 'MIX'
    mix_final_atmo.location = (450, 0)
    mix_final_atmo.inputs[7].default_value = (0.015, 0.022, 0.030, 1.0) # Dark horizon void
    links.new(ramp_dist.outputs['Color'], mix_final_atmo.inputs['Factor'])
    links.new(mix_canyon_fog.outputs[2], mix_final_atmo.inputs[6])

    links.new(mix_final_atmo.outputs[2], bsdf.inputs['Base Color'])

    return mat

def setup_tactical_recon_scene():
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

    # Smooth shading
    for p in obj.data.polygons:
        p.use_smooth = True

    # 3. Assign Tactical Material
    mat = build_tactical_craggy_rock_material()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    # -------------------------------------------------------------------------
    # 4. HIGH-ALTITUDE OBLIQUE RECON CAMERA (LOOKING DOWN INTO GORGE)
    # Matching the perspective, angle, and framing of the reference image
    # -------------------------------------------------------------------------
    cam_obj = bpy.data.objects.get("Camera_Canyon_Recon")
    if not cam_obj:
        cam_data = bpy.data.cameras.new("Camera_Canyon_Recon")
        cam_obj = bpy.data.objects.new("Camera_Canyon_Recon", cam_data)
        scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # 45mm lens for wide-angle tactical recon drone view
    cam_obj.data.lens = 42.0
    cam_obj.data.clip_start = 10.0
    cam_obj.data.clip_end = 250000.0

    # Camera positioned high above the ridge looking down at ~38° pitch into the canyon trench
    # Location: X = -13,500, Y = 7,500, Z = 7,400 (high altitude overhead)
    # Target: X = -6,800, Y = 14,500, Z = 3,800 (canyon floor winding corridor)
    cam_pos = mathutils.Vector((-13500.0, 7500.0, 7400.0))
    target_pos = mathutils.Vector((-6800.0, 14500.0, 3800.0))
    cam_obj.location = cam_pos
    direction = target_pos - cam_pos
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    # -------------------------------------------------------------------------
    # 5. DIRECTIONAL LIGHTING RIG (STARK TOP GUN TACTICAL CONTRAST)
    # Raking sun catching mountain ridges and leaving canyon floor in deep shadow
    # -------------------------------------------------------------------------
    sun = bpy.data.objects.get("Sun_Tactical")
    if not sun:
        sun_data = bpy.data.lights.new("Sun_Tactical", 'SUN')
        sun = bpy.data.objects.new("Sun_Tactical", sun_data)
        scene.collection.objects.link(sun)
    sun.data.energy = 6.2
    sun.data.color = (0.90, 0.94, 1.0)
    sun.data.use_shadow = False # Direct chiaroscuro without 92km VSM page dropout artifacts
    sun.rotation_euler = (math.radians(52.0), math.radians(24.0), math.radians(-70.0))

    # Ambient Fill (Slate tone)
    fill = bpy.data.objects.get("Sun_Fill")
    if not fill:
        fill_data = bpy.data.lights.new("Sun_Fill", 'SUN')
        fill = bpy.data.objects.new("Sun_Fill", fill_data)
        scene.collection.objects.link(fill)
    fill.data.energy = 1.6
    fill.data.color = (0.28, 0.36, 0.46)
    fill.data.use_shadow = False
    fill.rotation_euler = (math.radians(110.0), math.radians(-20.0), math.radians(110.0))

    # World background
    world = scene.world
    if not world:
        world = bpy.data.worlds.new("W_Tactical")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.015, 0.022, 0.030, 1.0)
        bg.inputs['Strength'].default_value = 0.70

    # Color Management: AgX High Contrast
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.view_settings.exposure = 0.15

    # 3D Viewport pre-configuration
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
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_reference_match.png"))
    scene.render.filepath = out_path
    print(f"[RENDER] Rendering tactical reference match to: {out_path}...")
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    # Also overwrite final master render
    master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved terrain.blend successfully!")

if __name__ == "__main__":
    setup_tactical_recon_scene()
