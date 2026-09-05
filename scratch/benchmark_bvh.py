import bpy
import mathutils
from mathutils.bvhtree import BVHTree
import time

dem = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')

t0 = time.time()
print("Building BVHTree from DEM...")
# We build BVHTree from evaluated mesh or object:
depsgraph = bpy.context.evaluated_depsgraph_get()
bvh = BVHTree.FromObject(dem, depsgraph)
t_build = time.time() - t0
print(f"BVHTree built in {t_build*1000:.1f} ms!")

# Now benchmark 1000 raycasts:
t1 = time.time()
test_pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))
inv_mat = dem.matrix_world.inverted()
inv_rot = inv_mat.to_3x3()

loc_origin = inv_mat @ test_pos
loc_dir = (inv_rot @ mathutils.Vector((0, 0, -1))).normalized()

for _ in range(1000):
    loc, norm, idx, dist = bvh.ray_cast(loc_origin, loc_dir, 8000.0)

t_rays = time.time() - t1
print(f"1000 raycasts executed in {t_rays*1000:.2f} ms ({t_rays:.6f} ms per raycast)!")
print(f"Result: hit={loc is not None}, dist={(dem.matrix_world @ loc - test_pos).length if loc else 0:.1f}m")
