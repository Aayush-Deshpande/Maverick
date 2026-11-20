// The sortie film's script and its signal. One clock (story seconds) drives the flight, the camera, the
// sensor stream and therefore the detector, so any chapter can be entered cold and replays identically.
// The fault is the guided demo's oil-pressure loss on the Rotax 912 iS. The detector and the reservoir that
// read this stream are computed live in the browser (detector.ts, reservoir.worker.ts).

export type ChapterId = 'cold' | 'problem' | 'twin' | 'approach' | 'inside' | 'signal' | 'pipeline' | 'detect' | 'memory' | 'decide' | 'divert' | 'land' | 'beyond';

export interface Chapter {
  id: ChapterId;
  /** the movement this shot belongs to (the rail groups by movement) */
  movement: number;
  title: string;
  body: string;
  /** Story seconds this chapter plays for. */
  dur: number;
}

/** The five movements of the film, plus the cold open (docs/demo/FILM_TREATMENT.md). */
export const MOVEMENTS = ['One engine', 'The problem', 'The twin', 'On board', 'The decision', 'Beyond'];

// One line of copy per shot. The picture carries the argument; the words only name it.
export const CHAPTERS: Chapter[] = [
  { id: 'cold', movement: 0, dur: 14, title: 'One engine.', body: 'Ladakh · 18,000 ft · hour six of eighteen' },
  { id: 'problem', movement: 1, dur: 20, title: 'A redline speaks last.', body: 'The gauge stays green until it is too late to turn back.' },
  { id: 'twin', movement: 2, dur: 8, title: 'A twin flies alongside.', body: 'A physics model of this exact engine, predicting every sensor, every second.' },
  { id: 'approach', movement: 2, dur: 10, title: '', body: '' },
  { id: 'inside', movement: 2, dur: 10, title: 'Every part. Every sensor.', body: '109 named components, the same model in Blender and on the web.' },
  { id: 'signal', movement: 3, dur: 10, title: 'Oil pressure slips. Every gauge: green.', body: 'But the twin expected more. That gap is the first warning.' },
  { id: 'pipeline', movement: 3, dur: 14, title: 'Heard on board. Sent as 29 bytes.', body: 'Raw vibration cannot fit down the datalink. So the aircraft does the listening, and sends only what it heard.' },
  { id: 'detect', movement: 3, dur: 12, title: 'Borrowed from a fruit fly’s brain.', body: 'A fly knows a smell it has never met. ANUMAAN knows an engine going wrong without ever being shown a fault.' },
  { id: 'memory', movement: 3, dur: 7, title: 'It remembers how it got here.', body: 'A 500-node reservoir reads the path of the drift, and names the fault.' },
  { id: 'decide', movement: 4, dur: 14, title: 'Detection is half the job.', body: 'Every option, with its cost. Then: where can it still glide?' },
  { id: 'divert', movement: 4, dur: 9, title: 'ANUMAAN advises. The crew decides.', body: 'Thoise is in reach. Power comes back to spare the engine.' },
  { id: 'land', movement: 4, dur: 13, title: 'The airframe comes home.', body: 'With its work order already written.' },
  { id: 'beyond', movement: 5, dur: 15, title: 'Never seen it. Still caught.', body: 'A trained model can only name what it was taught. The fly circuit learned normal flight, so anything else stands out.' },
];

export const STARTS = CHAPTERS.reduce<number[]>((acc, _c, i) => { acc.push(i ? acc[i - 1] + CHAPTERS[i - 1].dur : 0); return acc; }, []);
export const TOTAL = STARTS[STARTS.length - 1] + CHAPTERS[CHAPTERS.length - 1].dur;
export const chapterAt = (t: number) => { let i = 0; while (i < STARTS.length - 1 && t >= STARTS[i + 1]) i++; return i; };
export const startOf = (id: ChapterId) => STARTS[CHAPTERS.findIndex((c) => c.id === id)];

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const smooth = (x: number) => { const k = clamp01(x); return k * k * (3 - 2 * k); };

/* ------------------------------------------------------------------ the fault and the sensor stream */

/** The moment the fault begins (in the oil system, on screen in the engine bay). */
export const T_INJECT = startOf('signal') + 1.0;
/** Seconds the fault takes to develop (the console's ramp_sec, compressed to story time). */
const RAMP = 85;
/** The decision: options, then the glide assessment sweeps out from the aircraft. */
export const T_DECIDE = startOf('decide');
export const T_ASSESS = T_DECIDE + 5.0;
/** The crew accepts the divert: the aircraft turns off its valley and power comes back. */
export const T_TURN = startOf('divert') + 0.6;
/** Kept for modules that key the derate and descent to it. */
export const T_GLIDE = T_TURN;
export const T_TOUCH = startOf('land') + 7.0;
/** The flash-forward: two silent seconds of what a late warning looks like. */
export const FLASH = { from: startOf('problem') + 10.5, to: startOf('problem') + 12.8 };
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
