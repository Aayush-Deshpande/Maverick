import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Activity, AlertTriangle, ArrowDown, ArrowRight, Box, CheckCircle2, Clock, Flame, Info, Lock, Radio, RotateCw, ScanLine, Search, Sparkles, X, Zap } from 'lucide-react';
import InfoTooltip from './InfoTooltip';
import CommandPalette from './CommandPalette';
import type { EngineViewMode } from './viewer3d/EngineViewer3D';
import type { Highlight } from '../api/state';

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
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [viewMode, setViewMode] = useState<EngineViewMode>('solid');
  const [autoRotate, setAutoRotate] = useState(true);
  const [mobileControlsOpen, setMobileControlsOpen] = useState(false);

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
    uuid?: string;
    fault_id: string;
    name: string;
    cylinder?: number | null;
  }>;
  const status = p.state?.status?.level as string | undefined;
  const rawReason = (p.state?.status?.reasons ?? [])[0]?.text as string | undefined;
  const reason = useMemo(() => {
    if (!rawReason || status === 'GO') return undefined;
    if (active.length === 0 && (rawReason.includes('S02') || rawReason.includes('SENSOR_BIAS') || rawReason.includes('Sensor bias'))) {
      return undefined;
    }
    return rawReason;
  }, [rawReason, status, active.length]);
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

  const notify = useCallback((text: string) => {
    setNotice(text);
    window.setTimeout(() => setNotice(''), 3000);
  }, []);

  const clearAllFaults = useCallback(() => {
    setSettlingUntil(null);
    setSettlingFault(null);
    setRemainingMs(0);
    Promise.all([
      p.command('/faults', 'DELETE').catch(() => {}),
      p.command('/engine', 'POST', { command: 'RESET' }).catch(() => {}),
      p.command('/status/acknowledge', 'POST', {}).catch(() => {}),
    ])
      .then(() => notify('All faults cleared · Nominal state restored'))
      .catch(() => notify('Clear failed'));
  }, [p, notify]);

  const clearOneFault = useCallback(() => {
    if (active.length === 0) {
      notify('No active faults to clear');
      return;
    }
    const last = active[active.length - 1];
    setSettlingUntil(null);
    setSettlingFault(null);
    setRemainingMs(0);
    const deletePath = last.uuid ? `/faults/${encodeURIComponent(last.uuid)}` : '/faults';
    const pms: Promise<any>[] = [p.command(deletePath, 'DELETE')];
    if (active.length <= 1) {
      pms.push(p.command('/engine', 'POST', { command: 'RESET' }).catch(() => {}));
      pms.push(p.command('/status/acknowledge', 'POST', {}).catch(() => {}));
    }
    Promise.all(pms)
      .then(() => {
        const remaining = Math.max(0, active.length - 1);
        notify(`Cleared ${last.fault_id} ${title(last.name)}${remaining > 0 ? ` (${remaining} remaining)` : ' · Nominal restored'}`);
      })
      .catch(() => notify('Clear failed'));
  }, [active, p, notify]);

  // Keep engine RUNNING by default; auto-start if in ENGINE_OFF state
  useEffect(() => {
    if (status === 'ENGINE_OFF') {
      const t = window.setTimeout(() => {
        p.command('/engine', 'POST', { command: 'START' }).catch(() => {});
      }, 400);
      return () => window.clearTimeout(t);
    }
  }, [status, p]);

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

      if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
        return;
      }
      if (e.key === '/' && !commandPaletteOpen && !showGuideRef.current) {
        e.preventDefault();
        setCommandPaletteOpen(true);
        return;
      }
      if (e.key === 'Escape') {
        if (commandPaletteOpen) {
          setCommandPaletteOpen(false);
          e.preventDefault();
          return;
        }
        if (showGuideRef.current) {
          setShowGuide(false);
          e.preventDefault();
          return;
        }
      }
      if (commandPaletteOpen) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const k = e.key.toLowerCase();

      if (k === '?' || (k === 'h' && !showGuideRef.current)) {
        setShowGuide((s) => !s);
        e.preventDefault();
        return;
      }
      if (showGuideRef.current) return;

      if (k >= '1' && k <= '9') {
        const f = shown[Number(k) - 1];
        if (f) inject(f);
      } else if (k === 'x' || k === '0' || e.key === 'Delete') {
        clearAllFaults();
      } else if (k === 'z' || k === 'r' || e.key === 'Backspace' || k === 'u') {
        clearOneFault();
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
      } else if (k === 'v') {
        const modes: EngineViewMode[] = ['solid', 'glass', 'thermal', 'ghost'];
        setViewMode((current) => {
          const next = modes[(modes.indexOf(current) + 1) % modes.length];
          const modeLabels: Record<EngineViewMode, string> = {
            solid: 'CAD Surface',
            glass: 'X-Ray Casing',
            thermal: 'Thermal FLIR',
            ghost: 'Nominal Baseline',
          };
          say(`View: ${modeLabels[next]}`);
          return next;
        });
      } else {
        return;
      }
      e.preventDefault();
    };

    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [shown, cyl, pages, p, clearAllFaults, clearOneFault]);

  const rawHighlights = (p.state?.highlights ?? []) as Highlight[];
  const highlights = useMemo(() => {
    return rawHighlights.filter((h) => {
      const r = (h.reason || '') as string;
      if (active.length === 0 && (r.includes('S02') || r.includes('SENSOR_BIAS') || r.includes('Sensor bias'))) {
        return false;
      }
      return true;
    });
  }, [rawHighlights, active.length]);
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
    <div className="relative left-1/2 w-[calc(100vw-1.5rem)] sm:w-[calc(100vw-2.5rem)] -translate-x-1/2 h-[calc(100vh-12rem)] min-h-[420px] sm:min-h-[480px] overflow-hidden rounded-sm border border-surface-border bg-[#e8e7df]">
      <Suspense fallback={<div className="absolute inset-0 flex items-center justify-center p-6 text-xs font-mono text-slate-400">Loading 3D view…</div>}>
        <EngineViewer3D
          engineId={p.engineId}
          highlights={highlights}
          api={p.api}
          injected={injected}
          fill
          focusSignal={focus}
          bare
          autoRotate={autoRotate}
          readings={p.state?.readings}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />
      </Suspense>

      {/* Top Navigation & Viewport Bar: Compact responsive single-row bar */}
      <header className="surface-panel absolute inset-x-2 sm:inset-x-4 top-2 sm:top-2.5 z-20 flex items-center justify-between gap-1.5 sm:gap-3 rounded-sm px-2.5 sm:px-3 py-1 shadow-sm text-xs font-mono">
        {/* Left Section: Powerplant selector & Command Palette */}
        <div className="flex items-center gap-1.5 sm:gap-2.5 min-w-0">
          <label className="flex items-center gap-1 shrink-0" title="Select propulsion platform (Rotax 912 iSc, 914, 915 iSc, Austro AE300, VRDE 2.2L)">
            <span className="sr-only">Powerplant</span>
            <select
              value={p.engineId ?? ''}
              onChange={(e) => p.onSelectEngine(e.target.value)}
              className="bg-black/[0.04] border border-surface-border rounded-xs px-1.5 sm:px-2 py-0.5 text-xs font-mono font-semibold text-slate-800 outline-none cursor-pointer max-w-[130px] sm:max-w-none truncate"
              aria-label="Powerplant"
            >
              {p.engines.map((e) => (
                <option key={e.engine_id} value={e.engine_id}>
                  {e.display_name ?? e.engine_id}
                </option>
              ))}
            </select>
            <InfoTooltip
              title="Select Propulsion Platform"
              content="Switches the active digital twin between all 5 aero piston engine models: Rotax 912 iSc, Rotax 914, Rotax 915 iSc, Austro AE300, and VRDE 2.2L."
              placement="bottom"
              width={260}
            />
          </label>

          {status === 'ENGINE_OFF' && (
            <button
              type="button"
              onClick={() => {
                p.command('/engine', 'POST', { command: 'START' })
                  .then(() => notify('Engine started · Nominal cruise RPM'))
                  .catch(() => notify('Start failed'));
              }}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-xs bg-accent text-white font-mono text-[10px] font-bold hover:bg-accent/90 shadow-xs cursor-pointer animate-pulse"
              title="Powerplant is stopped. Click to start and restore nominal cruise telemetry."
            >
              <Zap className="w-3 h-3" />
              <span>START ENGINE</span>
            </button>
          )}

          <div className="h-3 w-px bg-surface-border hidden sm:block" />

          <span className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={() => setCommandPaletteOpen(true)}
              className="flex items-center gap-1 text-xs font-mono text-slate-600 hover:text-cyan-700 transition-colors cursor-pointer"
              title="Tactical Command Palette (Ctrl+K)"
            >
              <Search className="w-3.5 h-3.5 text-cyan-600" />
              <span className="font-semibold text-slate-700 hidden md:inline">Commands</span>
              <kbd className={`${key} hidden sm:inline-flex`}>Ctrl+K</kbd>
            </button>
            <InfoTooltip
              title="Tactical Command Palette"
              content="Opens a keyboard-first command palette to quickly search and switch engines, trigger fault scenarios, adjust throttle, or jump between views."
              shortcut="Ctrl+K"
              placement="bottom"
              width={260}
            />
          </span>
        </div>

        {/* Right Section: View Modes, Rotation, Guide */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {/* Segmented View Mode Selector */}
          <div className="flex items-center rounded-sm bg-black/[0.04] p-0.5 border border-surface-border">
            <button
              type="button"
              onClick={() => setViewMode('solid')}
              className={`px-1.5 sm:px-2 py-0.5 rounded-xs transition-all flex items-center gap-1 text-[11px] font-mono cursor-pointer ${
                viewMode === 'solid'
                  ? 'bg-accent text-white font-bold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-black/5'
              }`}
              title="Solid: Full physical engine CAD surface [Press V to cycle]"
            >
              <Box className={`w-3.5 h-3.5 ${viewMode === 'solid' ? 'text-white' : 'text-slate-600'}`} />
              <span className="hidden sm:inline">SOLID</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('glass')}
              className={`px-1.5 sm:px-2 py-0.5 rounded-xs transition-all flex items-center gap-1 text-[11px] font-mono cursor-pointer ${
                viewMode === 'glass'
                  ? 'bg-accent text-white font-bold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-black/5'
              }`}
              title="X-Ray: Optical glass casing revealing reciprocating internal assemblies [Press V to cycle]"
            >
              <ScanLine className={`w-3.5 h-3.5 ${viewMode === 'glass' ? 'text-white' : 'text-cyan-700'}`} />
              <span className="hidden sm:inline">X-RAY</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('thermal')}
              className={`px-1.5 sm:px-2 py-0.5 rounded-xs transition-all flex items-center gap-1 text-[11px] font-mono cursor-pointer ${
                viewMode === 'thermal'
                  ? 'bg-accent text-white font-bold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-black/5'
              }`}
              title="Thermal: Dynamic 20 Hz Planck blackbody pyrometry heatmaps [Press V to cycle]"
            >
              <Flame className={`w-3.5 h-3.5 ${viewMode === 'thermal' ? 'text-white' : 'text-rose-600'}`} />
              <span className="hidden sm:inline">THERMAL</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('ghost')}
              className={`px-1.5 sm:px-2 py-0.5 rounded-xs transition-all flex items-center gap-1 text-[11px] font-mono cursor-pointer ${
                viewMode === 'ghost'
                  ? 'bg-accent text-white font-bold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-black/5'
              }`}
              title="Wireframe: Holographic structural reference model [Press V to cycle]"
            >
              <Radio className={`w-3.5 h-3.5 ${viewMode === 'ghost' ? 'text-white' : 'text-indigo-600'}`} />
              <span className="hidden sm:inline">WIREFRAME</span>
            </button>
          </div>

          <div className="h-3 w-px bg-surface-border hidden sm:block" />

          {/* Auto-Rotation Toggle */}
          <span className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setAutoRotate((r) => !r)}
              className="flex items-center gap-1 text-xs font-mono text-slate-600 hover:text-slate-900 transition-colors cursor-pointer p-0.5"
              title={autoRotate ? 'Pause 3D engine auto-rotation' : 'Resume 3D engine auto-rotation'}
            >
              <RotateCw className="w-3.5 h-3.5 text-accent" />
              <span className="hidden xl:inline">{autoRotate ? 'Rotating' : 'Paused'}</span>
            </button>
            <InfoTooltip
              title="3D Auto-Rotation"
              content="Toggles continuous 360-degree rotation of the 3D engine viewport for inspection from all angles."
              placement="bottom"
              width={240}
            />
          </span>

          <div className="h-3 w-px bg-surface-border hidden sm:block" />

          {/* Guide Modal Trigger */}
          <span className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setShowGuide(true)}
              className="flex items-center gap-1 text-xs font-mono text-slate-600 hover:text-slate-900 transition-colors cursor-pointer p-0.5"
              title="Digital Twin & Telemetry Architecture Guide (Press ?)"
            >
              <Info className="w-3.5 h-3.5 text-accent" />
              <span className="font-semibold text-slate-700 hidden xl:inline">Twin Guide</span>
              <kbd className={`${key} hidden sm:inline-flex`}>?</kbd>
            </button>
            <InfoTooltip
              title="Architecture Reference Guide"
              content="Opens the comprehensive operational guide explaining 20 Hz Navier-Stokes physics, sensor FDI, UKF state observer, and CAN bus datalinks."
              shortcut="?"
              placement="bottom"
              width={260}
            />
          </span>
        </div>
      </header>

      {/* Mobile Toggle Button for Fault Scenarios */}
      <div className="md:hidden absolute left-2 top-[46px] z-10">
        <button
          type="button"
          onClick={() => setMobileControlsOpen(true)}
          className="surface-panel flex items-center gap-1.5 rounded-sm px-2.5 py-1.5 text-xs font-mono font-medium text-slate-800 shadow-sm border border-surface-border hover:bg-black/5"
        >
          <Zap className="w-3.5 h-3.5 text-accent" />
          <span>Faults</span>
          {active.length > 0 && <span className="w-2 h-2 rounded-full bg-critical animate-pulse" />}
        </button>
      </div>

      {/* Compact, High-Density Fault Controls (Desktop persistent / Mobile sliding panel) */}
      <aside
        className={`surface-panel z-10 w-[min(240px,calc(100%-1rem))] md:w-[220px] rounded-sm p-2 shadow-sm border border-surface-border overflow-hidden select-none ${
          mobileControlsOpen
            ? 'fixed left-2 top-[44px] bottom-auto md:absolute md:left-4 md:top-[44px] block'
            : 'hidden md:block md:absolute md:left-4 md:top-[44px]'
        }`}
        aria-label="Keyboard fault controls"
      >
        {/* Header & Page */}
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1">
            <span className="text-[10px] uppercase tracking-[0.14em] font-mono text-slate-500 font-semibold">Inject fault</span>
            <InfoTooltip
              title="Inject Fault Scenario"
              content="Simulates an engine malfunction in real time, such as an ignition misfire or cooling leak. The diagnostic system isolates the issue and highlights the affected part on the 3D model."
              placement="right"
            />
          </span>
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[9px] text-slate-400">
              {page + 1}/{pages}
            </span>
            <button
              type="button"
              onClick={() => setMobileControlsOpen(false)}
              className="md:hidden text-slate-400 hover:text-slate-800 p-0.5 rounded-sm cursor-pointer"
              aria-label="Close fault panel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* High-Precision Avionics Telemetry Settling Line */}
        <div className="mt-1 border-b border-surface-border pb-1">
          <div className="flex items-center justify-between font-mono text-[9px]">
            {isSettling ? (
              <span className="flex items-center gap-1 text-accent font-semibold">
                <Activity className="w-2.5 h-2.5 animate-pulse" />
                <span>PROPAGATING [{(remainingMs / 1000).toFixed(1)}s]</span>
              </span>
            ) : (
              <span className="flex items-center gap-1 text-success">
                <CheckCircle2 className="w-2.5 h-2.5" />
                <span className="text-slate-500 font-medium">TELEMETRY BUS READY</span>
              </span>
            )}
            <span className="text-slate-400 text-[8.5px] uppercase tracking-wider">{phaseText}</span>
          </div>

          {/* Micro Progress Bar */}
          <div className="mt-0.5 h-[1.5px] w-full rounded-full bg-surface-border/40 overflow-hidden">
            <div
              className={`h-full transition-all duration-75 ${
                isSettling ? 'bg-accent shadow-[0_0_4px_rgba(189,75,43,0.6)]' : 'bg-success/50'
              }`}
              style={{ width: `${Math.round(progress * 100)}%` }}
            />
          </div>
        </div>

        {/* Fault List: Clean, High-Density Rows */}
        <ol className="mt-1 space-y-0.5">
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
                  className={`w-full flex items-center justify-between text-left text-[11px] py-[2px] px-1 rounded-[2px] transition-colors leading-tight ${
                    isThisSettling
                      ? 'bg-accent/10 text-accent font-medium'
                      : isActive
                      ? 'bg-black/5 text-slate-900 font-medium'
                      : isSettling
                      ? 'opacity-40 cursor-not-allowed text-slate-500'
                      : 'hover:bg-black/5 text-slate-800 cursor-pointer'
                  }`}
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    <kbd className="inline-flex h-4 min-w-4 items-center justify-center rounded-[2px] border border-surface-border-strong bg-surface-card px-0.5 font-mono text-[9px] text-slate-700 shadow-[0_1px_0_rgba(0,0,0,0.15)]">{i + 1}</kbd>
                    <span className="truncate">
                      {title(f.name)}
                      {f.scope === 'CYLINDER' ? (
                        <span className="text-slate-400 font-mono text-[10px]"> · cyl {cyl}</span>
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

        {/* Compact 2-Line Keyboard Shortcuts Footer: ZERO SCROLLBAR */}
        <div className="mt-1.5 border-t border-surface-border pt-1 text-[9.5px] font-mono text-slate-500 space-y-1">
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={clearAllFaults}
              className="flex items-center gap-1 text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
              title="Clear all active faults (Key: X)"
            >
              <kbd className="inline-flex h-3.5 min-w-3.5 items-center justify-center rounded-[2px] border border-surface-border-strong bg-surface-card px-0.5 font-mono text-[8.5px] text-slate-700">X</kbd>
              <span>clear all</span>
            </button>
            <button
              type="button"
              onClick={clearOneFault}
              className="flex items-center gap-1 text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
              title="Clear last fault (Key: Z)"
            >
              <kbd className="inline-flex h-3.5 min-w-3.5 items-center justify-center rounded-[2px] border border-surface-border-strong bg-surface-card px-0.5 font-mono text-[8.5px] text-slate-700">Z</kbd>
              <span>undo</span>
            </button>
            <button
              type="button"
              onClick={cycleCylinder}
              className="flex items-center gap-1 text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
              title="Target cylinder (Key: C)"
            >
              <kbd className="inline-flex h-3.5 min-w-3.5 items-center justify-center rounded-[2px] border border-surface-border-strong bg-surface-card px-0.5 font-mono text-[8.5px] text-slate-700">C</kbd>
              <span>c{cyl}/{p.cylinders ?? 4}</span>
            </button>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-0.5" title="Page scenarios (Key: Q / E)">
              <kbd className="inline-flex h-3.5 min-w-3.5 items-center justify-center rounded-[2px] border border-surface-border-strong bg-surface-card px-0.5 font-mono text-[8.5px] text-slate-700">Q</kbd>
              <kbd className="inline-flex h-3.5 min-w-3.5 items-center justify-center rounded-[2px] border border-surface-border-strong bg-surface-card px-0.5 font-mono text-[8.5px] text-slate-700">E</kbd>
              <span>page</span>
            </span>
            <span className="flex items-center gap-1" title="Focus camera on fault (Key: F)">
              <kbd className="inline-flex h-3.5 min-w-3.5 items-center justify-center rounded-[2px] border border-surface-border-strong bg-surface-card px-0.5 font-mono text-[8.5px] text-slate-700">F</kbd>
              <span>focus</span>
            </span>
            <span className="flex items-center gap-1" title="Training overlay (Key: T)">
              <kbd className="inline-flex h-3.5 min-w-3.5 items-center justify-center rounded-[2px] border border-surface-border-strong bg-surface-card px-0.5 font-mono text-[8.5px] text-slate-700">T</kbd>
              <span>trn {p.training ? 'on' : 'off'}</span>
            </span>
          </div>
        </div>
      </aside>

      {/* Bottom: Annunciator Strip with quick navigation */}
      <div
        className={`surface-panel absolute inset-x-2 sm:inset-x-4 bottom-2 sm:bottom-4 rounded-sm border-l-4 px-2.5 sm:px-4 py-1.5 sm:py-2 z-10 ${
          status && STRIP[status] ? STRIP[status] : 'border-l-surface-border text-slate-800'
        }`}
        aria-live="polite"
      >
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 font-mono text-sm font-semibold tracking-wider">
              <span>{status ?? 'NO DATA'}</span>
              <InfoTooltip
                title="Flight Readiness Status"
                content="Aviation flight status indicator: GO (green, all systems normal), CAUTION (amber, advisory warning or abnormal sensor trend), or NO-GO (red, dangerous safety limit breached)."
              />
            </span>
            {status === 'ENGINE_OFF' && (
              <button
                type="button"
                onClick={() => {
                  p.command('/engine', 'POST', { command: 'START' })
                    .then(() => notify('Engine started · Nominal cruise RPM'))
                    .catch(() => notify('Start failed'));
                }}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[2px] bg-accent text-white font-mono text-[11px] font-bold hover:bg-accent/90 shadow-xs cursor-pointer animate-pulse transition-all"
                title="Start powerplant simulation (brings engine to nominal cruise RPM)"
              >
                <Zap className="w-3 h-3" />
                <span>START ENGINE</span>
              </button>
            )}
            {reason && status !== 'GO' && <span className="text-xs text-slate-700 truncate max-w-[160px] sm:max-w-none">{reason}</span>}
            {isSettling && (
              <span className="inline-flex items-center gap-1 text-xs font-mono text-accent font-medium">
                <Activity className="w-3 h-3 animate-pulse" />
                <span className="hidden sm:inline">settling transient:</span> {settlingFault?.name} [{(remainingMs / 1000).toFixed(1)}s]
              </span>
            )}
            {active.length > 0 && highlights.length === 0 && !isSettling && (
              <span className="text-xs text-slate-500">diagnosing…</span>
            )}
            {active.length > 0 && (
              <span className="text-xs text-slate-600 font-mono hidden sm:inline">
                injected {active.map((f) => `${f.fault_id}${f.cylinder ? `·c${f.cylinder}` : ''}`).join('  ')}
              </span>
            )}
          </div>

          {/* Quick links to live telemetry stream and full console */}
          <div className="flex items-center gap-2 text-xs font-mono">
            <button
              type="button"
              onClick={scrollToTelemetry}
              className="inline-flex items-center gap-1 text-slate-600 hover:text-slate-900 transition-colors"
              title="Scroll down to view live 20 Hz telemetry numbers and thermodynamic equations"
            >
              <ArrowDown className="w-3 h-3 text-accent" />
              <span className="hidden sm:inline">Live Telemetry Numbers ↓</span>
              <span className="sm:hidden">Telemetry ↓</span>
            </button>
            {p.onNavigateToRuntime && (
              <>
                <span className="text-slate-300">|</span>
                <button
                  type="button"
                  onClick={p.onNavigateToRuntime}
                  className="inline-flex items-center gap-1 text-accent hover:underline font-medium"
                >
                  <span className="hidden sm:inline">Engine Runtime Console</span>
                  <span className="sm:hidden">Runtime</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </>
            )}
            {notice && <span className="text-xs opacity-90 font-mono text-slate-600 ml-1 truncate max-w-[150px]">{notice}</span>}
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
                  <div className="flex items-center gap-1.5"><kbd className={key}>X</kbd><span>Clear all faults</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>Q/E</kbd><span>Page switch</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>C</kbd><span>Cycle target cylinder (1-4)</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>F</kbd><span>Refocus camera</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>T</kbd><span>Training highlight</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>V</kbd><span>Cycle 3D render views</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>Z</kbd><span>Clear one by one (Z / R)</span></div>
                  <div className="flex items-center gap-1.5"><kbd className={key}>Ctrl+K</kbd><span>Command palette</span></div>
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

      {/* Tactical Command Palette (Ctrl+K) */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        selectedEngineId={p.engineId}
        onSelectEngine={(id) => {
          p.onSelectEngine(id);
          setCommandPaletteOpen(false);
        }}
        onSelectViewMode={(mode) => {
          setViewMode(mode);
          setCommandPaletteOpen(false);
        }}
        onOpenCanInspector={() => {
          setCommandPaletteOpen(false);
          p.onNavigateToRuntime?.();
        }}
        onOpenConnectionModal={() => {
          setCommandPaletteOpen(false);
        }}
        onToggleVoice={() => {
          setCommandPaletteOpen(false);
        }}
        onInjectFault={(fid) => {
          const f = p.faults.find((item) => item.id === fid);
          if (f) injectFault(f);
          setCommandPaletteOpen(false);
        }}
        onClearFaults={() => {
          clearAllFaults();
          setCommandPaletteOpen(false);
        }}
        onSetThrottle={(pct) => {
          p.command('/levers', 'POST', { throttle_pct: pct })
            .then(() => notify(`Throttle set to ${pct}%`))
            .catch(() => notify('Lever update failed'));
          setCommandPaletteOpen(false);
        }}
        onEngineCommand={(cmd) => {
          p.command('/engine', 'POST', { action: cmd })
            .then(() => notify(`Engine ${cmd} command sent`))
            .catch(() => notify(`${cmd} failed`));
          setCommandPaletteOpen(false);
        }}
      />
    </div>
  );
}
