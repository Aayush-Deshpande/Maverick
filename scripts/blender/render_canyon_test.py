"""
Test Render Script for Tactical Terrain View
Aims camera down the Ladakh gorge from ridge altitude (5800m)
towards the canyon floor (4200m) and surrounding peaks (6000m).
"""

import bpy
import mathutils
import math
import os

def update_canyon_view():
    scene = bpy.context.scene
    cam_obj = bpy.data.objects.get("Camera_Canyon_Recon")
    if not cam_obj:
        cam_data = bpy.data.cameras.new("Camera_Canyon_Recon")
        cam_obj = bpy.data.objects.new("Camera_Canyon_Recon", cam_data)
        scene.collection.objects.link(cam_obj)
    
    scene.camera = cam_obj
    cam = cam_obj.data
    cam.lens = 32.0 # 32mm wide-angle tactical view
    cam.clip_start = 10.0
    cam.clip_end = 250000.0

    # Camera positioned at high ridge looking down along the canyon pass
    cam_pos = mathutils.Vector((-12500.0, 7500.0, 5600.0))
    target_pos = mathutils.Vector((-8500.0, 11500.0, 4400.0))
    
    cam_obj.location = cam_pos
    direction = target_pos - cam_pos
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

    # Sun positioned to cast raking side-light from right-rear
    sun = bpy.data.objects.get("Sun_Tactical")
    if sun:
        sun.data.energy = 5.5
        sun.data.color = (0.92, 0.96, 1.0)
        # 36 deg elevation, lighting the right canyon walls and skimming the left ridge crests
        sun.rotation_euler = (math.radians(54.0), math.radians(22.0), math.radians(-75.0))

    # Fill sun to keep shadow sides deep dark slate but clear
    fill = bpy.data.objects.get("Sun_Fill")
    if fill:
        fill.data.energy = 0.95
        fill.data.color = (0.35, 0.45, 0.55)
        fill.rotation_euler = (math.radians(110.0), math.radians(-15.0), math.radians(105.0))

    # Refine shader scales for kilometer-scale mountain topography
    mat = bpy.data.materials.get("M_Tactical_Ladakh_Terrain")
    if mat and mat.node_tree:
        nodes = mat.node_tree.nodes
        
        # Strata macro mapping (1km - 2km scale)
        for n in nodes:
            if n.type == 'MAPPING':
                # Check location to identify
                if n.location.y > 500: # strata
                    n.inputs['Scale'].default_value = (0.0008, 0.0008, 0.0002)
                elif n.location.y > 200: # crags
                    n.inputs['Scale'].default_value = (0.003, 0.003, 0.001)
                elif n.location.y > -100: # micro
                    n.inputs['Scale'].default_value = (0.015, 0.015, 0.015)

            # Contour intervals: 100m minor, 500m major
            if n.type == 'MATH' and n.operation == 'DIVIDE':
                if abs(n.inputs[1].default_value - 75.0) < 5.0:
                    n.inputs[1].default_value = 100.0 # 100m minor isoline
                elif abs(n.inputs[1].default_value - 375.0) < 10.0:
                    n.inputs[1].default_value = 500.0 # 500m major index line

    # Render image
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_preview2.png"))
    scene.render.filepath = out_path
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    
    print(f"Rendering to {out_path}...")
    bpy.ops.render.render(write_still=True)
    print("Render finished.")
    
    # Save blend
    bpy.ops.wm.save_mainfile()
    print("Saved blend file.")

if __name__ == "__main__":
    update_canyon_view()
