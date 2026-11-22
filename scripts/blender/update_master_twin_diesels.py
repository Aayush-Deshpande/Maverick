"""
Update Collection_Austro_AE300 and Collection_VRDE_2_2L in
assets/blender/scenes/anumaan_master_twin.blend (Card B-05).
"""
import bpy
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

master_blend = os.path.join(PROJECT_ROOT, "assets", "blender", "scenes", "anumaan_master_twin.blend")
ae300_blend = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "austro_ae300", "austro_ae300.blend")
vrde_blend = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "vrde_jayem_2_2l", "vrde_jayem_2_2l.blend")

print(f"[UPDATE MASTER] Opening master twin: {master_blend}")
bpy.ops.wm.open_mainfile(filepath=master_blend)

# 1. Update AE300
col_ae = bpy.data.collections.get("Collection_Austro_AE300")
if col_ae:
    print(f"  Removing {len(col_ae.objects)} old objects from Collection_Austro_AE300...")
    for obj in list(col_ae.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    with bpy.data.libraries.load(ae300_blend) as (data_from, data_to):
        data_to.objects = [n for n in data_from.objects if not any(c in n for c in ("Camera", "VerifyCam", "Light", "Studio", "Target"))]
    for obj in data_to.objects:
        if obj:
            col_ae.objects.link(obj)
    print(f"  Linked {len(data_to.objects)} objects to Collection_Austro_AE300.")

# 2. Update VRDE
col_vrde = bpy.data.collections.get("Collection_VRDE_2_2L")
if col_vrde:
    print(f"  Removing {len(col_vrde.objects)} old objects from Collection_VRDE_2_2L...")
    for obj in list(col_vrde.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    with bpy.data.libraries.load(vrde_blend) as (data_from, data_to):
        data_to.objects = [n for n in data_from.objects if not any(c in n for c in ("Camera", "VerifyCam", "Light", "Studio", "Target"))]
    for obj in data_to.objects:
        if obj:
            col_vrde.objects.link(obj)
    print(f"  Linked {len(data_to.objects)} objects to Collection_VRDE_2_2L.")

bpy.ops.wm.save_mainfile()
print("[UPDATE MASTER] Saved updated anumaan_master_twin.blend successfully!")
