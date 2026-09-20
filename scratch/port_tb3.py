import os
import re

src_path = r"e:\backup-llm\backup-no-llm\3d_engine\scripts\build_tb3_digital_twin.py"
dst_path = r"e:\backup-llm\backup-no-llm\3d_engine\ANUMAAN\scripts\build\build_bayraktar_tb3.py"

with open(src_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Imports and paths
code = code.replace(
    "import mathutils",
    "import mathutils\nfrom pathlib import Path\nimport sys\n\nROOT = Path(__file__).resolve().parents[2]\nLIB_DIR = ROOT / 'scripts' / 'lib'\nif str(LIB_DIR) not in sys.path:\n    sys.path.insert(0, str(LIB_DIR))\nimport anumaan_blender_lib as alb"
)

# 2. Base directory setup
old_dirs = """    base_dir = r"e:\\backup-llm\\backup-no-llm\\3d_engine"
    models_dir = os.path.join(base_dir, "3d_models")
    tex_dir = os.path.join(models_dir, "textures")
    rotax_blend = os.path.join(models_dir, "rotax_912_is_sport.blend")
    output_blend = os.path.join(models_dir, "bayraktar_tb3_digital_twin.blend")"""

new_dirs = """    models_dir = ROOT / "Models"
    tex_dir = models_dir / "textures"
    output_blend = models_dir / "airframes" / "bayraktar_tb3.blend" """

code = code.replace(old_dirs, new_dirs)

# 3. Scene properties
old_props = """    # Custom properties for UI control
    scene["display_mode"] = 0  # 0: Tactical PBR, 1: Wireframe Clay (fdda7fefdc.jpg), 2: X-Ray Hologram
    scene["wing_fold"] = 0.0   # 0.0 to 1.0 (0 to 115 deg)
    scene["gear_retract"] = 0.0 # 0.0 to 1.0
    scene["prop_spin"] = 0.0"""

new_props = """    # Twin properties per Section 13.2
    scene["twin_platform_id"] = "bayraktar_tb3"
    scene["twin_time_s"] = 0.0
    scene["prop_rpm_E1"] = 0.0
    scene["display_mode"] = 0
    scene["wing_fold"] = 0.0
    scene["gear_retract"] = 0.0
    scene["prop_spin"] = 0.0"""

code = code.replace(old_props, new_props)

# 4. Attach twin nodes to materials
code = code.replace(
    "if hasattr(mat_pbr, 'blend_method'):\n        mat_pbr.blend_method = 'HASHED'",
    "if hasattr(mat_pbr, 'blend_method'):\n        mat_pbr.blend_method = 'HASHED'\n    alb.add_twin_nodes(mat_pbr, is_skin=True)"
)

code = code.replace(
    "links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])",
    "links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])\n        alb.add_twin_nodes(mat, is_skin=False)"
)

# 5. Replace keyframes with property drivers (Section 13.3)
old_keyframes = """    ctrl_fold.location = (-0.50, 0.35, 3.0)
    ctrl_fold.keyframe_insert(data_path="location", index=2, frame=1)
    ctrl_fold.keyframe_insert(data_path="location", index=2, frame=120)
    ctrl_fold.location = (-0.50, 0.35, 4.0)
    ctrl_fold.keyframe_insert(data_path="location", index=2, frame=170)
    ctrl_fold.keyframe_insert(data_path="location", index=2, frame=210)
    ctrl_fold.location = (-0.50, 0.35, 3.0)
    ctrl_fold.keyframe_insert(data_path="location", index=2, frame=250)

    ctrl_gear.location = (0.50, 0.35, 3.0)
    ctrl_gear.keyframe_insert(data_path="location", index=2, frame=1)
    ctrl_gear.keyframe_insert(data_path="location", index=2, frame=40)
    ctrl_gear.location = (0.50, 0.35, 4.0)
    ctrl_gear.keyframe_insert(data_path="location", index=2, frame=60)
    ctrl_gear.keyframe_insert(data_path="location", index=2, frame=80)
    ctrl_gear.location = (0.50, 0.35, 3.0)
    ctrl_gear.keyframe_insert(data_path="location", index=2, frame=100)

    scene.frame_set(1)

    # Continuous Pusher Propeller Spin
    pivot_prop.rotation_euler = (0, 0, 0)
    pivot_prop.keyframe_insert(data_path="rotation_euler", frame=1)
    pivot_prop.rotation_euler = (0, math.radians(250 * 180), 0)
    pivot_prop.keyframe_insert(data_path="rotation_euler", frame=250)"""

new_drivers = """    # Drivers on mechanism controllers (Section 13.3 - No keyframes)
    alb.add_driver(ctrl_fold, "location", 2, "3.0 + val * 1.0", scene, '["wing_fold"]')
    alb.add_driver(ctrl_gear, "location", 2, "3.0 + val * 1.0", scene, '["gear_retract"]')
    alb.add_driver(pivot_prop, "rotation_euler", 1, "val * 6.283185307", scene, '["twin_time_s"]')"""

code = code.replace(old_keyframes, new_drivers)

# 6. Cameras per Section 11.5 and Manifest
old_cams = """    # 1. HERO CAMERA matching image.png (High-3/4 front-left angle, dark studio presentation)
    cam_hero_png = create_tracked_camera("Cam_Hero_Image_PNG", (-10.4, 9.5, 7.8), (0.1, 0.3, 0.9), lens=41.0)

    # 2. WIREFRAME CAMERA matching fdda7fefdc.jpg (Underside front-right 3/4 angle looking UP)
    cam_data_wire = bpy.data.cameras.new("Cam_Wireframe_FDDA")
    cam_data_wire.lens = 29.0
    cam_data_wire.clip_start = 0.1
    cam_data_wire.clip_end = 500.0
    cam_wire_fdda = bpy.data.objects.new("Cam_Wireframe_FDDA", cam_data_wire)
    cols["Cameras"].objects.link(cam_wire_fdda)
    
    cam_loc = mathutils.Vector((6.2, 5.0, -2.0))
    tgt_wire = mathutils.Vector((0.0, 0.6, 1.05))
    forward = (tgt_wire - cam_loc).normalized()
    up_approx = mathutils.Vector((0.0, 0.0, 1.0))
    right = forward.cross(up_approx).normalized()
    up = right.cross(forward).normalized()
    rot_roll = mathutils.Matrix.Rotation(math.radians(146.0), 3, forward)
    right_r = rot_roll @ right
    up_r = rot_roll @ up
    rot_mat = mathutils.Matrix([
        [right_r.x, up_r.x, -forward.x],
        [right_r.y, up_r.y, -forward.y],
        [right_r.z, up_r.z, -forward.z]
    ]).to_4x4()
    cam_wire_fdda.matrix_world = mathutils.Matrix.Translation(cam_loc) @ rot_mat

    # 3. Orbit Beauty Camera
    cam_orbit = create_tracked_camera("Cam_Beauty_Orbit", (-8.5, -9.5, 2.2), (0.0, 0.2, 0.9), lens=48.0)

    # 4. Sensor Close-up Camera
    cam_sensor = create_tracked_camera("Cam_Front_Sensor", (-1.10, 3.25, 0.30), (0.0, 2.05, 0.46), lens=65.0)

    # Set default camera to Hero image.png camera
    scene.camera = cam_hero_png"""

new_cams = """    # Cameras per Section 11.5 and Manifest
    cam_hero = create_tracked_camera("Cam_Hero", (-10.4, 9.5, 7.8), (0.1, 0.3, 0.9), lens=41.0)
    cam_orbit = create_tracked_camera("Cam_Beauty_Orbit", (-8.5, -9.5, 2.2), (0.0, 0.2, 0.9), lens=48.0)
    cam_wire = create_tracked_camera("Cam_Wireframe", (6.2, 5.0, 2.5), (0.0, 0.6, 1.05), lens=35.0)
    cam_sensor = create_tracked_camera("Cam_Front_Sensor", (-1.10, 3.25, 0.30), (0.0, 2.05, 0.46), lens=65.0)
    cam_engine = create_tracked_camera("Cam_Engine_Bay", (0.0, -4.2, 1.8), (0.0, -0.65, 1.15), lens=55.0)
    cam_gear = create_tracked_camera("Cam_Undercarriage", (0.0, -1.5, -0.2), (0.0, 0.35, 0.4), lens=45.0)

    scene.camera = cam_hero"""

code = code.replace(old_cams, new_cams)

# 7. Mount TEI-PD170 LOD1 engine into Internal_Systems
engine_mount_code = """
    # 10. Mount TEI-PD170 LOD1 Engine into Internal_Systems (Section 11.6)
    print("Mounting TEI-PD170 Turbodiesel LOD1...")
    engine_lod1_path = ROOT / "Models" / "engines" / "tei_pd170_lod1.blend"
    if engine_lod1_path.exists():
        mount_empty = bpy.data.objects.new("Engine_Mount_1", None)
        mount_empty.empty_display_type = 'ARROWS'
        mount_empty.empty_display_size = 0.4
        mount_empty.location = (0.0, -0.65, 1.15)
        mount_empty.rotation_euler = (0.0, 0.0, math.radians(180.0))
        mount_empty.parent = root_empty
        cols["Internal_Systems"].objects.link(mount_empty)

        with bpy.data.libraries.load(str(engine_lod1_path), link=False) as (data_from, data_to):
            data_to.objects = data_from.objects

        for o in data_to.objects:
            if o is not None:
                o.name = f"E1__{o.name}"
                o["twin_mount_id"] = "E1"
                o.parent = mount_empty
                cols["Internal_Systems"].objects.link(o)
    print("TEI-PD170 Engine Mounted Successfully!")
"""

code = code.replace(
    "# 10. MODELING: ROTAX 912 iS INTERNAL PROPULSION BAY",
    engine_mount_code + "\n    # 10. PREVIOUS ROTAX CODE SKIPPED"
)

# 8. Embed Controller and Manifest
old_controller = """    text_block = bpy.data.texts.new("tb3_ui_controller.py")
    text_block.write(controller_script_text)
    text_block.use_module = True"""

new_controller = """    manifest_p = ROOT / "manifests" / "platforms" / "bayraktar_tb3.json"
    with open(manifest_p, "r", encoding="utf-8") as f:
        manifest_text = f.read()
    txt_manifest = bpy.data.texts.new("bayraktar_tb3_manifest.json")
    txt_manifest.write(manifest_text)

    ctrl_p = ROOT / "scripts" / "lib" / "anumaan_twin_controller.py"
    with open(ctrl_p, "r", encoding="utf-8") as f:
        ctrl_text = f.read()
    text_block = bpy.data.texts.new("bayraktar_tb3_ui_controller.py")
    text_block.write(ctrl_text)
    text_block.use_module = True"""

code = code.replace(old_controller, new_controller)

# Save the updated script
with open(dst_path, "w", encoding="utf-8") as f:
    f.write(code)

print(f"Generated {dst_path} successfully ({len(code.splitlines())} lines)")
