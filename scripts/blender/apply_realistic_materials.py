import bpy, os

blend_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend'
bpy.ops.wm.open_mainfile(filepath=blend_path)

tex_dir = r'E:\TalentForge\Clay\3d_engine\textures'
labels_tex_path = os.path.join(tex_dir, 'Rotax_Labels_Color.png')
extras_tex_path = os.path.join(tex_dir, 'Rotax914_Extras_AlbedoTransparency.png')
extras_metal_path = os.path.join(tex_dir, 'Rotax914_Extras_MetallicSmoothness.png')
extras_normal_path = os.path.join(tex_dir, '2032_MetalGalvanized_Normal.png')

# Load images
img_labels = bpy.data.images.load(labels_tex_path) if os.path.exists(labels_tex_path) else None
img_extras = bpy.data.images.load(extras_tex_path) if os.path.exists(extras_tex_path) else None
img_extras_metal = bpy.data.images.load(extras_metal_path) if os.path.exists(extras_metal_path) else None
img_extras_normal = bpy.data.images.load(extras_normal_path) if os.path.exists(extras_normal_path) else None

material_configs = {
    'M_Labels': {'texture': img_labels, 'metallic': 0.1, 'roughness': 0.3, 'color': (1,1,1,1)},
    'M_Motherboard': {'texture': img_labels, 'metallic': 0.1, 'roughness': 0.4, 'color': (0.1, 0.5, 0.2, 1)},
    'M_Rotax914_Extras': {'texture': img_extras, 'metallic': 0.8, 'roughness': 0.3, 'color': (0.8, 0.8, 0.8, 1)},
    'Rotax915_Extras': {'texture': img_extras, 'metallic': 0.8, 'roughness': 0.3, 'color': (0.8, 0.8, 0.8, 1)},
    'Rotax915_A12': {'texture': img_extras, 'metallic': 0.8, 'roughness': 0.3, 'color': (0.8, 0.8, 0.8, 1)},
    'Rotax914_A12': {'texture': img_extras, 'metallic': 0.8, 'roughness': 0.3, 'color': (0.8, 0.8, 0.8, 1)},
    
    # Solid PBR Colors matching the real Rotax engine photos exactly:
    'M_PlasticGreen': {'color': (0.015, 0.35, 0.10, 1.0), 'metallic': 0.1, 'roughness': 0.25}, # Rotax signature dark forest green
    'M_PlasticTheme': {'color': (0.015, 0.35, 0.10, 1.0), 'metallic': 0.1, 'roughness': 0.25},
    'M_PlasticBlack': {'color': (0.02, 0.02, 0.025, 1.0), 'metallic': 0.05, 'roughness': 0.35}, # Jet black glossy manifold & ECU
    'M_MetalPaintedBlack': {'color': (0.015, 0.015, 0.018, 1.0), 'metallic': 0.3, 'roughness': 0.2}, # Black painted metal
    'M_PlasticCable': {'color': (0.01, 0.01, 0.01, 1.0), 'metallic': 0.0, 'roughness': 0.7}, # Matte black wiring loom
    'M_Black': {'color': (0.01, 0.01, 0.01, 1.0), 'metallic': 0.0, 'roughness': 0.8},
    'M_PlasticWhite': {'color': (0.95, 0.95, 0.96, 1.0), 'metallic': 0.0, 'roughness': 0.2}, # Glossy bright white cooling shroud
    'M_Chrome': {'color': (0.96, 0.96, 0.98, 1.0), 'metallic': 0.98, 'roughness': 0.08}, # High polished mirror chrome
    'M_Steel': {'color': (0.75, 0.75, 0.78, 1.0), 'metallic': 0.9, 'roughness': 0.25}, # Machined aluminum & stainless steel
    'M_SteelDark': {'color': (0.28, 0.28, 0.30, 1.0), 'metallic': 0.85, 'roughness': 0.4}, # Exhaust manifold steel
    'M_SteelBlack': {'color': (0.08, 0.08, 0.09, 1.0), 'metallic': 0.7, 'roughness': 0.35},
    'M_Cobalt': {'color': (0.35, 0.37, 0.40, 1.0), 'metallic': 0.8, 'roughness': 0.35}, # Aluminum casting block
    'M_Copper': {'color': (0.95, 0.50, 0.30, 1.0), 'metallic': 0.95, 'roughness': 0.2}, # Bright copper electrical leads
    'M_PlasticBlue': {'color': (0.02, 0.25, 0.90, 1.0), 'metallic': 0.0, 'roughness': 0.3}, # Electric blue connectors
    'M_PlasticLightBlue': {'color': (0.15, 0.55, 0.95, 1.0), 'metallic': 0.0, 'roughness': 0.3},
    'M_PlasticYellow': {'color': (0.98, 0.82, 0.02, 1.0), 'metallic': 0.0, 'roughness': 0.3}, # Bright safety yellow
    'M_PlasticRed': {'color': (0.90, 0.05, 0.03, 1.0), 'metallic': 0.0, 'roughness': 0.3}, # Warning red caps
    'M_PlasticRedDarker': {'color': (0.50, 0.03, 0.02, 1.0), 'metallic': 0.0, 'roughness': 0.3},
    'M_FuseLight': {'color': (0.20, 1.00, 0.05, 1.0), 'metallic': 0.0, 'roughness': 0.1, 'emission': (0.2, 1.0, 0.05, 1.0)}, # Glowing fuse LED
    'M_PlasticBegue': {'color': (0.80, 0.72, 0.60, 1.0), 'metallic': 0.0, 'roughness': 0.4},
    'M_Rubber': {'color': (0.03, 0.03, 0.035, 1.0), 'metallic': 0.0, 'roughness': 0.8}, # Dark rubber cooling hoses
    'M_TimingBelt': {'color': (0.04, 0.04, 0.04, 1.0), 'metallic': 0.0, 'roughness': 0.85},
    'M_Glass': {'color': (0.85, 0.95, 1.00, 0.2), 'metallic': 0.0, 'roughness': 0.05},
    'M_GlassMilky': {'color': (0.88, 0.90, 0.92, 0.6), 'metallic': 0.0, 'roughness': 0.25}
}

