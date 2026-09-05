import React from 'react';
import { Cog, Fuel, Zap, Flame, Wrench, HeartPulse, ShieldCheck, AlertTriangle } from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';

interface SubsystemHealthCardProps {
  state: UnifiedTelemetryState;
}

interface SubsystemItem {
  id: string;
  name: string;
  sublabel: string;
  score: number;
  physicsParam: string;
  icon: React.ReactNode;
}

export const SubsystemHealthCard: React.FC<SubsystemHealthCardProps> = ({ state }) => {
  const sub = state.analytics.subsystem_health || {
    propulsion: 1.0,
    fuel_system: 1.0,
    electrical: 1.0,
    thermal: 1.0,
    mechanical: 1.0,
  };

  const overallHealth = state.analytics.health_index;
  const isFaulted = state.analytics.diagnosed_fault_id > 0;

  const subsystems: SubsystemItem[] = [
    {
      id: 'propulsion',
      name: 'Propulsion Core',
      sublabel: 'Crankshaft & Combustion',
      physicsParam: 'RPM & MAP Balance',
      score: sub.propulsion,
      icon: <Cog className="w-4 h-4" />,
    },
    {
      id: 'fuel_system',
      name: 'Fuel Injection',
      sublabel: 'Dual Injection Lanes & Rail',
      physicsParam: 'Fuel Flow & Rail Pressure',
      score: sub.fuel_system,
      icon: <Fuel className="w-4 h-4" />,
    },
    {
      id: 'electrical',
      name: 'Electrical & FADEC',
      sublabel: 'Alternator & Dual ECU',
      physicsParam: 'Bus Voltage & Lane Skew',
      score: sub.electrical,
      icon: <Zap className="w-4 h-4" />,
    },
    {
      id: 'thermal',
      name: 'Thermal & Cooling',
      sublabel: 'CHT Heads & Oil Cooling',
      physicsParam: 'CHT 1-4 & Oil Temperature',
      score: sub.thermal,
      icon: <Flame className="w-4 h-4" />,
    },
    {
      id: 'mechanical',
      name: 'Drivetrain & Gearbox',
      sublabel: 'Reduction Gear & Clutch',
      physicsParam: 'Vibration RMS Harmonics',
      score: sub.mechanical,
      icon: <Wrench className="w-4 h-4" />,
    },
  ];

  const getScoreClasses = (val: number) => {
    if (val < 0.5) return 'text-critical bg-critical-dim border-critical-muted';
    if (val < 0.8) return 'text-warning bg-warning-dim border-warning-muted';
    return 'text-success bg-success-dim border-success-muted';
  };

  const getBarColor = (val: number) => {
    if (val < 0.5) return 'bg-critical';
    if (val < 0.8) return 'bg-warning';
    return 'bg-success';
  };

  const getStatusText = (val: number) => {
    if (val < 0.5) return 'DEGRADED';
    if (val < 0.8) return 'CAUTION';
    return 'NOMINAL';
  };

  return (
    <div className="surface-panel  p-4 sm:p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-surface-border pb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-sm bg-accent-dim flex items-center justify-center text-accent">
            <HeartPulse className={`w-3.5 h-3.5 ${isFaulted ? 'text-critical' : 'text-accent'}`} />
          </div>
          <div>
            <h2 className="text-xs font-semibold text-white">
              Physical Subsystem Health Index
            </h2>
            <p className="text-[11px] text-slate-500">Physics residuals &amp; anomaly autoencoder coupling</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] text-slate-500">
            Health index:
          </span>
          <span
            className={`text-xs font-mono font-semibold px-2.5 py-1 rounded-sm border flex items-center gap-1.5 ${getScoreClasses(
              overallHealth
            )}`}
          >
            {overallHealth >= 0.8 ? (
              <ShieldCheck className="w-3.5 h-3.5" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5" />
            )}
            <span>{(overallHealth * 100).toFixed(0)}%</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3.5">
        {subsystems.map((item) => {
          const pct = Math.max(0, Math.min(100, Math.round(item.score * 100)));
          return (
            <div
              key={item.id}
              className="bg-white/[0.02] p-3.5 rounded-sm border border-surface-border flex flex-col justify-between space-y-3 hover:border-surface-border-strong hover:bg-white/[0.04] transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <div
                    className={`w-8 h-8 rounded-sm flex items-center justify-center border ${getScoreClasses(
                      item.score
                    )}`}
                  >
                    {item.icon}
                  </div>
                  <div>
                    <h3 className="text-xs font-medium text-white leading-tight">
                      {item.name}
                    </h3>
                    <p className="text-[9px] text-slate-500">
                      {item.sublabel}
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span
                    className={`text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded border ${getScoreClasses(
                      item.score
                    )}`}
                  >
                    {getStatusText(item.score)}
                  </span>
                  <span className="font-semibold font-mono text-white">{pct}%</span>
                </div>

                <div className="w-full bg-black/20 h-1.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${getBarColor(item.score)}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>

                <div className="text-[9px] text-slate-600 mt-1 truncate">
                  Coupled: {item.physicsParam}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
