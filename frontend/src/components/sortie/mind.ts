// Draws the detector as it computes: the Detect chapter (tier-0: features -> FlyHash -> Fly Bloom, the
// three scorers against their conformal thresholds, the persistence gate) and the Memory chapter (the
// reservoir's nodes, its state path, its readout). Every value drawn comes from detector.ts or the
// reservoir worker; nothing here is decorative data.
import { FEATURES, FRAME, T_INJECT } from './story';
import { GATE, PROJ_COLS, PROJ_SIGN, SCORERS, SPEC, THRESHOLDS, familiarity, tier0, type ScorerName } from './detector';
import type { Reservoir } from './brain';

const CYAN = '88, 230, 242', ROSE = '255, 79, 139', AMBER = '255, 179, 71', INK = '238, 246, 243';
const MONO = '"JetBrains Mono", ui-monospace, monospace';
const LABEL = '"Sofia Sans Condensed", "Arial Narrow", sans-serif';
const SCORER_NAME: Record<ScorerName, string> = { fly_bloom: 'Fly Bloom', mahalanobis: 'Mahalanobis', max_abs_z: 'max |z|' };
const CLASS_NAME: Record<string, string> = {
  NOMINAL: 'Nominal', OIL_PRESSURE_LOSS: 'Oil pressure loss', COOLING_DEGRADATION: 'Cooling degradation',
  MISFIRE: 'Misfire', AIR_FILTER_BLOCKAGE: 'Air-filter blockage',
};

export interface Region { x: number; y: number; w: number; h: number; compact: boolean }

/** Where the overlay may draw: right of the story copy on wide screens, the top half on phones. */
export function region(w: number, h: number, lb: number): Region {
  if (w < 760) return { x: 16, y: 64, w: w - 32, h: h - 64 - 190, compact: true };
  const x = Math.max(w * 0.42, 560);
  return { x, y: lb + 70, w: w - x - Math.max(24, w * 0.03), h: h - lb - 70 - 90, compact: false };
}

const text = (g: CanvasRenderingContext2D, s: string, x: number, y: number, font: string, color: string, align: CanvasTextAlign = 'left') => {
  g.font = font; g.fillStyle = color; g.textAlign = align; g.fillText(s, x, y);
};

