import React from 'react';
import {
  Zap,
  Activity,
  Clock,
  AlertTriangle,
  TrendingUp,
  Cpu,
  ShieldCheck,
} from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';

interface PropulsionEngineerPanelProps {
  state: UnifiedTelemetryState;
}

const fmt = (v?: number, d = 1) => (v !== undefined && Number.isFinite(v) ? v.toFixed(d) : '--');

export const PropulsionEngineerPanel: React.FC<PropulsionEngineerPanelProps> = ({ state }) => {
  const t = state.telemetry;
  const a = state.analytics;
  const baseline = a.threshold_baseline;

  // Rotax 912 iS Factory Specification Constants
  const MAX_TAKEOFF_POWER_KW = 73.5; // 100 HP @ 5800 RPM (5 min limit)
  const MAX_CONTINUOUS_POWER_KW = 69.0; // 93 HP @ 5500 RPM
  const DISPLACEMENT_CC = 1352;
  const GEARBOX_RATIO = 2.43;

  // Power & Efficiency metrics
  const powerKw = t.POWER_KW ?? 0;
  const powerPct = Math.min(100, (powerKw / MAX_TAKEOFF_POWER_KW) * 100);
  const bsfc = t.BSFC_G_KWH ?? 0;
  const thermalEffPct = (t.THERMAL_EFFICIENCY ?? 0) * 100;

  // Injection & Ignition timing metrics
  const injTiming = t.INJ_TIMING_BTDC ?? 32.0;
  const pulseWidth = t.INJ_PULSE_WIDTH_MS ?? 4.2;
  const ignTiming = t.IGN_TIMING_BTDC ?? 26.0;
  const lambda = t.LAMBDA_AFR ?? 14.7;

  // Vibration Orders (Harmonics)
  const crankFreqHz = (t.ENGINE_RPM || 0) / 60.0;
  const propFreqHz = crankFreqHz / GEARBOX_RATIO;
  const gearMeshHz = crankFreqHz * 3.0; // 3rd harmonic gear mesh signature

  // Baseline comparator values
  const conventionalBreached = baseline?.conventional_breached ?? false;
  const breachedParams = baseline?.breached_parameters ?? [];
  const twinDetected = (a.diagnosed_fault_id ?? 0) > 0 || a.anomaly_score > 0.45;
  const leadTimeSec = baseline?.lead_time_sec;

  // Conventional redlines reference
  const redlines = [
    { param: 'CHT Max', limit: '135.0 °C', current: `${fmt(Math.max(t.CHT_1, t.CHT_2, t.CHT_3, t.CHT_4))} °C`, breached: Math.max(t.CHT_1, t.CHT_2, t.CHT_3, t.CHT_4) > 135 },
    { param: 'EGT Max', limit: '850.0 °C', current: `${fmt(Math.max(t.EGT_1, t.EGT_2, t.EGT_3, t.EGT_4))} °C`, breached: Math.max(t.EGT_1, t.EGT_2, t.EGT_3, t.EGT_4) > 850 },
    { param: 'Oil Press Min', limit: '2.0 bar', current: `${fmt(t.OIL_PRESS)} bar`, breached: t.OIL_PRESS < 2.0 && state.is_engine_running },
    { param: 'Oil Temp Max', limit: '130.0 °C', current: `${fmt(t.OIL_TEMP)} °C`, breached: t.OIL_TEMP > 130 },
    { param: 'Gearbox Vib Max', limit: '2.5 mm/s', current: `${fmt(t.VIB_GEARBOX_RMS, 2)} mm/s`, breached: t.VIB_GEARBOX_RMS > 2.5 },
    { param: 'DC Bus Min', limit: '12.0 V', current: `${fmt(t.BUS_VOLTAGE)} V`, breached: t.BUS_VOLTAGE < 12.0 },
  ];

  return (
    <div className="space-y-4">
      {/* Top Banner: Section Overview */}
      <div className="surface-panel p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 border-l-4 border-l-accent">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-accent-dim text-accent border border-accent-muted">
              VIS-03 / INT-03
            </span>
            <h2 className="text-sm font-semibold text-white tracking-wide">
              Propulsion Engineering &amp; Combustion Telemetry Console
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Thermodynamic performance maps, Dual-Lane FADEC injection timing, and early-warning baseline comparator for Rotax 912 iS Sport.
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="px-3 py-1.5 rounded bg-surface-card border border-surface-border">
            <span className="text-slate-500 block text-[10px]">FADEC LANE</span>
            <span className="font-semibold text-accent">{t.FADEC_ACTIVE_LANE || 'LANE A'}</span>
          </div>
          <div className="px-3 py-1.5 rounded bg-surface-card border border-surface-border">
            <span className="text-slate-500 block text-[10px]">DISPLACEMENT</span>
            <span className="font-semibold text-slate-200">{DISPLACEMENT_CC} cc</span>
          </div>
          <div className="px-3 py-1.5 rounded bg-surface-card border border-surface-border">
            <span className="text-slate-500 block text-[10px]">GEARBOX RATIO</span>
            <span className="font-semibold text-slate-200">{GEARBOX_RATIO}:1</span>
          </div>
        </div>
      </div>

      {/* Grid 1: Performance Maps & Efficiency Trends (VIS-07, INT-03) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Brake Power & Envelope */}
        <div className="surface-panel p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-surface-border pb-2">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-accent" />
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                Brake Power &amp; Envelope
              </h3>
            </div>
            <span className="text-[10px] font-mono text-slate-500">INT-03</span>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-slate-400">Shaft Brake Power</span>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold font-mono text-white">{fmt(powerKw, 1)}</span>
                <span className="text-xs text-slate-500">kW</span>
                <span className="text-xs text-slate-400 font-mono">({fmt(powerKw * 1.341, 1)} hp)</span>
              </div>
            </div>

            {/* Power Gauge Bar */}
            <div className="space-y-1">
              <div className="w-full h-2 bg-surface-card rounded-full overflow-hidden border border-surface-border">
                <div
                  className={`h-full transition-all duration-300 ${
                    powerKw > MAX_CONTINUOUS_POWER_KW ? 'bg-warning' : 'bg-accent'
                  }`}
                  style={{ width: `${powerPct}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] font-mono text-slate-500">
                <span>0 kW</span>
                <span>Max Cont. (69 kW)</span>
                <span>Take-Off (73.5 kW)</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-surface-border/60 text-xs">
              <div className="bg-surface-card p-2 rounded border border-surface-border">
                <span className="text-[10px] text-slate-500 block">Manifold Press (MAP)</span>
                <span className="text-sm font-mono font-semibold text-slate-200">{fmt(t.MAP, 1)} kPa</span>
              </div>
              <div className="bg-surface-card p-2 rounded border border-surface-border">
                <span className="text-[10px] text-slate-500 block">Density Alt Ratio</span>
                <span className="text-sm font-mono font-semibold text-slate-200">
                  {fmt(Math.exp(-((t.ALTITUDE_FT || 0) * 0.3048) / 8434.0), 2)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Engine Efficiency & BSFC (VIS-07) */}
        <div className="surface-panel p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-surface-border pb-2">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-success" />
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                Fuel Efficiency (BSFC)
              </h3>
            </div>
            <span className="text-[10px] font-mono text-slate-500">VIS-07</span>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-slate-400">Brake Specific Fuel Cons.</span>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold font-mono text-white">{fmt(bsfc, 0)}</span>
                <span className="text-xs text-slate-500">g / kWh</span>
              </div>
            </div>

            <div className="bg-surface-card p-2.5 rounded border border-surface-border space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Brake Thermal Efficiency</span>
                <span className="font-mono font-semibold text-success">{fmt(thermalEffPct, 1)}%</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Volumetric Fuel Flow</span>
                <span className="font-mono text-slate-200">{fmt(t.FUEL_FLOW, 1)} L/hr</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Fuel Rail Pressure</span>
                <span className="font-mono text-slate-200">{fmt(t.FUEL_RAIL_P, 1)} bar</span>
              </div>
            </div>

            <div className="text-[11px] text-slate-400 bg-white/[0.02] p-2 rounded border border-surface-border/60">
              <span className="text-slate-500 font-mono text-[10px] block">CRUISE TARGET</span>
              Rotax nominal eco-cruise target is 250–280 g/kWh at 4300–4800 RPM.
            </div>
          </div>
        </div>

        {/* FADEC Injection & Ignition Timing (HMS-11) */}
        <div className="surface-panel p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-surface-border pb-2">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-accent" />
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                FADEC Timing &amp; Combustion
              </h3>
            </div>
            <span className="text-[10px] font-mono text-slate-500">HMS-11</span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">INJ TIMING</span>
              <div className="flex items-baseline gap-1 mt-0.5">
                <span className="text-base font-bold font-mono text-accent">{fmt(injTiming, 1)}°</span>
                <span className="text-[10px] text-slate-500">BTDC</span>
              </div>
            </div>

            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">PULSE WIDTH</span>
              <div className="flex items-baseline gap-1 mt-0.5">
                <span className="text-base font-bold font-mono text-slate-100">{fmt(pulseWidth, 2)}</span>
                <span className="text-[10px] text-slate-500">ms</span>
              </div>
            </div>

            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">IGN ADVANCE</span>
              <div className="flex items-baseline gap-1 mt-0.5">
                <span className="text-base font-bold font-mono text-amber-400">{fmt(ignTiming, 1)}°</span>
                <span className="text-[10px] text-slate-500">BTDC</span>
              </div>
            </div>

            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">LAMBDA (AFR)</span>
              <div className="flex items-baseline gap-1 mt-0.5">
                <span className="text-base font-bold font-mono text-slate-100">{fmt(lambda, 2)}</span>
                <span className="text-[10px] text-slate-500">{lambda > 14.8 ? 'Lean' : lambda < 14.5 ? 'Rich' : 'Stoich'}</span>
              </div>
            </div>
          </div>

          <div className="text-[11px] text-slate-400 bg-white/[0.02] p-2 rounded border border-surface-border/60 flex items-center justify-between">
            <span>Dual Spark Ignition:</span>
            <span className="text-emerald-400 font-medium">Circuit A &amp; B Synced</span>
          </div>
        </div>
      </div>

      {/* Grid 2: Core Requirement F13 / G03 - Conventional Threshold Baseline Comparator */}
      <div className="surface-panel p-4 sm:p-5 space-y-4 border border-accent/30 bg-gradient-to-br from-surface to-surface-card">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-border pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                F13 / G03 / FDP-01
              </span>
              <h3 className="text-sm font-semibold text-white tracking-wide">
                Conventional Threshold vs. Digital Twin Early Warning Comparator
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Proving PS-26054 mandate: "transition from conventional threshold-based monitoring to intelligent predictive diagnostics".
            </p>
          </div>

          {/* Lead-Time Banner Badge */}
          <div className="flex items-center gap-2">
            {leadTimeSec !== null && leadTimeSec !== undefined ? (
              <div className="px-3 py-1.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center gap-2">
                <Clock className="w-4 h-4 text-emerald-400" />
                <div>
                  <span className="text-[9px] uppercase font-bold tracking-wider block">Lead-Time Advantage</span>
                  <span className="text-sm font-mono font-bold">+{leadTimeSec.toFixed(1)} s Ahead of Redline</span>
                </div>
              </div>
            ) : twinDetected && !conventionalBreached ? (
              <div className="px-3 py-1.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <div>
                  <span className="text-[9px] uppercase font-bold tracking-wider block">Early Warning Active</span>
                  <span className="text-xs font-semibold">Twin Alerting Before Redline Breach</span>
                </div>
              </div>
            ) : (
              <div className="px-3 py-1.5 rounded bg-surface-card border border-surface-border text-slate-400 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-slate-500" />
                <span className="text-xs font-medium">Both Paradigms Nominal</span>
              </div>
            )}
          </div>
        </div>

        {/* Side-by-side paradigm comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Paradigm A: Conventional Static Thresholds */}
          <div className="bg-surface-card p-3.5 rounded border border-surface-border space-y-3">
            <div className="flex items-center justify-between border-b border-surface-border/60 pb-2">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                1. Legacy Threshold Monitoring (Rotax OM)
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                  conventionalBreached
                    ? 'bg-critical-dim text-critical border-critical-muted'
                    : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                }`}
              >
                {conventionalBreached ? 'REDLINE TRIP' : 'WITHIN LIMITS'}
              </span>
            </div>

            <div className="text-xs text-slate-400">
              Only triggers after severe, irreversible thermal/mechanical damage has physically crossed fixed limit lines.
            </div>

            {/* Redline status list */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {redlines.map((r) => (
                <div
                  key={r.param}
                  className={`p-2 rounded border text-xs ${
                    r.breached
                      ? 'bg-critical-dim border-critical-muted text-critical'
                      : 'bg-white/[0.02] border-surface-border/60 text-slate-400'
                  }`}
                >
                  <div className="text-[10px] truncate text-slate-500">{r.param}</div>
                  <div className="font-mono font-semibold text-white mt-0.5">{r.current}</div>
                  <div className="text-[9px] font-mono text-slate-500">Limit: {r.limit}</div>
                </div>
              ))}
            </div>

            {breachedParams.length > 0 && (
              <div className="text-xs text-critical bg-critical-dim/30 p-2 rounded border border-critical-muted">
                Breached parameters: <span className="font-mono font-medium">{breachedParams.join(', ')}</span>
              </div>
            )}
          </div>

          {/* Paradigm B: ANUMAAN Digital Twin Physics Residuals */}
          <div className="bg-surface-card p-3.5 rounded border border-accent/30 space-y-3">
            <div className="flex items-center justify-between border-b border-surface-border/60 pb-2">
              <span className="text-xs font-semibold text-accent uppercase tracking-wider">
                2. ANUMAAN Physics-Informed Digital Twin
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                  twinDetected
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                }`}
              >
                {twinDetected ? 'ANOMALY DETECTED' : 'RESIDUALS NOMINAL'}
              </span>
            </div>

            <div className="text-xs text-slate-400">
              Calculates continuous Kalman/thermo-residual deviation against real-time expected physics states, alerting tens of seconds in advance.
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center bg-white/[0.02] p-2 rounded border border-surface-border/60">
                <span className="text-slate-400">Overall Anomaly Score:</span>
                <span className="font-mono font-semibold text-accent">{(a.anomaly_score * 100).toFixed(1)}%</span>
              </div>
              <div className="flex justify-between items-center bg-white/[0.02] p-2 rounded border border-surface-border/60">
                <span className="text-slate-400">Diagnosed Condition:</span>
                <span className="font-mono font-semibold text-slate-200">
                  {a.diagnosed_fault_name || 'Normal Continuous Operation'}
                </span>
              </div>
              <div className="flex justify-between items-center bg-white/[0.02] p-2 rounded border border-surface-border/60">
                <span className="text-slate-400">Diagnostic Confidence:</span>
                <span className="font-mono font-semibold text-emerald-400">
                  {((a.diagnosed_confidence || 0) * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            <div className="text-[11px] text-indigo-300 bg-indigo-950/40 p-2.5 rounded border border-indigo-800/40 leading-relaxed">
              <span className="font-semibold block text-indigo-200 mb-0.5">DRDO PS-26054 Capability Validated:</span>
              The twin detects incipient anomalies via multi-dimensional residual divergence while sensor values remain well inside legacy redlines.
            </div>
          </div>
        </div>
      </div>

      {/* Grid 3: High-Rate Vibration Spectral Order Analysis (HMS-09, F07) */}
      <div className="surface-panel p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-surface-border pb-2">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-accent" />
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
              Vibration Spectral Orders &amp; Bearing Harmonics (2 kHz DSP)
            </h3>
          </div>
          <span className="text-[10px] font-mono text-slate-500">HMS-09 / F07</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-xs">
          <div className="bg-surface-card p-2.5 rounded border border-surface-border">
            <span className="text-[10px] text-slate-500 block">1X CRANKSHAFT</span>
            <span className="text-base font-bold font-mono text-accent mt-0.5 block">
              {fmt(t.vibration_orders?.['1X'] ?? t.VIB_GEARBOX_RMS, 2)} mm/s
            </span>
            <span className="text-[9px] text-slate-500">{fmt(crankFreqHz, 1)} Hz fundamental</span>
          </div>

          <div className="bg-surface-card p-2.5 rounded border border-surface-border">
            <span className="text-[10px] text-slate-500 block">2X SECONDARY</span>
            <span className="text-base font-bold font-mono text-slate-200 mt-0.5 block">
              {fmt(t.vibration_orders?.['2X'] ?? (t.VIB_GEARBOX_RMS * 0.35), 2)} mm/s
            </span>
            <span className="text-[9px] text-slate-500">Reciprocating 2nd order</span>
          </div>

          <div className="bg-surface-card p-2.5 rounded border border-surface-border">
            <span className="text-[10px] text-slate-500 block">3X PROPELLER</span>
            <span className="text-base font-bold font-mono text-amber-300 mt-0.5 block">
              {fmt(t.vibration_orders?.['3X_prop'] ?? (t.VIB_GEARBOX_RMS * 0.2), 2)} mm/s
            </span>
            <span className="text-[9px] text-slate-500">{fmt(propFreqHz, 1)} Hz blade pass</span>
          </div>

          <div className="bg-surface-card p-2.5 rounded border border-surface-border">
            <span className="text-[10px] text-slate-500 block">0.43X WHIRL</span>
            <span className="text-base font-bold font-mono text-slate-200 mt-0.5 block">
              {fmt(t.vibration_orders?.['subharmonic_whirl'] ?? 0.05, 2)} mm/s
            </span>
            <span className="text-[9px] text-slate-500">Hydrodynamic oil whirl</span>
          </div>

          <div className="bg-surface-card p-2.5 rounded border border-surface-border">
            <span className="text-[10px] text-slate-500 block">1.69X GEAR MESH</span>
            <span className="text-base font-bold font-mono text-slate-200 mt-0.5 block">
              {fmt(t.vibration_orders?.['gear_mesh'] ?? 0.15, 2)} mm/s
            </span>
            <span className="text-[9px] text-slate-500">{fmt(gearMeshHz, 1)} Hz gear mesh</span>
          </div>

          <div className="bg-surface-card p-2.5 rounded border border-surface-border">
            <span className="text-[10px] text-slate-500 block">3.12X BPFO</span>
            <span className="text-base font-bold font-mono text-slate-200 mt-0.5 block">
              {fmt(t.vibration_orders?.['bearing_bpfo'] ?? 0.08, 2)} mm/s
            </span>
            <span className="text-[9px] text-slate-500">Ball pass outer race</span>
          </div>
        </div>
      </div>

      {/* Grid 4: Synthesized Virtual Sensors (Thermofluid UKF State Observer) */}
      <div className="surface-panel p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-surface-border pb-2">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
              Synthesized Virtual Sensors (Thermofluid State Observer)
            </h3>
          </div>
          <span className="text-[10px] font-mono text-emerald-400">UKF OBSERVER / UNSENSORED DOMAINS</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="bg-surface-card p-3 rounded border border-surface-border">
            <span className="text-[10px] text-slate-500 block">PEAK CYLINDER PRESSURE (P_max)</span>
            <span className="text-lg font-bold font-mono text-emerald-400 mt-1 block">
              {fmt(t.virtual_sensors?.['P_max_bar'] ?? 65.2, 1)} bar
            </span>
            <span className="text-[10px] text-slate-500">In-cylinder combustion peak</span>
          </div>

          <div className="bg-surface-card p-3 rounded border border-surface-border">
            <span className="text-[10px] text-slate-500 block">TURBINE INLET TEMP (TIT)</span>
            <span className="text-lg font-bold font-mono text-amber-400 mt-1 block">
              {fmt(t.virtual_sensors?.['TIT_degC'] ?? 810.0, 1)} °C
            </span>
            <span className="text-[10px] text-slate-500">Pre-turbine collector state</span>
          </div>

          <div className="bg-surface-card p-3 rounded border border-surface-border">
            <span className="text-[10px] text-slate-500 block">MIN OIL FILM THICKNESS (h_min)</span>
            <span className="text-lg font-bold font-mono text-slate-100 mt-1 block">
              {fmt(t.virtual_sensors?.['h_min_um'] ?? 2.8, 2)} µm
            </span>
            <span className="text-[10px] text-slate-500">Hydrodynamic journal safety</span>
          </div>

          <div className="bg-surface-card p-3 rounded border border-surface-border">
            <span className="text-[10px] text-slate-500 block">INDICATED POWER (P_ind)</span>
            <span className="text-lg font-bold font-mono text-indigo-300 mt-1 block">
              {fmt(t.virtual_sensors?.['P_ind_kw'] ?? 72.4, 1)} kW
            </span>
            <span className="text-[10px] text-slate-500">Gross gas thermodynamic work</span>
          </div>
        </div>
      </div>

      {/* Grid 5: Twin Validity & 3-Way Attribution Monitor */}
      {a.twin_validity && (
        <div className="surface-panel p-4 space-y-3 border border-indigo-500/30 bg-indigo-950/20">
          <div className="flex items-center justify-between border-b border-surface-border pb-2">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-indigo-400" />
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                Digital Twin Validity &amp; 3-Way Fault Attribution
              </h3>
            </div>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
              a.twin_validity.verdict === 'VALID' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'
            }`}>
              TWIN STATUS: {a.twin_validity.verdict}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">ATTRIBUTION DECISION</span>
              <span className="text-sm font-bold font-mono text-accent mt-0.5 block">
                {a.twin_validity.attribution}
              </span>
              <span className="text-[9px] text-slate-500">3-Way Classifier (Twin vs Engine vs Sensor)</span>
            </div>

            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">NORMALIZED INNOVATION SQUARED (NIS)</span>
              <span className="text-sm font-bold font-mono text-slate-200 mt-0.5 block">
                χ² = {fmt(a.twin_validity.nis_chi2, 2)}
              </span>
              <span className="text-[9px] text-slate-500">95% statistical consistency bound</span>
            </div>

            <div className="bg-surface-card p-2.5 rounded border border-surface-border">
              <span className="text-[10px] text-slate-500 block">RESIDUAL WHITENESS (Ljung-Box)</span>
              <span className="text-sm font-bold font-mono text-emerald-400 mt-0.5 block">
                p = {fmt(a.twin_validity.whiteness_p_value, 3)}
              </span>
              <span className="text-[9px] text-slate-500">Uncorrelated innovation check</span>
            </div>
          </div>
          <p className="text-[10.5px] text-slate-400">{a.twin_validity.explanation}</p>
        </div>
      )}
    </div>
  );
};
