"""
True Reference Match for Tactical Top Gun Canyon Flight
1. Zero Bump node on BSDF Normal -> 100% eliminates all black diamond/polygon normal artifacts
2. Albedo-based craggy rock fracture and vertical erosion fluting
3. Hairline topographic contour isolines + subtle tactical terrain coordinate grid
4. Low-altitude canyon floor atmospheric haze/smoke in the river trench
5. High-altitude oblique recon camera framing the canyon corridor matching the reference composition
"""

import bpy
import mathutils
import math
import os

def build_true_reference_material():
    mat = bpy.data.materials.get("M_Tactical_Ladakh_Terrain")
    if not mat:
        mat = bpy.data.materials.new("M_Tactical_Ladakh_Terrain")
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # 1. Output & Principled BSDF
    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (2500, 200)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (2150, 200)
    # Specular rim reflections without bump normal inversion
    bsdf.inputs['Roughness'].default_value = 0.80
    bsdf.inputs['Specular IOR Level'].default_value = 0.35
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-2200, 300)

    cam_data = nodes.new('ShaderNodeCameraData')
    cam_data.location = (-2200, -700)

    # -------------------------------------------------------------------------
    # 2. VERTICAL EROSION FLUTING & ROCK CHASM TEXTURE (IN BASE COLOR)
    # Stretched along Z to create natural vertical mountain gullies & cliffs
    # -------------------------------------------------------------------------
    map_strata = nodes.new('ShaderNodeMapping')
    map_strata.location = (-1900, 650)
    # Stretched Z creates vertical drainage channels
    map_strata.inputs['Scale'].default_value = (0.0035, 0.0035, 0.0006)
    links.new(geom.outputs['Position'], map_strata.inputs['Vector'])

    noise_strata = nodes.new('ShaderNodeTexNoise')
    noise_strata.location = (-1650, 650)
    noise_strata.inputs['Scale'].default_value = 1.5
    noise_strata.inputs['Detail'].default_value = 12.0
    noise_strata.inputs['Roughness'].default_value = 0.70
    noise_strata.inputs['Lacunarity'].default_value = 2.2
    noise_strata.inputs['Distortion'].default_value = 0.5
    links.new(map_strata.outputs['Vector'], noise_strata.inputs['Vector'])

    # Meso rock fracture scree (craggy rock texture)
    map_scree = nodes.new('ShaderNodeMapping')
    map_scree.location = (-1900, 300)
    map_scree.inputs['Scale'].default_value = (0.018, 0.018, 0.012)
    links.new(geom.outputs['Position'], map_scree.inputs['Vector'])

    noise_scree = nodes.new('ShaderNodeTexNoise')
    noise_scree.location = (-1650, 300)
    noise_scree.inputs['Scale'].default_value = 2.0
    noise_scree.inputs['Detail'].default_value = 10.0
    noise_scree.inputs['Roughness'].default_value = 0.85
    links.new(map_scree.outputs['Vector'], noise_scree.inputs['Vector'])

    # Combine strata + scree into craggy rock factor
    mix_rock_factor = nodes.new('ShaderNodeMix')
    mix_rock_factor.data_type = 'FLOAT'
    mix_rock_factor.blend_type = 'MIX'
    mix_rock_factor.location = (-1350, 500)
    mix_rock_factor.inputs['Factor'].default_value = 0.55
    links.new(noise_strata.outputs['Fac'], mix_rock_factor.inputs[2])
    links.new(noise_scree.outputs['Fac'], mix_rock_factor.inputs[3])

    # Calibrated Military Recon Rock Palette (Dark Slate to Bone Highlight)
    ramp_rock = nodes.new('ShaderNodeValToRGB')
    ramp_rock.location = (-1050, 500)
    ramp_rock.color_ramp.elements[0].position = 0.20
    ramp_rock.color_ramp.elements[0].color = (0.06, 0.075, 0.09, 1.0) # Deep charcoal gully
    ramp_rock.color_ramp.elements[1].position = 0.52
    ramp_rock.color_ramp.elements[1].color = (0.16, 0.19, 0.23, 1.0) # Slate rock midtone
    elem_high = ramp_rock.color_ramp.elements.new(0.80)
    elem_high.color = (0.34, 0.40, 0.46, 1.0) # Bright weathered ridge crest
    links.new(mix_rock_factor.outputs[0], ramp_rock.inputs['Fac'])

    # -------------------------------------------------------------------------
    # 3. TOPOGRAPHIC CONTOUR ISOLINES (Hairline, delicate elevation contours)
    # -------------------------------------------------------------------------
    sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    sep_pos.location = (-1900, -200)
    links.new(geom.outputs['Position'], sep_pos.inputs['Vector'])

    # 90-meter elevation interval
    div_iso = nodes.new('ShaderNodeMath')
    div_iso.location = (-1650, -200)
    div_iso.operation = 'DIVIDE'
    div_iso.inputs[1].default_value = 90.0
    links.new(sep_pos.outputs['Z'], div_iso.inputs[0])

    fract_iso = nodes.new('ShaderNodeMath')
    fract_iso.location = (-1450, -200)
    fract_iso.operation = 'FRACT'
    links.new(div_iso.outputs['Value'], fract_iso.inputs[0])

    sub_iso = nodes.new('ShaderNodeMath')
    sub_iso.location = (-1250, -200)
    sub_iso.operation = 'SUBTRACT'
    sub_iso.inputs[1].default_value = 0.5
    links.new(fract_iso.outputs['Value'], sub_iso.inputs[0])

    abs_iso = nodes.new('ShaderNodeMath')
    abs_iso.location = (-1050, -200)
    abs_iso.operation = 'ABSOLUTE'
    links.new(sub_iso.outputs['Value'], abs_iso.inputs[0])

    ramp_iso = nodes.new('ShaderNodeValToRGB')
    ramp_iso.location = (-800, -200)
    # Ultra-hairline threshold for delicate contour lines
    ramp_iso.color_ramp.elements[0].position = 0.488
    ramp_iso.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_iso.color_ramp.elements[1].position = 0.50
    ramp_iso.color_ramp.elements[1].color = (0.60, 0.75, 0.85, 1.0) # Delicate cyan-white isoline
    links.new(abs_iso.outputs['Value'], ramp_iso.inputs['Fac'])

    # -------------------------------------------------------------------------
    # 4. SUBTLE TACTICAL WIREFRAME / ELEVATION GRID
    # Seen on mountain slopes in the reference image
    # -------------------------------------------------------------------------
    div_x = nodes.new('ShaderNodeMath')
    div_x.location = (-1650, -500)
    div_x.operation = 'DIVIDE'
    div_x.inputs[1].default_value = 250.0 # 250m grid spacing
    links.new(sep_pos.outputs['X'], div_x.inputs[0])

    fract_x = nodes.new('ShaderNodeMath')
    fract_x.location = (-1450, -500)
    fract_x.operation = 'FRACT'
    links.new(div_x.outputs['Value'], fract_x.inputs[0])

    abs_x = nodes.new('ShaderNodeMath')
    abs_x.location = (-1250, -500)
    abs_x.operation = 'ABSOLUTE'
    sub_x = nodes.new('ShaderNodeMath')
    sub_x.location = (-1050, -500)
    sub_x.operation = 'SUBTRACT'
    sub_x.inputs[1].default_value = 0.5
    links.new(fract_x.outputs['Value'], sub_x.inputs[0])
    links.new(sub_x.outputs['Value'], abs_x.inputs[0])

    ramp_grid = nodes.new('ShaderNodeValToRGB')
    ramp_grid.location = (-800, -500)
    ramp_grid.color_ramp.elements[0].position = 0.485
    ramp_grid.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_grid.color_ramp.elements[1].position = 0.50
    ramp_grid.color_ramp.elements[1].color = (0.25, 0.35, 0.45, 1.0) # Faint grid line
    links.new(abs_x.outputs['Value'], ramp_grid.inputs['Fac'])

    # Combine Isolines + Grid
    mix_hud_lines = nodes.new('ShaderNodeMix')
    mix_hud_lines.data_type = 'RGBA'
    mix_hud_lines.blend_type = 'ADD'
    mix_hud_lines.location = (-500, -300)
    mix_hud_lines.inputs['Factor'].default_value = 0.60
    links.new(ramp_iso.outputs['Color'], mix_hud_lines.inputs[6])
    links.new(ramp_grid.outputs['Color'], mix_hud_lines.inputs[7])

    # Overlay HUD Isolines onto Rock Surface
    mix_surface = nodes.new('ShaderNodeMix')
    mix_surface.data_type = 'RGBA'
    mix_surface.blend_type = 'ADD'
    mix_surface.location = (-200, 200)
    mix_surface.inputs['Factor'].default_value = 0.45
    links.new(ramp_rock.outputs['Color'], mix_surface.inputs[6])
    links.new(mix_hud_lines.outputs[2], mix_surface.inputs[7])

    # -------------------------------------------------------------------------
    # 5. CANYON FLOOR TRENCH FOG & RIVERBED HAZE (Elevation < 3700m)
    # Dense, atmospheric rolling smoke in the canyon trench matching the reference
    # -------------------------------------------------------------------------
    sub_canyon = nodes.new('ShaderNodeMath')
    sub_canyon.location = (-500, -700)
    sub_canyon.operation = 'SUBTRACT'
    sub_canyon.inputs[1].default_value = 3200.0
    links.new(sep_pos.outputs['Z'], sub_canyon.inputs[0])

    div_canyon = nodes.new('ShaderNodeMath')
    div_canyon.location = (-300, -700)
    div_canyon.operation = 'DIVIDE'
    div_canyon.inputs[1].default_value = 900.0
    links.new(sub_canyon.outputs['Value'], div_canyon.inputs[0])

    # Noise for billowy riverbed smoke/fog
    noise_fog = nodes.new('ShaderNodeTexNoise')
    noise_fog.location = (-300, -950)
    noise_fog.inputs['Scale'].default_value = 0.008
    noise_fog.inputs['Detail'].default_value = 4.0
    links.new(geom.outputs['Position'], noise_fog.inputs['Vector'])

    add_fog = nodes.new('ShaderNodeMath')
    add_fog.location = (-80, -700)
    add_fog.operation = 'ADD'
    links.new(div_canyon.outputs['Value'], add_fog.inputs[0])
    links.new(noise_fog.outputs['Fac'], add_fog.inputs[1])

    ramp_canyon_fog = nodes.new('ShaderNodeValToRGB')
    ramp_canyon_fog.location = (150, -700)
    ramp_canyon_fog.color_ramp.elements[0].position = 0.20
    ramp_canyon_fog.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0) # Full fog in river trench
    ramp_canyon_fog.color_ramp.elements[1].position = 0.75
    ramp_canyon_fog.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
    links.new(add_fog.outputs['Value'], ramp_canyon_fog.inputs['Fac'])

    # Mix canyon haze into rock surface
    mix_canyon_haze = nodes.new('ShaderNodeMix')
    mix_canyon_haze.data_type = 'RGBA'
    mix_canyon_haze.blend_type = 'MIX'
    mix_canyon_haze.location = (550, 200)
    mix_canyon_haze.inputs[7].default_value = (0.035, 0.048, 0.060, 1.0) # Atmospheric canyon fog tone
    links.new(ramp_canyon_fog.outputs['Color'], mix_canyon_haze.inputs['Factor'])
    links.new(mix_surface.outputs[2], mix_canyon_haze.inputs[6])

    # -------------------------------------------------------------------------
    # 6. DISTANCE ATMOSPHERE / HORIZON HAZE
    # -------------------------------------------------------------------------
    div_dist = nodes.new('ShaderNodeMath')
    div_dist.location = (550, -300)
    div_dist.operation = 'DIVIDE'
    div_dist.inputs[1].default_value = 80000.0
    links.new(cam_data.outputs['View Distance'], div_dist.inputs[0])

    ramp_dist = nodes.new('ShaderNodeValToRGB')
    ramp_dist.location = (800, -300)
    ramp_dist.color_ramp.elements[0].position = 0.20
    ramp_dist.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_dist.color_ramp.elements[1].position = 0.95
    ramp_dist.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    links.new(div_dist.outputs['Value'], ramp_dist.inputs['Fac'])

    mix_final = nodes.new('ShaderNodeMix')
    mix_final.data_type = 'RGBA'
    mix_final.blend_type = 'MIX'
    mix_final.location = (1150, 200)
    mix_final.inputs[7].default_value = (0.015, 0.022, 0.030, 1.0) # Deep slate horizon
    links.new(ramp_dist.outputs['Color'], mix_final.inputs['Factor'])
    links.new(mix_canyon_haze.outputs[2], mix_final.inputs[6])

    # Final Output to BSDF Base Color
    links.new(mix_final.outputs[2], bsdf.inputs['Base Color'])

    return mat

