"""
Update configs/faults.json for Austro AE300 and VRDE Jayem 2.2L (Card B-05).
Switches from placeholders/markers to target component IDs.
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

faults_path = os.path.join(PROJECT_ROOT, "configs", "faults.json")
with open(faults_path, "r", encoding="utf-8") as fh:
    f = json.load(fh)

for item in f["faults"]:
    fid = item["id"]
    # AE300
    if fid in ["F15", "F16"]:
        item["components"]["austro_ae300"] = {"now": ["vgt_actuator", "turbocharger"], "marker": False, "marker_for": None}
    elif fid == "F21":
        item["components"]["austro_ae300"] = {"now": ["radiator"], "marker": False, "marker_for": None}
    elif fid == "F22":
        item["components"]["austro_ae300"] = {"now": ["thermostat"], "marker": False, "marker_for": None}
    
    # VRDE
    if fid == "F13":
        item["components"]["vrde_jayem_2_2l"] = {"now": ["airbox_filter"], "marker": False, "marker_for": None}
    elif fid == "F21":
        item["components"]["vrde_jayem_2_2l"] = {"now": ["radiator"], "marker": False, "marker_for": None}
    elif fid == "F36":
        item["components"]["vrde_jayem_2_2l"] = {"now": ["ecu_lane_a", "ecu_lane_b"], "marker": False, "marker_for": None}

with open(faults_path, "w", encoding="utf-8") as fh:
    json.dump(f, fh, indent=2)

print("Updated configs/faults.json for AE300 and VRDE successfully!")
