/// <reference lib="webworker" />
// Tier-1 of ANUMAAN's detector in the browser, mirroring backend/detect/reservoir.py and
// EngineRuntime.ensure_heavy: a frozen 500-node sparse leaky reservoir (12 links per node, spectral radius
// 0.9, leak 0.3, input density 0.1) with a closed-form ridge readout fitted on a simulated fault library
// (nominal + four faults, two runs each, 260 frames, faults ramped to severity 0.9, labelled from frame 150).
// It then replays the film's own sortie so the Memory chapter shows the reservoir actually reading it.
import { CHANNELS, FRAME, SIGNATURES, TOTAL, featuresAt, featurize, gauss } from './story';

const N = 500, NNZ = 12, RHO = 0.9, LEAK = 0.3, IN_DENSITY = 0.1;
const N_IN = 13, SHOW = 180;
const CLASSES = ['NOMINAL', 'OIL_PRESSURE_LOSS', 'COOLING_DEGRADATION', 'MISFIRE', 'AIR_FILTER_BLOCKAGE'];

function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const rng = mulberry32(42);
const normal = () => Math.sqrt(-2 * Math.log(rng() + 1e-12)) * Math.cos(2 * Math.PI * rng());

// W: sparse, row-major lists (row = post-synaptic node)
const Wcol = new Int32Array(N * NNZ), Wval = new Float64Array(N * NNZ);
for (let i = 0; i < N * NNZ; i++) { Wcol[i] = Math.floor(rng() * N); Wval[i] = normal(); }
function mulW(x: Float64Array, out: Float64Array) {
  for (let r = 0; r < N; r++) { let s = 0; for (let k = r * NNZ; k < (r + 1) * NNZ; k++) s += Wval[k] * x[Wcol[k]]; out[r] = s; }
}
// spectral radius by the asymptotic growth rate of power iteration, then rescale to RHO
{
  let v = new Float64Array(N).map(() => normal()), w = new Float64Array(N), logSum = 0, count = 0;
  for (let it = 0; it < 160; it++) {
    mulW(v, w); let nrm = 0; for (let i = 0; i < N; i++) nrm += w[i] * w[i]; nrm = Math.sqrt(nrm) || 1e-12;
    for (let i = 0; i < N; i++) v[i] = w[i] / nrm;
    if (it >= 60) { logSum += Math.log(nrm); count++; }
  }
  const radius = Math.exp(logSum / count);
  for (let i = 0; i < Wval.length; i++) Wval[i] *= RHO / Math.max(radius, 1e-9);
}
const Win = new Float64Array(N * N_IN);
for (let i = 0; i < Win.length; i++) Win[i] = rng() < IN_DENSITY ? 0.5 * normal() : 0;

const x = new Float64Array(N), pre = new Float64Array(N);
function reset() { x.fill(0); }
function step(u: number[]) {
  mulW(x, pre);
  for (let r = 0; r < N; r++) {
    let s = pre[r];
    for (let j = 0; j < N_IN; j++) s += Win[r * N_IN + j] * Math.max(-10, Math.min(10, u[j]));
    x[r] = (1 - LEAK) * x[r] + LEAK * Math.tanh(s);
  }
}

// ---- the simulated fault library
function run(fault: string | null, seed: number) {
  const U: number[][] = [];
  for (let f = 0; f < 260; f++) {
    const z = CHANNELS.map((_, ch) => gauss(seed * 1000 + f, ch + 31));
    if (fault) SIGNATURES[fault](0.9 * Math.min(1, f / 120), z);
    U.push(featurize(z));
  }
  return U;
}
const rows: Float64Array[] = [], labels: number[] = [], feats: number[][] = [];
for (let k = 0; k < 2; k++) {
  const nominal = run(null, 300 + k);
  reset(); nominal.forEach((u, f) => { step(u); if (f >= 30) { rows.push(Float64Array.from(x)); labels.push(0); feats.push(u); } });
  CLASSES.slice(1).forEach((c, ci) => {
    const U = run(c, 400 + k * 10 + ci);
    reset(); U.forEach((u, f) => { step(u); if (f >= 150) { rows.push(Float64Array.from(x)); labels.push(ci + 1); feats.push(u); } });
  });
}

