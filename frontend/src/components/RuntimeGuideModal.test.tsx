import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { RuntimeGuideModal } from './RuntimeGuideModal';

describe('RuntimeGuideModal', () => {
  it('renders complete analytical architecture sections when open', () => {
    const html = renderToStaticMarkup(<RuntimeGuideModal open={true} onClose={() => {}} />);
    expect(html).toContain('How ANUMAAN Monitors Engine Health, Detects Faults, and Protects Aircraft');
    expect(html).toContain('Real Engine Physics (20 Times Every Second)');
    expect(html).toContain('Smart Sensor Health Check');
    expect(html).toContain('Background Digital Twin Observer');
    expect(html).toContain('Virtual Sensors (Seeing Deep Inside the Engine)');
    expect(html).toContain('Instant Anomaly Detection');
    expect(html).toContain('Pinpoint Root-Cause Diagnosis');
    expect(html).toContain('Remaining Useful Life &amp; Danger Warnings');
    expect(html).toContain('Mission Reliability &amp; Risk Forecasting');
    expect(html).toContain('Automated Ground Crew Work Orders');
    expect(html).toContain('Multi-Mode 3D Viewport &amp; FLIR Thermal Pyrometry');
    expect(html).toContain('Avionics SAE J1939 CAN Bus &amp; Threat Detection');
    expect(html).toContain('Tactical Command Palette &amp; Remote Cockpit Displays');
  });

  it('renders nothing when closed', () => {
    const html = renderToStaticMarkup(<RuntimeGuideModal open={false} onClose={() => {}} />);
    expect(html).toBe('');
  });
});
