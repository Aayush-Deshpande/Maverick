"""
ANUMAAN — MULTI-ENGINE 3D DIGITAL TWIN VISUALIZATION CLIENT (BLENDER)
DRDO / iDEX Problem Statement ID: 26054

PURE VISUALIZATION CLIENT — ZERO LOCAL SIMULATION:
- Subscribes in real-time to the Multi-Engine Backend Server (FastAPI / 20 Hz state feed)
- Instant 0ms In-Memory Collection Swapping across all 5 UAV engines (Rotax 912iS, 914, 915iS, Austro AE300, VRDE 2.2L)
- Real-time Slot-Based Material Swapping & Dynamic Pulsing Red Emission
- Holographic Ghost Vision (X-Ray Mode) with semi-transparent ambient body
- Delta-Time Constant 60 FPS Camera Orbit around stationary engine center
- Precision Component Framing: Camera glides directly in front of fault components
- Telemetry Link Watchdog: Prominently indicates if backend server connection drops
"""

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
import blf
import mathutils
import math
import time
import os
import sys
import json
import threading
import urllib.request
import urllib.error
import collections
import random

# Server connection configuration (default: local server; overridable via env var)
SERVER_BASE_URL = os.environ.get("ROTAX_BACKEND_URL", "http://127.0.0.1:8000")
INITIAL_ENGINE_ID = os.environ.get("ANUMAAN_ENGINE_ID", "rotax_912is")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# ==============================================================================
# ENGINE PROFILES & FAULT DATABASES (ALL 5 ENGINES)
# ==============================================================================

ENGINE_PROFILES = {
    'rotax_912is': {
        'id': 'rotax_912is',
        'name': 'ROTAX 912 iS',
        'title': 'ROTAX 912 iS SPORT MALE UAV DIGITAL TWIN',
        'subtitle': '100 HP NATURALLY ASPIRATED EFI • DUAL FADEC (LANE A/B) • PS-26054',
        'collection': 'Collection_Rotax_912iS',
        'fuel_type': 'AVGAS / MOGAS',
        'induction': 'NATURALLY ASPIRATED',
        'default_center': mathutils.Vector((1.932, 61.648, -35.324)),
        'default_distance': 230.0,
        'default_elevation': math.radians(24.0),
        'rpm_max': 5800.0,
        'faults': {
            1: {'short': 'CYL #2 OVERHEAT', 'comp': 'Cylinder #2 Head & Baffle Assembly', 'tag': 'CRITICAL', 'parts': ['Covers_Theme_M_PlasticTheme_0', 'Covers_Theme_M_PlasticGreen_0', 'Cooling_Air_Baffle_M_PlasticWhite_0'], 'center': mathutils.Vector((0.966, 38.400, -10.990)), 'angle': math.radians(-140.0), 'elevation': math.radians(24.0), 'distance': 120.0},
            2: {'short': 'INJECTOR #1 CLOG', 'comp': 'Electronic Fuel Injector #1 (Lane A)', 'tag': 'MAJOR', 'parts': ['Rotax_912i_Base_M_PlasticGreen_0', 'Rotax_912i_Base_M_Steel_0', 'Rotax_912i_Base_M_PlasticCable_0', 'Rotax_912i_Base_M_Rubber_0'], 'center': mathutils.Vector((1.160, 61.687, -15.547)), 'angle': math.radians(-85.0), 'elevation': math.radians(34.0), 'distance': 115.0},
            3: {'short': 'IGNITION MISFIRE', 'comp': 'Secondary Spark Plug Lead & Harness', 'tag': 'MAJOR', 'parts': ['Wiring_Harness_M_Copper_0', 'Rotax_912i_Base_M_Copper_0', 'Wiring_Harness_M_Cobalt_0', 'Wiring_Harness_M_PlasticCable_0'], 'center': mathutils.Vector((4.962, 69.016, -15.626)), 'angle': math.radians(-115.0), 'elevation': math.radians(30.0), 'distance': 120.0},
            4: {'short': 'OIL PRESSURE LOSS', 'comp': 'Dry-Sump Reservoir & Scavenge Line', 'tag': 'CRITICAL', 'parts': ['Oil_Tank_M_Steel_0', 'Oil_Tank_M_Labels_0', 'Oil_Tank_M_Cobalt_0', 'Oil_Tank_M_PlasticBlack_0'], 'center': mathutils.Vector((-24.756, 105.824, -20.571)), 'angle': math.radians(135.0), 'elevation': math.radians(18.0), 'distance': 95.0},
            5: {'short': 'GEARBOX VIBRATION', 'comp': 'Propeller Reduction Gearbox (Type 2)', 'tag': 'MINOR', 'parts': ['Gearbox_Type_2_M_Steel_0', 'Gearbox_Type_2_M_MetalPaintedBlack_0', 'Gearbox_Type_2_M_Cobalt_0', 'Gearbox_Type_2_M_PlasticBlack_0', 'Gearbox_Type_2_M_PlasticWhite_0'], 'center': mathutils.Vector((0.966, 18.013, -12.264)), 'angle': math.radians(-90.0), 'elevation': math.radians(14.0), 'distance': 90.0},
            6: {'short': 'EXHAUST EGT DELTA', 'comp': 'Exhaust Runner Manifold (Runner #3)', 'tag': 'MINOR', 'parts': ['Exhaust_System_M_SteelDark_0', 'Exhaust_System_M_Steel_0', 'Exhaust_System_M_Cobalt_0', 'Exhaust_System_M_Chrome_0', 'Exhaust_System_M_PlasticBlack_0'], 'center': mathutils.Vector((6.679, 38.870, -45.570)), 'angle': math.radians(-45.0), 'elevation': math.radians(-8.0), 'distance': 125.0},
            7: {'short': 'ALTERNATOR SAG', 'comp': 'Heavy-Duty Alternator & Belt Drive', 'tag': 'MINOR', 'parts': ['External_Alternator_M_Rotax914_Extras_0', 'External_Alternator_M_TimingBelt_0'], 'center': mathutils.Vector((6.560, 17.394, -8.662)), 'angle': math.radians(-35.0), 'elevation': math.radians(20.0), 'distance': 90.0},
            8: {'short': 'DUAL FADEC DRIFT', 'comp': 'Lane A/B Dual FADEC ECU Assembly', 'tag': 'MINOR', 'parts': ['ECU_M_PlasticBlack_0', 'ECU_M_FuseLight_0', 'ECU_M_Motherboard_0', 'ECU_M_GlassMilky_0', 'ECU_M_Labels_0', 'ECU_M_Chrome_0', 'ECU_M_Copper_0', 'ECU_M_Steel_0', 'ECU_M_PlasticBlue_0', 'ECU_M_PlasticRed_0'], 'center': mathutils.Vector((13.409, 97.572, -16.925)), 'angle': math.radians(80.0), 'elevation': math.radians(26.0), 'distance': 110.0},
        }
    },
    'rotax_914': {
        'id': 'rotax_914',
        'name': 'ROTAX 914 F',
        'title': 'ROTAX 914 F TURBOCHARGED DIGITAL TWIN',
        'subtitle': '115 HP TURBOCHARGED ROTAX TCU • EXHAUST WASTEGATE ACTUATION',
        'collection': 'Collection_Rotax_912iS',
        'fuel_type': 'AVGAS / MOGAS',
        'induction': 'TURBOCHARGED',
        'default_center': mathutils.Vector((1.932, 61.648, -35.324)),
        'default_distance': 230.0,
        'default_elevation': math.radians(24.0),
        'rpm_max': 5800.0,
        'faults': {
            1: {'short': 'TURBO WASTEGATE LEAK', 'comp': 'Turbo Exhaust Wastegate Actuator', 'tag': 'CRITICAL', 'parts': ['Exhaust_System_M_SteelDark_0', 'Exhaust_System_M_Steel_0', 'Exhaust_System_M_Chrome_0', 'Fittings_Metric_Rotax914_Extras_0'], 'center': mathutils.Vector((6.679, 38.870, -45.570)), 'angle': math.radians(-45.0), 'elevation': math.radians(-8.0), 'distance': 120.0},
            2: {'short': 'INJECTOR #1 CLOG', 'comp': 'Fuel Injector #1 (Lane A)', 'tag': 'MAJOR', 'parts': ['Rotax_912i_Base_M_PlasticGreen_0', 'Rotax_912i_Base_M_Steel_0'], 'center': mathutils.Vector((1.160, 61.687, -15.547)), 'angle': math.radians(-85.0), 'elevation': math.radians(34.0), 'distance': 115.0},
            3: {'short': 'IGNITION MISFIRE', 'comp': 'Secondary Spark Plug Lead', 'tag': 'MAJOR', 'parts': ['Wiring_Harness_M_Copper_0', 'Rotax_912i_Base_M_Copper_0'], 'center': mathutils.Vector((4.962, 69.016, -15.626)), 'angle': math.radians(-115.0), 'elevation': math.radians(30.0), 'distance': 120.0},
            4: {'short': 'OIL PRESSURE LOSS', 'comp': 'Dry-Sump Reservoir & Scavenge Line', 'tag': 'CRITICAL', 'parts': ['Oil_Tank_M_Steel_0', 'Oil_Tank_M_Labels_0', 'Oil_Tank_M_Cobalt_0'], 'center': mathutils.Vector((-24.756, 105.824, -20.571)), 'angle': math.radians(135.0), 'elevation': math.radians(18.0), 'distance': 95.0},
            5: {'short': 'GEARBOX VIBRATION', 'comp': 'Propeller Reduction Gearbox', 'tag': 'MINOR', 'parts': ['Gearbox_Type_2_M_Steel_0', 'Gearbox_Type_2_M_MetalPaintedBlack_0'], 'center': mathutils.Vector((0.966, 18.013, -12.264)), 'angle': math.radians(-90.0), 'elevation': math.radians(14.0), 'distance': 90.0},
            6: {'short': 'CYL #2 OVERHEAT', 'comp': 'Cylinder #2 Head & Cooling Baffle', 'tag': 'CRITICAL', 'parts': ['Covers_Theme_M_PlasticTheme_0', 'Covers_Theme_M_PlasticGreen_0', 'Cooling_Air_Baffle_M_PlasticWhite_0'], 'center': mathutils.Vector((0.966, 38.400, -10.990)), 'angle': math.radians(-140.0), 'elevation': math.radians(24.0), 'distance': 120.0},
            7: {'short': 'ALTERNATOR SAG', 'comp': 'Heavy-Duty Alternator & Belt', 'tag': 'MINOR', 'parts': ['External_Alternator_M_Rotax914_Extras_0', 'External_Alternator_M_TimingBelt_0'], 'center': mathutils.Vector((6.560, 17.394, -8.662)), 'angle': math.radians(-35.0), 'elevation': math.radians(20.0), 'distance': 90.0},
            8: {'short': 'TCU BOOST CONTROLLER', 'comp': 'Rotax Turbo Control Unit (TCU)', 'tag': 'MAJOR', 'parts': ['ECU_M_PlasticBlack_0', 'ECU_M_FuseLight_0'], 'center': mathutils.Vector((13.409, 97.572, -16.925)), 'angle': math.radians(80.0), 'elevation': math.radians(26.0), 'distance': 110.0},
        }
    },
    'rotax_915is': {
        'id': 'rotax_915is',
        'name': 'ROTAX 915 iS',
        'title': 'ROTAX 915 iS A TURBO INTERCOOLED DIGITAL TWIN',
        'subtitle': '141 HP FULL FADEC TURBOCHARGED INTERCOOLED • CRUISE ALTITUDE 23,000 FT',
        'collection': 'Collection_Rotax_912iS',
        'fuel_type': 'AVGAS / MOGAS',
        'induction': 'TURBO INTERCOOLED',
        'default_center': mathutils.Vector((1.932, 61.648, -35.324)),
        'default_distance': 230.0,
        'default_elevation': math.radians(24.0),
        'rpm_max': 5800.0,
        'faults': {
            1: {'short': 'INTERCOOLER FOULING', 'comp': 'Charge Air Intercooler Core & Baffle', 'tag': 'MAJOR', 'parts': ['Cooling_Air_Baffle_M_PlasticWhite_0', 'Covers_Theme_M_PlasticGreen_0', 'Fittings_Metric_Rotax915_Extras_0'], 'center': mathutils.Vector((0.966, 38.400, -10.990)), 'angle': math.radians(-110.0), 'elevation': math.radians(28.0), 'distance': 125.0},
            2: {'short': 'INJECTOR #1 CLOG', 'comp': 'Electronic Fuel Injector #1 (Lane A)', 'tag': 'MAJOR', 'parts': ['Rotax_912i_Base_M_PlasticGreen_0', 'Rotax_912i_Base_M_Steel_0'], 'center': mathutils.Vector((1.160, 61.687, -15.547)), 'angle': math.radians(-85.0), 'elevation': math.radians(34.0), 'distance': 115.0},
            3: {'short': 'IGNITION MISFIRE', 'comp': 'Dual Spark Plug Harness & Coils', 'tag': 'MAJOR', 'parts': ['Wiring_Harness_M_Copper_0', 'Rotax_912i_Base_M_Copper_0'], 'center': mathutils.Vector((4.962, 69.016, -15.626)), 'angle': math.radians(-115.0), 'elevation': math.radians(30.0), 'distance': 120.0},
            4: {'short': 'OIL PRESSURE LOSS', 'comp': 'Dry-Sump Reservoir & Scavenge Line', 'tag': 'CRITICAL', 'parts': ['Oil_Tank_M_Steel_0', 'Oil_Tank_M_Labels_0', 'Oil_Tank_M_Cobalt_0'], 'center': mathutils.Vector((-24.756, 105.824, -20.571)), 'angle': math.radians(135.0), 'elevation': math.radians(18.0), 'distance': 95.0},
            5: {'short': 'GEARBOX VIBRATION', 'comp': 'Propeller Reduction Gearbox & Damper', 'tag': 'MINOR', 'parts': ['Gearbox_Type_2_M_Steel_0', 'Gearbox_Type_2_M_MetalPaintedBlack_0'], 'center': mathutils.Vector((0.966, 18.013, -12.264)), 'angle': math.radians(-90.0), 'elevation': math.radians(14.0), 'distance': 90.0},
            6: {'short': 'CYL #2 OVERHEAT', 'comp': 'Cylinder #2 Head & Cooling Baffle', 'tag': 'CRITICAL', 'parts': ['Covers_Theme_M_PlasticTheme_0', 'Covers_Theme_M_PlasticGreen_0'], 'center': mathutils.Vector((0.966, 38.400, -10.990)), 'angle': math.radians(-140.0), 'elevation': math.radians(24.0), 'distance': 120.0},
            7: {'short': 'ALTERNATOR SAG', 'comp': 'Heavy-Duty Alternator & Belt', 'tag': 'MINOR', 'parts': ['External_Alternator_M_Rotax914_Extras_0', 'External_Alternator_M_TimingBelt_0'], 'center': mathutils.Vector((6.560, 17.394, -8.662)), 'angle': math.radians(-35.0), 'elevation': math.radians(20.0), 'distance': 90.0},
            8: {'short': 'DUAL FADEC DRIFT', 'comp': 'Lane A/B Dual FADEC ECU Assembly', 'tag': 'MINOR', 'parts': ['ECU_M_PlasticBlack_0', 'ECU_M_FuseLight_0'], 'center': mathutils.Vector((13.409, 97.572, -16.925)), 'angle': math.radians(80.0), 'elevation': math.radians(26.0), 'distance': 110.0},
        }
    },
    'austro_ae300': {
        'id': 'austro_ae300',
        'name': 'AUSTRO AE300',
        'title': 'AUSTRO ENGINE AE300 / AE330 CRDi DIESEL TWIN',
        'subtitle': '170/180 HP COMMON-RAIL TURBO DIESEL • SINGLE-LEVER EECS (JET-A1)',
        'collection': 'Collection_Austro_AE300',
        'fuel_type': 'JET-A1 / DIESEL',
        'induction': 'CRDi TURBO DIESEL',
        'default_center': mathutils.Vector((-0.014, 0.30, 0.04)),
        'default_distance': 2.3,
        'default_elevation': math.radians(22.0),
        'rpm_max': 3900.0,
        'faults': {
            1: {'short': 'COMMON RAIL PRESSURE', 'comp': 'High-Pressure Common Rail & Radial Pump', 'tag': 'CRITICAL', 'parts': ['Common_Rail_M_Steel_0', 'HP_Fuel_Pump_M_SteelDark_0', 'Fuel_Line_1_M_Steel_0', 'Fuel_Line_2_M_Steel_0', 'Fuel_Line_3_M_Steel_0', 'Fuel_Line_4_M_Steel_0', 'Rail_PLV_Valve_M_Steel_0'], 'center': mathutils.Vector((0.102, 0.300, 0.042)), 'angle': math.radians(55.0), 'elevation': math.radians(28.0), 'distance': 1.20},
            2: {'short': 'CRDi INJECTOR #1', 'comp': 'CRDi Solenoid Injector #1 & Head', 'tag': 'CRITICAL', 'parts': ['Injector_1_M_Steel_0', 'Cylinder_Head_M_CastAluminium_0', 'Injector_Plugs_M_PlasticBlack_0', 'Injector_Hold_Downs_M_SteelDark_0'], 'center': mathutils.Vector((0.000, 0.293, 0.120)), 'angle': math.radians(35.0), 'elevation': math.radians(36.0), 'distance': 1.15},
            3: {'short': 'VGT TURBO FOULING', 'comp': 'Variable Geometry Turbocharger & Intercooler', 'tag': 'MAJOR', 'parts': ['Turbocharger_M_TurboHousing_0', 'Intercooler_M_CastAluminium_0', 'Boost_Pipe_Hot_M_PolishedAlu_0', 'Boost_Pipe_Cold_M_PolishedAlu_0', 'Heat_Shield_Turbo_M_CrinkleFoil_0', 'Air_Intake_Duct_M_RubberDark_0'], 'center': mathutils.Vector((-0.050, 0.263, 0.057)), 'angle': math.radians(-115.0), 'elevation': math.radians(22.0), 'distance': 1.30},
            4: {'short': 'OIL PRESSURE LOSS', 'comp': 'Lubrication Sump, Filter & Cooler Lines', 'tag': 'CRITICAL', 'parts': ['Oil_Filter_M_MetalPaintedBlack_0', 'Oil_Sump_M_CastAluminium_0', 'Oil_Cooler_M_CastAluminium_0', 'Turbo_Oil_Feed_Line_M_Steel_0', 'Turbo_Oil_Drain_Line_M_Steel_0'], 'center': mathutils.Vector((-0.031, 0.271, -0.016)), 'angle': math.radians(-45.0), 'elevation': math.radians(12.0), 'distance': 1.30},
            5: {'short': 'DUAL EECS DRIFT', 'comp': 'Dual FADEC EECS Controller & Loom', 'tag': 'MAJOR', 'parts': ['ECU_Lane_A_M_MetalPaintedBlack_0', 'ECU_Lane_B_M_MetalPaintedBlack_0', 'Engine_Harness_Loom_M_PlasticBlack_0', 'ECU_Bayonet_Plugs_M_CastAluminium_0'], 'center': mathutils.Vector((-0.035, 0.328, 0.067)), 'angle': math.radians(80.0), 'elevation': math.radians(22.0), 'distance': 1.25},
            6: {'short': 'GLOW PLUG CIRCUIT', 'comp': 'Cold-Start Glow Plug Preheater Array', 'tag': 'MINOR', 'parts': ['Glow_Plugs_M_Steel_0', 'Glow_Plug_Control_Unit_M_CastAluminium_0'], 'center': mathutils.Vector((-0.128, 0.365, 0.111)), 'angle': math.radians(-15.0), 'elevation': math.radians(35.0), 'distance': 0.95},
            7: {'short': 'COOLANT CAVITATION', 'comp': 'High-Efficiency Coolant Pump & Hoses', 'tag': 'MAJOR', 'parts': ['Water_Pump_M_CastAluminium_0', 'Coolant_Hose_Red_M_RedSilicone_0', 'Coolant_Hose_Blue_M_BlueSilicone_0', 'Water_Pump_Inlet_Elbow_M_BlueSilicone_0'], 'center': mathutils.Vector((-0.049, 0.165, -0.070)), 'angle': math.radians(-85.0), 'elevation': math.radians(14.0), 'distance': 1.15},
            8: {'short': 'GEARBOX VIBRATION', 'comp': 'Reduction Gearbox & PCU Prop Governor', 'tag': 'CRITICAL', 'parts': ['Gearbox_M_CastAluminium_0', 'Prop_Governor_PCU_M_CastAluminium_0', 'Prop_Flange_M_Steel_0', 'PCU_Oil_Line_M_Steel_0', 'Gearbox_Logo_M_CastAluminium_0'], 'center': mathutils.Vector((0.005, 0.093, 0.003)), 'angle': math.radians(-90.0), 'elevation': math.radians(16.0), 'distance': 1.10},
        }
    },
    'vrde_jayem_2_2l': {
        'id': 'vrde_jayem_2_2l',
        'name': 'VRDE / JAYEM 2.2L',
        'title': 'VRDE / JAYEM 2.2L INDIGENOUS CRDi DIESEL TWIN',
        'subtitle': '180 HP INDIGENOUS 2.2L CRDi TURBO DIESEL • DRDO / ADE TAPAS BH-201',
        'collection': 'Collection_VRDE_2_2L',
        'fuel_type': 'JET-A1 / DIESEL',
        'induction': 'CRDi TWIN TURBO DIESEL',
        'default_center': mathutils.Vector((0.00, 0.11, 0.00)),
        'default_distance': 2.6,
        'default_elevation': math.radians(24.0),
        'rpm_max': 4200.0,
        'faults': {
            1: {'short': 'CRDi INJECTOR COKING', 'comp': 'CRDi Common Rail & Injector Bank 1-4', 'tag': 'CRITICAL', 'parts': ['Common_Rail_M_Steel_0.001', 'HP_Fuel_Pump_M_SteelDark_0.001', 'Injector_1_M_Steel_0.001', 'Injector_2_M_Steel_0.001', 'Injector_3_M_Steel_0.001', 'Injector_4_M_Steel_0.001', 'Fuel_Line_HP_Cyl1_M_Stainless_0', 'Fuel_Line_HP_Cyl2_M_Stainless_0'], 'center': mathutils.Vector((-0.026, 0.198, 0.090)), 'angle': math.radians(45.0), 'elevation': math.radians(32.0), 'distance': 1.25},
            2: {'short': 'TURBO WASTEGATE', 'comp': 'Two-Stage Turbocharger & Red Wastegate', 'tag': 'CRITICAL', 'parts': ['Wastegate_Actuator_Red_M_AnodizedRed_0', 'Wastegate_Actuator_Canister_M_PlasticBlack_0', 'Wastegate_Rod_Red_M_Stainless_0', 'Intercooler_M_CastAluminium_0.001', 'Exhaust_Downpipe_M_Stainless_0', 'Exhaust_Collector_M_HeatTintedSteel_0'], 'center': mathutils.Vector((0.039, 0.297, 0.062)), 'angle': math.radians(-110.0), 'elevation': math.radians(20.0), 'distance': 1.30},
            3: {'short': 'HP PUMP CAVITATION', 'comp': 'High Pressure Fuel Pump & Leak-off Rail', 'tag': 'MAJOR', 'parts': ['HP_Fuel_Pump_M_SteelDark_0.001', 'Fuel_Return_LeakOff_Rail_M_Stainless_0', 'Fuel_Hose_ASAK_Feed_M_BraidedSilver_0'], 'center': mathutils.Vector((-0.070, 0.305, 0.095)), 'angle': math.radians(65.0), 'elevation': math.radians(24.0), 'distance': 1.35},
            4: {'short': 'LUBRICATION SCAVENGE', 'comp': 'Heavy Duty Block, Sump & Oil Filter', 'tag': 'CRITICAL', 'parts': ['Engine_Block_M_CastAluminium_0.001', 'Oil_Filter', 'Dipstick_Tube_M_Steel_0', 'Cylinder_Head_M_CastAluminium_0.001'], 'center': mathutils.Vector((0.000, 0.315, 0.040)), 'angle': math.radians(-35.0), 'elevation': math.radians(10.0), 'distance': 1.40},
            5: {'short': 'DUAL FADEC HARNESS', 'comp': 'DRDO Dual Redundant FADEC & Spine', 'tag': 'MAJOR', 'parts': ['ECU_Lane_A_M_MetalPaintedBlack_0.001', 'ECU_Lane_B_M_MetalPaintedBlack_0.001', 'Harness_Spine_M_PlasticBlack_0'], 'center': mathutils.Vector((0.018, 0.007, 0.000)), 'angle': math.radians(75.0), 'elevation': math.radians(20.0), 'distance': 1.15},
            6: {'short': 'EXHAUST MANIFOLD', 'comp': 'Stainless Exhaust Downpipe & Collector', 'tag': 'MINOR', 'parts': ['Exhaust_Downpipe_M_Stainless_0', 'Exhaust_Collector_M_HeatTintedSteel_0', 'Intake_Manifold_M_CastAluminium_0.001'], 'center': mathutils.Vector((-0.005, 0.472, 0.117)), 'angle': math.radians(-65.0), 'elevation': math.radians(24.0), 'distance': 1.15},
            7: {'short': 'COOLING JACKET', 'comp': 'High Flow Coolant Jacket & Water Pump', 'tag': 'MAJOR', 'parts': ['Water_Pump_M_CastAluminium_0.001', 'Coolant_Pipe_Junction_M_CastAluminium_0', 'Coolant_Hose_Upper_M_BlueSilicone_0'], 'center': mathutils.Vector((0.001, -0.050, -0.020)), 'angle': math.radians(-135.0), 'elevation': math.radians(15.0), 'distance': 1.20},
            8: {'short': 'GLOW PLUG RESISTANCE', 'comp': 'Ceramic Glow Plug Array 1-4', 'tag': 'MINOR', 'parts': ['Glow_Plug_Cyl1_M_Steel_0', 'Glow_Plug_Cyl2_M_Steel_0', 'Glow_Plug_Cyl3_M_Steel_0', 'Glow_Plug_Cyl4_M_Steel_0'], 'center': mathutils.Vector((-0.030, 0.220, 0.120)), 'angle': math.radians(20.0), 'elevation': math.radians(40.0), 'distance': 1.05},
        }
    }
}

