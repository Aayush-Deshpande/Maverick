import bpy, math, mathutils

blend_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend'
bpy.ops.wm.open_mainfile(filepath=blend_path)

# Dictionary of the 8 DRDO Fault Targets with their bounding boxes, camera focus vectors, and part names
fault_targets = {
    'FAULT_1_CYLINDER_OVERHEAT': {
        'name': 'Cylinder #2 & #4 CHT Overheating',
        'target_parts': ['Covers_Theme_M_PlasticTheme_0', 'Covers_Theme_M_PlasticGreen_0'],
        'ghost_parts': ['Cooling_Air_Baffle_M_PlasticWhite_0', 'Engine_Suspension_Frame_M_PlasticWhite_0'],
        'focus_offset': mathutils.Vector((-45.0, -15.0, 15.0)),
        'cam_distance': 95.0,
        'description': 'CHT exceeds 138°C on Cylinder #2 due to cooling restriction.'
    },
    'FAULT_2_FUEL_INJECTOR': {
        'name': 'Electronic Fuel Injector #1 Clog',
        'target_parts': ['Rotax_912i_Base_M_PlasticGreen_0', 'Rotax_912i_Base_M_Steel_0'],
        'ghost_parts': ['Covers_Theme_M_PlasticBlack_0'],
        'focus_offset': mathutils.Vector((0.0, 25.0, 25.0)),
        'cam_distance': 70.0,
        'description': 'Fuel injector flow rate drop causing lean burn condition.'
    },
    'FAULT_3_IGNITION_MISFIRE': {
        'name': 'Ignition Lead Spark Misfire',
        'target_parts': ['Wiring_Harness_M_Copper_0', 'Rotax_912i_Base_M_Copper_0'],
        'ghost_parts': ['Covers_Theme_M_PlasticTheme_0'],
        'focus_offset': mathutils.Vector((-25.0, 0.0, 5.0)),
        'cam_distance': 65.0,
        'description': 'Secondary spark lead voltage breakdown causing combustion misfire.'
    },
    'FAULT_4_LUBRICATION_DECAY': {
        'name': 'Oil Pressure Decay & Reservoir Low',
        'target_parts': ['Oil_Tank_M_Steel_0', 'Oil_Tank_M_Labels_0', 'Rotax_912i_Base_M_Rubber_0'],
        'ghost_parts': ['Wiring_Harness_M_PlasticCable_0'],
        'focus_offset': mathutils.Vector((-55.0, 75.0, -15.0)),
        'cam_distance': 110.0,
        'description': 'Oil supply line cavitation and dry-sump reservoir pressure drop < 2.0 bar.'
    },
    'FAULT_5_GEARBOX_VIBRATION': {
        'name': 'Propeller Gearbox Harmonic Vibration',
        'target_parts': ['Gearbox_Type_2_M_Steel_0', 'Gearbox_Type_2_M_MetalPaintedBlack_0', 'Gearbox_Type_2_M_Cobalt_0'],
        'ghost_parts': [],
        'focus_offset': mathutils.Vector((0.0, -60.0, -10.0)),
        'cam_distance': 85.0,
        'description': 'High-frequency 3rd order vibration harmonics detected on propeller dog clutch.'
    },
    'FAULT_6_EGT_IMBALANCE': {
        'name': 'Exhaust Gas Temperature Imbalance',
        'target_parts': ['Exhaust_System_M_SteelDark_0', 'Exhaust_System_M_Steel_0'],
        'ghost_parts': ['Rotax_912i_Base_M_Steel_0'],
        'focus_offset': mathutils.Vector((0.0, -10.0, -65.0)),
        'cam_distance': 105.0,
        'description': 'EGT temperature differential delta > 60°C between runner #1 and runner #3.'
    },
    'FAULT_7_ALTERNATOR_DROP': {
        'name': 'Alternator Generator Voltage Sag',
        'target_parts': ['External_Alternator_M_Rotax914_Extras_0', 'External_Alternator_M_TimingBelt_0'],
        'ghost_parts': [],
        'focus_offset': mathutils.Vector((35.0, -45.0, 10.0)),
        'cam_distance': 80.0,
        'description': 'Stator winding phase drop causing DC bus voltage to fall to 12.6V.'
    },
    'FAULT_8_ECU_SENSOR_DRIFT': {
        'name': 'Dual FADEC ECU Sensor Drift',
        'target_parts': ['ECU_M_PlasticBlack_0', 'ECU_M_FuseLight_0', 'ECU_M_Motherboard_0', 'ECU_M_GlassMilky_0'],
        'ghost_parts': [],
        'focus_offset': mathutils.Vector((45.0, 65.0, -10.0)),
        'cam_distance': 85.0,
        'description': 'Manifold Absolute Pressure (MAP) sensor correlation drift on Lane A ECU.'
    }
}

# Create / Update Camera Focus Markers for each fault
collection_name = 'Digital_Twin_Fault_Targets'
coll = bpy.data.collections.get(collection_name)
if not coll:
    coll = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(coll)

for fault_id, data in fault_targets.items():
    marker_name = f"Marker_{fault_id}"
    marker = bpy.data.objects.get(marker_name)
    if not marker:
        marker = bpy.data.objects.new(marker_name, None)
        marker.empty_display_type = 'SPHERE'
        marker.empty_display_size = 5.0
        coll.objects.link(marker)
    
    # Position marker at the target component center
    marker.location = data['focus_offset']
    marker['fault_name'] = data['name']
    marker['cam_distance'] = data['cam_distance']
    marker['description'] = data['description']

# Save Blender file with Digital Twin Markers
bpy.ops.wm.save_mainfile()
bpy.ops.wm.save_as_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\hehe\rotax_912_is_sport.blend', copy=True)
print(f"SUCCESS: Configured all 8 DRDO Digital Twin Fault Markers in Blender!")
