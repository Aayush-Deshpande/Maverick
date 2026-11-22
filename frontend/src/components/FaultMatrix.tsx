import React from 'react';
import { AlertTriangle, CheckCircle, FileText, Crosshair, Zap, Flame, Fuel, Cog, Battery, Activity } from 'lucide-react';
import { UnifiedTelemetryState, ControlCommand } from '../types/telemetry';
import { PanelInfoModal } from './PanelInfoModal';

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
            <div className="flex items-center gap-1.5">
              <h2 className="text-xs font-semibold text-white">
                DRDO Fault Injection Matrix
              </h2>
              <PanelInfoModal
                title="DRDO Fault Injection Matrix"
                subtitle="Physical Degradation & Parameter Perturbation (PS-26054)"
                description="Injects continuous physical parameter degradations into the engine simulation according to the DRDO PS-26054 37-Fault FMECA Catalog (F01–F37). In strict adherence to the Zero Truth Leakage rule, faults modify underlying physical parameters (orifice discharge coefficients, heat transfer multipliers, coil resistances) rather than output telemetry."
                formula={`Parameter Perturbation: θ_fault(t) = θ_nominal · (1 - α · ramp(t - t_inj, τ=6s))
Cylinder Overheat: UA_cyl2 = UA_nominal · (1 - 0.45 · ramp(t, 6s))
Injector Clog: C_d,inj = C_d0 · 0.40  (fuel flow drop, lean mixture)
Oil Pressure Leak: R_orifice = R_0 · 0.35  (scavenge decay to 1.8 bar)
Gearbox Harmonic: a_vib(t) = a_0 + α · sin(3 · ω_crank · t + φ)`}
                calculationSteps={[
                  { label: 'Fault Activation', detail: 'Operator or test harness triggers a physical degradation mode.' },
                  { label: 'Smooth Dynamic Ramp', detail: 'Linearly or exponentially ramps the parameter over 6.0 seconds (τ = 6 s) to emulate physical failure progression.' },
                  { label: 'Coupled Simulation', detail: '1D thermodynamic ODE solver propagates altered physical coefficients into temperatures, pressures, and vibration spectra.' },
                  { label: 'Zero Ground Truth Leak', detail: 'Inference and diagnostic observers inspect only telemetry residuals with zero access to the active fault ID.' },
                ]}
                sensorInputs={['CHT_1..4', 'EGT_1..4', 'OIL_PRESS', 'OIL_TEMP', 'FUEL_FLOW', 'VIB_RMS', 'BUS_VOLTAGE', 'MAP']}
                thresholds="8 primary degradation modes (F01–F08) spanning Thermal, Fuel, Ignition, Lube, Mechanical, and Avionics"
                provenance="DRDO PS-26054 FMECA Catalog, MIL-STD-1629A, and Rotax 912 iSc Maintenance Manual (Line/Heavy)"
              />
            </div>
            <p className="text-xs text-slate-500">8 physical degradation modes (PS-26054)</p>
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
              onClick={() => onCommand({ action: 'SET_FAULT', fault_id: f.id, ramp_duration_sec: 2.8, severity: 0.85 })}
              className={`p-3 rounded-sm text-left transition-colors border relative flex flex-col justify-between group ${
                isTriggered
                  ? 'bg-critical-dim border-critical-muted'
                  : 'bg-white/[0.02] border-surface-border hover:border-surface-border-strong hover:bg-white/[0.04]'
              }`}
            >
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-1.5">
                  <span
                    className={`w-5 h-5 rounded-sm flex items-center justify-center text-xs font-mono font-semibold ${
                      isTriggered
                        ? 'bg-critical text-black'
                        : 'bg-surface-card border border-surface-border text-slate-400 group-hover:text-slate-200'
                    }`}
                  >
                    F{f.id}
                  </span>
                  <span className="text-xs text-slate-500 uppercase tracking-wide">{f.category}</span>
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
                <div className="text-xs text-slate-500 mt-1 line-clamp-1">
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
