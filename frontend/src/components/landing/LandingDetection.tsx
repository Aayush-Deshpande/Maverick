import React from 'react';
import { CheckCircle2 } from 'lucide-react';

export const LandingDetection: React.FC = () => {
  return (
    <section id="detection" className="py-24 sm:py-32 px-4 sm:px-6 max-w-7xl mx-auto border-b border-white/[0.08]">
      {/* Header */}
      <div className="space-y-4 max-w-3xl">
        <div className="flex items-center gap-2 text-[11px] font-mono tracking-[0.2em] text-accent uppercase">
          <span>04 / MULTI-TIER ANOMALY ISOLATION</span>
          <span className="text-slate-600">—</span>
          <span>TIER-0 AND TIER-1 RESIDUAL ANALYSIS</span>
        </div>

        <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-white leading-tight font-mono">
          Single sensor channels trigger nuisance alarms.{' '}
          <span className="font-editorial italic font-normal text-slate-300">
            Correlated multi-channel residuals reveal the true failure signature.
          </span>
        </h2>

        <p className="text-sm sm:text-base text-slate-400 font-mono leading-relaxed">
          When a pilot climbs, engine temperature and manifold pressure rise together — a normal thermodynamic response. A univariate threshold trips an alarm; ANUMAAN evaluates the Mahalanobis covariance space. If CHT rises while MAP falls, the anomaly is isolated immediately.
        </p>
      </div>

      {/* Two-Tier Detection Pipeline */}
      <div className="mt-16 grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Tier-0: Sub-Millisecond Statistical Anomaly Tracking */}
        <div className="p-6 sm:p-8 rounded-sm bg-[#0e131d]/90 border border-white/10 space-y-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-2.5">
              <span className="px-2 py-0.5 rounded-xs bg-sky-500/10 text-sky-400 font-mono text-[10px] font-bold border border-sky-500/30">
                TIER 0
              </span>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                STATISTICAL ANOMALY DETECTION
              </h3>
            </div>
            <span className="text-[10px] font-mono text-slate-500 uppercase">&lt; 5 ms Latency</span>
          </div>

          <p className="text-xs font-mono text-slate-400 leading-relaxed">
            Continuously compares measured telemetry vectors against the physics digital twin baseline. Computes multi-sensor distance metrics dynamically bounded by Extreme Value Theory (EVT).
          </p>

          <div className="space-y-3">
            <div className="p-3 rounded-xs bg-white/[0.02] border border-white/[0.05]">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-300">MAHALANOBIS DISTANCE (D_M)</span>
                <span className="text-sky-400 font-bold">0.71 &times; THRESHOLD [NOMINAL]</span>
              </div>
              <div className="w-full bg-white/10 h-1.5 rounded-full mt-2 overflow-hidden">
                <div className="bg-sky-400 h-full rounded-full" style={{ width: '71%' }} />
              </div>
              <span className="text-[9px] font-mono text-slate-500 mt-1 block">
                Full 27-channel covariance matrix &Sigma;^-1 weighting cross-channel physical correlations
              </span>
            </div>

            <div className="p-3 rounded-xs bg-white/[0.02] border border-white/[0.05]">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-300">MAX ABSOLUTE RESIDUAL Z-SCORE</span>
                <span className="text-emerald-400 font-bold">0.65 &times; THRESHOLD [NOMINAL]</span>
              </div>
              <div className="w-full bg-white/10 h-1.5 rounded-full mt-2 overflow-hidden">
                <div className="bg-emerald-400 h-full rounded-full" style={{ width: '65%' }} />
              </div>
              <span className="text-[9px] font-mono text-slate-500 mt-1 block">
                Normalized residual across CHT, EGT, MAP, Oil P/T and Fuel Flow
              </span>
            </div>

            <div className="p-3 rounded-xs bg-white/[0.02] border border-white/[0.05]">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-300">FLY BLOOM TRANSIENT FILTER</span>
                <span className="text-sky-400 font-bold">0.26 &times; THRESHOLD [CLEAN]</span>
              </div>
              <div className="w-full bg-white/10 h-1.5 rounded-full mt-2 overflow-hidden">
                <div className="bg-sky-400 h-full rounded-full" style={{ width: '26%' }} />
              </div>
              <span className="text-[9px] font-mono text-slate-500 mt-1 block">
                High-frequency transient hash gate rejecting electrical bus spikes and telemetry dropouts
              </span>
            </div>
          </div>
        </div>

        {/* Tier-1: Echo State Network Reservoir Isolation */}
        <div className="p-6 sm:p-8 rounded-sm bg-[#0e131d]/90 border border-white/10 space-y-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-2.5">
              <span className="px-2 py-0.5 rounded-xs bg-accent/15 text-accent font-mono text-[10px] font-bold border border-accent/30">
                TIER 1
              </span>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                RESERVOIR FAULT ISOLATION
              </h3>
            </div>
            <span className="text-[10px] font-mono text-slate-500 uppercase">ESN Reservoir Computing</span>
          </div>

          <p className="text-xs font-mono text-slate-400 leading-relaxed">
            When Tier-0 detects significant residual innovation, the Tier-1 Echo State Network reservoir maps multi-channel temporal patterns onto calibrated physical failure modes.
          </p>

          <div className="grid grid-cols-2 gap-3 text-xs font-mono">
            <div className="p-3 rounded-xs bg-white/[0.02] border border-white/[0.06]">
              <span className="text-[10px] text-slate-500 block uppercase">FAILURE MODE 01</span>
              <span className="text-slate-200 font-semibold mt-1 block">AIR FILTER BLOCKAGE</span>
              <span className="text-[10px] text-slate-400 mt-1 block">Delta MAP vs RPM gradient</span>
            </div>

            <div className="p-3 rounded-xs bg-white/[0.02] border border-white/[0.06]">
              <span className="text-[10px] text-slate-500 block uppercase">FAILURE MODE 02</span>
              <span className="text-slate-200 font-semibold mt-1 block">INJECTOR COKING</span>
              <span className="text-[10px] text-slate-400 mt-1 block">Single cylinder EGT depression</span>
            </div>

            <div className="p-3 rounded-xs bg-white/[0.02] border border-white/[0.06]">
              <span className="text-[10px] text-slate-500 block uppercase">FAILURE MODE 03</span>
              <span className="text-slate-200 font-semibold mt-1 block">TURBO WASTEGATE LEAK</span>
              <span className="text-[10px] text-slate-400 mt-1 block">Boost pressure shortfall at altitude</span>
            </div>

            <div className="p-3 rounded-xs bg-white/[0.02] border border-white/[0.06]">
              <span className="text-[10px] text-slate-500 block uppercase">FAILURE MODE 04</span>
              <span className="text-slate-200 font-semibold mt-1 block">COOLING DEGRADATION</span>
              <span className="text-[10px] text-slate-400 mt-1 block">Baffle separation / thermal lag</span>
            </div>
          </div>

          <div className="p-3 rounded-xs bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono text-emerald-300 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>CURRENT OPERATIONAL EVALUATION: NOMINAL (Score: +1.704)</span>
          </div>
        </div>
      </div>
    </section>
  );
};
