import React, { useState, useEffect } from 'react';
import {
  WifiOff,
  Settings,
  Activity,
  Clock,
  Compass,
  Zap,
  User,
  Cpu,
  Wrench,
} from 'lucide-react';
import { UnifiedTelemetryState, GCSRole } from '../types/telemetry';
import { pct } from '../utils/format';
import InfoTooltip from './InfoTooltip';

interface HeaderProps {
  state: UnifiedTelemetryState;
  isConnected: boolean;
  latencyMs: number;
  activeRole: GCSRole;
  onSelectRole: (role: GCSRole) => void;
  onOpenSettings: () => void;
  runtimeMode?: boolean;
  onGoLanding?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  state,
  isConnected,
  latencyMs,
  activeRole,
  onSelectRole,
  onOpenSettings,
  runtimeMode = false,
  onGoLanding,
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
    <header className="sticky top-0 z-40 bg-surface/95 backdrop-blur-sm border-b border-surface-border px-2 sm:px-6 py-2">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-2 sm:gap-3 flex-wrap">
        {/* Left: Identity */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          <button
            onClick={onGoLanding}
            disabled={!onGoLanding}
            className="flex items-center gap-2 text-left group transition-opacity hover:opacity-90 disabled:cursor-default"
            title={onGoLanding ? 'Return to Platform Overview' : undefined}
          >
            <span className="w-8 h-8 sm:w-9 sm:h-9 grid place-items-center overflow-hidden rounded-sm bg-surface-card border border-surface-border shadow-sm group-hover:border-accent transition-colors shrink-0">
              <img src="/images/anumaan-mark-editorial.png" alt="ANUMAAN" className="w-full h-full object-contain" />
            </span>
            <div>
              <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                <span className="text-xs font-bold tracking-wider text-white">ANUMAAN</span>
                <span className="text-[10px] sm:text-xs font-mono px-1.5 py-0.5 rounded-sm bg-white/5 text-slate-300 border border-surface-border">
                  DRDO PS-26054
                </span>
              </div>
              <div className="text-[11px] sm:text-xs text-slate-400 font-mono hidden sm:flex items-center gap-1.5">
                <span>{runtimeMode ? 'Multi-engine propulsion health console' : 'MALE UAV Digital Twin GCS'}</span>
                {!runtimeMode && <>
                  <span className="text-slate-700">·</span>
                  <span className="text-slate-400 flex items-center gap-1">
                    <Compass className="w-3 h-3 text-accent" />
                    {theater === 'LADAKH' ? 'Ladakh FL200 (-22°C)' : 'Thar desert (+44°C)'}
                  </span>
                  <InfoTooltip
                    title="Flight Environment & Operating Theater"
                    content="Simulates the operating flight environment: Ladakh FL200 tests high-altitude engine power and sub-zero cooling at 20,000 ft (-22°C); Thar Desert tests extreme cooling radiator limits at +44°C. You can toggle between Ladakh and Thar anytime in Settings (gear icon on the right)."
                    width={280}
                  />
                </>}
              </div>
            </div>
          </button>
        </div>

        {/* Center: Live status badges */}
        <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-surface-card border border-surface-border text-xs font-mono text-slate-300">
            <Clock className="w-3.5 h-3.5 text-accent" />
            <span>{utcTime}</span>
            <InfoTooltip
              title="Mission Flight Clock (UTC)"
              content="Universal Coordinated Time (UTC) used across aviation ground control stations to synchronize sensor timestamps with flight black-box recordings."
              width={260}
            />
          </div>

          {runtimeMode ? (
            <div className="flex items-center gap-1 px-2 sm:px-2.5 py-1 rounded-sm text-xs border bg-surface-card text-accent border-accent/40 font-mono">
              <Activity className="w-3.5 h-3.5 text-accent" />
              <span className="font-semibold tracking-wide">ENGINE RUNTIME</span>
              <InfoTooltip
                title="Engine Runtime Mode"
                content="Live physical engine console running multi-cylinder simulations at 20 updates per second across all 5 UAV engines."
                width={260}
              />
            </div>
          ) : (
            <div className="flex items-center gap-1">
              <button
                onClick={onOpenSettings}
                className={`flex items-center gap-1.5 px-2 sm:px-2.5 py-1 rounded-sm text-xs font-mono border transition-colors ${
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
                    <span className="text-[11px] sm:text-xs font-mono px-1 sm:px-1.5 py-0.5 rounded bg-black/20 text-success">
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
              <InfoTooltip
                title="Avionics Telemetry Stream"
                content="Continuous live connection streaming 20 updates per second from the engine digital twin. The badge indicates round-trip network latency in milliseconds."
                width={260}
              />
            </div>
          )}

          {!runtimeMode && (
            <div
              className={`hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-xs font-mono border ${
                isEngineOn
                  ? 'bg-accent-dim text-accent border-accent-muted'
                  : 'bg-white/5 text-slate-500 border-surface-border'
              }`}
            >
              <Activity className={`w-3.5 h-3.5 ${isEngineOn ? 'text-accent' : 'text-slate-500'}`} />
              <span className="font-medium">{isEngineOn ? 'Propulsion Engaged' : 'Standby'}</span>
              <InfoTooltip
                title="Engine Operating State"
                content="Standby indicates the engine is cold or shut down; Propulsion Engaged indicates active ignition, fuel burning, and crankshaft power output."
                width={260}
              />
            </div>
          )}

          {!runtimeMode && (
            <div
              className={`flex items-center gap-1.5 px-2 sm:px-2.5 py-1 rounded-sm text-xs font-mono font-medium border ${
                isFaulted
                  ? 'bg-critical-dim text-critical border-critical-muted'
                  : 'bg-success-dim text-success border-success-muted'
              }`}
            >
              <Zap className={`w-3.5 h-3.5 ${isFaulted ? 'text-critical' : 'text-success'}`} />
              <span>HI: {pct(state.analytics.health_index)}</span>
              <InfoTooltip
                title="Propulsion Health Index (HI)"
                content="Overall engine health score (0% to 100%). Green (100%) means healthy within all limits; Amber warns of internal wear or cooling degradation; Red (<50%) signals an active diagnosed mechanical failure. NO DATA displays while waiting for calibrated telemetry."
                width={280}
              />
            </div>
          )}
        </div>

        {/* Role Selector (VIS-02..04) - Responsive for both mobile and desktop */}
        {!runtimeMode && (
          <div className="flex items-center gap-0.5 sm:gap-1 p-0.5 rounded-sm bg-surface-card border border-surface-border text-xs font-mono overflow-x-auto">
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
                  className={`flex items-center gap-1 px-2 sm:px-2.5 py-1 rounded-sm text-[11px] sm:text-xs font-medium transition-colors shrink-0 ${
                    isActive
                      ? 'bg-accent text-white shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                  title={`Switch GCS Role: ${r.label}`}
                >
                  {r.icon}
                  <span className="hidden xs:inline sm:inline">{r.label}</span>
                </button>
              );
            })}
            <InfoTooltip
              title="Ground Station Console Roles"
              content="Switches the workstation view: Operator for pilot flight gauges & route planning; Propulsion for thermodynamic twin state & sensor residuals; Maintenance for component wear & repair work orders."
              width={280}
            />
          </div>
        )}

        {/* Right: Sortie & settings */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {!runtimeMode && (
            <div className="hidden xl:flex items-center gap-1 text-right">
              <div className="flex flex-col">
                <span className="text-[10px] text-slate-500">Sortie</span>
                <span className="text-xs font-mono text-slate-300">{state.sortie_id}</span>
              </div>
              <InfoTooltip
                title="Flight Sortie Identifier"
                content="Unique operational mission flight test recording number. All telemetry readings, alarms, and pilot interventions are logged against this ID."
                width={260}
              />
            </div>
          )}

          <div className="flex items-center gap-1">
            <button
              onClick={onOpenSettings}
              className="p-1.5 sm:p-2 rounded-sm bg-surface-card border border-surface-border text-slate-400 hover:text-white hover:bg-surface-card-hover transition-colors"
              title="Configure backend data link and flight settings"
            >
              <Settings className="w-4 h-4" />
            </button>
            <InfoTooltip
              title="Console Settings"
              content="Adjust backend server URL, data stream ports, and toggle between Ladakh and Thar flight environments."
              width={260}
            />
          </div>
        </div>
      </div>
    </header>
  );
};
