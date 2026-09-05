"""
Permanent Master Blend File Color Grading & Shading Upgrade
Applies exact metallic PBR shaders, racing green covers, chrome intake runners,
matte black airbox, studio lighting, and HDR reflections into rotax_912_is_sport.blend.
"""

import bpy
import mathutils
import math
import os

def upgrade_master_blend():
    blend_path = r"E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    # Clean existing lights & cameras
    for obj in list(bpy.data.objects):
        if obj.type in ('LIGHT', 'CAMERA'):
            bpy.data.objects.remove(obj, do_unlink=True)

    # 1. PBR Material Grading
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    mname = mat.name.lower()
                    
                    # 1. VALVE COVERS (Dark Forest Racing Green)
                    if any(k in mname for k in ['green', 'plasticgreen', 'plastictheme', 'theme_m_plastic']):
                        node.inputs['Base Color'].default_value = (0.015, 0.28, 0.08, 1.0)
                        node.inputs['Roughness'].default_value = 0.30
                        node.inputs['Metallic'].default_value = 0.06
                    
                    # 2. INTAKE RUNNERS & CHROME TUBES (Polished Specular Chrome)
                    elif 'chrome' in mname:
                        node.inputs['Base Color'].default_value = (0.92, 0.94, 0.97, 1.0)
                        node.inputs['Roughness'].default_value = 0.06
                        node.inputs['Metallic'].default_value = 0.98
                    
                    # 3. LABELS & TEXT
                    elif 'label' in mname or 'fuse' in mname:
                        node.inputs['Base Color'].default_value = (0.85, 0.86, 0.88, 1.0)
                        node.inputs['Roughness'].default_value = 0.25
                        node.inputs['Metallic'].default_value = 0.0
                    
                    # 4. AIRBOX, CABLES, RUBBER (Matte Black)
                    elif any(k in mname for k in ['black', 'rubber', 'cable', 'timing', 'theme_m_black', 'plug', 'lead']):
                        node.inputs['Base Color'].default_value = (0.008, 0.008, 0.010, 1.0)
                        node.inputs['Roughness'].default_value = 0.65
                        node.inputs['Metallic'].default_value = 0.0
                    
                    # 5. EXHAUST SYSTEM (Dark Gunmetal Steel)
                    elif 'exhaust' in mname or 'steeldark' in mname:
                        node.inputs['Base Color'].default_value = (0.12, 0.13, 0.15, 1.0)
                        node.inputs['Roughness'].default_value = 0.38
                        node.inputs['Metallic'].default_value = 0.92
                    
                    # 6. OIL TANK (Warm Shadowed Steel)
                    elif 'oil_tank' in mname or 'tank' in mname:
                        node.inputs['Base Color'].default_value = (0.15, 0.14, 0.14, 1.0)
                        node.inputs['Roughness'].default_value = 0.35
                        node.inputs['Metallic'].default_value = 0.85
                    
                    # 7. ALTERNATOR (Cast Aluminum Alloy)
                    elif any(k in mname for k in ['alternator', 'rotax914', 'rotax915', 'extras', 'a12']):
                        node.inputs['Base Color'].default_value = (0.24, 0.25, 0.27, 1.0)
                        node.inputs['Roughness'].default_value = 0.30
                        node.inputs['Metallic'].default_value = 0.88
                    
                    # 8. GEARBOX & STEEL
                    elif 'gearbox' in mname or 'steelblack' in mname or 'steel' in mname:
                        node.inputs['Base Color'].default_value = (0.18, 0.19, 0.21, 1.0)
                        node.inputs['Roughness'].default_value = 0.32
                        node.inputs['Metallic'].default_value = 0.90
                    
                    # 9. GENERAL CASTINGS & ENGINE CRANKCASE
                    else:
                        node.inputs['Base Color'].default_value = (0.20, 0.21, 0.23, 1.0)
                        node.inputs['Roughness'].default_value = 0.35
                        node.inputs['Metallic'].default_value = 0.85

    # 2. Studio Lighting Rig
    sun_data = bpy.data.lights.new(name="SunKey", type='SUN')
    sun_data.energy = 5.0
    sun_data.color = (1.0, 0.97, 0.92)
    sun_obj = bpy.data.objects.new(name="SunKey", object_data=sun_data)
    sun_obj.rotation_euler = (math.radians(55), math.radians(25), math.radians(50))
    scene.collection.objects.link(sun_obj)

    fill_data = bpy.data.lights.new(name="FillLight", type='SUN')
    fill_data.energy = 1.2
    fill_data.color = (0.75, 0.85, 0.98)
    fill_obj = bpy.data.objects.new(name="FillLight", object_data=fill_data)
    fill_obj.rotation_euler = (math.radians(-40), math.radians(-30), math.radians(-140))
    scene.collection.objects.link(fill_obj)

    # 3. Studio HDRI World Environment
    scene.world.use_nodes = True
    world_tree = scene.world.node_tree
    world_tree.nodes.clear()

    node_bg = world_tree.nodes.new(type='ShaderNodeBackground')
    node_bg.inputs['Color'].default_value = (0.12, 0.14, 0.18, 1.0) # Aerospace slate background
    node_bg.inputs['Strength'].default_value = 0.6

    node_env = world_tree.nodes.new(type='ShaderNodeTexEnvironment')
    exr_path = r"E:\Blender\5.2\datafiles\studiolights\world\sunset.exr"
    if os.path.exists(exr_path):
        node_env.image = bpy.data.images.load(exr_path)

    node_mix = world_tree.nodes.new(type='ShaderNodeMixShader')
    node_lightpath = world_tree.nodes.new(type='ShaderNodeLightPath')
    node_output = world_tree.nodes.new(type='ShaderNodeOutputWorld')

    node_env_bg = world_tree.nodes.new(type='ShaderNodeBackground')
    node_env_bg.inputs['Strength'].default_value = 0.85

    world_tree.links.new(node_env.outputs['Color'], node_env_bg.inputs['Color'])
    world_tree.links.new(node_lightpath.outputs['Is Camera Ray'], node_mix.inputs['Fac'])
    world_tree.links.new(node_env_bg.outputs['Background'], node_mix.inputs[1])
    world_tree.links.new(node_bg.outputs['Background'], node_mix.inputs[2])
    world_tree.links.new(node_mix.outputs['Shader'], node_output.inputs['Surface'])

    # 4. Camera Setup
    cam_data = bpy.data.cameras.new(name="TurntableCam")
    cam_data.lens = 50
    cam_obj = bpy.data.objects.new(name="TurntableCam", object_data=cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    cam_obj.location = (0.0, -250.0, 75.0)

    # 5. Shading configuration in scene
    scene.render.engine = 'BLENDER_EEVEE'

    bpy.ops.wm.save_mainfile()
    print("SUCCESS: Permanently upgraded rotax_912_is_sport.blend with realistic PBR shading & studio lighting!")

if __name__ == '__main__':
    upgrade_master_blend()
