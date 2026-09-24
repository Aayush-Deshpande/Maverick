import bpy
import math

scene = bpy.context.scene
root_empty = bpy.data.objects.get("TB3_Root")
p_nose = bpy.data.objects.get("Pivot_Nose_Gear")
p_main_l = bpy.data.objects.get("Pivot_Main_Gear_Left")
p_main_r = bpy.data.objects.get("Pivot_Main_Gear_Right")

ctrl_gear = bpy.data.objects.get("CTRL_Gear_Retract")
if not ctrl_gear:
    ctrl_gear = bpy.data.objects.new("CTRL_Gear_Retract", None)
    ctrl_gear.empty_display_type = 'SINGLE_ARROW'
    ctrl_gear.empty_display_size = 0.8
    ctrl_gear.location = (0.6, 0, 3.0)
    ctrl_gear.parent = root_empty
    bpy.data.collections.get("Landing_Gear").objects.link(ctrl_gear)

# Clear constraints
p_nose.constraints.clear()
p_main_l.constraints.clear()
p_main_r.constraints.clear()

# Nose gear constraint: Z loc (3.0 -> 4.0) maps to X rot (0 -> 85 deg)
c_n = p_nose.constraints.new('TRANSFORM')
c_n.target = ctrl_gear
c_n.target_space = 'LOCAL'
c_n.owner_space = 'LOCAL'
c_n.map_from = 'LOCATION'
c_n.from_min_z = 3.0
c_n.from_max_z = 4.0
c_n.map_to = 'ROTATION'
c_n.map_to_x_from = 'Z'
c_n.to_min_x_rot = 0.0
c_n.to_max_x_rot = math.radians(85)
c_n.use_motion_extrapolate = True

# Main gear left: Z loc maps to Y rot (0 -> 85 deg)
c_ml = p_main_l.constraints.new('TRANSFORM')
c_ml.target = ctrl_gear
c_ml.target_space = 'LOCAL'
c_ml.owner_space = 'LOCAL'
c_ml.map_from = 'LOCATION'
c_ml.from_min_z = 3.0
c_ml.from_max_z = 4.0
c_ml.map_to = 'ROTATION'
c_ml.map_to_y_from = 'Z'
c_ml.to_min_y_rot = 0.0
c_ml.to_max_y_rot = math.radians(85)
c_ml.use_motion_extrapolate = True

# Main gear right: Z loc maps to Y rot (0 -> -85 deg)
c_mr = p_main_r.constraints.new('TRANSFORM')
c_mr.target = ctrl_gear
c_mr.target_space = 'LOCAL'
c_mr.owner_space = 'LOCAL'
c_mr.map_from = 'LOCATION'
c_mr.from_min_z = 3.0
c_mr.from_max_z = 4.0
c_mr.map_to = 'ROTATION'
c_mr.map_to_y_from = 'Z'
c_mr.to_min_y_rot = 0.0
c_mr.to_max_y_rot = math.radians(-85)
c_mr.use_motion_extrapolate = True

ctrl_gear.location.z = 3.0
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
print("Gear Down (ctrl_gear.z = 3.0):")
print("  Nose rot X:", math.degrees(p_nose.evaluated_get(dg).matrix_world.to_euler().x))
print("  Main L rot Y:", math.degrees(p_main_l.evaluated_get(dg).matrix_world.to_euler().y))
print("  Main R rot Y:", math.degrees(p_main_r.evaluated_get(dg).matrix_world.to_euler().y))

ctrl_gear.location.z = 4.0
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
print("Gear Up (ctrl_gear.z = 4.0):")
print("  Nose rot X:", math.degrees(p_nose.evaluated_get(dg).matrix_world.to_euler().x))
print("  Main L rot Y:", math.degrees(p_main_l.evaluated_get(dg).matrix_world.to_euler().y))
print("  Main R rot Y:", math.degrees(p_main_r.evaluated_get(dg).matrix_world.to_euler().y))
