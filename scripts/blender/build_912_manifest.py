"""
Generate authoritative configs/components/rotax_912is.json from rotax_912is.glb
and the master blend file (Card B-04).
"""
import json
import os
import struct

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

glb_path = os.path.join(PROJECT_ROOT, "assets", "web", "engines", "rotax_912is.glb")
manifest_path = os.path.join(PROJECT_ROOT, "configs", "components", "rotax_912is.json")

if not os.path.exists(glb_path):
    print(f"GLB not found: {glb_path}")
    exit(1)

with open(glb_path, "rb") as fh:
    magic, _version, _length = struct.unpack("<4sII", fh.read(12))
    chunk_len, chunk_type = struct.unpack("<I4s", fh.read(8))
    doc = json.loads(fh.read(chunk_len).decode("utf-8"))

glb_mesh_nodes = [node["name"] for node in doc.get("nodes", []) if "mesh" in node]
print(f"Total mesh nodes in 912 GLB: {len(glb_mesh_nodes)}")

comp_nodes = {
    # Per-Cylinder Placeholders
    "cylinder_head_1": [],
    "cylinder_head_2": [],
    "cylinder_head_3": [],
    "cylinder_head_4": [],
    "cylinder_barrel_1": [],
    "cylinder_barrel_2": [],
    "cylinder_barrel_3": [],
    "cylinder_barrel_4": [],
    "injector_1": [],
    "injector_2": [],
    "injector_3": [],
    "injector_4": [],
    "spark_plug_1": [],
    "spark_plug_2": [],
    "spark_plug_3": [],
    "spark_plug_4": [],
    "ignition_coil_1": [],
    "ignition_coil_2": [],
    "ignition_coil_3": [],
    "ignition_coil_4": [],
    "sensor_cht_1": [],
    "sensor_cht_2": [],
    "sensor_cht_3": [],
    "sensor_cht_4": [],
    "sensor_egt_1": [],
    "sensor_egt_2": [],
    "sensor_egt_3": [],
    "sensor_egt_4": [],
    # Engine-level Placeholders
    "fuel_rail": [],
    "intake_manifold": [],
    "airbox_filter": [],
    "oil_pump": [],
    "oil_cooler": [],
    "radiator": [],
    "water_pump": [],
    "prop_flange": [],
    "sensor_map": [],
    "sensor_oil_press": [],
    "sensor_oil_temp": [],
    "sensor_coolant_temp": [],
    # Real 912 parts (D47, Addendum 3.1)
    "crankcase": [],
    "covers": [],
    "cert_plate": [],
    "cooling_air_baffle": [],
    "coolant_hoses": [],
    "ecu": [],
    "wiring_harness": [],
    "exhaust": [],
    "alternator": [],
    "fuel_pump": [],
    "gearbox": [],
    "oil_tank": [],
    "engine_mount": [],
    "starter": [],
    "starter_relay": [],
    "vacuum_pump": [],
    "fittings": [],
}

