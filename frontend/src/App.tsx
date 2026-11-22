import { useState, useEffect, lazy, Suspense } from 'react';
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
const UnifiedCopilot = lazy(() => import('./components/UnifiedCopilot').then((m) => ({ default: m.UnifiedCopilot })));
const MissionReplayScrubber = lazy(() => import('./components/MissionReplayScrubber').then((m) => ({ default: m.MissionReplayScrubber })));
const PropulsionEngineerPanel = lazy(() => import('./components/PropulsionEngineerPanel').then((m) => ({ default: m.PropulsionEngineerPanel })));
const MaintenanceDashboardPanel = lazy(() => import('./components/MaintenanceDashboardPanel').then((m) => ({ default: m.MaintenanceDashboardPanel })));
const TwinWorkspace = lazy(() => import('./components/TwinWorkspace'));
const EngineRuntimeConsole = lazy(() => import('./components/EngineRuntimeConsole').then((m) => ({ default: m.EngineRuntimeConsole })));
const ConnectionModal = lazy(() => import('./components/ConnectionModal').then((m) => ({ default: m.ConnectionModal })));
const RuntimeGuideModal = lazy(() => import('./components/RuntimeGuideModal').then((m) => ({ default: m.RuntimeGuideModal })));

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

  const [isGuideOpen, setIsGuideOpen] = useState(false);
  const [activeRole, setActiveRole] = useState<GCSRole>('OPERATOR');
  const [activeTab, setActiveTab] = useState<
    'OPERATOR' | 'PROPULSION' | 'MAINTENANCE' | 'AI_COPILOT' | 'MISSION_REPLAY'
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
        onOpenGuide={() => setIsGuideOpen(true)}
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
              className="rounded-sm px-2.5 py-1 text-slate-400 hover:text-white active:scale-95 transition-all duration-150 flex items-center gap-1 shrink-0 whitespace-nowrap cursor-pointer"
              title="Return to Platform Overview"
            >
              <span className="text-xs">&larr;</span> Overview
            </button>
            <button
              onClick={() => setWorkspace('runtime')}
              className={`rounded-sm px-2.5 sm:px-3 py-1 transition-all duration-150 active:scale-95 shrink-0 whitespace-nowrap cursor-pointer ${
                workspace === 'runtime'
                  ? 'bg-accent text-white font-medium shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-surface-card-hover'
              }`}
            >
              Engine runtime
            </button>
            <button
              onClick={() => setWorkspace('twin')}
              className={`rounded-sm px-2.5 sm:px-3 py-1 transition-all duration-150 active:scale-95 shrink-0 whitespace-nowrap cursor-pointer ${
                workspace === 'twin'
                  ? 'bg-accent text-white font-medium shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-surface-card-hover'
              }`}
            >
              3D twin
            </button>
            <button
              onClick={() => setWorkspace('tactical')}
              className={`rounded-sm px-2.5 sm:px-3 py-1 transition-all duration-150 active:scale-95 shrink-0 whitespace-nowrap cursor-pointer ${
                workspace === 'tactical'
                  ? 'bg-accent text-white font-medium shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-surface-card-hover'
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
                  { id: 'AI_COPILOT' as const, label: 'Tactical AI Copilot', icon: <Brain className="w-3.5 h-3.5" /> },
                  { id: 'MISSION_REPLAY' as const, label: 'Mission Replay', icon: <History className="w-3.5 h-3.5" /> },
                ].map((tab) => {
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => handleTabClick(tab.id)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-medium transition-all duration-150 active:scale-95 whitespace-nowrap cursor-pointer ${
                        isActive
                          ? 'bg-accent text-white shadow-sm font-semibold'
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
                <Radio className="w-3.5 h-3.5 text-accent animate-pulse" />
                <span>DRDO PS-26054 CYBER-PHYSICAL STACK</span>
              </div>
            </div>

        {/* View 1: UAV Operator Tactical Flight Deck (VIS-02) */}
        {activeTab === 'OPERATOR' && (
          <div className="space-y-4 animate-fade-in">
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
          <div className="animate-fade-in">
            <PanelErrorBoundary label="Propulsion engineer console">
              <PropulsionEngineerPanel state={state} />
            </PanelErrorBoundary>
          </div>
        )}

        {/* View 3: Ground Crew Maintenance Dashboard (VIS-04, CBM-01, F12, F14) */}
        {activeTab === 'MAINTENANCE' && (
          <div className="animate-fade-in">
            <PanelErrorBoundary label="Maintenance dashboard">
              <MaintenanceDashboardPanel state={state} serverUrl={serverUrl} />
            </PanelErrorBoundary>
          </div>
        )}

        {/* View 4: Unified Tactical AI Copilot (Conversational + Voice RAG) */}
        {activeTab === 'AI_COPILOT' && (
          <div className="animate-fade-in">
            <PanelErrorBoundary label="Tactical AI copilot">
              <UnifiedCopilot state={state} serverUrl={serverUrl} />
            </PanelErrorBoundary>
          </div>
        )}

        {/* View 5: Historical Mission Replay */}
        {activeTab === 'MISSION_REPLAY' && (
          <div className="animate-fade-in">
            <PanelErrorBoundary label="Mission replay">
              <MissionReplayScrubber serverUrl={serverUrl} />
            </PanelErrorBoundary>
          </div>
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
        {isGuideOpen && (
          <RuntimeGuideModal
            open={isGuideOpen}
            onClose={() => setIsGuideOpen(false)}
          />
        )}
      </Suspense>
    </div>
  );
}

export default App;

