"""
Applies Hero Simulation Scaling & Cinematic Telephoto Camera Rig:
1. Scales the Predator UAV to 3.5x Hero Scale (~52m wingspan) for tactical legibility.
2. Repositions the Chase Camera 135m behind and 35m above with a 55mm telephoto lens.
3. Centers the 3D spline flight path directly down the canyon corridor between the towering peaks.
4. Renders cinematic frames showing the UAV flanked by mountain ridges on both sides.
5. Permanently saved to Models/terrain.blend.
"""

import bpy
import mathutils
import math
import os

def apply_hero_scale_and_camera():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    master_uav = bpy.data.objects.get("UAV_Predator_Master")
    if not master_uav:
        print("[ERROR] UAV_Predator_Master not found!")
        return

    # 1. Apply Hero Simulation Scale (3.5x)
    master_uav.scale = (3.5, 3.5, 3.5)
    print(f"[OK] Scaled UAV to {master_uav.scale} (Hero Simulation Scale).")

    # 2. Refine Canyon Flight Spline to thread down the center of the canyon gorge
    curve_obj = bpy.data.objects.get("FlightPath_Canyon_Corridor")
    if curve_obj and curve_obj.data.splines:
        spline = curve_obj.data.splines[0]
        # Precise center-canyon flight corridor waypoints (X, Y, Z)
        waypoints = [
            (-17500.0,  8500.0, 4800.0), # Canyon entry high
            (-15000.0, 11500.0, 4350.0), # Weaving past the south mountain wall
            (-12000.0, 14200.0, 4000.0), # Mid-gorge between peaks
            (-9200.0,  17000.0, 3750.0), # Deep canyon floor trench
            (-6200.0,  19800.0, 3900.0), # Egress into northern basin
        ]
        for i, wp in enumerate(waypoints):
            if i < len(spline.bezier_points):
                pt = spline.bezier_points[i]
                pt.co = wp
                pt.handle_left_type = 'AUTO'
                pt.handle_right_type = 'AUTO'

    # 3. Configure Cinematic Chase Camera
    chase_cam = bpy.data.objects.get("Camera_UAV_Chase")
    if not chase_cam:
        cam_data = bpy.data.cameras.new("Camera_UAV_Chase")
        chase_cam = bpy.data.objects.new("Camera_UAV_Chase", cam_data)
        scene.collection.objects.link(chase_cam)

    # Telephoto compression lens
    chase_cam.data.lens = 55.0 # 55mm cinematic compression
    chase_cam.data.clip_start = 1.0
    chase_cam.data.clip_end = 250000.0

    # Position 135m behind, 35m above the hero UAV
    chase_cam.parent = master_uav
    chase_cam.location = (0.0, -135.0, 35.0)
    chase_cam.rotation_euler = (math.radians(76.5), 0.0, 0.0) # Pitched down looking forward at the drone & canyon

    # Set frame to frame 120 (mid-canyon run)
    scene.frame_set(120)

    # 4. Viewport configuration
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'RENDERED'
                        space.region_3d.view_perspective = 'CAMERA'

    # 5. Render View 1: Cinematic Chase View (Hero Scale + 55mm Telephoto)
    scene.camera = chase_cam
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    out_chase = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/uav_hero_chase_view.png"))
    scene.render.filepath = out_chase
    print(f"[RENDER] Rendering UAV Hero Chase view to: {out_chase}...")
    bpy.ops.render.render(write_still=True)

    master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)

    # 6. Render View 2: Wide Recon View
    recon_cam = bpy.data.objects.get("Camera_Canyon_Recon")
    if recon_cam:
        scene.camera = recon_cam
        out_wide = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/uav_hero_wide_recon.png"))
        scene.render.filepath = out_wide
        print(f"[RENDER] Rendering UAV Hero Wide Recon view to: {out_wide}...")
        bpy.ops.render.render(write_still=True)

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved Hero Scale UAV and Camera permanently to Models/terrain.blend!")

if __name__ == "__main__":
    apply_hero_scale_and_camera()