for mat in bpy.data.materials:
    cfg = materialConfigs = material_configs.get(mat.name, {'color': (0.6, 0.6, 0.65, 1.0), 'metallic': 0.5, 'roughness': 0.5})
    c = cfg.get('color', (0.7, 0.7, 0.7, 1.0))
    mat.diffuse_color = c
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    # Output node
    node_out = nodes.new('ShaderNodeOutputMaterial')
    node_out.location = (400, 0)
    
    # Principled BSDF
    node_bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    node_bsdf.location = (0, 0)
    links.new(node_bsdf.outputs['BSDF'], node_out.inputs['Surface'])
    
    # Configure BSDF
    node_bsdf.inputs['Base Color'].default_value = c
    node_bsdf.inputs['Metallic'].default_value = cfg.get('metallic', 0.0)
    node_bsdf.inputs['Roughness'].default_value = cfg.get('roughness', 0.5)
    
    if 'emission' in cfg:
        node_bsdf.inputs['Emission Color'].default_value = cfg['emission']
        node_bsdf.inputs['Emission Strength'].default_value = 2.0
        
    # If texture is specified, link Image Texture node
    if 'texture' in cfg and cfg['texture']:
        node_tex = nodes.new('ShaderNodeTexImage')
        node_tex.location = (-400, 0)
        node_tex.image = cfg['texture']
        links.new(node_tex.outputs['Color'], node_bsdf.inputs['Base Color'])

bpy.ops.wm.save_as_mainfile(filepath=blend_path, check_existing=False)
bpy.ops.wm.save_as_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\hehe\rotax_912_is_sport.blend', check_existing=False)
print("Successfully applied realistic textures and PBR materials to .blend file!")
