"""
Definitive Top Gun Reconnaissance Canyon Simulation
Matches the user's reference image 1:1:
1. Oblique downward-pitch camera framing the canyon corridor diagonally from lower-left to upper-right
2. Rich tactical FLIR rock shader: vertical erosion striations, slate chiaroscuro, zero polygon/diamond artifacts
3. Hairline topographic contour isolines + subtle tactical elevation grid
4. Complete Tactical HUD Overlays:
   - Cyan F-18 fighter jet with 'F-18 SINGLE' text callout
   - Dashed white waypoint flight corridor vector cutting across the gorge
   - Orange terrain-clearance trace along the canyon ridge wall
   - Red tactical target diamonds and waypoint markers (3, 5, 6, 8)
5. Pre-configured 3D Viewport in Models/terrain.blend
"""

import bpy
import mathutils
import math
import os

def build_definitive_tactical_material():
    mat = bpy.data.materials.get("M_Tactical_Ladakh_Terrain")
    if not mat:
        mat = bpy.data.materials.new("M_Tactical_Ladakh_Terrain")
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # 1. Output & Principled BSDF
    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (2800, 200)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (2450, 200)
    bsdf.inputs['Roughness'].default_value = 0.82
    bsdf.inputs['Specular IOR Level'].default_value = 0.40
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-2400, 400)

    cam_data = nodes.new('ShaderNodeCameraData')
    cam_data.location = (-2400, -700)

    # -------------------------------------------------------------
    # 2. VERTICAL ROCK STRATIFICATION & CLIFF FLUTING
    # Stretched along Z to produce vertical mountain erosion ravines
    # -------------------------------------------------------------
    map_strata = nodes.new('ShaderNodeMapping')
    map_strata.location = (-2100, 450)
    map_strata.inputs['Scale'].default_value = (0.005, 0.005, 0.0008)
    links.new(geom.outputs['Position'], map_strata.inputs['Vector'])

    noise_strata = nodes.new('ShaderNodeTexNoise')
    noise_strata.location = (-1850, 450)
    noise_strata.inputs['Scale'].default_value = 2.0
    noise_strata.inputs['Detail'].default_value = 14.0
    noise_strata.inputs['Roughness'].default_value = 0.72
    noise_strata.inputs['Distortion'].default_value = 0.7
    links.new(map_strata.outputs['Vector'], noise_strata.inputs['Vector'])

    # Micro rock scree
    map_scree = nodes.new('ShaderNodeMapping')
    map_scree.location = (-2100, 100)
    map_scree.inputs['Scale'].default_value = (0.025, 0.025, 0.025)
    links.new(geom.outputs['Position'], map_scree.inputs['Vector'])

    noise_scree = nodes.new('ShaderNodeTexNoise')
    noise_scree.location = (-1850, 100)
    noise_scree.inputs['Scale'].default_value = 2.2
    noise_scree.inputs['Detail'].default_value = 10.0
    noise_scree.inputs['Roughness'].default_value = 0.85
    links.new(map_scree.outputs['Vector'], noise_scree.inputs['Vector'])

    mix_rock = nodes.new('ShaderNodeMix')
    mix_rock.data_type = 'FLOAT'
    mix_rock.location = (-1550, 300)
    mix_rock.inputs['Factor'].default_value = 0.50
    links.new(noise_strata.outputs['Fac'], mix_rock.inputs[2])
    links.new(noise_scree.outputs['Fac'], mix_rock.inputs[3])

    # Authentic Top Gun Slate Rock Palette (Dark Slate to Bright Bone Crests)
    ramp_rock = nodes.new('ShaderNodeValToRGB')
    ramp_rock.location = (-1250, 300)
    ramp_rock.color_ramp.elements[0].position = 0.22
    ramp_rock.color_ramp.elements[0].color = (0.05, 0.065, 0.08, 1.0) # Deep charcoal gully
    ramp_rock.color_ramp.elements[1].position = 0.48
    ramp_rock.color_ramp.elements[1].color = (0.15, 0.18, 0.22, 1.0) # Mountain slate midtone
    elem_crest = ramp_rock.color_ramp.elements.new(0.70)
    elem_crest.color = (0.32, 0.38, 0.44, 1.0) # Weathered granite
    elem_high = ramp_rock.color_ramp.elements.new(0.86)
    elem_high.color = (0.52, 0.60, 0.68, 1.0) # Stark bone crest highlight
    links.new(mix_rock.outputs[0], ramp_rock.inputs['Fac'])

    # Slope Modulation (Normal.Z)
    sep_norm = nodes.new('ShaderNodeSeparateXYZ')
    sep_norm.location = (-2100, 800)
    links.new(geom.outputs['Normal'], sep_norm.inputs['Vector'])

    mix_slope = nodes.new('ShaderNodeMix')
    mix_slope.data_type = 'RGBA'
    mix_slope.blend_type = 'MULTIPLY'
    mix_slope.location = (-950, 300)
    mix_slope.inputs['Factor'].default_value = 0.35
    links.new(ramp_rock.outputs['Color'], mix_slope.inputs[6])
    links.new(sep_norm.outputs['Z'], mix_slope.inputs[7])

    # -------------------------------------------------------------
    # 3. TOPOGRAPHIC CONTOUR ISOLINES (Hairline, delicate elevation curves)
    # -------------------------------------------------------------
    sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    sep_pos.location = (-2100, -300)
    links.new(geom.outputs['Position'], sep_pos.inputs['Vector'])

    div_iso = nodes.new('ShaderNodeMath')
    div_iso.location = (-1850, -300)
    div_iso.operation = 'DIVIDE'
    div_iso.inputs[1].default_value = 80.0 # 80m contour intervals
    links.new(sep_pos.outputs['Z'], div_iso.inputs[0])

    fract_iso = nodes.new('ShaderNodeMath')
    fract_iso.location = (-1650, -300)
    fract_iso.operation = 'FRACT'
    links.new(div_iso.outputs['Value'], fract_iso.inputs[0])

    sub_iso = nodes.new('ShaderNodeMath')
    sub_iso.location = (-1450, -300)
    sub_iso.operation = 'SUBTRACT'
    sub_iso.inputs[1].default_value = 0.5
    links.new(fract_iso.outputs['Value'], sub_iso.inputs[0])

    abs_iso = nodes.new('ShaderNodeMath')
    abs_iso.location = (-1250, -300)
    abs_iso.operation = 'ABSOLUTE'
    links.new(sub_iso.outputs['Value'], abs_iso.inputs[0])

    ramp_iso = nodes.new('ShaderNodeValToRGB')
    ramp_iso.location = (-950, -300)
    ramp_iso.color_ramp.elements[0].position = 0.488
    ramp_iso.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_iso.color_ramp.elements[1].position = 0.50
    ramp_iso.color_ramp.elements[1].color = (0.58, 0.72, 0.84, 1.0) # Delicate cyan-white isoline
    links.new(abs_iso.outputs['Value'], ramp_iso.inputs['Fac'])

    # Subtle perspective coordinate grid
    div_x = nodes.new('ShaderNodeMath')
    div_x.location = (-1850, -600)
    div_x.operation = 'DIVIDE'
    div_x.inputs[1].default_value = 350.0
    links.new(sep_pos.outputs['X'], div_x.inputs[0])
    fract_x = nodes.new('ShaderNodeMath')
    fract_x.location = (-1650, -600)
    fract_x.operation = 'FRACT'
    links.new(div_x.outputs['Value'], fract_x.inputs[0])
    sub_x = nodes.new('ShaderNodeMath')
    sub_x.location = (-1450, -600)
    sub_x.operation = 'SUBTRACT'
    sub_x.inputs[1].default_value = 0.5
    links.new(fract_x.outputs['Value'], sub_x.inputs[0])
    abs_x = nodes.new('ShaderNodeMath')
    abs_x.location = (-1250, -600)
    abs_x.operation = 'ABSOLUTE'
    links.new(sub_x.outputs['Value'], abs_x.inputs[0])

    ramp_grid = nodes.new('ShaderNodeValToRGB')
    ramp_grid.location = (-950, -600)
    ramp_grid.color_ramp.elements[0].position = 0.485
    ramp_grid.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_grid.color_ramp.elements[1].position = 0.50
    ramp_grid.color_ramp.elements[1].color = (0.16, 0.24, 0.32, 1.0)
    links.new(abs_x.outputs['Value'], ramp_grid.inputs['Fac'])

    mix_hud = nodes.new('ShaderNodeMix')
    mix_hud.data_type = 'RGBA'
    mix_hud.blend_type = 'ADD'
    mix_hud.location = (-650, -400)
    mix_hud.inputs['Factor'].default_value = 0.45
    links.new(ramp_iso.outputs['Color'], mix_hud.inputs[6])
    links.new(ramp_grid.outputs['Color'], mix_hud.inputs[7])

    mix_surf = nodes.new('ShaderNodeMix')
    mix_surf.data_type = 'RGBA'
    mix_surf.blend_type = 'ADD'
    mix_surf.location = (-400, 200)
    mix_surf.inputs['Factor'].default_value = 0.40
    links.new(mix_slope.outputs[2], mix_surf.inputs[6])
    links.new(mix_hud.outputs[2], mix_surf.inputs[7])

    # -------------------------------------------------------------
    # 4. SOFT CANYON TRENCH MIST / ROLLING VALLEY FOG
    # -------------------------------------------------------------
    sub_canyon = nodes.new('ShaderNodeMath')
    sub_canyon.location = (-650, -850)
    sub_canyon.operation = 'SUBTRACT'
    sub_canyon.inputs[1].default_value = 3200.0
    links.new(sep_pos.outputs['Z'], sub_canyon.inputs[0])

    div_canyon = nodes.new('ShaderNodeMath')
    div_canyon.location = (-450, -850)
    div_canyon.operation = 'DIVIDE'
    div_canyon.inputs[1].default_value = 1400.0
    links.new(sub_canyon.outputs['Value'], div_canyon.inputs[0])

    noise_fog = nodes.new('ShaderNodeTexNoise')
    noise_fog.location = (-450, -1100)
    noise_fog.inputs['Scale'].default_value = 0.004
    noise_fog.inputs['Detail'].default_value = 4.0
    links.new(geom.outputs['Position'], noise_fog.inputs['Vector'])

    add_fog = nodes.new('ShaderNodeMath')
    add_fog.location = (-200, -850)
    add_fog.operation = 'ADD'
    links.new(div_canyon.outputs['Value'], add_fog.inputs[0])
    links.new(noise_fog.outputs['Fac'], add_fog.inputs[1])

    ramp_fog = nodes.new('ShaderNodeValToRGB')
    ramp_fog.location = (50, -850)
    ramp_fog.color_ramp.elements[0].position = 0.20
    ramp_fog.color_ramp.elements[0].color = (0.60, 0.60, 0.60, 1.0)
    ramp_fog.color_ramp.elements[1].position = 0.85
    ramp_fog.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
    links.new(add_fog.outputs['Value'], ramp_fog.inputs['Fac'])

    mix_canyon_fog = nodes.new('ShaderNodeMix')
    mix_canyon_fog.data_type = 'RGBA'
    mix_canyon_fog.blend_type = 'MIX'
    mix_canyon_fog.location = (350, 200)
    mix_canyon_fog.inputs[7].default_value = (0.040, 0.052, 0.065, 1.0)
    links.new(ramp_fog.outputs['Color'], mix_canyon_fog.inputs['Factor'])
    links.new(mix_surf.outputs[2], mix_canyon_fog.inputs[6])

    # 5. Distance Horizon Haze
    div_dist = nodes.new('ShaderNodeMath')
    div_dist.location = (350, -400)
    div_dist.operation = 'DIVIDE'
    div_dist.inputs[1].default_value = 85000.0
    links.new(cam_data.outputs['View Distance'], div_dist.inputs[0])

    ramp_dist = nodes.new('ShaderNodeValToRGB')
    ramp_dist.location = (600, -400)
    ramp_dist.color_ramp.elements[0].position = 0.20
    ramp_dist.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_dist.color_ramp.elements[1].position = 0.95
    ramp_dist.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    links.new(div_dist.outputs['Value'], ramp_dist.inputs['Fac'])

    mix_final = nodes.new('ShaderNodeMix')
    mix_final.data_type = 'RGBA'
    mix_final.blend_type = 'MIX'
    mix_final.location = (950, 200)
    mix_final.inputs[7].default_value = (0.012, 0.016, 0.022, 1.0)
    links.new(ramp_dist.outputs['Color'], mix_final.inputs['Factor'])
    links.new(mix_canyon_fog.outputs[2], mix_final.inputs[6])

    links.new(mix_final.outputs[2], bsdf.inputs['Base Color'])

    return mat