/* ---------------------------------------------------------------- Detect: tier-0, live */
export function drawDetect(g: CanvasRenderingContext2D, R: Region, t: number, a: number) {
  if (a <= 0.01) return;
  const d = tier0(t);
  g.save(); g.globalAlpha = a;
  const fx = R.x, fw = R.compact ? 92 : 120;              // features column
  const kx = fx + fw + (R.compact ? 18 : 40);              // the 260 units
  const sx = R.compact ? R.x : R.x + R.w * 0.66;           // scorers column (below on phones)
  const kw = (R.compact ? R.x + R.w : sx - 40) - kx;
  const top = R.y + 22, rowH = Math.min(R.compact ? 16 : 26, (R.compact ? R.h * 0.62 : R.h * 0.7) / FEATURES.length);
  text(g, 'CALIBRATED FEATURES', fx, R.y + 4, `700 10.5px ${LABEL}`, `rgba(${INK},0.6)`);
  text(g, `FLYHASH  ${SPEC.D} → ${SPEC.M} UNITS · FAN-IN 6 · TOP ${SPEC.K}`, kx, R.y + 4, `700 10.5px ${LABEL}`, `rgba(${INK},0.6)`);

  // features: value as a signed bar
  const featY = (i: number) => top + i * rowH + rowH / 2;
  d.features.forEach((v, i) => {
    const y = featY(i);
    text(g, FEATURES[i], fx, y + 4, `500 ${R.compact ? 9.5 : 11}px ${MONO}`, `rgba(${INK},0.75)`);
    const bx = fx + fw - 34, len = Math.max(-1, Math.min(1, v / 8)) * 30;
    g.fillStyle = Math.abs(v) > 3 ? `rgba(${AMBER},0.95)` : `rgba(${CYAN},0.7)`;
    g.fillRect(len < 0 ? bx + len : bx, y - 2, Math.abs(len), 4);
  });

  // the 260 units, 13 rows x 20; winners lit and wired to their six real inputs
  const cols = 20, rows = Math.ceil(SPEC.M / cols);
  const cw = kw / cols, ch = Math.min(rowH, (rowH * FEATURES.length) / rows);
  const unitXY = (u: number) => [kx + (u % cols) * cw + cw / 2, top + Math.floor(u / cols) * ch + ch / 2];
  const win = new Set(d.winners);
  for (const u of d.winners) {
    const [ux, uy] = unitXY(u);
    PROJ_COLS[u].forEach((c, j) => {
      g.strokeStyle = PROJ_SIGN[u][j] > 0 ? `rgba(${CYAN},0.18)` : `rgba(${AMBER},0.18)`;
      g.lineWidth = 1; g.beginPath(); g.moveTo(fx + fw - 2, featY(c)); g.lineTo(ux, uy); g.stroke();
    });
  }
  for (let u = 0; u < SPEC.M; u++) {
    const [ux, uy] = unitXY(u);
    if (win.has(u)) {
      const fam = familiarity(u);
      g.fillStyle = fam >= 1 ? `rgba(${CYAN},1)` : `rgba(${ROSE},${0.55 + 0.45 * (1 - fam)})`;
      g.beginPath(); g.arc(ux, uy, Math.min(cw, ch) * 0.36, 0, Math.PI * 2); g.fill();
    } else {
      g.fillStyle = `rgba(${INK},0.12)`; g.fillRect(ux - 1, uy - 1, 2, 2);
    }
  }
  const novel = d.winners.filter((u) => familiarity(u) < 1).length;
  text(g, `${d.winners.length - novel} familiar · ${novel} never fired in nominal flight`, kx, top + rows * ch + 16,
    `500 ${R.compact ? 9.5 : 11}px ${MONO}`, novel ? `rgba(${ROSE},0.95)` : `rgba(${CYAN},0.9)`);

  // scorers against split-conformal thresholds, raw alarm, persistence gate
  const sy = R.compact ? top + rows * ch + 34 : top;
  const sw = R.compact ? R.w : R.x + R.w - sx;
  text(g, `THREE SCORERS · SPLIT-CONFORMAL α = 0.01`, sx, sy - 4 + (R.compact ? 0 : -18), `700 10.5px ${LABEL}`, `rgba(${INK},0.6)`);
  SCORERS.forEach((s, i) => {
    const y = sy + 8 + i * 34, r = d.ratios[s];
    text(g, SCORER_NAME[s], sx, y + 4, `600 12px ${LABEL}`, `rgba(${INK},0.85)`);
    text(g, `${r.toFixed(2)}×`, sx + sw, y + 4, `600 12px ${MONO}`, r > 1 ? `rgba(${AMBER},1)` : `rgba(${INK},0.85)`, 'right');
    const by = y + 10, bw = sw, full = 2.5;
    g.fillStyle = `rgba(${INK},0.1)`; g.fillRect(sx, by, bw, 5);
    g.fillStyle = r > 1 ? `rgba(${AMBER},0.95)` : `rgba(${CYAN},0.85)`; g.fillRect(sx, by, bw * Math.min(1, r / full), 5);
    g.fillStyle = `rgba(${INK},0.95)`; g.fillRect(sx + bw / full - 1, by - 4, 2, 13);
  });
  text(g, `thr  ${THRESHOLDS.fly_bloom.toFixed(2)} · ${THRESHOLDS.mahalanobis.toFixed(2)} · ${THRESHOLDS.max_abs_z.toFixed(2)}`, sx, sy + 8 + 3 * 34 + 2, `500 10.5px ${MONO}`, `rgba(${INK},0.5)`);
  const gy = sy + 8 + 3 * 34 + 26;
  text(g, `PERSISTENCE GATE · ${GATE.k} OF THE LAST ${GATE.n} FRAMES`, sx, gy, `700 10.5px ${LABEL}`, `rgba(${INK},0.6)`);
  const slot = Math.min(36, (sw - 4 * 6) / GATE.n);
  const window = [...Array(Math.max(0, GATE.n - d.window.length)).fill(false), ...d.window];
  window.forEach((on, i) => {
    g.fillStyle = on ? `rgba(${AMBER},0.95)` : `rgba(${INK},0.12)`;
    g.fillRect(sx + i * (slot + 6), gy + 10, slot, 12);
  });
  const hits = d.window.filter(Boolean).length;
  const confirmed = d.confirmed;
  text(g, confirmed ? 'CONFIRMED · PAGE THE CREW' : d.raw ? `RAW ALARM · ${hits} OF ${GATE.n}` : 'NO ALARM',
    sx, gy + 42, `800 13px ${LABEL}`, confirmed ? `rgba(${ROSE},1)` : d.raw ? `rgba(${AMBER},1)` : `rgba(${INK},0.6)`);
  text(g, 'backend/detect/detector.py · scorers.py', sx, gy + 66, `400 10px ${MONO}`, `rgba(${INK},0.45)`);
  text(g, 'ported, computed in this browser', sx, gy + 80, `400 10px ${MONO}`, `rgba(${INK},0.45)`);
  g.restore();
}

