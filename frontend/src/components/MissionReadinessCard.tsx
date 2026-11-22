import React from 'react';
import { CheckCircle2, AlertTriangle, AlertOctagon, Clock } from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';
import { PanelInfoModal } from './PanelInfoModal';

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
          <div className="flex items-center gap-1.5">
            <h2 className="text-xs font-semibold text-white">Pre-Flight Mission Readiness</h2>
            <PanelInfoModal
              title="Pre-Flight Mission Readiness & Go/No-Go Gate"
              subtitle="Conservative (p10) RUL vs. Planned Sortie Duration"
              description="Computes a deterministic pre-flight readiness gate for military MALE UAV sorties. Fits degradation trajectories across all 6 critical engine subsystems using 500-sample Monte Carlo extrapolation and computes the 10th percentile (p10) conservative Remaining Useful Life. Issues an automated GO, CAUTION, or NO-GO directive."
              formula={`Monte Carlo Extrapolation: RUL_i ~ N(μ_i, σ_i²) across 500 runs
Conservative Margin: RUL_p10 = μ_RUL - 1.28 · σ_RUL

Gate Decision Logic:
  GO:       RUL_p10 ≥ 1.25 · T_sortie  (≥ 22.5 h for standard 18 h mission)
  CAUTION:  1.00 · T_sortie ≤ RUL_p10 < 1.25 · T_sortie
  NO-GO:    RUL_p10 < 1.00 · T_sortie  (< 18.0 h)`}
              calculationSteps={[
                { label: 'Subsystem Degradation', detail: 'Ingests degradation rates for Cylinder Heads, Oil Circuit, Gearbox, Fuel Rail, Alternator, and Ignition.' },
                { label: 'Stochastic Simulation', detail: 'Runs 500-sample Monte Carlo degradation projections under expected mission power profiles.' },
                { label: 'p10 Safety Extraction', detail: 'Extracts the 10th percentile bound ensuring 90% statistical confidence before engine failure.' },
                { label: 'Gate Decision', detail: 'Evaluates limiting subsystem RUL_p10 against planned mission sortie duration (18.0 h).' },
              ]}
              sensorInputs={['RUL_p10 per component', 'Planned Sortie Duration', 'Active Degradation Slopes', 'Subsystem Health']}
              thresholds="Safety Factor: ≥ 1.25x for GO | Marginal: 1.00x–1.24x for CAUTION | Abort: < 1.00x for NO-GO"
              provenance="DRDO MALE UAV Mission Dispatch Guidelines & MIL-HDBK-338B Electronic Reliability"
            />
          </div>
          <p className="text-xs text-slate-500">Conservative (p10) RUL vs. planned sortie duration — DRDO PS-26054 Go/No-Go gate</p>
        </div>
        <span className="text-xs font-mono text-slate-500">
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
              <span className="text-xs uppercase font-medium tracking-wide text-slate-400">Mission feasibility advisory</span>
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
            <span className="text-xs text-slate-500 font-medium block">Limiting component RUL</span>
            <div className="flex items-baseline gap-1 mt-0.5">
              <span className="text-lg font-semibold text-white">{a.rul_p10_hours >= 500 ? '>500' : fmt(a.rul_p10_hours)}h</span>
              <span className="text-xs text-slate-500">p10</span>
              <span className="text-slate-700 mx-1">/</span>
              <span className="text-base font-medium text-slate-300">{a.rul_p50_hours >= 500 ? '>500' : fmt(a.rul_p50_hours)}h</span>
              <span className="text-xs text-slate-500">p50</span>
            </div>
            <span className="text-xs text-slate-600">{a.limiting_component ? COMPONENT_LABELS[a.limiting_component] || a.limiting_component : 'No active degradation trend'}</span>
          </div>
        </div>
      </div>

      {/* Per-component RUL breakdown — doc §1.2 "Multi-Subsystem Health Interrogation" */}
      <div>
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-xs font-mono text-slate-600">05</span>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-300">Per-Subsystem Probabilistic RUL</h3>
          <span className="text-xs text-slate-600">— 500-sample Monte Carlo, all 6 monitored components</span>
        </div>
        {rulEntries.length === 0 ? (
          <div className="text-xs text-slate-500 border border-surface-border bg-surface-card px-3 py-3">
            No component is currently showing a fitted degradation trend (R² ≥ 0.55 over a 2/10/30-minute window). All subsystems report
            nominal — RUL bound exceeds the 8-hour projection horizon.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="text-xs uppercase tracking-wider text-slate-500 border-b border-surface-border">
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
                        {isLimiting && <span className="ml-1.5 text-xs text-critical font-semibold">LIMITING</span>}
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
            <span className="text-xs font-mono text-slate-600">06</span>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-300">Live Mission Reliability (18h ISR Sortie)</h3>
            <span className="text-xs text-slate-600">— Weibull-Markov multi-stress system model</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-xs text-slate-500 block">SYSTEM RELIABILITY R(18h)</span>
              <span className={`text-base font-bold font-mono ${a.mission_reliability.mission_reliability < 0.90 ? 'text-critical' : a.mission_reliability.mission_reliability < 0.97 ? 'text-warning' : 'text-emerald-400'}`}>
                {(a.mission_reliability.mission_reliability * 100).toFixed(2)}%
              </span>
            </div>
            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-xs text-slate-500 block">LIMITING SUBSYSTEM</span>
              <span className="text-xs font-semibold text-slate-200 mt-1 block truncate">
                {a.mission_reliability.limiting_component.replace('_', ' ')}
              </span>
            </div>
            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-xs text-slate-500 block">COMPONENT SURVIVAL</span>
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
              <span className="text-xs font-mono text-slate-600">07</span>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-300">Emergency Glide Reachability &amp; Diversion Bases</h3>
            </div>
            <span className="text-xs font-mono text-accent">
              L/D {fmt(a.glide_assessment.glide_ratio)}:1 | Range {fmt(a.glide_assessment.still_air_range_km)} km | V_glide {fmt(a.glide_assessment.speed_best_glide_kt, 0)} kt
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {(a.glide_assessment.reachable_airfields ?? []).map((af) => (
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
                  <span className={`text-xs font-mono font-bold px-1 rounded ${af.is_reachable ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'}`}>
                    {af.is_reachable ? 'REACHABLE' : 'UNREACHABLE'}
                  </span>
                </div>
                <div className="mt-1 flex items-baseline justify-between text-xs font-mono">
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
