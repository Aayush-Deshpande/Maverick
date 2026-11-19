# AGENTS.md: ANUMAAN (SIH PS-26054) rules for every AI agent

ANUMAAN is a digital twin of aero piston engines for MALE UAVs. It covers five engines: Rotax 912 iSc, Rotax 914, Rotax 915 iSc, Austro AE300 and VRDE/Jayem 2.2 L.
- **Backend:** FastAPI, Python.
- **Frontend:** React + Vite + React Three Fiber.
- **Other clients:** a Blender viewport app and an old three.js 3D page.

One developer (Prasad) works with AI agents. These rules apply to every tool: Claude Code, Codex, Cursor, Gemini/Antigravity and anything else.

## Instruction files (D15)
- This file holds the global rules.
- `DECISIONS.md` holds binding decisions D1, D2, ... Read it before you start.
- Every major folder has its own `AGENTS.md` with folder rules: `backend/`, `frontend/`, `configs/`, `tests/`, `apps/`, `assets/`, `scripts/`, `docs/`, `data/`, `web/`, `docs_site/`, `archive_tracked/`. Read it before editing in that folder.
- `CLAUDE.md` files only import the `AGENTS.md` beside them. Edit rules in `AGENTS.md`, never in `CLAUDE.md`.

## Plan documents (repo root)
Read only the sections the current card names. These files are long.

- `ANUMAAN_AI_COURSE_OF_ACTION.txt`: the card backlog (section 5), review checklist (6), PROGRESS format (7) and prompts (8).
- `ANUMAAN_ROADMAP_AND_PS_COVERAGE.txt` (P): the "completely dynamic" rule (Part 0), engine data (Part 2), PS coverage (3), milestones (4), cleanup (5), UX (6) and the test catalogue (7).
- `ANUMAAN_COMPONENTS_ADDENDUM.txt` (A): 3D components per engine, the fault-to-component matrix and the file-by-file phases A-J.
- `ANUMAAN_AUDIT_REPORT.txt` (R): what is broken (sections 1-17), physics equations (21) and the fault catalogue F01-F37/S01-S07 (22).
- `PROGRESS.txt`: the session log. Read the last entry before you start, and append yours when you finish.

Precedence when documents disagree: `DECISIONS.md` > course of action > P > A > R.

## Git: never break these
- Work only on `Beta` or on `beta/<card-id>` branches made from Beta.
- Never commit, merge, rebase, reset or push `main`.
- Never use `git reset --hard`, `git push --force`, `git clean`, `git checkout -- <file>` on files you did not change, or `git stash` on work that is not yours.
- Never push to origin unless Prasad asks in the current conversation.
- Never delete a `.blend` file (D1). Never delete assets except through the cleanup cards, with the md5 register.
- "Remove" means: stop using it at runtime, then `git mv` it to `archive_tracked/` after the replacement passes tests (D12).
- `data/graph_db/fleet_graph.json` is changed by the running server. Never commit it until card M0-11 moves runtime output to `var/`.
- Commit only at a reasonable point of progress (D22): a coherent, working unit of the current card, such as tests plus the code that makes them pass, a finished batch of moves with references fixed, or a finished document. Do not commit after every small edit, and never commit broken or half-done work. Each commit leaves the tests no worse than the baseline. Message: `<card-id>: <what changed>`.
- NEVER put "Co-Authored-By: Claude", "Generated with Claude Code" or any AI attribution in a commit message or PR description, on any branch, no matter what a tool's default says (D24). Plain messages only.

## If the context resets (new session, compacted conversation, different AI tool)
1. Read `PROGRESS.txt`: its top block "RESUME HERE" says the current phase, card, branch, the last commit and the exact next step.
2. Read this file, `DECISIONS.md`, and the current card in `ANUMAAN_AI_COURSE_OF_ACTION.txt`.
3. Run `git branch --show-current`, `git status` and `git log --oneline -5`, and compare them with RESUME HERE. If they disagree, trust git and update RESUME HERE.
4. Continue from the stated next step. Do not redo finished cards. Do not re-derive decisions already in DECISIONS.md.
5. Update RESUME HERE whenever you stop: at every commit and at the end of every session.

