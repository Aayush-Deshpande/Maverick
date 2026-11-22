"""
Aerospace PBR Material Enhancement Script for ANUMAAN Master Twin.
Eliminates 'plastic toy' appearance on Austro AE300 and VRDE 2.2L engines:
1. Replaces neon toy plastics (TorqueSeal_Green, BlueSilicone, YellowPoly) with genuine aerospace PBR shaders:
   - Cadmium / zinc-plated grade-8 aerospace hardware (metallic: 0.94, roughness: 0.28)
   - Aerospace fluorosilicone / braided nitrile hoses (matte dark charcoal, roughness: 0.62)
   - Real MIL-SPEC hard-anodized aluminum AN fittings (metallic: 0.92, roughness: 0.24)
   - High-temp engineering thermoplastic (PEEK / PA66-GF30) satin composite (roughness: 0.58)
   - Cast aerospace A356-T6 aluminum engine blocks with authentic micro-roughness & fine bump
2. Updates Studio Lighting:
   - Removes harsh saturated cyan rim wash and replaces with crisp neutral daylight accent
3. Saves to assets/blender/scenes/anumaan_master_twin_work.blend
4. Re-renders verification frames to assets/renders/
"""

import bpy
import mathutils
import math
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "apps", "blender_twin"))

import standalone_digital_twin_app as twin

