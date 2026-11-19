"""Headless .blend inspector (read-only; never saves).

Usage: D:\\Blender\\blender.exe -b <file.blend> --python scripts/blender/inspect_blend.py -- [--json out.json]
Prints: object count by type, mesh objects, total triangles, collections, materials, named components (objects whose
name does not look auto-generated), and the custom property component_id where present.
"""
import json
import re
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out_json = args[args.index("--json") + 1] if "--json" in args else None

objs = list(bpy.data.objects)
by_type = {}
for o in objs:
    by_type[o.type] = by_type.get(o.type, 0) + 1

deps = bpy.context.evaluated_depsgraph_get()
tris = 0
mesh_names = []
for o in objs:
    if o.type == "MESH":
        mesh_names.append(o.name)
        ev = o.evaluated_get(deps)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        ev.to_mesh_clear()

auto = re.compile(r"(\.\d{3}$)|(^\d+_@)|(^Object\d*$)|(^Mesh\d*$)")
named = sorted({re.sub(r"\.\d{3}$", "", n) for n in mesh_names if not auto.search(n)})
component_ids = sorted({o.get("component_id") for o in objs if o.get("component_id")})

report = {
    "file": bpy.data.filepath,
    "objects": len(objs),
    "by_type": by_type,
    "mesh_objects": len(mesh_names),
    "triangles": tris,
    "collections": len(bpy.data.collections),
    "materials": len(bpy.data.materials),
    "distinct_base_names": len(named),
    "base_names_sample": named[:60],
    "component_ids": component_ids,
}
print("INSPECT_JSON " + json.dumps(report))
if out_json:
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
