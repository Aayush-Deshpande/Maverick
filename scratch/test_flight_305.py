import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar
st = app.FlightState()

# Update find_deepest_canyon_heading to return the true deepest canyon gorge (305°)
target_bearing = math.radians(305.0)
st.fault_overheat = True
st.tactical_dive_active = True
st.dive_phase = "SEEK_CANYON"
st.dive_target_bearing = target_bearing
st.target_canyon_alt = 4100.0
st.cht_c = 136.0

print(f"Starting test at Pos={st.pos}, Heading={math.degrees(st.heading_rad):.1f}°")

altitudes = []
pitches = []
phases = []

for tick in range(300):
    app.update_simulation(st)
    altitudes.append(st.pos.z)
    pitches.append(math.degrees(st.pitch_rad))
    phases.append(st.dive_phase)
    
    if tick % 25 == 0:
        print(f"Tick {tick:3d}: Phase={st.dive_phase:12s} | Alt={st.pos.z:6.1f}m | AGL={st.agl_m:5.1f}m | Pitch={math.degrees(st.pitch_rad):5.1f}° | Hdg={math.degrees(st.heading_rad):5.1f}° | CHT={st.cht_c:5.1f}°C (Rate: {st.cht_rate_c_s:+4.1f}°C/s)")

min_alt = min(altitudes)
max_pitch_down = min(pitches)
print(f"\nFinal State: Alt={st.pos.z:.1f}m, Min Alt Reached={min_alt:.1f}m, Max Dive Pitch={max_pitch_down:.1f}°")
print(f"Total Altitude Drop: {5800.0 - min_alt:.1f}m")
print(f"Final CHT: {st.cht_c:.1f}°C")
