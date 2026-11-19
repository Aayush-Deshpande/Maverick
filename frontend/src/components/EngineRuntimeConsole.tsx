import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, AlertTriangle, Check, ChevronDown, CircleHelp, Compass, Play, Radio, RotateCcw, SlidersHorizontal, Users, Wrench, Zap } from 'lucide-react';
import { useEngineRuntime, type EngineFrame } from '../hooks/useEngineRuntime';
import { consumeDemoRequest } from '../demoIntent';

const number = (value: unknown, digits = 1) => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '—';
const title = (value: string) => value.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c: string) => c.toUpperCase());

/** Readable names for the runtime's channel keys. Unknown keys fall back to title case. */
const CHANNEL_LABELS: Record<string, string> = {
  alt: 'Altitude', oat: 'Outside air', rpm: 'Engine speed', map_kpa: 'Manifold pressure', fuel_flow: 'Fuel flow',
  fuel_t: 'Fuel temperature', oil_p: 'Oil pressure', oil_t: 'Oil temperature', bus_v: 'Bus voltage', throttle: 'Throttle',
  egt_spread: 'EGT spread', vib_rms: 'Vibration RMS', boost_kpa: 'Boost pressure', iat: 'Intake air temp',
};
/** Channels that carry no information in the virtual plant and only confuse a reader. */
const HIDDEN_CHANNELS = new Set(['batt_i']);
const channelLabel = (key: string) => {
  const cyl = key.match(/^(cht|egt)_(\d+)$/);
  if (cyl) return `${cyl[1].toUpperCase()} · cyl ${cyl[2]}`;
  return CHANNEL_LABELS[key] ?? title(key);
};
const channelEvidence = (items: Array<string | [string, number]>) => items.map((item) => Array.isArray(item) ? `${channelLabel(item[0])} (${number(item[1], 1)}σ)` : channelLabel(item)).join(', ');
/** Backend display names carry provenance in parentheses; keep the name, surface provenance as a tag. */
const engineName = (name?: string, id?: string) => {
  const raw = name || (id ? title(id) : '');
  const m = raw.match(/^(.*?)\s*\((parametrised|parameterised)[^)]*\)\s*$/i);
  return m ? { name: m[1], tag: 'Parameterised profile' } : { name: raw, tag: '' };
};

const DEMO_ENGINE = 'rotax_912is';
const DEMO_FAULT = 'OIL_PRESSURE_LOSS';
const DEMO_SECONDS = 75;
/** The runtime plays at 20x real time: a 400 s simulated ramp develops over ~20 s on screen. */
const DEMO_RAMP_SIM_SEC = 400;
const AUTO_CLEAR_MS = 120_000;
const DEMO_STEPS = ['Fault injected', 'Residual rising', 'Fault confirmed', 'Decision issued'];

function demoStep(frame: EngineFrame | null): number {
  if (!frame?.detection) return 0;
  const diagnosed = frame.diagnosis && frame.diagnosis.ata_chapter && frame.diagnosis.ata_chapter !== 'ATA 00-00';
  if (frame.detection.confirmed && diagnosed) return 3;
  if (frame.detection.confirmed) return 2;
  const lead = frame.detection.top_channels?.[0];
  const sigma = Array.isArray(lead) ? Math.abs(lead[1]) : 0;
  return frame.detection.raw_alarm || sigma >= 3 ? 1 : 0;
}

