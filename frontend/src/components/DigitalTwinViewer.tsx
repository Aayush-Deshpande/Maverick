import React, { useRef, useEffect, useState, useCallback } from 'react';
import { UnifiedTelemetryState, ControlCommand } from '../types/telemetry';
import {
  Layers,
  Thermometer,
  Eye,
  Camera,
  RotateCcw,
  Maximize2,
  Minimize2,
  AlertTriangle,
  CheckCircle,
  Activity,
  Cpu,
} from 'lucide-react';

interface DigitalTwinViewerProps {
  state: UnifiedTelemetryState;
  serverUrl: string;
  onCommand?: (cmd: ControlCommand) => void;
  activeEngineId?: string;
  onSelectEngine?: (engineId: string) => void;
}

const STATIONS = [
  { id: 0, label: 'Full Assembly', tag: 'STATION 00' },
  { id: 1, label: 'Reduction Gearbox', tag: 'STATION 01' },
  { id: 2, label: 'Induction & Fuel', tag: 'STATION 02' },
  { id: 3, label: 'Thermal Scavenging', tag: 'STATION 03' },
  { id: 4, label: 'Electrical Gen', tag: 'STATION 04' },
  { id: 5, label: 'FADEC & PHM', tag: 'STATION 05' },
];

export const DigitalTwinViewer: React.FC<DigitalTwinViewerProps> = ({
  state,
  serverUrl,
  activeEngineId = 'rotax_912is',
  onSelectEngine,
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [twinReady, setTwinReady] = useState(false);
  const [activeStation, setActiveStation] = useState(0);
  const [thermalActive, setThermalActive] = useState(false);
  const [explodedActive, setExplodedActive] = useState(false);
  const [wireframeActive, setWireframeActive] = useState(false);

  const postToTwin = useCallback((type: string, payload?: any) => {
    if (iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage({ type, payload }, '*');
    }
  }, []);

  // Listen to messages from Three.js iframe
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (!event.data || typeof event.data !== 'object') return;
      const { type, engineId, stationId } = event.data;
      if (type === 'TWIN_READY') {
        setTwinReady(true);
      } else if (type === 'TWIN_ENGINE_CHANGED' && engineId) {
        if (onSelectEngine && engineId !== activeEngineId) {
          onSelectEngine(engineId);
        }
      } else if (type === 'TWIN_STATION_CHANGED' && stationId !== undefined) {
        setActiveStation(stationId);
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [activeEngineId, onSelectEngine]);

  // Synchronize engine changes to Three.js twin
  useEffect(() => {
    if (twinReady && activeEngineId) {
      postToTwin('SELECT_ENGINE', { engineId: activeEngineId });
    }
  }, [activeEngineId, twinReady, postToTwin]);

  // Synchronize backend fault state to 3D visualization
  const activeFaultId = state.active_commanded_fault_id || state.analytics.diagnosed_fault_id;
  useEffect(() => {
    if (!twinReady) return;
    if (activeFaultId > 0) {
      postToTwin('SET_FAULT', { faultId: activeFaultId });
    } else {
      postToTwin('CLEAR_FAULT');
    }
  }, [activeFaultId, twinReady, postToTwin]);

  const handleSelectStation = (id: number) => {
    setActiveStation(id);
    postToTwin('SELECT_STATION', { stationId: id });
  };

  const handleToggleThermal = () => {
    setThermalActive((prev) => !prev);
    postToTwin('TOGGLE_THERMAL');
  };

  const handleToggleExploded = () => {
    setExplodedActive((prev) => !prev);
    postToTwin('TOGGLE_EXPLODED');
  };

  const handleToggleWireframe = () => {
    setWireframeActive((prev) => !prev);
    postToTwin('TOGGLE_WIREFRAME');
  };

  const handleCaptureSnapshot = () => {
    postToTwin('CAPTURE_SNAPSHOT');
  };

  const handleResetView = () => {
    setActiveStation(0);
    postToTwin('RESET_VIEW');
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  const twinUrl = `${serverUrl}/apps/threejs_twin/index.html?engine=${activeEngineId}&dpr=1.5`;

  return (
    <div
      ref={containerRef}
      className={`surface-panel flex flex-col overflow-hidden bg-[#040d14] border border-cyan-500/20 shadow-2xl ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none' : 'min-h-[720px] rounded-lg'
      }`}
    >
      {/* Top Twin Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cyan-500/20 bg-slate-950/80 px-4 py-2.5 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Cpu className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold tracking-wider text-cyan-300 font-mono">
                AERO-TWIN 3D // {state.engine_name || activeEngineId.toUpperCase()}
              </h2>
              <span className="rounded bg-cyan-950/70 border border-cyan-500/40 px-1.5 py-0.5 font-mono text-[9px] text-cyan-400">
                PBR · DRACO GLB
              </span>
              {activeFaultId > 0 ? (
                <span className="flex items-center gap-1 rounded bg-amber-500/20 border border-amber-500/40 px-2 py-0.5 font-mono text-[10px] text-amber-300 animate-pulse">
                  <AlertTriangle className="h-3 w-3" />
                  FAULT ISOLATED: {state.analytics.diagnosed_fault_name || `F0${activeFaultId}`}
                </span>
              ) : (
                <span className="flex items-center gap-1 rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 font-mono text-[10px] text-emerald-400">
                  <CheckCircle className="h-3 w-3" />
                  NOMINAL SYNC
                </span>
              )}
            </div>
            <p className="text-[10px] font-mono text-slate-400 mt-0.5">
              Target mesh: <span className="text-cyan-400">{state.analytics.target_3d_mesh || 'ASSEMBLY_ROOT'}</span> · Subsystem:{' '}
              <span className="text-slate-200">{state.analytics.subsystem}</span> · Health:{' '}
              <span className="text-cyan-300 font-semibold">{(state.analytics.health_index * 100).toFixed(1)}%</span>
            </p>
          </div>
        </div>

        {/* 3D Action Tools Bar */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={handleToggleThermal}
            className={`flex items-center gap-1 rounded px-2.5 py-1 text-[11px] font-mono font-medium transition-all ${
              thermalActive
                ? 'bg-rose-500/20 border border-rose-500 text-rose-300 shadow-[0_0_12px_rgba(244,63,94,0.3)]'
                : 'bg-slate-900 border border-slate-700 text-slate-300 hover:border-cyan-500/40 hover:text-cyan-300'
            }`}
            title="Toggle Thermal Scavenging Heatmap Shader [T]"
          >
            <Thermometer className="h-3.5 w-3.5" />
            <span>THERMAL</span>
          </button>

          <button
            onClick={handleToggleExploded}
            className={`flex items-center gap-1 rounded px-2.5 py-1 text-[11px] font-mono font-medium transition-all ${
              explodedActive
                ? 'bg-cyan-500/20 border border-cyan-400 text-cyan-200 shadow-[0_0_12px_rgba(6,182,212,0.3)]'
                : 'bg-slate-900 border border-slate-700 text-slate-300 hover:border-cyan-500/40 hover:text-cyan-300'
            }`}
            title="Radial Exploded Assembly Inspection [X]"
          >
            <Layers className="h-3.5 w-3.5" />
            <span>EXPLODE</span>
          </button>

          <button
            onClick={handleToggleWireframe}
            className={`flex items-center gap-1 rounded px-2.5 py-1 text-[11px] font-mono font-medium transition-all ${
              wireframeActive
                ? 'bg-cyan-500/20 border border-cyan-400 text-cyan-200'
                : 'bg-slate-900 border border-slate-700 text-slate-300 hover:border-cyan-500/40 hover:text-cyan-300'
            }`}
            title="Wireframe Mesh Inspection [W]"
          >
            <Eye className="h-3.5 w-3.5" />
            <span>WIREFRAME</span>
          </button>

          <button
            onClick={handleCaptureSnapshot}
            className="flex items-center gap-1 rounded bg-slate-900 border border-slate-700 px-2.5 py-1 text-[11px] font-mono font-medium text-slate-300 hover:border-cyan-500/40 hover:text-cyan-300 transition-all"
            title="Capture 4K High-Resolution Diagnostic PNG [P]"
          >
            <Camera className="h-3.5 w-3.5" />
            <span>SNAP</span>
          </button>

          <button
            onClick={handleResetView}
            className="flex items-center gap-1 rounded bg-slate-900 border border-slate-700 px-2 py-1 text-[11px] font-mono font-medium text-slate-300 hover:border-cyan-500/40 hover:text-cyan-300 transition-all"
            title="Reset Camera & Orbit Orbit [ESC]"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>

          <button
            onClick={toggleFullscreen}
            className="flex items-center gap-1 rounded bg-slate-900 border border-slate-700 px-2 py-1 text-[11px] font-mono font-medium text-slate-300 hover:border-cyan-500/40 hover:text-cyan-300 transition-all"
            title="Toggle Fullscreen Canvas"
          >
            {isFullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Subsystem Station Navigation Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto bg-slate-950/60 border-b border-cyan-500/10 px-4 py-1.5 text-xs">
        <span className="text-[10px] font-mono text-cyan-500/70 uppercase tracking-widest mr-2 shrink-0">
          INSPECTION STATIONS:
        </span>
        {STATIONS.map((station) => (
          <button
            key={station.id}
            onClick={() => handleSelectStation(station.id)}
            className={`shrink-0 rounded px-2.5 py-1 font-mono text-[10px] font-medium transition-all ${
              activeStation === station.id
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-[0_0_8px_rgba(0,229,255,0.25)]'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 border border-transparent'
            }`}
          >
            <span className="text-cyan-500/60 mr-1">{station.tag.replace('STATION ', 'S')}</span>
            {station.label}
          </button>
        ))}
      </div>

      {/* Embedded High-Fidelity 3D Viewport */}
      <div className="relative flex-1 w-full h-[620px] bg-[#040d14]">
        <iframe
          ref={iframeRef}
          title="DRDO Aero-Piston High-Fidelity 3D Digital Twin"
          src={twinUrl}
          className="absolute inset-0 w-full h-full border-0 bg-[#040d14]"
          allow="fullscreen"
        />
      </div>

      {/* Live HUD Bottom Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-cyan-500/20 bg-slate-950/90 px-4 py-2 font-mono text-[11px] text-slate-400">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">RPM:</span>
            <span className="font-bold text-cyan-400">{Math.round(state.telemetry.ENGINE_RPM)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">CHT MAX:</span>
            <span className="font-bold text-amber-400">
              {Math.max(
                state.telemetry.CHT_1,
                state.telemetry.CHT_2,
                state.telemetry.CHT_3,
                state.telemetry.CHT_4
              ).toFixed(1)}
              °C
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">MAP:</span>
            <span className="font-bold text-cyan-300">{(state.telemetry.MAP_INHG ?? state.telemetry.MAP).toFixed(1)} inHg</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">OIL P:</span>
            <span className="font-bold text-cyan-300">{(state.telemetry.OIL_PRESS_BAR ?? state.telemetry.OIL_PRESS).toFixed(1)} bar</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-slate-500">
            FADEC LANE: <span className="text-cyan-400 font-bold">{state.telemetry.FADEC_ACTIVE_LANE}</span>
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-500">
            ATA: <span className="text-slate-300 font-bold">{state.analytics.ata_chapter}</span>
          </span>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-1.5">
            <Activity className="h-3 w-3 text-cyan-400" />
            <span className="text-cyan-300">20 HZ SYNC AUTHORITATIVE</span>
          </div>
        </div>
      </div>
    </div>
  );
};
export default DigitalTwinViewer;
