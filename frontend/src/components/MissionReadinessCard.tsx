import React from 'react';
import { CheckCircle2, AlertTriangle, AlertOctagon, Clock } from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';

interface MissionReadinessCardProps {
  state: UnifiedTelemetryState;
}

const COMPONENT_LABELS: Record<string, string> = {
  Cylinder_Head_Assembly: 'Cylinder Head Assembly',
  Lubrication_Oil_Circuit: 'Lubrication Oil Circuit',
  Reduction_Gearbox: 'Reduction Gearbox',
  Alternator_Bus: 'Alternator Bus',
  Fuel_Injection_Rail: 'Fuel Injection Rail',
  Ignition_Harness: 'Ignition Harness',
};

const fmt = (v: number, d = 1) => (Number.isFinite(v) ? v.toFixed(d) : '--');

export const MissionReadinessCard: React.FC<MissionReadinessCardProps> = ({ state }) => {
  const a = state.analytics;

  const goNoGoClasses =
    a.go_no_go === 'GO'
      ? 'bg-success-dim text-success border-success-muted'
      : a.go_no_go === 'CAUTION'
      ? 'bg-warning-dim text-warning border-warning-muted'
      : 'bg-critical-dim text-critical border-critical-muted';

  const rulEntries = Object.entries(a.rul_by_component || {});

  return (
    <div className="surface-panel p-4 sm:p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-surface-border pb-3 flex-wrap gap-2">
        <div>
          <h2 className="text-xs font-semibold text-white">Pre-Flight Mission Readiness</h2>
          <p className="text-[11px] text-slate-500">Conservative (p10) RUL vs. planned sortie duration — DRDO PS-26054 Go/No-Go gate</p>
        </div>
        <span className="text-[10px] font-mono text-slate-500">
          Planned sortie: <span className="text-slate-300">{fmt(a.planned_sortie_hours ?? 18, 1)} h</span>
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className={`md:col-span-2 p-4 border flex items-center gap-3.5 ${goNoGoClasses}`}>
          {a.go_no_go === 'GO' ? (
            <CheckCircle2 className="w-8 h-8 shrink-0" />
          ) : a.go_no_go === 'CAUTION' ? (
            <AlertTriangle className="w-8 h-8 shrink-0" />
          ) : (
            <AlertOctagon className="w-8 h-8 shrink-0" />
          )}
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] uppercase font-medium tracking-wide text-slate-400">Mission feasibility advisory</span>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 bg-black/15 border border-current/30">{a.go_no_go}</span>
            </div>
            <p className="text-xs mt-1 opacity-90 leading-relaxed">{a.go_no_go_reason}</p>
          </div>
        </div>

        <div className="surface-panel p-4 flex items-center gap-3">
          <div className="w-9 h-9 bg-accent-dim flex items-center justify-center text-accent shrink-0">
            <Clock className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] text-slate-500 font-medium block">Limiting component RUL</span>
            <div className="flex items-baseline gap-1 mt-0.5">
              <span className="text-lg font-semibold text-white">{a.rul_p10_hours >= 500 ? '>500' : fmt(a.rul_p10_hours)}h</span>
              <span className="text-[10px] text-slate-500">p10</span>
              <span className="text-slate-700 mx-1">/</span>
              <span className="text-base font-medium text-slate-300">{a.rul_p50_hours >= 500 ? '>500' : fmt(a.rul_p50_hours)}h</span>
              <span className="text-[10px] text-slate-500">p50</span>
            </div>
            <span className="text-[10px] text-slate-600">{a.limiting_component ? COMPONENT_LABELS[a.limiting_component] || a.limiting_component : 'No active degradation trend'}</span>
          </div>
        </div>
      </div>

      {/* Per-component RUL breakdown — doc §1.2 "Multi-Subsystem Health Interrogation" */}
      <div>
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-[10px] font-mono text-slate-600">05</span>
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-300">Per-Subsystem Probabilistic RUL</h3>
          <span className="text-[10px] text-slate-600">— 500-sample Monte Carlo, all 6 monitored components</span>
        </div>
        {rulEntries.length === 0 ? (
          <div className="text-[11px] text-slate-500 border border-surface-border bg-surface-card px-3 py-3">
            No component is currently showing a fitted degradation trend (R² ≥ 0.55 over a 2/10/30-minute window). All subsystems report
            nominal — RUL bound exceeds the 8-hour projection horizon.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="text-[9px] uppercase tracking-wider text-slate-500 border-b border-surface-border">
                  <th className="text-left font-medium py-1.5 pr-2">Component</th>
                  <th className="text-right font-medium py-1.5 px-2">RUL p10</th>
                  <th className="text-right font-medium py-1.5 px-2">RUL p50</th>
                  <th className="text-right font-medium py-1.5 px-2">RUL p90</th>
                  <th className="text-right font-medium py-1.5 pl-2">Fit confidence (R²)</th>
                </tr>
              </thead>
              <tbody>
                {rulEntries.map(([comp, rul]) => {
                  const isLimiting = comp === a.limiting_component;
                  return (
                    <tr key={comp} className={`border-b border-surface-border/60 last:border-0 ${isLimiting ? 'bg-critical-dim/40' : ''}`}>
                      <td className="py-1.5 pr-2 font-medium text-slate-300">
                        {COMPONENT_LABELS[comp] || comp}
                        {isLimiting && <span className="ml-1.5 text-[9px] text-critical font-semibold">LIMITING</span>}
                      </td>
                      <td className={`text-right py-1.5 px-2 font-mono font-semibold ${isLimiting ? 'text-critical' : 'text-slate-200'}`}>{fmt(rul.rul_p10_hours)}h</td>
                      <td className="text-right py-1.5 px-2 font-mono text-slate-400">{fmt(rul.rul_p50_hours)}h</td>
                      <td className="text-right py-1.5 px-2 font-mono text-slate-500">{fmt(rul.rul_p90_hours)}h</td>
                      <td className="text-right py-1.5 pl-2 font-mono text-slate-500">{fmt(rul.confidence, 2)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Live Mission Reliability & Limiting Subsystem */}
      {a.mission_reliability && (
        <div className="border-t border-surface-border pt-3">
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-[10px] font-mono text-slate-600">06</span>
            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-300">Live Mission Reliability (18h ISR Sortie)</h3>
            <span className="text-[10px] text-slate-600">— Weibull-Markov multi-stress system model</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">SYSTEM RELIABILITY R(18h)</span>
              <span className={`text-base font-bold font-mono ${a.mission_reliability.mission_reliability < 0.90 ? 'text-critical' : a.mission_reliability.mission_reliability < 0.97 ? 'text-warning' : 'text-emerald-400'}`}>
                {(a.mission_reliability.mission_reliability * 100).toFixed(2)}%
              </span>
            </div>
            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">LIMITING SUBSYSTEM</span>
              <span className="text-xs font-semibold text-slate-200 mt-1 block truncate">
                {a.mission_reliability.limiting_component.replace('_', ' ')}
              </span>
            </div>
            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">COMPONENT SURVIVAL</span>
              <span className="text-base font-bold font-mono text-slate-200">
                {(a.mission_reliability.limiting_component_survival * 100).toFixed(2)}%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Emergency Glide Polar & Diversion Airfield Reachability */}
      {a.glide_assessment && (
        <div className="border-t border-surface-border pt-3">
          <div className="flex items-baseline justify-between mb-2">
            <div className="flex items-baseline gap-2">
              <span className="text-[10px] font-mono text-slate-600">07</span>
              <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-300">Emergency Glide Reachability &amp; Diversion Bases</h3>
            </div>
            <span className="text-[10px] font-mono text-accent">
              L/D {fmt(a.glide_assessment.ld_ratio)}:1 | Range {fmt(a.glide_assessment.glide_range_nm * 1.852)} km | V_glide {fmt(a.glide_assessment.best_glide_tas_kt, 0)} kt
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {(a.glide_assessment.airfields ?? []).map((af) => (
              <div
                key={af.airfield_id}
                className={`p-2 rounded border text-xs flex flex-col justify-between ${
                  af.is_reachable
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                    : 'bg-critical-dim border-critical-muted text-slate-400'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold truncate">{af.name}</span>
                  <span className={`text-[9px] font-mono font-bold px-1 rounded ${af.is_reachable ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'}`}>
                    {af.is_reachable ? 'REACHABLE' : 'UNREACHABLE'}
                  </span>
                </div>
                <div className="mt-1 flex items-baseline justify-between text-[10px] font-mono">
                  <span>{fmt(af.distance_km)} km</span>
                  <span className={af.alt_margin_ft >= 0 ? 'text-emerald-400' : 'text-critical'}>
                    {af.alt_margin_ft >= 0 ? '+' : ''}{fmt(af.alt_margin_ft, 0)} ft
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