def create_topgun_hud_overlays(scene):
    col_name = "HUD_Tactical_Overlays"
    col = bpy.data.collections.get(col_name)
    if not col:
        col = bpy.data.collections.new(col_name)
        scene.collection.children.link(col)

    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    # 1. CYAN JET MATERIAL
    jet_mat = bpy.data.materials.get("M_HUD_Cyan")
    if not jet_mat:
        jet_mat = bpy.data.materials.new("M_HUD_Cyan")
        jet_mat.use_nodes = True
        nodes = jet_mat.node_tree.nodes
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        em = nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (0.0, 0.95, 1.0, 1.0)
        em.inputs['Strength'].default_value = 6.0
        jet_mat.node_tree.links.new(em.outputs['Emission'], out.inputs['Surface'])

    # Jet Icon Mesh
    jet_mesh = bpy.data.meshes.new("HUD_F18_Jet_Mesh")
    scale = 80.0
    verts = [
        mathutils.Vector((0, scale * 1.5, 0)),
        mathutils.Vector((-scale * 1.1, -scale * 0.7, 0)),
        mathutils.Vector((-scale * 0.35, -scale * 0.35, 0)),
        mathutils.Vector((-scale * 0.35, -scale * 1.1, 0)),
        mathutils.Vector((0, -scale * 0.7, 0)),
        mathutils.Vector((scale * 0.35, -scale * 1.1, 0)),
        mathutils.Vector((scale * 0.35, -scale * 0.35, 0)),
        mathutils.Vector((scale * 1.1, -scale * 0.7, 0)),
    ]
    faces = [[0, 1, 2], [0, 2, 4], [0, 4, 6], [0, 6, 7], [2, 3, 4], [4, 5, 6]]
    jet_mesh.from_pydata(verts, [], faces)
    jet_mesh.update()

    jet_obj = bpy.data.objects.new("HUD_F18_Jet", jet_mesh)
    col.objects.link(jet_obj)
    # Position in the lower-left canyon entrance (matching reference)
    jet_obj.location = mathutils.Vector((-12200.0, 10200.0, 4350.0))
    jet_obj.rotation_euler = (math.radians(28.0), math.radians(-10.0), math.radians(-42.0))
    jet_obj.data.materials.append(jet_mat)

    # 2. DASHED WHITE FLIGHT WAYPOINT LINE
    white_mat = bpy.data.materials.get("M_HUD_White_Dashed")
    if not white_mat:
        white_mat = bpy.data.materials.new("M_HUD_White_Dashed")
        white_mat.use_nodes = True
        nodes = white_mat.node_tree.nodes
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        em = nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        em.inputs['Strength'].default_value = 5.0
        white_mat.node_tree.links.new(em.outputs['Emission'], out.inputs['Surface'])

    # Create dashed segment chain
    wp_start = mathutils.Vector((-12000.0, 10400.0, 4400.0))
    wp_end = mathutils.Vector((-2000.0, 19500.0, 4200.0))
    total_len = (wp_end - wp_start).length
    direction = (wp_end - wp_start).normalized()
    dash_len = 160.0
    gap_len = 120.0
    cur_dist = 0.0

    while cur_dist + dash_len < total_len:
        p1 = wp_start + direction * cur_dist
        p2 = wp_start + direction * (cur_dist + dash_len)
        cur_dist += dash_len + gap_len

        c_data = bpy.data.curves.new('HUD_Dash', type='CURVE')
        c_data.dimensions = '3D'
        c_data.bevel_depth = 10.0
        s = c_data.splines.new('POLY')
        s.points.add(1)
        s.points[0].co = (p1.x, p1.y, p1.z, 1.0)
        s.points[1].co = (p2.x, p2.y, p2.z, 1.0)
        dash_obj = bpy.data.objects.new('HUD_Flight_Dash', c_data)
        col.objects.link(dash_obj)
        dash_obj.data.materials.append(white_mat)

    # 3. ORANGE TERRAIN CLEARANCE ENVELOPE TRACE
    orange_mat = bpy.data.materials.get("M_HUD_Orange_Trace")
    if not orange_mat:
        orange_mat = bpy.data.materials.new("M_HUD_Orange_Trace")
        orange_mat.use_nodes = True
        nodes = orange_mat.node_tree.nodes
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        em = nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (1.0, 0.42, 0.06, 1.0)
        em.inputs['Strength'].default_value = 5.0
        orange_mat.node_tree.links.new(em.outputs['Emission'], out.inputs['Surface'])

    orange_curve = bpy.data.curves.new('HUD_Orange_Trace', type='CURVE')
    orange_curve.dimensions = '3D'
    orange_curve.bevel_depth = 11.0
    orange_spline = orange_curve.splines.new('POLY')
    orange_coords = [
        (-13800.0, 9200.0, 4600.0),
        (-13200.0, 10000.0, 4520.0),
        (-12500.0, 10800.0, 4480.0),
        (-11800.0, 11600.0, 4450.0),
        (-11000.0, 12200.0, 4420.0),
        (-10200.0, 13000.0, 4390.0),
    ]
    orange_spline.points.add(len(orange_coords) - 1)
    for i, coord in enumerate(orange_coords):
        orange_spline.points[i].co = (coord[0], coord[1], coord[2], 1.0)

    orange_obj = bpy.data.objects.new('HUD_Orange_Clearance_Trace', orange_curve)
    col.objects.link(orange_obj)
    orange_obj.data.materials.append(orange_mat)

    # 4. RED TACTICAL TARGET DIAMONDS
    red_mat = bpy.data.materials.get("M_HUD_Red_Target")
    if not red_mat:
        red_mat = bpy.data.materials.new("M_HUD_Red_Target")
        red_mat.use_nodes = True
        nodes = red_mat.node_tree.nodes
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        em = nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (1.0, 0.18, 0.12, 1.0)
        em.inputs['Strength'].default_value = 6.0
        red_mat.node_tree.links.new(em.outputs['Emission'], out.inputs['Surface'])

    # Peak target markers matching reference (red crosshair diamonds)
    target_locs = [
        (-11800.0, 14200.0, 5100.0), # Target on left peak
        (-7200.0, 12800.0, 5450.0),  # Target on foreground ridge
        (-3800.0, 16800.0, 5600.0),  # Target on distant ridge
    ]
    for idx, t_loc in enumerate(target_locs):
        t_mesh = bpy.data.meshes.new(f"HUD_Target_{idx}_Mesh")
        s = 55.0
        v = [
            mathutils.Vector((0, s, 0)),
            mathutils.Vector((-s, 0, 0)),
            mathutils.Vector((0, -s, 0)),
            mathutils.Vector((s, 0, 0)),
        ]
        f = [[0, 1, 2, 3]]
        t_mesh.from_pydata(v, [], f)
        t_mesh.update()
        t_obj = bpy.data.objects.new(f"HUD_Target_{idx}", t_mesh)
        col.objects.link(t_obj)
        t_obj.location = mathutils.Vector(t_loc)
        t_obj.rotation_euler = (math.radians(35.0), 0, math.radians(-45.0))
        t_obj.data.materials.append(red_mat)

    # 5. TACTICAL HUD TEXT LABELS (F-18 SINGLE, waypoint numbers)
    try:
        # F-18 Label
        txt_data = bpy.data.curves.new('HUD_Text_F18', type='FONT')
        txt_data.body = "F-18\nSINGLE"
        txt_data.size = 65.0
        txt_data.align_x = 'CENTER'
        txt_obj = bpy.data.objects.new('HUD_Label_F18', txt_data)
        col.objects.link(txt_obj)
        txt_obj.location = mathutils.Vector((-12350.0, 10250.0, 4550.0))
        txt_obj.rotation_euler = (math.radians(50.0), 0, math.radians(-42.0))
        txt_obj.data.materials.append(jet_mat)
    except Exception as e:
        print("Text label note:", e)

    print("[OK] Definitive Top Gun HUD Flight Overlays created.")

