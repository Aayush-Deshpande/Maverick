import bpy
import bmesh
import math
import mathutils
from pathlib import Path

def reset_scene(name="Scene"):
    """Empty factory scene, METRIC, METERS, scale 1.0"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = name
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.length_unit = 'METERS'
    scene.unit_settings.scale_length = 1.0
    return scene

def make_collections(root_name, names):
    """Create a nested collection tree; return a dict of collections"""
    master_col = bpy.context.scene.collection
    root_col = bpy.data.collections.new(root_name)
    master_col.children.link(root_col)
    
    cols = {"_root": root_col}
    for cname in names:
        c = bpy.data.collections.new(cname)
        root_col.children.link(c)
        cols[cname] = c
    return cols

def unique_name(obj, name):
    """Assign a name and assert no .00N suffix"""
    obj.name = name
    if hasattr(obj, "data") and obj.data:
        obj.data.name = f"{name}_Mesh"
    assert not any(obj.name.endswith(f".{i:03d}") for i in range(1, 1000)), f"Name collision on {obj.name}"
    return obj.name

def add_twin_nodes(material, is_skin=False):
    """Insert fault emission, ghost and sensor-suspect nodes per Section 13.1"""
    if not material.node_tree:
        material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    # Find the output node
    out_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not out_node:
        out_node = nodes.new('ShaderNodeOutputMaterial')
        out_node.location = (1200, 0)

    # Find main BSDF
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf:
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (400, 100)

    # 1. Attribute node for Fault Level
    node_flevel = nodes.new('ShaderNodeAttribute')
    node_flevel.name = "TwinFaultLevel"
    node_flevel.attribute_type = 'OBJECT'
    node_flevel.attribute_name = "twin_fault_level"
    node_flevel.location = (-400, -200)

    # 2. Attribute node for Fault RGB
    node_frgb = nodes.new('ShaderNodeAttribute')
    node_frgb.name = "TwinFaultRGB"
    node_frgb.attribute_type = 'OBJECT'
    node_frgb.attribute_name = "twin_fault_rgb"
    node_frgb.location = (-400, -400)

    # 3. Attribute node for Ghosting
    node_ghost = nodes.new('ShaderNodeAttribute')
    node_ghost.name = "TwinGhost"
    node_ghost.attribute_type = 'OBJECT'
    node_ghost.attribute_name = "twin_ghost"
    node_ghost.location = (-400, -600)

    # 4. Attribute node for Sensor Suspect
    node_sensor = nodes.new('ShaderNodeAttribute')
    node_sensor.name = "TwinSensorSuspect"
    node_sensor.attribute_type = 'OBJECT'
    node_sensor.attribute_name = "twin_sensor_suspect"
    node_sensor.location = (-400, -800)

    # Math node: Fault Emission Strength = Level * 8.0
    math_mult = nodes.new('ShaderNodeMath')
    math_mult.operation = 'MULTIPLY'
    math_mult.inputs[1].default_value = 8.0
    math_mult.location = (-150, -200)
    links.new(node_flevel.outputs['Factor'], math_mult.inputs[0])

    # Connect to Principled BSDF emission inputs
    links.new(node_frgb.outputs['Color'], bsdf.inputs['Emission Color'])
    links.new(math_mult.outputs['Value'], bsdf.inputs['Emission Strength'])

    # Ghost Shader Branch (cyan rim glow + transparency)
    fresnel = nodes.new('ShaderNodeFresnel')
    fresnel.inputs['IOR'].default_value = 1.35
    fresnel.location = (200, -600)

    ghost_emit = nodes.new('ShaderNodeEmission')
    ghost_emit.inputs['Color'].default_value = (0.05, 0.85, 1.0, 1.0)
    ghost_emit.inputs['Strength'].default_value = 4.0
    ghost_emit.location = (400, -600)

    ghost_transp = nodes.new('ShaderNodeBsdfTransparent')
    ghost_transp.inputs['Color'].default_value = (0.85, 0.95, 1.0, 1.0)
    ghost_transp.location = (400, -500)

    mix_ghost_fresnel = nodes.new('ShaderNodeMixShader')
    mix_ghost_fresnel.location = (650, -550)
    links.new(fresnel.outputs['Fac'], mix_ghost_fresnel.inputs['Factor'])
    links.new(ghost_transp.outputs['BSDF'], mix_ghost_fresnel.inputs[1])
    links.new(ghost_emit.outputs['Emission'], mix_ghost_fresnel.inputs[2])

    # Combine XRayFactor (for skin) and twin_ghost
    if is_skin:
        xray_val = nodes.new('ShaderNodeValue')
        xray_val.name = "XRayFactor"
        xray_val.outputs['Value'].default_value = 0.0
        xray_val.location = (-400, -500)

        math_max_ghost = nodes.new('ShaderNodeMath')
        math_max_ghost.operation = 'MAXIMUM'
        math_max_ghost.location = (-150, -550)
        links.new(xray_val.outputs['Value'], math_max_ghost.inputs[0])
        links.new(node_ghost.outputs['Factor'], math_max_ghost.inputs[1])
        ghost_fac_socket = math_max_ghost.outputs['Value']
    else:
        ghost_fac_socket = node_ghost.outputs['Factor']

    # Mix main BSDF with Ghost Shader
    mix_ghost_main = nodes.new('ShaderNodeMixShader')
    mix_ghost_main.location = (900, 0)
    links.new(ghost_fac_socket, mix_ghost_main.inputs['Factor'])
    links.new(bsdf.outputs['BSDF'], mix_ghost_main.inputs[1])
    links.new(mix_ghost_fresnel.outputs['Shader'], mix_ghost_main.inputs[2])

    # Sensor Suspect Striping (magenta/white stripes on object coordinates)
    tex_coord = nodes.new('ShaderNodeTexCoord')
    tex_coord.location = (100, -900)

    wave_tex = nodes.new('ShaderNodeTexWave')
    wave_tex.bands_direction = 'DIAGONAL'
    wave_tex.inputs['Scale'].default_value = 35.0
    wave_tex.inputs['Distortion'].default_value = 0.0
    wave_tex.location = (300, -900)
    links.new(tex_coord.outputs['Object'], wave_tex.inputs['Vector'])

    color_ramp = nodes.new('ShaderNodeValToRGB')
    color_ramp.color_ramp.elements[0].position = 0.45
    color_ramp.color_ramp.elements[0].color = (1.0, 0.0, 1.0, 1.0) # Magenta
    color_ramp.color_ramp.elements[1].position = 0.55
    color_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0) # White
    color_ramp.location = (550, -900)
    links.new(wave_tex.outputs['Color'], color_ramp.inputs['Fac'])

    sensor_emit = nodes.new('ShaderNodeEmission')
    sensor_emit.inputs['Strength'].default_value = 5.0
    sensor_emit.location = (800, -900)
    links.new(color_ramp.outputs['Color'], sensor_emit.inputs['Color'])

    mix_sensor = nodes.new('ShaderNodeMixShader')
    mix_sensor.location = (1050, 0)
    links.new(node_sensor.outputs['Factor'], mix_sensor.inputs['Factor'])
    links.new(mix_ghost_main.outputs['Shader'], mix_sensor.inputs[1])
    links.new(sensor_emit.outputs['Emission'], mix_sensor.inputs[2])

    links.new(mix_sensor.outputs['Shader'], out_node.inputs['Surface'])

    # Enable transparent dithering / blending for ghost visibility in EEVEE
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = 'DITHERED'
    elif hasattr(material, "blend_method"):
        material.blend_method = 'HASHED'

def create_pbr_material(name, base_color=(0.5, 0.5, 0.5, 1.0), metallic=0.0, roughness=0.5, ior=1.45, is_skin=False):
    """Create a standard PBR material with twin nodes attached"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    out_node = nodes.new('ShaderNodeOutputMaterial')
    out_node.location = (1200, 0)
    
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (400, 100)
    bsdf.inputs['Base Color'].default_value = base_color
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['IOR'].default_value = ior

    if name in ["M_CastAluminium", "M_CastIron"]:
        tex_noise = nodes.new('ShaderNodeTexNoise')
        tex_noise.location = (-100, 200)
        tex_noise.inputs['Scale'].default_value = 400.0
        tex_noise.inputs['Detail'].default_value = 3.0
        tex_noise.inputs['Roughness'].default_value = 0.6

        bump = nodes.new('ShaderNodeBump')
        bump.location = (150, 200)
        bump.inputs['Strength'].default_value = 0.035 if name == "M_CastAluminium" else 0.060
        bump.inputs['Distance'].default_value = 0.005

        mat.node_tree.links.new(tex_noise.outputs['Fac'], bump.inputs['Height'])
        mat.node_tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    
    add_twin_nodes(mat, is_skin=is_skin)
    return mat

