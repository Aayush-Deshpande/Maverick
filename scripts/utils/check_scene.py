import bpy

bpy.ops.wm.open_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend')

for obj in bpy.data.objects:
    if obj.type == 'LIGHT':
        l = obj.data
        print(f"LIGHT: {obj.name} type={l.type} energy={l.energy} color=({l.color.r:.2f},{l.color.g:.2f},{l.color.b:.2f}) rot=({obj.rotation_euler.x:.3f},{obj.rotation_euler.y:.3f},{obj.rotation_euler.z:.3f})")
    elif obj.type == 'CAMERA':
        print(f"CAMERA: {obj.name} loc=({obj.location.x:.1f},{obj.location.y:.1f},{obj.location.z:.1f})")

# Check for HDRI
world = bpy.context.scene.world
if world:
    for node in world.node_tree.nodes:
        if node.type == 'TEX_ENVIRONMENT' and node.image:
            hdri_path = bpy.path.abspath(node.image.filepath)
            print(f"HDRI: {node.image.name} path={hdri_path}")
        elif node.type == 'BACKGROUND':
            s = node.inputs['Strength'].default_value
            c = node.inputs['Color'].default_value
            print(f"BG: strength={s:.2f} color=({c[0]:.3f},{c[1]:.3f},{c[2]:.3f})")

# List all materials
for mat in bpy.data.materials:
    if mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                bc = n.inputs['Base Color'].default_value
                metal = n.inputs['Metallic'].default_value
                rough = n.inputs['Roughness'].default_value
                print(f"MAT: {mat.name} metal={metal:.2f} rough={rough:.2f} baseColor=({bc[0]:.2f},{bc[1]:.2f},{bc[2]:.2f})")
                break
