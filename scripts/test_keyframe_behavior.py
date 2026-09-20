import bpy
import math

scene = bpy.context.scene
p_l = bpy.data.objects.get('Pivot_WingFold_Left')
print("Current frame:", scene.frame_current)
print("P_L rot Y:", math.degrees(p_l.rotation_euler[1]))

# If p_l has animation_data with an action:
print("Animation data:", p_l.animation_data)
if p_l.animation_data and p_l.animation_data.action:
    print("Action name:", p_l.animation_data.action.name)
    print("Fcurves:", [fc.data_path for fc in p_l.animation_data.action.fcurves])

# Set rotation directly:
p_l.rotation_euler.y = math.radians(115)
bpy.context.view_layer.update()
print("After manual set p_l rot Y:", math.degrees(p_l.rotation_euler[1]))

# Now change frame:
scene.frame_set(1)
print("After frame_set(1) p_l rot Y:", math.degrees(p_l.rotation_euler[1]))

scene.frame_set(60)
print("After frame_set(60) p_l rot Y:", math.degrees(p_l.rotation_euler[1]))
