import React, { useEffect, useState, useCallback } from 'react';
import { Compass, AlertCircle, CheckCircle2, Clock, Sparkles, RefreshCw, Zap } from 'lucide-react';

export interface DerateOption {
  power_setting_pct: number;
  reliability: number;
  ci: [number, number];
  delta_reliability: number;
  damage_rate_vs_baseline: number;
  endurance_penalty_min: number;
  limiting_component: string | null;
  meets_requirement: boolean;
}

export interface ReliabilityData {
  engine_id: string;
  mission_hours: number;
  reliability: number;
  limiting_component: string;
  limiting_component_survival: number;
  per_component_survival?: Record<string, number>;
  derate_options: DerateOption[];
  recommendation: string;
  verdict?: string;
  ci?: [number, number];
  replan?: {
    achievable: boolean;
    reliability: number;
    ci_lower: number;
    changes: string[];
  } | null;
  source: 'LIVE_MISSION' | 'CANONICAL_ISR';
}

export interface MissionReliabilityPanelProps {
  engineId: string;
  engineName?: string;
  serverUrl?: string;
  isLiveMission?: boolean;
  onApplyDerate?: (scale: number) => void;
}

export const MissionReliabilityPanel: React.FC<MissionReliabilityPanelProps> = ({
  engineId,
  engineName = 'Selected Engine',
  serverUrl = 'http://127.0.0.1:8000',
  isLiveMission = false,
  onApplyDerate,
}) => {
  const [mode, setMode] = useState<'LIVE' | 'BENCHMARK'>(isLiveMission ? 'LIVE' : 'BENCHMARK');
  const [hours, setHours] = useState(18);
  const [data, setData] = useState<ReliabilityData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync mode if isLiveMission prop changes
  useEffect(() => {
    if (isLiveMission) {
      setMode('LIVE');
    }
  }, [isLiveMission]);

  const fetchReliability = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (mode === 'LIVE') {
        const res = await fetch(`${serverUrl.replace(/\/$/, '')}/api/missions/reliability`);
        if (!res.ok) {
          const txt = await res.text();
          throw new Error(txt || `HTTP ${res.status}`);
        }
        const json = await res.json();
        const assessment = json.assessment || {};
        const derateOpts: DerateOption[] = (json.derate_options || []).map((o: any) => ({
          power_setting_pct: o.power_setting_pct ?? Math.round((o.power_scale ?? 1) * 100),
          reliability: o.reliability ?? 1.0,
          ci: o.ci ?? [o.ci_lower ?? 0.9, o.ci_upper ?? 1.0],
          delta_reliability: o.delta_reliability ?? 0.0,
          damage_rate_vs_baseline: o.damage_rate_vs_baseline ?? o.damage_rate_ratio ?? 1.0,
          endurance_penalty_min: o.endurance_penalty_min ?? 0.0,
          limiting_component: o.limiting_component ?? assessment.limiting_component ?? null,
          meets_requirement: Boolean(o.meets_requirement),
        }));

        const r: ReliabilityData = {
          engine_id: engineId,
          mission_hours: assessment.mission_hours ?? 0.12,
          reliability: assessment.reliability ?? 1.0,
          limiting_component: assessment.limiting_component || 'nominal',
          limiting_component_survival:
            assessment.limiting_component_share != null
              ? 1.0 - assessment.limiting_component_share
              : (assessment.reliability ?? 1.0),
          derate_options: derateOpts,
          recommendation:
            Array.isArray(json.advisory) && json.advisory.length > 0
              ? json.advisory.join(' ')
              : assessment.rationale || 'Nominal operation meets reliability target.',
          verdict: assessment.verdict || 'GO',
          ci: assessment.ci_lower != null ? [assessment.ci_lower, assessment.ci_upper] : undefined,
          replan: json.replan,
          source: 'LIVE_MISSION',
        };
        setData(r);
      } else {
        const res = await fetch(`${serverUrl.replace(/\/$/, '')}/api/engines/${engineId}/reliability?hours=${hours}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData({
          ...json,
          source: 'CANONICAL_ISR',
        });
      }
    } catch (err: any) {
      setError(err instanceof Error ? err.message : 'Failed to fetch reliability');
    } finally {
      setLoading(false);
    }
  }, [engineId, hours, mode, serverUrl]);

  useEffect(() => {
    fetchReliability();
    if (mode === 'LIVE') {
      const interval = setInterval(fetchReliability, 5000);
      return () => clearInterval(interval);
    }
  }, [fetchReliability, mode]);

  return (
    <section className="surface-panel p-4 sm:p-5" aria-label="Mission Reliability & Prescriptive Maintenance">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-slate-500">
            <Compass className="w-3.5 h-3.5 text-sky-400" />
            <span>Mission Reliability Engine · F56 / F57 / F58 (ARCH-2026-MP-002)</span>
          </div>
          <h3 className="mt-1 font-semibold text-white flex items-center gap-2">
            Prognostics-Driven Mission Reliability & Prescriptive Advisory
            {data?.source === 'LIVE_MISSION' && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                LIVE MISSION ACTIVE
              </span>
            )}
          </h3>
          <p className="mt-0.5 text-xs text-slate-400">
            {data?.source === 'LIVE_MISSION'
              ? `Real-time Monte Carlo survival & What-If derate analysis calculated across active mission phases for ${engineName}.`
              : `Analytic Weibull survival & prescriptive derate advisory benchmarked for ${engineName}.`}
          </p>
        </div>

        {/* Profile Switcher & Actions */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1 bg-surface-dark p-1 rounded border border-surface-border">
            <button
              onClick={() => setMode('LIVE')}
              className={`rounded px-2.5 py-1 text-xs font-mono transition-colors flex items-center gap-1 ${
                mode === 'LIVE'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Calculate reliability using real time-phased flight profile"
            >
              <Zap className="w-3 h-3 text-cyan-400" /> Live Mission
            </button>
            <button
              onClick={() => setMode('BENCHMARK')}
              className={`rounded px-2.5 py-1 text-xs font-mono transition-colors flex items-center gap-1 ${
                mode === 'BENCHMARK'
                  ? 'bg-sky-600 text-white font-semibold'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Benchmark against canonical endurance profiles"
            >
              <Clock className="w-3 h-3 text-slate-400" /> Canned ISR
            </button>
          </div>

          {mode === 'BENCHMARK' && (
            <div className="flex items-center gap-1">
              {[6, 12, 18].map((h) => (
                <button
                  key={h}
                  onClick={() => setHours(h)}
                  className={`rounded px-2.5 py-1 text-xs font-mono transition-colors ${
                    hours === h
                      ? 'bg-sky-600 text-white font-semibold'
                      : 'bg-white/[0.04] text-slate-400 hover:bg-white/[0.08]'
                  }`}
                >
                  {h}h ISR
                </button>
              ))}
            </div>
          )}

          <button
            onClick={() => fetchReliability()}
            disabled={loading}
            className="p-1.5 rounded bg-surface-dark border border-surface-border text-slate-400 hover:text-white transition-colors"
            title="Refresh reliability calculations"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {loading && !data && (
        <div className="mt-4 py-8 text-center text-xs text-slate-500">
          Calculating component Weibull survival integrals and Monte Carlo trials…
        </div>
      )}

      {error && (
        <div className="mt-4 rounded border border-amber-900/60 bg-amber-950/20 p-3 text-xs text-amber-300 flex items-center justify-between">
          <span>Reliability engine advisory: {error}</span>
          {mode === 'LIVE' && (
            <button
              onClick={() => setMode('BENCHMARK')}
              className="px-2 py-0.5 rounded bg-amber-800/60 hover:bg-amber-700 text-white text-[10px] font-mono ml-2"
            >
              Switch to Canned ISR
            </button>
          )}
        </div>
      )}

      {data && (
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded border border-white/[0.06] bg-black/20 p-3.5">
              <div className="text-[10px] uppercase tracking-wider text-slate-500 flex items-center justify-between">
                <span>Mission Completion P(Success)</span>
                {data.verdict && (
                  <span
                    className={`font-mono font-bold text-[9px] px-1.5 py-0.5 rounded ${
                      data.verdict === 'GO'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                        : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                    }`}
                  >
                    VERDICT: {data.verdict}
                  </span>
                )}
              </div>
              <div className="mt-1 text-2xl font-bold font-mono text-emerald-400">
                {(data.reliability * 100).toFixed(1)}%
              </div>
              <div className="mt-0.5 text-[10px] text-slate-500 font-mono">
                {data.ci
                  ? `95% CI: [${(data.ci[0] * 100).toFixed(1)}% - ${(data.ci[1] * 100).toFixed(1)}%]`
                  : `R(t=${data.mission_hours}h) analytic mission survival`}
              </div>
            </div>

            <div className="rounded border border-white/[0.06] bg-black/20 p-3.5">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">
                Limiting Component
              </div>
              <div className="mt-1 text-lg font-bold font-mono text-amber-300 truncate">
                {data.limiting_component.replace(/_/g, ' ')}
              </div>
              <div className="mt-0.5 text-[10px] text-slate-500 font-mono">
                Component survival: {(data.limiting_component_survival * 100).toFixed(2)}%
              </div>
            </div>

            <div className="rounded border border-sky-900/40 bg-sky-950/15 p-3.5 flex flex-col justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-sky-400 font-medium flex items-center gap-1">
                  <Sparkles className="w-3 h-3" /> Prescriptive Advisory
                </div>
                <div className="mt-1 text-xs text-slate-300 leading-snug">
                  {data.recommendation}
                </div>
              </div>
            </div>
          </div>

          {/* Replan Notification if sortie not achievable without alterations */}
          {data.replan && !data.replan.achievable && (
            <div className="rounded border border-rose-900/60 bg-rose-950/20 p-3 text-xs text-rose-300 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <div>
                <span className="font-bold font-mono">Replan Advisory: </span>
                {data.replan.changes.join(', ')}
              </div>
            </div>
          )}

          {/* Derate Options Table (What-If Analysis) */}
          <div className="rounded border border-white/[0.06] bg-black/20 p-3">
            <div className="text-xs font-semibold text-slate-200 mb-2 flex items-center justify-between">
              <span>Prescriptive Derate Schedule vs. Station Endurance (What-If Trade Study)</span>
              <span className="text-[10px] font-normal text-slate-500 font-mono">
                DAL-C Target: ≥ 90.0%
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/[0.08] text-[10px] uppercase tracking-wider text-slate-500 font-mono">
                    <th className="pb-1.5">Throttle Derate</th>
                    <th className="pb-1.5">Reliability</th>
                    <th className="pb-1.5">95% CI</th>
                    <th className="pb-1.5">Damage Rate</th>
                    <th className="pb-1.5">Endurance Penalty</th>
                    <th className="pb-1.5">DAL Target</th>
                    {onApplyDerate && <th className="pb-1.5 text-right">Action</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] font-mono">
                  {data.derate_options.map((opt) => (
                    <tr key={opt.power_setting_pct} className="hover:bg-white/[0.02]">
                      <td className="py-2 text-white font-medium">
                        {opt.power_setting_pct}% MCP
                      </td>
                      <td className="py-2 text-emerald-400">
                        {(opt.reliability * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 text-slate-400 text-[11px]">
                        [{(opt.ci[0] * 100).toFixed(1)}% - {(opt.ci[1] * 100).toFixed(1)}%]
                      </td>
                      <td className="py-2 text-slate-300">
                        {(opt.damage_rate_vs_baseline * 100).toFixed(0)}%
                      </td>
                      <td className="py-2 text-amber-300">
                        {opt.endurance_penalty_min > 0 ? `+${opt.endurance_penalty_min.toFixed(1)} min` : '0 min'}
                      </td>
                      <td className="py-2">
                        {opt.meets_requirement ? (
                          <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400">
                            <CheckCircle2 className="w-3 h-3" /> Met
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] text-rose-400">
                            <AlertCircle className="w-3 h-3" /> Below Target
                          </span>
                        )}
                      </td>
                      {onApplyDerate && (
                        <td className="py-2 text-right">
                          <button
                            onClick={() => onApplyDerate(opt.power_setting_pct / 100)}
                            className="px-2 py-0.5 rounded bg-amber-600/80 hover:bg-amber-500 text-white font-mono text-[10px] font-bold transition-colors"
                            title={`Apply ${opt.power_setting_pct}% MCP derate to live engine`}
                          >
                            APPLY
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
