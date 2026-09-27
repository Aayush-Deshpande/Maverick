"""
Universal Multi-Engine Cinematic Showcase Generator — DRDO ANUMAAN
===================================================================
Generates complete 6-station cinematic technical showcases for all ANUMAAN engines:
- rotax_912is    : Rotax 912 iS Sport (Naturally Aspirated Spark Ignition, Dual FADEC)
- rotax_914      : Rotax 914 F (Turbocharged Spark Ignition)
- rotax_915is    : Rotax 915 iS (Turbocharged Intercooled Spark Ignition)
- austro_ae300   : Austro Engine AE300 / AE330 (Common-Rail Turbo Diesel, Jet-A1)
- vrde_jayem_2_2l: DRDO VRDE / Jayem 2.2L (Indigenous 180 HP CRDi Turbo Diesel)

Outputs per engine in assets/renders/engines/<engine_id>/:
- <engine_id>_technical_showcase.mp4 (Full 1080p MP4 cinematic video with HUD overlays)
- <engine_id>_showcase_contact_sheet.png (3x2 1080p master contact sheet)
- stations/ (6 high-res beauty stills with technical HUD cards)
- cinematic_showcase/ (120 composited 1080p animation frames)
- tracking_data.json (evaluated 3D-to-2D tracking matrix)
- assets/blender/<engine_id>_showcase.blend (animated Blender scene)
"""

import os
import sys
import json
import math
import argparse
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np

REPO_ROOT = Path(r"e:\backup-llm\backup-no-llm\3d_engine")
RENDERS_ROOT = REPO_ROOT / "assets" / "renders" / "engines"
BLENDER_ROOT = REPO_ROOT / "assets" / "blender"
BLENDER_BIN = r"E:\Blender\blender.exe"

# ──────────────────────────────────────────────────────────────────────
# Engine Catalog & Configuration
# ──────────────────────────────────────────────────────────────────────

