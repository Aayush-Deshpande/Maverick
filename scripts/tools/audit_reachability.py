"""
Reachability audit -- which Python modules are LIVE, HARNESS/TEST-only, or DEAD?

Static (AST) import graph over backend/, apps/, scripts/, tests/.  Roots:
  LIVE     backend.server.main            (the FastAPI app: what the demo runs)
  HARNESS  backend.evaluation.harness, experiments/*.py
  TESTS    tests/*.py
A module is DEAD if nothing in any root's transitive import closure reaches it and it is not
itself a script/entry point (has `if __name__ == "__main__"` or lives in scripts/apps).

Limits (be honest): dynamic imports (importlib, string names), `python -m` launches from .bat
files and Blender-side scripts are not traced; treat "DEAD" as "nothing in the repo imports
it -- verify, then delete", not as proof.

Run:  python scripts/tools/audit_reachability.py [--json out.json]
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCAN = ["backend", "apps", "scripts", "tests", "experiments"]


def module_name(path: Path) -> str:
    rel = path.relative_to(REPO).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def collect():
    files = {}
    for top in SCAN:
        for p in (REPO / top).rglob("*.py"):
            if "__pycache__" in p.parts or "node_modules" in p.parts:
                continue
            files[module_name(p)] = p
    return files


def imports_of(path: Path, mod: str, known: set[str]) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    is_pkg = path.name == "__init__.py"
    out: set[str] = set()

    def add(name: str):
        # add the module and every known parent package
        parts = name.split(".")
        for i in range(len(parts), 0, -1):
            cand = ".".join(parts[:i])
            if cand in known:
                out.add(cand)
                break

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = mod.split(".")
                base = base if is_pkg else base[:-1]
                base = base[: len(base) - (node.level - 1)] if node.level > 1 else base
                prefix = ".".join(base + ([node.module] if node.module else []))
            else:
                prefix = node.module or ""
            if prefix:
                add(prefix)
            for a in node.names:
                add(f"{prefix}.{a.name}" if prefix else a.name)
    out.discard(mod)
    return out


def closure(roots, graph):
    seen, stack = set(), [r for r in roots if r in graph]
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        stack.extend(graph.get(m, ()))
    return seen


def main():
    files = collect()
    known = set(files)
    graph = {m: imports_of(p, m, known) for m, p in files.items()}

    live = closure(["backend.server.main"], graph)
    harness = closure(["backend.evaluation.harness"] + [m for m in files if m.startswith("experiments.")], graph)
    tests = closure([m for m in files if m.startswith("tests.")], graph)

    def is_entry(m):
        p = files[m]
        if m.startswith(("scripts.", "apps.", "experiments.", "tests.")):
            return True
        try:
            return "__main__" in p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False

    rows = {"LIVE": [], "HARNESS_ONLY": [], "TEST_ONLY": [], "ORPHAN_LIBRARY": [], "SCRIPT_OR_ENTRY": []}
    for m in sorted(m for m in files if m.startswith("backend.") and files[m].name != "__init__.py"):
        n = files[m].read_text(encoding="utf-8", errors="replace").count("\n")
        if m in live:
            rows["LIVE"].append((m, n))
        elif m in harness:
            rows["HARNESS_ONLY"].append((m, n))
        elif m in tests:
            rows["TEST_ONLY"].append((m, n))
        elif is_entry(m):
            rows["SCRIPT_OR_ENTRY"].append((m, n))
        else:
            rows["ORPHAN_LIBRARY"].append((m, n))

    # scripts / apps: who imports them (anything)?
    imported_by = {m: [k for k, v in graph.items() if m in v and k != m] for m in files}
    unref_scripts = sorted((m, files[m].read_text(encoding="utf-8", errors="replace").count("\n"))
                           for m in files if m.startswith(("scripts.", "apps.")) and not imported_by[m])

    summary = {k: {"modules": len(v), "lines": sum(n for _, n in v)} for k, v in rows.items()}
    for k, v in rows.items():
        print(f"\n== {k}: {summary[k]['modules']} modules, {summary[k]['lines']} lines")
        for m, n in v:
            print(f"   {n:5d}  {m}")
    print(f"\n== scripts/apps not imported by anything (entry points or dead; check launchers/docs): {len(unref_scripts)}")
    for m, n in unref_scripts:
        print(f"   {n:5d}  {m}")

    if "--json" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--json") + 1])
        out.write_text(json.dumps({"summary": summary, **{k: v for k, v in rows.items()},
                                   "unreferenced_scripts": unref_scripts}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
