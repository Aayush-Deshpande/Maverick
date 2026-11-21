"""
Generate authoritative configs/components/rotax_915is.json from rotax_915is.glb
and the master blend file.
"""
import json
import os
import struct

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

glb_path = os.path.join(PROJECT_ROOT, "assets", "web", "engines", "rotax_915is.glb")
manifest_path = os.path.join(PROJECT_ROOT, "configs", "components", "rotax_915is.json")

# Read GLB nodes
with open(glb_path, "rb") as fh:
    magic, _version, _length = struct.unpack("<4sII", fh.read(12))
    chunk_len, chunk_type = struct.unpack("<I4s", fh.read(8))
    doc = json.loads(fh.read(chunk_len).decode("utf-8"))

glb_mesh_nodes = []
node_extras = {}
for node in doc.get("nodes", []):
    if "mesh" in node:
        name = node.get("name")
        if name:
            glb_mesh_nodes.append(name)
            node_extras[name] = node.get("extras", {})

print(f"Total mesh nodes in GLB: {len(glb_mesh_nodes)}")

# Component mapping rules for 915
COMPONENT_DEFS = [
    # Per-Cylinder
    {"id": "cylinder_head_1", "subsystem": "combustion", "cyl": 1, "nodes": ["Cylinder_Head_1"]},
    {"id": "cylinder_head_2", "subsystem": "combustion", "cyl": 2, "nodes": ["Cylinder_Head_2"]},
    {"id": "cylinder_head_3", "subsystem": "combustion", "cyl": 3, "nodes": ["Cylinder_Head_3"]},
    {"id": "cylinder_head_4", "subsystem": "combustion", "cyl": 4, "nodes": ["Cylinder_Head_4"]},
    {"id": "cylinder_barrel_1", "subsystem": "core", "cyl": 1, "nodes": ["Cylinder_Barrel_1"]},
    {"id": "cylinder_barrel_2", "subsystem": "core", "cyl": 2, "nodes": ["Cylinder_Barrel_2"]},
    {"id": "cylinder_barrel_3", "subsystem": "core", "cyl": 3, "nodes": ["Cylinder_Barrel_3"]},
    {"id": "cylinder_barrel_4", "subsystem": "core", "cyl": 4, "nodes": ["Cylinder_Barrel_4"]},
    {"id": "injector_1", "subsystem": "fuel", "cyl": 1, "nodes": ["Injector_1"]},
    {"id": "injector_2", "subsystem": "fuel", "cyl": 2, "nodes": ["Injector_2"]},
    {"id": "injector_3", "subsystem": "fuel", "cyl": 3, "nodes": ["Injector_3"]},
    {"id": "injector_4", "subsystem": "fuel", "cyl": 4, "nodes": ["Injector_4"]},
    {"id": "spark_plug_1", "subsystem": "ignition", "cyl": 1, "nodes": ["Spark_Plug_1"]},
    {"id": "spark_plug_2", "subsystem": "ignition", "cyl": 2, "nodes": ["Spark_Plug_2"]},
    {"id": "spark_plug_3", "subsystem": "ignition", "cyl": 3, "nodes": ["Spark_Plug_3"]},
    {"id": "spark_plug_4", "subsystem": "ignition", "cyl": 4, "nodes": ["Spark_Plug_4"]},
    {"id": "sensor_cht_1", "subsystem": "sensors", "cyl": 1, "nodes": ["Sensor_CHT_1"]},
    {"id": "sensor_cht_2", "subsystem": "sensors", "cyl": 2, "nodes": ["Sensor_CHT_2"]},
    {"id": "sensor_cht_3", "subsystem": "sensors", "cyl": 3, "nodes": ["Sensor_CHT_3"]},
    {"id": "sensor_cht_4", "subsystem": "sensors", "cyl": 4, "nodes": ["Sensor_CHT_4"]},
    {"id": "sensor_egt_1", "subsystem": "sensors", "cyl": 1, "nodes": ["Sensor_EGT_1"]},
    {"id": "sensor_egt_2", "subsystem": "sensors", "cyl": 2, "nodes": ["Sensor_EGT_2"]},
    {"id": "sensor_egt_3", "subsystem": "sensors", "cyl": 3, "nodes": ["Sensor_EGT_3"]},
    {"id": "sensor_egt_4", "subsystem": "sensors", "cyl": 4, "nodes": ["Sensor_EGT_4"]},
    # Core & Subsystems
    {"id": "crankcase", "subsystem": "core", "cyl": None, "nodes": ["Crankcase_Engine_Block", "Engine_Fasteners_Brackets"]},
    {"id": "exhaust", "subsystem": "exhaust", "cyl": None, "nodes": ["Exhaust_Manifold_System"]},
    {"id": "turbocharger", "subsystem": "turbo", "cyl": None, "nodes": ["Turbocharger_Assembly"]},
    {"id": "wastegate", "subsystem": "turbo", "cyl": None, "nodes": ["Wastegate_Actuator"]},
    {"id": "intake_manifold", "subsystem": "intake", "cyl": None, "nodes": ["Intake_Manifold_Plenum", "Intake_Manifold_Runners"]},
    {"id": "intercooler", "subsystem": "turbo", "cyl": None, "nodes": ["Intercooler"]},
    {"id": "overboost_valve", "subsystem": "turbo", "cyl": None, "nodes": ["Overboost valve"]},
    {"id": "magneto_valve_block", "subsystem": "turbo", "cyl": None, "nodes": ["Magnetovalve"]},
    {"id": "fuel_rail", "subsystem": "fuel", "cyl": None, "nodes": ["Fuel_Rail"]},
    {"id": "oil_tank", "subsystem": "lubrication", "cyl": None, "nodes": ["Oil tank"]},
    {"id": "oil_cooler", "subsystem": "lubrication", "cyl": None, "nodes": ["Oil_Cooler"]},
    {"id": "oil_pump", "subsystem": "lubrication", "cyl": None, "nodes": ["Oil_Pump"]},
    {"id": "water_pump", "subsystem": "cooling", "cyl": None, "nodes": ["Water_Pump"]},
    {"id": "radiator", "subsystem": "cooling", "cyl": None, "nodes": ["Radiator"]},
    {"id": "coolant_hoses", "subsystem": "cooling", "cyl": None, "nodes": ["Coolant_Hoses_Harness"]},
    {"id": "air_baffles", "subsystem": "cooling", "cyl": None, "nodes": ["Air baffles"]},
    {"id": "airbox_filter", "subsystem": "intake", "cyl": None, "nodes": ["Airbox_Filter"]},
    {"id": "alternator", "subsystem": "electrical", "cyl": None, "nodes": ["Alternator"]},
    {"id": "gearbox", "subsystem": "drivetrain", "cyl": None, "nodes": ["Tranny"]},
    {"id": "prop_flange", "subsystem": "drivetrain", "cyl": None, "nodes": ["Prop_Flange"]},
    {"id": "ecu", "subsystem": "control", "cyl": None, "nodes": ["ECU", "ECU_Harness_Clip_1", "ECU_Harness_Clip_2", "ECU_Mount_Bracket", "ECU_Mount_Dowel_1", "ECU_Mount_Dowel_2"]},
    {"id": "fusebox", "subsystem": "electrical", "cyl": None, "nodes": ["Fusebox"]},
    {"id": "ambient_sensor", "subsystem": "sensors", "cyl": None, "nodes": ["Ambient sensor"]},
    {"id": "sensor_map", "subsystem": "sensors", "cyl": None, "nodes": ["Sensor_MAP"]},
    {"id": "sensor_oil_press", "subsystem": "sensors", "cyl": None, "nodes": ["Sensor_Oil_Press"]},
]

