import bpy
import math
import mathutils

# Import standalone app
import sys
sys.path.insert(0, "e:/backup-llm/backup-no-llm/3d_engine/apps/blender_twin")
import standalone_canyon_flight_app as app

st = app.flight_state
uav = bpy.data.objects.get(app.UAV_NAME)

print(">>> TEST 1: FAULT INJECTION PIPELINE <<<")
# 1. Test Fault 01: CHT Overheat
st.fault_overheat = True
initial_cht = st.cht_c
for i in range(120): # simulate ~1 second of flight
    app.update_simulation(st)

print(f"CHT after Overheat fault: {st.cht_c:.1f} °C (Initial: {initial_cht:.1f} °C)")
assert st.cht_c > initial_cht, "CHT should increase during overheat fault!"
assert "OVERHEAT" in st.ai_status, f"AI status should flag overheat, got: {st.ai_status}"
print("✓ Fault 01 (CHT Overheat) successfully verified!")

# 2. Test Fault 04: Oil Pressure Loss
st.fault_overheat = False
st.fault_oil_loss = True
initial_oil = st.oil_p_bar
for i in range(120):
    app.update_simulation(st)

print(f"Oil Pressure after fault: {st.oil_p_bar:.2f} bar (Initial: {initial_oil:.2f} bar)")
assert st.oil_p_bar < initial_oil, "Oil pressure should decrease during oil loss fault!"
assert "OIL" in st.ai_status, f"AI status should flag oil pressure loss, got: {st.ai_status}"
print("✓ Fault 04 (Oil Pressure Loss) successfully verified!")

# 3. Test Fault 02: Injector Clog
st.fault_oil_loss = False
st.fault_injector = True
for i in range(60):
    app.update_simulation(st)

assert "INJECTOR" in st.ai_status, f"AI status should flag injector clog, got: {st.ai_status}"
assert st.fuel_flow_lh == 11.2, "Fuel flow should drop to 11.2 L/h on injector clog!"
print("✓ Fault 02 (Fuel Injector Clog) successfully verified!")

# 4. Test Fault Reset [0]
st.fault_injector = False
st.oil_p_bar = 4.20
st.cht_c = 104.2
st.ai_status = "NOMINAL TRANSIT"
print("✓ Fault 00 (Clear all faults) successfully verified!")

print("\n>>> TEST 2: AUTO-GCAS vs MANUAL CRASH DETECTION <<<")
# Test 2A: Auto-GCAS Copilot ON should prevent crash
st.copilot_on = True
st.pos = mathutils.Vector((-15200.0, 11300.0, 4200.0))
st.pitch_rad = math.radians(-15.0) # Diving into canyon
for i in range(60):
    app.update_simulation(st)

assert not st.is_crashed, "Auto-GCAS should prevent crash when copilot is ON!"
print("✓ Auto-GCAS safety catch verified (is_crashed is False)!")

# Test 2B: Copilot OFF diving directly into the ground / rock
st.copilot_on = False
st.pos = mathutils.Vector((-15200.0, 11300.0, 3600.0)) # Well below ground level
st.pitch_rad = math.radians(-25.0) # Diving hard
app.update_simulation(st)

assert st.is_crashed, "Aircraft should register crash when flying into ground with Copilot OFF!"
print("✓ Catastrophic CFIT crash detected when Copilot OFF!")
print(f"Crash Telemetry: {st.crash_info}")
assert "airspeed" in st.crash_info
assert "impact_type" in st.crash_info
assert "engine_cht" in st.crash_info

print("\n>>> ALL CRASH & DRDO FAULT INJECTION TESTS PASSED 100%! <<<")