// ---- ridge readout: (S1^T S1 + I) B = S1^T T, solved by Cholesky
const P = N + 1, C = CLASSES.length, S = rows.length;
const G = new Float64Array(P * P), Bt = new Float64Array(P * C);
for (let s = 0; s < S; s++) {
  const r = rows[s];
  const row = (i: number) => (i < N ? r[i] : 1);
  for (let i = 0; i < P; i++) {
    const ri = row(i); if (ri === 0) continue;
    for (let j = i; j < P; j++) G[i * P + j] += ri * row(j);
    for (let c = 0; c < C; c++) Bt[i * C + c] += ri * (labels[s] === c ? 1 : -1);
  }
}
for (let i = 0; i < P; i++) { G[i * P + i] += 1.0; for (let j = 0; j < i; j++) G[i * P + j] = G[j * P + i]; }
for (let j = 0; j < P; j++) { // in-place Cholesky, lower triangle
  let d = G[j * P + j]; for (let k = 0; k < j; k++) d -= G[j * P + k] ** 2;
  d = Math.sqrt(Math.max(d, 1e-12)); G[j * P + j] = d;
  for (let i = j + 1; i < P; i++) { let s = G[i * P + j]; for (let k = 0; k < j; k++) s -= G[i * P + k] * G[j * P + k]; G[i * P + j] = s / d; }
}
const readout = new Float64Array(P * C);
for (let c = 0; c < C; c++) {
  const y = new Float64Array(P);
  for (let i = 0; i < P; i++) { let s = Bt[i * C + c]; for (let k = 0; k < i; k++) s -= G[i * P + k] * y[k]; y[i] = s / G[i * P + i]; }
  for (let i = P - 1; i >= 0; i--) { let s = y[i]; for (let k = i + 1; k < P; k++) s -= G[k * P + i] * readout[k * C + c]; readout[i * C + c] = s / G[i * P + i]; }
}

// ---- the state space, for drawing: top two principal components of the training states
const mean = new Float64Array(N);
rows.forEach((r) => { for (let i = 0; i < N; i++) mean[i] += r[i] / S; });
function pc(deflate: Float64Array[]) {
  let v = new Float64Array(N).map(() => normal());
  for (let it = 0; it < 50; it++) {
    const w = new Float64Array(N);
    for (const r of rows) { let d = 0; for (let i = 0; i < N; i++) d += (r[i] - mean[i]) * v[i]; for (let i = 0; i < N; i++) w[i] += d * (r[i] - mean[i]); }
    for (const u of deflate) { let d = 0; for (let i = 0; i < N; i++) d += w[i] * u[i]; for (let i = 0; i < N; i++) w[i] -= d * u[i]; }
    let nrm = 0; for (let i = 0; i < N; i++) nrm += w[i] * w[i]; nrm = Math.sqrt(nrm) || 1; v = w.map((q) => q / nrm);
  }
  return v;
}
const pc1 = pc([]), pc2 = pc([pc1]);
const projectState = (s: Float64Array) => { let a = 0, b = 0; for (let i = 0; i < N; i++) { const d = s[i] - mean[i]; a += d * pc1[i]; b += d * pc2[i]; } return [a, b]; };
const centroids = CLASSES.map((_, c) => {
  let a = 0, b = 0, n = 0; rows.forEach((r, s) => { if (labels[s] === c) { const [p, q] = projectState(r); a += p; b += q; n++; } });
  return [a / n, b / n];
});

