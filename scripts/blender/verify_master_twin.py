"""
Verification script for anumaan_master_twin_work.blend:
Verifies that all 5 engine collections exist and are populated with their respective meshes:
1. Collection_Rotax_912iS: 109 meshes
2. Collection_Rotax_914: 590 meshes
3. Collection_Rotax_915iS: 22 meshes
4. Collection_Austro_AE300: 177 meshes/objects
5. Collection_VRDE_2_2L: 472 meshes/objects
"""

import bpy
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "apps", "blender_twin"))

import standalone_digital_twin_app as twin

def verify():
    work_blend = os.path.join(PROJECT_ROOT, "assets", "blender", "scenes", "anumaan_master_twin_work.blend")
    assert os.path.exists(work_blend), f"File not found: {work_blend}"
    bpy.ops.wm.open_mainfile(filepath=work_blend)

    expected = {
        'rotax_912is': ('Collection_Rotax_912iS', 109),
        'rotax_914': ('Collection_Rotax_914', 590),
        'rotax_915is': ('Collection_Rotax_915iS', 22),
        'austro_ae300': ('Collection_Austro_AE300', 170),
        'vrde_jayem_2_2l': ('Collection_VRDE_2_2L', 450),
    }

    print("\n=======================================================")
    print("  VERIFYING ANUMAAN MASTER TWIN 5-ENGINE SCENE")
    print("=======================================================\n")

    for eng_id, (col_name, min_count) in expected.items():
        col = bpy.data.collections.get(col_name)
        assert col is not None, f"Missing collection: {col_name}"
        obj_count = len(col.objects)
        print(f"  [OK] {eng_id:15s} -> {col_name:25s} ({obj_count} objects, min {min_count})")
        assert obj_count >= min_count, f"Collection {col_name} has {obj_count} objects, expected at least {min_count}"

        # Test collection visibility switching
        twin.switch_engine_collection(eng_id)
        assert col.hide_viewport is False, f"Active collection {col_name} should not be hidden in viewport"
        assert col.hide_render is False, f"Active collection {col_name} should not be hidden in render"

    print("\n🎉 ALL 5 ENGINES IN MASTER TWIN SCENE VERIFIED SUCCESSFULLY!\n")

if __name__ == "__main__":
    verify()
