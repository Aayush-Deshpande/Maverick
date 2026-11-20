"""Card M0-03: build configs/components/<engine_id>.json from the canonical web models (assets/web/engines/*.glb)
using the component patterns of ANUMAAN_COMPONENTS_ADDENDUM.txt section 3. Patterns are used ONCE here to produce
exact node-name lists; viewers match exact names only (never substrings).

Prints, per engine: patterns that match nothing (error) and mesh nodes that no component claims (to review).
Re-run after every model export (Phase 7) and commit the regenerated manifests.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glb_nodes import node_names  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, "configs", "components")

# (component_id, subsystem, cylinder, regex, note). Order matters: the first matching component claims a node.
P = {
    "rotax_912is": [
        ("ecu", "control", None, r"ECU_.*", ""),
        ("wiring_harness", "electrical", None, r"Wiring_Harness_.*", ""),
        ("alternator", "electrical", None, r"External_Alternator_.*", ""),
        ("starter", "electrical", None, r"Starter_09Kw_.*", ""),
        ("starter_relay", "electrical", None, r"Starter_Relay_.*", ""),
        ("fuel_pump", "fuel", None, r"Fuel_Pump_.*", ""),
        ("oil_tank", "lubrication", None, r"Oil_Tank_.*", ""),
        ("gearbox", "drivetrain", None, r"Gearbox_Type_2_.*", ""),
        ("exhaust", "exhaust", None, r"Exhaust_System_.*", ""),
        ("coolant_hoses", "cooling", None, r"Water_Hoses_.*", ""),
        ("cooling_air_baffle", "cooling", None, r"Cooling_Air_Baffle_.*", ""),
        ("engine_mount", "structure", None, r"Engine_Suspension_Frame_.*", ""),
        ("vacuum_pump", "accessories", None, r"Vacuum_Pump_Drive_.*", ""),
        ("covers", "structure", None, r"Covers_Theme_.*", ""),
        ("cert_plate", "structure", None, r"Cert_912iSSport_.*", ""),
        ("fittings", "structure", None, r"Fittings_.*", ""),
        ("crankcase_cylinders_base", "core", None, r"Rotax_912i_Base_.*",
         "crankcase, barrels and heads merged; split per cylinder in Phase 7 (A section 4)"),
    ],
    "rotax_914": [
        ("crankcase", "core", None, r"Rotax914_Crankcase_Block.*", ""),
        ("cylinder_bank_unverified", "core", None, r"Rotax914_Cylinder_(Bank|Head)_.*",
         "names do not match cylinders (A 2.1); identify visually in Phase 7"),
        ("rocker_covers", "core", None, r"Rotax914_Rocker_Cover_Red.*", ""),
        ("coolant_lines", "cooling", None, r"Rotax914_Coolant_Line.*", ""),
        ("intake_manifold", "induction", None, r"Rotax914_Intake_Manifold.*", ""),
        ("turbo_compressor", "turbo", None, r"Rotax914_Turbo_Compressor.*", ""),
        ("turbo_turbine", "turbo", None, r"Rotax914_Turbo_Turbine_Exhaust.*", ""),
        ("wastegate_MISSEGMENTED", "turbo", None, r"Rotax914_Turbo_Wastegate.*",
         "320 objects, mostly fasteners/plumbing (A 2.2); never highlight as the wastegate"),
        ("exhaust", "exhaust", None, r"Rotax914_Plumbing_Exhaust.*", ""),
        ("gearbox", "drivetrain", None, r"Rotax914_Gearbox_Front.*", ""),
        ("prop_flange", "drivetrain", None, r"Rotax914_Prop_Flange.*", ""),
        ("starter", "electrical", None, r"Rotax914_Starter_Motor.*", ""),
        ("fasteners", "structure", None, r"Rotax914_Fitting_Fastener.*", ""),
    ],
    "rotax_915is": [
        ("main_engine_MERGED", "core", None, r"Main engine.*", "almost the whole engine in one object; split in Phase 7"),
        ("air_baffles", "cooling", None, r"Air baffles.*", "cooling baffles, NOT the air filter"),
        ("intercooler", "turbo", None, r"Intercooler.*", ""),
        ("oil_tank", "lubrication", None, r"Oil tank.*", ""),
        ("overboost_valve", "turbo", None, r"Overboost valve.*", ""),
        ("magneto_valve_block", "turbo", None, r"Magnetovalve.*", ""),
        ("ecu", "control", None, r"ECU.*", ""),
        ("fusebox", "electrical", None, r"Fusebox.*", ""),
        ("gearbox", "drivetrain", None, r"Tranny.*", ""),
        ("ambient_sensor", "sensors", None, r"Ambient sensor.*", ""),
        ("unnamed_cad_parts", "unknown", None, r"\d+_@OIS@.*", "CAD-id objects; identify in Phase 7"),
    ],
}

AE = [
    ("injector_{n}", "fuel", "{n}", r"Injector_{n}_M.*", ""),
    ("fuel_line_{n}", "fuel", "{n}", r"Fuel_Line_{n}_M.*", ""),
    ("sensor_egt_{n}", "sensors", "{n}", r"Sensor_EGT_{n}.*", ""),
    ("injector_hardware", "fuel", None, r"Injector_(Hold_Downs|Plugs).*", ""),
    ("common_rail", "fuel", None, r"Common_Rail.*", ""),
    ("rail_pressure_valve", "fuel", None, r"Rail_PLV_Valve.*", ""),
    ("hp_fuel_pump", "fuel", None, r"HP_Fuel_(Pump|Nuts).*", ""),
    ("fuel_metering_unit", "fuel", None, r"Fuel_Pump_ZME.*", ""),
    ("aux_fuel_pump", "fuel", None, r"Aux_Pump.*", ""),
    ("fuel_lines_misc", "fuel", None, r"Fuel_(Banjo|Line_Comp|Line_Dampers|Quick|Spill).*", ""),
    ("glow_plugs", "combustion", None, r"Glow_Plugs.*", "all four glow plugs in one object"),
    ("glow_control_unit", "combustion", None, r"(Glow_Plug_Control_Unit|GPC_).*", ""),
    ("air_filter", "induction", None, r"(Air_Filter_Box|Air_Filter_Duct|Air_Cleaner_Straps|Air_Intake_Duct).*", ""),
    ("intake_manifold", "induction", None, r"(Intake_Manifold|Manifold_Fasteners).*", ""),
    ("turbocharger", "turbo", None, r"(Turbocharger|VGT_Label|Heat_Shield_Turbo).*", ""),
    ("turbo_oil_lines", "turbo", None, r"Turbo_Oil_(Feed|Drain).*", ""),
    ("turbo_coolant_lines", "turbo", None, r"Turbo_Coolant_Lines.*", ""),
    ("boost_pipes", "turbo", None, r"(Boost_Pipe_|Silicone_Coupler_|Hose_Clamps_).*", ""),
    ("intercooler", "turbo", None, r"Intercooler.*", ""),
    ("exhaust", "exhaust", None, r"Exhaust_(Manifold|Downpipe).*", ""),
    ("water_pump", "cooling", None, r"Water_Pump.*", ""),
    ("coolant_hoses", "cooling", None, r"(Coolant_|Bypass_Hose).*", ""),
    ("oil_sump", "lubrication", None, r"Oil_Sump.*", ""),
    ("oil_filter", "lubrication", None, r"Oil_Filter_.*", ""),
    ("oil_cooler", "lubrication", None, r"Oil_Cooler_.*", ""),
    ("oil_fill_dipstick", "lubrication", None, r"(Oil_Dipstick|Oil_Filler|Dipstick).*", ""),
    ("crankcase_breather", "lubrication", None, r"(Crankcase_Breather|Breather_Hose|Top_Breather_Hose).*", ""),
    ("prop_governor", "drivetrain", None, r"(Prop_Governor_PCU|PCU_Oil_Line).*", ""),
    ("prop_flange", "drivetrain", None, r"Prop_Flange.*", ""),
    ("gearbox", "drivetrain", None, r"(Gearbox|GB_Bolt_).*", ""),
    ("alternator", "electrical", None, r"(Generator_1|Alternator_).*", ""),
    ("belt_drive", "electrical", None, r"(Serpentine_Belt|Belt_Tensioner|Idler_Pulley).*", ""),
    ("vacuum_pump", "accessories", None, r"Vacuum_Tandem_Pump.*", ""),
    ("starter", "electrical", None, r"Starter.*", ""),
    ("timing_gear", "core", None, r"Timing_Gear_Aux.*", ""),
    ("ecu_lane_a", "control", None, r"ECU_Lane_A.*", ""),
    ("ecu_lane_b", "control", None, r"ECU_Lane_B.*", ""),
    ("ecu_hardware", "control", None, r"ECU_(Bayonet|Details|Label).*", ""),
    ("wiring_harness", "electrical", None, r"(Wiring_Harness|Engine_Harness_Loom|Harness_P_Clamps|Wire_Marker|Ground_Straps).*", ""),
    ("engine_mount", "structure", None, r"(Engine_Mount_Frame|Lord_Mount_).*", ""),
    ("sensor_boost", "sensors", None, r"Sensor_Boost.*", ""),
    ("sensor_charge_air_temp", "sensors", None, r"Sensor_Charge_Air_Temp.*", ""),
    ("sensor_coolant_temp", "sensors", None, r"Sensor_Coolant_Temp.*", ""),
    ("sensor_oil_press", "sensors", None, r"Sensor_Oil_Press.*", ""),
    ("sensor_oil_temp", "sensors", None, r"Sensor_Oil_Temp.*", ""),
    ("sensor_fuel_rail_press", "sensors", None, r"Sensor_Fuel_Rail_Press.*", ""),
    ("sensor_fuel_low_press", "sensors", None, r"Sensor_Fuel_Low_Press.*", ""),
    ("sensor_fuel_temp", "sensors", None, r"Sensor_Fuel_Temp.*", ""),
    ("sensor_fuel_flow", "sensors", None, r"Sensor_Fuel_Flow.*", ""),
    ("sensor_rpm", "sensors", None, r"Sensor_RPM.*", ""),
    ("sensor_crank", "sensors", None, r"Sensor_Crank.*", ""),
    ("sensor_cam", "sensors", None, r"Sensor_Cam.*", ""),
    ("sensor_gearbox_temp", "sensors", None, r"Sensor_Gearbox_Temp.*", ""),
    ("sensor_gearbox_press", "sensors", None, r"Sensor_Gearbox_Press.*", ""),
    ("sensor_turbine_inlet_temp", "sensors", None, r"Sensor_TIT.*", ""),
    ("crank_pulley", "core", None, r"Crank_Pulley.*", ""),
    ("valve_cover", "core", None, r"(Valve_Cover|Cam_Cover_Bolts).*", ""),
    ("cylinder_head", "core", None, r"Cylinder_Head.*", "one object for all cylinders"),
    ("engine_block", "core", None, r"Engine_Block.*", ""),
    ("misc", "structure", None, r"(Blanket_Safety_Wire|Brass_Fittings|Cabin_Heat_Ports|Torque_Seal_Marks).*", ""),
]

VR = [
    ("injector_{n}", "fuel", "{n}", r"Injector_{n}_.*", ""),
    ("fuel_line_hp_{n}", "fuel", "{n}", r"Fuel_Line_HP_Cyl{n}.*", ""),
    ("glow_plug_{n}", "combustion", "{n}", r"Glow_Plug_Cyl{n}.*", ""),
    ("sensor_egt_{n}", "sensors", "{n}", r"Sensor_EGT_{n}.*", ""),
    ("sensor_crank_1", "sensors", None, r"Crank_Sensor(_Wire)?_1.*", ""),
    ("sensor_crank_2", "sensors", None, r"Crank_Sensor(_Wire)?_2.*", ""),
    ("rail_relief_valve", "fuel", None, r"Rail_Relief_Valve.*", ""),
    ("rail_pressure_sensor", "sensors", None, r"Rail_Pressure_Sensor.*", ""),
    ("common_rail", "fuel", None, r"Common_Rail_M.*", ""),
    ("hp_fuel_pump", "fuel", None, r"HP_Fuel_Pump.*", ""),
    ("fuel_filter", "fuel", None, r"(Fuel_Filter_ASAK|Fuel_Hose_ASAK|ASAK_).*", ""),
    ("fuel_return", "fuel", None, r"(Fuel_Return_LeakOff_Rail|Fuel_Return_Hose|Fuel_Feed_Hose).*", ""),
    ("intercooler", "turbo", None, r"Intercooler.*", ""),
    ("turbo_hp", "turbo", None, r"Turbo_HP_(CHRA|CompressorVolute|Inlet_Cap|OilBoss|Turbine|TurbineVolute|VBand).*", ""),
    ("turbo_lp", "turbo", None, r"Turbo_LP_.*", ""),
    ("turbo_ducts", "turbo", None, r"(Turbo_Interstage_Duct|Turbo_Silicone_Coupler|Turbo_T_Clamp_|Swept_C_Hose|Jubilee_Clamp_).*", ""),
    ("turbo_oil_drain", "turbo", None, r"(Turbo_Oil_Drain|Turbo_Drain_).*", ""),
    ("turbo_oil_feed", "turbo", None, r"Oil_Feed_Turbo_.*", ""),
    ("wastegate", "turbo", None, r"(Wastegate_|Turbo_HP_Wastegate_).*", ""),
    ("intake_manifold", "induction", None, r"(Intake_Manifold|Intake_Runner_Boss_|InMan_Bolt).*", ""),
    ("exhaust", "exhaust", None, r"(Exhaust_|ExMan_Bolt).*", ""),
    ("water_pump", "cooling", None, r"Water_Pump.*", ""),
    ("thermostat", "cooling", None, r"Thermostat_Housing.*", ""),
    ("coolant_hoses", "cooling", None, r"(Coolant_|Top_Coolant_).*", ""),
    ("oil_sump", "lubrication", None, r"(Oil_Sump|Sump_Bolt|Sump_Drain_Plug).*", ""),
    ("oil_filter", "lubrication", None, r"Oil_Filter.*", ""),
    ("oil_cooler", "lubrication", None, r"Oil_Cooler.*", ""),
    ("oil_fill_dipstick", "lubrication", None, r"(Oil_Filler_Cap|Dipstick_|Label_Engine_Oil).*", ""),
    ("crankcase_breather", "lubrication", None, r"Crankcase_Breather.*", ""),
    ("prop_governor", "drivetrain", None, r"(Gearbox_Governor|Governor_Port_Cap).*", ""),
    ("prop_flange", "drivetrain", None, r"(Prop_Flange|Prop_Shaft_Cap|Flange_Bolt).*", ""),
    ("sensor_gearbox_vibration", "sensors", None, r"(Sensor_Vibration_Gearbox|Gearbox_Lower_Port_Sensor).*", ""),
    ("gearbox", "drivetrain", None, r"(Gearbox_|GBCover_Bolt|GB_Flange_Bolt|Label_Reduction_Gbx).*", ""),
    ("alternator_1", "electrical", None, r"Generator_1.*", ""),
    ("alternator_2", "electrical", None, r"Generator_2.*", ""),
    ("alternator_wiring", "electrical", None, r"(Alternator_|Power_Drop_Cable_).*", ""),
    ("belt_drive", "electrical", None, r"(Serpentine_Belt|Belt_Tensioner).*", ""),
    ("starter", "electrical", None, r"Starter.*", ""),
    ("ecu_lane_a", "control", None, r"ECU_Lane_A.*", ""),
    ("ecu_lane_b", "control", None, r"ECU_Lane_B.*", ""),
    ("wiring_harness", "electrical", None, r"(Harness_|Connector_Mil_|Common_Rail_Wire_Tray|Label_Harness_Tag).*", ""),
    ("engine_mount", "structure", None, r"(Engine_Mount_|Mount_).*", ""),
    ("lifting_eyes", "structure", None, r"(Lifting_Eye|Lift_Eye_).*", ""),
    ("sensor_boost", "sensors", None, r"Sensor_Boost.*", ""),
    ("sensor_map", "sensors", None, r"Sensor_MAP.*", ""),
    ("sensor_charge_air_temp", "sensors", None, r"Sensor_Charge_Air_Temp.*", ""),
    ("sensor_coolant_temp", "sensors", None, r"Sensor_Coolant_Temp.*", ""),
    ("sensor_oil_press", "sensors", None, r"Sensor_Oil_Press.*", ""),
    ("sensor_oil_temp", "sensors", None, r"Sensor_Oil_Temp.*", ""),
    ("sensor_fuel_rail_press", "sensors", None, r"Sensor_Fuel_Rail_Press.*", ""),
    ("sensor_fuel_flow", "sensors", None, r"Sensor_Fuel_Flow.*", ""),
    ("sensor_rpm", "sensors", None, r"Sensor_RPM.*", ""),
    ("flywheel", "core", None, r"Flywheel.*", ""),
    ("timing_cover", "core", None, r"Timing_Cover_.*", ""),
    ("valve_cover", "core", None, r"(Valve_Cover|VC_Bolt_).*", ""),
    ("cylinder_head", "core", None, r"(Cylinder_Head|Label_Cyl_Head|TC_Bolt_).*", "one object for all cylinders"),
    ("engine_block", "core", None, r"(Engine_Block|BH_Bolt|Bellhousing_Dowel_|Intermediate_Bellhousing|HB_Bolt).*", ""),
    ("misc", "structure", None, r"(Hose_Fitting_|Port_Sensor_Yellow_Cap|Label_|Retainer_Bolt_|Torque_Seal_Marks).*", ""),
]


def expand(patterns, n_cyl=4):
    out = []
    for cid, sub, cyl, rx, note in patterns:
        if "{n}" in cid:
            for n in range(1, n_cyl + 1):
                out.append((cid.replace("{n}", str(n)), sub, n, rx.replace("{n}", str(n)), note))
        else:
            out.append((cid, sub, cyl, rx, note))
    return out


P["austro_ae300"] = expand(AE)
P["vrde_jayem_2_2l"] = expand(VR)

REPRESENTATIVE = {"austro_ae300": "AE330-shaped geometry (representative)",
                  "vrde_jayem_2_2l": "TEI PD170 geometry (representative)"}


def build(engine_id):
    glb = os.path.join(ROOT, "assets", "web", "engines", f"{engine_id}.glb")
    names = node_names(glb, mesh_only=True)
    claimed = {}
    components = []
    empty = []
    for cid, sub, cyl, rx, note in P[engine_id]:
        rgx = re.compile(rx)
        nodes = [n for n in names if n not in claimed and rgx.fullmatch(n)]
        for n in nodes:
            claimed[n] = cid
        if not nodes:
            empty.append(cid)
            continue
        entry = {"component_id": cid, "subsystem": sub, "cylinder": cyl, "nodes": sorted(nodes)}
        if note:
            entry["note"] = note
        components.append(entry)
    unassigned = [n for n in names if n not in claimed]
    manifest = {
        "engine_id": engine_id,
        "glb": f"assets/web/engines/{engine_id}.glb",
        "mesh_nodes": len(names),
        "representative_geometry": REPRESENTATIVE.get(engine_id),
        "generated_by": "scripts/assets/build_component_manifests.py (card M0-03; patterns from addendum section 3)",
        "components": components,
        "unassigned_nodes": unassigned,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, f"{engine_id}.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return len(names), len(components), empty, unassigned


if __name__ == "__main__":
    for eid in P:
        n, c, empty, un = build(eid)
        print(f"{eid}: {n} mesh nodes, {c} components, {len(empty)} patterns matched nothing, {len(un)} unassigned")
        if empty:
            print("   no match:", ", ".join(empty))
        if un:
            print("   unassigned:", ", ".join(un[:40]))
