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
mat_clay = bpy.data.materials.new("TB3_Wireframe_Clay_Pure")
mat_clay.use_nodes = True
bsdf_clay = mat_clay.node_tree.nodes.get("Principled BSDF")
if bsdf_clay:
    # Warm neutral clay matching fdda7fefdc.jpg (hex ~ #a8a096)
    bsdf_clay.inputs['Base Color'].default_value = (0.50, 0.47, 0.43, 1.0)
    bsdf_clay.inputs['Roughness'].default_value = 0.50
    if 'Specular IOR Level' in bsdf_clay.inputs:
        bsdf_clay.inputs['Specular IOR Level'].default_value = 0.25

mat_wire_line = bpy.data.materials.new("TB3_Wire_Line_White")
mat_wire_line.use_nodes = True
bsdf_line = mat_wire_line.node_tree.nodes.get("Principled BSDF")
if bsdf_line:
    # Crisp white/cream quad lines
    bsdf_line.inputs['Base Color'].default_value = (0.95, 0.94, 0.91, 1.0)
    bsdf_line.inputs['Roughness'].default_value = 0.2
    if 'Emission Color' in bsdf_line.inputs:
        bsdf_line.inputs['Emission Color'].default_value = (0.95, 0.94, 0.91, 1.0)
        bsdf_line.inputs['Emission Strength'].default_value = 0.35

# Apply to all visible meshes and reset material_index to 0
for obj in bpy.data.objects:
    if obj.type == 'MESH' and not obj.hide_render and obj.name != "Studio_Ground_Plane":
        w = obj.modifiers.get("Wire_Overlay")
        if w:
            obj.modifiers.remove(w)
        for mod in obj.modifiers:
            if mod.type == 'SUBSURF':
                mod.levels = 0
                mod.render_levels = 0

        # Reset all polygon material indices to 0 so all base polygons use clay!
        for poly in obj.data.polygons:
            poly.material_index = 0

        obj.data.materials.clear()
        obj.data.materials.append(mat_clay)
        obj.data.materials.append(mat_wire_line)

        wmod = obj.modifiers.new(name="Wire_Overlay", type='WIREFRAME')
        wmod.thickness = 0.0028
        wmod.use_replace = False
        wmod.material_offset = 1

# Camera matching fdda7fefdc.jpg
cam_wire = bpy.data.objects.get("Cam_Wireframe_FDDA")
if not cam_wire:
    cam_data = bpy.data.cameras.new("Cam_Wireframe_FDDA")
    cam_wire = bpy.data.objects.new("Cam_Wireframe_FDDA", cam_data)
    scene.collection.objects.link(cam_wire)

cam_wire.constraints.clear()
# Camera location: Starboard (+X), forward (+Y), below (-Z)
cam_loc = mathutils.Vector((5.2, 6.8, -2.4))
tgt_loc = mathutils.Vector((0.0, 0.5, 1.05))
forward = (tgt_loc - cam_loc).normalized()

up_approx = mathutils.Vector((0.0, 0.0, 1.0))
right = forward.cross(up_approx).normalized()
up = right.cross(forward).normalized()

# Roll angle to tilt fuselage and wing
roll_deg = -52.0
roll_rad = math.radians(roll_deg)
rot_roll = mathutils.Matrix.Rotation(roll_rad, 3, forward)
right_rolled = rot_roll @ right
up_rolled = rot_roll @ up

rot_mat = mathutils.Matrix([
    [right_rolled.x, up_rolled.x, -forward.x],
    [right_rolled.y, up_rolled.y, -forward.y],
    [right_rolled.z, up_rolled.z, -forward.z]
]).to_4x4()

cam_wire.matrix_world = mathutils.Matrix.Translation(cam_loc) @ rot_mat
cam_wire.data.lens = 29.0
scene.camera = cam_wire

# Even, soft studio clay lighting matching fdda7fefdc.jpg
for obj in list(scene.objects):
    if obj.type == 'LIGHT':
        bpy.data.objects.remove(obj, do_unlink=True)

# 1. Broad belly area light
l1_data = bpy.data.lights.new("Light_Wire_Belly", 'AREA')
l1_data.size = 20.0
l1_data.size_y = 20.0
l1_data.energy = 4500.0
l1_data.color = (1.0, 0.99, 0.97)
l1_obj = bpy.data.objects.new("Light_Wire_Belly", l1_data)
l1_obj.location = (5.0, 5.0, -4.0)
scene.collection.objects.link(l1_obj)

# 2. Nose and forward fill light
l2_data = bpy.data.lights.new("Light_Wire_Nose", 'AREA')
l2_data.size = 18.0
l2_data.size_y = 18.0
l2_data.energy = 3000.0
l2_data.color = (0.98, 0.98, 1.0)
l2_obj = bpy.data.objects.new("Light_Wire_Nose", l2_data)
l2_obj.location = (0.0, 8.0, -1.0)
scene.collection.objects.link(l2_obj)

# 3. Ambient top fill
l3_data = bpy.data.lights.new("Light_Wire_Top", 'AREA')
l3_data.size = 20.0
l3_data.size_y = 20.0
l3_data.energy = 1500.0
l3_data.color = (0.95, 0.95, 0.95)
l3_obj = bpy.data.objects.new("Light_Wire_Top", l3_data)
l3_obj.location = (0.0, 0.0, 6.0)
scene.collection.objects.link(l3_obj)

# World background dark studio matching fdda7fefdc.jpg (#222222)
if scene.world and scene.world.node_tree:
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.026, 0.026, 0.028, 1.0)
        bg.inputs['Strength'].default_value = 0.5

out_wire = r"e:\backup-llm\backup-no-llm\3d_engine\3d_models\renders\test_wireframe_match_v5.png"
scene.render.filepath = out_wire
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
bpy.ops.render.render(write_still=True)
print(f"Rendered test_wireframe_match_v5 to: {out_wire}")
