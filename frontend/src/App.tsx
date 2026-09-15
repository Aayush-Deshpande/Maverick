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
import { ConnectionModal } from './components/ConnectionModal';
import { PanelErrorBoundary } from './components/PanelErrorBoundary';
import { WifiOff, Radio, Shield, Layers, Brain, Mic, History } from 'lucide-react';

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

  const [activeTab, setActiveTab] = useState<'PILLAR_1' | 'AI_DIAGNOSTICS' | 'VOICE_COPILOT' | 'MISSION_REPLAY'>('PILLAR_1');

  return (
    <div className="min-h-screen bg-background text-[#f2f2f3] flex flex-col selection:bg-accent selection:text-white">
      <Header
        state={state}
        isConnected={isConnected}
        latencyMs={latencyMs}
        onOpenSettings={() => setIsModalOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-3 sm:p-4 md:p-6 space-y-4">
        {!isConnected && (
          <div className="surface-panel surface-panel-critical  p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-sm bg-critical-dim flex items-center justify-center text-critical shrink-0">
                <WifiOff className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-critical">
                  Telemetry datalink disconnected
                </h4>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Awaiting 20 Hz state feed from laptop server at <span className="font-medium text-slate-200">{serverUrl}</span>
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

        {/* Tab navigation */}
        <div className="flex items-center justify-between border-b border-surface-border pb-2 flex-wrap gap-2">
          <div className="flex items-center gap-1 p-1 rounded-sm bg-surface-card border border-surface-border">
            {[
              { id: 'PILLAR_1', label: 'Pillar 1 — Pre-Flight Certification', icon: <Layers className="w-3.5 h-3.5" /> },
              { id: 'AI_DIAGNOSTICS', label: 'AI reasoning & copilot', icon: <Brain className="w-3.5 h-3.5" /> },
              { id: 'VOICE_COPILOT', label: 'Voice copilot', icon: <Mic className="w-3.5 h-3.5" /> },
              { id: 'MISSION_REPLAY', label: 'Mission replay', icon: <History className="w-3.5 h-3.5" /> },
            ].map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-accent-dim text-accent'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {tab.icon}
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-2 text-[11px] text-slate-500">
            <Radio className="w-3.5 h-3.5" />
            <span>2-plane defense cyber-physical architecture</span>
          </div>
        </div>

        {activeTab === 'PILLAR_1' && (
          <div className="space-y-4">
            {/* Step 0 — mission parameters, alongside Step 1 — Fault Simulation, both near
                the top of the flow; engine telemetry appears directly below either way. */}
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

        {activeTab === 'AI_DIAGNOSTICS' && (
          <PanelErrorBoundary label="AI diagnostics">
            <DiagnosticCard state={state} serverUrl={serverUrl} />
          </PanelErrorBoundary>
        )}

        {activeTab === 'VOICE_COPILOT' && (
          <PanelErrorBoundary label="Voice copilot">
            <VoiceCopilot state={state} serverUrl={serverUrl} />
          </PanelErrorBoundary>
        )}

        {activeTab === 'MISSION_REPLAY' && (
          <PanelErrorBoundary label="Mission replay">
            <MissionReplayScrubber serverUrl={serverUrl} />
          </PanelErrorBoundary>
        )}
      </main>

      <footer className="bg-surface/80 border-t border-surface-border py-3 px-4 text-center mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] text-slate-500">
          <div className="flex items-center gap-2">
            <Shield className="w-3.5 h-3.5" />
            <span>DRDO / iDEX PS-26054 — Rotax 912 iS Sport High-Altitude MALE UAV Digital Twin</span>
          </div>
          <div>
            <span>Dual-lane FADEC active: <span className="text-slate-300 font-medium">{state.telemetry.FADEC_ACTIVE_LANE}</span></span>
            <span className="mx-2 text-slate-700">·</span>
            <span>Sortie: <span className="text-slate-300 font-medium">{state.sortie_id}</span></span>
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
