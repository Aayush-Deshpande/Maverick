import bpy
import os
import math

def setup_render_settings(scene, resolution=(1920, 1080)):
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 95
    scene.view_settings.view_transform = 'Standard'

def clear_lights_cameras():
    for obj in list(bpy.data.objects):
        if obj.type in ('LIGHT', 'CAMERA'):
            bpy.data.objects.remove(obj, do_unlink=True)

def add_studio_lighting():
    # Key light
    key = bpy.data.lights.new(name="Key_Light", type='AREA')
    key.energy = 800
    key.size = 2.0
    key_obj = bpy.data.objects.new("Key_Light", key)
    key_obj.location = (2.0, -2.5, 2.0)
    bpy.context.collection.objects.link(key_obj)

    # Fill light
    fill = bpy.data.lights.new(name="Fill_Light", type='AREA')
    fill.energy = 400
    fill.size = 3.0
    fill_obj = bpy.data.objects.new("Fill_Light", fill)
    fill_obj.location = (-2.5, -2.0, 1.5)
    bpy.context.collection.objects.link(fill_obj)

    # Rim light
    rim = bpy.data.lights.new(name="Rim_Light", type='AREA')
    rim.energy = 600
    rim.size = 2.0
    rim_obj = bpy.data.objects.new("Rim_Light", rim)
    rim_obj.location = (0.0, 2.5, 2.0)
    bpy.context.collection.objects.link(rim_obj)

def get_scene_bbox():
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    if not meshes:
        return (0,0,0), 1.0
    min_co = [float('inf')]*3
    max_co = [float('-inf')]*3
    for obj in meshes:
        for corner in obj.bound_box:
            world_co = obj.matrix_world @ mathutils.Vector(corner)
            for i in range(3):
                min_co[i] = min(min_co[i], world_co[i])
                max_co[i] = max(max_co[i], world_co[i])
    center = tuple((min_co[i] + max_co[i]) / 2 for i in range(3))
    size = max(max_co[i] - min_co[i] for i in range(3))
    return center, size

import mathutils

def render_multi_views(output_dir, prefix):
    os.makedirs(output_dir, exist_ok=True)
    clear_lights_cameras()
    add_studio_lighting()

    center, size = get_scene_bbox()
    dist = max(size * 1.6, 1.2)

    # World background to clean neutral light gray
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs[0].default_value = (0.12, 0.13, 0.15, 1.0) # Dark studio gray

    cam_data = bpy.data.cameras.new(name="RenderCamera")
    cam_data.lens = 85 # Telephoto portrait lens to minimize perspective distortion
    cam_obj = bpy.data.objects.new("RenderCamera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    views = [
        ("Front", (center[0], center[1] - dist, center[2]), (math.radians(90), 0, 0)),
        ("Rear", (center[0], center[1] + dist, center[2]), (math.radians(90), 0, math.radians(180))),
        ("Left_Side", (center[0] - dist, center[1], center[2]), (math.radians(90), 0, math.radians(-90))),
        ("Right_Side", (center[0] + dist, center[1], center[2]), (math.radians(90), 0, math.radians(90))),
        ("Top", (center[0], center[1], center[2] + dist), (0, 0, 0)),
        ("Iso_Front_Left", (center[0] - dist*0.8, center[1] - dist*0.8, center[2] + dist*0.6), (math.radians(60), 0, math.radians(-45))),
        ("Iso_Rear_Right", (center[0] + dist*0.8, center[1] + dist*0.8, center[2] + dist*0.6), (math.radians(60), 0, math.radians(135))),
        ("Iso_Front_Right", (center[0] + dist*0.8, center[1] - dist*0.8, center[2] + dist*0.6), (math.radians(60), 0, math.radians(45)))
    ]

    for name, loc, rot in views:
        cam_obj.location = loc
        cam_obj.rotation_euler = rot
        
        # Look at center
        direction = mathutils.Vector(center) - mathutils.Vector(loc)
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam_obj.rotation_euler = rot_quat.to_euler()

        out_path = os.path.join(output_dir, f"{prefix}_CAD_{name}.jpg")
        bpy.context.scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"Rendered: {out_path}")

if __name__ == "__main__":
    import sys
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    target = args[0] if args else "912"

    base_dir = r"E:\backup-llm\backup-no-llm\3d_engine\ANUMAAN\Models_Images"
    if target == "912":
        out_dir = os.path.join(base_dir, r"Bayraktar_TB2\03_Engine_Rotax_912iS")
        setup_render_settings(bpy.context.scene)
        render_multi_views(out_dir, "Rotax_912iS")
    elif target == "915":
        bpy.ops.wm.read_factory_settings(use_empty=True)
        fbx_path = r"E:\backup-llm\backup-no-llm\3d_engine\ANUMAAN\Models\Rotax_915.FBX"
        bpy.ops.import_scene.fbx(filepath=fbx_path)
        out_dir = os.path.join(base_dir, r"IAI_Heron_MkII\03_Engine_Rotax_915iS")
        setup_render_settings(bpy.context.scene)
        render_multi_views(out_dir, "Rotax_915iS")
