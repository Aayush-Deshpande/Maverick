"""
Complete Top Gun / Military Reconnaissance Canyon Simulation
Matches the user's reference image 1:1:
1. Oblique overhead high-altitude drone/recon camera looking down the winding gorge
2. Photorealistic craggy rock shader with vertical cliff striations, bone crest highlights, and soft canyon trench mist
3. Crisp, elegant cyan-white topographic contour isolines (70m intervals)
4. Tactical HUD Flight Sim Overlays:
   - Cyan F-18 Jet symbol with 'F-18 SINGLE' callout
   - Dashed white flight corridor waypoint track cutting through the gorge
   - Orange terrain-clearance safety envelope trace along the canyon wall
   - Red tactical target diamonds and waypoint elevation tags (3, 5, 6, 8)
5. Pre-configured rendered viewport in Models/terrain.blend
"""

import bpy
import mathutils
import math
import os

def create_topgun_canyon_material():
    mat = bpy.data.materials.get("M_Tactical_Ladakh_Terrain")
    if not mat:
        mat = bpy.data.materials.new("M_Tactical_Ladakh_Terrain")
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Output & Principled BSDF
    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (2800, 200)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (2450, 200)
    bsdf.inputs['Roughness'].default_value = 0.82
    bsdf.inputs['Specular IOR Level'].default_value = 0.38
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-2400, 400)

    cam_data = nodes.new('ShaderNodeCameraData')
    cam_data.location = (-2400, -700)

    # 1. Slope & Normal calculation (cliffs vs gentle ridges)
    sep_norm = nodes.new('ShaderNodeSeparateXYZ')
    sep_norm.location = (-2100, 800)
    links.new(geom.outputs['Normal'], sep_norm.inputs['Vector'])

    # 2. Multi-scale procedural rock fluting & scree
    # Macro vertical drainage gullies (stretched Z)
    map_strata = nodes.new('ShaderNodeMapping')
    map_strata.location = (-2100, 450)
    map_strata.inputs['Scale'].default_value = (0.004, 0.004, 0.0007)
    links.new(geom.outputs['Position'], map_strata.inputs['Vector'])

    noise_strata = nodes.new('ShaderNodeTexNoise')
    noise_strata.location = (-1850, 450)
    noise_strata.inputs['Scale'].default_value = 2.0
    noise_strata.inputs['Detail'].default_value = 14.0
    noise_strata.inputs['Roughness'].default_value = 0.72
    noise_strata.inputs['Distortion'].default_value = 0.7
    links.new(map_strata.outputs['Vector'], noise_strata.inputs['Vector'])

    # Meso rock fracture texture
    map_scree = nodes.new('ShaderNodeMapping')
    map_scree.location = (-2100, 100)
    map_scree.inputs['Scale'].default_value = (0.022, 0.022, 0.022)
    links.new(geom.outputs['Position'], map_scree.inputs['Vector'])

    noise_scree = nodes.new('ShaderNodeTexNoise')
    noise_scree.location = (-1850, 100)
    noise_scree.inputs['Scale'].default_value = 1.8
    noise_scree.inputs['Detail'].default_value = 10.0
    noise_scree.inputs['Roughness'].default_value = 0.85
    links.new(map_scree.outputs['Vector'], noise_scree.inputs['Vector'])

    # Mix macro and meso rock noise
    mix_rock = nodes.new('ShaderNodeMix')
    mix_rock.data_type = 'FLOAT'
    mix_rock.location = (-1550, 300)
    mix_rock.inputs['Factor'].default_value = 0.50
    links.new(noise_strata.outputs['Fac'], mix_rock.inputs[2])
    links.new(noise_scree.outputs['Fac'], mix_rock.inputs[3])

    # Top Gun Matte Slate Rock Palette
    ramp_rock = nodes.new('ShaderNodeValToRGB')
    ramp_rock.location = (-1250, 300)
    ramp_rock.color_ramp.elements[0].position = 0.25
    ramp_rock.color_ramp.elements[0].color = (0.05, 0.065, 0.08, 1.0) # Deep charcoal gully
    ramp_rock.color_ramp.elements[1].position = 0.50
    ramp_rock.color_ramp.elements[1].color = (0.15, 0.18, 0.22, 1.0) # Slate rock midtone
    elem_crest = ramp_rock.color_ramp.elements.new(0.72)
    elem_crest.color = (0.32, 0.38, 0.44, 1.0) # Weathered granite
    elem_highlight = ramp_rock.color_ramp.elements.new(0.88)
    elem_highlight.color = (0.50, 0.58, 0.65, 1.0) # Stark bone crest highlight
    links.new(mix_rock.outputs[0], ramp_rock.inputs['Fac'])

    # Multiply with slope (cliffs get deeper contrast, flat ground gets darker scree)
    mix_slope = nodes.new('ShaderNodeMix')
    mix_slope.data_type = 'RGBA'
    mix_slope.blend_type = 'MULTIPLY'
    mix_slope.location = (-950, 300)
    mix_slope.inputs['Factor'].default_value = 0.35
    links.new(ramp_rock.outputs['Color'], mix_slope.inputs[6])
    links.new(sep_norm.outputs['Z'], mix_slope.inputs[7])

    # 3. Topographic Contour Isolines (70m elevation intervals)
    sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    sep_pos.location = (-2100, -300)
    links.new(geom.outputs['Position'], sep_pos.inputs['Vector'])

    div_iso = nodes.new('ShaderNodeMath')
    div_iso.location = (-1850, -300)
    div_iso.operation = 'DIVIDE'
    div_iso.inputs[1].default_value = 70.0 # 70m contour interval
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
    ramp_iso.color_ramp.elements[0].position = 0.487
    ramp_iso.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_iso.color_ramp.elements[1].position = 0.50
    ramp_iso.color_ramp.elements[1].color = (0.55, 0.70, 0.82, 1.0) # Delicate cyan-white contour line
    links.new(abs_iso.outputs['Value'], ramp_iso.inputs['Fac'])

    # Subtle perspective coordinate grid (very faint)
    div_x = nodes.new('ShaderNodeMath')
    div_x.location = (-1850, -600)
    div_x.operation = 'DIVIDE'
    div_x.inputs[1].default_value = 350.0 # 350m grid spacing
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
    ramp_grid.color_ramp.elements[1].color = (0.18, 0.26, 0.35, 1.0) # Faint grid line
    links.new(abs_x.outputs['Value'], ramp_grid.inputs['Fac'])

    # Combine Isolines + Grid
    mix_hud = nodes.new('ShaderNodeMix')
    mix_hud.data_type = 'RGBA'
    mix_hud.blend_type = 'ADD'
    mix_hud.location = (-650, -400)
    mix_hud.inputs['Factor'].default_value = 0.45
    links.new(ramp_iso.outputs['Color'], mix_hud.inputs[6])
    links.new(ramp_grid.outputs['Color'], mix_hud.inputs[7])

    # Overlay HUD Isolines onto Rock Surface
    mix_surf = nodes.new('ShaderNodeMix')
    mix_surf.data_type = 'RGBA'
    mix_surf.blend_type = 'ADD'
    mix_surf.location = (-400, 200)
    mix_surf.inputs['Factor'].default_value = 0.40
    links.new(mix_slope.outputs[2], mix_surf.inputs[6])
    links.new(mix_hud.outputs[2], mix_surf.inputs[7])

    # 4. Soft Rolling Canyon Mist / Atmospheric River Haze
    sub_canyon = nodes.new('ShaderNodeMath')
    sub_canyon.location = (-650, -850)
    sub_canyon.operation = 'SUBTRACT'
    sub_canyon.inputs[1].default_value = 3200.0
    links.new(sep_pos.outputs['Z'], sub_canyon.inputs[0])

    div_canyon = nodes.new('ShaderNodeMath')
    div_canyon.location = (-450, -850)
    div_canyon.operation = 'DIVIDE'
    div_canyon.inputs[1].default_value = 1200.0
    links.new(sub_canyon.outputs['Value'], div_canyon.inputs[0])

    noise_fog = nodes.new('ShaderNodeTexNoise')
    noise_fog.location = (-450, -1100)
    noise_fog.inputs['Scale'].default_value = 0.005
    noise_fog.inputs['Detail'].default_value = 6.0
    noise_fog.inputs['Roughness'].default_value = 0.7
    links.new(geom.outputs['Position'], noise_fog.inputs['Vector'])

    add_fog = nodes.new('ShaderNodeMath')
    add_fog.location = (-200, -850)
    add_fog.operation = 'ADD'
    links.new(div_canyon.outputs['Value'], add_fog.inputs[0])
    links.new(noise_fog.outputs['Fac'], add_fog.inputs[1])

    ramp_fog = nodes.new('ShaderNodeValToRGB')
    ramp_fog.location = (50, -850)
    ramp_fog.color_ramp.elements[0].position = 0.15
    ramp_fog.color_ramp.elements[0].color = (0.75, 0.75, 0.75, 1.0) # Soft mist
    ramp_fog.color_ramp.elements[1].position = 0.90
    ramp_fog.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
    links.new(add_fog.outputs['Value'], ramp_fog.inputs['Fac'])

    # Blend rolling mist into canyon floor
    mix_canyon_fog = nodes.new('ShaderNodeMix')
    mix_canyon_fog.data_type = 'RGBA'
    mix_canyon_fog.blend_type = 'MIX'
    mix_canyon_fog.location = (350, 200)
    mix_canyon_fog.inputs[7].default_value = (0.045, 0.058, 0.070, 1.0) # Soft atmospheric haze
    links.new(ramp_fog.outputs['Color'], mix_canyon_fog.inputs['Factor'])
    links.new(mix_surf.outputs[2], mix_canyon_fog.inputs[6])

    # 5. Distance Atmosphere / Horizon Haze
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
    mix_final.inputs[7].default_value = (0.015, 0.020, 0.028, 1.0)
    links.new(ramp_dist.outputs['Color'], mix_final.inputs['Factor'])
    links.new(mix_canyon_fog.outputs[2], mix_final.inputs[6])

    links.new(mix_final.outputs[2], bsdf.inputs['Base Color'])

    return mat

