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
const LEVEL_TEXT: Record<string, string> = { 'NO-GO': 'text-critical', CAUTION: 'text-warning', ADVISORY: 'text-cyan-700' };
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
      else return;
      e.preventDefault();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [shown, cyl, pages, p]);

  const highlights = (p.state?.highlights ?? []) as Array<{ component_id: string; level: string; reason: string }>;
  return (
    <div className="relative h-[calc(100vh-11rem)] min-h-[480px] overflow-hidden rounded-sm border border-surface-border bg-[#e8e7df]">
      <Suspense fallback={<div className="p-6 text-xs font-mono text-slate-500">Loading 3D view…</div>}>
        <EngineViewer3D engineId={p.engineId} highlights={p.state?.highlights} api={p.api} injected={injected} fill focusSignal={focus} bare />
      </Suspense>

      {/* top right: engine */}
      <div className="absolute right-6 top-6 flex items-center gap-2">
        <select value={p.engineId ?? ''} onChange={(e) => p.onSelectEngine(e.target.value)} aria-label="Engine"
          className="rounded-xl border border-slate-200/80 bg-white/60 text-slate-900 shadow-lg backdrop-blur-xl px-4 py-2 text-sm [&>option]:text-black">
          {p.engines.map((e) => <option key={e.engine_id} value={e.engine_id}>{e.display_name ?? e.engine_id}</option>)}
        </select>
      </div>

      {/* left: faults on the keyboard */}
      <aside className="absolute left-6 top-6 w-[min(320px,calc(100%-3rem))] rounded-2xl border border-slate-200/80 bg-white/60 text-slate-900 shadow-lg backdrop-blur-xl p-4 text-xs"
        aria-label="Keyboard fault controls">
        <div className="font-semibold text-slate-900">Inject a fault</div>
        <ol className="mt-2 space-y-0.5 font-mono">
          {shown.map((f, i) => <li key={f.id} className="flex gap-2 text-slate-800">
            <span className="w-4 text-slate-500">{i + 1}</span><span className="truncate">{title(f.name)}{f.scope === 'CYLINDER' ? ` (cyl ${cyl})` : ''}</span>
          </li>)}
        </ol>
        <div className="mt-2 border-t border-slate-200 pt-2 font-mono text-slate-500">
          1-9 inject · 0 clear all · Q/E page {page + 1}/{pages} · C cylinder {cyl} · F focus · T training {p.training ? 'on' : 'off'}
        </div>
      </aside>

      {/* bottom: what is going on */}
      <div className="absolute inset-x-6 bottom-6 rounded-2xl border border-slate-200/80 bg-white/60 text-slate-900 shadow-lg backdrop-blur-xl px-5 py-3 text-sm" aria-live="polite">
        <span className={`font-semibold ${status ? LEVEL_TEXT[status] ?? 'text-slate-900' : 'text-slate-500'}`}>{status ?? 'NO DATA'}</span>
        {reason && status !== 'GO' && <span className="ml-2 text-slate-800">{reason}</span>}
        {active.length > 0 && <span className="ml-3 text-slate-500">Injected: {active.map((f) => `${f.fault_id}${f.cylinder ? ` cyl ${f.cylinder}` : ''}`).join(', ')}</span>}
        {highlights.length > 0 && <div className="mt-1 text-xs text-slate-600">{highlights.map((h) => `${h.level} · ${h.component_id.replace(/_/g, ' ')} · ${h.reason}`).join('   |   ')}</div>}
        {notice && <div className="mt-1 text-xs text-slate-800">{notice}</div>}
      </div>
    </div>
  );
}
