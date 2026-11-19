"""Check that every repo path referenced by scripts/launchers/*.bat exists (P0-05 done-when check)."""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
missing = 0
for path in sorted(glob.glob(os.path.join(ROOT, "scripts", "launchers", "*.bat"))):
    text = open(path, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r'%ROOT%([^"\s%]+)', text):
        rel = m.group(1).replace("\\", "/").rstrip(".")
        if rel and not os.path.exists(os.path.join(ROOT, rel)):
            print("MISSING", os.path.basename(path), rel)
            missing += 1
    for m in re.finditer(r"%~dp0(launch_\w+\.bat)", text):
        if not os.path.exists(os.path.join(ROOT, "scripts", "launchers", m.group(1))):
            print("MISSING sibling", os.path.basename(path), m.group(1))
            missing += 1
    if 'set "ROOT=%~dp0..\\..\\"' not in text:
        print("NO ROOT DEFINITION", os.path.basename(path))
        missing += 1
print("problems:", missing)
