import bpy
import math

scene = bpy.context.scene
root_empty = bpy.data.objects.get("TB3_Root")
p_l = bpy.data.objects.get("Pivot_WingFold_Left")
p_r = bpy.data.objects.get("Pivot_WingFold_Right")

ctrl_fold = bpy.data.objects.get("CTRL_Wing_Fold")
if not ctrl_fold:
    ctrl_fold = bpy.data.objects.new("CTRL_Wing_Fold", None)
    ctrl_fold.empty_display_type = 'SINGLE_ARROW'
    ctrl_fold.empty_display_size = 0.8
    ctrl_fold.location = (0, 0, 3.0)
    ctrl_fold.parent = root_empty
    bpy.data.collections.get("Wings").objects.link(ctrl_fold)

# Remove action from p_l and p_r
if p_l.animation_data:
    p_l.animation_data.action = None
if p_r.animation_data:
    p_r.animation_data.action = None

p_l.constraints.clear()
p_r.constraints.clear()

c_l = p_l.constraints.new('TRANSFORM')
c_l.target = ctrl_fold
c_l.target_space = 'LOCAL'
c_l.owner_space = 'LOCAL'
c_l.map_from = 'LOCATION'
c_l.from_min_z = 3.0
c_l.from_max_z = 4.0
c_l.map_to = 'ROTATION'
c_l.map_to_y_from = 'Z'
c_l.to_min_y_rot = 0.0
c_l.to_max_y_rot = math.radians(115)
c_l.use_motion_extrapolate = True

c_r = p_r.constraints.new('TRANSFORM')
c_r.target = ctrl_fold
c_r.target_space = 'LOCAL'
c_r.owner_space = 'LOCAL'
c_r.map_from = 'LOCATION'
c_r.from_min_z = 3.0
c_r.from_max_z = 4.0
c_r.map_to = 'ROTATION'
c_r.map_to_y_from = 'Z'
c_r.to_min_y_rot = 0.0
c_r.to_max_y_rot = math.radians(-115)
c_r.use_motion_extrapolate = True

ctrl_fold.location.z = 3.0
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
p_l_eval = p_l.evaluated_get(dg)
p_r_eval = p_r.evaluated_get(dg)
print("When ctrl_fold.location.z = 3.0 (Flight):")
print("p_l_eval rot Y deg:", math.degrees(p_l_eval.matrix_world.to_euler().y))
print("p_r_eval rot Y deg:", math.degrees(p_r_eval.matrix_world.to_euler().y))

ctrl_fold.location.z = 4.0
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
p_l_eval = p_l.evaluated_get(dg)
p_r_eval = p_r.evaluated_get(dg)
print("When ctrl_fold.location.z = 4.0 (Folded 115 deg):")
print("p_l_eval rot Y deg:", math.degrees(p_l_eval.matrix_world.to_euler().y))
print("p_r_eval rot Y deg:", math.degrees(p_r_eval.matrix_world.to_euler().y))

ctrl_fold.location.z = 3.5
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
p_l_eval = p_l.evaluated_get(dg)
p_r_eval = p_r.evaluated_get(dg)
print("When ctrl_fold.location.z = 3.5 (Folded 50%):")
print("p_l_eval rot Y deg:", math.degrees(p_l_eval.matrix_world.to_euler().y))
print("p_r_eval rot Y deg:", math.degrees(p_r_eval.matrix_world.to_euler().y))
