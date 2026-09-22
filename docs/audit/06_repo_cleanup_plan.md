# Repository Cleanup — Procedure and Analysis

*A plan, not an execution. Nothing in this document has been carried out. Every step states what it touches, why it is safe, how to verify it, and how to undo it.*

**Surveyed:** 22 September 2026 · working tree ≈ 10 GB · `.git` 3.7 GB (of which `.git/lfs` 1.9 GB) · 84 files in LFS.

---

## 1. The headline: this repo is cleaner than its size suggests

⚠️ **The instinct to "clean 10 GB of junk" is mostly wrong here.** The bulk is already excluded from version control:

| Directory | Size | Tracked in git? |
|---|---|---|
| `Qwen3-4B/` | **7.6 GB** | ❌ already gitignored |
| `competitors/` | 888 MB | ❌ already gitignored |
| `Voice/` | 421 MB | ❌ already gitignored |
| `frontend/node_modules/` | 137 MB | ❌ already gitignored |
| `build/` | 85 KB | ❌ already gitignored |

✅ Verified: **zero `__pycache__` and zero `.pyc` files are committed**, and `.gitignore` already covers `__pycache__/`, `*.py[cod]`, `node_modules/`, `build/`, `dist/`, `.pytest_cache/`, `*.blend1`.

🔶 So there are **two separate problems**, and conflating them causes bad decisions:

- **Problem A — local disk.** ~9 GB of untracked weight sitting in the working tree. Costs disk and makes the folder unpleasant to navigate. **Nothing here affects the repository or other people.**
- **Problem B — committed weight.** `Models_Images` (842 MB), `Models` (383 MB), `3d_models` (217 MB), `renders` (144 MB) *are* in git/LFS. Only this affects clone time and LFS quota.

**Problem B is the one that matters for the project. Problem A is housekeeping.**

---

## 2. Method

Classification was evidence-based, not by name:

1. **Entry points traced** — every `launch_*.bat`, `run_app.py`, `pytest.ini`.
2. **Reference counting** — `grep` across `backend/`, `apps/`, `scripts/`, `tests/`, `frontend/src/` for each directory name.
3. **Tracking status** — `git ls-files` and `git check-ignore` per entry.
4. **Duplicate detection** — md5 comparison where names collided.

⚠️ **Limit of the method:** a `grep` for a directory name misses paths built at runtime (`os.path.join(cfg.asset_root, ...)`). Every deletion step below therefore has a verification gate, and nothing is deleted before the gate passes.

---

## 3. Inventory and verdicts

### 3.1 KEEP — live, referenced by running code

| Entry | Size | Evidence |
|---|---|---|
| `backend/` | 3.3 MB | The system |
| `frontend/` (source only) | ~1 MB | React GCS |
| `apps/` | 584 KB | Referenced by 3 launchers |
| `scripts/` | 740 KB | `launch_mission_graph.bat` → `scripts/simulate_missions.py` |
| `tests/` | 298 KB | `pytest.ini` → `testpaths = tests` |
| `data/` | 33 MB | **22 code references.** Missions, telemetry, graph_db, documents |
| `report_dump/` | 2.7 MB | **18 code references.** Generated mission output |
| `docs/`, `analysis/` | 4.5 MB | Documentation |
| `Datasets/` | 85 KB | Metadata only; raw data already untracked |
| `manifests/`, `compiled_tb/` | 64 KB | Small, referenced by asset specs |
| Root configs + launchers | < 100 KB | `requirements.txt`, `pytest.ini`, `firebase.json`, `run_app.py`, `*.bat` |

### 3.2 KEEP — future scope

| Entry | Size | Why keep |
|---|---|---|
| `Models/` | 383 MB | Engine + airframe CAD. Required for the 3D twin ([`docs/assets/`](../assets/01_current_state_audit.md)) |
| `Models_Images/` | 842 MB | Reference libraries, cited by the asset program |
| `site/` | 33 MB | Standalone WebGL presentation site |
| **`avionix/`** | 15 MB | ⬜ **KEEP — user decision.** Reverse-engineering reference for the WebGL site |
| **`frontend-analysis/`** | 19 MB | ⬜ **KEEP — user decision.** USAvionix asset catalogue + 40 GLSL shaders |
| `Qwen3-4B/` | 7.6 GB | Local LLM. Already gitignored. See §5 |
| `Voice/` | 421 MB | Already gitignored. [Self-audit](02_self_audit.md) recommends cutting the *feature*, but that is a scope decision, not a cleanup one |

