import sys
import math

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar
st = app.FlightState()

best_hdg, gorge_z = app.find_deepest_canyon_heading(st.pos, radar)
st.fault_overheat = True
st.tactical_dive_active = True
st.dive_phase = "SEEK_CANYON"
st.dive_target_bearing = best_hdg
st.target_canyon_alt = max(3850.0, gorge_z + 80.0)

for _ in range(40):
    app.update_simulation(st)

for _ in range(120):
    app.update_simulation(st)

print(f"End of descent: Pos = {st.pos}")
hit, loc, _, _ = radar.raycast(st.pos + math.Vector((0, 0, 400.0)) if hasattr(math, 'Vector') else app.mathutils.Vector((st.pos.x, st.pos.y, 6500.0)), app.mathutils.Vector((0, 0, -1.0)), 6000.0)
print(f"Ground Z at this location: {loc.z if hit else 'None'}")
