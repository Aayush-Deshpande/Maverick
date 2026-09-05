import bpy
import mathutils
import math

rot_z = -0.8421 + math.pi
R = mathutils.Euler((0.0, 0.0, rot_z), 'XYZ').to_matrix()

# Local +Y:
p_pos_y = R @ mathutils.Vector((0, 1, 0))
# Local -Y:
p_neg_y = R @ mathutils.Vector((0, -1, 0))

print(f"When rot_z = -0.8421 + pi = {rot_z:.3f}:")
print(f"  Local +Y maps to world: ({p_pos_y.x:.3f}, {p_pos_y.y:.3f}, {p_pos_y.z:.3f})")
print(f"  Local -Y maps to world: ({p_neg_y.x:.3f}, {p_neg_y.y:.3f}, {p_neg_y.z:.3f})")

# In flipped_180_test.png, which way did the nose point?
# Canyon axis is (+X, +Y).
# Local -Y maps to (+0.66, +0.75, 0.0)!
# That is (+X, +Y)!
# So LOCAL -Y IS THE NOSE!
# AND LOCAL +Y IS THE PROPELLER / TAIL!
print(f"Local -Y is pointing towards (+X, +Y) down the canyon!")
