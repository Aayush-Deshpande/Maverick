/* Master warning / master caution tones (P Part 6 U2, AC 25.1322-1: one unique tone per alert level).
   Generated with Web Audio, so no audio files ship. A browser only allows sound after a user gesture; until then
   play() does nothing, and the visual alert stays the primary channel. */

export type ToneLevel = 'NO-GO' | 'CAUTION';

// [frequency Hz, duration s] steps: warning = fast high triple chime, caution = single lower chime
const PATTERNS: Record<ToneLevel, Array<[number, number]>> = {
  'NO-GO': [[1000, 0.12], [0, 0.06], [1000, 0.12], [0, 0.06], [1000, 0.12]],
  CAUTION: [[660, 0.3]],
};
const GAIN = 0.15;

type Ctx = { currentTime: number; destination: unknown; createOscillator: () => any; createGain: () => any };

export function playAlertTone(level: ToneLevel, makeCtx: () => Ctx | null = defaultCtx): boolean {
  const ctx = makeCtx();
  if (!ctx) return false;
  let t = ctx.currentTime;
  for (const [freq, dur] of PATTERNS[level]) {
    if (freq > 0) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      gain.gain.value = GAIN;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(t);
      osc.stop(t + dur);
    }
    t += dur;
  }
  return true;
}

let shared: Ctx | null = null;
function defaultCtx(): Ctx | null {
  try {
    const AC = (globalThis as any).AudioContext ?? (globalThis as any).webkitAudioContext;
    if (!AC) return null;
    shared = shared ?? new AC();
    return shared;
  } catch {
    return null;                                          // audio blocked or unavailable: visual alert only
  }
}

/** The tone to sound when the status moves from `prev` to `next`: only on entering a worse alert level. */
export function toneFor(prev: string | undefined, next: string | undefined): ToneLevel | null {
  const ORDER = ['CAUTION', 'NO-GO'];                     // alert levels that sound, mildest first
  const a = ORDER.indexOf(prev ?? '');                    // -1 = not an aural alert level
  const b = ORDER.indexOf(next ?? '');
  if (b <= a) return null;
  return next === 'NO-GO' ? 'NO-GO' : 'CAUTION';
}
