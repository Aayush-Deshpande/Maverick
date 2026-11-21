import { useState } from 'react';
import { NO_DATA, num } from '../utils/format';
import { channelLabel, useLabels } from '../utils/labels';
import InfoTooltip from './InfoTooltip';

type TwinParam = { name: string; location: string; mean: number; ci: [number, number]; healthy: boolean };
type Props = {
  residuals: Record<string, number> | undefined;
  twin: { nis?: number; params?: TwinParam[] } | null | undefined;
  virtualSensors: Record<string, number> | undefined;
  vibration: Record<string, number> | undefined;
};

const Z_FULL = 6;                                         // bar length scale: |z| = 6 sigma fills the bar
const TOP_N = 10;

const VIRTUAL_LABELS: Record<string, [string, string]> = {
  P_max_bar: ['Peak cylinder pressure', 'bar'],
  h_min_um: ['Min. bearing oil film', 'µm'],
  P_ind_kw: ['Indicated power', 'kW'],
  TIT_degC: ['Turbine inlet temperature', '°C'],
};

/** Propulsion engineer view (M6-03): measured-vs-model residuals in noise sigmas, the twin's health-parameter
 *  estimates with their intervals, virtual sensors (model estimates, labelled VIRTUAL) and vibration orders. */
export default function EngineerPanel({ residuals, twin, virtualSensors, vibration }: Props) {
  const [all, setAll] = useState(false);
  const labels = useLabels();
  const res = Object.entries(residuals ?? {}).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const shown = all ? res : res.slice(0, TOP_N);
  const params = twin?.params ?? [];
  return (
    <section className="surface-panel p-4 sm:p-5 rounded-sm">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold text-white tracking-tight">Twin and residuals</h3>
        <InfoTooltip
          title="Engine Twin & Mismatch Tracking"
          content="Compares live sensor measurements against what our healthy digital engine expects. If a reading drifts unusually far from normal, it highlights the mismatch so engineers can catch hidden problems early."
          width={280}
        />
      </div>
      <div className="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-4 text-xs font-mono">
        <div>
          <div className="flex items-center gap-1.5 text-slate-300">
            <span>Residuals, measured minus engine model (σ)</span>
            <InfoTooltip
              title="Sensor Deviation from Expected"
              content="Shows how many steps away each sensor reading is from what a healthy engine should show. A small bar means normal operation; a bar stretching past 3 indicates an unusual reading that deserves attention."
              width={280}
            />
          </div>
          {shown.length ? <ul className="mt-2 space-y-1.5">{shown.map(([ch, z]) => (
            <li key={ch} className="grid grid-cols-[minmax(7rem,14rem)_1fr_3.5rem] items-center gap-2">
              <span className="truncate text-slate-400" title={ch}>{channelLabel(labels, ch)}</span>
              <span className="relative h-1.5 bg-surface border border-surface-border rounded-full overflow-hidden">
                <span className="absolute top-0 bottom-0 left-1/2 w-px bg-slate-500" />
                <span className="absolute top-0 bottom-0 bg-slate-500"
                  style={z >= 0 ? { left: '50%', width: `${Math.min(50, (z / Z_FULL) * 50)}%` } : { right: '50%', width: `${Math.min(50, (-z / Z_FULL) * 50)}%` }} />
              </span>
              <span className="text-right tabular-nums text-slate-200">{num(z, 1)}</span>
            </li>
          ))}</ul> : <div className="mt-2 text-slate-500">{NO_DATA} (detector not calibrated yet)</div>}
          {res.length > TOP_N && <button type="button" onClick={() => setAll(!all)} className="mt-2 text-slate-400 hover:underline">
            {all ? `Show top ${TOP_N}` : `Show all ${res.length}`}</button>}
        </div>
        <div>
          <div className="flex items-center gap-1.5 text-slate-300">
            <span>Health parameters (twin estimate, 1 = nominal) · NIS {twin?.nis == null ? NO_DATA : num(twin.nis, 2)}</span>
            <InfoTooltip
              title="Internal Health & Model Match"
              content="Estimates the internal health of the cooling system and cylinders. A value near 1.0 means brand new condition; values below 0.75 indicate wear or cooling loss. The match score confirms whether the digital twin and real engine are in agreement."
              width={280}
            />
          </div>
          {params.length ? <table className="mt-2 w-full text-left">
            <thead className="text-slate-500"><tr><th className="py-0.5">Parameter</th><th>Estimate</th><th>Interval</th><th /></tr></thead>
            <tbody>{params.map((p) => (
              <tr key={`${p.name}-${p.location}`} className="text-slate-300 tabular-nums">
                <td className="py-0.5">{p.name} · {p.location}</td><td>{num(p.mean, 3)}</td>
                <td className="text-slate-500">{num(p.ci[0], 2)}–{num(p.ci[1], 2)}</td>
                <td>{p.healthy ? '' : 'outside nominal'}</td>
              </tr>
            ))}</tbody>
          </table> : <div className="mt-2 text-slate-500">{NO_DATA}</div>}
          <div className="mt-4 flex items-center gap-1.5 text-slate-300">
            <span>Virtual sensors <span className="text-slate-500">(VIRTUAL: model estimates, not measured)</span></span>
            <InfoTooltip
              title="Calculated Hidden Sensors"
              content="Key engine variables that physical sensors cannot measure directly without damaging the engine. Our digital twin calculates them in real time: peak cylinder firing pressure, bearing oil thickness, total engine power, and turbocharger heat."
              width={280}
            />
          </div>
          {Object.keys(virtualSensors ?? {}).length ? <div className="mt-1 space-y-0.5">{Object.entries(virtualSensors!).map(([k, v]) => (
            <div key={k} className="text-slate-400">{VIRTUAL_LABELS[k]?.[0] ?? k} <span className="text-slate-200 tabular-nums">{num(v, 2)}</span> {VIRTUAL_LABELS[k]?.[1] ?? ''}</div>
          ))}</div> : <div className="mt-1 text-slate-500">{NO_DATA}</div>}
          <div className="mt-4 flex items-center gap-1.5 text-slate-300">
            <span>Vibration orders (mm/s)</span>
            <InfoTooltip
              title="Engine Vibration Patterns"
              content="Tracks vibration pulses matched to engine rotation speed: 0.5X reveals valve or camshaft issues, 1.0X points to an unbalanced spinning shaft or propeller, and 2.0X monitors the smooth firing pulse of the engine cylinders."
              width={280}
            />
          </div>
          {Object.keys(vibration ?? {}).length ? <div className="mt-1 grid grid-cols-3 gap-x-3 gap-y-0.5">{Object.entries(vibration!).map(([k, v]) => (
            <div key={k} className="text-slate-400">{k} <span className="text-slate-200 tabular-nums">{num(v, 3)}</span></div>
          ))}</div> : <div className="mt-1 text-slate-500">{NO_DATA}</div>}
        </div>
      </div>
    </section>
  );
}
