# archive_tracked/: retired code, kept for history
Global rules: ../AGENTS.md and ../DECISIONS.md.

- Nothing here is imported by the server, the frontend or the tests. Do not import from it, fix it or extend it.
- Code retired by the cards (D12) is moved here with `git mv`, with one line per move in `ARCHIVE_LOG.txt` (date, card, old path, reason, replacement).
- To restore something, `git mv` it back and record why in DECISIONS.md.
- Never delete anything here without Prasad's explicit OK.
