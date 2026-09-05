import bpy, mathutils, os

blend_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend'
glb_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.glb'

# 1. Fresh Start
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb_path)

# 2. Textures Setup
tex_dir = r'E:\TalentForge\Clay\3d_engine\textures'
labels_tex_path = os.path.join(tex_dir, 'Rotax_Labels_Color.png')
extras_tex_path = os.path.join(tex_dir, 'Rotax914_Extras_AlbedoTransparency.png')

img_labels = bpy.data.images.load(labels_tex_path) if os.path.exists(labels_tex_path) else None
img_extras = bpy.data.images.load(extras_tex_path) if os.path.exists(extras_tex_path) else None

# 3. PBR Materials Configuration
materials_spec = {
    'M_Labels': {'texture': img_labels, 'metallic': 0.1, 'roughness': 0.3, 'color': (1,1,1,1)},
    'M_Motherboard': {'texture': img_labels, 'metallic': 0.1, 'roughness': 0.4, 'color': (0.05, 0.45, 0.2, 1)},
    'M_Rotax914_Extras': {'texture': img_extras, 'metallic': 0.8, 'roughness': 0.3, 'color': (0.8, 0.8, 0.8, 1)},
    'Rotax915_Extras': {'texture': img_extras, 'metallic': 0.8, 'roughness': 0.3, 'color': (0.8, 0.8, 0.8, 1)},
    'Rotax915_A12': {'texture': img_extras, 'metallic': 0.8, 'roughness': 0.3, 'color': (0.8, 0.8, 0.8, 1)},
    'Rotax914_A12': {'texture': img_extras, 'metallic': 0.8, 'roughness': 0.3, 'color': (0.8, 0.8, 0.8, 1)},
    'M_PlasticGreen': {'color': (0.015, 0.32, 0.10, 1.0), 'metallic': 0.1, 'roughness': 0.25},
    'M_PlasticTheme': {'color': (0.015, 0.32, 0.10, 1.0), 'metallic': 0.1, 'roughness': 0.25},
    'M_PlasticBlack': {'color': (0.02, 0.02, 0.025, 1.0), 'metallic': 0.05, 'roughness': 0.35},
    'M_MetalPaintedBlack': {'color': (0.015, 0.015, 0.018, 1.0), 'metallic': 0.4, 'roughness': 0.2},
    'M_PlasticCable': {'color': (0.01, 0.01, 0.01, 1.0), 'metallic': 0.0, 'roughness': 0.75},
    'M_Black': {'color': (0.01, 0.01, 0.01, 1.0), 'metallic': 0.0, 'roughness': 0.8},
    'M_PlasticWhite': {'color': (0.95, 0.95, 0.96, 1.0), 'metallic': 0.0, 'roughness': 0.2},
    'M_Chrome': {'color': (0.96, 0.96, 0.98, 1.0), 'metallic': 0.98, 'roughness': 0.08},
    'M_Steel': {'color': (0.75, 0.75, 0.78, 1.0), 'metallic': 0.9, 'roughness': 0.25},
    'M_SteelDark': {'color': (0.28, 0.28, 0.30, 1.0), 'metallic': 0.85, 'roughness': 0.45},
    'M_SteelBlack': {'color': (0.08, 0.08, 0.09, 1.0), 'metallic': 0.7, 'roughness': 0.35},
    'M_Cobalt': {'color': (0.35, 0.37, 0.40, 1.0), 'metallic': 0.8, 'roughness': 0.35},
    'M_Copper': {'color': (0.95, 0.50, 0.30, 1.0), 'metallic': 0.95, 'roughness': 0.2},
    'M_PlasticBlue': {'color': (0.02, 0.25, 0.90, 1.0), 'metallic': 0.0, 'roughness': 0.3},
    'M_PlasticLightBlue': {'color': (0.15, 0.55, 0.95, 1.0), 'metallic': 0.0, 'roughness': 0.3},
    'M_PlasticYellow': {'color': (0.98, 0.82, 0.02, 1.0), 'metallic': 0.0, 'roughness': 0.3},
    'M_PlasticRed': {'color': (0.90, 0.05, 0.03, 1.0), 'metallic': 0.0, 'roughness': 0.3},
    'M_PlasticRedDarker': {'color': (0.50, 0.03, 0.02, 1.0), 'metallic': 0.0, 'roughness': 0.3},
    'M_FuseLight': {'color': (0.20, 1.00, 0.05, 1.0), 'metallic': 0.0, 'roughness': 0.1, 'emission': (0.2, 1.0, 0.05, 1.0)},
    'M_PlasticBegue': {'color': (0.80, 0.72, 0.60, 1.0), 'metallic': 0.0, 'roughness': 0.4},
    'M_Rubber': {'color': (0.03, 0.03, 0.035, 1.0), 'metallic': 0.0, 'roughness': 0.8},
    'M_TimingBelt': {'color': (0.04, 0.04, 0.04, 1.0), 'metallic': 0.0, 'roughness': 0.85},
    'M_Glass': {'color': (0.85, 0.95, 1.00, 0.2), 'metallic': 0.0, 'roughness': 0.05},
    'M_GlassMilky': {'color': (0.88, 0.90, 0.92, 0.6), 'metallic': 0.0, 'roughness': 0.25}
}

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

