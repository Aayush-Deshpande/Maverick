import { useEffect, useState } from 'react';
import {
  MessageSquareText,
  Loader2,
  Sparkles,
  Volume2,
  VolumeX,
  Database,
  Copy,
  Check,
  Bot,
  LayoutGrid,
} from 'lucide-react';

type Section = { key: string; title: string; text: string };
type Answer = {
  mode: 'llm' | 'deterministic';
  provider: string;
  provider_error: string | null;
  sections: Section[];
  tool_calls: Array<{ name: string }>;
  grounding: { sentences_dropped: number };
};
type Props = {
  engineId: string | null;
  api: (path: string, method: string, body?: unknown) => Promise<any>;
};

// One-click questions an operator or maintainer actually asks; free text goes through the same endpoint.
const QUICK = ['What is going on?', 'Why is this happening?', 'What should I do right now?', 'How do I fix it?'];

export default function CopilotPanel({ engineId, api }: Props) {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [viewMode, setViewMode] = useState<'hybrid' | 'conversational' | 'matrix'>('hybrid');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setAnswer(null);
    setError('');
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, [engineId]);

  const ask = async (q: string) => {
    if (!engineId || !q.trim() || busy) return;
    setBusy(true);
    setError('');
    setQuestion(q);
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
    try {
      const res = await api('/api/v1/copilot/ask', 'POST', { engine_id: engineId, question: q.trim() });
      setAnswer(res);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Copilot unavailable');
    } finally {
      setBusy(false);
    }
  };

  const getSection = (key: string) => answer?.sections.find((s) => s.key === key)?.text || '';

  // Synthesize a fluid conversational brief from the structured sections
  const getConversationalBrief = () => {
    if (!answer) return '';
    const what = getSection('what');
    const why = getSection('why');
    const mit = getSection('mitigation');
    const fix = getSection('fix');
    const prog = getSection('prognosis');

    const parts = [];
    if (what) parts.push(what);
    if (why && !why.toLowerCase().includes('no fault')) parts.push(why);
    if (mit && !mit.toLowerCase().includes('no action')) parts.push(`Mitigation: ${mit}`);
    if (fix && !fix.toLowerCase().includes('no maintenance')) parts.push(`Maintenance: ${fix}`);
    if (prog) parts.push(prog);
    return parts.length > 0 ? parts.join(' ') : what || 'All engine parameters are within normal flight envelopes.';
  };

  const speakBrief = (text: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }
    window.speechSynthesis.cancel();
    const clean = text.replace(/[*_#`]/g, '').slice(0, 300);
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.rate = 1.05;
    utterance.pitch = 0.95;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const copyBrief = (text: string) => {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <section className="surface-panel p-4 sm:p-5 rounded-sm" aria-label="Engine copilot">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border pb-3">
        <div className="flex items-center gap-2">
          <MessageSquareText size={16} className="text-accent" />
          <h3 className="text-sm font-semibold text-white">Ask the engine copilot</h3>
        </div>

        {/* View Mode Switcher */}
        {answer && (
          <div className="flex items-center gap-1.5 p-0.5 rounded bg-surface-card border border-surface-border font-mono text-[11px]">
            <button
              onClick={() => setViewMode('hybrid')}
              className={`px-2 py-0.5 rounded transition-colors ${
                viewMode === 'hybrid' ? 'bg-accent text-white font-medium shadow-xs' : 'text-slate-400 hover:text-white'
              }`}
            >
              Hybrid (Both)
            </button>
            <button
              onClick={() => setViewMode('conversational')}
              className={`px-2 py-0.5 rounded transition-colors flex items-center gap-1 ${
                viewMode === 'conversational' ? 'bg-accent text-white font-medium shadow-xs' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Bot size={11} /> Conversational
            </button>
            <button
              onClick={() => setViewMode('matrix')}
              className={`px-2 py-0.5 rounded transition-colors flex items-center gap-1 ${
                viewMode === 'matrix' ? 'bg-accent text-white font-medium shadow-xs' : 'text-slate-400 hover:text-white'
              }`}
            >
              <LayoutGrid size={11} /> FMECA Matrix
            </button>
          </div>
        )}
      </div>

      {/* Metadata / Grounding Badge */}
      {answer && (
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-slate-400">
          <span>
            {answer.mode === 'llm' ? `Phrased by ${answer.provider}` : 'Rules only (no language model)'}
            {' · '}
            {answer.tool_calls.length > 0 ? `${answer.tool_calls.length} live lookups` : 'live state'}
            {answer.grounding.sentences_dropped > 0 &&
              ` · ${answer.grounding.sentences_dropped} unsupported sentence(s) removed`}
          </span>
          <span className="text-[11px] text-slate-500">
            Ground truth: 20 Hz Frame &amp; FMECA Bayes Isolator
          </span>
        </div>
      )}

      {/* Quick Action Prompt Chips */}
      <div className="mt-3 flex flex-wrap gap-2">
        {QUICK.map((q) => (
          <button
            key={q}
            type="button"
            disabled={busy || !engineId}
            onClick={() => void ask(q)}
            className="rounded-sm border border-surface-border px-3 py-1.5 text-xs text-slate-200 hover:border-surface-border-strong disabled:opacity-50 transition-colors font-mono"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Text Question Form */}
      <form
        className="mt-2 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void ask(question);
        }}
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={500}
          placeholder="Or type your own question…"
          disabled={busy || !engineId}
          className="min-w-0 flex-1 rounded-sm border border-surface-border bg-transparent px-3 py-2 text-xs text-white outline-none focus:border-accent disabled:opacity-50 transition-colors font-sans"
        />
        <button
          type="submit"
          disabled={busy || !question.trim() || !engineId}
          className="rounded-sm border border-surface-border px-3.5 py-2 text-xs text-white disabled:opacity-50 flex items-center gap-1.5 transition-colors bg-white/[0.03] hover:bg-white/[0.08] font-mono"
        >
          {busy ? <Loader2 size={13} className="animate-spin text-accent" /> : <Sparkles size={13} />}
          <span>{busy ? 'Evaluating…' : 'Ask'}</span>
        </button>
      </form>

      {/* Loading Skeleton */}
      {busy && (
        <div className="mt-3 space-y-3" aria-live="polite">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-200 bg-surface-card border border-surface-border px-3 py-2 rounded-sm shadow-2xs">
            <Loader2 size={14} className="animate-spin text-accent shrink-0" />
            <span>Reading live engine telemetry, physical limits, and ATA manual procedures…</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 animate-pulse">
            <div className="md:col-span-2 rounded-sm border border-surface-border bg-surface-card p-3 space-y-2">
              <div className="h-3 w-32 bg-white/[0.08] rounded-sm"></div>
              <div className="h-4 w-5/6 bg-white/[0.05] rounded-sm"></div>
            </div>
            <div className="rounded-sm border border-surface-border bg-surface-card p-3 space-y-2">
              <div className="h-3 w-28 bg-white/[0.08] rounded-sm"></div>
              <div className="h-4 w-4/5 bg-white/[0.05] rounded-sm"></div>
            </div>
            <div className="rounded-sm border border-surface-border bg-surface-card p-3 space-y-2">
              <div className="h-3 w-36 bg-white/[0.08] rounded-sm"></div>
              <div className="h-4 w-4/5 bg-white/[0.05] rounded-sm"></div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <p className="mt-3 text-xs font-mono text-critical bg-critical-dim border border-critical-muted px-3 py-2 rounded-sm">
          {error}
        </p>
      )}

      {answer && !busy && (
        <div className="mt-3 space-y-3">
          {/* 1. Conversational Executive Brief Card (Visible in Hybrid and Conversational modes) */}
          {(viewMode === 'hybrid' || viewMode === 'conversational') && (
            <div className="p-3.5 rounded-sm bg-surface-card border border-accent/40 shadow-sm space-y-2">
              <div className="flex items-center justify-between border-b border-surface-border/50 pb-2">
                <div className="flex items-center gap-2">
                  <Bot size={14} className="text-accent" />
                  <span className="text-xs font-semibold text-white tracking-wide font-mono">
                    MAVERICK Copilot Assessment
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-accent-dim text-accent border border-accent-muted">
                    Conversational
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => speakBrief(getConversationalBrief())}
                    className={`p-1.5 rounded transition-colors ${
                      isSpeaking ? 'bg-accent text-white' : 'hover:bg-white/5 text-slate-400 hover:text-white'
                    }`}
                    title={isSpeaking ? 'Stop speaking' : 'Speak assessment out loud'}
                  >
                    {isSpeaking ? <VolumeX size={13} /> : <Volume2 size={13} />}
                  </button>
                  <button
                    onClick={() => copyBrief(getConversationalBrief())}
                    className="p-1.5 rounded hover:bg-white/5 text-slate-400 hover:text-white transition-colors"
                    title="Copy brief"
                  >
                    {copied ? <Check size={13} className="text-success" /> : <Copy size={13} />}
                  </button>
                </div>
              </div>
              <p className="text-xs text-slate-200 leading-relaxed font-sans">
                {getConversationalBrief()}
              </p>
            </div>
          )}

          {/* 2. Structured FMECA Diagnostic Matrix (Visible in Hybrid and Matrix modes) */}
          {(viewMode === 'hybrid' || viewMode === 'matrix') && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {answer.sections
                .filter((s) => s.text)
                .map((s) => (
                  <div
                    key={s.key}
                    className={`rounded-sm border border-surface-border bg-surface-card p-3 ${
                      s.key === 'what' || s.key === 'sources' ? 'md:col-span-2' : ''
                    }`}
                  >
                    <div className="text-[11px] uppercase tracking-wider text-slate-400 font-mono flex items-center justify-between">
                      <span>{s.title}</span>
                      {s.key === 'sources' && <Database size={11} className="text-accent" />}
                    </div>
                    <p
                      className={`mt-1 ${
                        s.key === 'sources'
                          ? 'text-xs text-slate-300 font-mono break-words leading-relaxed'
                          : 'text-xs text-slate-200 leading-relaxed font-sans'
                      }`}
                    >
                      {s.text}
                    </p>
                  </div>
                ))}
            </div>
          )}

          {/* Fallback warning if provider failed */}
          {answer.provider_error && (
            <p className="text-xs font-mono text-slate-500">
              Language model unavailable ({answer.provider_error.slice(0, 120)}); this answer uses the deterministic rules.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
