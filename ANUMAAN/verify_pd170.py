"""
TEI-PD170 build verifier — audits the live Blender scene against ANUMAAN/tar.md.

Run inside Blender (or via blender --background <file> --python verify_pd170.py).
Prints a PASS/FAIL report and a remaining-work list.
"""
import bpy
import math
import os
from mathutils import Vector

TOL = 0.35          # dimension tolerance (fraction)
THIN = 120          # triangles below this = placeholder
ENVELOPE = 1.2      # m; anything beyond this from origin is stray

# shared helpers. Object.bound_box lies for CURVE objects (returns a ~2m cube),
# so all measurement goes through pd.bounds / pd.tris which evaluate to a mesh.
try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:          # exec'd from a string (Blender MCP) - no __file__
    _HERE = r"E:\backup-llm\backup-no-llm\3d_engine\ANUMAAN"
exec(open(os.path.join(_HERE, "pd170_lib.py"), encoding="utf-8").read())


def geo_objects():
    return [o for o in bpy.data.objects if o.type in ('MESH', 'CURVE')]


def visible(o):
    return pd.visible(o)


def wbb(o, dg):
    b = pd.bounds(o, dg)
    return b if b else (Vector(), Vector(), Vector())


def tri_count(o, dg):
    return pd.tris(o, dg)


def find(pattern, vis_only=True):
    out = []
    for o in geo_objects():
        if pattern.lower() in o.name.lower():
            if vis_only and not visible(o):
                continue
            out.append(o)
    return out


# ---------------------------------------------------------------- spec
# (tar_id, match pattern, min count, expected size mm (x,y,z) or None, material or None)
SPEC = [
    # 3.1 gearbox / prop drive
    ("1.01", "Gearbox_Housing",            1, (336, 187, 330), "M_CastAluminium"),
    ("1.02", "Gearbox_FrontCover",         1, (230, 16, 228),  "M_CastAluminium"),
    ("1.03", "Gearbox_Ribs",               1, None,            "M_CastAluminium"),
    ("1.04", "GBCover_Bolt_",             22, None,            "M_Steel"),
    ("1.05", "Gearbox_PropBoss",           1, (120, 46, 120),  "M_CastAluminium"),
    ("1.06", "Prop_Flange",                1, (142, 100, 142), None),
    ("1.08", "Gearbox_Governor",           1, None,            None),
    ("1.10", "Governor_Port_Cap",          1, None,            "M_YellowPoly"),
    ("1.11", "Gearbox_Sight_Glass",        1, None,            None),
    ("1.14", "Gearbox_Inspection_Cover",   1, None,            None),
    ("1.15", "Gearbox_Data_Plate",         1, None,            None),
    # 3.2 block & head
    ("2.01", "Engine_Block",               1, (340, 450, 245), "M_CastAluminium"),
    ("2.02", "Cylinder_Head",              1, (252, 336, 120), "M_CastAluminium"),
    ("2.03", "Valve_Cover",                1, None,            None),
    ("2.08", "Glow_Plug",                  4, None,            None),
    ("2.09", "Oil_Sump",                   1, None,            None),
    # 3.3 turbos
    ("3.03", "Turbo_HP_CompressorVolute",  1, None,            "M_MachinedAlloy"),
    ("3.04", "Turbo_LP_CompressorVolute",  1, None,            "M_MachinedAlloy"),
    ("3.05", "TurbineVolute",              2, None,            "M_ExhaustHeatTint"),
    ("3.06", "Turbo_Interstage_Duct",      1, None,            None),
    ("3.08", "Wastegate_Actuator_Canister",1, None,            None),
    ("3.09", "Wastegate_Actuator_Red",     1, None,            "M_AnodizedRed"),
    ("3.10", "Wastegate_Rod",              2, None,            "M_Stainless"),
    ("3.11", "VBand",                      4, None,            "M_Stainless"),
    ("3.12", "Oil_Feed_Turbo",             2, None,            "M_BraidedSilver"),
    ("3.14", "Turbo_HP_Inlet_Cap",         1, None,            "M_YellowPoly"),
    # 3.4 exhaust
    ("4.01", "Exhaust_Downpipe",           1, None,            "M_ExhaustHeatTint"),
    ("4.02", "Exhaust_VBand_Clamp",        1, None,            "M_ExhaustHeatTint"),
    ("9.06", "Hose_Fitting_",              8, None,            "M_AnodizedBlue"),
    ("11.07", "Harness_Boot_",            20, None,            "M_YellowPoly"),
    ("8.07", "Dipstick_Tube",              1, None,            "M_Steel"),
    ("5.16", "Belt_Tensioner",             1, None,            "M_SteelDark"),
    ("12.06", "Mount_Isolator_",           4, None,            "M_Rubber"),
    ("6.04", "Connector_Mil_",            10, None,            "M_MachinedAlloy"),
    ("9.04", "Jubilee_Clamp_",             8, None,            "M_Stainless"),
    ("4.03", "Exhaust_Heat_Blanket",       1, None,            None),
    # 3.5 electrical
    ("5.01", "External_Alternator",        2, (135, 215, 132), "M_GoldAnodized"),
    ("5.11", "Starter_09Kw_M_Steel",       1, None,            None),
    ("5.14", "Starter_Battery_Cable",      1, None,            None),
    ("5.15", "Serpentine_Belt",            1, None,            None),
    # 3.6 FADEC
    ("6.07", "Label_EECU",                 1, None,            "M_Labels"),
    # 3.7 fuel
    ("7.01", "Common_Rail_M_Steel",        1, None,            None),
    ("7.02", "Common_Rail_Wire_Tray",      1, None,            "M_YellowPoly"),
    ("7.03", "Injector_",                  4, None,            None),
    ("7.07", "HP_Fuel_Pump",               1, None,            None),
    ("7.11", "Fuel_Filter_ASAK",           1, None,            None),
    # 3.8 lubrication
    ("8.03", "Oil_Cooler_Line",            2, None,            "M_BraidedSilver"),
    ("8.08", "Vacuum_Pump_Drive",          1, None,            None),
    # 3.9 cooling
    ("9.01", "Water_Pump",                 1, None,            None),
    ("9.02", "Thermostat_Housing",         1, None,            None),
    ("9.03", "Coolant_Hose_",              5, None,            "M_BlueSilicone"),
    # 3.10 intake
    ("10.01", "Intake_Manifold",           1, None,            "M_CastAluminium"),
    ("10.05", "Turbo_Silicone_Coupler",    1, None,            "M_BlueSilicone"),
    ("10.06", "Turbo_T_Clamp",             2, None,            "M_Stainless"),
    # 3.11 harness
    ("11.01", "Harness_Spine",             1, None,            "M_PlasticBlack"),
    ("11.02", "Harness_Br_",               5, None,            "M_PlasticBlack"),
    ("11.09", "Harness_P_Clamp",           4, None,            "M_Stainless"),
    # 3.12 flywheel & mounts
    ("12.01", "Flywheel",                  1, None,            None),
    ("12.02", "Starter_Ring_Gear",         1, None,            None),
    ("12.04", "Intermediate_Bellhousing",  1, None,            None),
    ("12.08", "Crank_Sensor_",             2, None,            None),
    # text
    ("T.01",  "Label_ID_Plate",            1, None,            "M_Labels"),
    ("T.02",  "Label_Cyl_Head",            1, None,            "M_Labels"),
    ("T.03",  "Label_Reduction_Gbx",       1, None,            "M_Labels"),
    ("T.04",  "Label_Caution_Hot",         1, None,            "M_Labels"),
    ("T.06",  "Label_Engine_Oil",          1, None,            "M_Labels"),
    ("T.07",  "Label_Harness_Tag",         1, None,            "M_Labels"),
]

