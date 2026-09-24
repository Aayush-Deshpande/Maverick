import bpy
import math

scene = bpy.context.scene
p_l = bpy.data.objects.get('Pivot_WingFold_Left')
p_r = bpy.data.objects.get('Pivot_WingFold_Right')

bomb_l = bpy.data.objects.get("Guided_Bomb_Left_Outer")
bomb_r = bpy.data.objects.get("Guided_Bomb_Right_Outer")

if bomb_l and p_l:
    # Set parent with matrix_parent_inverse preserved
    mat_world = bomb_l.matrix_world.copy()
    bomb_l.parent = p_l
    bomb_l.matrix_parent_inverse = p_l.matrix_world.inverted()
    bomb_l.matrix_world = mat_world

if bomb_r and p_r:
    mat_world = bomb_r.matrix_world.copy()
    bomb_r.parent = p_r
    bomb_r.matrix_parent_inverse = p_r.matrix_world.inverted()
    bomb_r.matrix_world = mat_world

bpy.context.view_layer.update()

# Clear existing animation actions from pivots so they don't fight manual controls/sliders
if p_l.animation_data:
    p_l.animation_data.action = None
if p_r.animation_data:
    p_r.animation_data.action = None

print("Testing fold to 115 degrees:")
p_l.rotation_euler.y = math.radians(115)
p_r.rotation_euler.y = math.radians(-115)
bpy.context.view_layer.update()

print("P_L rot Y deg:", math.degrees(p_l.rotation_euler.y))
print("Bomb L world loc after fold:", bomb_l.matrix_world.translation)
print("Wing L outer world loc after fold:", bpy.data.objects["Wing_Outer_Left"].matrix_world.translation)

print("Testing unfold back to 0 degrees:")
p_l.rotation_euler.y = 0.0
p_r.rotation_euler.y = 0.0
bpy.context.view_layer.update()
print("Bomb L world loc after unfold:", bomb_l.matrix_world.translation)