def material_library():
    """Standard engine M_* material library with twin nodes"""
    lib = {}
    defs = {
        "M_Steel": ((0.75, 0.75, 0.78, 1.0), 0.90, 0.25),
        "M_SteelDark": ((0.28, 0.28, 0.30, 1.0), 0.85, 0.45),
        "M_SteelBlack": ((0.08, 0.08, 0.09, 1.0), 0.70, 0.35),
        "M_Chrome": ((0.96, 0.96, 0.98, 1.0), 0.98, 0.08),
        "M_Cobalt": ((0.35, 0.37, 0.40, 1.0), 0.80, 0.35),
        "M_Copper": ((0.95, 0.50, 0.30, 1.0), 0.95, 0.20),
        "M_Rubber": ((0.03, 0.03, 0.035, 1.0), 0.00, 0.80),
        "M_PlasticBlack": ((0.02, 0.02, 0.025, 1.0), 0.05, 0.35),
        "M_MetalPaintedBlack": ((0.015, 0.015, 0.018, 1.0), 0.40, 0.20),
        "M_CastAluminium": ((0.44, 0.46, 0.48, 1.0), 0.90, 0.40),
        "M_CastIron": ((0.28, 0.29, 0.30, 1.0), 0.85, 0.58),
        "M_HeatTintedSteel": ((0.45, 0.38, 0.32, 1.0), 0.88, 0.32),
        "M_BraidedHose": ((0.35, 0.36, 0.38, 1.0), 0.60, 0.45),
        "M_TurboHousing": ((0.25, 0.26, 0.28, 1.0), 0.80, 0.50),
        "M_Labels": ((0.95, 0.95, 0.95, 1.0), 0.10, 0.30),
        "M_Brass": ((0.88, 0.72, 0.28, 1.0), 0.92, 0.25),
        "M_Glass": ((0.85, 0.95, 1.0, 1.0), 0.00, 0.05),
        "M_YellowPoly": ((0.96, 0.82, 0.04, 1.0), 0.00, 0.35),
        "M_BlueSilicone": ((0.02, 0.18, 0.85, 1.0), 0.00, 0.28),
        "M_BraidedSilver": ((0.80, 0.80, 0.82, 1.0), 0.75, 0.40),
        "M_GoldAnodized": ((0.85, 0.68, 0.18, 1.0), 0.90, 0.30),
        "M_MachinedAlloy": ((0.80, 0.82, 0.84, 1.0), 0.94, 0.22),
        "M_AnodizedBlue": ((0.05, 0.20, 0.85, 1.0), 0.85, 0.20),
        "M_HeatShield": ((0.82, 0.82, 0.84, 1.0), 0.85, 0.35)
    }
    for mname, (col, met, rgh) in defs.items():
        lib[mname] = create_pbr_material(mname, base_color=col, metallic=met, roughness=rgh, is_skin=False)
    return lib

