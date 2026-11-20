"""Inventory before moving anything (card P0-03, safety net for T-REPO-1).

Lists every git-tracked file plus every untracked/ignored asset file (.blend, .blend1, .glb, .gltf, .stp, .fbx,
.rar, .exr) with size and md5. Output CSV: path, size_bytes, md5, tracked (yes/no).
Usage: python scripts/assets/inventory.py [output.csv]   (default docs/cleanup/inventory_before.csv)
"""
import csv
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "cleanup", "inventory_before.csv")
ASSET_EXT = (".blend", ".blend1", ".glb", ".gltf", ".stp", ".step", ".fbx", ".rar", ".exr")
SKIP_DIRS = {".git", "node_modules", "dist", "__pycache__", ".pytest_cache", "graphify-out", ".playwright-mcp"}


def md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


tracked = [f for f in subprocess.run(["git", "-C", ROOT, "ls-files", "-z"], capture_output=True).stdout.decode("utf-8", "replace").split("\0") if f]
tracked_set = set(tracked)
extra = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for name in filenames:
        if name.lower().endswith(ASSET_EXT):
            rel = os.path.relpath(os.path.join(dirpath, name), ROOT).replace("\\", "/")
            if rel not in tracked_set:
                extra.append(rel)

rows = []
for rel, is_tracked in [(f, "yes") for f in tracked] + [(f, "no") for f in sorted(extra)]:
    p = os.path.join(ROOT, rel)
    if os.path.isfile(p):
        rows.append((rel, os.path.getsize(p), md5(p), is_tracked))
    else:
        rows.append((rel, "", "MISSING_ON_DISK", is_tracked))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["path", "size_bytes", "md5", "tracked"])
    w.writerows(rows)

missing = sum(1 for r in rows if r[2] == "MISSING_ON_DISK")
print(f"tracked: {len(tracked)}  untracked assets: {len(extra)}  rows: {len(rows)}  missing on disk: {missing}")
print(f"written: {os.path.relpath(OUT, ROOT)}")
