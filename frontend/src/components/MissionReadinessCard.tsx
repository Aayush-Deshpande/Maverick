import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  Clock,
  ShieldAlert,
  Sliders,
  Check,
  X,
  RefreshCw,
} from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';

interface MissionReadinessCardProps {
  state: UnifiedTelemetryState;
  serverUrl?: string;
}

interface ReliabilityData {
  profile_name: string;
  mission_hours: number;
  analytic_reliability: number;
  monte_carlo_reliability: number;
  ci_lower: number;
  ci_upper: number;
  limiting_component: string;
  limiting_component_survival: number;
  per_component_survival: Record<string, number>;
  simulated_aborts: number;
  total_simulations: number;
}

interface DerateOption {
  power_setting_pct: number;
  reliability: number;
  ci: [number, number];
  delta_reliability: number;
  damage_rate_vs_baseline: number;
  endurance_penalty_min: number;
  limiting_component: string;
  meets_requirement: boolean;
}

interface PrescriptiveData {
  target_reliability: number;
  derate_options: DerateOption[];
  advisory_sentences: string[];
  replan_result?: {
    achievable: boolean;
    reliability: number;
    ci_lower: number;
    changes: string[];
    recommendation: string;
  } | null;
}

const COMPONENT_LABELS: Record<string, string> = {
  Cylinder_Head_Assembly: 'Cylinder Head Assembly',
  Lubrication_Oil_Circuit: 'Lubrication Oil Circuit',
  Reduction_Gearbox: 'Reduction Gearbox',
  Alternator_Bus: 'Alternator Bus',
  Fuel_Injection_Rail: 'Fuel Injection Rail',
  Ignition_Harness: 'Ignition Harness',
  cylinder_head_1: 'Cylinder #1 Head',
  cylinder_head_2: 'Cylinder #2 Head',
  injector_1: 'Fuel Injector #1',
  fuel_pump: 'High-Pressure Fuel Pump',
  reduction_gearbox: 'Reduction Gearbox',
  main_bearings: 'Crankshaft Bearings',
};

const fmt = (v: number, d = 1) => (Number.isFinite(v) ? v.toFixed(d) : '--');

