import React from 'react';
import { AlertTriangle, ShieldCheck } from 'lucide-react';

export const LandingProblem: React.FC = () => {
  return (
    <section id="problem" className="py-24 sm:py-32 px-4 sm:px-6 max-w-7xl mx-auto border-b border-white/[0.08]">
      {/* Section Header with Taxonomy & Editorial Phrase */}
      <div className="space-y-4 max-w-3xl">
        <div className="flex items-center gap-2 text-[11px] font-mono tracking-[0.2em] text-cyan-400 uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          <span>DRDO SIH PROBLEM STATEMENT 26054</span>
          <span className="text-slate-600">—</span>
          <span>OPERATIONAL CRITICALITY</span>
        </div>

        <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-white leading-tight font-display">
          The Silent Crisis in High-Altitude Aero-Piston Propulsion.{' '}
          <span className="font-editorial italic font-normal text-slate-300">
            When single-engine UAV propulsion fails, the airframe is lost.
          </span>
        </h2>

        <p className="text-sm sm:text-base text-slate-300 font-sans font-light leading-relaxed">
          Aero-piston engines powering Medium-Altitude Long-Endurance (MALE) UAVs operating over the northern frontier (Ladakh, FL230, -35°C) face extreme thermal gradients and sub-ambient barometric loads. In single-engine military UAVs, propulsion loss means complete airframe loss. 41% of military UAV mishaps stem directly from propulsion failures.
        </p>
      </div>

      {/* 4 Crisis Stat Cards (Direct from previous website) */}
      <div className="mt-12 grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-sm bg-red-950/20 border border-red-500/30 flex flex-col justify-between">
          <div className="text-3xl sm:text-4xl font-extrabold text-red-400 font-mono tracking-tight">41%</div>
          <div className="text-xs text-red-200/80 font-sans mt-2 leading-snug">
            Of all military UAV mishaps are propulsion-related losses
          </div>
        </div>

        <div className="p-5 rounded-sm bg-amber-950/20 border border-amber-500/30 flex flex-col justify-between">
          <div className="text-3xl sm:text-4xl font-extrabold text-amber-400 font-mono tracking-tight">0 MIN</div>
          <div className="text-xs text-amber-200/80 font-sans mt-2 leading-snug">
            Warning margin given by conventional redline threshold alarms
          </div>
        </div>

        <div className="p-5 rounded-sm bg-cyan-950/20 border border-cyan-500/30 flex flex-col justify-between">
          <div className="text-3xl sm:text-4xl font-extrabold text-cyan-400 font-mono tracking-tight">₹150 Cr+</div>
          <div className="text-xs text-cyan-200/80 font-sans mt-2 leading-snug">
            Total replacement cost of lost strategic airframes
          </div>
        </div>

        <div className="p-5 rounded-sm bg-emerald-950/20 border border-emerald-500/30 flex flex-col justify-between">
          <div className="text-3xl sm:text-4xl font-extrabold text-emerald-400 font-mono tracking-tight">4.2 HRS</div>
          <div className="text-xs text-emerald-200/80 font-sans mt-2 leading-snug">
            Prognostic advance warning provided by ANUMAAN physics twin
          </div>
        </div>
      </div>

      {/* Threshold vs Twin Visual Timeline Comparison Box */}
      <div className="mt-12 p-6 sm:p-8 rounded-sm bg-[#0c101a]/80 backdrop-blur border border-white/10 space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
            CONVENTIONAL REDLINE VS. ANUMAAN TWIN TIMELINE
          </h3>
          <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
            TIME-TO-EVENT ADVANCE WARNING
          </span>
        </div>

        {/* Timeline Track Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-[11px] font-mono text-slate-400">
            <span>T+00:00 (Nominal Cruise)</span>
            <span className="text-amber-400">T+02:40 (Twin Anomaly Detected)</span>
            <span className="text-red-400">T+04:15 (Threshold Alarm Trips)</span>
          </div>

          <div className="h-3 w-full bg-white/5 rounded-full overflow-hidden flex relative">
            <div className="h-full bg-emerald-500 w-[60%]" title="Nominal State" />
            <div className="h-full bg-amber-500 w-[35%]" title="Twin Early Detection Window (2.6 Hours Warning)" />
            <div className="h-full bg-red-500 w-[5%]" title="Conventional Static Threshold Trip (Fatal Seizure)" />
          </div>

          <div className="flex justify-between text-[10px] font-mono text-slate-500 pt-1">
            <span>HEALTHY ENVELOPE</span>
            <span className="text-amber-300 font-semibold">&larr; 1.6 - 4.2 HOURS ACTIONABLE BUFFER &rarr;</span>
            <span className="text-red-400">TOO LATE</span>
          </div>
        </div>

        {/* Side-by-side callouts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          <div className="p-4 rounded-xs bg-red-950/20 border-l-2 border-red-500 border-t border-r border-b border-white/5 text-xs font-mono space-y-1">
            <span className="text-red-400 font-bold uppercase tracking-wider">The Threshold Trap:</span>
            <p className="text-slate-300 leading-relaxed">
              Conventional EHMS waits for CHT to cross 165°C. By then, piston skirt galling has already occurred and seizure is irreversible, forcing immediate ditching.
            </p>
          </div>

          <div className="p-4 rounded-xs bg-cyan-950/20 border-l-2 border-cyan-400 border-t border-r border-b border-white/5 text-xs font-mono space-y-1">
            <span className="text-cyan-400 font-bold uppercase tracking-wider">The ANUMAAN Advantage:</span>
            <p className="text-slate-300 leading-relaxed">
              The digital twin detects when CHT is just 4°C above what first-principles physics predicts for the current altitude, throttle, and airspeed. Advance notice: 2+ hours.
            </p>
          </div>
        </div>
      </div>

      {/* Comparative Analytical Matrix: Conventional vs Digital Twin */}
      <div className="mt-12 grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Conventional Threshold Monitoring (The Vulnerability) */}
        <div className="p-6 sm:p-8 rounded-sm bg-[#12151d]/70 border border-red-500/20 space-y-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-xs bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400">
                <AlertTriangle className="w-3.5 h-3.5" />
              </div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                CONVENTIONAL THRESHOLD MONITORING
              </h3>
            </div>
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-xs bg-red-500/10 text-red-400 border border-red-500/20">
              REACTIVE / LAGGING
            </span>
          </div>

          <div className="space-y-4 text-xs font-mono text-slate-300">
            <div className="p-3 rounded-xs bg-white/[0.02] border border-white/[0.04] space-y-1">
              <span className="text-[10px] text-slate-500 uppercase">DETECTION MECHANISM</span>
              <p className="text-slate-200">
                Static scalar thresholds (e.g. CHT &gt; 155°C, Oil Pressure &lt; 2.0 bar). Redlines must be set wide to prevent nuisance trips during climb and transient maneuvers.
              </p>
            </div>

            <div className="p-3 rounded-xs bg-white/[0.02] border border-white/[0.04] space-y-1">
              <span className="text-[10px] text-slate-500 uppercase">THE CRITICAL BLIND SPOT</span>
              <p className="text-slate-200">
                Incipient damage (injector coking, micro-fretting, oil cavitation) accumulates over dozens of flight hours inside the nominal tolerance band without ever tripping an alarm.
              </p>
            </div>

            <div className="p-3 rounded-xs bg-white/[0.02] border border-white/[0.04] space-y-1">
              <span className="text-[10px] text-slate-500 uppercase">TACTICAL CONSEQUENCE</span>
              <p className="text-red-300/90">
                By the time a static threshold alarm triggers in flight, catastrophic thermal shock or bearing seizure is already irreversible, forcing dead-stick forced landings.
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-white/5 flex items-center gap-2 text-[11px] font-mono text-slate-500">
            <span>SIGNAL PATH:</span>
            <span className="text-slate-400">Sensor Value</span>
            <span>&rarr;</span>
            <span className="text-slate-400">Fixed Limit</span>
            <span>&rarr;</span>
            <span className="text-red-400 font-semibold">Post-Catastrophe Alarm</span>
          </div>
        </div>

        {/* ANUMAAN Physics-Informed Digital Twin (The Solution) */}
        <div className="p-6 sm:p-8 rounded-sm bg-[#0e1624]/70 border border-cyan-500/30 space-y-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-xs bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                <ShieldCheck className="w-3.5 h-3.5" />
              </div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                ANUMAAN PHYSICS-INFORMED TWIN
              </h3>
            </div>
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-xs bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              PROACTIVE / PREDICTIVE
            </span>
          </div>

          <div className="space-y-4 text-xs font-mono text-slate-300">
            <div className="p-3 rounded-xs bg-white/[0.02] border border-white/[0.04] space-y-1">
              <span className="text-[10px] text-slate-500 uppercase">STATE ESTIMATION MECHANISM</span>
              <p className="text-slate-200">
                Real-time 0D/1D thermofluid engine model coupled with an Unscented Kalman Filter (UKF) calculating the exact expected physical state at every instantaneous RPM, manifold pressure, and altitude.
              </p>
            </div>

            <div className="p-3 rounded-xs bg-white/[0.02] border border-white/[0.04] space-y-1">
              <span className="text-[10px] text-slate-500 uppercase">RESIDUAL NOISE TRACKING</span>
              <p className="text-slate-200">
                Generates analytical residuals (r = y_measured - y_twin) across 27 channels at 20 Hz. CUSUM filter and Mahalanobis distance detect statistical drift within 0.15σ.
              </p>
            </div>

            <div className="p-3 rounded-xs bg-white/[0.02] border border-white/[0.04] space-y-1">
              <span className="text-[10px] text-slate-500 uppercase">TACTICAL VALUE</span>
              <p className="text-emerald-300/90">
                Provides 2 to 6 hours of lead time before component failure, calculating conformal Remaining Useful Life (RUL) and recommending immediate throttle derating or safe return-to-base glide cones.
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-white/5 flex items-center gap-2 text-[11px] font-mono text-slate-500">
            <span>SIGNAL PATH:</span>
            <span className="text-slate-400">Sensor Value</span>
            <span>&minus;</span>
            <span className="text-cyan-400">Physics Twin</span>
            <span>&rarr;</span>
            <span className="text-emerald-400 font-semibold">Prognostic Divergence Lead Time</span>
          </div>
        </div>
      </div>
    </section>
  );
};
