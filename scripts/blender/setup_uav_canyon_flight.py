"""
Sets up the DRDO / Predator UAV inside the Top Gun Ladakh Canyon:
1. Imports general_atomics_mq-1_predator_uav.glb into Models/terrain.blend.
2. Creates a master flight control rig 'UAV_Predator_Master'.
3. Generates a 3D spline flight path 'FlightPath_Canyon_Corridor' threading through the gorge.
4. Constrains the UAV to follow the path with authentic banking & yaw.
5. Adds a cinematic Chase Camera 'Camera_UAV_Chase' behind the aircraft.
6. Renders verification frames showing the aircraft in flight.
7. Permanently saved to Models/terrain.blend.
"""

import bpy
import mathutils
import math
import os

def setup_uav_flight():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 250
    scene.render.fps = 30

    # 1. Clean up any previous UAV / FlightPath objects
    for o in list(scene.objects):
        if any(tag in o.name for tag in ['UAV', 'Predator', 'FlightPath', 'Sketchfab', 'MQ-1', 'Object_']):
            bpy.data.objects.remove(o, do_unlink=True)

    # 2. Import GLB
    glb_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Models/general_atomics_mq-1_predator_uav.glb"))
    if not os.path.exists(glb_path):
        print(f"[ERROR] GLB not found at: {glb_path}")
        return

    pre_import_objs = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=glb_path)
    new_objs = [bpy.data.objects[k] for k in bpy.data.objects.keys() if k not in pre_import_objs]

    root_obj = None
    for o in new_objs:
        if o.parent is None:
            root_obj = o
            break

    if not root_obj:
        print("[ERROR] Could not determine UAV root object!")
        return

    # Master UAV Control Empty
    master_uav = bpy.data.objects.new("UAV_Predator_Master", None)
    master_uav.empty_display_type = 'ARROWS'
    master_uav.empty_display_size = 20.0
    scene.collection.objects.link(master_uav)

    root_obj.parent = master_uav
    root_obj.rotation_euler = (0.0, 0.0, 0.0)
    root_obj.scale = (1.0, 1.0, 1.0)

    # 3. Create the Canyon Flight Path Spline
    curve_data = bpy.data.curves.new('FlightPath_Canyon_Corridor', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 32

    polyline = curve_data.splines.new('BEZIER')
    
    # Canyon flight path threading between the high peaks
    waypoints = [
        (-18000.0,  8000.0, 4850.0), # Canyon ingress
        (-15500.0, 11000.0, 4450.0), # Bank around south ridge
        (-12500.0, 14000.0, 4150.0), # Enter central gorge corridor
        (-9500.0,  16800.0, 3880.0), # Lowest canyon run
        (-6500.0,  19800.0, 4050.0), # Climb toward northern pass
    ]

    polyline.bezier_points.add(len(waypoints) - 1)
    for i, wp in enumerate(waypoints):
        pt = polyline.bezier_points[i]
        pt.co = wp
        pt.handle_left_type = 'AUTO'
        pt.handle_right_type = 'AUTO'

    curve_obj = bpy.data.objects.new('FlightPath_Canyon_Corridor', curve_data)
    scene.collection.objects.link(curve_obj)

    # 4. Attach UAV with Follow Path Constraint
    constraint = master_uav.constraints.new(type='FOLLOW_PATH')
    constraint.target = curve_obj
    constraint.use_curve_follow = True
    constraint.forward_axis = 'FORWARD_Y'
    constraint.up_axis = 'UP_Z'
    constraint.use_fixed_location = True

    # Keyframe offset factor (0.0 at frame 1 -> 1.0 at frame 250)
    constraint.offset_factor = 0.0
    constraint.keyframe_insert(data_path="offset_factor", frame=1)
    constraint.offset_factor = 1.0
    constraint.keyframe_insert(data_path="offset_factor", frame=250)

    # Set timeline to frame 120 (mid-canyon run)
    scene.frame_set(120)

    # 5. Create Cinematic Chase Camera
    chase_cam_obj = bpy.data.objects.get("Camera_UAV_Chase")
    if not chase_cam_obj:
        chase_cam_data = bpy.data.cameras.new("Camera_UAV_Chase")
        chase_cam_obj = bpy.data.objects.new("Camera_UAV_Chase", chase_cam_data)
        scene.collection.objects.link(chase_cam_obj)

    chase_cam_obj.data.lens = 32.0
    chase_cam_obj.data.clip_start = 1.0
    chase_cam_obj.data.clip_end = 250000.0

    chase_cam_obj.parent = master_uav
    chase_cam_obj.location = (0.0, -35.0, 8.5) # 35m behind, 8.5m above
    chase_cam_obj.rotation_euler = (math.radians(78.0), 0.0, 0.0)

    # 6. Render View 1: Chase Camera View
    scene.camera = chase_cam_obj
    out_chase = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/uav_chase_canyon_view.png"))
    scene.render.filepath = out_chase
    print(f"[RENDER] Rendering UAV Chase view to: {out_chase}...")
    bpy.ops.render.render(write_still=True)

    # 7. Render View 2: Wide Canyon Recon View
    canyon_cam = bpy.data.objects.get("Camera_Canyon_Recon")
    if canyon_cam:
        scene.camera = canyon_cam
        out_wide = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/uav_wide_recon_view.png"))
        scene.render.filepath = out_wide
        print(f"[RENDER] Rendering UAV Wide Recon view to: {out_wide}...")
        bpy.ops.render.render(write_still=True)

        master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
        scene.render.filepath = master_path
        bpy.ops.render.render(write_still=True)

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] UAV canyon flight simulation saved permanently to Models/terrain.blend!")

if __name__ == "__main__":
    setup_uav_flight()