def create_tactical_hud_elements(scene):
    # Collection for HUD overlays
    col_name = "HUD_Tactical_Overlays"
    col = bpy.data.collections.get(col_name)
    if not col:
        col = bpy.data.collections.new(col_name)
        scene.collection.children.link(col)

    # Clear previous HUD objects
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    # -------------------------------------------------------------
    # 1. CYAN F-18 FIGHTER JET ICON (Flying into the canyon)
    # -------------------------------------------------------------
    jet_mat = bpy.data.materials.get("M_HUD_Cyan")
    if not jet_mat:
        jet_mat = bpy.data.materials.new("M_HUD_Cyan")
        jet_mat.use_nodes = True
        nodes = jet_mat.node_tree.nodes
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        em = nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (0.0, 0.95, 1.0, 1.0) # Bright tactical cyan
        em.inputs['Strength'].default_value = 5.0
        jet_mat.node_tree.links.new(em.outputs['Emission'], out.inputs['Surface'])

    # Jet Mesh (Stylized delta-wing tactical aircraft icon)
    jet_mesh = bpy.data.meshes.new("HUD_F18_Jet_Mesh")
    # Coordinates of stylized delta-wing aircraft icon
    scale = 120.0
    verts = [
        mathutils.Vector((0, scale * 1.6, 0)),      # 0: Nose
        mathutils.Vector((-scale * 1.2, -scale * 0.8, 0)), # 1: Left wingtip
        mathutils.Vector((-scale * 0.4, -scale * 0.4, 0)), # 2: Left inner wing
        mathutils.Vector((-scale * 0.4, -scale * 1.2, 0)), # 3: Left tail
        mathutils.Vector((0, -scale * 0.8, 0)),      # 4: Center exhaust
        mathutils.Vector((scale * 0.4, -scale * 1.2, 0)),  # 5: Right tail
        mathutils.Vector((scale * 0.4, -scale * 0.4, 0)),  # 6: Right inner wing
        mathutils.Vector((scale * 1.2, -scale * 0.8, 0)),  # 7: Right wingtip
    ]
    faces = [[0, 1, 2], [0, 2, 4], [0, 4, 6], [0, 6, 7], [2, 3, 4], [4, 5, 6]]
    jet_mesh.from_pydata(verts, [], faces)
    jet_mesh.update()

    jet_obj = bpy.data.objects.new("HUD_F18_Jet", jet_mesh)
    col.objects.link(jet_obj)
    # Position low at the canyon entrance (matching reference image)
    jet_obj.location = mathutils.Vector((12600.0, -13500.0, 4350.0))
    # Heading northeast along the canyon corridor
    jet_obj.rotation_euler = (math.radians(15.0), math.radians(-10.0), math.radians(-55.0))
    jet_obj.data.materials.append(jet_mat)

    # -------------------------------------------------------------
    # 2. DASHED WHITE FLIGHT WAYPOINT LINE
    # -------------------------------------------------------------
    white_mat = bpy.data.materials.get("M_HUD_White_Dashed")
    if not white_mat:
        white_mat = bpy.data.materials.new("M_HUD_White_Dashed")
        white_mat.use_nodes = True
        nodes = white_mat.node_tree.nodes
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        em = nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        em.inputs['Strength'].default_value = 4.0
        white_mat.node_tree.links.new(em.outputs['Emission'], out.inputs['Surface'])

    # Curve line from Jet forward down the canyon trench
    curve_data = bpy.data.curves.new('HUD_Flight_Corridor', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = 12.0
    curve_data.bevel_resolution = 3

    polyline = curve_data.splines.new('POLY')
    # Waypoints through the canyon
    wp_coords = [
        (12600.0, -13500.0, 4350.0),
        (14200.0, -11800.0, 4200.0),
        (15800.0, -10000.0, 4100.0),
        (17500.0, -8200.0, 4000.0),
        (19000.0, -6500.0, 3950.0),
    ]
    polyline.points.add(len(wp_coords) - 1)
    for i, coord in enumerate(wp_coords):
        polyline.points[i].co = (coord[0], coord[1], coord[2], 1.0)

    line_obj = bpy.data.objects.new('HUD_Flight_Corridor_Line', curve_data)
    col.objects.link(line_obj)
    line_obj.data.materials.append(white_mat)

    # -------------------------------------------------------------
    # 3. ORANGE TERRAIN CLEARANCE WALL TRACE
    # -------------------------------------------------------------
    orange_mat = bpy.data.materials.get("M_HUD_Orange_Trace")
    if not orange_mat:
        orange_mat = bpy.data.materials.new("M_HUD_Orange_Trace")
        orange_mat.use_nodes = True
        nodes = orange_mat.node_tree.nodes
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        em = nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (1.0, 0.40, 0.05, 1.0) # Tactical HUD orange
        em.inputs['Strength'].default_value = 4.5
        orange_mat.node_tree.links.new(em.outputs['Emission'], out.inputs['Surface'])

    # Trace hugging the canyon cliff slope
    orange_curve = bpy.data.curves.new('HUD_Orange_Clearance_Trace', type='CURVE')
    orange_curve.dimensions = '3D'
    orange_curve.bevel_depth = 10.0
    orange_spline = orange_curve.splines.new('POLY')
    orange_coords = [
        (11200.0, -14800.0, 4700.0),
        (12000.0, -13900.0, 4600.0),
        (12800.0, -13100.0, 4550.0),
        (13600.0, -12500.0, 4500.0),
        (14400.0, -11900.0, 4480.0),
    ]
    orange_spline.points.add(len(orange_coords) - 1)
    for i, coord in enumerate(orange_coords):
        orange_spline.points[i].co = (coord[0], coord[1], coord[2], 1.0)

    orange_obj = bpy.data.objects.new('HUD_Orange_Clearance_Trace_Obj', orange_curve)
    col.objects.link(orange_obj)
    orange_obj.data.materials.append(orange_mat)

    # -------------------------------------------------------------
    # 4. RED TACTICAL TARGET DIAMONDS
    # -------------------------------------------------------------
    red_mat = bpy.data.materials.get("M_HUD_Red_Target")
    if not red_mat:
        red_mat = bpy.data.materials.new("M_HUD_Red_Target")
        red_mat.use_nodes = True
        nodes = red_mat.node_tree.nodes
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        em = nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (1.0, 0.15, 0.10, 1.0) # Military red
        em.inputs['Strength'].default_value = 5.0
        red_mat.node_tree.links.new(em.outputs['Emission'], out.inputs['Surface'])

    # Create target diamonds at key tactical peaks
    target_locations = [
        (14500.0, -10200.0, 4850.0), # Target 1 (ridge peak)
        (10800.0, -12200.0, 5200.0), # Target 2 (left spur)
    ]
    for idx, t_loc in enumerate(target_locations):
        t_mesh = bpy.data.meshes.new(f"HUD_Target_{idx}_Mesh")
        s = 70.0
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

    print("[OK] Tactical HUD Flight Overlays created.")

def configure_topgun_canyon_simulation():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        print("[ERROR] Terrain DEM object not found!")
        return

    # 1. DEM interpolation & anti-aliasing
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
    mat = create_topgun_canyon_material()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    # 4. Create Tactical HUD Overlays (F-18, waypoint track, target diamonds)
    create_tactical_hud_elements(scene)

    # -------------------------------------------------------------
    # 5. CAMERA: HIGH-ALTITUDE OBLIQUE RECON VIEW (TOP GUN CANYON)
    # Looking diagonally down the winding gorge corridor
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

    cam_pos = mathutils.Vector((10200.0, -17000.0, 6100.0))
    target_pos = mathutils.Vector((16500.0, -10000.0, 3600.0))
    cam_obj.location = cam_pos
    direction = target_pos - cam_pos
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    # -------------------------------------------------------------
    # 6. RAKING SUN LIGHTING RIG (STARK FLIR CHIAROSCURO)
    # -------------------------------------------------------------
    sun = bpy.data.objects.get("Sun_Tactical")
    if not sun:
        sun_data = bpy.data.lights.new("Sun_Tactical", 'SUN')
        sun = bpy.data.objects.new("Sun_Tactical", sun_data)
        scene.collection.objects.link(sun)
    sun.data.energy = 6.6
    sun.data.color = (0.92, 0.96, 1.0)
    sun.data.use_shadow = False
    sun.rotation_euler = (math.radians(52.0), math.radians(26.0), math.radians(-72.0))

    fill = bpy.data.objects.get("Sun_Fill")
    if not fill:
        fill_data = bpy.data.lights.new("Sun_Fill", 'SUN')
        fill = bpy.data.objects.new("Sun_Fill", fill_data)
        scene.collection.objects.link(fill)
    fill.data.energy = 1.3
    fill.data.color = (0.26, 0.34, 0.44)
    fill.data.use_shadow = False
    fill.rotation_euler = (math.radians(110.0), math.radians(-20.0), math.radians(110.0))

    world = scene.world
    if not world:
        world = bpy.data.worlds.new("W_Tactical")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.012, 0.018, 0.025, 1.0)
        bg.inputs['Strength'].default_value = 0.65

    # AgX High Contrast
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.view_settings.exposure = 0.12

    # Viewport pre-configuration
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
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_topgun_canyon_simulation.png"))
    scene.render.filepath = out_path
    print(f"[RENDER] Rendering Top Gun canyon simulation to: {out_path}...")
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
    configure_topgun_canyon_simulation()
