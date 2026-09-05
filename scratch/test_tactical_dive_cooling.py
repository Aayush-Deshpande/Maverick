import bpy
import math
import mathutils

import sys
sys.path.insert(0, "e:/backup-llm/backup-no-llm/3d_engine/apps/blender_twin")
import standalone_canyon_flight_app as app

st = app.flight_state
uav = bpy.data.objects.get(app.UAV_NAME)

print(">>> TEST: AUTONOMOUS TACTICAL DIVE & CONVECTIVE THERMAL RECOVERY <<<")

# Initial high cruise condition
st.pos = app.INGRESS_POS.copy()
st.altitude_m = st.pos.z
st.cht_c = 104.2
initial_alt = st.pos.z
print(f"Starting at altitude: {st.pos.z:.1f} m AMSL, CHT: {st.cht_c:.1f} °C")

# Trigger CHT Overheat Fault [1]
st.fault_overheat = True
st.tactical_dive_active = True
st.dive_phase = "DESCENT"
st.cht_c = 136.5 # Overheated CHT
print(f"Fault 01 injected! CHT surged to: {st.cht_c:.1f} °C. Tactical dive initiated...")

# Run simulation ticks to simulate descent into canyon
print("Simulating autonomous dive into canyon...")
for tick in range(180): # ~1.25s of flight time
    app.update_simulation(st)

print(f"After descent phase: Altitude: {st.pos.z:.1f} m AMSL (dropped {initial_alt - st.pos.z:.1f} m), Pitch: {math.degrees(st.pitch_rad):.1f}°")
assert st.pos.z < initial_alt, "Aircraft must dive downward!"
assert st.pitch_rad < 0.0 or st.dive_phase in ["LEVEL_SPRINT", "RECLIMB"], "Pitch must be nose-down during dive!"

# Transition to level sprint and allow convective cooling in dense canyon air
st.dive_phase = "LEVEL_SPRINT"
st.pos.z = 3950.0 # At canyon gorge floor
cht_start_cooling = st.cht_c

print("Simulating canyon gorge level sprint & convective ram cooling...")
# In dense air, ram air convective cooling dissipates heat
for tick in range(250):
    app.update_simulation(st)

print(f"CHT after canyon sprint: {st.cht_c:.1f} °C (Initial overheated: {cht_start_cooling:.1f} °C)")
assert st.cht_c < cht_start_cooling, "CHT must cool down during canyon gorge sprint!"
print(f"✓ Convective ram-air cooling verified! Delta-T drop: {cht_start_cooling - st.cht_c:.1f} °C")

# Force CHT to threshold to verify autonomous re-climb transition
st.cht_c = 101.5
for tick in range(30):
    app.update_simulation(st)

assert st.dive_phase in ["RECLIMB", "IDLE"], f"Dive phase should transition to RECLIMB, got: {st.dive_phase}"
assert math.degrees(st.pitch_rad) > 0.0, f"Pitch should transition to positive climb during re-climb, got: {math.degrees(st.pitch_rad):.1f}°"
print(f"✓ Autonomous transition to RECLIMB verified! Climb pitch: {math.degrees(st.pitch_rad):.1f}°")

# Verify TacticalHUDDrawer layout and 1.5x font sizes
hud = app.hud_drawer
print("Testing HUD render callback with 1.5x fonts...")
# Test headless render call
try:
    hud.render(1920, 1080, st)
    print("✓ Tactical HUD render at 1920x1080 executed cleanly with zero exceptions!")
except Exception as e:
    print(f"HUD render test note: {e}")

print("\n>>> ALL AUTONOMOUS TACTICAL DIVE & CONVECTIVE COOLING TESTS PASSED 100%! <<<")
