"""
Generate authoritative configs/components/rotax_914.json from rotax_914.glb
and the master blend file.
"""
import json
import os
import struct

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

glb_path = os.path.join(PROJECT_ROOT, "assets", "web", "engines", "rotax_914.glb")
manifest_path = os.path.join(PROJECT_ROOT, "configs", "components", "rotax_914.json")

# Read GLB nodes
with open(glb_path, "rb") as fh:
    magic, _version, _length = struct.unpack("<4sII", fh.read(12))
    chunk_len, chunk_type = struct.unpack("<I4s", fh.read(8))
    doc = json.loads(fh.read(chunk_len).decode("utf-8"))

glb_mesh_nodes = []
for node in doc.get("nodes", []):
    if "mesh" in node:
        name = node.get("name")
        if name:
            glb_mesh_nodes.append(name)

print(f"Total mesh nodes in 914 GLB: {len(glb_mesh_nodes)}")

# Match nodes to components
comp_nodes = {
    # Per-Cylinder
    "cylinder_head_1": [],
    "cylinder_head_2": [],
    "cylinder_head_3": [],
    "cylinder_head_4": [],
    "cylinder_barrel_1": [],
    "cylinder_barrel_2": [],
    "cylinder_barrel_3": [],
    "cylinder_barrel_4": [],
    "spark_plug_1": [],
    "spark_plug_2": [],
    "spark_plug_3": [],
    "spark_plug_4": [],
    "sensor_cht_1": [],
    "sensor_cht_2": [],
    "sensor_cht_3": [],
    "sensor_cht_4": [],
    "sensor_egt_1": [],
    "sensor_egt_2": [],
    "sensor_egt_3": [],
    "sensor_egt_4": [],
    # Added placeholders
    "carburettor_1": [],
    "carburettor_2": [],
    "airbox_filter": [],
    "tcu": [],
    "wastegate": [],
    "wastegate_actuator": [],
    "ignition_cdi": [],
    "oil_tank": [],
    "oil_cooler": [],
    "oil_pump": [],
    "water_pump": [],
    "radiator": [],
    "alternator": [],
    "fuel_pump": [],
    "sensor_map": [],
    "sensor_oil_press": [],
    "sensor_oil_temp": [],
    # Real 914 parts from addendum 3.2
    "crankcase": [],
    "rocker_covers": [],
    "coolant_lines": [],
    "intake_manifold": [],
    "turbo_compressor": [],
    "turbo_turbine": [],
    "exhaust": [],
    "gearbox": [],
    "prop_flange": [],
    "starter": [],
    "fasteners": [],
}

unassigned = []
for name in glb_mesh_nodes:
    if name.startswith("Cylinder_Head_1"):
        comp_nodes["cylinder_head_1"].append(name)
    elif name.startswith("Cylinder_Head_2"):
        comp_nodes["cylinder_head_2"].append(name)
    elif name.startswith("Cylinder_Head_3"):
        comp_nodes["cylinder_head_3"].append(name)
    elif name.startswith("Cylinder_Head_4"):
        comp_nodes["cylinder_head_4"].append(name)
    elif name.startswith("Cylinder_Barrel_1"):
        comp_nodes["cylinder_barrel_1"].append(name)
    elif name.startswith("Cylinder_Barrel_2"):
        comp_nodes["cylinder_barrel_2"].append(name)
    elif name.startswith("Cylinder_Barrel_3"):
        comp_nodes["cylinder_barrel_3"].append(name)
    elif name.startswith("Cylinder_Barrel_4"):
        comp_nodes["cylinder_barrel_4"].append(name)
    elif name.startswith("Spark_Plug_1"):
        comp_nodes["spark_plug_1"].append(name)
    elif name.startswith("Spark_Plug_2"):
        comp_nodes["spark_plug_2"].append(name)
    elif name.startswith("Spark_Plug_3"):
        comp_nodes["spark_plug_3"].append(name)
    elif name.startswith("Spark_Plug_4"):
        comp_nodes["spark_plug_4"].append(name)
    elif name.startswith("Sensor_CHT_1"):
        comp_nodes["sensor_cht_1"].append(name)
    elif name.startswith("Sensor_CHT_2"):
        comp_nodes["sensor_cht_2"].append(name)
    elif name.startswith("Sensor_CHT_3"):
        comp_nodes["sensor_cht_3"].append(name)
    elif name.startswith("Sensor_CHT_4"):
        comp_nodes["sensor_cht_4"].append(name)
    elif name.startswith("Sensor_EGT_1"):
        comp_nodes["sensor_egt_1"].append(name)
    elif name.startswith("Sensor_EGT_2"):
        comp_nodes["sensor_egt_2"].append(name)
    elif name.startswith("Sensor_EGT_3"):
        comp_nodes["sensor_egt_3"].append(name)
    elif name.startswith("Sensor_EGT_4"):
        comp_nodes["sensor_egt_4"].append(name)
    elif name.startswith("Carburettor_1"):
        comp_nodes["carburettor_1"].append(name)
    elif name.startswith("Carburettor_2"):
        comp_nodes["carburettor_2"].append(name)
    elif name.startswith("Airbox_Filter"):
        comp_nodes["airbox_filter"].append(name)
    elif name.startswith("TCU"):
        comp_nodes["tcu"].append(name)
    elif name.startswith("Wastegate_Flapper_Assembly"):
        comp_nodes["wastegate"].append(name)
    elif name.startswith("Wastegate_Actuator"):
        comp_nodes["wastegate_actuator"].append(name)
    elif name.startswith("Ignition_CDI"):
        comp_nodes["ignition_cdi"].append(name)
    elif name.startswith("Oil_Tank"):
        comp_nodes["oil_tank"].append(name)
    elif name.startswith("Oil_Cooler"):
        comp_nodes["oil_cooler"].append(name)
    elif name.startswith("Oil_Pump"):
        comp_nodes["oil_pump"].append(name)
    elif name.startswith("Water_Pump"):
        comp_nodes["water_pump"].append(name)
    elif name.startswith("Radiator"):
        comp_nodes["radiator"].append(name)
    elif name.startswith("Alternator"):
        comp_nodes["alternator"].append(name)
    elif name.startswith("Fuel_Pump"):
        comp_nodes["fuel_pump"].append(name)
    elif name.startswith("Sensor_MAP"):
        comp_nodes["sensor_map"].append(name)
    elif name.startswith("Sensor_Oil_Press"):
        comp_nodes["sensor_oil_press"].append(name)
    elif name.startswith("Sensor_Oil_Temp"):
        comp_nodes["sensor_oil_temp"].append(name)
    elif name.startswith("Rotax914_Crankcase_Block"):
        comp_nodes["crankcase"].append(name)
    elif name.startswith("Rotax914_Rocker_Cover_Red"):
        comp_nodes["rocker_covers"].append(name)
    elif name.startswith("Rotax914_Coolant_Line"):
        comp_nodes["coolant_lines"].append(name)
    elif name.startswith("Rotax914_Intake_Manifold"):
        comp_nodes["intake_manifold"].append(name)
    elif name.startswith("Rotax914_Turbo_Compressor"):
        comp_nodes["turbo_compressor"].append(name)
    elif name.startswith("Rotax914_Turbo_Turbine_Exhaust") or name == "Turbocharger_Exhaust_Plumbing":
        comp_nodes["turbo_turbine"].append(name)
    elif name.startswith("Rotax914_Plumbing_Exhaust"):
        comp_nodes["exhaust"].append(name)
    elif name.startswith("Rotax914_Gearbox_Front"):
        comp_nodes["gearbox"].append(name)
    elif name.startswith("Rotax914_Prop_Flange"):
        comp_nodes["prop_flange"].append(name)
    elif name.startswith("Rotax914_Starter_Motor"):
        comp_nodes["starter"].append(name)
    elif name.startswith("Rotax914_Fitting_Fastener") or name == "Engine_Fittings_Fasteners":
        comp_nodes["fasteners"].append(name)
    else:
        unassigned.append(name)

