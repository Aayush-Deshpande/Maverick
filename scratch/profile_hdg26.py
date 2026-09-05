import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar
pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))
hdg = math.radians(26.0)
fwd = mathutils.Vector((math.sin(hdg), math.cos(hdg), 0.0))

print("Probing ground profile along Heading 26° from spawn:")
for d in range(500, 5000, 500):
    p = pos + fwd * d
    hit, loc, _, _ = radar.raycast(mathutils.Vector((p.x, p.y, 6500.0)), mathutils.Vector((0, 0, -1.0)), 6000.0)
    gz = loc.z if hit else 0.0
    # Flight altitude if diving at -16° pitch:
    dive_alt = 5800.0 - d * math.tan(math.radians(16.0))
    print(f"Dist={d:4d}m | Pos=({p.x:6.0f}, {p.y:6.0f}) | Ground Z={gz:6.1f}m | Dive Alt={dive_alt:6.1f}m | Clearance={dive_alt - gz:6.1f}m")