ENGINE_CONFIGS = {
    "rotax_912is": {
        "title": "ROTAX 912 iS SPORT",
        "subtitle": "DUAL FADEC INJECTION AERO ENGINE // DRDO ANUMAAN",
        "power_str": "1,352 CC | 100 HP @ 5,800 RPM | DUAL EMS914 ECU",
        "source_blend": BLENDER_ROOT / "rotax_912_is_sport.blend",
        "out_blend": BLENDER_ROOT / "rotax_912is_showcase.blend",
        "output_dir": RENDERS_ROOT / "rotax_912is",
        "exclude_meshes": [],
        "telemetry_sim": {"rpm": 5800, "map": 1.01, "egt": 820, "cht": 105, "status": "NOMINAL"},
        "stations": {
            1: {
                "tag": "STATION 01 // OVERVIEW ARCHITECTURE",
                "title": "ROTAX 912 iS SPORT AERO ENGINE",
                "subtitle": "NATURALLY ASPIRATED BOXER WITH DUAL REDUNDANT FADEC",
                "specs": [
                    ("ENGINE TYPE", "4-Cyl Boxer, 4-Stroke Naturally Aspirated Engine"),
                    ("DISPLACEMENT", "1,352 cc (82.5 cu in) | Bore: 84mm / Stroke: 61mm"),
                    ("MAX POWER", "73.5 kW (100 HP) @ 5,800 RPM (Take-Off Power)"),
                    ("CONTINUOUS", "69.0 kW (92.5 HP) @ 5,500 RPM Continuous Operating"),
                    ("COOLING", "Liquid-Cooled Cylinder Heads, Ram-Air Cylinder Fins"),
                    ("LUBRICATION", "Dry Sump with Trochoid Pump & External Oil Tank"),
                    ("FUEL SYSTEM", "Dual Electronic Port Injection (2 Injectors/Cyl)"),
                    ("MANAGEMENT", "Rotax EMS914 Dual Redundant FADEC (Lanes A & B)"),
                ],
                "metric_label": "SYSTEM HEALTH INDEX: 99.2% [NOMINAL]",
                "metric_val": 0.992,
                "color": (0, 229, 255, 255),
                "side": "left"
            },
            2: {
                "tag": "STATION 02 // POWER TRANSMISSION",
                "title": "INTEGRATED REDUCTION GEARBOX & FLANGE",
                "subtitle": "MECHANICAL TORQUE REDUCTION & SLIPPER CLUTCH",
                "specs": [
                    ("GEAR RATIO", "Reduction Ratio i = 2.43 : 1 (Propeller RPM: 2,387)"),
                    ("OUTPUT FLANGE", "AND 20010 8-Bolt PCD Aircraft Propeller Flange"),
                    ("SLIPPER CLUTCH", "Integrated Torsional Overload Dog Clutch"),
                    ("DIRECTION", "Counter-Clockwise Rotation (Viewed from Front)"),
                    ("BEARINGS", "Precision Double Row Angular Contact Thrust Bearings"),
                    ("PHM SENSOR", "CH-02 Dynamic Torsional Load & Gear Vibration"),
                ],
                "metric_label": "GEARTRAIN VIBRATION: 0.08 g [ISO 10816 NOMINAL]",
                "metric_val": 0.98,
                "color": (0, 229, 255, 255),
                "side": "right"
            },
            3: {
                "tag": "STATION 03 // FADEC & INJECTION",
                "title": "DUAL ELECTRONIC INJECTION & THROTTLE",
                "subtitle": "REDUNDANT DUAL-LANE ENGINE MANAGEMENT (EMS914)",
                "specs": [
                    ("INJECTION TYPE", "Multi-Point Sequential Port Injection (2× per Cyl)"),
                    ("THROTTLE BODY", "Dual Synchronized Electronic Throttle Actuators"),
                    ("ECU REDUNDANCY", "Lane A / Lane B Autonomous Fail-Operational FADEC"),
                    ("FUEL SAVINGS", "Eco Mode (Lambda 1.05) delivers 35% Lower Cruise Burn"),
                    ("FUEL PRESSURE", "3.0 bar Constant Delivery from Dual Electric Pumps"),
                    ("PHM SENSOR", "CH-01 Fuel Pressure & Injector Solenoid Impedance"),
                ],
                "metric_label": "INJECTION STATUS: DUAL LANES ACTIVE & SYNCHRONIZED",
                "metric_val": 0.96,
                "color": (0, 230, 118, 255),
                "side": "right"
            },
            4: {
                "tag": "STATION 04 // ELECTRICAL GENERATION",
                "title": "DUAL INTERNAL GENERATORS & AVIONICS",
                "subtitle": "REDUNDANT POWER DISTRIBUTION ARCHITECTURE",
                "specs": [
                    ("GENERATOR A", "Internal 16A / 14V Stator for Engine Control (ECU)"),
                    ("GENERATOR B", "External 30A / 14V Alternator for Avionics Bus"),
                    ("FUSEBOX SYSTEM", "Integrated Solid-State Current Limiting Module"),
                    ("STARTING SYSTEM", "Electric Starter with Automatic Overrunning Clutch"),
                    ("IGNITION BUS", "Dedicated Engine Generator Power (No Battery Drain)"),
                    ("PHM SENSOR", "CH-06 Generator Voltage & Battery State-of-Charge"),
                ],
                "metric_label": "ELECTRICAL BUS: 14.2V GENERATOR B NOMINAL",
                "metric_val": 0.97,
                "color": (255, 179, 0, 255),
                "side": "left"
            },
            5: {
                "tag": "STATION 05 // EXHAUST & COOLING",
                "title": "STAINLESS EXHAUST & RAM COOLING BAFFLES",
                "subtitle": "EQUAL-LENGTH SCAVENGING & DUAL AIR DUCTS",
                "specs": [
                    ("EXHAUST MANIFOLD", "4-into-1 AISI 321 Stainless Headers with Silencer"),
                    ("EGT LIMIT", "Max Exhaust Gas Temp: 880°C (1,616°F) Continuous"),
                    ("CYLINDER BAFFLES", "Engineered Composite Ram-Air Cooling Shrouds"),
                    ("HEAD COOLING", "High-Velocity Coolant Jacket (Max CHT: 120°C)"),
                    ("EXPANSION JOINTS", "Stainless Tension Springs with Spherical Couplings"),
                    ("PHM SENSOR", "CH-03/04 EGT Thermocouples & CHT Temp Transducers"),
                ],
                "metric_label": "THERMAL SCAVENGING: 820°C EGT [ALL CYLINDERS BALANCED]",
                "metric_val": 0.95,
                "color": (0, 229, 255, 255),
                "side": "right"
            },
            6: {
                "tag": "STATION 06 // PHM DIAGNOSTIC SUITE",
                "title": "DRDO ANUMAAN HEALTH MONITORING SUITE",
                "subtitle": "PROGNOSTICS & SYSTEM DIAGNOSTICS DIGITAL TWIN",
                "specs": [
                    ("CH-01 [FUEL INJ]", "3.0 bar Fuel Rail Delivery | Dual Lanes Active"),
                    ("CH-02 [VIBRATION]", "0.08g Torsional Geartrain Spectrum Nominal"),
                    ("CH-03 [EGT ARRAY]", "820°C Average Combustion Exhaust Temperature"),
                    ("CH-04 [CHT ARRAY]", "105°C Cylinder Head Glycol Coolant Nominal"),
                    ("CH-05 [LAMBDA O2]", "Lambda = 1.05 Eco Cruise Fuel Economy Active"),
                    ("CH-06 [ELECTRICAL]", "Generator A: 14.1V | Generator B: 14.2V (30A)"),
                    ("DIAGNOSTIC MODEL", "Physics-Informed Causal Fault Isolation Active"),
                    ("PROGNOSTICS", "Remaining Useful Life (RUL): > 2,000 Flight Hours"),
                ],
                "metric_label": "ALL 8 TELEMETRY CHANNELS SYNCHRONIZED & ONLINE",
                "metric_val": 1.0,
                "color": (0, 230, 118, 255),
                "side": "left"
            }
        }
    },

    "rotax_915is": {
        "title": "ROTAX 915 iS TURBO",
        "subtitle": "TURBOCHARGED INTERCOOLED AERO ENGINE // DRDO ANUMAAN",
        "power_str": "1,352 CC | 141 HP @ 5,800 RPM | 15,000 FT CEILING",
        "source_blend": BLENDER_ROOT / "rotax_915is.blend",
        "out_blend": BLENDER_ROOT / "rotax_915is_showcase.blend",
        "output_dir": RENDERS_ROOT / "rotax_915is",
        "exclude_meshes": ["Plane001", "Plane"],
        "telemetry_sim": {"rpm": 5800, "map": 1.54, "egt": 920, "cht": 115, "status": "NOMINAL"},
        "stations": {
            1: {
                "tag": "STATION 01 // OVERVIEW ARCHITECTURE",
                "title": "ROTAX 915 iS TURBO AERO ENGINE",
                "subtitle": "HIGH-ALTITUDE TURBOCHARGED & INTERCOOLED POWERPLANT",
                "specs": [
                    ("ENGINE TYPE", "4-Cyl Boxer, 4-Stroke Turbocharged Intercooled"),
                    ("DISPLACEMENT", "1,352 cc (82.5 cu in) | 4 Valves per Cylinder"),
                    ("MAX POWER", "104 kW (141 HP) @ 5,800 RPM (5-min Take-Off)"),
                    ("CONTINUOUS", "99 kW (135 HP) @ 5,500 RPM Continuous Operating"),
                    ("INTERCOOLING", "Air-to-Air Aluminum Charge Air Cooler (Intercooler)"),
                    ("MAX BOOST", "1.54 bar (45.6 inHg / 22.3 PSI) Manifold Absolute"),
                    ("CRITICAL ALTITUDE", "Maintains Full 141 HP Power to 15,000 ft AMSL"),
                    ("MANAGEMENT", "Dual Redundant FADEC (EMS915 Lanes A & B)"),
                ],
                "metric_label": "SYSTEM HEALTH INDEX: 98.8% [NOMINAL]",
                "metric_val": 0.988,
                "color": (0, 229, 255, 255),
                "side": "left"
            },
            2: {
                "tag": "STATION 02 // POWER TRANSMISSION",
                "title": "REINFORCED REDUCTION GEARBOX & FLANGE",
                "subtitle": "HIGH-TORQUE 141 HP CAPABLE DRIVE TRAIN",
                "specs": [
                    ("GEAR RATIO", "Reduction Ratio i = 2.54 : 1 (Propeller RPM: 2,283)"),
                    ("TORQUE RATING", "Reinforced Gear Case rated for 150 Nm Continuous"),
                    ("SLIPPER CLUTCH", "Heavy-Duty Integrated Torsional Slipper Dog Clutch"),
                    ("PROP FLANGE", "AND 20010 Specification / 8-Bolt PCD Aircraft Pattern"),
                    ("VIBRATION DAMPER", "Elastomeric Torsional Dampener on Input Quill Shaft"),
                    ("PHM SENSOR", "CH-02 Geartrain Torsional Impulse & Bearing Load"),
                ],
                "metric_label": "GEARTRAIN VIBRATION: 0.10 g [OPTIMAL]",
                "metric_val": 0.97,
                "color": (0, 229, 255, 255),
                "side": "right"
            },
            3: {
                "tag": "STATION 03 // CHARGE AIR COOLING",
                "title": "ALUMINUM CHARGE AIR INTERCOOLER",
                "subtitle": "HIGH-EFFICIENCY AIR-TO-AIR DENSITY BOOSTING",
                "specs": [
                    ("HEAT EXCHANGER", "High-Flow Bar & Plate Aluminum Intercooler Core"),
                    ("TEMPERATURE DROP", "Charge Air ΔT > 50°C Reduction before Throttle Body"),
                    ("DENSITY BOOST", "Maintains High Mass Airflow into Combustion Chambers"),
                    ("CHARGE DUCTING", "Reinforced Multi-Ply Silicone Couplers & Clamps"),
                    ("AIR FILTER", "Dynamic Ram-Air Conical Filter with Water Separator"),
                    ("PHM SENSOR", "CH-01 Intercooler Delta-P & Charge Air Temp (CAT)"),
                ],
                "metric_label": "INTERCOOLER DELTA-T: 52°C HEAT REJECTION [NOMINAL]",
                "metric_val": 0.96,
                "color": (0, 229, 255, 255),
                "side": "left"
            },
            4: {
                "tag": "STATION 04 // TURBOCHARGER & WASTEGATE",
                "title": "INTEGRATED GARRETT TURBOCHARGER",
                "subtitle": "HIGH-PRESSURE TURBINE & ELECTRONIC WASTEGATE",
                "specs": [
                    ("TURBO MODEL", "Garrett High-Flow Floating Hydrodynamic Bearings"),
                    ("WASTEGATE CONTROL", "Precision DC Servomotor Electronic Actuation"),
                    ("MAX BOOST LIMIT", "1.54 bar (45.6 inHg) Closed-Loop FADEC Governed"),
                    ("TURBINE SPEED", "Max 165,000 RPM Continuous Operating Speed"),
                    ("EXHAUST SYSTEM", "AISI 321 Stainless Steel Tuned Headers with Heat Shield"),
                    ("PHM SENSOR", "CH-05 Turbocharger Compressor RPM & Wastegate Position"),
                ],
                "metric_label": "BOOST REGULATION: 1.54 bar MAP LOCKED [FADEC CLOSED LOOP]",
                "metric_val": 0.98,
                "color": (255, 179, 0, 255),
                "side": "right"
            },
            5: {
                "tag": "STATION 05 // DUAL FADEC SYSTEM",
                "title": "DUAL REDUNDANT EMS915 FADEC",
                "subtitle": "ELECTRONIC ENGINE CONTROL & SENSOR HARNESS",
                "specs": [
                    ("ARCHITECTURE", "Dual Lane FADEC (Lane A Master / Lane B Hot Backup)"),
                    ("IGNITION SYSTEM", "Dual Digital Transistorized Spark Ignition (2 Plugs/Cyl)"),
                    ("FUEL DELIVERY", "Dual High-Pressure Electric Pumps with Return Loop"),
                    ("ALTITUDE CONTROL", "Barometric Air Density Automatic Closed-Loop Mapping"),
                    ("FAULT TOLERANCE", "Seamless Single-Lane Fallback with Zero Power Loss"),
                    ("PHM SENSOR", "CH-07 FADEC Lane Health & Sensor Bus Integrity"),
                ],
                "metric_label": "FADEC STATUS: LANES A & B OPERATIONAL [ZERO FAULTS]",
                "metric_val": 0.99,
                "color": (0, 230, 118, 255),
                "side": "left"
            },
            6: {
                "tag": "STATION 06 // PHM DIAGNOSTIC SUITE",
                "title": "DRDO ANUMAAN HEALTH MONITORING SUITE",
                "subtitle": "PROGNOSTICS & SYSTEM DIAGNOSTICS DIGITAL TWIN",
                "specs": [
                    ("CH-01 [MAP BOOST]", "1.54 bar Manifold Absolute Pressure Nominal"),
                    ("CH-02 [VIBRATION]", "0.10g Torsional Geartrain Vibration Nominal"),
                    ("CH-03 [EGT ARRAY]", "920°C Turbine Inlet Temperature Nominal"),
                    ("CH-04 [CHT ARRAY]", "115°C Cylinder Head Coolant Temp Nominal"),
                    ("CH-05 [TURBO RPM]", "158,400 RPM Turbine Shaft Speed Active"),
                    ("CH-06 [CAT TEMP]", "42°C Charge Air Temperature Post-Intercooler"),
                    ("DIAGNOSTIC MODEL", "Physics-Informed Causal Fault Tree Active"),
                    ("PROGNOSTICS", "Remaining Useful Life (RUL): > 1,900 Flight Hours"),
                ],
                "metric_label": "ALL 8 TELEMETRY CHANNELS SYNCHRONIZED & ONLINE",
                "metric_val": 1.0,
                "color": (0, 230, 118, 255),
                "side": "left"
            }
        }
    },

    "austro_ae300": {
        "title": "AUSTRO ENGINE AE300 / AE330",
        "subtitle": "2.0L COMMON-RAIL TURBO DIESEL // DRDO ANUMAAN",
        "power_str": "1,991 CC | 180 HP @ 3,880 RPM | JET-A1 MULTI-FUEL",
        "source_blend": REPO_ROOT / "assets" / "models" / "engines" / "austro_ae330.blend",
        "out_blend": BLENDER_ROOT / "austro_ae300_showcase.blend",
        "output_dir": RENDERS_ROOT / "austro_ae300",
        "exclude_meshes": ["Studio_Cyclorama"],
        "telemetry_sim": {"rpm": 3880, "map": 2.25, "egt": 740, "cht": 98, "status": "NOMINAL"},
        "stations": {
            1: {
                "tag": "STATION 01 // OVERVIEW ARCHITECTURE",
                "title": "AUSTRO AE300 / AE330 TURBO DIESEL",
                "subtitle": "2.0L INLINE-4 DOHC COMMON-RAIL JET-A1 POWERPLANT",
                "specs": [
                    ("ENGINE TYPE", "Inline-4, 4-Stroke DOHC 16-Valve Turbo Diesel"),
                    ("DISPLACEMENT", "1,991 cc (121.5 cu in) | Bore: 83mm / Stroke: 92mm"),
                    ("MAX POWER", "132 kW (180 HP) @ 3,880 RPM (AE330 Take-Off Power)"),
                    ("MAX TORQUE", "410 Nm (302 lb-ft) @ 2,500 RPM High Torque Ceiling"),
                    ("FUEL SYSTEM", "Bosch High-Pressure Common-Rail Direct Injection (CRDi)"),
                    ("FUEL COMPATIBILITY", "Jet-A1, Jet-A, JP-8, Diesel EN 590 (Multi-Fuel)"),
                    ("ENGINE BLOCK", "High-Strength Cast Iron Crankcase with Aluminum Head"),
                    ("MANAGEMENT", "Dual-Channel EECU (Electronic Engine Control Unit)"),
                ],
                "metric_label": "SYSTEM HEALTH INDEX: 99.0% [NOMINAL]",
                "metric_val": 0.99,
                "color": (0, 229, 255, 255),
                "side": "left"
            },
            2: {
                "tag": "STATION 02 // POWER TRANSMISSION",
                "title": "INTEGRATED REDUCTION GEARBOX & DAMPER",
                "subtitle": "TORSIONAL VIBRATION ISOLATION & CONSTANT SPEED FLANGE",
                "specs": [
                    ("GEAR RATIO", "Reduction Ratio i = 1.69 : 1 (Propeller RPM: 2,300)"),
                    ("TORSIONAL DAMPER", "Integrated Dual-Mass Flywheel & Spring Slipper Damper"),
                    ("PROP GOVERNOR", "Direct Hydraulic PCU Constant-Speed Governor Mount"),
                    ("PROP FLANGE", "ARP 502 / SAE Type Propeller Flange 8-Stud PCD"),
                    ("LUBRICATION", "Independent Gearbox Oil Circuit with Dedicated Cooler"),
                    ("PHM SENSOR", "CH-02 Gearbox Oil Pressure & Vibration Telemetry"),
                ],
                "metric_label": "GEARTRAIN VIBRATION: 0.09 g [ISO 10816 NOMINAL]",
                "metric_val": 0.98,
                "color": (0, 229, 255, 255),
                "side": "right"
            },
            3: {
                "tag": "STATION 03 // COMMON RAIL INJECTION",
                "title": "1,600 BAR COMMON-RAIL DIRECT INJECTION",
                "subtitle": "BOSCH HIGH-PRESSURE FUEL DELIVERY & MICRO-INJECTORS",
                "specs": [
                    ("RAIL PRESSURE", "High-Pressure Accumulator Rail: 1,600 bar (23,200 PSI)"),
                    ("HP FUEL PUMP", "Engine-Driven Camshaft Radial-Piston High-Pressure Pump"),
                    ("INJECTORS", "Bosch Precision Multi-Hole Fast-Acting Solenoid Injectors"),
                    ("PILOT INJECTION", "Micro-Pilot Pre-Injection for Low Noise & Vibration"),
                    ("FUEL SPILL LINE", "Thermal Recirculation Cooling Circuit for Fuel Tank"),
                    ("PHM SENSOR", "CH-01 Fuel Rail Pressure & Fuel Delivery Temperature"),
                ],
                "metric_label": "RAIL PRESSURE: 1,600 bar LOCKED [BOSCH CRDi NOMINAL]",
                "metric_val": 0.99,
                "color": (255, 179, 0, 255),
                "side": "right"
            },
            4: {
                "tag": "STATION 04 // VGT TURBOCHARGER",
                "title": "VARIABLE GEOMETRY TURBOCHARGER (VGT)",
                "subtitle": "CLOSED-LOOP BOOST MAPPING & INTERCOOLING",
                "specs": [
                    ("TURBO TYPE", "Garrett Variable Nozzle Turbine (VNT/VGT) Technology"),
                    ("VANE ACTUATION", "High-Speed Electronic Stepper Actuator Control"),
                    ("BOOST PRESSURE", "Max Boost MAP: 2.25 bar (32.6 PSI absolute)"),
                    ("INTERCOOLER", "High-Efficiency Aluminum Cross-Flow Charge Air Cooler"),
                    ("EXHAUST SYSTEM", "Cast Stainless Exhaust Collector with Heat Blanket"),
                    ("PHM SENSOR", "CH-05 VGT Vane Position Resolver & Turbine Inlet Temp"),
                ],
                "metric_label": "VGT BOOST CONTROL: 2.25 bar [ELECTRONIC CLOSED LOOP]",
                "metric_val": 0.97,
                "color": (0, 229, 255, 255),
                "side": "right"
            },
            5: {
                "tag": "STATION 05 // DUAL LANE EECU",
                "title": "DUAL CHANNEL FADEC SYSTEM (EECU)",
                "subtitle": "SINGLE-LEVER POWER MANAGEMENT & BACKUP BATTERY",
                "specs": [
                    ("CONTROL CHANNELS", "Dual Lane EECU (Lane A / Lane B Active-Standby)"),
                    ("PILOT INTERFACE", "Single-Power Lever (FADEC Computes Prop & Fuel RPM)"),
                    ("GLOW PLUG UNIT", "Ceramic High-Temperature Quick-Start Glow Plug Controller"),
                    ("BACKUP POWER", "Dual Isolated Engine Backup Batteries for Emergency Power"),
                    ("SAFETY GATES", "Automatic Governor Fine-Pitch Stop Over-Speed Protection"),
                    ("PHM SENSOR", "CH-07 Dual-Lane EECU Sensor Cross-Check Bus"),
                ],
                "metric_label": "FADEC STATUS: EECU LANES A & B SYNCHRONIZED",
                "metric_val": 0.99,
                "color": (0, 230, 118, 255),
                "side": "left"
            },
            6: {
                "tag": "STATION 06 // PHM DIAGNOSTIC SUITE",
                "title": "DRDO ANUMAAN HEALTH MONITORING SUITE",
                "subtitle": "PROGNOSTICS & SYSTEM DIAGNOSTICS DIGITAL TWIN",
                "specs": [
                    ("CH-01 [RAIL PRESS]", "1,600 bar Common-Rail Fuel Injection Nominal"),
                    ("CH-02 [VIBRATION]", "0.09g Dual-Mass Flywheel Spectrum Nominal"),
                    ("CH-03 [TIT TEMP]", "740°C Turbine Inlet Temperature Nominal"),
                    ("CH-04 [COOLANT]", "98°C Liquid Engine Jacket Coolant Nominal"),
                    ("CH-05 [VGT POSITION]", "Electronic Vane Stepper: 68% Dynamic Modulation"),
                    ("CH-06 [FUEL FLOW]", "26.4 L/h Jet-A1 Cruise Fuel Consumption"),
                    ("DIAGNOSTIC MODEL", "Physics-Informed Causal Fault Tree Active"),
                    ("PROGNOSTICS", "Remaining Useful Life (RUL): > 2,400 Flight Hours"),
                ],
                "metric_label": "ALL 8 TELEMETRY CHANNELS SYNCHRONIZED & ONLINE",
                "metric_val": 1.0,
                "color": (0, 230, 118, 255),
                "side": "left"
            }
        }
    },

    "vrde_jayem_2_2l": {
        "title": "DRDO VRDE / JAYEM 2.2L",
        "subtitle": "INDIGENOUS 180 HP CRDi DIESEL // DRDO TAPAS UAV",
        "power_str": "2,179 CC | 180 HP @ 4,000 RPM | INDIGENOUS UAV TWIN",
        "source_blend": BLENDER_ROOT / "vrde_jayem_2_2l.blend",
        "out_blend": BLENDER_ROOT / "vrde_jayem_2_2l_showcase.blend",
        "output_dir": RENDERS_ROOT / "vrde_jayem_2_2l",
        "exclude_meshes": [],
        "telemetry_sim": {"rpm": 4000, "map": 2.35, "egt": 760, "cht": 96, "status": "NOMINAL"},
        "stations": {
            1: {
                "tag": "STATION 01 // OVERVIEW ARCHITECTURE",
                "title": "DRDO VRDE / JAYEM 2.2L CRDi",
                "subtitle": "INDIGENOUS INDIAN UAV TURBO DIESEL AERO ENGINE",
                "specs": [
                    ("ENGINE TYPE", "Inline-4, 4-Stroke Common-Rail Direct Injection Diesel"),
                    ("DISPLACEMENT", "2,179 cc (133 cu in) | Developed by VRDE & Jayem Automotives"),
                    ("MAX POWER", "132 kW (180 HP) @ 4,000 RPM (Take-Off Power Rating)"),
                    ("CONTINUOUS", "118 kW (160 HP) @ 3,750 RPM Max Continuous Rating"),
                    ("TARGET PLATFORMS", "TAPAS-BH-201 (Rustom-II), Archer-NG MALE UAV Platforms"),
                    ("FUEL COMPATIBILITY", "Aviation Turbine Fuel (ATF K-50 / Jet A-1 / High-Flash Diesel)"),
                    ("CYLINDER HEAD", "High-Thermal-Conductivity Aluminum Alloy Head Casting"),
                    ("MANAGEMENT", "DRDO Indigenous Dual-Channel Fault-Tolerant FADEC"),
                ],
                "metric_label": "SYSTEM HEALTH INDEX: 98.7% [NOMINAL]",
                "metric_val": 0.987,
                "color": (0, 229, 255, 255),
                "side": "left"
            },
            2: {
                "tag": "STATION 02 // POWER TRANSMISSION",
                "title": "AEROSPACE REDUCTION GEARBOX & GOVERNOR",
                "subtitle": "HIGH-STRENGTH PROPELLER DRIVE WITH TORSION DAMPER",
                "specs": [
                    ("GEAR RATIO", "Reduction Ratio i = 1.82 : 1 (Propeller RPM: 2,200)"),
                    ("PROP FLANGE", "Aerospace 8-Bolt PCD Heavy-Duty Propeller Hub Mount"),
                    ("DAMPER SYSTEM", "Multi-Stage Elastomeric & Spring Torsional Isolator"),
                    ("GOVERNOR DRIVE", "Direct Auxiliary Pad Drive for Constant-Speed Propeller"),
                    ("HOUSING", "A356-T6 Aerospace Aluminum Structural Gearbox Bell"),
                    ("PHM SENSOR", "CH-02 Gearbox Vibration & Output Shaft Torsional Load"),
                ],
                "metric_label": "GEARTRAIN VIBRATION: 0.11 g [ISO 10816 NOMINAL]",
                "metric_val": 0.97,
                "color": (0, 229, 255, 255),
                "side": "right"
            },
            3: {
                "tag": "STATION 03 // COMMON RAIL INJECTION",
                "title": "AEROSPACE-GRADE CRDi FUEL SYSTEM",
                "subtitle": "HIGH-PRESSURE ACCUMULATOR & HEAVY-FUEL RESISTANT INJECTORS",
                "specs": [
                    ("RAIL PRESSURE", "High-Pressure Rail: 1,800 bar (26,100 PSI) Operating"),
                    ("FUEL PUMP", "Engine-Driven Mechanical High-Pressure Radial Pump"),
                    ("HEAVY FUEL READY", "DLC-Coated Needles for ATF K-50 Lubricity Compensation"),
                    ("INJECTION TIMING", "Multi-Event Electronic Injection (Pre, Main, Post)"),
                    ("FUEL FILTRATION", "Dual Stage Coalescing Filter with Water-in-Fuel Sensor"),
                    ("PHM SENSOR", "CH-01 Fuel Rail Pressure & Fuel Delivery Delta-P"),
                ],
                "metric_label": "FUEL SYSTEM: 1,800 bar LOCKED [ATF COMPLIANT]",
                "metric_val": 0.98,
                "color": (255, 179, 0, 255),
                "side": "right"
            },
            4: {
                "tag": "STATION 04 // VGT TURBOCHARGER",
                "title": "VARIABLE GEOMETRY TURBOCHARGING",
                "subtitle": "ALTITUDE DENSITY MANAGEMENT & HEAT HARVESTING",
                "specs": [
                    ("TURBOCHARGER", "VGT with High-Temperature Inconel Turbine Wheel"),
                    ("ALTITUDE CEILING", "Maintains Cruise Boost up to 22,000 ft Operating Ceiling"),
                    ("WASTEGATE/VGT", "Fast Electronic Stepper Motor Variable Vane Controller"),
                    ("EXHAUST RUNNERS", "AISI 321 Stainless Steel Equal-Flow Tubular Manifold"),
                    ("CHARGE COOLING", "High-Effectiveness Air-to-Air Composite Intercooler"),
                    ("PHM SENSOR", "CH-05 Turbo RPM & Compressor Pressure Ratio"),
                ],
                "metric_label": "TURBINE EFFICIENCY: 82% [HIGH ALTITUDE BOOST NOMINAL]",
                "metric_val": 0.96,
                "color": (0, 229, 255, 255),
                "side": "right"
            },
            5: {
                "tag": "STATION 05 // DRDO INDIGENOUS FADEC",
                "title": "DRDO INDIGENOUS DUAL FADEC SYSTEM",
                "subtitle": "MIL-STD-1553B / CAN BUS AVIONICS INTEGRATION",
                "specs": [
                    ("CONTROLLER", "Dual-Channel Fault-Tolerant Redundant Digital Controller"),
                    ("AVIONICS BUS", "MIL-STD-1553B & CAN Aerospace Dual-Redundant Bus"),
                    ("SENSOR HARNESS", "Hermetically Sealed Mil-Spec Mil-DTL-38999 Connectors"),
                    ("FAIL-SAFE", "Autonomous Single-Lane Reversionary Mode with Zero Glitch"),
                    ("ALTITUDE MAPPING", "Fully Calibrated High-Altitude Flight Envelope Tables"),
                    ("PHM SENSOR", "CH-07 FADEC Channel Integrity & Watchdog Status"),
                ],
                "metric_label": "FADEC STATUS: DRDO DUAL CHANNEL ONLINE [ZERO FAULTS]",
                "metric_val": 0.99,
                "color": (0, 230, 118, 255),
                "side": "left"
            },
            6: {
                "tag": "STATION 06 // PHM DIAGNOSTIC SUITE",
                "title": "DRDO ANUMAAN HEALTH MONITORING SUITE",
                "subtitle": "PROGNOSTICS & SYSTEM DIAGNOSTICS DIGITAL TWIN",
                "specs": [
                    ("CH-01 [RAIL PRESS]", "1,800 bar High-Pressure Common-Rail Nominal"),
                    ("CH-02 [VIBRATION]", "0.11g Aerospace Gearbox Spectrum Nominal"),
                    ("CH-03 [TIT TEMP]", "760°C Inconel Turbine Inlet Temperature"),
                    ("CH-04 [COOLANT]", "96°C Liquid Cylinder Jacket Temperature"),
                    ("CH-05 [VGT MAP]", "2.35 bar Absolute Boost Manifold Pressure"),
                    ("CH-06 [FUEL FLOW]", "28.2 L/h ATF K-50 Cruise Consumption Nominal"),
                    ("DIAGNOSTIC MODEL", "Physics-Informed Causal Fault Tree Active"),
                    ("PROGNOSTICS", "Remaining Useful Life (RUL): > 2,000 Flight Hours"),
                ],
                "metric_label": "ALL 12 TELEMETRY CHANNELS SYNCHRONIZED & ONLINE",
                "metric_val": 1.0,
                "color": (0, 230, 118, 255),
                "side": "left"
            }
        }
    }
}


