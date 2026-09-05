import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar
print("Tracing river corridor along (dx=0.5, dy=0.866) through valley:")
for d in [-5000, -2500, 0, 2500, 5000, 7500, 10000, 15000]:
    x = -21500.0 + 0.5 * d
    y = 9500.0 + 0.866 * d
    hit, loc, _, _ = radar.raycast(mathutils.Vector((x, y, 6500.0)), mathutils.Vector((0, 0, -1.0)), 6000.0)
    print(f"d = {d:6d}m: (X={x:6.0f}, Y={y:6.0f}) -> Ground Z = {loc.z:6.1f}m (Depth below 5800m = {5800.0 - loc.z:6.1f}m)")
