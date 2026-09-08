"""
Iteration 13 Ground-Truth Master Multi-Vantage Render & Verification Script for Nubra Valley
Renders 5 distinct ground-truth camera views into renders/nubra_iteration13/
Using setup_nubra_hyperreal_v10 (Definitive Master)
Saves production state into Models/terrain.blend
"""

import bpy
import mathutils
import math
import os
import sys

sys.path.insert(0, os.path.abspath("scratch"))
import setup_nubra_hyperreal_v10

def render_iteration13_views():
    # Apply Master Engine v10
    setup_nubra_hyperreal_v10.setup_nubra_hyperreal_v10()

    scene = bpy.context.scene
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    out_dir = os.path.abspath("renders/nubra_iteration13")
    os.makedirs(out_dir, exist_ok=True)

    uav = bpy.data.objects.get("UAV_Predator_Master")
    dem = bpy.data.objects.get("Copernicus_DSM_COG_10_N34_00_E077_00_DEM")

    cam = bpy.data.objects.get("Camera_UAV_Chase")
    if not cam:
        cam_data = bpy.data.cameras.new("Camera_UAV_Chase")
        cam = bpy.data.objects.new("Camera_UAV_Chase", cam_data)
        bpy.context.collection.objects.link(cam)
    scene.camera = cam
    cam.data.clip_start = 0.5
    cam.data.clip_end = 250000.0

    def get_ground_z(x, y):
        mw = dem.matrix_world
        inv_mw = mw.inverted()
        ray_origin = inv_mw @ mathutils.Vector((x, y, 7000.0))
        ray_dir = inv_mw.to_3x3() @ mathutils.Vector((0, 0, -1.0))
        hit, loc, norm, idx = dem.ray_cast(ray_origin, ray_dir)
        if hit:
            return (mw @ loc).z
        return 3100.0

    # ─────────────────────────────────────────────────────────────────────────
    # VIEW 1: HERO CHASE FLIGHT VIEW (Valley Axis & Braided River Ingress)
    # UAV centered in lower-mid frame, flying 280m AGL along river braid
    # ─────────────────────────────────────────────────────────────────────────
    uav_x, uav_y = 2800.0, 6500.0
    ground_z = get_ground_z(uav_x, uav_y)
    uav_z = ground_z + 280.0
    uav_pos = mathutils.Vector((uav_x, uav_y, uav_z))

    hdg_deg = 38.0
    hdg_rad = math.radians(hdg_deg)
    cos_h = math.cos(hdg_rad)
    sin_h = math.sin(hdg_rad)
    fwd = mathutils.Vector((sin_h, cos_h, 0.0)).normalized()
    right = mathutils.Vector((cos_h, -sin_h, 0.0)).normalized()
    up = mathutils.Vector((0.0, 0.0, 1.0))
    rot_mat = mathutils.Matrix((-right, -fwd, up)).transposed()

    if uav:
        uav.location = uav_pos
        uav.scale = (1.553363, 1.553363, 1.553363)
        uav.matrix_world = mathutils.Matrix.Translation(uav_pos) @ rot_mat.to_4x4()
        uav.hide_render = False

    cam_dist = 16.5
    cam_height = 4.8
    look_dist = 40.0
    cam.location = uav_pos - fwd * cam_dist + up * cam_height
    look_target = uav_pos + fwd * look_dist + up * 4.0
    cam_dir = (look_target - cam.location).normalized()
    cam.rotation_euler = cam_dir.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 22.0
    bpy.context.view_layer.update()

    out_hero = os.path.join(out_dir, "01_hero_chase_valley_axis.png")
    scene.render.filepath = out_hero
    bpy.ops.render.render(write_still=True)
    print(f"[RENDERED] View 1 -> {out_hero}")

    # ─────────────────────────────────────────────────────────────────────────
    # VIEW 2: VALLEY FLOOR PERSPECTIVE (Matching sarangib-mountain-7565364.jpg)
    # ─────────────────────────────────────────────────────────────────────────
    if uav:
        uav.hide_render = True

    v2_x, v2_y = 3200.0, 6800.0
    v2_gz = get_ground_z(v2_x, v2_y)
    cam.location = mathutils.Vector((v2_x, v2_y, v2_gz + 2.5))
    look_target_2 = mathutils.Vector((v2_x + 3000.0, v2_y + 4500.0, v2_gz + 1200.0))
    cam_dir_2 = (look_target_2 - cam.location).normalized()
    cam.rotation_euler = cam_dir_2.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 32.0
    bpy.context.view_layer.update()

    out_v2 = os.path.join(out_dir, "02_valley_floor_portal.png")
    scene.render.filepath = out_v2
    bpy.ops.render.render(write_still=True)
    print(f"[RENDERED] View 2 -> {out_v2}")

    # ─────────────────────────────────────────────────────────────────────────
    # VIEW 3: HUNDER DUNES OVERLOOK (Matching sarangib-river-7833049.jpg)
    # ─────────────────────────────────────────────────────────────────────────
    v3_x, v3_y = 1200.0, 5200.0
    v3_gz = get_ground_z(v3_x, v3_y)
    cam.location = mathutils.Vector((v3_x, v3_y, v3_gz + 45.0))
    look_target_3 = mathutils.Vector((v3_x + 2500.0, v3_y + 3500.0, v3_gz + 250.0))
    cam_dir_3 = (look_target_3 - cam.location).normalized()
    cam.rotation_euler = cam_dir_3.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 28.0
    bpy.context.view_layer.update()

    out_v3 = os.path.join(out_dir, "03_hunder_dunes_overlook.png")
    scene.render.filepath = out_v3
    bpy.ops.render.render(write_still=True)
    print(f"[RENDERED] View 3 -> {out_v3}")

    # ─────────────────────────────────────────────────────────────────────────
    # VIEW 4: BRAIDED RIVER & TALUS SCREE PANORAMA (Matching sarangib-river-7548686.jpg)
    # ─────────────────────────────────────────────────────────────────────────
    v4_x, v4_y = 5800.0, 9200.0
    v4_gz = get_ground_z(v4_x, v4_y)
    cam.location = mathutils.Vector((v4_x, v4_y, v4_gz + 180.0))
    look_target_4 = mathutils.Vector((v4_x - 3000.0, v4_y + 2000.0, v4_gz - 80.0))
    cam_dir_4 = (look_target_4 - cam.location).normalized()
    cam.rotation_euler = cam_dir_4.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 26.0
    bpy.context.view_layer.update()

    out_v4 = os.path.join(out_dir, "04_braided_river_scree_panorama.png")
    scene.render.filepath = out_v4
    bpy.ops.render.render(write_still=True)
    print(f"[RENDERED] View 4 -> {out_v4}")

    # ─────────────────────────────────────────────────────────────────────────
    # VIEW 5: HIGH REFLECTION LAKE PORTAL (Matching sudipjotshi-lake-8908444.jpg)
    # ─────────────────────────────────────────────────────────────────────────
    v5_x, v5_y = 2500.0, 6900.0
    v5_gz = get_ground_z(v5_x, v5_y)
    cam.location = mathutils.Vector((v5_x, v5_y, v5_gz + 1.2))
    look_target_5 = mathutils.Vector((v5_x + 1500.0, v5_y + 4000.0, v5_gz + 1100.0))
    cam_dir_5 = (look_target_5 - cam.location).normalized()
    cam.rotation_euler = cam_dir_5.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 24.0
    bpy.context.view_layer.update()

    out_v5 = os.path.join(out_dir, "05_lake_reflection_portal.png")
    scene.render.filepath = out_v5
    bpy.ops.render.render(write_still=True)
    print(f"[RENDERED] View 5 -> {out_v5}")

    if uav:
        uav.hide_render = False

    # Save definitive production state to Models/terrain.blend
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
    print(f"[SUCCESS] Iteration 13 Definitive Master state saved to {bpy.data.filepath}")

if __name__ == "__main__":
    render_iteration13_views()
