import { useEffect, useState } from 'react';
import { useTelemetrySocket } from './hooks/useTelemetrySocket';
import { EngineSelectionProvider, useEngineSelection } from './contexts/EngineSelectionContext';
import { Header } from './components/Header';
import { EngineControls } from './components/EngineControls';
import { FaultMatrix } from './components/FaultMatrix';
import { ReadingsPanel } from './components/ReadingsPanel';
import { CalculationsPanel } from './components/CalculationsPanel';
import { MissionReadinessCard } from './components/MissionReadinessCard';
import { SubsystemHealthCard } from './components/SubsystemHealthCard';
import { DiagnosticCard } from './components/DiagnosticCard';
import { VoiceCopilot } from './components/VoiceCopilot';
import { MissionReplayScrubber } from './components/MissionReplayScrubber';
import { PropulsionEngineerPanel } from './components/PropulsionEngineerPanel';
import { MaintenanceDashboardPanel } from './components/MaintenanceDashboardPanel';
import { ConnectionModal } from './components/ConnectionModal';
import { PanelErrorBoundary } from './components/PanelErrorBoundary';
import { EngineRuntimeConsole } from './components/EngineRuntimeConsole';
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
  Activity,
  Layers,
  Sparkles,
  Compass,
} from 'lucide-react';
import { MissionOperationsPanel } from './components/MissionOperationsPanel';

export type NavArea =
  | 'FLIGHT_DECK'
  | 'PROPULSION'
  | 'DIGITAL_TWIN'
  | 'MULTI_ENGINE_RUNTIME'
  | 'MISSION_PLANNING'
  | 'MISSION_SIM'
  | 'MAINTENANCE_CBM'
  | 'AI_VOICE'
  | 'MISSION_REPLAY';

interface AppShellProps {
  state: ReturnType<typeof useTelemetrySocket>['state'];
  isConnected: boolean;
  latencyMs: number;
  serverUrl: string;
  setServerUrl: (url: string) => void;
  sendCommand: ReturnType<typeof useTelemetrySocket>['sendCommand'];
  isModalOpen: boolean;
  setIsModalOpen: (open: boolean) => void;
}

