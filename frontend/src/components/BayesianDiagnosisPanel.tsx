import React from 'react';
import { GitFork, AlertTriangle, ShieldCheck, Wrench, Cpu } from 'lucide-react';
import { EngineDiagnosisHypothesis } from '../hooks/useEngineRuntime';

interface BayesianDiagnosisPanelProps {
  diagnosis?: EngineDiagnosisHypothesis[] | null;
  engineName?: string;
  isCalibrated?: boolean;
}

export const BayesianDiagnosisPanel: React.FC<BayesianDiagnosisPanelProps> = ({
  diagnosis,
  engineName = 'Selected Engine',
  isCalibrated = true,
}) => {
  const hasDiagnosis = Boolean(diagnosis && diagnosis.length > 0);

  return (
    <section className="surface-panel p-4 sm:p-5" aria-label="Bayesian Diagnosis Network">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-slate-500">
            <GitFork className="w-3.5 h-3.5 text-sky-400" />
            <span>Bayesian Diagnostic Network · Tier 2 Attribution</span>
          </div>
          <h3 className="mt-1 font-semibold text-white">Probabilistic Root-Cause Diagnosis</h3>
          <p className="mt-0.5 text-xs text-slate-400">
            Causal inference over residual detector evidence and physical ambiguity groups for {engineName}.
          </p>
        </div>
        <span
          className={`shrink-0 rounded px-2.5 py-1 text-[11px] font-medium border ${
            hasDiagnosis
              ? 'border-amber-700/60 bg-amber-950/30 text-amber-300'
              : isCalibrated
              ? 'border-emerald-800/60 bg-emerald-950/20 text-emerald-300'
              : 'border-slate-800 bg-slate-900 text-slate-400'
          }`}
        >
          {hasDiagnosis
            ? `${diagnosis?.length} Active Hypotheses`
            : isCalibrated
            ? 'Nominal · Monitoring'
            : 'Calibrating'}
        </span>
      </div>

      {!hasDiagnosis ? (
        <div className="mt-4 flex items-center gap-3 rounded border border-white/[0.06] bg-black/20 p-3.5 text-xs text-slate-400">
          <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
          <div>
            <div className="text-slate-200 font-medium">No Fault Attribution Required</div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Residual detector is operating below alarm threshold. Bayesian prior probabilities remain quiescent.
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {diagnosis?.map((hypo, idx) => {
            const probPct = Math.round(hypo.probability * 100);
            return (
              <div
                key={`${hypo.mode_id}-${hypo.location ?? 'all'}-${idx}`}
                className="rounded border border-amber-900/60 bg-amber-950/15 p-3.5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.06] pb-2.5">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                    <span className="text-sm font-semibold text-white">
                      {hypo.mode_id.replace(/_/g, ' ')}
                    </span>
                    {hypo.location && (
                      <span className="rounded bg-black/40 px-2 py-0.5 text-[10px] text-amber-300 border border-amber-800/40 font-mono">
                        {hypo.location.replace(/_/g, ' ')}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-slate-400 font-mono">Posterior P(F|E):</span>
                    <span className="text-sm font-bold text-amber-300 font-mono">
                      {probPct}% ({hypo.probability.toFixed(3)})
                    </span>
                  </div>
                </div>

                <div className="mt-2.5 flex flex-wrap items-center gap-2 text-[10px]">
                  <span className="text-slate-500">Ambiguity Group:</span>
                  <span className="rounded bg-slate-800 px-1.5 py-0.5 text-slate-300 font-mono">
                    {hypo.ambiguity_group_id}
                  </span>
                  <span className="text-slate-600">|</span>
                  <span className="text-slate-500">Evidence:</span>
                  {hypo.supporting_evidence.map((ev) => (
                    <span
                      key={ev}
                      className="rounded bg-sky-950/60 border border-sky-800/50 px-1.5 py-0.5 text-sky-300 font-mono"
                    >
                      {ev}
                    </span>
                  ))}
                  <span className="ml-auto text-[10px] text-slate-500">{hypo.ata_chapter}</span>
                </div>

                <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-2 text-[11px]">
                  <div className="rounded bg-black/30 border border-white/[0.04] p-2.5">
                    <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-amber-400 font-semibold mb-1">
                      <AlertTriangle className="w-3 h-3" /> Flight Deck Directive
                    </div>
                    <p className="text-slate-300 leading-relaxed">{hypo.operator_text}</p>
                  </div>
                  <div className="rounded bg-black/30 border border-white/[0.04] p-2.5">
                    <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-sky-400 font-semibold mb-1">
                      <Cpu className="w-3 h-3" /> Propulsion Engineering
                    </div>
                    <p className="text-slate-300 leading-relaxed">{hypo.engineer_text}</p>
                  </div>
                  <div className="rounded bg-black/30 border border-white/[0.04] p-2.5">
                    <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-emerald-400 font-semibold mb-1">
                      <Wrench className="w-3 h-3" /> Maintenance Work Directive
                    </div>
                    <p className="text-slate-300 leading-relaxed">{hypo.maintainer_text}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
