import { useEffect, useState } from 'react';
import { MessageSquareText, Loader2, Sparkles } from 'lucide-react';

type Section = { key: string; title: string; text: string };
type Answer = { mode: 'llm' | 'deterministic'; provider: string; provider_error: string | null; sections: Section[];
  tool_calls: Array<{ name: string }>; grounding: { sentences_dropped: number } };
type Props = { engineId: string | null; api: (path: string, method: string, body?: unknown) => Promise<any> };

// One-click questions an operator or maintainer actually asks; free text goes through the same endpoint.
const QUICK = ['What is going on?', 'Why is this happening?', 'What should I do right now?', 'How do I fix it?'];

/** Engine copilot (Phase 8b, D45): asks POST /api/v1/copilot/ask. The answer is built from read-only tools over the
 *  live state (what this screen shows); a language model only phrases it, and the backend drops any sentence with a
 *  number it cannot trace to the live data. */
export default function CopilotPanel({ engineId, api }: Props) {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { setAnswer(null); setError(''); }, [engineId]);

  const ask = async (q: string) => {
    if (!engineId || !q.trim() || busy) return;
    setBusy(true); setError(''); setQuestion(q);
    try { setAnswer(await api('/api/v1/copilot/ask', 'POST', { engine_id: engineId, question: q.trim() })); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Copilot unavailable'); }
    finally { setBusy(false); }
  };

  return (
    <section className="surface-panel p-4 sm:p-5 rounded-sm" aria-label="Engine copilot">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-white"><MessageSquareText size={16} /> Ask the engine copilot</h3>
        {answer && <span className="text-xs font-mono text-slate-400">
          {answer.mode === 'llm' ? `Phrased by ${answer.provider}` : 'Rules only (no language model)'}
          {' · '}{answer.tool_calls.length > 0 ? `${answer.tool_calls.length} live lookups` : 'live state'}
          {answer.grounding.sentences_dropped > 0 && ` · ${answer.grounding.sentences_dropped} unsupported sentence(s) removed`}
        </span>}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {QUICK.map((q) => <button key={q} type="button" disabled={busy || !engineId} onClick={() => void ask(q)}
          className="rounded-sm border border-surface-border px-3 py-1.5 text-xs text-slate-200 hover:border-surface-border-strong disabled:opacity-50 transition-colors">{q}</button>)}
      </div>
      <form className="mt-2 flex gap-2" onSubmit={(e) => { e.preventDefault(); void ask(question); }}>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={500} placeholder="Or type your own question…"
          disabled={busy || !engineId}
          className="min-w-0 flex-1 rounded-sm border border-surface-border bg-transparent px-3 py-2 text-xs text-white outline-none disabled:opacity-50" />
        <button type="submit" disabled={busy || !question.trim() || !engineId}
          className="rounded-sm border border-surface-border px-3.5 py-2 text-xs text-white disabled:opacity-50 flex items-center gap-1.5 transition-colors bg-white/[0.03] hover:bg-white/[0.08]">
          {busy ? <Loader2 size={13} className="animate-spin text-accent" /> : <Sparkles size={13} />}
          <span>{busy ? 'Evaluating…' : 'Ask'}</span>
        </button>
      </form>
      {busy && (
        <div className="mt-3 space-y-3" aria-live="polite">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-300 bg-white/[0.02] border border-surface-border px-3 py-2 rounded-sm">
            <Loader2 size={14} className="animate-spin text-accent shrink-0" />
            <span>Reading live engine telemetry, physical limits, and ATA manual procedures…</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 animate-pulse">
            <div className="md:col-span-2 rounded-sm border border-surface-border/50 bg-white/[0.01] p-3 space-y-2">
              <div className="h-3 w-32 bg-slate-700/50 rounded-sm"></div>
              <div className="h-4 w-5/6 bg-slate-800/40 rounded-sm"></div>
            </div>
            <div className="rounded-sm border border-surface-border/50 bg-white/[0.01] p-3 space-y-2">
              <div className="h-3 w-28 bg-slate-700/50 rounded-sm"></div>
              <div className="h-4 w-4/5 bg-slate-800/40 rounded-sm"></div>
            </div>
            <div className="rounded-sm border border-surface-border/50 bg-white/[0.01] p-3 space-y-2">
              <div className="h-3 w-36 bg-slate-700/50 rounded-sm"></div>
              <div className="h-4 w-4/5 bg-slate-800/40 rounded-sm"></div>
            </div>
            <div className="md:col-span-2 rounded-sm border border-surface-border/50 bg-white/[0.01] p-3 space-y-2">
              <div className="h-3 w-40 bg-slate-700/50 rounded-sm"></div>
              <div className="h-3 w-2/3 bg-slate-800/30 rounded-sm"></div>
            </div>
          </div>
        </div>
      )}
      {error && <p className="mt-3 text-xs font-mono text-critical bg-critical-dim border border-critical-muted px-3 py-2 rounded-sm">{error}</p>}
      {answer && !busy && <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
        {answer.sections.filter((s) => s.text).map((s) => (
          <div key={s.key} className={`rounded-sm border border-surface-border p-3 ${s.key === 'what' || s.key === 'sources' ? 'md:col-span-2' : ''}`}>
            <div className="text-xs uppercase tracking-wider text-slate-400 font-mono">{s.title}</div>
            <p className={`mt-1 text-sm ${s.key === 'sources' ? 'text-xs text-slate-400 font-mono break-words' : 'text-slate-200'}`}>{s.text}</p>
          </div>
        ))}
        {answer.provider_error && <p className="md:col-span-2 text-xs font-mono text-slate-500">Language model unavailable ({answer.provider_error.slice(0, 120)}); this answer uses the rules only.</p>}
      </div>}
    </section>
  );
}
