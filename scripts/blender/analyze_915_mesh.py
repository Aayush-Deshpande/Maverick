"""
Analyze Main engine in rotax_915is.blend:
Separates by material in memory and computes bounding box / center / polygon count
for each piece to guide component classification.
"""
import bpy
import os

blend_path = os.path.abspath("assets/blender/engines/rotax_915is/rotax_915is.blend")
bpy.ops.wm.open_mainfile(filepath=blend_path)

main_engine = bpy.data.objects.get("Main engine")
if not main_engine:
    print("[ERROR] 'Main engine' object not found")
    exit(1)

bpy.ops.object.select_all(action='DESELECT')
main_engine.select_set(True)
bpy.context.view_layer.objects.active = main_engine

# Separate by material
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.separate(type='MATERIAL')
bpy.ops.object.mode_set(mode='OBJECT')

pieces = [o for o in bpy.context.selected_objects if o.type == 'MESH']
print(f"\n[ANALYSIS] Separated 'Main engine' by material into {len(pieces)} parts:\n")

for i, p in enumerate(pieces):
    mat_name = p.material_slots[0].material.name if p.material_slots else "NO_MAT"
    bbox = [p.matrix_world @ mathutils.Vector(corner) for corner in p.bound_box] if 'mathutils' in globals() else []
    dim = p.dimensions
    center = (
        sum(p.bound_box[j][0] for j in range(8)) / 8.0,
        sum(p.bound_box[j][1] for j in range(8)) / 8.0,
        sum(p.bound_box[j][2] for j in range(8)) / 8.0,
    )
    poly_count = len(p.data.polygons)
    print(f"Part {i:02d}: '{p.name}' | Mat: '{mat_name}' | Polys: {poly_count:6d} | Dim: ({dim.x:.3f}, {dim.y:.3f}, {dim.z:.3f}) | Center: ({center[0]:.3f}, {center[1]:.3f}, {center[2]:.3f})")

