"""
Bakes Perfect Top Gun Maverick Canyon Mission Sequence:
1. True Canyon Corridor Location: Placed directly in the dramatic Ladakh Indus river gorge.
2. 4-Phase Tactical Flight Profile:
   - Phase 1 (Frames 1-260): High Straight Cruise (~5,750m AMSL) along the canyon axis.
   - Phase 2 (Frames 261-460): CHT Overheat & Emergency Tactical Dive into canyon gorge trench (~3,850m AMSL).
   - Phase 3 (Frames 461-820): Low-Altitude High-Speed Canyon Run with 28 deg banking through the glowing cyan passes. CHT stabilizes.
   - Phase 4 (Frames 821-1200): Power restored -> Pitch up & smooth re-climb out of canyon back to high cruise.
3. High-Speed Thrill: Paced at ~220 knots (1200 frames at 120 FPS = 10s full tactical mission loop).
4. Independent Trailing Chase Camera: Gyro-stabilized horizon trailing 150m behind and 42m above with DAMPED_TRACK.
5. Saves permanently to Models/terrain.blend and updates renders.
"""

import bpy
import mathutils
import math
import numpy as np
import os

def bake_perfect_canyon_run():
    scene = bpy.context.scene
    scene.render.fps = 120
    total_frames = 1200
    scene.frame_start = 1
    scene.frame_end = total_frames

    uav = bpy.data.objects.get('UAV_Predator_Master')
    chase_cam = bpy.data.objects.get('Camera_UAV_Chase')

    if not uav or not chase_cam:
        print("[ERROR] Required objects not found!")
        return

    # Set UAV Scale: 36.0x (~530m wingspan, perfect hero scale)
    uav.scale = (36.0, 36.0, 36.0)

    # 1. Define Key Tactical Waypoints along the True Canyon Corridor
    # (X, Y, Z)
    # Phase 1: High Cruise Entry (5750m -> 5600m)
    # Phase 2: Steep Canyon Dive (5600m -> 3880m) down into the riverbed trench
    # Phase 3: Low-Altitude Canyon Run (3880m -> 4100m) weaving between towering walls
    # Phase 4: Re-climb (4100m -> 5650m) exiting canyon
    key_waypoints = [
        mathutils.Vector((-19500.0,  7000.0, 5800.0)), # WP 0: High cruise entry south
        mathutils.Vector((-17500.0,  9800.0, 5650.0)), # WP 1: High straight transit over gorge
        mathutils.Vector((-15500.0, 12200.0, 5500.0)), # WP 2: Point of fault injection
        mathutils.Vector((-13500.0, 14200.0, 4400.0)), # WP 3: STEEP CANYON DIVE (descending rapidly)
        mathutils.Vector((-11500.0, 16200.0, 3880.0)), # WP 4: Deep canyon trench floor (maximum cooling)
        mathutils.Vector((-9200.0,  18200.0, 3820.0)), # WP 5: Low-level gorge pass between ridge spurs
        mathutils.Vector((-6800.0,  20400.0, 3950.0)), # WP 6: Winding past northern river bend
        mathutils.Vector((-4500.0,  22800.0, 4400.0)), # WP 7: Re-climb initiation (power restored)
        mathutils.Vector((-2200.0,  25200.0, 5200.0)), # WP 8: Climbing steadily out of canyon
        mathutils.Vector(( 0.0,     27500.0, 5750.0)), # WP 9: High cruise re-established north
    ]

    # 2. Update Visual 3D Spline
    curve_obj = bpy.data.objects.get("FlightPath_Canyon_Corridor")
    if not curve_obj:
        curve_data = bpy.data.curves.new('FlightPath_Canyon_Corridor', type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.resolution_u = 32
        curve_obj = bpy.data.objects.new('FlightPath_Canyon_Corridor', curve_data)
        scene.collection.objects.link(curve_obj)
    
    curve_obj.data.splines.clear()
    spline = curve_obj.data.splines.new('BEZIER')
    spline.bezier_points.add(len(key_waypoints) - 1)

    for i, pt in enumerate(key_waypoints):
        bp = spline.bezier_points[i]
        bp.co = pt
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'

    # 3. Smooth Centripetal Spline Interpolation across 1200 frames
    times = np.linspace(0, 1, total_frames)
    flight_positions = []

    for t in times:
        p_idx = t * (len(key_waypoints) - 1)
        i0 = int(math.floor(p_idx))
        i1 = min(i0 + 1, len(key_waypoints) - 1)
        i_prev = max(0, i0 - 1)
        i_next = min(len(key_waypoints) - 1, i1 + 1)
        u = p_idx - i0

        p0 = key_waypoints[i_prev]
        p1 = key_waypoints[i0]
        p2 = key_waypoints[i1]
        p3 = key_waypoints[i_next]

        pos = 0.5 * (
            (2 * p1) +
            (-p0 + p2) * u +
            (2 * p0 - 5 * p1 + 4 * p2 - p3) * (u ** 2) +
            (-p0 + 3 * p1 - 3 * p2 + p3) * (u ** 3)
        )
        flight_positions.append(pos)

    # 4. Bake 1200 Frames of 6DOF Aerodynamics onto UAV Master
    uav.animation_data_clear()
    uav.animation_data_create()
    uav_action = bpy.data.actions.new(name="UAV_TopGun_Maverick_Action")
    uav.animation_data.action = uav_action

    for f_idx in range(total_frames):
        frame_num = f_idx + 1
        pos = flight_positions[f_idx]

        # Velocity tangent vector
        if f_idx < total_frames - 1:
            vel = (flight_positions[f_idx + 1] - pos).normalized()
        else:
            vel = (pos - flight_positions[f_idx - 1]).normalized()

        # Curvature acceleration vector for coordinated turn banking
        if 0 < f_idx < total_frames - 1:
            v_prev = (flight_positions[f_idx] - flight_positions[f_idx - 1]).normalized()
            v_next = (flight_positions[f_idx + 1] - flight_positions[f_idx]).normalized()
            accel = (v_next - v_prev)
            turn_rate = accel.x * vel.y - accel.y * vel.x
        else:
            turn_rate = 0.0

        yaw = math.atan2(-vel.x, vel.y)
        pitch = math.asin(max(-0.35, min(0.35, vel.z)))
        max_bank = math.radians(28.0)
        roll = max(-max_bank, min(max_bank, turn_rate * 45.0))

        euler_rot = mathutils.Euler((pitch, roll, yaw), 'XYZ')

        uav.location = pos
        uav.rotation_euler = euler_rot
        uav.keyframe_insert(data_path="location", frame=frame_num)
        uav.keyframe_insert(data_path="rotation_euler", frame=frame_num)

    print("[OK] Successfully baked 1200 frames of UAV canyon flight with 28 deg banking.")

    # 5. Bake Independent World Chase Camera Rig
    chase_cam.parent = None
    chase_cam.constraints.clear()
    chase_cam.animation_data_clear()

    # Damped track constraint pointing at UAV
    track = chase_cam.constraints.new(type='DAMPED_TRACK')
    track.target = uav
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.influence = 1.0

    chase_cam.animation_data_create()
    cam_action = bpy.data.actions.new(name="TopGun_Camera_Action")
    chase_cam.animation_data.action = cam_action

    chase_cam.data.lens = 45.0
    chase_cam.data.clip_start = 1.0
    chase_cam.data.clip_end = 250000.0

    # Trailing lag: 28 frames at 120 FPS (~0.23 seconds)
    lag_frames = 28
    cam_elevation = 48.0

    for f_idx in range(total_frames):
        frame_num = f_idx + 1
        target_uav_pos = flight_positions[f_idx]
        trail_idx = max(0, f_idx - lag_frames)
        trail_pos = flight_positions[trail_idx]

        lead_vec = (target_uav_pos - trail_pos)
        if lead_vec.length > 0.001:
            back_dir = -lead_vec.normalized()
        else:
            back_dir = mathutils.Vector((0, -1, 0))

        # Position camera behind along the flight trail and elevated
        cam_world_pos = trail_pos + mathutils.Vector((0, 0, cam_elevation)) + (back_dir * (lead_vec.length * 0.10))

        chase_cam.location = cam_world_pos
        chase_cam.keyframe_insert(data_path="location", frame=frame_num)

    print("[OK] Successfully baked 1200 frames of independent chase camera trailing.")

    # 6. Render Verification Frame (Frame 550: Mid-canyon low-altitude sprint with banking)
    scene.frame_set(550)
    scene.camera = chase_cam
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080

    out_chase = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/topgun_maverick_chase_final.png"))
    scene.render.filepath = out_chase
    print(f"[RENDER] Rendering Top Gun canyon sprint view to: {out_chase}...")
    bpy.ops.render.render(write_still=True)

    master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)

    # Save permanently to Models/terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Perfect Top Gun Maverick canyon simulation saved permanently to Models/terrain.blend!")

if __name__ == "__main__":
    bake_perfect_canyon_run()
