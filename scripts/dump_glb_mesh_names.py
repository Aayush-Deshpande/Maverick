"""
Extracts node and mesh names from binary GLTF (.glb) files using Python standard library only.
Used for inspecting Blender-derived CAD models and mapping 3D nodes to fault targets and stations.
"""

import json
import os
import struct
import sys
from typing import Any, Dict, List


def parse_glb_json(glb_path: str) -> Dict[str, Any]:
    with open(glb_path, "rb") as f:
        header = f.read(12)
        if len(header) < 12:
            raise ValueError(f"{glb_path}: File too short for GLB header")

        magic, version, length = struct.unpack("<4sII", header)
        if magic != b"glTF":
            raise ValueError(f"{glb_path}: Not a valid GLB file (magic={magic})")

        chunk_header = f.read(8)
        if len(chunk_header) < 8:
            raise ValueError(f"{glb_path}: File missing JSON chunk header")

        chunk_length, chunk_type = struct.unpack("<I4s", chunk_header)
        if chunk_type != b"JSON":
            raise ValueError(f"{glb_path}: First chunk is not JSON ({chunk_type})")

        json_bytes = f.read(chunk_length)
        return json.loads(json_bytes.decode("utf-8"))


def dump_mesh_and_node_names(glb_path: str) -> Dict[str, List[str]]:
    gltf = parse_glb_json(glb_path)
    nodes = [n.get("name") for n in gltf.get("nodes", []) if n.get("name")]
    meshes = [m.get("name") for m in gltf.get("meshes", []) if m.get("name")]
    return {"nodes": sorted(nodes), "meshes": sorted(meshes)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/dump_glb_mesh_names.py <path_to_glb>")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.isfile(path):
        print(f"Error: file not found: {path}")
        sys.exit(1)

    data = dump_mesh_and_node_names(path)
    print(f"=== {os.path.basename(path)} ===")
    print(f"Nodes ({len(data['nodes'])}):")
    for name in data["nodes"]:
        print(f"  {name}")
    print(f"\nMeshes ({len(data['meshes'])}):")
    for name in data["meshes"]:
        print(f"  {name}")