### 3.3 SAFE TO DELETE — junk with zero risk

| Item | Count | Why safe |
|---|---|---|
| `__pycache__/` directories | 15 | Regenerated automatically. Already gitignored, none committed |
| `*.pyc` files | 63 | Same |
| `apps/blender_twin/*.backup_pre_1to1`, `*.backup_pre_phase_h`, `*.checkpoint_golden` | 3 | ⚠️ Untracked local backups of `standalone_canyon_flight_app.py`. **Verify against git history first** (§4.2) |
| `docs/study.zip` | 1 | Untracked; superseded by `docs/study/` |

### 3.4 NEEDS A DECISION — do not act without one

| Item | Size | Issue |
|---|---|---|
| **`3d_models/` vs `Models/`** | 217 MB | ⚠️ **Overlapping content.** Both hold `bayraktar_tb3_digital_twin.blend` (identical LFS pointers) and a `.blend1`. The `.blend1` files *differ* (218,668 vs 219,113 bytes) — different backup states, not duplicates. `3d_models/renders/` (40 files) also overlaps conceptually with `renders/` (91 files). **Consolidating is the single biggest committed-size win available, but requires knowing which is canonical.** See §6 |
| `renders/` | 144 MB | Rendered output. Regenerable from `Models/` + `scripts/`, but only if the pipeline still runs. Candidate for untracking, not deleting |
| `tools/` | 53 MB | `cloudflared.exe`, `ngrok.exe` (third-party binaries, in LFS), `blender_mcp`. Only 3 files tracked. Binaries are freely re-downloadable |
| `scratch/` | 5 MB | 17 tracked files. **Zero code references.** Experiments — `bing_shot.png`, `port_tb3.py`, `build_detailed_pd170.py` |
| `competitors/` | 888 MB | Delete once the audit is closed. Already gitignored |

---

## 4. The procedure

⚠️ **Order matters. Each phase is independently revertible and must pass its gate before the next begins.**

### Phase 0 — Safety net (do this first, always)

```bash
git status --porcelain > /tmp/pre_cleanup_status.txt
git rev-parse HEAD > /tmp/pre_cleanup_head.txt
git add -A && git commit -m "checkpoint: before repository cleanup"
git branch backup/pre-cleanup-2026-09-22
```

🔶 **Everything after this is recoverable by `git reset --hard backup/pre-cleanup-2026-09-22`.** Untracked deletions are *not* covered, which is why §4.2 verifies before deleting.

**Baseline the behaviour you must not break:**
```bash
python -m pytest tests/ -q > /tmp/tests_before.txt 2>&1
```
⚠️ If tests already fail, record that. A pre-existing failure must not be mistaken for cleanup damage.

---

### Phase 1 — Zero-risk junk (regenerable, nothing committed)

```bash
find . -name "__pycache__" -type d -not -path "./competitors/*" \
       -not -path "*/node_modules/*" -prune -exec rm -rf {} +
find . -name "*.pyc" -not -path "./competitors/*" -delete
rm -f docs/study.zip
```

**Gate:** `python -m pytest tests/ -q` matches `/tmp/tests_before.txt`.
**Undo:** nothing to undo — Python regenerates caches on next run.
**Recovers:** a few MB. Real benefit is a navigable tree.

---

### Phase 2 — Stale backup files (verify, then delete)

⚠️ These three are **untracked**, so git cannot restore them. Verify before removing:

```bash
# 1. Confirm the live file is tracked and committed
git log --oneline -3 -- apps/blender_twin/standalone_canyon_flight_app.py

# 2. Diff each backup against the live file — understand what you would lose
for b in apps/blender_twin/standalone_canyon_flight_app.py.backup_pre_1to1 \
         apps/blender_twin/standalone_canyon_flight_app.py.backup_pre_phase_h \
         apps/blender_twin/standalone_canyon_flight_app.py.checkpoint_golden; do
  echo "=== $b ==="; diff <(cat "$b") apps/blender_twin/standalone_canyon_flight_app.py | head -20
done
```

