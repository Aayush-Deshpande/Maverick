"""
Completely remove all tactical materials, contour lines, isolines, and noise.
Sets the terrain to a pure, clean, completely normal natural mountain surface:
- Single Principled BSDF directly to Material Output (zero math nodes, zero ramps, zero noise)
- Natural mountain stone color
- EEVEE Fast GI disabled
- Clean neutral lighting
- Permanently saved to Models/terrain.blend
"""

import bpy
import mathutils
import math
import os

def apply_pure_normal_terrain():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        print("[ERROR] Terrain DEM object not found!")
        return

    # 1. Texture interpolation & anti-aliasing on DEM
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

    # 3. Completely delete any tactical materials
    for m in list(bpy.data.materials):
        if 'Tactical' in m.name or 'HUD' in m.name:
            bpy.data.materials.remove(m)

    # 4. Create PURE NORMAL MATERIAL (Zero math nodes, zero ramps, zero noise)
    mat = bpy.data.materials.new("M_Terrain_Natural")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (400, 0)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    # Clean natural mountain stone tone
    bsdf.inputs['Base Color'].default_value = (0.45, 0.43, 0.40, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.88
    bsdf.inputs['Specular IOR Level'].default_value = 0.22
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    obj.data.materials.clear()
    obj.data.materials.append(mat)
    print("[OK] Assigned pure normal material M_Terrain_Natural.")

    # 5. Remove any HUD collections
    col = bpy.data.collections.get('HUD_Tactical_Overlays')
    if col:
        for o in list(col.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(col)

    # 6. Turn off EEVEE Fast GI and Raytracing
    scene.eevee.use_fast_gi = False
    scene.eevee.use_raytracing = False

    # 7. Clean Natural Lighting
    sun = bpy.data.objects.get("Sun_Tactical")
    if not sun:
        sun_data = bpy.data.lights.new("Sun_Tactical", 'SUN')
        sun = bpy.data.objects.new("Sun_Tactical", sun_data)
        scene.collection.objects.link(sun)
    sun.data.energy = 4.2
    sun.data.color = (1.0, 0.98, 0.95)
    sun.data.use_shadow = False
    sun.rotation_euler = (math.radians(52.0), math.radians(24.0), math.radians(-70.0))

    fill = bpy.data.objects.get("Sun_Fill")
    if fill:
        fill.data.energy = 1.2
        fill.data.color = (0.50, 0.55, 0.60)
        fill.data.use_shadow = False

    # Sky World
    world = scene.world
    if not world:
        world = bpy.data.worlds.new("W_Natural")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.04, 0.05, 0.07, 1.0)
        bg.inputs['Strength'].default_value = 0.80

    # Color Management: Standard
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

    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/normal_clean_terrain.png"))
    scene.render.filepath = out_path
    print(f"[RENDER] Rendering normal clean terrain to: {out_path}...")
    bpy.ops.render.render(write_still=True)

    master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)
    print("[OK] Render complete!")

    # Save permanently to Models/terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved pure normal terrain.blend successfully!")

if __name__ == "__main__":
    apply_pure_normal_terrain()
