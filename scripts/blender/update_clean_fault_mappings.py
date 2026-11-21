import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FAULTS_JSON = os.path.join(ROOT, "configs", "faults.json")

with open(FAULTS_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

for fault in data["faults"]:
    fid = fault["id"]
    comps = fault.get("components", {})
    
    # Austro AE300
    if "austro_ae300" in comps:
        entry = comps["austro_ae300"]
        if "vgt_actuator" in entry.get("now", []):
            entry["now"] = ["turbocharger"]
            entry["marker"] = True
            entry["marker_for"] = "VGT actuator"
        if "radiator" in entry.get("now", []):
            entry["now"] = ["water_pump"]
            entry["marker"] = True
            entry["marker_for"] = "radiator"
        if "thermostat" in entry.get("now", []):
            entry["now"] = ["water_pump"]
            entry["marker"] = True
            entry["marker_for"] = "thermostat"
            
    # VRDE Jayem 2.2L
    if "vrde_jayem_2_2l" in comps:
        entry = comps["vrde_jayem_2_2l"]
        if "airbox_filter" in entry.get("now", []):
            entry["now"] = ["intake_manifold"]
            entry["marker"] = True
            entry["marker_for"] = "air filter"
        if "radiator" in entry.get("now", []):
            entry["now"] = ["water_pump"]
            entry["marker"] = True
            entry["marker_for"] = "radiator"
        if "ecu_main" in entry.get("now", []):
            entry["now"] = ["ecu_lane_a", "ecu_lane_b"]
            entry["marker"] = False
            entry["marker_for"] = None
            
    # Rotax 912 iS
    if "rotax_912is" in comps:
        entry = comps["rotax_912is"]
        if fid in ["F01", "F02", "F30", "F31"]:
            entry["now"] = ["wiring_harness"]
            entry["marker"] = True
            entry["marker_for"] = "spark plug / coil of cylinder {cyl}"
        elif fid == "F03":
            entry["now"] = ["covers"]
            entry["marker"] = True
            entry["marker_for"] = "cylinder {cyl}"
        elif fid in ["F05", "F07"]:
            entry["now"] = ["fuel_pump"]
            entry["marker"] = True
            entry["marker_for"] = "injector of cylinder {cyl}"
        elif fid == "F19":
            entry["now"] = ["coolant_hoses"]
            entry["marker"] = True
            entry["marker_for"] = "cylinder {cyl} head cooling"
        elif fid == "F20":
            entry["now"] = ["coolant_hoses"]
            entry["marker"] = True
            entry["marker_for"] = "water pump"
        elif fid == "F21":
            entry["now"] = ["coolant_hoses"]
            entry["marker"] = True
            entry["marker_for"] = "radiator"
        elif fid == "F25":
            entry["now"] = ["oil_tank"]
            entry["marker"] = True
            entry["marker_for"] = "oil cooler"
        elif fid == "F26":
            entry["now"] = ["engine_mount"]
            entry["marker"] = True
            entry["marker_for"] = "crankcase"
        elif fid == "F28":
            entry["now"] = ["gearbox"]
            entry["marker"] = True
            entry["marker_for"] = "prop flange"
        elif fid == "F13":
            entry["now"] = []
            entry["marker"] = True
            entry["marker_for"] = "airbox / air filter"
            
    # Rotax 914
    if "rotax_914" in comps:
        entry = comps["rotax_914"]
        if fid in ["F01", "F02", "F19", "F30", "F31"]:
            entry["now"] = ["cylinder_head_{cyl}"]
            entry["marker"] = False
            entry["marker_for"] = None
        elif fid == "F03":
            entry["now"] = ["cylinder_head_1", "cylinder_head_2", "cylinder_head_3", "cylinder_head_4"]
            entry["marker"] = False
            entry["marker_for"] = None
        elif fid in ["F05", "F07"]:
            entry["now"] = ["intake_manifold"]
            entry["marker"] = True
            entry["marker_for"] = "fuel delivery of cylinder {cyl}"
        elif fid == "F13":
            entry["now"] = ["intake_manifold"]
            entry["marker"] = True
            entry["marker_for"] = "air filter"
        elif fid in ["F15", "F16"]:
            entry["now"] = ["wastegate"]
            entry["marker"] = False
            entry["marker_for"] = None
        elif fid == "F21":
            entry["now"] = ["coolant_lines"]
            entry["marker"] = True
            entry["marker_for"] = "radiator"
            
    # Rotax 915 iS
    if "rotax_915is" in comps:
        entry = comps["rotax_915is"]
        if fid in ["F01", "F02", "F19", "F30", "F31"]:
            entry["now"] = ["cylinder_head_{cyl}"]
            entry["marker"] = False
            entry["marker_for"] = None
        elif fid == "F03":
            entry["now"] = ["cylinder_head_1", "cylinder_head_2", "cylinder_head_3", "cylinder_head_4"]
            entry["marker"] = False
            entry["marker_for"] = None
        elif fid in ["F05", "F07"]:
            entry["now"] = ["intake_manifold"]
            entry["marker"] = True
            entry["marker_for"] = "injector of cylinder {cyl}"
        elif fid == "F13":
            entry["now"] = ["intake_manifold"]
            entry["marker"] = True
            entry["marker_for"] = "air filter"
        elif fid in ["F15", "F16"]:
            entry["now"] = ["turbocharger"]
            entry["marker"] = False
            entry["marker_for"] = None
        elif fid == "F21":
            entry["now"] = ["coolant_hoses"]
            entry["marker"] = True
            entry["marker_for"] = "radiator"

with open(FAULTS_JSON, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Updated configs/faults.json successfully.")
