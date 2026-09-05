import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar

# Scan grid from X: -25000 to -10000, Y: 5000 to 20000 in steps of 2000m
print("Mapping terrain elevations (Z < 4200m are deep canyon basins):")
deep_points = []
for y in range(5000, 22000, 2000):
    row = []
    for x in range(-25000, -9000, 2000):
        hit, loc, _, _ = radar.raycast(mathutils.Vector((x, y, 6500.0)), mathutils.Vector((0, 0, -1.0)), 6000.0)
        z = loc.z if hit else 5500.0
        row.append(f"{z:4.0f}")
        if z < 4200.0:
            deep_points.append((x, y, z))
    print(f"Y={y:5d}: " + " ".join(row))

print(f"\nFound {len(deep_points)} canyon basin points (Z < 4200m):")
for p in deep_points[:15]:
    print(f"  X={p[0]:6d}, Y={p[1]:6d} -> Elevation {p[2]:.1f}m AMSL")
