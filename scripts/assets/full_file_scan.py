"""Read-only scan of EVERY git-tracked file for common defects.

Writes docs/cleanup/full_file_scan_latest.csv (one row per finding) and prints a summary.
Run from anywhere: python scripts/assets/full_file_scan.py
"""
import ast
import csv
import json
import os
import re
import subprocess
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "cleanup", "full_file_scan_latest.csv")
SKIP_PREFIX = ("web/usavionix/",)  # third-party/own mirror moved out in P0-04 (D27)

files = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"], capture_output=True).stdout.decode("utf-8", "replace").split("\0")
files = [f for f in files if f and not f.startswith(SKIP_PREFIX)]

findings = []


def add(path, kind, line, detail):
    findings.append((kind, path, line, detail[:200]))


TEXT_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".bat", ".ps1", ".sh", ".md", ".txt", ".json", ".yaml",
            ".yml", ".toml", ".ini", ".html", ".css", ".dbc", ".cfg"}
CODE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".bat", ".ps1", ".sh"}
PRODUCT_DIRS = ("backend/", "frontend/src/", "apps/", "docs_site/src/")

re_abs = re.compile(r"(?<![A-Za-z])[CDE]:[\\/](?:Users|Programming|backup|Blender|AI|ANUMAAN)[^\s\"'`)]*", re.I)
re_url = re.compile(r"https?://[^\s\"'`)<>]+")
re_secret = re.compile(r"(AIza[0-9A-Za-z_\-]{30,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|api[_-]?key\s*[:=]\s*[\"'][A-Za-z0-9_\-]{16,}[\"'])", re.I)
re_todo = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
re_jsrand = re.compile(r"Math\.random\s*\(")
re_pyrand = re.compile(r"\brandom\.(random|gauss|uniform|randint|choice)\s*\(|np\.random\.(rand|randn|normal|uniform)\s*\(")
re_except_pass = re.compile(r"except(\s+Exception)?\s*(as\s+\w+)?\s*:\s*\n\s*pass\b")
re_mdlink = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
re_host = re.compile(r"(onrender\.com|ngrok|trycloudflare|vercel\.app|localhost:\d+|127\.0\.0\.1:\d+)")

sizes = collections.Counter()
for f in files:
    p = os.path.join(ROOT, f)
    if not os.path.isfile(p):
        add(f, "MISSING_ON_DISK", 0, "tracked but not present (LFS pointer or deleted)")
        continue
    size = os.path.getsize(p)
    ext = os.path.splitext(f)[1].lower()
    sizes[f.split("/")[0]] += size
    if size == 0:
        add(f, "EMPTY_FILE", 0, "0 bytes")
    if size > 50 * 1024 * 1024:
        add(f, "HUGE_FILE", 0, f"{size/1e6:.1f} MB")
    if ext not in TEXT_EXT or size > 3 * 1024 * 1024:
        continue
    try:
        text = open(p, encoding="utf-8").read()
    except UnicodeDecodeError:
        text = open(p, encoding="utf-8", errors="replace").read()
    if text.startswith("version https://git-lfs"):
        continue
    lines = text.split("\n")
    is_product = f.startswith(PRODUCT_DIRS)
    if ext == ".py":
        try:
            ast.parse(text)
        except SyntaxError as e:
            add(f, "PY_SYNTAX_ERROR", e.lineno or 0, str(e.msg))
        for m in re_except_pass.finditer(text):
            add(f, "SWALLOWED_EXCEPTION", text[: m.start()].count("\n") + 1, "except ...: pass")
    if ext == ".json":
        try:
            json.loads(text)
        except Exception as e:
            add(f, "JSON_INVALID", 0, str(e))
    for i, line in enumerate(lines, 1):
        if ext in CODE_EXT or ext in {".json", ".yaml", ".yml", ".toml", ".ini", ".html"}:
            for m in re_abs.finditer(line):
                add(f, "ABS_LOCAL_PATH", i, m.group(0))
            if re_secret.search(line):
                add(f, "POSSIBLE_SECRET", i, "pattern match (value not shown)")
            if is_product and re_host.search(line):
                add(f, "HARDCODED_HOST", i, re_host.search(line).group(0))
        if ext in CODE_EXT and re_todo.search(line):
            add(f, "TODO_FIXME", i, line.strip())
        if is_product and ext in {".ts", ".tsx", ".js", ".jsx"} and re_jsrand.search(line):
            add(f, "RANDOM_IN_PRODUCT_UI", i, line.strip())
        if is_product and ext == ".py" and re_pyrand.search(line) and "rng" not in line:
            add(f, "RANDOM_IN_PRODUCT_PY", i, line.strip())
    if ext == ".md":
        d = os.path.dirname(p)
        for i, line in enumerate(lines, 1):
            for m in re_mdlink.finditer(line):
                target = m.group(1)
                if target.startswith(("http", "mailto:", "/")) or "{" in target:
                    continue
                if not os.path.exists(os.path.normpath(os.path.join(d, target))):
                    add(f, "DEAD_DOC_LINK", i, target)
    if ext == ".bat":
        for i, line in enumerate(lines, 1):
            for m in re.finditer(r"%~dp0([\w\\/.\-]+)", line):
                rel = m.group(1).replace("\\", "/").rstrip(".")
                if rel and not os.path.exists(os.path.join(ROOT, os.path.dirname(f), rel)):
                    add(f, "BAT_MISSING_PATH", i, rel)

# duplicate code/doc files by content (text only)
import hashlib
by_hash = collections.defaultdict(list)
for f in files:
    p = os.path.join(ROOT, f)
    if os.path.isfile(p) and os.path.splitext(f)[1].lower() in TEXT_EXT and os.path.getsize(p) > 200:
        by_hash[hashlib.md5(open(p, "rb").read()).hexdigest()].append(f)
for h, fs in by_hash.items():
    if len(fs) > 1:
        add(fs[0], "DUPLICATE_TEXT_FILE", 0, " == ".join(fs[1:6]))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["kind", "path", "line", "detail"])
    w.writerows(sorted(findings))

print(f"files scanned: {len(files)}")
cnt = collections.Counter(k for k, *_ in findings)
for k, n in cnt.most_common():
    print(f"  {k:24} {n}")
print("\nbytes by top folder (MB):", {k: round(v / 1e6, 1) for k, v in sizes.most_common(12)})
