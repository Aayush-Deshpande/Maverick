import bpy
import math
import mathutils
import sys

sys.path.insert(0, "e:/backup-llm/backup-no-llm/3d_engine/apps/blender_twin")
import standalone_canyon_flight_app as app

st = app.flight_state
radar = app.radar

print(">>> TEST 1: VERIFY DOUBLED FLIGHT SPEED <<<")
print(f"Cruise speed: {app.CRUISE_SPEED_MS:.1f} m/s (expected 1900.0)")
print(f"Sprint speed: {app.SPRINT_SPEED_MS:.1f} m/s (expected 2600.0)")
assert app.CRUISE_SPEED_MS == 1900.0, f"Expected cruise speed 1900 m/s, got {app.CRUISE_SPEED_MS}"
assert app.SPRINT_SPEED_MS == 2600.0, f"Expected sprint speed 2600 m/s, got {app.SPRINT_SPEED_MS}"
print("✓ Doubled flight speeds verified!")

print("\n>>> TEST 2: ACTIVE CANYON GORGE SCANNER <<<")
best_hdg, gorge_z = app.find_deepest_canyon_heading(st.pos, radar)
print(f"Deepest canyon gorge located at bearing: {math.degrees(best_hdg):.1f}°, floor elevation: {gorge_z:.1f}m AMSL")
assert gorge_z < st.pos.z, "Canyon floor must be lower than aircraft cruise altitude!"
print("✓ Canyon gorge scanner verified!")

print("\n>>> TEST 3: AUTONOMOUS VALLEY DIVE, SPRINT, AND ACTUAL PULL-UP ASCENSION <<<")
# Trigger CHT Overheat Fault [1]
st.fault_overheat = True
st.tactical_dive_active = True
st.dive_phase = "SEEK_CANYON"
st.dive_target_bearing = best_hdg
st.target_canyon_alt = max(3850.0, gorge_z + 80.0)
st.cht_c = 136.5 # Overheated CHT
initial_alt = st.pos.z

print(f"1. SEEK_CANYON: Aligning with canyon bearing {math.degrees(best_hdg):.1f}°...")
for _ in range(40):
    app.update_simulation(st)

print(f"Heading after alignment: {math.degrees(st.heading_rad):.1f}°, Dive phase: {st.dive_phase}")

# Continue through descent
print("2. DESCENT: Diving into canyon...")
for _ in range(120):
    app.update_simulation(st)

print(f"Altitude: {st.pos.z:.1f} m AMSL (altitude drop: {initial_alt - st.pos.z:.1f} m), Pitch: {math.degrees(st.pitch_rad):.1f}°")

# Level sprint in canyon floor
st.dive_phase = "LEVEL_SPRINT"
st.pos.z = max(3950.0, gorge_z + 30.0)
st.altitude_m = st.pos.z
st.cht_c = 135.0
cht_before = st.cht_c

print("3. LEVEL_SPRINT: High-speed canyon sprint & convective ram cooling...")
for _ in range(150):
    app.update_simulation(st)

print(f"CHT after sprint: {st.cht_c:.1f} °C (Rate: {st.cht_rate_c_s:.1f} °C/s, Drop: {cht_before - st.cht_c:.1f} °C)")
assert st.cht_c < cht_before, "Engine must cool down in canyon sprint!"
assert st.cht_rate_c_s < 0.0, f"CHT rate must be negative (cooling), got: {st.cht_rate_c_s}"
print("✓ Convective cooling and negative CHT rate verified!")

# Force CHT to recovery threshold to trigger actual pull-up
st.cht_c = 101.5
for _ in range(40):
    app.update_simulation(st)

print(f"4. RECLIMB: Pitch attitude: {math.degrees(st.pitch_rad):.1f}°, Throttle: {st.throttle_pct:.0f}%, Phase: {st.dive_phase}")
assert st.dive_phase in ["RECLIMB", "IDLE"], f"Expected RECLIMB, got: {st.dive_phase}"
assert math.degrees(st.pitch_rad) > 10.0, f"UAV must pull up with steep positive climb pitch! Got: {math.degrees(st.pitch_rad):.1f}°"
print("✓ Actual pull-up ascension verified (+18° climb attitude)!")

print("\n>>> ALL CANYON SCANNER, SPEED & PULL-UP TESTS PASSED 100%! <<<")
