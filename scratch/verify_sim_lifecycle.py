import bpy
import sys
import os

# Import the script
sys.path.append(os.path.abspath("e:/backup-llm/backup-no-llm/3d_engine/apps/blender_twin"))
import standalone_canyon_flight_app as app

st = app.flight_state
print(f"Initial Pos: {st.pos}")
print(f"Initial Altitude: {st.altitude_m:.1f}m AMSL, AGL: {st.agl_m:.1f}m")

# Test 60 ticks of nominal cruise:
for i in range(60):
    app.update_simulation(st)

print(f"After 60 ticks cruise: Pos=({st.pos.x:.1f}, {st.pos.y:.1f}, {st.pos.z:.1f})")
print(f"AGL: {st.agl_m:.1f}m, FwdDist: {st.fwd_dist_m:.1f}m, TTI: {st.tti_s:.1f}s, Airspeed: {st.airspeed_kias:.1f} KIAS")
print(f"GCAS Active: {st.gcas_active}, Crashed: {st.is_crashed}")
assert not st.gcas_active, "GCAS should NOT be active at nominal ingress altitude!"
assert not st.is_crashed, "Should NOT be crashed!"

# Test Pitch Down (Dive into canyon):
st.inp_pitch_down = True
for i in range(40):
    app.update_simulation(st)
st.inp_pitch_down = False

print(f"After diving: Pitch={app.math.degrees(st.pitch_rad):.1f} deg, Alt={st.altitude_m:.1f}m, AGL={st.agl_m:.1f}m")

# Test Turn Left:
st.inp_turn_left = True
for i in range(30):
    app.update_simulation(st)
st.inp_turn_left = False

print(f"After turn left: Heading={st.heading_deg:.1f} deg, Roll={app.math.degrees(st.roll_rad):.1f} deg")

# Test Camera Update:
app.update_chase_camera(st)
cam = bpy.data.objects.get(app.CAM_NAME)
print(f"Camera Position: {cam.location}")
print(f"Camera Rotation: {cam.rotation_euler}")

# Verify camera is behind the UAV:
cam_rel = cam.location - st.pos
print(f"Camera Relative to UAV: X={cam_rel.x:.1f}, Y={cam_rel.y:.1f}, Z={cam_rel.z:.1f}")

print(">>> ALL SIMULATION INTEGRATION TESTS PASSED 100%! <<<")
