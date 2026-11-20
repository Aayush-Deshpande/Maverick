// Two chapters that argue the architecture itself, both computed live:
//   One frame  - a single telemetry frame through the twelve real pipeline stages, each showing the value it
//                produces at this instant, ending in a real SHA-256 seal of the frame
//   Never seen - a fault in no training library: the closed-set namers (a random forest and the reservoir,
//                trained here on the fault library) must answer with a name they know; the open-set tier,
//                trained on nominal flight only, says abnormal; and the Fly Bloom fleet memory merges
//                across aircraft to exactly what pooling their flights would give, without moving any.
import { FLEET, evaluate, type ScorerName } from './detector';
import { noveltyGate, type Reservoir } from './brain';
import type { Region } from './mind';

const CYAN = '88, 230, 242', ROSE = '255, 79, 139', AMBER = '255, 179, 71', INK = '238, 246, 243';
const MONO = '"JetBrains Mono", ui-monospace, monospace';
const LABEL = '"Sofia Sans Condensed", "Arial Narrow", sans-serif';
const SCORER_NAME: Record<ScorerName, string> = { fly_bloom: 'Fly Bloom', mahalanobis: 'Mahalanobis', max_abs_z: 'max |z|' };
const CLASS_NAME: Record<string, string> = {
  NOMINAL: 'Nominal', OIL_PRESSURE_LOSS: 'Oil pressure loss', COOLING_DEGRADATION: 'Cooling degradation',
  MISFIRE: 'Misfire', AIR_FILTER_BLOCKAGE: 'Air-filter blockage',
};
const text = (g: CanvasRenderingContext2D, s: string, x: number, y: number, font: string, color: string, align: CanvasTextAlign = 'left') => {
  g.font = font; g.fillStyle = color; g.textAlign = align; g.fillText(s, x, y);
};

/** Progress through the edge scene as 0..12, so the score rings a bell on each beat. */
export const pipelineReach = (k: number) => Math.min(11.999, Math.max(0, (k - 0.02) / 0.8) * 12);

// The edge arithmetic, from backend/edge/compressor.py (EdgeCompressor().bandwidth_report on a 4-cylinder frame)
export const EDGE = {
  rawKbit: 160, spareKbit: 22, linkKbit: 100, frameBytes: 29, featKbit: 0.232, ratio: 690, linkPct: 1.1, watts: 9.5, enduranceMin: 0.6,
  // the packed frame's fields and their sizes in bytes (EdgeFeatureFrame.pack)
  fields: [['time', 4], ['orders', 8], ['shape', 4], ['cylinders', 9], ['verdict', 4]] as Array<[string, number]>,
};

/** The vibration of a four-stroke flat-four at crank angle th (degrees): a ringing pulse at every firing. */
function vib(th: number, seed: number) {
  const ph = ((((th % 180) + 180) % 180) / 180);
  const cyl = Math.floor((((th % 720) + 720) % 720) / 180);
  const amp = [1, 0.92, 1.05, 0.97][cyl];
  const noise = Math.sin(th * 0.71 + seed * 13.1) * 0.08 + Math.sin(th * 2.3 + seed * 5.7) * 0.06;
  return amp * Math.exp(-ph / 0.16) * Math.sin(2 * Math.PI * ph * 5.5) + 0.12 * Math.sin((th * Math.PI) / 360) + noise;
}

