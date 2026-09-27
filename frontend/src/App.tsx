import { useState } from 'react';
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
} from 'lucide-react';

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
  const [workspace, setWorkspace] = useState<'runtime' | 'legacy'>('runtime');
  const [activeTab, setActiveTab] = useState<
    'OPERATOR' | 'PROPULSION' | 'MAINTENANCE' | 'AI_DIAGNOSTICS' | 'VOICE_COPILOT' | 'MISSION_REPLAY'
  >('OPERATOR');

  const handleSelectRole = (role: GCSRole) => {
    setActiveRole(role);
    if (role === 'OPERATOR') setActiveTab('OPERATOR');
    else if (role === 'PROPULSION_ENGINEER') setActiveTab('PROPULSION');
    else if (role === 'MAINTENANCE_CREW') setActiveTab('MAINTENANCE');
    sendCommand({ action: 'SET_ROLE', role });
  };

  const handleTabClick = (tabId: typeof activeTab) => {
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
        runtimeMode={workspace === 'runtime'}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-3 sm:p-4 md:p-6 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">ANUMAAN · Ground console</div>
          <div className="flex rounded border border-surface-border bg-surface-card p-0.5 text-[11px]">
            <button onClick={() => setWorkspace('runtime')} className={`rounded px-3 py-1.5 ${workspace === 'runtime' ? 'bg-accent-dim text-accent' : 'text-slate-400 hover:text-white'}`}>Engine runtime</button>
            <button onClick={() => setWorkspace('legacy')} className={`rounded px-3 py-1.5 ${workspace === 'legacy' ? 'bg-accent-dim text-accent' : 'text-slate-400 hover:text-white'}`}>Legacy GCS</button>
          </div>
        </div>
        {workspace === 'runtime' ? <EngineRuntimeConsole serverUrl={serverUrl} /> : <>
        {workspace === 'legacy' && !isConnected && (
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

        {/* Tab / Role navigation (VIS-01..04) */}
        <div className="flex items-center justify-between border-b border-surface-border pb-2 flex-wrap gap-2">
          <div className="flex items-center gap-1 p-1 rounded-sm bg-surface-card border border-surface-border overflow-x-auto max-w-full">
            {[
              { id: 'OPERATOR' as const, label: 'Operator Flight Deck (VIS-02)', icon: <User className="w-3.5 h-3.5" /> },
              { id: 'PROPULSION' as const, label: 'Propulsion Engineer (VIS-03)', icon: <Cpu className="w-3.5 h-3.5" /> },
              { id: 'MAINTENANCE' as const, label: 'Maintenance & CBM (VIS-04)', icon: <Wrench className="w-3.5 h-3.5" /> },
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

          <div className="flex items-center gap-2 text-[11px] text-slate-500">
            <Radio className="w-3.5 h-3.5 text-accent" />
            <span>DRDO 2-Plane Cyber-Physical Architecture</span>
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
          <PanelErrorBoundary label="AI diagnostics">
            <DiagnosticCard state={state} serverUrl={serverUrl} />
          </PanelErrorBoundary>
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
        </>}
      </main>

      {workspace === 'legacy' ? <footer className="bg-surface/80 border-t border-surface-border py-3 px-4 text-center mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] text-slate-500">
          <div className="flex items-center gap-2">
            <Shield className="w-3.5 h-3.5" />
            <span>DRDO / iDEX PS-26054 — Rotax 912 iS Sport High-Altitude MALE UAV Digital Twin</span>
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
      </footer> : <footer className="bg-surface/80 border-t border-surface-border py-3 px-4 text-center mt-auto text-[11px] text-slate-500">DRDO / iDEX PS-26054 · Simulation-backed multi-engine condition monitoring demonstrator</footer>}

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
