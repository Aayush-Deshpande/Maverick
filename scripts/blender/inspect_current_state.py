import bpy
import math

print("=== SCENE INSPECTION ===")
for obj in bpy.data.objects:
    if obj.type == 'LIGHT':
        print(f"Light: {obj.name}, type={obj.data.type}, rot={[round(math.degrees(r), 2) for r in obj.rotation_euler]}, energy={obj.data.energy}, angle={round(math.degrees(getattr(obj.data, 'angle', 0)), 2)}")

world = bpy.context.scene.world
print("Active world:", world.name if world else "None")
if world and world.node_tree:
    for n in world.node_tree.nodes:
        print(f"World node: {n.name} ({n.type})")
        if n.type == 'BACKGROUND':
            print(f"  Background Strength: {n.inputs['Strength'].default_value}")
        for inp in n.inputs:
            if inp.is_linked:
                for l in inp.links:
                    print(f"  [{inp.name}] <-- {l.from_node.name} [{l.from_socket.name}]")

# Check view layer mist pass
view_layer = bpy.context.scene.view_layers[0]
print("Mist pass enabled:", view_layer.use_pass_mist)
if bpy.context.scene.world:
    print("Mist start:", bpy.context.scene.world.mist_settings.start)
    print("Mist depth:", bpy.context.scene.world.mist_settings.depth)
    print("Mist falloff:", bpy.context.scene.world.mist_settings.falloff)
