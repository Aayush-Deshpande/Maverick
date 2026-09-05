import bpy
import mathutils

dem = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
fp = bpy.data.objects.get('FlightPath_Canyon_Corridor')
spline = fp.data.splines[0]
points = [p.co for p in (spline.points or spline.bezier_points)]

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

print("=== TESTING 10 CANYON CORRIDOR WAYPOINTS ===")
for i, pt in enumerate(points):
    pos = mathutils.Vector((pt.x, pt.y, pt.z))
    # Down ray
    hit_dn, loc_dn, agl, _ = probe_dem(pos, mathutils.Vector((0, 0, -1)))
    terr_z = loc_dn.z if hit_dn else 0
    # Next waypoint direction
    if i < len(points) - 1:
        next_pt = points[i + 1]
        fwd_dir = (mathutils.Vector((next_pt.x, next_pt.y, next_pt.z)) - pos).normalized()
    else:
        fwd_dir = mathutils.Vector((1, 1, 0)).normalized()
    
    hit_fwd, _, dist_fwd, _ = probe_dem(pos, fwd_dir, max_dist=5000.0)
    print(f"WP {i+1:2d} ({pos.x:7.0f}, {pos.y:7.0f}, {pos.z:5.0f}): TerrZ={terr_z:5.0f} AGL={agl:5.0f}m | FwdDist={dist_fwd:6.1f}m")
