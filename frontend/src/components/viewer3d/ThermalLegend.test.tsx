import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import ThermalLegend from './ThermalLegend';

describe('ThermalLegend HUD overlay', () => {
  it('renders cylinder CHT temperatures and limit indicators', () => {
    const readings = {
      CHT_1: 118.5,
      CHT_2: 122.0,
      CHT_3: 120.2,
      CHT_4: 136.4,
      EGT_1: 820.0,
      EGT_2: 835.0,
      EGT_3: 825.0,
      EGT_4: 840.0,
    };

    const html = renderToStaticMarkup(<ThermalLegend readings={readings} chtMax={135} egtMax={950} />);

    expect(html).toContain('Thermal Pyrometry (FLIR)');
    expect(html).toContain('118.5°C');
    expect(html).toContain('136.4°C');
    expect(html).toContain('840.0°C');
    expect(html).toContain('CYL 1');
    expect(html).toContain('CYL 4');
  });

  it('renders fallback when no telemetry readings are available', () => {
    const html = renderToStaticMarkup(<ThermalLegend readings={null} />);
    expect(html).toContain('Thermal Pyrometry (FLIR)');
    expect(html).toContain('NO DATA');
  });
});