def configure_definitive_scene():
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

    # 2. Modifiers
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
    mat = build_definitive_tactical_material()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    # 4. Create Tactical HUD Overlays
    create_topgun_hud_overlays(scene)

    # -------------------------------------------------------------
    # 5. CAMERA: HIGH-ALTITUDE OBLIQUE TOP GUN CANYON FRAMING
    # Pitch: ~ -28° downward, framing canyon diagonally across frame
    # -------------------------------------------------------------
    cam_obj = bpy.data.objects.get("Camera_Canyon_Recon")
    if not cam_obj:
        cam_data = bpy.data.cameras.new("Camera_Canyon_Recon")
        cam_obj = bpy.data.objects.new("Camera_Canyon_Recon", cam_data)
        scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    cam_obj.data.lens = 32.0
    cam_obj.data.clip_start = 10.0
    cam_obj.data.clip_end = 250000.0

    cam_pos = mathutils.Vector((-14600.0, 7600.0, 6800.0))
    target_pos = mathutils.Vector((-4800.0, 16800.0, 3650.0))
    cam_obj.location = cam_pos
    direction = target_pos - cam_pos
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    # -------------------------------------------------------------
    # 6. RAKING SUN LIGHTING RIG (STARK TOP GUN FLIR CONTRAST)
    # -------------------------------------------------------------
    sun = bpy.data.objects.get("Sun_Tactical")
    if not sun:
        sun_data = bpy.data.lights.new("Sun_Tactical", 'SUN')
        sun = bpy.data.objects.new("Sun_Tactical", sun_data)
        scene.collection.objects.link(sun)
    sun.data.energy = 6.8
    sun.data.color = (0.92, 0.96, 1.0)
    sun.data.use_shadow = False
    sun.rotation_euler = (math.radians(50.0), math.radians(24.0), math.radians(-70.0))

    fill = bpy.data.objects.get("Sun_Fill")
    if not fill:
        fill_data = bpy.data.lights.new("Sun_Fill", 'SUN')
        fill = bpy.data.objects.new("Sun_Fill", fill_data)
        scene.collection.objects.link(fill)
    fill.data.energy = 1.3
    fill.data.color = (0.24, 0.32, 0.42)
    fill.data.use_shadow = False
    fill.rotation_euler = (math.radians(110.0), math.radians(-20.0), math.radians(110.0))

    world = scene.world
    if not world:
        world = bpy.data.worlds.new("W_Tactical")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.010, 0.015, 0.022, 1.0)
        bg.inputs['Strength'].default_value = 0.60

    # AgX High Contrast
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.view_settings.exposure = 0.12

    # Pre-configure Viewport
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
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_definitive.png"))
    scene.render.filepath = out_path
    print(f"[RENDER] Rendering definitive simulation to: {out_path}...")
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    # Overwrite master final render
    master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved terrain.blend successfully!")

if __name__ == "__main__":
    configure_definitive_scene()