export const MissionReadinessCard: React.FC<MissionReadinessCardProps> = ({
  state,
  serverUrl = 'http://127.0.0.1:8000',
}) => {
  const a = state.analytics;
  const [reliability, setReliability] = useState<ReliabilityData | null>(null);
  const [prescriptive, setPrescriptive] = useState<PrescriptiveData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchReliabilityAndPrescriptive = async () => {
    try {
      setIsLoading(true);
      const [relRes, preRes] = await Promise.all([
        fetch(`${serverUrl}/api/mission/reliability`),
        fetch(`${serverUrl}/api/mission/prescriptive`),
      ]);
      if (relRes.ok) {
        const relData = await relRes.json();
        setReliability(relData);
      }
      if (preRes.ok) {
        const preData = await preRes.json();
        setPrescriptive(preData);
      }
    } catch (e) {
      console.warn('Failed to load mission reliability/prescriptive data', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReliabilityAndPrescriptive();
    const interval = setInterval(fetchReliabilityAndPrescriptive, 8000);
    return () => clearInterval(interval);
  }, [serverUrl, a.diagnosed_fault_id]);

  const goNoGoClasses =
    a.go_no_go === 'GO'
      ? 'bg-success-dim text-success border-success-muted'
      : a.go_no_go === 'CAUTION'
      ? 'bg-warning-dim text-warning border-warning-muted'
      : 'bg-critical-dim text-critical border-critical-muted';

  const rulEntries = Object.entries(a.rul_by_component || {});

  return (
    <div className="surface-panel p-4 sm:p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-surface-border pb-3 flex-wrap gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 font-mono text-[9px] text-cyan-400">
              WP-06 / F56-F58
            </span>
            <h2 className="text-xs font-semibold text-white">
              Mission Reliability &amp; Prescriptive Derating Advisor
            </h2>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Phase-integrated hazard rates over 18-hour ISR profile vs. live component degradation
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchReliabilityAndPrescriptive}
            disabled={isLoading}
            className="p-1 rounded bg-slate-900 border border-slate-700 text-slate-400 hover:text-white transition-colors"
            title="Refresh Monte Carlo Simulation"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <span className="text-[10px] font-mono text-slate-500">
            Profile: <span className="text-cyan-400 font-semibold">{reliability?.profile_name || '18h High-Alt ISR'}</span>
          </span>
        </div>
      </div>

      {/* Top Cards: Go/No-Go and Limiting Component RUL */}
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
              <span className="text-[10px] uppercase font-medium tracking-wide text-slate-400">
                Mission feasibility advisory
              </span>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 bg-black/15 border border-current/30">
                {a.go_no_go}
              </span>
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
              <span className="text-lg font-semibold text-white">
                {a.rul_p10_hours >= 500 ? '>500' : fmt(a.rul_p10_hours)}h
              </span>
              <span className="text-[10px] text-slate-500">p10</span>
              <span className="text-slate-700 mx-1">/</span>
              <span className="text-base font-medium text-slate-300">
                {a.rul_p50_hours >= 500 ? '>500' : fmt(a.rul_p50_hours)}h
              </span>
              <span className="text-[10px] text-slate-500">p50</span>
            </div>
            <span className="text-[10px] text-slate-400 truncate max-w-[170px] block">
              {a.limiting_component
                ? COMPONENT_LABELS[a.limiting_component] || a.limiting_component
                : 'No active degradation trend'}
            </span>
          </div>
        </div>
      </div>

      {/* WP-06: Authoritative Mission Reliability Monte Carlo Metrics */}
      {reliability && (
        <div className="bg-slate-950/60 p-3.5 rounded border border-cyan-500/20 space-y-3">
          <div className="flex items-center justify-between border-b border-surface-border/60 pb-2">
            <span className="text-xs font-semibold text-cyan-300 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />
              Sortie Completion Probability R(t)
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              500-TRIAL MONTE CARLO (WILSON 95% CI)
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">MC PROBABILITY</span>
              <div className="text-base font-bold font-mono text-cyan-300 mt-0.5">
                {(reliability.monte_carlo_reliability * 100).toFixed(1)}%
              </div>
              <span className="text-[9px] font-mono text-slate-500">
                [{ (reliability.ci_lower * 100).toFixed(1) }% – { (reliability.ci_upper * 100).toFixed(1) }%]
              </span>
            </div>

            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">ANALYTIC R(t)</span>
              <div className="text-base font-bold font-mono text-slate-200 mt-0.5">
                {(reliability.analytic_reliability * 100).toFixed(1)}%
              </div>
              <span className="text-[9px] font-mono text-slate-500">Exact hazard integral</span>
            </div>

            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">LIMITING FACTOR</span>
              <div className="text-xs font-semibold font-mono text-amber-300 mt-1 truncate">
                {COMPONENT_LABELS[reliability.limiting_component] || reliability.limiting_component || 'NOMINAL'}
              </div>
              <span className="text-[9px] font-mono text-slate-500">
                Survival: {(reliability.limiting_component_survival * 100).toFixed(1)}%
              </span>
            </div>

            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">SIMULATED ABORTS</span>
              <div className="text-base font-bold font-mono text-slate-200 mt-0.5">
                {reliability.simulated_aborts} <span className="text-xs font-normal text-slate-500">/ 500</span>
              </div>
              <span className="text-[9px] font-mono text-slate-500">Hazard inverse draws</span>
            </div>
          </div>
        </div>
      )}

      {/* WP-06: Prescriptive Power Derating Ladder */}
      {prescriptive && prescriptive.derate_options && prescriptive.derate_options.length > 0 && (
        <div className="bg-slate-950/60 p-3.5 rounded border border-surface-border space-y-3">
          <div className="flex items-center justify-between border-b border-surface-border/60 pb-2">
            <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-amber-400" />
              Prescriptive Power Derating Ladder (F57)
            </span>
            <span className="text-[10px] font-mono text-amber-400">
              TARGET R ≥ {(prescriptive.target_reliability * 100).toFixed(0)}%
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="text-[9px] uppercase tracking-wider text-slate-500 border-b border-surface-border">
                  <th className="text-left font-medium py-1.5 pr-2">Power Setting</th>
                  <th className="text-right font-medium py-1.5 px-2">Sortie R(t)</th>
                  <th className="text-right font-medium py-1.5 px-2">Δ Reliability</th>
                  <th className="text-right font-medium py-1.5 px-2">Damage Rate vs Base</th>
                  <th className="text-right font-medium py-1.5 px-2">Endurance Penalty</th>
                  <th className="text-center font-medium py-1.5 pl-2">Meets Req</th>
                </tr>
              </thead>
              <tbody>
                {prescriptive.derate_options.map((opt, idx) => (
                  <tr
                    key={idx}
                    className={`border-b border-surface-border/60 last:border-0 ${
                      opt.meets_requirement ? 'bg-emerald-500/5' : ''
                    }`}
                  >
                    <td className="py-1.5 pr-2 font-mono font-semibold text-slate-200">
                      {opt.power_setting_pct}% Max Cont
                    </td>
                    <td className="text-right py-1.5 px-2 font-mono font-bold text-cyan-300">
                      {(opt.reliability * 100).toFixed(1)}%
                    </td>
                    <td className="text-right py-1.5 px-2 font-mono text-emerald-400">
                      {opt.delta_reliability >= 0 ? '+' : ''}
                      {(opt.delta_reliability * 100).toFixed(1)}%
                    </td>
                    <td className="text-right py-1.5 px-2 font-mono text-slate-300">
                      {Math.round(opt.damage_rate_vs_baseline * 100)}%
                    </td>
                    <td className="text-right py-1.5 px-2 font-mono text-amber-300">
                      +{opt.endurance_penalty_min.toFixed(0)} min
                    </td>
                    <td className="text-center py-1.5 pl-2">
                      {opt.meets_requirement ? (
                        <span className="inline-flex items-center text-emerald-400">
                          <Check className="w-3.5 h-3.5" />
                        </span>
                      ) : (
                        <span className="inline-flex items-center text-slate-600">
                          <X className="w-3.5 h-3.5" />
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {prescriptive.advisory_sentences && prescriptive.advisory_sentences.length > 0 && (
            <div className="bg-amber-500/10 border border-amber-500/30 p-2.5 rounded text-[11px] text-amber-200 leading-relaxed">
              <span className="font-semibold block text-amber-100 mb-0.5">Tactical Advisory Recommendation:</span>
              {prescriptive.replan_result?.recommendation || prescriptive.advisory_sentences[1] || prescriptive.advisory_sentences[0]}
            </div>
          )}
        </div>
      )}

      {/* Per-component RUL breakdown */}
      <div>
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-[10px] font-mono text-slate-600">05</span>
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-300">
            Per-Subsystem Probabilistic RUL
          </h3>
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
                    <tr
                      key={comp}
                      className={`border-b border-surface-border/60 last:border-0 ${
                        isLimiting ? 'bg-critical-dim/40' : ''
                      }`}
                    >
                      <td className="py-1.5 pr-2 font-medium text-slate-300">
                        {COMPONENT_LABELS[comp] || comp}
                        {isLimiting && <span className="ml-1.5 text-[9px] text-critical font-semibold">LIMITING</span>}
                      </td>
                      <td
                        className={`text-right py-1.5 px-2 font-mono font-semibold ${
                          isLimiting ? 'text-critical' : 'text-slate-200'
                        }`}
                      >
                        {fmt(rul.rul_p10_hours)}h
                      </td>
                      <td className="text-right py-1.5 px-2 font-mono text-slate-400">{fmt(rul.rul_p50_hours)}h</td>
                      <td className="text-right py-1.5 px-2 font-mono text-slate-500">{fmt(rul.rul_p90_hours)}h</td>
                      <td className="text-right py-1.5 pl-2 font-mono text-slate-500">{rul.confidence.toFixed(2)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
export default MissionReadinessCard;
