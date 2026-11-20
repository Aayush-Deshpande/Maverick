import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import RouteMap from './RouteMap';

const fields = [{ id: 'VILH', name: 'Leh', lat: 34.1359, lon: 77.5465, status: 'MARGINAL' }];

describe('RouteMap', () => {
  it('draws nothing without data', () => {
    expect(renderToStaticMarkup(<RouteMap airfields={[]} />)).toBe('');
  });

  it('draws the route, the footprint and labelled airfields inside the view box', () => {
    const html = renderToStaticMarkup(
      <RouteMap airfields={fields}
        route={[{ lat: 34.4, lon: 77.45 }, { lat: 34.2, lon: 77.5 }]}
        footprint={[{ lat: 34.5, lon: 77.4 }, { lat: 34.4, lon: 77.6 }, { lat: 34.3, lon: 77.4 }]}
        aircraft={{ lat: 34.4, lon: 77.45 }} />);
    expect(html).toContain('<polyline');
    expect(html).toContain('<polygon');
    expect(html).toContain('VILH · MARGINAL');
    const nums = [...html.matchAll(/(?:cx|cy)="([-\d.]+)"/g)].map((m) => Number(m[1]));
    expect(nums.every((v) => v >= 0 && v <= 480)).toBe(true);
  });
});
