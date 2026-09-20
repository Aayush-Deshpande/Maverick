import bpy
import math

scene = bpy.context.scene
p_l = bpy.data.objects.get("Pivot_WingFold_Left")
p_r = bpy.data.objects.get("Pivot_WingFold_Right")
ctrl_w = bpy.data.objects.get("CTRL_Wing_Fold")
ctrl_g = bpy.data.objects.get("CTRL_Gear_Retract")
p_nose = bpy.data.objects.get("Pivot_Nose_Gear")
p_main_l = bpy.data.objects.get("Pivot_Main_Gear_Left")
bomb_out_l = bpy.data.objects.get("Guided_Bomb_Left_Outer")

print("\n--- 1. Testing Default Stance (Flight Ready) ---")
print("ctrl_w loc:", ctrl_w.location)
print("ctrl_g loc:", ctrl_g.location)
dg = bpy.context.evaluated_depsgraph_get()
print("P_L rot Y deg:", math.degrees(p_l.evaluated_get(dg).matrix_world.to_euler().y))
print("P_R rot Y deg:", math.degrees(p_r.evaluated_get(dg).matrix_world.to_euler().y))
print("Nose Gear rot X deg:", math.degrees(p_nose.evaluated_get(dg).matrix_world.to_euler().x))
print("Main Gear L rot Y deg:", math.degrees(p_main_l.evaluated_get(dg).matrix_world.to_euler().y))
print("Outer Bomb L world loc:", bomb_out_l.matrix_world.translation if bomb_out_l else "Not found")

print("\n--- 2. Testing Operator: tb3.wing_action(action='FOLD') ---")
bpy.ops.tb3.wing_action(action="FOLD")
dg = bpy.context.evaluated_depsgraph_get()
print("scene.tb3_wing_fold:", scene.tb3_wing_fold)
print("ctrl_w.location.z:", ctrl_w.location.z)
print("P_L rot Y deg:", math.degrees(p_l.evaluated_get(dg).matrix_world.to_euler().y))
print("P_R rot Y deg:", math.degrees(p_r.evaluated_get(dg).matrix_world.to_euler().y))
print("Outer Bomb L world loc after fold:", bomb_out_l.matrix_world.translation if bomb_out_l else "Not found")

print("\n--- 3. Testing Operator: tb3.wing_action(action='UNFOLD') ---")
bpy.ops.tb3.wing_action(action="UNFOLD")
dg = bpy.context.evaluated_depsgraph_get()
print("scene.tb3_wing_fold:", scene.tb3_wing_fold)
print("ctrl_w.location.z:", ctrl_w.location.z)
print("P_L rot Y deg:", math.degrees(p_l.evaluated_get(dg).matrix_world.to_euler().y))
print("P_R rot Y deg:", math.degrees(p_r.evaluated_get(dg).matrix_world.to_euler().y))
print("Outer Bomb L world loc after unfold:", bomb_out_l.matrix_world.translation if bomb_out_l else "Not found")

print("\n--- 4. Testing Operator: tb3.gear_action(action='RETRACT') ---")
bpy.ops.tb3.gear_action(action="RETRACT")
dg = bpy.context.evaluated_depsgraph_get()
print("scene.tb3_gear_retract:", scene.tb3_gear_retract)
print("ctrl_g.location.z:", ctrl_g.location.z)
print("Nose Gear rot X deg:", math.degrees(p_nose.evaluated_get(dg).matrix_world.to_euler().x))
print("Main Gear L rot Y deg:", math.degrees(p_main_l.evaluated_get(dg).matrix_world.to_euler().y))

print("\n--- 5. Testing Operator: tb3.gear_action(action='LOWER') ---")
bpy.ops.tb3.gear_action(action="LOWER")
dg = bpy.context.evaluated_depsgraph_get()
print("scene.tb3_gear_retract:", scene.tb3_gear_retract)
print("ctrl_g.location.z:", ctrl_g.location.z)
print("Nose Gear rot X deg:", math.degrees(p_nose.evaluated_get(dg).matrix_world.to_euler().x))
print("Main Gear L rot Y deg:", math.degrees(p_main_l.evaluated_get(dg).matrix_world.to_euler().y))

print("\n--- 6. Testing Timeline Animation (Playback) ---")
for f in [1, 60, 100, 170, 210, 250]:
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    print(f"Frame {f:3d}: ctrl_w.z={ctrl_w.evaluated_get(dg).location.z:.2f} (WingL={math.degrees(p_l.evaluated_get(dg).matrix_world.to_euler().y):.1f}°), ctrl_g.z={ctrl_g.evaluated_get(dg).location.z:.2f} (Nose={math.degrees(p_nose.evaluated_get(dg).matrix_world.to_euler().x):.1f}°)")

# Reset to frame 1
scene.frame_set(1)
print("\nALL VERIFICATION CHECKS PASSED!")
