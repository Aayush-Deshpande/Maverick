import bpy
import json
import sys
from pathlib import Path
import mathutils

def inspect_scene(output_json_path):
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()

    # 1. Collection tree
    def parse_collection(col):
        return {
            "name": col.name,
            "children": [parse_collection(child) for child in col.children],
            "objects": [obj.name for obj in col.objects]
        }
    collection_tree = parse_collection(scene.collection)

    # 2. Object counts by type
    counts_by_type = {}
    for obj in bpy.data.objects:
        counts_by_type[obj.type] = counts_by_type.get(obj.type, 0) + 1

    # 3. Evaluated triangle count and bounding box
    total_eval_tris = 0
    min_co = [float('inf')]*3
    max_co = [float('-inf')]*3
    has_mesh = False

    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            has_mesh = True
            eval_obj = obj.evaluated_get(depsgraph)
            mesh = eval_obj.to_mesh()
            total_eval_tris += len(mesh.loop_triangles)
            eval_obj.to_mesh_clear()

            for corner in obj.bound_box:
                w_co = obj.matrix_world @ mathutils.Vector(corner)
                for i in range(3):
                    min_co[i] = min(min_co[i], w_co[i])
                    max_co[i] = max(max_co[i], w_co[i])

    bbox = {
        "min": min_co if has_mesh else [0,0,0],
        "max": max_co if has_mesh else [0,0,0],
        "dimensions": [max_co[i] - min_co[i] for i in range(3)] if has_mesh else [0,0,0]
    }

    # 4. Objects details
    objects_detail = []
    for obj in bpy.data.objects:
        col_names = [col.name for col in obj.users_collection]
        objects_detail.append({
            "name": obj.name,
            "type": obj.type,
            "collections": col_names,
            "modifiers": [m.type for m in obj.modifiers]
        })

    # 5. Materials
    materials = [mat.name for mat in bpy.data.materials]

    # 6. Images
    images = []
    for img in bpy.data.images:
        images.append({
            "name": img.name,
            "filepath": img.filepath,
            "packed": img.packed_file is not None,
            "size": list(img.size) if hasattr(img, "size") else [0, 0]
        })

    # 7. Cameras
    cameras = []
    for cam_obj in [o for o in bpy.data.objects if o.type == 'CAMERA']:
        cam_data = cam_obj.data
        cameras.append({
            "name": cam_obj.name,
            "location": list(cam_obj.location),
            "lens": cam_data.lens,
            "constraints": [c.type for c in cam_obj.constraints]
        })

    # 8. Lights
    lights = [l.name for l in bpy.data.lights]

    # 9. Animated objects and driven objects
    animated_objects = []
    driven_objects = []
    for obj in bpy.data.objects:
        if obj.animation_data:
            if obj.animation_data.action:
                animated_objects.append(obj.name)
            if obj.animation_data.drivers:
                driven_objects.append(obj.name)

    # 10. Modifiers by type summary
    modifiers_by_type = {}
    for obj in bpy.data.objects:
        for m in obj.modifiers:
            modifiers_by_type[m.type] = modifiers_by_type.get(m.type, 0) + 1

    # 11. Named shader nodes across materials
    named_shader_nodes = {}
    for mat in bpy.data.materials:
        if mat.node_tree:
            for n in mat.node_tree.nodes:
                named_shader_nodes.setdefault(n.name, []).append(mat.name)

    # 12. Text blocks
    text_blocks = [t.name for t in bpy.data.texts]

    summary = {
        "scene_name": scene.name,
        "collection_tree": collection_tree,
        "object_counts_by_type": counts_by_type,
        "total_objects": len(bpy.data.objects),
        "total_eval_triangles": total_eval_tris,
        "bounding_box": bbox,
        "objects": objects_detail,
        "materials": materials,
        "images": images,
        "cameras": cameras,
        "lights": lights,
        "animated_objects": animated_objects,
        "driven_objects": driven_objects,
        "modifiers_by_type": modifiers_by_type,
        "named_shader_nodes": list(named_shader_nodes.keys()),
        "text_blocks": text_blocks
    }

    out_p = Path(output_json_path).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Inspection complete. Written to {out_p}")
    print(f"Objects: {len(bpy.data.objects)} | Eval Tris: {total_eval_tris} | BBox: {bbox['dimensions']}")

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_path = args[0] if args else "inspection.json"
    inspect_scene(out_path)
