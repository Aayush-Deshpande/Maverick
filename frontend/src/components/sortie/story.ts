// The sortie film's script and its signal. One clock (story seconds) drives the flight, the camera, the
// sensor stream and therefore the detector, so any chapter can be entered cold and replays identically.
// The fault is the guided demo's oil-pressure loss on the Rotax 912 iS. The detector and the reservoir that
// read this stream are computed live in the browser (detector.ts, reservoir.worker.ts).

export type ChapterId = 'open' | 'twin' | 'inside' | 'pipeline' | 'drift' | 'detect' | 'memory' | 'unseen' | 'decide' | 'glide' | 'land';

export interface Chapter {
  id: ChapterId;
  rail: string;
  title: string;
  body: string;
  /** Story seconds this chapter plays for. */
  dur: number;
}

export const CHAPTERS: Chapter[] = [
  {
    id: 'open', rail: 'Sortie', dur: 8,
    title: 'Eighteen hours over Ladakh. One engine.',
    body: 'A MALE UAV on an ISR sortie flies a single aero piston engine through valleys where the nearest runway can be a ridge away.',
  },
  {
    id: 'twin', rail: 'Twin', dur: 7,
    title: 'A physics twin of this exact engine flies with it.',
    body: 'A thermofluid model predicts every channel at this altitude, throttle and outside air. An unscented Kalman filter keeps its parameters honest. Measured and expected agree.',
  },
  {
    id: 'inside', rail: 'Inside', dur: 13,
    title: 'Not one model. One hundred and nine parts.',
    body: 'The twin is built from the full Blender assembly, every component named. A fault is injected into the plant through the same API the console uses, and the component it lives in lights up.',
  },
  {
    id: 'pipeline', rail: 'One frame', dur: 15,
    title: 'One frame. Twelve stages. Fifty milliseconds.',
    body: 'Follow a single telemetry frame through the real pipeline: ingest, sensor sanity, the physics twin, calibration, three scorers, the gate, the reservoir, diagnosis, prognosis, the mission, and a hash that seals it into the sortie record.',
  },
  {
    id: 'drift', rail: 'Drift', dur: 7,
    title: 'Oil pressure slips. Nothing is red yet.',
    body: 'The reading is still far inside its limit, so a redline stays silent. The gap from what the twin expects is already growing.',
  },
  {
    id: 'detect', rail: 'Detect', dur: 12,
    title: 'Thirteen numbers, read the way a fly reads a smell.',
    body: 'Calibrated residuals expand into 260 sparse units and only the strongest 13 fire. Three scorers, each with a split-conformal threshold, and three of the last five frames must agree before the crew is paged.',
  },
  {
    id: 'memory', rail: 'Memory', dur: 11,
    title: 'It reads the path, not the snapshot.',
    body: 'A 500-node recurrent reservoir carries a fading memory of every frame before this one. A readout trained on this engine’s simulated fault library names the fault from how the drift developed.',
  },
  {
    id: 'unseen', rail: 'Never seen', dur: 15,
    title: 'A forest can only name what it was taught.',
    body: 'A random forest and the reservoir, trained here on the fault library, meet a fault that is not in it, and must answer with a name they know. The one-class tier, trained on nominal flight alone, says what is true: abnormal, and like nothing it was told about. Fly Bloom’s part is its memory: built without a single fault label, merged across a fleet without moving any telemetry.',
  },
  {
    id: 'decide', rail: 'Decide', dur: 8,
    title: 'Detection is half the job.',
    body: 'The finding becomes an ATA-chapter maintenance directive, a remaining-life estimate with a conformal interval, and the odds of finishing this sortie.',
  },
  {
    id: 'glide', rail: 'Glide', dur: 9,
    title: 'Where can it still land?',
    body: 'From the current altitude and glide ratio, the twin draws the engine-out footprint and checks every airfield in the sector.',
  },
  {
    id: 'land', rail: 'Recover', dur: 13,
    title: 'The airframe comes home.',
    body: 'The crew turns for Thoise with margin to spare. The engine arrives at the hangar with its work order already written.',
  },
];

export const STARTS = CHAPTERS.reduce<number[]>((acc, _c, i) => { acc.push(i ? acc[i - 1] + CHAPTERS[i - 1].dur : 0); return acc; }, []);
export const TOTAL = STARTS[STARTS.length - 1] + CHAPTERS[CHAPTERS.length - 1].dur;
export const chapterAt = (t: number) => { let i = 0; while (i < STARTS.length - 1 && t >= STARTS[i + 1]) i++; return i; };
export const startOf = (id: ChapterId) => STARTS[CHAPTERS.findIndex((c) => c.id === id)];

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const smooth = (x: number) => { const k = clamp01(x); return k * k * (3 - 2 * k); };

/* ------------------------------------------------------------------ the fault and the sensor stream */

/** The moment the fault is injected into the plant (inside the Inside chapter, on screen). */
export const T_INJECT = startOf('inside') + 6.5;
/** Seconds the fault takes to develop (the console's ramp_sec, compressed to story time). */
const RAMP = 108;
export const T_GLIDE = startOf('glide');
export const T_TOUCH = startOf('land') + 7.0;
/** One detector frame per this many story seconds (the runtime ticks once per simulated second). */
export const FRAME = 0.5;

export function severity(t: number) {
  return t < T_INJECT ? 0 : 0.85 * smooth((t - T_INJECT) / RAMP);
}

export const OIL = { expected: 4.15, limit: 0.8, sigma: 0.11 };