// ---- replay the film's sortie through the trained reservoir
const FRAMES = Math.ceil(TOTAL / FRAME) + 1;
const scores = new Float32Array(FRAMES * C), path = new Float32Array(FRAMES * 2), act = new Float32Array(FRAMES * SHOW);
const label = new Int8Array(FRAMES);
reset();
for (let f = 0; f < FRAMES; f++) {
  step(featuresAt(f));
  let best = 0;
  for (let c = 0; c < C; c++) {
    let s = readout[N * C + c]; for (let i = 0; i < N; i++) s += x[i] * readout[i * C + c];
    scores[f * C + c] = s; if (s > scores[f * C + best]) best = c;
  }
  label[f] = best;
  const [a, b] = projectState(x); path[f * 2] = a; path[f * 2 + 1] = b;
  for (let i = 0; i < SHOW; i++) act[f * SHOW + i] = x[i];
}

// a drawable slice of the network: the first SHOW nodes, the links among them, a fixed layout
const edges: number[] = [];
for (let r = 0; r < SHOW; r++) for (let k = r * NNZ; k < (r + 1) * NNZ; k++) if (Wcol[k] < SHOW) edges.push(Wcol[k], r);
const layout = new Float32Array(SHOW * 2);
for (let i = 0; i < SHOW; i++) { const a = rng() * Math.PI * 2, d = Math.sqrt(rng()); layout[i * 2] = Math.cos(a) * d; layout[i * 2 + 1] = Math.sin(a) * d; }

// what the reservoir and its readout reported on the training library itself (frame-level accuracy)
let correct = 0;
rows.forEach((r, s) => { let best = 0, bs = -Infinity; for (let c = 0; c < C; c++) { let v = readout[N * C + c]; for (let i = 0; i < N; i++) v += r[i] * readout[i * C + c]; if (v > bs) { bs = v; best = c; } } if (best === labels[s]) correct++; });