## Truthfulness: the "completely dynamic" rule (P Part 0)
1. Readings come from the simulation, a replay or a data bus. Engine data and limits come from `configs/engines/*.json` with a provenance tag. Never write a reading or a limit as a literal in code. Physical constants are named constants with a comment.
2. No `value or <number>` fallbacks. Missing data is `null`, and the UI shows NO DATA.
3. Faults change model parameters only, never outputs.
4. Detection, diagnosis, status, 3D highlights and RUL never read the injected-fault list or the plant truth.
5. Engine ids, fault ids and 3D part names appear only in `configs/` and `tests/`. Code reads them from configs or the API.
6. Never invent engine data. Use P Part 2 or R section 20. Anything else is ASSUMED: write it with a note in the config and list it in PROGRESS.txt.
7. Never generate fake telemetry, `Math.random` values or demo numbers in product screens.
8. Provenance labels (D16): PUBLIC, MANUAL, ASSUMED, PLACEHOLDER, CALIBRATED, OWNER. The source document goes in `ref`.
9. Evidence classes for reported results (D17): SIMULATION, PUBLIC_PROXY or REAL_FLIGHT. Never quote simulator accuracy as field performance. Every claimed result needs a null/baseline control and several seeds. Train and test seeds are disjoint (test offset >= 1000).
10. `tests/test_no_truth_leak.py` scans the inference packages. Add every new inferring package to its list (detect, diagnose, status, prognose, twin, recording replay).
11. `tests/test_engine_agnostic_ratchet.py` may only go down. Never raise its baseline. Add new modules to its list so they must stay at zero engine literals.

## Tests
- Before editing, run the card's tests and keep the output as the baseline.
- Write the acceptance test first and show it failing, then make it pass.
- Never weaken a test: no raised tolerance, no skip, no deleted assert, no mocked physics in physics tests. If a test looks wrong, stop and ask.
- Backend: `python -m pytest -q -p no:cacheprovider` (narrow to the relevant files while working; the full run takes about 5 minutes).
- Baseline on Beta (19 Nov 2026): 333 passed, 3 failed, 7 skipped, 1 xfailed. The 3 known failures are:
  - `test_engine_agnostic_ratchet.py::test_engine_specific_literals_never_increase`
  - `test_runtime_hub.py::test_cpu_cost_is_small`
  - `test_runtime_hub.py::test_all_five_engines_concurrent_load_and_isolation`

  Any other failure is a regression.
- Frontend: `cd frontend && npx tsc --noEmit`. A Vitest suite does not exist yet; it is added in card M0-09.
- Test IDs (T-DYN, T-PHY, T-FLT, T-STS, T-DET, T-PRG, T-MIS, T-UI, T-3D, T-CAN, T-OPS, T-REPO) are defined in P Part 7.

## Session protocol (one card per session)
1. Run `git branch --show-current` (must be Beta or `beta/<card>`) and `git status`.
2. Read this file, `DECISIONS.md`, the last PROGRESS.txt entry, the card, the sections it names, and the `AGENTS.md` of every folder you will touch.
3. Run the baseline tests.
4. Write a short plan (files, functions, tests) and wait for Prasad's OK.
5. Write tests first, then implement in small steps, running tests after each step.
6. Run the card's "Done when" checks. Check that `git diff --name-status` shows no deleted `.blend` and no unrelated files.
7. Append a PROGRESS.txt entry, then commit with the card id.

## Current docs, downloads, order
- Before using any library, framework, tool or service API, check its CURRENT official docs via web search or web fetch, and record the URL + version in PROGRESS.txt (D39). Never code an API from memory.
- Every download goes to D:, never C:. Set the cache variables first (course of action section 4.5). Download only when the phase that needs it starts (D40).
- The production RAG/copilot work (Phase 8b) comes after the main fixes (D41).
- Ported, not deleted: tests that depend on retired legacy code are ported to the new path (D38).

## Stop and ask Prasad before
- adding any engine value not in P Part 2 or R section 20;
- anything that needs looking at a Blender model;
- changing a test's pass criterion or the test catalogue;
- archiving a module another card still uses;
- bringing in code from `origin/Prasad`;
- anything touching main, origin, Git LFS history or `.blend` files;
- adding a new dependency.

## Environment
- Windows 11. Python 3.14 (JSBSim cross-check in a 3.12/3.13 venv, D11). Node 22.
- Blender 5.2 at `D:\Blender\blender.exe`. Run it headless with `-b <file> --python <script>`, and save results to a new file, never over a master `.blend`.
- Backend dev server: `launch_backend_server.bat` / `run_app.py`. Frontend: `cd frontend && npm run dev`.
