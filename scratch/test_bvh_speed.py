import sys
import time
import bpy
import mathutils
from mathutils.bvhtree import BVHTree

dem = bpy.data.objects.get("Copernicus_DSM_COG_10_N34_00_E077_00_DEM")
dg = bpy.context.evaluated_depsgraph_get()

t0 = time.time()
bvh = BVHTree.FromObject(dem, dg)
t_build = (time.time() - t0) * 1000.0

times = []
for _ in range(50):
    t = time.time()
    bvh.ray_cast(mathutils.Vector((0, 0, 6000)), mathutils.Vector((0, 0, -1)), 1000)
    times.append((time.time() - t) * 1000.0)

avg_bvh = sum(times) / len(times)
print(f"BVHTree Build: {t_build:.2f} ms")
print(f"BVHTree Raycast Average across 50 rays: {avg_bvh:.4f} ms per raycast!")
