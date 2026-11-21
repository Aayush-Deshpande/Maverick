import os
import bpy

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

BLENDS = [
    os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "austro_ae300", "austro_ae300.blend"),
    os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "vrde_jayem_2_2l", "vrde_jayem_2_2l.blend"),
    os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_915is", "rotax_915is.blend"),
    os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_914", "rotax_914.blend"),
    os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_912is", "rotax_912is.blend"),
    os.path.join(PROJECT_ROOT, "assets", "blender", "scenes", "anumaan_master_twin.blend"),
]

for b in BLENDS:
    if not os.path.exists(b):
        continue
    print(f"\nChecking: {os.path.basename(b)}")
    bpy.ops.wm.open_mainfile(filepath=b)
    
    to_remove = []
    for o in bpy.data.objects:
        nl = o.name.lower()
        if any(k in nl for k in ["cyclorama", "backdrop", "studio_cyclorama", "circle001", "plane001"]) and not "ground_straps" in nl:
            to_remove.append(o)
            
    if to_remove:
        print(f"  Removing {len(to_remove)} backdrop objects: {[o.name for o in to_remove]}")
        for o in to_remove:
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.ops.wm.save_mainfile()
        print("  Saved cleaned blend.")
    else:
        print("  Clean (no backdrops).")
