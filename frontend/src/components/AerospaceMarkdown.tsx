import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Copy,
  Check,
  ShieldAlert,
  BookOpen,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';

interface AerospaceMarkdownProps {
  content: string;
  citations?: string[];
  title?: string;
}

/** Legacy clipboard fallback for insecure contexts (plain http://) where
 * navigator.clipboard doesn't exist at all. Best-effort: silently no-ops on failure
 * rather than throwing, since a failed copy is a minor inconvenience, not worth surfacing. */
function fallbackCopy(text: string) {
  try {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
  } catch {
    // Nothing more we can do here.
  }
}

export const AerospaceMarkdown: React.FC<AerospaceMarkdownProps> = ({
  content,
  citations = [],
  title,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    // navigator.clipboard is undefined in insecure contexts (plain http://, not localhost) -
    // and the documented mobile-GCS flow is a phone hitting http://<laptop-lan-ip>:5173 over
    // wifi, so this throws a TypeError on every tap of Copy on that exact path. Falls back to
    // the legacy execCommand copy, which still works over plain HTTP.
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(content).catch(() => fallbackCopy(content));
    } else {
      fallbackCopy(content);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isDiagnosticAdvisory = content.includes('[DIAGNOSTIC ADVISORY');
  const isManualRetrieval = content.includes('[MANUAL RETRIEVAL') || content.includes('[TECHNICAL MANUAL DIRECTIVE');

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between border-b border-surface-border pb-2">
        <div className="flex items-center gap-2">
          {isDiagnosticAdvisory ? (
            <ShieldAlert className="w-3.5 h-3.5 text-critical" />
          ) : isManualRetrieval ? (
            <BookOpen className="w-3.5 h-3.5 text-accent" />
          ) : (
            <Sparkles className="w-3.5 h-3.5 text-ai-accent" />
          )}
          <span className="text-[11px] font-medium text-slate-300">
            {title || (isDiagnosticAdvisory ? 'Diagnostic Advisory' : isManualRetrieval ? 'Technical Manual Excerpt' : 'Mission Intelligence Synthesis')}
          </span>
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-1 rounded-sm hover:bg-white/5 text-[11px] text-slate-400 hover:text-slate-200 transition-colors font-mono"
          title="Copy to clipboard"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-success" />
              <span className="text-success">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      <div className="assistant-markdown text-xs text-slate-300">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => (
              <h1 className="text-sm font-semibold text-white border-b border-surface-border pb-1 mt-2 mb-1">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-xs font-semibold text-slate-200 mt-2 mb-1">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-xs font-semibold text-slate-300 mt-1.5 mb-1">
                {children}
              </h3>
            ),
            strong: ({ children }) => {
              const str = String(children);
              if (str.includes('CRITICAL')) {
                return (
                  <span className="px-1.5 py-0.5 rounded bg-critical-dim border border-critical-muted text-critical font-medium text-[10px] mx-1 inline-flex items-center gap-1">
                    <AlertTriangle className="w-2.5 h-2.5" /> {children}
                  </span>
                );
              }
              if (str.includes('MAJOR') || str.includes('CAUTION') || str.includes('WARNING')) {
                return (
                  <span className="px-1.5 py-0.5 rounded bg-warning-dim border border-warning-muted text-warning font-medium text-[10px] mx-1 inline-flex items-center gap-1">
                    <AlertTriangle className="w-2.5 h-2.5" /> {children}
                  </span>
                );
              }
              if (str.includes('NOMINAL') || str.includes('GO')) {
                return (
                  <span className="px-1.5 py-0.5 rounded bg-success-dim border border-success-muted text-success font-medium text-[10px] mx-1 inline-flex items-center gap-1">
                    <CheckCircle2 className="w-2.5 h-2.5" /> {children}
                  </span>
                );
              }
              if (str.startsWith('[DIAGNOSTIC ADVISORY') || str.startsWith('[MANUAL RETRIEVAL') || str.startsWith('[TECHNICAL MANUAL DIRECTIVE')) {
                return (
                  <span className="block my-1 px-2.5 py-1.5 rounded-sm bg-white/[0.04] border border-surface-border-strong text-slate-200 font-medium text-[11px] tracking-wide uppercase font-mono">
                    {children}
                  </span>
                );
              }
              return <strong className="text-white font-semibold">{children}</strong>;
            },
            table: ({ children }) => (
              <div className="overflow-x-auto my-2 rounded-sm border border-surface-border">
                <table className="min-w-full divide-y divide-surface-border text-xs font-mono">{children}</table>
              </div>
            ),
            th: ({ children }) => (
              <th className="px-2.5 py-1.5 bg-white/[0.03] text-slate-300 font-semibold text-left text-[11px] font-mono">
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td className="px-2.5 py-1.5 border-t border-surface-border text-slate-400 bg-white/[0.01] font-mono">
                {children}
              </td>
            ),
            code: ({ className, children, ...props }) => {
              const isInline = !className;
              if (isInline) {
                return (
                  <code className="bg-white/5 text-slate-200 border border-surface-border px-1.5 py-0.5 rounded-sm font-mono text-[11px]" {...props}>
                    {children}
                  </code>
                );
              }
              return (
                <div className="relative my-2 rounded-sm bg-black/20 border border-surface-border p-2.5 overflow-x-auto font-mono text-[11px] text-slate-300">
                  <code {...props}>{children}</code>
                </div>
              );
            },
            blockquote: ({ children }) => (
              <blockquote className="border-l-2 border-surface-border-strong bg-white/[0.02] px-3 py-1.5 my-2 rounded-r text-slate-400 text-xs">
                {children}
              </blockquote>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>

      {citations && citations.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-surface-border">
          <span className="text-[10px] text-slate-500 font-medium flex items-center gap-1">
            <FileText className="w-3 h-3" />
            Citations:
          </span>
          {citations.map((c, idx) => (
            <span
              key={idx}
              className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 border border-surface-border text-slate-400"
            >
              {c}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