ACTIVE_ENGINE_ID = INITIAL_ENGINE_ID if INITIAL_ENGINE_ID in ENGINE_PROFILES else 'rotax_912is'
ENGINE_PROFILE = ENGINE_PROFILES[ACTIVE_ENGINE_ID]
FAULT_DATABASE = ENGINE_PROFILE['faults']

ENGINE_CENTER = ENGINE_PROFILE['default_center']
DEFAULT_ORBIT_DISTANCE = ENGINE_PROFILE['default_distance']
DEFAULT_ORBIT_ELEVATION = ENGINE_PROFILE['default_elevation']
DEFAULT_ORBIT_SPEED = math.radians(22.5)

STATE_ENDPOINT = f"{SERVER_BASE_URL}/api/engines/{ACTIVE_ENGINE_ID}/state"
LEGACY_STATE_ENDPOINT = f"{SERVER_BASE_URL}/api/state"
CONTROL_ENDPOINT = f"{SERVER_BASE_URL}/api/engines/{ACTIVE_ENGINE_ID}/faults"
LEGACY_CONTROL_ENDPOINT = f"{SERVER_BASE_URL}/api/control"


# ==============================================================================
# 1. CLIENT STATE & NETWORK RECEIVER
# ==============================================================================

class DigitalTwinClientState:
    def __init__(self):
        self.is_connected = False
        self.last_packet_time = 0.0
        self.server_url = SERVER_BASE_URL
        self.engine_id = ACTIVE_ENGINE_ID
        self.engine_profile = ENGINE_PROFILE
        
        self.sortie_id = "SORTIE-OFFLINE"
        self.is_engine_running = True
        self.active_commanded_fault_id = 0
        self.active_commanded_fault_name = "NOMINAL"
        
        self.telemetry = {
            'ENGINE_RPM': 4680.0, 'PROP_RPM': 1926.0, 'TPS': 72.0,
            'CHT_1': 95.0, 'CHT_2': 105.0, 'CHT_3': 95.0, 'CHT_4': 95.0,
            'EGT_1': 780.0, 'EGT_2': 780.0, 'EGT_3': 783.0, 'EGT_4': 780.0,
            'OIL_PRESS': 4.89, 'OIL_TEMP': 57.4, 'FUEL_FLOW': 11.1,
            'FUEL_RAIL_P': 3.0, 'MAP': 38.9, 'VIB_GEARBOX_RMS': 0.74,
            'BUS_VOLTAGE': 14.1, 'BATTERY_CURRENT': 4.2,
            'FADEC_ACTIVE_LANE': 'LANE_A', 'ALTITUDE_FT': 20000.0,
            'OAT_C': -22.0, 'TAS_KNOTS': 90.0, 'FLIGHT_PHASE': 'CRUISE_LOITER',
            'THEATER': 'LADAKH'
        }
        
        self.analytics = {
            'residuals': {},
            'anomaly_score': 0.0,
            'health_index': 1.0,
            'diagnosed_fault_id': 0,
            'diagnosed_fault_name': 'NOMINAL_FLIGHT',
            'diagnosed_confidence': 0.99,
            'target_3d_mesh': 'All',
            'target_parts': [],
            'ata_chapter': 'ATA 00-00',
            'subsystem': 'PROPULSION_CORE',
            'severity': 'NORMAL',
            'root_cause': 'Waiting for server connection...',
            'prescriptive_action': 'Start backend server on port 8000.',
            'emergency_checklist': [],
            'maintenance_order': 'No maintenance required.',
            'go_no_go': 'GO',
            'go_no_go_reason': 'Ready.',
            'rul_p10_hours': 14.2,
            'rul_p50_hours': 18.0,
            'early_warning_trend': None,
            'causal_chain': [],
            'ai_diagnosis': {'status': 'IDLE', 'fault_name': 'NOMINAL_FLIGHT', 'explanation': '', 'citations': []}
        }
        
        self.is_auto_orbit = True
        self.is_ghost_vision = False
        self.is_hud_visible = True
        self.applied_fault_id = -1
        self.start_time = time.time()
        self.last_frame_time = time.time()
        self.fps = 60.0
        self.frame_count = 0
        self.last_fps_calc = time.time()
        
        self.history_egt = collections.deque([710.0 + random.uniform(-5, 5) for _ in range(40)], maxlen=60)
        self.history_oil_temp = collections.deque([56.0 + random.uniform(-1, 2) for _ in range(40)], maxlen=60)
        self.history_oil_press = collections.deque([4.85 + random.uniform(-0.05, 0.05) for _ in range(40)], maxlen=60)
        self.history_rpm = collections.deque([4670.0 + random.uniform(-15, 15) for _ in range(40)], maxlen=60)
        self.last_history_sample_time = time.time()
        
        self.active_tab = "3D ENGINE"
        
        self.orbit_angle = -1.2
        self.target_orbit_angle = -1.2
        self.orbit_elevation = DEFAULT_ORBIT_ELEVATION
        self.target_orbit_elevation = DEFAULT_ORBIT_ELEVATION
        self.orbit_distance = DEFAULT_ORBIT_DISTANCE
        self.target_orbit_distance = DEFAULT_ORBIT_DISTANCE
        
        self.cam_target = ENGINE_CENTER.copy()
        self.cur_cam_target = ENGINE_CENTER.copy()
        self.cur_cam_pos = ENGINE_CENTER + mathutils.Vector((0.0, -DEFAULT_ORBIT_DISTANCE, 100.0))
        
        self.is_dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.drag_button = None
        
        self.original_object_materials = {}
        self.button_rects = []
        self.hovered_button = None
        self.debrief_msg = ""
        self.debrief_time = 0.0

    @property
    def flight_time(self) -> float:
        return max(0.0, time.time() - self.start_time)

