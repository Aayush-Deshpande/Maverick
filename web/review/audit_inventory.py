"""Read-only project inventory and structural source index for the review."""
from pathlib import Path
from collections import Counter
import ast
import json
import os

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SKIP = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', '.pytest_cache', '.codex', '.claude', '.vscode'}
files = []
sources = []
for folder, dirs, names in os.walk(ROOT):
    dirs[:] = sorted(d for d in dirs if d not in SKIP and not (Path(folder) / d).is_symlink())
    for name in sorted(names):
        p = Path(folder) / name
        if p.is_symlink() or name.startswith('.env') or OUT in p.parents:
            continue
        rel = p.relative_to(ROOT).as_posix()
        try:
            size = p.stat().st_size
        except OSError:
            continue
        files.append({'path': rel, 'bytes': size, 'extension': p.suffix.lower()})
        first = rel.split('/')[0]
        include = (first == 'backend' and p.suffix == '.py') or rel.startswith('frontend/src/') or (first in {'tests', 'experiments', 'scripts'} and p.suffix == '.py')
        if not include:
            continue
        src = p.read_text(encoding='utf-8', errors='replace')
        rec = {'path': rel, 'lines': len(src.splitlines())}
        if p.suffix == '.py':
            try:
                tree = ast.parse(src)
                rec['purpose'] = (ast.get_docstring(tree) or '').split('\n\n')[0][:800]
                rec['symbols'] = [{'name': n.name, 'line': n.lineno, 'kind': type(n).__name__} for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]
                rec['imports'] = sorted({n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module})
                rec['syntax'] = 'parsed'
            except SyntaxError as exc:
                rec['syntax'] = str(exc)
        sources.append(rec)
summary = {'root': str(ROOT), 'files': len(files), 'bytes': sum(f['bytes'] for f in files), 'by_area': dict(Counter(f['path'].split('/')[0] for f in files)), 'indexed_sources': len(sources), 'scope': 'File metadata plus structural source indexing; not a semantic review of every dataset, asset, dependency, or archived file.'}
(OUT / 'file-inventory.json').write_text(json.dumps({'summary': summary, 'files': files}, indent=2), encoding='utf-8')
(OUT / 'source-index.json').write_text(json.dumps(sources, indent=2), encoding='utf-8')
lines = ['# Source index', '', 'Structural index only. Deep review evidence is in PROJECT_REVIEW.md.', '']
for s in sources:
    lines += [f"## {s['path']} ({s['lines']} lines)", '', s.get('purpose', 'Frontend source / stylesheet.'), '', ', '.join(f"{x['name']}:{x['line']}" for x in s.get('symbols', [])), '']
(OUT / 'SOURCE_INDEX.md').write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps(summary, indent=2))
