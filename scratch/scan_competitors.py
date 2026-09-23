import os
import json
import glob

competitors_dir = r"e:\backup-llm\backup-no-llm\3d_engine\competitors"

summary = {}

for author in os.listdir(competitors_dir):
    author_path = os.path.join(competitors_dir, author)
    if not os.path.isdir(author_path):
        continue
    for project in os.listdir(author_path):
        proj_path = os.path.join(author_path, project)
        if not os.path.isdir(proj_path):
            continue
        
        rel_key = f"{author}/{project}"
        
        # Check files
        files = []
        for root, dirs, fnames in os.walk(proj_path):
            # ignore .git, node_modules, venv
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'venv', '__pycache__', '.pytest_cache']]
            for fn in fnames:
                files.append(os.path.relpath(os.path.join(root, fn), proj_path))
        
        # Check readme
        readme_snippet = ""
        for r_name in ['README.md', 'readme.md', 'README.txt', 'Readme.md']:
            r_path = os.path.join(proj_path, r_name)
            if os.path.exists(r_path):
                try:
                    with open(r_path, 'r', encoding='utf-8', errors='ignore') as rf:
                        readme_snippet = rf.read(1500)
                except Exception:
                    pass
                break
                
        # Detect techs
        tech = []
        if any('package.json' in f for f in files):
            tech.append('Node/JS')
        if any('requirements.txt' in f or 'pyproject.toml' in f or f.endswith('.py') for f in files):
            tech.append('Python')
        if any('three' in f.lower() or f.endswith('.glb') or f.endswith('.gltf') or f.endswith('.blend') for f in files):
            tech.append('3D/WebGL')
        if any('socketcan' in f.lower() or 'can' in f.lower() for f in files):
            tech.append('CAN-bus')
        if any('mavlink' in f.lower() for f in files):
            tech.append('MAVLink')
            
        summary[rel_key] = {
            'total_files': len(files),
            'sample_files': files[:15],
            'tech_tags': tech,
            'readme_preview': readme_snippet[:300].replace('\n', ' ')
        }

with open(r"scratch\competitors_overview.json", "w", encoding="utf-8") as out_f:
    json.dump(summary, out_f, indent=2)

print(f"Scanned {len(summary)} competitor projects.")