export function EngineRuntimeConsole({ serverUrl }: { serverUrl: string }) {
  const runtime = useEngineRuntime(serverUrl);
  const [faultMode, setFaultMode] = useState('');
  const [cylinder, setCylinder] = useState(1);
  const [severity, setSeverity] = useState(0.8);
  const [throttle, setThrottle] = useState(70);
  const [altitude, setAltitude] = useState(9000);
  const [oat, setOat] = useState(10);
  const [notice, setNotice] = useState('');
  const [demoStartedAt, setDemoStartedAt] = useState<number | null>(null);
  const [demoReached, setDemoReached] = useState(0);
  const [now, setNow] = useState(Date.now());
  const seededFor = useRef<string | null>(null);
  const clearTimer = useRef<number | undefined>(undefined);
  const { profile, frame } = runtime;
  const readings = useMemo(() => Object.entries(frame?.channels ?? {}).filter(([name]) => !HIDDEN_CHANNELS.has(name)).sort(([a], [b]) => a.localeCompare(b)), [frame]);
  const alarms = frame?.detection;
  const detectorEntries = Object.entries(alarms?.ratios ?? {}).sort((a, b) => b[1] - a[1]);
  const activeFaults = profile?.commanded_faults ?? [];
  const candidate = frame?.heavy?.label && frame.heavy.label !== 'NOMINAL' ? title(frame.heavy.label) : '';
  const demoActive = demoStartedAt !== null;
  const demoRemaining = demoActive ? Math.max(0, DEMO_SECONDS - Math.floor((now - demoStartedAt) / 1000)) : 0;

  useEffect(() => setFaultMode(''), [runtime.engineId]);

  // Start the flight-condition sliders from what the plant is actually flying, once per engine,
  // so the controls never disagree with the live readout.
  useEffect(() => {
    if (!frame || seededFor.current === runtime.engineId) return;
    seededFor.current = runtime.engineId;
    if (typeof frame.channels.alt === 'number') setAltitude(Math.round(frame.channels.alt / 500) * 500);
    if (typeof frame.channels.oat === 'number') setOat(Math.round(frame.channels.oat));
    if (typeof frame.channels.throttle === 'number') setThrottle(Math.round(frame.channels.throttle));
  }, [frame, runtime.engineId]);

  // Only frames produced after the demo's own fault count, so a previous scenario still draining
  // out of the stream can never tick the steps ahead.
  const demoFromT = useRef(Infinity);
  useEffect(() => {
    if (!demoActive || !frame || frame.engine_id !== DEMO_ENGINE || frame.t <= demoFromT.current) return;
    setDemoReached((reached) => Math.max(reached, demoStep(frame)));
  }, [frame, demoActive]);

  useEffect(() => {
    if (!demoActive) return;
    const id = window.setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, [demoActive]);

  const engineUrl = useCallback((id: string, path: string) => `${serverUrl}/api/engines/${encodeURIComponent(id)}${path}`, [serverUrl]);
  const clearFaults = useCallback(async (id: string) => { await fetch(engineUrl(id, '/faults'), { method: 'DELETE' }); }, [engineUrl]);

  // Shared demo backend: a fault this browser injects is cleared again after two minutes,
  // so the next visitor never lands on someone else's scenario.
  const scheduleAutoClear = useCallback((id: string) => {
    window.clearTimeout(clearTimer.current);
    clearTimer.current = window.setTimeout(() => { void clearFaults(id).then(() => runtime.refreshCatalog()); }, AUTO_CLEAR_MS);
  }, [clearFaults, runtime]);
  useEffect(() => () => window.clearTimeout(clearTimer.current), []);

  useEffect(() => {
    if (!demoActive || demoRemaining > 0) return;
    setDemoStartedAt(null);
    void clearFaults(DEMO_ENGINE).then(() => { setNotice('Demo finished · engine returned to nominal'); void runtime.refreshCatalog(); });
  }, [demoActive, demoRemaining, clearFaults, runtime]);

  const leverFields: Array<{ label: string; value: number; min: number; max: number; step: number; unit: string; set: (value: number) => void }> = [
    { label: 'Throttle', value: throttle, min: 0, max: 100, step: 1, unit: '%', set: setThrottle },
    { label: 'Altitude', value: altitude, min: 0, max: 25000, step: 500, unit: ' ft', set: setAltitude },
    { label: 'Outside air', value: oat, min: -40, max: 45, step: 1, unit: ' °C', set: setOat },
  ];

  const run = async (fn: () => Promise<unknown>, success: string) => {
    try { await fn(); setNotice(success); setTimeout(() => setNotice(''), 3500); await runtime.refreshCatalog(); }
    catch (cause) { setNotice(cause instanceof Error ? cause.message : 'Command failed'); }
  };
  const inject = () => {
    if (!faultMode) return;
    void run(async () => {
      await runtime.command('/faults', 'POST', { mode: faultMode, cylinder: profile?.faults.find((fault) => fault.mode === faultMode)?.per_cylinder ? cylinder : undefined, severity, ramp_sec: 8 });
      scheduleAutoClear(runtime.engineId);
    }, `${title(faultMode)} injected · auto-clears in 2 min`);
  };
  const changeLever = (values: Record<string, number>) => void run(() => runtime.command('/levers', 'POST', values), 'Flight condition target updated');

  const runDemo = async () => {
    setDemoReached(0);
    demoFromT.current = Infinity;
    setNow(Date.now());
    try {
      if (runtime.engineId !== DEMO_ENGINE) await runtime.selectEngine(DEMO_ENGINE);
      // Fresh sortie when the backend supports it; otherwise just clear earlier scenarios.
      const reset = await fetch(engineUrl(DEMO_ENGINE, '/reset'), { method: 'POST' }).catch(() => null);
      if (!reset?.ok) await clearFaults(DEMO_ENGINE);
      const response = await fetch(engineUrl(DEMO_ENGINE, '/faults'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mode: DEMO_FAULT, severity: 0.8, ramp_sec: DEMO_RAMP_SIM_SEC }) });
      if (!response.ok) throw new Error(`Demo fault was refused (${response.status})`);
      const injected = await response.json().catch(() => null) as { t?: number } | null;
      demoFromT.current = typeof injected?.t === 'number' ? injected.t : (frame?.t ?? 0) + 40;
      setDemoStartedAt(Date.now());
      scheduleAutoClear(DEMO_ENGINE);
      await runtime.refreshCatalog();
      document.querySelector('[aria-label="Guided demonstration"]')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (cause) { setNotice(cause instanceof Error ? cause.message : 'Demo could not start'); }
  };
  // Arriving from the landing's "Run the 60-second demo": start once the stream is live.
  // The request is consumed only when the demo can actually start, so a StrictMode remount or a
  // still-connecting stream never swallows it.
  useEffect(() => {
    if (!runtime.connected || !profile?.ready || demoActive) return;
    if (!consumeDemoRequest()) return;
    void runDemo();
  });

  const stopDemo = () => { setDemoStartedAt(null); void clearFaults(DEMO_ENGINE).then(() => { setNotice('Demo stopped · engine returned to nominal'); void runtime.refreshCatalog(); }); };

  const detectorState = !alarms ? ['Waiting', 'TIER 0 · RESIDUALS'] :
    alarms.confirmed ? ['Fault confirmed', candidate ? `TIER 1 · ${candidate.toUpperCase()}` : 'PERSISTENCE GATE PASSED'] :
    alarms.raw_alarm ? ['Anomaly', 'CONFIRMING · PERSISTENCE GATE'] :
    ['Nominal', 'TIER 0 · RESIDUALS'];

  return <div className="space-y-4">
    <section className="surface-panel p-4 sm:p-5">
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-[#68757a] font-mono"><span className={`w-2 h-2 rounded-full ${runtime.connected ? 'bg-emerald-400' : 'bg-slate-600'}`} /> Ground health console <span className="text-slate-600">/</span> Multi-engine runtime</div>
          <h2 className="mt-2 text-xl sm:text-2xl font-semibold text-white tracking-tight">Engine condition, with evidence</h2>
          <p className="mt-1 text-xs text-slate-400 font-mono">Live plant telemetry, calibrated residuals, and operator-controlled fault scenarios.</p>
        </div>
        <label className="relative flex items-center gap-3 rounded-sm border border-surface-border bg-surface-card px-3 py-2 min-w-[260px]">
          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono">Powerplant</span>
          <select value={runtime.engineId} onChange={(event) => void runtime.selectEngine(event.target.value)} className="flex-1 bg-transparent text-xs font-mono text-white outline-none appearance-none pr-6 cursor-pointer">
            {(runtime.catalog?.engines ?? []).map((engine) => <option key={engine.engine_id} value={engine.engine_id} className="bg-surface-card text-[#101b20]">{engineName(engine.display_name, engine.engine_id).name}</option>)}
          </select><ChevronDown className="w-4 h-4 text-slate-400 pointer-events-none absolute right-3" />
        </label>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-surface-border pt-3 text-[11px] font-mono">
        <span className={`px-2 py-0.5 rounded-sm border ${runtime.connected ? 'text-success border-success-muted bg-success-dim' : 'text-warning border-warning-muted bg-warning-dim'}`}>{runtime.connected ? 'LIVE · 20 Hz SYNCHRONOUS' : 'CONNECTING'}</span>
        <span className="px-2 py-0.5 rounded-sm border border-surface-border text-slate-300">{frame?.source ?? 'PLANT'} SOURCE</span>
        <span className="px-2 py-0.5 rounded-sm border border-surface-border text-slate-300">{frame?.evidence_class ?? 'SIMULATION'} EVIDENCE</span>
        <span className="text-slate-400 ml-1">{profile?.tail_id ?? 'Waiting for calibration'}</span>
        {engineName(profile?.display_name).tag && <span className="px-2 py-0.5 rounded-sm border border-surface-border text-slate-400">{engineName(profile?.display_name).tag}</span>}
        {profile && !profile.ready && <span className="text-amber-300">Profile calibrating</span>}
        {notice && <span className="ml-auto text-accent font-medium" role="status">{notice}</span>}
      </div>
      {runtime.error && <div className="mt-3 rounded-sm border border-amber-800/80 bg-amber-950/20 p-3 text-xs font-mono text-amber-200">{runtime.error}. Check the backend connection in Settings.</div>}
    </section>

    <section aria-label="Guided demonstration" className={`surface-panel p-4 sm:p-5 rounded-sm ${demoActive ? 'border-accent/70 sticky top-[72px] z-20 shadow-card-lg' : ''}`}>
      <div className="flex flex-col lg:flex-row lg:items-center gap-4">
        <div className="lg:w-[300px] shrink-0">
          <h3 className="text-sm font-semibold text-white tracking-tight">See it catch a fault in 60 seconds</h3>
          <p className="mt-1 text-xs font-mono text-slate-400">Injects an oil-pressure loss on the Rotax 912 iS and follows it from first residual to maintenance directive.</p>
        </div>
        <ol className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-2" aria-live="polite">
          {DEMO_STEPS.map((label, i) => {
            const done = demoActive && demoReached >= i;
            const current = demoActive && demoReached === i - 1;
            return <li key={label} className={`rounded-sm border px-3 py-2 text-xs font-mono transition-colors ${done ? 'border-accent/70 bg-accent/10 text-white' : current ? 'border-surface-border-strong text-slate-300' : 'border-surface-border text-slate-500'}`}>
              <span className="flex items-center gap-1.5">{done ? <Check className="w-3.5 h-3.5 text-accent" /> : <span className="inline-block w-3.5 text-center tabular-nums">{i + 1}</span>}{label}</span>
            </li>;
          })}
        </ol>
        <div className="shrink-0 flex items-center gap-2">
          {demoActive
            ? <><span className="text-xs font-mono text-slate-400 tabular-nums">{demoRemaining}s</span><button onClick={stopDemo} className="rounded-sm border border-surface-border bg-surface-card px-3 py-2 text-xs font-mono text-slate-200 hover:bg-white/5"><RotateCcw className="inline w-3.5 h-3.5 mr-1.5" />Stop &amp; reset</button></>
            : <button disabled={!runtime.connected} onClick={() => void runDemo()} className="rounded-sm bg-accent text-white px-4 py-2 text-xs font-mono font-medium disabled:opacity-40 hover:bg-accent/90 transition-colors shadow-sm"><Play className="inline w-3.5 h-3.5 mr-1.5" />Run the 60-second demo</button>}
        </div>
      </div>
    </section>

    <section aria-label="Fleet overview" className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-2">
      {runtime.fleet.map((member) => <button key={member.engine_id} onClick={() => void runtime.selectEngine(member.engine_id)} className={`surface-panel p-3 text-left transition-colors rounded-sm hover:border-surface-border-strong ${runtime.engineId === member.engine_id ? 'border-accent/70 bg-accent/10 shadow-sm' : ''}`}>
        <div className="flex items-center justify-between gap-2"><span className="truncate text-xs font-medium text-slate-200">{engineName(runtime.catalog?.engines.find((engine) => engine.engine_id === member.engine_id)?.display_name, member.engine_id).name}</span><span className={`h-1.5 w-1.5 rounded-full ${!member.ready ? 'bg-slate-600' : member.confirmed ? 'bg-critical' : member.raw_alarm ? 'bg-warning' : 'bg-success'}`} /></div>
        <div className="mt-2 text-[10px] font-mono text-slate-400">{member.ready ? `${number(member.rpm, 0)} RPM · ${number(member.max_cht, 0)}° CHT` : 'Calibrating profile'}</div>
        <div className="mt-1 text-[9px] uppercase tracking-wider font-mono text-slate-500">{runtime.engineId === member.engine_id ? '● Selected engine' : member.confirmed ? 'Confirmed anomaly' : member.raw_alarm ? 'Raw anomaly' : member.ready ? 'Monitoring' : 'Preparing'}</div>
      </button>)}
    </section>

    <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
      {[
        ['Engine speed', `${number(frame?.channels.rpm, 0)} RPM`, 'CRANK SPEED'],
        ['Cylinder head', `${number(Math.max(...(frame?.cht ?? [NaN])))} °C`, `MAX OF ${profile?.n_cylinders ?? '—'} CYLINDERS`],
        ['Exhaust gas', `${number(Math.max(...(frame?.egt ?? [NaN])))} °C`, 'MAX CYLINDER'],
        ['Detector state', detectorState[0], detectorState[1]],
      ].map(([label, value, caption], index) => <div key={label} className={`surface-panel p-4 rounded-sm ${index === 3 && alarms?.confirmed ? 'surface-panel-critical' : ''}`}><div className="text-[10px] uppercase tracking-wider font-mono text-slate-400">{label}</div><div className={`mt-2 text-xl sm:text-2xl font-mono font-semibold tabular-nums ${index === 3 && alarms?.confirmed ? 'text-critical' : index === 3 && alarms?.raw_alarm ? 'text-warning' : 'text-white'}`}>{value}</div><div className="mt-1 text-[10px] font-mono text-slate-500 truncate">{caption}</div></div>)}
    </div>

    <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-4">
      <section id="detector-evidence" className="surface-panel p-4 sm:p-5 rounded-sm scroll-mt-24">
        <div className="flex items-start justify-between"><div><h3 className="text-sm font-semibold text-white tracking-tight">Detector evidence</h3><p className="text-xs font-mono text-slate-400 mt-1">Live tier-0 score relative to its calibrated threshold. Above 1.0 is a raw anomaly.</p></div><Activity className="w-4 h-4 text-accent" /></div>
        {detectorEntries.length ? <div className="mt-5 space-y-4">{detectorEntries.map(([name, ratio]) => <div key={name}><div className="flex justify-between text-xs font-mono"><span className="text-slate-300">{title(name)}</span><span className={ratio >= 1 ? 'text-warning tabular-nums font-semibold' : 'text-slate-400 tabular-nums'}>{number(ratio, 2)}× threshold</span></div><div className="mt-2 h-1.5 rounded-full bg-surface overflow-hidden border border-surface-border"><div className={`h-full rounded-full transition-[width] duration-300 ${ratio >= 1 ? 'bg-warning' : 'bg-accent'}`} style={{ width: `${Math.min(100, Math.max(2, ratio * 35))}%` }} /></div></div>)}</div> : <div className="mt-6 rounded-sm bg-white/[0.03] p-4 text-xs font-mono text-slate-400">{profile?.ready ? 'Waiting for first scored frame…' : 'Calibration is preparing the residual baseline.'}</div>}
        {alarms && <div className={`mt-5 flex gap-2 rounded-sm border p-3 text-xs font-mono ${alarms.confirmed ? 'border-critical/60 bg-critical-dim text-critical' : alarms.raw_alarm ? 'border-warning/60 bg-warning-dim text-warning' : 'border-success/50 bg-success-dim text-success'}`}>
          {alarms.confirmed ? <AlertTriangle className="w-4 h-4 shrink-0" /> : alarms.raw_alarm ? <CircleHelp className="w-4 h-4 shrink-0" /> : <Check className="w-4 h-4 shrink-0" />}
          <span>{alarms.confirmed ? `Fault confirmed${candidate ? ` · ${candidate}` : ''}` : alarms.raw_alarm ? 'Anomaly detected · waiting for the persistence gate to confirm it' : 'Engine nominal · no residual alarm'}{alarms.top_channels.length ? ` · Leading channels: ${channelEvidence(alarms.top_channels)}` : ''}</span>
        </div>}
        {frame?.heavy && <div className="mt-4 rounded-sm border border-accent/40 bg-accent/5 p-3"><div className="flex items-center justify-between gap-2"><div className="text-xs font-medium font-mono text-accent">Reservoir classifier · tier 1 <span className="font-normal opacity-70">(readout scores, not probabilities)</span></div><span className="text-[10px] font-mono text-accent font-semibold text-right">Candidate: {title(frame.heavy.label)}</span></div><div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2">{frame.heavy.classes.map((label, i) => <div key={label} className={`rounded-sm border p-2 ${label === frame.heavy?.label ? 'border-accent/60 bg-accent/10' : 'bg-black/30 border-surface-border'}`}><div className="truncate text-[10px] font-mono text-slate-400">{title(label)}</div><div className="mt-1 text-xs font-mono font-medium text-white tabular-nums">{number(frame.heavy?.scores[i], 3)}</div></div>)}</div></div>}
        {!frame?.heavy && <div className="mt-4 text-[10px] font-mono text-slate-500">Tier 1 {profile?.heavy_ready ? 'warming on selection' : 'not ready'} · randomized reservoir readout trained on this tail's simulated fault library.</div>}
      </section>

      <section className="surface-panel p-4 sm:p-5 rounded-sm">
        <div className="flex items-start justify-between"><div><h3 className="text-sm font-semibold text-white tracking-tight">Scenario controls</h3><p className="text-xs font-mono text-slate-400 mt-1">Commands change simulated plant conditions (marked MANUAL).</p></div><SlidersHorizontal className="w-4 h-4 text-accent" /></div>
        <div className="mt-4 space-y-3">
          {leverFields.map((field) => <label key={field.label} className="block"><span className="flex justify-between text-xs font-mono text-slate-400"><span>{field.label}</span><span className="tabular-nums text-slate-200 font-semibold">{field.value}{field.unit}</span></span><input className="mt-2 w-full" type="range" min={field.min} max={field.max} step={field.step} value={field.value} onChange={(e) => field.set(Number(e.target.value))} onPointerUp={() => changeLever({ throttle_pct: throttle, altitude_ft: altitude, oat_c: oat })} onKeyUp={(e) => { if (e.key.startsWith('Arrow')) changeLever({ throttle_pct: throttle, altitude_ft: altitude, oat_c: oat }); }} /></label>)}
          <button onClick={() => changeLever({ throttle_pct: throttle, altitude_ft: altitude, oat_c: oat })} className="w-full rounded-sm border border-surface-border bg-surface-card px-3 py-2 text-xs font-mono text-slate-200 hover:bg-white/5 transition-colors">Apply flight conditions</button>
        </div>
        <div className="mt-5 border-t border-surface-border pt-4">
          <div className="text-xs font-medium font-mono text-slate-200 uppercase tracking-wider">Inject a profile-valid fault</div>
          <div className="mt-2 flex gap-2">
            <select aria-label="Fault mode" value={faultMode} onChange={(e) => setFaultMode(e.target.value)} className="min-w-0 flex-1 rounded-sm border border-surface-border bg-surface-card px-2.5 py-2 text-xs font-mono text-slate-200"><option value="">Choose fault…</option>{profile?.faults.map((fault) => <option key={fault.mode} value={fault.mode}>{title(fault.mode)}</option>)}</select>
            {profile?.faults.find((fault) => fault.mode === faultMode)?.per_cylinder && <select aria-label="Cylinder" value={cylinder} onChange={(e) => setCylinder(Number(e.target.value))} className="rounded-sm border border-surface-border bg-surface-card px-2 text-xs font-mono text-slate-200">{Array.from({ length: profile.n_cylinders }, (_, i) => <option key={i + 1} value={i + 1}>Cyl {i + 1}</option>)}</select>}
          </div>
          {faultMode && <div className="mt-2 flex items-center justify-between gap-2 font-mono"><span className="text-[10px] text-slate-400">{profile?.faults.find((fault) => fault.mode === faultMode)?.description} · {profile?.faults.find((fault) => fault.mode === faultMode)?.scalar_visible ? 'scalar-visible' : 'waveform-only'}</span><span className="text-[10px] text-accent font-semibold">{Math.round(severity * 100)}%</span></div>}
          <input aria-label="Fault severity" className="mt-2 w-full" type="range" min="0.1" max="1" step="0.05" value={severity} onChange={(e) => setSeverity(Number(e.target.value))} />
          <button disabled={!faultMode || !runtime.connected} onClick={inject} className="mt-2 w-full rounded-sm bg-accent text-white px-3 py-2 text-xs font-mono font-medium disabled:opacity-40 hover:bg-accent/90 transition-colors shadow-sm"><Zap className="inline w-3.5 h-3.5 mr-1.5" />Inject scenario</button>
          {activeFaults.length > 0 && <div className="mt-3 rounded-sm border border-warning/60 bg-warning-dim p-2.5"><div className="flex items-center justify-between text-[11px] font-mono text-warning"><span>Manual scenarios active</span><button title="Clear injected faults" onClick={() => void run(() => runtime.command('/faults', 'DELETE'), 'Manual scenarios cleared')} className="flex items-center gap-1 text-warning hover:underline"><RotateCcw className="w-3 h-3" /> Clear</button></div><div className="mt-1 text-[10px] font-mono text-slate-300">{activeFaults.map((fault) => `${title(fault.mode)}${fault.cylinder ? ` · cyl ${fault.cylinder}` : ''}`).join('  /  ')}</div></div>}
          <p className="mt-3 flex gap-1.5 text-[10px] leading-relaxed font-mono text-slate-500"><Users className="w-3 h-3 shrink-0 mt-0.5" />Shared demo: other visitors see the scenarios you inject. Faults you inject clear automatically after 2 minutes.</p>
        </div>
      </section>
    </div>

    <DecisionSupport frame={frame} />

    <section className="surface-panel p-4 sm:p-5 rounded-sm">
      <div className="flex items-center justify-between gap-3"><div><h3 className="font-semibold text-white">Live engine channels</h3><p className="text-xs text-slate-500 mt-1">Profile-provided stream from the virtual plant at 20 Hz</p></div><Radio className="w-4 h-4 text-slate-500" /></div>
      {readings.length ? <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">{readings.map(([name, value]) => { const unit = runtime.schema?.channels.find((channel) => channel.name === name)?.unit; return <div key={name} className="rounded border border-white/[0.06] bg-black/10 px-3 py-2"><div className="truncate text-[10px] text-slate-500" title={name}>{channelLabel(name)}</div><div className="mt-1 text-sm font-medium tabular-nums text-slate-200">{number(value, name === 'alt' || name === 'rpm' ? 0 : 2)}{unit ? <span className="ml-1 text-[10px] text-slate-500">{unit}</span> : null}</div></div>; })}</div> : <div className="mt-4 text-sm text-slate-500">Waiting for calibrated engine frames…</div>}
    </section>
    <div className="flex items-start gap-2 px-1 text-[10px] leading-relaxed text-slate-600"><CircleHelp className="w-3.5 h-3.5 shrink-0 mt-0.5" /><span>Prototype boundary: this console runs a virtual plant in simulated time (20× real time). Outputs are advisory software evidence, not readings from an aircraft or a certified diagnosis.</span></div>
  </div>;
}

const SHORT_AIRFIELD: Record<string, string> = { VILH: 'Leh', VI82: 'Thoise', VIKG: 'Kargil' };

function DecisionSupport({ frame }: { frame: EngineFrame | null }) {
  const diagnosis = frame?.diagnosis;
  const rul = frame?.prognostics?.rul;
  const reliability = frame?.reliability;
  const glide = frame?.glide;
  if (!diagnosis && !rul && !reliability && !glide) return null;
  const nominal = !diagnosis || diagnosis.ata_chapter === 'ATA 00-00';
  const airfields = [...(glide?.airfields ?? [])].sort((a, b) => a.distance_nm - b.distance_nm).slice(0, 3);
  const percent = (v?: number) => typeof v === 'number' ? `${(v * 100).toFixed(v >= 0.995 || v <= 0.005 ? 0 : 1)}%` : '—';
  return <section aria-label="Decision support" className="surface-panel p-4 sm:p-5 rounded-sm">
    <div className="flex items-start justify-between"><div><h3 className="text-sm font-semibold text-white tracking-tight">From detection to decision</h3><p className="text-xs font-mono text-slate-400 mt-1">What the finding means for maintenance, the remaining mission and the nearest safe airfield.</p></div><Wrench className="w-4 h-4 text-accent" /></div>
    <div className="mt-4 grid grid-cols-1 lg:grid-cols-[1.3fr_0.7fr_0.7fr_1fr] gap-3">
      <div className={`rounded-sm border p-3 ${nominal ? 'border-surface-border' : 'border-critical/50 bg-critical-dim'}`}>
        <div className="text-[10px] uppercase tracking-wider font-mono text-slate-400">Maintenance directive</div>
        <div className={`mt-1.5 text-sm font-semibold ${nominal ? 'text-white' : 'text-critical'}`}>{diagnosis ? (nominal ? 'No action required' : title(diagnosis.fault_name)) : '—'}</div>
        {diagnosis && <div className="mt-1 text-[11px] font-mono text-slate-300">{diagnosis.ata_chapter}{diagnosis.manual_reference ? ` · ${diagnosis.manual_reference}` : ''}</div>}
        {!nominal && diagnosis?.prescriptive_action && <p className="mt-2 text-xs text-slate-200 leading-relaxed">{diagnosis.prescriptive_action}</p>}
        {!nominal && diagnosis?.maintenance_order && <p className="mt-1.5 text-[11px] font-mono text-slate-400 leading-relaxed">{diagnosis.maintenance_order}</p>}
      </div>
      <div className="rounded-sm border border-surface-border p-3">
        <div className="text-[10px] uppercase tracking-wider font-mono text-slate-400">Remaining useful life</div>
        <div className="mt-1.5 text-xl font-mono font-semibold tabular-nums text-white">{number(rul?.rul_point, 1)} <span className="text-xs text-slate-400">h</span></div>
        <div className="mt-1 text-[11px] font-mono text-slate-400 tabular-nums">{rul ? `${number(rul.rul_p_lower, 1)}–${number(rul.rul_p_upper, 1)} h · ${Math.round(rul.nominal_coverage * 100)}% conformal` : '—'}</div>
      </div>
      <div className="rounded-sm border border-surface-border p-3">
        <div className="text-[10px] uppercase tracking-wider font-mono text-slate-400">Mission reliability</div>
        <div className="mt-1.5 text-xl font-mono font-semibold tabular-nums text-white">{percent(reliability?.mission_reliability)}</div>
        <div className="mt-1 text-[11px] font-mono text-slate-400">{reliability ? `${Math.round(reliability.mission_hours)} h ISR · limit ${title(reliability.limiting_component)}` : '—'}</div>
      </div>
      <div className="rounded-sm border border-surface-border p-3">
        <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-mono text-slate-400"><Compass className="w-3 h-3" />Engine-out glide</div>
        <div className="mt-1.5 text-sm font-mono text-white tabular-nums">{glide ? `${number(glide.glide_range_nm, 0)} nm · ${number(glide.time_aloft_min, 0)} min aloft from ${Math.round(glide.altitude_ft).toLocaleString('en-IN')} ft` : '—'}</div>
        <ul className="mt-2 space-y-1">{airfields.map((a) => <li key={a.airfield_id} className="flex justify-between gap-2 text-[11px] font-mono"><span className="truncate text-slate-300" title={a.name}>{SHORT_AIRFIELD[a.airfield_id] ?? a.name.split(' ')[0]}</span><span className={`shrink-0 tabular-nums ${a.is_reachable ? 'text-success' : 'text-slate-500'}`}>{number(a.distance_nm, 0)} nm · {a.is_reachable ? 'reachable' : `${Math.round(-a.alt_margin_ft).toLocaleString('en-IN')} ft short`}</span></li>)}</ul>
      </div>
    </div>
  </section>;
}
