import math
import mathutils

heading_rad = math.radians(46.0)
fwd_vel = mathutils.Vector((math.sin(heading_rad), math.cos(heading_rad), 0.0)).normalized()
up_world = mathutils.Vector((0.0, 0.0, 1.0))
right_base = fwd_vel.cross(up_world).normalized()
up_base = right_base.cross(fwd_vel).normalized()

print(f"Heading 46°: fwd={fwd_vel}, right_base={right_base}")

for roll_deg in [-30.0, 0.0, 30.0]:
    rot_roll = mathutils.Matrix.Rotation(math.radians(roll_deg), 3, fwd_vel)
    right_rolled = rot_roll @ right_base
    
    pos = mathutils.Vector((0, 0, 5000.0))
    left_wing = pos - right_rolled * 264.0
    right_wing = pos + right_rolled * 264.0
    print(f"Roll {roll_deg:+5.1f}°: left_wing.z = {left_wing.z:6.1f}m, right_wing.z = {right_wing.z:6.1f}m (diff: {left_wing.z - right_wing.z:+6.1f}m)")
