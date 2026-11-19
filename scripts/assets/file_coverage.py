"""Coverage manifest: map EVERY file in the working tree (tracked + untracked, plus ignored folders as groups)
to the plan item that handles it. Any file no rule matches is printed as UNCOVERED and must get a rule.

Output: docs/cleanup/file_coverage_latest.csv  (path, status, rule_id, plan_reference)
Run: python scripts/assets/file_coverage.py
"""
import csv
import fnmatch
import os
import subprocess
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "cleanup", "file_coverage_latest.csv")

# Ordered rules: first match wins. (rule_id, glob patterns, plan reference)
RULES = [
    ("ai-instructions", ["AGENTS.md", "CLAUDE.md", "DECISIONS.md", "PROGRESS.txt", "*/AGENTS.md", "*/CLAUDE.md"],
     "Course of action 0.1, P0-01 (commit), D15"),
    ("plan-docs", ["ANUMAAN_AUDIT_REPORT.txt", "ANUMAAN_COMPONENTS_ADDENDUM.txt", "ANUMAAN_ROADMAP_AND_PS_COVERAGE.txt",
                   "ANUMAAN_AI_COURSE_OF_ACTION.txt"], "P0-01"),
    ("submitted-texts", ["ANUMAAN_Idea_Description.txt", "ANUMAAN_Abstract_Summary.txt"], "P0-04 -> docs/submission/; section 15"),
    ("root-screenshots", ["*.png"], "P0-04 -> docs/screenshots/"),
    ("launchers", ["launch_*.bat"], "P0-05 -> scripts/launchers/ (+ audit #63/#64)"),
    ("root-config", ["Dockerfile", ".dockerignore", "render.yaml", "railway.json", "firebase.json", ".firebaserc",
                     "pytest.ini", "requirements.txt", "requirements-server.txt", "run_app.py", ".env.example",
                     ".gitignore", ".gitattributes", "README.md"], "KEEP at root (4.1); run_app.py Blender path #63; README P0-08"),
    ("gitmodules", [".gitmodules"], "P0-04 git rm (D26)"),
    ("crazy-landing", ["web/Crazy_Landing/*", "web/usavionix/*"], "D42: git mv to archive_tracked/crazy_landing/ (P0-04)"),
    ("web-site", ["web/*"], "web/AGENTS.md; P0-07 single GLB set; sim-engine.js labelled ILLUSTRATION (P Part 0 D1)"),
    ("rag-fabricated", ["data/documents/*"], "D34: archive_tracked/synthetic_rag_corpus (P0-04); AI-03a real corpus"),
    ("missions-generated", ["data/missions/*"], "D35: label SIMULATION (M4-07)"),
    ("graph-runtime", ["data/graph_db/*"], "M0-11 -> var/ + seed file"),
    ("data-telemetry", ["data/telemetry/*"], "data/AGENTS.md; replay converter M5-05; C-MAPSS M4-07"),
    ("data-other", ["data/*"], "data/AGENTS.md; mission_reports/knowledge sources (AI-03); P0-04 Datasets merge"),
    ("datasets-folder", ["Datasets/*"], "P0-04 -> data/external/ (download scripts path fix)"),
    ("updated-report", ["UpdatedReport/*"], "P0-04 -> docs/history/UpdatedReport/ (D17)"),
    ("final-touch", ["final_touch/*"], "P0-04 -> docs/history/final_touch/ (D17)"),
    ("experiments", ["experiments/*"], "P0-04 -> archive_tracked/experiments/ (grep first)"),
    ("vendor", ["vendor/*"], "KEEP + vendor/README.txt (4.1); cloudflared/ngrok exes in LFS (#67)"),
    ("cleanup-reports", ["docs/cleanup/*"], "P0-03 inventory + scans (D37)"),
    ("docs-build-history", ["docs/build/*"], "D17 history"),
    ("docs-ps", ["docs/00_official_problem_statement.md"], "M8-05 (dead links N2, claims N3)"),
    ("docs-reference", ["docs/reference/*"], "AI-03a real RAG corpus; engine data refs (D16)"),
    ("docs-study-zip", ["docs/study.zip"], "D42: git mv to archive_tracked/docs_study_zip/"),
    ("docs-other", ["docs/*"], "docs/AGENTS.md; rewritten/regenerated in M8-05; claims #59"),
    ("docs-site-content", ["docs_site/technical/*", "docs_site/journey/*", "docs_site/*.md"], "M8-05 (EKF wording D19, claims #59)"),
    ("docs-site-png", ["docs_site/*.png"], "P0-04 -> docs/screenshots/docs_site/"),
    ("docs-site-models", ["docs_site/public/assets/models/*"], "P0-07 single GLB set"),
    ("docs-site-app", ["docs_site/*"], "docs_site/AGENTS.md; MermaidDiagram ids (Math.random ok for DOM ids)"),
    ("frontend-landing", ["frontend/src/components/landing/*"], "audit #58 (fake live numbers/claims) -> M6 / UX"),
    ("frontend-models", ["frontend/public/models/*", "frontend/public/draco/*"], "P0-07 single GLB set; #68 one Draco copy"),
    ("frontend-src", ["frontend/src/*"], "M0-09 store, M6 views; hosts #62"),
    ("frontend-config", ["frontend/*"], "frontend/AGENTS.md (build config; vite publicDir P0-07)"),
    ("threejs-twin", ["apps/threejs_twin/*"], "M0-10 minimal, retire D10 (M6-05); uncompressed GLBs P0-07"),
    ("blender-apps", ["apps/blender_twin/*"], "M0-10, M5-10, #60/#61"),
    ("desktop-gcs", ["apps/desktop_gcs/*"], "ASK at M8-02 (section 4.4)"),
    ("graph-viewer", ["apps/mission_graph_viewer/*"], "KEEP optional tool, reads var/graph_db (section 4.4)"),
    ("assets-blend", ["assets/*.blend", "assets/*/*.blend", "assets/*/*/*.blend"], "P0-06 layout (D1, D25), Phase 7"),
    ("assets-cad", ["assets/models/engine-rotax-*"], "P0-06 -> assets/blender/engines/*/import/cad/ (#67)"),
    ("assets-glb", ["assets/models/*.glb", "assets/models/draco/*", "assets/models/airframes/*", "assets/models/*.FBX"], "P0-06/P0-07"),
    ("assets-manifests", ["assets/manifests/*"], "M0-03 component manifests (configs/components supersedes)"),
    ("assets-images", ["assets/model_images/*", "assets/renders/*", "assets/textures/*"], "P0-06 register; reference images only; #68/#69"),
    ("assets-blender-other", ["assets/blender/*"], "P0-06"),
    ("assets-other", ["assets/*"], "P0-06 register"),
    ("configs", ["configs/*"], "configs/AGENTS.md; M0-01/02/03, M7-01 (DBC), MAVLink dialect (#62)"),
    ("tests-legacy", ["tests/test_analytical_pipeline.py", "tests/test_canonical_runtime_pipeline.py",
                      "tests/test_causal_propagation.py", "tests/test_engine_agnostic_ratchet.py",
                      "tests/test_fun_req_compliance.py", "tests/test_independent_plant_adapter.py",
                      "tests/test_no_truth_leak.py", "tests/test_physics_and_telemetry.py", "tests/test_server_api.py"],
     "D38 port in M0-07/M0-08/M3-07 (#66)"),
    ("tests", ["tests/*"], "tests/AGENTS.md; baseline 333/3/7/1"),
    ("scripts-generators", ["scripts/build_*", "scripts/blueprint_builder/*", "scripts/dt_builder/*",
                            "scripts/intent_builder/*", "scripts/generate_analysis_md.py", "scripts/audit_*",
                            "scripts/populate_engine_references.py", "scripts/inject_pixelcode_avionix.py"],
     "ARCHIVE with final_touch history (section 4.4, P0-04)"),
    ("scripts-rag", ["scripts/ingest_rag_docs.py"], "D34 archive generator part; AI-03 ingestion"),
    ("scripts-assets", ["scripts/assets/*"], "P0-03 inventory/scans (D37)"),
    ("scripts-other", ["scripts/*"], "scripts/AGENTS.md; Blender tools Phase 7; launchers P0-05; lib merge M8-02"),
    ("archive", ["archive_tracked/*"], "archive_tracked/AGENTS.md"),
]

