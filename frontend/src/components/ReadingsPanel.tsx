import React from 'react';
import { Activity, Gauge } from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';

interface ReadingsPanelProps {
  state: UnifiedTelemetryState;
}

type Status = 'NOMINAL' | 'WARNING' | 'CRITICAL';

const statusColor: Record<Status, string> = {
  NOMINAL: 'text-slate-200',
  WARNING: 'text-warning',
  CRITICAL: 'text-critical',
};

const statusDot: Record<Status, string> = {
  NOMINAL: 'bg-success/70',
  WARNING: 'bg-warning',
  CRITICAL: 'bg-critical',
};

/** One physics-modeled residual channel: doc §2 nominal range + §4.1 z-score divisor. */
type ChannelTest = (actual: number, expected: number, residual: number, z: number) => boolean;

interface ChannelSpec {
  key: string;          // residuals dict key, e.g. "d_CHT_2"
  label: string;
  actual: number;
  unit: string;
  divisor: number;      // z-score normalisation divisor (doc §4.1)
  criticalTest: ChannelTest;
  warningTest: ChannelTest;
  nominalRange: string;
}

const fmt = (v: number, d = 1) => (Number.isFinite(v) ? v.toFixed(d) : '--');

const StatChip: React.FC<{ label: string; value: string; sub?: string }> = ({ label, value, sub }) => (
  <div className="border border-surface-border bg-surface-card px-3 py-2 flex flex-col gap-0.5 min-w-0">
    <span className="text-[9px] uppercase tracking-wider text-slate-500 truncate">{label}</span>
    <span className="text-sm font-mono font-semibold text-slate-100 truncate">{value}</span>
    {sub && <span className="text-[9px] font-mono text-slate-500 truncate">{sub}</span>}
  </div>
);

const SectionLabel: React.FC<{ index: string; title: string; caption: string }> = ({ index, title, caption }) => (
  <div className="flex items-baseline gap-2 mb-2">
    <span className="text-[10px] font-mono text-slate-600">{index}</span>
    <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-300">{title}</h3>
    <span className="text-[10px] text-slate-600">— {caption}</span>
  </div>
);

