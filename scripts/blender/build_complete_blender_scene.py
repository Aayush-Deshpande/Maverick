import bpy, mathutils, os

glb_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.glb'
blend_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend'
hehe_blend_path = r'E:\TalentForge\Clay\3d_engine\hehe\rotax_912_is_sport.blend'

# 1. Start fresh scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# 2. Import GLB
print("Importing GLB...")
bpy.ops.import_scene.gltf(filepath=glb_path)

# 3. Textures
tex_dir = r'E:\TalentForge\Clay\3d_engine\textures'
labels_tex_path = os.path.join(tex_dir, 'Rotax_Labels_Color.png')
extras_tex_path = os.path.join(tex_dir, 'Rotax914_Extras_AlbedoTransparency.png')
extras_metal_path = os.path.join(tex_dir, 'Rotax914_Extras_MetallicSmoothness.png')
extras_normal_path = os.path.join(tex_dir, '2032_MetalGalvanized_Normal.png')
honeycomb_tex_path = os.path.join(tex_dir, 'AluminiumHoneycomb_albedo.jpg')

img_labels = bpy.data.images.load(labels_tex_path) if os.path.exists(labels_tex_path) else None
img_extras = bpy.data.images.load(extras_tex_path) if os.path.exists(extras_tex_path) else None
img_extras_metal = bpy.data.images.load(extras_metal_path) if os.path.exists(extras_metal_path) else None
img_extras_normal = bpy.data.images.load(extras_normal_path) if os.path.exists(extras_normal_path) else None
img_honeycomb = bpy.data.images.load(honeycomb_tex_path) if os.path.exists(honeycomb_tex_path) else None

# 4. Realistic PBR Material Specifications
materials_spec = {
    # Textures / Decals
    'M_Labels': {'texture': img_labels, 'metallic': 0.2, 'roughness': 0.3, 'color': (1,1,1,1)},
    'M_Motherboard': {'texture': img_labels, 'metallic': 0.1, 'roughness': 0.4, 'color': (0.05, 0.45, 0.2, 1)},
    'M_Rotax914_Extras': {'texture': img_extras, 'metallic': 0.8, 'roughness': 0.3, 'color': (0.8, 0.8, 0.8, 1)},
    'Rotax915_Extras': {'texture': img_extras, 'metallic': 0.8, 'roughness': 0.3, 'color': (0.8, 0.8, 0.8, 1)},
    'Rotax915_A12': {'texture': img_extras, 'metallic': 0.8, 'roughness': 0.3, 'color': (0.8, 0.8, 0.8, 1)},
    'Rotax914_A12': {'texture': img_extras, 'metallic': 0.8, 'roughness': 0.3, 'color': (0.8, 0.8, 0.8, 1)},
    
    # Engine Plastics & Metals
    'M_PlasticGreen': {'color': (0.015, 0.32, 0.10, 1.0), 'metallic': 0.1, 'roughness': 0.25}, # British racing green cylinder heads
    'M_PlasticTheme': {'color': (0.015, 0.32, 0.10, 1.0), 'metallic': 0.1, 'roughness': 0.25},
    'M_PlasticBlack': {'color': (0.02, 0.02, 0.025, 1.0), 'metallic': 0.05, 'roughness': 0.35}, # Jet black intake manifold & ECU
    'M_MetalPaintedBlack': {'color': (0.015, 0.015, 0.018, 1.0), 'metallic': 0.4, 'roughness': 0.2}, # Black painted metal
    'M_PlasticCable': {'color': (0.01, 0.01, 0.01, 1.0), 'metallic': 0.0, 'roughness': 0.75}, # Matte black wiring loom
    'M_Black': {'color': (0.01, 0.01, 0.01, 1.0), 'metallic': 0.0, 'roughness': 0.8},
    'M_PlasticWhite': {'color': (0.95, 0.95, 0.96, 1.0), 'metallic': 0.0, 'roughness': 0.2}, # Glossy bright white cooling shroud & frame
    'M_Chrome': {'color': (0.96, 0.96, 0.98, 1.0), 'metallic': 0.98, 'roughness': 0.08}, # High polished mirror chrome alternator
    'M_Steel': {'color': (0.75, 0.75, 0.78, 1.0), 'metallic': 0.9, 'roughness': 0.25}, # Machined aluminum & stainless steel
    'M_SteelDark': {'color': (0.28, 0.28, 0.30, 1.0), 'metallic': 0.85, 'roughness': 0.45}, # Dark bronze / ceramic exhaust
    'M_SteelBlack': {'color': (0.08, 0.08, 0.09, 1.0), 'metallic': 0.7, 'roughness': 0.35}, # Black oxide brackets
    'M_Cobalt': {'color': (0.35, 0.37, 0.40, 1.0), 'metallic': 0.8, 'roughness': 0.35}, # Aluminum casting block
    'M_Copper': {'color': (0.95, 0.50, 0.30, 1.0), 'metallic': 0.95, 'roughness': 0.2}, # Bright copper electrical leads
    'M_PlasticBlue': {'color': (0.02, 0.25, 0.90, 1.0), 'metallic': 0.0, 'roughness': 0.3}, # Electric blue connectors
    'M_PlasticLightBlue': {'color': (0.15, 0.55, 0.95, 1.0), 'metallic': 0.0, 'roughness': 0.3},
    'M_PlasticYellow': {'color': (0.98, 0.82, 0.02, 1.0), 'metallic': 0.0, 'roughness': 0.3}, # Bright safety yellow
    'M_PlasticRed': {'color': (0.90, 0.05, 0.03, 1.0), 'metallic': 0.0, 'roughness': 0.3}, # Warning red caps
    'M_PlasticRedDarker': {'color': (0.50, 0.03, 0.02, 1.0), 'metallic': 0.0, 'roughness': 0.3},
    'M_FuseLight': {'color': (0.20, 1.00, 0.05, 1.0), 'metallic': 0.0, 'roughness': 0.1, 'emission': (0.2, 1.0, 0.05, 1.0)}, # Glowing fuse LED
    'M_PlasticBegue': {'color': (0.80, 0.72, 0.60, 1.0), 'metallic': 0.0, 'roughness': 0.4},
    'M_Rubber': {'color': (0.03, 0.03, 0.035, 1.0), 'metallic': 0.0, 'roughness': 0.8}, # Dark rubber cooling hoses & oil filter
    'M_TimingBelt': {'color': (0.04, 0.04, 0.04, 1.0), 'metallic': 0.0, 'roughness': 0.85},
    'M_Glass': {'color': (0.85, 0.95, 1.00, 0.2), 'metallic': 0.0, 'roughness': 0.05},
    'M_GlassMilky': {'color': (0.88, 0.90, 0.92, 0.6), 'metallic': 0.0, 'roughness': 0.25}
}

