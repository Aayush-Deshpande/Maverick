import React from 'react';
import { Cpu, ShieldCheck, Gauge, RefreshCw } from 'lucide-react';

export const LandingTwin: React.FC = () => {
  return (
    <section id="twin" className="py-24 sm:py-32 px-4 sm:px-6 max-w-7xl mx-auto border-b border-white/[0.08]">
      {/* Header */}
      <div className="space-y-4 max-w-3xl">
        <div className="flex items-center gap-2 text-[11px] font-hud tracking-[0.2em] text-cyan-400 uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          <span>03 / DIGITAL TWIN THEORY</span>
          <span className="text-slate-600">—</span>
          <span>STATE ESTIMATION &amp; SYNTHESIS</span>
        </div>

        <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-white leading-tight font-display">
          An airworthiness digital twin is not a 3D animation.{' '}
          <span className="font-editorial italic font-normal text-slate-300">
            It is a deterministic mathematical state observer.
          </span>
        </h2>

        <p className="text-sm sm:text-base text-slate-300 font-sans font-light leading-relaxed">
          In military aviation, pure deep learning fails due to catastrophic data scarcity and lack of verifiable bounds. ANUMAAN anchors real-time telemetry to first-principles 0D/1D thermodynamics. The physics model generates the healthy baseline; AI isolates the subtle deviations.
        </p>
      </div>

      {/* 4 Core Pillars of the Digital Twin Engine */}
      <div className="mt-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Pillar 1: First-Principles Thermodynamics */}
        <div className="p-6 rounded-sm bg-[#090c13] border border-white/10 space-y-4 hover:border-cyan-400/40 transition-colors">
          <div className="w-8 h-8 rounded-xs bg-white/5 border border-white/10 flex items-center justify-center text-cyan-400">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-hud">
              0D/1D THERMODYNAMICS
            </h3>
            <span className="text-[10px] font-hud text-slate-500 uppercase tracking-wide">First-Principles Foundation</span>
          </div>
          <p className="text-xs font-sans text-slate-300 font-light leading-relaxed">
            Deterministic mass and energy conservation equations modeling in-cylinder combustion, manifold filling dynamics, and heat rejection across all operational airspeeds and ambient temperatures.
          </p>
          <div className="pt-2 border-t border-white/5 text-[10px] font-mono text-cyan-400">
            &Delta;E = Q_in - W_shaft - Q_coolant
          </div>
        </div>

        {/* Pillar 2: UKF State Observer */}
        <div className="p-6 rounded-sm bg-[#090c13] border border-white/10 space-y-4 hover:border-cyan-400/40 transition-colors">
          <div className="w-8 h-8 rounded-xs bg-white/5 border border-white/10 flex items-center justify-center text-cyan-400">
            <RefreshCw className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-hud">
              UKF STATE OBSERVER
            </h3>
            <span className="text-[10px] font-hud text-slate-500 uppercase tracking-wide">20 Hz Real-Time Synchronization</span>
          </div>
          <p className="text-xs font-sans text-slate-300 font-light leading-relaxed">
            Unscented Kalman Filter tracking nonlinear thermal and hydraulic states. Filters sensor noise while capturing rapid transient changes during pilot throttle inputs.
          </p>
          <div className="pt-2 border-t border-white/5 text-[10px] font-mono text-cyan-400">
            Innovation: v_k = y_k - h(x_k|k-1)
          </div>
        </div>

        {/* Pillar 3: Virtual Sensor Synthesis */}
        <div className="p-6 rounded-sm bg-[#090c13] border border-white/10 space-y-4 hover:border-emerald-400/40 transition-colors">
          <div className="w-8 h-8 rounded-xs bg-white/5 border border-white/10 flex items-center justify-center text-emerald-400">
            <Gauge className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-hud">
              VIRTUAL SENSORS
            </h3>
            <span className="text-[10px] font-hud text-slate-500 uppercase tracking-wide">Observing The Unmeasured</span>
          </div>
          <p className="text-xs font-sans text-slate-300 font-light leading-relaxed">
            Synthesizes flight-critical parameters where physical sensors are prohibited due to weight, cost, or harshness: Peak Cylinder Pressure (P_max), Turbine Inlet Temp (TIT), and Oil Film Thickness (h_min).
          </p>
          <div className="pt-2 border-t border-white/5 text-[10px] font-mono text-emerald-400">
            h_min &gt; 2.5 &micro;m Journal Safety
          </div>
        </div>

        {/* Pillar 4: 3-Way Fault Attribution */}
        <div className="p-6 rounded-sm bg-[#090c13] border border-white/10 space-y-4 hover:border-amber-400/40 transition-colors">
          <div className="w-8 h-8 rounded-xs bg-white/5 border border-white/10 flex items-center justify-center text-amber-400">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-hud">
              3-WAY ATTRIBUTION
            </h3>
            <span className="text-[10px] font-hud text-slate-500 uppercase tracking-wide">Sensor vs Engine vs Twin</span>
          </div>
          <p className="text-xs font-sans text-slate-300 font-light leading-relaxed">
            Performs statistical validation (Normalized Innovation Squared &chi;&sup2; test + Ljung-Box residual whiteness) to disambiguate whether an anomaly is a sensor wiring glitch, a true mechanical fault, or twin model drift.
          </p>
          <div className="pt-2 border-t border-white/5 text-[10px] font-mono text-amber-400">
            Whiteness p &gt; 0.05 Verification
          </div>
        </div>
      </div>

      {/* Synthesized Virtual Sensor Telemetry Panel */}
      <div className="mt-12 p-6 sm:p-8 rounded-sm bg-[#080b11] border border-white/10 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-hud">
              REAL-TIME SYNTHESIZED THERMOFLUID STATES (UNMEASURED DOMAINS)
            </h3>
            <p className="text-xs font-sans text-slate-400 mt-1">
              Live UKF state estimates computed continuously during flight sortie simulation
            </p>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 self-start sm:self-auto">
            ALL VIRTUAL OBSERVERS ONLINE
          </span>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xs bg-white/[0.02] border border-white/[0.06]">
            <span className="text-[10px] font-hud text-slate-400 uppercase tracking-wider block">PEAK CYLINDER PRESSURE (P_max)</span>
            <span className="text-xl font-bold font-mono text-emerald-400 mt-1 block">65.2 bar</span>
            <span className="text-[10px] font-sans text-slate-400 mt-1 block">In-cylinder thermodynamic peak</span>
          </div>

          <div className="p-4 rounded-xs bg-white/[0.02] border border-white/[0.06]">
            <span className="text-[10px] font-hud text-slate-400 uppercase tracking-wider block">TURBINE INLET TEMP (TIT)</span>
            <span className="text-xl font-bold font-mono text-amber-400 mt-1 block">810.0 &deg;C</span>
            <span className="text-[10px] font-sans text-slate-400 mt-1 block">Pre-turbine collector state</span>
          </div>

          <div className="p-4 rounded-xs bg-white/[0.02] border border-white/[0.06]">
            <span className="text-[10px] font-hud text-slate-400 uppercase tracking-wider block">MIN OIL FILM THICKNESS (h_min)</span>
            <span className="text-xl font-bold font-mono text-slate-200 mt-1 block">2.82 &micro;m</span>
            <span className="text-[10px] font-sans text-slate-400 mt-1 block">Hydrodynamic journal safety margin</span>
          </div>

          <div className="p-4 rounded-xs bg-white/[0.02] border border-white/[0.06]">
            <span className="text-[10px] font-hud text-slate-400 uppercase tracking-wider block">GROSS INDICATED POWER (P_ind)</span>
            <span className="text-xl font-bold font-mono text-sky-400 mt-1 block">72.4 kW</span>
            <span className="text-[10px] font-sans text-slate-400 mt-1 block">Calculated shaft gas work</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default LandingTwin;
