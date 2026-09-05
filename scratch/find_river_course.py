import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar
valley_center = mathutils.Vector((-21500.0, 9500.0, 5800.0))

print("Scanning valley floor from center (-21500, 9500) to find river course:")
for deg in range(0, 360, 30):
    ang_rad = math.radians(deg)
    fwd = mathutils.Vector((math.sin(ang_rad), math.cos(ang_rad), 0.0))
    p = valley_center + fwd * 3000.0
    hit, loc, _, _ = radar.raycast(mathutils.Vector((p.x, p.y, 6500.0)), mathutils.Vector((0, 0, -1.0)), 6000.0)
    print(f"Heading {deg:3d}° -> Ground Z: {loc.z:6.1f}m (Canyon depth: {5800.0 - loc.z:6.1f}m)")
