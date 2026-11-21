import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, AlertTriangle, CheckCircle2, Clock, Info, Lock, Sparkles, X } from 'lucide-react';

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

/**
 * 3D twin view: the engine fills the screen and everything is accessible via keyboard and mouse.
 * Features an anti-spam telemetry interlock that blocks successive fault injections during the
 * aero-thermal transient propagation window (~2.8s) so the single-fault physics and 3D highlight
 * finish framing before further perturbations.
 */
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

  // only faults that light a part of THIS engine's model (sensor faults and parts missing from the model stay in the
  // console); the 3D twin is for watching a fault land on the engine
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

  // Reset page and settling when engine changes
  useEffect(() => {
    setPage(0);
    setCyl(1);
    setSettlingUntil(null);
    setSettlingFault(null);
    setRemainingMs(0);
  }, [p.engineId]);

  // Telemetry interlock timer loop
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
    if (!isSettling) return 'TELEMETRY BUS READY · 20 HZ NOMINAL';
    if (progress < 0.33) return '1/3 AERO-THERMAL TRANSIENT INGESTION';
    if (progress < 0.66) return '2/3 UKF RESIDUAL ESTIMATION & ISOLATION';
    return '3/3 3D MESH LOCALIZATION & CAMERA LOCK';
  }, [isSettling, progress]);

  // Keep a ref to current settling state for the keydown listener to avoid stale closure
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
        say('Telemetry interlock active: physical transient propagating...');
        return;
      }
      const perCyl = f.scope === 'CYLINDER';
      const faultTitle = title(f.name);

      // Lock new injections and start the avionics settling progression
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
      if (el && ['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) return; // typing elsewhere wins
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const k = e.key.toLowerCase();

      // Guide toggle bindings
      if (k === '?' || (k === 'h' && !showGuideRef.current)) {
        setShowGuide((s) => !s);
        e.preventDefault();
        return;
      }
      if (e.key === 'Escape') {
        if (showGuideRef.current) {
          setShowGuide(false);
          e.preventDefault();
          return;
        }
      }

      // If guide modal is open, suppress other controls
      if (showGuideRef.current) return;

      if (k >= '1' && k <= '9') {
        const f = shown[Number(k) - 1];
        if (f) inject(f);
      } else if (k === '0') {
        // Clearing faults unlocks settling immediately
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
        // Resetting engine also unlocks settling immediately
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
    'inline-flex h-6 min-w-6 items-center justify-center rounded-[3px] border border-surface-border-strong bg-surface-card px-1.5 font-mono text-[11px] text-slate-200 shadow-[0_1px_0_rgba(0,0,0,0.25)]';

  const injectFault = (f: Fault) => {
    if (isSettling) {
      setNotice('Telemetry interlock active: physical transient propagating...');
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

      {/* Top right toolbar: Powerplant selector & Info guide button */}
      <div className="absolute right-4 top-4 flex items-center gap-2 z-10">
        <label className="surface-panel flex items-center gap-3 rounded-sm px-3 py-2 shadow-sm">
          <span className={label}>Powerplant</span>
          <select
            value={p.engineId ?? ''}
            onChange={(e) => p.onSelectEngine(e.target.value)}
            className="bg-transparent text-xs font-mono text-white outline-none"
          >
            {p.engines.map((e) => (
              <option key={e.engine_id} value={e.engine_id}>
                {e.display_name ?? e.engine_id}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          onClick={() => setShowGuide(true)}
          className="surface-panel flex items-center gap-1.5 rounded-sm px-2.5 py-2 text-xs font-mono text-slate-300 hover:text-white hover:border-surface-border-strong transition-colors shadow-sm"
          title="Digital Twin & Telemetry Architecture Guide (Press ?)"
        >
          <Info className="w-3.5 h-3.5 text-accent" />
          <span className="font-semibold text-slate-200">Twin Guide</span>
          <kbd className={key}>?</kbd>
        </button>
      </div>

      {/* Left: Faults control panel with anti-spam telemetry interlock */}
      <aside
        className="surface-panel absolute left-4 top-4 w-[min(320px,calc(100%-2rem))] rounded-sm p-3 shadow-card z-10"
        aria-label="Keyboard fault controls"
      >
        <div className="flex items-center justify-between">
          <span className={label}>Inject a fault</span>
          <span className="font-mono text-[11px] text-slate-500">
            page {page + 1}/{pages}
          </span>
        </div>

        {/* Tactical Telemetry Settling Interlock HUD */}
        <div className="mt-2.5 rounded-sm border border-surface-border bg-black/10 p-2 font-mono">
          {isSettling ? (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px]">
                <span className="flex items-center gap-1.5 text-accent font-semibold tracking-wide">
                  <Activity className="w-3.5 h-3.5 animate-pulse" />
                  <span>TRANSIENT PROPAGATION</span>
                </span>
                <span className="font-bold text-accent">{(remainingMs / 1000).toFixed(1)}s</span>
              </div>

              {/* Segmented LED Bar */}
              <div className="flex items-center gap-0.5">
                {Array.from({ length: 12 }).map((_, idx) => {
                  const filled = (idx + 1) / 12 <= progress;
                  return (
                    <div
                      key={idx}
                      className={`h-2 flex-1 rounded-[1px] transition-colors duration-100 ${
                        filled
                          ? 'bg-accent shadow-[0_0_6px_rgba(189,75,43,0.45)]'
                          : 'bg-surface-border/40'
                      }`}
                    />
                  );
                })}
              </div>

              {/* Telemetry Stage Readout */}
              <div className="flex items-center justify-between text-[10px] text-slate-400">
                <span className="truncate">{phaseText}</span>
                <span className="text-slate-500 shrink-0 ml-1">{Math.round(progress * 100)}%</span>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between text-[11px]">
              <span className="flex items-center gap-1.5 text-success">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span className="font-medium text-slate-300">TELEMETRY BUS READY</span>
              </span>
              <span className="text-[10px] text-slate-500">20 HZ NOMINAL</span>
            </div>
          )}
        </div>

        {/* Fault Buttons List */}
        <ol className="mt-2 space-y-1">
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
                      ? 'Telemetry interlock active: awaiting physical transient to settle'
                      : `Inject ${title(f.name)} (Key: ${i + 1})`
                  }
                  className={`w-full flex items-center justify-between gap-2 rounded-sm border px-2 py-1.5 text-xs text-left transition-all ${
                    isThisSettling
                      ? 'border-accent bg-accent-dim text-white font-medium'
                      : isActive
                      ? 'border-surface-border-strong bg-white/[0.06] text-slate-200'
                      : isSettling
                      ? 'border-surface-border/40 bg-black/5 text-slate-500 opacity-60 cursor-not-allowed'
                      : 'border-transparent hover:border-surface-border-strong hover:bg-white/[0.05] text-slate-200 cursor-pointer'
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <kbd className={`${key} ${isSettling ? 'opacity-50' : ''}`}>{i + 1}</kbd>
                    <span className="truncate font-sans">
                      {title(f.name)}
                      {f.scope === 'CYLINDER' ? (
                        <span className="text-slate-500 font-mono"> · cyl {cyl}</span>
                      ) : null}
                    </span>
                  </div>
                  {isThisSettling ? (
                    <span className="text-[10px] font-mono text-accent uppercase tracking-wider shrink-0 flex items-center gap-1">
                      <Lock className="w-2.5 h-2.5" />
                      <span>PROPAGATING</span>
                    </span>
                  ) : isActive ? (
                    <span className="text-[10px] font-mono text-cyan-600 uppercase tracking-wider shrink-0">
                      ACTIVE
                    </span>
                  ) : isSettling ? (
                    <Lock className="w-2.5 h-2.5 text-slate-500 shrink-0" />
                  ) : null}
                </button>
              </li>
            );
          })}
        </ol>

        {/* Keyboard bindings grid */}
        <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 border-t border-surface-border pt-3 text-[11px] text-slate-400">
          <span>
            <kbd className={key}>0</kbd> clear all
          </span>
          <span>
            <kbd className={key}>Q</kbd>
            <kbd className={`${key} ml-1`}>E</kbd> page
          </span>
          <span>
            <kbd className={key}>C</kbd> cylinder {cyl}
          </span>
          <span>
            <kbd className={key}>F</kbd> focus
          </span>
          <span>
            <kbd className={key}>T</kbd> training {p.training ? 'on' : 'off'}
          </span>
          <span>
            <kbd className={key}>R</kbd> reset engine
          </span>
        </div>
      </aside>

      {/* Bottom: Annunciator with live settling indicator */}
      <div
        className={`surface-panel absolute inset-x-4 bottom-4 rounded-sm border-l-4 px-4 py-2.5 z-10 ${
          status && STRIP[status] ? STRIP[status] : 'border-l-surface-border text-slate-200'
        }`}
        aria-live="polite"
      >
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="font-mono text-sm font-semibold tracking-wider">
            {status ?? 'NO DATA'}
          </span>
          {reason && status !== 'GO' && <span className="text-xs text-slate-200">{reason}</span>}
          {isSettling && (
            <span className="inline-flex items-center gap-1.5 text-xs font-mono text-accent font-medium">
              <Activity className="w-3 h-3 animate-pulse" />
              <span>settling transient: {settlingFault?.name} [{(remainingMs / 1000).toFixed(1)}s]</span>
            </span>
          )}
          {active.length > 0 && highlights.length === 0 && !isSettling && (
            <span className="text-xs text-slate-300">diagnosing…</span>
          )}
          {active.length > 0 && (
            <span className="text-xs text-slate-400">
              injected {active.map((f) => `${f.fault_id}${f.cylinder ? `·c${f.cylinder}` : ''}`).join('  ')}
            </span>
          )}
          {notice && <span className="ml-auto text-xs opacity-90 font-mono">{notice}</span>}
        </div>
        {highlights.length > 0 && (
          <div className="mt-1 font-mono text-[11px] text-slate-400">
            {highlights.map((h) => `${h.component_id.replace(/_/g, ' ')} — ${h.reason}`).join('   ·   ')}
          </div>
        )}
      </div>

      {/* System Architecture & Telemetry Guide Modal */}
      {showGuide && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in"
          onClick={() => setShowGuide(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="guide-title"
        >
          <div
            className="surface-panel w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-sm p-5 shadow-card-lg border border-surface-border-strong text-slate-200"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-start justify-between border-b border-surface-border pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <Info className="w-4 h-4 text-accent" />
                  <h2
                    id="guide-title"
                    className="text-sm font-semibold tracking-tight uppercase font-mono text-white"
                  >
                    3D Digital Twin · Telemetry & Physics Architecture
                  </h2>
                </div>
                <p className="mt-1 text-xs text-slate-400 font-mono">
                  ANUMAAN Multi-Physics Propagation & Diagnostic Isolation Architecture
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowGuide(false)}
                className="rounded-sm p-1 text-slate-400 hover:text-white hover:bg-black/10 transition-colors"
                title="Close guide (Esc)"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Content Sections */}
            <div className="mt-4 space-y-3.5 text-xs font-mono leading-relaxed">
              {/* Section 1 */}
              <div className="rounded-sm border border-surface-border bg-black/10 p-3">
                <div className="flex items-center gap-1.5 text-accent font-semibold uppercase tracking-wider text-[11px]">
                  <Activity className="w-3.5 h-3.5" />
                  <span>1. Zero-Falsification Dynamic Simulation</span>
                </div>
                <p className="mt-1 text-slate-300">
                  Readings are never mocked or generated via synthetic random values. Every cylinder temperature,
                  manifold pressure, vibration harmonic, and fuel flow rate is dynamically computed in real time by
                  20 Hz thermodynamic differential equations. Injected faults alter underlying physical parameters
                  (e.g., injector flow area, boost leak orifice, cooling jacket conductance).
                </p>
              </div>

              {/* Section 2 */}
              <div className="rounded-sm border border-surface-border bg-black/10 p-3">
                <div className="flex items-center gap-1.5 text-accent font-semibold uppercase tracking-wider text-[11px]">
                  <Clock className="w-3.5 h-3.5" />
                  <span>2. Why Highlight Animations Take ~2.5 Seconds</span>
                </div>
                <p className="mt-1 text-slate-300">
                  An aero-piston powerplant exhibits real thermal and mechanical inertia. When a fault is injected,
                  its physical effects propagate across three sequential stages:
                </p>
                <div className="mt-2 space-y-1.5 pl-2 border-l-2 border-surface-border">
                  <div>
                    <span className="font-semibold text-slate-200">
                      Stage 1 · Aero-Thermal Transient Ingestion (~0.9s):
                    </span>
                    <span className="text-slate-400">
                      {' '}Cylinder heat, boost pressure, or oil flows shift according to thermal mass and fluid dynamics.
                    </span>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-200">
                      Stage 2 · Telemetry & UKF Residual Isolation (~1.0s):
                    </span>
                    <span className="text-slate-400">
                      {' '}Measured sensor channels stream to the Unscented Kalman Filter state observer to compute analytical residuals without truth-leak.
                    </span>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-200">
                      Stage 3 · 3D Spatial Framing & Emissive Pulse (~0.9s):
                    </span>
                    <span className="text-slate-400">
                      {' '}The camera vector orbits outside the engine cowl, frames the faulty component, and initiates the diagnostic breathing pulse.
                    </span>
                  </div>
                </div>
              </div>

              {/* Section 3 */}
              <div className="rounded-sm border border-surface-border bg-black/10 p-3">
                <div className="flex items-center gap-1.5 text-accent font-semibold uppercase tracking-wider text-[11px]">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>3. Anti-Spam Telemetry Interlock</span>
                </div>
                <p className="mt-1 text-slate-300">
                  Rapidly spamming multiple fault injections simultaneously induces cascading multi-point failures,
                  causing all engine components to illuminate concurrently. The 2.8s interlock preserves simulation
                  fidelity by allowing the physical transient to settle before accepting subsequent perturbations.
                </p>
              </div>

              {/* Section 4 */}
              <div className="rounded-sm border border-surface-border bg-black/10 p-3">
                <div className="flex items-center gap-1.5 text-accent font-semibold uppercase tracking-wider text-[11px]">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>4. Flight Deck Controls Reference</span>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-[11px]">
                  <div className="flex items-center gap-2">
                    <kbd className={key}>1-9</kbd>
                    <span>Inject fault on current page</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <kbd className={key}>0</kbd>
                    <span>Clear all active faults</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <kbd className={key}>Q</kbd>
                    <kbd className={key}>E</kbd>
                    <span>Previous / next page</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <kbd className={key}>C</kbd>
                    <span>Cycle target cylinder (1-4)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <kbd className={key}>F</kbd>
                    <span>Refocus camera on fault</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <kbd className={key}>T</kbd>
                    <span>Toggle training highlight (violet)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <kbd className={key}>R</kbd>
                    <span>Cold reset & restart engine</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <kbd className={key}>?</kbd>
                    <span>Toggle this guide</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="mt-5 flex items-center justify-between border-t border-surface-border pt-3">
              <span className="text-[11px] font-mono text-slate-400">ANUMAAN · SIH PS-26054</span>
              <button
                type="button"
                onClick={() => setShowGuide(false)}
                className="rounded-sm bg-accent px-3 py-1.5 text-xs font-mono font-medium text-white hover:bg-accent/90 transition-colors shadow-sm"
              >
                Acknowledge & Close [Esc]
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
