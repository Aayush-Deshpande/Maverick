import { lazy, Suspense, useEffect, useMemo, useState } from 'react';

const EngineViewer3D = lazy(() => import('./viewer3d/EngineViewer3D'));

type Fault = { id: string; name: string; scope?: string; default_severity?: number | null };
type Props = {
  engineId: string | null;
  engines: Array<{ engine_id: string; display_name?: string }>;
  onSelectEngine: (id: string) => void;
  state: any;
  faults: Fault[];
  cylinders: number | null;                       // from the engine profile; null = unknown (C does nothing)
  api: (path: string, method: string, body?: unknown) => Promise<any>;
  command: (path: string, method: string, body?: unknown) => Promise<any>;
  training: boolean;
  onTraining: (on: boolean) => void;
};

const PAGE = 9;                                    // keys 1-9 pick a fault on the current page
// annunciator strip in the status banner's alert colours (D4): red NO-GO, amber CAUTION, cyan ADVISORY
const STRIP: Record<string, string> = { 'NO-GO': 'border-l-critical text-critical', CAUTION: 'border-l-warning text-warning',
  ADVISORY: 'border-l-cyan-600 text-cyan-700' };
const title = (v: string) => v.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
let counter = 0;
const newRequestId = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${++counter}`;

/** 3D twin view: the engine fills the screen and everything is on the keyboard, so the highlighted part is always in
 *  view. Same store, fault API and highlights as the console (state.highlights + component manifests): injecting here
 *  is the same as injecting anywhere else. */
export default function TwinStage(p: Props) {
  const [page, setPage] = useState(0);
  const [cyl, setCyl] = useState(1);
  const [focus, setFocus] = useState(0);
  const [notice, setNotice] = useState('');
  const pages = Math.max(1, Math.ceil(p.faults.length / PAGE));
  const shown = p.faults.slice(page * PAGE, page * PAGE + PAGE);
  const active = (p.state?.active_faults ?? []) as Array<{ fault_id: string; name: string; cylinder?: number | null }>;
  const status = p.state?.status?.level as string | undefined;
  const reason = (p.state?.status?.reasons ?? [])[0]?.text as string | undefined;
  const injected = useMemo(() => p.training ? active.flatMap((f: any) => (f.components ?? []).map((c: string) =>
    ({ component_id: c, reason: `${f.fault_id} ${title(f.name)} (injected)` }))) : [], [p.training, active]);

  useEffect(() => { setPage(0); setCyl(1); }, [p.engineId]);

  useEffect(() => {
    const say = (t: string) => { setNotice(t); window.setTimeout(() => setNotice(''), 3000); };
    const inject = (f: Fault) => {
      const perCyl = f.scope === 'CYLINDER';
      p.command('/faults', 'POST', { fault_id: f.id, cylinder: perCyl ? cyl : undefined, severity: f.default_severity ?? undefined,
        source: '3d', request_id: newRequestId() })
        .then(() => say(`Injected ${title(f.name)}${perCyl ? ` · cylinder ${cyl}` : ''}`))
        .catch((e) => say(e instanceof Error ? e.message : 'Injection failed'));
    };
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && ['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) return;     // typing elsewhere wins
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const k = e.key.toLowerCase();
      if (k >= '1' && k <= '9') { const f = shown[Number(k) - 1]; if (f) inject(f); }
      else if (k === '0') p.command('/faults', 'DELETE').then(() => say('All faults cleared')).catch(() => say('Clear failed'));
      else if (k === 'q') setPage((n) => (n - 1 + pages) % pages);
      else if (k === 'e') setPage((n) => (n + 1) % pages);
      else if (k === 'c') { const n = p.cylinders; if (n) setCyl((c) => (c % n) + 1); }
      else if (k === 'f') setFocus((n) => n + 1);
      else if (k === 't') p.onTraining(!p.training);
      else if (k === 'r') {                          // a seized engine stays seized until reset (R 19.4)
        p.command('/faults', 'DELETE')
          .then(() => p.command('/engine', 'POST', { command: 'RESET' }))
          .then(() => p.command('/engine', 'POST', { command: 'START' }))
          .then(() => p.command('/status/acknowledge', 'POST', {}))
          .then(() => say('Engine reset and restarted')).catch((e) => say(e instanceof Error ? e.message : 'Reset failed'));
      }
      else return;
      e.preventDefault();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [shown, cyl, pages, p]);

  const highlights = (p.state?.highlights ?? []) as Array<{ component_id: string; level: string; reason: string }>;
  const label = 'text-[11px] uppercase tracking-[0.18em] font-mono text-slate-400';
  const key = 'inline-flex h-6 min-w-6 items-center justify-center rounded-[3px] border border-surface-border-strong bg-surface-card px-1.5 font-mono text-[11px] text-slate-200 shadow-[0_1px_0_rgba(0,0,0,0.25)]';
  return (
    <div className="relative left-1/2 w-[calc(100vw-2.5rem)] -translate-x-1/2 h-[calc(100vh-11rem)] min-h-[480px] overflow-hidden rounded-sm border border-surface-border bg-[#e8e7df]">
      <Suspense fallback={<div className="p-6 text-xs font-mono text-slate-400">Loading 3D view…</div>}>
        <EngineViewer3D engineId={p.engineId} highlights={p.state?.highlights} api={p.api} injected={injected} fill focusSignal={focus} bare />
      </Suspense>

      {/* top right: powerplant */}
      <label className="surface-panel absolute right-4 top-4 flex items-center gap-3 rounded-sm px-3 py-2">
        <span className={label}>Powerplant</span>
        <select value={p.engineId ?? ''} onChange={(e) => p.onSelectEngine(e.target.value)}
          className="bg-transparent text-xs font-mono text-white outline-none">
          {p.engines.map((e) => <option key={e.engine_id} value={e.engine_id}>{e.display_name ?? e.engine_id}</option>)}
        </select>
      </label>

      {/* left: faults on the keyboard */}
      <aside className="surface-panel absolute left-4 top-4 w-[min(300px,calc(100%-2rem))] rounded-sm p-3" aria-label="Keyboard fault controls">
        <div className="flex items-center justify-between"><span className={label}>Inject a fault</span>
          <span className="font-mono text-[11px] text-slate-500">page {page + 1}/{pages}</span></div>
        <ol className="mt-2 space-y-1">
          {shown.map((f, i) => <li key={f.id} className="flex items-center gap-2.5 text-xs text-slate-200">
            <kbd className={key}>{i + 1}</kbd><span className="truncate">{title(f.name)}{f.scope === 'CYLINDER' ? <span className="text-slate-500"> · cyl {cyl}</span> : null}</span>
          </li>)}
        </ol>
        <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 border-t border-surface-border pt-3 text-[11px] text-slate-400">
          <span><kbd className={key}>0</kbd> clear all</span><span><kbd className={key}>Q</kbd><kbd className={`${key} ml-1`}>E</kbd> page</span>
          <span><kbd className={key}>C</kbd> cylinder {cyl}</span><span><kbd className={key}>F</kbd> focus</span>
          <span><kbd className={key}>T</kbd> training {p.training ? 'on' : 'off'}</span><span><kbd className={key}>R</kbd> reset engine</span>
        </div>
      </aside>

      {/* bottom: annunciator */}
      <div className={`surface-panel absolute inset-x-4 bottom-4 rounded-sm border-l-4 px-4 py-2.5 ${status && STRIP[status] ? STRIP[status] : 'border-l-surface-border text-slate-200'}`} aria-live="polite">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="font-mono text-sm font-semibold tracking-wider">{status ?? 'NO DATA'}</span>
          {reason && status !== 'GO' && <span className="text-xs text-slate-200">{reason}</span>}
          {active.length > 0 && highlights.length === 0 && <span className="text-xs text-slate-300">diagnosing…</span>}
          {active.length > 0 && <span className="text-xs text-slate-400">injected {active.map((f) => `${f.fault_id}${f.cylinder ? `·c${f.cylinder}` : ''}`).join('  ')}</span>}
          {notice && <span className="ml-auto text-xs opacity-80">{notice}</span>}
        </div>
        {highlights.length > 0 && <div className="mt-1 font-mono text-[11px] text-slate-400">
          {highlights.map((h) => `${h.component_id.replace(/_/g, ' ')} — ${h.reason}`).join('   ·   ')}</div>}
      </div>
    </div>
  );
}
