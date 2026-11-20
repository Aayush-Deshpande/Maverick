# docs/: project documentation
Global rules: ../AGENTS.md and ../DECISIONS.md.

## Authority
- The current plan and rules are the root files: AGENTS.md, DECISIONS.md, `ANUMAAN_AI_COURSE_OF_ACTION.txt`, `ANUMAAN_ROADMAP_AND_PS_COVERAGE.txt`, `ANUMAAN_COMPONENTS_ADDENDUM.txt`, `ANUMAAN_AUDIT_REPORT.txt`, PROGRESS.txt.
- `docs/build/*` is HISTORY and background (D17): `DECISIONS.md` D01-D37, `AGENT_BRIEF.md`, `HANDOFF_PROMPT.md`, `BACKLOG.md`, `CURRENT_STATE.md`, `MENTAL_MODEL.md`, `INTERFACES.md`, etc. Read it for design reasoning. Do not follow its task lists or decisions where the root files differ, and do not add new decisions there.
- `docs/00_official_problem_statement.md` is the SIH problem statement. Its 7 links to `../analysis/` are dead (P N2) and its section 7 claims are not true on main (P N3). Card M8-05 fixes them.
- `docs/reference/` holds manufacturer documents (Rotax manuals and others). Quote page numbers when using them as `ref` in configs.

## Rules
- Docs describe only what exists on the branch. No claim without a code path or a test.
- Generated docs (fault catalogue from `configs/faults.json`, physics constants table, API reference) are produced by scripts, not hand-edited.
- New docs from M1 onward: `docs/physics/ENGINE_MODEL.txt` (M1-16), evaluation reports under `reports/` or `docs/evaluation/` (M3-07, M4), the architecture and deployment roadmap (M8-05).
- Plain text or markdown. No marketing claims. Label every result with its evidence class (SIMULATION / PUBLIC_PROXY / REAL_FLIGHT).
