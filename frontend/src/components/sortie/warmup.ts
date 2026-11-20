// Once the film has what it needs (airframe, terrain, fonts), quietly pull the full-CAD engine
// models into the HTTP cache so the engine section opens instantly. Vercel serves /models/*
// as `immutable`, so the inset's later fetch() of the same URL is a cache hit.
import { ENGINE_MODELS } from '../survey/engineScene';

let started = false;

const idle = () => new Promise<void>((resolve) => {
  const ric = (window as Window & { requestIdleCallback?: (cb: () => void, o?: { timeout: number }) => number }).requestIdleCallback;
  if (ric) ric(() => resolve(), { timeout: 1500 }); else setTimeout(resolve, 300);
});

/** Order matters: the engine shown first in the engine section goes first. */
const ORDER = ['rotax_912is', 'rotax_915is', 'rotax_914', 'austro_ae300', 'vrde_jayem_2_2l'];

export async function warmEngineModels() {
  if (started) return;
  started = true;
  const conn = (navigator as Navigator & { connection?: { saveData?: boolean; effectiveType?: string } }).connection;
  if (conn?.saveData || /(^|-)2g$|^3g$/.test(conn?.effectiveType ?? '')) return; // respect data saver and slow links
  try { await document.fonts.ready; } catch { /* fonts are a courtesy, not a gate */ }
  await idle();
  for (const id of ORDER) {
    const url = ENGINE_MODELS[id];
    if (!url) continue;
    try {
      // one at a time, low priority, so the page and the film never compete with it
      const res = await fetch(url, { priority: 'low' } as RequestInit);
      await res.arrayBuffer(); // the body must be read for the response to land in the cache
    } catch { return; }
    await idle();
  }
}
