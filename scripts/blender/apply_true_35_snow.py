"""
Applies True Elevation-Scaled Snow Mask (~35% Snow on High Peak Crests):
1. Map Range: From Min = 2925.0, From Max = 7616.0, To Min = 0.0, To Max = 1.0, Clamped = True.
2. Elevation Threshold: 0.46 (corresponds to ~5,080m AMSL, covering the upper 30-35% of the mountain peaks).
3. Slope Threshold: Normal Z > 0.68 (< 47 deg slope) so steep mountain rock faces remain exposed.
4. Correct RGBA Sockets on Mix_Snow_Blend: Result_Color -> Principled BSDF Base Color.
5. Preserves 100% of existing rock color, hillshade, and normal bump across the lower 65-70% of terrain.
6. Renders verification images.
"""

import bpy
import os

def apply_true_35_snow():
    terrain = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    mat = terrain.material_slots[0].material
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # 1. Map Range: Real geographic span 2925m to 7616m AMSL
    mr = nodes.get('Map Range')
    if mr:
        mr.clamp = True
        mr.inputs[1].default_value = 2925.0
        mr.inputs[2].default_value = 7616.0
        mr.inputs[3].default_value = 0.0
        mr.inputs[4].default_value = 1.0

    # 2. Elevation Threshold: 0.46 = 2925 + 0.46 * 4691 = ~5,080m AMSL (Upper 35% of peaks)
    me = nodes.get('Math_Elevation_Mask')
    if me:
        me.operation = 'GREATER_THAN'
        me.inputs[1].default_value = 0.46

    # 3. Slope Threshold: Normal Z > 0.68 (Slopes flatter than 47 deg)
    ms = nodes.get('Math_Slope_Mask')
    if ms:
        ms.operation = 'GREATER_THAN'
        ms.inputs[1].default_value = 0.68

    # 4. Multiply Snow Mask
    sm = nodes.get('Math_Snow_Mask')
    if sm:
        sm.operation = 'MULTIPLY'

    # 5. Snow Color Ramp
    cr_snow = nodes.get('ColorRamp_Snow')
    if cr_snow:
        cr = cr_snow.color_ramp
        cr.elements[0].position = 0.0
        cr.elements[0].color = (0.18, 0.18, 0.19, 1.0)
        cr.elements[1].position = 1.0
        cr.elements[1].color = (0.686, 0.665, 0.604, 1.0) # #D8D5CC

    # 6. Mix_Snow_Blend
    mix_snow = nodes.get('Mix_Snow_Blend')
    bsdf = nodes.get('Principled BSDF')
    existing_mix = nodes.get('Mix')

    if mix_snow and bsdf and existing_mix:
        mix_snow.data_type = 'RGBA'
        mix_snow.blend_type = 'MIX'
        
        factor_sock = mix_snow.inputs[0] # Factor_Float
        a_sock = mix_snow.inputs[6]      # A_Color (Rock)
        b_sock = mix_snow.inputs[7]      # B_Color (Snow)
        result_sock = mix_snow.outputs[2] # Result_Color (RGBA)

        links.new(sm.outputs['Value'], factor_sock)
        links.new(existing_mix.outputs['Result'], a_sock)
        links.new(cr_snow.outputs['Color'], b_sock)
        links.new(result_sock, bsdf.inputs['Base Color'])

    # Save to Models/terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved true 35% snow setup to Models/terrain.blend!")

    # Render Previews
    scene = bpy.context.scene
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080

    # 1. Recon Overview
    cam_recon = bpy.data.objects.get('Camera_Canyon_Recon')
    if cam_recon:
        scene.camera = cam_recon
        out_recon = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/snow_35_recon_final.png"))
        scene.render.filepath = out_recon
        print(f"Rendering recon overview to: {out_recon}...")
        bpy.ops.render.render(write_still=True)

    # 2. Chase View
    scene.frame_set(550)
    cam_chase = bpy.data.objects.get('Camera_UAV_Chase')
    if cam_chase:
        scene.camera = cam_chase
        out_chase = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/snow_35_chase_final.png"))
        scene.render.filepath = out_chase
        print(f"Rendering chase view to: {out_chase}...")
        bpy.ops.render.render(write_still=True)

    print("[OK] All previews rendered successfully!")

if __name__ == "__main__":
    apply_true_35_snow()