/** Deterministic noise: a hash of (frame, channel) to a standard normal. */
export function gauss(a: number, b: number) {
  let h = (Math.imul(a | 0, 374761393) + Math.imul(b | 0, 668265263) + 0x9e3779b9) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16;
  const u1 = ((h >>> 0) + 1) / 4294967298;
  let g = Math.imul(h ^ 0x85ebca6b, 0xc2b2ae35); g ^= g >>> 15;
  const u2 = ((g >>> 0) + 1) / 4294967298;
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

/** The detector's channels, in TailCalibration order: cht 1-4, egt 1-4, then the scalars. */
export const CHANNELS = ['cht_1', 'cht_2', 'cht_3', 'cht_4', 'egt_1', 'egt_2', 'egt_3', 'egt_4', 'oil_p', 'oil_t', 'fuel_flow', 'map_kpa', 'rpm'];
export const FEATURES = ['cht_mean', 'cht_max', 'cht_min', 'cht_std', 'egt_mean', 'egt_max', 'egt_min', 'egt_std', 'oil_p', 'oil_t', 'fuel_flow', 'map_kpa', 'rpm'];

/** How each fault moves the per-channel z-scores at severity s (shapes follow the E20 evidence channels). */
export const SIGNATURES: Record<string, (s: number, z: number[]) => void> = {
  // not in any training library: a blocked filter and fouled cooling together (a dust-storm sortie)
  DUST_COMPOUND: (s, z) => {
    for (let i = 0; i < 4; i++) z[i] += 3.5 * s + (i === 2 ? 2 * s : 0);
    z[11] -= 6 * s; for (let i = 4; i < 8; i++) z[i] += 2.5 * s; z[9] += 2.5 * s; z[10] += 3 * s; z[12] -= 2 * s;
  },
  OIL_PRESSURE_LOSS: (s, z) => { z[8] -= 18 * s; z[9] += 4.5 * s; z[12] += 3 * s; },
  COOLING_DEGRADATION: (s, z) => { for (let i = 0; i < 4; i++) z[i] += 6 * s; z[9] += 3 * s; for (let i = 4; i < 8; i++) z[i] += 1 * s; },
  MISFIRE: (s, z) => { z[5] -= 12 * s; z[1] -= 6 * s; z[12] -= 3 * s; z[4] += s; z[6] += s; z[7] += s; },
  AIR_FILTER_BLOCKAGE: (s, z) => { z[11] -= 8 * s; for (let i = 4; i < 8; i++) z[i] += 4 * s; z[10] -= 2 * s; },
};

/** TailCalibration.features: [mean, max, min, std] of CHT and of EGT, then the five scalar z-scores. */
export function featurize(z: number[]) {
  const block = (a: number[]) => {
    const m = a.reduce((p, v) => p + v, 0) / a.length;
    const sd = Math.sqrt(a.reduce((p, v) => p + (v - m) ** 2, 0) / a.length);
    return [m, Math.max(...a), Math.min(...a), sd];
  };
  return [...block(z.slice(0, 4)), ...block(z.slice(4, 8)), ...z.slice(8)];
}

/** Per-channel z at a detector frame of the film's own sortie. */
export function channelZ(frame: number) {
  const t = frame * FRAME;
  const z = CHANNELS.map((_, ch) => gauss(frame + 7919, ch + 17));
  SIGNATURES.OIL_PRESSURE_LOSS(severity(t), z);
  return z;
}
export const featuresAt = (frame: number) => featurize(channelZ(frame));
export const frameAt = (t: number) => Math.max(0, Math.floor(t / FRAME));

/* ------------------------------------------------------------------ instrument readings for the HUD */

const jitter = (t: number, seed: number) => Math.sin(t * 7.3 + seed) * 0.5 + Math.sin(t * 13.1 + seed * 2.1) * 0.3 + Math.sin(t * 29.7 + seed * 0.7) * 0.2;

export function oilExpected(t: number) {
  const powerCut = t > T_GLIDE ? smooth((t - T_GLIDE) / 4) : 0;
  return OIL.expected - 0.35 * powerCut + 0.02 * jitter(t, 4);
}
export function oilMeasured(t: number) {
  return oilExpected(t) - 1.95 * severity(t) + 0.045 * jitter(t, 1);
}

export function gauges(t: number) {
  const sev = severity(t);
  const powerCut = t > T_GLIDE ? smooth((t - T_GLIDE) / 4) : 0;
  const glideT = clamp01((t - T_GLIDE) / (T_TOUCH - T_GLIDE));
  return {
    sev,
    rpm: 5480 - 900 * powerCut + 14 * jitter(t, 3),
    cht: 101 + 9 * sev - 6 * powerCut + 0.4 * jitter(t, 5),
    oilT: 96 + 14 * sev + 0.3 * jitter(t, 6),
    oilP: oilMeasured(t),
    oilPExp: oilExpected(t),
    altFt: 18000 - (18000 - 10066) * smooth(glideT),
  };
}

/** Engine-out glide when the decision is made. L/D and field floors follow the backend's glide model. */
export const GLIDE = {
  ld: 27.3,
  altFt: 18000,
  fields: [
    { id: 'VI82', name: 'Thoise', nm: 22, marginFt: 1600, reach: true },
    { id: 'VILH', name: 'Leh', nm: 34, marginFt: -1770, reach: false },
    { id: 'VIKG', name: 'Kargil', nm: 58, marginFt: -6190, reach: false },
  ],
};

export const DIRECTIVE = {
  fault: 'Oil pressure loss',
  ata: 'ATA 79 · Oil',
  action: 'Inspect oil pump, pressure relief valve and oil lines before next flight',
};

/** The request the film shows at the moment of injection: the console's own API. */
export const INJECTION = {
  method: 'POST',
  path: '/api/engines/rotax_912is/faults',
  body: '{ "mode": "OIL_PRESSURE_LOSS", "severity": 0.8, "ramp_sec": 60 }',
};
