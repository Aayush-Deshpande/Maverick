// Two chapters that argue the architecture itself, both computed live:
//   One frame  - a single telemetry frame through the twelve real pipeline stages, each showing the value it
//                produces at this instant, ending in a real SHA-256 seal of the frame
//   Never seen - a fault in no training library: the closed-set namers (a random forest and the reservoir,
//                trained here on the fault library) must answer with a name they know; the open-set tier,
//                trained on nominal flight only, says abnormal; and the Fly Bloom fleet memory merges
//                across aircraft to exactly what pooling their flights would give, without moving any.
import { channelZ, frameAt, gauges, oilExpected } from './story';
import { FLEET, GATE, SCORERS, evaluate, tier0, type ScorerName } from './detector';
import { readout } from './timeline';
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

const seals = new Map<number, string>();
/** The sortie record seals each frame with SHA-256 (backend/security/merkle_log.py); this hashes the frame shown. */
function seal(f: number, payload: string) {
  const known = seals.get(f);
  if (known) return known;
  seals.set(f, '…');
  if (typeof crypto !== 'undefined' && crypto.subtle) {
    void crypto.subtle.digest('SHA-256', new TextEncoder().encode(payload)).then((h) => {
      seals.set(f, Array.from(new Uint8Array(h)).map((b) => b.toString(16).padStart(2, '0')).join(''));
    });
  }
  return '…';
}

/** Where the packet is, 0..12 (stage index plus fraction), for the score to follow. */
export const pipelineReach = (k: number) => Math.min(11.999, Math.max(0, (k - 0.06) / 0.78) * 12);

