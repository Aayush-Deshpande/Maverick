// Main-thread handle on the reservoir worker. Started once, early (it needs well under a second off the
// main thread); the Memory chapter draws from it if it is ready and says so if it is not.
import { FRAME } from './story';

export interface Reservoir {
  classes: string[];
  frames: number;
  show: number;
  nodes: number;
  scores: Float32Array;
  path: Float32Array;
  act: Float32Array;
  label: Int8Array;
  edges: Int32Array;
  layout: Float32Array;
  centroids: Float32Array;
  trainAccuracy: number;
  trainFrames: number;
}

let started: Promise<Reservoir | null> | null = null;
let ready: Reservoir | null = null;

export function startReservoir() {
  if (started) return started;
  started = new Promise((resolve) => {
    try {
      const w = new Worker(new URL('./reservoir.worker.ts', import.meta.url), { type: 'module' });
      w.onmessage = (e: MessageEvent<Reservoir>) => { ready = e.data; resolve(ready); w.terminate(); };
      w.onerror = () => { resolve(null); w.terminate(); };
    } catch { resolve(null); }
  });
  return started;
}
export const reservoir = () => ready;

/** First frame at or after `from` where the readout's label is `cls` (story seconds), or null. */
export function namedAt(res: Reservoir, cls: string, from = 0) {
  const c = res.classes.indexOf(cls);
  for (let f = Math.floor(from / FRAME); f < res.frames; f++) if (res.label[f] === c) return f * FRAME;
  return null;
}
