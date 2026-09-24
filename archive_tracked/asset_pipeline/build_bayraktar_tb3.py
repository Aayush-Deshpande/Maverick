"""
=============================================================================
BAYRAKTAR TB3 UCAV - MASTER 3D DIGITAL TWIN GENERATOR (PIXEL-PERFECT V3)
=============================================================================
Fully optimized, grain-free production digital twin matching:
1. image.png (Hero Tactical PBR: dark graphite carbon, dorsal SATCOM dome,
   CATS EO/IR turret with sapphire windows, red boom warning bands, 4x MAM-L
   smart munitions, seamless dark studio floor, resting on ground at Z=0.00).
2. bayraktar-tb3-ucav-3d-model-fdda7fefdc.jpg (Ghost Mode / Wireframe Mode:
   Subdivision Level 0 Quad Topology over warm clay shading).
3. bayraktar-tb3-ucav-3d-model-82ba0fb294.jpg (Clean consolidated hierarchy,
   Subsurf Levels Viewport = 0 for 120 FPS, Render = 2, Optimal Display).
4. ZERO floating quads: All decals, Turkish flags, PT-2 markings, roundels,
   danger warning stripes, and stencils are directly integrated into mesh UVs!
=============================================================================
"""

import bpy
import bmesh
import math
import os
import mathutils
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LIB_DIR = ROOT / 'scripts' / 'lib'
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))
import anumaan_blender_lib as alb

