import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Info, X, Calculator, ShieldCheck, Database, Sliders } from 'lucide-react';

export interface CalculationStep {
  label: string;
  detail: string;
}

export interface PanelInfoModalProps {
  title: string;
  subtitle?: string;
  description: string;
  formula?: string;
  calculationSteps?: CalculationStep[];
  provenance?: string;
  thresholds?: string;
  sensorInputs?: string[];
}

export const PanelInfoModal: React.FC<PanelInfoModalProps> = ({
  title,
  subtitle,
  description,
  formula,
  calculationSteps,
  provenance,
  thresholds,
  sensorInputs,
}) => {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open]);

  const modal = open ? (
    <div
      className="fixed inset-0 z-[110] flex items-center justify-center bg-black/60 backdrop-blur-xs p-3 sm:p-4 animate-fade-in"
      onClick={() => setOpen(false)}
      role="dialog"
      aria-modal="true"
      aria-labelledby={`info-title-${title.replace(/\s+/g, '-').toLowerCase()}`}
    >
      <div
        className="surface-panel w-full max-w-xl max-h-[85vh] flex flex-col rounded-sm shadow-card-lg border border-surface-border text-slate-800 bg-[#f7f6f0] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Pinned Header */}
        <div className="flex items-start justify-between border-b border-surface-border p-3.5 sm:p-4 shrink-0 bg-[#f7f6f0]">
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-[#68757a] font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-accent" />
              <span>DRDO PS-26054 Telemetry &amp; Physics Specification</span>
            </div>
            <h3
              id={`info-title-${title.replace(/\s+/g, '-').toLowerCase()}`}
              className="text-sm sm:text-base font-bold text-slate-900 tracking-tight mt-0.5"
            >
              {title}
            </h3>
            {subtitle && (
              <p className="text-xs text-slate-500 font-mono mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="rounded-sm p-1.5 text-slate-400 hover:text-slate-800 hover:bg-black/10 transition-colors"
            title="Close explanation (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-3.5 sm:p-4 space-y-3.5 text-xs font-sans leading-relaxed text-slate-700">
          {/* 1. Purpose */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3 space-y-1">
            <div className="flex items-center gap-1.5 text-accent font-semibold uppercase tracking-wider text-[11px] font-mono">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>System Role &amp; Purpose</span>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed font-sans">{description}</p>
          </div>

          {/* 2. Mathematical Formula */}
          {formula && (
            <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3 space-y-1.5">
              <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px] font-mono">
                <Calculator className="w-3.5 h-3.5 text-indigo-700" />
                <span>Mathematical Formulation</span>
              </div>
              <div className="font-mono text-[11px] leading-relaxed bg-[#f2f1eb] border border-surface-border p-2 rounded-xs text-accent whitespace-pre-wrap break-words">
                {formula}
              </div>
            </div>
          )}

          {/* 3. Step-by-Step Calculation Flow */}
          {calculationSteps && calculationSteps.length > 0 && (
            <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3 space-y-2">
              <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px] font-mono">
                <Sliders className="w-3.5 h-3.5 text-emerald-700" />
                <span>How This Is Calculated</span>
              </div>
              <div className="space-y-1.5">
                {calculationSteps.map((step, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-xs">
                    <span className="w-4 h-4 rounded-full bg-accent-dim text-accent flex items-center justify-center text-[10px] font-mono font-bold shrink-0 mt-0.5">
                      {idx + 1}
                    </span>
                    <div>
                      <span className="font-semibold text-slate-800 font-mono text-[11px]">{step.label}: </span>
                      <span className="text-slate-600">{step.detail}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 4. Sensor Inputs */}
          {sensorInputs && sensorInputs.length > 0 && (
            <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3 space-y-1.5">
              <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px] font-mono">
                <Database className="w-3.5 h-3.5 text-cyan-700" />
                <span>Sensor Channels &amp; Inputs</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {sensorInputs.map((sensor, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 bg-[#f2f1eb] border border-surface-border rounded-xs font-mono text-[10px] text-slate-700 font-medium"
                  >
                    {sensor}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 5. Thresholds & Provenance */}
          {(thresholds || provenance) && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
              {thresholds && (
                <div className="rounded-sm border border-surface-border bg-black/[0.02] p-2.5 space-y-1">
                  <span className="font-mono uppercase tracking-wider text-slate-500 font-semibold block text-[10px]">
                    Alert Thresholds
                  </span>
                  <p className="text-slate-700 font-mono text-[11px] leading-tight">{thresholds}</p>
                </div>
              )}
              {provenance && (
                <div className="rounded-sm border border-surface-border bg-black/[0.02] p-2.5 space-y-1">
                  <span className="font-mono uppercase tracking-wider text-slate-500 font-semibold block text-[10px]">
                    Data Provenance
                  </span>
                  <p className="text-slate-700 font-mono text-[11px] leading-tight">{provenance}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  ) : null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="p-1 rounded-sm text-slate-400 hover:text-accent hover:bg-black/5 transition-colors"
        title={`Specification & Calculation: ${title}`}
      >
        <Info className="w-3.5 h-3.5" />
      </button>
      {typeof document !== 'undefined' && createPortal(modal, document.body)}
    </>
  );
};
