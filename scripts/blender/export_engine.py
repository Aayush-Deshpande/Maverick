"""
Authoritative 3D Engine GLB Exporter for ANUMAAN.
DRDO / iDEX PS-26054 Compliance - Card B-01:
Exports engines from anumaan_master_twin.blend (or per-engine blends) into optimized WebGL GLBs:
- export_format='GLB'
- export_apply=True (modifiers applied)
- export_extras=True (custom properties like component_id, placeholder exported to glTF extras)
- export_materials='EXPORT' (pristine PBR materials)
- export_draco_mesh_compression_enable=True (Web optimization)
- Outputs to assets/web/engines/<engine_id>.glb
"""

import bpy
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

ENGINE_COLLECTIONS = {
    "rotax_912is": "Collection_Rotax_912iS",
    "rotax_914": "Collection_Rotax_914",
    "rotax_915is": "Collection_Rotax_915iS",
    "austro_ae300": "Collection_Austro_AE300",
    "vrde_jayem_2_2l": "Collection_VRDE_2_2L",
}

def export_engine(engine_id, output_dir=None, blend_file=None):
    if engine_id not in ENGINE_COLLECTIONS:
        raise ValueError(f"Unknown engine_id: {engine_id}")
        
    col_name = ENGINE_COLLECTIONS[engine_id]
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "assets", "web", "engines")
    os.makedirs(output_dir, exist_ok=True)
    
    output_glb = os.path.join(output_dir, f"{engine_id}.glb")
    
    if blend_file:
        bpy.ops.wm.open_mainfile(filepath=blend_file)
    elif not bpy.data.collections.get(col_name):
        master_blend = os.path.join(PROJECT_ROOT, "assets", "blender", "scenes", "anumaan_master_twin.blend")
        bpy.ops.wm.open_mainfile(filepath=master_blend)
        
    col = bpy.data.collections.get(col_name)
    if not col:
        print(f"[ERROR] Collection {col_name} not found in open blend file!")
        return False
        
    bpy.ops.object.select_all(action='DESELECT')
    col.hide_viewport = False
    col.hide_render = False
    
    export_objs = [o for o in col.objects if o.type in ('MESH', 'CURVE')]
    print(f"\n[EXPORTER] Exporting {engine_id} ({len(export_objs)} objects from {col_name})...")
    
    for obj in export_objs:
        obj.hide_viewport = False
        obj.hide_render = False
        obj.hide_set(False)
        obj.select_set(True)
        
    try:
        bpy.ops.export_scene.gltf(
            filepath=output_glb,
            use_selection=True,
            export_format='GLB',
            export_apply=True,
            export_extras=True,
            export_materials='EXPORT',
            export_cameras=False,
            export_lights=False,
            export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=7,
            export_draco_position_quantization=14,
            export_draco_normal_quantization=10,
            export_draco_texcoord_quantization=12
        )
        file_size_mb = os.path.getsize(output_glb) / (1024 * 1024)
        print(f"  [SUCCESS] Exported {output_glb} ({file_size_mb:.2f} MB)")
        return True
    except Exception as e:
        print(f"  [ERROR] Export failed for {engine_id}: {e}")
        return False

def export_all():
    master_blend = os.path.join(PROJECT_ROOT, "assets", "blender", "scenes", "anumaan_master_twin.blend")
    print(f"[EXPORTER] Loading Master Blend: {master_blend}")
    bpy.ops.wm.open_mainfile(filepath=master_blend)
    
    success = True
    for eid in ENGINE_COLLECTIONS:
        ok = export_engine(eid)
        if not ok:
            success = False
            
    if success:
        print("\n🎉 ALL 5 ENGINE GLB ASSETS EXPORTED SUCCESSFULLY!\n")
    else:
        print("\n❌ SOME ENGINES FAILED EXPORT!\n")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[-1] in ENGINE_COLLECTIONS:
        export_engine(sys.argv[-1])
    else:
        export_all()
