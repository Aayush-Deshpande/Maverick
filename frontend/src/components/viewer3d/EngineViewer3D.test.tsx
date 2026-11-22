import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import EngineViewer3D from './EngineViewer3D';

describe('EngineViewer3D Multi-Mode HUD and Viewport', () => {
  const dummyApi = async () => ({
    model_url: '/assets/web/engines/rotax_914.glb',
    representative_geometry: null,
    components: [],
  });

  it('renders multi-mode segmented HUD buttons (Solid, X-Ray Glass, Thermal FLIR, Twin Ghost)', () => {
    const html = renderToStaticMarkup(
      <EngineViewer3D
        engineId="rotax_914"
        highlights={[]}
        api={dummyApi}
        readings={{ CHT_1: 110, CHT_2: 112, CHT_3: 115, CHT_4: 118, EGT_1: 810 }}
      />
    );

    expect(html).toContain('SOLID');
    expect(html).toContain('X-RAY');
    expect(html).toContain('THERMAL');
    expect(html).toContain('WIREFRAME');
  });

  it('renders ThermalLegend when viewMode is thermal', () => {
    const html = renderToStaticMarkup(
      <EngineViewer3D
        engineId="rotax_914"
        highlights={[]}
        api={dummyApi}
        viewMode="thermal"
        readings={{ CHT_1: 115, CHT_2: 118, CHT_3: 120, CHT_4: 122, EGT_1: 825 }}
      />
    );

    expect(html).toContain('Thermal Pyrometry (FLIR)');
    expect(html).toContain('115.0°C');
    expect(html).toContain('122.0°C');
  });
});
