import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Activity, AlertTriangle, CheckCircle2, Clock, Cpu, Gauge, Info, ShieldCheck, Wrench, X, Zap } from 'lucide-react';

interface RuntimeGuideModalProps {
  open: boolean;
  onClose: () => void;
}

export const RuntimeGuideModal: React.FC<RuntimeGuideModalProps> = ({ open, onClose }) => {
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const modal = (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="runtime-guide-title"
    >
      <div
        className="surface-panel w-full max-w-2xl max-h-[85vh] flex flex-col rounded-sm shadow-card-lg border border-surface-border-strong text-slate-800 bg-[#f7f6f0] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header - pinned at top */}
        <div className="flex items-start justify-between border-b border-surface-border p-4 shrink-0 bg-[#f7f6f0]">
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-[#68757a] font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Avionics Architecture · Multi-Engine Runtime</span>
            </div>
            <h2 id="runtime-guide-title" className="text-base font-bold text-slate-900 tracking-tight mt-1">
              ANUMAAN Analytical Pipeline &amp; Mathematical Foundations
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-sm p-1.5 text-slate-400 hover:text-slate-800 hover:bg-black/10 transition-colors"
            title="Close guide (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3.5 text-xs font-mono leading-relaxed">
          {/* Section 1 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-accent font-semibold uppercase tracking-wider text-[11px]">
              <Zap className="w-3.5 h-3.5" />
              <span>1. Zero-Falsification Dynamic Simulation (20 Hz)</span>
            </div>
            <p className="mt-1.5 text-slate-700 font-sans text-xs">
              All engine channels (RPM, CHT, EGT, manifold pressure, fuel mass flow) are computed in continuous time by real thermodynamic differential equations integrated at 20 Hz (Δt = 50 ms):
            </p>
            <div className="mt-2 rounded bg-black/5 p-2 font-mono text-[11px] text-slate-800 border border-black/5">
              dT_i / dt = (Q̇_in,i - Q̇_out,i) / (m_i · C_p,i)
            </div>
            <p className="mt-1.5 text-slate-600 font-sans text-[11px]">
              Readings are never mocked or randomly generated. Injected fault scenarios alter physical plant coefficients (e.g. fuel injector orifice area, boost leak conductance, valve sealing, cooling jacket heat exchange) rather than outputs directly.
            </p>
          </div>

          {/* Section 2 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px]">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>2. Sensor FDI &amp; Quarantine Shielding</span>
            </div>
            <p className="mt-1.5 text-slate-700 font-sans text-xs">
              Every sensor channel undergoes 20 Hz Fault Detection &amp; Isolation (FDI) checking operational range limits, signal noise variance, and maximum slew rate. Degraded or shorted sensors are tagged <code className="bg-black/5 px-1 rounded">Q_SHIELDED</code> and excluded from engine anomaly scores, preventing sensor harness issues from generating false engine shutdown alarms.
            </p>
          </div>

          {/* Section 3 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px]">
              <Cpu className="w-3.5 h-3.5 text-cyan-700" />
              <span>3. Unscented Kalman Filter (UKF) State Observer</span>
            </div>
            <p className="mt-1.5 text-slate-700 font-sans text-xs">
              An online UKF observer executes non-linear state propagation using measured operational inputs (throttle, RPM, OAT, altitude). It estimates internal temperatures, heat transfer conductance <code className="bg-black/5 px-1 rounded">U_cyl</code>, and tracks the Normalized Innovation Squared (NIS). When physical sensors are quarantined, the UKF supplies synthesized analytical replacements tagged <code className="bg-black/5 px-1 rounded">VIRTUAL</code>.
            </p>
          </div>

          {/* Section 4 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px]">
              <Gauge className="w-3.5 h-3.5 text-indigo-700" />
              <span>4. Virtual Sensor Synthesis</span>
            </div>
            <p className="mt-1.5 text-slate-700 font-sans text-xs">
              Synthesizes inaccessible physical variables in real time without requiring dedicated onboard instrumentation:
            </p>
            <ul className="mt-1.5 list-disc pl-5 space-y-1 text-slate-600 font-sans text-[11px]">
              <li><strong>P_max (Peak Cylinder Pressure)</strong>: Derived from indicated P-V work and combustion phasing (bar).</li>
              <li><strong>h_min (Bearing Oil Film)</strong>: Hydrodynamic crankshaft journal minimum thickness via Reynolds equation (µm).</li>
              <li><strong>P_ind (Indicated Power)</strong>: In-cylinder cyclic mechanical work delivered to piston crowns (kW).</li>
              <li><strong>TIT (Turbine Inlet Temp)</strong>: Pre-turbine exhaust stagnation temperature on turbocharged variants (°C).</li>
            </ul>
          </div>

          {/* Section 5 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px]">
              <Activity className="w-3.5 h-3.5 text-amber-600" />
              <span>5. Multi-Channel Residual Anomaly Detection</span>
            </div>
            <p className="mt-1.5 text-slate-700 font-sans text-xs">
              The detector evaluates normalized innovation residuals <code className="bg-black/5 px-1 rounded">z = (y_meas - y_model) / σ_noise</code> across all calibrated channels:
            </p>
            <ul className="mt-1.5 list-disc pl-5 space-y-1 text-slate-600 font-sans text-[11px]">
              <li><strong>Tier-0 Score</strong>: Mahalanobis distance relative to false-alarm threshold. Ratio &gt; 1.0 flags a raw anomaly.</li>
              <li><strong>Persistence Gate</strong>: Multi-frame temporal confirmation eliminates transient single-tick noise spikes before declaring a confirmed alarm.</li>
              <li><strong>Tier-1 Reservoir Computing</strong>: A 500-node sparse Echo State Network (ESN) classifies non-linear dynamic patterns across multivariate time series.</li>
            </ul>
          </div>

          {/* Section 6 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px]">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
              <span>6. Bayesian Fault Isolation</span>
            </div>
            <p className="mt-1.5 text-slate-700 font-sans text-xs">
              Computes continuous Bayesian posterior probabilities <code className="bg-black/5 px-1 rounded">P(Fault | z)</code> over all registered failure modes and sensor bias modes. The leading candidate identifies the specific cylinder, subsystem, confidence percentage, and supporting channel z-scores.
            </p>
          </div>

          {/* Section 7 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px]">
              <Clock className="w-3.5 h-3.5 text-blue-700" />
              <span>7. Fatigue Damage Accumulation &amp; Conformal RUL</span>
            </div>
            <p className="mt-1.5 text-slate-700 font-sans text-xs">
              Continuous thermal-mechanical stress cycles are counted via online Rainflow algorithms on cylinder heads. Linear trend forecasting projects <strong>Time to Limit (TTL)</strong> in minutes. A conformal quantile regression model estimates <strong>Remaining Useful Life (RUL)</strong> in operating hours with a 90% guaranteed statistical coverage band.
            </p>
          </div>

          {/* Section 8 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px]">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
              <span>8. Mission Reliability &amp; Forward Monte Carlo</span>
            </div>
            <p className="mt-1.5 text-slate-700 font-sans text-xs">
              Executes 10,000 forward Monte Carlo rollouts across planned mission profile phases (takeoff, climb, cruise, loiter, dash, descent). Combines baseline Weibull hazard rates with active component fatigue damage to output mission success probability, 95% confidence intervals, and the critical limiting component.
            </p>
          </div>

          {/* Section 9 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px]">
              <Wrench className="w-3.5 h-3.5 text-slate-700" />
              <span>9. Automated ATA Work Orders</span>
            </div>
            <p className="mt-1.5 text-slate-700 font-sans text-xs">
              Evidence-based maintenance dispatches work orders mapped to standard Air Transport Association (ATA) chapters (ATA 72 Engine, ATA 73 Fuel, ATA 74 Ignition, ATA 75 Cooling, ATA 79 Lubrication) whenever isolated fault posteriors or impending limit crossings require line maintenance.
            </p>
          </div>
        </div>

        {/* Modal Footer - pinned at bottom */}
        <div className="flex items-center justify-between border-t border-surface-border p-3 shrink-0 bg-[#f7f6f0]">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-600 font-mono">
            <Info className="w-3.5 h-3.5 text-slate-400" />
            <span>Fully dynamic plant · Zero mock data · DRDO/IDEX PS-26054</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-sm bg-accent px-3 py-1.5 text-xs font-mono font-medium text-white hover:bg-accent/90 transition-colors shadow-sm"
          >
            Acknowledge &amp; Close [Esc]
          </button>
        </div>
      </div>
    </div>
  );

  if (typeof document === 'undefined') return modal;
  return createPortal(modal, document.body);
};

export default RuntimeGuideModal;
