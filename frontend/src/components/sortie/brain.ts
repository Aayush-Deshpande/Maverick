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
  forest: { trees: number; maxDepth: number; trainMs: number; knownAccuracy: number; reservoirKnownAccuracy: number; tested: number };
  unseen: { frames: number; forest: Float32Array; reservoir: Int8Array; features: Float32Array; distance: Float32Array };
}

/** backend/evaluation/validation.py NoveltyGate (F17), same thresholds: withhold a label it cannot stand behind. */
export const NOVELTY_GATE = { minConfidence: 0.55, minMargin: 0.15, maxDistance: 3.0 };
export function noveltyGate(posterior: ArrayLike<number>, distance: number) {
  const p = Array.from(posterior);
  const order = p.map((v, i) => [v, i]).sort((a, b) => b[0] - a[0]);
  const [top, second] = [order[0][0], order[1]?.[0] ?? 0];
  const reasons: string[] = [];
  if (top < NOVELTY_GATE.minConfidence) reasons.push(`posterior ${top.toFixed(2)} below ${NOVELTY_GATE.minConfidence}`);
  if (top - second < NOVELTY_GATE.minMargin) reasons.push(`margin ${(top - second).toFixed(2)} below ${NOVELTY_GATE.minMargin}`);
  if (distance > NOVELTY_GATE.maxDistance) reasons.push(`distance ${distance.toFixed(2)} beyond any known signature`);
  return { unknown: reasons.length > 0, candidate: order[0][1], top, margin: top - second, reasons };
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
