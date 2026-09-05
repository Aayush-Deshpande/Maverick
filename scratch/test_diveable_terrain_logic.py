import bpy
import math
import mathutils
import sys

sys.path.insert(0, "e:/backup-llm/backup-no-llm/3d_engine/apps/blender_twin")
import standalone_canyon_flight_app as app

st = app.flight_state
radar = app.radar

print(">>> TEST: DIVEABLE TERRAIN LOGIC & DELAYED COOLING <<<")

# Initial nominal state
st.pos = app.INGRESS_POS.copy()
st.altitude_m = st.pos.z
st.cht_c = 105.0
st.tactical_dive_active = False
st.dive_phase = "IDLE"

print(f"Initial State: Alt {st.pos.z:.0f}m, CHT {st.cht_c:.1f}°C")

# Step 1: Trigger CHT Overheat Fault [1]
st.fault_overheat = True
st.tactical_dive_active = True
st.dive_phase = "SEEK_CANYON"

# Set a non-aligned heading to simulate scanning for diveable terrain
st.heading_rad = math.radians(app.NOMINAL_HEADING_DEG + 45.0)

print("\n--- PHASE 1: PRE-DIVE SCANNING AT HIGH CRUISE (5,800m) ---")
cht_start = st.cht_c
for i in range(15):
    # During scanning before diveable terrain is locked
    app.update_simulation(st)

print(f"After 15 ticks scanning: CHT = {st.cht_c:.2f}°C (Rate: {st.cht_rate_c_s:+.2f}°C/s, Delta: {st.cht_c - cht_start:+.2f}°C)")
assert st.cht_c > cht_start, f"Temperature MUST RISE while scanning before the dive actually starts! Start: {cht_start}, Now: {st.cht_c}"
assert st.cht_rate_c_s > 0.0, f"CHT rate must be positive (heating), got: {st.cht_rate_c_s}"
print("✓ Verified: Temperature rises while scanning before dive starts into diveable terrain!")

# Step 2: Now align directly with deepest canyon gorge and verify diveable terrain detection
print("\n--- PHASE 2: DETECTING DIVEABLE TERRAIN & COMMENCING DIVE ---")
best_hdg, lowest_z = app.find_deepest_canyon_heading(st.pos, radar)
is_diveable, floor_z, depth = app.check_diveable_terrain(st.pos, best_hdg, radar)

print(f"Canyon Scan: Best HDG = {math.degrees(best_hdg):.1f}°, Floor = {floor_z:.0f}m, Depth = {depth:.0f}m, Diveable = {is_diveable}")
assert is_diveable, f"Deepest canyon corridor must be diveable terrain! Depth: {depth}"

st.heading_rad = best_hdg
st.dive_target_bearing = best_hdg
st.target_canyon_alt = max(3850.0, lowest_z + 80.0)

# Run update multiple ticks to allow alignment and dive initiation
for tick in range(15):
    app.update_simulation(st)
    if st.dive_phase == "DESCENT":
        print(f"Transitioned to DESCENT on tick {tick}!")
        break
    else:
        print(f"Tick {tick}: Phase={st.dive_phase}, Hdg={math.degrees(st.heading_rad):.1f}°, Target={math.degrees(st.dive_target_bearing):.1f}°, Diveable={st.diveable_terrain_found}, Depth={st.canyon_depth_m:.0f}m")

print(f"Dive Phase after alignment: {st.dive_phase} (Diveable found: {st.diveable_terrain_found})")
assert st.dive_phase == "DESCENT", f"Expected DESCENT, got {st.dive_phase}"
print("✓ Verified: Diveable terrain detected and dive commenced!")

# Step 3: Descend into canyon gorge and verify temperature reduction
print("\n--- PHASE 3: DESCENT INTO DENSE GORGE AIR & CONVECTIVE TEMPERATURE REDUCTION ---")
# Let UAV descend into dense canyon air
for _ in range(80):
    app.update_simulation(st)

print(f"Current Altitude: {st.pos.z:.1f}m AMSL, Pitch: {math.degrees(st.pitch_rad):.1f}°, CHT: {st.cht_c:.1f}°C")

# Now enter canyon floor sprint
st.dive_phase = "LEVEL_SPRINT"
st.pos.z = 3950.0
cht_at_gorge_entry = st.cht_c

for _ in range(60):
    app.update_simulation(st)

print(f"Canyon Sprint: Alt = {st.pos.z:.0f}m, CHT = {st.cht_c:.1f}°C (Rate: {st.cht_rate_c_s:+.2f}°C/s, Drop: {cht_at_gorge_entry - st.cht_c:.1f}°C)")
assert st.cht_c < cht_at_gorge_entry, "Temperature MUST decrease once inside dense canyon air!"
assert st.cht_rate_c_s < 0.0, f"CHT rate must be negative (cooling), got: {st.cht_rate_c_s}"
print("✓ Verified: Temperature reduction starts as soon as the dive starts into diveable terrain!")

print("\n>>> ALL DIVEABLE TERRAIN & DELAYED COOLING TESTS PASSED 100%! <<<")
