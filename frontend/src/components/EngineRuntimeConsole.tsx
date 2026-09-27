import { useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, Check, ChevronDown, CircleHelp, Radio, RotateCcw, SlidersHorizontal, Zap } from 'lucide-react';
import { useEngineRuntime } from '../hooks/useEngineRuntime';

const number = (value: unknown, digits = 1) => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '—';
const title = (value: string) => value.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c: string) => c.toUpperCase());
const channelEvidence = (items: Array<string | [string, number]>) => items.map((item) => Array.isArray(item) ? `${item[0]} (${number(item[1], 2)}σ)` : item).join(', ');

export function EngineRuntimeConsole({ serverUrl }: { serverUrl: string }) {
  const runtime = useEngineRuntime(serverUrl);
  const [faultMode, setFaultMode] = useState('');
  const [cylinder, setCylinder] = useState(1);
  const [severity, setSeverity] = useState(0.8);
  const [throttle, setThrottle] = useState(70);
  const [altitude, setAltitude] = useState(12000);
  const [oat, setOat] = useState(10);
  const [notice, setNotice] = useState('');
  const { profile, frame } = runtime;
  const readings = useMemo(() => Object.entries(frame?.channels ?? {}).sort(([a], [b]) => a.localeCompare(b)), [frame]);
  const alarms = frame?.detection;
  const detectorEntries = Object.entries(alarms?.ratios ?? {}).sort((a, b) => b[1] - a[1]);
  const activeFaults = profile?.commanded_faults ?? [];
  useEffect(() => setFaultMode(''), [runtime.engineId]);
  const leverFields: Array<{ label: string; value: number; min: number; max: number; unit: string; set: (value: number) => void }> = [
    { label: 'Throttle', value: throttle, min: 0, max: 100, unit: '%', set: setThrottle },
    { label: 'Altitude', value: altitude, min: 0, max: 25000, unit: ' ft', set: setAltitude },
    { label: 'Outside air', value: oat, min: -40, max: 45, unit: ' °C', set: setOat },
  ];

  const run = async (fn: () => Promise<unknown>, success: string) => {
    try { await fn(); setNotice(success); setTimeout(() => setNotice(''), 3500); await runtime.refreshCatalog(); }
    catch (cause) { setNotice(cause instanceof Error ? cause.message : 'Command failed'); }
  };
  const inject = () => {
    if (!faultMode) return;
    void run(() => runtime.command('/faults', 'POST', { mode: faultMode, cylinder: profile?.faults.find((fault) => fault.mode === faultMode)?.per_cylinder ? cylinder : undefined, severity, ramp_sec: 8 }), `${title(faultMode)} injected as a manual scenario`);
  };
  const changeLever = (values: Record<string, number>) => void run(() => runtime.command('/levers', 'POST', values), 'Flight condition target updated');

  return <div className="space-y-4">
    <section className="surface-panel p-4 sm:p-5">
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-slate-500"><span className={`w-2 h-2 rounded-full ${runtime.connected ? 'bg-emerald-400' : 'bg-slate-600'}`} /> Ground health console <span className="text-slate-700">/</span> Multi-engine runtime</div>
          <h2 className="mt-2 text-xl sm:text-2xl font-semibold text-white">Engine condition, with evidence</h2>
          <p className="mt-1 text-sm text-slate-400">Live plant telemetry, calibrated residuals, and operator-controlled fault scenarios.</p>
        </div>
        <label className="relative flex items-center gap-3 rounded border border-surface-border bg-[#141417] px-3 py-2 min-w-[250px]">
          <span className="text-[10px] uppercase tracking-wider text-slate-500">Engine</span>
          <select value={runtime.engineId} onChange={(event) => void runtime.selectEngine(event.target.value)} className="flex-1 bg-transparent text-sm text-white outline-none appearance-none pr-6">
            {(runtime.catalog?.engines ?? []).map((engine) => <option key={engine.engine_id} value={engine.engine_id}>{engine.display_name || title(engine.engine_id)}</option>)}
          </select><ChevronDown className="w-4 h-4 text-slate-500 pointer-events-none absolute right-3" />
        </label>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-white/5 pt-3 text-[11px]">
        <span className={`px-2 py-1 rounded border ${runtime.connected ? 'text-emerald-300 border-emerald-900 bg-emerald-950/40' : 'text-amber-300 border-amber-900 bg-amber-950/30'}`}>{runtime.connected ? 'LIVE · 20 Hz' : 'CONNECTING'}</span>
        <span className="px-2 py-1 rounded border border-slate-700 text-slate-300">{frame?.source ?? 'PLANT'} source</span>
        <span className="px-2 py-1 rounded border border-slate-700 text-slate-300">{frame?.evidence_class ?? 'SIMULATION'} evidence</span>
        <span className="text-slate-500">{profile?.tail_id ?? 'Waiting for calibration'}</span>
        {profile && !profile.ready && <span className="text-amber-300">Profile calibrating</span>}
        {notice && <span className="ml-auto text-sky-300">{notice}</span>}
      </div>
      {runtime.error && <div className="mt-3 rounded border border-amber-900/70 bg-amber-950/20 p-3 text-sm text-amber-200">{runtime.error}. Check the backend connection in Settings.</div>}
    </section>

    <section aria-label="Fleet overview" className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-2">
      {runtime.fleet.map((member) => <button key={member.engine_id} onClick={() => void runtime.selectEngine(member.engine_id)} className={`surface-panel p-3 text-left transition-colors hover:bg-white/[0.04] ${runtime.engineId === member.engine_id ? 'border-sky-700/70 bg-sky-950/15' : ''}`}>
        <div className="flex items-center justify-between gap-2"><span className="truncate text-xs font-medium text-slate-200">{runtime.catalog?.engines.find((engine) => engine.engine_id === member.engine_id)?.display_name || title(member.engine_id)}</span><span className={`h-1.5 w-1.5 rounded-full ${!member.ready ? 'bg-slate-600' : member.confirmed ? 'bg-red-400' : member.raw_alarm ? 'bg-amber-400' : 'bg-emerald-400'}`} /></div>
        <div className="mt-2 text-[10px] text-slate-500">{member.ready ? `${number(member.rpm, 0)} rpm · ${number(member.max_cht, 0)}° CHT` : 'Calibrating profile'}</div>
        <div className="mt-1 text-[9px] uppercase tracking-wider text-slate-600">{runtime.engineId === member.engine_id ? 'Selected engine' : member.confirmed ? 'Confirmed anomaly' : member.raw_alarm ? 'Raw anomaly' : member.ready ? 'Monitoring' : 'Preparing'}</div>
      </button>)}
    </section>

    <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
      {[
        ['Engine speed', `${number(frame?.channels.rpm, 0)} rpm`, 'CRANK SPEED'],
        ['Cylinder head', `${number(Math.max(...(frame?.cht ?? [NaN])))} °C`, `MAX OF ${profile?.n_cylinders ?? '—'} CYLINDERS`],
        ['Exhaust gas', `${number(Math.max(...(frame?.egt ?? [NaN])))} °C`, 'MAX CYLINDER'],
        ['Detector state', !alarms ? 'Waiting' : alarms.confirmed ? 'Confirmed' : alarms.raw_alarm ? 'Review' : 'Nominal', alarms?.confirmed ? 'PERSISTENCE GATE' : 'TIER 0 · RESIDUALS'],
      ].map(([label, value, caption], index) => <div key={label} className={`surface-panel p-4 ${index === 3 && alarms?.confirmed ? 'surface-panel-critical' : ''}`}><div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div><div className="mt-2 text-xl sm:text-2xl font-semibold tabular-nums text-white">{value}</div><div className="mt-1 text-[10px] text-slate-500">{caption}</div></div>)}
    </div>

    <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-4">
      <section className="surface-panel p-4 sm:p-5">
        <div className="flex items-start justify-between"><div><h3 className="font-semibold text-white">Detector evidence</h3><p className="text-xs text-slate-500 mt-1">Live tier-0 score relative to its threshold. Above 1.0 indicates a raw alarm.</p></div><Activity className="w-4 h-4 text-slate-500" /></div>
        {detectorEntries.length ? <div className="mt-5 space-y-4">{detectorEntries.map(([name, ratio]) => <div key={name}><div className="flex justify-between text-xs"><span className="text-slate-300">{title(name)}</span><span className={ratio >= 1 ? 'text-amber-300 tabular-nums' : 'text-slate-400 tabular-nums'}>{number(ratio, 2)}× threshold</span></div><div className="mt-2 h-1.5 rounded bg-slate-800 overflow-hidden"><div className={`h-full rounded ${ratio >= 1 ? 'bg-amber-400' : 'bg-sky-500'}`} style={{ width: `${Math.min(100, Math.max(2, ratio * 35))}%` }} /></div></div>)}</div> : <div className="mt-6 rounded bg-white/[0.03] p-4 text-sm text-slate-400">{profile?.ready ? 'Waiting for first scored frame…' : 'Calibration is preparing the residual baseline.'}</div>}
        {alarms && <div className={`mt-5 flex gap-2 rounded border p-3 text-xs ${alarms.confirmed ? 'border-red-900 bg-red-950/20 text-red-200' : alarms.raw_alarm ? 'border-amber-900 bg-amber-950/20 text-amber-200' : 'border-emerald-900/70 bg-emerald-950/10 text-emerald-200'}`}>
          {alarms.confirmed ? <AlertTriangle className="w-4 h-4 shrink-0" /> : alarms.raw_alarm ? <CircleHelp className="w-4 h-4 shrink-0" /> : <Check className="w-4 h-4 shrink-0" />}
          <span>{alarms.confirmed ? 'Persistence confirmed anomaly' : alarms.raw_alarm ? 'Raw anomaly — persistence gate has not confirmed it' : 'No active residual alarm'}{alarms.top_channels.length ? ` · Leading channels: ${channelEvidence(alarms.top_channels)}` : ''}</span>
        </div>}
        {frame?.heavy && <div className="mt-4 rounded border border-indigo-900/60 bg-indigo-950/20 p-3"><div className="flex items-center justify-between"><div className="text-xs font-medium text-indigo-200">Selected-engine reservoir · tier 1 <span className="font-normal text-indigo-300/70">(readout scores, not probabilities)</span></div><span className="text-[10px] text-indigo-300">Candidate: {title(frame.heavy.label)}</span></div><div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2">{frame.heavy.classes.map((label, i) => <div key={label} className="rounded bg-black/20 p-2"><div className="truncate text-[10px] text-slate-400">{title(label)}</div><div className="mt-1 text-xs text-white tabular-nums">{number(frame.heavy?.scores[i], 3)}</div></div>)}</div></div>}
        {!frame?.heavy && <div className="mt-4 text-[11px] text-slate-500">Tier 1 {profile?.heavy_ready ? 'warming on selection' : 'not ready'} · randomized reservoir classification, not a connectome model.</div>}
      </section>

      <section className="surface-panel p-4 sm:p-5">
        <div className="flex items-start justify-between"><div><h3 className="font-semibold text-white">Scenario controls</h3><p className="text-xs text-slate-500 mt-1">Commands change the simulated plant and are marked MANUAL.</p></div><SlidersHorizontal className="w-4 h-4 text-slate-500" /></div>
        <div className="mt-4 space-y-3">
          {leverFields.map((field) => <label key={field.label} className="block"><span className="flex justify-between text-xs text-slate-400"><span>{field.label}</span><span className="tabular-nums text-slate-200">{field.value}{field.unit}</span></span><input className="mt-2 w-full" type="range" min={field.min} max={field.max} value={field.value} onChange={(e) => field.set(Number(e.target.value))} onPointerUp={() => changeLever({ throttle_pct: throttle, altitude_ft: altitude, oat_c: oat })} onKeyUp={(e) => { if (e.key.startsWith('Arrow')) changeLever({ throttle_pct: throttle, altitude_ft: altitude, oat_c: oat }); }} /></label>)}
          <button onClick={() => changeLever({ throttle_pct: throttle, altitude_ft: altitude, oat_c: oat })} className="w-full rounded border border-slate-700 px-3 py-2 text-xs text-slate-200 hover:bg-white/5">Apply flight conditions</button>
        </div>
        <div className="mt-5 border-t border-white/5 pt-4">
          <div className="text-xs font-medium text-slate-200">Inject a profile-valid fault</div>
          <div className="mt-2 flex gap-2">
            <select value={faultMode} onChange={(e) => setFaultMode(e.target.value)} className="min-w-0 flex-1 rounded border border-surface-border bg-[#141417] px-2 py-2 text-xs text-slate-200"><option value="">Choose fault…</option>{profile?.faults.map((fault) => <option key={fault.mode} value={fault.mode}>{title(fault.mode)}</option>)}</select>
            {profile?.faults.find((fault) => fault.mode === faultMode)?.per_cylinder && <select value={cylinder} onChange={(e) => setCylinder(Number(e.target.value))} className="rounded border border-surface-border bg-[#141417] px-2 text-xs text-slate-200">{Array.from({ length: profile.n_cylinders }, (_, i) => <option key={i + 1} value={i + 1}>Cyl {i + 1}</option>)}</select>}
          </div>
          {faultMode && <div className="mt-2 flex items-center justify-between gap-2"><span className="text-[10px] text-slate-500">{profile?.faults.find((fault) => fault.mode === faultMode)?.description} · {profile?.faults.find((fault) => fault.mode === faultMode)?.scalar_visible ? 'scalar-visible' : 'waveform-only'}</span><span className="text-[10px] text-slate-400">{Math.round(severity * 100)}%</span></div>}
          <input aria-label="Fault severity" className="mt-2 w-full" type="range" min="0.1" max="1" step="0.05" value={severity} onChange={(e) => setSeverity(Number(e.target.value))} />
          <button disabled={!faultMode || !runtime.connected} onClick={inject} className="mt-2 w-full rounded bg-amber-500/10 border border-amber-700/60 px-3 py-2 text-xs font-medium text-amber-200 disabled:opacity-40 hover:bg-amber-500/20"><Zap className="inline w-3.5 h-3.5 mr-1.5" />Inject scenario</button>
          {activeFaults.length > 0 && <div className="mt-3 rounded border border-amber-900/70 bg-amber-950/15 p-2.5"><div className="flex items-center justify-between text-[11px] text-amber-200"><span>Manual scenarios active</span><button title="Clear injected faults" onClick={() => void run(() => runtime.command('/faults', 'DELETE'), 'Manual scenarios cleared')} className="flex items-center gap-1 text-amber-100"><RotateCcw className="w-3 h-3" /> Clear</button></div><div className="mt-1 text-[10px] text-slate-400">{activeFaults.map((fault) => `${title(fault.mode)}${fault.cylinder ? ` · cyl ${fault.cylinder}` : ''}`).join('  /  ')}</div></div>}
        </div>
      </section>
    </div>

    <section className="surface-panel p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3"><div><h3 className="font-semibold text-white">Live engine channels</h3><p className="text-xs text-slate-500 mt-1">Profile-provided stream · values are simulation evidence in this prototype</p></div><Radio className="w-4 h-4 text-slate-500" /></div>
      {readings.length ? <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">{readings.map(([name, value]) => { const unit = runtime.schema?.channels.find((channel) => channel.name === name)?.unit; return <div key={name} className="rounded border border-white/[0.06] bg-black/10 px-3 py-2"><div className="truncate text-[10px] text-slate-500" title={name}>{name.replace(/_/g, ' ')}</div><div className="mt-1 text-sm font-medium tabular-nums text-slate-200">{number(value, 2)}{unit ? <span className="ml-1 text-[10px] text-slate-500">{unit}</span> : null}</div></div>; })}</div> : <div className="mt-4 text-sm text-slate-500">Waiting for calibrated engine frames…</div>}
    </section>
    <div className="flex items-start gap-2 px-1 text-[10px] leading-relaxed text-slate-600"><CircleHelp className="w-3.5 h-3.5 shrink-0 mt-0.5" /><span>This console currently runs virtual plant data. Tier 0 publishes residual anomaly evidence; tier 1 is a randomized reservoir classifier warmed for the selected engine. High-rate waveform sensing, Bayesian diagnosis, prognostics, and physical aircraft links exist as separate backend modules or experiments and are not represented here as live functions.</span></div>
  </div>;
}
