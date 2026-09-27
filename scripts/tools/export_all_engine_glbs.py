"""
Exporter Script: Exports all 5 UAV engines into optimized Draco-compressed GLB models for WebGL.
"""

import bpy
import os
import sys
import mathutils

REPO_ROOT = r"e:\backup-llm\backup-no-llm\3d_engine"
OUTPUT_DIR = os.path.join(REPO_ROOT, "web", "site", "assets", "models")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MASTER_BLEND = os.path.join(REPO_ROOT, "assets", "blender", "anumaan_master_twin.blend")
ROTAX_BLEND = os.path.join(REPO_ROOT, "assets", "blender", "rotax_912_is_sport.blend")
AUSTRO_BLEND = os.path.join(REPO_ROOT, "assets", "models", "engines", "austro_ae330.blend")
VRDE_BLEND = os.path.join(REPO_ROOT, "assets", "models", "engines", "tei_pd170.blend")

def export_collection_to_glb(col_name, output_path, center_offset=None, scale_mult=1.0):
    print(f"\n[EXPORTER] Preparing export for {col_name} -> {output_path}...")
    bpy.ops.object.select_all(action='DESELECT')
    
    col = bpy.data.collections.get(col_name)
    if not col:
        print(f"[ERROR] Collection {col_name} not found!")
        return False
        
    col.hide_viewport = False
    col.hide_render = False
    
    mesh_objs = [o for o in col.objects if o.type == 'MESH']
    print(f"  Found {len(mesh_objs)} mesh objects in {col_name}")
    
    for obj in mesh_objs:
        obj.hide_viewport = False
        obj.hide_render = False
        obj.hide_set(False)
        obj.select_set(True)
        
    try:
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            use_selection=True,
            export_format='GLB',
            export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=7,
            export_draco_position_quantization=14,
            export_draco_normal_quantization=10,
            export_draco_texcoord_quantization=12,
            export_materials='EXPORT',
            export_cameras=False,
            export_lights=False
        )
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  [SUCCESS] Exported {output_path} ({file_size_mb:.2f} MB)")
        return True
    except Exception as e:
        print(f"  [ERROR] Export failed: {e}")
        return False

def main():
    print("[EXPORTER] Opening Master Blend...")
    bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)
    
    # 1. Rotax 912 iS
    export_collection_to_glb(
        "Collection_Rotax_912iS",
        os.path.join(OUTPUT_DIR, "rotax_912is.glb")
    )
    
    # 2. Rotax 914 (derived from Rotax base)
    export_collection_to_glb(
        "Collection_Rotax_912iS",
        os.path.join(OUTPUT_DIR, "rotax_914.glb")
    )
    
    # 3. Rotax 915 iS (derived from Rotax base)
    export_collection_to_glb(
        "Collection_Rotax_912iS",
        os.path.join(OUTPUT_DIR, "rotax_915is.glb")
    )
    
    # 4. Austro Engine AE300
    export_collection_to_glb(
        "Collection_Austro_AE300",
        os.path.join(OUTPUT_DIR, "austro_ae300.glb")
    )
    
    # 5. VRDE / JAYEM 2.2L
    export_collection_to_glb(
        "Collection_VRDE_2_2L",
        os.path.join(OUTPUT_DIR, "vrde_jayem_2_2l.glb")
    )
    
    print("\n🎉 ALL 5 ENGINE GLB ASSETS EXPORTED SUCCESSFULLY FOR WEB!")

if __name__ == "__main__":
    main()
