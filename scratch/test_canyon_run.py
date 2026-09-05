import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

st = app.FlightState()
radar = app.radar

# Canyon entry waypoint and corridor axis
canyon_entry = mathutils.Vector((-20250.0, 11665.0, 3950.0))
canyon_corridor_axis = math.radians(30.0)

print(f"Initial State: Pos={st.pos}, Alt={st.pos.z}m, CHT={st.cht_c}°C")

# Trigger CHT Overheat [1]
st.fault_overheat = True
st.tactical_dive_active = True
st.dive_phase = "SEEK_CANYON"
st.dive_target_bearing = math.atan2(canyon_entry.x - st.pos.x, canyon_entry.y - st.pos.y)
st.target_canyon_alt = 3950.0
st.cht_c = 136.0

print(f"Target Bearing to canyon entry: {math.degrees(st.dive_target_bearing):.1f}°")

altitudes = []
pitches = []
chts = []
phases = []

for tick in range(250):
    app.update_simulation(st)
    altitudes.append(st.pos.z)
    pitches.append(math.degrees(st.pitch_rad))
    chts.append(st.cht_c)
    phases.append(st.dive_phase)

    # When reaching canyon entry, turn down the canyon river axis (30°)
    if st.pos.y > 11000.0 and st.dive_phase in ["DESCENT", "LEVEL_SPRINT"]:
        st.dive_target_bearing = canyon_corridor_axis

    if tick % 25 == 0 or tick == 249:
        print(f"Tick {tick:3d}: Phase={st.dive_phase:12s} | Pos=({st.pos.x:6.0f}, {st.pos.y:6.0f}, {st.pos.z:5.0f}m) | Pitch={math.degrees(st.pitch_rad):5.1f}° | Hdg={math.degrees(st.heading_rad):5.1f}° | CHT={st.cht_c:5.1f}°C (Rate: {st.cht_rate_c_s:+4.1f}°C/s)")

min_alt = min(altitudes)
print(f"\nResults: Min Alt Reached = {min_alt:.1f}m (Drop of {5800.0 - min_alt:.1f}m)")
print(f"Final CHT = {st.cht_c:.1f}°C (Cooldown of {136.0 - st.cht_c:.1f}°C)")
assert 5800.0 - min_alt > 1200.0, "UAV must dive down by at least 1,200m!"
print("✓ Full canyon flight test verified successfully!")
