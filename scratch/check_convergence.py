import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

st = app.FlightState()
st.fault_overheat = True
st.tactical_dive_active = True
st.dive_phase = "LEVEL_SPRINT"
st.pos = mathutils.Vector((-19000.0, 14000.0, 4100.0))
st.dive_target_bearing = math.radians(30.0)
st.cht_c = 135.0

print("Running 400 frames of LEVEL_SPRINT to observe CHT convergence:")
for i in range(400):
    app.update_simulation(st)
    if i % 40 == 0:
        print(f"Frame {i:3d}: Alt={st.pos.z:.1f}m | Throttle={st.throttle_pct:.0f}% | RPM={st.rpm:.0f} | CHT={st.cht_c:.1f}°C (Rate: {st.cht_rate_c_s:+.2f}°C/s) | Basin Loiter: {getattr(st, 'basin_loiter_s', 0.0):.2f}s | Phase: {st.dive_phase}")
