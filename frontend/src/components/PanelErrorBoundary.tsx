import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface PanelErrorBoundaryProps {
  /** Shown in the fallback card so the operator knows which panel failed. */
  label: string;
  children: React.ReactNode;
}

interface PanelErrorBoundaryState {
  error: Error | null;
}

/**
 * Isolates a render crash to a single dashboard panel instead of taking down the whole
 * cockpit UI. Without this, any unguarded field access on a telemetry/analytics payload
 * (e.g. `.toFixed()` on a value the backend renamed or stopped sending) throws during
 * render, and with no ErrorBoundary anywhere in the tree, React unmounts everything -
 * the entire dashboard goes blank mid-demo with no way to recover short of a page reload.
 * Each wrapped panel can now fail independently while the rest of the cockpit (and the
 * "Reset panel" affordance below) keeps working.
 */
export class PanelErrorBoundary extends React.Component<PanelErrorBoundaryProps, PanelErrorBoundaryState> {
  state: PanelErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): PanelErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(`[PanelErrorBoundary:${this.props.label}]`, error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="surface-panel surface-panel-critical rounded-2xl p-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-critical-dim flex items-center justify-center text-critical shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-xs font-semibold text-critical">
                {this.props.label} panel crashed
              </h4>
              <p className="text-[11px] text-slate-400 mt-0.5">
                {this.state.error.message || 'Unexpected rendering error.'} — other panels are unaffected.
              </p>
            </div>
          </div>
          <button
            onClick={() => this.setState({ error: null })}
            className="px-3.5 py-1.5 rounded-lg bg-critical-dim text-critical text-xs font-medium hover:bg-critical-dim/70 border border-critical-muted transition-colors shrink-0"
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