**Only if** the live file is committed **and** the diffs contain nothing you want:
```bash
mkdir -p ../_anumaan_attic && mv apps/blender_twin/*.backup_pre_* apps/blender_twin/*.checkpoint_golden ../_anumaan_attic/
```
🔶 **Move to an attic outside the repo rather than delete.** Costs nothing, and makes the step reversible.

**Gate:** `launch_canyon_simulation.bat` still starts.

---

### Phase 3 — Tighten `.gitignore` (prevents recurrence; deletes nothing)

Append:
```gitignore
*.backup_pre_*
*.checkpoint_*
docs/study.zip
_attic/
```
**Gate:** `git status --porcelain` shows no newly-ignored *tracked* file (ignoring a tracked file does not untrack it, so this is safe by construction).

---

### Phase 4 — Untrack regenerable binaries (reduces clone weight; keeps files on disk)

⚠️ **`git rm --cached` removes from the index, not from disk.** Files stay locally; they stop being distributed.

**4a — third-party executables** (freely re-downloadable, currently in LFS):
```bash
git rm --cached tools/cloudflared.exe tools/ngrok.exe
printf 'tools/*.exe\n' >> .gitignore
```
⬜ Add a `tools/README.md` recording versions and download URLs so the environment stays reproducible.

**4b — rendered output** — ⚠️ **only after confirming the pipeline regenerates them.** Do not run this blind:
```bash
# FIRST verify renders can be regenerated:
ls scripts/ | grep -i render
# Only if a working render script exists:
# git rm -r --cached renders/ && echo 'renders/' >> .gitignore
```
🔶 If nothing can regenerate `renders/`, **keep it tracked.** Irreproducible output is data, not build artifact.

**Gate:** `git status` shows deletions staged but files present on disk. `python -m pytest tests/ -q` unchanged.
**Undo:** `git reset HEAD~1` before pushing; or `git checkout HEAD -- <path>`.

---

### Phase 5 — Move local-only bulk out of the working tree (Problem A)

These are already gitignored, so this is pure disk/navigation hygiene and **cannot affect the repository**:

```bash
mkdir -p ../_anumaan_local
mv Qwen3-4B ../_anumaan_local/     # 7.6 GB
mv Voice    ../_anumaan_local/     # 421 MB
```
⚠️ **Only if the copilot/voice features are not currently in use.** `backend/agent/copilot.py` scans an `llm/` directory (which does not exist), and `Voice/` has 2 code references. **Verify both before moving:**
```bash
grep -rn "Qwen3-4B\|Voice/" backend/ apps/ scripts/ run_app.py | grep -v "^Binary"
```
🔶 Safer alternative: leave them and accept the disk cost. This phase buys navigation comfort, nothing else.

**`competitors/` (888 MB)** — delete when the audit is closed:
```bash
rm -rf competitors/     # re-clonable via docs/audit/01 + 05
```

---

### Phase 6 — Consolidate `3d_models/` and `Models/` (biggest win, highest risk)

⚠️ **Do not attempt until §6 is answered.** This is the only phase that can silently break the 3D pipeline.

---

## 5. What must NOT be touched

| Never touch | Why |
|---|---|
| `data/` | **22 code references.** Contains `graph_db`, `missions`, `telemetry`, `documents`. Some is irreproducible |
| `report_dump/` | **18 code references.** 400 tracked files |
| `backend/`, `apps/`, `scripts/`, `tests/` | The system |
| `Datasets/*/README.md`, `fetch.py` | The catalogue *is* the deliverable; raw data already excluded by `Datasets/.gitignore` |
| `.gitattributes` | LFS routing. Breaking it corrupts binary checkout |
| `manifests/` | Engine/platform manifests referenced by asset specs |
| `avionix/`, `frontend-analysis/` | ⬜ **User decision: keep** |
| Anything under `.git/` | Obvious, but worth stating |

---

## 6. The one question that must be answered first

**`3d_models/` (217 MB) and `Models/` (383 MB) overlap. Which is canonical?**

