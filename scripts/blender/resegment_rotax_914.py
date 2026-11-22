"""
Resegment Rotax 914 F Turbo components and reassign wastegate objects.
DRDO / iDEX PS-26054 Compliance - Card B-03:
- Splits Rotax914_Cylinder_Bank_1 into cylinder_barrel_1 and cylinder_barrel_3
- Renames Rotax914_Cylinder_Head_5 -> cylinder_barrel_2 and Rotax914_Cylinder_Head_4 -> cylinder_barrel_4
- Splits Rotax914_Cylinder_Head_3 into cylinder_head_1 and cylinder_head_3
- Splits Rotax914_Cylinder_Head_2 into cylinder_head_2 and cylinder_head_4
- Reassigns 320 wastegate objects: 294 small -> fasteners/fittings, exhaust/turbo -> exhaust/turbo, true wastegate -> wastegate
- Adds placeholders: carburettor_1, carburettor_2, airbox_filter, tcu, wastegate_actuator, oil_tank, oil_pump, oil_cooler, radiator, water_pump, alternator, fuel_pump, ignition_cdi, spark_plug_1..4, sensors
- Saves to assets/blender/engines/rotax_914/rotax_914_work.blend (Rule D53)
- Renders verification frame to assets/renders/rotax_914_resegmented.png
"""

import bpy
import mathutils
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

