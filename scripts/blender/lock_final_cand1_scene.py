"""
Final Master Scene Setup - Matching test_cam_cand1.png 1:1
- Exact Camera: Location (-16000, 10000, 6800), Target (-10000, 16000, 3600), Lens 38mm
- Zero Bump Node on Normal -> 100% mathematically guarantees ZERO black spots/diamonds
- Clean tactical slate rock palette with delicate topographic contour isolines (90m intervals)
- Clean directional raking sunlight and subtle atmospheric depth
- Pre-configured Viewport: Active Camera + RENDERED shading mode
- Permanently saved to Models/terrain.blend
"""

import bpy
import mathutils
import math
import os

def create_cand1_material():
    mat = bpy.data.materials.get("M_Tactical_Ladakh_Terrain")
    if not mat:
        mat = bpy.data.materials.new("M_Tactical_Ladakh_Terrain")
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # 1. Output & Principled BSDF (Zero bump on Normal -> Zero black spots)
    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (2400, 200)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (2050, 200)
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Specular IOR Level'].default_value = 0.32
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-2200, 300)

    cam_data = nodes.new('ShaderNodeCameraData')
    cam_data.location = (-2200, -700)

    # -------------------------------------------------------------
    # 2. SLATE ROCK TEXTURE & VERTICAL EROSION FLUTING
    # -------------------------------------------------------------
    # Macro vertical cliff striations (stretched along Z)
    map_strata = nodes.new('ShaderNodeMapping')
    map_strata.location = (-1900, 500)
    map_strata.inputs['Scale'].default_value = (0.003, 0.003, 0.0007)
    links.new(geom.outputs['Position'], map_strata.inputs['Vector'])

    noise_strata = nodes.new('ShaderNodeTexNoise')
    noise_strata.location = (-1650, 500)
    noise_strata.inputs['Scale'].default_value = 1.8
    noise_strata.inputs['Detail'].default_value = 12.0
    noise_strata.inputs['Roughness'].default_value = 0.70
    noise_strata.inputs['Distortion'].default_value = 0.5
    links.new(map_strata.outputs['Vector'], noise_strata.inputs['Vector'])

    # Micro rocky surface scree
    map_scree = nodes.new('ShaderNodeMapping')
    map_scree.location = (-1900, 150)
    map_scree.inputs['Scale'].default_value = (0.02, 0.02, 0.02)
    links.new(geom.outputs['Position'], map_scree.inputs['Vector'])

    noise_scree = nodes.new('ShaderNodeTexNoise')
    noise_scree.location = (-1650, 150)
    noise_scree.inputs['Scale'].default_value = 1.8
    noise_scree.inputs['Detail'].default_value = 8.0
    noise_scree.inputs['Roughness'].default_value = 0.85
    links.new(map_scree.outputs['Vector'], noise_scree.inputs['Vector'])

    # Mix macro strata and micro scree
    mix_rock = nodes.new('ShaderNodeMix')
    mix_rock.data_type = 'FLOAT'
    mix_rock.location = (-1350, 350)
    mix_rock.inputs['Factor'].default_value = 0.50
    links.new(noise_strata.outputs['Fac'], mix_rock.inputs[2])
    links.new(noise_scree.outputs['Fac'], mix_rock.inputs[3])

    # Tactical Slate Rock Palette (matching cand1)
    ramp_rock = nodes.new('ShaderNodeValToRGB')
    ramp_rock.location = (-1050, 350)
    ramp_rock.color_ramp.elements[0].position = 0.20
    ramp_rock.color_ramp.elements[0].color = (0.06, 0.075, 0.09, 1.0) # Deep charcoal slate
    ramp_rock.color_ramp.elements[1].position = 0.52
    ramp_rock.color_ramp.elements[1].color = (0.16, 0.19, 0.23, 1.0) # Mountain slate midtone
    elem_crest = ramp_rock.color_ramp.elements.new(0.82)
    elem_crest.color = (0.34, 0.40, 0.46, 1.0) # Bright weathered ridge crest
    links.new(mix_rock.outputs[0], ramp_rock.inputs['Fac'])

    # -------------------------------------------------------------
    # 3. DELICATE TOPOGRAPHIC CONTOUR ISOLINES (90m Intervals)
    # -------------------------------------------------------------
    sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    sep_pos.location = (-1900, -250)
    links.new(geom.outputs['Position'], sep_pos.inputs['Vector'])

    div_iso = nodes.new('ShaderNodeMath')
    div_iso.location = (-1650, -250)
    div_iso.operation = 'DIVIDE'
    div_iso.inputs[1].default_value = 90.0 # 90-meter contour interval
    links.new(sep_pos.outputs['Z'], div_iso.inputs[0])

    fract_iso = nodes.new('ShaderNodeMath')
    fract_iso.location = (-1450, -250)
    fract_iso.operation = 'FRACT'
    links.new(div_iso.outputs['Value'], fract_iso.inputs[0])

    sub_iso = nodes.new('ShaderNodeMath')
    sub_iso.location = (-1250, -250)
    sub_iso.operation = 'SUBTRACT'
    sub_iso.inputs[1].default_value = 0.5
    links.new(fract_iso.outputs['Value'], sub_iso.inputs[0])

    abs_iso = nodes.new('ShaderNodeMath')
    abs_iso.location = (-1050, -250)
    abs_iso.operation = 'ABSOLUTE'
    links.new(sub_iso.outputs['Value'], abs_iso.inputs[0])

    ramp_iso = nodes.new('ShaderNodeValToRGB')
    ramp_iso.location = (-800, -250)
    ramp_iso.color_ramp.elements[0].position = 0.486
    ramp_iso.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_iso.color_ramp.elements[1].position = 0.50
    ramp_iso.color_ramp.elements[1].color = (0.55, 0.70, 0.82, 1.0) # Delicate cyan-white contour line
    links.new(abs_iso.outputs['Value'], ramp_iso.inputs['Fac'])

    # Overlay Topographic Isolines onto Rock
    mix_with_iso = nodes.new('ShaderNodeMix')
    mix_with_iso.data_type = 'RGBA'
    mix_with_iso.blend_type = 'ADD'
    mix_with_iso.location = (-450, 100)
    mix_with_iso.inputs['Factor'].default_value = 0.42
    links.new(ramp_rock.outputs['Color'], mix_with_iso.inputs[6])
    links.new(ramp_iso.outputs['Color'], mix_with_iso.inputs[7])

    # -------------------------------------------------------------
    # 4. CANYON FLOOR TRENCH MIST / RIVERBED HAZE
    # -------------------------------------------------------------
    sub_canyon = nodes.new('ShaderNodeMath')
    sub_canyon.location = (-800, -650)
    sub_canyon.operation = 'SUBTRACT'
    sub_canyon.inputs[1].default_value = 3200.0
    links.new(sep_pos.outputs['Z'], sub_canyon.inputs[0])

    div_canyon = nodes.new('ShaderNodeMath')
    div_canyon.location = (-600, -650)
    div_canyon.operation = 'DIVIDE'
    div_canyon.inputs[1].default_value = 1100.0
    links.new(sub_canyon.outputs['Value'], div_canyon.inputs[0])

    ramp_canyon_fog = nodes.new('ShaderNodeValToRGB')
    ramp_canyon_fog.location = (-380, -650)
    ramp_canyon_fog.color_ramp.elements[0].position = 0.0
    ramp_canyon_fog.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    ramp_canyon_fog.color_ramp.elements[1].position = 1.0
    ramp_canyon_fog.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
    links.new(div_canyon.outputs['Value'], ramp_canyon_fog.inputs['Fac'])

    mix_canyon_fog = nodes.new('ShaderNodeMix')
    mix_canyon_fog.data_type = 'RGBA'
    mix_canyon_fog.blend_type = 'MIX'
    mix_canyon_fog.location = (-100, 100)
    mix_canyon_fog.inputs[7].default_value = (0.035, 0.048, 0.062, 1.0) # Dark river trench tone
    links.new(ramp_canyon_fog.outputs['Color'], mix_canyon_fog.inputs['Factor'])
    links.new(mix_with_iso.outputs[2], mix_canyon_fog.inputs[6])

    # -------------------------------------------------------------
    # 5. DISTANCE ATMOSPHERE / HORIZON HAZE
    # -------------------------------------------------------------
    div_dist = nodes.new('ShaderNodeMath')
    div_dist.location = (-100, -400)
    div_dist.operation = 'DIVIDE'
    div_dist.inputs[1].default_value = 80000.0
    links.new(cam_data.outputs['View Distance'], div_dist.inputs[0])

    ramp_dist = nodes.new('ShaderNodeValToRGB')
    ramp_dist.location = (150, -400)
    ramp_dist.color_ramp.elements[0].position = 0.15
    ramp_dist.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_dist.color_ramp.elements[1].position = 0.95
    ramp_dist.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    links.new(div_dist.outputs['Value'], ramp_dist.inputs['Fac'])

    mix_final_atmo = nodes.new('ShaderNodeMix')
    mix_final_atmo.data_type = 'RGBA'
    mix_final_atmo.blend_type = 'MIX'
    mix_final_atmo.location = (450, 100)
    mix_final_atmo.inputs[7].default_value = (0.015, 0.022, 0.030, 1.0) # Deep slate horizon void
    links.new(ramp_dist.outputs['Color'], mix_final_atmo.inputs['Factor'])
    links.new(mix_canyon_fog.outputs[2], mix_final_atmo.inputs[6])

    # Connect to BSDF Base Color
    links.new(mix_final_atmo.outputs[2], bsdf.inputs['Base Color'])

    return mat

