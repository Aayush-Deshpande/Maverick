"""
Sets 35% Alpine Snow on High Peaks with Rock Textures Dominant:
1. Map Range: 2925m to 7616m AMSL.
2. Elevation Mask: Greater Than 0.40 (~4,800m AMSL) -> Selects upper 35% of peaks.
3. Slope Mask: Normal Z > 0.05 -> Keeps sheer cliff faces and shadowed couloirs as bare rock.
4. Math Multiply: SNOW MASK = Elevation * Slope.
5. Mix_Snow_Blend: Connects Result_Color (RGBA) to Base Color.
   - Input A: Existing Rock Color (Mix.Result) -> Dominant over 65% of terrain!
   - Input B: Snow Color (#D8D5CC neutral off-white) -> Appears on upper 35% of peaks!
   - Factor: Math_Snow_Mask
"""

import bpy
import os

def apply_35_percent_snow():
    terrain = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    mat = terrain.material_slots[0].material
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # 1. Map Range
    mr = nodes.get('Map Range')
    mr.clamp = True
    mr.inputs[1].default_value = 2925.0
    mr.inputs[2].default_value = 7616.0
    mr.inputs[3].default_value = 0.0
    mr.inputs[4].default_value = 1.0

    # 2. Elevation Mask: 0.40 (4,801m AMSL, upper 35% of mountains)
    me = nodes.get('Math_Elevation_Mask')
    me.operation = 'GREATER_THAN'
    me.inputs[1].default_value = 0.40

    # 3. Slope Mask: 0.05 (allows snow on all upward-facing alpine slopes, leaves sheer vertical cliffs bare)
    ms = nodes.get('Math_Slope_Mask')
    ms.operation = 'GREATER_THAN'
    ms.inputs[1].default_value = 0.05

    # 4. Multiply
    sm = nodes.get('Math_Snow_Mask')
    sm.operation = 'MULTIPLY'

    # 5. Snow Color Ramp
    cr_snow = nodes.get('ColorRamp_Snow')
    cr = cr_snow.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.18, 0.18, 0.19, 1.0)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.75, 0.73, 0.69, 1.0) # #D8D5CC neutral snow

    # 6. Mix_Snow_Blend
    mix_snow = nodes.get('Mix_Snow_Blend')
    bsdf = nodes.get('Principled BSDF')
    existing_mix = nodes.get('Mix')

    mix_snow.data_type = 'RGBA'
    mix_snow.blend_type = 'MIX'
    
    # Factor Socket (Index 0)
    links.new(sm.outputs['Value'], mix_snow.inputs[0])
    # A Socket (Index 6, Rock)
    links.new(existing_mix.outputs['Result'], mix_snow.inputs[6])
    # B Socket (Index 7, Snow)
    links.new(cr_snow.outputs['Color'], mix_snow.inputs[7])
    # Result Socket (Index 2, RGBA) -> Base Color
    links.new(mix_snow.outputs[2], bsdf.inputs['Base Color'])

    # Save to Models/terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved 35% alpine snow setup to Models/terrain.blend!")

    # Render Previews
    scene = bpy.context.scene
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080

    # 1. Recon Overview
    cam_recon = bpy.data.objects.get('Camera_Canyon_Recon')
    scene.camera = cam_recon
    out_recon = os.path.abspath(r'e:\TalentForge\Clay\3d_engine\renders\snow_35_balanced_recon.png')
    scene.render.filepath = out_recon
    print(f"Rendering recon overview to: {out_recon}...")
    bpy.ops.render.render(write_still=True)

    # 2. Chase View
    scene.frame_set(550)
    cam_chase = bpy.data.objects.get('Camera_UAV_Chase')
    scene.camera = cam_chase
    out_chase = os.path.abspath(r'e:\TalentForge\Clay\3d_engine\renders\snow_35_balanced_chase.png')
    scene.render.filepath = out_chase
    print(f"Rendering chase view to: {out_chase}...")
    bpy.ops.render.render(write_still=True)

    print("[OK] Balanced 35% snow renders complete!")

if __name__ == "__main__":
    apply_35_percent_snow()