# ──────────────────────────────────────────────────────────────────────
# Step 1: Blender 3D Scene Setup & Render Script Generator
# ──────────────────────────────────────────────────────────────────────

def generate_blender_script(engine_id, cfg):
    """Generate the Blender python script to build camera animation, export tracking, and render 3D frames."""
    source_blend = str(cfg["source_blend"]).replace("\\", "/")
    out_blend = str(cfg["out_blend"]).replace("\\", "/")
    out_dir = str(cfg["output_dir"]).replace("\\", "/")
    frames_dir = f"{out_dir}/cinematic_showcase"
    stations_dir = f"{out_dir}/stations"
    tracking_json = f"{out_dir}/tracking_data.json"
    exclude_list = json.dumps(cfg["exclude_meshes"])

    script = f'''import bpy
import bmesh
import mathutils
from bpy_extras.object_utils import world_to_camera_view
import math
import os
import json
from pathlib import Path

print("=== STARTING BLENDER SHOWCASE PIPELINE FOR {engine_id} ===")

# Open source blend
bpy.ops.wm.open_mainfile(filepath="{source_blend}")
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 480
scene.render.fps = 24

# Ensure output directories
for p in ["{frames_dir}", "{stations_dir}"]:
    os.makedirs(p, exist_ok=True)

# Remove excluded objects
exclude_meshes = {exclude_list}
for ex in exclude_meshes:
    o = scene.objects.get(ex)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)
        print(f"  Removed excluded mesh: {{ex}}")

# Compute bounding box & radius
mesh_objs = [o for o in scene.objects if o.type == 'MESH']
mn = mathutils.Vector((1e9, 1e9, 1e9))
mx = mathutils.Vector((-1e9, -1e9, -1e9))
for o in mesh_objs:
    for corner in o.bound_box:
        wp = o.matrix_world @ mathutils.Vector(corner)
        mn.x = min(mn.x, wp.x); mn.y = min(mn.y, wp.y); mn.z = min(mn.z, wp.z)
        mx.x = max(mx.x, wp.x); mx.y = max(mx.y, wp.y); mx.z = max(mx.z, wp.z)

center = (mn + mx) / 2.0
dim = mx - mn
radius = dim.length / 2.0
print(f"  Engine Center: ({{center.x:.2f}}, {{center.y:.2f}}, {{center.z:.2f}})")
print(f"  Dimensions:    ({{dim.x:.2f}}, {{dim.y:.2f}}, {{dim.z:.2f}})")
print(f"  Radius:        {{radius:.2f}}")

# Clean existing lights & cameras
for o in list(scene.objects):
    if o.type in ('LIGHT', 'CAMERA') or o.name.startswith("Showcase_"):
        bpy.data.objects.remove(o, do_unlink=True)

# Dark Aerospace World
if not scene.world:
    scene.world = bpy.data.worlds.new("Showcase_World")
scene.world.use_nodes = True
wnodes = scene.world.node_tree.nodes
wnodes.clear()
wo = wnodes.new("ShaderNodeOutputWorld")
wb = wnodes.new("ShaderNodeBackground")
wb.inputs["Color"].default_value = (0.012, 0.018, 0.030, 1.0)
wb.inputs["Strength"].default_value = 0.2
scene.world.node_tree.links.new(wb.outputs["Background"], wo.inputs["Surface"])

# 4-Point Studio Lighting Rig
def add_sun(name, energy, color, rot_euler):
    data = bpy.data.lights.new(name=name, type='SUN')
    data.energy = energy
    data.color = color
    data.angle = math.radians(3.0)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.rotation_euler = rot_euler
    return obj

add_sun("Showcase_Key", 4.8, (1.0, 0.97, 0.93), (math.radians(55), math.radians(15), math.radians(-40)))
add_sun("Showcase_Fill", 2.6, (0.75, 0.88, 1.0), (math.radians(45), math.radians(-25), math.radians(130)))
add_sun("Showcase_Rim", 4.2, (0.0, 0.85, 1.0), (math.radians(25), math.radians(10), math.radians(170)))
add_sun("Showcase_Bottom", 1.2, (0.9, 0.9, 0.9), (math.radians(-70), 0, 0))

# Dark Reflective Floor Stage
bpy.ops.mesh.primitive_circle_add(
    vertices=64, radius=radius * 3.5,
    fill_type='NGON',
    location=(center.x, center.y, center.z - radius * 0.55)
)
floor = bpy.context.active_object
floor.name = "Showcase_Floor"
fmat = bpy.data.materials.new("M_Showcase_Floor")
fmat.use_nodes = True
bsdf = fmat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.025, 0.03, 0.04, 1.0)
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = 0.7
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 0.15
floor.data.materials.append(fmat)

# Camera Setup
cam_data = bpy.data.cameras.new("Showcase_Camera")
cam_data.lens = 45.0
cam_data.clip_start = max(0.01, radius * 0.01)
cam_data.clip_end = max(1000.0, radius * 100.0)
cam_data.dof.use_dof = False
cam_obj = bpy.data.objects.new("Showcase_Camera", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

tgt = bpy.data.objects.new("Showcase_Cam_Target", None)
scene.collection.objects.link(tgt)
tgt.location = center

con = cam_obj.constraints.new('TRACK_TO')
con.target = tgt
con.track_axis = 'TRACK_NEGATIVE_Z'
con.up_axis = 'UP_Y'

# Orbit Helper
def orbit_pt(r, ang_deg, z):
    rad = math.radians(ang_deg)
    return mathutils.Vector((center.x + r * math.cos(rad), center.y + r * math.sin(rad), z))

orbit_wide = radius * 2.2
orbit_mid = radius * 1.55
orbit_close = radius * 1.35
orbit_pull = radius * 2.6

# 6 Dynamic Stations Choreography across 480 frames
stations = [
    # St1: Overview (F1-80)
    (1,   orbit_wide, -40,  center.z + radius * 0.50, mathutils.Vector((0, 0, 0)), 36),
    (40,  orbit_wide, -25,  center.z + radius * 0.45, mathutils.Vector((0, 0, 0)), 38),
    (80,  orbit_wide,   0,  center.z + radius * 0.35, mathutils.Vector((0, 0, 0)), 40),

    # St2: Prop Flange & Gearbox (F81-160)
    (100, orbit_mid,   20,  center.z + radius * 0.20, mathutils.Vector((radius * 0.25, 0, radius * 0.1)), 46),
    (140, orbit_close, 35,  center.z + radius * 0.15, mathutils.Vector((radius * 0.25, 0, radius * 0.1)), 48),
    (160, orbit_mid,   55,  center.z + radius * 0.15, mathutils.Vector((radius * 0.2, 0, radius * 0.1)), 46),

    # St3: Port Induction / Fuel System (F161-240)
    (180, orbit_mid,   90,  center.z + radius * 0.25, mathutils.Vector((-radius * 0.1, radius * 0.15, radius * 0.1)), 42),
    (220, orbit_close, 120, center.z + radius * 0.30, mathutils.Vector((-radius * 0.1, radius * 0.15, radius * 0.1)), 44),
    (240, orbit_mid,   150, center.z + radius * 0.20, mathutils.Vector((-radius * 0.1, radius * 0.1, radius * 0.1)), 42),

    # St4: Underbelly Exhaust / Heat System (F241-320)
    (260, orbit_mid,   185, center.z - radius * 0.15, mathutils.Vector((-radius * 0.15, 0, -radius * 0.15)), 40),
    (300, orbit_close, 215, center.z - radius * 0.20, mathutils.Vector((-radius * 0.15, 0, -radius * 0.15)), 42),
    (320, orbit_mid,   250, center.z - radius * 0.10, mathutils.Vector((-radius * 0.15, 0, -radius * 0.1)), 38),

    # St5: Starboard Turbo / Electrical System (F321-400)
    (340, orbit_mid,   280, center.z + radius * 0.05, mathutils.Vector((-radius * 0.15, -radius * 0.1, 0)), 42),
    (380, orbit_close, 300, center.z + radius * 0.10, mathutils.Vector((-radius * 0.15, -radius * 0.1, 0)), 45),
    (400, orbit_mid,   325, center.z + radius * 0.25, mathutils.Vector((0, 0, 0)), 40),

    # St6: Pull-out Master Drone Overview (F401-480)
    (430, orbit_wide,  340, center.z + radius * 0.65, mathutils.Vector((0, 0, 0)), 34),
    (460, orbit_pull,  355, center.z + radius * 0.90, mathutils.Vector((0, 0, 0)), 30),
    (480, orbit_pull,  370, center.z + radius * 1.05, mathutils.Vector((0, 0, 0)), 28),
]

for frame, orb_r, angle, cam_z, tgt_offset, lens in stations:
    cam_pos = orbit_pt(orb_r, angle, cam_z)
    cam_obj.location = cam_pos
    cam_obj.keyframe_insert(data_path="location", frame=frame)
    tgt.location = center + tgt_offset
    tgt.keyframe_insert(data_path="location", frame=frame)
    cam_data.lens = lens
    cam_data.keyframe_insert(data_path="lens", frame=frame)

# Set Bezier interpolation
def set_bezier(animated_obj):
    if not animated_obj.animation_data or not animated_obj.animation_data.action:
        return
    act = animated_obj.animation_data.action
    if hasattr(act, 'layers'):
        for l in act.layers:
            for s in l.strips:
                if hasattr(s, 'channelbags'):
                    for b in s.channelbags:
                        for fc in b.fcurves:
                            for kf in fc.keyframe_points:
                                kf.interpolation = 'BEZIER'
                                kf.handle_left_type = 'AUTO_CLAMPED'
                                kf.handle_right_type = 'AUTO_CLAMPED'

set_bezier(cam_obj)
set_bezier(tgt)
if cam_data.animation_data and cam_data.animation_data.action:
    set_bezier(cam_data)

# Configure Render
avail = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
if "BLENDER_EEVEE_NEXT" in avail:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
elif "BLENDER_EEVEE" in avail:
    scene.render.engine = "BLENDER_EEVEE"
else:
    scene.render.engine = avail[0]

scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.compression = 15
scene.render.film_transparent = False

try:
    if hasattr(scene.eevee, 'taa_render_samples'):
        scene.eevee.taa_render_samples = 64
    if hasattr(scene.eevee, 'use_bloom'):
        scene.eevee.use_bloom = True
except Exception:
    pass

# Save Showcase Blend
bpy.ops.wm.save_as_mainfile(filepath="{out_blend}")
print(f"  [SAVED BLEND] -> {out_blend}")

# Compute 3D Tracking Matrix
anchors = {{
    "engine_core": center,
    "gearbox": center + mathutils.Vector((radius * 0.35, 0, radius * 0.15)),
    "induction": center + mathutils.Vector((-radius * 0.15, radius * 0.2, radius * 0.15)),
    "exhaust": center + mathutils.Vector((-radius * 0.2, 0, -radius * 0.2)),
    "turbo": center + mathutils.Vector((-radius * 0.25, -radius * 0.15, -radius * 0.1)),
}}

tracking = {{}}
for f in range(1, 481):
    scene.frame_set(f)
    fkey = f"frame_{{f:04d}}"
    tracking[fkey] = {{}}
    for aname, apt in anchors.items():
        co = world_to_camera_view(scene, cam_obj, apt)
        px = int(co.x * scene.render.resolution_x)
        py = int((1.0 - co.y) * scene.render.resolution_y)
        vis = bool(co.z > 0 and 0.0 <= co.x <= 1.0 and 0.0 <= co.y <= 1.0)
        tracking[fkey][aname] = {{
            "screen_x": px,
            "screen_y": py,
            "depth": float(co.z),
            "visible": vis
        }}

with open("{tracking_json}", "w") as fp:
    json.dump(tracking, fp, indent=2)
print(f"  [SAVED TRACKING] -> {tracking_json}")

# Render 6 Station Beauty Stills
station_frames = [
    ("01_architecture_overview", 40),
    ("02_gearbox_reduction", 140),
    ("03_induction_airbox", 220),
    ("04_thermal_exhaust", 300),
    ("05_turbo_wastegate", 380),
    ("06_telemetry_sensor_suite", 460),
]

print("\\n=== Rendering 6 Station Beauty Stills ===")
for sname, frame in station_frames:
    scene.frame_set(frame)
    out_path = f"{stations_dir}/station_{{sname}}.png"
    scene.render.filepath = out_path
    print(f"  Rendering Station '{{sname}}' @ Frame {{frame}}...")
    bpy.ops.render.render(write_still=True)
    fsize = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    print(f"    -> {{out_path}} ({{fsize:,}} bytes)")

# Render Animation Frames (120 frames, step=4)
print("\\n=== Rendering Animation Frames (120 frames, step=4) ===")
rendered = 0
for f in range(1, 481, 4):
    scene.frame_set(f)
    out_path = f"{frames_dir}/frame_{{f:04d}}.png"
    scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    rendered += 1
    if rendered % 25 == 0 or f == 1:
        fsize = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        print(f"  Rendered frame {{f}}/480 ({{rendered}} total, {{fsize:,}} bytes)")

print(f"  [OK] {{rendered}} frames rendered to {frames_dir}")
print("=== BLENDER PIPELINE FINISHED ===")
'''
    return script