export const ReadingsPanel: React.FC<ReadingsPanelProps> = ({ state }) => {
  const t = state.telemetry;
  const res = state.analytics.residuals || {};

  const channels: ChannelSpec[] = [
    { key: 'd_CHT_1', label: 'CHT #1', actual: t.CHT_1, unit: '°C', divisor: 4.0, nominalRange: '85 – 110',
      criticalTest: (a) => a > 135, warningTest: (a, _e, _r, z) => z >= 1.0 || a > 118 },
    { key: 'd_CHT_2', label: 'CHT #2', actual: t.CHT_2, unit: '°C', divisor: 4.0, nominalRange: '85 – 110',
      criticalTest: (a) => a > 135, warningTest: (a, _e, _r, z) => z >= 1.0 || a > 118 },
    { key: 'd_CHT_3', label: 'CHT #3', actual: t.CHT_3, unit: '°C', divisor: 4.0, nominalRange: '85 – 110',
      criticalTest: (a) => a > 135, warningTest: (a, _e, _r, z) => z >= 1.0 || a > 118 },
    { key: 'd_CHT_4', label: 'CHT #4', actual: t.CHT_4, unit: '°C', divisor: 4.0, nominalRange: '85 – 110',
      criticalTest: (a) => a > 135, warningTest: (a, _e, _r, z) => z >= 1.0 || a > 118 },
    { key: 'd_EGT_1', label: 'EGT #1', actual: t.EGT_1, unit: '°C', divisor: 15.0, nominalRange: '740 – 820',
      criticalTest: (a, _e, r) => a > 880 || Math.abs(r) > 65, warningTest: (_a, _e, _r, z) => z >= 1.0 },
    { key: 'd_EGT_2', label: 'EGT #2', actual: t.EGT_2, unit: '°C', divisor: 15.0, nominalRange: '740 – 820',
      criticalTest: (a, _e, r) => a > 880 || Math.abs(r) > 65, warningTest: (_a, _e, _r, z) => z >= 1.0 },
    { key: 'd_EGT_3', label: 'EGT #3', actual: t.EGT_3, unit: '°C', divisor: 15.0, nominalRange: '740 – 820',
      criticalTest: (a, _e, r) => a > 880 || Math.abs(r) > 65, warningTest: (_a, _e, _r, z) => z >= 1.0 },
    { key: 'd_EGT_4', label: 'EGT #4', actual: t.EGT_4, unit: '°C', divisor: 15.0, nominalRange: '740 – 820',
      criticalTest: (a, _e, r) => a > 880 || Math.abs(r) > 65, warningTest: (_a, _e, _r, z) => z >= 1.0 },
    { key: 'd_OIL_PRESS', label: 'Oil Pressure', actual: t.OIL_PRESS, unit: 'bar', divisor: 0.30, nominalRange: '2.0 – 5.0',
      criticalTest: (a) => a < 2.0, warningTest: (a, _e, _r, z) => z >= 1.0 || a < 2.4 },
    { key: 'd_OIL_TEMP', label: 'Oil Temperature', actual: t.OIL_TEMP, unit: '°C', divisor: 5.0, nominalRange: '75 – 110',
      criticalTest: (a) => a > 130, warningTest: (a, _e, _r, z) => z >= 1.0 || a > 115 },
    { key: 'd_FUEL_FLOW', label: 'Fuel Flow', actual: t.FUEL_FLOW, unit: 'L/hr', divisor: 1.5, nominalRange: '14.0 – 25.0',
      criticalTest: (_a, e, r) => e > 0.1 && Math.abs(r) / e > 0.20, warningTest: (_a, _e, _r, z) => z >= 1.0 },
    { key: 'd_MAP', label: 'Manifold Press.', actual: t.MAP, unit: 'kPa', divisor: 3.0, nominalRange: '80 – 100',
      criticalTest: (_a, _e, r) => Math.abs(r) > 8.0, warningTest: (_a, _e, _r, z) => z >= 1.0 },
    { key: 'd_VIB_RMS', label: 'Gearbox Vibration', actual: t.VIB_GEARBOX_RMS, unit: 'mm/s', divisor: 0.25, nominalRange: '0.20 – 1.50',
      criticalTest: (a) => a > 1.80, warningTest: (a, _e, _r, z) => z >= 1.0 || a > 1.5 },
    { key: 'd_BUS_VOLTAGE', label: 'DC Bus Voltage', actual: t.BUS_VOLTAGE, unit: 'V', divisor: 0.35, nominalRange: '13.8 – 14.2',
      criticalTest: (a) => a < 12.8, warningTest: (a, _e, _r, z) => z >= 1.0 || a < 13.5 },
  ];

  const rows = channels.map((c) => {
    const residual = res[c.key] ?? 0;
    const expected = c.actual - residual;
    const z = Math.abs(residual) / c.divisor;
    let status: Status = 'NOMINAL';
    if (c.criticalTest(c.actual, expected, residual, z)) status = 'CRITICAL';
    else if (c.warningTest(c.actual, expected, residual, z)) status = 'WARNING';
    return { ...c, residual, expected, z, status };
  });

  const thermalRows = rows.filter((r) => r.key.includes('CHT') || r.key.includes('EGT'));
  const fluidRows = rows.filter((r) => !r.key.includes('CHT') && !r.key.includes('EGT'));

  const sanity = state.analytics.sensor_sanity;
  const anomalyScore = state.analytics.anomaly_score;

  const renderChannelTable = (list: typeof rows) => (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="text-[9px] uppercase tracking-wider text-slate-500 border-b border-surface-border">
            <th className="text-left font-medium py-1.5 pr-2">Channel</th>
            <th className="text-right font-medium py-1.5 px-2">
              Actual<div className="text-[8px] text-slate-600 normal-case">sensor reading</div>
            </th>
            <th className="text-right font-medium py-1.5 px-2">
              Expected<div className="text-[8px] text-slate-600 normal-case">physics baseline</div>
            </th>
            <th className="text-right font-medium py-1.5 px-2">
              Δ Residual<div className="text-[8px] text-slate-600 normal-case">actual − expected</div>
            </th>
            <th className="text-right font-medium py-1.5 px-2">
              Z-score<div className="text-[8px] text-slate-600 normal-case">|Δ| / tolerance</div>
            </th>
            <th className="text-left font-medium py-1.5 pl-2">
              Status<div className="text-[8px] text-slate-600 normal-case">vs. nominal range</div>
            </th>
          </tr>
        </thead>
        <tbody>
          {list.map((r) => (
            <tr key={r.key} className="border-b border-surface-border/60 last:border-0 hover:bg-white/[0.02]">
              <td className="py-1.5 pr-2 font-medium text-slate-300">
                {r.label}
                <span className="text-slate-600 font-mono text-[10px] ml-1">({r.nominalRange} {r.unit})</span>
              </td>
              <td className={`text-right py-1.5 px-2 font-mono font-semibold ${statusColor[r.status]}`}>
                {fmt(r.actual, r.unit === 'bar' ? 2 : r.unit === 'mm/s' ? 2 : 1)} <span className="text-slate-600 font-normal">{r.unit}</span>
              </td>
              <td className="text-right py-1.5 px-2 font-mono text-slate-500">
                {fmt(r.expected, r.unit === 'bar' ? 2 : r.unit === 'mm/s' ? 2 : 1)}
              </td>
              <td className="text-right py-1.5 px-2 font-mono text-slate-400">
                {r.residual > 0 ? '+' : ''}{fmt(r.residual, r.unit === 'bar' ? 2 : r.unit === 'mm/s' ? 2 : 1)}
              </td>
              <td className="text-right py-1.5 px-2 font-mono text-slate-400">
                {r.z.toFixed(2)}σ
              </td>
              <td className="py-1.5 pl-2">
                <span className={`inline-flex items-center gap-1.5 text-[10px] font-medium ${statusColor[r.status]}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${statusDot[r.status]}`} />
                  {r.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="surface-panel p-4 sm:p-5 space-y-5">
      <div className="flex items-center justify-between border-b border-surface-border pb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-accent-dim flex items-center justify-center text-accent">
            <Activity className="w-3.5 h-3.5" />
          </div>
          <div>
            <h2 className="text-xs font-semibold text-white">Live Engine Readings</h2>
            <p className="text-[11px] text-slate-500">20 Hz sensor stream against the RotaxThermoModel physics baseline</p>
          </div>
        </div>
        <div className="flex items-center gap-3 text-[11px]">
          <span className="text-slate-500">
            Composite anomaly score:{' '}
            <span className={`font-mono font-semibold ${anomalyScore >= 0.65 ? 'text-critical' : anomalyScore >= 0.35 ? 'text-warning' : 'text-success'}`}>
              {(anomalyScore * 100).toFixed(1)}%
            </span>
          </span>
          <span className="text-slate-500">
            Sensor sanity:{' '}
            <span className={`font-mono font-semibold ${sanity?.all_sensors_valid === false ? 'text-critical' : 'text-success'}`}>
              {sanity?.all_sensors_valid === false ? `${sanity.failed_channels.length} FAILED` : 'ALL VALID'}
            </span>
          </span>
        </div>
      </div>

      {/* Group 1 — Raw flight & kinematic inputs */}
      <div>
        <SectionLabel index="01" title="Raw Flight & Kinematic Inputs" caption="drive the physics twin; not residual-checked" />
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-2">
          <StatChip label="Engine RPM" value={fmt(t.ENGINE_RPM, 0)} sub="crankshaft" />
          <StatChip label="Prop RPM" value={fmt(t.PROP_RPM, 0)} sub="i = 2.43" />
          <StatChip label="Throttle (TPS)" value={`${fmt(t.TPS, 0)}%`} sub="command" />
          <StatChip label="Altitude MSL" value={`${fmt(t.ALTITUDE_FT / 1000, 1)}k ft`} />
          <StatChip label="OAT" value={`${fmt(t.OAT_C, 1)}°C`} />
          <StatChip label="True Airspeed" value={`${fmt(t.TAS_KNOTS, 0)} kt`} />
          <StatChip label="Fuel Rail Press." value={`${fmt(t.FUEL_RAIL_P, 2)} bar`} />
          <StatChip label="Battery Current" value={`${t.BATTERY_CURRENT > 0 ? '+' : ''}${fmt(t.BATTERY_CURRENT, 1)} A`} />
          <StatChip label="FADEC Lane" value={t.FADEC_ACTIVE_LANE} />
          <StatChip label="Flight Phase" value={t.FLIGHT_PHASE.replace('_', ' ')} />
        </div>
      </div>

      {/* Group 2 — Physics-correlated channels (the 14-channel residual vector, doc §4.1) */}
      <div>
        <SectionLabel index="02" title="Thermal Channels — Actual vs. Physics-Expected" caption="8 of 14 residual-checked channels" />
        {renderChannelTable(thermalRows)}
      </div>

      <div>
        <SectionLabel index="03" title="Fluids, Pressure & Electrical — Actual vs. Physics-Expected" caption="remaining 6 of 14 residual-checked channels" />
        {renderChannelTable(fluidRows)}
      </div>

      <div className="pt-1 flex items-start gap-2 text-[10px] text-slate-600 border-t border-surface-border">
        <Gauge className="w-3 h-3 mt-0.5 shrink-0" />
        <span>
          Expected values are solved live by <span className="font-mono text-slate-500">RotaxThermoModel.compute_expected_state()</span> from
          altitude, OAT, throttle and airspeed — see the Detection Logic panel below for the composite anomaly formula built from these residuals.
        </span>
      </div>
    </div>
  );
};