/* ---------------------------------------------------------------- Memory: the reservoir, live */
export function drawMemory(g: CanvasRenderingContext2D, R: Region, t: number, start: number, res: Reservoir | null, a: number) {
  if (a <= 0.01) return;
  g.save(); g.globalAlpha = a;
  if (!res) {
    text(g, 'Training the reservoir readout…', R.x, R.y + 20, `600 13px ${MONO}`, `rgba(${INK},0.7)`);
    g.restore(); return;
  }
  // replay: in the first five seconds the path is redrawn from the injection up to now
  const replay = Math.min(1, Math.max(0, (t - start) / 5));
  const ease = replay * replay * (3 - 2 * replay);
  const tNow = T_INJECT + (t - T_INJECT) * ease;
  const f = Math.min(res.frames - 1, Math.floor(tNow / FRAME));
  const f0 = Math.max(0, Math.floor((T_INJECT - 6) / FRAME));

  // the network: 180 of 500 nodes and the links among them
  const netR = R.compact ? Math.min(R.w * 0.3, 100) : Math.min(R.w * 0.21, R.h * 0.36);
  const ncx = R.x + netR + 6, ncy = R.y + netR + 26;
  text(g, `RESERVOIR · ${res.nodes} NODES · 12 LINKS EACH · ρ 0.9 · LEAK 0.3`, R.x, R.y + 4, `700 10.5px ${LABEL}`, `rgba(${INK},0.6)`);
  const P = (i: number) => [ncx + res.layout[i * 2] * netR, ncy + res.layout[i * 2 + 1] * netR];
  g.lineWidth = 0.6;
  for (let e = 0; e < res.edges.length; e += 2) {
    const [x1, y1] = P(res.edges[e]), [x2, y2] = P(res.edges[e + 1]);
    const act = Math.abs(res.act[f * res.show + res.edges[e]]);
    g.strokeStyle = `rgba(${CYAN},${0.04 + 0.22 * act})`;
    g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke();
  }
  for (let i = 0; i < res.show; i++) {
    const v = res.act[f * res.show + i], [x, y] = P(i);
    g.fillStyle = v >= 0 ? `rgba(${CYAN},${0.2 + 0.8 * Math.min(1, v)})` : `rgba(${AMBER},${0.2 + 0.8 * Math.min(1, -v)})`;
    g.beginPath(); g.arc(x, y, 1.6 + 2.2 * Math.min(1, Math.abs(v)), 0, Math.PI * 2); g.fill();
  }
  text(g, `showing ${res.show} of ${res.nodes}`, R.x, ncy + netR + 18, `400 10px ${MONO}`, `rgba(${INK},0.45)`);

  // the state path in its top two principal components; older points fade: that fading is the memory
  // phones stack the state path under the network; wide screens put it beside
  const px = R.compact ? R.x : R.x + R.w * 0.46, pw = R.x + R.w - px, ph = R.compact ? 150 : netR * 2;
  const py = R.compact ? ncy + netR + 62 : R.y + 26;
  text(g, 'STATE PATH · TOP TWO PRINCIPAL COMPONENTS', px, py - 22, `700 10.5px ${LABEL}`, `rgba(${INK},0.6)`);
  let minA = Infinity, maxA = -Infinity, minB = Infinity, maxB = -Infinity;
  const pts: number[][] = [];
  for (let k = 0; k < res.classes.length; k++) pts.push([res.centroids[k * 2], res.centroids[k * 2 + 1]]);
  for (let q = f0; q < res.frames; q++) pts.push([res.path[q * 2], res.path[q * 2 + 1]]);
  pts.forEach(([p, q]) => { minA = Math.min(minA, p); maxA = Math.max(maxA, p); minB = Math.min(minB, q); maxB = Math.max(maxB, q); });
  const map = (p: number, q: number) => [px + 14 + ((p - minA) / (maxA - minA || 1)) * (pw - 150), py + 14 + ((q - minB) / (maxB - minB || 1)) * (ph - 28)];
  g.strokeStyle = `rgba(${INK},0.12)`; g.strokeRect(px, py, pw, ph);
  res.classes.forEach((c, k) => {
    const [x, y] = map(res.centroids[k * 2], res.centroids[k * 2 + 1]);
    g.strokeStyle = c === 'NOMINAL' ? `rgba(${CYAN},0.6)` : `rgba(${INK},0.35)`;
    g.beginPath(); g.arc(x, y, 5, 0, Math.PI * 2); g.stroke();
    text(g, CLASS_NAME[c] ?? c, x + 8, y + 4, `500 10.5px ${MONO}`, `rgba(${INK},0.55)`);
  });
  for (let q = f0 + 1; q <= f; q++) {
    const age = (f - q) / Math.max(1, f - f0);
    const [x1, y1] = map(res.path[(q - 1) * 2], res.path[(q - 1) * 2 + 1]), [x2, y2] = map(res.path[q * 2], res.path[q * 2 + 1]);
    const lab = res.classes[res.label[q]];
    g.strokeStyle = lab === 'NOMINAL' ? `rgba(${CYAN},${0.15 + 0.85 * (1 - age)})` : `rgba(${ROSE},${0.15 + 0.85 * (1 - age)})`;
    g.lineWidth = 1 + 1.6 * (1 - age);
    g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke();
  }
  const [hx, hy] = map(res.path[f * 2], res.path[f * 2 + 1]);
  g.fillStyle = `rgba(${INK},1)`; g.beginPath(); g.arc(hx, hy, 4, 0, Math.PI * 2); g.fill();
  // the moment the readout first named the fault, if the replay has reached it
  const named = res.label.findIndex((l, q) => q >= f0 && res.classes[l] !== 'NOMINAL');
  if (named >= 0 && named <= f) {
    const [nx, ny] = map(res.path[named * 2], res.path[named * 2 + 1]);
    g.strokeStyle = `rgba(${ROSE},1)`; g.lineWidth = 1.5; g.beginPath(); g.arc(nx, ny, 9, 0, Math.PI * 2); g.stroke();
    const label = `named ${(named * FRAME - T_INJECT).toFixed(1)} s after injection`;
    const roomLeft = nx - 13 - g.measureText(label).width > px + 4;
    text(g, label, roomLeft ? nx - 13 : nx + 13, ny + 22, `600 11px ${MONO}`, `rgba(${ROSE},1)`, roomLeft ? 'right' : 'left');
  }
  text(g, replay < 1 ? `replaying memory · ${(tNow - T_INJECT).toFixed(1)} s after injection` : 'live', px, py + ph + 16,
    `500 10.5px ${MONO}`, `rgba(${INK},0.55)`);

  // the readout: five class scores
  const ry = Math.max(ncy + netR + 40, py + ph + 38);
  text(g, R.compact ? 'RIDGE READOUT · FITTED IN THIS BROWSER · FROZEN IN FLIGHT' : 'RIDGE READOUT · TRAINED IN THIS BROWSER ON A SIMULATED FAULT LIBRARY · FROZEN IN FLIGHT', R.x, ry, `700 10.5px ${LABEL}`, `rgba(${INK},0.6)`);
  const best = res.label[f];
  const bw = (R.w - 4 * 10) / res.classes.length;
  res.classes.forEach((c, k) => {
    const s = res.scores[f * res.classes.length + k];
    const x = R.x + k * (bw + 10), y = ry + 12;
    g.fillStyle = `rgba(${INK},0.08)`; g.fillRect(x, y, bw, 6);
    const v = Math.max(0, Math.min(1, (s + 1) / 2));
    g.fillStyle = k === best ? (c === 'NOMINAL' ? `rgba(${CYAN},1)` : `rgba(${ROSE},1)`) : `rgba(${INK},0.4)`;
    g.fillRect(x, y, bw * v, 6);
    text(g, R.compact ? (CLASS_NAME[c] ?? c).split(' ')[0] : CLASS_NAME[c] ?? c, x, y + 22, `${k === best ? 700 : 500} ${R.compact ? 10 : 11}px ${LABEL}`, k === best ? `rgba(${INK},1)` : `rgba(${INK},0.55)`);
  });
  text(g, R.compact ? 'reservoir.py · E19 (sim): +4–5 macro-F1 vs windowed RF' : 'backend/detect/reservoir.py · E19 (simulation): +4–5 macro-F1 over a windowed random forest; fly-connectome wiring tied random wiring',
    R.x, ry + 52, `400 10px ${MONO}`, `rgba(${INK},0.4)`);
  g.restore();
}
