import React from 'react';
import { AlertTriangle, CheckCircle, FileText, Crosshair, Zap, Flame, Fuel, Cog, Battery, Activity } from 'lucide-react';
import { UnifiedTelemetryState, ControlCommand } from '../types/telemetry';

interface FaultMatrixProps {
  state: UnifiedTelemetryState;
  onCommand: (cmd: ControlCommand) => void;
}

interface FaultDefinition {
  id: number;
  name: string;
  category: 'THERMAL' | 'FUEL' | 'IGNITION' | 'LUBE' | 'MECHANICAL' | 'EXHAUST' | 'ELECTRICAL' | 'AVIONICS';
  desc: string;
  icon: React.ReactNode;
}

const DRDO_FAULTS: FaultDefinition[] = [
  { id: 1, name: 'Cyl #2 CHT Overheat', category: 'THERMAL', desc: 'Baffle leak / +43°C thermal surge', icon: <Flame className="w-3.5 h-3.5" /> },
  { id: 2, name: 'Fuel Injector #1 Clog', category: 'FUEL', desc: 'Lean burn / fuel flow drop', icon: <Fuel className="w-3.5 h-3.5" /> },
  { id: 3, name: 'Ignition Spark Misfire', category: 'IGNITION', desc: 'Lane A drop / RPM jitter ±185', icon: <Zap className="w-3.5 h-3.5" /> },
  { id: 4, name: 'Oil Pressure Decay', category: 'LUBE', desc: 'Scavenge leak / 3.85 -> 1.8 bar', icon: <Activity className="w-3.5 h-3.5" /> },
  { id: 5, name: 'Gearbox Vibration', category: 'MECHANICAL', desc: 'Micro-pitting / 3rd harmonic surge', icon: <Cog className="w-3.5 h-3.5" /> },
  { id: 6, name: 'Exhaust EGT Imbalance', category: 'EXHAUST', desc: 'Manifold delta > 60°C', icon: <Flame className="w-3.5 h-3.5" /> },
  { id: 7, name: 'Alternator Voltage Sag', category: 'ELECTRICAL', desc: '14.2V -> 11.8V bus sag', icon: <Battery className="w-3.5 h-3.5" /> },
  { id: 8, name: 'Dual FADEC ECU Drift', category: 'AVIONICS', desc: 'MAP sensor skew between lanes', icon: <Crosshair className="w-3.5 h-3.5" /> },
];

export const FaultMatrix: React.FC<FaultMatrixProps> = ({ state, onCommand }) => {
  const activeFaultId = state.active_commanded_fault_id;
  const diagnosedFaultId = state.analytics.diagnosed_fault_id;

  return (
    <div className="surface-panel  p-4 sm:p-5 space-y-3.5">
      <div className="flex items-center justify-between border-b border-surface-border pb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-sm bg-critical-dim flex items-center justify-center text-critical">
            <AlertTriangle className="w-3.5 h-3.5" />
          </div>
          <div>
            <h2 className="text-xs font-semibold text-white">
              DRDO Fault Injection Matrix
            </h2>
            <p className="text-[11px] text-slate-500">8 physical degradation modes (PS-26054)</p>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => onCommand({ action: 'CLEAR_FAULT' })}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-medium transition-colors ${
              activeFaultId === 0 && diagnosedFaultId === 0
                ? 'bg-success-dim text-success border border-success-muted/60'
                : 'bg-success-dim text-success border border-success-muted hover:bg-success-dim/70'
            }`}
          >
            <CheckCircle className="w-3.5 h-3.5" />
            <span>Reset nominal</span>
          </button>

          <button
            onClick={() => onCommand({ action: 'EXPORT_DEBRIEF' })}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-medium bg-accent-dim text-accent border border-accent-muted hover:bg-accent-dim/70 transition-colors"
            title="Export post-flight CBM PDF / Markdown debrief report"
          >
            <FileText className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">CBM debrief</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {DRDO_FAULTS.map((f) => {
          const isCommanded = activeFaultId === f.id;
          const isDiagnosed = diagnosedFaultId === f.id;
          const isTriggered = isCommanded || isDiagnosed;

          return (
            <button
              key={f.id}
              onClick={() => onCommand({ action: 'SET_FAULT', fault_id: f.id })}
              className={`p-3 rounded-sm text-left transition-colors border relative flex flex-col justify-between group ${
                isTriggered
                  ? 'bg-critical-dim border-critical-muted'
                  : 'bg-white/[0.02] border-surface-border hover:border-surface-border-strong hover:bg-white/[0.04]'
              }`}
            >
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-1.5">
                  <span
                    className={`w-5 h-5 rounded-sm flex items-center justify-center text-[10px] font-mono font-semibold ${
                      isTriggered
                        ? 'bg-critical text-black'
                        : 'bg-surface-card border border-surface-border text-slate-400 group-hover:text-slate-200'
                    }`}
                  >
                    F{f.id}
                  </span>
                  <span className="text-[9px] text-slate-500 uppercase tracking-wide">{f.category}</span>
                </div>

                {isTriggered ? (
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-critical"></span>
                  </span>
                ) : (
                  <div className="text-slate-500 group-hover:text-slate-300 transition-colors">
                    {f.icon}
                  </div>
                )}
              </div>

              <div className="mt-2">
                <div className="font-medium text-xs text-white leading-tight">
                  {f.name}
                </div>
                <div className="text-[10px] text-slate-500 mt-1 line-clamp-1">
                  {f.desc}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
