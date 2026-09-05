import sys
import bpy
import mathutils

dem = bpy.data.objects.get("Copernicus_DSM_COG_10_N34_00_E077_00_DEM")
mod = dem.modifiers.get("DEM")
tex = mod.texture

W_X = 92102.3359
W_Y = 111123.4688

def get_elevation_fast(x, y):
    u = (x + (W_X * 0.5)) / W_X
    v = (y + (W_Y * 0.5)) / W_Y
    val = tex.evaluate((u, v, 0.0))
    return val[0]

inv = dem.matrix_world.inverted()
test_points = [
    (-20500.0, 11500.0),
    (-19500.0, 7000.0),
    (-15000.0, 15000.0),
    (-11000.0, 19000.0),
]

print("Comparing Fast Texture Elevation vs Slow Mesh Raycast:")
for x, y in test_points:
    z_fast = get_elevation_fast(x, y)
    hit, loc, _, _ = dem.ray_cast(inv @ mathutils.Vector((x, y, 6500)), mathutils.Vector((0, 0, -1)), distance=6000)
    z_ray = (dem.matrix_world @ loc).z if hit else None
    print(f"Pos ({x:6.0f}, {y:6.0f}): Fast Z = {z_fast:7.2f}m | Raycast Z = {z_ray:7.2f}m | Diff = {abs(z_fast - (z_ray or 0)):.2f}m")
