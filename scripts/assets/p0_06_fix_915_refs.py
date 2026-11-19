"""P0-06 follow-up: references that pointed at rotax_915.blend now use the 915 iS master (the archived copy is
byte-identical, but tools and launchers should open the master)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXES = {
    "scripts/launchers/launch_rotax_915_cad.bat": [
        (r"assets\blender\_archive\rotax_915.blend", r"assets\blender\engines\rotax_915is\rotax_915is.blend")],
    "scripts/tools/build_master_twin_blend.py": [
        ('"assets", "blender", "_archive", "rotax_915.blend"', '"assets", "blender", "engines", "rotax_915is", "rotax_915is.blend"')],
    "scripts/tools/update_master_twin.py": [
        ('"assets" / "blender" / "_archive" / "rotax_915.blend"', '"assets" / "blender" / "engines" / "rotax_915is" / "rotax_915is.blend"')],
}
for rel, reps in FIXES.items():
    p = os.path.join(ROOT, rel)
    s = open(p, encoding="utf-8", errors="surrogateescape", newline="").read()
    for a, b in reps:
        if a in s:
            s = s.replace(a, b)
            print("fixed", rel)
        else:
            print("already fixed or not found:", rel)
    open(p, "w", encoding="utf-8", errors="surrogateescape", newline="").write(s)
