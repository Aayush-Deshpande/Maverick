"""
Decompose Rotax 915 iS 'Main engine' into structured components and add placeholders.
DRDO / iDEX PS-26054 Compliance - Card B-02:
- Separates 'Main engine' by Material and Loose Parts
- Identifies and isolates cylinder_head_1..4 (valve covers and heads)
- Isolates exhaust, turbocharger, wastegate, crankcase, intake plenum, coolant hoses
- Renames CAD-ID parts (5608_@OIS@_5081 etc.) to ECU mounting hardware
- Adds placeholder components with custom properties (component_id, placeholder=True)
- Saves result to assets/blender/engines/rotax_915is/rotax_915is_work.blend (Rule D53)
- Renders verification image to assets/renders/rotax_915is_decomposed.png
"""

import bpy
import mathutils
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

def decompose_915():
    blend_path = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_915is", "rotax_915is.blend")
    work_blend = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_915is", "rotax_915is_work.blend")
    
    print(f"\n[B-02] Opening Rotax 915 iS Master: {blend_path}")
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    
    main_engine = bpy.data.objects.get("Main engine")
    if not main_engine:
        print("[ERROR] 'Main engine' object not found in scene!")
        return False
        
    print(f"  [OK] Found 'Main engine' ({len(main_engine.data.polygons)} polygons, {len(main_engine.material_slots)} materials)")
    
    # 1. Rename CAD-ID objects
    cad_renames = {
        "5608_@OIS@_5081": "ECU_Mount_Bracket",
        "6270_@OIS@_5818": "ECU_Harness_Clip_1",
        "6289_@OIS@_5818": "ECU_Harness_Clip_2",
        "7767_@OIS@_7310": "ECU_Mount_Dowel_1",
        "7786_@OIS@_7310": "ECU_Mount_Dowel_2",
    }
    for old_name, new_name in cad_renames.items():
        obj = bpy.data.objects.get(old_name)
        if obj:
            obj.name = new_name
            obj["component_id"] = "ecu"
            print(f"  [RENAME] {old_name} -> {new_name}")

    # Set component_id on existing discrete objects
    existing_comp_map = {
        "Air baffles": "air_baffles",
        "Ambient sensor": "ambient_sensor",
        "ECU": "ecu",
        "Fusebox": "fusebox",
        "Intercooler": "intercooler",
        "Magnetovalve": "magneto_valve_block",
        "Oil tank": "oil_tank",
        "Overboost valve": "overboost_valve",
        "Tranny": "gearbox",
    }
    for obj_name, comp_id in existing_comp_map.items():
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj["component_id"] = comp_id
            
    # 2. Separate Main engine by Material
    bpy.ops.object.select_all(action='DESELECT')
    main_engine.select_set(True)
    bpy.context.view_layer.objects.active = main_engine
    
    print("  [SEPARATE] Separating 'Main engine' by Material...")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.separate(type='MATERIAL')
    bpy.ops.object.mode_set(mode='OBJECT')
    
    mat_parts = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    print(f"  [OK] Produced {len(mat_parts)} material-separated objects")
    
    # Classify parts by material name and location
    blue_covers = None
    exhaust_part = None
    turbo_parts = []
    intake_parts = []
    crankcase_parts = []
    hoses_parts = []
    fasteners_parts = []
    
    for p in mat_parts:
        mat_name = p.material_slots[0].material.name if p.material_slots else ""
        c = tuple(sum(p.bound_box[j][k] for j in range(8)) / 8.0 for k in range(3))
        
        if "Enamel blue" in mat_name:
            blue_covers = p
        elif "Metal exhaust pipes" in mat_name:
            exhaust_part = p
        elif any(t in mat_name for t in ["shinier.013", "shinier.014", "shinier.015", "#649", "#650", "shinier.017"]):
            if c[0] < -5.0 and c[1] < -2.0 and c[2] < -5.0:
                turbo_parts.append(p)
            else:
                fasteners_parts.append(p)
        elif any(h in mat_name for h in ["Hose black", "black hoes sheath", "Plastic black soft"]):
            hoses_parts.append(p)
        elif any(m in mat_name for m in ["more matte", "Black iron paint", "Metal"]):
            if c[2] > -4.0 and abs(c[1]) < 8.0:
                crankcase_parts.append(p)
            else:
                fasteners_parts.append(p)
        elif any(ip in mat_name for ip in ["Plastic black hard matte.002", "Plastic black hard matte.003", "#4152", "#640"]):
            intake_parts.append(p)
        else:
            fasteners_parts.append(p)
            
    # Process Exhaust
    if exhaust_part:
        exhaust_part.name = "Exhaust_Manifold_System"
        exhaust_part["component_id"] = "exhaust"
        print(f"  [IDENTIFY] Exhaust system: {exhaust_part.name}")
        
    # Process Turbocharger & Wastegate
    if turbo_parts:
        bpy.ops.object.select_all(action='DESELECT')
        for tp in turbo_parts:
            tp.select_set(True)
        bpy.context.view_layer.objects.active = turbo_parts[0]
        bpy.ops.object.join()
        turbo_obj = bpy.context.view_layer.objects.active
        turbo_obj.name = "Turbocharger_Assembly"
        turbo_obj["component_id"] = "turbocharger"
        print(f"  [IDENTIFY] Turbocharger assembly: {turbo_obj.name} ({len(turbo_parts)} parts merged)")
        
    # Process Crankcase
    if crankcase_parts:
        bpy.ops.object.select_all(action='DESELECT')
        for cp in crankcase_parts:
            cp.select_set(True)
        bpy.context.view_layer.objects.active = crankcase_parts[0]
        bpy.ops.object.join()
        cc_obj = bpy.context.view_layer.objects.active
        cc_obj.name = "Crankcase_Engine_Block"
        cc_obj["component_id"] = "crankcase"
        print(f"  [IDENTIFY] Crankcase engine block: {cc_obj.name} ({len(crankcase_parts)} parts merged)")
        
    # Process Intake
    if intake_parts:
        bpy.ops.object.select_all(action='DESELECT')
        for ip in intake_parts:
            ip.select_set(True)
        bpy.context.view_layer.objects.active = intake_parts[0]
        bpy.ops.object.join()
        intake_obj = bpy.context.view_layer.objects.active
        intake_obj.name = "Intake_Manifold_Plenum"
        intake_obj["component_id"] = "intake_manifold"
        print(f"  [IDENTIFY] Intake manifold plenum: {intake_obj.name} ({len(intake_parts)} parts merged)")
        
    # Process Coolant Hoses
    if hoses_parts:
        bpy.ops.object.select_all(action='DESELECT')
        for hp in hoses_parts:
            hp.select_set(True)
        bpy.context.view_layer.objects.active = hoses_parts[0]
        bpy.ops.object.join()
        hoses_obj = bpy.context.view_layer.objects.active
        hoses_obj.name = "Coolant_Hoses_Harness"
        hoses_obj["component_id"] = "coolant_hoses"
        print(f"  [IDENTIFY] Coolant hoses & harness: {hoses_obj.name} ({len(hoses_parts)} parts merged)")
        
    # Process Fasteners/Remaining
    if fasteners_parts:
        bpy.ops.object.select_all(action='DESELECT')
        for fp in fasteners_parts:
            fp.select_set(True)
        bpy.context.view_layer.objects.active = fasteners_parts[0]
        bpy.ops.object.join()
        fast_obj = bpy.context.view_layer.objects.active
        fast_obj.name = "Engine_Fasteners_Brackets"
        fast_obj["component_id"] = "crankcase"
        print(f"  [IDENTIFY] Engine fasteners & brackets: {fast_obj.name} ({len(fasteners_parts)} parts merged)")

    # 3. Process Valve Covers / Cylinder Heads (Enamel Blue)
    head_centers = {}
    if blue_covers:
        print("  [SEPARATE] Separating Valve Covers by Loose Parts...")
        bpy.ops.object.select_all(action='DESELECT')
        blue_covers.select_set(True)
        bpy.context.view_layer.objects.active = blue_covers
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        loose_blue = [o for o in bpy.context.selected_objects if o.type == 'MESH']
        print(f"  [OK] Separated into {len(loose_blue)} loose pieces")
        
        # Identify the 4 main valve covers (dim.x around 0.115 and dim.z around 0.102)
        covers = []
        intake_runners = []
        for o in loose_blue:
            if o.dimensions.x > 0.1 and o.dimensions.z > 0.08:
                c = tuple(sum(o.bound_box[j][k] for j in range(8)) / 8.0 for k in range(3))
                if c[2] < 1.0: # Valve covers sit lower at Z ~ -0.6
                    covers.append(o)
                else: # Intake runners sit higher at Z ~ 3.8
                    intake_runners.append(o)
            else:
                intake_runners.append(o)
                
        # Sort covers into Cylinders 1..4 based on Rotax boxer geometry:
        # Bank Y < 0: Cyl 1 (front, X > -2.0), Cyl 3 (rear, X < -2.0)
        # Bank Y > 0: Cyl 2 (front, X > -3.0), Cyl 4 (rear, X < -3.0)
        for cov in covers:
            c = tuple(sum(cov.bound_box[j][k] for j in range(8)) / 8.0 for k in range(3))
            cyl_num = None
            if c[1] < 0: # Bank 1 & 3
                if c[0] > -2.0:
                    cyl_num = 1
                else:
                    cyl_num = 3
            else: # Bank 2 & 4
                if c[0] > -3.0:
                    cyl_num = 2
                else:
                    cyl_num = 4
                    
            cov.name = f"Cylinder_Head_{cyl_num}"
            cov["component_id"] = f"cylinder_head_{cyl_num}"
            cov["cylinder"] = cyl_num
            head_centers[cyl_num] = c
            print(f"  [IDENTIFY] Cylinder {cyl_num} Head Cover: {cov.name} at center {tuple(round(v, 3) for v in c)}")
            
        # Join intake runners into intake manifold
        if intake_runners:
            bpy.ops.object.select_all(action='DESELECT')
            for ir in intake_runners:
                ir.select_set(True)
            bpy.context.view_layer.objects.active = intake_runners[0]
            bpy.ops.object.join()
            ir_obj = bpy.context.view_layer.objects.active
            ir_obj.name = "Intake_Manifold_Runners"
            ir_obj["component_id"] = "intake_manifold"

    # Default fallback centers if not found
    if 1 not in head_centers: head_centers[1] = (0.0, -0.25, 0.0)
    if 2 not in head_centers: head_centers[2] = (-0.03, 0.25, 0.0)
    if 3 not in head_centers: head_centers[3] = (-0.11, -0.25, 0.0)
    if 4 not in head_centers: head_centers[4] = (-0.14, 0.25, 0.0)

    # 4. Create Material for Placeholder Primitives
    mat_placeholder = bpy.data.materials.get("M_Component_Placeholder")
    if not mat_placeholder:
        mat_placeholder = bpy.data.materials.new(name="M_Component_Placeholder")
        mat_placeholder.use_nodes = True
        bsdf = mat_placeholder.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.22, 0.24, 0.26, 1.0)
            bsdf.inputs['Metallic'].default_value = 0.85
            bsdf.inputs['Roughness'].default_value = 0.35

    def add_placeholder_mesh(name, comp_id, cyl, loc, size=(0.04, 0.04, 0.04), shape='CUBE'):
        if shape == 'CYLINDER':
            bpy.ops.mesh.primitive_cylinder_add(radius=size[0]/2.0, depth=size[2], location=loc)
        elif shape == 'SPHERE':
            bpy.ops.mesh.primitive_uv_sphere_add(radius=size[0]/2.0, location=loc)
        else:
            bpy.ops.mesh.primitive_cube_add(size=size[0], location=loc)
            
        p_obj = bpy.context.view_layer.objects.active
        p_obj.name = name
        p_obj["component_id"] = comp_id
        p_obj["placeholder"] = True
        if cyl is not None:
            p_obj["cylinder"] = cyl
            
        if p_obj.data.materials:
            p_obj.data.materials[0] = mat_placeholder
        else:
            p_obj.data.materials.append(mat_placeholder)
        return p_obj

    print("\n  [PLACEHOLDERS] Adding missing components per DRDO Addendum Section 4.3...")
    
    # 4.1 Per-Cylinder Placeholders: Injectors, Spark Plugs, CHT & EGT Sensors, Cylinder Barrels
    for cyl in range(1, 5):
        hc = head_centers[cyl]
        # In scale of 915is: engine dimensions are ~0.5m across
        # Bounding box coordinates from earlier were scaled by 0.0254 or unit matrix. Let's place relative to head
        head_obj = bpy.data.objects.get(f"Cylinder_Head_{cyl}")
        h_loc = head_obj.location if head_obj else mathutils.Vector((0, 0, 0))
        
        # Injectors (on intake side: Z slightly higher)
        inj_loc = (hc[0] * 0.0254 if abs(hc[0]) > 1.0 else hc[0], 
                   (hc[1] * 0.0254 if abs(hc[1]) > 1.0 else hc[1]) * 0.85, 
                   0.08)
        add_placeholder_mesh(f"Injector_{cyl}", f"injector_{cyl}", cyl, inj_loc, size=(0.02, 0.02, 0.05), shape='CYLINDER')
        
        # Spark Plugs (on top of head)
        plug_loc = (inj_loc[0], inj_loc[1] * 1.08, 0.05)
        add_placeholder_mesh(f"Spark_Plug_{cyl}", f"spark_plug_{cyl}", cyl, plug_loc, size=(0.015, 0.015, 0.04), shape='CYLINDER')
        
        # CHT Sensor (on head)
        cht_loc = (inj_loc[0] + 0.02, inj_loc[1] * 1.05, 0.02)
        add_placeholder_mesh(f"Sensor_CHT_{cyl}", f"sensor_cht_{cyl}", cyl, cht_loc, size=(0.015, 0.015, 0.02), shape='SPHERE')
        
        # EGT Sensor (on exhaust near head)
        egt_loc = (inj_loc[0] - 0.02, inj_loc[1] * 0.95, -0.12)
        add_placeholder_mesh(f"Sensor_EGT_{cyl}", f"sensor_egt_{cyl}", cyl, egt_loc, size=(0.015, 0.015, 0.02), shape='SPHERE')
        
        # Cylinder Barrels
        barrel_loc = (inj_loc[0], inj_loc[1] * 0.75, -0.02)
        add_placeholder_mesh(f"Cylinder_Barrel_{cyl}", f"cylinder_barrel_{cyl}", cyl, barrel_loc, size=(0.08, 0.08, 0.09), shape='CYLINDER')

    # 4.2 Engine-Level Placeholders
    # Fuel Rail
    add_placeholder_mesh("Fuel_Rail", "fuel_rail", None, (-0.08, 0.0, 0.09), size=(0.18, 0.02, 0.02), shape='CYLINDER')
    # Airbox / Air Filter
    add_placeholder_mesh("Airbox_Filter", "airbox_filter", None, (-0.28, -0.15, 0.12), size=(0.14, 0.12, 0.10), shape='CUBE')
    # Oil Cooler
    add_placeholder_mesh("Oil_Cooler", "oil_cooler", None, (-0.22, 0.22, -0.12), size=(0.12, 0.08, 0.10), shape='CUBE')
    # Oil Pump
    add_placeholder_mesh("Oil_Pump", "oil_pump", None, (0.05, 0.0, -0.15), size=(0.06, 0.06, 0.06), shape='CYLINDER')
    # Water Pump
    add_placeholder_mesh("Water_Pump", "water_pump", None, (0.08, -0.05, -0.12), size=(0.07, 0.07, 0.06), shape='CYLINDER')
    # Radiator
    add_placeholder_mesh("Radiator", "radiator", None, (0.22, 0.0, -0.08), size=(0.05, 0.28, 0.22), shape='CUBE')
    # Alternator (Internal stator/external)
    add_placeholder_mesh("Alternator", "alternator", None, (-0.20, 0.0, -0.08), size=(0.10, 0.10, 0.08), shape='CYLINDER')
    # Propeller Flange
    add_placeholder_mesh("Prop_Flange", "prop_flange", None, (0.24, 0.0, 0.08), size=(0.12, 0.12, 0.03), shape='CYLINDER')
    # Wastegate Actuator
    add_placeholder_mesh("Wastegate_Actuator", "wastegate", None, (-0.22, -0.12, -0.22), size=(0.05, 0.05, 0.08), shape='CYLINDER')
    # MAP Sensor
    add_placeholder_mesh("Sensor_MAP", "sensor_map", None, (-0.15, 0.0, 0.15), size=(0.02, 0.02, 0.02), shape='CUBE')
    # Oil Pressure Sensor
    add_placeholder_mesh("Sensor_Oil_Press", "sensor_oil_press", None, (0.02, 0.08, -0.14), size=(0.02, 0.02, 0.03), shape='CYLINDER')

    # Remove temporary floor plane if exists
    plane = bpy.data.objects.get("Plane001")
    if plane:
        bpy.data.objects.remove(plane, do_unlink=True)
        
    # Frame camera
    cam = bpy.data.objects.get('Main_Studio_Camera')
    if cam:
        cam.location = mathutils.Vector((1.0, -1.3, 0.8))
        target = mathutils.Vector((-0.25, 0.0, 0.0))
        direction = target - cam.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam.rotation_euler = rot_quat.to_euler()
        cam.data.clip_start = 0.05
        cam.data.clip_end = 100.0

    # Save to _work.blend
    print(f"\n[SAVE] Saving decomposed model to: {work_blend}")
    bpy.ops.wm.save_as_mainfile(filepath=work_blend)
    
    # Render verification image
    out_dir = os.path.join(PROJECT_ROOT, "assets", "renders")
    os.makedirs(out_dir, exist_ok=True)
    render_path = os.path.join(out_dir, "rotax_915is_decomposed.png")
    
    scene = bpy.context.scene
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = render_path
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    
    print(f"[RENDER] Rendering verification frame to {render_path}...")
    bpy.ops.render.render(write_still=True)
    print("  [SUCCESS] Card B-02 script executed successfully!\n")
    return True

if __name__ == "__main__":
    decompose_915()
