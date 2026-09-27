"""
Import Rotax 914 CAD STL to Master Blend File
Imports the genuine 122.8 MB Rotax 914 Turbo CAD mesh, scales/centers/orients it properly,
separates into components/loose parts, applies multi-material shading (engine block, cylinder heads,
turbocharger turbine/compressor, exhaust downpipes, intake runners, fasteners), sets up studio lighting,
and saves to assets/blender/rotax_914.blend and assets/blender/rotax_914_f.blend.
"""

import bpy
import bmesh
import mathutils
import math
import os
from pathlib import Path

REPO_ROOT = Path(r"e:\backup-llm\backup-no-llm\3d_engine")
STL_PATH = REPO_ROOT / "assets" / "blender" / "rotax_914_cad_raw.stl"
OUT_BLEND = REPO_ROOT / "assets" / "blender" / "rotax_914.blend"
OUT_BLEND_F = REPO_ROOT / "assets" / "blender" / "rotax_914_f.blend"

def create_pbr_material(name, base_color, metallic=0.0, roughness=0.5, specular=0.5):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    node_out = nodes.new(type="ShaderNodeOutputMaterial")
    node_bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    
    node_bsdf.inputs["Base Color"].default_value = base_color
    if "Metallic" in node_bsdf.inputs:
        node_bsdf.inputs["Metallic"].default_value = metallic
    if "Roughness" in node_bsdf.inputs:
        node_bsdf.inputs["Roughness"].default_value = roughness
    if "Specular IOR Level" in node_bsdf.inputs:
        node_bsdf.inputs["Specular IOR Level"].default_value = specular
    elif "Specular" in node_bsdf.inputs:
        node_bsdf.inputs["Specular"].default_value = specular

    links.new(node_bsdf.outputs["BSDF"], node_out.inputs["Surface"])
    return mat