def run():
    print("======================================================================")
    print("RECONSTRUCTING BAYRAKTAR TB3 UCAV - MASTER PIXEL-PERFECT DIGITAL TWIN")
    print("======================================================================")

    # 1. Reset Scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "TB3_Scene"
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.length_unit = 'METERS'
    scene.unit_settings.scale_length = 1.0

    models_dir = ROOT / "Models"
    tex_dir = models_dir / "textures"
    output_blend = models_dir / "airframes" / "bayraktar_tb3.blend" 
    diffuse_4k = os.path.join(tex_dir, "tb3_body_diffuse_4k.png")
    roughness_4k = os.path.join(tex_dir, "tb3_body_roughness_4k.png")
    normal_4k = os.path.join(tex_dir, "tb3_body_normal_4k.png")

    # Viewport and Render Settings
    # Use EEVEE by default for instant 120 FPS, 0% grain, interactive viewing
    scene.render.engine = 'BLENDER_EEVEE'
    if hasattr(scene, 'eevee'):
        if hasattr(scene.eevee, 'use_gtao'):
            scene.eevee.use_gtao = True
        if hasattr(scene.eevee, 'use_ssr'):
            scene.eevee.use_ssr = True

    # Color Management
    scene.display_settings.display_device = 'sRGB'
    available_transforms = [v.name for v in scene.view_settings.bl_rna.properties['view_transform'].enum_items]
    scene.view_settings.view_transform = 'AgX' if 'AgX' in available_transforms else ('Filmic' if 'Filmic' in available_transforms else 'Standard')
    scene.view_settings.look = 'Medium High Contrast'

    # Ground alignment constant: Bottom of wheels sits exactly at Z = 0.000m!
    Z_OFFSET = 1.020

    # Twin properties per Section 13.2
    scene["twin_platform_id"] = "bayraktar_tb3"
    scene["twin_time_s"] = 0.0
    scene["prop_rpm_E1"] = 0.0
    scene["display_mode"] = 0
    scene["wing_fold"] = 0.0
    scene["gear_retract"] = 0.0
    scene["prop_spin"] = 0.0

    # 2. Collections Setup (Matching Turbosquid structure)
    master_col = scene.collection
    twin_col = bpy.data.collections.new("Bayraktar_TB3_UCAV")
    master_col.children.link(twin_col)

    cols = {}
    col_names = [
        "Airframe", "Wings", "Tail", "Propulsion", "Landing_Gear",
        "Sensors_Payload", "Internal_Systems", "Cameras", "Lighting", "Environment"
    ]
    for cname in col_names:
        c = bpy.data.collections.new(cname)
        twin_col.children.link(c)
        cols[cname] = c

    # Root Empty Object (Centered at ground contact Z = 0.000m)
    root_empty = bpy.data.objects.new("TB3_Root", None)
    root_empty.empty_display_type = 'ARROWS'
    root_empty.empty_display_size = 1.5
    root_empty.location = (0, 0, 0)
    cols["Airframe"].objects.link(root_empty)

    # 3. Master Materials & Shaders
    print("Building Photorealistic 4K PBR & Wireframe Shaders...")

    # 3.1 Material 1: Tactical Carbon PBR (Hero image.png)
    mat_pbr = bpy.data.materials.new("TB3_Tactical_PBR")
    mat_pbr.use_nodes = True
    pnodes = mat_pbr.node_tree.nodes
    plinks = mat_pbr.node_tree.links
    pnodes.clear()

    out_pbr = pnodes.new('ShaderNodeOutputMaterial')
    out_pbr.location = (1100, 0)

    bsdf_pbr = pnodes.new('ShaderNodeBsdfPrincipled')
    bsdf_pbr.location = (500, 100)
    # Tactical dark carbon graphite base color
    bsdf_pbr.inputs['Base Color'].default_value = (0.135, 0.145, 0.160, 1.0)
    bsdf_pbr.inputs['Metallic'].default_value = 0.02
    bsdf_pbr.inputs['Roughness'].default_value = 0.38
    bsdf_pbr.inputs['IOR'].default_value = 1.50

    if os.path.exists(diffuse_4k):
        tex_d = pnodes.new('ShaderNodeTexImage')
        tex_d.location = (-150, 300)
        tex_d.image = bpy.data.images.load(diffuse_4k)
        plinks.new(tex_d.outputs['Color'], bsdf_pbr.inputs['Base Color'])

    if os.path.exists(roughness_4k):
        tex_r = pnodes.new('ShaderNodeTexImage')
        tex_r.location = (-150, 0)
        tex_r.image = bpy.data.images.load(roughness_4k)
        if hasattr(tex_r.image, 'colorspace_settings'):
            tex_r.image.colorspace_settings.name = 'Non-Color'
        plinks.new(tex_r.outputs['Color'], bsdf_pbr.inputs['Roughness'])

    if os.path.exists(normal_4k):
        tex_n = pnodes.new('ShaderNodeTexImage')
        tex_n.location = (-400, -250)
        tex_n.image = bpy.data.images.load(normal_4k)
        if hasattr(tex_n.image, 'colorspace_settings'):
            tex_n.image.colorspace_settings.name = 'Non-Color'
        norm_node = pnodes.new('ShaderNodeNormalMap')
        norm_node.location = (-150, -250)
        norm_node.inputs['Strength'].default_value = 0.75
        plinks.new(tex_n.outputs['Color'], norm_node.inputs['Color'])
        plinks.new(norm_node.outputs['Normal'], bsdf_pbr.inputs['Normal'])

    # Holographic X-Ray Rim Glow branch
    fresnel = pnodes.new('ShaderNodeFresnel')
    fresnel.location = (100, -450)
    fresnel.inputs['IOR'].default_value = 1.30

    emission = pnodes.new('ShaderNodeEmission')
    emission.location = (300, -450)
    emission.inputs['Color'].default_value = (0.05, 0.85, 1.0, 1.0)
    emission.inputs['Strength'].default_value = 3.5

    transp = pnodes.new('ShaderNodeBsdfTransparent')
    transp.location = (300, -320)
    transp.inputs['Color'].default_value = (0.85, 0.95, 1.0, 1.0)

    mix_xray_glow = pnodes.new('ShaderNodeMixShader')
    mix_xray_glow.location = (550, -400)
    plinks.new(fresnel.outputs['Fac'], mix_xray_glow.inputs['Factor'])
    plinks.new(transp.outputs['BSDF'], mix_xray_glow.inputs[1])
    plinks.new(emission.outputs['Emission'], mix_xray_glow.inputs[2])

    val_xray = pnodes.new('ShaderNodeValue')
    val_xray.name = "XRayFactor"
    val_xray.location = (550, -200)
    val_xray.outputs['Value'].default_value = 0.0

    mix_master = pnodes.new('ShaderNodeMixShader')
    mix_master.location = (850, 0)
    plinks.new(val_xray.outputs['Value'], mix_master.inputs['Factor'])
    plinks.new(bsdf_pbr.outputs['BSDF'], mix_master.inputs[1])
    plinks.new(mix_xray_glow.outputs['Shader'], mix_master.inputs[2])
    plinks.new(mix_master.outputs['Shader'], out_pbr.inputs['Surface'])
    if hasattr(mat_pbr, 'blend_method'):
        mat_pbr.blend_method = 'HASHED'
    alb.add_twin_nodes(mat_pbr, is_skin=True)

    # 3.2 Material 2: Wireframe Clay Topology Shader (matching fdda7fefdc.jpg)
    mat_wire = bpy.data.materials.new("TB3_Wireframe_Clay")
    mat_wire.use_nodes = True
    wnodes = mat_wire.node_tree.nodes
    wlinks = mat_wire.node_tree.links
    wnodes.clear()

    out_wire = wnodes.new('ShaderNodeOutputMaterial')
    out_wire.location = (800, 0)

    # Warm neutral clay surface matching fdda7fefdc.jpg
    bsdf_clay = wnodes.new('ShaderNodeBsdfPrincipled')
    bsdf_clay.location = (300, 150)
    bsdf_clay.inputs['Base Color'].default_value = (0.68, 0.65, 0.60, 1.0) # Warm clay
    bsdf_clay.inputs['Metallic'].default_value = 0.0
    bsdf_clay.inputs['Roughness'].default_value = 0.44

    # Crisp dark quad wireframe line
    bsdf_dark_line = wnodes.new('ShaderNodeEmission')
    bsdf_dark_line.location = (300, -150)
    bsdf_dark_line.inputs['Color'].default_value = (0.10, 0.10, 0.11, 1.0)
    bsdf_dark_line.inputs['Strength'].default_value = 1.0

    wire_node = wnodes.new('ShaderNodeWireframe')
    wire_node.location = (100, 0)
    wire_node.use_pixel_size = True
    wire_node.inputs['Size'].default_value = 0.90

    mix_wire = wnodes.new('ShaderNodeMixShader')
    mix_wire.location = (550, 0)
    wlinks.new(wire_node.outputs['Fac'], mix_wire.inputs['Factor'])
    wlinks.new(bsdf_clay.outputs['BSDF'], mix_wire.inputs[1])
    wlinks.new(bsdf_dark_line.outputs['Emission'], mix_wire.inputs[2])
    wlinks.new(mix_wire.outputs['Shader'], out_wire.inputs['Surface'])

    # 3.3 Supporting PBR Materials
    def create_pbr_material(name, base_color=(0.5, 0.5, 0.5, 1.0), metallic=0.0, roughness=0.5, ior=1.45):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.inputs['Base Color'].default_value = base_color
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
        bsdf.inputs['IOR'].default_value = ior
        links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
        alb.add_twin_nodes(mat, is_skin=False)
        return mat

    mat_sapphire = create_pbr_material("TB3_Sapphire_Optics", base_color=(0.04, 0.18, 0.38, 1.0), roughness=0.04, ior=1.76)
    mat_alloy = create_pbr_material("TB3_Machined_Alloy", base_color=(0.80, 0.82, 0.85, 1.0), metallic=0.92, roughness=0.22)
    mat_chrome = create_pbr_material("TB3_Chrome_Piston", base_color=(0.95, 0.95, 0.96, 1.0), metallic=0.98, roughness=0.06)
    mat_rubber = create_pbr_material("TB3_Tire_Rubber", base_color=(0.035, 0.035, 0.04, 1.0), roughness=0.72)
    mat_propeller = create_pbr_material("TB3_Propeller_Blade", base_color=(0.04, 0.045, 0.05, 1.0), roughness=0.32)
    mat_yellow = create_pbr_material("TB3_Hazard_Yellow", base_color=(0.92, 0.74, 0.08, 1.0), roughness=0.28)
    mat_maml_body = create_pbr_material("TB3_MAML_Body", base_color=(0.28, 0.30, 0.33, 1.0), roughness=0.35)
    mat_satcom = create_pbr_material("TB3_SATCOM_Dome", base_color=(0.13, 0.14, 0.15, 1.0), roughness=0.38, metallic=0.04)
    mat_cats = create_pbr_material("TB3_CATS_Gimbal", base_color=(0.18, 0.20, 0.22, 1.0), roughness=0.28, metallic=0.75)

    # 3.4 Modifiers Helper (Subsurf Levels: Viewport = 0, Render = 2, Optimal Display)
    def set_smooth_and_modifiers(obj, subdiv_levels=0, add_bevel=True):
        for poly in obj.data.polygons:
            poly.use_smooth = True
        if add_bevel:
            bev = obj.modifiers.new(name="Bevel", type='BEVEL')
            bev.width = 0.002
            bev.segments = 2
            bev.limit_method = 'ANGLE'
            bev.angle_limit = math.radians(35)
        if subdiv_levels >= 0:
            sub = obj.modifiers.new(name="Subdivision", type='SUBSURF')
            sub.levels = 0 # 0 subdivisions in Viewport -> 120 FPS buttery smooth orbit!
            sub.render_levels = 2 # 2 subdivisions at Render time -> pristine curved surfaces
            sub.show_only_control_edges = True # Optimal display matching Turbosquid reference!

    # 4. MODELING: FUSELAGE & INTEGRATED UV MAPPING
    print("Reconstructing Aerodynamic Monocoque Fuselage & Dorsal SATCOM Dome...")
    fuse_sections = [
        # (Y, (Width_X, Height_Z, Center_Z))
        ( 3.85, (0.10, 0.08, -0.04)),   # Nose apex probe collar
        ( 3.65, (0.34, 0.28, -0.06)),   # Forward nose dome
        ( 3.40, (0.64, 0.52, -0.08)),   # Forward chin camera cradle
        ( 3.05, (0.92, 0.74, -0.07)),   # Nose flare
        ( 2.65, (1.10, 0.86, -0.05)),   # Nose gear station
        ( 2.20, (1.18, 0.92, -0.02)),   # SATCOM radome forward taper
        ( 1.70, (1.24, 0.94,  0.01)),   # Mid SATCOM dorsal crest
        ( 1.25, (1.28, 0.96,  0.04)),   # Mid fuselage
        ( 0.75, (1.30, 0.94,  0.06)),   # Forward wing root
        ( 0.25, (1.30, 0.90,  0.08)),   # Center wing root / dorsal NACA scoop
        (-0.25, (1.28, 0.86,  0.09)),   # Wing center section
        (-0.70, (1.24, 0.84,  0.11)),   # Aft wing root / ventral scoop start
        (-1.15, (1.14, 0.85,  0.15)),   # Nacelle start & lower radiator intake
        (-1.50, (0.96, 0.80,  0.22)),   # Engine mid nacelle
        (-1.75, (0.76, 0.70,  0.26)),   # Nacelle aft taper
        (-1.95, (0.50, 0.50,  0.28)),   # Propeller firewall collar
    ]

    bm_fuse = bmesh.new()
    prev_verts = []
    num_pts = 36

    for y, (wx, hz, cz) in fuse_sections:
        ring_verts = []
        for j in range(num_pts):
            angle = j * (2.0 * math.pi / num_pts)
            sin_a = math.sin(angle)
            cos_a = math.cos(angle)

            rad_mod_z = 1.0
            rad_mod_x = 1.0

            # Dorsal SATCOM Blended Teardrop Dome (Y between 0.8 and 2.6)
            if sin_a > 0 and 0.8 < y < 2.6:
                dome_fac = math.sin(math.pi * (y - 0.8) / 1.8)
                rad_mod_z += 0.22 * dome_fac * (sin_a ** 2)

            # Dorsal Engine Cowl Hump (Y between -0.6 and -1.9)
            if sin_a > 0 and -1.9 < y < -0.6:
                cowl_fac = math.sin(math.pi * (y - (-1.9)) / 1.3)
                rad_mod_z += 0.20 * cowl_fac * (sin_a ** 2)

            # Chine flank lateral contour
            if abs(sin_a) < 0.35:
                rad_mod_x *= 1.06

            # Belly chine profile
            if sin_a < -0.4:
                rad_mod_z *= 0.92

            vx = 0.5 * wx * cos_a * rad_mod_x
            vy = y
            vz = cz + 0.5 * hz * sin_a * rad_mod_z + Z_OFFSET
            v = bm_fuse.verts.new((vx, vy, vz))
            ring_verts.append(v)

        if prev_verts:
            for j in range(num_pts):
                bm_fuse.faces.new([prev_verts[j], prev_verts[(j + 1) % num_pts], ring_verts[(j + 1) % num_pts], ring_verts[j]])
        else:
            nose_tip = bm_fuse.verts.new((0.0, y + 0.04, cz + Z_OFFSET))
            for j in range(num_pts):
                bm_fuse.faces.new([nose_tip, ring_verts[(j + 1) % num_pts], ring_verts[j]])

        prev_verts = ring_verts

    firewall_center = bm_fuse.verts.new((0.0, -1.95, 0.28 + Z_OFFSET))
    for j in range(num_pts):
        bm_fuse.faces.new([prev_verts[j], prev_verts[(j + 1) % num_pts], firewall_center])

    # Integrated UV Mapping for Fuselage -> Quadrant 1 (U: [0.05, 0.46], V: [0.50, 1.00])
    uv_lay = bm_fuse.loops.layers.uv.new("UVMap")
    for face in bm_fuse.faces:
        for loop in face.loops:
            vco = loop.vert.co
            # Lengthwise:
            # Starboard (+X): Firewall at -1.95m -> U=0.05, Nose at +3.85m -> U=0.46
            # Port (-X): Nose at +3.85m -> U=0.05, Firewall at -1.95m -> U=0.46
            t_len = max(0.0, min(1.0, (vco.y - (-1.95)) / 5.80))
            if vco.x >= 0:
                u_coord = 0.05 + t_len * 0.41
            else:
                u_coord = 0.05 + (1.0 - t_len) * 0.41

            # Circumferential angle around fuselage center:
            # Dorsal spine -> V=0.750, Port flank -> V=0.875, Starboard flank -> V=0.625, Belly -> V=0.50/1.00
            ang = math.atan2(vco.x, vco.z - (0.05 + Z_OFFSET))
            v_coord = 0.750 - (ang / (2.0 * math.pi)) * 0.50
            v_coord = max(0.50, min(1.0, v_coord))
            loop[uv_lay].uv = (u_coord, v_coord)

    mesh_fuse = bpy.data.meshes.new("Fuselage_Mesh")
    bm_fuse.to_mesh(mesh_fuse)
    bm_fuse.free()

    obj_fuse = bpy.data.objects.new("Fuselage", mesh_fuse)
    obj_fuse.parent = root_empty
    cols["Airframe"].objects.link(obj_fuse)
    obj_fuse.data.materials.append(mat_pbr)
    set_smooth_and_modifiers(obj_fuse, subdiv_levels=2)

    # 4.1 Forward Pitot Probe
    bpy.ops.mesh.primitive_cylinder_add(radius=0.009, depth=0.92, vertices=20, location=(0, 4.30, -0.04 + Z_OFFSET), rotation=(math.radians(90), 0, 0))
    obj_pitot = bpy.context.active_object
    obj_pitot.name = "Nose_Pitot_Probe"
    obj_pitot.parent = root_empty
    cols["Airframe"].objects.link(obj_pitot)
    scene.collection.objects.unlink(obj_pitot)
    obj_pitot.data.materials.append(mat_alloy)
    set_smooth_and_modifiers(obj_pitot, subdiv_levels=0, add_bevel=False)

    # 4.2 Ventral Radiator Scoop / Intake (matching image.png underside & fdda7fefdc.jpg)
    bm_vscoop = bmesh.new()
    scoop_sections = [
        (-0.75, (0.32, 0.08, -0.32 + Z_OFFSET)),
        (-0.95, (0.42, 0.16, -0.36 + Z_OFFSET)),
        (-1.20, (0.44, 0.18, -0.38 + Z_OFFSET)),
        (-1.45, (0.40, 0.14, -0.34 + Z_OFFSET)),
        (-1.65, (0.28, 0.06, -0.30 + Z_OFFSET)),
    ]
    prev_sverts = []
    num_spts = 16
    for sy, (swx, shz, scz) in scoop_sections:
        ring = []
        for sj in range(num_spts):
            s_ang = sj * (2.0 * math.pi / num_spts)
            sz_mod = math.sin(s_ang)
            if sz_mod > 0:
                sz_val = scz + 0.5 * shz * sz_mod * 0.3
            else:
                sz_val = scz + 0.5 * shz * sz_mod
            sx_val = 0.5 * swx * math.cos(s_ang)
            v = bm_vscoop.verts.new((sx_val, sy, sz_val))
            ring.append(v)
        if prev_sverts:
            for sj in range(num_spts):
                bm_vscoop.faces.new([prev_sverts[sj], prev_sverts[(sj + 1) % num_spts], ring[(sj + 1) % num_spts], ring[sj]])
        prev_sverts = ring
    
    rear_tip = bm_vscoop.verts.new((0.0, -1.68, -0.30 + Z_OFFSET))
    for sj in range(num_spts):
        bm_vscoop.faces.new([prev_sverts[sj], prev_sverts[(sj + 1) % num_spts], rear_tip])

    mesh_vscoop = bpy.data.meshes.new("Ventral_Radiator_Scoop_Mesh")
    bm_vscoop.to_mesh(mesh_vscoop)
    bm_vscoop.free()
    obj_vscoop = bpy.data.objects.new("Ventral_Radiator_Scoop", mesh_vscoop)
    obj_vscoop.parent = root_empty
    cols["Airframe"].objects.link(obj_vscoop)
    obj_vscoop.data.materials.append(mat_pbr)
    set_smooth_and_modifiers(obj_vscoop, subdiv_levels=1)

    # 4.3 Dorsal Composite SATCOM Radome (matching image.png callout)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, segments=24, ring_count=16, location=(0, 1.65, 0.46 + Z_OFFSET))
    obj_satcom = bpy.context.active_object
    obj_satcom.name = "SATCOM_Radome"
    obj_satcom.scale = (0.95, 2.6, 0.65) # Streamlined teardrop radome
    obj_satcom.parent = root_empty
    cols["Airframe"].objects.link(obj_satcom)
    scene.collection.objects.unlink(obj_satcom)
    obj_satcom.data.materials.append(mat_satcom)
    set_smooth_and_modifiers(obj_satcom, subdiv_levels=1)

    # 5. MODELING: 14.0M SUPERCRITICAL WINGS WITH INTEGRATED UVS
    print("Reconstructing 14.0m Wingspan with Integrated De-Ice Boots & Insignia UVs...")

    def create_airfoil_cross_section(chord=1.0, thickness=0.13, num_points=14):
        pts = []
        for i in range(num_points + 1):
            t = i / float(num_points)
            xc = 1.0 - t
            yt = 5.0 * thickness * (0.2969 * math.sqrt(xc) - 0.1260 * xc - 0.3516 * (xc**2) + 0.2843 * (xc**3) - 0.1015 * (xc**4))
            pts.append((xc * chord, yt * chord))
        for i in range(1, num_points):
            t = i / float(num_points)
            xc = t
            yt = -5.0 * thickness * (0.2969 * math.sqrt(xc) - 0.1260 * xc - 0.3516 * (xc**2) + 0.2843 * (xc**3) - 0.1015 * (xc**4))
            pts.append((xc * chord, yt * chord))
        return pts

    def build_wing_mesh(name, x_coords, sweep_y, dih_z, chords, is_left=True, is_local=False):
        bm = bmesh.new()
        prev_ring = []
        pts_airfoil = create_airfoil_cross_section(chord=1.0, thickness=0.13, num_points=14)
        num_airfoil_pts = len(pts_airfoil)
        ring_history = []

        for x_pos, y_off, z_off, c_len in zip(x_coords, sweep_y, dih_z, chords):
            ring = []
            for cx, cz in pts_airfoil:
                vx = x_pos
                vy = (0.0 if is_local else 0.45) + y_off - cx * c_len
                vz = (0.0 if is_local else 0.08 + Z_OFFSET) + z_off + cz * c_len
                v = bm.verts.new((vx, vy, vz))
                ring.append(v)

            if prev_ring:
                for j in range(num_airfoil_pts):
                    bm.faces.new([prev_ring[j], prev_ring[(j + 1) % num_airfoil_pts], ring[(j + 1) % num_airfoil_pts], ring[j]])
            else:
                root_c = bm.verts.new((x_coords[0], (0.0 if is_local else 0.45) + sweep_y[0] - 0.5 * chords[0], (0.0 if is_local else 0.08 + Z_OFFSET) + dih_z[0]))
                for j in range(num_airfoil_pts):
                    bm.faces.new([root_c, ring[(j + 1) % num_airfoil_pts], ring[j]])

            prev_ring = ring
            ring_history.append(ring)

        tip_c = bm.verts.new((x_coords[-1], (0.0 if is_local else 0.45) + sweep_y[-1] - 0.5 * chords[-1], (0.0 if is_local else 0.08 + Z_OFFSET) + dih_z[-1]))
        for j in range(num_airfoil_pts):
            bm.faces.new([tip_c, prev_ring[j], prev_ring[(j + 1) % num_airfoil_pts]])

        # Deterministic Global Span UV Unwrapping for Wings -> Quadrant 2 (U: [0.525, 0.975], V: [0.52, 0.98])
        uv_lay = bm.loops.layers.uv.new("UVMap")
        for face in bm.faces:
            for loop in face.loops:
                vco = loop.vert.co
                # Spanwise station: root (|X|=0.64m) to tip (|X|=7.00m)
                abs_x = (2.30 + abs(vco.x)) if is_local else abs(vco.x)
                t_span = max(0.0, min(1.0, (abs_x - 0.64) / (7.00 - 0.64)))
                u_coord = 0.525 + t_span * 0.450

                # Chordwise: leading edge (front) to trailing edge (rear)
                curr_chord = chords[0]
                y_lead = (0.0 if is_local else 0.45) + sweep_y[0]
                t_chord = max(0.0, min(1.0, (y_lead - vco.y) / curr_chord))

                if is_left:
                    # Port Wing: Leading edge at V=0.980, Trailing edge at V=0.765
                    v_coord = 0.980 - t_chord * 0.215
                else:
                    # Starboard Wing: Leading edge at V=0.736, Trailing edge at V=0.521
                    v_coord = 0.736 - t_chord * 0.215

                loop[uv_lay].uv = (max(0.50, min(1.0, u_coord)), max(0.50, min(1.0, v_coord)))

        mesh = bpy.data.meshes.new(f"{name}_Mesh")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(name, mesh)
        obj.data.materials.append(mat_pbr)
        return obj

    # 5.1 Inner Wings (Fixed Root to Fold Station X = ±2.30m)
    x_in_l = [-0.64, -1.15, -1.60, -1.70, -2.00, -2.30]
    swp_in = [0.0, -0.02, -0.04, -0.05, -0.07, -0.08]
    dih_in = [0.0, 0.01, 0.02, 0.025, 0.035, 0.04]
    chd_in = [1.32, 1.25, 1.18, 1.16, 1.12, 1.08]

    obj_wing_in_left = build_wing_mesh("Wing_Inner_Left", x_in_l, swp_in, dih_in, chd_in, is_left=True)
    obj_wing_in_left.parent = root_empty
    cols["Wings"].objects.link(obj_wing_in_left)
    set_smooth_and_modifiers(obj_wing_in_left, subdiv_levels=2)

    x_in_r = [0.64, 1.15, 1.60, 1.70, 2.00, 2.30]
    obj_wing_in_right = build_wing_mesh("Wing_Inner_Right", x_in_r, swp_in, dih_in, chd_in, is_left=False)
    obj_wing_in_right.parent = root_empty
    cols["Wings"].objects.link(obj_wing_in_right)
    set_smooth_and_modifiers(obj_wing_in_right, subdiv_levels=2)

    # 5.2 Wing Fold Pivots (Empty Controllers) at X = ±2.30, Y = 0.35, Z = 0.12 + Z_OFFSET
    pivot_fold_left = bpy.data.objects.new("Pivot_WingFold_Left", None)
    pivot_fold_left.location = (-2.30, 0.35, 0.12 + Z_OFFSET)
    pivot_fold_left.empty_display_type = 'CIRCLE'
    pivot_fold_left.empty_display_size = 0.35
    pivot_fold_left.parent = root_empty
    cols["Wings"].objects.link(pivot_fold_left)

    pivot_fold_right = bpy.data.objects.new("Pivot_WingFold_Right", None)
    pivot_fold_right.location = (2.30, 0.35, 0.12 + Z_OFFSET)
    pivot_fold_right.empty_display_type = 'CIRCLE'
    pivot_fold_right.empty_display_size = 0.35
    pivot_fold_right.parent = root_empty
    cols["Wings"].objects.link(pivot_fold_right)

    # 5.3 Outer Wings (Local Coordinates relative to fold pivot, extending to 7.0m tip)
    lx_out_l = [0.0, -1.0, -2.1, -3.3, -4.70]
    lx_out_r = [0.0,  1.0,  2.1,  3.3,  4.70]
    swp_out_loc = [0.0, -0.06, -0.14, -0.22, -0.32]
    dih_out_loc = [0.0, 0.04, 0.09, 0.15, 0.22]
    chd_out = [1.08, 0.94, 0.78, 0.64, 0.48]

    obj_wing_out_left = build_wing_mesh("Wing_Outer_Left", lx_out_l, swp_out_loc, dih_out_loc, chd_out, is_left=True, is_local=True)
    obj_wing_out_left.parent = pivot_fold_left
    cols["Wings"].objects.link(obj_wing_out_left)
    set_smooth_and_modifiers(obj_wing_out_left, subdiv_levels=2)

    obj_wing_out_right = build_wing_mesh("Wing_Outer_Right", lx_out_r, swp_out_loc, dih_out_loc, chd_out, is_left=False, is_local=True)
    obj_wing_out_right.parent = pivot_fold_right
    cols["Wings"].objects.link(obj_wing_out_right)
    set_smooth_and_modifiers(obj_wing_out_right, subdiv_levels=2)

    # 5.4 Underwing Flap Track Fairings (Canoes) - 4 per wing matching image.png
    def create_flap_canoe(name, loc, parent_obj):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.038, depth=0.48, vertices=16, location=loc, rotation=(math.radians(90), 0, 0))
        c_obj = bpy.context.active_object
        c_obj.name = name
        c_obj.parent = parent_obj
        cols["Wings"].objects.link(c_obj)
        scene.collection.objects.unlink(c_obj)
        c_obj.data.materials.append(mat_pbr)
        set_smooth_and_modifiers(c_obj, subdiv_levels=0)
        return c_obj

    # Inner wing canoes
    create_flap_canoe("Flap_Canoe_In_L", (-1.35, -0.25, 0.04 + Z_OFFSET), root_empty)
    create_flap_canoe("Flap_Canoe_In_R", ( 1.35, -0.25, 0.04 + Z_OFFSET), root_empty)
    # Outer wing canoes (attached to fold pivots)
    for c_idx, lx in enumerate([-0.8, -1.9, -3.1]):
        create_flap_canoe(f"Flap_Canoe_Out_L_{c_idx+1}", (lx, -0.25, 0.02), pivot_fold_left)
    for c_idx, lx in enumerate([0.8, 1.9, 3.1]):
        create_flap_canoe(f"Flap_Canoe_Out_R_{c_idx+1}", (lx, -0.25, 0.02), pivot_fold_right)

    # 6. MODELING: 4X ROKETSAN MAM-L SMART MUNITIONS ON HEAVY PYLONS
    print("Reconstructing 4x Roketsan MAM-L Laser-Guided Smart Bombs...")

    def build_solid_maml(name, x_pos, y_pos, z_pos, parent_obj=root_empty):
        bm_m = bmesh.new()
        # Heavy Weapon Pylon
        pylon_v = [
            bm_m.verts.new((x_pos - 0.022, y_pos + 0.35, z_pos + 0.12)),
            bm_m.verts.new((x_pos + 0.022, y_pos + 0.35, z_pos + 0.12)),
            bm_m.verts.new((x_pos + 0.022, y_pos - 0.40, z_pos + 0.12)),
            bm_m.verts.new((x_pos - 0.022, y_pos - 0.40, z_pos + 0.12)),
            bm_m.verts.new((x_pos - 0.016, y_pos + 0.28, z_pos)),
            bm_m.verts.new((x_pos + 0.016, y_pos + 0.28, z_pos)),
            bm_m.verts.new((x_pos + 0.016, y_pos - 0.35, z_pos)),
            bm_m.verts.new((x_pos - 0.016, y_pos - 0.35, z_pos)),
        ]
        bm_m.faces.new([pylon_v[0], pylon_v[1], pylon_v[5], pylon_v[4]])
        bm_m.faces.new([pylon_v[1], pylon_v[2], pylon_v[6], pylon_v[5]])
        bm_m.faces.new([pylon_v[2], pylon_v[3], pylon_v[7], pylon_v[6]])
        bm_m.faces.new([pylon_v[3], pylon_v[0], pylon_v[4], pylon_v[7]])
        for f in bm_m.faces:
            f.material_index = 0

        # MAM-L Missile Body (length 0.98m, diam 0.16m)
        r_maml = 0.080
        z_c = z_pos - 0.12
        maml_rings = []
        m_stations = [
            (y_pos + 0.48, 0.010, 2), # Seeker Tip (Sapphire)
            (y_pos + 0.45, 0.052, 2), # Seeker Dome
            (y_pos + 0.38, r_maml, 1),# Yellow Hazard Band Front
            (y_pos + 0.30, r_maml, 1),# Yellow Hazard Band Rear
            (y_pos + 0.05, r_maml, 0),# Mid Body Forward
            (y_pos - 0.25, r_maml, 0),# Mid Body Aft
            (y_pos - 0.45, 0.072, 0),# Boat Tail
            (y_pos - 0.50, 0.058, 0),# Exhaust Nozzle
        ]

        n_seg = 16
        for my, mr, mat_id in m_stations:
            ring = []
            for j in range(n_seg):
                ang = j * (2.0 * math.pi / n_seg)
                v = bm_m.verts.new((x_pos + mr * math.sin(ang), my, z_c + mr * math.cos(ang)))
                ring.append(v)
            maml_rings.append((ring, mat_id))

        for idx in range(len(maml_rings) - 1):
            r1, _ = maml_rings[idx]
            r2, mat_id = maml_rings[idx + 1]
            for j in range(n_seg):
                f = bm_m.faces.new([r1[j], r1[(j+1)%n_seg], r2[(j+1)%n_seg], r2[j]])
                f.material_index = mat_id

        # 4 Cruciform Tail Fins
        for f_idx in range(4):
            ang = f_idx * (math.pi / 2.0) + math.pi / 4.0
            dx = math.sin(ang)
            dz = math.cos(ang)
            v_fin = [
                bm_m.verts.new((x_pos + r_maml * dx, y_pos - 0.28, z_c + r_maml * dz)),
                bm_m.verts.new((x_pos + 0.24 * dx, y_pos - 0.42, z_c + 0.24 * dz)),
                bm_m.verts.new((x_pos + 0.24 * dx, y_pos - 0.52, z_c + 0.24 * dz)),
                bm_m.verts.new((x_pos + 0.058 * dx, y_pos - 0.50, z_c + 0.058 * dz)),
            ]
            f = bm_m.faces.new(v_fin)
            f.material_index = 0

        # UV Unwrapping for MAM-L -> Region 4 (U: [0.52, 0.98], V: [0.35, 0.48])
        uv_lay = bm_m.loops.layers.uv.new("UVMap")
        for face in bm_m.faces:
            for loop in face.loops:
                vco = loop.vert.co
                t_len = (vco.y - (y_pos - 0.50)) / 0.98
                u_coord = 0.55 + max(0.0, min(1.0, t_len)) * 0.40
                ang = math.atan2(vco.x - x_pos, vco.z - z_c)
                v_coord = 0.38 + ((ang / (2.0 * math.pi) + 0.5) % 1.0) * 0.08
                loop[uv_lay].uv = (u_coord, v_coord)

        mesh_m = bpy.data.meshes.new(f"{name}_Mesh")
        bm_m.to_mesh(mesh_m)
        bm_m.free()

        obj_m = bpy.data.objects.new(name, mesh_m)
        obj_m.parent = parent_obj
        cols["Sensors_Payload"].objects.link(obj_m)
        obj_m.data.materials.append(mat_maml_body) # Slot 0: Tactical Gray Body
        obj_m.data.materials.append(mat_yellow)    # Slot 1: Hazard Yellow Ring
        obj_m.data.materials.append(mat_sapphire)  # Slot 2: Seeker Lens
        set_smooth_and_modifiers(obj_m, subdiv_levels=0)
        return obj_m

    # 4 Hardpoints: Inner (X = ±1.70m, stationary), Outer (X = ±2.75m, folding with outer wings)
    build_solid_maml("Guided_Bomb_Left_Inner",  -1.70, 0.15, 0.02 + Z_OFFSET, parent_obj=root_empty)
    build_solid_maml("Guided_Bomb_Right_Inner",  1.70, 0.15, 0.02 + Z_OFFSET, parent_obj=root_empty)
    # Outer bombs: local coordinates relative to Pivot_WingFold at (±2.30, 0.35, 0.12 + Z_OFFSET)
    build_solid_maml("Guided_Bomb_Left_Outer",  -0.45, -0.20, -0.07, parent_obj=pivot_fold_left)
    build_solid_maml("Guided_Bomb_Right_Outer",  0.45, -0.20, -0.07, parent_obj=pivot_fold_right)


    # 7. MODELING: TWIN TAIL BOOMS & INVERTED-V TAIL (INTEGRATED MARKINGS UVS)
    print("Reconstructing Twin Tail Booms, Warning Bands & Inverted-V Stabilizer...")
    boom_sections = [
        # (Y, (Radius_X, Radius_Z, Center_Z))
        (-0.45, (0.085, 0.085, 0.08)),  # Wing root merge
        (-1.20, (0.075, 0.075, 0.08)),  # Forward boom
        (-1.95, (0.070, 0.070, 0.08)),  # Propeller plane (DANGER PROPELLER BAND)
        (-2.70, (0.065, 0.065, 0.08)),  # Mid boom
        (-3.40, (0.060, 0.060, 0.08)),  # Aft boom taper
        (-3.70, (0.055, 0.055, 0.08)),  # Fin root junction
    ]

    for bsign, bside in [(-1, "Left"), (1, "Right")]:
        bx = bsign * 1.70
        bm_b = bmesh.new()
        prev_ring = []
        n_seg = 24

        for by, (brx, brz, bcz) in boom_sections:
            ring = []
            for j in range(n_seg):
                ang = j * (2.0 * math.pi / n_seg)
                vx = bx + brx * math.sin(ang)
                vy = by
                vz = bcz + brz * math.cos(ang) + Z_OFFSET
                v = bm_b.verts.new((vx, vy, vz))
                ring.append(v)

            if prev_ring:
                for j in range(n_seg):
                    bm_b.faces.new([prev_ring[j], prev_ring[(j + 1) % n_seg], ring[(j + 1) % n_seg], ring[j]])
            prev_ring = ring

        # Integrated UV Mapping for Tail Booms -> Zone 3D (U: [0.27, 0.48], V: [0.01, 0.24])
        uv_lay = bm_b.loops.layers.uv.new("UVMap")
        for face in bm_b.faces:
            for loop in face.loops:
                vco = loop.vert.co
                # Lengthwise: Aft (Y=-3.70m) to Forward (Y=-0.45m)
                # Propeller plane (Y=-1.95m) maps to U=0.383 (X_PIL=1569 -> Propeller Red Band)
                t_boom = max(0.0, min(1.0, (vco.y - (-3.70)) / 3.25))
                u_coord = 0.27 + t_boom * 0.21

                # Circumference: Center outer flank at V = 0.125 (Y_PIL = 3584)
                # Invert angle so top of boom maps to top of text in PIL!
                outer_dx = (vco.x - bx) if (bsign > 0) else -(vco.x - bx)
                outer_dz = vco.z - (0.08 + Z_OFFSET)
                ang_outer = math.atan2(outer_dx, outer_dz)
                t_circ = (0.50 - (ang_outer - math.pi / 2.0) / (2.0 * math.pi)) % 1.0
                v_coord = 0.01 + t_circ * 0.23

                loop[uv_lay].uv = (u_coord, v_coord)

        mesh_b = bpy.data.meshes.new(f"Tail_Boom_{bside}_Mesh")
        bm_b.to_mesh(mesh_b)
        bm_b.free()

        obj_b = bpy.data.objects.new(f"Tail_Boom_{bside}", mesh_b)
        obj_b.parent = root_empty
        cols["Tail"].objects.link(obj_b)
        obj_b.data.materials.append(mat_pbr)
        set_smooth_and_modifiers(obj_b, subdiv_levels=1)

    # 7.1 Vertical Fins with Integrated Turkish Flags, PT-2 & Stencils
    def build_vertical_fin(name, bx, is_left=True):
        bm_f = bmesh.new()
        z_bot = 0.08 + Z_OFFSET
        z_top = 1.35 + Z_OFFSET
        n_z = 8
        pts_fin_airfoil = create_airfoil_cross_section(chord=1.0, thickness=0.10, num_points=12)
        n_fpts = len(pts_fin_airfoil)
        prev_ring = []

        for zi in range(n_z + 1):
            tz = zi / float(n_z)
            curr_z = z_bot + tz * (z_top - z_bot)
            chord = 0.65 - tz * 0.22  # Tapers upward
            sweep_back = -tz * 0.35   # Sweeps rearward
            lead_y = -3.65 + sweep_back

            ring = []
            for cx, cy in pts_fin_airfoil:
                vx = bx + cy * chord
                vy = lead_y - cx * chord
                vz = curr_z
                ring.append(bm_f.verts.new((vx, vy, vz)))

            if prev_ring:
                for j in range(n_fpts):
                    bm_f.faces.new([prev_ring[j], prev_ring[(j+1)%n_fpts], ring[(j+1)%n_fpts], ring[j]])
            prev_ring = ring

        bm_f.normal_update()
        bm_f.verts.ensure_lookup_table()
        bm_f.faces.ensure_lookup_table()

        # Deterministic UV Unwrapping for Fin Outer Face & Clean Inner Face
        uv_lay = bm_f.loops.layers.uv.new("UVMap")
        for face in bm_f.faces:
            # Outer face normal points away from aircraft: Port outer points in -X (normal.x < 0), Starboard outer points in +X (normal.x > 0)
            is_outer = (face.normal.x < 0.0) if is_left else (face.normal.x > 0.0)
            for loop in face.loops:
                vco = loop.vert.co
                tz = max(0.0, min(1.0, (vco.z - z_bot) / (z_top - z_bot)))

                # Exact local chord and leading edge accounting for taper & sweep at height tz:
                curr_chord = max(0.1, 0.65 - tz * 0.22)
                lead_y = -3.65 - tz * 0.35
                # Local chord fraction: 0.0 at leading edge, 1.0 at trailing edge:
                tc = max(0.0, min(1.0, (lead_y - vco.y) / curr_chord))

                if is_outer:
                    # Vertical height: Base at V=0.26, Top at V=0.49
                    v_coord = 0.26 + tz * 0.23

                    if is_left:
                        # Port Fin (Zone 3B: U in [0.03, 0.22]): Leading edge at low U, Trailing edge at high U
                        u_coord = 0.03 + tc * 0.19
                    else:
                        # Starboard Fin (Zone 3A: U in [0.28, 0.47]): Trailing edge at low U, Leading edge at high U
                        u_coord = 0.28 + (1.0 - tc) * 0.19
                else:
                    # INNER FACE: Map to Zone 3C (Clean tactical carbon, ZERO stencils, ZERO bleed-through!)
                    u_coord = 0.04 + tc * 0.15
                    v_coord = 0.04 + tz * 0.15

                loop[uv_lay].uv = (u_coord, v_coord)

        mesh_f = bpy.data.meshes.new(f"{name}_Mesh")
        bm_f.to_mesh(mesh_f)
        bm_f.free()
        obj_f = bpy.data.objects.new(name, mesh_f)
        obj_f.parent = root_empty
        cols["Tail"].objects.link(obj_f)
        obj_f.data.materials.append(mat_pbr)
        set_smooth_and_modifiers(obj_f, subdiv_levels=1)
        return obj_f

    build_vertical_fin("Fin_Left", -1.70, is_left=True)
    build_vertical_fin("Fin_Right", 1.70, is_left=False)

    # 7.2 Inverted-V Horizontal Stabilizer Bridging the Twin Booms
    bm_vstab = bmesh.new()
    n_vsta = 14
    pts_stab = create_airfoil_cross_section(chord=0.48, thickness=0.11, num_points=10)
    n_spts = len(pts_stab)
    prev_sring = []

    for i in range(n_vsta + 1):
        t = i / float(n_vsta)
        sx = -1.70 + t * 3.40
        # Inverted-V apex crests at center (X=0)
        apex_rise = math.cos((t - 0.5) * math.pi) * 0.28
        sz = 1.35 + Z_OFFSET - apex_rise
        sy = -3.95 - (apex_rise * 0.4)

        ring = []
        for cx, cz in pts_stab:
            vx = sx
            vy = sy - cx
            vz = sz + cz
            ring.append(bm_vstab.verts.new((vx, vy, vz)))

        if prev_sring:
            for j in range(n_spts):
                bm_vstab.faces.new([prev_sring[j], prev_sring[(j+1)%n_spts], ring[(j+1)%n_spts], ring[j]])
        prev_sring = ring

    uv_lay = bm_vstab.loops.layers.uv.new("UVMap")
    for face in bm_vstab.faces:
        for loop in face.loops:
            vco = loop.vert.co
            loop[uv_lay].uv = (0.25 + (vco.x / 3.40) * 0.20, 0.15)

    mesh_vstab = bpy.data.meshes.new("Inverted_V_Stabilizer_Mesh")
    bm_vstab.to_mesh(mesh_vstab)
    bm_vstab.free()
    obj_vstab = bpy.data.objects.new("Inverted_V_Stabilizer", mesh_vstab)
    obj_vstab.parent = root_empty
    cols["Tail"].objects.link(obj_vstab)
    obj_vstab.data.materials.append(mat_pbr)
    set_smooth_and_modifiers(obj_vstab, subdiv_levels=1)

    # 8. MODELING: 3-BLADE PUSHER PROPELLER & CONICAL SPINNER
    print("Reconstructing 3-Blade Pusher Propeller with Conical Spinner...")
    pivot_prop = bpy.data.objects.new("Pivot_Propeller", None)
    pivot_prop.location = (0, -1.95, 0.28 + Z_OFFSET)
    pivot_prop.empty_display_type = 'CIRCLE'
    pivot_prop.empty_display_size = 0.45
    pivot_prop.parent = root_empty
    cols["Propulsion"].objects.link(pivot_prop)

    # Conical Spinner (local relative to pivot_prop)
    bpy.ops.mesh.primitive_cone_add(radius1=0.18, radius2=0.015, depth=0.38, vertices=24, location=(0, -0.19, 0), rotation=(math.radians(-90), 0, 0))
    obj_spinner = bpy.context.active_object
    obj_spinner.name = "Propeller_Spinner"
    obj_spinner.parent = pivot_prop
    cols["Propulsion"].objects.link(obj_spinner)
    scene.collection.objects.unlink(obj_spinner)
    obj_spinner.data.materials.append(mat_pbr)
    set_smooth_and_modifiers(obj_spinner, subdiv_levels=1)

    # 3 Aerodynamic Propeller Blades (120 deg apart)
    for b_idx in range(3):
        b_angle = b_idx * (2.0 * math.pi / 3.0)
        bm_blade = bmesh.new()
        b_radii = [0.18, 0.35, 0.55, 0.72, 0.88]
        chords_b = [0.11, 0.13, 0.12, 0.095, 0.065]
        twists_b = [math.radians(35), math.radians(28), math.radians(20), math.radians(14), math.radians(8)]
        pts_b_airfoil = create_airfoil_cross_section(chord=1.0, thickness=0.10, num_points=8)
        prev_ring = []

        for br, bc, btw in zip(b_radii, chords_b, twists_b):
            ring = []
            for cx, cz in pts_b_airfoil:
                lx = -cx * bc * math.cos(btw)
                ly = cx * bc * math.sin(btw)
                lz = br + cz * bc
                # Rotate around propeller axis
                gx = lx * math.cos(b_angle) - lz * math.sin(b_angle)
                gy = ly
                gz = lx * math.sin(b_angle) + lz * math.cos(b_angle)
                ring.append(bm_blade.verts.new((gx, gy, gz)))

            if prev_ring:
                for j in range(len(pts_b_airfoil)):
                    f = bm_blade.faces.new([prev_ring[j], prev_ring[(j+1)%len(pts_b_airfoil)], ring[(j+1)%len(pts_b_airfoil)], ring[j]])
                    f.material_index = 1 if br > 0.80 else 0
            prev_ring = ring

        mesh_blade = bpy.data.meshes.new(f"Propeller_Blade_{b_idx+1}_Mesh")
        bm_blade.to_mesh(mesh_blade)
        bm_blade.free()
        obj_blade = bpy.data.objects.new(f"Propeller_Blade_{b_idx+1}", mesh_blade)
        obj_blade.parent = pivot_prop
        cols["Propulsion"].objects.link(obj_blade)
        obj_blade.data.materials.append(mat_propeller) # Carbon body
        obj_blade.data.materials.append(mat_yellow)    # Yellow hazard tip
        set_smooth_and_modifiers(obj_blade, subdiv_levels=0)

    # 9. MODELING: PRODUCTION TRICYCLE LANDING GEAR (GROUND-ALIGNED AT Z=0.000)
    print("Reconstructing Landing Gear Assemblies with Ground Alignment at Z = 0.000m...")

    def build_solid_10spoke_wheel(name, local_loc, tire_radius=0.18, tire_width=0.088, rim_radius=0.105, parent_obj=None):
        bm_w = bmesh.new()
        n_rad = 20
        n_cross = 10
        r_core = (tire_radius + rim_radius) * 0.5
        r_thick = (tire_radius - rim_radius) * 0.5

        tire_rings = []
        for i in range(n_rad):
            ang = i * (2.0 * math.pi / n_rad)
            cross_verts = []
            for j in range(n_cross):
                c_ang = j * (2.0 * math.pi / n_cross)
                wx = math.sin(c_ang) * (tire_width * 0.5)
                rad_curr = r_core + math.cos(c_ang) * r_thick
                wy = math.cos(ang) * rad_curr
                wz = math.sin(ang) * rad_curr
                cross_verts.append(bm_w.verts.new((wx, wy, wz)))
            tire_rings.append(cross_verts)

        for i in range(n_rad):
            r1 = tire_rings[i]
            r2 = tire_rings[(i + 1) % n_rad]
            for j in range(n_cross):
                f = bm_w.faces.new([r1[j], r1[(j+1)%n_cross], r2[(j+1)%n_cross], r2[j]])
                f.material_index = 0

        # Hub and Spokes
        n_spokes = 10
        hub_r = rim_radius * 0.35
        hub_w = tire_width * 0.40
        for side_sign in [-1, 1]:
            hx = side_sign * hub_w
            hub_v = [bm_w.verts.new((hx, math.cos(i * 2*math.pi/(2*n_spokes)) * hub_r, math.sin(i * 2*math.pi/(2*n_spokes)) * hub_r)) for i in range(2*n_spokes)]
            rim_v = [bm_w.verts.new((side_sign * tire_width * 0.38, math.cos(i * 2*math.pi/(2*n_spokes)) * rim_radius, math.sin(i * 2*math.pi/(2*n_spokes)) * rim_radius)) for i in range(2*n_spokes)]
            c_hub = bm_w.verts.new((side_sign * (hub_w + 0.01), 0, 0))
            for i in range(2*n_spokes):
                f = bm_w.faces.new([c_hub, hub_v[i], hub_v[(i+1)%(2*n_spokes)]])
                f.material_index = 1
            for s in range(n_spokes):
                i1 = s * 2
                i2 = i1 + 1
                f = bm_w.faces.new([hub_v[i1], rim_v[i1], rim_v[i2], hub_v[i2]])
                f.material_index = 1

        mesh_w = bpy.data.meshes.new(f"{name}_Mesh")
        bm_w.to_mesh(mesh_w)
        bm_w.free()
        obj_w = bpy.data.objects.new(name, mesh_w)
        obj_w.location = local_loc
        if parent_obj:
            obj_w.parent = parent_obj
        cols["Landing_Gear"].objects.link(obj_w)
        obj_w.data.materials.append(mat_rubber)
        obj_w.data.materials.append(mat_alloy)
        set_smooth_and_modifiers(obj_w, subdiv_levels=0)
        return obj_w

    # 9.1 Nose Gear: Resting at Z = 0.000m
    pivot_nose_gear = bpy.data.objects.new("Pivot_Nose_Gear", None)
    pivot_nose_gear.location = (0, 2.65, -0.15 + Z_OFFSET)
    pivot_nose_gear.empty_display_type = 'CIRCLE'
    pivot_nose_gear.empty_display_size = 0.30
    pivot_nose_gear.parent = root_empty
    cols["Landing_Gear"].objects.link(pivot_nose_gear)

    bm_ngear = bmesh.new()
    res_n1 = bmesh.ops.create_cone(bm_ngear, cap_ends=True, segments=16, radius1=0.035, radius2=0.035, depth=0.45)
    for v in res_n1['verts']:
        v.co.z -= 0.225
    for f in {f for v in res_n1['verts'] for f in v.link_faces}:
        f.material_index = 0

    res_n2 = bmesh.ops.create_cone(bm_ngear, cap_ends=True, segments=16, radius1=0.025, radius2=0.025, depth=0.32)
    for v in res_n2['verts']:
        v.co.z -= 0.52
    for f in {f for v in res_n2['verts'] for f in v.link_faces}:
        f.material_index = 1

    mesh_ngear = bpy.data.meshes.new("Nose_Gear_Strut_Mesh")
    bm_ngear.to_mesh(mesh_ngear)
    bm_ngear.free()
    obj_nstrut = bpy.data.objects.new("Nose_Gear_Strut", mesh_ngear)
    obj_nstrut.parent = pivot_nose_gear
    cols["Landing_Gear"].objects.link(obj_nstrut)
    obj_nstrut.data.materials.append(mat_alloy)
    obj_nstrut.data.materials.append(mat_chrome)
    set_smooth_and_modifiers(obj_nstrut, subdiv_levels=0)

    # Wheel bottom touches Z = 0.000 (-0.15 + 1.020 - 0.70 - 0.17 = 0.000m!)
    build_solid_10spoke_wheel("Nose_Wheel", (0, -0.04, -0.70), tire_radius=0.17, tire_width=0.085, rim_radius=0.105, parent_obj=obj_nstrut)

    # 9.2 Main Gear: Resting at Z = 0.000m
    pivots_main = {}
    for m_sign, m_side in [(-1, "Left"), (1, "Right")]:
        pivot_main = bpy.data.objects.new(f"Pivot_Main_Gear_{m_side}", None)
        pivot_main.location = (m_sign * 1.62, -0.45, 0.02 + Z_OFFSET)
        pivot_main.empty_display_type = 'CIRCLE'
        pivot_main.empty_display_size = 0.35
        pivot_main.parent = root_empty
        cols["Landing_Gear"].objects.link(pivot_main)
        pivots_main[m_side] = pivot_main

        bm_mgear = bmesh.new()
        res_m1 = bmesh.ops.create_cone(bm_mgear, cap_ends=True, segments=16, radius1=0.045, radius2=0.045, depth=0.50)
        for v in res_m1['verts']:
            v.co.z -= 0.25
        for f in {f for v in res_m1['verts'] for f in v.link_faces}:
            f.material_index = 0

        res_m2 = bmesh.ops.create_cone(bm_mgear, cap_ends=True, segments=16, radius1=0.032, radius2=0.032, depth=0.35)
        for v in res_m2['verts']:
            v.co.z -= 0.58
        for f in {f for v in res_m2['verts'] for f in v.link_faces}:
            f.material_index = 1

        mesh_mgear = bpy.data.meshes.new(f"Main_Gear_Strut_{m_side}_Mesh")
        bm_mgear.to_mesh(mesh_mgear)
        bm_mgear.free()
        obj_mstrut = bpy.data.objects.new(f"Main_Gear_Strut_{m_side}", mesh_mgear)
        obj_mstrut.parent = pivot_main
        cols["Landing_Gear"].objects.link(obj_mstrut)
        obj_mstrut.data.materials.append(mat_alloy)
        obj_mstrut.data.materials.append(mat_chrome)
        set_smooth_and_modifiers(obj_mstrut, subdiv_levels=0)

        # Main wheel bottom touches Z = 0.000 (0.02 + 1.020 - 0.83 - 0.21 = 0.000m!)
        build_solid_10spoke_wheel(f"Main_Wheel_{m_side}", (m_sign * 0.08, -0.06, -0.83), tire_radius=0.21, tire_width=0.115, rim_radius=0.13, parent_obj=obj_mstrut)

    # 10. MODELING: ASELSAN CATS EO/IR MULTI-SPECTRAL GIMBAL TURRET
    print("Reconstructing Aselsan CATS EO/IR Gimbal Turret with Sapphire Windows...")
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.08, vertices=24, location=(0, 2.05, -0.38 + Z_OFFSET))
    obj_eobase = bpy.context.active_object
    obj_eobase.name = "EO_IR_Mounting_Base"
    obj_eobase.parent = root_empty
    cols["Sensors_Payload"].objects.link(obj_eobase)
    scene.collection.objects.unlink(obj_eobase)
    obj_eobase.data.materials.append(mat_cats)

    # Spherical Turret Gimbal Ball
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.20, segments=24, ring_count=16, location=(0, 2.05, -0.56 + Z_OFFSET))
    obj_turret = bpy.context.active_object
    obj_turret.name = "Sensor_Turret_CATS"
    obj_turret.parent = root_empty
    cols["Sensors_Payload"].objects.link(obj_turret)
    scene.collection.objects.unlink(obj_turret)
    obj_turret.data.materials.append(mat_cats)
    set_smooth_and_modifiers(obj_turret, subdiv_levels=1)

    # Sapphire & FLIR Germanium Optical Windows (local relative to obj_turret)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.075, depth=0.04, vertices=20, location=(0, 0.17, 0), rotation=(math.radians(90), 0, 0))
    obj_opt1 = bpy.context.active_object
    obj_opt1.name = "Turret_Optics_Sapphire"
    obj_opt1.parent = obj_turret
    cols["Sensors_Payload"].objects.link(obj_opt1)
    scene.collection.objects.unlink(obj_opt1)
    obj_opt1.data.materials.append(mat_sapphire)

    # 11. INTERNAL SYSTEMS: MOUNT TEI-PD170 TURBODIESEL (Section 11.6)
    print("Mounting TEI-PD170 Turbodiesel LOD1 into Internal_Systems...")
    engine_lod1_path = ROOT / "Models" / "engines" / "tei_pd170_lod1.blend"
    if engine_lod1_path.exists():
        mount_empty = bpy.data.objects.new("Engine_Mount_1", None)
        mount_empty.empty_display_type = 'ARROWS'
        mount_empty.empty_display_size = 0.4
        mount_empty.location = (0.0, -1.95, 0.28 + Z_OFFSET)
        mount_empty.rotation_euler = (0.0, 0.0, math.radians(180.0))
        mount_empty.parent = root_empty
        cols["Internal_Systems"].objects.link(mount_empty)

        try:
            with bpy.data.libraries.load(str(engine_lod1_path), link=False) as (data_from, data_to):
                data_to.objects = data_from.objects

            for o in data_to.objects:
                if o is not None:
                    o.name = f"E1__{o.name}"
                    o["twin_mount_id"] = "E1"
                    o.parent = mount_empty
                    for col in list(o.users_collection):
                        col.objects.unlink(o)
                    cols["Internal_Systems"].objects.link(o)
            print("  TEI-PD170 Turbodiesel LOD1 successfully mounted to Engine_Mount_1!")
        except Exception as e:
            print(f"  Note on engine mount: {e}")

    # Hide internal collection by default for ultra-fast viewport response
    cols["Internal_Systems"].hide_viewport = True

    # 12. ANIMATION TIMELINE & RIGGED KINEMATICS
    print("Setting up Kinematic Constraints (Wing Fold & Gear Retraction)...")

    # 12.1 Interactive 3D Viewport Controllers (Empties)
    ctrl_fold = bpy.data.objects.new("CTRL_Wing_Fold", None)
    ctrl_fold.empty_display_type = 'SINGLE_ARROW'
    ctrl_fold.empty_display_size = 0.80
    ctrl_fold.location = (-0.50, 0.35, 3.00)
    ctrl_fold.parent = root_empty
    cols["Wings"].objects.link(ctrl_fold)

    # Limit location of ctrl_fold so user can slide it Z: 3.0 (Flight) to 4.0 (Folded 115°)
    lim_fold = ctrl_fold.constraints.new('LIMIT_LOCATION')
    lim_fold.use_min_z = True
    lim_fold.min_z = 3.0
    lim_fold.use_max_z = True
    lim_fold.max_z = 4.0
    lim_fold.use_min_x = True
    lim_fold.min_x = -0.50
    lim_fold.use_max_x = True
    lim_fold.max_x = -0.50
    lim_fold.use_min_y = True
    lim_fold.min_y = 0.35
    lim_fold.use_max_y = True
    lim_fold.max_y = 0.35
    lim_fold.owner_space = 'LOCAL'

    # Rig Pivot_WingFold_Left with Transformation Constraint
    c_wfl = pivot_fold_left.constraints.new('TRANSFORM')
    c_wfl.target = ctrl_fold
    c_wfl.target_space = 'LOCAL'
    c_wfl.owner_space = 'LOCAL'
    c_wfl.map_from = 'LOCATION'
    c_wfl.from_min_z = 3.0
    c_wfl.from_max_z = 4.0
    c_wfl.map_to = 'ROTATION'
    c_wfl.map_to_y_from = 'Z'
    c_wfl.to_min_y_rot = 0.0
    c_wfl.to_max_y_rot = math.radians(115.0)
    c_wfl.use_motion_extrapolate = True

    # Rig Pivot_WingFold_Right with Transformation Constraint
    c_wfr = pivot_fold_right.constraints.new('TRANSFORM')
    c_wfr.target = ctrl_fold
    c_wfr.target_space = 'LOCAL'
    c_wfr.owner_space = 'LOCAL'
    c_wfr.map_from = 'LOCATION'
    c_wfr.from_min_z = 3.0
    c_wfr.from_max_z = 4.0
    c_wfr.map_to = 'ROTATION'
    c_wfr.map_to_y_from = 'Z'
    c_wfr.to_min_y_rot = 0.0
    c_wfr.to_max_y_rot = math.radians(-115.0)
    c_wfr.use_motion_extrapolate = True

    # 12.2 Interactive Landing Gear Retraction Controller
    ctrl_gear = bpy.data.objects.new("CTRL_Gear_Retract", None)
    ctrl_gear.empty_display_type = 'SINGLE_ARROW'
    ctrl_gear.empty_display_size = 0.80
    ctrl_gear.location = (0.50, 0.35, 3.00)
    ctrl_gear.parent = root_empty
    cols["Landing_Gear"].objects.link(ctrl_gear)

    lim_gear = ctrl_gear.constraints.new('LIMIT_LOCATION')
    lim_gear.use_min_z = True
    lim_gear.min_z = 3.0
    lim_gear.use_max_z = True
    lim_gear.max_z = 4.0
    lim_gear.use_min_x = True
    lim_gear.min_x = 0.50
    lim_gear.use_max_x = True
    lim_gear.max_x = 0.50
    lim_gear.use_min_y = True
    lim_gear.min_y = 0.35
    lim_gear.use_max_y = True
    lim_gear.max_y = 0.35
    lim_gear.owner_space = 'LOCAL'

    # Nose Gear Constraint: Z (3.0 -> 4.0) -> X rot (0.0 -> 85.0 deg)
    c_ng = pivot_nose_gear.constraints.new('TRANSFORM')
    c_ng.target = ctrl_gear
    c_ng.target_space = 'LOCAL'
    c_ng.owner_space = 'LOCAL'
    c_ng.map_from = 'LOCATION'
    c_ng.from_min_z = 3.0
    c_ng.from_max_z = 4.0
    c_ng.map_to = 'ROTATION'
    c_ng.map_to_x_from = 'Z'
    c_ng.to_min_x_rot = 0.0
    c_ng.to_max_x_rot = math.radians(85.0)
    c_ng.use_motion_extrapolate = True

    # Main Gear Left: Z (3.0 -> 4.0) -> Y rot (0.0 -> 85.0 deg)
    pivot_main_left = pivots_main["Left"]
    c_mgl = pivot_main_left.constraints.new('TRANSFORM')
    c_mgl.target = ctrl_gear
    c_mgl.target_space = 'LOCAL'
    c_mgl.owner_space = 'LOCAL'
    c_mgl.map_from = 'LOCATION'
    c_mgl.from_min_z = 3.0
    c_mgl.from_max_z = 4.0
    c_mgl.map_to = 'ROTATION'
    c_mgl.map_to_y_from = 'Z'
    c_mgl.to_min_y_rot = 0.0
    c_mgl.to_max_y_rot = math.radians(85.0)
    c_mgl.use_motion_extrapolate = True

    # Main Gear Right: Z (3.0 -> 4.0) -> Y rot (0.0 -> -85.0 deg)
    pivot_main_right = pivots_main["Right"]
    c_mgr = pivot_main_right.constraints.new('TRANSFORM')
    c_mgr.target = ctrl_gear
    c_mgr.target_space = 'LOCAL'
    c_mgr.owner_space = 'LOCAL'
    c_mgr.map_from = 'LOCATION'
    c_mgr.from_min_z = 3.0
    c_mgr.from_max_z = 4.0
    c_mgr.map_to = 'ROTATION'
    c_mgr.map_to_y_from = 'Z'
    c_mgr.to_min_y_rot = 0.0
    c_mgr.to_max_y_rot = math.radians(-85.0)
    c_mgr.use_motion_extrapolate = True

    # 12.3 Animation Timeline Setup on Controllers (Keyframes)
    # Frames 1-40: Flight ready (wings flat Z=3, gear down Z=3)
    # Frames 40-80: Gear retracts (ctrl_gear Z: 3.0 -> 4.0)
    # Frames 80-120: Gear extends (ctrl_gear Z: 4.0 -> 3.0)
    # Frames 120-170: Wings fold 115° for carrier deck (ctrl_fold Z: 3.0 -> 4.0)
    # Frames 170-210: Wings held in folded carrier stowage
    # Frames 210-250: Wings unfold back to flight ready (ctrl_fold Z: 4.0 -> 3.0)
    # Drivers on mechanism controllers (Section 13.3 - No keyframes)
    alb.add_driver(ctrl_fold, "location", 2, "3.0 + val * 1.0", scene, '["wing_fold"]')
    alb.add_driver(ctrl_gear, "location", 2, "3.0 + val * 1.0", scene, '["gear_retract"]')
    alb.add_driver(pivot_prop, "rotation_euler", 1, "val * 6.283185307", scene, '["twin_time_s"]')

    # 13. CAMERAS & CINEMATIC LIGHTING SUITE
    print("Setting up Master Cameras matching image.png & fdda7fefdc.jpg...")

    def create_tracked_camera(name, loc, target_loc, lens=50.0):
        tgt = bpy.data.objects.new(f"Target_{name}", None)
        tgt.location = target_loc
        cols["Cameras"].objects.link(tgt)
        cam_data = bpy.data.cameras.new(name)
        cam_data.lens = lens
        cam_data.clip_start = 0.1
        cam_data.clip_end = 500.0
        cam_obj = bpy.data.objects.new(name, cam_data)
        cam_obj.location = loc
        cols["Cameras"].objects.link(cam_obj)
        tt = cam_obj.constraints.new(type='TRACK_TO')
        tt.target = tgt
        tt.track_axis = 'TRACK_NEGATIVE_Z'
        tt.up_axis = 'UP_Y'
        return cam_obj

    # Cameras per Section 11.5 and Manifest
    cam_hero = create_tracked_camera("Cam_Hero", (-10.4, 9.5, 7.8), (0.1, 0.3, 0.9), lens=41.0)
    cam_orbit = create_tracked_camera("Cam_Beauty_Orbit", (-8.5, -9.5, 2.2), (0.0, 0.2, 0.9), lens=48.0)
    cam_wire = create_tracked_camera("Cam_Wireframe", (6.2, 5.0, 2.5), (0.0, 0.6, 1.05), lens=35.0)
    cam_sensor = create_tracked_camera("Cam_Front_Sensor", (-1.10, 3.25, 0.30), (0.0, 2.05, 0.46), lens=65.0)
    cam_engine = create_tracked_camera("Cam_Engine_Bay", (0.0, -4.2, 1.8), (0.0, -0.65, 1.15), lens=55.0)
    cam_gear = create_tracked_camera("Cam_Undercarriage", (0.0, -1.5, -0.2), (0.0, 0.35, 0.4), lens=45.0)

    scene.camera = cam_hero

    # Studio Lighting Suite matching image.png & fdda7fefdc.jpg
    # 1. Main Overhead Soft Studio Key Area Light
    key_data = bpy.data.lights.new("Studio_Key_Area", 'AREA')
    key_data.shape = 'RECTANGLE'
    key_data.size = 12.0
    key_data.size_y = 8.0
    key_data.energy = 2600.0
    key_data.color = (1.0, 1.0, 1.0)
    key_obj = bpy.data.objects.new("Studio_Key_Area", key_data)
    key_obj.location = (-7.0, 6.0, 9.0)
    cols["Lighting"].objects.link(key_obj)

    # 2. Soft Fill Area Light (Illuminates far wing & tail)
    fill_data = bpy.data.lights.new("Studio_Fill_Area", 'AREA')
    fill_data.shape = 'RECTANGLE'
    fill_data.size = 10.0
    fill_data.size_y = 10.0
    fill_data.energy = 1400.0
    fill_data.color = (0.95, 0.96, 1.0)
    fill_obj = bpy.data.objects.new("Studio_Fill_Area", fill_data)
    fill_obj.location = (8.0, -2.0, 7.5)
    cols["Lighting"].objects.link(fill_obj)

    # 3. Top Rim/Highlight Area Light (Casts sleek edge highlights on wings and fuselage)
    top_data = bpy.data.lights.new("Studio_Top_Area", 'AREA')
    top_data.shape = 'RECTANGLE'
    top_data.size = 14.0
    top_data.size_y = 14.0
    top_data.energy = 1200.0
    top_data.color = (1.0, 1.0, 1.0)
    top_obj = bpy.data.objects.new("Studio_Top_Area", top_data)
    top_obj.location = (0.0, 2.0, 11.0)
    cols["Lighting"].objects.link(top_obj)

    # Studio Shadow Catcher Ground Plane at EXACT Z = 0.000m
    bpy.ops.mesh.primitive_plane_add(size=60.0, location=(0, 0, 0.0))
    ground_plane = bpy.context.active_object
    ground_plane.name = "Studio_Ground_Plane"
    cols["Environment"].objects.link(ground_plane)
    scene.collection.objects.unlink(ground_plane)
    ground_plane.is_shadow_catcher = True

    # Dark Studio Ground Material (#16171a) for EEVEE and Cycles
    mat_floor = create_pbr_material("TB3_Studio_Floor", base_color=(0.024, 0.024, 0.026, 1.0), roughness=0.80)
    ground_plane.data.materials.append(mat_floor)

    # World Environment: Dark Studio Gradient
    if not scene.world:
        scene.world = bpy.data.worlds.new("World_TB3")
    scene.world.use_nodes = True
    wnodes = scene.world.node_tree.nodes
    wlinks = scene.world.node_tree.links
    wnodes.clear()
    out_w = wnodes.new('ShaderNodeOutputWorld')
    bg_w = wnodes.new('ShaderNodeBackground')
    bg_w.inputs['Color'].default_value = (0.024, 0.024, 0.026, 1.0) # #16171a dark studio
    bg_w.inputs['Strength'].default_value = 0.80
    wlinks.new(bg_w.outputs['Background'], out_w.inputs['Surface'])

    # 14. Embed Interactive Controller Script in .blend
    controller_script_text = '''import bpy
import math

def update_wing_fold(self, context):
    ctrl = bpy.data.objects.get("CTRL_Wing_Fold")
    if ctrl:
        ctrl.location.z = 3.0 + self.tb3_wing_fold * 1.0
        if context and context.view_layer:
            context.view_layer.update()

def update_gear_retract(self, context):
    ctrl = bpy.data.objects.get("CTRL_Gear_Retract")
    if ctrl:
        ctrl.location.z = 3.0 + self.tb3_gear_retract * 1.0
        if context and context.view_layer:
            context.view_layer.update()

class TB3_PT_Controller(bpy.types.Panel):
    bl_label = "Bayraktar TB3 Digital Twin"
    bl_idname = "VIEW3D_PT_tb3_controller"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bayraktar TB3"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Display Modes
        col = layout.column(align=True)
        col.label(text="Display Modes:", icon='RESTRICT_VIEW_OFF')
        row = col.row(align=True)
        row.operator("tb3.set_mode", text="Tactical PBR (image.png)").mode = 0
        row.operator("tb3.set_mode", text="Wireframe (fdda)").mode = 1
        col.operator("tb3.set_mode", text="X-Ray Digital Twin").mode = 2

        layout.separator()
        # Preset Cameras
        col = layout.column(align=True)
        col.label(text="Preset Cameras:", icon='CAMERA_DATA')
        row = col.row(align=True)
        row.operator("tb3.set_cam", text="Hero image.png").cam_name = "Cam_Hero_Image_PNG"
        row.operator("tb3.set_cam", text="Wireframe fdda").cam_name = "Cam_Wireframe_FDDA"

        layout.separator()
        # Carrier Wing Fold
        box_w = layout.box()
        box_w.label(text="Carrier Wing Fold (TCG Anadolu):", icon='ORIENTATION_GIMBAL')
        row_w = box_w.row(align=True)
        row_w.operator("tb3.wing_action", text="🛫 Unfold Wings").action = "UNFOLD"
        row_w.operator("tb3.wing_action", text="🚢 Fold 115°").action = "FOLD"
        box_w.prop(scene, "tb3_wing_fold", text="Fold Slider", slider=True)

        layout.separator()
        # Landing Gear System
        box_g = layout.box()
        box_g.label(text="Landing Gear System:", icon='MOD_PHYSICS')
        row_g = box_g.row(align=True)
        row_g.operator("tb3.gear_action", text="🛞 Lower Gear").action = "LOWER"
        row_g.operator("tb3.gear_action", text="✈ Retract Gear").action = "RETRACT"
        box_g.prop(scene, "tb3_gear_retract", text="Gear Retract", slider=True)

class TB3_OT_WingAction(bpy.types.Operator):
    bl_idname = "tb3.wing_action"
    bl_label = "Wing Fold Action"
    action: bpy.props.StringProperty()

    def execute(self, context):
        if self.action == "FOLD":
            context.scene.tb3_wing_fold = 1.0
        elif self.action == "UNFOLD":
            context.scene.tb3_wing_fold = 0.0
        return {'FINISHED'}

class TB3_OT_GearAction(bpy.types.Operator):
    bl_idname = "tb3.gear_action"
    bl_label = "Gear Retraction Action"
    action: bpy.props.StringProperty()

    def execute(self, context):
        if self.action == "RETRACT":
            context.scene.tb3_gear_retract = 1.0
        elif self.action == "LOWER":
            context.scene.tb3_gear_retract = 0.0
        return {'FINISHED'}

class TB3_OT_SetMode(bpy.types.Operator):
    bl_idname = "tb3.set_mode"
    bl_label = "Set Display Mode"
    mode: bpy.props.IntProperty(default=0)

    def execute(self, context):
        mat_pbr = bpy.data.materials.get("TB3_Tactical_PBR")
        mat_wire = bpy.data.materials.get("TB3_Wireframe_Clay")
        col_internal = bpy.data.collections.get("Internal_Systems")

        target_mat = mat_wire if self.mode == 1 else mat_pbr
        target_objs = ["Fuselage", "Wing_Inner_Left", "Wing_Inner_Right", "Wing_Outer_Left", "Wing_Outer_Right",
                       "Tail_Boom_Left", "Tail_Boom_Right", "Fin_Left", "Fin_Right", "Inverted_V_Stabilizer"]
        for oname in target_objs:
            obj = bpy.data.objects.get(oname)
            if obj and obj.data.materials:
                obj.data.materials[0] = target_mat

        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                for mod in obj.modifiers:
                    if mod.type == 'SUBSURF':
                        mod.levels = 0

        if mat_pbr and mat_pbr.node_tree:
            val_xray = mat_pbr.node_tree.nodes.get("XRayFactor")
            if val_xray:
                val_xray.outputs['Value'].default_value = 1.0 if self.mode == 2 else 0.0

        if col_internal:
            col_internal.hide_viewport = (self.mode != 2)

        self.report({'INFO'}, f"TB3 Display Mode set to {self.mode}")
        return {'FINISHED'}

class TB3_OT_SetCam(bpy.types.Operator):
    bl_idname = "tb3.set_cam"
    bl_label = "Set Active Camera"
    cam_name: bpy.props.StringProperty()

    def execute(self, context):
        cam = bpy.data.objects.get(self.cam_name)
        if cam and cam.type == 'CAMERA':
            context.scene.camera = cam
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.spaces.active.region_3d.view_perspective = 'CAMERA'
        return {'FINISHED'}

def register():
    if hasattr(bpy.types.Scene, "tb3_wing_fold"):
        try:
            del bpy.types.Scene.tb3_wing_fold
        except Exception:
            pass
    if hasattr(bpy.types.Scene, "tb3_gear_retract"):
        try:
            del bpy.types.Scene.tb3_gear_retract
        except Exception:
            pass

    bpy.types.Scene.tb3_wing_fold = bpy.props.FloatProperty(
        name="Carrier Wing Fold",
        description="Fold wings 0 to 115 degrees for TCG Anadolu naval carrier elevator stowage",
        min=0.0, max=1.0, default=0.0,
        update=update_wing_fold
    )
    bpy.types.Scene.tb3_gear_retract = bpy.props.FloatProperty(
        name="Gear Retract",
        description="Retract landing gear flush into belly wells",
        min=0.0, max=1.0, default=0.0,
        update=update_gear_retract
    )

    try:
        bpy.utils.register_class(TB3_PT_Controller)
        bpy.utils.register_class(TB3_OT_SetMode)
        bpy.utils.register_class(TB3_OT_SetCam)
        bpy.utils.register_class(TB3_OT_WingAction)
        bpy.utils.register_class(TB3_OT_GearAction)
    except Exception:
        pass

if __name__ == "__main__":
    register()
'''
    manifest_p = ROOT / "manifests" / "platforms" / "bayraktar_tb3.json"
    with open(manifest_p, "r", encoding="utf-8") as f:
        manifest_text = f.read()
    txt_manifest = bpy.data.texts.new("bayraktar_tb3_manifest.json")
    txt_manifest.write(manifest_text)

    ctrl_p = ROOT / "scripts" / "lib" / "anumaan_twin_controller.py"
    with open(ctrl_p, "r", encoding="utf-8") as f:
        ctrl_text = f.read()
    text_block = bpy.data.texts.new("bayraktar_tb3_ui_controller.py")
    text_block.write(ctrl_text)
    text_block.use_module = True

    try:
        exec(ctrl_text, globals())
        register()
    except Exception as e:
        print(f"Controller direct register note: {e}")

    # 15. Set Viewport Shading to MATERIAL PREVIEW (0% Grain, 120 FPS instantaneous)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'
                        space.shading.use_scene_lights = False
                        space.shading.use_scene_world = False

    # 16. Save Master .blend File
    print(f"\nSaving Master Scene to: {output_blend}")
    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"pack_all note: {e}")
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend), compress=True)
    print("Master Blend File Saved Successfully with Zero Grain & Ground Alignment!")
    print("======================================================================")

if __name__ == "__main__":
    run()
