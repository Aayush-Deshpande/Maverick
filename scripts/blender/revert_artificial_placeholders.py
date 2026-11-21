"""
Remove artificial placeholder meshes (primitive cubes/slabs) from all engine .blend files,
restoring 100% authentic CAD realism while preserving PBR aerospace materials and real segmentation.
"""
import bpy
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def clean_vrde():
    blend_path = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "vrde_jayem_2_2l", "vrde_jayem_2_2l.blend")
    print(f"\n[VRDE] Loading {blend_path}")
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    
    # Remove artificial meshes added in B-05
    to_remove = [o for o in bpy.data.objects if o.name.startswith("Radiator") or o.name.startswith("Airbox_Filter") or o.name == "ECU_Lane_A_M_MetalPaintedBlack_0.001" or o.get("placeholder")]
    print(f"  Removing {len(to_remove)} artificial objects: {[o.name for o in to_remove]}")
    for o in to_remove:
        bpy.data.objects.remove(o, do_unlink=True)
        
    bpy.ops.wm.save_mainfile()
    print("  Saved VRDE clean.")

def clean_ae300():
    blend_path = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "austro_ae300", "austro_ae300.blend")
    print(f"\n[AE300] Loading {blend_path}")
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    
    # Remove artificial meshes added in B-05
    to_remove = [o for o in bpy.data.objects if o.name.startswith("Radiator") or o.name == "Thermostat" or o.name == "VGT_Actuator" or o.get("placeholder")]
    print(f"  Removing {len(to_remove)} artificial objects: {[o.name for o in to_remove]}")
    for o in to_remove:
        bpy.data.objects.remove(o, do_unlink=True)
        
    bpy.ops.wm.save_mainfile()
    print("  Saved AE300 clean.")