unassigned = []
for name in glb_mesh_nodes:
    if name.startswith("Cylinder_Head_1"): comp_nodes["cylinder_head_1"].append(name)
    elif name.startswith("Cylinder_Head_2"): comp_nodes["cylinder_head_2"].append(name)
    elif name.startswith("Cylinder_Head_3"): comp_nodes["cylinder_head_3"].append(name)
    elif name.startswith("Cylinder_Head_4"): comp_nodes["cylinder_head_4"].append(name)
    elif name.startswith("Cylinder_Barrel_1"): comp_nodes["cylinder_barrel_1"].append(name)
    elif name.startswith("Cylinder_Barrel_2"): comp_nodes["cylinder_barrel_2"].append(name)
    elif name.startswith("Cylinder_Barrel_3"): comp_nodes["cylinder_barrel_3"].append(name)
    elif name.startswith("Cylinder_Barrel_4"): comp_nodes["cylinder_barrel_4"].append(name)
    elif name.startswith("Injector_1"): comp_nodes["injector_1"].append(name)
    elif name.startswith("Injector_2"): comp_nodes["injector_2"].append(name)
    elif name.startswith("Injector_3"): comp_nodes["injector_3"].append(name)
    elif name.startswith("Injector_4"): comp_nodes["injector_4"].append(name)
    elif name.startswith("Spark_Plug_1"): comp_nodes["spark_plug_1"].append(name)
    elif name.startswith("Spark_Plug_2"): comp_nodes["spark_plug_2"].append(name)
    elif name.startswith("Spark_Plug_3"): comp_nodes["spark_plug_3"].append(name)
    elif name.startswith("Spark_Plug_4"): comp_nodes["spark_plug_4"].append(name)
    elif name.startswith("Ignition_Coil_1"): comp_nodes["ignition_coil_1"].append(name)
    elif name.startswith("Ignition_Coil_2"): comp_nodes["ignition_coil_2"].append(name)
    elif name.startswith("Ignition_Coil_3"): comp_nodes["ignition_coil_3"].append(name)
    elif name.startswith("Ignition_Coil_4"): comp_nodes["ignition_coil_4"].append(name)
    elif name.startswith("Sensor_CHT_1"): comp_nodes["sensor_cht_1"].append(name)
    elif name.startswith("Sensor_CHT_2"): comp_nodes["sensor_cht_2"].append(name)
    elif name.startswith("Sensor_CHT_3"): comp_nodes["sensor_cht_3"].append(name)
    elif name.startswith("Sensor_CHT_4"): comp_nodes["sensor_cht_4"].append(name)
    elif name.startswith("Sensor_EGT_1"): comp_nodes["sensor_egt_1"].append(name)
    elif name.startswith("Sensor_EGT_2"): comp_nodes["sensor_egt_2"].append(name)
    elif name.startswith("Sensor_EGT_3"): comp_nodes["sensor_egt_3"].append(name)
    elif name.startswith("Sensor_EGT_4"): comp_nodes["sensor_egt_4"].append(name)
    elif name.startswith("Fuel_Rail"): comp_nodes["fuel_rail"].append(name)
    elif name.startswith("Intake_Manifold"): comp_nodes["intake_manifold"].append(name)
    elif name.startswith("Airbox_Filter"): comp_nodes["airbox_filter"].append(name)
    elif name.startswith("Oil_Pump"): comp_nodes["oil_pump"].append(name)
    elif name.startswith("Oil_Cooler"): comp_nodes["oil_cooler"].append(name)
    elif name.startswith("Radiator"): comp_nodes["radiator"].append(name)
    elif name.startswith("Water_Pump"): comp_nodes["water_pump"].append(name)
    elif name.startswith("Prop_Flange"): comp_nodes["prop_flange"].append(name)
    elif name.startswith("Sensor_MAP"): comp_nodes["sensor_map"].append(name)
    elif name.startswith("Sensor_Oil_Press"): comp_nodes["sensor_oil_press"].append(name)
    elif name.startswith("Sensor_Oil_Temp"): comp_nodes["sensor_oil_temp"].append(name)
    elif name.startswith("Sensor_Coolant_Temp"): comp_nodes["sensor_coolant_temp"].append(name)
    elif name.startswith("Rotax_912i_Base"): comp_nodes["crankcase"].append(name)
    elif name.startswith("Covers_Theme"): comp_nodes["covers"].append(name)
    elif name.startswith("Cert_912iSSport"): comp_nodes["cert_plate"].append(name)
    elif name.startswith("Cooling_Air_Baffle"): comp_nodes["cooling_air_baffle"].append(name)
    elif name.startswith("Water_Hoses"): comp_nodes["coolant_hoses"].append(name)
    elif name.startswith("ECU"): comp_nodes["ecu"].append(name)
    elif name.startswith("Wiring_Harness"): comp_nodes["wiring_harness"].append(name)
    elif name.startswith("Exhaust_System"): comp_nodes["exhaust"].append(name)
    elif name.startswith("External_Alternator"): comp_nodes["alternator"].append(name)
    elif name.startswith("Fuel_Pump"): comp_nodes["fuel_pump"].append(name)
    elif name.startswith("Gearbox_Type_2"): comp_nodes["gearbox"].append(name)
    elif name.startswith("Oil_Tank"): comp_nodes["oil_tank"].append(name)
    elif name.startswith("Engine_Suspension_Frame"): comp_nodes["engine_mount"].append(name)
    elif name.startswith("Starter_09Kw"): comp_nodes["starter"].append(name)
    elif name.startswith("Starter_Relay"): comp_nodes["starter_relay"].append(name)
    elif name.startswith("Vacuum_Pump_Drive"): comp_nodes["vacuum_pump"].append(name)
    elif name.startswith("Fittings"): comp_nodes["fittings"].append(name)
    else: unassigned.append(name)

