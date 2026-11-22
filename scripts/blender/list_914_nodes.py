import bpy

bpy.ops.wm.open_mainfile(filepath="assets/blender/engines/rotax_914/rotax_914_work.blend")

meshes = [o for o in bpy.data.objects if o.type == 'MESH']
meshes.sort(key=lambda o: o.name)

print(f"\n[ROTAX 914 F] Total Mesh Objects: {len(meshes)}\n")
comp_map = {}
for m in meshes:
    cid = m.get("component_id", "NONE")
    cyl = m.get("cylinder", "-")
    comp_map.setdefault(cid, []).append(m.name)

for cid, objs in sorted(comp_map.items()):
    print(f"  Component '{cid:<25s}': {len(objs):3d} meshes (e.g. {objs[:3]})")
