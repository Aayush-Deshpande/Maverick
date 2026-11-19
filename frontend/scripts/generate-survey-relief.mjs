// Generates the landing page's schematic relief for the Leh–Nubra–Kargil sheet.
// Output: public/survey/relief.webp (hypsometric tints + hillshade) and public/survey/contours.json.
// The terrain is procedural (seeded fBm with valleys carved along schematic river courses); it is
// labelled "schematic relief" on the page and is not a digital elevation model.
// Run: node scripts/generate-survey-relief.mjs   (needs ffmpeg on PATH for the WebP encode)
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { SHEET, RIVERS, toXY } from '../src/components/survey/geo.js';

const OUT = path.resolve('public/survey');
fs.mkdirSync(OUT, { recursive: true });
const { width: W, height: H } = SHEET;

// ---- seeded value noise ---------------------------------------------------------------
let s = 0x2ad9c3;
const rand = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
const G = 256, perm = Array.from({ length: G }, (_, i) => i).sort(() => rand() - 0.5), vals = Array.from({ length: G }, rand);
const lattice = (x, y) => vals[(perm[(x & 255)] + y) & 255];
const smooth = (t) => t * t * (3 - 2 * t);
function noise(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const a = lattice(xi, yi), b = lattice(xi + 1, yi), c = lattice(xi, yi + 1), d = lattice(xi + 1, yi + 1);
  const u = smooth(xf), v = smooth(yf);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function fbm(x, y) { let f = 0, amp = 0.5, fr = 1; for (let o = 0; o < 6; o++) { f += amp * noise(x * fr, y * fr); fr *= 2.03; amp *= 0.5; } return f; }
function ridged(x, y) { let f = 0, amp = 0.5, fr = 1; for (let o = 0; o < 5; o++) { f += amp * (1 - Math.abs(noise(x * fr, y * fr) * 2 - 1)) ** 2; fr *= 2.1; amp *= 0.5; } return f; }

// ---- river distance field ---------------------------------------------------------------
const riverPts = RIVERS.map((r) => r.path.map(([lon, lat]) => toXY(lon, lat)));
function distToRivers(x, y) {
  let best = Infinity;
  for (const pts of riverPts) for (let i = 0; i < pts.length - 1; i++) {
    const [ax, ay] = pts[i], [bx, by] = pts[i + 1];
    const dx = bx - ax, dy = by - ay, t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)));
    best = Math.min(best, Math.hypot(x - ax - t * dx, y - ay - t * dy));
  }
  return best;
}

// ---- height field (metres) on a coarse grid ---------------------------------------------
const GW = 400, GH = 250, sx = W / (GW - 1), sy = H / (GH - 1);
const hgt = new Float32Array(GW * GH);
for (let j = 0; j < GH; j++) for (let i = 0; i < GW; i++) {
  const x = i * sx, y = j * sy, nx = x / 260, ny = y / 260;
  const base = 0.55 * ridged(nx * 0.9 + 11, ny * 0.9 + 3) + 0.45 * fbm(nx * 1.3 + 7, ny * 1.3 + 19);
  // Domain-warp the river distance so valley walls meander instead of running as straight trenches.
  const wx = x + 70 * (fbm(nx * 2 + 31, ny * 2 + 5) - 0.5), wy = y + 70 * (fbm(nx * 2 + 3, ny * 2 + 41) - 0.5);
  const d = distToRivers(wx, wy);
  const valley = 1 - Math.exp(-((d / (48 + 30 * fbm(nx * 1.7, ny * 1.7))) ** 1.3)); // 0 at the river, 1 far away
  const northRise = 0.22 * (1 - y / H);                          // Karakoram side stands higher
  const floor = 3050 + 350 * (x / W);                            // valley floors rise upstream (east)
  const e = floor + valley * (700 + 3000 * (base + northRise)) + 160 * (fbm(nx * 4, ny * 4) - 0.5);
  hgt[j * GW + i] = e;
}
const at = (i, j) => hgt[Math.min(GH - 1, Math.max(0, j)) * GW + Math.min(GW - 1, Math.max(0, i))];
function sample(x, y) { // bilinear
  const fi = x / sx, fj = y / sy, i = Math.floor(fi), j = Math.floor(fj), u = fi - i, v = fj - j;
  return at(i, j) * (1 - u) * (1 - v) + at(i + 1, j) * u * (1 - v) + at(i, j + 1) * (1 - u) * v + at(i + 1, j + 1) * u * v;
}