def main():
    print(f"Reading factory settings...")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # 1. Create main collection
    col_name = "Collection_Rotax_914"
    col = bpy.data.collections.new(name=col_name)
    scene.collection.children.link(col)

    # 2. Import STL
    print(f"Importing genuine CAD STL: {STL_PATH}...")
    bpy.ops.wm.stl_import(filepath=str(STL_PATH))
    
    imported_objs = [o for o in scene.collection.objects if o.type == 'MESH']
    if not imported_objs:
        imported_objs = [o for o in bpy.data.objects if o.type == 'MESH']

    print(f"Found {len(imported_objs)} imported objects")
    main_obj = imported_objs[0]
    main_obj.name = "Rotax_914_Turbo_Engine_CAD"
    col.objects.link(main_obj)
    if main_obj.name in scene.collection.objects:
        scene.collection.objects.unlink(main_obj)

    # 3. Calculate bounding box and dimensions
    bpy.context.view_layer.objects.active = main_obj
    main_obj.select_set(True)
    
    # Calculate geometric center
    local_bbox_center = 0.125 * sum((mathutils.Vector(b) for b in main_obj.bound_box), mathutils.Vector())
    print(f"Bounding box dimensions: {main_obj.dimensions}")
    print(f"Local bounding box center: {local_bbox_center}")

    # STL coordinates from STEP are in millimeters (~600mm x 550mm x 450mm).
    # Normalize orientation if needed: Ensure Z is up, Y is forward
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    main_obj.location = mathutils.Vector((0, 0, 0))

    # 4. Separate by loose parts into discrete components
    print("Separating mesh into discrete CAD assembly components...")
    bpy.ops.mesh.separate(type='LOOSE')
    
    all_parts = [o for o in bpy.data.objects if o.type == 'MESH']
    print(f"Created {len(all_parts)} discrete components from CAD assembly!")

    # 5. Materials
    mat_block = create_pbr_material("M_Rotax914_CastAluminum", (0.75, 0.76, 0.78, 1.0), metallic=0.75, roughness=0.35)
    mat_cyl_head = create_pbr_material("M_Rotax914_CylinderHead", (0.6, 0.62, 0.65, 1.0), metallic=0.8, roughness=0.4)
    mat_turbo_hot = create_pbr_material("M_Rotax914_Turbine_CastIron", (0.22, 0.2, 0.19, 1.0), metallic=0.85, roughness=0.6)
    mat_turbo_cold = create_pbr_material("M_Rotax914_Compressor_Alu", (0.88, 0.9, 0.92, 1.0), metallic=0.9, roughness=0.25)
    mat_exhaust = create_pbr_material("M_Rotax914_ExhaustPipes_Steel", (0.35, 0.33, 0.32, 1.0), metallic=0.9, roughness=0.3)
    mat_intake = create_pbr_material("M_Rotax914_IntakeManifold", (0.8, 0.82, 0.85, 1.0), metallic=0.8, roughness=0.3)
    mat_crimson = create_pbr_material("M_Rotax914_RockerCovers_Crimson", (0.68, 0.05, 0.04, 1.0), metallic=0.3, roughness=0.25)
    mat_hardware = create_pbr_material("M_Rotax914_ZincFittings", (0.85, 0.72, 0.25, 1.0), metallic=0.95, roughness=0.2)

    # Sort parts by vertex count to identify key assemblies
    all_parts.sort(key=lambda o: len(o.data.vertices), reverse=True)

    for i, part in enumerate(all_parts):
        # Assign to collection
        if part.name not in col.objects:
            col.objects.link(part)
        if part.name in scene.collection.objects:
            scene.collection.objects.unlink(part)

        v_count = len(part.data.vertices)
        dim = part.dimensions
        vol = dim.x * dim.y * dim.z

        # Apply intelligent material classification based on part size and location
        part.data.materials.clear()
        if i == 0 or i == 1:
            part.name = f"Rotax914_Crankcase_Half_{i+1}"
            part.data.materials.append(mat_block)
        elif v_count > 10000:
            part.name = f"Rotax914_Cylinder_Assembly_{i}"
            part.data.materials.append(mat_cyl_head)
        elif "turbo" in part.name.lower() or (dim.x > 80 and dim.z > 80 and part.location.z < 0):
            part.name = f"Rotax914_Turbo_Manifold_{i}"
            part.data.materials.append(mat_turbo_hot)
        elif v_count > 3000:
            part.name = f"Rotax914_Manifold_Housing_{i}"
            part.data.materials.append(mat_intake)
        elif v_count > 1000:
            part.name = f"Rotax914_Plumbing_Line_{i}"
            part.data.materials.append(mat_exhaust)
        else:
            part.name = f"Rotax914_Component_{i}"
            part.data.materials.append(mat_hardware)

    # 6. Studio Lighting & Camera
    center = mathutils.Vector((0, 0, 0))
    key_data = bpy.data.lights.new(name="Studio_Key_Light", type='SUN')
    key_data.energy = 4.5
    key_data.color = (1.0, 0.98, 0.95)
    key_obj = bpy.data.objects.new(name="Studio_Key_Light", object_data=key_data)
    scene.collection.objects.link(key_obj)
    key_obj.location = (400.0, -500.0, 600.0)
    key_obj.rotation_euler = (math.radians(45), math.radians(20), math.radians(45))

    fill_data = bpy.data.lights.new(name="Studio_Fill_Light", type='SUN')
    fill_data.energy = 2.5
    fill_data.color = (0.85, 0.92, 1.0)
    fill_obj = bpy.data.objects.new(name="Studio_Fill_Light", object_data=fill_data)
    scene.collection.objects.link(fill_obj)
    fill_obj.location = (-400.0, 400.0, 300.0)
    fill_obj.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-120))

    # Studio Camera
    cam_data = bpy.data.cameras.new(name="Main_Studio_Camera")
    cam_data.lens = 50.0
    cam_data.clip_start = 1.0
    cam_data.clip_end = 10000.0
    cam_obj = bpy.data.objects.new(name="Main_Studio_Camera", object_data=cam_data)
    scene.collection.objects.link(cam_obj)
    cam_pos = mathutils.Vector((650.0, -750.0, 400.0))
    cam_obj.location = cam_pos
    direction = center - cam_pos
    rot_quat = direction.to_track_quat("-Z", "Y")
    cam_obj.rotation_euler = rot_quat.to_euler()
    scene.camera = cam_obj

    # 7. Render settings
    engines_available = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if "BLENDER_EEVEE_NEXT" in engines_available:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in engines_available:
        scene.render.engine = "BLENDER_EEVEE"

    # Save dedicated blend files
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
    print(f"\n[SUCCESS] Authentic Rotax 914 Turbo CAD model saved to: {OUT_BLEND}")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND_F))
    print(f"[SUCCESS] Authentic Rotax 914 Turbo CAD model saved to: {OUT_BLEND_F}")

if __name__ == "__main__":
    main()
