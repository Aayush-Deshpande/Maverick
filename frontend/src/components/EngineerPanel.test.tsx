import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import EngineerPanel from './EngineerPanel';

describe('EngineerPanel', () => {
  it('ranks residuals by |z| and shows twin parameters, virtual sensors labelled VIRTUAL', () => {
    const res: Record<string, number> = {};
    for (let i = 0; i < 12; i += 1) res[`ch_${i}`] = i % 2 ? -i : i;
    const html = renderToStaticMarkup(<EngineerPanel residuals={res}
      twin={{ nis: 1.2, params: [{ name: 'eta_cool', location: 'cyl1', mean: 0.62, ci: [0.5, 0.7], healthy: false }] }}
      virtualSensors={{ P_max_bar: 41.2 }} vibration={{ '1X': 0.1 }} />);
    expect(html.indexOf('ch_11')).toBeLessThan(html.indexOf('ch_10'));     // |-11| ranks before |10|
    expect(html).not.toContain('>ch_1<');                                    // only the top 10 by default
    expect(html).toContain('Show all 12');
    expect(html).toContain('outside nominal');
    expect(html).toContain('VIRTUAL');
    expect(html).toContain('Peak cylinder pressure');
  });

  it('shows NO DATA, not zeros, before calibration', () => {
    const html = renderToStaticMarkup(<EngineerPanel residuals={{}} twin={null} virtualSensors={{}} vibration={{}} />);
    expect(html).toContain('not calibrated yet');
    expect(html).not.toMatch(/>0\.0</);
  });
});
