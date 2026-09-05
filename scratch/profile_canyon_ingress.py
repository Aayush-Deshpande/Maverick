import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar
pos = mathutils.Vector((-20500.0, 11500.0, 5800.0))
hdg = math.radians(45.0)
fwd = mathutils.Vector((math.sin(hdg), math.cos(hdg), 0.0))

print("Probing ground profile from CANYON INGRESS (-20500, 11500) along Heading 45°:")
for d in range(0, 12000, 1000):
    p = pos + fwd * d
    hit, loc, _, _ = radar.raycast(mathutils.Vector((p.x, p.y, 6500.0)), mathutils.Vector((0, 0, -1.0)), 6000.0)
    gz = loc.z if hit else 0.0
    print(f"Dist={d:5d}m | Pos=({p.x:6.0f}, {p.y:6.0f}) | Ground Z={gz:6.1f}m (Canyon depth: {5800.0 - gz:6.1f}m)")
