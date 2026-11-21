import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Activity, AlertTriangle, ArrowDown, ArrowRight, CheckCircle2, Clock, Info, Lock, Sparkles, X } from 'lucide-react';

const EngineViewer3D = lazy(() => import('./viewer3d/EngineViewer3D'));

type Fault = {
  id: string;
  name: string;
  kind?: string;
  scope?: string;
  default_severity?: number | null;
  components?: Record<string, { now?: string[] }>;
};

type Props = {
  engineId: string | null;
  engines: Array<{ engine_id: string; display_name?: string }>;
  onSelectEngine: (id: string) => void;
  state: any;
  faults: Fault[];
  cylinders: number | null; // from the engine profile; null = unknown (C does nothing)
  api: (path: string, method: string, body?: unknown) => Promise<any>;
  command: (path: string, method: string, body?: unknown) => Promise<any>;
  training: boolean;
  onTraining: (on: boolean) => void;
  onNavigateToRuntime?: () => void;
};

const PAGE = 9; // keys 1-9 pick a fault on the current page
const SETTLING_DURATION_MS = 2800; // telemetry & transient convergence window (2.8s)

// annunciator strip in the status banner's alert colours (D4): red NO-GO, amber CAUTION, cyan ADVISORY
const STRIP: Record<string, string> = {
  'NO-GO': 'border-l-critical text-critical',
  CAUTION: 'border-l-warning text-warning',
  ADVISORY: 'border-l-cyan-600 text-cyan-700',
};

const title = (v: string) =>
  v.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

