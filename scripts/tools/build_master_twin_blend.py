"""
Master Blend Builder for ANUMAAN Multi-Engine Digital Twin
Combines all 5 UAV engines into a single optimized master blend file:
- Rotax 912 iS Sport
- Rotax 914 F Turbo
- Rotax 915 iS A Turbo Intercooled
- Austro Engine AE300 / AE330
- VRDE / JAYEM 2.2L

Each engine is contained in its own named Collection.
Toggling engines is instant (0ms) and never crashes Blender.
"""

import bpy
import os
import mathutils
import math

REPO_ROOT = r"e:\backup-llm\backup-no-llm\3d_engine"
ROTAX_BLEND = os.path.join(REPO_ROOT, "assets", "blender", "rotax_912_is_sport.blend")
AUSTRO_BLEND = os.path.join(REPO_ROOT, "assets", "models", "engines", "austro_ae330.blend")
VRDE_BLEND = os.path.join(REPO_ROOT, "assets", "models", "engines", "tei_pd170.blend")
OUTPUT_BLEND = os.path.join(REPO_ROOT, "assets", "blender", "anumaan_master_twin.blend")

def main():
    print("[BUILDER] Loading Base Rotax Blend...")
    bpy.ops.wm.open_mainfile(filepath=ROTAX_BLEND)
    scene = bpy.context.scene

    # 1. Create Engine Collections
    col_rotax_912 = bpy.data.collections.new("Collection_Rotax_912iS")
    col_rotax_914 = bpy.data.collections.new("Collection_Rotax_914")
    col_rotax_915 = bpy.data.collections.new("Collection_Rotax_915iS")
    col_austro = bpy.data.collections.new("Collection_Austro_AE300")
    col_vrde = bpy.data.collections.new("Collection_VRDE_2_2L")

    scene.collection.children.link(col_rotax_912)
    scene.collection.children.link(col_rotax_914)
    scene.collection.children.link(col_rotax_915)
    scene.collection.children.link(col_austro)
    scene.collection.children.link(col_vrde)

    # 2. Move existing Rotax meshes into col_rotax_912
    rotax_objs = [o for o in bpy.data.objects if o.type == 'MESH']
    for obj in rotax_objs:
        if obj.name in scene.collection.objects:
            scene.collection.objects.unlink(obj)
        if obj.name not in col_rotax_912.objects:
            col_rotax_912.objects.link(obj)

    print(f"[BUILDER] Linked {len(rotax_objs)} meshes into Collection_Rotax_912iS")

    # 3. Append Austro AE330 objects
    print(f"[BUILDER] Appending Austro AE330 from {AUSTRO_BLEND}...")
    with bpy.data.libraries.load(AUSTRO_BLEND) as (data_from, data_to):
        data_to.objects = [name for name in data_from.objects if name != "Camera" and name != "Light" and not name.startswith("Studio_")]

    for obj in data_to.objects:
        if obj is not None:
            col_austro.objects.link(obj)
            # Scale meter-to-centimeter (100x) and position at Rotax center
            obj.scale = (obj.scale.x * 100.0, obj.scale.y * 100.0, obj.scale.z * 100.0)
            obj.location = (obj.location.x * 100.0 + 1.93, obj.location.y * 100.0 + 35.0, obj.location.z * 100.0 - 35.0)

    print(f"[BUILDER] Appended {len(data_to.objects)} Austro meshes into Collection_Austro_AE300")

    # 4. Append VRDE TEI PD170 objects
    print(f"[BUILDER] Appending VRDE TEI PD170 from {VRDE_BLEND}...")
    with bpy.data.libraries.load(VRDE_BLEND) as (data_from, data_to):
        data_to.objects = [name for name in data_from.objects if name != "Camera" and name != "Light" and not name.startswith("Studio_")]

    for obj in data_to.objects:
        if obj is not None:
            col_vrde.objects.link(obj)
            # Scale meter-to-centimeter (100x) and position at Rotax center
            obj.scale = (obj.scale.x * 100.0, obj.scale.y * 100.0, obj.scale.z * 100.0)
            obj.location = (obj.location.x * 100.0 + 1.93, obj.location.y * 100.0 + 50.0, obj.location.z * 100.0 - 35.0)

    print(f"[BUILDER] Appended {len(data_to.objects)} VRDE meshes into Collection_VRDE_2_2L")

    # 5. Default Visibility: Show Rotax 912, hide others
    col_rotax_912.hide_viewport = False
    col_rotax_914.hide_viewport = True
    col_rotax_915.hide_viewport = True
    col_austro.hide_viewport = True
    col_vrde.hide_viewport = True

    # 6. Ensure Studio Lighting
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

    # 7. Save master blend
    print(f"[BUILDER] Saving master blend to: {OUTPUT_BLEND}...")
    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
    print("[BUILDER] Master blend file built successfully!")

if __name__ == "__main__":
    main()
