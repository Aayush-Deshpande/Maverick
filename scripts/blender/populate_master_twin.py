"""
Populate Master Twin Blend Collections for Rotax 914 and Rotax 915 iS.
DRDO / iDEX PS-26054 Compliance - Rule D53:
- Never overwrite master blend files directly.
- Loads assets/blender/scenes/anumaan_master_twin.blend.
- Appends Collection_Rotax_914 objects from rotax_914.blend.
- Appends Collection_Rotax_915iS objects from rotax_915is.blend.
- Saves output to assets/blender/scenes/anumaan_master_twin_work.blend.
- Renders verification turntable frames for all 5 engines to assets/renders/.
"""

import bpy
import mathutils
import math
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "apps", "blender_twin"))

import standalone_digital_twin_app as twin

def populate():
    master_path = os.path.join(PROJECT_ROOT, "assets", "blender", "scenes", "anumaan_master_twin.blend")
    work_path = os.path.join(PROJECT_ROOT, "assets", "blender", "scenes", "anumaan_master_twin_work.blend")
    rotax_914_path = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_914", "rotax_914.blend")
    rotax_915_path = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_915is", "rotax_915is.blend")
    renders_dir = os.path.join(PROJECT_ROOT, "assets", "renders")
    os.makedirs(renders_dir, exist_ok=True)

    print("\n=================================================================")
    print("  POPULATING ANUMAAN MASTER TWIN COLLECTIONS (D53)")
    print("=================================================================\n")

    bpy.ops.wm.open_mainfile(filepath=master_path)
    print(f"[1/4] Opened master file: {master_path}")
    
    col_914 = bpy.data.collections.get("Collection_Rotax_914")
    if not col_914:
        col_914 = bpy.data.collections.new("Collection_Rotax_914")
        bpy.context.scene.collection.children.link(col_914)

    col_915 = bpy.data.collections.get("Collection_Rotax_915iS")
    if not col_915:
        col_915 = bpy.data.collections.new("Collection_Rotax_915iS")
        bpy.context.scene.collection.children.link(col_915)

    # 1. Append Rotax 914 objects
    print("\n[2/4] Appending Rotax 914 meshes from rotax_914.blend...")
    with bpy.data.libraries.load(rotax_914_path, link=False) as (data_from, data_to):
        data_to.objects = [name for name in data_from.objects if name.startswith("Rotax914_")]
    
    count_914 = 0
    for obj in data_to.objects:
        if obj is not None:
            col_914.objects.link(obj)
            count_914 += 1
    print(f"  [OK] Linked {count_914} meshes into Collection_Rotax_914.")

    # 2. Append Rotax 915 objects
    print("\n[3/4] Appending Rotax 915 iS meshes from rotax_915is.blend...")
    with bpy.data.libraries.load(rotax_915_path, link=False) as (data_from, data_to):
        data_to.objects = [name for name in data_from.objects if name != 'Plane001']
    
    count_915 = 0
    for obj in data_to.objects:
        if obj is not None:
            col_915.objects.link(obj)
            count_915 += 1
    print(f"  [OK] Linked {count_915} meshes into Collection_Rotax_915iS.")

    # Ensure lighting & camera with wide clipping plane (handles millimeter scale 914 at 1920 distance)
    scene = bpy.context.scene
    twin.ensure_studio_lighting()
    cam = bpy.data.objects.get("TurntableCam")
    if not cam:
        cam_data = bpy.data.cameras.new("TurntableCam")
        cam = bpy.data.objects.new("TurntableCam", cam_data)
        scene.collection.objects.link(cam)
    if cam.data:
        cam.data.clip_start = 0.05
        cam.data.clip_end = 15000.0
        cam.data.lens = 50.0
    scene.camera = cam

    # Save to _work.blend
    bpy.ops.wm.save_as_mainfile(filepath=work_path)
    print(f"\n  [OK] Saved work file to: {work_path}")

    # 3. Render verification turntable frames for all 5 engines
    print("\n[4/4] Rendering verification frames for all 5 engines in anumaan_master_twin_work.blend...")
    
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720

    engines_to_verify = [
        ("rotax_912is", "master_twin_rotax_912is.png"),
        ("rotax_914", "master_twin_rotax_914.png"),
        ("rotax_915is", "master_twin_rotax_915is.png"),
        ("austro_ae300", "master_twin_austro_ae300.png"),
        ("vrde_jayem_2_2l", "master_twin_vrde_jayem_2_2l.png"),
    ]

    for eng_id, render_name in engines_to_verify:
        twin.switch_engine_collection(eng_id)
        prof = twin.ENGINE_PROFILES[eng_id]
        center = prof['default_center']
        dist = prof['default_distance']
        elev = prof['default_elevation']
        angle = prof.get('front_angle', -1.57)

        # Position camera in front isometric view
        cam_x = center.x + dist * math.cos(elev) * math.sin(angle)
        cam_y = center.y - dist * math.cos(elev) * math.cos(angle)
        cam_z = center.z + dist * math.sin(elev)
        cam.location = mathutils.Vector((cam_x, cam_y, cam_z))
        
        direction = center - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

        out_img = os.path.join(renders_dir, render_name)
        scene.render.filepath = out_img
        bpy.ops.render.render(write_still=True)
        print(f"  [OK] Rendered {eng_id} to: {out_img}")

    print("\n🎉 MASTER TWIN POPULATION & RENDERING COMPLETED SUCCESSFULLY!\n")

if __name__ == "__main__":
    populate()
