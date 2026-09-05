import React from 'react';
import { FunctionSquare, ChevronRight } from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';

interface CalculationsPanelProps {
  state: UnifiedTelemetryState;
}

const DIVISORS: Record<string, number> = {
  d_CHT_1: 4.0, d_CHT_2: 4.0, d_CHT_3: 4.0, d_CHT_4: 4.0,
  d_EGT_1: 15.0, d_EGT_2: 15.0, d_EGT_3: 15.0, d_EGT_4: 15.0,
  d_OIL_PRESS: 0.30, d_OIL_TEMP: 5.0, d_FUEL_FLOW: 1.5,
  d_MAP: 3.0, d_VIB_RMS: 0.25, d_BUS_VOLTAGE: 0.35,
};

const fmt = (v: number, d = 2) => (Number.isFinite(v) ? v.toFixed(d) : '--');

const Formula: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="font-mono text-[12px] leading-relaxed text-accent bg-black/25 border border-surface-border px-3 py-2">
    {children}
  </div>
);

const CalcCard: React.FC<{
  step: string;
  title: string;
  purpose: string;
  formula: React.ReactNode;
  inputs: { label: string; value: string }[];
  result: { label: string; value: string; tone: 'nominal' | 'warning' | 'critical' | 'accent' };
}> = ({ step, title, purpose, formula, inputs, result }) => {
  const toneClass = {
    nominal: 'text-success border-success-muted bg-success-dim',
    warning: 'text-warning border-warning-muted bg-warning-dim',
    critical: 'text-critical border-critical-muted bg-critical-dim',
    accent: 'text-accent border-accent-muted bg-accent-dim',
  }[result.tone];

  return (
    <div className="border border-surface-border bg-surface-card p-3.5 space-y-2.5 flex flex-col">
      <div className="flex items-start gap-2">
        <span className="text-[10px] font-mono text-slate-600 mt-0.5 shrink-0">{step}</span>
        <div>
          <h4 className="text-xs font-semibold text-slate-100">{title}</h4>
          <p className="text-[10.5px] text-slate-500 leading-snug">{purpose}</p>
        </div>
      </div>

      {formula}

      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
        {inputs.map((inp) => (
          <div key={inp.label} className="flex justify-between gap-2 border-b border-surface-border/50 py-0.5">
            <span className="text-slate-500">{inp.label}</span>
            <span className="font-mono text-slate-300">{inp.value}</span>
          </div>
        ))}
      </div>

      <div className={`mt-auto flex items-center justify-between px-2.5 py-1.5 border text-xs font-medium ${toneClass}`}>
        <span className="flex items-center gap-1"><ChevronRight className="w-3 h-3" />{result.label}</span>
        <span className="font-mono font-semibold">{result.value}</span>
      </div>
    </div>
  );
};

