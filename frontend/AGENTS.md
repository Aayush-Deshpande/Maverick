# frontend/: React 18 + TypeScript + Vite + Tailwind + React Three Fiber (three 0.169) + zustand
Global rules: ../AGENTS.md and ../DECISIONS.md.

## Today (main @ 9b5942e)
- `src/App.tsx` hosts the tabs and embeds the old 3D page (`apps/threejs_twin`) in an iframe.
- `src/hooks/`:
  - `useTelemetrySocket.ts` (legacy `/ws/telemetry`, hard-coded Render URL fallback);
  - `useEngineRuntime.ts` (new runtime, plus 1 s and 3 s polls);
  - `useMissionReplay.ts`.
- `src/components/`: the console, Tactical GCS panels, `VoiceCopilot`, `landing/` (`LandingHero3D` with 10 engine literals).
- `public/models/*.glb`: Draco copies of the engine models (single source after card C-05: `assets/web/engines/`).
- No unit tests yet. `npm run build` = `tsc && vite build`.

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
