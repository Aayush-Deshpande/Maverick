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

describe('AltitudeProfile', () => {
  it('keeps the planned line above the terrain band when the plan has clearance', async () => {
    const { default: AltitudeProfile } = await import('./AltitudeProfile');
    const wps = [
      { lat: 34.4, lon: 77.45, altitude_ft: 20000, terrain_ft: 17000 },
      { lat: 34.3, lon: 77.5, altitude_ft: 21000, terrain_ft: 19500 },
      { lat: 34.2, lon: 77.5, altitude_ft: 14000, terrain_ft: 11000 },
    ];
    const html = renderToStaticMarkup(<AltitudeProfile waypoints={wps} />);
    const line = /<polyline points="([^"]+)"/.exec(html)![1].split(' ').map((p) => Number(p.split(',')[1]));
    const ground = /<polygon points="([^"]+)"/.exec(html)![1].split(' ').slice(1, -1).map((p) => Number(p.split(',')[1]));
    line.forEach((yv, i) => expect(yv).toBeLessThan(ground[i]));            // SVG y grows downward
  });
});
