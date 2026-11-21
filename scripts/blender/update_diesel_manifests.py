"""
Update configs/components/austro_ae300.json and configs/components/vrde_jayem_2_2l.json
with the new placeholder components and updated node counts (Card B-05).
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# 1. Update Austro AE300
ae300_path = os.path.join(PROJECT_ROOT, "configs", "components", "austro_ae300.json")
with open(ae300_path, "r", encoding="utf-8") as fh:
    ae_data = json.load(fh)

ae_comps = {c["component_id"]: c for c in ae_data["components"]}

# Add/ensure vgt_actuator, thermostat, radiator
new_ae = [
    {"component_id": "vgt_actuator", "subsystem": "turbo", "cylinder": None, "nodes": ["VGT_Actuator"]},
    {"component_id": "thermostat", "subsystem": "cooling", "cylinder": None, "nodes": ["Thermostat"]},
    {"component_id": "radiator", "subsystem": "cooling", "cylinder": None, "nodes": ["Radiator"]},
]
for item in new_ae:
    ae_comps[item["component_id"]] = item

all_ae_nodes = []
for c in ae_comps.values():
    all_ae_nodes.extend(c["nodes"])

ae_data["components"] = list(ae_comps.values())
ae_data["mesh_nodes"] = len(all_ae_nodes)
ae_data["representative_geometry"] = "representative geometry (AE330 shape)"

with open(ae300_path, "w", encoding="utf-8") as fh:
    json.dump(ae_data, fh, indent=2)
print(f"Updated {ae300_path}: {len(ae_data['components'])} components, {ae_data['mesh_nodes']} nodes.")

# 2. Update VRDE Jayem 2.2L
vrde_path = os.path.join(PROJECT_ROOT, "configs", "components", "vrde_jayem_2_2l.json")
with open(vrde_path, "r", encoding="utf-8") as fh:
    vrde_data = json.load(fh)

vrde_comps = {c["component_id"]: c for c in vrde_data["components"]}

new_vrde = [
    {"component_id": "airbox_filter", "subsystem": "intake", "cylinder": None, "nodes": ["Airbox_Filter"]},
    {"component_id": "radiator", "subsystem": "cooling", "cylinder": None, "nodes": ["Radiator"]},
    {"component_id": "ecu", "subsystem": "control", "cylinder": None, "nodes": ["ECU_Main"]},
]
for item in new_vrde:
    vrde_comps[item["component_id"]] = item

all_vrde_nodes = []
for c in vrde_comps.values():
    all_vrde_nodes.extend(c["nodes"])

vrde_data["components"] = list(vrde_comps.values())
vrde_data["mesh_nodes"] = len(all_vrde_nodes)
vrde_data["representative_geometry"] = "representative 2.2 L CRDI geometry"

with open(vrde_path, "w", encoding="utf-8") as fh:
    json.dump(vrde_data, fh, indent=2)
print(f"Updated {vrde_path}: {len(vrde_data['components'])} components, {vrde_data['mesh_nodes']} nodes.")