subsystems = {
    "cylinder_head_1": ("combustion", 1),
    "cylinder_head_2": ("combustion", 2),
    "cylinder_head_3": ("combustion", 3),
    "cylinder_head_4": ("combustion", 4),
    "cylinder_barrel_1": ("core", 1),
    "cylinder_barrel_2": ("core", 2),
    "cylinder_barrel_3": ("core", 3),
    "cylinder_barrel_4": ("core", 4),
    "injector_1": ("fuel", 1),
    "injector_2": ("fuel", 2),
    "injector_3": ("fuel", 3),
    "injector_4": ("fuel", 4),
    "spark_plug_1": ("ignition", 1),
    "spark_plug_2": ("ignition", 2),
    "spark_plug_3": ("ignition", 3),
    "spark_plug_4": ("ignition", 4),
    "ignition_coil_1": ("ignition", 1),
    "ignition_coil_2": ("ignition", 2),
    "ignition_coil_3": ("ignition", 3),
    "ignition_coil_4": ("ignition", 4),
    "sensor_cht_1": ("sensors", 1),
    "sensor_cht_2": ("sensors", 2),
    "sensor_cht_3": ("sensors", 3),
    "sensor_cht_4": ("sensors", 4),
    "sensor_egt_1": ("sensors", 1),
    "sensor_egt_2": ("sensors", 2),
    "sensor_egt_3": ("sensors", 3),
    "sensor_egt_4": ("sensors", 4),
    "fuel_rail": ("fuel", None),
    "intake_manifold": ("intake", None),
    "airbox_filter": ("intake", None),
    "oil_pump": ("lubrication", None),
    "oil_cooler": ("lubrication", None),
    "radiator": ("cooling", None),
    "water_pump": ("cooling", None),
    "prop_flange": ("drivetrain", None),
    "sensor_map": ("sensors", None),
    "sensor_oil_press": ("sensors", None),
    "sensor_oil_temp": ("sensors", None),
    "sensor_coolant_temp": ("sensors", None),
    "crankcase": ("core", None),
    "covers": ("structure", None),
    "cert_plate": ("structure", None),
    "cooling_air_baffle": ("cooling", None),
    "coolant_hoses": ("cooling", None),
    "ecu": ("control", None),
    "wiring_harness": ("electrical", None),
    "exhaust": ("exhaust", None),
    "alternator": ("electrical", None),
    "fuel_pump": ("fuel", None),
    "gearbox": ("drivetrain", None),
    "oil_tank": ("lubrication", None),
    "engine_mount": ("structure", None),
    "starter": ("electrical", None),
    "starter_relay": ("electrical", None),
    "vacuum_pump": ("accessories", None),
    "fittings": ("structure", None),
}

components = []
for cid, nodes in comp_nodes.items():
    if nodes:
        subsys, cyl = subsystems.get(cid, ("core", None))
        entry = {
            "component_id": cid,
            "subsystem": subsys,
            "cylinder": cyl,
            "nodes": sorted(nodes),
        }
        components.append(entry)

manifest = {
    "engine_id": "rotax_912is",
    "glb": "assets/web/engines/rotax_912is.glb",
    "mesh_nodes": len(glb_mesh_nodes),
    "representative_geometry": None,
    "generated_by": "scripts/blender/build_912_manifest.py (Card B-04)",
    "components": components,
    "unassigned_nodes": unassigned,
}

with open(manifest_path, "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2)

print(f"Generated {manifest_path} with {len(components)} components, {len(unassigned)} unassigned nodes.")