function AppShell({
  state,
  isConnected,
  latencyMs,
  serverUrl,
  setServerUrl,
  sendCommand,
  isModalOpen,
  setIsModalOpen,
}: AppShellProps) {
  const { engineId, selectEngine, isRotax912isSelected, profile } = useEngineSelection();
  const [activeRole, setActiveRole] = useState<GCSRole>('OPERATOR');
  const [currentArea, setCurrentArea] = useState<NavArea>('FLIGHT_DECK');
  const [aiSubTab, setAiSubTab] = useState<'AI_RAG' | 'VOICE'>('AI_RAG');

  // Listen for engine change messages from the Three.js Twin iframe
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data && event.data.type === 'ANUMAAN_ENGINE_CHANGED' && typeof event.data.engineId === 'string') {
        if (event.data.engineId !== engineId) {
          void selectEngine(event.data.engineId);
        }
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [engineId, selectEngine]);

  // When engineId changes in React state, notify the iframe
  useEffect(() => {
    const iframe = document.getElementById('threejs-twin-iframe') as HTMLIFrameElement | null;
    if (iframe && iframe.contentWindow) {
      iframe.contentWindow.postMessage({ type: 'ANUMAAN_SELECT_ENGINE', engineId }, '*');
    }
  }, [engineId]);

  const handleSelectRole = (role: GCSRole) => {
    setActiveRole(role);
    if (role === 'OPERATOR') setCurrentArea('FLIGHT_DECK');
    else if (role === 'PROPULSION_ENGINEER') setCurrentArea('PROPULSION');
    else if (role === 'MAINTENANCE_CREW') setCurrentArea('MAINTENANCE_CBM');
    sendCommand({ action: 'SET_ROLE', role });
  };

  const handleAreaClick = (area: NavArea) => {
    setCurrentArea(area);
    if (area === 'FLIGHT_DECK') {
      setActiveRole('OPERATOR');
      sendCommand({ action: 'SET_ROLE', role: 'OPERATOR' });
    } else if (area === 'PROPULSION') {
      setActiveRole('PROPULSION_ENGINEER');
      sendCommand({ action: 'SET_ROLE', role: 'PROPULSION_ENGINEER' });
    } else if (area === 'MAINTENANCE_CBM') {
      setActiveRole('MAINTENANCE_CREW');
      sendCommand({ action: 'SET_ROLE', role: 'MAINTENANCE_CREW' });
    }
  };

  const is5EngineArea =
    currentArea === 'MULTI_ENGINE_RUNTIME' ||
    currentArea === 'DIGITAL_TWIN' ||
    currentArea === 'MISSION_PLANNING';

  const NAV_ITEMS: { id: NavArea; label: string; icon: JSX.Element; is5Engine: boolean }[] = [
    { id: 'FLIGHT_DECK', label: 'Flight Deck', icon: <User className="w-3.5 h-3.5" />, is5Engine: false },
    { id: 'PROPULSION', label: 'Propulsion', icon: <Cpu className="w-3.5 h-3.5" />, is5Engine: false },
    { id: 'DIGITAL_TWIN', label: '3D Digital Twin', icon: <Layers className="w-3.5 h-3.5" />, is5Engine: true },
    { id: 'MULTI_ENGINE_RUNTIME', label: 'Multi-Engine Runtime', icon: <Activity className="w-3.5 h-3.5" />, is5Engine: true },
    { id: 'MISSION_PLANNING', label: 'Mission Operations', icon: <Compass className="w-3.5 h-3.5 text-cyan-400" />, is5Engine: true },
    { id: 'MAINTENANCE_CBM', label: 'Maintenance / CBM', icon: <Wrench className="w-3.5 h-3.5" />, is5Engine: false },
    { id: 'AI_VOICE', label: 'AI & Voice', icon: <Brain className="w-3.5 h-3.5" />, is5Engine: false },
    { id: 'MISSION_REPLAY', label: 'Mission Replay', icon: <History className="w-3.5 h-3.5" />, is5Engine: false },
  ];

  // Full-screen mission simulation cockpit: bypasses the shared max-w-7xl shell/nav chrome
  // entirely so the launched flight fills the viewport (per the brief's "transition into a
  // full-screen/large simulation view" requirement) rather than sitting in a sized card
  // beside a duplicate telemetry sidebar.
  if (currentArea === 'MISSION_SIM') {
    return (
      <div className="min-h-screen bg-[#030a12]">
        <PanelErrorBoundary label="Mission Simulation">
          <MissionOperationsPanel
            serverUrl={serverUrl}
            onNavigate={(area) => setCurrentArea(area)}
            fullscreenSimOnly
          />
        </PanelErrorBoundary>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-[#f2f2f3] flex flex-col selection:bg-accent selection:text-white">
      <Header
        state={state}
        isConnected={isConnected}
        latencyMs={latencyMs}
        activeRole={activeRole}
        onSelectRole={handleSelectRole}
        onOpenSettings={() => setIsModalOpen(true)}
        runtimeMode={is5EngineArea}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-3 sm:p-4 md:p-6 space-y-4">
        {/* Unified Primary Navigation Bar */}
        <div className="flex items-center justify-between border-b border-surface-border pb-2 flex-wrap gap-2">
          <div className="flex items-center gap-1 p-1 rounded-lg bg-surface-card border border-surface-border overflow-x-auto max-w-full">
            {NAV_ITEMS.map((item) => {
              const isActive = currentArea === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleAreaClick(item.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
                    isActive
                      ? 'bg-accent-dim text-accent border border-accent-muted'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-2">
            {is5EngineArea ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded border bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                Active Twin: {profile?.display_name || engineId} (5 Engines Ready)
              </span>
            ) : (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded border bg-sky-500/10 text-sky-400 border-sky-500/30">
                {isRotax912isSelected
                  ? 'Rotax 912 iS Sport — live sortie'
                  : `Active Twin: ${profile?.display_name || engineId} · Sortie: 912 iS`}
              </span>
            )}
            <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-slate-500">
              <Radio className="w-3.5 h-3.5 text-accent" />
              <span>DRDO PS-26054</span>
            </div>
          </div>
        </div>

        {/* Datalink disconnection notice for live sortie areas */}
        {!is5EngineArea && !isConnected && (
          <div className="surface-panel surface-panel-critical p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-sm bg-critical-dim flex items-center justify-center text-critical shrink-0">
                <WifiOff className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-critical">
                  Telemetry datalink disconnected
                </h4>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Awaiting 20 Hz state feed from server at{' '}
                  <span className="font-medium text-slate-200">{serverUrl}</span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 self-end sm:self-auto">
              <button
                onClick={() => setIsModalOpen(true)}
                className="px-3.5 py-1.5 rounded-sm bg-critical-dim text-critical text-xs font-medium hover:bg-critical-dim/70 border border-critical-muted transition-colors"
              >
                Configure host link
              </button>
            </div>
          </div>
        )}

        {/* Area 1: Flight Deck (Tactical Flight Deck) */}
        {currentArea === 'FLIGHT_DECK' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <PanelErrorBoundary label="Engine controls">
                <EngineControls state={state} onCommand={sendCommand} />
              </PanelErrorBoundary>
              <PanelErrorBoundary label="Fault matrix">
                <FaultMatrix state={state} onCommand={sendCommand} />
              </PanelErrorBoundary>
            </div>

            <PanelErrorBoundary label="Live readings">
              <ReadingsPanel state={state} />
            </PanelErrorBoundary>

            <PanelErrorBoundary label="Detection logic">
              <CalculationsPanel state={state} />
            </PanelErrorBoundary>

            <PanelErrorBoundary label="Mission readiness">
              <MissionReadinessCard state={state} />
            </PanelErrorBoundary>
            <PanelErrorBoundary label="Subsystem health">
              <SubsystemHealthCard state={state} />
            </PanelErrorBoundary>
          </div>
        )}

        {/* Area 2: Propulsion Engineer Console */}
        {currentArea === 'PROPULSION' && (
          <PanelErrorBoundary label="Propulsion engineer console">
            <PropulsionEngineerPanel state={state} />
          </PanelErrorBoundary>
        )}

        {/* Area 3: 3D Digital Twin */}
        {currentArea === 'DIGITAL_TWIN' && (
          <section className="surface-panel overflow-hidden rounded-2xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-border px-4 py-3">
              <div>
                <h2 className="text-sm font-semibold text-white">Interactive 3D Digital Twin</h2>
                <p className="mt-1 text-[11px] text-slate-500">
                  Blender-derived Draco CAD asset · Subsystem inspection · Ghost-material fault localization
                </p>
              </div>
              <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded border border-surface-border text-slate-400">
                Web 3D · 5-Engine Ready
              </span>
            </div>
            <iframe
              id="threejs-twin-iframe"
              title="ANUMAAN interactive engine twin"
              src={`${serverUrl}/apps/threejs_twin/?engine=${encodeURIComponent(engineId)}`}
              className="block h-[calc(100vh-12rem)] min-h-[680px] w-full bg-[#061019]"
              allow="fullscreen"
            />
          </section>
        )}

        {/* Area 4: Multi-Engine Runtime Console */}
        {currentArea === 'MULTI_ENGINE_RUNTIME' && (
          <EngineRuntimeConsole serverUrl={serverUrl} />
        )}

        {/* Area: Mission Planning & 3D Canyon Flight Simulation */}
        {currentArea === 'MISSION_PLANNING' && (
          <PanelErrorBoundary label="Mission Operations">
            <MissionOperationsPanel
              serverUrl={serverUrl}
              onNavigate={(area) => setCurrentArea(area)}
            />
          </PanelErrorBoundary>
        )}

        {/* Area 5: Maintenance / Condition-Based Maintenance */}
        {currentArea === 'MAINTENANCE_CBM' && (
          <PanelErrorBoundary label="Maintenance dashboard">
            <MaintenanceDashboardPanel state={state} serverUrl={serverUrl} />
          </PanelErrorBoundary>
        )}

        {/* Area 6: AI & Voice Copilot */}
        {currentArea === 'AI_VOICE' && (
          <div className="space-y-4">
            <div className="flex items-center gap-1 p-1 rounded-lg bg-surface-card border border-surface-border w-fit">
              <button
                onClick={() => setAiSubTab('AI_RAG')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  aiSubTab === 'AI_RAG'
                    ? 'bg-accent-dim text-accent border border-accent-muted'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>AI Reasoning & RAG Copilot</span>
              </button>
              <button
                onClick={() => setAiSubTab('VOICE')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  aiSubTab === 'VOICE'
                    ? 'bg-accent-dim text-accent border border-accent-muted'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Mic className="w-3.5 h-3.5" />
                <span>Voice Copilot</span>
              </button>
            </div>

            {aiSubTab === 'AI_RAG' ? (
              <PanelErrorBoundary label="AI diagnostics">
                <DiagnosticCard state={state} serverUrl={serverUrl} />
              </PanelErrorBoundary>
            ) : (
              <PanelErrorBoundary label="Voice copilot">
                <VoiceCopilot state={state} serverUrl={serverUrl} />
              </PanelErrorBoundary>
            )}
          </div>
        )}

        {/* Area 7: Historical Mission Replay */}
        {currentArea === 'MISSION_REPLAY' && (
          <PanelErrorBoundary label="Mission replay">
            <MissionReplayScrubber serverUrl={serverUrl} />
          </PanelErrorBoundary>
        )}
      </main>

      <footer className="bg-surface/80 border-t border-surface-border py-3 px-4 text-center mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] text-slate-500">
          <div className="flex items-center gap-2">
            <Shield className="w-3.5 h-3.5" />
            <span>DRDO / iDEX PS-26054 — UAV Propulsion Digital Twin</span>
          </div>
          <div>
            <span>
              Active Role: <span className="text-accent font-medium">{activeRole}</span>
            </span>
            <span className="mx-2 text-slate-700">·</span>
            <span>
              FADEC Lane: <span className="text-slate-300 font-medium">{state.telemetry.FADEC_ACTIVE_LANE || 'LANE_A'}</span>
            </span>
            <span className="mx-2 text-slate-700">·</span>
            <span>
              Sortie: <span className="text-slate-300 font-medium">{state.sortie_id || 'STANDBY'}</span>
            </span>
          </div>
        </div>
      </footer>

      <ConnectionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        serverUrl={serverUrl}
        onSave={setServerUrl}
        isConnected={isConnected}
      />
    </div>
  );
}

export function App() {
  const socket = useTelemetrySocket();
  return (
    <EngineSelectionProvider serverUrl={socket.serverUrl}>
      <AppShell {...socket} />
    </EngineSelectionProvider>
  );
}

export default App;
