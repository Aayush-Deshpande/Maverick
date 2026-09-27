import { useState, useEffect } from 'react';
import { useTelemetrySocket } from './hooks/useTelemetrySocket';
import { Header } from './components/Header';
import { EngineControls } from './components/EngineControls';
import { FaultMatrix } from './components/FaultMatrix';
import { ReadingsPanel } from './components/ReadingsPanel';
import { CalculationsPanel } from './components/CalculationsPanel';
import { MissionReadinessCard } from './components/MissionReadinessCard';
import { SubsystemHealthCard } from './components/SubsystemHealthCard';
import { DiagnosticCard } from './components/DiagnosticCard';
import { VoiceCopilot } from './components/VoiceCopilot';
import { PropulsionEngineerPanel } from './components/PropulsionEngineerPanel';
import { MaintenanceDashboardPanel } from './components/MaintenanceDashboardPanel';
import { ConnectionModal } from './components/ConnectionModal';
import { PanelErrorBoundary } from './components/PanelErrorBoundary';
import { EngineRuntimeConsole } from './components/EngineRuntimeConsole';
import { DigitalTwinViewer } from './components/DigitalTwinViewer';
import { GCSRole } from './types/telemetry';
import {
  WifiOff,
  Radio,
  Shield,
  Brain,
  Cpu,
  Wrench,
  User,
  Box,
  Layers,
} from 'lucide-react';

export type UnifiedAppTab =
  | 'OPERATOR'
  | 'PROPULSION'
  | 'DIGITAL_TWIN'
  | 'FLEET_RUNTIME'
  | 'MAINTENANCE'
  | 'AI_VOICE';

