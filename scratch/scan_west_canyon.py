import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar
start_pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))

print("Detailed scan between 280° and 330°:")
for hdg_deg in [280, 290, 300, 310, 315, 320, 325]:
    hdg_rad = math.radians(hdg_deg)
    fwd = mathutils.Vector((math.sin(hdg_rad), math.cos(hdg_rad), 0.0))
    print(f"\n--- HEADING {hdg_deg:3d}° ---")
    for dist in [1000, 2000, 3500, 5000, 7500]:
        p = start_pos + fwd * dist
        hit, loc, _, _ = radar.raycast(mathutils.Vector((p.x, p.y, 6500.0)), mathutils.Vector((0, 0, -1.0)), 6000.0)
        gz = loc.z if hit else 0.0
        depth = 5800.0 - gz
        print(f"  Dist {dist:4d}m: Ground Z = {gz:6.1f}m (Canyon depth = {depth:6.1f}m)")
