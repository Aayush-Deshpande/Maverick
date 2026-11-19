# CLAUDE.md: ANUMAAN
The rules live in AGENTS.md and the binding decisions in DECISIONS.md. Both are imported below. Edit rules there, not here.

@AGENTS.md
@DECISIONS.md

## Claude Code specifics
- Each major folder has its own CLAUDE.md, which imports that folder's AGENTS.md. Claude Code loads it when you work in that folder.
- Use plan mode for step 4 of the session protocol.
- Use `/code-review` on your diff before committing.
- When running a second session in parallel, use a separate git worktree on its own `beta/<card>` branch.
- The `.claude/settings.json` guard hook (card S-02) blocks push, reset --hard, clean, force, switching to main and deleting `.blend` files. Do not try to bypass it.
