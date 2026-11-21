import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { RuntimeGuideModal } from './RuntimeGuideModal';

describe('RuntimeGuideModal', () => {
  it('renders complete analytical architecture sections when open', () => {
    const html = renderToStaticMarkup(<RuntimeGuideModal open={true} onClose={() => {}} />);
    expect(html).toContain('ANUMAAN Analytical Pipeline &amp; Mathematical Foundations');
    expect(html).toContain('Zero-Falsification Dynamic Simulation (20 Hz)');
    expect(html).toContain('Sensor FDI &amp; Quarantine Shielding');
    expect(html).toContain('Unscented Kalman Filter (UKF) State Observer');
    expect(html).toContain('Virtual Sensor Synthesis');
    expect(html).toContain('Multi-Channel Residual Anomaly Detection');
    expect(html).toContain('Bayesian Fault Isolation');
    expect(html).toContain('Fatigue Damage Accumulation &amp; Conformal RUL');
    expect(html).toContain('Mission Reliability &amp; Forward Monte Carlo');
    expect(html).toContain('Automated ATA Work Orders');
    expect(html).toContain('dT_i / dt = (Q̇_in,i - Q̇_out,i) / (m_i · C_p,i)');
  });

  it('renders nothing when closed', () => {
    const html = renderToStaticMarkup(<RuntimeGuideModal open={false} onClose={() => {}} />);
    expect(html).toBe('');
  });
});
