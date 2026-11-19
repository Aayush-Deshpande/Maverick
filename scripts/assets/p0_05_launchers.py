"""Card P0-05: move launch_*.bat into scripts/launchers/ and keep them working (moves + path fixes only, D21).

After the move %~dp0 points at scripts\\launchers\\, so every repo path uses ROOT=%~dp0..\\..\\ instead.
Calls to sibling launchers keep %~dp0 (same folder). Also fixes audit #64 (missing AE300 .blend path) and the
cwd-relative path in launch_rotax_914_cad.bat.
"""
import glob
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEST = os.path.join(ROOT, "scripts", "launchers")
os.makedirs(DEST, exist_ok=True)

for src in sorted(glob.glob(os.path.join(ROOT, "launch_*.bat"))):
    name = os.path.basename(src)
    subprocess.run(["git", "-C", ROOT, "mv", name, f"scripts/launchers/{name}"], check=True)
    path = os.path.join(DEST, name)
    raw = open(path, "rb").read()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8", errors="surrogateescape").replace("\r\n", "\n")

    text = text.replace("%~dp0launch_", "@@SIBLING@@")
    has_root = 'set "ROOT=%~dp0"' in text
    text = text.replace('set "ROOT=%~dp0"', "@@ROOTDEF@@")
    text = text.replace("%~dp0", "%ROOT%").replace("@@SIBLING@@", "%~dp0launch_")
    if has_root:
        text = text.replace("@@ROOTDEF@@", 'set "ROOT=%~dp0..\\..\\"')
    else:
        lines = text.split("\n")
        insert_at = 1 if lines and lines[0].strip().lower().startswith("@echo off") else 0
        lines.insert(insert_at, 'set "ROOT=%~dp0..\\..\\"')
        text = "\n".join(lines)

    if name == "launch_rotax_914_cad.bat":
        text = text.replace('"assets\\blender\\rotax_914.blend"', '"%ROOT%assets\\blender\\rotax_914.blend"')
    if name == "launch_austro_ae300_cad.bat":
        # audit #64: assets/blender/austro_ae300.blend never existed; the AE300 model file is the AE330-shaped one
        text = text.replace("%ROOT%assets\\blender\\austro_ae300.blend", "%ROOT%assets\\models\\engines\\austro_ae330.blend")

    if crlf:
        text = text.replace("\n", "\r\n")
    open(path, "wb").write(text.encode("utf-8", errors="surrogateescape"))
    print("moved + fixed:", name)
