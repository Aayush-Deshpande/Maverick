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
    blend_path = os.path.join(project_root, "3d_models", "rotax_912_is_sport.blend")
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
    from standalone_digital_twin_app import FAULT_DATABASE
    for fid, fdata in FAULT_DATABASE.items():
        found_targets = []
        for tp in fdata['target_parts']:
            if tp in bpy.data.objects:
                found_targets.append(tp)
        print(f"  [OK] {fid} ({fdata['short']}): Found {len(found_targets)}/{len(fdata['target_parts'])} target meshes.")
        assert len(found_targets) > 0, f"No target meshes found for {fid}"

    print("\n--- 4. TEST RENDER VERIFICATION ---")
    out_dir = os.path.join(project_root, "renders")
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
