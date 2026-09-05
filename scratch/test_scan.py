import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar
start_pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))

best_heading = 0.0
lowest_ground_z = 99999.0

for deg in range(0, 360, 15):
    ang_rad = math.radians(deg)
    fwd_dir = mathutils.Vector((math.sin(ang_rad), math.cos(ang_rad), 0.0)).normalized()
    probe_point = start_pos + fwd_dir * 3200.0
    hit, loc, _, _ = radar.raycast(probe_point + mathutils.Vector((0, 0, 400.0)), mathutils.Vector((0, 0, -1.0)), 4000.0)
    if hit:
        print(f"Azimuth {deg:3d}° -> Ground Z: {loc.z:6.1f}m (Canyon depth: {5800.0 - loc.z:6.1f}m)")
        if loc.z < lowest_ground_z:
            lowest_ground_z = loc.z
            best_heading = ang_rad

print(f"\nDeepest canyon gorge found at: {math.degrees(best_heading):.1f}° (Ground Z: {lowest_ground_z:.1f}m, Depth: {5800.0 - lowest_ground_z:.1f}m)")
