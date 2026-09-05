import bpy

blend_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend'
bpy.ops.wm.open_mainfile(filepath=blend_path)

# Set up EVERY viewport shading mode to display full Material colors in Solid, Material, and Rendered modes!
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    # Set Solid shading to show Material colors
                    space.shading.type = 'SOLID'
                    space.shading.color_type = 'MATERIAL'
                    space.shading.show_cavity = True
                    space.shading.cavity_type = 'BOTH'
                    space.shading.show_shadows = True

# Also ensure every material's diffuse_color (viewport color) and Principled BSDF are vibrant and distinct
color_map = {
    'M_Chrome': (0.95, 0.95, 0.98, 1.0),
    'M_Cobalt': (0.18, 0.28, 0.45, 1.0),       # Deep cobalt engine casting
    'M_Steel': (0.80, 0.82, 0.85, 1.0),        # Stainless steel
    'M_SteelDark': (0.30, 0.30, 0.35, 1.0),    # Dark steel exhaust
    'M_SteelBlack': (0.12, 0.12, 0.14, 1.0),   # Black steel brackets
    'M_MetalPaintedBlack': (0.05, 0.05, 0.05, 1.0),
    'M_Black': (0.04, 0.04, 0.04, 1.0),
    'M_PlasticBlack': (0.10, 0.10, 0.11, 1.0), # Matte black plastic manifold
    'M_PlasticCable': (0.06, 0.06, 0.07, 1.0), # Cable harnesses
    'M_PlasticWhite': (0.95, 0.95, 0.95, 1.0), # White air baffle
    'M_PlasticGreen': (0.05, 0.75, 0.25, 1.0), # Rotax signature green valve covers
    'M_PlasticTheme': (0.05, 0.75, 0.25, 1.0),
    'M_Copper': (0.96, 0.55, 0.35, 1.0),       # Copper electrical leads
    'M_PlasticRed': (0.90, 0.08, 0.05, 1.0),   # Red ECU connectors & caps
    'M_PlasticRedDarker': (0.60, 0.04, 0.02, 1.0),
    'M_PlasticBlue': (0.05, 0.40, 0.95, 1.0),  # Blue harness plugs
    'M_PlasticLightBlue': (0.20, 0.65, 0.95, 1.0),
    'M_PlasticYellow': (0.98, 0.88, 0.05, 1.0),# Yellow warning labels & caps
    'M_FuseLight': (0.30, 1.00, 0.10, 1.0),    # Neon green fuse
    'M_PlasticBegue': (0.85, 0.78, 0.65, 1.0), # Beige clips
    'M_Motherboard': (0.05, 0.45, 0.20, 1.0),  # Green circuit board
    'M_Rubber': (0.12, 0.12, 0.12, 1.0),       # Black rubber hoses
    'M_Glass': (0.85, 0.95, 1.00, 0.5),
    'M_GlassMilky': (0.88, 0.90, 0.92, 0.8),
    'M_TimingBelt': (0.15, 0.15, 0.15, 1.0),   # Timing belt
    'M_Labels': (0.90, 0.90, 0.92, 1.0),
    'M_Rotax914_Extras': (0.75, 0.75, 0.78, 1.0),
    'Rotax915_Extras': (0.75, 0.75, 0.78, 1.0),
    'Rotax915_A12': (0.80, 0.80, 0.82, 1.0),
    'Rotax914_A12': (0.80, 0.80, 0.82, 1.0)
}

for mat in bpy.data.materials:
    c = color_map.get(mat.name, (0.7, 0.7, 0.75, 1.0))
    mat.diffuse_color = c
    if mat.node_tree:
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Base Color'].default_value = c

bpy.ops.wm.save_as_mainfile(filepath=blend_path, check_existing=False)
bpy.ops.wm.save_as_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\hehe\rotax_912_is_sport.blend', check_existing=False)
print("Successfully updated all material colors and solid viewport color settings!")
