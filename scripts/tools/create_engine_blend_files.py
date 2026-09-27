"""
Engine Blend Generator — Creates dedicated, fully-configured standalone .blend files
for all engine variants:
- VRDE / Jayem 2.2L (Indigenous DRDO CRDi Diesel) -> assets/blender/vrde_jayem_2_2l.blend
- Rotax 914 F (Turbocharged TCU)                  -> assets/blender/rotax_914.blend & rotax_914_f.blend
- Austro Engine AE300 (Jet-A1 Common Rail Diesel) -> assets/blender/austro_ae300.blend
"""

import bpy
import mathutils
import math
import os
import shutil
from pathlib import Path

REPO_ROOT = Path(r"e:\backup-llm\backup-no-llm\3d_engine")
BLENDER_DIR = REPO_ROOT / "assets" / "blender"
MODELS_ENGINES_DIR = REPO_ROOT / "assets" / "models" / "engines"

def setup_studio_lighting_and_camera(scene, center, camera_pos, focal_length=50.0):
    # Remove existing cameras and lights
    for obj in list(scene.collection.objects):
        if obj.type in {'LIGHT', 'CAMERA'}:
            scene.collection.objects.unlink(obj)
            bpy.data.objects.remove(obj, do_unlink=True)

    # 1. Key Light
    key_data = bpy.data.lights.new(name="Studio_Key_Light", type='SUN')
    key_data.energy = 3.5
    key_data.color = (1.0, 0.98, 0.95)
    key_obj = bpy.data.objects.new(name="Studio_Key_Light", object_data=key_data)
    scene.collection.objects.link(key_obj)
    key_obj.location = camera_pos + mathutils.Vector((50.0, -50.0, 80.0))
    key_obj.rotation_euler = (math.radians(45), math.radians(20), math.radians(50))

    # 2. Fill Light
    fill_data = bpy.data.lights.new(name="Studio_Fill_Light", type='SUN')
    fill_data.energy = 1.8
    fill_data.color = (0.85, 0.92, 1.0)
    fill_obj = bpy.data.objects.new(name="Studio_Fill_Light", object_data=fill_data)
    scene.collection.objects.link(fill_obj)
    fill_obj.location = camera_pos + mathutils.Vector((-70.0, 60.0, 40.0))
    fill_obj.rotation_euler = (math.radians(60), math.radians(-30), math.radians(-120))

    # 3. Rim Light
    rim_data = bpy.data.lights.new(name="Studio_Rim_Light", type='SUN')
    rim_data.energy = 2.5
    rim_data.color = (0.7, 0.85, 1.0)
    rim_obj = bpy.data.objects.new(name="Studio_Rim_Light", object_data=rim_data)
    scene.collection.objects.link(rim_obj)
    rim_obj.location = center + mathutils.Vector((0.0, 100.0, 60.0))
    rim_obj.rotation_euler = (math.radians(-45), math.radians(10), math.radians(-170))

    # 4. Camera
    cam_data = bpy.data.cameras.new(name="Main_Studio_Camera")
    cam_data.lens = focal_length
    cam_data.clip_start = 0.1
    cam_data.clip_end = 2000.0
    cam_obj = bpy.data.objects.new(name="Main_Studio_Camera", object_data=cam_data)
    scene.collection.objects.link(cam_obj)
    cam_obj.location = camera_pos
    
    # Point camera to center
    direction = center - camera_pos
    rot_quat = direction.to_track_quat("-Z", "Y")
    cam_obj.rotation_euler = rot_quat.to_euler()
    scene.camera = cam_obj

    # 5. Render Settings
    engines_available = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if "BLENDER_EEVEE_NEXT" in engines_available:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in engines_available:
        scene.render.engine = "BLENDER_EEVEE"
        
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

