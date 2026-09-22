import React from 'react';
import { Power, Gauge, Mountain, Thermometer, Compass, Sliders } from 'lucide-react';
import { UnifiedTelemetryState, ControlCommand } from '../types/telemetry';

interface EngineControlsProps {
  state: UnifiedTelemetryState;
  onCommand: (cmd: ControlCommand) => void;
}

export const EngineControls: React.FC<EngineControlsProps> = ({ state, onCommand }) => {
  const isEngineOn = state.is_engine_running;
  const throttle = state.telemetry.TPS || 0;
  const altitude = state.telemetry.ALTITUDE_FT || 18500;
  const oat = state.telemetry.OAT_C || -22;
  const theater = state.telemetry.THEATER || 'LADAKH';

  const handleThrottleChange = (val: number) => {
    onCommand({ action: 'SET_THROTTLE', throttle: val });
  };

  const handleAltitudeChange = (val: number) => {
    onCommand({ action: 'SET_ALTITUDE', altitude_ft: val });
  };

  const handleOatChange = (val: number) => {
    onCommand({ action: 'SET_OAT', oat_c: val });
  };

  return (
    <div className="surface-panel  p-4 sm:p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-surface-border pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-sm bg-accent-dim flex items-center justify-center text-accent">
            <Gauge className="w-3.5 h-3.5" />
          </div>
          <div>
            <h2 className="text-xs font-semibold text-white">
              Flight Deck &amp; Propulsion Controls
            </h2>
            <p className="text-[11px] text-slate-500">Authoritative ECU FADEC command</p>
          </div>
        </div>

        <button
          onClick={() =>
            onCommand({
              action: isEngineOn ? 'STOP_ENGINE' : 'START_ENGINE',
            })
          }
          className={`flex items-center gap-2 px-3 py-1.5 rounded-sm text-xs font-medium transition-colors ${
            isEngineOn
              ? 'bg-critical-dim text-critical border border-critical-muted hover:bg-critical-dim/70'
              : 'bg-success-dim text-success border border-success-muted hover:bg-success-dim/70'
          }`}
        >
          <Power className="w-3.5 h-3.5" />
          <span>{isEngineOn ? 'Engine cutoff' : 'Ignition start'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Left: Throttle */}
        <div className="space-y-3 bg-white/[0.03] p-3.5 rounded-sm border border-surface-border">
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400 flex items-center gap-1.5 font-medium">
              <Sliders className="w-3.5 h-3.5 text-slate-500" />
              Throttle (TPS)
            </span>
            <div className="flex items-baseline gap-1">
              <span className="text-base font-semibold font-mono text-white">
                {throttle.toFixed(0)}%
              </span>
              <span className="text-[10px] text-slate-500">command</span>
            </div>
          </div>

          <div className="relative pt-1 pb-1">
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={throttle}
              disabled={!isEngineOn}
              onChange={(e) => handleThrottleChange(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-surface-card rounded-full appearance-none cursor-pointer disabled:opacity-30 transition-opacity"
            />
          </div>

          <div className="grid grid-cols-4 gap-1.5 pt-1">
            {[
              { label: 'Idle', val: 15, sub: '15%' },
              { label: 'Cruise', val: 72, sub: '72%' },
              { label: 'MCN', val: 90, sub: '90%' },
              { label: 'WOT', val: 100, sub: '100%' },
            ].map((p) => {
              const isActive = Math.abs(throttle - p.val) < 2;
              return (
                <button
                  key={p.label}
                  disabled={!isEngineOn}
                  onClick={() => handleThrottleChange(p.val)}
                  className={`py-1.5 px-2 text-[11px] rounded-sm border transition-colors disabled:opacity-30 ${
                    isActive
                      ? 'border-accent-muted text-accent bg-accent-dim font-medium'
                      : 'bg-surface-card border-surface-border text-slate-400 hover:text-white hover:border-surface-border-strong'
                  }`}
                >
                  <div className="font-medium">{p.label}</div>
                  <div className="text-[9px] font-mono text-slate-500">{p.sub}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Mission Regimes & Environment (SIM-05..SIM-08) */}
        <div className="space-y-3 bg-white/[0.03] p-3.5 rounded-sm border border-surface-border">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400 flex items-center gap-1.5 font-medium">
              <Compass className="w-3.5 h-3.5 text-slate-500" />
              Mission Regimes (SIM-05..08)
            </span>
            <span className="text-[10px] font-mono text-accent">{theater}</span>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            <button
              onClick={() => onCommand({ action: 'SET_REGIME', regime: 'LADAKH', region: 'LADAKH' })}
              className={`px-2 py-1.5 text-[11px] rounded-sm border transition-colors text-left ${
                theater === 'LADAKH'
                  ? 'border-accent-muted text-accent bg-accent-dim font-medium'
                  : 'bg-surface-card border-surface-border text-slate-400 hover:text-white'
              }`}
            >
              <div className="font-semibold">Ladakh (20k ft)</div>
              <div className="text-[9px] text-slate-500 font-mono">SIM-05 High-Alt</div>
            </button>
            <button
              onClick={() => onCommand({ action: 'SET_REGIME', regime: 'THAR_DESERT', region: 'THAR_DESERT' })}
              className={`px-2 py-1.5 text-[11px] rounded-sm border transition-colors text-left ${
                theater === 'THAR_DESERT'
                  ? 'border-warning-muted text-warning bg-warning-dim font-medium'
                  : 'bg-surface-card border-surface-border text-slate-400 hover:text-white'
              }`}
            >
              <div className="font-semibold">Thar (+44°C)</div>
              <div className="text-[9px] text-slate-500 font-mono">SIM-07 Hot-Weather</div>
            </button>
            <button
              onClick={() => onCommand({ action: 'SET_REGIME', regime: 'ENDURANCE_LOITER', region: 'ENDURANCE_LOITER' })}
              className={`px-2 py-1.5 text-[11px] rounded-sm border transition-colors text-left ${
                theater === 'ENDURANCE_LOITER'
                  ? 'border-emerald-500/50 text-emerald-300 bg-emerald-500/10 font-medium'
                  : 'bg-surface-card border-surface-border text-slate-400 hover:text-white'
              }`}
            >
              <div className="font-semibold">Endurance Loiter</div>
              <div className="text-[9px] text-slate-500 font-mono">SIM-06 Eco-Cruise</div>
            </button>
            <button
              onClick={() => onCommand({ action: 'SET_REGIME', regime: 'RAPID_THROTTLE_TRANSIENTS', region: 'RAPID_THROTTLE_TRANSIENTS' })}
              className={`px-2 py-1.5 text-[11px] rounded-sm border transition-colors text-left ${
                theater === 'RAPID_THROTTLE_TRANSIENTS'
                  ? 'border-indigo-500/50 text-indigo-300 bg-indigo-500/10 font-medium'
                  : 'bg-surface-card border-surface-border text-slate-400 hover:text-white'
              }`}
            >
              <div className="font-semibold">Rapid Transients</div>
              <div className="text-[9px] text-slate-500 font-mono">SIM-08 FADEC Burst</div>
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="space-y-1 bg-surface-card p-2 rounded-sm border border-surface-border">
              <div className="flex justify-between text-[11px]">
                <span className="text-slate-400 flex items-center gap-1">
                  <Mountain className="w-3 h-3 text-slate-500" />
                  Altitude
                </span>
                <span className="text-white font-mono font-medium">{(altitude / 1000).toFixed(1)}k ft</span>
              </div>
              <input
                type="range"
                min="0"
                max="25000"
                step="500"
                value={altitude}
                onChange={(e) => handleAltitudeChange(parseFloat(e.target.value))}
                className="w-full h-1 bg-surface rounded-full appearance-none cursor-pointer"
              />
            </div>

            <div className="space-y-1 bg-surface-card p-2 rounded-sm border border-surface-border">
              <div className="flex justify-between text-[11px]">
                <span className="text-slate-400 flex items-center gap-1">
                  <Thermometer className="w-3 h-3 text-slate-500" />
                  OAT
                </span>
                <span className="text-white font-mono font-medium">{oat.toFixed(0)}°C</span>
              </div>
              <input
                type="range"
                min="-40"
                max="50"
                step="1"
                value={oat}
                onChange={(e) => handleOatChange(parseFloat(e.target.value))}
                className="w-full h-1 bg-surface rounded-full appearance-none cursor-pointer"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