MATERIALS = ["M_CastAluminium", "M_MachinedAlloy", "M_CastIron", "M_Stainless", "M_Steel",
             "M_SteelDark", "M_GoldAnodized", "M_YellowPoly", "M_BlueSilicone",
             "M_AnodizedBlue", "M_AnodizedRed", "M_BraidedSilver", "M_BraidedOlive",
             "M_PlasticBlack", "M_MetalPaintedBlack", "M_Rubber", "M_Brass",
             "M_HeatShield", "M_Glass", "M_Labels"]


# ---------------------------------------------------------------- run
def main():
    dg = bpy.context.evaluated_depsgraph_get()
    print("=" * 78)
    print("TEI-PD170 BUILD VERIFICATION")
    print("=" * 78)

    passes, fails, warns = [], [], []

    # --- A. component presence / count / dims / material
    print("\n--- A. COMPONENT AUDIT ---")
    for tid, pat, need, dims, mat in SPEC:
        objs = find(pat)
        got = len(objs)
        if got == 0:
            fails.append("%-6s %-34s MISSING" % (tid, pat))
            continue
        if got < need:
            fails.append("%-6s %-34s count %d < %d" % (tid, pat, got, need))
            continue
        msg = []
        if dims:
            _, _, d = wbb(objs[0], dg)
            act = (d.x * 1000, d.y * 1000, d.z * 1000)
            off = max(abs(a - e) / e for a, e in zip(act, dims) if e > 0)
            if off > TOL:
                msg.append("dim %.0f/%.0f/%.0f vs %d/%d/%d" %
                           (act[0], act[1], act[2], dims[0], dims[1], dims[2]))
        if mat:
            names = set()
            for o in objs:
                names |= {s.material.name for s in o.material_slots if s.material}
            if mat not in names:
                msg.append("material %s not found" % mat)
        if msg:
            warns.append("%-6s %-34s %s" % (tid, pat, "; ".join(msg)))
        else:
            passes.append(tid)

    print("  PASS %d   WARN %d   FAIL %d" % (len(passes), len(warns), len(fails)))
    for f in fails:
        print("   FAIL  " + f)
    for w in warns:
        print("   WARN  " + w)

    # --- B. placeholders still visible
    print("\n--- B. PLACEHOLDER GEOMETRY (<%d tris, visible) ---" % THIN)
    thin = []
    for o in geo_objects():
        if not visible(o) or o.name.startswith("Label_"):
            continue
        n = tri_count(o, dg)
        if n < THIN:
            thin.append((n, o.name))
    thin.sort()
    print("  count: %d" % len(thin))
    for n, nm in thin[:18]:
        print("   %4d  %s" % (n, nm))
    if len(thin) > 18:
        print("   ... and %d more" % (len(thin) - 18))

    # --- C. materials present
    print("\n--- C. MATERIAL LIBRARY ---")
    missing_mat = [m for m in MATERIALS if m not in bpy.data.materials]
    print("  defined %d/%d" % (len(MATERIALS) - len(missing_mat), len(MATERIALS)))
    for m in missing_mat:
        print("   MISSING  " + m)

    # --- D. scene hygiene
    print("\n--- D. SCENE HYGIENE ---")
    dups = [o.name for o in bpy.data.objects if ".00" in o.name]
    print("  .00N duplicate suffixes : %d %s" % (len(dups), dups[:4]))
    unpacked = [i.name for i in bpy.data.images if i.source == 'FILE' and not i.packed_file]
    print("  unpacked images         : %d %s" % (len(unpacked), unpacked[:4]))
    stray = []
    for o in geo_objects():
        if not visible(o):
            continue
        mn, mx, _ = wbb(o, dg)
        if max(abs(v) for v in list(mn) + list(mx)) > ENVELOPE:
            stray.append(o.name)
    print("  objects outside %.1fm     : %d %s" % (ENVELOPE, len(stray), stray[:4]))
    nozero = [o.name for o in geo_objects() if min(abs(v) for v in o.scale) < 1e-6]
    print("  zero-scale objects      : %d" % len(nozero))
    noparent = [o.name for o in geo_objects() if o.parent and o.parent.type == 'EMPTY']
    print("  parented to empties     : %d" % len(noparent))

    # --- F. detached hardware (bolts/clamps must touch something)
    print("\n--- F. DETACHED HARDWARE ---")
    HW = ("Bolt_", "_Bolt", "P_Clamp", "VBand", "V_Band", "Clamp_")
    # anchors: any solid part a fastener could bolt to, incl. small fittings/ports
    ANCHOR_OK = ("Hose_Fitting_", "Fitting", "Boss", "Port", "Neck", "Flange")
    bodies = [o for o in geo_objects()
              if o.type == 'MESH' and visible(o)
              and (tri_count(o, dg) > 200 or any(k in o.name for k in ANCHOR_OK))
              and not any(k in o.name for k in HW)]
    detached = []
    for o in geo_objects():
        if not visible(o) or not any(k in o.name for k in HW):
            continue
        b = pd.bounds(o, dg)
        if not b:
            continue
        c = (b[0] + b[1]) / 2
        reach = max(b[2]) * 0.5 + 0.012        # own size + 12 mm tolerance
        best = 1e9
        for t in bodies:
            try:
                ok, loc, _, _ = t.closest_point_on_mesh(t.matrix_world.inverted() @ c)
            except Exception:
                continue
            if ok:
                best = min(best, ((t.matrix_world @ loc) - c).length)
        if best > reach:
            detached.append((best * 1000, o.name))
    detached.sort(reverse=True)
    print("  detached: %d" % len(detached))
    for d, nm in detached[:12]:
        print("   %6.1f mm  %s" % (d, nm))
    if len(detached) > 12:
        print("   ... and %d more" % (len(detached) - 12))

    # --- E. totals
    print("\n--- E. TOTALS ---")
    tris = sum(tri_count(o, dg) for o in geo_objects() if visible(o))
    print("  visible objects : %d" % len([o for o in geo_objects() if visible(o)]))
    print("  hidden objects  : %d" % len([o for o in geo_objects() if not visible(o)]))
    print("  curves          : %d" % len([o for o in bpy.data.objects if o.type == 'CURVE']))
    print("  evaluated tris  : %d" % tris)
    print("  materials       : %d" % len(bpy.data.materials))
    print("  images          : %d" % len(bpy.data.images))
    print("\n  SPEC COVERAGE   : %d / %d  (%.0f%%)" %
          (len(passes), len(SPEC), 100.0 * len(passes) / len(SPEC)))
    print("=" * 78)


main()
