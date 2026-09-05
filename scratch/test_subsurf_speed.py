import sys
import time
import bpy
import mathutils

dem = bpy.data.objects.get("Copernicus_DSM_COG_10_N34_00_E077_00_DEM")
sub = dem.modifiers.get("Subsurf_Smooth")

# Test with subsurf enabled
t0 = time.time()
inv = dem.matrix_world.inverted()
hit, loc, _, _ = dem.ray_cast(inv @ mathutils.Vector((-20500, 11500, 6500)), mathutils.Vector((0, 0, -1)), distance=6000)
t_sub = (time.time() - t0) * 1000.0

# Disable subsurf
sub.show_viewport = False
t1 = time.time()
hit2, loc2, _, _ = dem.ray_cast(inv @ mathutils.Vector((-20500, 11500, 6500)), mathutils.Vector((0, 0, -1)), distance=6000)
t_nosub = (time.time() - t1) * 1000.0

print(f"With Subsurf: {t_sub:.2f} ms | Elevation: {(dem.matrix_world @ loc).z if hit else None}")
print(f"Without Subsurf: {t_nosub:.2f} ms | Elevation: {(dem.matrix_world @ loc2).z if hit2 else None}")