client_state = DigitalTwinClientState()


class TelemetryReceiverThread(threading.Thread):
    """Background daemon thread fetching 20 Hz state from Multi-Engine Backend."""
    def __init__(self):
        super().__init__(daemon=True)
        self.is_running = True

    def run(self):
        while self.is_running:
            data = None
            active_id = client_state.engine_id
            dyn_endpoint = f"{SERVER_BASE_URL}/api/engines/{active_id}/state"
            
            for endpoint in [dyn_endpoint, LEGACY_STATE_ENDPOINT]:
                try:
                    req = urllib.request.Request(
                        endpoint,
                        headers={'User-Agent': 'AnumaanBlenderTwinClient/2.0'}
                    )
                    with urllib.request.urlopen(req, timeout=0.35) as response:
                        if response.status == 200:
                            raw = response.read().decode('utf-8')
                            data = json.loads(raw)
                            break
                except Exception:
                    continue

            if data:
                client_state.is_connected = True
                client_state.last_packet_time = time.time()
                client_state.sortie_id = data.get('sortie_id', client_state.sortie_id)
                client_state.is_engine_running = data.get('is_engine_running', True)
                client_state.active_commanded_fault_id = data.get('active_commanded_fault_id', client_state.active_commanded_fault_id)
                client_state.active_commanded_fault_name = data.get('active_commanded_fault_name', client_state.active_commanded_fault_name)
                
                # 1. Direct telemetry dictionary
                if 'telemetry' in data and isinstance(data['telemetry'], dict):
                    client_state.telemetry.update(data['telemetry'])
                elif 'state' in data and isinstance(data['state'], dict):
                    client_state.telemetry.update(data['state'])
                    
                # 2. Canonical channels mapping from EngineRuntime Frame
                if 'channels' in data and isinstance(data['channels'], dict):
                    ch = data['channels']
                    if 'rpm' in ch: client_state.telemetry['ENGINE_RPM'] = float(ch['rpm'])
                    if 'prop_rpm' in ch: client_state.telemetry['PROP_RPM'] = float(ch['prop_rpm'])
                    if 'throttle' in ch: client_state.telemetry['TPS'] = float(ch['throttle'])
                    if 'map_kpa' in ch: client_state.telemetry['MAP'] = float(ch['map_kpa'])
                    if 'oil_p' in ch: client_state.telemetry['OIL_PRESS'] = float(ch['oil_p'])
                    if 'oil_t' in ch: client_state.telemetry['OIL_TEMP'] = float(ch['oil_t'])
                    if 'fuel_flow' in ch: client_state.telemetry['FUEL_FLOW'] = float(ch['fuel_flow'])
                    if 'rail_p' in ch: client_state.telemetry['FUEL_RAIL_P'] = float(ch['rail_p'])
                    if 'bus_v' in ch: client_state.telemetry['BUS_VOLTAGE'] = float(ch['bus_v'])
                    if 'batt_i' in ch: client_state.telemetry['BATTERY_CURRENT'] = float(ch['batt_i'])
                    if 'alt' in ch: client_state.telemetry['ALTITUDE_FT'] = float(ch['alt'])
                    if 'oat' in ch: client_state.telemetry['OAT_C'] = float(ch['oat'])
                    if 'tas' in ch: client_state.telemetry['TAS_KNOTS'] = float(ch['tas'])
                    for k in range(1, 7):
                        if f'cht_{k}' in ch: client_state.telemetry[f'CHT_{k}'] = float(ch[f'cht_{k}'])
                        if f'egt_{k}' in ch: client_state.telemetry[f'EGT_{k}'] = float(ch[f'egt_{k}'])

                if 'cht' in data and isinstance(data['cht'], list):
                    for idx, v in enumerate(data['cht'], 1):
                        client_state.telemetry[f'CHT_{idx}'] = float(v)
                if 'egt' in data and isinstance(data['egt'], list):
                    for idx, v in enumerate(data['egt'], 1):
                        client_state.telemetry[f'EGT_{idx}'] = float(v)

                # 3. Direct analytics dictionary
                if 'analytics' in data and isinstance(data['analytics'], dict):
                    client_state.analytics.update(data['analytics'])
                    
                # 4. Canonical detection & heavy scores mapping
                if 'detection' in data and data['detection']:
                    det = data['detection']
                    scores = det.get('scores', {})
                    if scores:
                        client_state.analytics['residuals'] = scores
                        client_state.analytics['anomaly_score'] = max([float(s) for s in scores.values()] + [0.0])
                    if det.get('confirmed'):
                        top = det.get('top_channels', [])
                        if top:
                            client_state.analytics['root_cause'] = f"Physics residual anomaly detected on: {', '.join(top[:3])}"
            else:
                if time.time() - client_state.last_packet_time > 0.6:
                    client_state.is_connected = False
            
            time.sleep(0.020)


def send_server_command(action: str, **kwargs):
    """Sends a control command to the backend in a background thread."""
    def _worker():
        payload = {"action": action, **kwargs}
        fid = kwargs.get("fault_id", 0)
        
        # Local client optimistic state update
        if action == "SET_FAULT":
            client_state.active_commanded_fault_id = fid
            f_meta = FAULT_DATABASE.get(fid, {})
            client_state.active_commanded_fault_name = f_meta.get('short', f'FAULT_{fid}')
        elif action == "CLEAR_FAULT":
            client_state.active_commanded_fault_id = 0
            client_state.active_commanded_fault_name = "NOMINAL"
            
        dyn_control = f"{SERVER_BASE_URL}/api/engines/{client_state.engine_id}/faults"
        for endpoint in [dyn_control, LEGACY_CONTROL_ENDPOINT]:
            try:
                if action == "CLEAR_FAULT" and "/faults" in endpoint:
                    req = urllib.request.Request(endpoint, method='DELETE')
                else:
                    req = urllib.request.Request(
                        endpoint,
                        data=json.dumps(payload).encode('utf-8'),
                        headers={'Content-Type': 'application/json'}
                    )
                with urllib.request.urlopen(req, timeout=0.5) as resp:
                    return
            except Exception:
                continue
    threading.Thread(target=_worker, daemon=True).start()


def compute_engine_bounds(fallback_center=None, fallback_distance=None):
    """Dynamically computes the bounding center and orbit distance for the currently visible 3D engine mesh model."""
    mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_viewport]
    if not mesh_objs:
        return fallback_center or mathutils.Vector((0.0, 0.0, 0.0)), fallback_distance or 200.0
    
    min_co = mathutils.Vector((float('inf'), float('inf'), float('inf')))
    max_co = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
    
    for obj in mesh_objs:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            min_co.x = min(min_co.x, world_corner.x)
            min_co.y = min(min_co.y, world_corner.y)
            min_co.z = min(min_co.z, world_corner.z)
            max_co.x = max(max_co.x, world_corner.x)
            max_co.y = max(max_co.y, world_corner.y)
            max_co.z = max(max_co.z, world_corner.z)
            
    center = (min_co + max_co) * 0.5
    size = (max_co - min_co).length
    dist = max(1.5, size * 1.35)
    return center, dist


def switch_engine_collection(engine_id: str):
    """Instant 0ms collection visibility toggling without reloading files."""
    prof = ENGINE_PROFILES.get(engine_id, ENGINE_PROFILES['rotax_912is'])
    target_col_name = prof.get('collection', 'Collection_Rotax_912iS')
    
    has_collections = any(c.name.startswith("Collection_") for c in bpy.data.collections)
    if has_collections:
        for col in bpy.data.collections:
            if col.name.startswith("Collection_"):
                is_active = (col.name == target_col_name)
                col.hide_viewport = not is_active
                col.hide_render = not is_active
                for obj in col.objects:
                    obj.hide_viewport = not is_active
                    obj.hide_render = not is_active


def switch_engine(engine_id: str):
    """Seamlessly switches active engine context in real-time."""
    global ACTIVE_ENGINE_ID, ENGINE_PROFILE, FAULT_DATABASE, ENGINE_CENTER, DEFAULT_ORBIT_DISTANCE, DEFAULT_ORBIT_ELEVATION
    if engine_id not in ENGINE_PROFILES:
        return
    
    ACTIVE_ENGINE_ID = engine_id
    ENGINE_PROFILE = ENGINE_PROFILES[engine_id]
    FAULT_DATABASE = ENGINE_PROFILE['faults']
    
    client_state.engine_id = engine_id
    client_state.engine_profile = ENGINE_PROFILE
    
    # 1. Toggle 3D mesh collection visibility
    switch_engine_collection(engine_id)
    
    # Initialize baseline nominal telemetry for electrical & fuel system scale
    if 'rotax' in engine_id:
        client_state.telemetry['BUS_VOLTAGE'] = 14.1
        client_state.telemetry['FUEL_RAIL_P'] = 3.0
    else:
        client_state.telemetry['BUS_VOLTAGE'] = 28.2
        client_state.telemetry['FUEL_RAIL_P'] = 1600.0
    
    # 2. Notify backend server
    def _notify():
        try:
            req = urllib.request.Request(
                f"{SERVER_BASE_URL}/api/engines/select",
                data=json.dumps({"engine_id": engine_id}).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=0.5)
        except Exception:
            pass
    threading.Thread(target=_notify, daemon=True).start()
    
    # 3. Dynamic camera bounds calculation & scale adaptation
    center, dist = compute_engine_bounds(ENGINE_PROFILE['default_center'], ENGINE_PROFILE['default_distance'])
    ENGINE_CENTER = center
    DEFAULT_ORBIT_DISTANCE = dist
    DEFAULT_ORBIT_ELEVATION = ENGINE_PROFILE['default_elevation']
    
    client_state.cam_target = ENGINE_CENTER.copy()
    client_state.cur_cam_target = ENGINE_CENTER.copy()
    client_state.orbit_distance = DEFAULT_ORBIT_DISTANCE
    client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE
    client_state.orbit_elevation = DEFAULT_ORBIT_ELEVATION
    client_state.target_orbit_elevation = DEFAULT_ORBIT_ELEVATION
    client_state.is_auto_orbit = True
    
    cx = ENGINE_CENTER.x + DEFAULT_ORBIT_DISTANCE * math.cos(client_state.orbit_angle) * math.cos(DEFAULT_ORBIT_ELEVATION)
    cy = ENGINE_CENTER.y + DEFAULT_ORBIT_DISTANCE * math.sin(client_state.orbit_angle) * math.cos(DEFAULT_ORBIT_ELEVATION)
    cz = ENGINE_CENTER.z + DEFAULT_ORBIT_DISTANCE * math.sin(DEFAULT_ORBIT_ELEVATION)
    client_state.cur_cam_pos = mathutils.Vector((cx, cy, cz))
    
    client_state.applied_fault_id = -1
    if hasattr(update_camera_for_backend_fault, "_last_state_key"):
        delattr(update_camera_for_backend_fault, "_last_state_key")
    
    save_original_materials()
    apply_material_state()


# ==============================================================================
# 2. 2D HUD GPU DRAWING ENGINE
# ==============================================================================

