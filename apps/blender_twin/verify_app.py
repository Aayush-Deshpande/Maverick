"""
Verification Script for Standalone Digital Twin Simulator
Validates scene geometry, fault database markers, materials, and renders sample validation frames.
"""

import bpy
import mathutils
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_verification():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, "..", ".."))
    blend_path = os.path.join(project_root, "assets", "blender", "rotax_912_is_sport.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    
    print("\n--- 1. VERIFYING SCENE OBJECTS ---")
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    print(f"Total Mesh Objects: {len(meshes)} (Expected 109)")
    assert len(meshes) >= 100, f"Mesh count too low: {len(meshes)}"

    print("\n--- 2. VERIFYING MATERIALS & SHADERS ---")
    mats = bpy.data.materials
    print(f"Total Materials: {len(mats)}")
    key_materials = ['M_Chrome', 'M_Steel', 'M_Copper', 'M_PlasticGreen', 'M_PlasticBlack', 'M_PlasticTheme']
    for km in key_materials:
        assert km in mats, f"Missing key material: {km}"
        print(f"  [OK] Found Material: {km}")

    print("\n--- 3. VERIFYING DRDO FAULT COMPONENT TARGETS ---")
    # Every declared target must exist -- not just "at least one". A partially-stale
    # list (e.g. 3 real names + 1 renamed/deleted one) still highlights *something*,
    # so a ">0 found" check passes silently while quietly under-highlighting the
    # fault region. That gap is exactly how the 'Cooling_Air_Baffle_M_PlasticCable_0'
    # stale entry (fixed alongside this check) went undetected.
    from standalone_digital_twin_app import FAULT_DATABASE
    all_missing = {}
    for fid, fdata in FAULT_DATABASE.items():
        parts = fdata.get('target_parts', fdata.get('parts', []))
        missing = [tp for tp in parts if tp not in bpy.data.objects]
        found = len(parts) - len(missing)
        print(f"  {'[OK]' if not missing else '[STALE]'} {fid} ({fdata['short']}): "
              f"{found}/{len(parts)} target meshes exist"
              + (f" -- MISSING: {missing}" if missing else ""))
        if missing:
            all_missing[fid] = missing
        assert found > 0, f"No target meshes found for {fid} at all -- this fault will never highlight"
    assert not all_missing, (
        f"{sum(len(v) for v in all_missing.values())} stale target-part name(s) across "
        f"{len(all_missing)} fault(s): {all_missing}. These highlight nothing and silently "
        f"under-represent the fault region even though the fault still shows *some* highlight."
    )

    print("\n--- 4. TEST RENDER VERIFICATION ---")
    out_dir = os.path.join(project_root, "assets", "renders")
    os.makedirs(out_dir, exist_ok=True)
    
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    
    test_out = os.path.join(out_dir, "standalone_verification_render.png")
    scene.render.filepath = test_out
    bpy.ops.render.render(write_still=True)
    print(f"  [OK] Successfully rendered verification frame to: {test_out}")
    print("\n🎉 ALL STANDALONE SIMULATOR VERIFICATIONS PASSED SUCCESSFULLY!\n")

if __name__ == "__main__":
    run_verification()
