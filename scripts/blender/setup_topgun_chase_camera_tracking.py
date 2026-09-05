"""
Top Gun: Maverick World Chase Camera Rig:
1. Unparents the chase camera from the UAV so it is completely independent in world space.
2. Trailing Camera Jet Dynamics: The camera flies independently through the world corridor behind the UAV (trailing by ~18 frames / ~0.6s) with vertical elevation offset.
3. Gyro-Stabilized Horizon with Damped Tracking: The camera points forward tracking the UAV via DAMPED_TRACK.
4. When the UAV banks 28 degrees into canyon turns, the viewer sees the UAV roll and carve through the pass against the stable mountain canyon backdrop, exactly like the movie.
5. Saves permanently to Models/terrain.blend and updates renders.
"""

import bpy
import mathutils
import math
import os

def setup_topgun_chase_tracking():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 600

    uav = bpy.data.objects.get("UAV_Predator_Master")
    chase_cam = bpy.data.objects.get("Camera_UAV_Chase")
    if not uav or not chase_cam:
        print("[ERROR] UAV or Camera not found!")
        return

    # 1. Unparent camera from UAV (Zero rigid connection)
    if chase_cam.parent:
        matrix_world = chase_cam.matrix_world.copy()
        chase_cam.parent = None
        chase_cam.matrix_world = matrix_world
        print("[OK] Unparented camera from UAV: Camera is now an independent world agent.")

    chase_cam.constraints.clear()
    chase_cam.animation_data_clear()

    # 2. Camera Tracking Constraint: DAMPED_TRACK pointing directly at UAV
    track = chase_cam.constraints.new(type='DAMPED_TRACK')
    track.target = uav
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.influence = 1.0

    # 3. Read UAV world positions across all 600 frames
    uav_locs = []
    for f in range(1, 601):
        scene.frame_set(f)
        uav_locs.append(uav.matrix_world.translation.copy())

    # 4. Bake Independent World Camera Flight Path Trailing Behind the UAV
    # Lag behind by 16 frames (~0.53 seconds), elevated by 75m above flight line
    lag_frames = 16
    cam_elevation = 75.0
    cam_distance_boost = 1.15

    chase_cam.animation_data_create()
    cam_action = bpy.data.actions.new(name="TopGun_Chase_Camera_Action")
    chase_cam.animation_data.action = cam_action

    chase_cam.data.lens = 48.0 # 48mm cinematic telephoto
    chase_cam.data.clip_start = 1.0
    chase_cam.data.clip_end = 250000.0

    for f in range(1, 601):
        frame_idx = f - 1
        target_uav_pos = uav_locs[frame_idx]

        # Calculate trailing frame
        trail_idx = (frame_idx - lag_frames) % 600
        trail_pos = uav_locs[trail_idx]

        # Vector from trail position to current UAV
        lead_vec = (target_uav_pos - trail_pos)
        lead_dist = lead_vec.length
        if lead_dist > 0.001:
            back_dir = -lead_vec.normalized()
        else:
            back_dir = mathutils.Vector((0, -1, 0))

        # Position camera behind along the flight trail and elevated
        # Smooth camera position in world space
        cam_world_pos = trail_pos + mathutils.Vector((0, 0, cam_elevation)) + (back_dir * (lead_dist * 0.15))

        chase_cam.location = cam_world_pos
        chase_cam.keyframe_insert(data_path="location", frame=f)

    print("[OK] Successfully baked 600 frames of independent trailing camera pursuit.")

    # 5. Render Verification Frame (Frame 175: Mid-canyon coordinated turn)
    # At this frame, the UAV is banking hard into the turn in front of the camera!
    scene.frame_set(175)
    scene.camera = chase_cam
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080

    out_chase = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/topgun_maverick_chase_final.png"))
    scene.render.filepath = out_chase
    print(f"[RENDER] Rendering Top Gun independent chase view to: {out_chase}...")
    bpy.ops.render.render(write_still=True)

    master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)

    # Save permanently to Models/terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Top Gun independent tracking camera saved permanently to Models/terrain.blend!")

if __name__ == "__main__":
    setup_topgun_chase_tracking()