# ──────────────────────────────────────────────────────────────────────
# Step 2: Aerospace HUD Motion Graphics Compositor
# ──────────────────────────────────────────────────────────────────────

def composite_engine_hud(engine_id, cfg):
    """Composite aerospace HUD onto rendered frames and beauty stills for the given engine."""
    print(f"\n" + "=" * 70)
    print(f" COMPOSITING AEROSPACE HUD FOR: {cfg['title']}")
    print("=" * 70)

    out_dir = cfg["output_dir"]
    frames_dir = out_dir / "cinematic_showcase"
    stations_dir = out_dir / "stations"
    tracking_json = out_dir / "tracking_data.json"
    mp4_out = out_dir / f"{engine_id}_technical_showcase.mp4"
    contact_out = out_dir / f"{engine_id}_showcase_contact_sheet.png"

    tracking = {}
    if tracking_json.exists():
        try:
            with open(tracking_json, "r") as f:
                tracking = json.load(f)
        except Exception as e:
            print("  Notice: Could not load tracking JSON:", e)

    # Fonts
    try:
        font_title = ImageFont.truetype("bahnschrift.ttf", 24)
        font_subtitle = ImageFont.truetype("bahnschrift.ttf", 16)
        font_bold = ImageFont.truetype("segoeuib.ttf", 15)
        font_body = ImageFont.truetype("segoeui.ttf", 14)
        font_telemetry = ImageFont.truetype("consola.ttf", 14)
        font_telemetry_sm = ImageFont.truetype("consola.ttf", 12)
        font_telemetry_xs = ImageFont.truetype("consola.ttf", 10)
    except Exception:
        font_title = font_subtitle = font_bold = font_body = font_telemetry = font_telemetry_sm = font_telemetry_xs = ImageFont.load_default()

    CYAN = (0, 229, 255, 255)
    CYAN_SOFT = (0, 229, 255, 180)
    CYAN_GLOW = (0, 229, 255, 60)
    AMBER = (255, 179, 0, 255)
    GREEN = (0, 230, 118, 255)
    WHITE = (245, 250, 255, 255)
    MUTED = (165, 185, 205, 220)
    HEADER_BG = (8, 14, 24, 215)

    def draw_hud(img, frame_num):
        W, H = img.size
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        margin = 40

        # Corner reticles
        def corner(x, y, dx, dy, s=35):
            draw.line([(x, y), (x + dx * s, y)], fill=CYAN_SOFT, width=2)
            draw.line([(x, y), (x, y + dy * s)], fill=CYAN_SOFT, width=2)

        corner(margin, margin, 1, 1)
        corner(W - margin, margin, -1, 1)
        corner(margin, H - margin, 1, -1)
        corner(W - margin, H - margin, -1, -1)

        # Top Aerospace Banner
        bw, bh = W - 2 * margin - 80, 56
        bx, by = margin + 40, margin - 15
        draw.rectangle([(bx, by), (bx + bw, by + bh)], fill=HEADER_BG, outline=(0, 229, 255, 90), width=1)
        draw.text((bx + 20, by + 8), f"DRDO // ANUMAAN DIGITAL TWIN PROGRAM", fill=CYAN, font=font_subtitle)
        draw.text((bx + 20, by + 29), f"{cfg['title']} | {cfg['power_str']}", fill=MUTED, font=font_telemetry_sm)

        # Telemetry live indicators
        tx = bx + bw - 530
        sim = cfg["telemetry_sim"]
        rpm_val = sim["rpm"] + int(12 * math.sin(frame_num * 0.1))
        map_val = sim["map"] + 0.01 * math.sin(frame_num * 0.08)
        egt_val = sim["egt"] + int(3 * math.sin(frame_num * 0.05))
        cht_val = sim["cht"] + int(2 * math.cos(frame_num * 0.04))
        metrics = [
            ("ENGINE RPM", f"{rpm_val:,}", GREEN),
            ("MAP BOOST", f"{map_val:.2f} bar", AMBER),
            ("EXHAUST EGT", f"{egt_val}°C", WHITE),
            ("COOLANT CHT", f"{cht_val}°C", WHITE),
            ("PHM STATUS", sim["status"], GREEN),
        ]
        for l, v, c in metrics:
            draw.text((tx, by + 8), l, fill=MUTED, font=font_telemetry_xs)
            draw.text((tx, by + 24), v, fill=c, font=font_telemetry)
            tx += 105

        # Bottom Station Ribbon
        bar_y = H - margin - 22
        st_names = ["01 ARCHITECTURE", "02 GEARBOX", "03 INDUCTION", "04 EXHAUST", "05 TURBO / FADEC", "06 TELEMETRY SUITE"]
        st_idx = min(6, max(1, (frame_num - 1) // 80 + 1))
        meta = cfg["stations"][st_idx]

        pw = (W - 2 * margin - 100) // len(st_names)
        for i, sname in enumerate(st_names):
            px = margin + 50 + i * pw
            act = (i == (st_idx - 1))
            bg = (0, 229, 255, 45) if act else (12, 18, 28, 160)
            bdr = CYAN if act else (40, 60, 85, 180)
            draw.rectangle([(px, bar_y - 12), (px + pw - 8, bar_y + 16)], fill=bg, outline=bdr, width=1)
            draw.text((px + 12, bar_y - 6), sname, fill=CYAN if act else MUTED, font=font_telemetry_sm)
            if act:
                draw.line([(px + 4, bar_y + 14), (px + pw - 12, bar_y + 14)], fill=CYAN, width=2)

        # Alpha transition
        st_start = (st_idx - 1) * 80 + 1
        st_local = frame_num - st_start
        if st_local < 15:
            alpha = st_local / 15.0
        elif st_local > 70:
            alpha = max(0.0, (80 - st_local) / 10.0)
        else:
            alpha = 1.0

        if alpha > 0.05:
            # Tracking anchor point
            fkey = f"frame_{frame_num:04d}"
            ftrack = tracking.get(fkey, {})
            anchor_key = list(ftrack.keys())[min(st_idx - 1, len(ftrack) - 1)] if ftrack else None
            anch_info = ftrack.get(anchor_key, {}) if anchor_key else {}
            if "screen_x" in anch_info and anch_info.get("visible", True):
                ax, ay = anch_info["screen_x"], anch_info["screen_y"]
            else:
                defaults = {1: (960, 520), 2: (1260, 480), 3: (980, 320), 4: (900, 600), 5: (800, 540), 6: (960, 500)}
                ax, ay = defaults.get(st_idx, (960, 540))

            card_w, card_h = 510, 320
            card_y = 150
            side = meta.get("side", "left")
            if ax > W * 0.55:
                card_x = margin + 50
                elbow_x = card_x + card_w + 50
            elif ax < W * 0.45:
                card_x = W - margin - 50 - card_w
                elbow_x = card_x - 50
            else:
                if side == "left":
                    card_x = margin + 50
                    elbow_x = card_x + card_w + 50
                else:
                    card_x = W - margin - 50 - card_w
                    elbow_x = card_x - 50

            elbow_y = max(card_y + 40, min(card_y + card_h - 40, ay - 40))

            c_color = meta["color"]
            r_c = (*c_color[:3], int(255 * alpha))

            # Reticle
            draw.ellipse([(ax - 12, ay - 12), (ax + 12, ay + 12)], outline=r_c, width=2)
            draw.ellipse([(ax - 4, ay - 4), (ax + 4, ay + 4)], fill=r_c)
            draw.line([(ax - 20, ay), (ax - 14, ay)], fill=r_c, width=1)
            draw.line([(ax + 14, ay), (ax + 20, ay)], fill=r_c, width=1)
            draw.line([(ax, ay - 20), (ax, ay - 14)], fill=r_c, width=1)
            draw.line([(ax, ay + 14), (ax, ay + 20)], fill=r_c, width=1)

            # Leader Line
            c_conn = card_x + card_w if card_x < ax else card_x
            draw.line([(ax, ay), (elbow_x, elbow_y)], fill=r_c, width=2)
            draw.line([(elbow_x, elbow_y), (c_conn, elbow_y)], fill=r_c, width=2)
            draw.ellipse([(elbow_x - 3, elbow_y - 3), (elbow_x + 3, elbow_y + 3)], fill=r_c)

            # HUD Card
            card_bg = (10, 16, 26, int(225 * alpha))
            card_bdr = (*c_color[:3], int(180 * alpha))
            draw.rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], fill=card_bg, outline=card_bdr, width=2)
            # Header strip
            hdr_h = 36
            draw.rectangle([(card_x, card_y), (card_x + card_w, card_y + hdr_h)], fill=(*c_color[:3], int(40 * alpha)))
            draw.line([(card_x, card_y + hdr_h), (card_x + card_w, card_y + hdr_h)], fill=card_bdr, width=1)
            draw.text((card_x + 18, card_y + 8), meta["tag"], fill=r_c, font=font_subtitle)

            # Title
            draw.text((card_x + 18, card_y + hdr_h + 8), meta["title"], fill=WHITE, font=font_bold)
            draw.text((card_x + 18, card_y + hdr_h + 28), meta["subtitle"], fill=MUTED, font=font_telemetry_xs)

            # Specs
            cy = card_y + hdr_h + 48
            for label, val in meta["specs"]:
                draw.text((card_x + 18, cy), label, fill=r_c, font=font_telemetry_xs)
                draw.text((card_x + 145, cy), val, fill=WHITE, font=font_body)
                cy += 21

            # Status bar
            bar_btm = card_y + card_h - 14
            bar_top = card_y + card_h - 24
            bar_w = card_w - 36
            draw.rectangle([(card_x + 18, bar_top), (card_x + 18 + bar_w, bar_btm)], fill=(*c_color[:3], int(30 * alpha)), outline=(*c_color[:3], int(90 * alpha)))
            fill_w = int(bar_w * meta["metric_val"])
            draw.rectangle([(card_x + 18, bar_top), (card_x + 18 + fill_w, bar_btm)], fill=(*GREEN[:3], int(220 * alpha)))
            draw.text((card_x + 18, bar_top - 18), meta["metric_label"], fill=GREEN, font=font_telemetry_sm)

        # Station 6 multi-sensor nodes
        if st_idx == 6 and alpha > 0.3:
            s_nodes = [
                ("S1: CH-01 NOMINAL", (120, -50), AMBER),
                ("S2: CH-02 OPTIMAL", (100, 40), GREEN),
                ("S3: CH-03 BALANCED", (-110, 60), CYAN),
                ("S4: CH-04 SYNCHRONIZED", (-120, -50), AMBER),
            ]
            for sname, offset, scolor in s_nodes:
                sx, sy = W // 2 + offset[0] * 2, H // 2 + offset[1] * 2
                draw.ellipse([(sx - 4, sy - 4), (sx + 4, sy + 4)], fill=scolor)
                draw.ellipse([(sx - 8, sy - 8), (sx + 8, sy + 8)], outline=scolor, width=1)
                tw, th = 145, 22
                draw.rectangle([(sx + 15, sy - 11), (sx + 15 + tw, sy + 11)], fill=(8, 14, 24, 210), outline=scolor, width=1)
                draw.line([(sx, sy), (sx + 15, sy)], fill=scolor, width=1)
                draw.text((sx + 20, sy - 6), sname, fill=scolor, font=font_telemetry_sm)

        return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # 1. Composite Station Stills
    print("  [1/4] Compositing 6 Station Beauty Stills...")
    station_files = [
        ("station_01_architecture_overview.png", 40),
        ("station_02_gearbox_reduction.png", 140),
        ("station_03_induction_airbox.png", 220),
        ("station_04_thermal_exhaust.png", 300),
        ("station_05_turbo_wastegate.png", 380),
        ("station_06_telemetry_sensor_suite.png", 460),
    ]
    for fname, fnum in station_files:
        p = stations_dir / fname
        if p.exists():
            im = Image.open(p)
            comp = draw_hud(im, fnum)
            comp.save(p, quality=95)

    # 2. Composite Animation Frames
    print("  [2/4] Compositing 120 Animation Frames...")
    ffiles = sorted(frames_dir.glob("frame_*.png"))
    for idx, fp in enumerate(ffiles):
        fnum = int(fp.stem.split("_")[1])
        im = Image.open(fp)
        comp = draw_hud(im, fnum)
        comp.save(fp, quality=95)
        if (idx + 1) % 40 == 0 or idx == 0:
            print(f"    Composited frame {idx+1}/{len(ffiles)}")

    # 3. Encode MP4 Video via OpenCV
    print(f"  [3/4] Encoding Master MP4 Video via OpenCV -> {mp4_out.name}")
    first = cv2.imread(str(ffiles[0]))
    h, w, _ = first.shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(mp4_out), fourcc, 24.0, (w, h))
    for fp in ffiles:
        img = cv2.imread(str(fp))
        if img is not None:
            writer.write(img)
            writer.write(img)  # 2x hold = 10 sec @ 24fps
    writer.release()
    fsize = mp4_out.stat().st_size if mp4_out.exists() else 0
    print(f"    [MP4 OK] {fsize:,} bytes")

    # 4. Generate Master Contact Sheet
    print(f"  [4/4] Building Master Contact Sheet -> {contact_out.name}")
    cols, rows = 3, 2
    cw, ch = 640, 360
    hh = 70
    sheet = Image.new("RGB", (cols * cw, rows * ch + hh), (8, 12, 20))
    sdraw = ImageDraw.Draw(sheet)
    sdraw.rectangle([(0, 0), (cols * cw, hh)], fill=(5, 8, 14))
    sdraw.line([(0, hh), (cols * cw, hh)], fill=(0, 229, 255, 120), width=2)
    sdraw.text((30, 16), f"DRDO ANUMAAN DIGITAL TWIN // {cfg['title']} SHOWCASE", fill=CYAN, font=font_title)
    sdraw.text((30, 44), f"6-STATION AEROSPACE CINEMATIC REEL | {cfg['power_str']}", fill=MUTED, font=font_telemetry_sm)

    labels = [
        "STATION 01: OVERVIEW ARCHITECTURE",
        "STATION 02: GEARBOX & PROP FLANGE",
        "STATION 03: INDUCTION & FUEL SYSTEM",
        "STATION 04: THERMAL EXHAUST MANIFOLD",
        "STATION 05: TURBO / FADEC MANAGEMENT",
        "STATION 06: DIGITAL TWIN TELEMETRY",
    ]
    for idx, (sfname, _) in enumerate(station_files):
        sfp = stations_dir / sfname
        if not sfp.exists():
            continue
        r, c = idx // cols, idx % cols
        x, y = c * cw, r * ch + hh
        im = Image.open(sfp).resize((cw, ch), Image.Resampling.LANCZOS)
        sheet.paste(im, (x, y))
        sdraw.rectangle([(x + 10, y + 10), (x + cw - 10, y + 36)], fill=(8, 14, 24, 200), outline=(0, 229, 255, 120), width=1)
        sdraw.text((x + 20, y + 14), labels[idx], fill=CYAN, font=font_bold)

    sheet.save(str(contact_out), quality=95)
    print(f"    [CONTACT SHEET OK] {contact_out.stat().st_size:,} bytes")
    print(f" [SUCCESS] SHOWCASE COMPLETE FOR {engine_id}!")


