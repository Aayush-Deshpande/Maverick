"""
Multi-Engine 3D Rendering Pipeline — ANUMAAN
Renders high-resolution beauty shots and fault visualization stills for all 5 UAV engines:
- Rotax 912 iS (Naturally Aspirated Spark Ignition)
- Rotax 914 (Turbocharged Spark Ignition)
- Rotax 915 iS (Turbocharged Intercooled Spark Ignition)
- Austro AE300 / AE330 (Common-Rail Turbo Diesel)
- VRDE / JAYEM 2.2L (Indigenous 180 hp CRDi Turbo Diesel)

Renders both HEALTHY state and FAULT INJECTION states with emissive heatmaps and precision camera framing.
"""

import bpy
import mathutils
import math
import os
import sys
from pathlib import Path

REPO_ROOT = Path(r"e:\backup-llm\backup-no-llm\3d_engine")
RENDERS_ROOT = REPO_ROOT / "assets" / "renders" / "engines"

ENGINE_RENDER_SPECS = {
    "rotax_912is": {
        "blend_file": REPO_ROOT / "assets" / "blender" / "rotax_912_is_sport.blend",
        "output_dir": RENDERS_ROOT / "rotax_912is",
        "default_center": mathutils.Vector((1.93, 61.65, -35.32)),
        "shots": [
            {
                "name": "01_healthy_hero",
                "fault": None,
                "cam_pos": mathutils.Vector((-160.0, -140.0, 60.0)),
                "target": mathutils.Vector((1.93, 61.65, -35.32)),
                "lens": 50.0,
            },
            {
                "name": "02_fault_cyl2_overheat",
                "fault": "CYLINDER_2_OVERHEAT",
                "target_parts": [
                    "Covers_Theme_M_PlasticTheme_0",
                    "Covers_Theme_M_PlasticGreen_0",
                    "Cooling_Air_Baffle_M_PlasticWhite_0",
                ],
                "cam_pos": mathutils.Vector((-95.0, -40.0, 30.0)),
                "target": mathutils.Vector((-22.0, 44.0, -10.0)),
                "lens": 65.0,
                "color": (1.0, 0.05, 0.02, 1.0),
                "emission_strength": 12.0,
            },
            {
                "name": "03_fault_injector_clog",
                "fault": "INJECTOR_1_CLOG",
                "target_parts": [
                    "Rotax_912i_Base_M_PlasticGreen_0",
                    "Rotax_912i_Base_M_Steel_0",
                    "Rotax_912i_Base_M_PlasticCable_0",
                ],
                "cam_pos": mathutils.Vector((1.0, -65.0, 45.0)),
                "target": mathutils.Vector((1.06, 25.69, -8.0)),
                "lens": 70.0,
                "color": (1.0, 0.4, 0.0, 1.0),
                "emission_strength": 10.0,
            },
        ],
    },
    "rotax_914": {
        "blend_file": REPO_ROOT / "assets" / "blender" / "rotax_912_is_sport.blend",
        "output_dir": RENDERS_ROOT / "rotax_914",
        "default_center": mathutils.Vector((1.93, 61.65, -35.32)),
        "shots": [
            {
                "name": "01_healthy_turbo_hero",
                "fault": None,
                "cam_pos": mathutils.Vector((140.0, -150.0, 40.0)),
                "target": mathutils.Vector((1.93, 61.65, -35.32)),
                "lens": 50.0,
            },
            {
                "name": "02_fault_wastegate_stuck_open",
                "fault": "TURBO_WASTEGATE_LEAK",
                "target_parts": [
                    "Exhaust_System_M_SteelDark_0",
                    "Exhaust_System_M_Steel_0",
                    "Exhaust_System_M_Chrome_0",
                ],
                "cam_pos": mathutils.Vector((85.0, -35.0, -20.0)),
                "target": mathutils.Vector((6.68, 38.87, -45.78)),
                "lens": 60.0,
                "color": (1.0, 0.15, 0.0, 1.0),
                "emission_strength": 14.0,
            },
            {
                "name": "03_fault_oil_pressure_loss",
                "fault": "OIL_PRESSURE_DECAY",
                "target_parts": [
                    "Oil_Tank_M_Steel_0",
                    "Oil_Tank_M_Labels_0",
                    "Oil_Tank_M_Cobalt_0",
                    "Oil_Tank_M_PlasticBlack_0",
                ],
                "cam_pos": mathutils.Vector((-120.0, 180.0, 25.0)),
                "target": mathutils.Vector((-24.76, 105.82, -20.31)),
                "lens": 65.0,
                "color": (0.9, 0.0, 0.1, 1.0),
                "emission_strength": 12.0,
            },
        ],
    },
    "rotax_915is": {
        "blend_file": REPO_ROOT / "assets" / "blender" / "rotax_912_is_sport.blend",
        "output_dir": RENDERS_ROOT / "rotax_915is",
        "default_center": mathutils.Vector((1.93, 61.65, -35.32)),
        "shots": [
            {
                "name": "01_healthy_915_intercooler",
                "fault": None,
                "cam_pos": mathutils.Vector((-150.0, 100.0, 80.0)),
                "target": mathutils.Vector((1.93, 61.65, -35.32)),
                "lens": 50.0,
            },
            {
                "name": "02_fault_cooling_degradation",
                "fault": "COOLING_DEGRADATION",
                "target_parts": [
                    "Cooling_Air_Baffle_M_PlasticWhite_0",
                    "Covers_Theme_M_PlasticGreen_0",
                ],
                "cam_pos": mathutils.Vector((-110.0, -20.0, 45.0)),
                "target": mathutils.Vector((-10.0, 50.0, -15.0)),
                "lens": 60.0,
                "color": (1.0, 0.1, 0.05, 1.0),
                "emission_strength": 12.0,
            },
        ],
    },
    "austro_ae300": {
        "blend_file": REPO_ROOT / "assets" / "models" / "engines" / "austro_ae330.blend",
        "output_dir": RENDERS_ROOT / "austro_ae300",
        "default_center": mathutils.Vector((0.0, 0.25, 0.0)),
        "shots": [
            {
                "name": "01_healthy_hero",
                "fault": None,
                "cam_pos": mathutils.Vector((-1.52, 0.35, 0.08)),
                "target": mathutils.Vector((-0.06, 0.35, -0.02)),
                "lens": 52.0,
            },
            {
                "name": "02_fault_common_rail_pressure_loss",
                "fault": "RAIL_PRESSURE_LOSS",
                "target_parts": [
                    "Common_Rail_M_Steel_0",
                    "HP_Fuel_Pump_M_CastAluminium_0",
                    "Fuel_Rail_Pipes_M_Steel_0",
                ],
                "cam_pos": mathutils.Vector((0.95, 0.41, 0.35)),
                "target": mathutils.Vector((0.1, 0.41, 0.18)),
                "lens": 60.0,
                "color": (1.0, 0.35, 0.0, 1.0),
                "emission_strength": 15.0,
            },
            {
                "name": "03_fault_injector1_combustion_failure",
                "fault": "INJECTOR_1_FAILURE",
                "target_parts": [
                    "Injector_1_M_Steel_0",
                    "Cylinder_Head_M_CastAluminium_0",
                ],
                "cam_pos": mathutils.Vector((0.6, -0.2, 0.5)),
                "target": mathutils.Vector((0.0, 0.15, 0.2)),
                "lens": 70.0,
                "color": (1.0, 0.05, 0.0, 1.0),
                "emission_strength": 15.0,
            },
            {
                "name": "04_fault_turbo_fouling",
                "fault": "TURBO_INTERCOOLER_FOULING",
                "target_parts": [
                    "Turbocharger_M_CastAluminium_0",
                    "Intercooler_M_CastAluminium_0",
                ],
                "cam_pos": mathutils.Vector((-0.85, 0.44, 0.2)),
                "target": mathutils.Vector((-0.18, 0.44, 0.16)),
                "lens": 65.0,
                "color": (0.95, 0.55, 0.0, 1.0),
                "emission_strength": 12.0,
            },
        ],
    },
    "vrde_jayem_2_2l": {
        "blend_file": REPO_ROOT / "assets" / "models" / "engines" / "tei_pd170.blend",
        "output_dir": RENDERS_ROOT / "vrde_jayem_2_2l",
        "default_center": mathutils.Vector((0.0, 0.0, 0.0)),
        "shots": [
            {
                "name": "01_healthy_vrde_crdi_hero",
                "fault": None,
                "cam_pos": mathutils.Vector((1.6, -1.8, 1.1)),
                "target": mathutils.Vector((0.0, 0.0, 0.0)),
                "lens": 50.0,
            },
            {
                "name": "02_fault_crdi_injector_coking",
                "fault": "CRDI_INJECTOR_COKING",
                "target_parts": [
                    "Fuel_Rail",
                    "Injector_1",
                    "Injector_2",
                    "Injector_3",
                    "Injector_4",
                ],
                "cam_pos": mathutils.Vector((0.8, -0.6, 0.7)),
                "target": mathutils.Vector((0.0, 0.0, 0.2)),
                "lens": 65.0,
                "color": (1.0, 0.2, 0.0, 1.0),
                "emission_strength": 15.0,
            },
            {
                "name": "03_fault_turbo_bearing_drag",
                "fault": "TURBO_BEARING_DRAG",
                "target_parts": [
                    "Turbocharger",
                    "Exhaust_Manifold",
                ],
                "cam_pos": mathutils.Vector((-0.9, -0.7, 0.4)),
                "target": mathutils.Vector((-0.2, 0.0, 0.1)),
                "lens": 70.0,
                "color": (1.0, 0.0, 0.2, 1.0),
                "emission_strength": 15.0,
            },
        ],
    },
}


