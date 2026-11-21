"""
Add missing placeholders to VRDE Jayem 2.2L (Card B-05).
Adds: Radiator, Airbox_Filter, ECU_Main.
"""
import os
import bpy
import bmesh
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

INPUT_BLEND = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "vrde_jayem_2_2l", "vrde_jayem_2_2l.blend")
OUTPUT_BLEND = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "vrde_jayem_2_2l", "vrde_jayem_2_2l_work.blend")
RENDER_OUT = os.path.join(PROJECT_ROOT, "assets", "renders", "vrde_jayem_2_2l_placeholders.png")

print(f"Loading {INPUT_BLEND}...")
bpy.ops.wm.open_mainfile(filepath=INPUT_BLEND)

# Material for placeholders
mat_name = "M_Placeholder"
if mat_name in bpy.data.materials:
    placeholder_mat = bpy.data.materials[mat_name]
else:
    placeholder_mat = bpy.data.materials.new(name=mat_name)
    placeholder_mat.use_nodes = True
    bsdf = placeholder_mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.55, 0.60, 0.68, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.35
        bsdf.inputs["Metallic"].default_value = 0.85

def create_placeholder(name, comp_id, loc, size, shape='BOX'):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    if shape == 'BOX':
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x *= size[0]
            v.co.y *= size[1]
            v.co.z *= size[2]
    elif shape == 'CYLINDER':
        bmesh.ops.create_cone(
            bm, cap_ends=True, cap_tris=False, segments=16,
            radius1=size[0], radius2=size[0], depth=size[1]
        )
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    obj.location = Vector(loc)
    obj["placeholder"] = True
    obj["component_id"] = comp_id
    if obj.data.materials:
        obj.data.materials[0] = placeholder_mat
    else:
        obj.data.materials.append(placeholder_mat)
    bpy.context.scene.collection.objects.link(obj)
    return obj

# 1. Airbox Filter (intake air filter housing near rear / intake)
# Intake manifold is at (-0.136, 0.472, 0.105), intercooler is at (0.0, 0.65, 0.22)
airbox = create_placeholder("Airbox_Filter", "airbox_filter", (0.0, 0.74, 0.22), (0.18, 0.12, 0.10), 'BOX')

# 2. Radiator (front engine coolant radiator)
# Engine block is at (0.0, 0.50, -0.0075), prop flange is at (0.0, 0.038, 0.018)
radiator = create_placeholder("Radiator", "radiator", (0.0, -0.06, -0.08), (0.34, 0.04, 0.26), 'BOX')

# 3. ECU Main (central ECU housing)
ecu = create_placeholder("ECU_Main", "ecu", (0.18, 0.42, 0.12), (0.10, 0.14, 0.04), 'BOX')

print("Created VRDE placeholders: Airbox_Filter, Radiator, ECU_Main.")

for obj in bpy.data.objects:
    if obj.type in ('MESH', 'CURVE'):
        if "placeholder" not in obj:
            obj["placeholder"] = False

bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
print(f"Saved {OUTPUT_BLEND}")

# Verification render
cam_data = bpy.data.cameras.new("VerifyCam")
cam_obj = bpy.data.objects.new("VerifyCam", cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj
cam_obj.location = Vector((-0.8, -0.6, 0.5))
direction = Vector((0.0, 0.4, 0.0)) - cam_obj.location
rot_quat = direction.to_track_quat('-Z', 'Y')
cam_obj.rotation_euler = rot_quat.to_euler()

bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720
bpy.context.scene.render.filepath = RENDER_OUT
bpy.ops.render.render(write_still=True)
print(f"Rendered verification frame to {RENDER_OUT}")