export function drawPipeline(g: CanvasRenderingContext2D, R: Region, _t: number, k: number, real: number, a: number) {
  if (a <= 0.01) return;
  g.save(); g.globalAlpha = a;
  const W = R.w, x0 = R.x;
  const S = R.compact ? 0.62 : 1;
  const head = (n: string, cap: string, sub: string, y: number, on: number) => {
    g.globalAlpha = a * on;
    text(g, n, x0, y, `800 ${Math.round(13 * S + 2)}px ${MONO}`, `rgba(${CYAN},1)`);
    text(g, cap, x0 + 26, y, `800 ${Math.round(12 * S + 1)}px ${LABEL}`, `rgba(${INK},0.62)`);
    text(g, sub, x0, y + 24 * S + 2, `700 ${Math.round(20 * S + 3)}px ${LABEL}`, `rgba(${INK},1)`);
    g.globalAlpha = a;
  };
  const on = (from: number) => Math.max(0, Math.min(1, (k - from) / 0.06));

  // 1 · the raw signal: what the accelerometer hears, smeared by an engine that never holds one speed
  const yA = R.y + 8, hA = 64 * S;
  head('1', 'AT THE ENGINE', '10,000 vibration samples a second', yA, on(0.02));
  {
    const top = yA + 46 * S, mid = top + hA / 2;
    g.globalAlpha = a * on(0.04) * (1 - 0.55 * on(0.34));
    g.strokeStyle = `rgba(${INK},0.85)`; g.lineWidth = 1.2; g.beginPath();
    for (let i = 0; i <= 600; i++) {
      const u = i / 600, tt = real * 0.9 + u * 0.12;
      const th = 360 * (tt * 30 + 0.6 * Math.sin(tt * 1.7)); // speed wanders: on a clock axis every line smears
      const y = mid - vib(th, 1) * hA * 0.42;
      if (i) g.lineTo(x0 + u * W, y); else g.moveTo(x0, y);
    }
    g.stroke(); g.globalAlpha = a;
  }

  // 2 · order tracking: resample by crank angle and every cycle lands on the same shape
  const yB = yA + 128 * S, hB = 104 * S, wB = R.compact ? W : W * 0.6;
  head('2', 'LOCKED TO THE CRANKSHAFT', 'Every cylinder, every cycle', yB, on(0.3));
  if (k > 0.3) {
    const top = yB + 46 * S, mid = top + hB / 2;
    const lock = Math.max(0, Math.min(1, (k - 0.36) / 0.16)), e2 = lock * lock * (3 - 2 * lock);
    g.globalAlpha = a * on(0.32);
    for (let c = 0; c < 6; c++) {
      const stretch = 1 + (c - 2.5) * 0.07 * (1 - e2);      // each cycle ran at its own speed
      const shift = (c - 2.5) * 9 * (1 - e2);
      g.strokeStyle = `rgba(${e2 > 0.95 ? CYAN : INK},${0.22 + 0.5 * e2})`; g.lineWidth = 1.1; g.beginPath();
      for (let i = 0; i <= 360; i++) {
        const th = (i / 360) * 720, x = x0 + shift + (i / 360) * wB * stretch;
        if (x > x0 + wB) break;
        const y = mid - vib(th, c + 2) * hB * 0.4;
        if (i) g.lineTo(x, y); else g.moveTo(x, y);
      }
      g.stroke();
    }
    // once locked, each firing is a cylinder: the Rotax fires 1-4-2-3
    if (e2 > 0.9) ['1', '4', '2', '3'].forEach((cy, i) => text(g, `cyl ${cy}`, x0 + (i / 4) * wB + 4, top - 2, `700 11px ${MONO}`, `rgba(${CYAN},${(e2 - 0.9) * 10})`));
    text(g, '0°', x0, top + hB + 14, `500 10px ${MONO}`, `rgba(${INK},0.5)`);
    text(g, '720° · one engine cycle', x0 + wB, top + hB + 14, `500 10px ${MONO}`, `rgba(${INK},0.5)`, 'right');
    // the order spectrum: lines that stay put at any throttle
    if (!R.compact) {
      const sx = x0 + W * 0.68, sw = W * 0.32, base = top + hB;
      const orders: Array<[string, number]> = [['½×', 0.12], ['1×', 0.3], ['1½×', 0.1], ['2×', 1], ['3×', 0.22], ['4×', 0.55]];
      const grow = Math.max(0, Math.min(1, (k - 0.46) / 0.1));
      orders.forEach(([n, v], i) => {
        const bw = sw / orders.length, bx = sx + i * bw + bw * 0.2, bh = (hB - 4) * v * grow;
        g.fillStyle = n === '2×' ? `rgba(${CYAN},0.95)` : n === '½×' ? `rgba(${AMBER},0.9)` : `rgba(${INK},0.55)`;
        g.fillRect(bx, base - bh, bw * 0.6, bh);
        text(g, n, bx + bw * 0.3, base + 14, `600 10.5px ${MONO}`, `rgba(${INK},0.7)`, 'center');
      });
      g.globalAlpha = a * grow;
      text(g, 'ORDERS OF CRANK SPEED', sx, top - 6, `700 10px ${LABEL}`, `rgba(${INK},0.55)`);
      text(g, '2× firing · ½× misfire', sx, base + 30, `500 10px ${MONO}`, `rgba(${INK},0.5)`);
    }
    g.globalAlpha = a;
  }

  // 3 · the link: raw cannot fit; the answer barely registers
  const yC = yB + 196 * S;
  head('3', 'ONLY THE ANSWER LEAVES THE AIRCRAFT', `${EDGE.frameBytes} bytes a second · ${EDGE.ratio}× smaller`, yC, on(0.58));
  if (k > 0.58) {
    const top = yC + 52 * S, scale = (W * 0.86) / 180, grow = Math.max(0, Math.min(1, (k - 0.6) / 0.12));
    const bar = (y: number, label: string, kbit: number, col: string) => {
      text(g, label, x0, y - 6, `600 ${R.compact ? 10 : 12}px ${MONO}`, `rgba(${INK},0.85)`);
      g.fillStyle = `rgba(${INK},0.08)`; g.fillRect(x0, y, W * 0.86, 12);
      const len = Math.max(3, kbit * scale * grow), fit = Math.min(len, EDGE.spareKbit * scale);
      g.fillStyle = col; g.fillRect(x0, y, fit, 12);
      if (len > fit) { g.fillStyle = `rgba(${ROSE},0.85)`; g.fillRect(x0 + fit, y, len - fit, 12); }
    };
    bar(top, `raw vibration · ${EDGE.rawKbit} kbit/s`, EDGE.rawKbit, `rgba(${INK},0.6)`);
    bar(top + 40 * S, `ANUMAAN features · ${EDGE.featKbit} kbit/s`, EDGE.featKbit, `rgba(${CYAN},1)`);
    const mx = x0 + EDGE.spareKbit * scale;
    g.fillStyle = `rgba(${INK},0.95)`; g.fillRect(mx - 1, top - 4, 2, 40 * S + 38);
    text(g, `the link has ${EDGE.spareKbit} kbit/s spare`, mx + 6, top + 40 * S + 30, `600 10.5px ${MONO}`, `rgba(${INK},0.75)`);
    if (grow >= 1) text(g, `${(EDGE.rawKbit / EDGE.spareKbit).toFixed(1)}× too much`, x0 + EDGE.rawKbit * scale, top - 6, `700 11px ${MONO}`, `rgba(${ROSE},1)`, 'right');
    // the frame itself, byte by byte, leaving
    if (!R.compact) {
      const py = top + 40 * S + 46, cell = Math.min(15, (W * 0.86) / EDGE.frameBytes - 3);
      const sent = Math.floor((real * 22) % 40);
      let bi = 0;
      EDGE.fields.forEach(([name, n], fi) => {
        const fx = x0 + bi * (cell + 3);
        for (let j = 0; j < n; j++, bi++) {
          g.fillStyle = bi <= sent ? `rgba(${CYAN},${fi % 2 ? 0.7 : 1})` : `rgba(${INK},0.14)`;
          g.fillRect(x0 + bi * (cell + 3), py, cell, cell);
        }
        text(g, name, fx, py + cell + 14, `500 9.5px ${MONO}`, `rgba(${INK},0.55)`);
      });
      text(g, `${EDGE.linkPct}% of the spare link · ${EDGE.watts} W on board ≈ ${EDGE.enduranceMin} min of an 18 h sortie`, x0, py + cell + 30, `500 11px ${MONO}`, `rgba(${INK},0.7)`);
    }
  }
  text(g, 'backend/edge/compressor.py · ml/crank_diagnostics.py · waveform drawn for illustration', x0, R.y + R.h, `400 9.5px ${MONO}`, `rgba(${INK},0.38)`);
  g.restore();
}

