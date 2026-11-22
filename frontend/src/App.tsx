import { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import { useTelemetrySocket } from './hooks/useTelemetrySocket';
import { Header } from './components/Header';
import { PanelErrorBoundary } from './components/PanelErrorBoundary';
import { LandingPage } from './components/landing/LandingPage';
import InfoTooltip from './components/InfoTooltip';

// Lazy-load non-landing dashboards and consoles to ensure initial landing page bundle is ultralight
const EngineControls = lazy(() => import('./components/EngineControls').then((m) => ({ default: m.EngineControls })));
const FaultMatrix = lazy(() => import('./components/FaultMatrix').then((m) => ({ default: m.FaultMatrix })));
const ReadingsPanel = lazy(() => import('./components/ReadingsPanel').then((m) => ({ default: m.ReadingsPanel })));
const CalculationsPanel = lazy(() => import('./components/CalculationsPanel').then((m) => ({ default: m.CalculationsPanel })));
const MissionReadinessCard = lazy(() => import('./components/MissionReadinessCard').then((m) => ({ default: m.MissionReadinessCard })));
const SubsystemHealthCard = lazy(() => import('./components/SubsystemHealthCard').then((m) => ({ default: m.SubsystemHealthCard })));
const DiagnosticCard = lazy(() => import('./components/DiagnosticCard').then((m) => ({ default: m.DiagnosticCard })));
const CopilotPanel = lazy(() => import('./components/CopilotPanel'));
const VoiceCopilot = lazy(() => import('./components/VoiceCopilot').then((m) => ({ default: m.VoiceCopilot })));
const MissionReplayScrubber = lazy(() => import('./components/MissionReplayScrubber').then((m) => ({ default: m.MissionReplayScrubber })));
const PropulsionEngineerPanel = lazy(() => import('./components/PropulsionEngineerPanel').then((m) => ({ default: m.PropulsionEngineerPanel })));
const MaintenanceDashboardPanel = lazy(() => import('./components/MaintenanceDashboardPanel').then((m) => ({ default: m.MaintenanceDashboardPanel })));
const TwinWorkspace = lazy(() => import('./components/TwinWorkspace'));
const EngineRuntimeConsole = lazy(() => import('./components/EngineRuntimeConsole').then((m) => ({ default: m.EngineRuntimeConsole })));
const ConnectionModal = lazy(() => import('./components/ConnectionModal').then((m) => ({ default: m.ConnectionModal })));

const TacticalLoaderFallback = () => (
  <div className="surface-panel p-8 flex items-center justify-center gap-3 font-mono text-xs text-slate-400">
    <div className="w-2.5 h-2.5 rounded-full bg-accent animate-ping" />
    <span>SUBSYSTEM INITIALIZATION IN PROGRESS // DRDO PS-26054</span>
  </div>
);
import { GCSRole } from './types/telemetry';
import {
  WifiOff,
  Radio,
  Shield,
  Brain,
  Mic,
  History,
  Cpu,
  Wrench,
  User,
  Play,
  ArrowUpRight,
} from 'lucide-react';

export function App() {
  const [workspace, setWorkspace] = useState<'landing' | 'runtime' | 'twin' | 'tactical'>(() => {
    try {
      const p = new URLSearchParams(window.location.search).get('workspace');
      if (p === 'twin' || p === 'runtime' || p === 'tactical' || p === 'landing') return p;
      if (p === 'legacy') return 'tactical';
      const h = window.location.hash.replace('#', '');
      if (h === 'twin' || h === 'runtime' || h === 'tactical' || h === 'landing') return h;
      if (h === 'legacy') return 'tactical';
    } catch {}
    return 'landing';
  });

  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior }); }, [workspace]);

  // Gate 20Hz telemetry WebSocket to active console workspaces only (avoids polling overhead on landing)
  const {
    state,
    isConnected,
    latencyMs,
    serverUrl,
    setServerUrl,
    sendCommand,
    isModalOpen,
    setIsModalOpen,
  } = useTelemetrySocket({ enabled: workspace !== 'landing' });

  const [activeRole, setActiveRole] = useState<GCSRole>('OPERATOR');
  const [activeTab, setActiveTab] = useState<
    'OPERATOR' | 'PROPULSION' | 'MAINTENANCE' | 'AI_DIAGNOSTICS' | 'VOICE_COPILOT' | 'MISSION_REPLAY'
  >('OPERATOR');

  // The role is a client-side view setting; it is never sent to the server (audit #42, M0-09).
  const handleSelectRole = (role: GCSRole) => {
    setActiveRole(role);
    if (role === 'OPERATOR') setActiveTab('OPERATOR');
    else if (role === 'PROPULSION_ENGINEER') setActiveTab('PROPULSION');
    else if (role === 'MAINTENANCE_CREW') setActiveTab('MAINTENANCE');
  };

  const handleTabClick = (tabId: typeof activeTab) => {
    setActiveTab(tabId);
    if (tabId === 'OPERATOR') {
      setActiveRole('OPERATOR');
    } else if (tabId === 'PROPULSION') {
      setActiveRole('PROPULSION_ENGINEER');
    } else if (tabId === 'MAINTENANCE') {
      setActiveRole('MAINTENANCE_CREW');
    }
  };

  const api = useCallback(async (path: string, method: string = 'GET', body?: unknown) => {
    const res = await fetch(`${serverUrl}${path}`, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || err.detail || `Request failed (${res.status})`);
    }
    return res.json();
  }, [serverUrl]);

  if (workspace === 'landing') {
    return <LandingPage serverUrl={serverUrl} onLaunchConsole={(target) => setWorkspace(target === 'legacy' ? 'tactical' : (target || 'runtime'))} />;
  }

  return (
    <div className="workspace-shell min-h-screen bg-background text-[#101b20] flex flex-col selection:bg-accent selection:text-white">
      <Header
        state={state}
        isConnected={isConnected}
        latencyMs={latencyMs}
        activeRole={activeRole}
        onSelectRole={handleSelectRole}
        onOpenSettings={() => setIsModalOpen(true)}
        runtimeMode={workspace !== 'tactical'}
        showRoleSelector={false}
        onGoLanding={() => setWorkspace('landing')}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-3 sm:p-4 md:p-6 space-y-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="text-xs uppercase tracking-[0.18em] text-[#68757a] font-mono flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-accent" />
            <span>ANUMAAN · GCS WORKSPACE</span>
            <InfoTooltip
              title="Workspace Modes"
              content="Switch between workspaces: Overview (editorial presentation), Engine Runtime (20 Hz live simulation across 5 engines), 3D Twin (keyboard-driven 3D engine CAD), or Tactical GCS (operator flight deck)."
              width={280}
            />
          </div>
          <div className="flex rounded-sm border border-surface-border bg-surface-card p-0.5 text-xs font-mono max-w-full overflow-x-auto no-scrollbar">
            <button
              onClick={() => setWorkspace('landing')}
              className="rounded-sm px-2.5 py-1 text-slate-400 hover:text-white flex items-center gap-1 transition-colors shrink-0 whitespace-nowrap"
              title="Return to Platform Overview"
            >
              <span className="text-xs">&larr;</span> Overview
            </button>
            <button
              onClick={() => setWorkspace('runtime')}
              className={`rounded-sm px-2.5 sm:px-3 py-1 transition-colors shrink-0 whitespace-nowrap ${
                workspace === 'runtime'
                  ? 'bg-accent text-white font-medium shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Engine runtime
            </button>
            <button
              onClick={() => setWorkspace('twin')}
              className={`rounded-sm px-2.5 sm:px-3 py-1 transition-colors shrink-0 whitespace-nowrap ${
                workspace === 'twin'
                  ? 'bg-accent text-white font-medium shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              3D twin
            </button>
            <button
              onClick={() => setWorkspace('tactical')}
              className={`rounded-sm px-2.5 sm:px-3 py-1 transition-colors shrink-0 whitespace-nowrap ${
                workspace === 'tactical'
                  ? 'bg-accent text-white font-medium shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Tactical GCS
            </button>
          </div>
        </div>

        <Suspense fallback={<TacticalLoaderFallback />}>
        {workspace === 'runtime' ? (
          <EngineRuntimeConsole serverUrl={serverUrl} />
        ) : workspace === 'twin' ? (
          // The 3D twin tab is only the engine (keyboard-driven): same store, same fault API, highlights from
          // state.highlights and the component manifests, so console, twin and GCS always agree.
          <TwinWorkspace serverUrl={serverUrl} onNavigateToRuntime={() => setWorkspace('runtime')} />
        ) : (
          <>
            {workspace === 'tactical' && !isConnected && (
              <div className="surface-panel surface-panel-critical p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-sm bg-critical-dim flex items-center justify-center text-critical shrink-0">
                    <WifiOff className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-critical font-mono">
                      Telemetry Datalink Disconnected
                    </h4>
                    <p className="text-xs text-slate-400 mt-0.5 font-mono">
                      Awaiting 20 Hz telemetry feed from backend server at{' '}
                      <span className="font-medium text-slate-200">{serverUrl}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-auto">
                  <button
                    onClick={() => setIsModalOpen(true)}
                    className="px-3.5 py-1.5 rounded-sm bg-critical-dim text-critical text-xs font-medium hover:bg-critical-dim/70 border border-critical-muted transition-colors font-mono"
                  >
                    Configure host link
                  </button>
                </div>
              </div>
            )}

            {/* Tab / Role navigation (VIS-01..04) */}
            <div className="flex items-center justify-between border-b border-surface-border pb-2 flex-wrap gap-2">
              <div className="flex items-center gap-1 p-1 rounded-sm bg-surface-card border border-surface-border overflow-x-auto max-w-full font-mono text-xs">
                {[
                  { id: 'OPERATOR' as const, label: 'Operator Flight Deck', icon: <User className="w-3.5 h-3.5" /> },
                  { id: 'PROPULSION' as const, label: 'Propulsion Engineer', icon: <Cpu className="w-3.5 h-3.5" /> },
                  { id: 'MAINTENANCE' as const, label: 'Maintenance & CBM', icon: <Wrench className="w-3.5 h-3.5" /> },
                  { id: 'AI_DIAGNOSTICS' as const, label: 'AI Reasoning & RAG', icon: <Brain className="w-3.5 h-3.5" /> },
                  { id: 'VOICE_COPILOT' as const, label: 'Voice Copilot', icon: <Mic className="w-3.5 h-3.5" /> },
                  { id: 'MISSION_REPLAY' as const, label: 'Mission Replay', icon: <History className="w-3.5 h-3.5" /> },
                ].map((tab) => {
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => handleTabClick(tab.id)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-medium transition-colors whitespace-nowrap ${
                        isActive
                          ? 'bg-accent text-white shadow-sm'
                          : 'text-slate-400 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      {tab.icon}
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>

              <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                <Radio className="w-3.5 h-3.5 text-accent" />
                <span>DRDO PS-26054 CYBER-PHYSICAL STACK</span>
              </div>
            </div>

        {/* View 1: UAV Operator Tactical Flight Deck (VIS-02) */}
        {activeTab === 'OPERATOR' && (
          <div className="space-y-4">
            {/* Step 0 — mission parameters, alongside Step 1 — Fault Simulation */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <PanelErrorBoundary label="Engine controls">
                <EngineControls state={state} onCommand={sendCommand} />
              </PanelErrorBoundary>
              <PanelErrorBoundary label="Fault matrix">
                <FaultMatrix state={state} onCommand={sendCommand} />
              </PanelErrorBoundary>
            </div>

            {/* Step 2 — Engine Telemetry & derived physics-expected values */}
            <PanelErrorBoundary label="Live readings">
              <ReadingsPanel state={state} />
            </PanelErrorBoundary>

            {/* Step 3 — Detection / Anomaly Calculation */}
            <PanelErrorBoundary label="Detection logic">
              <CalculationsPanel state={state} />
            </PanelErrorBoundary>

            {/* Step 4 — Health / Fault Result */}
            <PanelErrorBoundary label="Mission readiness">
              <MissionReadinessCard state={state} />
            </PanelErrorBoundary>
            <PanelErrorBoundary label="Subsystem health">
              <SubsystemHealthCard state={state} />
            </PanelErrorBoundary>
          </div>
        )}

        {/* View 2: Propulsion Engineer Console (VIS-03, INT-03, VIS-07, F13) */}
        {activeTab === 'PROPULSION' && (
          <PanelErrorBoundary label="Propulsion engineer console">
            <PropulsionEngineerPanel state={state} />
          </PanelErrorBoundary>
        )}

        {/* View 3: Ground Crew Maintenance Dashboard (VIS-04, CBM-01, F12, F14) */}
        {activeTab === 'MAINTENANCE' && (
          <PanelErrorBoundary label="Maintenance dashboard">
            <MaintenanceDashboardPanel state={state} serverUrl={serverUrl} />
          </PanelErrorBoundary>
        )}

        {/* View 4: AI Diagnostics & Root Cause */}
        {activeTab === 'AI_DIAGNOSTICS' && (
          <div className="space-y-4">
            <PanelErrorBoundary label="Engine copilot orchestrator">
              <CopilotPanel engineId={state.engine_id || 'rotax_912is'} api={api} />
            </PanelErrorBoundary>
            <PanelErrorBoundary label="AI diagnostics">
              <DiagnosticCard state={state} serverUrl={serverUrl} />
            </PanelErrorBoundary>
          </div>
        )}

        {/* View 5: Voice Copilot */}
        {activeTab === 'VOICE_COPILOT' && (
          <PanelErrorBoundary label="Voice copilot">
            <VoiceCopilot state={state} serverUrl={serverUrl} />
          </PanelErrorBoundary>
        )}

        {/* View 6: Historical Mission Replay */}
        {activeTab === 'MISSION_REPLAY' && (
          <PanelErrorBoundary label="Mission replay">
            <MissionReplayScrubber serverUrl={serverUrl} />
          </PanelErrorBoundary>
        )}
        </>)}
        </Suspense>
      </main>

      {workspace === 'tactical' ? <footer className="bg-surface/80 border-t border-surface-border py-3 px-4 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col gap-2.5 text-xs text-slate-500">
          <div className="flex items-center justify-between pb-2 border-b border-surface-border/50">
            <a
              href="https://youtu.be/L97JAlS9Z7c"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-red-500 hover:text-red-400 font-mono text-xs font-semibold transition-colors"
            >
              <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-red-600 text-white"><Play size={9} fill="currentColor" /></span>
              <span>Watch Demonstration Video: ANUMAAN System Walkthrough (YouTube)</span>
              <ArrowUpRight size={12} />
            </a>
          </div>
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Shield className="w-3.5 h-3.5" />
              <span>DRDO / iDEX PS-26054 · Rotax 912 iS Sport High-Altitude MALE UAV Digital Twin</span>
            </div>
            <div>
              <span>
                Active Role: <span className="text-accent font-medium">{activeRole}</span>
              </span>
              <span className="mx-2 text-slate-700">·</span>
              <span>
                FADEC Lane: <span className="text-slate-300 font-medium">{state.telemetry.FADEC_ACTIVE_LANE}</span>
              </span>
              <span className="mx-2 text-slate-700">·</span>
              <span>
                Sortie: <span className="text-slate-300 font-medium">{state.sortie_id}</span>
              </span>
            </div>
          </div>
        </div>
      </footer> : <footer className="bg-surface/80 border-t border-surface-border py-3 px-4 mt-auto text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2.5">
          <a
            href="https://youtu.be/L97JAlS9Z7c"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-red-500 hover:text-red-400 font-mono text-xs font-semibold transition-colors order-first"
          >
            <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-red-600 text-white"><Play size={9} fill="currentColor" /></span>
            <span>Watch Demonstration Video: ANUMAAN Walkthrough (YouTube)</span>
            <ArrowUpRight size={12} />
          </a>
          <span>DRDO / iDEX PS-26054 · Simulation-backed multi-engine condition monitoring demonstrator</span>
        </div>
      </footer>}

      <Suspense fallback={null}>
        <ConnectionModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          serverUrl={serverUrl}
          onSave={setServerUrl}
          isConnected={isConnected}
        />
      </Suspense>
    </div>
  );
}

export default App;