Evidence gathered:
- Both contain `bayraktar_tb3_digital_twin.blend` — **identical LFS pointers**, so the same underlying object.
- Both contain `bayraktar_tb3_digital_twin.blend1` — **different sizes** (218,668 vs 219,113 bytes), so different Blender backup states.
- `3d_models/` also holds `rotax_912_is_sport.blend`, `textures/`, `tb3_digital_twin_controller.py`, and a `renders/` subfolder (40 files).
- `Models/` holds the larger CAD set: `engine-rotax-912is-1.snapshot.15/`, `engine-rotax-914-1.snapshot.2/`, `Rotax_915.FBX`, `915_complete.max`, `airframes/`, `engines/`.
- ⚠️ [`docs/assets/01_current_state_audit.md`](../assets/01_current_state_audit.md) states *"only a `.blend1` backup remains in `3d_models/`"* — **this is now inaccurate**; a full `.blend` is present in both. The asset audit predates the ANUMAAN→root restructure and should be re-verified.

🔶 **My reading:** `Models/` is the curated asset library (it came from `ANUMAAN/Models/` and is what the asset program documents), and `3d_models/` is the older working directory. But `3d_models/` holds `rotax_912_is_sport.blend` and `textures/` which may be actively used by the Blender pipeline.

⬜ **Recommended resolution, in order:**
1. `grep -rn "3d_models" backend/ apps/ scripts/ run_app.py` — find every live reference.
2. If none: move `3d_models/` to the attic, run the Blender launchers, confirm they still work, then remove from the index.
3. If some: merge the unique files into `Models/`, update references, then retire `3d_models/`.
4. Either way, **correct `docs/assets/01_current_state_audit.md` afterwards.**

---

## 7. Expected outcome

| | Before | After | Notes |
|---|---|---|---|
| Working tree | ~10 GB | ~1.5 GB | After Phase 5 moves Qwen3-4B, Voice, competitors out |
| Committed (git/LFS) | 3.7 GB | ~3.2 GB | Phase 4 only. Phase 6 could take another ~200 MB |
| Junk files | 81 | 0 | pycache, pyc, backups, study.zip |
| Behaviour | — | **identical** | Every phase gated on tests + launchers |

⚠️ **Note on history:** `git rm --cached` stops *future* distribution but does **not** shrink history — the objects remain in `.git`. Genuinely shrinking `.git` requires `git filter-repo` and a force-push, which **rewrites history for every collaborator**. ⬜ **Not recommended** for a repo with an active team and a deadline. The gain is not worth the coordination risk.

---

## 8. Rollback

| Phase | Undo |
|---|---|
| 0 | — |
| 1 | Nothing needed (caches regenerate) |
| 2 | `mv ../_anumaan_attic/* apps/blender_twin/` |
| 3 | Revert `.gitignore` |
| 4 | `git checkout HEAD -- <path>` (pre-push) or `git reset HEAD~1` |
| 5 | `mv ../_anumaan_local/* .` |
| 6 | `git reset --hard backup/pre-cleanup-2026-09-22` |

**Full reset:** `git reset --hard backup/pre-cleanup-2026-09-22` restores every tracked file. Untracked items live in `../_anumaan_attic/` and `../_anumaan_local/` — which is precisely why nothing in this plan is deleted outright on first pass.

---

## 9. Recommended sequence

🔶 If time is short, **Phases 0–3 only.** They remove every genuine junk file, cost about ten minutes, carry effectively zero risk, and leave the repository navigable.

Phases 4–6 are optimisation. Phase 6 in particular should wait until after the current build push — consolidating the 3D asset directories while the twin pipeline is under active development is a poorly-timed risk for a ~200 MB gain.

---

## 10. One thing to be aware of, separate from cleanup

🔶 Not a cleanup item, and not a recommendation to remove anything — but worth knowing since this repository is pushed publicly:

**22 files in `site/` are byte-identical to assets in the USAvionix scrape** (verified by md5 on `delta-pbr.glb`, `drone-animations.glb`, `slide-1.3cbb161c.webp`). The content-hashed filenames — `border-storm.31d3c346.webp`, `slide-1.3cbb161c.webp` — confirm common origin.

So the presentation site currently ships another company's 3D models, baked camera/drone animations, and marketing imagery. Two practical consequences:

1. **Public redistribution** of third-party commercial assets in a public GitHub repository.
2. **Demo risk** — an evaluator who knows the source site may recognise the drone models or slide imagery.

⬜ The low-cost fix, whenever convenient, is to keep `avionix/` and `frontend-analysis/` as the *reference* material they are (as decided), while replacing the assets actually shipped in `site/` with our own — we already have `Models/` and a Blender pipeline capable of producing them.

---

*Companion to the [audit set](README.md). Nothing here has been executed.*
