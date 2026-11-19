"""Read node and mesh names from a .glb (JSON chunk only; works for Draco/Meshopt-compressed files).
Usage: python scripts/assets/glb_nodes.py assets/web/engines/rotax_912is.glb [--mesh-only]"""
import json
import struct
import sys


def glb_json(path):
    with open(path, "rb") as fh:
        magic, _version, _length = struct.unpack("<4sII", fh.read(12))
        if magic != b"glTF":
            raise ValueError(f"{path} is not a GLB file")
        chunk_len, chunk_type = struct.unpack("<I4s", fh.read(8))
        if chunk_type != b"JSON":
            raise ValueError(f"{path}: first chunk is not JSON")
        return json.loads(fh.read(chunk_len).decode("utf-8"))


def node_names(path, mesh_only=False):
    doc = glb_json(path)
    names = []
    for node in doc.get("nodes", []):
        if mesh_only and "mesh" not in node:
            continue
        if node.get("name"):
            names.append(node["name"])
    return names


if __name__ == "__main__":
    names = node_names(sys.argv[1], mesh_only="--mesh-only" in sys.argv)
    print(len(names))
    for n in names:
        print(n)
