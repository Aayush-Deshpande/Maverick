"""
Update Collection_Rotax_914 in assets/blender/scenes/anumaan_master_twin.blend
with the resegmented objects from assets/blender/engines/rotax_914/rotax_914.blend.
"""
import bpy
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

master_blend = os.path.join(PROJECT_ROOT, "assets", "blender", "scenes", "anumaan_master_twin.blend")
engine_blend = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_914", "rotax_914.blend")

print(f"[UPDATE MASTER] Opening master twin: {master_blend}")
bpy.ops.wm.open_mainfile(filepath=master_blend)

col_914 = bpy.data.collections.get("Collection_Rotax_914")
if not col_914:
    raise ValueError("Collection_Rotax_914 not found in master blend")

old_objs = list(col_914.objects)
print(f"  Removing {len(old_objs)} old objects from Collection_Rotax_914...")
for obj in old_objs:
    bpy.data.objects.remove(obj, do_unlink=True)

print(f"  Appending resegmented objects from: {engine_blend}")
with bpy.data.libraries.load(engine_blend) as (data_from, data_to):
    data_to.objects = [name for name in data_from.objects if name not in ("Camera", "Main_Studio_Camera", "Studio_Fill_Light", "Studio_Key_Light", "Studio_Rim_Light", "Light")]

for obj in data_to.objects:
    if obj:
        col_914.objects.link(obj)

print(f"  Linked {len(data_to.objects)} objects to Collection_Rotax_914.")

bpy.ops.wm.save_mainfile()
print("[UPDATE MASTER] Saved updated anumaan_master_twin.blend successfully!")
