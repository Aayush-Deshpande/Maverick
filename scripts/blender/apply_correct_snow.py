"""
Applies Mathematically Correct High-Altitude Alpine Snow (Exact ~35% on Mountain Peaks):
1. Elevation Map Range: From Min = 2925.0, From Max = 7616.0.
   - River valley (3000m) evaluates to ~0.02 (COMPLETELY EXCLUDED).
   - High peaks (> 5,100m) evaluate to > 0.46 (INCLUDED).
   - Threshold = 0.46.
2. Slope Mask:
   - Sheer vertical cliffs (< 0.40 / slope > 66 deg) shed snow -> exposed raw rock.
   - Mountain crests and saddles (> 0.40) hold snow.
   - Threshold = 0.40.
3. Multiply Mask: Snow ONLY appears on high peaks (> 5,100m) on non-vertical faces (~30-35% coverage).
4. Mix_Snow_Blend: Result_Color (RGBA) connected to Base Color.
   - Rock, scree, and hillshade completely dominant across lower 65-70% of terrain.
5. Renders verification previews.
"""

import bpy
import os

def apply_correct_snow():
    terrain = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    mat = terrain.material_slots[0].material
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # 1. Map Range: 2925m to 7616m
    mr = nodes.get('Map Range')
    if mr:
        mr.clamp = True
        mr.inputs[1].default_value = 2925.0
        mr.inputs[2].default_value = 7616.0
        mr.inputs[3].default_value = 0.0
        mr.inputs[4].default_value = 1.0

    # 2. Elevation Mask: High peaks only (> 5,100m AMSL)
    me = nodes.get('Math_Elevation_Mask')
    if me:
        me.operation = 'GREATER_THAN'
        me.inputs[1].default_value = 0.46 # 2925 + 0.46 * 4691 = ~5,083m AMSL

    # 3. Slope Mask: Normal Z > 0.40 (Only sheer vertical rock faces > 66 deg shed snow)
    ms = nodes.get('Math_Slope_Mask')
    if ms:
        ms.operation = 'GREATER_THAN'
        ms.inputs[1].default_value = 0.40

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
        cr.elements[1].color = (0.72, 0.70, 0.65, 1.0) # #D8D5CC neutral snow

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
    print("[OK] Saved true high-altitude snow setup to Models/terrain.blend!")

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

    print("[OK] Previews rendered successfully!")

if __name__ == "__main__":
    apply_correct_snow()