assigned_nodes = set()
components_list = []
for cdef in COMPONENT_DEFS:
    # Filter nodes that actually exist in the GLB
    existing = [n for n in cdef["nodes"] if n in glb_mesh_nodes]
    if not existing:
        print(f"[WARN] Component {cdef['id']} has no nodes in GLB! Declared: {cdef['nodes']}")
    for n in existing:
        assigned_nodes.add(n)
        
    comp_entry = {
        "component_id": cdef["id"],
        "subsystem": cdef["subsystem"],
        "cylinder": cdef["cyl"],
        "nodes": existing
    }
    components_list.append(comp_entry)

unassigned = [n for n in glb_mesh_nodes if n not in assigned_nodes]
print(f"Assigned {len(assigned_nodes)} nodes across {len(components_list)} components.")
print(f"Unassigned nodes ({len(unassigned)}): {unassigned}")

manifest_data = {
    "engine_id": "rotax_915is",
    "glb": "assets/web/engines/rotax_915is.glb",
    "mesh_nodes": len(glb_mesh_nodes),
    "representative_geometry": None,
    "generated_by": "scripts/blender/build_915_manifest.py (Card B-02)",
    "components": components_list,
    "unassigned_nodes": unassigned
}

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest_data, f, indent=2)

print(f"[SUCCESS] Wrote updated manifest to: {manifest_path}")
