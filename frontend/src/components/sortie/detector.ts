// Tier-0 of ANUMAAN's detector, ported to the browser with the backend's algorithms and parameters
// (backend/detect/detector.py, scorers.py, backend/ml/flyhash_novelty.py):
//   13 calibrated features -> {Fly Bloom, Mahalanobis, max|z|} -> split-conformal threshold per scorer
//   (alpha 0.01, fitted on held-out nominal frames) -> raw alarm if any scorer is over -> persistence gate
//   (3 of the last 5 frames) -> confirmed.
// It is calibrated here on nominal frames and then reads the film's own sensor stream, so every number the
// film shows in the Detect chapter is computed, not scripted. Random seeds differ from the backend's.
import { FEATURES, FRAME, T_INJECT, TOTAL, featuresAt, featurize, gauss } from './story';

const D = FEATURES.length;           // 13
export const EXPANSION = 20;         // FlyHash: 13 -> 260 units
export const FAN_IN = 6;             // each unit samples 6 inputs
export const SPARSITY = 0.05;        // keep the top 5%
export const ALPHA = 0.01;           // conformal false-alarm target per scorer
export const GATE = { k: 3, n: 5 };
const F0 = 0.05;
const M = D * EXPANSION;
const K = Math.max(1, Math.round(M * SPARSITY)); // 13 winners

function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

/* ---- FlyHash: fixed sparse random projection + winner-take-all (SparseRandomProjection, FlyHashEncoder) */
const rng = mulberry32(7);
export const PROJ_COLS: number[][] = [];
export const PROJ_SIGN: number[][] = [];
for (let r = 0; r < M; r++) {
  const pool = Array.from({ length: D }, (_, i) => i);
  for (let i = pool.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [pool[i], pool[j]] = [pool[j], pool[i]]; }
  PROJ_COLS.push(pool.slice(0, FAN_IN));
  PROJ_SIGN.push(Array.from({ length: FAN_IN }, () => (rng() < 0.5 ? -1 : 1)));
}
export function project(x: number[]) {
  const y = new Float64Array(M);
  for (let r = 0; r < M; r++) { let s = 0; const c = PROJ_COLS[r], g = PROJ_SIGN[r]; for (let j = 0; j < FAN_IN; j++) s += g[j] * x[c[j]]; y[r] = s; }
  return y;
}
export function winners(x: number[]) {
  const y = project(x);
  return Array.from(y.keys()).sort((a, b) => y[b] - y[a]).slice(0, K);
}

/* ---- calibration on nominal frames (fit set + held-out set), as ResidualDetector.calibrate */
const nominal = (i: number) => featurize(Array.from({ length: D }, (_, ch) => gauss(100000 + i, ch + 17)));
const FIT = Array.from({ length: 700 }, (_, i) => nominal(i));
const HOLD = Array.from({ length: 400 }, (_, i) => nominal(5000 + i));

// Fly Bloom: frequency memory of nominal activations; score = 1 - mean familiarity of the active units
const FREQ = new Float64Array(M);
for (const x of FIT) for (const w of winners(x)) FREQ[w] += 1 / FIT.length;
export const familiarity = (w: number) => Math.min(1, FREQ[w] / F0);

// Mahalanobis: mean and (pseudo)inverse covariance of the fit set
const MU = Array.from({ length: D }, (_, j) => FIT.reduce((s, x) => s + x[j], 0) / FIT.length);
const COV = Array.from({ length: D }, (_, i) => Array.from({ length: D }, (_, j) =>
  FIT.reduce((s, x) => s + (x[i] - MU[i]) * (x[j] - MU[j]), 0) / (FIT.length - 1) + (i === j ? 1e-6 : 0)));
const P = invert(COV);
function invert(A: number[][]) {
  const n = A.length, a = A.map((r, i) => [...r, ...Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))]);
  for (let c = 0; c < n; c++) {
    let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(a[r][c]) > Math.abs(a[p][c])) p = r;
    [a[c], a[p]] = [a[p], a[c]];
    const d = a[c][c] || 1e-12; for (let j = 0; j < 2 * n; j++) a[c][j] /= d;
    for (let r = 0; r < n; r++) if (r !== c) { const f = a[r][c]; if (f) for (let j = 0; j < 2 * n; j++) a[r][j] -= f * a[c][j]; }
  }
  return a.map((r) => r.slice(n));
}

export type ScorerName = 'fly_bloom' | 'mahalanobis' | 'max_abs_z';
export const SCORERS: ScorerName[] = ['fly_bloom', 'mahalanobis', 'max_abs_z'];
function scores(x: number[]): Record<ScorerName, number> {
  const w = winners(x);
  const fly = 1 - w.reduce((s, u) => s + familiarity(u), 0) / w.length;
  const d = x.map((v, i) => v - MU[i]);
  let m = 0; for (let i = 0; i < D; i++) for (let j = 0; j < D; j++) m += d[i] * P[i][j] * d[j];
  return { fly_bloom: fly, mahalanobis: Math.sqrt(Math.max(0, m)), max_abs_z: Math.max(...x.map(Math.abs)) };
}

