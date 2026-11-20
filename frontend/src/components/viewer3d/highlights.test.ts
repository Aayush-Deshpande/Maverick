import { describe, expect, it } from 'vitest';
import { focusNodes, highlightMap, sanitize } from './highlights';

const h = (level: string, nodes: string[]) => ({ component_id: 'c', level, nodes, reason: 'r' }) as any;

describe('highlightMap', () => {
  it('lights exactly the nodes in the message, highest level wins on overlap', () => {
    const m = highlightMap([h('INJECTED', ['Oil_Tank_A', 'Oil_Tank_B']), h('NO-GO', ['Oil_Tank_B']), h('SENSOR', ['ECU_1'])]);
    expect([...m.keys()].sort()).toEqual(['ECU_1', 'Oil_Tank_A', 'Oil_Tank_B']);
    expect(m.get('Oil_Tank_B')).toBe('NO-GO');
    expect(m.get('Oil_Tank_A')).toBe('INJECTED');
  });

  it('matches loader-sanitized names (spaces become underscores) and ignores unknown levels', () => {
    const m = highlightMap([h('CAUTION', ['Main engine']), h('BOGUS', ['X'])]);
    expect(m.get(sanitize('Main engine'))).toBe('CAUTION');
    expect(sanitize('Main engine')).toBe('Main_engine');
    expect(m.has('X')).toBe(false);
  });

  it('nothing highlighted without highlights', () => {
    expect(highlightMap(undefined).size).toBe(0);
  });
});

describe('focusNodes', () => {
  it('frames the parts at the highest level present, and nothing when nothing is lit', () => {
    const levels = new Map([['Oil_Tank', 'CAUTION'], ['ECU', 'NO-GO'], ['Wiring', 'NO-GO'], ['Hose', 'INJECTED']] as const);
    expect(focusNodes(new Map(levels))).toEqual(['ECU', 'Wiring']);
    expect(focusNodes(new Map())).toEqual([]);
  });
});
