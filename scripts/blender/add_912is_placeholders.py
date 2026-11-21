"""
Add component grouping and placeholders to Rotax 912 iS (Card B-04).
Follows D47: Never change existing geometry; only add grouping and placeholders.
"""
import os
import bpy
import bmesh
from mathutils import Vector, Matrix

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

INPUT_BLEND = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_912is", "rotax_912is.blend")
OUTPUT_BLEND = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_912is", "rotax_912is_work.blend")
RENDER_OUT = os.path.join(PROJECT_ROOT, "assets", "renders", "rotax_912is_placeholders.png")

print(f"Loading {INPUT_BLEND}...")
bpy.ops.wm.open_mainfile(filepath=INPUT_BLEND)

# Create or retrieve M_Placeholder material (clean neutral engineering aluminum)
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
    """Create a placeholder object with metadata."""
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    if shape == 'BOX':
        bmesh.ops.create_cube(bm, size=1.0)
        # Scale to size
        for v in bm.verts:
            v.co.x *= size[0]
            v.co.y *= size[1]
            v.co.z *= size[2]
    elif shape == 'CYLINDER':
        bmesh.ops.create_cone(
            bm,
            cap_ends=True,
            cap_tris=False,
            segments=16,
            radius1=size[0],
            radius2=size[0],
            depth=size[1]
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

# Rotax 912 boxer cylinder locations (Right bank = +X, Left bank = -X, Front = +Y smaller, Rear = +Y larger)
# Coordinates derived from exhaust flange connections and rocker covers:
# Cyl 1: Right Front
# Cyl 2: Left Front
# Cyl 3: Right Rear
# Cyl 4: Left Rear
cyl_coords = {
    1: {"head": (25.5, 23.0, -8.0), "barrel": (17.0, 23.0, -9.0), "egt": (19.7, 23.0, -17.0), "cht": (26.5, 23.0, -2.0), "plug": (25.5, 21.5, -1.0), "inj": (22.0, 25.0, -4.0), "coil": (20.0, 26.0, 1.0)},
    2: {"head": (-24.0, 19.7, -8.0), "barrel": (-15.5, 19.7, -9.0), "egt": (-18.0, 19.7, -16.5), "cht": (-25.0, 19.7, -2.0), "plug": (-24.0, 18.2, -1.0), "inj": (-20.5, 21.7, -4.0), "coil": (-18.5, 22.7, 1.0)},
    3: {"head": (25.5, 56.5, -8.0), "barrel": (17.0, 56.5, -9.0), "egt": (19.8, 56.5, -17.0), "cht": (26.5, 56.5, -2.0), "plug": (25.5, 55.0, -1.0), "inj": (22.0, 58.5, -4.0), "coil": (20.0, 59.5, 1.0)},
    4: {"head": (-24.0, 53.3, -8.0), "barrel": (-15.5, 53.3, -9.0), "egt": (-17.9, 53.3, -16.5), "cht": (-25.0, 53.3, -2.0), "plug": (-24.0, 51.8, -1.0), "inj": (-20.5, 55.3, -4.0), "coil": (-18.5, 56.3, 1.0)},
}

placeholders = []

for c, coords in cyl_coords.items():
    # Cylinder Head
    placeholders.append(create_placeholder(f"Cylinder_Head_{c}", f"cylinder_head_{c}", coords["head"], (7.0, 12.0, 11.0), 'BOX'))
    # Cylinder Barrel
    placeholders.append(create_placeholder(f"Cylinder_Barrel_{c}", f"cylinder_barrel_{c}", coords["barrel"], (4.8, 8.0), 'CYLINDER'))
    # Spark Plug
    placeholders.append(create_placeholder(f"Spark_Plug_{c}", f"spark_plug_{c}", coords["plug"], (1.2, 3.5), 'CYLINDER'))
    # Injector
    placeholders.append(create_placeholder(f"Injector_{c}", f"injector_{c}", coords["inj"], (1.2, 4.0), 'CYLINDER'))
    # Ignition Coil
    placeholders.append(create_placeholder(f"Ignition_Coil_{c}", f"ignition_coil_{c}", coords["coil"], (3.5, 4.5, 3.0), 'BOX'))
    # Sensor CHT
    placeholders.append(create_placeholder(f"Sensor_CHT_{c}", f"sensor_cht_{c}", coords["cht"], (1.0, 2.5), 'CYLINDER'))
    # Sensor EGT
    placeholders.append(create_placeholder(f"Sensor_EGT_{c}", f"sensor_egt_{c}", coords["egt"], (0.9, 2.8), 'CYLINDER'))

# Engine-level Placeholders
# Fuel Rail
placeholders.append(create_placeholder("Fuel_Rail", "fuel_rail", (0.96, 38.0, 2.0), (32.0, 2.0, 2.0), 'BOX'))

# Intake Manifold
placeholders.append(create_placeholder("Intake_Manifold", "intake_manifold", (0.96, 38.0, -2.0), (36.0, 24.0, 4.0), 'BOX'))

# Airbox Filter
placeholders.append(create_placeholder("Airbox_Filter", "airbox_filter", (0.96, 62.0, -10.0), (18.0, 14.0, 12.0), 'BOX'))

# Oil Pump
placeholders.append(create_placeholder("Oil_Pump", "oil_pump", (0.96, 14.0, -26.0), (6.0, 8.0, 6.0), 'BOX'))

# Oil Cooler
placeholders.append(create_placeholder("Oil_Cooler", "oil_cooler", (0.96, 8.0, -32.0), (22.0, 5.0, 10.0), 'BOX'))

# Radiator
placeholders.append(create_placeholder("Radiator", "radiator", (0.96, 6.0, -18.0), (26.0, 4.0, 14.0), 'BOX'))

# Water Pump
placeholders.append(create_placeholder("Water_Pump", "water_pump", (0.96, 18.0, -22.0), (7.0, 7.0, 8.0), 'BOX'))

# Propeller Flange
placeholders.append(create_placeholder("Prop_Flange", "prop_flange", (0.96, 3.5, -8.4), (7.0, 3.0), 'CYLINDER'))

# Engine sensors
placeholders.append(create_placeholder("Sensor_MAP", "sensor_map", (0.96, 46.0, 3.5), (1.2, 3.0), 'CYLINDER'))
placeholders.append(create_placeholder("Sensor_Oil_Press", "sensor_oil_press", (6.0, 15.0, -24.0), (1.2, 3.0), 'CYLINDER'))
placeholders.append(create_placeholder("Sensor_Oil_Temp", "sensor_oil_temp", (-4.0, 15.0, -24.0), (1.2, 3.0), 'CYLINDER'))
placeholders.append(create_placeholder("Sensor_Coolant_Temp", "sensor_coolant_temp", (0.96, 32.0, -8.0), (1.2, 3.0), 'CYLINDER'))

print(f"Created {len(placeholders)} placeholders.")

# Ensure all objects have component_id metadata
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        if "placeholder" not in obj:
            obj["placeholder"] = False

# Save work blend
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
print(f"Saved {OUTPUT_BLEND}")

# Setup camera and render verification frame
cam_data = bpy.data.cameras.new("VerifyCam")
cam_obj = bpy.data.objects.new("VerifyCam", cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj
cam_obj.location = Vector((65.0, -40.0, 25.0))
# Look at center
direction = Vector((0.96, 38.0, -12.0)) - cam_obj.location
rot_quat = direction.to_track_quat('-Z', 'Y')
cam_obj.rotation_euler = rot_quat.to_euler()

bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720
bpy.context.scene.render.filepath = RENDER_OUT
bpy.ops.render.render(write_still=True)
print(f"Rendered verification frame to {RENDER_OUT}")
