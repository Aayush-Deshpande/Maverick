import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import CanBusInspector from './CanBusInspector';

describe('CanBusInspector Modal component', () => {
  it('renders nothing when isOpen is false', () => {
    const html = renderToStaticMarkup(
      <CanBusInspector engineId="rotax_912is" isOpen={false} onClose={() => {}} />
    );
    expect(html).toBe('');
  });

  it('renders CAN bus avionics HUD when isOpen is true', () => {
    const html = renderToStaticMarkup(
      <CanBusInspector engineId="rotax_912is" isOpen={true} onClose={() => {}} />
    );
    expect(html).toContain('Avionics CAN Bus &amp; FADEC Telemetry Hub');
    expect(html).toContain('SAE J1939 29-bit ID');
    expect(html).toContain('Telemetry Source Mode');
    expect(html).toContain('CAN Intrusion Detection System (IDS)');
    expect(html).toContain('Rogue ID');
    expect(html).toContain('Sequence Gap');
    expect(html).toContain('Out-Of-Range Payload');
  });
});