// ---- hypsometric tints + hillshade -------------------------------------------------------
const STOPS = [ // metres -> RGB, Survey-sheet hypsometric convention adapted to a high-altitude sheet
  [3000, [150, 166, 120]], [3500, [186, 186, 132]], [4000, [214, 190, 128]], [4500, [206, 158, 96]],
  [5000, [180, 124, 78]], [5600, [148, 98, 70]], [6100, [178, 160, 150]], [6400, [228, 232, 234]], [6900, [246, 249, 250]],
];
function tint(e) {
  for (let k = 0; k < STOPS.length - 1; k++) {
    const [e0, c0] = STOPS[k], [e1, c1] = STOPS[k + 1];
    if (e <= e1) { const t = Math.max(0, (e - e0) / (e1 - e0)); return c0.map((c, n) => c + (c1[n] - c) * t); }
  }
  return STOPS[STOPS.length - 1][1];
}
const RW = 1600, RH = 1000, rgba = Buffer.alloc(RW * RH * 3);
const light = [-0.6, -0.7, 0.4]; const ln = Math.hypot(...light); light.forEach((v, k) => (light[k] = v / ln));
for (let y = 0; y < RH; y++) for (let x = 0; x < RW; x++) {
  const px = (x / RW) * W, py = (y / RH) * H, e = sample(px, py);
  const dzdx = (sample(px + 2, py) - sample(px - 2, py)) / 4, dzdy = (sample(px, py + 2) - sample(px, py - 2)) / 4;
  const n = [-dzdx / 6, -dzdy / 6, 1], nl = Math.hypot(...n);
  const shade = Math.max(0, (n[0] * light[0] + n[1] * light[1] + n[2] * light[2]) / nl);
  const k = 0.8 + 0.3 * shade, c = tint(e), o = (y * RW + x) * 3;
  rgba[o] = Math.min(255, c[0] * k); rgba[o + 1] = Math.min(255, c[1] * k); rgba[o + 2] = Math.min(255, c[2] * k);
}
const raw = path.join(OUT, '_relief.rgb');
fs.writeFileSync(raw, rgba);
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', `${RW}x${RH}`, '-i', raw, '-c:v', 'libwebp', '-quality', '82', '-compression_level', '6', path.join(OUT, 'relief.webp')]);
fs.rmSync(raw);

// ---- contours by marching squares, chained into polylines --------------------------------
const levels = []; for (let e = 3200; e <= 6800; e += 200) levels.push(e);
const contours = [];
for (const lv of levels) {
  const segs = [];
  for (let j = 0; j < GH - 1; j++) for (let i = 0; i < GW - 1; i++) {
    const a = at(i, j), b = at(i + 1, j), c = at(i + 1, j + 1), d = at(i, j + 1);
    const code = (a > lv ? 8 : 0) | (b > lv ? 4 : 0) | (c > lv ? 2 : 0) | (d > lv ? 1 : 0);
    if (code === 0 || code === 15) continue;
    const x = i * sx, y = j * sy, lerp = (p, q) => (lv - p) / (q - p);
    const T = [x + sx * lerp(a, b), y], R = [x + sx, y + sy * lerp(b, c)], B = [x + sx * lerp(d, c), y + sy], L = [x, y + sy * lerp(a, d)];
    const map = { 1: [[L, B]], 2: [[B, R]], 3: [[L, R]], 4: [[T, R]], 5: [[L, T], [B, R]], 6: [[T, B]], 7: [[L, T]], 8: [[L, T]], 9: [[T, B]], 10: [[L, B], [T, R]], 11: [[T, R]], 12: [[L, R]], 13: [[B, R]], 14: [[L, B]] };
    for (const sg of map[code]) segs.push(sg);
  }
  const key = (p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`;
  const ends = new Map(); segs.forEach((sg, n) => { for (const p of sg) { const k = key(p); (ends.get(k) || ends.set(k, []).get(k)).push(n); } });
  const used = new Uint8Array(segs.length);
  for (let n = 0; n < segs.length; n++) {
    if (used[n]) continue; used[n] = 1;
    const line = [segs[n][0], segs[n][1]];
    for (const dir of [1, -1]) {
      for (;;) {
        const tip = dir === 1 ? line[line.length - 1] : line[0];
        const next = (ends.get(key(tip)) || []).find((m) => !used[m]);
        if (next === undefined) break;
        used[next] = 1;
        const [p, q] = segs[next], far = key(p) === key(tip) ? q : p;
        dir === 1 ? line.push(far) : line.unshift(far);
      }
    }
    if (line.length < 6) continue;
    const pts = line.filter((_, k) => k % 2 === 0 || k === line.length - 1);
    contours.push({ e: lv, index: lv % 1000 === 0, d: 'M' + pts.map((p) => `${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join('L') });
  }
}
fs.writeFileSync(path.join(OUT, 'contours.json'), JSON.stringify({ width: W, height: H, contours }));
console.log(`relief.webp ${(fs.statSync(path.join(OUT, 'relief.webp')).size / 1024).toFixed(0)} KB · ${contours.length} contour lines · contours.json ${(fs.statSync(path.join(OUT, 'contours.json')).size / 1024).toFixed(0)} KB`);