export const CalculationsPanel: React.FC<CalculationsPanelProps> = ({ state }) => {
  const t = state.telemetry;
  const a = state.analytics;
  const res = a.residuals || {};

  const zScores = Object.entries(DIVISORS).map(([key, div]) => Math.abs(res[key] ?? 0) / div);
  const zMax = zScores.length ? Math.max(...zScores) : 0;
  const zRms = zScores.length ? Math.sqrt(zScores.reduce((s, z) => s + z * z, 0) / zScores.length) : 0;
  const zComposite = 0.65 * zMax + 0.35 * zRms;
  const computedAnomaly = 1 - Math.exp(-0.45 * zComposite);

  const anomalyTone = a.anomaly_score >= 0.65 ? 'critical' : a.anomaly_score >= 0.35 ? 'warning' : 'nominal';

  const dCht2 = res.d_CHT_2 ?? 0;
  const expectedCht2 = t.CHT_2 - dCht2;

  const sanity = a.sensor_sanity;
  const sanityTone = sanity?.all_sensors_valid === false ? 'warning' : 'nominal';

  const planned = a.planned_sortie_hours ?? 18.0;
  const safetyMargin = 2.0;
  const p10 = a.rul_p10_hours;
  const goNoGoTone = a.go_no_go === 'GO' ? 'nominal' : a.go_no_go === 'CAUTION' ? 'warning' : 'critical';

  return (
    <div className="surface-panel p-4 sm:p-5 space-y-4">
      <div className="flex items-center gap-2.5 border-b border-surface-border pb-3">
        <div className="w-7 h-7 bg-accent-dim flex items-center justify-center text-accent">
          <FunctionSquare className="w-3.5 h-3.5" />
        </div>
        <div>
          <h2 className="text-xs font-semibold text-white">Detection Logic & Prognostic Calculations</h2>
          <p className="text-[11px] text-slate-500">The four calculations that turn raw residuals into the Go/No-Go certification</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <CalcCard
          step="01"
          title="Channel Z-Score & Composite Anomaly Score"
          purpose="Normalizes each of the 14 physics residuals by its flight tolerance, then blends peak stress with whole-engine RMS stress."
          formula={
            <Formula>
              z_composite = 0.65·z_max + 0.35·z_rms &nbsp;→&nbsp; score = 1 − exp(−0.45·z_composite)
            </Formula>
          }
          inputs={[
            { label: 'z_max (worst channel)', value: `${fmt(zMax)}σ` },
            { label: 'z_rms (14-channel)', value: `${fmt(zRms)}σ` },
            { label: 'z_composite', value: `${fmt(zComposite)}σ` },
            { label: 'Regime bands', value: '<0.35 / 0.35–0.65 / ≥0.65' },
          ]}
          result={{ label: 'Composite anomaly score', value: `${(a.anomaly_score * 100).toFixed(1)}% (calc. ${(computedAnomaly * 100).toFixed(1)}%)`, tone: anomalyTone }}
        />

        <CalcCard
          step="02"
          title="Sensor Sanity — Physical Ramp vs. Electrical Artifact"
          purpose="Rejects thermocouple open-circuits and frozen ADCs before they can masquerade as an engine fault (DRDO PS-26054 req. #4)."
          formula={
            <Formula>
              dT/dt ≤ 1.5°C/s = real thermal ramp
              <br />
              Δ&gt;10°C/50ms or variance&lt;floor = sensor fault
            </Formula>
          }
          inputs={[
            { label: 'All channels valid', value: sanity?.all_sensors_valid === false ? 'NO' : 'YES' },
            { label: 'Failed channels', value: sanity?.failed_channels?.length ? sanity.failed_channels.join(', ') : 'none' },
            { label: 'Anomaly suppressed', value: sanity?.suppressed_anomaly ? 'YES — sensor fault masked' : 'no' },
            { label: 'Monitored channels', value: '14 (rate + frozen-ADC + cross-correlation)' },
          ]}
          result={{ label: 'Sensor sanity advisory', value: sanity?.all_sensors_valid === false ? `${sanity.failed_channels.length} FAILED` : 'ALL VALID', tone: sanityTone }}
        />

        <CalcCard
          step="03"
          title="Cylinder Head Thermal Equilibrium"
          purpose="Physics-shadow baseline: heat generated by fuel flow and RPM vs. convective cooling from airspeed and air density."
          formula={
            <Formula>
              CHT_expected = OAT + 75 + 35·(heat_gen / heat_dissip), heat_dissip ∝ ρ_ratio·TAS
            </Formula>
          }
          inputs={[
            { label: 'OAT (ambient)', value: `${fmt(t.OAT_C, 1)}°C` },
            { label: 'True airspeed (cooling)', value: `${fmt(t.TAS_KNOTS, 0)} kt` },
            { label: 'Engine RPM', value: fmt(t.ENGINE_RPM, 0) },
            { label: 'CHT #2 actual', value: `${fmt(t.CHT_2, 1)}°C` },
          ]}
          result={{
            label: 'CHT #2 physics-expected',
            value: `${fmt(expectedCht2, 1)}°C (Δ ${dCht2 > 0 ? '+' : ''}${fmt(dCht2, 1)}°C)`,
            tone: Math.abs(dCht2) > 20 ? 'critical' : Math.abs(dCht2) > 8 ? 'warning' : 'nominal',
          }}
        />

        <CalcCard
          step="04"
          title="Probabilistic Go / No-Go Certification"
          purpose="Compares the conservative p10 RUL bound (500-sample Monte Carlo) of the limiting component against the planned sortie duration."
          formula={
            <Formula>
              NO-GO if T_planned &gt; RUL_p10
              <br />
              CAUTION if T_planned &gt; RUL_p10 − margin, else GO
            </Formula>
          }
          inputs={[
            { label: 'Planned sortie (T_planned)', value: `${fmt(planned, 1)} h` },
            { label: 'Safety margin', value: `${fmt(safetyMargin, 1)} h` },
            { label: 'Limiting component', value: a.limiting_component || 'none (no active trend)' },
            { label: 'RUL p50 (median)', value: `${a.rul_p50_hours >= 500 ? '>500' : fmt(a.rul_p50_hours, 1)} h` },
          ]}
          result={{ label: `RUL p10 (${a.limiting_component ? 'conservative' : 'no trend'})`, value: `${p10 >= 500 ? '>500' : fmt(p10, 1)} h → ${a.go_no_go}`, tone: goNoGoTone }}
        />
      </div>

      <p className="text-[10px] text-slate-600 pt-1 border-t border-surface-border">
        Not shown here to keep the instrument panel legible: AIC-based model selection (linear / exponential / power-law) across three trend
        windows (2 / 10 / 30 min), and the 500-iteration Monte Carlo parameter perturbation that produces the p10/p50/p90 spread above —
        see the Prognostics &amp; Mission Readiness panel for the resulting per-component RUL table.
      </p>
    </div>
  );
};
