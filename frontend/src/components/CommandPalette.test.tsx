import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import CommandPalette from './CommandPalette';

describe('CommandPalette component', () => {
  it('renders nothing when isOpen is false', () => {
    const html = renderToStaticMarkup(
      <CommandPalette
        isOpen={false}
        onClose={() => {}}
        selectedEngineId="rotax_912is"
        onSelectEngine={() => {}}
        onSelectViewMode={() => {}}
        onOpenCanInspector={() => {}}
        onOpenConnectionModal={() => {}}
        onToggleVoice={() => {}}
      />
    );
    expect(html).toBe('');
  });

  it('renders commands across engines, views, faults, and controls when isOpen is true', () => {
    const html = renderToStaticMarkup(
      <CommandPalette
        isOpen={true}
        onClose={() => {}}
        selectedEngineId="rotax_912is"
        onSelectEngine={() => {}}
        onSelectViewMode={() => {}}
        onOpenCanInspector={() => {}}
        onOpenConnectionModal={() => {}}
        onToggleVoice={() => {}}
      />
    );

    // Engines
    expect(html).toContain('Rotax 912 iSc Sport');
    expect(html).toContain('VRDE-Jayem 2.2L');
    expect(html).toContain('Austro Engine AE300');

    // 3D Visual Modes
    expect(html).toContain('Solid CAD Surface');
    expect(html).toContain('X-Ray Internal View');
    expect(html).toContain('Thermal Pyrometry Heatmap');
    expect(html).toContain('Wireframe Structural Overlay');

    // Tactical Faults & Operations
    expect(html).toContain('Ignition Misfire Cylinder 2');
    expect(html).toContain('Turbo Wastegate Actuator Seized');
    expect(html).toContain('Clear All Active Faults');

    // Avionics & CAN
    expect(html).toContain('Open Avionics CAN Bus &amp; FADEC Hub');
    expect(html).toContain('Telemetry Source: Switch to CAN Bus Link');

    // Footer shortcut
    expect(html).toContain('Ctrl+K');
  });
});
