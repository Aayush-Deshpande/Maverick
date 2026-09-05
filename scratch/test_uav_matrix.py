import bpy
import mathutils
import math

uav = bpy.data.objects.get('UAV_Predator_Master')

# Let's test setting orientation using a rotation matrix or look_at:
# Nose = +Y in local space, Up = +Z in local space, Right = +X in local space.
# If we want the UAV to point in direction `fwd` with bank `roll_rad`:
fwd = mathutils.Vector((1.0, 1.0, 0.0)).normalized() # 45 deg along canyon
up_approx = mathutils.Vector((0.0, 0.0, 1.0))
right = fwd.cross(up_approx).normalized()
up = right.cross(fwd).normalized()

# If roll is applied:
roll_rad = math.radians(20.0) # 20 deg right bank
# Rotate right and up around fwd:
rot_roll = mathutils.Matrix.Rotation(roll_rad, 3, fwd)
right_rolled = rot_roll @ right
up_rolled = rot_roll @ up

# Matrix columns: X=right, Y=fwd, Z=up
R = mathutils.Matrix((right_rolled, fwd, up_rolled)).transposed()
print("Rotation matrix for fwd=(1,1,0), roll=20deg:")
print(R.to_euler())

# Check where the nose (+Y local) points:
nose_world = R @ mathutils.Vector((0, 1, 0))
print("Nose world:", nose_world)
print("Should match fwd:", fwd)
assert (nose_world - fwd).length < 1e-4, "Nose does not match fwd!"

# Check where right wing (+X local) points:
wing_world = R @ mathutils.Vector((1, 0, 0))
print("Right wing world:", wing_world)
print("Right wing Z (should be negative for right bank):", wing_world.z)
assert wing_world.z < -0.1, "Right wing did not bank down!"
print(">>> UAV ORIENTATION MATH VERIFIED PERFECTLY! <<<")
