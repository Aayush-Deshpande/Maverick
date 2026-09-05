"""
Batch snapshot renderer for all 8 DRDO Fault Scenarios in Blender using precision camera framing
"""

import bpy
import mathutils
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from standalone_digital_twin_app import FAULT_DATABASE, trigger_fault, reset_to_nominal

def render_all_fault_snapshots():
    blend_path = r"E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    
    out_dir = r"E:\TalentForge\Clay\3d_engine\renders\fault_snapshots"
    os.makedirs(out_dir, exist_ok=True)
    
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.image_settings.file_format = 'PNG'
    
    cam = scene.camera
    
    print("\n=======================================================")
    print("📸 RENDERING VALIDATION SNAPSHOTS FOR ALL 8 FAULT MODES")
    print("=======================================================\n")
    
    for fid, data in FAULT_DATABASE.items():
        print(f"Rendering: {fid} — {data['title']}...")
        trigger_fault(fid)
        
        # Position camera at precision fault view
        center = data['target_center']
        angle = data['target_angle']
        elevation = data['target_elevation']
        dist = data['target_distance']
        
        cx = center.x + dist * math.cos(angle) * math.cos(elevation)
        cy = center.y + dist * math.sin(angle) * math.cos(elevation)
        cz = center.z + dist * math.sin(elevation)
        
        cam.location = mathutils.Vector((cx, cy, cz))
        direction = center - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        
        out_file = os.path.join(out_dir, f"{fid.lower()}_{data['short'].lower().replace(' ', '_')}.png")
        scene.render.filepath = out_file
        bpy.ops.render.render(write_still=True)
        print(f"  -> Saved snapshot: {out_file}")
        
        reset_to_nominal()

    print("\n✅ All 8 precision fault snapshot renders completed successfully!\n")

if __name__ == "__main__":
    render_all_fault_snapshots()
