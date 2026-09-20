import bpy
import math

def update_wing_fold(self, context):
    val = self.tb3_wing_fold # 0.0 to 1.0
    rad = math.radians(115.0) * val
    p_l = bpy.data.objects.get("Pivot_WingFold_Left")
    p_r = bpy.data.objects.get("Pivot_WingFold_Right")
    if p_l:
        # If there's an action, we can update or remove it so manual control works
        p_l.rotation_euler.y = rad
    if p_r:
        p_r.rotation_euler.y = -rad
    print(f"Callback fired! val={val}, rad={rad}, p_l.rot.y={p_l.rotation_euler.y if p_l else None}")

# Unregister if already registered
if hasattr(bpy.types.Scene, "tb3_wing_fold"):
    del bpy.types.Scene.tb3_wing_fold

bpy.types.Scene.tb3_wing_fold = bpy.props.FloatProperty(
    name="Carrier Wing Fold",
    description="Fold wings 0 to 115 degrees for TCG Anadolu naval carrier elevator stowage",
    min=0.0,
    max=1.0,
    default=0.0,
    update=update_wing_fold
)

scene = bpy.context.scene
p_l = bpy.data.objects.get('Pivot_WingFold_Left')
p_r = bpy.data.objects.get('Pivot_WingFold_Right')

# If keyframes exist on rotation_euler, Blender will evaluate the keyframe on frame change!
# If we clear the action from animation_data or mute the fcurve when dragging, or how should timeline work?
print("Testing slider update:")
scene.tb3_wing_fold = 0.5
print("p_l rot Y deg:", math.degrees(p_l.rotation_euler[1]))

scene.tb3_wing_fold = 1.0
print("p_l rot Y deg:", math.degrees(p_l.rotation_euler[1]))

scene.tb3_wing_fold = 0.0
print("p_l rot Y deg:", math.degrees(p_l.rotation_euler[1]))
