import React, { useState } from 'react';
import {
  Wrench,
  ShieldAlert,
  Zap,
  Sparkles,
  Loader2,
  Send,
  CheckSquare,
  Square,
  ArrowRight,
  Info,
} from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';
import { AerospaceMarkdown } from './AerospaceMarkdown';
import { useEngineSelection } from '../contexts/EngineSelectionContext';

interface DiagnosticCardProps {
  state: UnifiedTelemetryState;
  serverUrl?: string;
}

const SUGGESTED_QUERIES = [
  'Emergency SOP for low oil pressure in Ladakh?',
  'Explain Cylinder #2 CHT overheat causal chain',
  'What are the maximum RPM limits for Rotax 912 iS?',
  'FADEC Lane A vs Lane B fault isolation checklist',
];

export const DiagnosticCard: React.FC<DiagnosticCardProps> = ({
  state,
  serverUrl = 'http://127.0.0.1:8000',
}) => {
  const a = state.analytics;
  const isFaulted = a.diagnosed_fault_id > 0;
  const isEarlyTrend = Boolean(a.early_warning_trend);

  const [copilotQuery, setCopilotQuery] = useState('');
  const [copilotAnswer, setCopilotAnswer] = useState<string | null>(null);
  const [copilotCitations, setCopilotCitations] = useState<string[]>([]);
  const [isCopilotAsking, setIsCopilotAsking] = useState(false);

  const [checkedSteps, setCheckedSteps] = useState<Record<number, boolean>>({});

  const toggleCheckStep = (idx: number) => {
    setCheckedSteps((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleAskCopilot = async (queryToAsk?: string) => {
    const query = (queryToAsk || copilotQuery).trim();
    if (!query || isCopilotAsking) return;

    setIsCopilotAsking(true);
    setCopilotAnswer(null);
    // Without a timeout, a stalled local LLM (Ollama busy/crashed, GPU contention) leaves the
    // Send button spinning forever with no way to recover short of reloading the whole page -
    // the fetch itself never rejects on its own since nothing here ever closes the connection.
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);
    try {
      const res = await fetch(`${serverUrl}/api/ai/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': '69420',
        },
        body: JSON.stringify({ query }),
        signal: controller.signal,
      });
      if (res.ok) {
        const data = await res.json();
        setCopilotAnswer(data.response || 'No response returned.');
        setCopilotCitations(data.citations || []);
      } else {
        setCopilotAnswer(`**Error**: Server returned status code \`${res.status}\`. Please ensure backend is running.`);
      }
    } catch (err: any) {
      const message = err?.name === 'AbortError' ? 'Request timed out after 45s — the AI reasoning engine may be overloaded or unreachable.' : (err?.message || err);
      setCopilotAnswer(`**Connection Error**: Failed to query Mission Copilot (\`${message}\`).`);
    } finally {
      clearTimeout(timeoutId);
      setIsCopilotAsking(false);
    }
  };

  let engineContext: ReturnType<typeof useEngineSelection> | null = null;
  try {
    engineContext = useEngineSelection();
  } catch {
    engineContext = null;
  }

  return (
    <div className="space-y-4">
      {engineContext && !engineContext.isDefaultEngineSelected && (
        <div className="rounded border border-sky-800/50 bg-sky-950/25 p-3 text-xs text-sky-200 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-white">
              Multi-Engine Twin Active: {engineContext.profile?.display_name || engineContext.engineId}
            </div>
            <div className="text-[11px] text-slate-300 mt-0.5 leading-relaxed">
              Authoritative physics, calibrated residual detectors, and Bayesian diagnosis are running for {engineContext.profile?.display_name || engineContext.engineId}. RAG documentation retrieval prioritizes indexed maintenance manuals and active telemetry.
            </div>
          </div>
        </div>
      )}

      {/* Early warning trend — the Go/No-Go certification banner and per-component RUL table
          live in MissionReadinessCard, directly under the Detection Logic panel. */}
      {isEarlyTrend && a.early_warning_trend && (
        <div className="surface-panel surface-panel-warning  p-4 flex items-start gap-3.5">
          <div className="w-8 h-8 rounded-sm bg-warning-dim flex items-center justify-center text-warning shrink-0 mt-0.5">
            <Zap className="w-4 h-4" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-medium text-warning">
                Prognostic early warning [{a.early_warning_trend.alert_level}]: {a.early_warning_trend.channel}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-warning-dim border border-warning-muted text-warning">
                {a.early_warning_trend.drift_rate_per_hr > 0 ? '+' : ''}{a.early_warning_trend.drift_rate_per_hr.toFixed(2)}/hr drift
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              {a.early_warning_trend.message} — predicted limit breach in ~{a.early_warning_trend.time_to_threshold_min.toFixed(0)} min while the gauge is still nominal.
            </p>
          </div>
        </div>
      )}

      {/* 3. AI diagnostic directive */}
      <div className={`surface-panel  p-4 sm:p-5 space-y-4 ${isFaulted ? 'surface-panel-critical' : ''}`}>
        <div className="flex items-center justify-between border-b border-surface-border pb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2.5">
            <div className={`w-7 h-7 rounded-sm flex items-center justify-center ${isFaulted ? 'bg-critical-dim text-critical' : 'bg-accent-dim text-accent'}`}>
              <ShieldAlert className="w-3.5 h-3.5" />
            </div>
            <div>
              <h2 className="text-xs font-semibold text-white">
                AI Diagnostic Directive &amp; Physical Causality
              </h2>
              <p className="text-[11px] text-slate-500">Physics twin residuals + local RAG grounding</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono px-2 py-1 rounded-sm bg-white/5 border border-surface-border text-slate-300">
              {a.ata_chapter}
            </span>
            <span className="text-[10px] px-2 py-1 rounded-sm bg-white/5 border border-surface-border text-slate-400">
              {a.subsystem}
            </span>
            <span
              className={`text-[10px] font-semibold px-2 py-1 rounded-sm border ${
                a.severity === 'CRITICAL'
                  ? 'bg-critical-dim text-critical border-critical-muted'
                  : a.severity === 'MAJOR' || a.severity === 'WARNING'
                  ? 'bg-warning-dim text-warning border-warning-muted'
                  : 'bg-success-dim text-success border-success-muted'
              }`}
            >
              {a.severity}
            </span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-baseline gap-2 flex-wrap">
            <span className="text-xs font-medium text-slate-500">Diagnosis:</span>
            <span className={`text-base font-semibold ${isFaulted ? 'text-critical' : 'text-success'}`}>
              {a.diagnosed_fault_name}
            </span>
            <span className="text-xs text-slate-500">
              ({(a.diagnosed_confidence * 100).toFixed(0)}% confidence)
            </span>
          </div>

          <div className="text-xs text-slate-300 bg-white/[0.02] p-3.5 rounded-sm border border-surface-border leading-relaxed">
            <span className="text-slate-200 font-medium block mb-1">Physical root cause analysis</span>
            <p className="text-slate-400">{a.root_cause}</p>
          </div>
        </div>

        {a.causal_chain && a.causal_chain.length > 0 && (
          <div className="space-y-2 pt-1">
            <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
              <ArrowRight className="w-3.5 h-3.5" />
              Deterministic causal propagation cascade
            </span>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {a.causal_chain.map((step, idx) => (
                <div
                  key={idx}
                  className="text-xs text-slate-300 bg-white/[0.02] p-3 rounded-sm border border-surface-border flex items-start gap-2.5"
                >
                  <span className="w-5 h-5 rounded-sm bg-white/5 border border-surface-border text-slate-400 text-[10px] font-semibold flex items-center justify-center shrink-0">
                    {idx + 1}
                  </span>
                  <span className="leading-relaxed text-slate-400">{step}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI reasoning box */}
        <div className="space-y-2 pt-1">
          <span className="text-[11px] font-medium text-ai-accent flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            AI reasoning (local LLM, RAG-grounded)
          </span>

          {(!a.ai_diagnosis || a.ai_diagnosis.status === 'IDLE') && (
            <div className="flex items-center justify-between text-xs text-slate-400 bg-ai-accent-dim p-3 rounded-sm border border-surface-border">
              <div className="flex items-center gap-2">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-success"></span>
                </span>
                <span>AI propulsion monitor active — standing by for anomaly onset or operator inquiry.</span>
              </div>
              <span className="text-[10px] text-slate-500 px-2 py-0.5 rounded-full bg-white/5 border border-surface-border">
                RAG index ready
              </span>
            </div>
          )}

          {a.ai_diagnosis?.status === 'THINKING' && (
            <div className="flex items-center gap-3 text-xs text-slate-300 bg-ai-accent-dim p-3.5 rounded-sm border border-surface-border">
              <Loader2 className="w-4 h-4 animate-spin text-ai-accent" />
              <span>Synthesizing causal explanation against Rotax maintenance manuals &amp; DRDO FMECA documents...</span>
            </div>
          )}

          {a.ai_diagnosis?.status === 'READY' && (
            <div className="surface-panel surface-panel-ai p-4 rounded-sm">
              <AerospaceMarkdown
                content={a.ai_diagnosis.explanation}
                citations={a.ai_diagnosis.citations}
                title="Local LLM Grounded Diagnostic Synthesis"
              />
            </div>
          )}

          {a.ai_diagnosis?.status === 'ERROR' && (
            <p className="text-[11px] text-slate-500 bg-white/[0.02] p-3 rounded-sm border border-surface-border">
              AI reasoning layer offline — deterministic physics causal cascade and telemetry diagnostics above remain fully active.
            </p>
          )}
        </div>

        {/* SOP checklist */}
        {a.emergency_checklist && a.emergency_checklist.length > 0 && (
          <div className="space-y-2 pt-1">
            <span className="text-[11px] font-medium text-warning flex items-center gap-1.5">
              <CheckSquare className="w-3.5 h-3.5" />
              Authoritative SOP emergency directive checklist
            </span>
            <div className="space-y-1.5">
              {a.emergency_checklist.map((step, idx) => {
                const isChecked = checkedSteps[idx] || false;
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => toggleCheckStep(idx)}
                    className={`w-full text-left text-xs px-3.5 py-2.5 rounded-sm border flex items-start gap-3 transition-colors ${
                      isChecked
                        ? 'bg-success-dim border-success-muted/60 text-slate-500 line-through'
                        : 'bg-white/[0.02] border-surface-border text-slate-300 hover:border-surface-border-strong hover:bg-white/[0.04]'
                    }`}
                  >
                    <div className="mt-0.5 shrink-0 text-slate-500">
                      {isChecked ? (
                        <CheckSquare className="w-4 h-4 text-success" />
                      ) : (
                        <Square className="w-4 h-4" />
                      )}
                    </div>
                    <div className="flex-1">
                      <span className="font-medium text-slate-400 mr-2">Step {idx + 1}:</span>
                      <span className="leading-relaxed">{step}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Prescriptive action & maintenance order */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-surface-border">
          <div className="text-xs text-slate-300 bg-white/[0.02] p-3.5 rounded-sm border border-surface-border">
            <span className="text-warning font-medium block mb-1">
              Prescriptive pilot directive
            </span>
            <span className="leading-relaxed text-slate-400">{a.prescriptive_action}</span>
          </div>

          <div className="text-xs text-slate-300 bg-white/[0.02] p-3.5 rounded-sm border border-surface-border">
            <div className="flex items-center gap-1.5 text-accent font-medium mb-1">
              <Wrench className="w-3.5 h-3.5" />
              <span>Maintenance work order</span>
            </div>
            <span className="leading-relaxed text-slate-400">{a.maintenance_order}</span>
          </div>
        </div>

        {/* 4. Copilot query bar */}
        <div className="pt-3 border-t border-surface-border space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-ai-accent" />
              <span className="text-xs font-medium text-slate-300">
                Ask Mission Copilot
              </span>
            </div>
            <span className="text-[10px] text-slate-500">
              Retrieval over Rotax OM/MM &amp; DRDO FMECA documents
            </span>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {SUGGESTED_QUERIES.map((sq) => (
              <button
                key={sq}
                type="button"
                onClick={() => {
                  setCopilotQuery(sq);
                  handleAskCopilot(sq);
                }}
                disabled={isCopilotAsking}
                className="text-[11px] px-2.5 py-1 rounded-full bg-white/[0.03] hover:bg-white/[0.06] border border-surface-border text-slate-400 transition-colors disabled:opacity-40"
              >
                {sq}
              </button>
            ))}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAskCopilot();
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={copilotQuery}
              onChange={(e) => setCopilotQuery(e.target.value)}
              placeholder="Ask any technical manual, checklist, or diagnostic question..."
              className="flex-1 px-4 py-2.5 rounded-sm bg-surface text-xs text-slate-100 border border-surface-border focus:border-accent-muted focus:outline-none placeholder:text-slate-600"
            />
            <button
              type="submit"
              disabled={isCopilotAsking || !copilotQuery.trim()}
              className="px-4 py-2.5 rounded-sm bg-accent text-white text-xs font-medium hover:bg-accent/90 disabled:opacity-40 flex items-center gap-1.5 transition-colors"
            >
              {isCopilotAsking ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              <span>Send</span>
            </button>
          </form>

          {copilotAnswer && (
            <div className="p-4 rounded-sm surface-panel surface-panel-ai animate-fade-in">
              <AerospaceMarkdown
                content={copilotAnswer}
                citations={copilotCitations}
                title="Mission Copilot Intelligence Response"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
