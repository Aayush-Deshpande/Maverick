import { describe, expect, it } from 'vitest';
import { channelLabel, componentLabel, humanize } from './labels';

const L = {
  channels: { oil_p: 'Oil pressure', 'cht[{n}]': 'Cylinder {n} head temperature', 'cht_{n}': 'Cylinder {n} head temperature' },
  components: { 'injector_{n}': 'Injector, cylinder {n}', ecu: 'Engine control unit (ECU)' },
  status: {},
};

describe('labels', () => {
  it('uses exact names, then cylinder patterns in both id forms', () => {
    expect(channelLabel(L, 'oil_p')).toBe('Oil pressure');
    expect(channelLabel(L, 'cht[3]')).toBe('Cylinder 3 head temperature');
    expect(channelLabel(L, 'cht_2')).toBe('Cylinder 2 head temperature');
    expect(componentLabel(L, 'injector_4')).toBe('Injector, cylinder 4');
    expect(componentLabel(L, 'ecu')).toBe('Engine control unit (ECU)');
  });

  it('falls back to a readable form, never an empty string', () => {
    expect(componentLabel(L, 'oil_filter')).toBe('Oil filter');
    expect(channelLabel(L, 'egt[2]')).toBe('Egt 2');
    expect(humanize('')).toBe('');
  });
});
