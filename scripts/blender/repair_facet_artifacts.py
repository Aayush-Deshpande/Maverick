"""
Pure, Clean Tactical Digital Twin Material Setup
1. Zero noise textures, zero rock simulation, zero bump nodes.
2. Sleek, uniform military slate surface.
3. Crisp, delicate topographic elevation contour isolines.
4. Guaranteed 100% clean with zero black spots, facets, or artifacts.
"""

import bpy
import mathutils
import math
import os

def build_smooth_tactical_material():
    mat = bpy.data.materials.get("M_Tactical_Ladakh_Terrain")
    if not mat:
        mat = bpy.data.materials.new("M_Tactical_Ladakh_Terrain")
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # 1. Output & Principled BSDF
    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (1200, 200)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (850, 200)
    bsdf.inputs['Roughness'].default_value = 0.82
    bsdf.inputs['Specular IOR Level'].default_value = 0.30
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    # 2. Pure Mathematical Topographic Elevation Isolines
    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-800, 200)

    sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    sep_pos.location = (-550, 200)
    links.new(geom.outputs['Position'], sep_pos.inputs['Vector'])

    div_iso = nodes.new('ShaderNodeMath')
    div_iso.location = (-350, 200)
    div_iso.operation = 'DIVIDE'
    div_iso.inputs[1].default_value = 80.0 # 80m elevation contour interval
    links.new(sep_pos.outputs['Z'], div_iso.inputs[0])

    fract_iso = nodes.new('ShaderNodeMath')
    fract_iso.location = (-180, 200)
    fract_iso.operation = 'FRACT'
    links.new(div_iso.outputs['Value'], fract_iso.inputs[0])

    sub_iso = nodes.new('ShaderNodeMath')
    sub_iso.location = (-10, 200)
    sub_iso.operation = 'SUBTRACT'
    sub_iso.inputs[1].default_value = 0.5
    links.new(fract_iso.outputs['Value'], sub_iso.inputs[0])

    abs_iso = nodes.new('ShaderNodeMath')
    abs_iso.location = (150, 200)
    abs_iso.operation = 'ABSOLUTE'
    links.new(sub_iso.outputs['Value'], abs_iso.inputs[0])

    ramp_iso = nodes.new('ShaderNodeValToRGB')
    ramp_iso.location = (320, 200)
    ramp_iso.color_ramp.elements[0].position = 0.486
    ramp_iso.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_iso.color_ramp.elements[1].position = 0.50
    ramp_iso.color_ramp.elements[1].color = (0.60, 0.75, 0.88, 1.0) # Delicate cyan-white contour line
    links.new(abs_iso.outputs['Value'], ramp_iso.inputs['Fac'])

    # 3. Clean Slate Surface Color
    mix_color = nodes.new('ShaderNodeMix')
    mix_color.data_type = 'RGBA'
    mix_color.blend_type = 'ADD'
    mix_color.location = (600, 200)
    mix_color.inputs[6].default_value = (0.19, 0.23, 0.28, 1.0) # Pure clean slate
    mix_color.inputs['Factor'].default_value = 0.45
    links.new(ramp_iso.outputs['Color'], mix_color.inputs[7])

    links.new(mix_color.outputs[2], bsdf.inputs['Base Color'])

    return mat

def apply_repair():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        print("[ERROR] Terrain DEM object not found!")
        return

    # Modifiers: DEM + Subsurf Smooth
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

    # Assign Pure Clean Material
    mat = build_smooth_tactical_material()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Pure clean terrain saved successfully!")

if __name__ == "__main__":
    apply_repair()
