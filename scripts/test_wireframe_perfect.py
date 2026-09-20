import bpy
import math
import os
import mathutils

blend_path = r"e:\backup-llm\backup-no-llm\3d_engine\3d_models\bayraktar_tb3_digital_twin.blend"
bpy.ops.wm.open_mainfile(filepath=blend_path)
scene = bpy.context.scene

# Hide ground plane
ground_plane = bpy.data.objects.get("Studio_Ground_Plane")
if ground_plane:
    ground_plane.hide_render = True

# Hide munitions, boxes, internal systems for clean wireframe mode matching fdda7fefdc.jpg
for obj in bpy.data.objects:
    name_lower = obj.name.lower()
    if any(k in name_lower for k in ["maml", "bomb", "guided", "cube", "box", "internal"]):
        obj.hide_render = True

# Setup Wireframe materials: Uniform warm clay + crisp light quad lines
mat_clay = bpy.data.materials.new("TB3_Clay_Warm")
mat_clay.use_nodes = True
bsdf_clay = mat_clay.node_tree.nodes.get("Principled BSDF")
if bsdf_clay:
    # Warm neutral clay matching fdda7fefdc.jpg (#827c73)
    bsdf_clay.inputs['Base Color'].default_value = (0.44, 0.41, 0.37, 1.0)
    bsdf_clay.inputs['Roughness'].default_value = 0.45
    if 'Specular IOR Level' in bsdf_clay.inputs:
        bsdf_clay.inputs['Specular IOR Level'].default_value = 0.25

mat_wire_line = bpy.data.materials.new("TB3_Line_Crisp")
mat_wire_line.use_nodes = True
nodes = mat_wire_line.node_tree.nodes
links = mat_wire_line.node_tree.links
nodes.clear()
out_n = nodes.new('ShaderNodeOutputMaterial')
emit_n = nodes.new('ShaderNodeEmission')
emit_n.inputs['Color'].default_value = (0.94, 0.92, 0.88, 1.0)
emit_n.inputs['Strength'].default_value = 1.4
links.new(emit_n.outputs['Emission'], out_n.inputs['Surface'])

for obj in bpy.data.objects:
    if obj.type == 'MESH' and not obj.hide_render and obj.name != "Studio_Ground_Plane":
        w = obj.modifiers.get("Wire_Overlay")
        if w: obj.modifiers.remove(w)
        for mod in obj.modifiers:
            if mod.type == 'SUBSURF':
                mod.levels = 0
                mod.render_levels = 0
        for poly in obj.data.polygons:
            poly.material_index = 0
        obj.data.materials.clear()
        obj.data.materials.append(mat_clay)
        obj.data.materials.append(mat_wire_line)
        wmod = obj.modifiers.new(name="Wire_Overlay", type='WIREFRAME')
        wmod.thickness = 0.0038
        wmod.use_replace = False
        wmod.material_offset = 1

# Setup Camera matching fdda7fefdc.jpg
cam = bpy.data.objects.get("Cam_Wireframe_FDDA")
if not cam:
    cam_data = bpy.data.cameras.new("Cam_Wireframe_FDDA")
    cam = bpy.data.objects.new("Cam_Wireframe_FDDA", cam_data)
    scene.collection.objects.link(cam)
scene.camera = cam

# Camera position: (+6.2, 5.0, -2.0) with roll = 135.0 degrees!
cam_loc = mathutils.Vector((6.2, 5.0, -2.0))
tgt = mathutils.Vector((0.0, 0.6, 1.05))

forward = (tgt - cam_loc).normalized()
up_approx = mathutils.Vector((0.0, 0.0, 1.0))
right = forward.cross(up_approx).normalized()
up = right.cross(forward).normalized()

roll_deg = 135.0
rot_roll = mathutils.Matrix.Rotation(math.radians(roll_deg), 3, forward)
right_r = rot_roll @ right
up_r = rot_roll @ up
rot_mat = mathutils.Matrix([
    [right_r.x, up_r.x, -forward.x],
    [right_r.y, up_r.y, -forward.y],
    [right_r.z, up_r.z, -forward.z]
]).to_4x4()
cam.matrix_world = mathutils.Matrix.Translation(cam_loc) @ rot_mat
cam.data.lens = 29.0

# Lighting: Studio Clay Soft Lighting matching fdda7fefdc.jpg
for obj in list(scene.objects):
    if obj.type == 'LIGHT':
        bpy.data.objects.remove(obj, do_unlink=True)

# 1. Broad studio key light from camera side
l1_data = bpy.data.lights.new("Studio_Clay_Key", 'AREA')
l1_data.size = 20.0
l1_data.size_y = 20.0
l1_data.energy = 4500.0
l1_data.color = (1.0, 0.98, 0.95)
l1_obj = bpy.data.objects.new("Studio_Clay_Key", l1_data)
l1_obj.location = (6.0, 4.0, -3.0)
scene.collection.objects.link(l1_obj)

# 2. Studio fill light from opposite side
l2_data = bpy.data.lights.new("Studio_Clay_Fill", 'AREA')
l2_data.size = 18.0
l2_data.size_y = 18.0
l2_data.energy = 2800.0
l2_data.color = (0.95, 0.96, 1.0)
l2_obj = bpy.data.objects.new("Studio_Clay_Fill", l2_data)
l2_obj.location = (-6.0, -2.0, 1.0)
scene.collection.objects.link(l2_obj)

# 3. Top fill light
l3_data = bpy.data.lights.new("Studio_Clay_Top", 'AREA')
l3_data.size = 20.0
l3_data.size_y = 20.0
l3_data.energy = 1800.0
l3_data.color = (1.0, 1.0, 1.0)
l3_obj = bpy.data.objects.new("Studio_Clay_Top", l3_data)
l3_obj.location = (0.0, 0.0, 7.0)
scene.collection.objects.link(l3_obj)

# Dark Studio background matching fdda7fefdc.jpg (#222222)
if scene.world and scene.world.node_tree:
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.026, 0.026, 0.028, 1.0)
        bg.inputs['Strength'].default_value = 0.45

scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
out_path = r"e:\backup-llm\backup-no-llm\3d_engine\3d_models\renders\test_wireframe_perfect_v3.png"
scene.render.filepath = out_path
bpy.ops.render.render(write_still=True)
print(f"Rendered perfect wireframe v3 to: {out_path}")
