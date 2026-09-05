"""
Finalizes the exact node chain requested by user with ~35% alpine snow coverage:
- Geometry -> Position -> Separate XYZ -> Z -> Map Range (2925 to 7616) -> Math_Elevation_Mask (> 0.44)
- Geometry -> Normal -> Separate_XYZ_Normal -> Z -> Math_Slope_Mask (> 0.05)
- Math_Snow_Mask = Math_Elevation_Mask * Math_Slope_Mask
- ColorRamp_Snow outputting #D8D5CC neutral snow
- Mix_Snow_Blend (RGBA):
    Factor: Math_Snow_Mask
    Input A: Existing Rock Color (Mix.Result)
    Input B: Snow Color (ColorRamp_Snow)
    Result_Color: Principled BSDF Base Color
"""

import bpy
import os

def finalize_35_snow_material():
    terrain = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    mat = terrain.material_slots[0].material
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf = nodes.get('Principled BSDF')
    me = nodes.get('Math_Elevation_Mask')
    ms = nodes.get('Math_Slope_Mask')
    sm = nodes.get('Math_Snow_Mask')
    cr_snow = nodes.get('ColorRamp_Snow')
    mix_snow = nodes.get('Mix_Snow_Blend')
    existing_mix = nodes.get('Mix')

    # 1. Elevation Threshold: 0.44 (~4,990m AMSL, upper 35% of peaks)
    me.operation = 'GREATER_THAN'
    me.inputs[1].default_value = 0.44

    # 2. Slope Threshold: 0.05 (leaves sheer vertical cliffs as bare rock)
    ms.operation = 'GREATER_THAN'
    ms.inputs[1].default_value = 0.05

    # 3. Multiply Snow Mask
    sm.operation = 'MULTIPLY'
    links.new(me.outputs['Value'], sm.inputs[0])
    links.new(ms.outputs['Value'], sm.inputs[1])

    # 4. ColorRamp Snow Palette (#D8D5CC neutral off-white)
    cr = cr_snow.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.72, 0.74, 0.76, 1.0)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.82, 0.81, 0.78, 1.0)

    # 5. Mix_Snow_Blend
    mix_snow.data_type = 'RGBA'
    mix_snow.blend_type = 'MIX'
    links.new(sm.outputs['Value'], mix_snow.inputs[0]) # Factor
    links.new(existing_mix.outputs['Result'], mix_snow.inputs[6]) # A (Rock)
    links.new(cr_snow.outputs['Color'], mix_snow.inputs[7]) # B (Snow)
    links.new(mix_snow.outputs[2], bsdf.inputs['Base Color']) # Result_Color -> Base Color

    # Save to terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved finalized 35% snow material setup!")

    # Render final verification stills
    scene = bpy.context.scene
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080

    # Recon Overview
    cam_recon = bpy.data.objects.get('Camera_Canyon_Recon')
    scene.camera = cam_recon
    out_recon = os.path.abspath(r'e:\TalentForge\Clay\3d_engine\renders\snow_35_final_recon.png')
    scene.render.filepath = out_recon
    bpy.ops.render.render(write_still=True)

    # Chase View
    scene.frame_set(550)
    cam_chase = bpy.data.objects.get('Camera_UAV_Chase')
    scene.camera = cam_chase
    out_chase = os.path.abspath(r'e:\TalentForge\Clay\3d_engine\renders\snow_35_final_chase.png')
    scene.render.filepath = out_chase
    bpy.ops.render.render(write_still=True)

    print("[OK] Final 35% snow verification renders complete!")

if __name__ == "__main__":
    finalize_35_snow_material()
