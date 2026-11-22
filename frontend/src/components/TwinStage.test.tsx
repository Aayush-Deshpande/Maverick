import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import TwinStage from './TwinStage';

const dummyApi = async () => ({});
const dummyCommand = async () => ({});

const dummyFaults = [
  {
    id: 'F01',
    name: 'SPARK_PLUG_FOULING',
    scope: 'CYLINDER',
    kind: 'MECHANICAL',
    default_severity: 0.8,
    components: {
      rotax_912is: { now: ['Cylinder_1_Head', 'Spark_Plug_1'] },
    },
  },
  {
    id: 'F13',
    name: 'TURBO_BOOST_LEAK',
    scope: 'SYSTEM',
    kind: 'THERMO',
    default_severity: 1.0,
    components: {
      rotax_912is: { now: ['Turbocharger_Housing'] },
    },
  },
];

const dummyEngines = [
  { engine_id: 'rotax_912is', display_name: 'Rotax 912 iSc Sport' },
  { engine_id: 'austro_ae300', display_name: 'Austro Engine AE300' },
];

describe('TwinStage 3D View & Telemetry Interlock', () => {
  it('renders the 3D twin stage with powerplant selector, fault panel, and telemetry bus HUD', () => {
    const html = renderToStaticMarkup(
      <TwinStage
        engineId="rotax_912is"
        engines={dummyEngines}
        onSelectEngine={() => {}}
        state={{ status: { level: 'GO', reasons: [] }, active_faults: [], highlights: [] }}
        faults={dummyFaults}
        cylinders={4}
        api={dummyApi}
        command={dummyCommand}
        training={true}
        onTraining={() => {}}
      />
    );

    // Verify powerplant dropdown
    expect(html).toContain('Powerplant');
    expect(html).toContain('Rotax 912 iSc Sport');
    expect(html).toContain('Austro Engine AE300');

    // Verify Guide and Command Palette buttons on top right
    expect(html).toContain('Twin Guide');
    expect(html).toContain('Commands');
    expect(html).toContain('Ctrl+K');
    expect(html).toContain('title="Digital Twin &amp; Telemetry Architecture Guide (Press ?)"');

    // Verify Telemetry Bus HUD in the fault aside panel
    expect(html).toContain('TELEMETRY BUS READY');

    // Verify interactive fault buttons
    expect(html).toContain('Spark Plug Fouling');
    expect(html).toContain('Turbo Boost Leak');
    expect(html).toContain('· cyl 1');

    // Verify Annunciator strip
    expect(html).toContain('GO');
  });

  it('renders alert strip when status is NO-GO or CAUTION', () => {
    const html = renderToStaticMarkup(
      <TwinStage
        engineId="rotax_912is"
        engines={dummyEngines}
        onSelectEngine={() => {}}
        state={{
          status: { level: 'NO-GO', reasons: [{ text: 'Loss of oil pressure' }] },
          active_faults: [{ fault_id: 'F23', name: 'OIL_PRESSURE_LOSS' }],
          highlights: [{ component_id: 'Oil_Pump', level: 'NO-GO', reason: 'Critical pressure drop' }],
        }}
        faults={dummyFaults}
        cylinders={4}
        api={dummyApi}
        command={dummyCommand}
        training={true}
        onTraining={() => {}}
      />
    );

    expect(html).toContain('NO-GO');
    expect(html).toContain('border-l-critical');
    expect(html).toContain('Loss of oil pressure');
    expect(html).toContain('Oil Pump — Critical pressure drop');
  });
});
