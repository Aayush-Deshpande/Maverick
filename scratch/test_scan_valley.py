import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar
pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))

print("Testing Big Valley Scan from Ingress (-19500, 7000, 5800):")
for deg in range(0, 360, 30):
    ang_rad = math.radians(deg)
    fwd_dir = mathutils.Vector((math.sin(ang_rad), math.cos(ang_rad), 0.0)).normalized()
    probe_p = pos + fwd_dir * 4200.0
    
    hit_floor, loc_floor, _, _ = radar.raycast(probe_p + mathutils.Vector((0, 0, 500.0)), mathutils.Vector((0, 0, -1.0)), 5000.0)
    floor_z = loc_floor.z if hit_floor else 4600.0
    depth = max(0.0, 5800.0 - floor_z)
    
    left_perp = mathutils.Vector((-fwd_dir.y, fwd_dir.x, 0.0)).normalized()
    right_perp = -left_perp
    wall_origin = mathutils.Vector((probe_p.x, probe_p.y, floor_z + 150.0))
    hit_wl, _, dist_wl, _ = radar.raycast(wall_origin, left_perp, 4000.0)
    hit_wr, _, dist_wr, _ = radar.raycast(wall_origin, right_perp, 4000.0)
    
    width = (dist_wl if hit_wl else 4000.0) + (dist_wr if hit_wr else 4000.0)
    print(f"Hdg {deg:3d}°: Floor Z = {floor_z:6.1f}m | Depth = {depth:6.1f}m | Width = {width:6.1f}m (L: {dist_wl if hit_wl else 4000.0:5.0f}m, R: {dist_wr if hit_wr else 4000.0:5.0f}m)")
