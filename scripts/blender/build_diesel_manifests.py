"""
Generate authoritative configs/components/austro_ae300.json and
configs/components/vrde_jayem_2_2l.json directly from their exported GLBs (Card B-05).
"""
import json
import os
import struct

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

def get_glb_mesh_nodes(glb_path):
    with open(glb_path, "rb") as fh:
        magic, _version, _length = struct.unpack("<4sII", fh.read(12))
        chunk_len, chunk_type = struct.unpack("<I4s", fh.read(8))
        doc = json.loads(fh.read(chunk_len).decode("utf-8"))
    return [node["name"] for node in doc.get("nodes", []) if "mesh" in node]

# 1. Update AE300
ae300_glb = os.path.join(PROJECT_ROOT, "assets", "web", "engines", "austro_ae300.glb")
ae300_manifest = os.path.join(PROJECT_ROOT, "configs", "components", "austro_ae300.json")

ae_nodes = get_glb_mesh_nodes(ae300_glb)
print(f"AE300 GLB has {len(ae_nodes)} mesh nodes.")

with open(ae300_manifest, "r", encoding="utf-8") as fh:
    ae_data = json.load(fh)

ae_comps = {c["component_id"]: c for c in ae_data["components"]}

# Match newly added placeholders from GLB nodes
rad_nodes = [n for n in ae_nodes if n.startswith("Radiator")]
vgt_nodes = [n for n in ae_nodes if n.startswith("VGT_Actuator")]
therm_nodes = [n for n in ae_nodes if n.startswith("Thermostat")]

ae_comps["radiator"] = {"component_id": "radiator", "subsystem": "cooling", "cylinder": None, "nodes": sorted(rad_nodes)}
ae_comps["vgt_actuator"] = {"component_id": "vgt_actuator", "subsystem": "turbo", "cylinder": None, "nodes": sorted(vgt_nodes)}
ae_comps["thermostat"] = {"component_id": "thermostat", "subsystem": "cooling", "cylinder": None, "nodes": sorted(therm_nodes)}

all_ae_nodes = []
for c in ae_comps.values():
    all_ae_nodes.extend(c["nodes"])

ae_data["components"] = list(ae_comps.values())
ae_data["mesh_nodes"] = len(all_ae_nodes)
ae_data["representative_geometry"] = "representative geometry (AE330 shape)"

with open(ae300_manifest, "w", encoding="utf-8") as fh:
    json.dump(ae_data, fh, indent=2)
print(f"Updated AE300: {len(ae_data['components'])} components, {ae_data['mesh_nodes']} nodes.")

# 2. Update VRDE
vrde_glb = os.path.join(PROJECT_ROOT, "assets", "web", "engines", "vrde_jayem_2_2l.glb")
vrde_manifest = os.path.join(PROJECT_ROOT, "configs", "components", "vrde_jayem_2_2l.json")

vrde_nodes = get_glb_mesh_nodes(vrde_glb)
print(f"VRDE GLB has {len(vrde_nodes)} mesh nodes.")

with open(vrde_manifest, "r", encoding="utf-8") as fh:
    vrde_data = json.load(fh)

vrde_comps = {c["component_id"]: c for c in vrde_data["components"]}

vrde_rad_nodes = [n for n in vrde_nodes if n.startswith("Radiator")]
vrde_airbox_nodes = [n for n in vrde_nodes if n.startswith("Airbox_Filter")]
vrde_ecu_nodes = [n for n in vrde_nodes if n.startswith("ECU_Main")]

vrde_comps["radiator"] = {"component_id": "radiator", "subsystem": "cooling", "cylinder": None, "nodes": sorted(vrde_rad_nodes)}
vrde_comps["airbox_filter"] = {"component_id": "airbox_filter", "subsystem": "intake", "cylinder": None, "nodes": sorted(vrde_airbox_nodes)}
vrde_comps["ecu"] = {"component_id": "ecu", "subsystem": "control", "cylinder": None, "nodes": sorted(vrde_ecu_nodes)}

all_vrde_nodes = []
for c in vrde_comps.values():
    all_vrde_nodes.extend(c["nodes"])

vrde_data["components"] = list(vrde_comps.values())
vrde_data["mesh_nodes"] = len(all_vrde_nodes)
vrde_data["representative_geometry"] = "representative 2.2 L CRDI geometry"

with open(vrde_manifest, "w", encoding="utf-8") as fh:
    json.dump(vrde_data, fh, indent=2)
print(f"Updated VRDE: {len(vrde_data['components'])} components, {vrde_data['mesh_nodes']} nodes.")
