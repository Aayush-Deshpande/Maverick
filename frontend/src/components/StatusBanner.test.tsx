import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import StatusBanner from './StatusBanner';

const api = async () => ({});
const render = (status: any, alerts: any[] = []) => renderToStaticMarkup(
  <StatusBanner engineId="e" status={status} alerts={alerts} simTimeS={100} api={api} onNotice={() => {}} />);

describe('StatusBanner', () => {
  it('uses red only for NO-GO and shows every reason with value and limit', () => {
    const html = render({ level: 'NO-GO', latched: true, acknowledged: false,
      reasons: [{ code: 'OIL_P_LOW', text: 'oil_p below minimum', value: 0.6, limit: 0.8 }] });
    expect(html).toContain('bg-critical-dim');
    expect(html).toContain('oil_p below minimum');
    expect(html).toContain('0.60 vs limit 0.80');
    expect(html).toContain('Acknowledge');
  });

  it('GO and missing status are not alerts', () => {
    expect(render({ level: 'GO', reasons: [] })).not.toMatch(/critical|warning/);
    expect(render(null)).not.toMatch(/critical|warning/);
  });

  it('lists active alerts with their action; shelved ones are not offered again', () => {
    const a = { id: 'a1', level: 'CAUTION', text: 'CHT high', action: 'Reduce power', active: true, acknowledged: false,
      count: 2, code: 'X', group: 'g', first_s: 0, last_s: 1 };
    const html = render({ level: 'CAUTION', reasons: [] }, [a, { ...a, id: 'a2', shelved_until: 500 }]);
    expect(html).toContain('Reduce power');
    expect(html).toContain('×2');
    expect((html.match(/Shelve 10 min/g) ?? []).length).toBe(1);
  });
});
