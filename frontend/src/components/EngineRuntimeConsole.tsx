import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, Check, ChevronDown, CircleHelp, Radio, RotateCcw, SlidersHorizontal, Zap } from 'lucide-react';
import { useEngineRuntime, useNow } from '../hooks/useEngineRuntime';
import { dataAgeMs } from '../store/engineStore';
import { NO_DATA, num } from '../utils/format';
import { LabelsContext, channelLabel, componentLabel, useFetchLabels } from '../utils/labels';
import RoutePlannerPanel from './RoutePlannerPanel';
import StatusBanner from './StatusBanner';
import EngineerPanel from './EngineerPanel';

const EngineViewer3D = lazy(() => import('./viewer3d/EngineViewer3D'));

const title = (value: string) => value.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c: string) => c.toUpperCase());
type Detections = { confirmed?: boolean; raw_alarm?: boolean; top_channels?: Array<string | [string, number]>;
  ratios?: Record<string, number>; candidate?: { label: string; classes: string[]; scores: number[] } | null };
const channelEvidence = (items: Array<string | [string, number]>) =>
  items.map((item) => Array.isArray(item) ? `${item[0]} (${num(item[1], 2)}σ)` : item).join(', ');
let requestCounter = 0;
/* crypto.randomUUID is missing on plain-http LAN pages, so fall back to time + a per-page counter (no Math.random). */
const newRequestId = () => (globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${++requestCounter}`);
const maxOf = (values: Array<number | null | undefined>) => {
  const v = values.filter((x): x is number => typeof x === 'number' && Number.isFinite(x));
  return v.length ? Math.max(...v) : null;
};

type View = 'ALL' | 'OPERATOR' | 'ENGINEER' | 'MAINTENANCE' | 'MISSION';
const VIEWS: Array<{ id: View; label: string }> = [
  { id: 'OPERATOR', label: 'Operator' }, { id: 'ENGINEER', label: 'Propulsion engineer' },
  { id: 'MAINTENANCE', label: 'Maintenance' }, { id: 'MISSION', label: 'Mission' }, { id: 'ALL', label: 'All panels' },
];
const VIEW_KEY = 'anumaan.console.view';
const TRAINING_KEY = 'anumaan.console.training';       // D56: off by default, per viewer                  // per-viewer convenience only (role is never sent to the server)
const loadView = (): View => {
  try { const v = localStorage.getItem(VIEW_KEY); return VIEWS.some((x) => x.id === v) ? (v as View) : 'OPERATOR'; }
  catch { return 'OPERATOR'; }
};

export function EngineRuntimeConsole({ serverUrl }: { serverUrl: string }) {
  const runtime = useEngineRuntime(serverUrl);
  const now = useNow(500);
  const { state, profile, faults } = runtime;
  const labels = useFetchLabels(runtime.api);
  const [faultId, setFaultId] = useState('');
  const [cylinder, setCylinder] = useState(1);
  const [severity, setSeverity] = useState<number | null>(null);
  const [levers, setLevers] = useState<{ throttle_pct: number; altitude_ft: number; oat_c: number } | null>(null);
  const [notice, setNotice] = useState('');
  const [missions, setMissions] = useState<Array<{ id: string; title: string; engines: string | string[] }>>([]);
  const [missionId, setMissionId] = useState('');
  const [recording, setRecording] = useState(false);
  const [lastSortie, setLastSortie] = useState('');
  const [view, setViewState] = useState<View>(loadView);
  const setView = (v: View) => { setViewState(v); try { localStorage.setItem(VIEW_KEY, v); } catch { /* storage blocked: keep in memory */ } };
  const show = (...views: View[]) => view === 'ALL' || views.includes(view);
  const [training, setTrainingState] = useState<boolean>(() => { try { return localStorage.getItem(TRAINING_KEY) === '1'; } catch { return false; } });
  const setTraining = (on: boolean) => { setTrainingState(on); try { localStorage.setItem(TRAINING_KEY, on ? '1' : '0'); } catch { /* memory only */ } };

  const readings = useMemo(() => Object.entries(state?.readings ?? {}).sort(([a], [b]) => a.localeCompare(b)), [state]);
  const det = (state?.detections ?? null) as Detections | null;
  const detectorEntries = Object.entries(det?.ratios ?? {}).sort((a, b) => b[1] - a[1]);
  const activeFaults = state?.active_faults ?? [];
  const hypotheses = state?.hypotheses ?? [];
  const prog = (state?.prognostics ?? null) as { time_to_limit?: Array<{ channel: string; limit: number; time_to_limit_s: number; low_s: number; high_s: number }>; baseline?: { version: number; learning: boolean; reason: string }; rul?: { status: string; reason?: string; rul_h?: number; rul_lower_h?: number; rul_upper_h?: number; coverage_target?: number; trained_on?: string } } | null;
  const rul = prog?.rul ?? null;
  const ttl = prog?.time_to_limit ?? [];
  const baseline = prog?.baseline ?? null;
  const rel = (state?.reliability ?? null) as { mission_reliability: number; ci_lower: number; ci_upper: number; mission_profile: string; limiting_component?: string } | null;
  const orders = (state?.maintenance ?? []) as Array<{ id: string; title: string; ata_chapter?: string; status: string; action?: string }>;
  const fault = faults.find((f) => f.id === faultId);
  const age = dataAgeMs(runtime.slot, now);
  const live = runtime.connection === 'LIVE';

  useEffect(() => { setFaultId(''); setLevers(null); }, [runtime.engineId]);
  useEffect(() => {
    fetch(`${serverUrl}/api/v1/missions`, { cache: 'no-store' }).then((r) => r.json())
      .then((d) => setMissions(d.missions ?? [])).catch(() => setMissions([]));
  }, [serverUrl]);
  const availableMissions = missions.filter((m) => m.engines === 'ALL' || (Array.isArray(m.engines) && m.engines.includes(runtime.engineId ?? '')));
  const mission = state?.mission as { title?: string; phase?: string; state?: string; elapsed_s?: number; total_s?: number; remaining_s?: number } | null | undefined;
  const missionCommand = (action: 'START' | 'ABORT') => void run(() => runtime.command('/mission', 'POST',
    action === 'START' ? { action, mission_id: missionId } : { action }), action === 'START' ? 'Mission started' : 'Mission aborted');
  const recordingCommand = () => void run(async () => {
    const res = await runtime.command('/recording', 'POST', { action: recording ? 'STOP' : 'START' }) as { recording?: { sortie_id?: string } };
    if (recording && res?.recording?.sortie_id) setLastSortie(res.recording.sortie_id);
    setRecording(!recording);
  }, recording ? 'Recording stopped' : 'Recording started');
  useEffect(() => { if (fault) setSeverity(fault.default_severity); }, [fault]);
  // sliders start from the SERVER's lever targets, never from local defaults (audit section 9)
  useEffect(() => {
    const lv = state?.levers;
    if (levers || !lv) return;
    const t = lv.throttle_target, a = lv.altitude_target_ft, o = lv.oat_target_c;
    if (typeof t === 'number' && typeof a === 'number' && typeof o === 'number') setLevers({ throttle_pct: t, altitude_ft: a, oat_c: o });
  }, [state, levers]);

  const run = async (fn: () => Promise<unknown>, success: string) => {
    try { await fn(); setNotice(success); setTimeout(() => setNotice(''), 3500); }
    catch (cause) { setNotice(cause instanceof Error ? cause.message : 'Command failed'); }
  };
  const inject = () => {
    if (!fault) return;
    void run(() => runtime.command('/faults', 'POST', {
      fault_id: fault.id, cylinder: fault.scope === 'CYLINDER' ? cylinder : undefined,
      severity: severity ?? undefined, source: 'console', request_id: newRequestId(),
    }), `${title(fault.name)} injected`);
  };
  const applyLevers = () => { if (levers) void run(() => runtime.command('/levers', 'POST', levers), 'Flight condition target updated'); };
  const leverFields = levers ? [
    { key: 'throttle_pct' as const, label: 'Throttle', min: 0, max: 100, unit: '%' },
    { key: 'altitude_ft' as const, label: 'Altitude', min: 0, max: 25000, unit: ' ft' },
    { key: 'oat_c' as const, label: 'Outside air', min: -40, max: 45, unit: ' °C' },
  ] : [];

  const badge = runtime.connection === 'LIVE'
    ? `LIVE · ${state?.rate_hz_actual != null ? `${num(state.rate_hz_actual, 1)} Hz` : 'rate —'} · age ${age != null ? `${Math.round(age)} ms` : NO_DATA}`
    : runtime.connection;

  return <LabelsContext.Provider value={labels}><div className="space-y-4">
    <section className="surface-panel p-4 sm:p-5">
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[#68757a] font-mono"><span className={`w-2 h-2 rounded-full ${live ? 'bg-emerald-400' : 'bg-slate-600'}`} /> Ground health console <span className="text-slate-600">/</span> Multi-engine runtime</div>
          <h2 className="mt-2 text-xl sm:text-2xl font-semibold text-white tracking-tight">Engine condition, with evidence</h2>
          <p className="mt-1 text-xs text-slate-400 font-mono">Live plant telemetry, calibrated residuals, and operator-controlled fault scenarios.</p>
        </div>
        <label className="relative flex items-center gap-3 rounded-sm border border-surface-border bg-surface-card px-3 py-2 min-w-[260px]">
          <span className="text-xs uppercase tracking-wider text-slate-400 font-mono">Powerplant</span>
          <select value={runtime.engineId ?? ''} onChange={(event) => runtime.selectEngine(event.target.value)} className="flex-1 bg-transparent text-xs font-mono text-white outline-none appearance-none pr-6 cursor-pointer">
            {runtime.engines.map((engine) => <option key={engine.engine_id} value={engine.engine_id} className="bg-surface-card text-[#101b20]">{engine.display_name}</option>)}
          </select><ChevronDown className="w-4 h-4 text-slate-400 pointer-events-none absolute right-3" />
        </label>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-surface-border pt-3 text-xs font-mono">
        <span className={`px-2 py-0.5 rounded-sm border ${live ? 'text-success border-success-muted bg-success-dim' : 'text-slate-300 border-surface-border'}`}>{badge}</span>
        <span className="px-2 py-0.5 rounded-sm border border-surface-border text-slate-300">{state?.source ?? NO_DATA} SOURCE</span>
        <span className="px-2 py-0.5 rounded-sm border border-surface-border text-slate-300">{state?.evidence_class ?? NO_DATA} EVIDENCE</span>
        <span className="px-2 py-0.5 rounded-sm border border-surface-border text-slate-300">STATUS {state?.status.level ?? NO_DATA}</span>
        {profile && !profile.ready && <span className="text-slate-300">Profile calibrating</span>}
        {notice && <span className="ml-auto text-accent font-medium">{notice}</span>}
      </div>
      {runtime.error && <div className="mt-3 rounded-sm border border-surface-border bg-white/[0.03] p-3 text-xs font-mono text-slate-200">{runtime.error}. Check the backend connection in Settings.</div>}
      <nav aria-label="Console view" className="mt-3 flex flex-wrap gap-1 text-xs font-mono">
        {VIEWS.map((v) => <button key={v.id} type="button" aria-pressed={view === v.id} onClick={() => setView(v.id)}
          className={`px-3 py-1.5 rounded-sm border ${view === v.id ? 'border-surface-border-strong bg-white/10 text-white' : 'border-surface-border text-slate-400 hover:bg-white/5'}`}>{v.label}</button>)}
        <button type="button" aria-pressed={training} onClick={() => setTraining(!training)} title="Training mode also draws the injected fault on the 3D engine"
          className={`ml-auto px-3 py-1.5 rounded-sm border ${training ? 'border-surface-border-strong bg-white/10 text-white' : 'border-surface-border text-slate-400 hover:bg-white/5'}`}>Training mode: {training ? 'on' : 'off'}</button>
      </nav>
    </section>

    <StatusBanner engineId={runtime.engineId ?? null} status={state?.status} alerts={state?.alerts ?? []} simTimeS={state?.sim_time_s}
      units={Object.fromEntries(Object.entries(state?.readings ?? {}).map(([k, r]) => [k, r.unit]))}
      api={runtime.api} onNotice={(t) => { setNotice(t); setTimeout(() => setNotice(''), 3500); }} />

    {show('OPERATOR') && <section aria-label="Fleet overview" className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-2">
      {runtime.engines.map((engine) => {
        const s = runtime.fleet[engine.engine_id]?.state;
        const d = (s?.detections ?? null) as Detections | null;
        const cht = maxOf(Object.entries(s?.readings ?? {}).filter(([k]) => k.startsWith('cht[')).map(([, r]) => r.value));
        return <button key={engine.engine_id} onClick={() => runtime.selectEngine(engine.engine_id)} className={`surface-panel p-3 text-left transition-colors rounded-sm hover:border-surface-border-strong ${runtime.engineId === engine.engine_id ? 'border-accent/70 bg-accent/10 shadow-sm' : ''}`}>
          <div className="flex items-center justify-between gap-2"><span className="truncate text-xs font-medium text-slate-200">{engine.display_name}</span><span className={`h-1.5 w-1.5 rounded-full ${!s ? 'bg-slate-600' : d?.confirmed ? 'bg-critical' : d?.raw_alarm ? 'bg-warning' : 'bg-success'}`} /></div>
          <div className="mt-2 text-xs font-mono text-slate-400">{s ? `${num(s.readings?.rpm?.value, 0)} RPM · ${num(cht, 0)}° CHT` : engine.ready ? NO_DATA : 'Calibrating profile'}</div>
          <div className="mt-1 text-xs uppercase tracking-wider font-mono text-slate-500">{runtime.engineId === engine.engine_id ? '● Selected' : d?.confirmed ? 'Confirmed anomaly' : d?.raw_alarm ? 'Raw anomaly' : s ? 'Monitoring' : 'Preparing'}</div>
        </button>;
      })}
    </section>}

    {show('OPERATOR', 'ENGINEER') && <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
      {[
        ['Engine speed', `${num(state?.readings?.rpm?.value, 0)} RPM`, 'CRANK SPEED'],
        ['Cylinder head', `${num(maxOf(readings.filter(([k]) => k.startsWith('cht[')).map(([, r]) => r.value)))} °C`, `MAX OF ${profile?.cylinders ?? '—'} CYLINDERS`],
        ['Exhaust gas', `${num(maxOf(readings.filter(([k]) => k.startsWith('egt[')).map(([, r]) => r.value)))} °C`, 'MAX CYLINDER'],
        ['Fault detector', !det ? 'Starting up' : det.confirmed ? 'Fault confirmed' : det.raw_alarm ? 'Checking an anomaly' : 'No anomaly', 'READINGS VS ENGINE MODEL'],
      ].map(([label, value, caption], index) => <div key={label} className={`surface-panel p-4 rounded-sm ${index === 3 && det?.confirmed ? 'surface-panel-critical' : ''}`}><div className="text-xs uppercase tracking-wider font-mono text-slate-400">{label}</div><div className="mt-2 text-xl sm:text-2xl font-mono font-semibold tabular-nums text-white">{value}</div><div className="mt-1 text-xs font-mono text-slate-500">{caption}</div></div>)}
    </div>}

    {show('OPERATOR', 'MAINTENANCE') && <Suspense fallback={<div className="surface-panel p-4 text-xs font-mono text-slate-400">Loading 3D view…</div>}>
      <EngineViewer3D engineId={runtime.engineId ?? null} highlights={state?.highlights} api={runtime.api}
        injected={training ? activeFaults.flatMap((f) => (f.components ?? []).map((c) => ({ component_id: c, reason: `${f.fault_id} ${title(f.name)} (injected)` }))) : []} />
    </Suspense>}

    {show('OPERATOR', 'MAINTENANCE') && <section className="surface-panel p-4 sm:p-5 rounded-sm">
      <h3 className="text-sm font-semibold text-white tracking-tight">Prognosis and maintenance</h3>
      <div className="mt-3 grid grid-cols-1 lg:grid-cols-3 gap-3 text-xs font-mono">
        <div className="rounded-sm border border-surface-border p-3">
          <div className="text-slate-300">Time to limit</div>
          {ttl.length ? ttl.map((x) => <div key={x.channel} className="mt-1 text-slate-400">{channelLabel(labels, x.channel)} reaches its limit ({num(x.limit, 1)}) in about {num(x.time_to_limit_s / 60, 0)} min <span className="text-slate-500">({num(x.low_s / 60, 0)}–{num(x.high_s / 60, 0)} min)</span></div>) : <div className="mt-1 text-slate-500">No significant trend toward a limit</div>}
          {baseline && show('ENGINEER', 'MAINTENANCE') && <div className="mt-2 text-slate-500">Normal-behaviour baseline v{baseline.version} · {baseline.learning ? 'learning' : `paused: ${baseline.reason}`}</div>}
          <div className="mt-3 text-slate-300">Remaining useful life</div>
          {rul?.status === 'OK'
            ? <><div className="mt-1 text-white tabular-nums">{num(rul.rul_h, 0)} h <span className="text-slate-500">({num(rul.rul_lower_h, 0)}–{num(rul.rul_upper_h, 0)} h, {rul.coverage_target == null ? NO_DATA : num(rul.coverage_target * 100, 0)} % band)</span></div>
                <div className="text-slate-500">{rul.trained_on}</div></>
            : <div className="mt-1 text-slate-500">{rul?.reason ?? NO_DATA}</div>}
        </div>
        <div className="rounded-sm border border-surface-border p-3">
          <div className="text-slate-300">Mission reliability</div>
          {rel ? <><div className="mt-1 text-lg text-white tabular-nums">{num(rel.mission_reliability * 100, 2)}%</div>
            <div className="text-slate-500">95 % CI {num(rel.ci_lower * 100, 2)}–{num(rel.ci_upper * 100, 2)} % · {rel.mission_profile}</div>
            {rel.limiting_component && <div className="text-slate-400">Weakest part: {componentLabel(labels, rel.limiting_component)}</div>}</> : <div className="mt-1 text-slate-500">{NO_DATA}</div>}
        </div>
        <div className="rounded-sm border border-surface-border p-3">
          <div className="text-slate-300">Work orders</div>
          {orders.length ? orders.map((w) => <div key={w.id} className="mt-2"><div className="text-slate-200">{w.title}</div><div className="text-slate-500">{w.ata_chapter ? `ATA ${w.ata_chapter} · ` : ''}{w.status}</div><div className="text-slate-400">{w.action}</div>
            <div className="mt-1 flex gap-2">{w.status === 'OPEN' && <button onClick={() => void run(() => runtime.api(`/api/v1/work_orders/${encodeURIComponent(w.id)}/transition`, 'POST', { to: 'IN_WORK', by: 'console' }), 'Work order in work')} className="rounded-sm border border-surface-border px-2 py-1 hover:bg-white/5">In work</button>}
              <button onClick={() => void run(() => runtime.api(`/api/v1/work_orders/${encodeURIComponent(w.id)}/transition`, 'POST', { to: 'SIGNED_OFF', by: 'console operator' }), 'Signed off - repair applied')} className="rounded-sm border border-surface-border px-2 py-1 hover:bg-white/5">Sign off</button></div></div>) : <div className="mt-1 text-slate-500">No open work order</div>}
        </div>
      </div>
    </section>}

    <div className={`grid grid-cols-1 gap-4 ${show('ENGINEER', 'MAINTENANCE') && show('OPERATOR', 'MISSION') ? 'xl:grid-cols-[1.2fr_0.8fr]' : ''}`}>
      {show('ENGINEER', 'MAINTENANCE') && <section className="surface-panel p-4 sm:p-5 rounded-sm">
        <div className="flex items-start justify-between"><div><h3 className="text-sm font-semibold text-white tracking-tight">Detector evidence</h3><p className="text-xs font-mono text-slate-400 mt-1">Live tier-0 score relative to threshold. Value &gt; 1.0 indicates raw anomaly.</p></div><Activity className="w-4 h-4 text-accent" /></div>
        {detectorEntries.length ? <div className="mt-5 space-y-4">{detectorEntries.map(([name, ratio]) => <div key={name}><div className="flex justify-between text-xs font-mono"><span className="text-slate-300">{title(name)}</span><span className={ratio >= 1 ? 'text-warning tabular-nums font-semibold' : 'text-slate-400 tabular-nums'}>{num(ratio, 2)}× threshold</span></div><div className="mt-2 h-1.5 rounded-full bg-surface overflow-hidden border border-surface-border"><div className={`h-full rounded-full ${ratio >= 1 ? 'bg-warning' : 'bg-accent'}`} style={{ width: `${Math.min(100, Math.max(2, ratio * 35))}%` }} /></div></div>)}</div> : <div className="mt-6 rounded-sm bg-white/[0.03] p-4 text-xs font-mono text-slate-400">{profile?.ready ? 'Waiting for first scored frame…' : 'Calibration is preparing the residual baseline.'}</div>}
        {det && <div className={`mt-5 flex gap-2 rounded-sm border p-3 text-xs font-mono ${det.confirmed ? 'border-critical/60 bg-critical-dim text-critical' : det.raw_alarm ? 'border-warning/60 bg-warning-dim text-warning' : 'border-surface-border text-slate-300'}`}>
          {det.confirmed ? <AlertTriangle className="w-4 h-4 shrink-0" /> : det.raw_alarm ? <CircleHelp className="w-4 h-4 shrink-0" /> : <Check className="w-4 h-4 shrink-0" />}
          <span>{det.confirmed ? 'Persistence confirmed anomaly' : det.raw_alarm ? 'Raw anomaly — persistence gate has not confirmed it' : 'No active residual alarm'}{det.top_channels?.length ? ` · Leading channels: ${channelEvidence(det.top_channels)}` : ''}</span>
        </div>}
        {hypotheses.length > 0 && <div className="mt-4 rounded-sm border border-surface-border bg-white/[0.03] p-3">
          <div className="text-xs font-medium font-mono text-slate-200">Fault isolation <span className="font-normal text-slate-500">(Bayesian posterior over registry faults and sensor offsets)</span></div>
          <div className="mt-3 space-y-2.5">{hypotheses.map((h, i) => {
            const where = h.cylinder ? `cyl ${h.cylinder}` : h.channel ? h.channel : '';
            const support = (h.supporting ?? []).map((e) => `${e.channel} ${num(e.z, 1)}σ`).join(', ');
            const ambiguous = i > 0 && h.group && h.group === hypotheses[0].group;
            return <div key={`${h.fault_id}-${where}-${i}`}>
              <div className="flex justify-between gap-2 text-xs font-mono"><span className="truncate text-slate-200">{h.fault_id ? `${h.fault_id} · ` : ''}{title(h.name)}{where ? ` · ${where}` : ''}<span className="ml-1.5 text-slate-500">{h.kind === 'SENSOR' ? 'sensor' : h.kind === 'PROCESS' ? 'engine' : ''}{ambiguous ? ' · cannot be told apart' : ''}</span></span><span className="tabular-nums text-slate-300">{h.posterior == null ? NO_DATA : num(h.posterior * 100, 0)}%</span></div>
              <div className="mt-1 h-1 rounded-full bg-surface overflow-hidden border border-surface-border"><div className={`h-full ${h.kind === 'NOMINAL' ? 'bg-success' : h.kind === 'SENSOR' ? 'bg-accent' : 'bg-warning'}`} style={{ width: h.posterior == null ? '0%' : `${Math.max(2, h.posterior * 100)}%` }} /></div>
              {(support || h.severity != null) && <div className="mt-1 text-xs font-mono text-slate-500">{h.severity != null ? `est. severity ${num(h.severity, 2)}` : ''}{support ? ` · evidence: ${support}` : ''}</div>}
            </div>;
          })}</div>
        </div>}
        {det?.candidate && <div className="mt-4 rounded-sm border border-accent/40 bg-accent/5 p-3"><div className="flex items-center justify-between"><div className="text-xs font-medium font-mono text-accent">Selected-engine reservoir · tier 1 <span className="font-normal opacity-70">(readout scores, not probabilities)</span></div><span className="text-xs font-mono text-accent font-semibold">Candidate: {title(det.candidate.label)}</span></div><div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2">{det.candidate.classes.map((label, i) => <div key={label} className="rounded-sm bg-black/30 border border-surface-border p-2"><div className="truncate text-xs font-mono text-slate-400">{title(label)}</div><div className="mt-1 text-xs font-mono font-medium text-white tabular-nums">{num(det.candidate?.scores[i], 3)}</div></div>)}</div></div>}
      </section>}

      {show('OPERATOR', 'MISSION') && <section className="surface-panel p-4 sm:p-5 rounded-sm">
        <div className="flex items-start justify-between"><div><h3 className="text-sm font-semibold text-white tracking-tight">Scenario controls</h3><p className="text-xs font-mono text-slate-400 mt-1">Commands change simulated plant conditions; every client sees the result.</p></div><SlidersHorizontal className="w-4 h-4 text-accent" /></div>
        <div className="mt-4 space-y-3">
          {!levers && <div className="text-xs font-mono text-slate-500">Waiting for the server's lever targets…</div>}
          {levers && leverFields.map((field) => <label key={field.key} className="block"><span className="flex justify-between text-xs font-mono text-slate-400"><span>{field.label}</span><span className="tabular-nums text-slate-200 font-semibold">{Math.round(levers[field.key])}{field.unit}</span></span><input className="mt-2 w-full" type="range" min={field.min} max={field.max} value={levers[field.key]} onChange={(e) => setLevers({ ...levers, [field.key]: Number(e.target.value) })} onPointerUp={applyLevers} onKeyUp={(e) => { if (e.key.startsWith('Arrow')) applyLevers(); }} /></label>)}
          {levers && <button onClick={applyLevers} className="w-full rounded-sm border border-surface-border bg-surface-card px-3 py-2 text-xs font-mono text-slate-200 hover:bg-white/5 transition-colors">Apply flight conditions</button>}
        </div>
        <div className="mt-5 border-t border-surface-border pt-4">
          <div className="text-xs font-medium font-mono text-slate-200 uppercase tracking-wider">Mission and recording</div>
          <div className="mt-2 flex gap-2">
            <select value={missionId} onChange={(e) => setMissionId(e.target.value)} className="min-w-0 flex-1 rounded-sm border border-surface-border bg-surface-card px-2.5 py-2 text-xs font-mono text-slate-200"><option value="">Choose mission…</option>{availableMissions.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}</select>
            <button disabled={!missionId || !live} onClick={() => missionCommand('START')} className="rounded-sm border border-surface-border px-3 text-xs font-mono text-slate-200 disabled:opacity-40 hover:bg-white/5">Fly</button>
            <button disabled={!mission || mission.state !== 'RUNNING'} onClick={() => missionCommand('ABORT')} className="rounded-sm border border-surface-border px-3 text-xs font-mono text-slate-200 disabled:opacity-40 hover:bg-white/5">Abort</button>
          </div>
          {mission && <div className="mt-2 text-xs font-mono text-slate-400">{mission.title} · {mission.state} · {mission.phase} · {mission.elapsed_s == null ? NO_DATA : num(mission.elapsed_s / 60, 0)} / {mission.total_s == null ? NO_DATA : num(mission.total_s / 60, 0)} min</div>}
          <div className="mt-2 flex items-center gap-2">
            <button disabled={!live} onClick={recordingCommand} className="rounded-sm border border-surface-border px-3 py-1.5 text-xs font-mono text-slate-200 disabled:opacity-40 hover:bg-white/5">{recording ? 'Stop recording' : 'Record sortie'}</button>
            {lastSortie && <a className="text-xs font-mono text-accent hover:underline" href={`${serverUrl}/api/v1/recordings/${encodeURIComponent(lastSortie)}/report`} target="_blank" rel="noreferrer">Sortie report</a>}
          </div>
        </div>
        <div className="mt-5 border-t border-surface-border pt-4">
          <div className="text-xs font-medium font-mono text-slate-200 uppercase tracking-wider">Inject a fault valid for this engine</div>
          <div className="mt-2 flex gap-2">
            <select value={faultId} onChange={(e) => setFaultId(e.target.value)} className="min-w-0 flex-1 rounded-sm border border-surface-border bg-surface-card px-2.5 py-2 text-xs font-mono text-slate-200"><option value="">Choose fault…</option>{faults.map((f) => <option key={f.id} value={f.id}>{f.id} · {title(f.name)}</option>)}</select>
            {fault?.scope === 'CYLINDER' && profile && <select value={cylinder} onChange={(e) => setCylinder(Number(e.target.value))} className="rounded-sm border border-surface-border bg-surface-card px-2 text-xs font-mono text-slate-200">{Array.from({ length: profile.cylinders }, (_, i) => <option key={i + 1} value={i + 1}>Cyl {i + 1}</option>)}</select>}
          </div>
          {fault && <div className="mt-2 flex items-center justify-between gap-2 font-mono"><span className="text-xs text-slate-400">{fault.description}</span><span className="text-xs text-accent font-semibold">{severity != null ? `${Math.round(severity * 100)}%` : NO_DATA}</span></div>}
          {fault && severity != null && <input aria-label="Fault severity" className="mt-2 w-full" type="range" min="0.05" max="1" step="0.05" value={severity} onChange={(e) => setSeverity(Number(e.target.value))} />}
          <button disabled={!fault || !live} onClick={inject} className="mt-2 w-full rounded-sm bg-accent text-white px-3 py-2 text-xs font-mono font-medium disabled:opacity-40 hover:bg-accent/90 transition-colors shadow-sm"><Zap className="inline w-3.5 h-3.5 mr-1.5" />Inject scenario</button>
          {activeFaults.length > 0 && <div className="mt-3 rounded-sm border border-surface-border bg-white/[0.03] p-2.5"><div className="flex items-center justify-between text-xs font-mono text-slate-200"><span>Injected scenarios (training display)</span><button title="Clear injected faults" onClick={() => void run(() => runtime.command('/faults?source=console', 'DELETE'), 'Injected scenarios cleared')} className="flex items-center gap-1 text-slate-200 hover:underline"><RotateCcw className="w-3 h-3" /> Clear all</button></div><div className="mt-1 text-xs font-mono text-slate-300">{activeFaults.map((f) => `${f.fault_id} ${title(f.name)}${f.cylinder ? ` · cyl ${f.cylinder}` : ''} · ${f.source}${f.simulated ? '' : ' · not yet simulated'}`).join('  /  ')}</div></div>}
        </div>
      </section>}
    </div>


    {show('MISSION') && <RoutePlannerPanel engineId={runtime.engineId ?? null} api={runtime.api} />}

    {show('ENGINEER') && <EngineerPanel residuals={state?.residuals} twin={state?.twin as any}
      virtualSensors={state?.virtual_sensors} vibration={state?.vibration_orders} />}

    {show('ENGINEER') && <section className="surface-panel p-4 sm:p-5 rounded-sm">
      <div className="flex items-center justify-between gap-3"><div><h3 className="font-semibold text-white">Live engine channels</h3><p className="text-xs text-slate-500 mt-1">From the v1 state message · {state?.evidence_class ?? 'SIMULATION'} evidence</p></div><Radio className="w-4 h-4 text-slate-500" /></div>
      {readings.length ? <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">{readings.map(([name, r]) => <div key={name} className="rounded border border-white/[0.06] bg-black/10 px-3 py-2"><div className="truncate text-xs text-slate-500" title={name}>{channelLabel(labels, name)}{r.quality !== 'OK' ? ` · ${r.quality}` : ''}</div><div className="mt-1 text-sm font-medium tabular-nums text-slate-200">{num(r.value, 2)}<span className="ml-1 text-xs text-slate-500">{r.unit}</span></div></div>)}</div> : <div className="mt-4 text-sm text-slate-500">Waiting for calibrated engine frames…</div>}
    </section>}
    <div className="flex items-start gap-2 px-1 text-xs leading-relaxed text-slate-600"><CircleHelp className="w-3.5 h-3.5 shrink-0 mt-0.5" /><span>This console runs virtual plant data (SIMULATION evidence). Detection, isolation and status read only the measured channels; injected scenarios are shown for training only.</span></div>
  </div></LabelsContext.Provider>;
}