def resegment_914():
    blend_path = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_914", "rotax_914.blend")
    work_blend = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_914", "rotax_914_work.blend")
    
    print(f"\n[B-03] Opening Rotax 914 Master: {blend_path}")
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    
    # 1. Resegment Cylinder Barrels
    # Rotax 914 is modeled in millimeters. Center of engine is around (-96, 0, -48).
    # Bank 1 & 3: Y < 0 (-170.6)
    # Bank 2 & 4: Y > 0 (+170.6)
    # Rotax914_Cylinder_Bank_1 spans both Cyl 1 (front, local X > 0) and Cyl 3 (rear, local X <= 0)
    bank_1 = bpy.data.objects.get("Rotax914_Cylinder_Bank_1")
    if bank_1:
        bpy.ops.object.select_all(action='DESELECT')
        bank_1.select_set(True)
        bpy.context.view_layer.objects.active = bank_1
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        for v in bank_1.data.vertices:
            if v.co.x > 0:
                v.select = True
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        parts = bpy.context.selected_objects
        for p in parts:
            c = sum(p.bound_box[j][0] for j in range(8)) / 8.0
            if c > 0:
                p.name = "Cylinder_Barrel_1"
                p["component_id"] = "cylinder_barrel_1"
                p["cylinder"] = 1
            else:
                p.name = "Cylinder_Barrel_3"
                p["component_id"] = "cylinder_barrel_3"
                p["cylinder"] = 3
        print(f"  [CYLINDERS] Split Rotax914_Cylinder_Bank_1 into Barrel 1 & Barrel 3")

    cyl_5 = bpy.data.objects.get("Rotax914_Cylinder_Head_5")
    if cyl_5:
        cyl_5.name = "Cylinder_Barrel_2"
        cyl_5["component_id"] = "cylinder_barrel_2"
        cyl_5["cylinder"] = 2
        print(f"  [CYLINDERS] Renamed Rotax914_Cylinder_Head_5 -> Cylinder_Barrel_2")

    cyl_4 = bpy.data.objects.get("Rotax914_Cylinder_Head_4")
    if cyl_4:
        cyl_4.name = "Cylinder_Barrel_4"
        cyl_4["component_id"] = "cylinder_barrel_4"
        cyl_4["cylinder"] = 4
        print(f"  [CYLINDERS] Renamed Rotax914_Cylinder_Head_4 -> Cylinder_Barrel_4")

    # 2. Resegment Cylinder Heads
    # Rotax914_Cylinder_Head_3 (Y = -192.12): head assembly on Bank 1 & 3
    head_3 = bpy.data.objects.get("Rotax914_Cylinder_Head_3")
    if head_3:
        bpy.ops.object.select_all(action='DESELECT')
        head_3.select_set(True)
        bpy.context.view_layer.objects.active = head_3
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        for v in head_3.data.vertices:
            if v.co.x > 0:
                v.select = True
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        parts = bpy.context.selected_objects
        for p in parts:
            c = sum(p.bound_box[j][0] for j in range(8)) / 8.0
            if c > 0:
                p.name = "Cylinder_Head_1"
                p["component_id"] = "cylinder_head_1"
                p["cylinder"] = 1
            else:
                p.name = "Cylinder_Head_3"
                p["component_id"] = "cylinder_head_3"
                p["cylinder"] = 3
        print(f"  [CYLINDERS] Split Rotax914_Cylinder_Head_3 into Head 1 & Head 3")

    # Rotax914_Cylinder_Head_2 (Y = +189.63): head assembly on Bank 2 & 4
    head_2 = bpy.data.objects.get("Rotax914_Cylinder_Head_2")
    if head_2:
        bpy.ops.object.select_all(action='DESELECT')
        head_2.select_set(True)
        bpy.context.view_layer.objects.active = head_2
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        for v in head_2.data.vertices:
            if v.co.x > 0:
                v.select = True
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        parts = bpy.context.selected_objects
        for p in parts:
            c = sum(p.bound_box[j][0] for j in range(8)) / 8.0
            if c > 0:
                p.name = "Cylinder_Head_2"
                p["component_id"] = "cylinder_head_2"
                p["cylinder"] = 2
            else:
                p.name = "Cylinder_Head_4"
                p["component_id"] = "cylinder_head_4"
                p["cylinder"] = 4
        print(f"  [CYLINDERS] Split Rotax914_Cylinder_Head_2 into Head 2 & Head 4")

    # 3. Reassign 320 Wastegate Objects
    wg_objects = [o for o in bpy.data.objects if "Rotax914_Turbo_Wastegate" in o.name]
    print(f"\n  [WASTEGATE] Reassigning {len(wg_objects)} missegmented wastegate objects...")
    
    true_wastegate = []
    turbo_exhaust = []
    small_fasteners = []
    
    for obj in wg_objects:
        max_d = max(obj.dimensions)
        loc = obj.location
        if max_d > 50.0:
            # Check if it's the actual wastegate valve at bottom outlet (Z < -150)
            if loc.z < -150.0 and loc.x > -100.0:
                true_wastegate.append(obj)
            else:
                turbo_exhaust.append(obj)
        else:
            small_fasteners.append(obj)
            
    print(f"    - True Wastegate: {len(true_wastegate)} objects")
    print(f"    - Exhaust / Turbo Housing: {len(turbo_exhaust)} objects")
    print(f"    - Fasteners & Hardware: {len(small_fasteners)} objects")
    
    # Merge small fasteners
    if small_fasteners:
        bpy.ops.object.select_all(action='DESELECT')
        for sf in small_fasteners:
            sf.select_set(True)
        bpy.context.view_layer.objects.active = small_fasteners[0]
        bpy.ops.object.join()
        fast_obj = bpy.context.view_layer.objects.active
        fast_obj.name = "Engine_Fittings_Fasteners"
        fast_obj["component_id"] = "crankcase"
        
    # Merge turbo/exhaust parts
    if turbo_exhaust:
        bpy.ops.object.select_all(action='DESELECT')
        for te in turbo_exhaust:
            te.select_set(True)
        bpy.context.view_layer.objects.active = turbo_exhaust[0]
        bpy.ops.object.join()
        te_obj = bpy.context.view_layer.objects.active
        te_obj.name = "Turbocharger_Exhaust_Plumbing"
        te_obj["component_id"] = "turbocharger"
        
    # Merge true wastegate
    if true_wastegate:
        bpy.ops.object.select_all(action='DESELECT')
        for tw in true_wastegate:
            tw.select_set(True)
        bpy.context.view_layer.objects.active = true_wastegate[0]
        bpy.ops.object.join()
        tw_obj = bpy.context.view_layer.objects.active
        tw_obj.name = "Wastegate_Flapper_Assembly"
        tw_obj["component_id"] = "wastegate"

    # Set component_id on existing other Rotax 914 parts
    for o in bpy.data.objects:
        if o.type == 'MESH' and "component_id" not in o:
            n = o.name.lower()
            if "crankcase" in n or "block" in n:
                o["component_id"] = "crankcase"
            elif "gearbox" in n or "prop" in n:
                o["component_id"] = "gearbox"
            elif "exhaust" in n:
                o["component_id"] = "exhaust"
            elif "intake" in n:
                o["component_id"] = "intake_manifold"
            elif "turbo" in n:
                o["component_id"] = "turbocharger"
            else:
                o["component_id"] = "crankcase"

    # 4. Add Placeholders per Addendum Section 4.2
    # In Rotax 914 scale (mm): engine is ~660 x 575 x 520 mm centered at (-96, 0, -48)
    mat_placeholder = bpy.data.materials.get("M_Component_Placeholder")
    if not mat_placeholder:
        mat_placeholder = bpy.data.materials.new(name="M_Component_Placeholder")
        mat_placeholder.use_nodes = True
        bsdf = mat_placeholder.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.25, 0.26, 0.28, 1.0)
            bsdf.inputs['Metallic'].default_value = 0.88
            bsdf.inputs['Roughness'].default_value = 0.32

    def add_placeholder_914(name, comp_id, cyl, loc, size=(40, 40, 40), shape='CUBE'):
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

    print("\n  [PLACEHOLDERS] Adding missing components for Rotax 914 F...")
    
    # 4.1 Carburettors: 914 is carburetted with two Bing CD carbs (one per bank)
    add_placeholder_914("Carburettor_1", "carburettor_1", None, (-120.0, -180.0, 180.0), size=(90, 70, 110), shape='CUBE')
    add_placeholder_914("Carburettor_2", "carburettor_2", None, (-150.0, 180.0, 180.0), size=(90, 70, 110), shape='CUBE')
    
    # 4.2 Airbox / Turbocharged Air Plenum
    add_placeholder_914("Airbox_Filter", "airbox_filter", None, (-180.0, 0.0, 210.0), size=(180, 220, 120), shape='CUBE')
    
    # 4.3 TCU (Turbocharger Control Unit)
    add_placeholder_914("TCU_Control_Unit", "tcu", None, (-310.0, 0.0, 80.0), size=(140, 100, 60), shape='CUBE')
    
    # 4.4 Wastegate Servo Actuator
    add_placeholder_914("Wastegate_Actuator", "wastegate_actuator", None, (-80.0, -90.0, -160.0), size=(70, 70, 120), shape='CYLINDER')
    
    # 4.5 Dual Ducati Ignition CDI Boxes
    add_placeholder_914("Ignition_CDI", "ignition_cdi", None, (-280.0, 80.0, 120.0), size=(100, 70, 60), shape='CUBE')
    
    # 4.6 Lubrication & Cooling Placeholders
    add_placeholder_914("Oil_Tank", "oil_tank", None, (-260.0, -160.0, -50.0), size=(120, 120, 240), shape='CYLINDER')
    add_placeholder_914("Oil_Pump", "oil_pump", None, (60.0, 0.0, -80.0), size=(80, 80, 70), shape='CYLINDER')
    add_placeholder_914("Oil_Cooler", "oil_cooler", None, (-140.0, -220.0, -90.0), size=(160, 60, 120), shape='CUBE')
    add_placeholder_914("Water_Pump", "water_pump", None, (80.0, -40.0, -60.0), size=(90, 90, 80), shape='CYLINDER')
    add_placeholder_914("Radiator", "radiator", None, (180.0, 0.0, -50.0), size=(60, 280, 220), shape='CUBE')
    add_placeholder_914("Alternator", "alternator", None, (-220.0, 0.0, -60.0), size=(110, 110, 90), shape='CYLINDER')
    add_placeholder_914("Fuel_Pump", "fuel_pump", None, (-240.0, 140.0, -40.0), size=(80, 80, 90), shape='CYLINDER')
    
    # 4.7 Per-Cylinder Spark Plugs & Sensors
    # Head 1 (X ~ -50, Y ~ -190), Head 3 (X ~ -150, Y ~ -190)
    # Head 2 (X ~ -80, Y ~ +190), Head 4 (X ~ -180, Y ~ +190)
    cyl_coords = {
        1: (-50.0, -190.0, 110.0),
        2: (-80.0, 190.0, 110.0),
        3: (-150.0, -190.0, 110.0),
        4: (-180.0, 190.0, 110.0),
    }
    for cyl, (cx, cy, cz) in cyl_coords.items():
        add_placeholder_914(f"Spark_Plug_{cyl}", f"spark_plug_{cyl}", cyl, (cx, cy, cz + 25.0), size=(20, 20, 45), shape='CYLINDER')
        add_placeholder_914(f"Sensor_CHT_{cyl}", f"sensor_cht_{cyl}", cyl, (cx + 20.0, cy, cz + 10.0), size=(18, 18, 20), shape='SPHERE')
        add_placeholder_914(f"Sensor_EGT_{cyl}", f"sensor_egt_{cyl}", cyl, (cx - 20.0, cy * 0.9, cz - 120.0), size=(18, 18, 20), shape='SPHERE')

    # Sensors: MAP, Oil Pressure, Oil Temp
    add_placeholder_914("Sensor_MAP", "sensor_map", None, (-160.0, 0.0, 220.0), size=(25, 25, 25), shape='CUBE')
    add_placeholder_914("Sensor_Oil_Press", "sensor_oil_press", None, (40.0, 50.0, -70.0), size=(25, 25, 35), shape='CYLINDER')
    add_placeholder_914("Sensor_Oil_Temp", "sensor_oil_temp", None, (-240.0, -150.0, -30.0), size=(20, 20, 30), shape='CYLINDER')

    # 5. Calibrate Camera & Save
    cam = bpy.data.objects.get("Camera") or bpy.data.objects.get("Main_Studio_Camera")
    if cam:
        cam.location = mathutils.Vector((900.0, -1100.0, 700.0))
        target = mathutils.Vector((-96.0, 0.0, -48.0))
        direction = target - cam.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam.rotation_euler = rot_quat.to_euler()
        cam.data.clip_start = 5.0
        cam.data.clip_end = 15000.0

    print(f"\n[SAVE] Saving resegmented model to: {work_blend}")
    bpy.ops.wm.save_as_mainfile(filepath=work_blend)
    
    out_dir = os.path.join(PROJECT_ROOT, "assets", "renders")
    os.makedirs(out_dir, exist_ok=True)
    render_path = os.path.join(out_dir, "rotax_914_resegmented.png")
    
    scene = bpy.context.scene
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = render_path
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    
    print(f"[RENDER] Rendering verification frame to {render_path}...")
    bpy.ops.render.render(write_still=True)
    print("  [SUCCESS] Card B-03 script executed successfully!\n")
    return True

if __name__ == "__main__":
    resegment_914()
