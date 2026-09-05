import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar
start_pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))

print("Detailed scan between 330° and 30° around North:")
for hdg_deg in [330, 340, 350, 0, 10, 20, 30]:
    hdg_rad = math.radians(hdg_deg)
    fwd = mathutils.Vector((math.sin(hdg_rad), math.cos(hdg_rad), 0.0))
    print(f"\n--- HEADING {hdg_deg:3d}° ---")
    for dist in [1500, 3000, 5000, 7000, 9000]:
        p = start_pos + fwd * dist
        hit, loc, _, _ = radar.raycast(mathutils.Vector((p.x, p.y, 6500.0)), mathutils.Vector((0, 0, -1.0)), 6000.0)
        gz = loc.z if hit else 0.0
        depth = 5800.0 - gz
        print(f"  Dist {dist:4d}m: Ground Z = {gz:6.1f}m (Canyon depth = {depth:6.1f}m)")