def create_fault_emission_material(color, strength=10.0):
    mat = bpy.data.materials.new(name=f"ANUMAAN_Fault_Emission_{color[0]:.2f}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    node_out = nodes.new(type="ShaderNodeOutputMaterial")
    node_emit = nodes.new(type="ShaderNodeEmission")
    node_emit.inputs["Color"].default_value = color
    node_emit.inputs["Strength"].default_value = strength

    links.new(node_emit.outputs["Emission"], node_out.inputs["Surface"])
    return mat


def setup_camera(scene, name, location, target, lens_mm=50.0):
    cam_data = bpy.data.cameras.new(name=f"Data_{name}")
    cam_data.lens = lens_mm
    cam_obj = bpy.data.objects.new(name=name, object_data=cam_data)
    scene.collection.objects.link(cam_obj)
    cam_obj.location = location

    # Direction towards target
    direction = target - location
    rot_quat = direction.to_track_quat("-Z", "Y")
    cam_obj.rotation_euler = rot_quat.to_euler()

    scene.camera = cam_obj
    return cam_obj


def render_engine(engine_id, spec):
    blend_file = str(spec["blend_file"])
    out_dir = spec["output_dir"]
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n==========================================")
    print(f"LOADING ENGINE: {engine_id} ({blend_file})")
    print(f"==========================================")

    if not os.path.exists(blend_file):
        print(f"Error: Blend file {blend_file} does not exist!")
        return

    bpy.ops.wm.open_mainfile(filepath=blend_file)
    scene = bpy.context.scene

    # Render settings
    engines_available = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if "BLENDER_EEVEE_NEXT" in engines_available:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    else:
        scene.render.engine = "BLENDER_EEVEE"

    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    # Setup studio light if not present
    if not any(obj.type == "LIGHT" for obj in bpy.data.objects):
        light_data = bpy.data.lights.new(name="Studio_Key", type="SUN")
        light_data.energy = 4.0
        light_obj = bpy.data.objects.new(name="Studio_Key", object_data=light_data)
        scene.collection.objects.link(light_obj)
        light_obj.rotation_euler = (math.radians(45), math.radians(30), math.radians(60))

    # Backup original materials
    original_materials = {}
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            original_materials[obj.name] = [slot.material for slot in obj.material_slots]

    for shot in spec["shots"]:
        shot_name = shot["name"]
        out_path = os.path.join(out_dir, f"{shot_name}.png")
        print(f"-> Rendering Shot: {shot_name} ...")

        # Restore original materials
        for obj_name, mats in original_materials.items():
            obj = bpy.data.objects.get(obj_name)
            if obj and obj.type == "MESH":
                for i, mat in enumerate(mats):
                    if i < len(obj.material_slots):
                        obj.material_slots[i].material = mat

        # Apply fault highlight if specified
        if shot["fault"] and "target_parts" in shot:
            fault_color = shot.get("color", (1.0, 0.1, 0.0, 1.0))
            strength = shot.get("emission_strength", 12.0)
            fault_mat = create_fault_emission_material(fault_color, strength)

            for target_pattern in shot["target_parts"]:
                # Match exact or partial object name
                matched = [
                    obj for obj in bpy.data.objects
                    if obj.type == "MESH" and (target_pattern.lower() in obj.name.lower() or obj.name == target_pattern)
                ]
                for m_obj in matched:
                    print(f"   [FAULT HIGHLIGHT] Applied to {m_obj.name}")
                    if len(m_obj.material_slots) == 0:
                        m_obj.data.materials.append(fault_mat)
                    else:
                        for slot in m_obj.material_slots:
                            slot.material = fault_mat

        # Setup Camera
        cam = setup_camera(
            scene,
            f"Cam_{shot_name}",
            shot["cam_pos"],
            shot["target"],
            shot.get("lens", 50.0),
        )

        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"   Saved -> {out_path}")

        # Cleanup camera
        bpy.data.objects.remove(cam, do_unlink=True)


def main():
    target = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[-1].endswith(".py") else "all"
    if target in ENGINE_RENDER_SPECS:
        render_engine(target, ENGINE_RENDER_SPECS[target])
    else:
        for engine_id, spec in ENGINE_RENDER_SPECS.items():
            render_engine(engine_id, spec)

    print("\n==========================================")
    print("ALL MULTI-ENGINE RENDERS COMPLETE!")
    print("==========================================")


if __name__ == "__main__":
    main()
