import { useMemo, useState } from 'react';
import { useEngineRuntime } from '../hooks/useEngineRuntime';
import { channelLabel, LabelsContext, useFetchLabels, useLabels } from '../utils/labels';
import { Activity, ArrowRight } from 'lucide-react';
import TwinStage from './TwinStage';

type Props = {
  serverUrl: string;
  onNavigateToRuntime?: () => void;
};

const num = (v: number | null | undefined, digits = 2) =>
  v === null || v === undefined ? '—' : v.toFixed(digits);

export default function TwinWorkspace({ serverUrl, onNavigateToRuntime }: Props) {
  const runtime = useEngineRuntime(serverUrl);
  const labels = useFetchLabels(runtime.api);
  const [training, setTraining] = useState(true);

  return (
    <LabelsContext.Provider value={labels}>
      <div className="space-y-6">
        {/* 3D Engine Twin Viewport */}
        <TwinStage
          engineId={runtime.engineId ?? null}
          engines={runtime.engines ?? []}
          onSelectEngine={runtime.selectEngine}
          state={runtime.state}
          faults={runtime.faults}
          cylinders={runtime.profile?.cylinders ?? null}
          api={runtime.api}
          command={runtime.command}
          training={training}
          onTraining={setTraining}
          onNavigateToRuntime={onNavigateToRuntime}
        />

        {/* Live Multi-Physics Telemetry Section (Revealed when scrolling down) */}
        <section className="surface-panel rounded-sm p-4 sm:p-5 shadow-card" aria-label="Live Telemetry Bus">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-border pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900">
                  Live 20 Hz Multi-Physics Telemetry Stream
                </h3>
              </div>
              <p className="mt-1 text-xs text-slate-500 font-mono">
                Real-time differential equation solutions for thermodynamic manifolds, combustion, and fluid dynamics.
                Injected faults directly alter physical engine parameters.
              </p>
            </div>

            {onNavigateToRuntime && (
              <button
                type="button"
                onClick={onNavigateToRuntime}
                className="inline-flex items-center gap-1.5 self-start sm:self-auto rounded-sm bg-accent px-3 py-1.5 text-xs font-mono font-medium text-white hover:bg-accent/90 transition-colors shadow-sm shrink-0 cursor-pointer"
              >
                <span>Full Engine Runtime & UKF Residuals</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <TelemetryGrid state={runtime.state} />
        </section>
      </div>
    </LabelsContext.Provider>
  );
}

function TelemetryGrid({ state }: { state: any }) {
  const labels = useLabels();
  const readings = useMemo(
    () => Object.entries(state?.readings ?? {}).sort(([a], [b]) => a.localeCompare(b)) as Array<[string, any]>,
    [state?.readings]
  );

  if (!readings.length) {
    return (
      <div className="py-8 text-center font-mono text-xs text-slate-500">
        Connecting to authoritative 20 Hz telemetry bus…
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-4">
      {/* Primary Thermodynamic Gauges */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
        {readings.map(([name, r]) => {
          const isWarning = r.quality === 'WARNING' || r.quality === 'CRITICAL';
          return (
            <div
              key={name}
              className={`rounded-sm border p-2.5 font-mono transition-colors ${
                isWarning
                  ? 'border-warning/50 bg-warning/5 text-warning'
                  : 'border-surface-border bg-black/[0.02] text-slate-800'
              }`}
            >
              <div className="truncate text-[10px] uppercase tracking-wider text-slate-500" title={name}>
                {channelLabel(labels, name)}
              </div>
              <div className="mt-1 flex items-baseline justify-between">
                <span className="text-base font-semibold tabular-nums text-slate-900">
                  {num(r.value, r.value > 100 ? 0 : 2)}
                </span>
                <span className="text-[11px] text-slate-500">{r.unit}</span>
              </div>
              {r.quality && r.quality !== 'OK' && (
                <div className="mt-0.5 text-[9px] font-bold text-critical uppercase">{r.quality}</div>
              )}
            </div>
          );
        })}
      </div>

      {/* Physics Truth Proof Callout */}
      <div className="flex items-center justify-between rounded-sm border border-surface-border bg-surface-card px-3 py-2 text-xs font-mono text-slate-600">
        <span className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-accent" />
          <span>Continuous Numerical Response: Watch temperatures (EGT/CHT) and manifold pressures react to injected faults in real time.</span>
        </span>
        <span className="text-[11px] text-slate-500 hidden sm:inline">SAMPLE RATE: 20 HZ</span>
      </div>
    </div>
  );
}
