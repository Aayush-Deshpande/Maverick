// Everything the film shows at a story time, assembled from the signal (story.ts) and the detector that
// reads it (detector.ts). The alarm is latched at the gate's confirmation, as an operator's alarm is.
import { T_TOUCH, gauges, smooth, startOf } from './story';
import { T_CONFIRM, T_CROSS, tier0, type ScorerName } from './detector';

export { T_CONFIRM, T_CROSS };

export interface Readout {
  t: number;
  sev: number;
  rpm: number;
  cht: number;
  oilT: number;
  oilP: number;
  oilPExp: number;
  altFt: number;
  ratios: Record<ScorerName, number>;
  raw: boolean;
  window: boolean[];
  confirmed: boolean;
  rul: number;
  rulLo: number;
  rulHi: number;
  missionRel: number;
}

export function readout(t: number): Readout {
  const g = gauges(t);
  const d = tier0(t);
  const confirmed = t >= T_CONFIRM;
  const rul = 410 - 407.6 * smooth((t - T_CONFIRM) / 6);
  return {
    t, ...g,
    ratios: d.ratios, raw: d.raw, window: d.window, confirmed,
    rul: Math.max(2.4, rul), rulLo: Math.max(1.6, rul * 0.67), rulHi: Math.max(3.3, rul * 1.38),
    missionRel: 0.978 - (0.978 - 0.41) * smooth((t - T_CONFIRM - 1) / 5),
  };
}

/** Cross-cut to the ground station as the gate fires (real console recording). */
export const INSERT = { at: T_CONFIRM - 0.05, dur: 3.0, src: '/survey/insert-confirm.mp4' };

/** Radio traffic, captioned in the letterbox. Every line restates what is on screen. */
export const RADIO: Array<{ at: number; who: string; line: string }> = [
  { at: startOf('twin') + 1.5, who: 'Leh ground control', line: 'Twin locked on. All channels nominal.' },
  { at: startOf('inside') + 6.0, who: 'Leh ground control', line: 'Injecting scenario: oil pressure loss, severity zero point eight.' },
  { at: startOf('drift') + 2.5, who: 'ANUMAAN', line: 'Oil pressure trending below expected. Inside limits. Watching.' },
  { at: T_CONFIRM + 0.6, who: 'ANUMAAN', line: 'Oil pressure loss confirmed. Three of five frames. ATA 79.' },
  { at: startOf('decide') + 2.5, who: 'Leh ground control', line: 'Copy. Two point four hours remaining. Nearest field?' },
  { at: startOf('glide') + 3.5, who: 'ANUMAAN', line: 'Thoise in glide reach, sixteen hundred feet margin. Leh short.' },
  { at: startOf('land') + 0.8, who: 'Leh ground control', line: 'Diverting to Thoise.' },
  { at: T_TOUCH + 1.6, who: 'Thoise tower', line: 'Wheels down.' },
];
export const RADIO_HOLD = 3.6;
