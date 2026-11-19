"""Read-only scan: every backend module -> LOC, docstring, reachable from server, imported by tests,
mentioned in plan docs. Output CSV + per-package summary."""
import ast, os, re, csv, subprocess, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
files = subprocess.run(["git", "-C", ROOT, "ls-files", "backend"], capture_output=True, text=True).stdout.split()
mods = {}
for f in files:
    if not f.endswith(".py"):
        continue
    mod = f[:-3].replace("/", ".")
    if mod.endswith(".__init__"):
        mod = mod[: -len(".__init__")]
    src = open(os.path.join(ROOT, f), encoding="utf-8", errors="ignore").read()
    try:
        tree = ast.parse(src)
        doc = (ast.get_docstring(tree) or "").strip().split("\n")[0][:110]
    except Exception:
        tree, doc = None, "PARSE ERROR"
    imps = set()
    if tree:
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imps.update(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.module:
                if n.level:
                    base = mod.split(".")[: -n.level] if not f.endswith("__init__.py") else mod.split(".")[: len(mod.split(".")) - n.level + 1]
                    full = ".".join(base + [n.module])
                else:
                    full = n.module
                imps.add(full)
                for a in n.names:
                    imps.add(full + "." + a.name)
    mods[mod] = dict(file=f, loc=src.count("\n"), doc=doc, imports=imps)

names = set(mods)
def resolve(i):
    out = set()
    parts = i.split(".")
    for k in range(len(parts), 0, -1):
        c = ".".join(parts[:k])
        if c in names:
            out.add(c)
            break
    return out

graph = {m: set().union(*[resolve(i) for i in d["imports"]]) if d["imports"] else set() for m, d in mods.items()}
# packages import their parents' __init__ implicitly
def reach(starts):
    seen, st = set(), list(starts)
    while st:
        m = st.pop()
        if m in seen or m not in mods:
            continue
        seen.add(m)
        st.extend(graph[m])
        p = m.rsplit(".", 1)[0]
        if p in mods:
            st.append(p)
    return seen

server = reach([m for m in mods if m.startswith("backend.server")])

# tests
tfiles = subprocess.run(["git", "-C", ROOT, "ls-files", "tests"], capture_output=True, text=True).stdout.split()
test_imports = set()
for f in tfiles:
    if f.endswith(".py"):
        s = open(os.path.join(ROOT, f), encoding="utf-8", errors="ignore").read()
        for m in re.findall(r"(?:from|import)\s+(backend[\w\.]*)", s):
            test_imports |= resolve(m)
tested = reach(test_imports)

plan = ""
for p in ["ANUMAAN_AUDIT_REPORT.txt", "ANUMAAN_COMPONENTS_ADDENDUM.txt", "ANUMAAN_ROADMAP_AND_PS_COVERAGE.txt", "ANUMAAN_AI_COURSE_OF_ACTION.txt"]:
    plan += open(os.path.join(ROOT, p), encoding="utf-8").read()

out = os.path.join(ROOT, "docs", "cleanup", "subsystem_scan_latest.csv")
rows = []
for m, d in sorted(mods.items()):
    short = m.replace("backend.", "")
    leaf = short.split(".")[-1]
    in_plan = (d["file"] in plan) or (short.replace(".", "/") + ".py" in plan) or (re.search(r"\b" + re.escape(leaf) + r"\.py\b", plan) is not None)
    rows.append([m, d["loc"], m in server, m in tested, in_plan, d["doc"]])
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["module", "loc", "server_reachable", "tested", "in_plan", "doc"])
    w.writerows(rows)

pk = collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0])
for m, loc, sv, te, ip, _ in rows:
    p = m.split(".")[1] if m.count(".") >= 1 else m
    a = pk[p]
    a[0] += 1; a[1] += loc; a[2] += sv; a[3] += te; a[4] += ip; a[5] += (not sv and not ip)
print(f"{'package':16} mods   loc  server tested inplan  unreached&unplanned")
for p, a in sorted(pk.items(), key=lambda x: -x[1][1]):
    print(f"{p:16} {a[0]:4} {a[1]:6} {a[2]:6} {a[3]:6} {a[4]:6}  {a[5]:4}")
print("total modules", len(rows), "server-reachable", sum(r[2] for r in rows), "in plan", sum(r[4] for r in rows))
print("\nNOT IN PLAN (module, loc, server, tested, doc):")
for r in rows:
    if not r[4] and r[1] > 40:
        print(f"  {r[0]:52} {r[1]:5} {'S' if r[2] else '-'}{'T' if r[3] else '-'}  {r[5][:80]}")