// split-conformal upper quantile: ceil((n+1)(1-alpha))/n-th order statistic of held-out nominal scores
const held = HOLD.map(scores);
export const THRESHOLDS = Object.fromEntries(SCORERS.map((s) => {
  const v = held.map((h) => h[s]).sort((a, b) => a - b);
  const k = Math.min(v.length, Math.ceil((v.length + 1) * (1 - ALPHA)));
  return [s, v[k - 1]];
})) as Record<ScorerName, number>;

/* ---- the film's sortie, frame by frame */
export interface Tier0 {
  frame: number;
  features: number[];
  ratios: Record<ScorerName, number>;
  raw: boolean;
  /** the last GATE.n raw decisions, oldest first */
  window: boolean[];
  confirmed: boolean;
  winners: number[];
}
const FRAMES = Math.ceil(TOTAL / FRAME) + 1;
const TL: Tier0[] = [];
for (let f = 0; f < FRAMES; f++) {
  const x = featuresAt(f);
  const s = scores(x);
  const ratios = Object.fromEntries(SCORERS.map((n) => [n, s[n] / Math.max(THRESHOLDS[n], 1e-12)])) as Record<ScorerName, number>;
  const raw = SCORERS.some((n) => ratios[n] > 1);
  const window = [...(TL.slice(Math.max(0, f - GATE.n + 1)).map((t) => t.raw)), raw];
  const confirmed = window.filter(Boolean).length >= GATE.k;
  TL.push({ frame: f, features: x, ratios, raw, window: window.slice(-GATE.n), confirmed, winners: winners(x) });
}
export const tier0 = (t: number) => TL[Math.min(TL.length - 1, Math.max(0, Math.floor(t / FRAME)))];

const injectFrame = Math.floor(T_INJECT / FRAME);
const firstConfirm = TL.findIndex((x) => x.confirmed);
let runStart = firstConfirm < 0 ? TL.length - 1 : firstConfirm;
while (runStart > injectFrame && TL[runStart - 1].raw) runStart--;
/** Start of the raw-alarm run the gate confirms, and the frame it confirms (story seconds). */
export const T_CROSS = runStart * FRAME;
export const T_CONFIRM = (firstConfirm < 0 ? TL.length : firstConfirm) * FRAME;
/** Raw alarms before the fault existed: the gate is what keeps them from paging anyone. */
export const NOMINAL_RAW = TL.filter((x) => x.frame < injectFrame && x.raw).length;
export const NOMINAL_CONFIRMED = TL.filter((x) => x.frame < injectFrame && x.confirmed).length;
export const SPEC = { D, M, K, F0 };

/* ---- any stream, not just the film's sortie: score one feature vector */
export function evaluate(x: number[]) {
  const s = scores(x);
  const ratios = Object.fromEntries(SCORERS.map((n) => [n, s[n] / Math.max(THRESHOLDS[n], 1e-12)])) as Record<ScorerName, number>;
  const w = winners(x);
  /** fraction of the firing units that never fired in nominal flight (FlyNoveltyDetector's question) */
  const unseen = w.filter((u) => FREQ[u] === 0).length / w.length;
  return { ratios, raw: SCORERS.some((n) => ratios[n] > 1), winners: w, unseen };
}

/* ---- the fleet: three tails, each with its own nominal memory, merged by weighted average of the
   frequency memories (FlyBloomScorer.merge, backlog W12): no raw telemetry leaves any aircraft */
export const FLEET = (() => {
  const tails = [
    { id: 'Tail 01', frames: 700, seed: 210000 },
    { id: 'Tail 02', frames: 420, seed: 320000 },
    { id: 'Tail 03', frames: 560, seed: 430000 },
  ].map((tl) => {
    const f = new Float64Array(M);
    for (let i = 0; i < tl.frames; i++) {
      const x = featurize(Array.from({ length: D }, (_, ch) => gauss(tl.seed + i, ch + 17)));
      for (const w of winners(x)) f[w] += 1 / tl.frames;
    }
    return { ...tl, freq: f };
  });
  const total = tails.reduce((s, t) => s + t.frames, 0);
  const merged = new Float64Array(M);
  tails.forEach((t) => { for (let u = 0; u < M; u++) merged[u] += (t.freq[u] * t.frames) / total; });
  // the same memory computed the other way: every tail's nominal frames pooled in one place
  const pooled = new Float64Array(M);
  tails.forEach((tl) => {
    for (let i = 0; i < tl.frames; i++) {
      const x = featurize(Array.from({ length: D }, (_, ch) => gauss(tl.seed + i, ch + 17)));
      for (const w of winners(x)) pooled[w] += 1 / total;
    }
  });
  let maxDiff = 0;
  for (let u = 0; u < M; u++) maxDiff = Math.max(maxDiff, Math.abs(pooled[u] - merged[u]));
  return { tails, merged, pooledMaxDiff: maxDiff, bytes: M * 8, frames: total };
})();
