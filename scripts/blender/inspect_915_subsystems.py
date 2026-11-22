"""
Classify separated parts of Rotax 915 iS Main engine into subsystems and components:
cylinder_head_1..4, cylinder_barrel_1..4, crankcase, turbocharger, wastegate,
intake_manifold, exhaust, injector_1..4, fuel_rail, water_pump, coolant_hoses, alternator, prop_flange.
"""
import bpy
import mathutils
import os

blend_path = os.path.abspath("assets/blender/engines/rotax_915is/rotax_915is.blend")
bpy.ops.wm.open_mainfile(filepath=blend_path)

me = bpy.data.objects['Main engine']
bpy.context.view_layer.objects.active = me
me.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.separate(type='MATERIAL')
bpy.ops.object.mode_set(mode='OBJECT')

parts = [o for o in bpy.context.selected_objects if o.type == 'MESH']
print(f"Total separated material parts: {len(parts)}")

# Sort by polygon count descending
parts.sort(key=lambda o: len(o.data.polygons), reverse=True)

for i, p in enumerate(parts):
    mat = p.material_slots[0].material.name if p.material_slots else "NONE"
    dim = p.dimensions
    c = tuple(round(sum(p.bound_box[j][k] for j in range(8))/8.0, 3) for k in range(3))
    print(f"#{i:02d}: '{p.name}' | Mat: '{mat[:25]:25s}' | Polys: {len(p.data.polygons):6d} | Center: {c} | Dim: ({dim.x:.3f}, {dim.y:.3f}, {dim.z:.3f})")