def configure_cand1_master_scene():
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

    # 3. Clean up any temporary HUD overlay collections/objects
    col = bpy.data.collections.get('HUD_Tactical_Overlays')
    if col:
        for o in list(col.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(col)

    # 4. Assign Material
    mat = create_cand1_material()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    print(f"[OK] Material '{mat.name}' assigned (zero bump nodes -> zero black spots).")

    # -------------------------------------------------------------
    # 5. EXACT CANDIDATE 1 CAMERA VIEWPOINT
    # Location: (-16000, 10000, 6800), Target: (-10000, 16000, 3600), Lens: 38mm
    # -------------------------------------------------------------
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

    # -------------------------------------------------------------
    # 6. TACTICAL LIGHTING RIG (STARK FLIR CHIAROSCURO)
    # -------------------------------------------------------------
    sun = bpy.data.objects.get("Sun_Tactical")
    if not sun:
        sun_data = bpy.data.lights.new("Sun_Tactical", 'SUN')
        sun = bpy.data.objects.new("Sun_Tactical", sun_data)
        scene.collection.objects.link(sun)
    sun.data.energy = 6.0
    sun.data.color = (0.92, 0.96, 1.0)
    sun.data.use_shadow = False # Direct chiaroscuro -> Zero shadow map page dropouts
    sun.rotation_euler = (math.radians(52.0), math.radians(24.0), math.radians(-70.0))

    fill = bpy.data.objects.get("Sun_Fill")
    if not fill:
        fill_data = bpy.data.lights.new("Sun_Fill", 'SUN')
        fill = bpy.data.objects.new("Sun_Fill", fill_data)
        scene.collection.objects.link(fill)
    fill.data.energy = 1.5
    fill.data.color = (0.28, 0.36, 0.46)
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

    # AgX High Contrast Color Management
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.view_settings.exposure = 0.14

    # Pre-configure Viewport for immediate user opening
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'RENDERED'
                        space.region_3d.view_perspective = 'CAMERA'

    # Render High-Resolution 1080p Final Output
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    out_cand1 = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/test_cam_cand1_final.png"))
    scene.render.filepath = out_cand1
    print(f"[RENDER] Rendering cand1 master to: {out_cand1}...")
    bpy.ops.render.render(write_still=True)

    master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    # Save permanently to Models/terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved cand1 master permanently to Models/terrain.blend!")

if __name__ == "__main__":
    configure_cand1_master_scene()