def create_vrde_jayem_blend():
    source_blend = MODELS_ENGINES_DIR / "tei_pd170.blend"
    out_blend = BLENDER_DIR / "vrde_jayem_2_2l.blend"
    print(f"\n==========================================")
    print(f"[VRDE / JAYEM 2.2L] Generating {out_blend}...")
    print(f"==========================================")

    bpy.ops.wm.open_mainfile(filepath=str(source_blend))
    scene = bpy.context.scene

    # Organize all mesh objects into Collection_VRDE_2_2L
    col_name = "Collection_VRDE_2_2L"
    target_col = bpy.data.collections.get(col_name)
    if not target_col:
        target_col = bpy.data.collections.new(name=col_name)
        scene.collection.children.link(target_col)

    mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
    for obj in mesh_objs:
        # Ensure it is in target collection
        if obj.name not in target_col.objects:
            target_col.objects.link(obj)
        # Unlink from other root scene collections if present
        for col in bpy.data.collections:
            if col != target_col and obj.name in col.objects:
                try:
                    col.objects.unlink(obj)
                except Exception:
                    pass

    center = mathutils.Vector((0.0, 0.0, 0.0))
    cam_pos = mathutils.Vector((1.8, -2.0, 1.2))
    setup_studio_lighting_and_camera(scene, center, cam_pos, focal_length=50.0)

    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
    print(f"[SUCCESS] Saved {out_blend} ({len(mesh_objs)} meshes, {len(bpy.data.materials)} materials)")

def create_rotax_914_blend():
    source_blend = BLENDER_DIR / "rotax_912_is_sport.blend"
    out_blend_914 = BLENDER_DIR / "rotax_914.blend"
    out_blend_914_f = BLENDER_DIR / "rotax_914_f.blend"
    print(f"\n==========================================")
    print(f"[ROTAX 914 F TURBO] Generating {out_blend_914}...")
    print(f"==========================================")

    bpy.ops.wm.open_mainfile(filepath=str(source_blend))
    scene = bpy.context.scene

    # Create/Rename collection for 914
    col_name = "Collection_Rotax_914"
    target_col = bpy.data.collections.get(col_name)
    if not target_col:
        target_col = bpy.data.collections.new(name=col_name)
        scene.collection.children.link(target_col)

    mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
    for obj in mesh_objs:
        if obj.name not in target_col.objects:
            target_col.objects.link(obj)
        for col in bpy.data.collections:
            if col != target_col and obj.name in col.objects:
                try:
                    col.objects.unlink(obj)
                except Exception:
                    pass

    center = mathutils.Vector((1.932, 61.648, -35.324))
    cam_pos = mathutils.Vector((150.0, -160.0, 50.0))
    setup_studio_lighting_and_camera(scene, center, cam_pos, focal_length=50.0)

    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend_914))
    print(f"[SUCCESS] Saved {out_blend_914}")
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend_914_f))
    print(f"[SUCCESS] Saved {out_blend_914_f}")

def create_austro_ae300_blend():
    source_blend = MODELS_ENGINES_DIR / "austro_ae330.blend"
    out_blend = BLENDER_DIR / "austro_ae300.blend"
    print(f"\n==========================================")
    print(f"[AUSTRO AE300] Generating {out_blend}...")
    print(f"==========================================")

    bpy.ops.wm.open_mainfile(filepath=str(source_blend))
    scene = bpy.context.scene

    col_name = "Collection_Austro_AE300"
    target_col = bpy.data.collections.get(col_name)
    if not target_col:
        target_col = bpy.data.collections.new(name=col_name)
        scene.collection.children.link(target_col)

    mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
    for obj in mesh_objs:
        if obj.name not in target_col.objects:
            target_col.objects.link(obj)
        for col in bpy.data.collections:
            if col != target_col and obj.name in col.objects:
                try:
                    col.objects.unlink(obj)
                except Exception:
                    pass

    center = mathutils.Vector((-0.014, 0.30, 0.04))
    cam_pos = mathutils.Vector((-1.6, 0.4, 0.2))
    setup_studio_lighting_and_camera(scene, center, cam_pos, focal_length=50.0)

    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
    print(f"[SUCCESS] Saved {out_blend} ({len(mesh_objs)} meshes, {len(bpy.data.materials)} materials)")

def main():
    create_vrde_jayem_blend()
    create_rotax_914_blend()
    create_austro_ae300_blend()
    print("\n🎉 ALL DEDICATED BLEND FILES PRODUCED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
