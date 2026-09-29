import React from 'react';

export const LandingPrognosis: React.FC = () => {
  return (
    <section id="prognosis" className="py-24 sm:py-32 px-4 sm:px-6 max-w-7xl mx-auto border-b border-white/[0.08]">
      {/* Header */}
      <div className="space-y-4 max-w-3xl">
        <div className="flex items-center gap-2 text-[11px] font-mono tracking-[0.2em] text-accent uppercase">
          <span>05 / REMAINING USEFUL LIFE (RUL)</span>
          <span className="text-slate-600">—</span>
          <span>CONFORMAL DAMAGE KINETICS</span>
        </div>

        <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-white leading-tight font-mono">
          Single-number predictions create false confidence.{' '}
          <span className="font-editorial italic font-normal text-slate-300">
            Certified conformal intervals guarantee airworthiness bounds.
          </span>
        </h2>

        <p className="text-sm sm:text-base text-slate-400 font-mono leading-relaxed">
          Predicting that an engine component has exactly 47.3 hours remaining is unscientific and rejected by military certifiers. ANUMAAN couples physics-based damage accumulation (Paris-Erdogan crack propagation &amp; Miner&apos;s rule) with Conformal Prediction to produce mathematically bounded confidence percentiles (P10, P50, P90).
        </p>
      </div>

      {/* Conformal RUL Overview Card */}
      <div className="mt-16 p-6 sm:p-8 rounded-sm bg-[#0b101c] border border-white/10 space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div>
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">
              OVERALL FLEET PROPULSION HEALTH INDEX
            </span>
            <div className="flex items-baseline gap-3 mt-1">
              <span className="text-3xl sm:text-4xl font-bold font-mono text-white">450.0</span>
              <span className="text-sm font-mono text-accent">FLIGHT HOURS REMAINING (P50)</span>
            </div>
            <p className="text-xs font-mono text-slate-400 mt-1">
              Conformal 90% confidence interval: [385.0 h &mdash; 515.0 h] under current operational sortie intensity
            </p>
          </div>

          <div className="flex items-center gap-3 self-start sm:self-auto">
            <span className="px-3 py-1.5 rounded-xs bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono font-semibold">
              MISSION READINESS: 98.4%
            </span>
          </div>
        </div>

        {/* 4 Flight-Critical Subsystem RUL Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xs bg-white/[0.02] border border-white/[0.06] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-slate-500 uppercase">TURBOCHARGER CORE</span>
              <span className="text-[10px] font-mono text-emerald-400 font-semibold">NOMINAL</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">385.0 hrs</div>
            <div className="w-full bg-white/10 h-1 rounded-full overflow-hidden">
              <div className="bg-emerald-400 h-full rounded-full" style={{ width: '82%' }} />
            </div>
            <span className="text-[9px] font-mono text-slate-500 block">
              Shaft radial play &amp; thermal cycling wear
            </span>
          </div>

          <div className="p-4 rounded-xs bg-white/[0.02] border border-white/[0.06] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-slate-500 uppercase">EXHAUST VALVES</span>
              <span className="text-[10px] font-mono text-emerald-400 font-semibold">NOMINAL</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">420.0 hrs</div>
            <div className="w-full bg-white/10 h-1 rounded-full overflow-hidden">
              <div className="bg-emerald-400 h-full rounded-full" style={{ width: '88%' }} />
            </div>
            <span className="text-[9px] font-mono text-slate-500 block">
              Seat erosion &amp; metallurgical micro-crack growth
            </span>
          </div>

          <div className="p-4 rounded-xs bg-white/[0.02] border border-white/[0.06] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-slate-500 uppercase">CRANK JOURNAL BEARINGS</span>
              <span className="text-[10px] font-mono text-emerald-400 font-semibold">NOMINAL</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">650.0 hrs</div>
            <div className="w-full bg-white/10 h-1 rounded-full overflow-hidden">
              <div className="bg-emerald-400 h-full rounded-full" style={{ width: '94%' }} />
            </div>
            <span className="text-[9px] font-mono text-slate-500 block">
              Hydrodynamic wedge film thickness history
            </span>
          </div>

          <div className="p-4 rounded-xs bg-white/[0.02] border border-white/[0.06] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-slate-500 uppercase">FUEL INJECTION SYSTEM</span>
              <span className="text-[10px] font-mono text-emerald-400 font-semibold">NOMINAL</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">510.0 hrs</div>
            <div className="w-full bg-white/10 h-1 rounded-full overflow-hidden">
              <div className="bg-emerald-400 h-full rounded-full" style={{ width: '90%' }} />
            </div>
            <span className="text-[9px] font-mono text-slate-500 block">
              Injector nozzle orifice erosion &amp; solenoid lag
            </span>
          </div>
        </div>

        {/* Damage Kinetics Explainer */}
        <div className="p-4 rounded-xs bg-white/[0.015] border border-white/[0.05] flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs font-mono text-slate-400">
          <div>
            <span className="text-slate-300 font-semibold uppercase block">
              PARIS-ERDOGAN CRACK PROPAGATION + MINER&apos;S CUMULATIVE DAMAGE
            </span>
            <p className="mt-0.5 text-slate-400 text-[11px]">
              &Delta;D_k = C &times; (&Delta;K_eff)^m &times; N_rev + &int; (&sigma;_therm / &sigma;_yield) dt
            </p>
          </div>
          <span className="text-[10px] text-accent uppercase tracking-wider whitespace-nowrap">
            CONTINUOUS WEIBULL ACCUMULATION // VERIFIED
          </span>
        </div>
      </div>
    </section>
  );
};
