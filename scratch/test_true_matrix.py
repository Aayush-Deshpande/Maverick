import bpy
import mathutils
import math

fwd = mathutils.Vector((1.0, 1.0, 0.0)).normalized()
roll_rad = math.radians(20.0) # 20 deg right bank
pitch_rad = math.radians(10.0) # 10 deg nose up

# Apply pitch to fwd:
fwd_pitched = mathutils.Vector((fwd.x * math.cos(pitch_rad), fwd.y * math.cos(pitch_rad), math.sin(pitch_rad))).normalized()

up_world = mathutils.Vector((0.0, 0.0, 1.0))
right = fwd_pitched.cross(up_world).normalized()
up = right.cross(fwd_pitched).normalized()

rot_roll = mathutils.Matrix.Rotation(roll_rad, 3, fwd_pitched)
right_rolled = rot_roll @ right
up_rolled = rot_roll @ up

# Local mapping:
# Local -Y is nose -> points along +fwd_pitched -> col 1 is -fwd_pitched
# Local -X is right wing -> points along +right_rolled -> col 0 is -right_rolled
# Local +Z is up -> col 2 is up_rolled
R = mathutils.Matrix((-right_rolled, -fwd_pitched, up_rolled)).transposed()

nose_world = R @ mathutils.Vector((0, -1, 0))
tail_world = R @ mathutils.Vector((0, 1, 0))
r_wing_world = R @ mathutils.Vector((-1, 0, 0))
l_wing_world = R @ mathutils.Vector((1, 0, 0))
up_world_res = R @ mathutils.Vector((0, 0, 1))

print("Nose world:", nose_world)
print("Should match fwd_pitched:", fwd_pitched)
assert (nose_world - fwd_pitched).length < 1e-4

print("Tail world:", tail_world)
assert (tail_world - (-fwd_pitched)).length < 1e-4

print("Right wing world:", r_wing_world)
print("Right wing Z (should be negative for right bank):", r_wing_world.z)
assert r_wing_world.z < -0.1

print(">>> ABSOLUTE MATHEMATICAL PERFECTION! <<<")