# backend: every module has a fate in course of action 4.4 (subsystem scan); map by package
BACKEND = {
    "server": "M0-05..08 (api_v1, legacy adapter, schemas merge)", "runtime": "M0-06/07, M3-07",
    "plant": "M1-14 facade", "physics": "M1 (port/reuse, section 4.4)", "telemetry": "M0-07 retire can_streamer; M5-05 replay; M7 CAN/MAVLink; ACES loader keep",
    "twin": "M3-01, M4-06", "detect": "M3-02..04", "diagnose": "M3-05/06", "prognose": "M4-02/03",
    "ml": "M3-04 (flyhash, crank, spectral); legacy detection_pipeline/trend_analyser retired M2-02/M3-07",
    "agent": "Phase 8b AI-02/05; diagnostic_agent M3-06", "knowledge": "Phase 8b AI-03/04", "voice": "Phase 8b AI-06",
    "graph": "M4-05 + AI-05; reporter merge M5-06", "reports": "M5-06 one writer", "mission": "M4-04, M5-01..09",
    "reliability": "M3-05 (fmeca, isolability)", "maintenance": "M4-05", "evaluation": "M3-08, M4-03",
    "core": "M0-05 frame, M2-01 limits, M8-05 OSA-CBM", "alarms": "M2-03", "dsp": "M1-09/M3-02",
    "edge": "M7-03", "link": "M7-03", "fadec_emulator": "M7-02", "security": "M7-04", "federation": "M7-05",
    "foundation": "RESEARCH (D36)", "datasets": "M4-07 rename/label (D35)", "economics": "RESEARCH / UX-03 optional",
    "performance": "M1-14 maps", "sources": "M0/M7 Frame sources", "osacbm.py": "M8-05", "ml_runtime_lock.py": "KEEP (AI layer)",
    "__init__.py": "package", "AGENTS.md": "instructions", "CLAUDE.md": "instructions",
}