export function App() {
  const {
    state,
    isConnected,
    latencyMs,
    serverUrl,
    setServerUrl,
    sendCommand,
    isModalOpen,
    setIsModalOpen,
  } = useTelemetrySocket();

  const [activeRole, setActiveRole] = useState<GCSRole>('OPERATOR');
  const [activeTab, setActiveTab] = useState<UnifiedAppTab>('OPERATOR');
  const [activeEngineId, setActiveEngineId] = useState<string>('rotax_912is');

  // Synchronize incoming state.engine_id from authoritative backend
  useEffect(() => {
    if (state.engine_id && state.engine_id !== activeEngineId) {
      setActiveEngineId(state.engine_id);
    }
  }, [state.engine_id]);

  const handleSelectEngine = async (engineId: string) => {
    setActiveEngineId(engineId);
    sendCommand({ action: 'SELECT_ENGINE', engine_id: engineId });
    try {
      await fetch(`${serverUrl}/api/engines/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ engine_id: engineId }),
      });
    } catch (e) {
      console.warn('Backend engine selection sync error:', e);
    }
  };

  const handleSelectRole = (role: GCSRole) => {
    setActiveRole(role);
    if (role === 'OPERATOR') setActiveTab('OPERATOR');
    else if (role === 'PROPULSION_ENGINEER') setActiveTab('PROPULSION');
    else if (role === 'MAINTENANCE_CREW') setActiveTab('MAINTENANCE');
    sendCommand({ action: 'SET_ROLE', role });
  };

  const handleTabClick = (tabId: UnifiedAppTab) => {
    setActiveTab(tabId);
    if (tabId === 'OPERATOR') {
      setActiveRole('OPERATOR');
      sendCommand({ action: 'SET_ROLE', role: 'OPERATOR' });
    } else if (tabId === 'PROPULSION') {
      setActiveRole('PROPULSION_ENGINEER');
      sendCommand({ action: 'SET_ROLE', role: 'PROPULSION_ENGINEER' });
    } else if (tabId === 'MAINTENANCE') {
      setActiveRole('MAINTENANCE_CREW');
      sendCommand({ action: 'SET_ROLE', role: 'MAINTENANCE_CREW' });
    }
  };

  return (
    <div className="min-h-screen bg-background text-[#f2f2f3] flex flex-col selection:bg-accent selection:text-white">
      <Header
        state={state}
        isConnected={isConnected}
        latencyMs={latencyMs}
        activeRole={activeRole}
        onSelectRole={handleSelectRole}
        onOpenSettings={() => setIsModalOpen(true)}
        runtimeMode={false}
        activeEngineId={activeEngineId}
        onSelectEngine={handleSelectEngine}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-3 sm:p-4 md:p-6 space-y-4">
        {/* Offline Alert Banner */}
        {!isConnected && (
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
                  Awaiting 20 Hz state feed from laptop server at{' '}
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

        {/* Unified Top-Level Navigation Bar (WP-03) */}
        <div className="flex items-center justify-between border-b border-surface-border pb-2 flex-wrap gap-2">
          <div className="flex items-center gap-1 p-1 rounded-sm bg-surface-card border border-surface-border overflow-x-auto max-w-full">
            {[
              { id: 'OPERATOR' as const, label: 'Flight Deck', icon: <User className="w-3.5 h-3.5" /> },
              { id: 'PROPULSION' as const, label: 'Propulsion Engineering', icon: <Cpu className="w-3.5 h-3.5" /> },
              { id: 'DIGITAL_TWIN' as const, label: '3D Digital Twin', icon: <Box className="w-3.5 h-3.5" /> },
              { id: 'FLEET_RUNTIME' as const, label: 'Fleet Runtime', icon: <Layers className="w-3.5 h-3.5" /> },
              { id: 'MAINTENANCE' as const, label: 'Maintenance & CBM', icon: <Wrench className="w-3.5 h-3.5" /> },
              { id: 'AI_VOICE' as const, label: 'AI & Voice Copilot', icon: <Brain className="w-3.5 h-3.5" /> },
            ].map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabClick(tab.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-medium transition-colors whitespace-nowrap ${
                    isActive
                      ? 'bg-accent-dim text-accent border border-accent-muted'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {tab.icon}
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono">
            <Radio className="w-3.5 h-3.5 text-cyan-400" />
            <span>DRDO PS-26054 AUTHORITATIVE RUNTIME</span>
          </div>
        </div>

        {/* View 1: UAV Operator Tactical Flight Deck (VIS-02) */}
        {activeTab === 'OPERATOR' && (
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
              <MissionReadinessCard state={state} serverUrl={serverUrl} />
            </PanelErrorBoundary>
            <PanelErrorBoundary label="Subsystem health">
              <SubsystemHealthCard state={state} />
            </PanelErrorBoundary>
          </div>
        )}

        {/* View 2: Propulsion Engineer Console (VIS-03, INT-03, VIS-07, F13, WP-09) */}
        {activeTab === 'PROPULSION' && (
          <PanelErrorBoundary label="Propulsion engineer console">
            <PropulsionEngineerPanel state={state} />
          </PanelErrorBoundary>
        )}

        {/* View 3: 3D Digital Twin Inspection View (WP-04) */}
        {activeTab === 'DIGITAL_TWIN' && (
          <PanelErrorBoundary label="3D Digital Twin Viewer">
            <DigitalTwinViewer
              state={state}
              serverUrl={serverUrl}
              onCommand={sendCommand}
              activeEngineId={activeEngineId}
              onSelectEngine={handleSelectEngine}
            />
          </PanelErrorBoundary>
        )}

        {/* View 4: Fleet / Multi-Engine Runtime Hub (WP-05) */}
        {activeTab === 'FLEET_RUNTIME' && (
          <PanelErrorBoundary label="Engine Runtime Console">
            <EngineRuntimeConsole serverUrl={serverUrl} />
          </PanelErrorBoundary>
        )}

        {/* View 5: Ground Crew Maintenance Dashboard & Debrief (WP-08, WP-10) */}
        {activeTab === 'MAINTENANCE' && (
          <PanelErrorBoundary label="Maintenance dashboard">
            <MaintenanceDashboardPanel state={state} serverUrl={serverUrl} />
          </PanelErrorBoundary>
        )}

        {/* View 6: AI Diagnostics & Voice Copilot (WP-07, WP-08) */}
        {activeTab === 'AI_VOICE' && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <PanelErrorBoundary label="AI diagnostics">
              <DiagnosticCard state={state} serverUrl={serverUrl} />
            </PanelErrorBoundary>
            <PanelErrorBoundary label="Voice copilot">
              <VoiceCopilot state={state} serverUrl={serverUrl} />
            </PanelErrorBoundary>
          </div>
        )}
      </main>

      <footer className="bg-surface/80 border-t border-surface-border py-3 px-4 text-center mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] text-slate-500">
          <div className="flex items-center gap-2">
            <Shield className="w-3.5 h-3.5 text-cyan-400" />
            <span>DRDO / iDEX PS-26054 — Aero-Piston Propulsion Digital Twin Platform</span>
          </div>
          <div>
            <span>
              Engine: <span className="text-cyan-300 font-mono font-medium">{state.engine_name || activeEngineId}</span>
            </span>
            <span className="mx-2 text-slate-700">·</span>
            <span>
              Active Role: <span className="text-accent font-medium">{activeRole}</span>
            </span>
            <span className="mx-2 text-slate-700">·</span>
            <span>
              FADEC: <span className="text-slate-300 font-medium">{state.telemetry.FADEC_ACTIVE_LANE}</span>
            </span>
            <span className="mx-2 text-slate-700">·</span>
            <span>
              Sortie: <span className="text-slate-300 font-medium">{state.sortie_id}</span>
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

export default App;
