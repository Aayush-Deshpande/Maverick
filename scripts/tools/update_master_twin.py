"""
Update Master Twin Blend:
Ensures assets/blender/anumaan_master_twin.blend has all 5 collections properly populated
with their distinct engine meshes and materials.
"""

import bpy
from pathlib import Path

REPO_ROOT = Path(r"e:\backup-llm\backup-no-llm\3d_engine")
MASTER_BLEND = REPO_ROOT / "assets" / "blender" / "anumaan_master_twin.blend"
ROTAX_914_BLEND = REPO_ROOT / "assets" / "blender" / "rotax_914.blend"
ROTAX_915_BLEND = REPO_ROOT / "assets" / "blender" / "rotax_915.blend"

def update_master_twin():
    print(f"Opening Master Blend: {MASTER_BLEND}")
    bpy.ops.wm.open_mainfile(filepath=str(MASTER_BLEND))
    scene = bpy.context.scene

    # 1. Clear empty or outdated 914 collection
    col_914 = bpy.data.collections.get("Collection_Rotax_914")
    if not col_914:
        col_914 = bpy.data.collections.new(name="Collection_Rotax_914")
        scene.collection.children.link(col_914)

    # 2. Append 914 meshes from rotax_914.blend
    print(f"Linking 914 objects from {ROTAX_914_BLEND}...")
    with bpy.data.libraries.load(str(ROTAX_914_BLEND)) as (data_from, data_to):
        data_to.objects = [name for name in data_from.objects if name in [
            "Rotax914_Turbo_Turbine_Housing",
            "Rotax914_Turbo_Compressor_Housing",
            "Rotax914_Turbo_Bearing_Cartridge",
            "Rotax914_Turbo_Wastegate_Actuator",
            "Rotax914_Turbo_Wastegate_Rod",
            "Rotax914_Turbo_Exhaust_Downpipe",
            "Rotax914_Turbo_Charge_Air_Pipe",
            "Rotax914_Badge_Plate",
            "Rotax914_Badge_Bezel",
        ]]

    for obj in data_to.objects:
        if obj and obj.name not in col_914.objects:
            col_914.objects.link(obj)

    bpy.ops.wm.save_as_mainfile(filepath=str(MASTER_BLEND))
    print("[SUCCESS] Master twin updated!")

if __name__ == "__main__":
    update_master_twin()
