"""Card P0-06: assets layout per P Part 5.2/5.3 with md5 registers. No .blend is deleted (D1); duplicates go to
assets/blender/_archive/ (D25: rotax_914_f.blend has identical content to rotax_914.blend, checked headless).

Steps: register md5s -> git mv -> rewrite references in code/launchers (every path style) -> report leftovers.
Re-running is safe: moves whose source is gone are skipped.
"""
import csv
import datetime
import glob
import hashlib
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TODAY = datetime.date.today().isoformat()
E = "assets/blender/engines"

MOVES = [  # (old, new, reason)
    ("assets/blender/rotax_912_is_sport.blend", f"{E}/rotax_912is/rotax_912is.blend", "MASTER 912 iS Sport (D47)"),
    ("assets/blender/rotax_912is_showcase.blend", f"{E}/rotax_912is/variants/rotax_912is_showcase.blend", "variant"),
    ("assets/blender/rotax_914.blend", f"{E}/rotax_914/rotax_914.blend", "MASTER 914 (D25)"),
    ("assets/blender/rotax_914_showcase.blend", f"{E}/rotax_914/variants/rotax_914_showcase.blend", "variant"),
    ("assets/blender/rotax_914_f.blend", "assets/blender/_archive/rotax_914_f.blend",
     "same content as rotax_914.blend (594 objects, 490617 triangles, same names; D25)"),
    ("assets/blender/rotax_915is.blend", f"{E}/rotax_915is/rotax_915is.blend", "MASTER 915 iS"),
    ("assets/blender/rotax_915is_showcase.blend", f"{E}/rotax_915is/variants/rotax_915is_showcase.blend", "variant"),
    ("assets/blender/rotax_915.blend", "assets/blender/_archive/rotax_915.blend", "byte-identical to rotax_915is.blend"),
    ("assets/models/Rotax_915.FBX", f"{E}/rotax_915is/import/Rotax_915.FBX", "source import"),
    ("assets/models/engines/austro_ae330.blend", f"{E}/austro_ae300/austro_ae300.blend",
     "MASTER AE300 (AE330-shaped, representative geometry)"),
    ("assets/models/engines/austro_ae330_lod1.blend", f"{E}/austro_ae300/variants/austro_ae330_lod1.blend", "variant"),
    ("assets/blender/austro_ae300_showcase.blend", f"{E}/austro_ae300/variants/austro_ae300_showcase.blend", "variant"),
    ("assets/blender/vrde_jayem_2_2l.blend", f"{E}/vrde_jayem_2_2l/vrde_jayem_2_2l.blend",
     "MASTER VRDE (TEI PD170 geometry, representative)"),
    ("assets/blender/vrde_jayem_2_2l_showcase.blend", f"{E}/vrde_jayem_2_2l/variants/vrde_jayem_2_2l_showcase.blend", "variant"),
    ("assets/models/engines/tei_pd170.blend", "assets/blender/reference/tei_pd170/tei_pd170.blend", "reference geometry"),
    ("assets/models/engines/tei_pd170_lod1.blend", "assets/blender/reference/tei_pd170/tei_pd170_lod1.blend", "reference"),
    ("assets/models/engines/tei_pd170_lookdev.blend", "assets/blender/reference/tei_pd170/tei_pd170_lookdev.blend", "reference"),
    ("assets/blender/bayraktar_tb3_digital_twin.blend", "assets/blender/airframes/bayraktar_tb3/variants/bayraktar_tb3_digital_twin.blend", "variant"),
    ("assets/models/bayraktar_tb3_digital_twin.blend", "assets/blender/_archive/bayraktar_tb3_digital_twin.blend",
     "byte-identical to the assets/blender copy"),
    ("assets/models/airframes/bayraktar_tb3.blend", "assets/blender/airframes/bayraktar_tb3/bayraktar_tb3.blend", "airframe"),
    ("assets/models/terrain.blend", "assets/blender/terrain/terrain_N34E077.blend", "Copernicus N34 E077 terrain"),
    ("assets/blender/anumaan_master_twin.blend", "assets/blender/scenes/anumaan_master_twin.blend", "multi-engine scene"),
    ("assets/models/engine-rotax-912is-1.snapshot.15", f"{E}/rotax_912is/import/cad", "CAD source (stp/rar)"),
    ("assets/models/engine-rotax-914-1.snapshot.2", f"{E}/rotax_914/import/cad", "CAD source (stp/rar)"),
]

