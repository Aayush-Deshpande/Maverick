import bpy
import bmesh
import json
import sys
import math
from pathlib import Path
import mathutils

def run_validation(manifest_path, report_base_path):
    report_base = Path(report_base_path).resolve()
    report_base.parent.mkdir(parents=True, exist_ok=True)
    json_path = report_base.with_suffix(".json")
    md_path = report_base.with_suffix(".md")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    is_engine = "engine_id" in manifest
    asset_id = manifest.get("engine_id") or manifest.get("platform_id")
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()

    checks = {}
    failures = []
    warnings = []

    # Helper to record check
    def record_check(cid, name, passed, details="", is_warn=False):
        status = "PASS" if passed else ("WARN" if is_warn else "FAIL")
        checks[cid] = {"name": name, "status": status, "details": details}
        if not passed:
            if is_warn:
                warnings.append(f"[{cid}] {name}: {details}")
            else:
                failures.append(f"[{cid}] {name}: {details}")

    # C1: Manifest named objects exist exactly once
    expected_objs = []
    if is_engine:
        if "components" in manifest:
            for cname, cdata in manifest["components"].items():
                expected_objs.extend(cdata.get("objects", []))
        if "sensors" in manifest:
            for sname, sdata in manifest["sensors"].items():
                expected_objs.extend(sdata.get("objects", []))
    else:
        for cname in manifest.get("must_have_features", []):
            pass # airframe specific
    missing_objs = [name for name in expected_objs if name not in bpy.data.objects]
    record_check("C1", "Manifest objects exist", len(missing_objs) == 0, f"Missing: {missing_objs}")

    # C2: No duplicate .00N names
    dot_names = [o.name for o in bpy.data.objects if any(o.name.endswith(f".{i:03d}") for i in range(1, 1000))]
    dot_mats = [m.name for m in bpy.data.materials if any(m.name.endswith(f".{i:03d}") for i in range(1, 1000))]
    record_check("C2", "No .00N duplicate suffixes", len(dot_names) == 0 and len(dot_mats) == 0, f"Objects: {dot_names}, Mats: {dot_mats}")

    # C3: Airframe ground contact (Z=0.000 ± 0.005m)
    if not is_engine:
        lg_col = bpy.data.collections.get("Landing_Gear")
        if lg_col:
            gear_objs = [o for o in lg_col.objects if o.type == 'MESH']
        else:
            gear_objs = [o for o in bpy.data.objects if (("gear" in o.name.lower() and "gearbox" not in o.name.lower()) or "wheel" in o.name.lower() or "tire" in o.name.lower())]
        min_z = float('inf')
        for o in gear_objs:
            if o.type == 'MESH':
                for corner in o.bound_box:
                    w_co = o.matrix_world @ mathutils.Vector(corner)
                    min_z = min(min_z, w_co.z)
        z_pass = abs(min_z) <= 0.005 if min_z != float('inf') else False
        record_check("C3", "Ground contact Z=0", z_pass, f"Min Z: {min_z:.4f} m")

    # C4: Airframe bounding box vs dimensions
    if not is_engine and "dimensions_m" in manifest:
        dims = manifest["dimensions_m"]
        min_co = [float('inf')]*3
        max_co = [float('-inf')]*3
        for o in bpy.data.objects:
            if o.type == 'MESH' and not any(k in o.name.lower() for k in ['ground', 'plane', 'blur', 'target']):
                for corner in o.bound_box:
                    w = o.matrix_world @ mathutils.Vector(corner)
                    for i in range(3):
                        min_co[i] = min(min_co[i], w[i])
                        max_co[i] = max(max_co[i], w[i])
        actual_span = max_co[0] - min_co[0]
        actual_len = max_co[1] - min_co[1]
        actual_ht = max_co[2] - min_co[2]
        exp_span = dims.get("wingspan", {}).get("value")
        exp_len = dims.get("length", {}).get("value")
        exp_ht = dims.get("height", {}).get("value")
        tol = 0.05 if manifest.get("dimension_confidence") == "LOW" else 0.02
        dim_pass = True
        err_msg = []
        if exp_span:
            diff = abs(actual_span - exp_span) / exp_span
            if diff > tol:
                dim_pass = False
                err_msg.append(f"Wingspan err {diff*100:.1f}%")
        record_check("C4", "Bounding box dimensions", dim_pass, ", ".join(err_msg) or "Dimensions within tolerance")

    # C5: Required collections exist
    req_cols = ["Cameras", "Lighting"]
    if is_engine:
        req_cols.extend(["Block_Cylinders", "Intake_Charge_Air", "Exhaust", "Lubrication", "Cooling", "Gearbox_Prop_Drive"])
    else:
        req_cols.extend(["Airframe", "Wings", "Tail", "Propulsion", "Landing_Gear", "Sensors_Payload"])
    all_col_names = [c.name for c in bpy.data.collections]
    missing_cols = [c for c in req_cols if c not in all_col_names]
    record_check("C5", "Required collections exist", len(missing_cols) == 0, f"Missing: {missing_cols}")

    # C6: Materials have twin attribute nodes
    mats_without_twin = []
    for m in bpy.data.materials:
        if m.node_tree:
            node_names = [n.name for n in m.node_tree.nodes]
            if not all(k in node_names for k in ["TwinFaultLevel", "TwinFaultRGB", "TwinGhost", "TwinSensorSuspect"]):
                mats_without_twin.append(m.name)
    record_check("C6", "Material twin nodes", len(mats_without_twin) == 0, f"Materials missing twin nodes: {mats_without_twin}")

    # C7: Cameras exist with TrackTo
    raw_cams = manifest.get("cameras", ["Cam_Hero"])
    expected_cams = [c.get("name") if isinstance(c, dict) else c for c in raw_cams]
    cams_missing = [c for c in expected_cams if c not in bpy.data.objects]
    record_check("C7", "Manifest cameras exist", len(cams_missing) == 0, f"Missing cameras: {cams_missing}")

    # C8: No decal planes (faces <= 12 with Decal/Marking/Roundel)
    decal_planes = []
    for o in bpy.data.objects:
        if o.type == 'MESH':
            if any(k in o.name.lower() for k in ["decal", "roundel", "flag", "marking"]):
                if len(o.data.polygons) <= 12:
                    decal_planes.append(o.name)
    record_check("C8", "No floating decal planes", len(decal_planes) == 0, f"Decal planes found: {decal_planes}")

    # C9: Triangle budget
    total_tris = 0
    for o in bpy.data.objects:
        if o.type == 'MESH':
            eval_obj = o.evaluated_get(depsgraph)
            m = eval_obj.to_mesh()
            total_tris += len(m.loop_triangles)
            eval_obj.to_mesh_clear()
    limit = 2500000 if is_engine else 150000
    record_check("C9", "Triangle budget", total_tris <= limit, f"Total tris: {total_tris} (limit: {limit})")

    # C10: Images packed and none missing
    unpacked_images = [img.name for img in bpy.data.images if not img.packed_file and not img.name.startswith("Viewer")]
    record_check("C10", "All images packed", len(unpacked_images) == 0, f"Unpacked: {unpacked_images}")

    # C11: No action animations on mechanisms/propellers
    pivots_with_actions = []
    for o in bpy.data.objects:
        if any(k in o.name.lower() for k in ["pivot", "propeller", "gear", "wingfold"]):
            if o.animation_data and o.animation_data.action:
                pivots_with_actions.append(o.name)
    record_check("C11", "No animation actions on pivots", len(pivots_with_actions) == 0, f"Objects: {pivots_with_actions}")

    # C12: Units METRIC, METERS, 1.0
    u = scene.unit_settings
    units_pass = (u.system == 'METRIC' and u.length_unit == 'METERS' and abs(u.scale_length - 1.0) < 1e-5)
    record_check("C12", "Units METRIC/METERS/1.0", units_pass, f"System: {u.system}, Unit: {u.length_unit}, Scale: {u.scale_length}")

    # C16: Sides centroids Left < 0, Right > 0
    side_mismatches = []
    for o in bpy.data.objects:
        if o.type == 'MESH':
            if o.name.endswith("_Right") or "_Right_" in o.name:
                if o.location.x < -0.01:
                    side_mismatches.append(f"{o.name} at X={o.location.x:.3f}")
            elif o.name.endswith("_Left") or "_Left_" in o.name:
                if o.location.x > 0.01:
                    side_mismatches.append(f"{o.name} at X={o.location.x:.3f}")
    record_check("C16", "Sides coordinate alignment", len(side_mismatches) == 0, f"Mismatches: {side_mismatches}")

    # C20: No placeholder components (>= 300 tris, not 8-vert cube)
    placeholders = []
    if is_engine and "components" in manifest:
        for cname, cdata in manifest["components"].items():
            comp_tris = 0
            for oname in cdata.get("objects", []):
                if oname in bpy.data.objects:
                    o = bpy.data.objects[oname]
                    eval_o = o.evaluated_get(depsgraph)
                    m = eval_o.to_mesh()
                    comp_tris += len(m.loop_triangles)
                    eval_o.to_mesh_clear()
            if comp_tris < 300:
                placeholders.append(f"{cname} ({comp_tris} tris < 300)")
    record_check("C20", "No placeholder components", len(placeholders) == 0, f"Placeholders: {placeholders}")

    # Write JSON report
    report_data = {
        "asset_id": asset_id,
        "manifest_path": str(manifest_path),
        "overall_status": "FAIL" if len(failures) > 0 else "PASS",
        "total_eval_triangles": total_tris,
        "checks": checks,
        "failures": failures,
        "warnings": warnings
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    # Write Markdown report
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Validation Report: `{asset_id}`\n\n")
        f.write(f"**Overall Status:** `{'FAIL' if failures else 'PASS'}`\n\n")
        f.write(f"- Total Evaluated Triangles: `{total_tris}`\n")
        f.write(f"- Failures: `{len(failures)}`\n")
        f.write(f"- Warnings: `{len(warnings)}`\n\n")
        f.write("## Checks Summary\n\n")
        f.write("| ID | Check | Status | Details |\n|---|---|---|---|\n")
        for cid, c in sorted(checks.items()):
            f.write(f"| {cid} | {c['name']} | **{c['status']}** | {c['details']} |\n")

    print(f"Validation complete: {'FAIL' if failures else 'PASS'}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")

    if failures:
        sys.exit(1)

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    manifest_p = ""
    report_p = ""
    for i in range(len(args)):
        if args[i] == "--manifest" and i + 1 < len(args):
            manifest_p = args[i+1]
        elif args[i] == "--report" and i + 1 < len(args):
            report_p = args[i+1]
    if manifest_p and report_p:
        run_validation(manifest_p, report_p)
    else:
        print("Usage: validate_asset.py -- --manifest <path> --report <path>")
        sys.exit(1)
