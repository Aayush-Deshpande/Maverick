"""
Applies Elevation + Slope Snow Mask to Existing Ladakh Terrain Material:
1. Updates Map Range to: From Min = 2925, From Max = 7616, To Min = 0, To Max = 1, Clamp = True.
2. Connects Geometry.Normal -> Separate XYZ (Normal) -> Z.
3. Math (Greater Than 0.55) for Slope Mask.
4. Math (Greater Than 0.55) for Elevation Mask.
5. Math (Multiply) combining both into SNOW MASK.
6. ColorRamp for snow layer (dark rocky gray -> #D8D5CC off-white).
7. Mix node (Mix Color) blending existing rock/hillshade base color with the snow layer using SNOW MASK.
8. Preserves all existing Hillshade, Elevation Color, and Bump/Normal nodes.
"""

import bpy

def apply_snow_nodes():
    terrain = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not terrain or not terrain.material_slots:
        print("[ERROR] Terrain object or material slot not found!")
        return

    mat = terrain.material_slots[0].material
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    print(f"[OK] Editing material: {mat.name}")

    # 1. Update Existing Map Range
    map_range = nodes.get('Map Range')
    if map_range:
        map_range.clamp = True
        map_range.inputs[1].default_value = 2925.0 # From Min
        map_range.inputs[2].default_value = 7616.0 # From Max
        map_range.inputs[3].default_value = 0.0    # To Min
        map_range.inputs[4].default_value = 1.0    # To Max
        print("[OK] Updated Map Range: 2925 to 7616 -> 0 to 1 (Clamped)")

    # 2. Existing Geometry node
    geo = nodes.get('Geometry')
    if not geo:
        print("[ERROR] Geometry node not found!")
        return

    # 3. Add Separate XYZ for Normal
    sep_norm = nodes.get('Separate_XYZ_Normal')
    if not sep_norm:
        sep_norm = nodes.new(type='ShaderNodeSeparateXYZ')
        sep_norm.name = 'Separate_XYZ_Normal'
        sep_norm.label = 'Separate Normal'
    sep_norm.location = (geo.location.x + 220, geo.location.y - 260)
    links.new(geo.outputs['Normal'], sep_norm.inputs['Vector'])
    print("[OK] Connected Geometry.Normal -> Separate_XYZ_Normal.Vector")

    # 4. Slope Mask: Normal Z > 0.55
    math_slope = nodes.get('Math_Slope_Mask')
    if not math_slope:
        math_slope = nodes.new(type='ShaderNodeMath')
        math_slope.name = 'Math_Slope_Mask'
        math_slope.label = 'Slope Mask (> 0.55)'
    math_slope.operation = 'GREATER_THAN'
    math_slope.inputs[1].default_value = 0.55
    math_slope.location = (sep_norm.location.x + 200, sep_norm.location.y)
    links.new(sep_norm.outputs['Z'], math_slope.inputs[0])
    print("[OK] Connected Separate_XYZ_Normal.Z -> Math_Slope_Mask (> 0.55)")

    # 5. Elevation Mask: Elevation Map Range > 0.55
    math_elev = nodes.get('Math_Elevation_Mask')
    if not math_elev:
        math_elev = nodes.new(type='ShaderNodeMath')
        math_elev.name = 'Math_Elevation_Mask'
        math_elev.label = 'Elevation Mask (> 0.55)'
    math_elev.operation = 'GREATER_THAN'
    math_elev.inputs[1].default_value = 0.55
    math_elev.location = (map_range.location.x + 220, map_range.location.y - 180)
    links.new(map_range.outputs['Result'], math_elev.inputs[0])
    print("[OK] Connected Map_Range.Result -> Math_Elevation_Mask (> 0.55)")

    # 6. Math Multiply: SNOW MASK = Elevation Mask * Slope Mask
    math_snow_mult = nodes.get('Math_Snow_Mask')
    if not math_snow_mult:
        math_snow_mult = nodes.new(type='ShaderNodeMath')
        math_snow_mult.name = 'Math_Snow_Mask'
        math_snow_mult.label = 'SNOW MASK (Multiply)'
    math_snow_mult.operation = 'MULTIPLY'
    math_snow_mult.location = (math_elev.location.x + 220, math_elev.location.y)
    links.new(math_elev.outputs['Value'], math_snow_mult.inputs[0])
    links.new(math_slope.outputs['Value'], math_snow_mult.inputs[1])
    print("[OK] Created SNOW MASK via Math.Multiply(Elevation, Slope)")

    # 7. Snow Color Layer: ColorRamp driven by Snow Mask
    # Transition: Dark rocky gray -> neutral off-white snow (#D8D5CC)
    snow_ramp = nodes.get('ColorRamp_Snow')
    if not snow_ramp:
        snow_ramp = nodes.new(type='ShaderNodeValToRGB')
        snow_ramp.name = 'ColorRamp_Snow'
        snow_ramp.label = 'Snow Color Ramp'
    snow_ramp.location = (math_snow_mult.location.x + 220, math_snow_mult.location.y)
    
    # Configure ColorRamp stops
    # Stop 0: Dark rocky gray transition
    # Stop 1: #D8D5CC off-white snow
    # sRGB #D8D5CC = (216/255, 213/255, 204/255) -> linear ~ (0.686, 0.665, 0.604, 1.0)
    cr = snow_ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.18, 0.18, 0.19, 1.0) # Dark rock gray
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.686, 0.665, 0.604, 1.0) # #D8D5CC neutral off-white snow

    links.new(math_snow_mult.outputs['Value'], snow_ramp.inputs['Factor'])
    print("[OK] Configured Snow ColorRamp (dark rocky gray -> #D8D5CC off-white)")

    # 8. Combine Snow Layer with Existing Rock Color System
    # Existing rock color comes from 'Mix' node (Hillshade * Elevation)
    existing_mix = nodes.get('Mix')
    bsdf = nodes.get('Principled BSDF')

    if not existing_mix or not bsdf:
        print("[ERROR] Existing Mix or Principled BSDF not found!")
        return

    # Add Mix Color node to blend existing rock color with snow
    mix_snow = nodes.get('Mix_Snow_Blend')
    if not mix_snow:
        mix_snow = nodes.new(type='ShaderNodeMix')
        mix_snow.name = 'Mix_Snow_Blend'
        mix_snow.label = 'Mix Snow & Rock'
    mix_snow.data_type = 'RGBA'
    mix_snow.blend_type = 'MIX'
    mix_snow.location = (bsdf.location.x - 180, bsdf.location.y + 80)

    # In ShaderNodeMix with RGBA data_type:
    # inputs[0] / 'Factor' -> Float Factor
    # inputs[6] / 'A' -> Color A (Existing Rock Color)
    # inputs[7] / 'B' -> Color B (Snow Color Layer)
    # outputs[2] / 'Result' -> Final Base Color
    factor_socket = mix_snow.inputs[0] # Factor
    a_socket = [inp for inp in mix_snow.inputs if inp.name == 'A' and inp.type == 'RGBA'][0]
    b_socket = [inp for inp in mix_snow.inputs if inp.name == 'B' and inp.type == 'RGBA'][0]
    result_socket = [out for out in mix_snow.outputs if out.name == 'Result'][0]

    # Connect SNOW MASK to Factor
    links.new(math_snow_mult.outputs['Value'], factor_socket)
    
    # Connect Existing Mix.Result to Input A (Rock Color)
    links.new(existing_mix.outputs['Result'], a_socket)

    # Connect Snow ColorRamp to Input B (Snow Color)
    links.new(snow_ramp.outputs['Color'], b_socket)

    # Connect Result to Principled BSDF Base Color
    links.new(result_socket, bsdf.inputs['Base Color'])

    print("[OK] Successfully integrated Snow Layer into Principled BSDF Base Color!")
    print("     - Rock coloration preserved where Snow Mask = 0")
    print("     - #D8D5CC snow appears where Snow Mask = 1")
    print("     - Hillshade, Elevation Color, and Bump/Normal intact!")

    # Save permanently to Models/terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Saved updated terrain material permanently to Models/terrain.blend!")

if __name__ == "__main__":
    apply_snow_nodes()