# ──────────────────────────────────────────────────────────────────────
# Main Dispatcher
# ──────────────────────────────────────────────────────────────────────

def run_engine_showcase(engine_id, skip_blender=False):
    if engine_id not in ENGINE_CONFIGS:
        print(f"ERROR: Unknown engine '{engine_id}'. Available: {list(ENGINE_CONFIGS.keys())}")
        return False

    cfg = ENGINE_CONFIGS[engine_id]
    print("\n" + "=" * 75)
    print(f" LAUNCHING SHOWCASE PIPELINE FOR: {engine_id.upper()}")
    print("=" * 75)

    if not skip_blender:
        # 1. Generate Blender Script
        b_script_path = REPO_ROOT / f"scratch_render_{engine_id}.py"
        b_script_content = generate_blender_script(engine_id, cfg)
        with open(b_script_path, "w") as f:
            f.write(b_script_content)

        # 2. Run Blender Render
        print(f"\n[BLENDER] Running 3D render pipeline via {BLENDER_BIN}...")
        cmd = [BLENDER_BIN, "--background", "--python", str(b_script_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[BLENDER ERROR] Code {res.returncode}")
            if res.stderr:
                print("STDERR:", res.stderr[-500:])
            return False
        print("  [BLENDER OK] 3D render completed successfully.")

        # Clean temporary scratch script
        if b_script_path.exists():
            os.remove(b_script_path)
    else:
        print("\n[BLENDER] Skipped 3D render stage (--skip-blender). Proceeding to HUD compositing...")

    # 3. Composite Aerospace HUD & Video
    composite_engine_hud(engine_id, cfg)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal ANUMAAN Engine Showcase Generator")
    parser.add_argument("--engine", type=str, choices=list(ENGINE_CONFIGS.keys()) + ["all"], default="all",
                        help="Engine ID to process, or 'all' to process all 4 other engines")
    parser.add_argument("--skip-blender", action="store_true",
                        help="Skip 3D Blender rendering stage and run only HUD compositing")
    args = parser.parse_args()

    if args.engine == "all":
        target_engines = ["rotax_912is", "rotax_915is", "austro_ae300", "vrde_jayem_2_2l"]
        for eng in target_engines:
            run_engine_showcase(eng, skip_blender=args.skip_blender)
    else:
        run_engine_showcase(args.engine, skip_blender=args.skip_blender)