def configure_true_reference_scene():
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

    # 3. Assign Master Material
    mat = build_true_reference_material()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    # -------------------------------------------------------------------------
    # 4. HIGH-ALTITUDE OBLIQUE RECON CAMERA
    # Looking down the winding gorge corridor matching the reference composition:
    # Foreground ridge at bottom-right, winding river canyon through the middle,
    # and dramatic mountain wall rising on the opposite side
    # -------------------------------------------------------------------------
    cam_obj = bpy.data.objects.get("Camera_Canyon_Recon")
    if not cam_obj:
        cam_data = bpy.data.cameras.new("Camera_Canyon_Recon")
        cam_obj = bpy.data.objects.new("Camera_Canyon_Recon", cam_data)
        scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    cam_obj.data.lens = 40.0
    cam_obj.data.clip_start = 10.0
    cam_obj.data.clip_end = 250000.0

    cam_pos = mathutils.Vector((-14500.0, 9500.0, 6800.0))
    target_pos = mathutils.Vector((-8500.0, 15500.0, 3700.0))
    cam_obj.location = cam_pos
    direction = target_pos - cam_pos
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    # -------------------------------------------------------------------------
    # 5. LIGHTING: TOP GUN CANYON RAKING SUN
    # Strong raking sunlight highlighting rock faces, deep slate shadows in crevices
    # -------------------------------------------------------------------------
    sun = bpy.data.objects.get("Sun_Tactical")
    if not sun:
        sun_data = bpy.data.lights.new("Sun_Tactical", 'SUN')
        sun = bpy.data.objects.new("Sun_Tactical", sun_data)
        scene.collection.objects.link(sun)
    sun.data.energy = 5.8
    sun.data.color = (0.92, 0.96, 1.0)
    sun.data.use_shadow = False # Direct chiaroscuro without shadow map page dropout artifacts
    sun.rotation_euler = (math.radians(50.0), math.radians(22.0), math.radians(-68.0))

    # Ambient Fill
    fill = bpy.data.objects.get("Sun_Fill")
    if not fill:
        fill_data = bpy.data.lights.new("Sun_Fill", 'SUN')
        fill = bpy.data.objects.new("Sun_Fill", fill_data)
        scene.collection.objects.link(fill)
    fill.data.energy = 1.6
    fill.data.color = (0.32, 0.40, 0.50)
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
    scene.view_settings.exposure = 0.12

    # Configure Viewport
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
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_true_match.png"))
    scene.render.filepath = out_path
    print(f"[RENDER] Rendering true reference match to: {out_path}...")
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    # Also update final master render
    master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved terrain.blend successfully!")

if __name__ == "__main__":
    configure_true_reference_scene()
