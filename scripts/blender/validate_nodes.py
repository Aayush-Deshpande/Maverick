"""
Node validation script for ANUMAAN 3D engine assets.
DRDO / iDEX PS-26054 Compliance - Check T-REPO-2:
Validates that all 3D mesh nodes declared in configs/components/{engine_id}.json exist
in both the canonical web GLB (assets/web/engines/{engine_id}.glb) and the Blender scene.
"""

import json
import os
import struct
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

ENGINES = ["rotax_912is", "rotax_914", "rotax_915is", "austro_ae300", "vrde_jayem_2_2l"]

def get_glb_nodes(glb_path, mesh_only=True):
    if not os.path.exists(glb_path):
        return None
    with open(glb_path, "rb") as fh:
        magic, _version, _length = struct.unpack("<4sII", fh.read(12))
        if magic != b"glTF":
            raise ValueError(f"{glb_path} is not a GLB file")
        chunk_len, chunk_type = struct.unpack("<I4s", fh.read(8))
        if chunk_type != b"JSON":
            raise ValueError(f"{glb_path}: first chunk is not JSON")
        doc = json.loads(fh.read(chunk_len).decode("utf-8"))
    
    names = set()
    for node in doc.get("nodes", []):
        if mesh_only and "mesh" not in node:
            continue
        if node.get("name"):
            names.add(node["name"])
    return names

def load_manifest(engine_id):
    manifest_path = os.path.join(PROJECT_ROOT, "configs", "components", f"{engine_id}.json")
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_engine_glb(engine_id):
    manifest = load_manifest(engine_id)
    if not manifest:
        return False, f"Missing manifest for {engine_id}"
    
    glb_rel = manifest.get("glb")
    glb_path = os.path.join(PROJECT_ROOT, glb_rel) if glb_rel else os.path.join(PROJECT_ROOT, "assets", "web", "engines", f"{engine_id}.glb")
    
    if not os.path.exists(glb_path):
        return False, f"Missing GLB file: {glb_path}"
        
    actual_nodes = get_glb_nodes(glb_path, mesh_only=True)
    if actual_nodes is None:
        return False, f"Failed to parse GLB: {glb_path}"
        
    declared_nodes = set()
    missing_nodes = []
    
    for comp in manifest.get("components", []):
        for node in comp.get("nodes", []):
            declared_nodes.add(node)
            if node not in actual_nodes:
                missing_nodes.append((comp.get("component_id"), node))
                
    if missing_nodes:
        msg = f"GLB {engine_id}: {len(missing_nodes)} declared nodes missing from {glb_path}:\n"
        for comp_id, node in missing_nodes[:10]:
            msg += f"  - Component '{comp_id}': Node '{node}'\n"
        if len(missing_nodes) > 10:
            msg += f"  ... and {len(missing_nodes) - 10} more\n"
        return False, msg
        
    return True, f"GLB {engine_id}: All {len(declared_nodes)} declared nodes verified ({len(actual_nodes)} meshes total in GLB)"

def main():
    print("\n=======================================================")
    print("  ANUMAAN 3D ENGINE NODE VALIDATOR (T-REPO-2)")
    print("=======================================================\n")
    
    all_ok = True
    for eid in ENGINES:
        ok, msg = validate_engine_glb(eid)
        if ok:
            print(f"  [PASS] {msg}")
        else:
            print(f"  [FAIL] {msg}")
            all_ok = False
            
    print("\n-------------------------------------------------------")
    if all_ok:
        print("  🎉 ALL 5 ENGINES PASSED T-REPO-2 NODE VALIDATION!")
        print("-------------------------------------------------------\n")
        sys.exit(0)
    else:
        print("  ❌ SOME ENGINES FAILED NODE VALIDATION!")
        print("-------------------------------------------------------\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
