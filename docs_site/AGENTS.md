# docs_site/: public documentation website (Vite + React + Tailwind)
Global rules: ../AGENTS.md and ../DECISIONS.md.

- Sources: `src/` (pages, components, lib), `technical/` and `journey/` content, `CONTENT_MAP.md`, `STYLE_BRIEF.md`, `RESEARCH_DOSSIER.md`.
- `public/assets/models/*.glb` are copies of the engine models. After card C-05 they come from `assets/web/engines/` at build time. Never hand-copy them.
- `dist/` and `node_modules/` are build output. Never edit or commit them.
- The PNG screenshots in this folder are old UI captures. Card C-04 moves them to `docs/screenshots/`.
- Content rule: the site must describe only what works on the branch. `technical/16-mission-planning.md` and other pages that describe features only on origin/Prasad are corrected in M8-05.
- Commands: `cd docs_site && npm run dev` / `npm run build`.
