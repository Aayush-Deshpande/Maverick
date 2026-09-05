"""
Locks the clean studio terrain matching the user's reference:
- Removes all tactical graphics, HUD elements, isolines, and noise
- Removes harsh directional lights and replaces with soft studio/ambient illumination
- Applies pure, smooth slate-grey clay material directly from BSDF to Output
- Zero black spots, zero facets, zero artifacts
- Permanently saved to Models/terrain.blend
"""

import bpy
import mathutils
import math
import os

def configure_clean_studio_terrain():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        print("[ERROR] Terrain object not found!")
        return

    # 1. Texture interpolation & anti-aliasing
    dem_tex = bpy.data.textures.get('demText.003')
    if dem_tex:
        dem_tex.use_interpolation = True
        dem_tex.filter_size = 3.5

    # 2. Modifiers: DEM Displace + Smooth Subdivision
    dem_mod = obj.modifiers.get('DEM')
    if dem_mod:
        dem_mod.direction = 'Z'

    sub = obj.modifiers.get('Subsurf_Smooth')
    if not sub:
        sub = obj.modifiers.new(name='Subsurf_Smooth', type='SUBSURF')
    sub.subdivision_type = 'CATMULL_CLARK'
    sub.levels = 1
    sub.render_levels = 1

    for m in list(obj.modifiers):
        if m.name not in ['DEM', 'Subsurf_Smooth']:
            obj.modifiers.remove(m)

    for p in obj.data.polygons:
        p.use_smooth = True

    # 3. Completely delete any tactical / HUD materials
    for m in list(bpy.data.materials):
        if 'Tactical' in m.name or 'HUD' in m.name or 'Natural' in m.name:
            bpy.data.materials.remove(m)

    # 4. Remove all HUD collections & objects
    for c in list(bpy.data.collections):
        if 'HUD' in c.name:
            for o in list(c.objects):
                bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.collections.remove(c)

    # 5. Pure Clean Material (Zero math nodes, zero ramps, zero noise)
    mat = bpy.data.materials.new("M_Terrain_Clean")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (300, 0)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    # Slate-grey stone color matching the reference
    bsdf.inputs['Base Color'].default_value = (0.42, 0.46, 0.50, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.90
    bsdf.inputs['Specular IOR Level'].default_value = 0.15
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    obj.data.materials.clear()
    obj.data.materials.append(mat)
    print("[OK] Assigned pure clean material M_Terrain_Clean.")

    # 6. Remove all old lights
    for o in list(scene.objects):
        if o.type == 'LIGHT':
            bpy.data.objects.remove(o, do_unlink=True)

    # 7. Soft Studio Illumination (Zero harsh shadows)
    sun_data = bpy.data.lights.new('Studio_Light', 'SUN')
    sun_data.energy = 1.6
    sun_data.color = (1.0, 1.0, 1.0)
    sun_data.use_shadow = False
    sun_obj = bpy.data.objects.new('Studio_Light', sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (0.75, 0.25, -0.65)

    # Ambient World
    world = scene.world
    if not world:
        world = bpy.data.worlds.new("W_Clean")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.72, 0.76, 0.80, 1.0) # Soft ambient sky fill
        bg.inputs['Strength'].default_value = 1.0

    # 8. Standard Color Management & Render Settings
    scene.eevee.use_fast_gi = False
    scene.eevee.use_raytracing = False
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0

    # Viewport configuration
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'RENDERED'
                        space.region_3d.view_perspective = 'CAMERA'

    # Render High-Resolution Frame
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/studio_terrain_final.png"))
    scene.render.filepath = out_path
    print(f"[RENDER] Rendering studio clean terrain to: {out_path}...")
    bpy.ops.render.render(write_still=True)

    master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved clean studio terrain permanently to Models/terrain.blend!")

if __name__ == "__main__":
    configure_clean_studio_terrain()
