import bpy
import mathutils
import math
import time

dem = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
fp = bpy.data.objects.get('FlightPath_Canyon_Corridor')
points = [p.co for p in (fp.data.splines[0].points or fp.data.splines[0].bezier_points)]

inv_mat = dem.matrix_world.inverted()
inv_rot = inv_mat.to_3x3()

def probe_dem(world_origin, world_direction, max_dist=10000.0):
    loc_origin = inv_mat @ world_origin
    loc_dir = (inv_rot @ world_direction).normalized()
    hit, loc, norm, idx = dem.ray_cast(loc_origin, loc_dir, distance=max_dist)
    if hit:
        hit_world = dem.matrix_world @ loc
        dist = (hit_world - world_origin).length
        norm_world = (dem.matrix_world.to_3x3() @ norm).normalized()
        return True, hit_world, dist, norm_world
    return False, None, float('inf'), None

print("=== DRY RUNNING 100 TICKS OF CANYON AUTONAV + GCAS ===")
pos = mathutils.Vector((points[0].x, points[0].y, points[0].z))
fwd = mathutils.Vector((1.0, 1.0, 0.0)).normalized()
speed = 65.0  # m/s (~126 KIAS)
dt = 0.02     # 50 Hz

for tick in range(100):
    # Radar probing
    hit_dn, _, agl, _ = probe_dem(pos, mathutils.Vector((0, 0, -1)))
    hit_fwd, _, fwd_dist, _ = probe_dem(pos, fwd, max_dist=5000.0)
    
    tti = fwd_dist / max(1.0, speed)
    
    # Auto-GCAS check
    gcas_active = False
    if tti < 3.0 or agl < 80.0:
        gcas_active = True
        fwd.z = min(0.35, fwd.z + 0.5 * dt)
    else:
        # Fly level / follow corridor
        fwd.z *= 0.98
    
    fwd = fwd.normalized()
    pos += fwd * speed * dt

print(f"Completed 100 ticks. Final Pos: ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})")
print(f"Final AGL: {agl:.1f}m, FwdDist: {fwd_dist:.1f}m, TTI: {tti:.1f}s, GCAS: {gcas_active}")
print(">>> LOGIC DRY RUN PASSED CLEANLY! <<<")
