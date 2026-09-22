import React, { useState, useEffect } from 'react';
import {
  WifiOff,
  Settings,
  Shield,
  Activity,
  Clock,
  Compass,
  Zap,
  User,
  Cpu,
  Wrench,
} from 'lucide-react';
import { UnifiedTelemetryState, GCSRole } from '../types/telemetry';

interface HeaderProps {
  state: UnifiedTelemetryState;
  isConnected: boolean;
  latencyMs: number;
  activeRole: GCSRole;
  onSelectRole: (role: GCSRole) => void;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  state,
  isConnected,
  latencyMs,
  activeRole,
  onSelectRole,
  onOpenSettings,
}) => {
  const isFaulted = state.analytics.diagnosed_fault_id > 0;
  const isEngineOn = state.is_engine_running;
  const theater = state.telemetry.THEATER || 'LADAKH';

  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toISOString().substring(11, 19) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="sticky top-0 z-40 bg-surface/95 backdrop-blur-sm border-b border-surface-border px-3 sm:px-6 py-2.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
        {/* Left: Identity */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-sm bg-accent-dim border border-surface-border flex items-center justify-center text-accent">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-sm font-semibold tracking-tight text-white flex items-center gap-1.5">
                Rotax 912 iS
                <span className="text-xs font-normal text-slate-400">Sport</span>
              </h1>
              <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded-sm bg-white/5 text-slate-400 border border-surface-border">
                DRDO PS-26054
              </span>
            </div>
            <p className="text-[11px] text-slate-500 hidden sm:flex items-center gap-1.5">
              <span>MALE UAV Digital Twin GCS</span>
              <span className="text-slate-700">·</span>
              <span className="text-slate-400 flex items-center gap-1">
                <Compass className="w-3 h-3" />
                {theater === 'LADAKH' ? 'Ladakh theater (20k ft)' : 'Thar desert (+44°C)'}
              </span>
            </p>
          </div>
        </div>

        {/* Center: Live status badges */}
        <div className="flex items-center gap-2">
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-surface-card border border-surface-border text-xs font-mono text-slate-400">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span>{utcTime}</span>
          </div>

          <button
            onClick={onOpenSettings}
            className={`flex items-center gap-2 px-2.5 py-1 rounded-full text-xs border transition-colors ${
              isConnected
                ? 'bg-success-dim text-success border-success-muted hover:bg-success-dim/80'
                : 'bg-critical-dim text-critical border-critical-muted hover:bg-critical-dim/80'
            }`}
            title="Click to configure backend URL"
          >
            {isConnected ? (
              <>
                <span className="relative flex h-1.5 w-1.5">
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-success"></span>
                </span>
                <span className="font-medium hidden sm:inline">20 Hz Active</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-black/20 text-success">
                  {latencyMs}ms
                </span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5" />
                <span className="font-medium">Offline</span>
              </>
            )}
          </button>

          <div
            className={`hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border ${
              isEngineOn
                ? 'bg-accent-dim text-accent border-accent-muted'
                : 'bg-white/5 text-slate-500 border-surface-border'
            }`}
          >
            <Activity className={`w-3.5 h-3.5 ${isEngineOn ? 'text-accent' : 'text-slate-500'}`} />
            <span className="font-medium">{isEngineOn ? 'Propulsion engaged' : 'Standby'}</span>
          </div>

          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
              isFaulted
                ? 'bg-critical-dim text-critical border-critical-muted'
                : 'bg-success-dim text-success border-success-muted'
            }`}
          >
            <Zap className={`w-3.5 h-3.5 ${isFaulted ? 'text-critical' : 'text-success'}`} />
            <span>HI</span>
            <span>{(state.analytics.health_index * 100).toFixed(0)}%</span>
          </div>
        </div>

        {/* Role Selector (VIS-02..04) */}
        <div className="hidden sm:flex items-center gap-1 p-0.5 rounded bg-surface-card border border-surface-border text-xs">
          {[
            { id: 'OPERATOR' as GCSRole, label: 'Operator', icon: <User className="w-3 h-3" /> },
            { id: 'PROPULSION_ENGINEER' as GCSRole, label: 'Propulsion', icon: <Cpu className="w-3 h-3" /> },
            { id: 'MAINTENANCE_CREW' as GCSRole, label: 'Maintenance', icon: <Wrench className="w-3 h-3" /> },
          ].map((r) => {
            const isActive = activeRole === r.id;
            return (
              <button
                key={r.id}
                onClick={() => onSelectRole(r.id)}
                className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                  isActive
                    ? 'bg-accent-dim text-accent border border-accent-muted'
                    : 'text-slate-400 hover:text-white'
                }`}
                title={`Switch GCS Role: ${r.label}`}
              >
                {r.icon}
                <span>{r.label}</span>
              </button>
            );
          })}
        </div>

        {/* Right: Sortie & settings */}
        <div className="flex items-center gap-2">
          <div className="hidden xl:flex flex-col text-right">
            <span className="text-[10px] text-slate-500">Sortie</span>
            <span className="text-xs font-mono text-slate-300">{state.sortie_id}</span>
          </div>

          <button
            onClick={onOpenSettings}
            className="p-2 rounded-sm bg-surface-card border border-surface-border text-slate-400 hover:text-white hover:bg-surface-card-hover transition-colors"
            title="Configure backend data link"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