def skin_material(prefix, maps=None):
    """Airframe PBR skin material with XRayFactor and twin nodes"""
    name = f"{prefix}_Skin_PBR"
    mat = create_pbr_material(name, base_color=(0.14, 0.15, 0.16, 1.0), metallic=0.02, roughness=0.38, is_skin=True)
    return mat

def add_tracked_camera(name, loc, target_loc, lens=50.0):
    """Add camera + Target_ empty + TRACK_TO constraint"""
    target = bpy.data.objects.new(f"Target_{name}", None)
    target.empty_display_type = 'PLAIN_AXES'
    target.empty_display_size = 0.25
    target.location = target_loc
    bpy.context.collection.objects.link(target)

    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_obj = bpy.data.objects.new(name, cam_data)
    cam_obj.location = loc
    bpy.context.collection.objects.link(cam_obj)

    c = cam_obj.constraints.new('TRACK_TO')
    c.target = target
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return cam_obj, target

def studio_lighting():
    """Three-point studio lighting rig matching baseline standard with showroom background"""
    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("Studio_World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.55, 0.55, 0.58, 1.0)
        bg.inputs[1].default_value = 1.0

    # Key light
    key = bpy.data.lights.new("Studio_Key_Area", 'AREA')
    key.energy = 850
    key.size = 3.0
    key_obj = bpy.data.objects.new("Studio_Key_Area", key)
    key_obj.location = (3.5, -4.5, 4.0)
    bpy.context.collection.objects.link(key_obj)

    # Fill light
    fill = bpy.data.lights.new("Studio_Fill_Area", 'AREA')
    fill.energy = 450
    fill.size = 4.0
    fill_obj = bpy.data.objects.new("Studio_Fill_Area", fill)
    fill_obj.location = (-4.0, -3.5, 2.5)
    bpy.context.collection.objects.link(fill_obj)

    # Top/Rim light
    top = bpy.data.lights.new("Studio_Top_Area", 'AREA')
    top.energy = 600
    top.size = 3.5
    top_obj = bpy.data.objects.new("Studio_Top_Area", top)
    top_obj.location = (0.0, 3.0, 4.5)
    bpy.context.collection.objects.link(top_obj)

def add_driver(obj, path, index, expr, prop_target, prop_data_path):
    """Add driver with SINGLE_PROP variable targeting a scene property"""
    d = obj.driver_add(path, index)
    d.driver.type = 'SCRIPTED'
    d.driver.expression = expr
    var = d.driver.variables.new()
    var.name = "val"
    var.type = 'SINGLE_PROP'
    var.targets[0].id_type = 'SCENE'
    var.targets[0].id = prop_target
    var.targets[0].data_path = prop_data_path
    return d

def loft_rings(rings, name, collection=None):
    """bmesh ring lofting between consecutive cross-sectional rings"""
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    if collection:
        collection.objects.link(obj)
    else:
        bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    prev_verts = []
    
    for ring in rings:
        cur_verts = [bm.verts.new(pt) for pt in ring]
        if prev_verts:
            n = len(ring)
            for i in range(n):
                next_i = (i + 1) % n
                bm.faces.new([prev_verts[i], cur_verts[i], cur_verts[next_i], prev_verts[next_i]])
        prev_verts = cur_verts

    # Close endcaps if first or last ring has center point
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    return obj

def curve_tube(points, radius, name, collection=None):
    """Create a 3D tube along a series of points for plumbing/harnesses"""
    curve_data = bpy.data.curves.new(name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = radius
    curve_data.bevel_resolution = 4
    curve_data.fill_mode = 'FULL'

    polyline = curve_data.splines.new('POLY')
    polyline.points.add(len(points) - 1)
    for i, pt in enumerate(points):
        polyline.points[i].co = (pt[0], pt[1], pt[2], 1.0)

    curve_obj = bpy.data.objects.new(name, curve_data)
    if collection:
        collection.objects.link(curve_obj)
    else:
        bpy.context.collection.objects.link(curve_obj)
    return curve_obj

def tri_count(obj_or_collection):
    """Evaluate triangle count using depsgraph"""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    if isinstance(obj_or_collection, bpy.types.Object):
        if obj_or_collection.type != 'MESH':
            return 0
        eval_obj = obj_or_collection.evaluated_get(depsgraph)
        m = eval_obj.to_mesh()
        cnt = len(m.loop_triangles)
        eval_obj.to_mesh_clear()
        return cnt
    elif isinstance(obj_or_collection, bpy.types.Collection):
        total = 0
        for o in obj_or_collection.all_objects:
            if o.type == 'MESH':
                eval_obj = o.evaluated_get(depsgraph)
                m = eval_obj.to_mesh()
                total += len(m.loop_triangles)
                eval_obj.to_mesh_clear()
        return total
    return 0

def pack_and_save(filepath, compress=True):
    """Pack all resources and save .blend file cleanly"""
    p = Path(filepath).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"pack_all note: {e}")
    bpy.ops.wm.save_as_mainfile(filepath=str(p), compress=compress)
    print(f"Saved: {p}")