# Create / Update all materials
for mat_name, cfg in materials_spec.items():
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
    
    mat.diffuse_color = cfg.get('color', (0.7, 0.7, 0.7, 1.0))
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    node_out = nodes.new('ShaderNodeOutputMaterial')
    node_out.location = (400, 0)
    
    node_bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    node_bsdf.location = (0, 0)
    links.new(node_bsdf.outputs['BSDF'], node_out.inputs['Surface'])
    
    node_bsdf.inputs['Base Color'].default_value = cfg.get('color', (0.7, 0.7, 0.7, 1.0))
    node_bsdf.inputs['Metallic'].default_value = cfg.get('metallic', 0.0)
    node_bsdf.inputs['Roughness'].default_value = cfg.get('roughness', 0.5)
    
    if 'emission' in cfg:
        node_bsdf.inputs['Emission Color'].default_value = cfg['emission']
        node_bsdf.inputs['Emission Strength'].default_value = 2.0
        
    if 'texture' in cfg and cfg['texture']:
        node_tex = nodes.new('ShaderNodeTexImage')
        node_tex.location = (-400, 0)
        node_tex.image = cfg['texture']
        links.new(node_tex.outputs['Color'], node_bsdf.inputs['Base Color'])

# 5. Precise mesh assignment (sorted by length descending)
known_mats = sorted(list(materials_spec.keys()), key=len, reverse=True)

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        matched_mat = None
        for km in known_mats:
            if km in obj.name:
                matched_mat = km
                break
        if matched_mat and matched_mat in bpy.data.materials:
            t_mat = bpy.data.materials[matched_mat]
            if obj.data.materials:
                obj.data.materials[0] = t_mat
            else:
                obj.data.materials.append(t_mat)

# 6. Lighting & Studio Environment
world = bpy.data.worlds.new('StudioWorld')
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
if bg:
    bg.inputs['Color'].default_value = (0.05, 0.05, 0.07, 1.0)
    bg.inputs['Strength'].default_value = 0.5

# Bounding box
min_co = [float('inf')] * 3
max_co = [float('-inf')] * 3
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            for i in range(3):
                min_co[i] = min(min_co[i], world_corner[i])
                max_co[i] = max(max_co[i], world_corner[i])

center = [(min_co[i] + max_co[i]) / 2 for i in range(3)]
size = max([max_co[i] - min_co[i] for i in range(3)])

# Camera
cam_data = bpy.data.cameras.new('MainCamera')
cam_obj = bpy.data.objects.new('MainCamera', cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj
cam_obj.location = (center[0] + size * 0.8, center[1] - size * 1.1, center[2] + size * 0.5)
cam_obj.rotation_euler = (mathutils.Vector(center) - cam_obj.location).to_track_quat('-Z', 'Y').to_euler()
cam_data.clip_end = max(10000.0, size * 10.0)

# Key Light
key_data = bpy.data.lights.new('KeyLight', 'SUN')
key_data.energy = 2.5
key_data.color = (1.0, 0.98, 0.95)
key_obj = bpy.data.objects.new('KeyLight', key_data)
bpy.context.scene.collection.objects.link(key_obj)
key_obj.location = (center[0] + size, center[1] - size, center[2] + size * 1.5)
key_obj.rotation_euler = (0.8, 0.2, 0.6)

# Fill Light
fill_data = bpy.data.lights.new('FillLight', 'SUN')
fill_data.energy = 1.0
fill_data.color = (0.85, 0.90, 1.0)
fill_obj = bpy.data.objects.new('FillLight', fill_data)
bpy.context.scene.collection.objects.link(fill_obj)
fill_obj.location = (center[0] - size, center[1] + size, center[2] + size)
fill_obj.rotation_euler = (-0.5, -0.3, -2.0)

# Configure Viewport Shading
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
                    space.shading.use_scene_lights = True
                    space.shading.use_scene_world = True

# Save .blend
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
bpy.ops.wm.save_as_mainfile(filepath=hehe_blend_path)

print("Saved complete master .blend file!")
