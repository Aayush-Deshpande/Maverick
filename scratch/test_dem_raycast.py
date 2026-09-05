import bpy
import mathutils

dem = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
uav = bpy.data.objects.get('UAV_Predator_Master')

print(f"DEM object: {dem.name}, type={dem.type}, dim={dem.dimensions}")
print(f"DEM matrix: {dem.matrix_world}")

# Let's test a raycast directly against the DEM mesh:
# We need world-to-local transformation
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

# Test at ingress point: (-19500, 7000, 5800)
test_pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))
# Downward AGL
hit_dn, loc_dn, dist_agl, _ = probe_dem(test_pos, mathutils.Vector((0, 0, -1)))
print(f"At Ingress (-19500, 7000, 5800): Down hit={hit_dn}, AGL={dist_agl:.1f}m, TerrZ={loc_dn.z if hit_dn else 0:.1f}")

# Forward along canyon corridor (heading 45 deg, towards (+X, +Y))
canyon_fwd = mathutils.Vector((1.0, 1.0, 0.0)).normalized()
hit_fwd, loc_fwd, dist_fwd, norm_fwd = probe_dem(test_pos, canyon_fwd, max_dist=5000.0)
print(f"Forward (45 deg) hit={hit_fwd}, Dist={dist_fwd:.1f}m, HitLoc={loc_fwd}")

# Left and Right
canyon_left = mathutils.Vector((-1.0, 1.0, 0.0)).normalized()
canyon_right = mathutils.Vector((1.0, -1.0, 0.0)).normalized()
hit_l, _, dist_l, _ = probe_dem(test_pos, canyon_left, max_dist=3000.0)
hit_r, _, dist_r, _ = probe_dem(test_pos, canyon_right, max_dist=3000.0)
print(f"Left Dist={dist_l:.1f}m, Right Dist={dist_r:.1f}m")
