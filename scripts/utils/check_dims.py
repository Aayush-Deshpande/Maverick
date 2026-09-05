import bpy

bpy.ops.wm.open_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend')

meshes = [o for o in bpy.data.objects if o.type == 'MESH']
print(f"Total mesh objects: {len(meshes)}")

# Get first few objects' dimensions directly
for obj in sorted(meshes, key=lambda o: max(o.dimensions), reverse=True)[:10]:
    d = obj.dimensions
    l = obj.location
    print(f"  {obj.name}: dims={d.x:.2f} x {d.y:.2f} x {d.z:.2f} | loc=({l.x:.2f}, {l.y:.2f}, {l.z:.2f})")