SKIP_REWRITE = ("archive_tracked/", "docs/history/", "docs/build/", "docs/cleanup/", "assets/blender/_archive/")
SKIP_FILES = {"ANUMAAN_AUDIT_REPORT.txt", "ANUMAAN_COMPONENTS_ADDENDUM.txt", "ANUMAAN_ROADMAP_AND_PS_COVERAGE.txt",
              "ANUMAAN_AI_COURSE_OF_ACTION.txt", "DECISIONS.md", "PROGRESS.txt", "scripts/assets/p0_06_assets.py"}
TEXT_EXT = (".py", ".bat", ".ps1", ".json", ".ts", ".tsx", ".js", ".md", ".txt", ".yaml", ".yml", ".html")


def git(*a):
    r = subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


# 1. registers
reg_path = os.path.join(ROOT, "assets", "blender", "_archive", "ARCHIVE_REGISTER.csv")
os.makedirs(os.path.dirname(reg_path), exist_ok=True)
new_reg = not os.path.exists(reg_path)
with open(reg_path, "a", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    if new_reg:
        w.writerow(["date", "card", "old_path", "new_path", "md5", "size_bytes", "reason"])
    for old, new, reason in MOVES:
        p = os.path.join(ROOT, old)
        if os.path.isfile(p):
            w.writerow([TODAY, "P0-06", old, new, md5(p), os.path.getsize(p), reason])
        elif os.path.isdir(p):
            for f in sorted(glob.glob(os.path.join(p, "**", "*"), recursive=True)):
                if os.path.isfile(f):
                    rel = os.path.relpath(f, ROOT).replace("\\", "/")
                    w.writerow([TODAY, "P0-06", rel, new + rel[len(old):], md5(f), os.path.getsize(f), reason])

# 2. moves
done = []
for old, new, reason in MOVES:
    if not os.path.exists(os.path.join(ROOT, old)):
        print("skip (missing):", old)
        continue
    os.makedirs(os.path.dirname(os.path.join(ROOT, new)), exist_ok=True)
    git("mv", old, new)
    done.append((old, new))
    print("moved:", old, "->", new)

# local, untracked Blender backups (never into Git, D42)
for b in glob.glob(os.path.join(ROOT, "assets", "blender", "*.blend1")):
    dst = os.path.join(ROOT, "assets", "blender", "_archive", "blend1_backups", os.path.basename(b))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    os.replace(b, dst)
    print("local backup moved:", os.path.basename(b))

# 3. rewrite references (all path styles: a/b/c, a\\b\\c, "a", "b", "c", "a" / "b" / "c")
SEP = r'(?P<sep>\\\\|[/\\]|"\s*,\s*"|\'\s*,\s*\'|"\s*/\s*"|\'\s*/\s*\')'


def build_regex(parts):
    rx = re.escape(parts[0])
    for i, part in enumerate(parts[1:]):
        rx += (SEP if i == 0 else r"(?P=sep)") + re.escape(part)
    return re.compile(r"(?<![\w.-])" + rx + r"(?![\w])")


changed = {}
files = [f for f in git("ls-files").splitlines() if f.endswith(TEXT_EXT) and not f.startswith(SKIP_REWRITE) and f not in SKIP_FILES]
for old, new in done:
    rx = build_regex(old.split("/"))
    new_parts = new.split("/")
    for f in files:
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p):
            continue
        s = open(p, encoding="utf-8", errors="surrogateescape").read()
        s2 = rx.sub(lambda m: m.group("sep").join(new_parts), s)
        if s2 != s:
            open(p, "w", encoding="utf-8", errors="surrogateescape", newline="").write(s2)
            changed[f] = changed.get(f, 0) + 1
for f, n in sorted(changed.items()):
    print(f"rewrote {n} path(s) in {f}")

# 4. leftovers: old file names still mentioned in code/launchers
left = 0
for old, _ in done:
    name = old.split("/")[-1]
    for f in files:
        p = os.path.join(ROOT, f)
        if os.path.isfile(p) and f.endswith((".py", ".bat", ".ps1", ".ts", ".tsx", ".js")):
            for i, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
                if re.search(r"(?<![\w.-])" + re.escape(name) + r"(?![\w])", line) and old.split("/")[0] in line:
                    print(f"LEFTOVER {f}:{i}: {line.strip()[:140]}")
                    left += 1
print("leftovers:", left)