// ---- the comparison: a random forest on the same labelled library (what a conventional ensemble needs)
interface Node { f: number; thr: number; l: number; r: number; leaf: Float64Array | null }
const NTREES = 60, MTRY = 4, MAXDEPTH = 12, MINLEAF = 3;
const forest: Node[][] = [];
const tForest = performance.now();
for (let tr = 0; tr < NTREES; tr++) {
  const idx = Array.from({ length: feats.length }, () => Math.floor(rng() * feats.length));
  const nodes: Node[] = [];
  const build = (ids: number[], depth: number): number => {
    const counts = new Float64Array(C); ids.forEach((i) => { counts[labels[i]]++; });
    const pure = counts.filter((c) => c > 0).length <= 1;
    if (pure || depth >= MAXDEPTH || ids.length < 2 * MINLEAF) {
      nodes.push({ f: -1, thr: 0, l: -1, r: -1, leaf: counts.map((c) => c / ids.length) }); return nodes.length - 1;
    }
    const gini = (c: Float64Array, n: number) => { let g = 1; for (let k = 0; k < C; k++) g -= (c[k] / n) ** 2; return g; };
    let best = { score: Infinity, f: -1, thr: 0 };
    const pool = Array.from({ length: N_IN }, (_, i) => i);
    for (let m = 0; m < MTRY; m++) {
      const j = m + Math.floor(rng() * (N_IN - m)); [pool[m], pool[j]] = [pool[j], pool[m]];
      const f = pool[m];
      const sorted = [...ids].sort((a, b) => feats[a][f] - feats[b][f]);
      const left = new Float64Array(C), right = Float64Array.from(counts);
      for (let q = 0; q < sorted.length - 1; q++) {
        const lab = labels[sorted[q]]; left[lab]++; right[lab]--;
        const v = feats[sorted[q]][f], vn = feats[sorted[q + 1]][f];
        if (v === vn || q + 1 < MINLEAF || sorted.length - q - 1 < MINLEAF) continue;
        const nl = q + 1, nr = sorted.length - nl;
        const sc = (nl * gini(left, nl) + nr * gini(right, nr)) / sorted.length;
        if (sc < best.score) best = { score: sc, f, thr: (v + vn) / 2 };
      }
    }
    if (best.f < 0) { nodes.push({ f: -1, thr: 0, l: -1, r: -1, leaf: counts.map((c) => c / ids.length) }); return nodes.length - 1; }
    const me = nodes.length; nodes.push({ f: best.f, thr: best.thr, l: -1, r: -1, leaf: null });
    const L = ids.filter((i) => feats[i][best.f] <= best.thr), R = ids.filter((i) => feats[i][best.f] > best.thr);
    nodes[me].l = build(L, depth + 1); nodes[me].r = build(R, depth + 1);
    return me;
  };
  build(idx, 0);
  forest.push(nodes);
}
const forestMs = performance.now() - tForest;
function forestProba(u: number[]) {
  const p = new Float64Array(C);
  for (const nodes of forest) { let n = nodes[0]; while (!n.leaf) n = nodes[u[n.f] <= n.thr ? n.l : n.r]; for (let k = 0; k < C; k++) p[k] += n.leaf[k] / NTREES; }
  return p;
}
// held-out check on faults the models were trained for (fresh seeds), so the comparison is fair
let fCorrect = 0, rCorrect = 0, tested = 0;
CLASSES.forEach((c, ci) => {
  const U = run(ci === 0 ? null : c, 900 + ci);
  reset();
  U.forEach((u, f) => {
    step(u);
    if (f < (ci === 0 ? 30 : 150)) return;
    const p = forestProba(u); let bf = 0; for (let k = 1; k < C; k++) if (p[k] > p[bf]) bf = k;
    let br = 0, bs = -Infinity; for (let k = 0; k < C; k++) { let v = readout[N * C + k]; for (let i = 0; i < N; i++) v += x[i] * readout[i * C + k]; if (v > bs) { bs = v; br = k; } }
    fCorrect += bf === ci ? 1 : 0; rCorrect += br === ci ? 1 : 0; tested++;
  });
});
// known signatures in feature space (class means of the library), for NoveltyGate's distance test
const sig = CLASSES.map((_, c) => {
  const m = new Float64Array(N_IN); let n = 0;
  feats.forEach((u, i) => { if (labels[i] === c) { for (let j = 0; j < N_IN; j++) m[j] += u[j]; n++; } });
  return Array.from(m, (v) => v / Math.max(1, n));
});
// the unseen fault: in no library, ramped over 100 frames to severity 0.9
const UF = 100;
const unseenFeat: number[][] = [];
const unseenForest = new Float32Array(UF * C), unseenRes = new Int8Array(UF);
reset();
for (let f = 0; f < UF; f++) {
  const z = CHANNELS.map((_, ch) => gauss(770000 + f, ch + 31));
  SIGNATURES.DUST_COMPOUND(0.9 * Math.min(1, f / 60), z);
  const u = featurize(z); unseenFeat.push(u);
  const p = forestProba(u); for (let k = 0; k < C; k++) unseenForest[f * C + k] = p[k];
  step(u);
  let br = 0, bs = -Infinity; for (let k = 0; k < C; k++) { let v = readout[N * C + k]; for (let i = 0; i < N; i++) v += x[i] * readout[i * C + k]; if (v > bs) { bs = v; br = k; } }
  unseenRes[f] = br;
}

(self as unknown as Worker).postMessage({
  forest: { trees: NTREES, maxDepth: MAXDEPTH, trainMs: forestMs, knownAccuracy: fCorrect / tested, reservoirKnownAccuracy: rCorrect / tested, tested },
  unseen: {
    frames: UF, forest: unseenForest, reservoir: unseenRes, features: Float32Array.from(unseenFeat.flat()),
    // distance (z-units, RMS over features) from each frame to the nearest known signature
    distance: Float32Array.from(unseenFeat.map((u) => Math.min(...sig.map((m) => Math.sqrt(m.reduce((s2, v, j) => s2 + (u[j] - v) ** 2, 0) / N_IN))))),
  },
  classes: CLASSES, frames: FRAMES, show: SHOW, nodes: N,
  scores, path, act, label, edges: Int32Array.from(edges), layout,
  centroids: Float32Array.from(centroids.flat()), trainAccuracy: correct / S, trainFrames: S,
}, [scores.buffer, path.buffer, act.buffer, label.buffer, layout.buffer]);
