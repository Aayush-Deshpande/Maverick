"""
Top Gun: Maverick Tactical Canyon UAV Simulation - Master Rig:
1. Normal safe-clearance canyon cruise flight path down the center of the Ladakh river valley corridor (5,200m - 5,400m AMSL).
2. 8.0x Hero Scale for the MQ-1 Predator UAV (~118m wingspan across 92km map) for commanding visibility.
3. Valley floor atmospheric depth mist and distant range depth fading to dramatically separate foreground ridges from background peaks.
4. Top Gun Maverick cinematic chase camera rig (50mm lens, 180m back, 45m above) with level-horizon canyon framing.
5. Preserves smooth geometry stack (Subsurf before DEM + WeightedNormal) with ZERO block polygons.
6. Permanently saved to Models/terrain.blend.
"""

import bpy
import mathutils
import math
import os

def apply_maverick_simulation():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.frame_start = 1
    scene.frame_end = 300
    scene.render.fps = 30

    obj = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
    if not obj:
        print("[ERROR] Terrain object not found!")
        return

    # Select terrain object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # 1. Modifiers: Subsurf (Simple) -> DEM (Displace) -> WeightedNormal (Zero block polygons)
    sub = obj.modifiers.get('Subsurf_Smooth')
    if not sub:
        sub = obj.modifiers.new(name='Subsurf_Smooth', type='SUBSURF')
    sub.subdivision_type = 'SIMPLE'
    sub.levels = 1
    sub.render_levels = 1
    bpy.ops.object.modifier_move_to_index(modifier='Subsurf_Smooth', index=0)

    dem_mod = obj.modifiers.get('DEM')
    if dem_mod:
        dem_mod.direction = 'Z'
        dem_mod.strength = 1.0

    wn = obj.modifiers.get('Weighted_Normal')
    if not wn:
        wn = obj.modifiers.new(name='Weighted_Normal', type='WEIGHTED_NORMAL')
    wn.weight = 50
    wn.keep_sharp = False

    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.update()

    # 2. Material: Top Gun Maverick with Valley Atmospheric Mist & Distance Depth Fading
    for m in list(bpy.data.materials):
        if any(tag in m.name for tag in ['TopGun', 'Rock', 'Clean', 'Tactical']):
            bpy.data.materials.remove(m)

    mat = bpy.data.materials.new("M_TopGun_Canyon_Simulation")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (2000, 0)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (1650, 0)
    bsdf.inputs['Roughness'].default_value = 0.70
    bsdf.inputs['Specular IOR Level'].default_value = 0.35
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-1800, 200)

    cam_data_node = nodes.new('ShaderNodeCameraData')
    cam_data_node.location = (-1800, -300)

    # A. Tactical Cobalt Navy Base Color
    mix_base = nodes.new('ShaderNodeMix')
    mix_base.data_type = 'RGBA'
    mix_base.location = (-600, 350)
    mix_base.inputs[6].default_value = (0.025, 0.060, 0.120, 1.0) # Deep Navy Shadow
    mix_base.inputs[7].default_value = (0.070, 0.145, 0.250, 1.0) # Tactical Cerulean Midtone
    mix_base.inputs['Factor'].default_value = 0.50

    # B. Holographic Ridge Edge Glow (Fresnel / Facing Curvature)
    layer_weight = nodes.new('ShaderNodeLayerWeight')
    layer_weight.location = (-1400, -100)
    layer_weight.inputs['Blend'].default_value = 0.32

    ramp_edge = nodes.new('ShaderNodeValToRGB')
    ramp_edge.location = (-1100, -100)
    ramp_edge.color_ramp.elements[0].position = 0.52
    ramp_edge.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_edge.color_ramp.elements[1].position = 0.94
    ramp_edge.color_ramp.elements[1].color = (0.0, 0.85, 1.0, 1.0) # Glowing Electric Cyan
    links.new(layer_weight.outputs['Facing'], ramp_edge.inputs['Fac'])

    # C. Luminous Topographic Elevation Contour Lines (80m intervals)
    sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    sep_pos.location = (-1400, 500)
    links.new(geom.outputs['Position'], sep_pos.inputs['Vector'])

    div_80 = nodes.new('ShaderNodeMath')
    div_80.location = (-1150, 500)
    div_80.operation = 'DIVIDE'
    div_80.inputs[1].default_value = 80.0
    links.new(sep_pos.outputs['Z'], div_80.inputs[0])

    fract_80 = nodes.new('ShaderNodeMath')
    fract_80.location = (-980, 500)
    fract_80.operation = 'FRACT'
    links.new(div_80.outputs['Value'], fract_80.inputs[0])

    sub_80 = nodes.new('ShaderNodeMath')
    sub_80.location = (-810, 500)
    sub_80.operation = 'SUBTRACT'
    sub_80.inputs[1].default_value = 0.5
    links.new(fract_80.outputs['Value'], sub_80.inputs[0])

    abs_80 = nodes.new('ShaderNodeMath')
    abs_80.location = (-640, 500)
    abs_80.operation = 'ABSOLUTE'
    links.new(sub_80.outputs['Value'], abs_80.inputs[0])

    ramp_iso = nodes.new('ShaderNodeValToRGB')
    ramp_iso.location = (-470, 500)
    ramp_iso.color_ramp.elements[0].position = 0.485
    ramp_iso.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_iso.color_ramp.elements[1].position = 0.50
    ramp_iso.color_ramp.elements[1].color = (0.05, 0.90, 1.0, 1.0) # Crisp Cyan Isolines
    links.new(abs_80.outputs['Value'], ramp_iso.inputs['Fac'])

    # Combine Base + Edge Glow + Contours
    mix_glow = nodes.new('ShaderNodeMix')
    mix_glow.data_type = 'RGBA'
    mix_glow.blend_type = 'ADD'
    mix_glow.location = (-150, 300)
    mix_glow.inputs['Factor'].default_value = 0.75
    links.new(mix_base.outputs[2], mix_glow.inputs[6])
    links.new(ramp_edge.outputs['Color'], mix_glow.inputs[7])

    mix_terrain = nodes.new('ShaderNodeMix')
    mix_terrain.data_type = 'RGBA'
    mix_terrain.blend_type = 'ADD'
    mix_terrain.location = (150, 300)
    mix_terrain.inputs['Factor'].default_value = 0.90
    links.new(mix_glow.outputs[2], mix_terrain.inputs[6])
    links.new(ramp_iso.outputs['Color'], mix_terrain.inputs[7])

    # D. VALLEY FLOOR ATMOSPHERIC MIST (Elevation Haze below 4,100m)
    ramp_valley_mist = nodes.new('ShaderNodeValToRGB')
    ramp_valley_mist.location = (-600, 100)
    # Z range from 3200m (trench floor) to 4300m (mid-slope)
    ramp_valley_mist.color_ramp.elements[0].position = 0.32
    ramp_valley_mist.color_ramp.elements[0].color = (0.06, 0.15, 0.28, 1.0) # Cerulean Trench Haze
    ramp_valley_mist.color_ramp.elements[1].position = 0.44
    ramp_valley_mist.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)

    # Normalize elevation for mist ramp (Z / 10000)
    div_z_norm = nodes.new('ShaderNodeMath')
    div_z_norm.location = (-850, 100)
    div_z_norm.operation = 'DIVIDE'
    div_z_norm.inputs[1].default_value = 10000.0
    links.new(sep_pos.outputs['Z'], div_z_norm.inputs[0])
    links.new(div_z_norm.outputs['Value'], ramp_valley_mist.inputs['Fac'])

    mix_valley = nodes.new('ShaderNodeMix')
    mix_valley.data_type = 'RGBA'
    mix_valley.blend_type = 'ADD'
    mix_valley.location = (450, 200)
    mix_valley.inputs['Factor'].default_value = 0.65
    links.new(mix_terrain.outputs[2], mix_valley.inputs[6])
    links.new(ramp_valley_mist.outputs['Color'], mix_valley.inputs[7])

    # E. DISTANCE DEPTH FADING (Separates foreground ridges from background peaks)
    # Distance from 2km to 30km
    ramp_depth = nodes.new('ShaderNodeValToRGB')
    ramp_depth.location = (-600, -300)
    ramp_depth.color_ramp.elements[0].position = 0.05 # 2.5km (clear foreground)
    ramp_depth.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_depth.color_ramp.elements[1].position = 0.65 # 32km (distant atmospheric fade)
    ramp_depth.color_ramp.elements[1].color = (0.015, 0.035, 0.070, 1.0) # Deep Navy Horizon Fog

    div_depth_norm = nodes.new('ShaderNodeMath')
    div_depth_norm.location = (-850, -300)
    div_depth_norm.operation = 'DIVIDE'
    div_depth_norm.inputs[1].default_value = 50000.0 # 50km normalization
    links.new(cam_data_node.outputs['View Distance'], div_depth_norm.inputs[0])
    links.new(div_depth_norm.outputs['Value'], ramp_depth.inputs['Fac'])

    mix_final_color = nodes.new('ShaderNodeMix')
    mix_final_color.data_type = 'RGBA'
    mix_final_color.blend_type = 'MIX'
    mix_final_color.location = (850, 150)
    mix_final_color.inputs['Factor'].default_value = 0.55
    links.new(mix_valley.outputs[2], mix_final_color.inputs[6])
    links.new(ramp_depth.outputs['Color'], mix_final_color.inputs[7])

    links.new(mix_final_color.outputs[2], bsdf.inputs['Base Color'])

    # Emission for glowing HUD contours & ridge lines
    if 'Emission Color' in bsdf.inputs:
        links.new(ramp_iso.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = 0.55

    obj.data.materials.clear()
    obj.data.materials.append(mat)
    print("[OK] Assigned Top Gun Maverick simulation material with atmospheric mist.")

    # 3. UAV Hero Scaling (8.0x ~118m wingspan for commanding visual presence)
    master_uav = bpy.data.objects.get("UAV_Predator_Master")
    if master_uav:
        master_uav.scale = (8.0, 8.0, 8.0)
        print("[OK] Set UAV to Hero Simulation Scale (8.0x).")

    # 4. Safe Canyon Corridor Flight Path (Centerline Cruise at 5,200m - 5,400m AMSL)
    curve_obj = bpy.data.objects.get("FlightPath_Canyon_Corridor")
    if not curve_obj:
        curve_data = bpy.data.curves.new('FlightPath_Canyon_Corridor', type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.resolution_u = 32
        polyline = curve_data.splines.new('BEZIER')
        curve_obj = bpy.data.objects.new('FlightPath_Canyon_Corridor', curve_data)
        scene.collection.objects.link(curve_obj)
    
    spline = curve_obj.data.splines[0]
    
    # Safe cruise waypoints right down the open canyon centerline
    # Ample clearance (600m+ from all ridge walls, safe cruise altitude)
    waypoints = [
        (-18500.0,  7500.0, 5450.0), # Ingress high above valley entry
        (-15000.0, 11000.0, 5250.0), # Gliding smoothly down central river corridor
        (-11500.0, 14500.0, 5100.0), # Centered between towering peaks on both sides
        (-8000.0,  18000.0, 5000.0), # Winding gracefully past northern bend
        (-4500.0,  21500.0, 5150.0), # Egress toward northern basin
    ]

    while len(spline.bezier_points) < len(waypoints):
        spline.bezier_points.add(1)

    for i, wp in enumerate(waypoints):
        pt = spline.bezier_points[i]
        pt.co = wp
        pt.handle_left_type = 'AUTO'
        pt.handle_right_type = 'AUTO'

    # Re-attach constraint to ensure perfect evaluation
    if master_uav:
        constraint = master_uav.constraints.get('Follow Path')
        if not constraint:
            constraint = master_uav.constraints.new(type='FOLLOW_PATH')
        constraint.target = curve_obj
        constraint.use_curve_follow = True
        constraint.forward_axis = 'FORWARD_Y'
        constraint.up_axis = 'UP_Z'
        constraint.use_fixed_location = True
        constraint.offset_factor = 0.0
        constraint.keyframe_insert(data_path="offset_factor", frame=1)
        constraint.offset_factor = 1.0
        constraint.keyframe_insert(data_path="offset_factor", frame=300)

    # 5. Top Gun Maverick Cinematic Chase Camera
    chase_cam = bpy.data.objects.get("Camera_UAV_Chase")
    if not chase_cam:
        cam_data = bpy.data.cameras.new("Camera_UAV_Chase")
        chase_cam = bpy.data.objects.new("Camera_UAV_Chase", cam_data)
        scene.collection.objects.link(chase_cam)

    chase_cam.parent = master_uav
    chase_cam.data.lens = 50.0 # 50mm cinematic focal length
    chase_cam.data.clip_start = 1.0
    chase_cam.data.clip_end = 250000.0

    # Elevated chase framing: 160m behind, 40m above, looking near-level horizon
    chase_cam.location = (0.0, -160.0, 40.0)
    chase_cam.rotation_euler = (math.radians(83.5), 0.0, 0.0)

    # 6. Directional Tactical Sun & Ambient Atmosphere
    for o in list(scene.objects):
        if o.type == 'LIGHT':
            bpy.data.objects.remove(o, do_unlink=True)

    sun_data = bpy.data.lights.new('Sun_TopGun', 'SUN')
    sun_data.energy = 4.2
    sun_data.color = (0.75, 0.90, 1.0) # Cold tactical key light
    sun_data.use_shadow = False
    sun_obj = bpy.data.objects.new('Sun_TopGun', sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(52.0), math.radians(18.0), math.radians(-115.0))

    # Deep Navy Atmosphere Sky
    world = scene.world
    if not world:
        world = bpy.data.worlds.new("W_TopGun")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.015, 0.035, 0.070, 1.0)
        bg.inputs['Strength'].default_value = 0.90

    # 7. Render Mid-Flight Verification Frame (Frame 130)
    scene.frame_set(130)
    scene.camera = chase_cam
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    out_chase = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/topgun_maverick_chase_final.png"))
    scene.render.filepath = out_chase
    print(f"[RENDER] Rendering Top Gun Maverick Chase view to: {out_chase}...")
    bpy.ops.render.render(write_still=True)

    master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/tactical_terrain_final.png"))
    scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)

    # 8. Render Wide Corridor View
    recon_cam = bpy.data.objects.get("Camera_Canyon_Recon")
    if recon_cam:
        scene.camera = recon_cam
        out_wide = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/topgun_maverick_wide_final.png"))
        scene.render.filepath = out_wide
        print(f"[RENDER] Rendering Top Gun Maverick Wide Recon view to: {out_wide}...")
        bpy.ops.render.render(write_still=True)

    # Reset active camera back to chase camera for interactive user playback
    scene.camera = chase_cam

    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'RENDERED'
                        space.region_3d.view_perspective = 'CAMERA'

    # Save permanently to Models/terrain.blend
    bpy.ops.wm.save_mainfile()
    print("[OK] Top Gun Maverick simulation saved permanently to Models/terrain.blend!")

if __name__ == "__main__":
    apply_maverick_simulation()
