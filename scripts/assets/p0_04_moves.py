"""Card P0-04: root documents, screenshots, history folders, archive items (moves only; DECISIONS D21, D42, D34).

Every move uses `git mv` so history follows. Each move is appended to archive_tracked/ARCHIVE_LOG.txt
(for archive moves) and printed. Re-running is safe: moves whose source no longer exists are skipped.
"""
import datetime
import glob
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TODAY = datetime.date.today().isoformat()
LOG = os.path.join(ROOT, "archive_tracked", "ARCHIVE_LOG.txt")


def git(*args):
    r = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def mv(src, dst, reason, archive=False):
    s, d = os.path.join(ROOT, src), os.path.join(ROOT, dst)
    if not os.path.exists(s):
        print(f"skip (missing): {src}")
        return
    os.makedirs(os.path.dirname(d) if not src.endswith("/") else d, exist_ok=True)
    git("mv", "-k", src.rstrip("/"), dst.rstrip("/"))
    print(f"moved: {src} -> {dst}")
    if archive:
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{TODAY} | P0-04 | {src} -> {dst} | {reason}\n")


if not os.path.exists(LOG):
    with open(LOG, "w", encoding="utf-8") as fh:
        fh.write("ARCHIVE LOG - every move into archive_tracked/ (date | card | old path -> new path | reason)\n"
                 "Restore with git mv and record why in DECISIONS.md (archive_tracked/AGENTS.md).\n")

# 1. submitted texts, screenshots
mv("ANUMAAN_Idea_Description.txt", "docs/submission/ANUMAAN_Idea_Description.txt", "submitted text")
mv("ANUMAAN_Abstract_Summary.txt", "docs/submission/ANUMAAN_Abstract_Summary.txt", "submitted text")
for png in ["full_ui_check.png", "shadow_fix_check.png", "ui_fix_check.png"]:
    mv(png, f"docs/screenshots/{png}", "root screenshot")
for png in sorted(glob.glob(os.path.join(ROOT, "docs_site", "*.png"))):
    name = os.path.basename(png)
    mv(f"docs_site/{name}", f"docs/screenshots/docs_site/{name}", "docs_site screenshot")

# 2. history folders (D17)
os.makedirs(os.path.join(ROOT, "docs", "history"), exist_ok=True)
mv("UpdatedReport", "docs/history/UpdatedReport", "earlier audit (history)")
mv("final_touch", "docs/history/final_touch", "generated blueprint docs (history)")

# 3. archive: generators that write final_touch / generated manuals, experiments, Crazy_Landing, study.zip
gen = (["scripts/" + os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "scripts", "build_*.py"))]
       + ["scripts/generate_analysis_md.py", "scripts/audit_aero_dt_coverage.py", "scripts/audit_drdo_intent_coverage.py",
          "scripts/audit_fl_coverage.py", "scripts/audit_ideal_blueprint_coverage.py",
          "scripts/populate_engine_references.py", "scripts/inject_pixelcode_avionix.py", "scripts/ingest_rag_docs.py",
          "scripts/blueprint_builder", "scripts/dt_builder", "scripts/intent_builder"])
for g in gen:
    mv(g, "archive_tracked/doc_generators/" + g.split("/", 1)[1],
       "generator of history docs or of the fabricated RAG manuals (D17, D34)", archive=True)
mv("experiments", "archive_tracked/experiments", "research experiments, not imported by app or tests", archive=True)
mv("docs/study.zip", "archive_tracked/docs_study_zip/study.zip", "zip duplicate of docs/study (D42)", archive=True)

# generated RAG corpus (D34/D44)
for f in sorted(os.listdir(os.path.join(ROOT, "data", "documents"))):
    mv(f"data/documents/{f}", f"archive_tracked/synthetic_rag_corpus/{f}",
       "AI-generated text named as OEM/DRDO manuals; never index (D34, D44)", archive=True)

# 4. Crazy_Landing (renamed on disk from web/usavionix/mirror by Prasad): record the rename, then archive (D42)
git("add", "-A", "web/usavionix", "web/Crazy_Landing")
mv("web/Crazy_Landing", "archive_tracked/crazy_landing", "Prasad's separate experiment (was web/usavionix/mirror) (D42)",
   archive=True)

# 5. stale submodule declaration (D26)
if os.path.exists(os.path.join(ROOT, ".gitmodules")):
    git("rm", "-q", ".gitmodules")
    print("removed: .gitmodules (stale submodule declaration, D26)")

# 6. empty folders and placeholders
ppt = os.path.join(ROOT, "ppt")
if os.path.isdir(ppt) and not os.listdir(ppt):
    os.rmdir(ppt)
    print("removed empty folder: ppt/")
print("done")
