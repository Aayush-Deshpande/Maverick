import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar
pos = mathutils.Vector((-20000.0, 11500.0, 4100.0))
hdg = math.radians(30.0)

print(f"Starting at canyon entrance: {pos}")
current_p = pos.copy()
current_hdg = hdg

for step in range(12):
    # Probe 3 candidate headings ahead (+1500m)
    best_step_hdg = current_hdg
    min_floor = 99999.0
    
    for offset_deg in [-30, -15, 0, 15, 30]:
        test_hdg = current_hdg + math.radians(offset_deg)
        test_fwd = mathutils.Vector((math.sin(test_hdg), math.cos(test_hdg), 0.0))
        probe_p = current_p + test_fwd * 1500.0
        
        hit, loc, _, _ = radar.raycast(mathutils.Vector((probe_p.x, probe_p.y, 6500.0)), mathutils.Vector((0, 0, -1.0)), 6000.0)
        floor = loc.z if hit else 5000.0
        if floor < min_floor:
            min_floor = floor
            best_step_hdg = test_hdg
            
    current_hdg = best_step_hdg
    fwd = mathutils.Vector((math.sin(current_hdg), math.cos(current_hdg), 0.0))
    current_p += fwd * 1500.0
    print(f"Step {step+1:2d}: Pos=({current_p.x:6.0f}, {current_p.y:6.0f}) | Hdg={math.degrees(current_hdg):5.1f}° | Floor Z={min_floor:6.1f}m (Canyon depth: {5800.0 - min_floor:6.1f}m)")
