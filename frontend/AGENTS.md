# frontend/: React 18 + TypeScript + Vite + Tailwind + React Three Fiber (three 0.169) + zustand
Global rules: ../AGENTS.md and ../DECISIONS.md.

## Today (Beta, 20 Nov 2026)
Two layers with different rules:

**Product layer (all rules below apply; scanned by T-DYN-1):**
- `src/App.tsx`: workspaces landing / runtime / twin / legacy. The "3D twin" tab embeds Beta's
  `apps/threejs_twin` (on `/api/v1` since M0-10).
- `src/store/engineStore.ts` + `src/api/socket.ts`: the ONE `/ws/v1` socket (fleet subscription) and the store.
  `src/api/state.ts` is generated (`npm run gen:types`).
- `src/hooks/useEngineRuntime.ts`: store access, engine list (default engine from `/api/v1/engines`), commands.
- `src/components/EngineRuntimeConsole.tsx`: role views Operator / Engineer / Maintenance / Mission / All
  (client-side, never sent to the server), with:
  - `StatusBanner`: status, reasons, alerts, tones;
  - `EngineerPanel`: residuals, twin parameters, virtual sensors;
  - `viewer3d/EngineViewer3D`: React Three Fiber, highlights only from `state.highlights` plus training mode;
  - `RoutePlannerPanel`, `RouteMap` and `AltitudeProfile`: route, glide and divert.
- `src/utils/labels.tsx`: display names from `configs/ui/labels_<lang>.json` via `/api/v1/ui/labels`.
- Legacy Tactical GCS panels (`legacy` workspace) use `useTelemetrySocket` and the legacy adapter. They retire
  with M6.
- Tests: `npx vitest run` (`*.test.ts(x)` next to the code).

**Presentation layer (D57; imported from main 20 Nov 2026; outside T-DYN-1):**
- `src/components/landing/`, `sortie/` (the film), `studio/` and `survey/`, plus `src/demoIntent.ts`.
- Media in `public/studio`, `public/survey`, `public/vids` and `public/twin` (main's static twin page, vendored
  three.js, and `component_map.json`, which the film reads).
- Purpose: a storytelling surface that also gives the backend time to warm up. It may name engines in its
  showcase and use `Math.random` for the film's sound.
- It reads live data only through `survey/useLiveEngine.ts` + `survey/frame.ts`, an adapter onto Beta's
  `/api/engines/{id}/state` payload. If the backend payload changes, update that adapter.
- Known debts, kept on purpose (not product code):
  - a second three.js copy and a second fault-to-part map in `public/twin`. Product highlights come only from
    `configs/faults.json` + `configs/components`;
  - the survey polls every 2.5 s instead of using the store.

- `public/models/<engine>.glb`: gitignored copies synced from `assets/web/engines/` (D49, `npm run sync-models`).
  Do NOT replace them with other exports: the component manifests depend on their node names.

## Target (cards M0-09, M6-*)
- `src/store/`: one zustand store, fed by ONE WebSocket manager at `/ws/v1` with `{"subscribe": id}`. It handles reconnect, resync by `seq`, and stale detection (2 s STALE, 10 s DISCONNECTED).
- `src/api/`: types generated from the backend pydantic schema. Never hand-write state types.
- `src/views/`: Operator, Engineer, Maintenance, Fleet, Replay, Mission. The role is a client-side choice; never send SET_ROLE to the server.
- `src/components/Viewer3D/`: R3F viewer driven by `state.highlights` and `configs/components` (D5). Exact node names only.

## Rules
- No component opens its own socket or poll. Everything reads the store.
- No hard-coded engine ids, fault lists, limits, units or rate labels ("20 Hz"). They come from `/api/v1` (engines, faults, schema) and the state message.
- No `Math.random` or fake numbers in product screens. Missing data shows NO DATA. Stale data greys out.
- No optimistic UI for faults or levers: show them only when the server confirms. Commands show pending / ok / error.
- Colours (D4): red = NO-GO warning, amber = CAUTION, cyan = ADVISORY. Red and amber are used for nothing else.
- Minimum text 12 px (14 px for values), WCAG AA contrast, layout works at 360 / 768 / 1280 px. No fixed heights like `min-h-[680px]`.
- Backend URL is derived from `window.location` (`wss://` on https) or set in settings. No hard-coded host.

## Commands
- `cd frontend && npm run dev`
- `npx tsc --noEmit` (must pass)
- `npm run build`
- From card M0-09: `npx vitest run`. From M6-10: Playwright.
