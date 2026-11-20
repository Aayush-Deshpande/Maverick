import { describe, expect, it } from 'vitest';
import { playAlertTone, toneFor } from './alertTone';

function fakeCtx() {
  const started: number[] = [];
  const freqs: number[] = [];
  const node = () => ({ connect: () => {}, gain: { value: 0 } });
  return {
    started, freqs,
    ctx: {
      currentTime: 0, destination: {},
      createGain: node,
      createOscillator: () => ({ ...node(), frequency: { set value(v: number) { freqs.push(v); } }, start: (t: number) => started.push(t), stop: () => {} }),
    },
  };
}

describe('alert tones', () => {
  it('sounds only when entering a worse alert level', () => {
    expect(toneFor('GO', 'CAUTION')).toBe('CAUTION');
    expect(toneFor('CAUTION', 'NO-GO')).toBe('NO-GO');
    expect(toneFor('NO-GO', 'CAUTION')).toBeNull();
    expect(toneFor('CAUTION', 'CAUTION')).toBeNull();
    expect(toneFor('GO', 'ADVISORY')).toBeNull();
    expect(toneFor(undefined, 'GO')).toBeNull();
  });

  it('warning and caution are distinct patterns; no audio context means visual only', () => {
    const w = fakeCtx();
    expect(playAlertTone('NO-GO', () => w.ctx)).toBe(true);
    const c = fakeCtx();
    playAlertTone('CAUTION', () => c.ctx);
    expect(w.started.length).toBe(3);
    expect(c.started.length).toBe(1);
    expect(new Set(w.freqs)).not.toEqual(new Set(c.freqs));
    expect(playAlertTone('CAUTION', () => null)).toBe(false);
  });
});
