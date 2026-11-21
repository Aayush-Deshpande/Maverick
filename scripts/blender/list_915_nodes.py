import bpy

bpy.ops.wm.open_mainfile(filepath="assets/blender/engines/rotax_915is/rotax_915is_work.blend")

meshes = [o for o in bpy.data.objects if o.type == 'MESH']
meshes.sort(key=lambda o: o.name)

print(f"\n[ROTAX 915 iS] Total Mesh Objects: {len(meshes)}\n")
for m in meshes:
    cid = m.get("component_id", "NONE")
    cyl = m.get("cylinder", "-")
    ph = " [PLACEHOLDER]" if m.get("placeholder") else ""
    print(f"  {m.name:<30s} -> comp={cid:<22s} cyl={str(cyl):<4s}{ph}")