IGNORED_GROUPS = ["node_modules", "dist", "__pycache__", ".pytest_cache", "graphify-out", ".playwright-mcp",
                  "report_dump", "Voice", "tools", ".env", "*.blend1", "data/telemetry/live_sorties"]


def run(args):
    return subprocess.run(["git", "-C", ROOT] + args, capture_output=True).stdout.decode("utf-8", "replace")


tracked = [f for f in run(["ls-files", "-z"]).split("\0") if f]
untracked = [f for f in run(["ls-files", "-z", "--others", "--exclude-standard"]).split("\0") if f]
deleted = set(f for f in run(["ls-files", "-z", "--deleted"]).split("\0") if f)
ignored_dirs = [l.strip() for l in run(["status", "--ignored", "--porcelain"]).splitlines() if l.startswith("!!")]

rows, uncovered = [], []
for path, status in [(f, "tracked-deleted-on-disk" if f in deleted else "tracked") for f in tracked] + [(f, "untracked") for f in untracked]:
    rule = ref = None
    if path.startswith("backend/"):
        part = path.split("/")[1]
        rule, ref = "backend:" + part, BACKEND.get(part)
    else:
        for rid, pats, r in RULES:
            if any(fnmatch.fnmatch(path, p) for p in pats):
                rule, ref = rid, r
                break
    if not ref:
        uncovered.append(path)
        rule, ref = "UNCOVERED", ""
    rows.append((path, status, rule, ref))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["path", "status", "rule_id", "plan_reference"])
    w.writerows(rows)

print(f"tracked: {len(tracked)} (deleted on disk: {len(deleted)}), untracked: {len(untracked)}, total rows: {len(rows)}")
print("by rule:")
for k, v in collections.Counter(r[2] for r in rows).most_common():
    print(f"  {v:5}  {k}")
print(f"\nignored entries (generated/local, handled by .gitignore + STRUCTURE.txt external deps): {len(ignored_dirs)}")
for l in ignored_dirs[:40]:
    print("   ", l)
print(f"\nUNCOVERED: {len(uncovered)}")
for u in uncovered[:80]:
    print("   ", u)
