import sys
import bpy

dem = bpy.data.objects.get("Copernicus_DSM_COG_10_N34_00_E077_00_DEM")
print("Matrix World:\n", dem.matrix_world)
print("Bound Box:")
for b in dem.bound_box:
    world_b = dem.matrix_world @ bpy.path.mathutils.Vector(b) if hasattr(bpy.path, 'mathutils') else b
    print(" ", b)
