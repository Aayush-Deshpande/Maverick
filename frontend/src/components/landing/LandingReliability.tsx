import React from 'react';
import { MapPin } from 'lucide-react';

export const LandingReliability: React.FC = () => {
  return (
    <section id="reliability" className="py-24 sm:py-32 px-4 sm:px-6 max-w-7xl mx-auto border-b border-white/[0.08]">
      {/* Header */}
      <div className="space-y-4 max-w-3xl">
        <div className="flex items-center gap-2 text-[11px] font-mono tracking-[0.2em] text-accent uppercase">
          <span>06 / TACTICAL MISSION SURVIVABILITY</span>
          <span className="text-slate-600">—</span>
          <span>PRESCRIPTIVE COPILOT &amp; GLIDE SAFETY</span>
        </div>

        <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-white leading-tight font-mono">
          Engine data is meaningless in a crisis unless translated into pilot action.{' '}
          <span className="font-editorial italic font-normal text-slate-300">
            Real-time prescriptive guidance preserves the airframe.
          </span>
        </h2>

        <p className="text-sm sm:text-base text-slate-400 font-mono leading-relaxed">
          When an anomaly is confirmed in-flight, the SAARTHI copilot translates thermodynamic residuals into operational flight adjustments: exact throttle derate percentages, cooling descent trajectories, and real-time glide range cones to safe diversion airstrips.
        </p>
      </div>

      {/* Two Pillars: Prescriptive Actions & Glide Assessment */}
      <div className="mt-16 grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Prescriptive Operational Action Matrix */}
        <div className="p-6 sm:p-8 rounded-sm bg-[#0c121d] border border-white/10 space-y-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              SAARTHI PRESCRIPTIVE FLIGHT GUIDANCE
            </h3>
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              REAL-TIME ADVISORY
            </span>
          </div>

          <div className="space-y-3">
            <div className="p-3.5 rounded-xs bg-white/[0.02] border border-white/[0.06] space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-semibold text-slate-200 uppercase">
                  ACTION 01: THROTTLE DERATING
                </span>
                <span className="text-[10px] font-mono text-amber-400">P_max MITIGATION</span>
              </div>
              <p className="text-xs font-mono text-slate-400 leading-relaxed">
                Automatically calculates the exact derate limit (e.g. 78% throttle) required to keep cylinder head temperature below 140&deg;C without stalling or compromising minimum operational airspeed.
              </p>
            </div>

            <div className="p-3.5 rounded-xs bg-white/[0.02] border border-white/[0.06] space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-semibold text-slate-200 uppercase">
                  ACTION 02: DYNAMIC COOLING DESCENT
                </span>
                <span className="text-[10px] font-mono text-sky-400">CONVECTIVE RECOVERY</span>
              </div>
              <p className="text-xs font-mono text-slate-400 leading-relaxed">
                Computes optimal shallow descent path from thin high-altitude air (FL250) to denser ambient air (14,000 ft), increasing radiator mass flow and convective heat rejection by 38%.
              </p>
            </div>

            <div className="p-3.5 rounded-xs bg-white/[0.02] border border-white/[0.06] space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-semibold text-slate-200 uppercase">
                  ACTION 03: FADEC LANE SWITCHING
                </span>
                <span className="text-[10px] font-mono text-emerald-400">FAILOVER ISOLATION</span>
              </div>
              <p className="text-xs font-mono text-slate-400 leading-relaxed">
                If sensor drift or injector pulse-width jitter is isolated to Lane A, recommends immediate electronic lane transfer to Lane B before spark timing degradation triggers detonation.
              </p>
            </div>
          </div>
        </div>

        {/* Glide Polar & Emergency Airfield Assessment */}
        <div className="p-6 sm:p-8 rounded-sm bg-[#0c121d] border border-white/10 space-y-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              TACTICAL GLIDE FOOTPRINT &amp; DIVERSION
            </h3>
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-xs bg-sky-500/10 text-sky-400 border border-sky-500/20">
              L/D = 18.2 : 1 POLAR
            </span>
          </div>

          <div className="p-4 rounded-xs bg-white/[0.02] border border-white/[0.06] flex items-center justify-between">
            <div>
              <span className="text-[10px] font-mono text-slate-500 uppercase block">CURRENT STILL-AIR GLIDE RANGE</span>
              <span className="text-2xl font-bold font-mono text-sky-400 mt-0.5 block">138.6 km</span>
              <span className="text-[10px] font-mono text-slate-400 mt-1 block">From 25,000 ft AGL at best glide speed (78 kt)</span>
            </div>
            <div className="text-right">
              <span className="text-[10px] font-mono text-slate-500 uppercase block">AIRFRAME WEIGHT</span>
              <span className="text-sm font-bold font-mono text-slate-200 mt-0.5 block">700 kg MTOW</span>
              <span className="text-[10px] font-mono text-emerald-400 mt-1 block">GLIDE POLAR VALID</span>
            </div>
          </div>

          <div className="space-y-2">
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">
              REACHABLE DIVERSION AIRFIELDS (WITH SAFETY ALTITUDE MARGIN)
            </span>

            <div className="p-2.5 rounded-xs bg-white/[0.02] border border-white/[0.05] flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2">
                <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-slate-200">FORWARD OPERATING BASE LEH</span>
              </div>
              <span className="text-emerald-400 font-semibold">REACHABLE (+2,400 ft margin)</span>
            </div>

            <div className="p-2.5 rounded-xs bg-white/[0.02] border border-white/[0.05] flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2">
                <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-slate-200">KARGIL ADVANCED LANDING GROUND</span>
              </div>
              <span className="text-emerald-400 font-semibold">REACHABLE (+1,850 ft margin)</span>
            </div>

            <div className="p-2.5 rounded-xs bg-white/[0.02] border border-white/[0.05] flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2">
                <MapPin className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-slate-400">SRINAGAR AIR FORCE STATION</span>
              </div>
              <span className="text-slate-500 font-semibold">MARGINAL (-400 ft margin)</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
