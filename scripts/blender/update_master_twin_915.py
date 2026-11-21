"""
Update Collection_Rotax_915iS in assets/blender/scenes/anumaan_master_twin.blend
with the newly decomposed objects from assets/blender/engines/rotax_915is/rotax_915is.blend.
"""
import bpy
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

master_blend = os.path.join(PROJECT_ROOT, "assets", "blender", "scenes", "anumaan_master_twin.blend")
engine_blend = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_915is", "rotax_915is.blend")

print(f"[UPDATE MASTER] Opening master twin: {master_blend}")
bpy.ops.wm.open_mainfile(filepath=master_blend)

col_915 = bpy.data.collections.get("Collection_Rotax_915iS")
if not col_915:
    raise ValueError("Collection_Rotax_915iS not found in master blend")

# Unlink and delete old objects in Collection_Rotax_915iS
old_objs = list(col_915.objects)
print(f"  Removing {len(old_objs)} old objects from Collection_Rotax_915iS...")
for obj in old_objs:
    bpy.data.objects.remove(obj, do_unlink=True)

# Append new objects from rotax_915is.blend
print(f"  Appending decomposed objects from: {engine_blend}")
with bpy.data.libraries.load(engine_blend) as (data_from, data_to):
    # Load all mesh objects except studio camera/lights/plane
    data_to.objects = [name for name in data_from.objects if name not in ("Main_Studio_Camera", "Studio_Fill_Light", "Studio_Key_Light", "Studio_Rim_Light", "Plane001")]

for obj in data_to.objects:
    if obj:
        col_915.objects.link(obj)

print(f"  Linked {len(data_to.objects)} objects to Collection_Rotax_915iS.")

bpy.ops.wm.save_mainfile()
print("[UPDATE MASTER] Saved updated anumaan_master_twin.blend successfully!")