def clean_rotax_912is():
    blend_path = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_912is", "rotax_912is.blend")
    print(f"\n[ROTAX 912iS] Loading {blend_path}")
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    
    # In 912, remove all 40 placeholder cubes added in B-04
    to_remove = [o for o in bpy.data.objects if o.get("placeholder") or o.name.startswith("Cylinder_Head_") or o.name.startswith("Cylinder_Barrel_") or o.name.startswith("Injector_") or o.name.startswith("Spark_Plug_") or o.name.startswith("Ignition_Coil_") or o.name.startswith("Sensor_") or o.name.startswith("Radiator") or o.name.startswith("Airbox_") or o.name.startswith("Oil_") and o.name.endswith(".001") or o.name.startswith("Water_Pump.001") or o.name.startswith("Fuel_Rail.001") or o.name.startswith("Prop_Flange.001")]
    # Double check we don't remove original 912 objects
    orig_912_names = {
        "Cert_912iSSport_M_Chrome_0", "Cert_912iSSport_M_Labels_0", "Cooling_Air_Baffle_M_PlasticWhite_0",
        "Covers_Theme_M_Chrome_0", "Covers_Theme_M_Cobalt_0", "Covers_Theme_M_PlasticBlack_0",
        "Covers_Theme_M_PlasticCable_0", "Covers_Theme_M_PlasticGreen_0", "Covers_Theme_M_PlasticTheme_0",
        "Covers_Theme_M_PlasticWhite_0", "Covers_Theme_M_Steel_0", "Covers_Theme_M_Steel_0.001",
        "Covers_Theme_M_SteelDark_0", "ECU_M_Chrome_0", "ECU_M_Copper_0", "ECU_M_FuseLight_0",
        "ECU_M_Glass_0", "ECU_M_GlassMilky_0", "ECU_M_Labels_0", "ECU_M_Motherboard_0",
        "ECU_M_PlasticBegue_0", "ECU_M_PlasticBlack_0", "ECU_M_PlasticBlack_0.001", "ECU_M_PlasticBlack_0.002",
        "ECU_M_PlasticBlack_0.003", "ECU_M_PlasticBlack_0.004", "ECU_M_PlasticBlue_0", "ECU_M_PlasticLightBlue_0",
        "ECU_M_PlasticRed_0", "ECU_M_PlasticRedDarker_0", "ECU_M_PlasticYellow_0", "ECU_M_Steel_0",
        "ECU_M_SteelDark_0", "Engine_Suspension_Frame_M_Cobalt_0", "Engine_Suspension_Frame_M_PlasticWhite_0",
        "Exhaust_System_M_Chrome_0", "Exhaust_System_M_Cobalt_0", "Exhaust_System_M_PlasticBlack_0",
        "Exhaust_System_M_Steel_0", "Exhaust_System_M_SteelDark_0", "External_Alternator_M_Rotax914_Extras_0",
        "External_Alternator_M_TimingBelt_0", "Fittings_Metric_Rotax914_A12_0", "Fittings_Metric_Rotax914_Extras_0",
        "Fittings_Metric_Rotax915_A12_0", "Fittings_Metric_Rotax915_Extras_0", "Fittings_UNF_M_Cobalt_0",
        "Fittings_UNF_Rotax915_A12_0", "Fittings_UNF_Rotax915_Extras_0", "Fuel_Pump_M_Chrome_0",
        "Fuel_Pump_M_Cobalt_0", "Fuel_Pump_M_PlasticBlack_0", "Fuel_Pump_M_Rubber_0", "Fuel_Pump_M_Steel_0",
        "Fuel_Pump_M_SteelDark_0", "Gearbox_Type_2_M_Cobalt_0", "Gearbox_Type_2_M_MetalPaintedBlack_0",
        "Gearbox_Type_2_M_PlasticBlack_0", "Gearbox_Type_2_M_PlasticWhite_0", "Gearbox_Type_2_M_Steel_0",
        "Oil_Tank_M_Cobalt_0", "Oil_Tank_M_Labels_0", "Oil_Tank_M_PlasticBlack_0", "Oil_Tank_M_Steel_0",
        "Rotax_912i_Base_M_Black_0", "Rotax_912i_Base_M_Chrome_0", "Rotax_912i_Base_M_Chrome_0.001",
        "Rotax_912i_Base_M_Cobalt_0", "Rotax_912i_Base_M_Cobalt_0.001", "Rotax_912i_Base_M_Copper_0",
        "Rotax_912i_Base_M_Labels_0", "Rotax_912i_Base_M_Motherboard_0", "Rotax_912i_Base_M_PlasticBlack_0",
        "Rotax_912i_Base_M_PlasticBlack_0.001", "Rotax_912i_Base_M_PlasticCable_0",
        "Rotax_912i_Base_M_PlasticCable_0.001", "Rotax_912i_Base_M_PlasticGreen_0", "Rotax_912i_Base_M_Rubber_0",
        "Rotax_912i_Base_M_Steel_0", "Rotax_912i_Base_M_Steel_0.001", "Rotax_912i_Base_M_Steel_0.002",
        "Rotax_912i_Base_M_Steel_0.003", "Rotax_912i_Base_M_Steel_0.004", "Rotax_912i_Base_M_SteelBlack_0",
        "Rotax_912i_Base_M_SteelBlack_0.001", "Rotax_912i_Base_M_SteelDark_0", "Starter_09Kw_M_Labels_0",
        "Starter_09Kw_M_Steel_0", "Starter_Relay_M_Chrome_0", "Starter_Relay_M_Cobalt_0",
        "Starter_Relay_M_PlasticBlack_0", "Starter_Relay_M_PlasticCable_0", "Starter_Relay_M_Steel_0",
        "Vacuum_Pump_Drive_M_Chrome_0", "Vacuum_Pump_Drive_M_Rubber_0", "Water_Hoses_M_Chrome_0",
        "Water_Hoses_M_Cobalt_0", "Water_Hoses_M_Labels_0", "Water_Hoses_M_PlasticBlack_0",
        "Water_Hoses_M_Rubber_0", "Water_Hoses_M_Steel_0", "Water_Hoses_M_SteelDark_0",
        "Wiring_Harness_M_Chrome_0", "Wiring_Harness_M_Cobalt_0", "Wiring_Harness_M_Copper_0",
        "Wiring_Harness_M_PlasticBlack_0", "Wiring_Harness_M_PlasticCable_0",
        "Wiring_Harness_M_PlasticCable_0.001", "Wiring_Harness_M_Steel_0"
    }
    
    really_remove = [o for o in bpy.data.objects if o.name not in orig_912_names]
    print(f"  Removing {len(really_remove)} artificial objects from 912: {[o.name for o in really_remove]}")
    for o in really_remove:
        bpy.data.objects.remove(o, do_unlink=True)
        
    bpy.ops.wm.save_mainfile()
    print("  Saved Rotax 912 clean (100% original CAD geometry preserved).")

def clean_rotax_915is():
    blend_path = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_915is", "rotax_915is.blend")
    print(f"\n[ROTAX 915iS] Loading {blend_path}")
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    
    # Remove artificial cube placeholders that have placeholder=True (like Radiator, Airbox_Filter)
    to_remove = [o for o in bpy.data.objects if o.get("placeholder")]
    print(f"  Removing {len(to_remove)} artificial placeholder objects: {[o.name for o in to_remove]}")
    for o in to_remove:
        bpy.data.objects.remove(o, do_unlink=True)
        
    bpy.ops.wm.save_mainfile()
    print("  Saved Rotax 915 clean.")

clean_vrde()
clean_ae300()
clean_rotax_912is()
clean_rotax_915is()
print("\nAll artificial placeholders reverted!")