export function drawPipeline(g: CanvasRenderingContext2D, R: Region, t: number, k: number, res: Reservoir | null, a: number) {
  if (a <= 0.01) return;
  g.save(); g.globalAlpha = a;
  const f = frameAt(t), z = channelZ(f), gv = gauges(t), d = tier0(t), rd = readout(t);
  const lab = res ? res.classes[res.label[Math.min(res.frames - 1, f)]] : '';
  const hash = seal(f, JSON.stringify({ frame: f, z: z.map((v) => +v.toFixed(3)), oil_p: +gv.oilP.toFixed(3) }));
  const worst = Math.max(...Object.values(d.ratios));
  const stages: Array<[string, string, string]> = [
    ['Sensors', 'core/channels.py', `oil ${gv.oilP.toFixed(2)} bar`],
    ['Ingest', 'telemetry/can_streamer.py', 'CAN · MAVLink · IDS'],
    ['Sensor sanity', 'physics/sensor_validator.py', '13 / 13 valid'],
    ['Physics twin', 'physics/thermo_model.py', `expects ${oilExpected(t).toFixed(2)} bar`],
    ['Calibration', 'detect/calibration.py', `z(oil_p) ${z[8] >= 0 ? '+' : '−'}${Math.abs(z[8]).toFixed(2)}`],
    ['Three scorers', 'detect/scorers.py', `worst ${worst.toFixed(2)}×`],
    ['Persistence gate', 'detect/detector.py', `${d.window.filter(Boolean).length} of ${GATE.n} · ${d.confirmed ? 'confirmed' : 'holding'}`],
    ['Reservoir', 'detect/reservoir.py', CLASS_NAME[lab] ?? 'training'],
    ['Diagnosis', 'agent/diagnostic_agent.py', rd.confirmed ? 'ATA 79 · oil' : 'no action'],
    ['Prognosis', 'prognose/rul.py', `RUL ${rd.rul.toFixed(1)} h`],
    ['Mission', 'mission/reliability.py', `18 h odds ${(rd.missionRel * 100).toFixed(1)}%`],
    ['Sealed', 'security/merkle_log.py', hash.slice(0, 12)],
  ];
  const cols = R.compact ? 3 : 4, rows = Math.ceil(stages.length / cols);
  const gap = R.compact ? 8 : 14;
  const cw = (R.w - gap * (cols - 1)) / cols;
  const ch = Math.min(R.compact ? 80 : 98, (R.h - 40 - gap * (rows - 1)) / rows);
  const pos = stages.map((_, i) => {
    const r = Math.floor(i / cols), c0 = i % cols, c = r % 2 ? cols - 1 - c0 : c0; // snake: the path reads like the data's
    return [R.x + c * (cw + gap), R.y + 26 + r * (ch + gap)];
  });
  const reach = pipelineReach(k);
  text(g, `ONE FRAME · FRAME ${f} · THE SAME PIPELINE FOR ALL FIVE ENGINES`, R.x, R.y + 6, `700 10.5px ${LABEL}`, `rgba(${INK},0.6)`);
  g.lineWidth = 1;
  for (let i = 1; i < stages.length; i++) {
    const [x1, y1] = pos[i - 1], [x2, y2] = pos[i];
    g.strokeStyle = i <= reach ? `rgba(${CYAN},0.55)` : `rgba(${INK},0.12)`;
    g.beginPath(); g.moveTo(x1 + cw / 2, y1 + ch / 2); g.lineTo(x2 + cw / 2, y2 + ch / 2); g.stroke();
  }
  stages.forEach(([name, mod, val], i) => {
    const [x, y] = pos[i], now = i === Math.floor(reach), lit = i < reach;
    g.fillStyle = now ? 'rgba(10, 32, 36, 0.94)' : 'rgba(6, 12, 14, 0.84)';
    g.fillRect(x, y, cw, ch);
    g.strokeStyle = now ? `rgba(${CYAN},0.95)` : lit ? `rgba(${CYAN},0.35)` : `rgba(${INK},0.12)`;
    g.strokeRect(x + 0.5, y + 0.5, cw - 1, ch - 1);
    g.save(); g.beginPath(); g.rect(x + 4, y, cw - 8, ch); g.clip();
    text(g, String(i + 1).padStart(2, '0'), x + 10, y + 19, `600 10px ${MONO}`, `rgba(${INK},0.4)`);
    text(g, name, x + 34, y + 19, `700 ${R.compact ? 12 : 14}px ${LABEL}`, lit || now ? `rgba(${INK},1)` : `rgba(${INK},0.45)`);
    if (lit || now) text(g, val, x + 10, y + (R.compact ? 44 : 52), `600 ${R.compact ? 9.5 : 12.5}px ${MONO}`, now ? `rgba(${CYAN},1)` : `rgba(${INK},0.85)`);
    text(g, mod, x + 10, y + ch - 12, `400 ${R.compact ? 8 : 10}px ${MONO}`, `rgba(${INK},0.38)`);
    g.restore();
  });
  const i0 = Math.floor(reach), fr = reach - i0;
  const [ax, ay] = pos[i0], [bx, by] = pos[Math.min(stages.length - 1, i0 + 1)];
  const px = ax + cw / 2 + (bx - ax) * fr, py = ay + ch / 2 + (by - ay) * fr;
  const glow = g.createRadialGradient(px, py, 0, px, py, 20);
  glow.addColorStop(0, `rgba(${CYAN},0.9)`); glow.addColorStop(1, `rgba(${CYAN},0)`);
  g.fillStyle = glow; g.beginPath(); g.arc(px, py, 20, 0, Math.PI * 2); g.fill();
  g.fillStyle = `rgba(${INK},1)`; g.beginPath(); g.arc(px, py, 3, 0, Math.PI * 2); g.fill();
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
  const small = R.compact ? 9.5 : 11;
  const colW = R.compact ? R.w : (R.w - 30) / 2;
  const top = R.y + 8;
  text(g, 'THE FAULT · A BLOCKED FILTER AND FOULED COOLING TOGETHER · IN NO TRAINING LIBRARY', R.x, top, `700 10.5px ${LABEL}`, `rgba(${ROSE},0.95)`);

  // the closed world
  const lx = R.x, ly = top + 28;
  text(g, 'CLOSED WORLD · MUST ANSWER WITH A NAME IT KNOWS', lx, ly, `700 10.5px ${LABEL}`, `rgba(${INK},0.6)`);
  text(g, `Random forest · ${res.forest.trees} trees · ${res.trainFrames.toLocaleString('en-IN')} labelled frames`, lx, ly + 18, `500 ${small}px ${MONO}`, `rgba(${INK},0.7)`);
  res.classes.forEach((c, ci) => {
    const y = ly + 34 + ci * 22, v = post[ci];
    text(g, CLASS_NAME[c] ?? c, lx, y + 9, `600 12px ${LABEL}`, ci === gate.candidate ? `rgba(${INK},1)` : `rgba(${INK},0.55)`);
    const bx = lx + (R.compact ? 118 : 150), bw = colW - (R.compact ? 156 : 196);
    g.fillStyle = `rgba(${INK},0.08)`; g.fillRect(bx, y + 2, bw, 8);
    g.fillStyle = ci === gate.candidate ? (ci === 0 ? `rgba(${CYAN},0.9)` : `rgba(${AMBER},0.95)`) : `rgba(${INK},0.35)`;
    g.fillRect(bx, y + 2, bw * v, 8);
    text(g, `${Math.round(v * 100)}%`, lx + colW, y + 10, `600 11px ${MONO}`, `rgba(${INK},0.75)`, 'right');
  });
  const ry = ly + 34 + C * 22 + 12;
  const resLab = res.classes[U.reservoir[uf]];
  text(g, `Reservoir readout: ${CLASS_NAME[resLab] ?? resLab}`, lx, ry, `600 12px ${MONO}`, U.reservoir[uf] === 0 ? `rgba(${INK},0.75)` : `rgba(${AMBER},1)`);
  text(g, `Both ${(res.forest.knownAccuracy * 100).toFixed(0)}% on faults they were trained for (sim).`, lx, ry + 18, `400 ${small}px ${MONO}`, `rgba(${INK},0.55)`);
  text(g, 'Here every name is wrong: there is none to give.', lx, ry + 34, `400 ${small}px ${MONO}`, `rgba(${INK},0.55)`);
  text(g, `NoveltyGate (F17) withheld ${withheld} of ${named} names.`, lx, ry + 50, `400 ${small}px ${MONO}`, `rgba(${INK},0.55)`);

  // the open world
  const ox = R.compact ? R.x : R.x + colW + 30, oy = R.compact ? ry + 76 : ly;
  text(g, 'OPEN WORLD · TRAINED ON NOMINAL FLIGHT ONLY · ZERO FAULT LABELS', ox, oy, `700 10.5px ${LABEL}`, `rgba(${INK},0.6)`);
  SCORERS.forEach((s, i) => {
    const y = oy + 24 + i * 30, r = ev.ratios[s];
    text(g, SCORER_NAME[s], ox, y + 4, `600 12px ${LABEL}`, `rgba(${INK},0.85)`);
    text(g, `${r.toFixed(2)}×`, ox + colW, y + 4, `600 12px ${MONO}`, r > 1 ? `rgba(${AMBER},1)` : `rgba(${INK},0.8)`, 'right');
    g.fillStyle = `rgba(${INK},0.1)`; g.fillRect(ox, y + 10, colW, 5);
    g.fillStyle = r > 1 ? `rgba(${AMBER},0.95)` : `rgba(${CYAN},0.85)`; g.fillRect(ox, y + 10, colW * Math.min(1, r / 2.5), 5);
    g.fillStyle = `rgba(${INK},0.95)`; g.fillRect(ox + colW / 2.5 - 1, y + 6, 2, 13);
  });
  const verdict = ev.raw ? 'ABNORMAL · MATCHES NOTHING IT WAS TOLD ABOUT' : uf < 30 ? 'NORMAL' : 'WATCHING';
  text(g, verdict, ox, oy + 24 + 3 * 30 + 8, `800 13px ${LABEL}`, ev.raw ? `rgba(${ROSE},1)` : `rgba(${INK},0.6)`);
  text(g, 'It says something is wrong;', ox, oy + 24 + 3 * 30 + 26, `400 ${small}px ${MONO}`, `rgba(${INK},0.55)`);
  text(g, 'the namers can only say which known thing.', ox, oy + 24 + 3 * 30 + 42, `400 ${small}px ${MONO}`, `rgba(${INK},0.55)`);

  // why the fly earns its place in that tier: a memory that merges across a fleet
  const fy = R.compact ? oy + 24 + 3 * 30 + 50 : Math.max(ry + 74, oy + 24 + 3 * 30 + 50);
  text(g, 'FLY BLOOM MEMORY · 260 NUMBERS PER AIRCRAFT · MERGED ACROSS THE FLEET', R.x, fy, `700 10.5px ${LABEL}`, `rgba(${INK},0.6)`);
  const strips = [...FLEET.tails.map((tl) => ({ name: `${tl.id} · ${tl.frames} nominal frames`, f: tl.freq })), { name: 'Fleet · weighted average', f: FLEET.merged }];
  const sw = R.w - (R.compact ? 0 : 210), cell = sw / 260;
  const merge = Math.max(0, Math.min(1, (k - 0.66) / 0.16));
  strips.forEach((st, i) => {
    const y = fy + 14 + i * 16;
    if (i === 3 && merge <= 0) return;
    for (let u = 0; u < 260; u++) {
      const v = Math.min(1, st.f[u] / 0.1);
      g.fillStyle = i === 3 ? `rgba(${CYAN},${(0.1 + 0.9 * v) * merge})` : `rgba(${INK},${0.06 + 0.7 * v})`;
      g.fillRect(R.x + u * cell, y, Math.max(1, cell - 0.4), 11);
    }
    if (!R.compact) text(g, st.name, R.x + sw + 10, y + 9, `500 10.5px ${MONO}`, i === 3 ? `rgba(${CYAN},${merge})` : `rgba(${INK},0.55)`);
  });
  const fy2 = fy + 14 + 4 * 16 + 14;
  if (merge > 0.5) {
    text(g, `Identical to pooling every aircraft's flights (max difference ${FLEET.pooledMaxDiff.toExponential(1)}).`, R.x, fy2, `500 ${small}px ${MONO}`, `rgba(${CYAN},1)`);
    text(g, 'No raw telemetry moved. No fault was labelled.', R.x, fy2 + 16, `500 ${small}px ${MONO}`, `rgba(${CYAN},1)`);
  }
  text(g, 'Honest limit (E17, sim): alone on these 13 features Fly Bloom is the weakest scorer, AUROC 0.84 vs 0.97.', R.x, fy2 + 38, `400 ${R.compact ? 8.5 : 10.5}px ${MONO}`, `rgba(${INK},0.5)`);
  text(g, 'So it is one voice of three, and its real home is the high-dimensional vibration spectrum.', R.x, fy2 + 53, `400 ${R.compact ? 8.5 : 10.5}px ${MONO}`, `rgba(${INK},0.5)`);
  g.restore();
  return { frame: uf, abnormal: ev.raw, forestCandidate: gate.candidate, forestTop: gate.top };
}
