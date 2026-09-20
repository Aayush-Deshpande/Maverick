import bpy
import math
import os
import mathutils

blend_path = r"e:\backup-llm\backup-no-llm\3d_engine\3d_models\bayraktar_tb3_digital_twin.blend"
bpy.ops.wm.open_mainfile(filepath=blend_path)
scene = bpy.context.scene

ground_plane = bpy.data.objects.get("Studio_Ground_Plane")
if ground_plane:
    ground_plane.hide_render = True

for obj in bpy.data.objects:
    name_lower = obj.name.lower()
    if any(k in name_lower for k in ["maml", "bomb", "guided", "cube", "box", "internal"]):
        obj.hide_render = True

# Clay + Wire
mat_clay = bpy.data.materials.new("TB3_Clay")
mat_clay.use_nodes = True
mat_clay.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.50, 0.47, 0.43, 1.0)
mat_wire_line = bpy.data.materials.new("TB3_Line")
mat_wire_line.use_nodes = True
mat_wire_line.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.95, 0.94, 0.91, 1.0)

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
        wmod.thickness = 0.0028
        wmod.use_replace = False
        wmod.material_offset = 1

cam = bpy.data.objects.get("Cam_Test")
if not cam:
    cam_data = bpy.data.cameras.new("Cam_Test")
    cam = bpy.data.objects.new("Cam_Test", cam_data)
    scene.collection.objects.link(cam)
scene.camera = cam
cam.data.lens = 28.0

# Broad light
for obj in list(scene.objects):
    if obj.type == 'LIGHT':
        bpy.data.objects.remove(obj, do_unlink=True)
l1 = bpy.data.lights.new("L1", 'SUN')
l1.energy = 4.0
l1.color = (1, 1, 1)
lo1 = bpy.data.objects.new("L1", l1)
lo1.rotation_euler = (math.radians(-50), math.radians(20), math.radians(-30))
scene.collection.objects.link(lo1)

tgt = mathutils.Vector((0.0, 0.5, 1.05))

# Angles to test around the clock (in degrees from forward Y axis)
test_configs = [
    ("angle_045", ( 7.0, -4.0, -1.8), 25.0),
    ("angle_135", ( 6.0,  5.0, -2.0), -45.0),
    ("angle_225", (-6.0,  5.0, -2.0), 45.0),
    ("angle_315", (-7.0, -4.0, -1.8), -25.0),
    ("angle_aft", ( 3.0, -7.0, -1.5), 35.0),
    ("angle_fwd", ( 3.0,  7.0, -1.5), -35.0),
]

scene.render.resolution_x = 960
scene.render.resolution_y = 540

for name, pos, roll_deg in test_configs:
    cam_loc = mathutils.Vector(pos)
    cam.location = cam_loc
    forward = (tgt - cam_loc).normalized()
    up_approx = mathutils.Vector((0.0, 0.0, 1.0))
    right = forward.cross(up_approx).normalized()
    up = right.cross(forward).normalized()
    rot_roll = mathutils.Matrix.Rotation(math.radians(roll_deg), 3, forward)
    right_r = rot_roll @ right
    up_r = rot_roll @ up
    rot_mat = mathutils.Matrix([
        [right_r.x, up_r.x, -forward.x],
        [right_r.y, up_r.y, -forward.y],
        [right_r.z, up_r.z, -forward.z]
    ]).to_4x4()
    cam.matrix_world = mathutils.Matrix.Translation(cam_loc) @ rot_mat
    
    out_path = fr"e:\backup-llm\backup-no-llm\3d_engine\3d_models\renders\test_{name}.png"
    scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {name}")