let counter = 0;
const newRequestId = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${++counter}`;

export default function TwinStage(p: Props) {
  const [page, setPage] = useState(0);
  const [cyl, setCyl] = useState(1);
  const [focus, setFocus] = useState(0);
  const [notice, setNotice] = useState('');
  const [showGuide, setShowGuide] = useState(false);

  // Anti-spam telemetry settling interlock state
  const [settlingUntil, setSettlingUntil] = useState<number | null>(null);
  const [settlingFault, setSettlingFault] = useState<{ id: string; name: string } | null>(null);
  const [remainingMs, setRemainingMs] = useState(0);

  const visible = useMemo(
    () =>
      p.faults.filter(
        (f) =>
          f.kind !== 'SENSOR' &&
          (f.components?.[p.engineId ?? '']?.now ?? []).length > 0
      ),
    [p.faults, p.engineId]
  );
  const pages = Math.max(1, Math.ceil(visible.length / PAGE));
  const shown = visible.slice(page * PAGE, page * PAGE + PAGE);
  const active = (p.state?.active_faults ?? []) as Array<{
    fault_id: string;
    name: string;
    cylinder?: number | null;
  }>;
  const status = p.state?.status?.level as string | undefined;
  const reason = (p.state?.status?.reasons ?? [])[0]?.text as string | undefined;
  const injected = useMemo(
    () =>
      p.training
        ? active.flatMap((f: any) =>
            (f.components ?? []).map((c: string) => ({
              component_id: c,
              reason: `${f.fault_id} ${title(f.name)} (injected)`,
            }))
          )
        : [],
    [p.training, active]
  );

  useEffect(() => {
    setPage(0);
    setCyl(1);
    setSettlingUntil(null);
    setSettlingFault(null);
    setRemainingMs(0);
  }, [p.engineId]);

  useEffect(() => {
    if (!settlingUntil) {
      setRemainingMs(0);
      return;
    }
    const update = () => {
      const rem = Math.max(0, settlingUntil - Date.now());
      setRemainingMs(rem);
      if (rem <= 0) {
        setSettlingUntil(null);
        setSettlingFault(null);
      }
    };
    update();
    const interval = window.setInterval(update, 50);
    return () => window.clearInterval(interval);
  }, [settlingUntil]);

  const isSettling = settlingUntil !== null && remainingMs > 0;
  const progress = isSettling ? Math.min(1, Math.max(0, (SETTLING_DURATION_MS - remainingMs) / SETTLING_DURATION_MS)) : 1;

  const phaseText = useMemo(() => {
    if (!isSettling) return 'READY';
    if (progress < 0.33) return '1/3 TRANSIENT INGESTION';
    if (progress < 0.66) return '2/3 UKF ESTIMATION';
    return '3/3 3D VECTOR LOCK';
  }, [isSettling, progress]);

  const isSettlingRef = useRef(isSettling);
  isSettlingRef.current = isSettling;
  const showGuideRef = useRef(showGuide);
  showGuideRef.current = showGuide;

  useEffect(() => {
    const say = (t: string) => {
      setNotice(t);
      window.setTimeout(() => setNotice(''), 3000);
    };

    const inject = (f: Fault) => {
      if (isSettlingRef.current) {
        say('Telemetry bus busy: physical transient propagating');
        return;
      }
      const perCyl = f.scope === 'CYLINDER';
      const faultTitle = title(f.name);

      setSettlingUntil(Date.now() + SETTLING_DURATION_MS);
      setSettlingFault({ id: f.id, name: faultTitle });
      setRemainingMs(SETTLING_DURATION_MS);

      p.command('/faults', 'POST', {
        fault_id: f.id,
        cylinder: perCyl ? cyl : undefined,
        severity: f.default_severity ?? undefined,
        source: '3d',
        request_id: newRequestId(),
      })
        .then(() => say(`Injected ${faultTitle}${perCyl ? ` · cylinder ${cyl}` : ''}`))
        .catch((e) => {
          setSettlingUntil(null);
          setSettlingFault(null);
          setRemainingMs(0);
          say(e instanceof Error ? e.message : 'Injection failed');
        });
    };

    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && ['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const k = e.key.toLowerCase();

      if (k === '?' || (k === 'h' && !showGuideRef.current)) {
        setShowGuide((s) => !s);
        e.preventDefault();
        return;
      }
      if (e.key === 'Escape' && showGuideRef.current) {
        setShowGuide(false);
        e.preventDefault();
        return;
      }
      if (showGuideRef.current) return;

      if (k >= '1' && k <= '9') {
        const f = shown[Number(k) - 1];
        if (f) inject(f);
      } else if (k === '0') {
        setSettlingUntil(null);
        setSettlingFault(null);
        setRemainingMs(0);
        p.command('/faults', 'DELETE')
          .then(() => say('All faults cleared'))
          .catch(() => say('Clear failed'));
      } else if (k === 'q') {
        setPage((n) => (n - 1 + pages) % pages);
      } else if (k === 'e') {
        setPage((n) => (n + 1) % pages);
      } else if (k === 'c') {
        const n = p.cylinders;
        if (n) setCyl((c) => (c % n) + 1);
      } else if (k === 'f') {
        setFocus((n) => n + 1);
      } else if (k === 't') {
        p.onTraining(!p.training);
      } else if (k === 'r') {
        setSettlingUntil(null);
        setSettlingFault(null);
        setRemainingMs(0);
        p.command('/faults', 'DELETE')
          .then(() => p.command('/engine', 'POST', { command: 'RESET' }))
          .then(() => p.command('/engine', 'POST', { command: 'START' }))
          .then(() => p.command('/status/acknowledge', 'POST', {}))
          .then(() => say('Engine reset and restarted'))
          .catch((e) => say(e instanceof Error ? e.message : 'Reset failed'));
      } else {
        return;
      }
      e.preventDefault();
    };

    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [shown, cyl, pages, p]);

  const highlights = (p.state?.highlights ?? []) as Array<{
    component_id: string;
    level: string;
    reason: string;
  }>;
  const label = 'text-[11px] uppercase tracking-[0.18em] font-mono text-slate-400';
  const key =
    'inline-flex h-5 min-w-5 items-center justify-center rounded-[3px] border border-surface-border-strong bg-surface-card px-1 font-mono text-[10px] text-slate-700 shadow-[0_1px_0_rgba(0,0,0,0.15)]';

  const injectFault = (f: Fault) => {
    if (isSettling) {
      setNotice('Telemetry bus busy: physical transient propagating');
      window.setTimeout(() => setNotice(''), 3000);
      return;
    }
    const perCyl = f.scope === 'CYLINDER';
    const faultTitle = title(f.name);

    setSettlingUntil(Date.now() + SETTLING_DURATION_MS);
    setSettlingFault({ id: f.id, name: faultTitle });
    setRemainingMs(SETTLING_DURATION_MS);

    p.command('/faults', 'POST', {
      fault_id: f.id,
      cylinder: perCyl ? cyl : undefined,
      severity: f.default_severity ?? undefined,
      source: '3d',
      request_id: newRequestId(),
    })
      .then(() => {
        setNotice(`Injected ${faultTitle}${perCyl ? ` · cylinder ${cyl}` : ''}`);
        window.setTimeout(() => setNotice(''), 3000);
      })
      .catch((e) => {
        setSettlingUntil(null);
        setSettlingFault(null);
        setRemainingMs(0);
        setNotice(e instanceof Error ? e.message : 'Injection failed');
        window.setTimeout(() => setNotice(''), 3000);
      });
  };

  const cycleCylinder = () => {
    const n = p.cylinders;
    if (n) setCyl((c) => (c % n) + 1);
  };

  const scrollToTelemetry = () => {
    window.scrollBy({ top: 400, behavior: 'smooth' });
  };

  return (
    <div className="relative left-1/2 w-[calc(100vw-2.5rem)] -translate-x-1/2 h-[calc(100vh-11rem)] min-h-[480px] overflow-hidden rounded-sm border border-surface-border bg-[#e8e7df]">
      <Suspense fallback={<div className="p-6 text-xs font-mono text-slate-400">Loading 3D view…</div>}>
        <EngineViewer3D
          engineId={p.engineId}
          highlights={p.state?.highlights}
          api={p.api}
          injected={injected}
          fill
          focusSignal={focus}
          bare
        />
      </Suspense>

      {/* Top right: Unified Powerplant & Guide Toolbar */}
      <div className="surface-panel absolute right-4 top-4 z-10 flex items-center gap-3 rounded-sm px-3 py-1.5 shadow-sm">
        <label className="flex items-center gap-2">
          <span className={label}>Powerplant</span>
          <select
            value={p.engineId ?? ''}
            onChange={(e) => p.onSelectEngine(e.target.value)}
            className="bg-transparent text-xs font-mono text-slate-800 outline-none cursor-pointer"
            title="Select powerplant (Rotax 912 iSc, 914, 915 iSc, Austro AE300, VRDE 2.2L)"
          >
            {p.engines.map((e) => (
              <option key={e.engine_id} value={e.engine_id}>
                {e.display_name ?? e.engine_id}
              </option>
            ))}
          </select>
        </label>
        <div className="h-3.5 w-px bg-surface-border" />
        <button
          type="button"
          onClick={() => setShowGuide(true)}
          className="flex items-center gap-1.5 text-xs font-mono text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
          title="Digital Twin & Telemetry Architecture Guide (Press ?)"
        >
          <Info className="w-3.5 h-3.5 text-accent" />
          <span className="font-semibold text-slate-700">Twin Guide</span>
          <kbd className={key}>?</kbd>
        </button>
      </div>

      {/* Left: Compact, High-Density Fault Controls (fits viewport without overlap) */}
      <aside
        className="surface-panel absolute left-4 top-4 z-10 w-[min(280px,calc(100%-2rem))] max-h-[calc(100%-4.5rem)] overflow-y-auto rounded-sm p-2.5 shadow-card"
        aria-label="Keyboard fault controls"
      >
        {/* Header & Page */}
        <div className="flex items-center justify-between">
          <span className={label}>Inject a fault</span>
          <span className="font-mono text-[10px] text-slate-500">
            page {page + 1}/{pages}
          </span>
        </div>

        {/* High-Precision Avionics Telemetry Settling Line */}
        <div className="mt-1.5 border-b border-surface-border pb-1.5">
          <div className="flex items-center justify-between font-mono text-[10px]">
            {isSettling ? (
              <span className="flex items-center gap-1 text-accent font-semibold">
                <Activity className="w-3 h-3 animate-pulse" />
                <span>PROPAGATING [{(remainingMs / 1000).toFixed(1)}s]</span>
              </span>
            ) : (
              <span className="flex items-center gap-1 text-success">
                <CheckCircle2 className="w-3 h-3" />
                <span className="text-slate-600">TELEMETRY BUS READY</span>
              </span>
            )}
            <span className="text-slate-500 text-[9px] uppercase tracking-wider">{phaseText}</span>
          </div>

          {/* Micro Progress Bar (only 2px high, zero vertical clutter) */}
          <div className="mt-1 h-[2px] w-full rounded-full bg-surface-border/40 overflow-hidden">
            <div
              className={`h-full transition-all duration-75 ${
                isSettling ? 'bg-accent shadow-[0_0_4px_rgba(189,75,43,0.6)]' : 'bg-success/50'
              }`}
              style={{ width: `${Math.round(progress * 100)}%` }}
            />
          </div>
        </div>

        {/* Fault List: Clean, High-Density Rows */}
        <ol className="mt-1.5 space-y-0.5">
          {shown.map((f, i) => {
            const isActive = active.some((a) => a.fault_id === f.id);
            const isThisSettling = isSettling && settlingFault?.id === f.id;
            return (
              <li key={f.id}>
                <button
                  type="button"
                  disabled={isSettling}
                  onClick={() => injectFault(f)}
                  title={
                    isSettling
                      ? 'Telemetry interlock active: physical transient settling'
                      : `Inject ${title(f.name)} (Key: ${i + 1})`
                  }
                  className={`w-full flex items-center justify-between text-left text-xs py-0.5 px-1 rounded-[2px] transition-colors ${
                    isThisSettling
                      ? 'bg-accent/10 text-accent font-medium'
                      : isActive
                      ? 'bg-black/5 text-slate-900 font-medium'
                      : isSettling
                      ? 'opacity-40 cursor-not-allowed text-slate-500'
                      : 'hover:bg-black/5 text-slate-800 cursor-pointer'
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <kbd className={key}>{i + 1}</kbd>
                    <span className="truncate">
                      {title(f.name)}
                      {f.scope === 'CYLINDER' ? (
                        <span className="text-slate-500 font-mono text-[11px]"> · cyl {cyl}</span>
                      ) : null}
                    </span>
                  </div>
                  {isThisSettling ? (
                    <Lock className="w-2.5 h-2.5 text-accent shrink-0 ml-1" />
                  ) : isActive ? (
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-600 shrink-0 ml-1" title="Active fault" />
                  ) : null}
                </button>
              </li>
            );
          })}
        </ol>

        {/* Keyboard Bindings Footer */}
        <div className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1.5 border-t border-surface-border pt-2 text-[10px] font-mono text-slate-500">
          <span className="flex items-center gap-1" title="Press 0 to clear all active injected faults">
            <kbd className={key}>0</kbd> clear all
          </span>
          <span className="flex items-center gap-1" title="Press Q or E to cycle fault catalogue pages">
            <kbd className={key}>Q</kbd>
            <kbd className={key}>E</kbd> page
          </span>
          <button
            type="button"
            onClick={cycleCylinder}
            className="flex items-center gap-1 text-left text-slate-700 hover:text-slate-900 font-medium transition-colors cursor-pointer"
            title="Click or press C to cycle target cylinder (1-4) for single-cylinder faults like misfires"
          >
            <kbd className={key}>C</kbd>
            <span>cyl {cyl}/{p.cylinders ?? 4}</span>
          </button>
          <span className="flex items-center gap-1" title="Press F to focus 3D camera on diagnosed faulty part">
            <kbd className={key}>F</kbd> focus
          </span>
          <span className="flex items-center gap-1" title="Press T to toggle training highlight ghost (violet)">
            <kbd className={key}>T</kbd> train {p.training ? 'on' : 'off'}
          </span>
          <span className="flex items-center gap-1" title="Press R to cold reset & restart engine">
            <kbd className={key}>R</kbd> reset
          </span>
        </div>
      </aside>

      {/* Bottom: Annunciator Strip with quick navigation */}
      <div
        className={`surface-panel absolute inset-x-4 bottom-4 rounded-sm border-l-4 px-4 py-2 z-10 ${
          status && STRIP[status] ? STRIP[status] : 'border-l-surface-border text-slate-800'
        }`}
        aria-live="polite"
      >
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span
            className="font-mono text-sm font-semibold tracking-wider"
            title="14 CFR 25.1322 flight deck alert level: GO (nominal), CAUTION (amber), NO-GO (red)"
          >
            {status ?? 'NO DATA'}
          </span>
          {reason && status !== 'GO' && <span className="text-xs text-slate-700">{reason}</span>}
          {isSettling && (
            <span className="inline-flex items-center gap-1 text-xs font-mono text-accent font-medium">
              <Activity className="w-3 h-3 animate-pulse" />
              <span>settling transient: {settlingFault?.name} [{(remainingMs / 1000).toFixed(1)}s]</span>
            </span>
          )}
          {active.length > 0 && highlights.length === 0 && !isSettling && (
            <span className="text-xs text-slate-500">diagnosing…</span>
          )}
          {active.length > 0 && (
            <span className="text-xs text-slate-600 font-mono">
              injected {active.map((f) => `${f.fault_id}${f.cylinder ? `·c${f.cylinder}` : ''}`).join('  ')}
            </span>
          )}

          {/* Quick links to live telemetry stream and full console */}
          <div className="ml-auto flex items-center gap-2">
            <button
              type="button"
              onClick={scrollToTelemetry}
              className="inline-flex items-center gap-1 text-xs font-mono text-slate-600 hover:text-slate-900 transition-colors"
              title="Scroll down to view live 20 Hz telemetry numbers and thermodynamic equations"
            >
              <ArrowDown className="w-3 h-3 text-accent" />
              <span>Live Telemetry Numbers ↓</span>
            </button>
            {p.onNavigateToRuntime && (
              <>
                <span className="text-slate-300">|</span>
                <button
                  type="button"
                  onClick={p.onNavigateToRuntime}
                  className="inline-flex items-center gap-1 text-xs font-mono text-accent hover:underline font-medium"
                >
                  <span>Engine Runtime Console</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </>
            )}
            {notice && <span className="text-xs opacity-90 font-mono text-slate-600 ml-2">{notice}</span>}
          </div>
        </div>
        {highlights.length > 0 && (
          <div className="mt-1 font-mono text-[11px] text-slate-600">
            {highlights.map((h) => `${h.component_id.replace(/_/g, ' ')} — ${h.reason}`).join('   ·   ')}
          </div>
        )}
      </div>

      {/* System Guide Modal - rendered via createPortal so it escapes container bounds & transforms */}
      {showGuide && typeof document !== 'undefined' && createPortal(
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in"
          onClick={() => setShowGuide(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="guide-title"
        >
          <div
            className="surface-panel w-full max-w-xl max-h-[85vh] flex flex-col rounded-sm shadow-card-lg border border-surface-border-strong text-slate-800 bg-[#f7f6f0] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header - pinned at top */}
            <div className="flex items-start justify-between border-b border-surface-border p-4 shrink-0 bg-[#f7f6f0]">
              <div>
                <div className="flex items-center gap-2">
                  <Info className="w-4 h-4 text-accent" />
                  <h2
                    id="guide-title"
                    className="text-sm font-semibold tracking-tight uppercase font-mono text-slate-900"
                  >
                    3D Digital Twin · Telemetry & Physics Architecture
                  </h2>
                </div>
                <p className="mt-1 text-xs text-slate-500 font-mono">
                  ANUMAAN Multi-Physics Propagation & Diagnostic Isolation Architecture
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowGuide(false)}
                className="rounded-sm p-1.5 text-slate-400 hover:text-slate-800 hover:bg-black/10 transition-colors"
                title="Close guide (Esc)"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Scrollable Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs font-mono leading-relaxed">
              <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
                <div className="flex items-center gap-1.5 text-accent font-semibold uppercase tracking-wider text-[11px]">
                  <Activity className="w-3.5 h-3.5" />
                  <span>1. Zero-Falsification Dynamic Simulation</span>
                </div>
                <p className="mt-1 text-slate-600">
                  Readings are never mocked or generated via synthetic random values. Every cylinder temperature,
                  manifold pressure, and vibration harmonic is dynamically computed in real time by 20 Hz
                  thermodynamic differential equations.
                </p>
              </div>

              <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
                <div className="flex items-center gap-1.5 text-accent font-semibold uppercase tracking-wider text-[11px]">
                  <Clock className="w-3.5 h-3.5" />
                  <span>2. Why Highlight Animations Take ~2.5 Seconds</span>
                </div>
                <p className="mt-1 text-slate-600">
                  A real powerplant has thermal and mechanical inertia. When a fault is injected, its physical effects
                  propagate sequentially:
                </p>
                <div className="mt-2 space-y-1 pl-2 border-l-2 border-surface-border text-[11px]">
                  <div>
                    <span className="font-semibold text-slate-800">Stage 1 · Transient Ingestion (~0.9s):</span>
                    <span className="text-slate-600"> Thermal & pressure lag across engine manifolds.</span>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-800">Stage 2 · UKF Residuals (~1.0s):</span>
                    <span className="text-slate-600"> Observer computes analytical residuals without truth-leak.</span>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-800">Stage 3 · 3D Framing & Glow (~0.9s):</span>
                    <span className="text-slate-600"> Camera frames the component and pulses the emissive glow.</span>
                  </div>
                </div>
              </div>

              <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
                <div className="flex items-center gap-1.5 text-accent font-semibold uppercase tracking-wider text-[11px]">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>3. Anti-Spam Telemetry Interlock</span>
                </div>
                <p className="mt-1 text-slate-600">
                  Spamming multiple fault injections simultaneously induces cascading multi-point failures, causing all
                  engine components to illuminate concurrently. The 2.8s interlock preserves simulation fidelity by
                  allowing the physical transient to settle before accepting subsequent perturbations.
                </p>
              </div>

              <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
                <div className="flex items-center gap-1.5 text-accent font-semibold uppercase tracking-wider text-[11px]">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>4. Flight Deck Controls Reference</span>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-1.5 text-[11px]">
                  <div className="flex items-center gap-1.5"><kbd className={key}>1-9</kbd><span>Inject fault</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>0</kbd><span>Clear all faults</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>Q/E</kbd><span>Page switch</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>C</kbd><span>Cycle target cylinder (1-4)</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>F</kbd><span>Refocus camera</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>T</kbd><span>Training highlight</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>R</kbd><span>Reset & restart</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>?</kbd><span>Toggle guide</span></div>
                </div>
              </div>
            </div>

            {/* Modal Footer - pinned at bottom */}
            <div className="flex items-center justify-between border-t border-surface-border p-3.5 shrink-0 bg-[#f7f6f0]">
              <span className="text-[11px] font-mono text-slate-500">ANUMAAN · SIH PS-26054</span>
              <button
                type="button"
                onClick={() => setShowGuide(false)}
                className="rounded-sm bg-accent px-3 py-1.5 text-xs font-mono font-medium text-white hover:bg-accent/90 transition-colors shadow-sm"
              >
                Acknowledge & Close [Esc]
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