export interface UnseenState { frame: number; abnormal: boolean; forestCandidate: number; forestTop: number }

export function drawUnseen(g: CanvasRenderingContext2D, R: Region, k: number, res: Reservoir | null, a: number): UnseenState | null {
  if (a <= 0.01) return null;
  g.save(); g.globalAlpha = a;
  if (!res) { text(g, 'Training the forest and the reservoir…', R.x, R.y + 20, `600 13px ${MONO}`, `rgba(${INK},0.7)`); g.restore(); return null; }
  const U = res.unseen, C = res.classes.length;
  const uf = Math.min(U.frames - 1, Math.floor(Math.max(0, Math.min(1, (k - 0.04) / 0.62)) * (U.frames - 1)));
  const ev = evaluate(Array.from(U.features.slice(uf * 13, uf * 13 + 13)));
  const post = U.forest.slice(uf * C, uf * C + C);
  const gate = noveltyGate(post, U.distance[uf]);
  let withheld = 0, named = 0;
  for (let q = 0; q <= uf; q++) {
    const p = U.forest.slice(q * C, q * C + C); let b = 0; for (let c = 1; c < C; c++) if (p[c] > p[b]) b = c;
    if (b !== 0) { named++; if (noveltyGate(p, U.distance[q]).unknown) withheld++; }
  }
  const big = R.compact ? 18 : 30;
  const colW = R.compact ? R.w : (R.w - 36) / 2;
  const top = R.y + 8;
  text(g, 'SAME UNSEEN FAULT · TWO APPROACHES', R.x, top, `800 11px ${LABEL}`, `rgba(${INK},0.62)`);
  text(g, 'blocked filter + fouled cooling, together: in no training library', R.x + (R.compact ? 0 : 236), top, `500 11px ${MONO}`, `rgba(${INK},0.45)`);
  const ch = R.compact ? 132 : 206, cy = top + 44;
  const nm = CLASS_NAME[res.classes[gate.candidate]] ?? res.classes[gate.candidate];
  const wrong = gate.candidate !== 0;
  const stamp = (x: number, y: number, ok: boolean, label: string) => {
    const r = R.compact ? 13 : 17;
    g.fillStyle = ok ? `rgba(${CYAN},1)` : `rgba(${ROSE},0.95)`;
    g.beginPath(); g.arc(x + r, y, r, 0, Math.PI * 2); g.fill();
    g.strokeStyle = '#061012'; g.lineWidth = 3; g.lineCap = 'round'; g.beginPath();
    if (ok) { g.moveTo(x + r * 0.55, y); g.lineTo(x + r * 0.9, y + r * 0.38); g.lineTo(x + r * 1.5, y - r * 0.4); }
    else { g.moveTo(x + r * 0.6, y - r * 0.4); g.lineTo(x + r * 1.4, y + r * 0.4); g.moveTo(x + r * 1.4, y - r * 0.4); g.lineTo(x + r * 0.6, y + r * 0.4); }
    g.stroke(); g.lineCap = 'butt';
    text(g, label, x + r * 2 + 10, y + 5, `800 ${R.compact ? 13 : 16}px ${LABEL}`, ok ? `rgba(${CYAN},1)` : `rgba(${ROSE},1)`);
  };

  // the usual approach: a classifier trained on known faults, which must answer with one of their names
  const lx = R.x;
  g.fillStyle = 'rgba(6, 12, 14, 0.6)'; g.fillRect(lx, cy, colW, ch);
  g.strokeStyle = `rgba(${INK},0.12)`; g.lineWidth = 1; g.strokeRect(lx + 0.5, cy + 0.5, colW - 1, ch - 1);
  text(g, 'THE USUAL APPROACH', lx + 16, cy + 26, `800 13px ${LABEL}`, `rgba(${INK},0.55)`);
  text(g, `trained classifier (random forest) · taught ${C - 1} faults`, lx + 16, cy + 44, `500 11px ${MONO}`, `rgba(${INK},0.42)`);
  text(g, wrong ? `“${nm}”` : '“All normal”', lx + 16, cy + 44 + big + 8, `800 ${big}px ${LABEL}`, `rgba(${INK},0.5)`);
  if (wrong) {
    const w = g.measureText(`“${nm}”`).width;
    g.fillStyle = `rgba(${ROSE},0.85)`; g.fillRect(lx + 14, cy + 44 + big - big * 0.32, w + 4, 2.5);
  }
  stamp(lx + 16, cy + ch - 34, false, wrong ? `${Math.round(gate.top * 100)}% sure, and wrong` : 'misses it');
  if (!R.compact) text(g, 'It can only pick a fault it was taught.', lx + 16, cy + ch - 8, `500 10.5px ${MONO}`, `rgba(${INK},0.4)`);

  // ours: the fruit-fly circuit, which only learned what normal flight looks like
  const ox = R.compact ? R.x : R.x + colW + 36, oy = R.compact ? cy + ch + 14 : cy;
  const glow = g.createLinearGradient(ox, oy, ox, oy + ch);
  glow.addColorStop(0, 'rgba(88, 230, 242, 0.16)'); glow.addColorStop(1, 'rgba(88, 230, 242, 0.04)');
  g.fillStyle = 'rgba(6, 14, 16, 0.86)'; g.fillRect(ox, oy, colW, ch);
  g.fillStyle = glow; g.fillRect(ox, oy, colW, ch);
  g.strokeStyle = `rgba(${CYAN},0.95)`; g.lineWidth = 2; g.strokeRect(ox + 1, oy + 1, colW - 2, ch - 2);
  // the tab that says whose this is
  const tab = 'ANUMAAN · OURS';
  g.font = `800 11px ${LABEL}`; const tw = g.measureText(tab).width + 18;
  g.fillStyle = `rgba(${CYAN},1)`; g.fillRect(ox, oy - 20, tw, 20);
  text(g, tab, ox + 9, oy - 6, `800 11px ${LABEL}`, '#061012');
  text(g, 'FLY BLOOM · THE FRUIT-FLY CIRCUIT', ox + 16, oy + 26, `800 13px ${LABEL}`, `rgba(${CYAN},1)`);
  text(g, 'learned normal flight only · zero fault labels', ox + 16, oy + 44, `500 11px ${MONO}`, `rgba(${INK},0.7)`);
  text(g, ev.raw ? 'ABNORMAL' : 'listening…', ox + 16, oy + 44 + big + 8, `800 ${big}px ${LABEL}`, ev.raw ? `rgba(${INK},1)` : `rgba(${INK},0.55)`);
  if (ev.raw) stamp(ox + 16, oy + ch - 34, true, 'caught · flagged as never seen');
  else text(g, `${SCORER_NAME.fly_bloom} ${ev.ratios.fly_bloom.toFixed(2)}× of threshold`, ox + 16, oy + ch - 30, `600 13px ${MONO}`, `rgba(${INK},0.6)`);
  if (!R.compact) text(g, 'It does not need a name to know.', ox + 16, oy + ch - 8, `500 10.5px ${MONO}`, `rgba(${INK},0.6)`);

  // and its memory merges across the fleet: three aircraft, 260 numbers each
  const fy = (R.compact ? oy : cy) + ch + 40;
  const merge = Math.max(0, Math.min(1, (k - 0.62) / 0.16));
  text(g, 'EACH AIRCRAFT REMEMBERS NORMAL IN 260 NUMBERS', R.x, fy, `800 11px ${LABEL}`, `rgba(${INK},0.62)`);
  const strips = [...FLEET.tails.map((tl) => ({ name: tl.id, f: tl.freq })), { name: 'FLEET', f: FLEET.merged }];
  const sw = R.w - 70, cell = sw / 260;
  strips.forEach((st, i) => {
    const y = fy + 14 + i * 17 + (i === 3 ? 8 : 0);
    if (i === 3 && merge <= 0) return;
    for (let u = 0; u < 260; u++) {
      const v = Math.min(1, st.f[u] / 0.1);
      g.fillStyle = i === 3 ? `rgba(${CYAN},${(0.1 + 0.9 * v) * merge})` : `rgba(${INK},${0.06 + 0.7 * v})`;
      g.fillRect(R.x + u * cell, y, Math.max(1, cell - 0.4), 12);
    }
    text(g, st.name, R.x + sw + 10, y + 10, `600 10.5px ${MONO}`, i === 3 ? `rgba(${CYAN},${merge})` : `rgba(${INK},0.55)`);
  });
  if (merge > 0.5) {
    text(g, 'Merged, the fleet learns together. No telemetry leaves an aircraft.', R.x, fy + 14 + 4 * 17 + 30, `700 ${R.compact ? 12 : 16}px ${LABEL}`, `rgba(${CYAN},1)`);
  }
  text(g, 'Simulation. Fly Bloom is one of three detectors; the merge equals pooling every flight (max diff 2e-15).', R.x, R.y + R.h, `400 9.5px ${MONO}`, `rgba(${INK},0.38)`);
  g.restore();
  return { frame: uf, abnormal: ev.raw, forestCandidate: gate.candidate, forestTop: gate.top };
}