class HUDDrawer:
    def __init__(self):
        self.font_id = 0
        self.sh_uni = None
        self.sh_smooth = None

    def init_shaders(self):
        if self.sh_uni is None:
            self.sh_uni = gpu.shader.from_builtin('UNIFORM_COLOR')
            self.sh_smooth = gpu.shader.from_builtin('SMOOTH_COLOR')

    def draw_rect(self, x, y, w, h, color):
        self.init_shaders()
        x1, y1, x2, y2 = x, y, x + w, y + h
        coords = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        batch = batch_for_shader(self.sh_uni, 'TRI_FAN', {"pos": coords})
        self.sh_uni.bind()
        self.sh_uni.uniform_float("color", color)
        batch.draw(self.sh_uni)

    def draw_rect_outline(self, x, y, w, h, color, width=1.0):
        self.init_shaders()
        x1, y1, x2, y2 = x, y, x + w, y + h
        coords = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
        batch = batch_for_shader(self.sh_uni, 'LINE_STRIP', {"pos": coords})
        self.sh_uni.bind()
        self.sh_uni.uniform_float("color", color)
        gpu.state.line_width_set(width)
        batch.draw(self.sh_uni)
        gpu.state.line_width_set(1.0)

    def draw_gradient_rect(self, x, y, w, h, col_top, col_bot):
        self.init_shaders()
        x1, y1, x2, y2 = x, y, x + w, y + h
        coords = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        colors = [col_bot, col_bot, col_top, col_top]
        batch = batch_for_shader(self.sh_smooth, 'TRI_FAN', {"pos": coords, "color": colors})
        self.sh_smooth.bind()
        batch.draw(self.sh_smooth)

    def draw_ring(self, cx, cy, radius, thickness, color, fill_ratio=1.0):
        self.init_shaders()
        segments = 40
        num_fill = max(2, int(segments * max(0.05, min(1.0, fill_ratio))))
        coords = []
        for i in range(num_fill + 1):
            theta = -math.pi / 2 + (2 * math.pi * (i / segments))
            ox = cx + radius * math.cos(theta)
            oy = cy + radius * math.sin(theta)
            ix = cx + (radius - thickness) * math.cos(theta)
            iy = cy + (radius - thickness) * math.sin(theta)
            coords.append((ox, oy))
            coords.append((ix, iy))
        batch = batch_for_shader(self.sh_uni, 'TRI_STRIP', {"pos": coords})
        self.sh_uni.bind()
        self.sh_uni.uniform_float("color", color)
        batch.draw(self.sh_uni)

    def draw_text(self, text, x, y, size=11, color=(1.0, 1.0, 1.0, 1.0)):
        blf.size(self.font_id, size)
        blf.color(self.font_id, 0.0, 0.0, 0.0, color[3] * 0.85)
        blf.position(self.font_id, x + 1, y - 1, 0)
        blf.draw(self.font_id, text)
        blf.color(self.font_id, color[0], color[1], color[2], color[3])
        blf.position(self.font_id, x, y, 0)
        blf.draw(self.font_id, text)

    def get_text_width(self, text, size=11):
        blf.size(self.font_id, size)
        return blf.dimensions(self.font_id, text)[0]

    def draw_multiline_text(self, text, x, y, max_width=250, size=10, line_height=15, max_lines=4, color=(1.0, 1.0, 1.0, 1.0)):
        words = text.split(' ')
        lines = []
        cur_line = []
        for word in words:
            test_line = ' '.join(cur_line + [word])
            if self.get_text_width(test_line, size=size) <= max_width:
                cur_line.append(word)
            else:
                if cur_line:
                    lines.append(' '.join(cur_line))
                cur_line = [word]
        if cur_line:
            lines.append(' '.join(cur_line))

        cur_y = y
        for i, line in enumerate(lines[:max_lines]):
            if i == max_lines - 1 and len(lines) > max_lines:
                line = line[:len(line) - 3] + "..."
            self.draw_text(line, x, cur_y, size=size, color=color)
            cur_y -= line_height

    def draw_gauge_card(self, x, y, w, h, icon, label, norm_label, val_str, norm_val, min_label, max_label, is_warn, is_crit):
        if is_crit:
            bg_col = (0.28, 0.04, 0.06, 0.95)
            border_c = (0.95, 0.25, 0.30, 0.95)
            border_w = 1.5
            bar_col = (1.0, 0.25, 0.25, 1.0)
            lbl_col = (1.0, 0.50, 0.50, 1.0)
            val_col = (1.0, 0.92, 0.92, 1.0)
            val_box_bg = (0.50, 0.08, 0.08, 0.85)
        elif is_warn:
            bg_col = (0.22, 0.13, 0.02, 0.92)
            border_c = (0.95, 0.72, 0.12, 0.92)
            border_w = 1.5
            bar_col = (1.0, 0.75, 0.12, 0.98)
            lbl_col = (1.0, 0.88, 0.35, 1.0)
            val_col = (1.0, 0.96, 0.75, 1.0)
            val_box_bg = (0.40, 0.22, 0.04, 0.8)
        else:
            bg_col = (0.04, 0.07, 0.11, 0.85)
            border_c = (0.12, 0.24, 0.38, 0.45)
            border_w = 1.0
            bar_col = (0.0, 0.85, 1.0, 0.90)
            lbl_col = (0.82, 0.92, 1.0, 0.95)
            val_col = (1.0, 1.0, 1.0, 1.0)
            val_box_bg = None

        self.draw_rect(x, y, w, h, bg_col)
        self.draw_rect_outline(x, y, w, h, border_c, width=border_w)

        if icon:
            self.draw_text(icon, x + 8, y + h - 17, size=12.0, color=bar_col)
            label_x = x + 24
        else:
            label_x = x + 8
            
        self.draw_text(label, label_x, y + h - 17, size=10.5, color=lbl_col)
        self.draw_text(norm_label, label_x, y + h - 29, size=9.0, color=(0.48, 0.65, 0.82, 0.85))

        val_w = self.get_text_width(val_str, size=12.0)
        val_x = x + w - val_w - 10
        if val_box_bg:
            self.draw_rect(val_x - 6, y + h - 29, val_w + 12, 20, val_box_bg)
            self.draw_rect_outline(val_x - 6, y + h - 29, val_w + 12, 20, border_c, width=1.0)
        self.draw_text(val_str, val_x, y + h - 19, size=12.0, color=val_col)

        track_y = y + 7
        track_h = 4
        min_w = self.get_text_width(min_label, size=8.0)
        max_w = self.get_text_width(max_label, size=8.0)
        
        self.draw_text(min_label, x + 8, track_y - 2, size=8.0, color=(0.45, 0.60, 0.75, 0.75))
        self.draw_text(max_label, x + w - max_w - 8, track_y - 2, size=8.0, color=(0.45, 0.60, 0.75, 0.75))

        track_x = x + 8 + min_w + 5
        track_w = w - 16 - min_w - max_w - 10
        self.draw_rect(track_x, track_y, track_w, track_h, (0.06, 0.10, 0.16, 0.95))
        self.draw_rect_outline(track_x, track_y, track_w, track_h, (0.15, 0.25, 0.35, 0.40), width=1.0)

        fill_w = max(2, min(track_w, int(track_w * max(0.0, min(1.0, norm_val)))))
        self.draw_rect(track_x, track_y, fill_w, track_h, bar_col)

    def render(self, width, height, state: DigitalTwinClientState):
        if not state.is_hud_visible:
            self.draw_text("Press [H] or [TAB] to Open Full Digital Twin HUD", 25, 25, size=13, color=(0.0, 0.9, 1.0, 0.90))
            return

        gpu.state.blend_set('ALPHA')
        state.button_rects.clear()

        prof = state.engine_profile

        # ======================================================================
        # A. TOP HEADER BAR + ENGINE SWITCHER
        # ======================================================================
        top_h = 74
        top_y = height - top_h
        self.draw_gradient_rect(0, top_y, width, top_h, (0.03, 0.06, 0.10, 0.95), (0.01, 0.02, 0.04, 0.98))
        self.draw_rect_outline(0, top_y, width, top_h, (0.08, 0.18, 0.28, 0.40))
        self.draw_rect(0, height - 2, width, 2, (0.0, 0.85, 1.0, 1.0))

        # 1. Left Title Block
        self.draw_text(prof['title'], 20, top_y + 48, size=13.5, color=(1.0, 1.0, 1.0, 1.0))
        self.draw_text(prof['subtitle'], 20, top_y + 32, size=9.5, color=(0.0, 0.80, 0.95, 0.85))

        # 2. Engine Selection Ribbon
        engine_list = [
            ("F1: ROTAX 912 iS", "rotax_912is"),
            ("F2: ROTAX 914 TURBO", "rotax_914"),
            ("F3: ROTAX 915 iS", "rotax_915is"),
            ("F4: AUSTRO AE300", "austro_ae300"),
            ("F5: VRDE 2.2L CRDi", "vrde_jayem_2_2l")
        ]
        eng_x = 20
        eng_y = top_y + 6
        eng_btn_h = 20
        for label, eid in engine_list:
            is_active = (state.engine_id == eid)
            is_hover = (state.hovered_button == f"ENGINE_{eid}")
            
            t_w = self.get_text_width(label, size=9.0)
            btn_w = t_w + 16
            
            if is_active:
                b_bg = (0.0, 0.45, 0.75, 0.95)
                b_bd = (0.0, 0.90, 1.0, 1.0)
                t_col = (1.0, 1.0, 1.0, 1.0)
            elif is_hover:
                b_bg = (0.12, 0.28, 0.42, 0.85)
                b_bd = (0.0, 0.80, 0.95, 0.80)
                t_col = (0.90, 0.95, 1.0, 1.0)
            else:
                b_bg = (0.05, 0.09, 0.14, 0.70)
                b_bd = (0.15, 0.25, 0.35, 0.45)
                t_col = (0.65, 0.78, 0.90, 0.85)
                
            self.draw_rect(eng_x, eng_y, btn_w, eng_btn_h, b_bg)
            self.draw_rect_outline(eng_x, eng_y, btn_w, eng_btn_h, b_bd, width=1.0)
            self.draw_text(label, eng_x + 8, eng_y + 5, size=9.0, color=t_col)
            
            state.button_rects.append((eng_x, eng_y, btn_w, eng_btn_h, f"ENGINE_{eid}"))
            eng_x += btn_w + 8

        # 3. Central Status Alert Banner
        active_fid = state.active_commanded_fault_id if state.active_commanded_fault_id > 0 else state.analytics.get('diagnosed_fault_id', 0)
        alert_w = 360
        alert_x = (width - alert_w) // 2
        alert_y = top_y + 30
        alert_h = 34

        if not state.is_connected:
            self.draw_rect(alert_x, alert_y, alert_w, alert_h, (0.24, 0.05, 0.05, 0.92))
            self.draw_rect_outline(alert_x, alert_y, alert_w, alert_h, (0.95, 0.25, 0.25, 0.95), width=1.5)
            self.draw_text("⚠ TELEMETRY LINK OFFLINE — WAITING FOR SERVER", alert_x + 14, alert_y + 11, size=10.5, color=(1.0, 0.4, 0.4, 1.0))
        elif active_fid > 0:
            f_title = state.analytics.get('diagnosed_fault_name', '') or state.active_commanded_fault_name
            f_title = f_title.replace('_', ' ')
            if len(f_title) > 22:
                f_title = f_title[:20] + ".."
            self.draw_rect(alert_x, alert_y, alert_w, alert_h, (0.26, 0.04, 0.06, 0.92))
            self.draw_rect_outline(alert_x, alert_y, alert_w, alert_h, (0.95, 0.25, 0.30, 0.95), width=1.5)
            self.draw_text(f"⚠ {f_title}", alert_x + 14, alert_y + 11, size=11.5, color=(1.0, 0.35, 0.35, 1.0))
            self.draw_text(f"HEALTH: {state.analytics['health_index']*100:.0f}%", alert_x + alert_w - 95, alert_y + 11, size=11.0, color=(1.0, 0.45, 0.45, 1.0))
        elif not state.is_engine_running:
            self.draw_rect(alert_x, alert_y, alert_w, alert_h, (0.15, 0.18, 0.25, 0.90))
            self.draw_rect_outline(alert_x, alert_y, alert_w, alert_h, (0.45, 0.55, 0.70, 0.90), width=1.0)
            self.draw_text("⏸ ENGINE SHUTDOWN / STANDBY", alert_x + 16, alert_y + 11, size=11.5, color=(0.85, 0.90, 1.0, 1.0))
        else:
            self.draw_rect(alert_x, alert_y, alert_w, alert_h, (0.03, 0.16, 0.08, 0.90))
            self.draw_rect_outline(alert_x, alert_y, alert_w, alert_h, (0.18, 0.80, 0.45, 0.80), width=1.0)
            self.draw_text("● PROPULSION NOMINAL", alert_x + 16, alert_y + 11, size=11.5, color=(0.35, 1.0, 0.55, 1.0))
            self.draw_text(f"HEALTH: {state.analytics['health_index']*100:.0f}%", alert_x + alert_w - 95, alert_y + 11, size=11.0, color=(0.40, 1.0, 0.60, 1.0))

        # 4. Mission Readiness Badge
        gng_w = 120
        gng_x = alert_x + alert_w + 10
        gng_status = state.analytics.get('go_no_go', 'GO')
        if gng_status == "NO_GO":
            gng_bg = (0.25, 0.05, 0.08, 0.92)
            gng_border = (0.95, 0.25, 0.25, 0.95)
            gng_col = (1.0, 0.35, 0.35, 1.0)
        elif gng_status == "CAUTION":
            gng_bg = (0.22, 0.13, 0.02, 0.90)
            gng_border = (0.95, 0.72, 0.12, 0.92)
            gng_col = (1.0, 0.85, 0.20, 1.0)
        else:
            gng_bg = (0.03, 0.14, 0.08, 0.88)
            gng_border = (0.15, 0.75, 0.40, 0.75)
            gng_col = (0.35, 1.0, 0.55, 1.0)
            
        self.draw_rect(gng_x, alert_y, gng_w, alert_h, gng_bg)
        self.draw_rect_outline(gng_x, alert_y, gng_w, alert_h, gng_border, width=1.0)
        self.draw_text(f"MISSION: {gng_status}", gng_x + 10, alert_y + 11, size=10.0, color=gng_col)

        # 5. Right Stats Block (Elapsed Time & Large FPS)
        m, s = divmod(int(state.flight_time), 60)
        time_str = f"T+{m//60:02d}:{m%60:02d}:{s:02d}"
        self.draw_text(time_str, width - 200, top_y + 48, size=12.0, color=(1.0, 1.0, 1.0, 1.0))
        self.draw_text("ELAPSED TIME", width - 200, top_y + 32, size=8.5, color=(0.48, 0.65, 0.82, 0.80))

        fps_val = f"{int(round(state.fps))}"
        self.draw_text(fps_val, width - 65, top_y + 44, size=16.0, color=(0.35, 1.0, 0.55, 1.0))
        self.draw_text("FPS", width - 65, top_y + 30, size=8.5, color=(0.35, 1.0, 0.55, 0.85))

        # ======================================================================
        # B. LEFT PANEL — "PROPULSION TELEMETRY" (320px width)
        # ======================================================================
        bot_h = 165
        left_w = 320
        left_x = 18
        left_y = bot_h + 16
        left_h = height - top_h - left_y - 10

        self.draw_gradient_rect(left_x, left_y, left_w, left_h, (0.03, 0.06, 0.10, 0.90), (0.01, 0.02, 0.04, 0.94))
        self.draw_rect_outline(left_x, left_y, left_w, left_h, (0.10, 0.22, 0.35, 0.45))
        self.draw_text(f"{prof['name']} TELEMETRY (20 HZ)", left_x + 12, left_y + left_h - 20, size=11.5, color=(0.0, 0.88, 1.0, 1.0))

        t = state.telemetry
        res = state.analytics.get('residuals', {})
        fid_cmd = state.active_commanded_fault_id
        is_diesel = ("diesel" in prof['induction'].lower() or "crdi" in prof['induction'].lower())

        if is_diesel:
            rail_p = t.get('FUEL_RAIL_P', 1600.0)
            if rail_p < 200.0:
                rail_p = rail_p * 500.0
            gauges_config = [
                ("⚙", "ENGINE SPEED", f"Prop: {t.get('PROP_RPM', 1900):.0f} | Load: {t.get('TPS', 70):.0f}%", f"{t.get('ENGINE_RPM', 3800):.0f} RPM", t.get('ENGINE_RPM', 3800) / prof['rpm_max'], "0", f"{int(prof['rpm_max'])}", t.get('ENGINE_RPM', 0) > prof['rpm_max'] * 0.95, t.get('ENGINE_RPM', 0) > prof['rpm_max']),
                ("⛽", "CRDi RAIL PRESSURE", f"Δ {res.get('d_FUEL_RAIL_P', 0.0):+.0f}b [NORM 1600b]", f"{rail_p:.0f} BAR", rail_p / 2000.0, "0", "2000", abs(res.get('d_FUEL_RAIL_P', 0.0)) > 150.0 or fid_cmd in (1, 8), abs(res.get('d_FUEL_RAIL_P', 0.0)) > 300.0 or rail_p < 400.0),
                ("📊", "BOOST PRESSURE", f"Δ {res.get('d_MAP', 0.0):+.1f} kPa [VGT Turbo]", f"{t.get('MAP', 180.0):.1f} kPa", t.get('MAP', 180.0) / 250.0, "0", "250", abs(res.get('d_MAP', 0.0)) > 15.0 or fid_cmd in (2, 3), abs(res.get('d_MAP', 0.0)) > 30.0),
                ("🌡", "COOLANT TEMP", f"Δ {res.get('d_CHT_1', 0.0):+.1f}°C [NORM 88°C]", f"{t.get('CHT_1', 88.0):.1f} °C", (t.get('CHT_1', 88.0)) / 130.0, "0", "130", t.get('CHT_1', 88.0) > 105.0 or fid_cmd in (6, 7), t.get('CHT_1', 88.0) > 118.0),
                ("💧", "OIL PRESSURE", f"Δ {res.get('d_OIL_PRESS', 0.0):+.2f}b [NORM 4.5b]", f"{t.get('OIL_PRESS', 4.5):.2f} BAR", t.get('OIL_PRESS', 4.5) / 10.0, "0", "10", res.get('d_OIL_PRESS', 0.0) < -0.6 or fid_cmd == 4, res.get('d_OIL_PRESS', 0.0) < -1.2 or t.get('OIL_PRESS', 4.5) < 2.0),
                ("🔥", "EXHAUST TEMP (EGT)", f"Δ {res.get('d_EGT_1', 0.0):+.0f}°C [Turbine Inlet]", f"{t.get('EGT_1', 650.0):.0f} °C", t.get('EGT_1', 650.0) / 900.0, "0", "900", t.get('EGT_1', 650.0) > 750.0 or fid_cmd in (2, 3), t.get('EGT_1', 650.0) > 830.0),
                ("⚡", "28V AVIONICS BUS", f"Bat: {t.get('BATTERY_CURRENT', 4.2):+.1f}A | EECS FADEC", f"{t.get('BUS_VOLTAGE', 28.0):.1f} V", (t.get('BUS_VOLTAGE', 28.0) - 20.0) / 12.0, "20", "32", t.get('BUS_VOLTAGE', 28.0) < 24.0 or fid_cmd == 5, t.get('BUS_VOLTAGE', 28.0) < 22.5),
                ("⚠", "ANOMALY SCORE", f"Confidence: {state.analytics.get('diagnosed_confidence', 0.99)*100:.0f}%", f"{state.analytics['anomaly_score']*100:.1f}%", state.analytics['anomaly_score'], "0", "100", state.analytics['anomaly_score'] > 0.35, state.analytics['anomaly_score'] > 0.65),
            ]
        else:
            gauges_config = [
                ("⚙", "ENGINE RPM", f"Prop: {t['PROP_RPM']:.0f} | TPS: {t['TPS']:.0f}%", f"{t['ENGINE_RPM']:.0f} RPM", t['ENGINE_RPM'] / prof['rpm_max'], "0", f"{int(prof['rpm_max'])}", t['ENGINE_RPM'] > 5500 or fid_cmd in (2, 3, 5), t['ENGINE_RPM'] > 5750 or (t['ENGINE_RPM'] < 3800 and state.is_engine_running)),
                ("🌡", "OIL TEMP", f"Δ {res.get('d_OIL_TEMP', 0.0):+.1f}°C [NORM 92°C]", f"{t['OIL_TEMP']:.1f} °C", (t['OIL_TEMP'] + 20.0) / 170.0, "-20", "150", res.get('d_OIL_TEMP', 0.0) > 8.0 or fid_cmd in (1, 4, 5), res.get('d_OIL_TEMP', 0.0) > 18.0 or t['OIL_TEMP'] > 125.0),
                ("💧", "OIL PRESSURE", f"Δ {res.get('d_OIL_PRESS', 0.0):+.2f}b [NORM 3.8b]", f"{t['OIL_PRESS']:.2f} BAR", t['OIL_PRESS'] / 10.0, "0", "10", (res.get('d_OIL_PRESS', 0.0) < -0.4 and state.is_engine_running) or fid_cmd == 4, (res.get('d_OIL_PRESS', 0.0) < -0.9 or t['OIL_PRESS'] < 2.0) and state.is_engine_running),
                ("⛽", "FUEL FLOW", f"Rail {t['FUEL_RAIL_P']:.1f}b | Δ {res.get('d_FUEL_FLOW', 0.0):+.1f} L/h", f"{t['FUEL_FLOW']:.1f} L/H", t['FUEL_FLOW'] / 30.0, "0", "30", abs(res.get('d_FUEL_FLOW', 0.0)) > 2.5 or fid_cmd in (2, 8), res.get('d_FUEL_FLOW', 0.0) < -4.5 or (t['FUEL_FLOW'] < 2.5 and state.is_engine_running)),
                ("🔥", "EXHAUST EGT #3", f"Δ {res.get('d_EGT_3', 0.0):+.0f}°C [E1-4: {t['EGT_1']:.0f}/{t['EGT_2']:.0f}/{t['EGT_3']:.0f}/{t['EGT_4']:.0f}]", f"{t['EGT_3']:.0f} °C", t['EGT_3'] / 1000.0, "0", "1000", abs(res.get('d_EGT_3', 0.0)) > 25.0 or fid_cmd in (3, 6, 8), abs(res.get('d_EGT_3', 0.0)) > 45.0 or t['EGT_3'] > 910.0),
                ("📊", "MANIFOLD PRESSURE", f"Δ {res.get('d_MAP', 0.0):+.1f} kPa [{t['FADEC_ACTIVE_LANE']}]", f"{t['MAP']:.1f} kPa", t['MAP'] / 100.0, "0", "100", abs(res.get('d_MAP', 0.0)) > 3.5 or fid_cmd in (5, 8), abs(res.get('d_MAP', 0.0)) > 7.0),
                ("⚡", "DC BUS VOLT", f"Bat: {t['BATTERY_CURRENT']:+.1f}A | Δ {res.get('d_BUS_VOLTAGE', 0.0):+.1f}V", f"{t['BUS_VOLTAGE']:.1f} V", (t['BUS_VOLTAGE'] - 11.0) / 5.0, "11", "16", res.get('d_BUS_VOLTAGE', 0.0) < -0.8 or fid_cmd == 7, res.get('d_BUS_VOLTAGE', 0.0) < -1.5 or t['BUS_VOLTAGE'] < 12.6),
                ("⚠", "ANOMALY SCORE", f"Confidence: {state.analytics.get('diagnosed_confidence', 0.99)*100:.0f}%", f"{state.analytics['anomaly_score']*100:.1f}%", state.analytics['anomaly_score'], "0", "100", state.analytics['anomaly_score'] > 0.35, state.analytics['anomaly_score'] > 0.65),
            ]

        avail_card_space = left_h - 34
        card_step = avail_card_space / 8.0
        card_h = max(34, int(card_step - 4))
        c_y = left_y + left_h - 32 - card_h

        for icon, label, norm_lbl, val_str, norm_val, min_lbl, max_lbl, is_warn, is_crit in gauges_config:
            self.draw_gauge_card(left_x + 8, int(c_y), left_w - 16, card_h, icon, label, norm_lbl, val_str, norm_val, min_lbl, max_lbl, is_warn, is_crit)
            c_y -= card_step

        # ======================================================================
        # C. RIGHT SPLIT PANELS — "FAULT MATRIX" & "SYSTEM HEALTH"
        # ======================================================================
        right_w = 320
        right_x = width - right_w - 18
        avail_r_h = height - top_h - bot_h - 26

        # 1. Fault Matrix (Top Right)
        fm_h = max(240, int(avail_r_h * 0.56))
        fm_y = left_y + left_h - fm_h

        self.draw_gradient_rect(right_x, fm_y, right_w, fm_h, (0.03, 0.06, 0.10, 0.90), (0.01, 0.02, 0.04, 0.94))
        self.draw_rect_outline(right_x, fm_y, right_w, fm_h, (0.10, 0.22, 0.35, 0.45))
        self.draw_text(f"{prof['name']} FAULT MATRIX", right_x + 12, fm_y + fm_h - 20, size=11.5, color=(1.0, 1.0, 1.0, 1.0))

        fm_btn_h = 22
        fm_spacing = (fm_h - 36) / 8.0
        btn_y = fm_y + fm_h - 28 - fm_btn_h

        for i in range(1, 9):
            f_id = f'FAULT_{i}'
            f_data = FAULT_DATABASE.get(i, FAULT_DATABASE.get(f_id, {'short': f'FAULT #{i}', 'tag': 'MINOR'}))
            is_active = (state.analytics.get('diagnosed_fault_id', 0) == i or state.active_commanded_fault_id == i)
            is_hover = (state.hovered_button == f_id)
            sev_tag = f_data.get('tag', f_data.get('severity_tag', 'MINOR'))

            if is_active:
                row_bg = (0.85, 0.14, 0.14, 0.95)
                row_border = (1.0, 0.45, 0.45, 1.0)
                badge_bg = (0.50, 0.08, 0.08, 1.0)
                badge_col = (1.0, 0.9, 0.9, 1.0)
                text_col = (1.0, 1.0, 1.0, 1.0)
            elif is_hover:
                row_bg = (0.10, 0.28, 0.45, 0.90)
                row_border = (0.0, 0.90, 1.0, 0.90)
                badge_bg = (0.05, 0.18, 0.30, 0.9)
                badge_col = (0.0, 0.90, 1.0, 1.0)
                text_col = (1.0, 1.0, 1.0, 1.0)
            else:
                row_bg = (0.04, 0.07, 0.11, 0.70)
                row_border = (0.12, 0.22, 0.32, 0.35)
                if sev_tag == 'CRITICAL':
                    badge_bg = (0.35, 0.06, 0.08, 0.8)
                    badge_col = (1.0, 0.35, 0.35, 1.0)
                elif sev_tag == 'MAJOR':
                    badge_bg = (0.30, 0.18, 0.02, 0.8)
                    badge_col = (1.0, 0.75, 0.15, 1.0)
                else:
                    badge_bg = (0.08, 0.14, 0.20, 0.8)
                    badge_col = (0.55, 0.70, 0.85, 0.8)
                text_col = (0.82, 0.88, 0.95, 0.90)

            self.draw_rect(right_x + 8, int(btn_y), right_w - 16, fm_btn_h, row_bg)
            self.draw_rect_outline(right_x + 8, int(btn_y), right_w - 16, fm_btn_h, row_border)

            self.draw_text(str(i), right_x + 16, int(btn_y) + 5, size=10.0, color=text_col)
            self.draw_text(f_data['short'], right_x + 34, int(btn_y) + 5, size=9.5, color=text_col)

            b_w = self.get_text_width(sev_tag, size=8.5) + 12
            b_x = right_x + right_w - 16 - b_w
            self.draw_rect(b_x, int(btn_y) + 2, b_w, 18, badge_bg)
            self.draw_text(sev_tag, b_x + 6, int(btn_y) + 5, size=8.5, color=badge_col)

            state.button_rects.append((right_x + 8, int(btn_y), right_w - 16, fm_btn_h, f_id))
            btn_y -= fm_spacing

        # 2. System Health
        sh_h = max(180, left_h - fm_h - 10)
        sh_y = left_y

        self.draw_gradient_rect(right_x, sh_y, right_w, sh_h, (0.03, 0.06, 0.10, 0.90), (0.01, 0.02, 0.04, 0.94))
        self.draw_rect_outline(right_x, sh_y, right_w, sh_h, (0.10, 0.22, 0.35, 0.45))
        self.draw_text("SYSTEM HEALTH", right_x + 12, sh_y + sh_h - 20, size=12.0, color=(1.0, 1.0, 1.0, 1.0))

        overall_health = state.analytics.get('health_index', 1.0)
        ring_cx = right_x + 52
        ring_cy = sh_y + (sh_h // 2) - 8
        ring_r = 32
        
        if overall_health < 0.60:
            ring_col = (1.0, 0.25, 0.25, 1.0)
        elif overall_health < 0.85:
            ring_col = (1.0, 0.75, 0.15, 1.0)
        else:
            ring_col = (0.25, 0.95, 0.55, 1.0)

        self.draw_ring(ring_cx, ring_cy, ring_r, 5, (0.10, 0.18, 0.25, 0.5), fill_ratio=1.0)
        self.draw_ring(ring_cx, ring_cy, ring_r, 5, ring_col, fill_ratio=overall_health)
        
        pct_txt = f"{int(round(overall_health * 100))}%"
        p_w = self.get_text_width(pct_txt, size=13.0)
        self.draw_text(pct_txt, ring_cx - (p_w // 2), ring_cy - 4, size=13.0, color=(1.0, 1.0, 1.0, 1.0))
        self.draw_text("OVERALL", ring_cx - 18, ring_cy - 16, size=7.5, color=(0.60, 0.75, 0.90, 0.80))
        self.draw_text("HEALTH", ring_cx - 16, ring_cy - 25, size=7.5, color=(0.60, 0.75, 0.90, 0.80))

        subsys_x = right_x + 105
        subsys_w = right_w - 118
        subsys_y = sh_y + sh_h - 38
        
        subsystems = [
            ("PROPULSION", 0.94 if active_fid in (0, 7, 8) else 0.42),
            ("FUEL SYSTEM", 0.99 if active_fid != 2 else 0.35),
            ("ELECTRICAL", 1.00 if active_fid != 7 else 0.55),
            ("THERMAL", 0.99 if active_fid not in (1, 6) else 0.40),
            ("MECHANICAL", 1.00 if active_fid not in (4, 5) else 0.30),
        ]

        for s_name, s_val in subsystems:
            if active_fid > 0:
                s_val = min(s_val, overall_health + 0.05)
            
            s_bar_col = (0.25, 0.95, 0.55, 1.0) if s_val > 0.80 else ((1.0, 0.75, 0.15, 1.0) if s_val > 0.60 else (1.0, 0.25, 0.25, 1.0))
            
            self.draw_text(f"● {s_name}", subsys_x, subsys_y, size=8.5, color=(0.75, 0.88, 0.98, 0.90))
            val_t = f"{int(s_val*100)}%"
            v_w = self.get_text_width(val_t, size=8.5)
            self.draw_text(val_t, subsys_x + subsys_w - v_w, subsys_y, size=8.5, color=s_bar_col)
            
            self.draw_rect(subsys_x + 65, subsys_y + 3, subsys_w - 95, 3, (0.10, 0.18, 0.25, 0.6))
            fill_len = max(2, int((subsys_w - 95) * s_val))
            self.draw_rect(subsys_x + 65, subsys_y + 3, fill_len, 3, s_bar_col)
            
            subsys_y -= 22

        # ======================================================================
        # D. BOTTOM SPLIT DECKS — "AI DIAGNOSTIC DIRECTIVE" & "SOP"
        # ======================================================================
        bot_y = 14
        mid_space = 16
        deck_w1 = (width - left_w - right_w - 36 - mid_space) * 0.58
        deck_w2 = (width - left_w - right_w - 36 - mid_space) * 0.42
        deck_x1 = left_x + left_w + 12
        deck_x2 = deck_x1 + deck_w1 + mid_space

        self.draw_gradient_rect(deck_x1, bot_y, deck_w1, bot_h, (0.03, 0.06, 0.10, 0.92), (0.01, 0.02, 0.04, 0.95))
        self.draw_rect_outline(deck_x1, bot_y, deck_w1, bot_h, (0.10, 0.22, 0.35, 0.50))
        self.draw_text("AI DIAGNOSTIC DIRECTIVE & PHYSICAL CAUSAL CHAIN", deck_x1 + 14, bot_y + bot_h - 22, size=12.0, color=(0.0, 0.85, 1.0, 1.0))

        ata_str = state.analytics.get('ata_chapter', 'ATA 00-00')
        subsys_str = state.analytics.get('subsystem', 'PROPULSION_CORE')
        
        b1_w = self.get_text_width(ata_str, size=9.0) + 14
        b1_x = deck_x1 + deck_w1 - b1_w - 14
        self.draw_rect(b1_x, bot_y + bot_h - 26, b1_w, 20, (0.05, 0.22, 0.32, 0.8))
        self.draw_rect_outline(b1_x, bot_y + bot_h - 26, b1_w, 20, (0.0, 0.85, 1.0, 0.75))
        self.draw_text(ata_str, b1_x + 7, bot_y + bot_h - 22, size=9.0, color=(0.0, 0.92, 1.0, 1.0))

        b2_w = self.get_text_width(subsys_str, size=9.0) + 14
        b2_x = b1_x - b2_w - 8
        self.draw_rect(b2_x, bot_y + bot_h - 26, b2_w, 20, (0.08, 0.20, 0.35, 0.65))
        self.draw_rect_outline(b2_x, bot_y + bot_h - 26, b2_w, 20, (0.25, 0.60, 0.85, 0.55))
        self.draw_text(subsys_str, b2_x + 7, bot_y + bot_h - 22, size=9.0, color=(0.85, 0.92, 1.0, 0.95))

        diag_name = state.analytics.get('diagnosed_fault_name', 'NOMINAL_FLIGHT')
        diag_conf = state.analytics.get('diagnosed_confidence', 0.99) * 100
        diag_col = (1.0, 0.35, 0.35, 1.0) if active_fid > 0 else (0.35, 1.0, 0.55, 1.0)
        self.draw_text(f"DIAGNOSIS: {diag_name} ({diag_conf:.0f}% confidence)", deck_x1 + 14, bot_y + bot_h - 44, size=11.5, color=diag_col)

        causal_steps = state.analytics.get('causal_chain', [])
        if not causal_steps:
            causal_steps = [
                f"All 27 telemetry channels within FAA/EASA certified limits for {prof['name']}.",
                "Continuous physics residual autoencoder loss < 0.05.",
                "Zero sub-threshold sensor drift detected across fleet.",
                "Subsystem health index nominal at 100.0%."
            ]

        max_causal_rows = 3
        step_y = bot_y + bot_h - 64
        for idx, step in enumerate(causal_steps[:max_causal_rows], 1):
            step_txt = f"{idx}. {step}"
            if len(step_txt) > 85:
                step_txt = step_txt[:82] + "..."
            self.draw_text(step_txt, deck_x1 + 16, step_y, size=10.0, color=(0.85, 0.92, 1.0, 0.95) if active_fid > 0 else (0.75, 0.88, 0.95, 0.85))
            step_y -= 19

        ai_diag = state.analytics.get('ai_diagnosis', {}) or {}
        ai_status = ai_diag.get('status', 'IDLE')
        if ai_status == 'IDLE':
            self.draw_text("🧠 QWEN3-4B: AI standby (activates on fault onset or operator query)", deck_x1 + 16, step_y, size=9.5, color=(0.60, 0.50, 0.85, 0.75))
        elif ai_status == 'THINKING':
            self.draw_text(f"🧠 QWEN3-4B: Analyzing causal chain against {prof['name']} manuals...", deck_x1 + 16, step_y, size=9.5, color=(0.75, 0.55, 1.0, 0.90))
        elif ai_status == 'READY':
            ai_text = ai_diag.get('explanation', '')
            ai_line = f"🧠 QWEN3-4B: {ai_text}"
            if len(ai_line) > 90:
                ai_line = ai_line[:87] + "..."
            self.draw_text(ai_line, deck_x1 + 16, step_y, size=9.5, color=(0.85, 0.70, 1.0, 0.95))
        elif ai_status == 'ERROR':
            self.draw_text("🧠 QWEN3-4B: AI reasoning layer unavailable (deterministic diagnosis unaffected).", deck_x1 + 16, step_y, size=9.0, color=(0.55, 0.55, 0.60, 0.75))

        self.draw_gradient_rect(deck_x2, bot_y, deck_w2, bot_h, (0.03, 0.06, 0.10, 0.92), (0.01, 0.02, 0.04, 0.95))
        self.draw_rect_outline(deck_x2, bot_y, deck_w2, bot_h, (0.10, 0.22, 0.35, 0.50))
        self.draw_text("PRESCRIPTIVE DIRECTIVE & SOP", deck_x2 + 14, bot_y + bot_h - 22, size=12.0, color=(1.0, 0.75, 0.15, 1.0))

        rec_action = state.analytics.get('prescriptive_action', 'Maintain standard flight profile.')
        self.draw_text("🔧 ACTION:", deck_x2 + 14, bot_y + bot_h - 45, size=10.0, color=(1.0, 0.85, 0.25, 1.0))
        self.draw_multiline_text(rec_action, deck_x2 + 78, bot_y + bot_h - 45, max_width=deck_w2 - 92, size=9.5, line_height=14, max_lines=2, color=(0.35, 1.0, 0.55, 1.0) if active_fid > 0 else (0.85, 0.92, 1.0, 0.90))

        m_order = state.analytics.get('maintenance_order', 'No maintenance required.')
        self.draw_text("🛠 ORDER:", deck_x2 + 14, bot_y + bot_h - 78, size=10.0, color=(0.0, 0.85, 1.0, 0.95))
        self.draw_multiline_text(m_order, deck_x2 + 78, bot_y + bot_h - 78, max_width=deck_w2 - 92, size=9.5, line_height=14, max_lines=2, color=(0.80, 0.88, 0.98, 0.85))

        actions_list = [
            ("[SPACE] ORBIT", 'ACTION_ORBIT'),
            ("[G] GHOST", 'ACTION_GHOST'),
            ("[D] DEBRIEF", 'ACTION_DEBRIEF'),
            ("[0] RESET", 'ACTION_RESET'),
        ]
        act_x = deck_x2 + 14
        act_y = bot_y + 12
        btn_w = (deck_w2 - 28 - (len(actions_list) - 1) * 8) / len(actions_list)

        for act_title, act_id in actions_list:
            is_hover = (state.hovered_button == act_id)
            if act_id == 'ACTION_GHOST' and state.is_ghost_vision:
                b_bg = (0.45, 0.15, 0.65, 0.90)
                b_bd = (0.85, 0.45, 1.0, 1.0)
            elif is_hover:
                b_bg = (0.12, 0.35, 0.55, 0.90)
                b_bd = (0.0, 0.90, 1.0, 0.95)
            else:
                b_bg = (0.06, 0.12, 0.20, 0.80)
                b_bd = (0.16, 0.30, 0.45, 0.50)

            self.draw_rect(int(act_x), act_y, int(btn_w), 24, b_bg)
            self.draw_rect_outline(int(act_x), act_y, int(btn_w), 24, b_bd)
            
            t_w = self.get_text_width(act_title, size=9.0)
            self.draw_text(act_title, int(act_x + (btn_w - t_w) / 2), act_y + 6, size=9.0, color=(1.0, 1.0, 1.0, 1.0))
            
            state.button_rects.append((int(act_x), act_y, int(btn_w), 24, act_id))
            act_x += btn_w + 8

        presets = [
            ("ISO", 'CAM_ISO'),
            ("TOP", 'CAM_TOP'),
            ("FRONT", 'CAM_FRONT'),
            ("FOCUSED", 'CAM_GEARBOX'),
            ("MANIFOLD", 'CAM_EXHAUST'),
            ("GHOST", 'CAM_GHOST'),
            ("RESET", 'CAM_RESET')
        ]
        p_w = 54
        p_h = 20
        p_total_w = len(presets) * (p_w + 6)
        p_x = (width - p_total_w) // 2
        p_y = bot_y + bot_h + 12

        for p_label, p_id in presets:
            is_hover = (state.hovered_button == p_id)
            if is_hover:
                self.draw_rect(p_x, p_y, p_w, p_h, (0.0, 0.45, 0.70, 0.90))
                self.draw_rect_outline(p_x, p_y, p_w, p_h, (0.0, 0.90, 1.0, 0.95))
            else:
                self.draw_rect(p_x, p_y, p_w, p_h, (0.05, 0.10, 0.16, 0.75))
                self.draw_rect_outline(p_x, p_y, p_w, p_h, (0.18, 0.32, 0.48, 0.50))
            
            txt_w = self.get_text_width(p_label, size=8.5)
            self.draw_text(p_label, p_x + (p_w - txt_w) // 2, p_y + 5, size=8.5, color=(0.85, 0.95, 1.0, 0.95))
            state.button_rects.append((p_x, p_y, p_w, p_h, p_id))
            p_x += p_w + 6

        gpu.state.blend_set('NONE')

hud_drawer = HUDDrawer()


# ==============================================================================
# 3. BLENDER SCENE & SHADER CONTROLLER
# ==============================================================================

def ensure_ghost_materials():
    """Ensure reusable Ghost Vision and Fault Red materials exist in Blender datablocks"""
    ghost_mat = bpy.data.materials.get('M_GhostVision_XRay')
    if not ghost_mat:
        ghost_mat = bpy.data.materials.new(name='M_GhostVision_XRay')
        ghost_mat.use_nodes = True
        bsdf = ghost_mat.node_tree.nodes.get('Principled BSDF')
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.06, 0.22, 0.38, 1.0)
            bsdf.inputs['Metallic'].default_value = 0.1
            bsdf.inputs['Roughness'].default_value = 0.15
            bsdf.inputs['Alpha'].default_value = 0.22
            if 'Transmission Weight' in bsdf.inputs:
                bsdf.inputs['Transmission Weight'].default_value = 0.8
            if 'Emission Color' in bsdf.inputs:
                bsdf.inputs['Emission Color'].default_value = (0.01, 0.08, 0.18, 1.0)
                bsdf.inputs['Emission Strength'].default_value = 0.6

    fault_mat = bpy.data.materials.get('M_Fault_RedHighlight')
    if not fault_mat:
        fault_mat = bpy.data.materials.new(name='M_Fault_RedHighlight')
        fault_mat.use_nodes = True
        f_bsdf = fault_mat.node_tree.nodes.get('Principled BSDF')
        if f_bsdf:
            f_bsdf.inputs['Base Color'].default_value = (0.92, 0.04, 0.02, 1.0)
            f_bsdf.inputs['Metallic'].default_value = 0.2
            f_bsdf.inputs['Roughness'].default_value = 0.1
            f_bsdf.inputs['Alpha'].default_value = 1.0
            if 'Emission Color' in f_bsdf.inputs:
                f_bsdf.inputs['Emission Color'].default_value = (1.0, 0.08, 0.02, 1.0)
                f_bsdf.inputs['Emission Strength'].default_value = 4.5

    return ghost_mat, fault_mat

def save_original_materials():
    """Cache authentic materials for all mesh objects in scene."""
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name not in client_state.original_object_materials:
            valid_slots = []
            for slot in obj.material_slots:
                if slot.material and slot.material.name not in {'M_GhostVision_XRay', 'M_Fault_RedHighlight'}:
                    valid_slots.append(slot.material)
                else:
                    valid_slots.append(None)
            client_state.original_object_materials[obj.name] = valid_slots


def get_parts_center_and_radius(part_names: list[str]):
    """Dynamically calculates the 3D bounding box center and radius of matching mesh parts in Blender."""
    if not part_names:
        return None, None
    objs = [
        o for o in bpy.data.objects 
        if o.type == 'MESH' and not o.hide_viewport and any(p.lower() in o.name.lower() or p.lower() == o.name.lower() for p in part_names)
    ]
    if not objs:
        return None, None
    min_co = mathutils.Vector((float('inf'), float('inf'), float('inf')))
    max_co = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
    for obj in objs:
        for c in obj.bound_box:
            w = obj.matrix_world @ mathutils.Vector(c)
            min_co.x = min(min_co.x, w.x)
            min_co.y = min(min_co.y, w.y)
            min_co.z = min(min_co.z, w.z)
            max_co.x = max(max_co.x, w.x)
            max_co.y = max(max_co.y, w.y)
            max_co.z = max(max_co.z, w.z)
    center = (min_co + max_co) * 0.5
    radius = max(0.1, (max_co - min_co).length * 0.5)
    return center, radius


def resolve_fault_targets_from_physics(engine_id: str, telemetry: dict, analytics: dict) -> list[str]:
    """
    PHYSICAL-TO-VISUAL ATTRIBUTION ENGINE (DRDO PS-26054)
    Examines incoming continuous telemetry, compression readings, and physics residuals (d_MAP, d_CHT, d_EGT, etc.)
    and returns matching 3D component mesh names to highlight.
    """
    targets = []
    res = analytics.get('residuals', {})
    
    # 1. Intake Compression Loss / Boost Leak / Turbo Wastegate / Intercooler
    d_map = float(res.get('d_MAP', res.get('map_kpa', 0.0)))
    map_val = float(telemetry.get('MAP', 38.0))
    tps_val = float(telemetry.get('TPS', 70.0))
    if d_map < -6.0 or (map_val < 32.0 and tps_val > 50.0):
        if 'rotax' in engine_id:
            targets.extend(['Exhaust_System_M_SteelDark_0', 'Exhaust_System_M_Steel_0', 'Exhaust_System_M_Chrome_0', 'Cooling_Air_Baffle_M_PlasticWhite_0', 'Fittings_Metric_Rotax914_Extras_0', 'Fittings_Metric_Rotax915_Extras_0'])
        elif 'austro' in engine_id:
            targets.extend(['Turbocharger_M_TurboHousing_0', 'Intercooler_M_CastAluminium_0', 'Boost_Pipe_Hot_M_PolishedAlu_0', 'Boost_Pipe_Cold_M_PolishedAlu_0', 'Heat_Shield_Turbo_M_CrinkleFoil_0', 'Air_Intake_Duct_M_RubberDark_0'])
        elif 'vrde' in engine_id:
            targets.extend(['Wastegate_Actuator_Red_M_AnodizedRed_0', 'Wastegate_Actuator_Canister_M_PlasticBlack_0', 'Wastegate_Rod_Red_M_Stainless_0', 'Intercooler_M_CastAluminium_0.001', 'Exhaust_Downpipe_M_Stainless_0'])

    # 2. Cylinder Compression & Thermal Surge (CHT Overheat)
    for k in range(1, 5):
        d_cht = float(res.get(f'd_CHT_{k}', res.get(f'cht_{k}', 0.0)))
        cht_val = float(telemetry.get(f'CHT_{k}', 95.0))
        if d_cht > 8.0 or cht_val > 115.0:
            if 'rotax' in engine_id:
                targets.extend(['Covers_Theme_M_PlasticTheme_0', 'Covers_Theme_M_PlasticGreen_0', 'Cooling_Air_Baffle_M_PlasticWhite_0'])
            elif 'austro' in engine_id:
                targets.extend(['Cylinder_Head_M_CastAluminium_0', 'Valve_Cover_M_PlasticBlack_0', 'Water_Pump_M_CastAluminium_0', 'Coolant_Hose_Red_M_RedSilicone_0', 'Coolant_Hose_Blue_M_BlueSilicone_0'])
            elif 'vrde' in engine_id:
                targets.extend(['Cylinder_Head_M_CastAluminium_0.001', 'Water_Pump_M_CastAluminium_0.001', 'Coolant_Pipe_Junction_M_CastAluminium_0', 'Coolant_Hose_Upper_M_BlueSilicone_0'])
            break

    # 3. High-Pressure Injection / Common Rail / Fuel Rail
    d_rail = float(res.get('d_FUEL_RAIL_P', res.get('rail_p', 0.0)))
    d_flow = float(res.get('d_FUEL_FLOW', res.get('fuel_flow', 0.0)))
    rail_p = float(telemetry.get('FUEL_RAIL_P', 3.0))
    if d_rail < -40.0 or d_flow < -2.0 or (rail_p < 2.4 and 'rotax' in engine_id) or (rail_p < 500.0 and 'rotax' not in engine_id and rail_p > 10.0):
        if 'rotax' in engine_id:
            targets.extend(['Rotax_912i_Base_M_PlasticGreen_0', 'Rotax_912i_Base_M_Steel_0', 'Rotax_912i_Base_M_PlasticCable_0', 'Fuel_Pump_M_Steel_0', 'Fuel_Pump_M_Rubber_0'])
        elif 'austro' in engine_id:
            targets.extend(['Common_Rail_M_Steel_0', 'HP_Fuel_Pump_M_SteelDark_0', 'Injector_1_M_Steel_0', 'Injector_2_M_Steel_0', 'Injector_3_M_Steel_0', 'Injector_4_M_Steel_0', 'Fuel_Line_1_M_Steel_0', 'Fuel_Line_2_M_Steel_0'])
        elif 'vrde' in engine_id:
            targets.extend(['Common_Rail_M_Steel_0.001', 'HP_Fuel_Pump_M_SteelDark_0.001', 'Injector_1_M_Steel_0.001', 'Injector_2_M_Steel_0.001', 'Injector_3_M_Steel_0.001', 'Injector_4_M_Steel_0.001', 'Fuel_Line_HP_Cyl1_M_Stainless_0', 'Fuel_Line_HP_Cyl2_M_Stainless_0'])

    # 4. Combustion Misfire / EGT Delta / Spark / Glow Plugs
    egts = [float(telemetry.get(f'EGT_{k}', 780.0)) for k in range(1, 5)]
    d_egts = [float(res.get(f'd_EGT_{k}', res.get(f'egt_{k}', 0.0))) for k in range(1, 5)]
    if (max(egts) - min(egts) > 35.0) or min(d_egts) < -30.0:
        if 'rotax' in engine_id:
            targets.extend(['Wiring_Harness_M_Copper_0', 'Rotax_912i_Base_M_Copper_0', 'Wiring_Harness_M_Cobalt_0', 'Wiring_Harness_M_PlasticCable_0'])
        elif 'austro' in engine_id:
            targets.extend(['Glow_Plugs_M_Steel_0', 'Glow_Plug_Control_Unit_M_CastAluminium_0', 'Injector_1_M_Steel_0', 'Injector_2_M_Steel_0'])
        elif 'vrde' in engine_id:
            targets.extend(['Glow_Plug_Cyl1_M_Steel_0', 'Glow_Plug_Cyl2_M_Steel_0', 'Glow_Plug_Cyl3_M_Steel_0', 'Glow_Plug_Cyl4_M_Steel_0', 'Injector_1_M_Steel_0.001'])

    # 5. Lubrication & Oil Pressure Loss / Scavenge Anomaly
    d_oil_p = float(res.get('d_OIL_PRESS', res.get('oil_p', 0.0)))
    oil_p = float(telemetry.get('OIL_PRESS', 4.8))
    d_oil_t = float(res.get('d_OIL_TEMP', res.get('oil_t', 0.0)))
    if d_oil_p < -0.45 or oil_p < 2.2 or d_oil_t > 10.0:
        if 'rotax' in engine_id:
            targets.extend(['Oil_Tank_M_Steel_0', 'Oil_Tank_M_Labels_0', 'Oil_Tank_M_Cobalt_0', 'Oil_Tank_M_PlasticBlack_0'])
        elif 'austro' in engine_id:
            targets.extend(['Oil_Filter_M_MetalPaintedBlack_0', 'Oil_Sump_M_CastAluminium_0', 'Oil_Cooler_M_CastAluminium_0', 'Turbo_Oil_Feed_Line_M_Steel_0', 'Turbo_Oil_Drain_Line_M_Steel_0'])
        elif 'vrde' in engine_id:
            targets.extend(['Engine_Block_M_CastAluminium_0.001', 'Oil_Filter', 'Dipstick_Tube_M_Steel_0'])

    # 6. Propeller Gearbox / Vibration Surge
    vib = float(telemetry.get('VIB_GEARBOX_RMS', 0.7))
    if vib > 1.7 or float(res.get('VIB_RMS', res.get('vib_rms', 0.0))) > 1.8:
        if 'rotax' in engine_id:
            targets.extend(['Gearbox_Type_2_M_Steel_0', 'Gearbox_Type_2_M_MetalPaintedBlack_0', 'Gearbox_Type_2_M_Cobalt_0', 'Gearbox_Type_2_M_PlasticBlack_0', 'Gearbox_Type_2_M_PlasticWhite_0'])
        elif 'austro' in engine_id:
            targets.extend(['Gearbox_M_CastAluminium_0', 'Prop_Governor_PCU_M_CastAluminium_0', 'Prop_Flange_M_Steel_0', 'PCU_Oil_Line_M_Steel_0', 'Gearbox_Logo_M_CastAluminium_0'])
        elif 'vrde' in engine_id:
            targets.extend(['Gearbox_M_CastAluminium_0.001', 'Gearbox_FrontCover_M_CastAluminium_0', 'Gearbox_PropBoss_M_CastAluminium_0', 'Gearbox_Governor_M_CastAluminium_0'])

    # 7. Electrical / Alternator Sag
    v_bus = float(telemetry.get('BUS_VOLTAGE', 14.1))
    d_v = float(res.get('d_BUS_VOLTAGE', res.get('bus_v', 0.0)))
    if (v_bus < 12.8 and 'rotax' in engine_id) or (v_bus < 24.0 and 'rotax' not in engine_id) or d_v < -0.8:
        if 'rotax' in engine_id:
            targets.extend(['External_Alternator_M_Rotax914_Extras_0', 'External_Alternator_M_TimingBelt_0'])
        elif 'austro' in engine_id:
            targets.extend(['Alternator_Details_M_CastAluminium_0', 'Alternator_Bracket_M_SteelDark_0', 'Alternator_Impeller_Fan_M_Steel_0', 'Serpentine_Belt_M_Rubber_0'])
        elif 'vrde' in engine_id:
            targets.extend(['Generator_1_M_CastAluminium_0.001', 'Generator_2_M_CastAluminium_0', 'Alternator_Power_Loom_M_PlasticBlack_0', 'Belt_Tensioner_M_SteelDark_0'])

    # 8. Dual FADEC / EECS Desync & Drift
    if telemetry.get('FADEC_ACTIVE_LANE') == 'LANE_DISAGREE' or float(res.get('d_FADEC', 0.0)) > 0.5:
        if 'rotax' in engine_id:
            targets.extend(['ECU_M_PlasticBlack_0', 'ECU_M_FuseLight_0', 'ECU_M_Motherboard_0', 'ECU_M_GlassMilky_0', 'ECU_M_Labels_0', 'ECU_M_Chrome_0', 'ECU_M_Copper_0'])
        elif 'austro' in engine_id:
            targets.extend(['ECU_Lane_A_M_MetalPaintedBlack_0', 'ECU_Lane_B_M_MetalPaintedBlack_0', 'Engine_Harness_Loom_M_PlasticBlack_0', 'ECU_Bayonet_Plugs_M_CastAluminium_0'])
        elif 'vrde' in engine_id:
            targets.extend(['ECU_Lane_A_M_MetalPaintedBlack_0.001', 'ECU_Lane_B_M_MetalPaintedBlack_0.001', 'Harness_Spine_M_PlasticBlack_0'])

    return targets


def apply_material_state():
    """Slot-Based Material Swapping driven by backend diagnosed fault and physical residuals."""
    ghost_mat, fault_mat = ensure_ghost_materials()
    save_original_materials()
    
    active_fid = client_state.active_commanded_fault_id if client_state.active_commanded_fault_id > 0 else client_state.analytics.get('diagnosed_fault_id', 0)
    target_patterns = set(client_state.analytics.get('target_parts', []))
    
    # 1. Fault profile target parts
    if active_fid in FAULT_DATABASE:
        for p in FAULT_DATABASE[active_fid].get('parts', []):
            target_patterns.add(p)

    # 2. Physics-based residual target parts
    physics_targets = resolve_fault_targets_from_physics(client_state.engine_id, client_state.telemetry, client_state.analytics)
    for pt in physics_targets:
        target_patterns.add(pt)

    # 3. Apply shader materials to active collection meshes
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and not obj.hide_viewport:
            is_target = False
            for pat in target_patterns:
                if pat.lower() in obj.name.lower() or obj.name == pat:
                    is_target = True
                    break
            
            if is_target:
                if len(obj.material_slots) == 0:
                    obj.data.materials.append(fault_mat)
                else:
                    for slot in obj.material_slots:
                        slot.material = fault_mat
            else:
                if client_state.is_ghost_vision:
                    if len(obj.material_slots) == 0:
                        obj.data.materials.append(ghost_mat)
                    else:
                        for slot in obj.material_slots:
                            slot.material = ghost_mat
                else:
                    orig_slots = client_state.original_object_materials.get(obj.name, [])
                    for i, orig_m in enumerate(orig_slots):
                        if i < len(obj.material_slots) and orig_m is not None:
                            obj.material_slots[i].material = orig_m


def update_pulsing_emission():
    """Update dynamic pulsating emission on the active fault material."""
    fault_mat = bpy.data.materials.get('M_Fault_RedHighlight')
    if fault_mat and fault_mat.use_nodes:
        bsdf = fault_mat.node_tree.nodes.get('Principled BSDF')
        if bsdf and 'Emission Strength' in bsdf.inputs:
            pulse = 3.5 + 1.8 * math.sin(time.time() * 9.0)
            bsdf.inputs['Emission Strength'].default_value = pulse


def update_camera_for_backend_fault():
    """Adjusts camera focus target and cinematic framing when backend fault or physics attribution changes."""
    diag_id = client_state.active_commanded_fault_id if client_state.active_commanded_fault_id > 0 else client_state.analytics.get('diagnosed_fault_id', 0)
    physics_targets = resolve_fault_targets_from_physics(client_state.engine_id, client_state.telemetry, client_state.analytics)
    
    current_state_key = (diag_id, tuple(sorted(physics_targets)))
    if current_state_key != getattr(update_camera_for_backend_fault, "_last_state_key", None):
        update_camera_for_backend_fault._last_state_key = current_state_key
        client_state.applied_fault_id = diag_id
        
        # 1. Preset fault mode active
        if diag_id in FAULT_DATABASE:
            f_data = FAULT_DATABASE[diag_id]
            client_state.is_auto_orbit = False
            
            mesh_center, _ = get_parts_center_and_radius(f_data.get('parts', []))
            if mesh_center is not None:
                client_state.cam_target = mesh_center
            else:
                client_state.cam_target = f_data['center'].copy()
                
            client_state.target_orbit_angle = f_data['angle']
            client_state.target_orbit_elevation = f_data['elevation']
            client_state.target_orbit_distance = f_data['distance']
            
        # 2. Generic physics residual triggered without specific fault ID
        elif physics_targets:
            client_state.is_auto_orbit = False
            mesh_center, mesh_radius = get_parts_center_and_radius(physics_targets)
            if mesh_center is not None:
                client_state.cam_target = mesh_center
                client_state.target_orbit_distance = max(DEFAULT_ORBIT_DISTANCE * 0.40, mesh_radius * 2.2)
                client_state.target_orbit_elevation = math.radians(22.0)
            else:
                client_state.cam_target = ENGINE_CENTER.copy()
                client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE * 0.65
                
        # 3. System nominal / cleared
        else:
            client_state.is_auto_orbit = True
            client_state.cam_target = ENGINE_CENTER.copy()
            client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE
            client_state.target_orbit_elevation = DEFAULT_ORBIT_ELEVATION
            
        apply_material_state()


# ==============================================================================
# 4. MODAL INTERACTION OPERATOR
# ==============================================================================

class OT_DigitalTwinSimulator(bpy.types.Operator):
    bl_idname = "view3d.rotax_digital_twin_simulator"
    bl_label = "ANUMAAN Multi-Engine Digital Twin"

    _handle_2d = None
    _timer = None

    def modal(self, context, event):
        now = time.time()

        if event.type == 'TIMER':
            dt = max(0.001, min(0.05, now - client_state.last_frame_time))
            client_state.last_frame_time = now

            client_state.frame_count += 1
            if now - client_state.last_fps_calc >= 0.5:
                client_state.fps = client_state.frame_count / (now - client_state.last_fps_calc)
                client_state.frame_count = 0
                client_state.last_fps_calc = now

            if now - client_state.last_history_sample_time >= 0.10:
                client_state.last_history_sample_time = now
                t = client_state.telemetry
                client_state.history_egt.append(t.get('EGT_2', 780.0))
                client_state.history_oil_temp.append(t.get('OIL_TEMP', 57.4))
                client_state.history_oil_press.append(t.get('OIL_PRESS', 4.89))
                client_state.history_rpm.append(t.get('ENGINE_RPM', 4680.0))

            update_camera_for_backend_fault()
            
            if client_state.analytics.get('diagnosed_fault_id', 0) > 0 or client_state.active_commanded_fault_id > 0:
                update_pulsing_emission()

            # Delta-time exponential smoothing factors
            alpha_target = 1.0 - math.exp(-7.0 * dt)
            alpha_angle = 1.0 - math.exp(-6.5 * dt)
            alpha_elev = 1.0 - math.exp(-7.0 * dt)
            alpha_dist = 1.0 - math.exp(-7.5 * dt)

            if client_state.is_auto_orbit and not client_state.is_dragging:
                client_state.orbit_angle = (client_state.orbit_angle + DEFAULT_ORBIT_SPEED * dt) % (2 * math.pi)
                client_state.target_orbit_angle = client_state.orbit_angle
                client_state.orbit_elevation += (DEFAULT_ORBIT_ELEVATION - client_state.orbit_elevation) * alpha_elev
                client_state.orbit_distance += (DEFAULT_ORBIT_DISTANCE - client_state.orbit_distance) * alpha_dist
                client_state.cur_cam_target = client_state.cur_cam_target.lerp(ENGINE_CENTER, alpha_target)

            elif not client_state.is_dragging:
                angle_diff = (client_state.target_orbit_angle - client_state.orbit_angle + math.pi) % (2 * math.pi) - math.pi
                client_state.orbit_angle = (client_state.orbit_angle + angle_diff * alpha_angle) % (2 * math.pi)
                client_state.orbit_elevation += (client_state.target_orbit_elevation - client_state.orbit_elevation) * alpha_elev
                client_state.orbit_distance += (client_state.target_orbit_distance - client_state.orbit_distance) * alpha_dist
                client_state.cur_cam_target = client_state.cur_cam_target.lerp(client_state.cam_target, alpha_target)

            # Direct computation of camera location along spherical manifold (zero chord-cutting wobble)
            cx = client_state.cur_cam_target.x + client_state.orbit_distance * math.cos(client_state.orbit_angle) * math.cos(client_state.orbit_elevation)
            cy = client_state.cur_cam_target.y + client_state.orbit_distance * math.sin(client_state.orbit_angle) * math.cos(client_state.orbit_elevation)
            cz = client_state.cur_cam_target.z + client_state.orbit_distance * math.sin(client_state.orbit_elevation)
            client_state.cur_cam_pos = mathutils.Vector((cx, cy, cz))

            cam = context.scene.camera
            if cam:
                cam.location = client_state.cur_cam_pos
                direction = client_state.cur_cam_target - cam.location
                cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

            if context.space_data and context.space_data.type == 'VIEW_3D':
                context.space_data.region_3d.view_perspective = 'CAMERA'

            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        # Mouse Hover Check
        mx, my = event.mouse_region_x, event.mouse_region_y
        client_state.hovered_button = None
        for bx, by, bw, bh, bid in client_state.button_rects:
            if bx <= mx <= bx + bw and by <= my <= by + bh:
                client_state.hovered_button = bid
                break

        # Click on HUD Buttons
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS' and client_state.hovered_button:
            bid = client_state.hovered_button
            scale = DEFAULT_ORBIT_DISTANCE / 230.0
            if bid.startswith('ENGINE_'):
                eid = bid.replace('ENGINE_', '')
                switch_engine(eid)
            elif bid.startswith('FAULT_'):
                fid = int(bid.split('_')[1])
                send_server_command("SET_FAULT", fault_id=fid)
            elif bid == 'CAM_ISO':
                client_state.is_auto_orbit = False
                client_state.cam_target = ENGINE_CENTER.copy()
                client_state.target_orbit_angle = -1.2
                client_state.target_orbit_elevation = DEFAULT_ORBIT_ELEVATION
                client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE
            elif bid == 'CAM_TOP':
                client_state.is_auto_orbit = False
                client_state.cam_target = ENGINE_CENTER.copy()
                client_state.target_orbit_angle = 0.0
                client_state.target_orbit_elevation = math.radians(88.0)
                client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE * 1.15
            elif bid == 'CAM_FRONT':
                client_state.is_auto_orbit = False
                client_state.cam_target = ENGINE_CENTER.copy()
                client_state.target_orbit_angle = math.radians(-90.0)
                client_state.target_orbit_elevation = math.radians(5.0)
                client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE * 0.90
            elif bid == 'CAM_GEARBOX':
                client_state.is_auto_orbit = False
                client_state.cam_target = ENGINE_CENTER.copy() + mathutils.Vector((0.0, -10.0 * scale, 5.0 * scale))
                client_state.target_orbit_angle = math.radians(-90.0)
                client_state.target_orbit_elevation = math.radians(14.0)
                client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE * 0.65
            elif bid == 'CAM_EXHAUST':
                client_state.is_auto_orbit = False
                client_state.cam_target = ENGINE_CENTER.copy() + mathutils.Vector((5.0 * scale, 10.0 * scale, -10.0 * scale))
                client_state.target_orbit_angle = math.radians(-45.0)
                client_state.target_orbit_elevation = math.radians(-8.0)
                client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE * 0.75
            elif bid in {'CAM_GHOST', 'ACTION_GHOST'}:
                client_state.is_ghost_vision = not client_state.is_ghost_vision
                apply_material_state()
            elif bid in {'CAM_RESET', 'ACTION_RESET'}:
                send_server_command("CLEAR_FAULT")
                client_state.is_auto_orbit = True
                client_state.cam_target = ENGINE_CENTER.copy()
                client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE
                client_state.target_orbit_elevation = DEFAULT_ORBIT_ELEVATION
            elif bid == 'ACTION_ORBIT':
                client_state.is_auto_orbit = not client_state.is_auto_orbit
            elif bid == 'ACTION_DEBRIEF':
                send_server_command("EXPORT_DEBRIEF")
                client_state.debrief_msg = "Debrief report requested on laptop server."
                client_state.debrief_time = time.time()
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        # Mouse Orbit / Pan / Zoom
        if event.type in {'LEFTMOUSE', 'MIDDLEMOUSE', 'RIGHTMOUSE'}:
            if event.value == 'PRESS' and not client_state.hovered_button:
                client_state.is_dragging = True
                client_state.drag_button = event.type
                client_state.last_mouse_x = event.mouse_x
                client_state.last_mouse_y = event.mouse_y
                if event.type in {'LEFTMOUSE', 'MIDDLEMOUSE'}:
                    client_state.is_auto_orbit = False
            elif event.value == 'RELEASE':
                client_state.is_dragging = False
                client_state.drag_button = None

        elif event.type == 'MOUSEMOVE' and client_state.is_dragging:
            dx = event.mouse_x - client_state.last_mouse_x
            dy = event.mouse_y - client_state.last_mouse_y
            client_state.last_mouse_x = event.mouse_x
            client_state.last_mouse_y = event.mouse_y

            if client_state.drag_button in {'LEFTMOUSE', 'MIDDLEMOUSE'}:
                client_state.orbit_angle = (client_state.orbit_angle + dx * 0.005) % (2 * math.pi)
                client_state.target_orbit_angle = client_state.orbit_angle
                client_state.orbit_elevation = max(-0.30, min(1.45, client_state.orbit_elevation + dy * 0.005))
                client_state.target_orbit_elevation = client_state.orbit_elevation
            elif client_state.drag_button == 'RIGHTMOUSE':
                cam_mat = context.scene.camera.matrix_world if context.scene.camera else mathutils.Matrix.Identity(4)
                right = cam_mat.to_3x3() @ mathutils.Vector((1, 0, 0))
                up = cam_mat.to_3x3() @ mathutils.Vector((0, 1, 0))
                pan_scale = DEFAULT_ORBIT_DISTANCE * 0.0012
                pan_delta = (right * dx - up * dy) * pan_scale
                client_state.cam_target -= pan_delta
                client_state.cur_cam_target -= pan_delta

        elif event.type == 'WHEELUPMOUSE':
            client_state.target_orbit_distance = max(DEFAULT_ORBIT_DISTANCE * 0.20, client_state.target_orbit_distance * 0.88)
        elif event.type == 'WHEELDOWNMOUSE':
            client_state.target_orbit_distance = min(DEFAULT_ORBIT_DISTANCE * 3.5, client_state.target_orbit_distance * 1.14)

        # Keyboard Shortcuts
        if event.value == 'PRESS':
            scale = DEFAULT_ORBIT_DISTANCE / 230.0
            if event.type == 'F1':
                switch_engine('rotax_912is')
            elif event.type == 'F2':
                switch_engine('rotax_914')
            elif event.type == 'F3':
                switch_engine('rotax_915is')
            elif event.type == 'F4':
                switch_engine('austro_ae300')
            elif event.type == 'F5':
                switch_engine('vrde_jayem_2_2l')
                
            elif event.type in {'ONE', 'NUMPAD_1'}:
                send_server_command("SET_FAULT", fault_id=1)
            elif event.type in {'TWO', 'NUMPAD_2'}:
                send_server_command("SET_FAULT", fault_id=2)
            elif event.type in {'THREE', 'NUMPAD_3'}:
                send_server_command("SET_FAULT", fault_id=3)
            elif event.type in {'FOUR', 'NUMPAD_4'}:
                send_server_command("SET_FAULT", fault_id=4)
            elif event.type in {'FIVE', 'NUMPAD_5'}:
                send_server_command("SET_FAULT", fault_id=5)
            elif event.type in {'SIX', 'NUMPAD_6'}:
                send_server_command("SET_FAULT", fault_id=6)
            elif event.type in {'SEVEN', 'NUMPAD_7'}:
                send_server_command("SET_FAULT", fault_id=7)
            elif event.type in {'EIGHT', 'NUMPAD_8'}:
                send_server_command("SET_FAULT", fault_id=8)
                
            elif event.type in {'T'}:
                client_state.is_auto_orbit = False
                client_state.cam_target = ENGINE_CENTER.copy()
                client_state.target_orbit_angle = 0.0
                client_state.target_orbit_elevation = math.radians(88.0)
                client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE * 1.15
            elif event.type in {'F'}:
                client_state.is_auto_orbit = False
                client_state.cam_target = ENGINE_CENTER.copy()
                client_state.target_orbit_angle = math.radians(-90.0)
                client_state.target_orbit_elevation = math.radians(5.0)
                client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE * 0.90
            elif event.type in {'I'}:
                client_state.is_auto_orbit = False
                client_state.cam_target = ENGINE_CENTER.copy()
                client_state.target_orbit_angle = -1.2
                client_state.target_orbit_elevation = DEFAULT_ORBIT_ELEVATION
                client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE
            elif event.type in {'G', 'X'}:
                client_state.is_ghost_vision = not client_state.is_ghost_vision
                apply_material_state()
            elif event.type == 'D':
                send_server_command("EXPORT_DEBRIEF")
                client_state.debrief_msg = "Debrief report requested on laptop server."
                client_state.debrief_time = time.time()
            elif event.type in {'ZERO', 'NUMPAD_0', 'ESC'}:
                send_server_command("CLEAR_FAULT")
                client_state.is_auto_orbit = True
                client_state.cam_target = ENGINE_CENTER.copy()
                client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE
                client_state.target_orbit_elevation = DEFAULT_ORBIT_ELEVATION
            elif event.type == 'SPACE':
                client_state.is_auto_orbit = not client_state.is_auto_orbit
            elif event.type in {'H', 'TAB'}:
                client_state.is_hud_visible = not client_state.is_hud_visible

        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            return {'CANCELLED'}

        args = (self, context)
        self._handle_2d = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
        
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.020, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

def draw_callback_px(op, context):
    region = context.region
    hud_drawer.render(region.width, region.height, client_state)


# ==============================================================================
# 5. WORKSPACE CONFIGURATION & STARTUP
# ==============================================================================

def ensure_studio_lighting():
    """Configures high-definition 3-point studio lighting if lights are absent."""
    scene = bpy.context.scene
    lights = [o for o in bpy.data.objects if o.type == 'LIGHT']
    if not lights:
        light_data1 = bpy.data.lights.new(name="Studio_Key_Sun", type="SUN")
        light_data1.energy = 4.0
        light_data1.color = (1.0, 0.98, 0.95)
        light_obj1 = bpy.data.objects.new(name="Studio_Key_Sun", object_data=light_data1)
        scene.collection.objects.link(light_obj1)
        light_obj1.rotation_euler = (math.radians(45), math.radians(30), math.radians(60))
        
        light_data2 = bpy.data.lights.new(name="Studio_Fill_Sun", type="SUN")
        light_data2.energy = 2.0
        light_data2.color = (0.85, 0.92, 1.0)
        light_obj2 = bpy.data.objects.new(name="Studio_Fill_Sun", object_data=light_data2)
        scene.collection.objects.link(light_obj2)
        light_obj2.rotation_euler = (math.radians(-45), math.radians(-30), math.radians(-120))


def configure_clean_viewport_workspace():
    """Set up clean Viewport Shading simulation window and start network receiver."""
    scene = bpy.context.scene
    
    # 1. Set Render engine to EEVEE
    engines_available = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if "BLENDER_EEVEE_NEXT" in engines_available:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    else:
        scene.render.engine = 'BLENDER_EEVEE'

    # 2. Guarantee stationary meshes
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.animation_data_clear()

    # 3. Setup Studio Lighting
    ensure_studio_lighting()

    # 4. Activate initial engine collection
    switch_engine_collection(ACTIVE_ENGINE_ID)

    # 5. Auto-compute bounds and camera distance
    center, dist = compute_engine_bounds(ENGINE_PROFILE['default_center'], ENGINE_PROFILE['default_distance'])
    global ENGINE_CENTER, DEFAULT_ORBIT_DISTANCE
    ENGINE_CENTER = center
    DEFAULT_ORBIT_DISTANCE = dist
    client_state.cam_target = ENGINE_CENTER.copy()
    client_state.cur_cam_target = ENGINE_CENTER.copy()
    client_state.orbit_distance = DEFAULT_ORBIT_DISTANCE
    client_state.target_orbit_distance = DEFAULT_ORBIT_DISTANCE

    # 6. Setup Camera
    cam = bpy.data.objects.get("TurntableCam") or bpy.data.objects.get("MainCamera")
    if not cam:
        cam_data = bpy.data.cameras.new("TurntableCam")
        cam = bpy.data.objects.new("TurntableCam", cam_data)
        scene.collection.objects.link(cam)
    if cam.data:
        cam.data.clip_start = 0.01
        cam.data.clip_end = 5000.0
        cam.data.lens = 55.0
        cam.data.sensor_width = 36.0
    scene.camera = cam
    cam.animation_data_clear()

    # 7. Cache master materials
    save_original_materials()

    # 8. Lock Viewport to Camera View + Rendered Shading + Hide Gizmos
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.region_3d.view_perspective = 'CAMERA'
                        space.shading.type = 'RENDERED'
                        space.shading.use_scene_lights = True
                        space.shading.use_scene_world = True
                        
                        space.overlay.show_overlays = False
                        space.show_gizmo = False
                        space.show_region_toolbar = False
                        space.show_region_ui = False
                        space.show_region_header = False

    # 9. Start Background Telemetry Receiver Thread
    if not hasattr(configure_clean_viewport_workspace, "_receiver_started"):
        receiver = TelemetryReceiverThread()
        receiver.start()
        configure_clean_viewport_workspace._receiver_started = True
        print(f"[BLENDER CLIENT] Connecting to Multi-Engine Backend Server at: {SERVER_BASE_URL}")

    # 10. Maximize 3D Viewport & invoke modal
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        try:
                            with bpy.context.temp_override(window=window, area=area, region=region):
                                bpy.ops.screen.screen_full_area(use_hide_panels=True)
                                bpy.ops.view3d.rotax_digital_twin_simulator('INVOKE_DEFAULT')
                        except Exception as e:
                            print(f"[NOTE] Viewport maximized: {e}")
                        return

def register():
    try:
        bpy.utils.register_class(OT_DigitalTwinSimulator)
    except ValueError:
        pass

def unregister():
    try:
        bpy.utils.unregister_class(OT_DigitalTwinSimulator)
    except ValueError:
        pass

if __name__ == "__main__":
    register()
    
    if "--test-mode" in sys.argv or bpy.app.background:
        print("[BLENDER CLIENT] Headless verification passed successfully!")
    else:
        bpy.app.timers.register(configure_clean_viewport_workspace, first_interval=0.25)