# Subsystems metadata
subsystems = {
    "cylinder_head_1": ("combustion", 1),
    "cylinder_head_2": ("combustion", 2),
    "cylinder_head_3": ("combustion", 3),
    "cylinder_head_4": ("combustion", 4),
    "cylinder_barrel_1": ("core", 1),
    "cylinder_barrel_2": ("core", 2),
    "cylinder_barrel_3": ("core", 3),
    "cylinder_barrel_4": ("core", 4),
    "spark_plug_1": ("ignition", 1),
    "spark_plug_2": ("ignition", 2),
    "spark_plug_3": ("ignition", 3),
    "spark_plug_4": ("ignition", 4),
    "sensor_cht_1": ("sensors", 1),
    "sensor_cht_2": ("sensors", 2),
    "sensor_cht_3": ("sensors", 3),
    "sensor_cht_4": ("sensors", 4),
    "sensor_egt_1": ("sensors", 1),
    "sensor_egt_2": ("sensors", 2),
    "sensor_egt_3": ("sensors", 3),
    "sensor_egt_4": ("sensors", 4),
    "carburettor_1": ("fuel", 1),
    "carburettor_2": ("fuel", 2),
    "airbox_filter": ("intake", None),
    "tcu": ("control", None),
    "wastegate": ("turbo", None),
    "wastegate_actuator": ("turbo", None),
    "turbo_compressor": ("turbo", None),
    "turbo_turbine": ("turbo", None),
    "exhaust": ("exhaust", None),
    "intake_manifold": ("intake", None),
    "gearbox": ("drivetrain", None),
    "prop_flange": ("drivetrain", None),
    "starter": ("electrical", None),
    "fasteners": ("structure", None),
    "rocker_covers": ("core", None),
    "coolant_lines": ("cooling", None),
    "ignition_cdi": ("ignition", None),
    "oil_tank": ("lubrication", None),
    "oil_cooler": ("lubrication", None),
    "oil_pump": ("lubrication", None),
    "water_pump": ("cooling", None),
    "radiator": ("cooling", None),
    "alternator": ("electrical", None),
    "fuel_pump": ("fuel", None),
    "sensor_map": ("sensors", None),
    "sensor_oil_press": ("sensors", None),
    "sensor_oil_temp": ("sensors", None),
    "crankcase": ("core", None),
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
    "engine_id": "rotax_914",
    "glb": "assets/web/engines/rotax_914.glb",
    "mesh_nodes": len(glb_mesh_nodes),
    "representative_geometry": None,
    "generated_by": "scripts/blender/build_914_manifest.py (Card B-03)",
    "components": components,
    "unassigned_nodes": unassigned,
}

with open(manifest_path, "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2)

print(f"Generated {manifest_path} with {len(components)} components, {len(unassigned)} unassigned nodes.")