def upgrade_materials():
    work_blend = os.path.join(PROJECT_ROOT, "assets", "blender", "scenes", "anumaan_master_twin_work.blend")
    assert os.path.exists(work_blend), f"File not found: {work_blend}"
    bpy.ops.wm.open_mainfile(filepath=work_blend)

    print("\n=======================================================")
    print("  UPGRADING AEROSPACE PBR MATERIALS (AE300 & VRDE 2.2L)")
    print("=======================================================\n")

    # Helper to get or create Principled BSDF
    def get_principled(mat):
        if not mat or not mat.node_tree:
            return None
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if not bsdf:
            for n in mat.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    return n
        return bsdf

    # 1. FIX VRDE M_TorqueSeal_Green -> Genuine Cad-Plated / Zinc Aerospace Hardware
    m_ts_green = bpy.data.materials.get("M_TorqueSeal_Green")
    if m_ts_green:
        bsdf = get_principled(m_ts_green)
        if bsdf:
            print("  [FIX] Upgrading M_TorqueSeal_Green from neon plastic to Cad-Plated Aerospace Steel...")
            bsdf.inputs['Base Color'].default_value = (0.72, 0.74, 0.77, 1.0)
            bsdf.inputs['Metallic'].default_value = 0.94
            bsdf.inputs['Roughness'].default_value = 0.28
            if 'Specular IOR Level' in bsdf.inputs:
                bsdf.inputs['Specular IOR Level'].default_value = 0.5
            elif 'Specular' in bsdf.inputs:
                bsdf.inputs['Specular'].default_value = 0.5

    # Assign real steel material to Mount_Center_Hex_Bolt and Mount_Bolt_TorqueSeal if they had neon green
    col_vrde = bpy.data.collections.get("Collection_VRDE_2_2L")
    if col_vrde:
        m_steel = bpy.data.materials.get("M_Steel.002") or bpy.data.materials.get("M_Stainless")
        for obj_name in ["Mount_Center_Hex_Bolt", "Mount_Bolt_TorqueSeal"]:
            obj = col_vrde.objects.get(obj_name)
            if obj and m_steel:
                for slot in obj.material_slots:
                    slot.material = m_steel
                print(f"  [FIX] Reassigned {obj_name} to {m_steel.name}")

    # 2. FIX BLUE SILICONE (M_BlueSilicone and M_BlueSilicone.001)
    # Convert from oversaturated neon blue plastic to reinforced black nitrile / aerospace hose
    for m_name in ["M_BlueSilicone", "M_BlueSilicone.001"]:
        mat = bpy.data.materials.get(m_name)
        if mat:
            bsdf = get_principled(mat)
            if bsdf:
                print(f"  [FIX] Upgrading {m_name} from neon blue plastic to Reinforced Black Nitrile / Fluoroelastomer...")
                bsdf.inputs['Base Color'].default_value = (0.045, 0.048, 0.052, 1.0)
                bsdf.inputs['Metallic'].default_value = 0.05
                bsdf.inputs['Roughness'].default_value = 0.62
                if 'Specular IOR Level' in bsdf.inputs:
                    bsdf.inputs['Specular IOR Level'].default_value = 0.35
                elif 'Specular' in bsdf.inputs:
                    bsdf.inputs['Specular'].default_value = 0.35

    # 3. FIX ANODIZED FITTINGS (M_AnodizedBlue) -> Genuine Hard-Anodized Aluminum
    m_anod_blue = bpy.data.materials.get("M_AnodizedBlue")
    if m_anod_blue:
        bsdf = get_principled(m_anod_blue)
        if bsdf:
            print("  [FIX] Upgrading M_AnodizedBlue to MIL-A-8625 Hard-Anodized Aluminum...")
            bsdf.inputs['Base Color'].default_value = (0.018, 0.065, 0.22, 1.0)
            bsdf.inputs['Metallic'].default_value = 0.92
            bsdf.inputs['Roughness'].default_value = 0.24

    # 4. FIX M_TorqueSealBlue (AE300) -> Aerospace Dark Anodized Blue
    m_ts_blue = bpy.data.materials.get("M_TorqueSealBlue")
    if m_ts_blue:
        bsdf = get_principled(m_ts_blue)
        if bsdf:
            print("  [FIX] Upgrading M_TorqueSealBlue to Hard-Anodized Aero Finish...")
            bsdf.inputs['Base Color'].default_value = (0.02, 0.08, 0.25, 1.0)
            bsdf.inputs['Metallic'].default_value = 0.90
            bsdf.inputs['Roughness'].default_value = 0.26

    # 5. FIX YELLOW PLASTIC (M_YellowPoly, M_YellowCap) -> Engineering Satin Composite / Amber
    for m_name in ["M_YellowPoly", "M_YellowCap", "M_YellowLabel"]:
        mat = bpy.data.materials.get(m_name)
        if mat:
            bsdf = get_principled(mat)
            if bsdf:
                print(f"  [FIX] Upgrading {m_name} from toy yellow to High-Temp Engineering Polymer...")
                bsdf.inputs['Base Color'].default_value = (0.06, 0.065, 0.072, 1.0)
                bsdf.inputs['Metallic'].default_value = 0.08
                bsdf.inputs['Roughness'].default_value = 0.55

    # 6. FIX CAST ALUMINIUM (M_CastAluminium, M_CastAluminium.001) -> Authentic Cast Monoblock
    for m_name in ["M_CastAluminium", "M_CastAluminium.001"]:
        mat = bpy.data.materials.get(m_name)
        if mat:
            bsdf = get_principled(mat)
            if bsdf:
                print(f"  [FIX] Calibrating {m_name} to Authentic A356 Cast Aluminum Alloy...")
                bsdf.inputs['Base Color'].default_value = (0.58, 0.60, 0.63, 1.0)
                bsdf.inputs['Metallic'].default_value = 0.92
                bsdf.inputs['Roughness'].default_value = 0.38
                # Enhance bump distance for cast texture
                bump = mat.node_tree.nodes.get("Bump")
                if bump:
                    bump.inputs['Strength'].default_value = 0.06
                    bump.inputs['Distance'].default_value = 0.005

    # 7. FIX VALVE COVER PLASTIC (M_PlasticBlack.001, M_PlasticBlack.002)
    for m_name in ["M_PlasticBlack.001", "M_PlasticBlack.002"]:
        mat = bpy.data.materials.get(m_name)
        if mat:
            bsdf = get_principled(mat)
            if bsdf:
                print(f"  [FIX] Upgrading {m_name} to Powder-Coated Cast Satin Finish...")
                bsdf.inputs['Base Color'].default_value = (0.038, 0.040, 0.042, 1.0)
                bsdf.inputs['Metallic'].default_value = 0.20
                bsdf.inputs['Roughness'].default_value = 0.52

    # 8. UPGRADE STUDIO LIGHTING (Neutral Daylight Accent instead of 100% Cyan Wash)
    scene = bpy.context.scene
    rim_obj = bpy.data.objects.get("Studio_Rim_Cyan")
    if rim_obj and rim_obj.data:
        print("  [FIX] Calibrating studio rim lighting to neutral crisp daylight...")
        rim_obj.data.color = (0.92, 0.95, 1.0)
        rim_obj.data.energy = 2.0

    key_sun = bpy.data.objects.get("Studio_Key_Sun")
    if key_sun and key_sun.data:
        key_sun.data.energy = 3.2
        key_sun.data.color = (1.0, 0.98, 0.95)

    fill_sun = bpy.data.objects.get("Studio_Fill_Sun")
    if fill_sun and fill_sun.data:
        fill_sun.data.energy = 1.4
        fill_sun.data.color = (0.88, 0.92, 0.98)

    # Save to _work.blend
    bpy.ops.wm.save_as_mainfile(filepath=work_blend)
    print(f"\n  [OK] Saved enhanced materials to work blend: {work_blend}")

    # 9. RE-RENDER VERIFICATION FRAMES FOR AE300 AND VRDE 2.2L
    print("\n[VERIFY] Rendering updated verification frames...")
    renders_dir = os.path.join(PROJECT_ROOT, "assets", "renders")
    cam = bpy.data.objects.get("TurntableCam")
    scene.camera = cam

    for eng_id in ["austro_ae300", "vrde_jayem_2_2l"]:
        twin.switch_engine_collection(eng_id)
        prof = twin.ENGINE_PROFILES[eng_id]
        center = prof['default_center']
        dist = prof['default_distance']
        elev = prof['default_elevation']
        angle = prof.get('front_angle', -1.57)

        cam_x = center.x + dist * math.cos(elev) * math.sin(angle)
        cam_y = center.y - dist * math.cos(elev) * math.cos(angle)
        cam_z = center.z + dist * math.sin(elev)
        cam.location = mathutils.Vector((cam_x, cam_y, cam_z))
        
        direction = center - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

        out_img = os.path.join(renders_dir, f"master_twin_{eng_id}.png")
        scene.render.filepath = out_img
        bpy.ops.render.render(write_still=True)
        print(f"  [OK] Rendered enhanced {eng_id} to: {out_img}")

    print("\n🎉 AEROSPACE PBR UPGRADE COMPLETED SUCCESSFULLY!\n")

if __name__ == "__main__":
    upgrade_materials()
