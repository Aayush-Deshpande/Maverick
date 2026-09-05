import bpy

# Set up a scene to save EXR as float PNG or HDR
scene = bpy.data.scenes.new("ConvertScene")
scene.use_nodes = True
tree = scene.node_tree
for n in tree.nodes:
    tree.nodes.remove(n)

input_node = tree.nodes.new("CompositorNodeImage")
output_node = tree.nodes.new("CompositorNodeOutputFile")
output_node.base_path = r"E:\TalentForge\Clay\3d_engine\digital_twin_web\studiolights"
output_node.format.file_format = 'HDR'

tree.links.new(input_node.outputs['Image'], output_node.inputs['Image'])

for fname in ['sunset.exr', 'sunrise.exr', 'studio.exr', 'forest.exr', 'courtyard.exr', 'city.exr']:
    img_path = rf"E:\Blender\5.2\datafiles\studiolights\world\{fname}"
    img = bpy.data.images.load(img_path)
    input_node.image = img
    output_node.file_slots[0].path = fname.replace('.exr', '')
    bpy.context.window.scene = scene
    bpy.ops.render.render()
    print(f"Composited {fname}")
