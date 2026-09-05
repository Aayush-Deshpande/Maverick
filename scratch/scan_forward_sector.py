import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar
pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))

print("Scanning FORWARD sector (-45° to +45° of heading 46° -> Azimuth 0° to 90°):")
for deg in range(0, 95, 10):
    ang_rad = math.radians(deg)
    fwd_dir = mathutils.Vector((math.sin(ang_rad), math.cos(ang_rad), 0.0))
    probe_p = pos + fwd_dir * 4000.0
    
    hit_floor, loc_floor, _, _ = radar.raycast(probe_p + mathutils.Vector((0, 0, 500.0)), mathutils.Vector((0, 0, -1.0)), 5000.0)
    floor_z = loc_floor.z if hit_floor else 4800.0
    
    # Check if there is an obstacle ridge directly in between pos and probe_p!
    hit_obs, loc_obs, dist_obs, _ = radar.raycast(pos, fwd_dir, 4000.0)
    
    print(f"Azimuth {deg:2d}°: Floor Z = {floor_z:6.1f}m (Depth: {5800.0 - floor_z:6.1f}m) | Obstacle in between: {'YES at ' + str(round(dist_obs)) + 'm (Z=' + str(round(loc_obs.z)) + 'm)' if hit_obs else 'CLEAR'}")