# 4. Remove Duplicate Conflicting Objects (Covers_Custom, Gearbox_Type_3, Cert_912iScSport)
to_delete = []
for obj in bpy.data.objects:
    if any(k in obj.name for k in ['Covers_Custom', 'Gearbox_Type_3', 'Cert_912iScSport']):
        to_delete.append(obj)

for obj in to_delete:
    bpy.data.objects.remove(obj, do_unlink=True)
print(f"Removed {len(to_delete)} duplicate/conflicting configurator objects.")

# 5. Correct Material Assignment with Exact Precedence
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

# 6. Center & Master Parent Controller (Parent Everything to 1 Master Empty)
min_co = [float('inf')] * 3
max_co = [float('-inf')] * 3
engine_mesh_objects = [o for o in bpy.data.objects if o.type == 'MESH']

for obj in engine_mesh_objects:
    for corner in obj.bound_box:
        world_corner = obj.matrix_world @ mathutils.Vector(corner)
        for i in range(3):
            min_co[i] = min(min_co[i], world_corner[i])
            max_co[i] = max(max_co[i], world_corner[i])

center = [(min_co[i] + max_co[i]) / 2 for i in range(3)]
size = max([max_co[i] - min_co[i] for i in range(3)])

master_empty = bpy.data.objects.new('Master_Engine_Controller', None)
master_empty.empty_display_type = 'PLAIN_AXES'
master_empty.empty_display_size = 20.0
master_empty.location = center
bpy.context.scene.collection.objects.link(master_empty)

for obj in engine_mesh_objects:
    obj.parent = master_empty
    obj.matrix_parent_inverse = master_empty.matrix_world.inverted()

print(f"Parented all {len(engine_mesh_objects)} engine parts to Master_Engine_Controller at {center}!")

# 7. Soft Studio Ambient Lighting (NO Harsh Directional Cast Shadows)
world = bpy.data.worlds.new('StudioWorld')
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
if bg:
    bg.inputs['Color'].default_value = (0.55, 0.55, 0.58, 1.0)
    bg.inputs['Strength'].default_value = 1.3

# High-Quality Real-time EEVEE Settings
bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.context.scene.view_settings.view_transform = 'Filmic'
bpy.context.scene.view_settings.look = 'Medium High Contrast'

# Camera
cam_data = bpy.data.cameras.new('MainCamera')
cam_obj = bpy.data.objects.new('MainCamera', cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj
cam_obj.location = (center[0] + size * 0.85, center[1] - size * 1.15, center[2] + size * 0.55)
cam_obj.rotation_euler = (mathutils.Vector(center) - cam_obj.location).to_track_quat('-Z', 'Y').to_euler()
cam_data.clip_end = max(10000.0, size * 10.0)

# Configure 3D Viewports: RENDERED + NO GRIDS + High Depth Precision (Clip Start 0.1m)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'RENDERED'
                    space.shading.use_scene_lights = True
                    space.shading.use_scene_world = True
                    
                    space.clip_start = 0.1
                    space.clip_end = 1000.0
                    
                    space.overlay.show_floor = False
                    space.overlay.show_axis_x = False
                    space.overlay.show_axis_y = False
                    space.overlay.show_axis_z = False
                    space.overlay.show_cursor = False
                    space.overlay.show_object_origins = False

# 8. Pack Textures & Save
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=blend_path, check_existing=False)
bpy.ops.wm.save_as_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\hehe\rotax_912_is_sport.blend', check_existing=False)
print("SUCCESS: Configured and saved pristine Master Rotax Engine Blend File!")
