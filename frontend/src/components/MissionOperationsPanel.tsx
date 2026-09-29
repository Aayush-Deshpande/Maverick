import React, { useState, useEffect, useMemo } from 'react';
import {
  Compass,
  Play,
  Pause,
  Square,
  ShieldAlert,
  FastForward,
  RotateCcw,
  CheckCircle2,
  Flame,
  Sliders,
  Maximize2,
  Minimize2,
  Clock,
  Plus,
  Trash2,
  Edit3,
  Monitor,
  Zap,
} from 'lucide-react';
import { useMissionSocket } from '../hooks/useMissionSocket';
import { useEngineSelection } from '../contexts/EngineSelectionContext';
import { MissionDefinition, MissionPhaseSpec, PhaseScheduledEvent } from '../types/mission';
import { NavArea } from '../App';
import { MissionReliabilityPanel } from './MissionReliabilityPanel';

interface MissionOperationsPanelProps {
  serverUrl: string;
  onNavigate?: (area: NavArea) => void;
  fullscreenSimOnly?: boolean;
}

type SubTab = 'PLANNER' | 'SIMULATION' | 'DEBRIEF';

const STANDARD_PHASE_NAMES = ['TAKEOFF', 'CLIMB', 'CRUISE', 'LOITER', 'DESCENT', 'LANDING'];

const PHASE_COLORS: Record<string, { bg: string; border: string; text: string; glow: string }> = {
  TAKEOFF: { bg: 'bg-emerald-500/20', border: 'border-emerald-500/50', text: 'text-emerald-300', glow: 'shadow-emerald-500/20' },
  CLIMB: { bg: 'bg-sky-500/20', border: 'border-sky-500/50', text: 'text-sky-300', glow: 'shadow-sky-500/20' },
  CRUISE: { bg: 'bg-indigo-500/20', border: 'border-indigo-500/50', text: 'text-indigo-300', glow: 'shadow-indigo-500/20' },
  LOITER: { bg: 'bg-purple-500/20', border: 'border-purple-500/50', text: 'text-purple-300', glow: 'shadow-purple-500/20' },
  DESCENT: { bg: 'bg-amber-500/20', border: 'border-amber-500/50', text: 'text-amber-300', glow: 'shadow-amber-500/20' },
  LANDING: { bg: 'bg-teal-500/20', border: 'border-teal-500/50', text: 'text-teal-300', glow: 'shadow-teal-500/20' },
};

function getPhaseStyle(name: string) {
  const upper = name.toUpperCase();
  for (const k of Object.keys(PHASE_COLORS)) {
    if (upper.includes(k)) return PHASE_COLORS[k];
  }
  return { bg: 'bg-cyan-500/20', border: 'border-cyan-500/40', text: 'text-cyan-300', glow: 'shadow-cyan-500/20' };
}

export const MissionOperationsPanel: React.FC<MissionOperationsPanelProps> = ({
  serverUrl,
  onNavigate,
  fullscreenSimOnly = false,
}) => {
  const {
    missionState,
    definition,
    templates,
    isConnected,
    loadMission,
    startMission,
    pauseMission,
    resumeMission,
    abortMission,
    derateMission,
    setTimeScale,
    injectLiveFault,
    clearFaults,
  } = useMissionSocket(serverUrl);

  // Computed ONCE per mount, not on every render: missionState updates ~20x/sec from the
  // websocket, and this component re-renders on every update. Date.now() inlined directly
  // in the iframe's src (as it previously was) recomputes every render, which changes the
  // src on every render, which makes React tear down and reload the entire iframe
  // continuously -- the canyon_flight page never got enough time between reloads to finish
  // loading its GLB/Draco assets, so the 3D view stayed permanently blank. This cache-bust
  // value only needs to change once per page load (to dodge a stale browser cache after a
  // deploy), not on every mission tick.
  const canyonFlightCacheBust = useMemo(() => Date.now(), []);

  const { engineId, selectEngine } = useEngineSelection();
  const [activeTab, setActiveTab] = useState<SubTab>(fullscreenSimOnly ? 'SIMULATION' : 'PLANNER');
  const [isCinemaMode, setIsCinemaMode] = useState<boolean>(fullscreenSimOnly);

  // Local Editable Plan Draft
  const [draftPlan, setDraftPlan] = useState<MissionDefinition | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('MSN-ENDURANCE-PHASE-ROTAX-912IS');
  const [selectedPhaseIdx, setSelectedPhaseIdx] = useState<number>(0);
  const [plannerMode, setPlannerMode] = useState<'PHASE' | 'WAYPOINTS'>('PHASE');

  // New Phase Scheduled Fault Form State
  const [newFaultPhase, setNewFaultPhase] = useState<string>('CRUISE');
  const [newFaultElapsed, setNewFaultElapsed] = useState<number>(60.0);
  const [newFaultMode, setNewFaultMode] = useState<string>('COOLING_DEGRADATION');
  const [newFaultCylinder, setNewFaultCylinder] = useState<number>(1);
  const [newFaultSeverity, setNewFaultSeverity] = useState<number>(0.85);
  const [newFaultRamp, setNewFaultRamp] = useState<number>(15.0);

  // Live Fault Injector Form
  const [liveFaultMode, setLiveFaultMode] = useState<string>('COOLING_DEGRADATION');
  const [liveFaultSeverity, setLiveFaultSeverity] = useState<number>(0.85);
  const [liveFaultRamp, setLiveFaultRamp] = useState<number>(15.0);
  const [liveFaultCylinder, setLiveFaultCylinder] = useState<number>(1);
  const [isInjectingLive, setIsInjectingLive] = useState<boolean>(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  // When returning to the embedded Mission Operations Center from a just-finished
  // full-screen sortie, land on DEBRIEF (not the planner)
  useEffect(() => {
    if (!fullscreenSimOnly && (missionState?.status === 'COMPLETED' || missionState?.status === 'ABORTED')) {
      setActiveTab('DEBRIEF');
    }
  }, [fullscreenSimOnly, missionState?.status]);

  // Sync draftPlan with active definition or first template
  useEffect(() => {
    if (definition && !draftPlan) {
      const clone = JSON.parse(JSON.stringify(definition));
      setDraftPlan(clone);
      if (clone.phases && clone.phases.length > 0) {
        setPlannerMode('PHASE');
      }
    } else if (templates.length > 0 && !draftPlan) {
      const clone = JSON.parse(JSON.stringify(templates[0]));
      setDraftPlan(clone);
      setSelectedTemplateId(clone.mission_id);
      if (clone.phases && clone.phases.length > 0) {
        setPlannerMode('PHASE');
      }
    }
  }, [definition, templates, draftPlan]);

  const handleSelectTemplate = (template: MissionDefinition) => {
    setSelectedTemplateId(template.mission_id);
    const clone: MissionDefinition = JSON.parse(JSON.stringify(template));
    setDraftPlan(clone);
    setSelectedPhaseIdx(0);
    if (clone.phases && clone.phases.length > 0) {
      setPlannerMode('PHASE');
      setNewFaultPhase(clone.phases[0]?.name || 'CRUISE');
    } else {
      setPlannerMode('WAYPOINTS');
    }
    // Align engine selection
    if (clone.engine_id && clone.engine_id !== engineId) {
      void selectEngine(clone.engine_id);
    }
  };

  const [divertLat, setDivertLat] = useState<string>('34.70');
  const [divertLon, setDivertLon] = useState<string>('77.60');
  const [isDiverting, setIsDiverting] = useState<boolean>(false);

  const launchNativeBlender = async (mode: 'client' | 'canyon' = 'client') => {
    try {
      setActionFeedback(`Launching native Blender simulation (${mode === 'canyon' ? 'Standalone Canyon Flight' : 'Live Mission Client'})...`);
      const res = await fetch(`${serverUrl.replace(/\/$/, '')}/api/missions/launch-blender`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Launch failed');
      setActionFeedback(`🚀 ${data.title} launched in native Blender (PID ${data.pid}). Check your taskbar.`);
    } catch (err: any) {
      setActionFeedback(`Blender launch failed: ${err.message}`);
    }
  };

  const handleLaunchPlan = async () => {
    if (!draftPlan) return;
    try {
      setActionFeedback('Validating and loading mission plan into Digital Twin Executive...');
      // Sync planned duration
      const totalPhasesDuration = (draftPlan.phases || []).reduce((acc, p) => acc + p.duration_sec, 0);
      const readyPlan = {
        ...draftPlan,
        planned_duration_sec: totalPhasesDuration > 0 ? totalPhasesDuration : draftPlan.planned_duration_sec,
      };

      await loadMission(readyPlan);
      await startMission();
      setActionFeedback('🚀 Mission sortie running in real-time twin executive.');
      setActiveTab('SIMULATION');
      setTimeout(() => setActionFeedback(null), 3000);
    } catch (err: any) {
      setActionFeedback(`Launch failed: ${err.message}`);
    }
  };

  const handleStartMission = async () => {
    try {
      setActionFeedback('Arming and launching mission flight sortie...');
      if (draftPlan) {
        const totalPhasesDuration = (draftPlan.phases || []).reduce((acc, p) => acc + p.duration_sec, 0);
        const readyPlan = {
          ...draftPlan,
          planned_duration_sec: totalPhasesDuration > 0 ? totalPhasesDuration : draftPlan.planned_duration_sec,
        };
        await loadMission(readyPlan);
      }
      await startMission();
      setActionFeedback('🚀 Mission sortie running in real-time twin executive.');
      setActiveTab('SIMULATION');
      setTimeout(() => setActionFeedback(null), 3500);
    } catch (err: any) {
      setActionFeedback(`Start mission failed: ${err.message}`);
    }
  };

  const handleRestartMission = async () => {
    try {
      setActionFeedback('Resetting mission flight sortie to T+00:00...');
      if (draftPlan) {
        const totalPhasesDuration = (draftPlan.phases || []).reduce((acc, p) => acc + p.duration_sec, 0);
        const readyPlan = {
          ...draftPlan,
          planned_duration_sec: totalPhasesDuration > 0 ? totalPhasesDuration : draftPlan.planned_duration_sec,
        };
        await loadMission(readyPlan);
      }
      await startMission();
      setActionFeedback('🚀 Mission sortie re-armed and running.');
      setTimeout(() => setActionFeedback(null), 3500);
    } catch (err: any) {
      setActionFeedback(`Reset mission failed: ${err.message}`);
    }
  };

  const handleLaunchAndOpenBlender = async () => {
    await handleLaunchPlan();
    await launchNativeBlender('client');
  };

  const handleDivert = async () => {
    try {
      setIsDiverting(true);
      const lat = Number(divertLat);
      const lon = Number(divertLon);
      const res = await fetch(`${serverUrl.replace(/\/$/, '')}/api/missions/divert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lon, name: 'OPERATOR_DIVERT' }),
      });
      if (!res.ok) throw new Error(await res.text());
      setActionFeedback(`Diverting to (${lat.toFixed(3)}, ${lon.toFixed(3)}).`);
      setTimeout(() => setActionFeedback(null), 4000);
    } catch (err: any) {
      setActionFeedback(`Divert failed: ${err.message}`);
    } finally {
      setIsDiverting(false);
    }
  };

  const handleInjectFaultLive = async () => {
    try {
      setIsInjectingLive(true);
      await injectLiveFault(liveFaultMode, liveFaultCylinder, liveFaultSeverity, liveFaultRamp);
      setActionFeedback(`Fault ${liveFaultMode} injected live!`);
      setTimeout(() => setActionFeedback(null), 4000);
    } catch (err: any) {
      setActionFeedback(`Fault injection failed: ${err.message}`);
    } finally {
      setIsInjectingLive(false);
    }
  };

  const handleDerate = async (scale: number) => {
    try {
      const res = await derateMission(scale);
      setActionFeedback(`Propulsion derated to ${Math.round(scale * 100)}%: ${res.advisory}`);
      setTimeout(() => setActionFeedback(null), 5000);
    } catch (err: any) {
      setActionFeedback(`Derate failed: ${err.message}`);
    }
  };

  const handleAbort = async () => {
    try {
      await abortMission();
      setActionFeedback('Emergency ABORT / RTB commanded. Sortie exported.');
      setTimeout(() => setActiveTab('DEBRIEF'), 1000);
    } catch (err: any) {
      setActionFeedback(`Abort failed: ${err.message}`);
    }
  };

  const handleTimeScale = async (scale: number) => {
    try {
      await setTimeScale(scale);
    } catch (err: any) {
      console.warn('Timescale error:', err);
    }
  };

  // Phase Manipulation Helpers
  const totalPhaseDuration = useMemo(() => {
    if (!draftPlan?.phases) return 0;
    return draftPlan.phases.reduce((sum, p) => sum + p.duration_sec, 0);
  }, [draftPlan?.phases]);

  const handleUpdatePhase = (idx: number, field: keyof MissionPhaseSpec, value: any) => {
    if (!draftPlan?.phases) return;
    const newPhases = [...draftPlan.phases];
    newPhases[idx] = { ...newPhases[idx], [field]: value };
    const newDuration = newPhases.reduce((s, p) => s + p.duration_sec, 0);
    setDraftPlan({ ...draftPlan, phases: newPhases, planned_duration_sec: newDuration });
  };

  const handleAddPhase = () => {
    if (!draftPlan) return;
    const phases = draftPlan.phases || [];
    const prevPhase = phases[phases.length - 1];
    const newStart = prevPhase ? prevPhase.end_alt_ft : 10000;
    const newPhase: MissionPhaseSpec = {
      name: `PHASE_${phases.length + 1}`,
      duration_sec: 60.0,
      start_alt_ft: newStart,
      end_alt_ft: newStart,
      throttle_pct: 65.0,
      oat_c: 10.0,
      dust_mg_m3: 0.15,
    };
    const nextPhases = [...phases, newPhase];
    setDraftPlan({
      ...draftPlan,
      phases: nextPhases,
      planned_duration_sec: nextPhases.reduce((s, p) => s + p.duration_sec, 0),
    });
    setSelectedPhaseIdx(nextPhases.length - 1);
  };

  const handleDeletePhase = (idx: number) => {
    if (!draftPlan?.phases || draftPlan.phases.length <= 1) return;
    const nextPhases = draftPlan.phases.filter((_, i) => i !== idx);
    const newSelected = Math.max(0, Math.min(selectedPhaseIdx, nextPhases.length - 1));
    setDraftPlan({
      ...draftPlan,
      phases: nextPhases,
      planned_duration_sec: nextPhases.reduce((s, p) => s + p.duration_sec, 0),
    });
    setSelectedPhaseIdx(newSelected);
  };

  const handleInitializeDefaultPhases = () => {
    if (!draftPlan) return;
    const defaultPhases: MissionPhaseSpec[] = [
      { name: 'TAKEOFF', duration_sec: 30.0, start_alt_ft: 10480.0, end_alt_ft: 10800.0, throttle_pct: 90.0, oat_c: 8.0 },
      { name: 'CLIMB', duration_sec: 90.0, start_alt_ft: 10800.0, end_alt_ft: 16000.0, throttle_pct: 80.0, oat_c: 2.0 },
      { name: 'CRUISE', duration_sec: 150.0, start_alt_ft: 16000.0, end_alt_ft: 16000.0, throttle_pct: 65.0, oat_c: -6.0 },
      { name: 'LOITER', duration_sec: 90.0, start_alt_ft: 16000.0, end_alt_ft: 16000.0, throttle_pct: 55.0, oat_c: -6.0 },
      { name: 'DESCENT', duration_sec: 60.0, start_alt_ft: 16000.0, end_alt_ft: 10800.0, throttle_pct: 40.0, oat_c: 4.0 },
      { name: 'LANDING', duration_sec: 30.0, start_alt_ft: 10800.0, end_alt_ft: 10480.0, throttle_pct: 20.0, oat_c: 8.0 },
    ];
    const defaultEvents: PhaseScheduledEvent[] = [
      { phase_name: 'CRUISE', elapsed_in_phase_sec: 60.0, fault_mode: 'COOLING_DEGRADATION', severity: 0.85, ramp_sec: 30.0 },
    ];
    setDraftPlan({
      ...draftPlan,
      phases: defaultPhases,
      phase_events: defaultEvents,
      planned_duration_sec: defaultPhases.reduce((s, p) => s + p.duration_sec, 0),
    });
    setPlannerMode('PHASE');
    setSelectedPhaseIdx(0);
    setNewFaultPhase('CRUISE');
  };

  const handleAddPhaseScheduledEvent = () => {
    if (!draftPlan) return;
    const currentEvents = draftPlan.phase_events || [];
    const newEvent: PhaseScheduledEvent = {
      phase_name: newFaultPhase,
      elapsed_in_phase_sec: Number(newFaultElapsed),
      action: 'INJECT_FAULT',
      fault_mode: newFaultMode,
      cylinder: (newFaultMode === 'INJECTOR_CLOGGED' || newFaultMode === 'SPARK_PLUG_FOULING') ? newFaultCylinder : undefined,
      severity: Number(newFaultSeverity),
      ramp_sec: Number(newFaultRamp),
      applied: false,
    };
    setDraftPlan({
      ...draftPlan,
      phase_events: [...currentEvents, newEvent],
    });
  };

  const handleDeletePhaseScheduledEvent = (idx: number) => {
    if (!draftPlan?.phase_events) return;
    const nextEvents = draftPlan.phase_events.filter((_, i) => i !== idx);
    setDraftPlan({ ...draftPlan, phase_events: nextEvents });
  };

  // Full-Screen Sim Only View
  if (fullscreenSimOnly) {
    return (
      <div className="min-h-screen flex flex-col bg-[#030a12]">
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-1.5 bg-[#030a12] border-b border-cyan-900/40">
          <div className="flex items-center gap-3">
            <button
              onClick={() => onNavigate && onNavigate('MISSION_PLANNING')}
              className="text-[10px] font-mono font-bold text-slate-400 hover:text-cyan-300 flex items-center gap-1.5 transition-colors"
            >
              ← EXIT TO MISSION OPERATIONS CENTER
            </button>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                missionState?.status === 'RUNNING'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  : missionState?.status === 'DERATED'
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                  : missionState?.status === 'PAUSED'
                  ? 'bg-slate-500/20 text-slate-300 border border-slate-500/40'
                  : 'bg-red-500/20 text-red-400 border border-red-500/40'
              }`}
            >
              {missionState?.status || 'READY'}
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              PHASE: <strong className="text-amber-400">{missionState?.phase || 'PREFLIGHT'}</strong>
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              {missionState?.phase_duration_sec && missionState.phase_duration_sec > 0
                ? `PHASE ${(missionState.current_phase_idx ?? 0) + 1} / ${definition?.phases?.length || 6} (${missionState.phase} ${Math.floor(missionState.elapsed_in_phase_sec || 0)}s / ${Math.floor(missionState.phase_duration_sec)}s)`
                : `WAYPOINT ${missionState?.current_waypoint_idx || 1} / ${definition?.waypoints.length || 6}`}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 bg-surface-dark p-0.5 rounded border border-surface-border">
              {[1, 2, 5, 10].map((scale) => (
                <button
                  key={scale}
                  onClick={() => handleTimeScale(scale)}
                  className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                    (missionState?.time_scale || 1) === scale
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {scale}x
                </button>
              ))}
            </div>

            {missionState?.status === 'RUNNING' || missionState?.status === 'DERATED' ? (
              <button
                onClick={pauseMission}
                className="px-2.5 py-1 rounded bg-amber-600 hover:bg-amber-500 text-white font-mono text-[10px] font-bold flex items-center gap-1 transition-colors cursor-pointer"
              >
                <Pause className="w-3 h-3 fill-current" /> PAUSE
              </button>
            ) : missionState?.status === 'PAUSED' ? (
              <button
                onClick={resumeMission}
                className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-[10px] font-bold flex items-center gap-1 transition-colors cursor-pointer"
              >
                <Play className="w-3 h-3 fill-current" /> RESUME
              </button>
            ) : (
              <button
                onClick={handleStartMission}
                className="px-3 py-1 rounded bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-mono text-[10px] font-black flex items-center gap-1 shadow-md shadow-emerald-500/30 transition-all hover:scale-105 animate-pulse cursor-pointer border border-emerald-300"
              >
                <Play className="w-3 h-3 fill-current" /> START MISSION
              </button>
            )}

            <button
              onClick={() => handleDerate(0.85)}
              className="px-2.5 py-1 rounded bg-amber-600/80 hover:bg-amber-500 text-white font-mono text-[10px] font-bold flex items-center gap-1 transition-colors"
              title="Prescriptive Derate: caps maximum throttle demand to 85%"
            >
              <Sliders className="w-3 h-3" /> DERATE
            </button>

            <div className="flex items-center gap-1">
              <input
                type="text"
                value={divertLat}
                onChange={(e) => setDivertLat(e.target.value)}
                className="w-14 bg-surface-dark border border-surface-border rounded px-1 py-1 text-[10px] font-mono text-white"
                title="Divert latitude"
              />
              <input
                type="text"
                value={divertLon}
                onChange={(e) => setDivertLon(e.target.value)}
                className="w-14 bg-surface-dark border border-surface-border rounded px-1 py-1 text-[10px] font-mono text-white"
                title="Divert longitude"
              />
              <button
                onClick={handleDivert}
                disabled={isDiverting}
                className="px-2.5 py-1 rounded bg-sky-600/80 hover:bg-sky-500 text-white font-mono text-[10px] font-bold flex items-center gap-1 transition-colors"
                title="Divert to alternate lat/lon"
              >
                <Compass className="w-3 h-3" /> DIVERT
              </button>
            </div>

            <button
              onClick={handleAbort}
              className="px-2.5 py-1 rounded bg-red-600/90 hover:bg-red-500 text-white font-mono text-[10px] font-bold flex items-center gap-1 transition-colors"
              title="Emergency Abort / Return to Base"
            >
              <Square className="w-3 h-3 fill-current" /> ABORT RTB
            </button>

            <button
              onClick={() => launchNativeBlender('client')}
              className="px-2.5 py-1 rounded bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono text-[10px] font-bold flex items-center gap-1 transition-colors shadow"
              title="Launch Authoritative Native Blender Cockpit (launch_mission_flight_client.bat)"
            >
              <Play className="w-3 h-3 fill-current" /> BLENDER COCKPIT
            </button>

            <button
              onClick={() => launchNativeBlender('canyon')}
              className="px-2.5 py-1 rounded bg-amber-500 hover:bg-amber-400 text-slate-950 font-mono text-[10px] font-bold flex items-center gap-1 transition-colors shadow"
              title="Launch Standalone Canyon Simulation (launch_canyon_simulation.bat)"
            >
              <Zap className="w-3 h-3 fill-current" /> CANYON SIM
            </button>
          </div>
        </div>

        {actionFeedback && (
          <div className="px-3 py-1.5 bg-cyan-950/60 border-b border-cyan-500/30 text-cyan-300 text-[10px] font-mono">
            {actionFeedback}
          </div>
        )}

        <div className="px-3 py-1 bg-amber-950/40 border-b border-amber-500/30 flex items-center justify-between text-[10px] font-mono">
          <span className="text-amber-300 font-bold">
            [WEB 3D PROTOTYPE ECHO] Lightweight C2 Telemetry Mirror
          </span>
          <span className="text-slate-400">
            Authoritative High-Fidelity Simulation runs in native Blender (<code className="text-cyan-300">launch_canyon_simulation.bat</code>)
          </span>
        </div>

        <div className="flex-1 relative">
          <iframe
            id="canyon-sim-iframe-fullscreen"
            src={`${serverUrl.replace(/\/$/, '')}/apps/canyon_flight/`}
            className="absolute inset-0 w-full h-full border-0"
            title="Tactical Canyon Flight Simulation"
          />
        </div>

        {(missionState?.status === 'COMPLETED' || missionState?.status === 'ABORTED') && (
          <div className="px-3 py-2 bg-emerald-950/60 border-t border-emerald-500/30 flex items-center justify-between">
            <span className="text-xs font-mono text-emerald-300">
              Mission {missionState.status.toLowerCase()} — sortie recorded.
            </span>
            <button
              onClick={() => onNavigate && onNavigate('MISSION_PLANNING')}
              className="px-3 py-1.5 rounded bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono font-bold text-[10px] flex items-center gap-1.5 transition-all"
            >
              <FastForward className="w-3.5 h-3.5 fill-current" /> VIEW SORTIE DEBRIEF
            </button>
          </div>
        )}
      </div>
    );
  }

  const selectedPhase = draftPlan?.phases && draftPlan.phases[selectedPhaseIdx];

  return (
    <div className="surface-panel p-4 sm:p-5 space-y-4">
      {/* Top Header & Sub-Tab Navigation */}
      <div className="flex flex-wrap items-center justify-between border-b border-surface-border pb-3 gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold tracking-wider text-white uppercase font-mono">
                Mission Operations Center
              </h2>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                  isConnected
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                    : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                }`}
              >
                {isConnected ? '20 Hz WS CONNECTED' : 'WS RECONNECTING'}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Phase-Based Mission Profile Authoring, Live 3D Digital Twin Simulation & Prognostic What-If Advisory
            </p>
          </div>
        </div>

        {/* Top Header Controls: Sub-Tabs & Global Start Mission Action */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Sub-Tab Navigation Buttons */}
          <div className="flex items-center gap-1.5 bg-surface-darker/80 p-1 rounded-lg border border-surface-border">
            <button
              onClick={() => setActiveTab('PLANNER')}
              className={`px-3 py-1.5 rounded text-xs font-mono font-semibold transition-all ${
                activeTab === 'PLANNER'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              1. PLANNER
            </button>
            <button
              onClick={() => setActiveTab('SIMULATION')}
              className={`px-3 py-1.5 rounded text-xs font-mono font-semibold transition-all ${
                activeTab === 'SIMULATION'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              2. COCKPIT & CANYON 3D
            </button>
            <button
              onClick={() => setActiveTab('DEBRIEF')}
              className={`px-3 py-1.5 rounded text-xs font-mono font-semibold transition-all ${
                activeTab === 'DEBRIEF'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              3. SORTIE DEBRIEF
            </button>
          </div>

          {/* Persistent Global Mission Control Trigger */}
          {missionState?.status === 'RUNNING' || missionState?.status === 'DERATED' ? (
            <div className="flex items-center gap-1.5">
              <button
                onClick={pauseMission}
                className="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 font-mono text-xs font-bold flex items-center gap-1.5 transition-all shadow cursor-pointer"
                title="Pause active mission flight"
              >
                <Pause className="w-3.5 h-3.5 fill-current" /> PAUSE
              </button>
              <button
                onClick={handleAbort}
                className="px-2.5 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/40 font-mono text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer"
                title="Emergency Abort / Return to Base"
              >
                <Square className="w-3 h-3 fill-current" /> ABORT
              </button>
            </div>
          ) : missionState?.status === 'PAUSED' ? (
            <div className="flex items-center gap-1.5">
              <button
                onClick={resumeMission}
                className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-mono text-xs font-black flex items-center gap-1.5 transition-all shadow-md shadow-emerald-500/25 cursor-pointer"
                title="Resume mission simulation"
              >
                <Play className="w-3.5 h-3.5 fill-current" /> RESUME
              </button>
              <button
                onClick={handleAbort}
                className="px-2.5 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/40 font-mono text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer"
              >
                <Square className="w-3 h-3 fill-current" /> ABORT
              </button>
            </div>
          ) : (
            <button
              onClick={handleStartMission}
              className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-mono text-xs font-black flex items-center gap-2 shadow-lg shadow-emerald-500/35 transition-all hover:scale-105 animate-pulse cursor-pointer border border-emerald-300"
              title="Start real-time mission sortie in C2 Digital Twin"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>START MISSION</span>
            </button>
          )}
        </div>
      </div>

      {actionFeedback && (
        <div className="p-2.5 rounded bg-cyan-950/40 border border-cyan-500/30 text-cyan-300 text-xs font-mono flex items-center justify-between">
          <span>{actionFeedback}</span>
          <button onClick={() => setActionFeedback(null)} className="text-slate-400 hover:text-white text-xs">
            ✕
          </button>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SUB-TAB 1: MISSION PLANNER (PHASE-BASED TIMELINE & WHAT-IF)               */}
      {/* ========================================================================= */}
      {activeTab === 'PLANNER' && draftPlan && (
        <div className="space-y-5">
          {/* Top Planner Action Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-surface-darker/80 border border-surface-border">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                  Operational Theater & Profile Presets
                </span>
                <span className="text-[10px] font-mono text-cyan-400">
                  ARCH-2026-MP-002 Phase-Driven Twin
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Select an operational mission profile, inspect timeline phases, then start the sortie.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleStartMission}
                className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-mono font-black text-xs flex items-center gap-2 shadow-lg shadow-emerald-500/30 transition-all hover:scale-105 animate-pulse cursor-pointer border border-emerald-300"
                title="Validate plan and start sortie immediately in C2 Simulation"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>START MISSION (C2)</span>
              </button>
              <button
                onClick={handleLaunchAndOpenBlender}
                className="px-4 py-2 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-mono font-bold text-xs flex items-center gap-1.5 transition-all shadow-md shadow-amber-500/25 cursor-pointer"
                title="Launch in Native Blender Cockpit (120 FPS EEVEE)"
              >
                <Monitor className="w-3.5 h-3.5" />
                <span>LAUNCH BLENDER</span>
              </button>
            </div>
          </div>

          {/* Preset Selector Cards */}
          <div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
              {templates.map((tpl) => {
                const hasPhases = tpl.phases && tpl.phases.length > 0;
                return (
                  <div
                    key={`${tpl.mission_id}-${tpl.engine_id}`}
                    onClick={() => handleSelectTemplate(tpl)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${
                      selectedTemplateId === tpl.mission_id
                        ? 'bg-cyan-500/10 border-cyan-400 shadow-md shadow-cyan-500/10'
                        : 'bg-surface-darker/60 border-surface-border hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[9px] font-mono font-bold text-cyan-400 px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-800">
                        {tpl.engine_id}
                      </span>
                      {hasPhases ? (
                        <span className="text-[9px] font-mono text-emerald-400 font-bold bg-emerald-950/60 px-1 py-0.5 rounded border border-emerald-800/60">
                          {tpl.phases?.length} PHASES
                        </span>
                      ) : (
                        <span className="text-[9px] font-mono text-slate-500">
                          {tpl.waypoints?.length || 0} WP
                        </span>
                      )}
                    </div>
                    <h4 className="text-xs font-bold text-white mb-1 line-clamp-1">{tpl.name}</h4>
                    <div className="text-[10px] text-slate-400 flex items-center justify-between font-mono">
                      <span>{Math.round(tpl.planned_duration_sec / 60)} min</span>
                      <span className="truncate max-w-[80px]">{tpl.environment.theater_name}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Engine, Airframe & Mode Settings */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 rounded-lg bg-surface-darker/60 border border-surface-border">
            <div>
              <label className="text-xs font-mono font-bold text-slate-300 mb-1.5 block">
                Selected Engine Twin
              </label>
              <select
                value={draftPlan.engine_id}
                onChange={(e) => {
                  const newId = e.target.value;
                  setDraftPlan({ ...draftPlan, engine_id: newId });
                  void selectEngine(newId);
                }}
                className="w-full bg-surface-dark border border-surface-border rounded p-2 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-400"
              >
                <option value="rotax_912is">Rotax 912 iS (Naturally Aspirated)</option>
                <option value="rotax_914">Rotax 914 (Turbocharged)</option>
                <option value="rotax_915is">Rotax 915 iS (Turbo Intercooled)</option>
                <option value="austro_ae300">Austro Engine AE300 (Common-Rail Turbodiesel)</option>
                <option value="vrde_jayem_2_2l">VRDE Jayem 2.2L (Indigenous Aero-Diesel)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-mono font-bold text-slate-300 mb-1.5 block">
                Airframe Model
              </label>
              <select
                value={draftPlan.airframe_id}
                onChange={(e) => setDraftPlan({ ...draftPlan, airframe_id: e.target.value })}
                className="w-full bg-surface-dark border border-surface-border rounded p-2 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-400"
              >
                <option value="bayraktar_tb3">Bayraktar TB3 UCAV (14.0m Wingspan)</option>
                <option value="tapas_bh201">TAPAS-BH-201 MALE UAV (20.6m Wingspan)</option>
                <option value="mq1_predator">MQ-1 Predator Recon UAV (14.8m Wingspan)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-mono font-bold text-slate-300 mb-1.5 block">
                Total Sortie Duration
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={draftPlan.planned_duration_sec}
                  readOnly={plannerMode === 'PHASE' && (draftPlan.phases?.length || 0) > 0}
                  onChange={(e) => setDraftPlan({ ...draftPlan, planned_duration_sec: Number(e.target.value) })}
                  className="w-full bg-surface-dark border border-surface-border rounded p-2 text-xs font-mono text-white focus:outline-none focus:border-cyan-400"
                />
                <span className="text-xs font-mono text-slate-400 whitespace-nowrap">
                  ({(draftPlan.planned_duration_sec / 60).toFixed(1)}m)
                </span>
              </div>
            </div>

            <div>
              <label className="text-xs font-mono font-bold text-slate-300 mb-1.5 block">
                Planning Mode
              </label>
              <div className="flex items-center gap-1 bg-surface-dark p-1 rounded border border-surface-border">
                <button
                  type="button"
                  onClick={() => setPlannerMode('PHASE')}
                  className={`flex-1 py-1 px-2 rounded text-[11px] font-mono font-bold transition-all ${
                    plannerMode === 'PHASE'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Phase Profile
                </button>
                <button
                  type="button"
                  onClick={() => setPlannerMode('WAYPOINTS')}
                  className={`flex-1 py-1 px-2 rounded text-[11px] font-mono font-bold transition-all ${
                    plannerMode === 'WAYPOINTS'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Waypoints
                </button>
              </div>
            </div>
          </div>

          {/* ======================================================================= */}
          {/* PRIMARY: PHASE TIMELINE BUILDER                                         */}
          {/* ======================================================================= */}
          {plannerMode === 'PHASE' && (
            <div className="space-y-4">
              {(!draftPlan.phases || draftPlan.phases.length === 0) ? (
                <div className="p-6 rounded-lg bg-surface-darker/60 border border-dashed border-surface-border text-center space-y-3">
                  <Clock className="w-8 h-8 text-cyan-400 mx-auto opacity-70" />
                  <h4 className="text-sm font-bold text-white font-mono">No Operating Phases Defined</h4>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    This template was authored in legacy waypoint mode. Convert it to a time-phased operating profile to drive the real propulsion digital twin.
                  </p>
                  <button
                    onClick={handleInitializeDefaultPhases}
                    className="px-4 py-2 rounded bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono font-bold text-xs inline-flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" /> Initialize Standard 6-Phase Profile
                  </button>
                </div>
              ) : (
                <>
                  {/* Timeline Bar Track */}
                  <div className="p-4 rounded-lg bg-surface-darker/80 border border-surface-border space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-cyan-400" />
                        <h4 className="text-xs font-bold font-mono text-white uppercase tracking-wider">
                          Phase Operating Profile ({draftPlan.phases.length} Phases · {Math.round(totalPhaseDuration)}s Total)
                        </h4>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-slate-400">
                          Click any phase segment to inspect & edit operating conditions
                        </span>
                        <button
                          onClick={handleAddPhase}
                          className="px-2.5 py-1 rounded bg-surface-dark border border-surface-border hover:border-cyan-400 text-cyan-300 font-mono text-[10px] font-bold flex items-center gap-1 transition-all"
                        >
                          <Plus className="w-3 h-3" /> Add Phase
                        </button>
                      </div>
                    </div>

                    {/* Proportional Timeline Bar */}
                    <div className="relative pt-6 pb-2">
                      {/* Scheduled Fault Markers */}
                      {draftPlan.phase_events && draftPlan.phase_events.map((ev, evIdx) => {
                        let cumSec = 0;
                        for (const ph of draftPlan.phases || []) {
                          if (ph.name.toUpperCase() === ev.phase_name.toUpperCase()) {
                            cumSec += ev.elapsed_in_phase_sec;
                            break;
                          }
                          cumSec += ph.duration_sec;
                        }
                        const pct = totalPhaseDuration > 0 ? (cumSec / totalPhaseDuration) * 100 : 0;
                        return (
                          <div
                            key={evIdx}
                            className="absolute top-0 z-20 transform -translate-x-1/2 flex flex-col items-center group cursor-pointer"
                            style={{ left: `${Math.min(99, Math.max(1, pct))}%` }}
                          >
                            <span className="text-[9px] font-mono font-bold text-red-400 bg-red-950/90 border border-red-500/50 px-1.5 py-0.5 rounded shadow-md whitespace-nowrap mb-0.5 group-hover:scale-105 transition-transform flex items-center gap-1">
                              <Flame className="w-2.5 h-2.5 text-red-400" />
                              {ev.fault_mode?.replace(/_/g, ' ') || 'FAULT'}
                            </span>
                            <div className="w-2 h-2 rounded-full bg-red-500 ring-2 ring-red-400/50 animate-pulse" />
                            <div className="w-0.5 h-3 bg-red-500/50" />
                          </div>
                        );
                      })}

                      {/* Multi-Segment Horizontal Track */}
                      <div className="flex w-full h-20 rounded-lg overflow-hidden border border-surface-border bg-black/40 p-1 gap-1">
                        {draftPlan.phases.map((ph, idx) => {
                          const widthPct = totalPhaseDuration > 0 ? (ph.duration_sec / totalPhaseDuration) * 100 : 16.6;
                          const isSelected = selectedPhaseIdx === idx;
                          const style = getPhaseStyle(ph.name);
                          return (
                            <div
                              key={idx}
                              onClick={() => setSelectedPhaseIdx(idx)}
                              style={{ width: `${widthPct}%`, minWidth: '85px' }}
                              className={`h-full rounded cursor-pointer transition-all relative flex flex-col justify-between p-2 border ${
                                style.bg
                              } ${style.border} ${
                                isSelected
                                  ? 'ring-2 ring-cyan-400 shadow-lg shadow-cyan-500/25 z-10 brightness-110'
                                  : 'hover:brightness-105 opacity-90'
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <span className={`text-[10px] font-mono font-bold truncate ${style.text}`}>
                                  {idx + 1}. {ph.name}
                                </span>
                                <span className="text-[9px] font-mono text-slate-300 font-bold bg-black/40 px-1 rounded">
                                  {Math.round(ph.duration_sec)}s
                                </span>
                              </div>
                              <div className="space-y-0.5 text-[9px] font-mono text-slate-300">
                                <div className="flex justify-between text-slate-400">
                                  <span>THR:</span>
                                  <strong className="text-cyan-300">{ph.throttle_pct}%</strong>
                                </div>
                                <div className="flex justify-between text-slate-400">
                                  <span>ALT:</span>
                                  <strong className="text-white">
                                    {Math.round(ph.start_alt_ft / 1000)}k → {Math.round(ph.end_alt_ft / 1000)}k'
                                  </strong>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      <div className="flex justify-between text-[10px] font-mono text-slate-500 pt-1">
                        <span>T+ 00:00 (TAKEOFF)</span>
                        <span>T+ {Math.floor(totalPhaseDuration / 60).toString().padStart(2, '0')}:{Math.floor(totalPhaseDuration % 60).toString().padStart(2, '0')} (RECOVERY)</span>
                      </div>
                    </div>
                  </div>

                  {/* Click-a-Phase-to-Edit Inspector */}
                  {selectedPhase && (
                    <div className="p-4 rounded-lg bg-surface-darker/90 border border-cyan-500/30 space-y-4 shadow-lg shadow-cyan-950/20">
                      <div className="flex flex-wrap items-center justify-between border-b border-surface-border pb-2.5 gap-2">
                        <div className="flex items-center gap-2">
                          <Edit3 className="w-4 h-4 text-cyan-400" />
                          <h4 className="text-xs font-bold font-mono text-white uppercase">
                            Phase Inspector & Operating Conditions: Phase #{selectedPhaseIdx + 1} ({selectedPhase.name})
                          </h4>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              // Chain to next phase
                              if (selectedPhaseIdx < (draftPlan.phases?.length || 0) - 1) {
                                handleUpdatePhase(selectedPhaseIdx + 1, 'start_alt_ft', selectedPhase.end_alt_ft);
                              }
                            }}
                            className="px-2 py-1 rounded bg-surface-dark border border-surface-border text-slate-400 hover:text-white text-[10px] font-mono"
                            title="Set next phase's start altitude equal to this phase's end altitude"
                          >
                            Chain Next Alt
                          </button>
                          <button
                            type="button"
                            disabled={(draftPlan.phases?.length || 0) <= 1}
                            onClick={() => handleDeletePhase(selectedPhaseIdx)}
                            className="px-2 py-1 rounded bg-red-950/60 hover:bg-red-900 border border-red-800/60 text-red-300 text-[10px] font-mono flex items-center gap-1 disabled:opacity-40"
                          >
                            <Trash2 className="w-3 h-3" /> Remove Phase
                          </button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 font-mono">
                        <div>
                          <label className="text-[10px] text-slate-400 block mb-1">Phase Identifier</label>
                          <div className="flex gap-1">
                            <input
                              type="text"
                              value={selectedPhase.name}
                              onChange={(e) => handleUpdatePhase(selectedPhaseIdx, 'name', e.target.value.toUpperCase())}
                              className="w-full bg-surface-dark border border-surface-border rounded p-1.5 text-xs text-cyan-300 font-bold"
                            />
                            <select
                              value={STANDARD_PHASE_NAMES.includes(selectedPhase.name) ? selectedPhase.name : 'CUSTOM'}
                              onChange={(e) => {
                                if (e.target.value !== 'CUSTOM') {
                                  handleUpdatePhase(selectedPhaseIdx, 'name', e.target.value);
                                }
                              }}
                              className="bg-surface-dark border border-surface-border rounded px-1 text-[10px] text-slate-300 font-mono"
                              title="Preset phase names"
                            >
                              {STANDARD_PHASE_NAMES.map((name) => (
                                <option key={name} value={name}>{name}</option>
                              ))}
                              <option value="CUSTOM">OTHER</option>
                            </select>
                          </div>
                        </div>

                        <div>
                          <label className="text-[10px] text-slate-400 block mb-1">
                            Duration: {selectedPhase.duration_sec}s
                          </label>
                          <div className="flex items-center gap-1">
                            <input
                              type="number"
                              min="5"
                              max="3600"
                              value={selectedPhase.duration_sec}
                              onChange={(e) => handleUpdatePhase(selectedPhaseIdx, 'duration_sec', Number(e.target.value))}
                              className="w-full bg-surface-dark border border-surface-border rounded p-1.5 text-xs text-white"
                            />
                            <button
                              type="button"
                              onClick={() => handleUpdatePhase(selectedPhaseIdx, 'duration_sec', Math.max(5, selectedPhase.duration_sec - 15))}
                              className="px-1.5 py-1 bg-surface-dark border border-surface-border text-[10px] text-slate-400 hover:text-white rounded"
                            >
                              -15
                            </button>
                            <button
                              type="button"
                              onClick={() => handleUpdatePhase(selectedPhaseIdx, 'duration_sec', selectedPhase.duration_sec + 15)}
                              className="px-1.5 py-1 bg-surface-dark border border-surface-border text-[10px] text-slate-400 hover:text-white rounded"
                            >
                              +15
                            </button>
                          </div>
                        </div>

                        <div>
                          <label className="text-[10px] text-slate-400 block mb-1">Start Alt (ft MSL)</label>
                          <input
                            type="number"
                            step="100"
                            value={selectedPhase.start_alt_ft}
                            onChange={(e) => handleUpdatePhase(selectedPhaseIdx, 'start_alt_ft', Number(e.target.value))}
                            className="w-full bg-surface-dark border border-surface-border rounded p-1.5 text-xs text-white"
                          />
                        </div>

                        <div>
                          <label className="text-[10px] text-slate-400 block mb-1">End Alt (ft MSL)</label>
                          <input
                            type="number"
                            step="100"
                            value={selectedPhase.end_alt_ft}
                            onChange={(e) => handleUpdatePhase(selectedPhaseIdx, 'end_alt_ft', Number(e.target.value))}
                            className="w-full bg-surface-dark border border-surface-border rounded p-1.5 text-xs text-white"
                          />
                        </div>

                        <div>
                          <label className="text-[10px] text-slate-400 block mb-1">
                            Throttle Demand: <strong className="text-cyan-300">{selectedPhase.throttle_pct}%</strong>
                          </label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            step="1"
                            value={selectedPhase.throttle_pct}
                            onChange={(e) => handleUpdatePhase(selectedPhaseIdx, 'throttle_pct', Number(e.target.value))}
                            className="w-full accent-cyan-400 mt-1"
                          />
                        </div>

                        <div>
                          <label className="text-[10px] text-slate-400 block mb-1">
                            Ambient OAT: <strong className="text-amber-300">{selectedPhase.oat_c}°C</strong>
                          </label>
                          <input
                            type="range"
                            min="-30"
                            max="50"
                            step="1"
                            value={selectedPhase.oat_c}
                            onChange={(e) => handleUpdatePhase(selectedPhaseIdx, 'oat_c', Number(e.target.value))}
                            className="w-full accent-amber-400 mt-1"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Phase-Scheduled Fault Injections */}
                  <div className="p-4 rounded-lg bg-surface-darker/60 border border-surface-border space-y-3 font-mono">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ShieldAlert className="w-4 h-4 text-amber-400" />
                        <h4 className="text-xs font-bold text-white uppercase">
                          Phase-Scheduled Fault Timeline Events ({draftPlan.phase_events?.length || 0})
                        </h4>
                      </div>
                      <span className="text-[10px] text-slate-400">
                        Triggered at elapsed offset within named phase
                      </span>
                    </div>

                    {/* Events List */}
                    {draftPlan.phase_events && draftPlan.phase_events.length > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {draftPlan.phase_events.map((ev, idx) => (
                          <div
                            key={idx}
                            className="p-2.5 rounded bg-surface-dark border border-amber-500/30 text-xs flex items-center justify-between"
                          >
                            <div>
                              <span className="text-amber-400 font-bold">
                                {ev.phase_name} + {ev.elapsed_in_phase_sec}s:{' '}
                              </span>
                              <span className="text-white">{ev.fault_mode || ev.action}</span>
                              {ev.cylinder && <span className="text-slate-400"> (Cyl {ev.cylinder})</span>}
                              <div className="text-[10px] text-slate-400">
                                Severity: {Math.round((ev.severity ?? 0.8) * 100)}% | Ramp: {ev.ramp_sec}s
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleDeletePhaseScheduledEvent(idx)}
                              className="p-1 rounded text-slate-400 hover:text-red-400 transition-colors"
                              title="Delete scheduled event"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic">No phase-scheduled faults currently configured.</p>
                    )}

                    {/* Add Scheduled Fault Form */}
                    <div className="pt-2 border-t border-surface-border/60">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                        + Schedule Fault Inside Phase
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-7 gap-2 text-xs">
                        <div>
                          <label className="text-[9px] text-slate-400 block mb-0.5">Target Phase</label>
                          <select
                            value={newFaultPhase}
                            onChange={(e) => setNewFaultPhase(e.target.value)}
                            className="w-full bg-surface-dark border border-surface-border rounded p-1.5 text-white"
                          >
                            {(draftPlan.phases || []).map((p) => (
                              <option key={p.name} value={p.name}>
                                {p.name}
                              </option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="text-[9px] text-slate-400 block mb-0.5">Elapsed in Phase (s)</label>
                          <input
                            type="number"
                            min="0"
                            value={newFaultElapsed}
                            onChange={(e) => setNewFaultElapsed(Number(e.target.value))}
                            className="w-full bg-surface-dark border border-surface-border rounded p-1.5 text-white"
                          />
                        </div>

                        <div>
                          <label className="text-[9px] text-slate-400 block mb-0.5">Fault Mode</label>
                          <select
                            value={newFaultMode}
                            onChange={(e) => setNewFaultMode(e.target.value)}
                            className="w-full bg-surface-dark border border-surface-border rounded p-1.5 text-white"
                          >
                            <option value="COOLING_DEGRADATION">Cooling Degradation (Radiator)</option>
                            <option value="OIL_PRESSURE_LOSS">Oil Pressure Loss (Pump Valve)</option>
                            <option value="MISFIRE">Cylinder Misfire</option>
                            <option value="AIR_FILTER_BLOCKAGE">Air Filter Blockage</option>
                            <option value="BOOST_LEAK">Turbo Boost Leak</option>
                            <option value="WASTEGATE_STUCK_OPEN">Wastegate Stuck Open</option>
                          </select>
                        </div>

                        <div>
                          <label className="text-[9px] text-slate-400 block mb-0.5">Cylinder</label>
                          <select
                            value={newFaultCylinder}
                            disabled={newFaultMode !== 'MISFIRE' && newFaultMode !== 'INJECTOR_CLOGGED' && newFaultMode !== 'SPARK_PLUG_FOULING'}
                            onChange={(e) => setNewFaultCylinder(Number(e.target.value))}
                            className="w-full bg-surface-dark border border-surface-border rounded p-1.5 text-white disabled:opacity-30"
                          >
                            {[1, 2, 3, 4].map((c) => (
                              <option key={c} value={c}>Cylinder #{c}</option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="text-[9px] text-slate-400 block mb-0.5">Severity: {Math.round(newFaultSeverity * 100)}%</label>
                          <input
                            type="range"
                            min="0.2"
                            max="1.0"
                            step="0.05"
                            value={newFaultSeverity}
                            onChange={(e) => setNewFaultSeverity(Number(e.target.value))}
                            className="w-full accent-amber-500 mt-1"
                          />
                        </div>

                        <div>
                          <label className="text-[9px] text-slate-400 block mb-0.5">Ramp: {newFaultRamp}s</label>
                          <input
                            type="range"
                            min="5"
                            max="60"
                            step="5"
                            value={newFaultRamp}
                            onChange={(e) => setNewFaultRamp(Number(e.target.value))}
                            className="w-full accent-amber-500 mt-1"
                          />
                        </div>

                        <div className="flex items-end">
                          <button
                            type="button"
                            onClick={handleAddPhaseScheduledEvent}
                            className="w-full py-1.5 rounded bg-amber-600/80 hover:bg-amber-500 text-white font-bold text-xs transition-colors flex items-center justify-center gap-1"
                          >
                            <Plus className="w-3.5 h-3.5" /> Schedule
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ======================================================================= */}
          {/* FALLBACK: LEGACY WAYPOINTS TABLE (Dormant Route Mode)                   */}
          {/* ======================================================================= */}
          {plannerMode === 'WAYPOINTS' && (
            <div className="space-y-4">
              <div className="overflow-x-auto border border-surface-border rounded-lg">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-surface-dark border-b border-surface-border text-slate-400 uppercase text-[10px]">
                    <tr>
                      <th className="p-2.5">ID</th>
                      <th className="p-2.5">Name</th>
                      <th className="p-2.5">Latitude</th>
                      <th className="p-2.5">Longitude</th>
                      <th className="p-2.5">Alt MSL (m)</th>
                      <th className="p-2.5">KTAS</th>
                      <th className="p-2.5">Loiter Radius</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border bg-surface-darker/40">
                    {draftPlan.waypoints.map((wp) => (
                      <tr key={wp.id} className="hover:bg-cyan-500/5 transition-colors">
                        <td className="p-2.5 font-bold text-cyan-400">{wp.id}</td>
                        <td className="p-2.5 text-white">{wp.name}</td>
                        <td className="p-2.5 text-slate-300">{wp.lat.toFixed(4)}°</td>
                        <td className="p-2.5 text-slate-300">{wp.lon.toFixed(4)}°</td>
                        <td className="p-2.5 text-emerald-400 font-bold">{wp.alt_msl_m} m</td>
                        <td className="p-2.5 text-amber-400">{wp.airspeed_ktas} kt</td>
                        <td className="p-2.5 text-slate-400">
                          {wp.loiter_radius_m && wp.loiter_radius_m > 0 ? `${wp.loiter_radius_m} m` : 'None'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Live Mission Reliability & What-If Prescriptive Advisory */}
          <MissionReliabilityPanel
            engineId={draftPlan.engine_id}
            engineName={draftPlan.engine_id}
            serverUrl={serverUrl}
            isLiveMission={true}
            onApplyDerate={handleDerate}
          />

          {/* Action Footer */}
          <div className="pt-2 flex flex-wrap justify-end gap-3">
            <button
              onClick={handleLaunchPlan}
              className="px-5 py-2.5 rounded bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-mono font-black text-xs flex items-center gap-2 transition-all shadow-lg shadow-emerald-500/25 cursor-pointer"
            >
              <Play className="w-4 h-4 fill-current" />
              START MISSION (IN C2 CONSOLE)
            </button>
            <button
              onClick={handleLaunchAndOpenBlender}
              className="px-6 py-2.5 rounded bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-mono font-bold text-xs flex items-center gap-2 transition-all shadow-lg shadow-amber-500/25 cursor-pointer"
              title="Validate and start the mission, and automatically launch the Native Blender Flight Cockpit (launch_mission_flight_client.bat)"
            >
              <Play className="w-4 h-4 fill-current" />
              🚀 LAUNCH IN NATIVE BLENDER COCKPIT
            </button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SUB-TAB 2: LIVE COCKPIT & CANYON 3D                                       */}
      {/* ========================================================================= */}
      {activeTab === 'SIMULATION' && (
        <div className="space-y-3.5">
          {/* Unified Master C2 Mission Command Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 px-3.5 py-2 rounded-xl bg-surface-darker/95 border border-cyan-500/30 shadow-lg shadow-black/30">
            {/* Left: Mission Operational Telemetry */}
            <div className="flex flex-wrap items-center gap-2.5">
              <span
                className={`px-2.5 py-1 rounded-md text-xs font-mono font-extrabold uppercase tracking-wide flex items-center gap-1.5 shadow-sm ${
                  missionState?.status === 'RUNNING'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                    : missionState?.status === 'DERATED'
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                    : missionState?.status === 'PAUSED'
                    ? 'bg-slate-500/20 text-slate-300 border border-slate-500/40'
                    : 'bg-red-500/20 text-red-400 border border-red-500/40'
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${
                  missionState?.status === 'RUNNING' ? 'bg-emerald-400 animate-pulse' : missionState?.status === 'DERATED' ? 'bg-amber-400' : 'bg-slate-400'
                }`} />
                {missionState?.status || 'READY'}
              </span>

              <div className="px-2 py-0.5 rounded bg-surface-dark border border-surface-border text-xs font-mono flex items-center gap-1.5">
                <span className="text-slate-400 text-[10px]">PHASE:</span>
                <span className="text-amber-400 font-bold">{missionState?.phase || 'PREFLIGHT'}</span>
              </div>

              <div className="px-2 py-0.5 rounded bg-surface-dark border border-surface-border text-xs font-mono flex items-center gap-1.5">
                <span className="text-slate-400 text-[10px]">CLOCK:</span>
                <span className="text-cyan-400 font-bold">
                  T+ {Math.floor((missionState?.time_elapsed_sec || 0) / 60).toString().padStart(2, '0')}:
                  {Math.floor((missionState?.time_elapsed_sec || 0) % 60).toString().padStart(2, '0')}
                </span>
              </div>

              {missionState?.phase_duration_sec && missionState.phase_duration_sec > 0 ? (
                <div className="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-dark/60 border border-surface-border text-xs font-mono text-slate-300">
                  <span className="text-slate-400 text-[10px]">PROGRESS:</span>
                  <span className="text-slate-200 font-semibold">P{((missionState.current_phase_idx ?? 0) + 1)}/{definition?.phases?.length || 6}</span>
                  <span className="text-slate-500">({Math.floor(missionState.elapsed_in_phase_sec || 0)}s / {Math.floor(missionState.phase_duration_sec)}s)</span>
                </div>
              ) : null}

              {/* Time Compression Multiplier */}
              <div className="flex items-center gap-1 bg-surface-dark p-0.5 rounded-lg border border-surface-border">
                {[1, 2, 5, 10].map((scale) => (
                  <button
                    key={scale}
                    onClick={() => handleTimeScale(scale)}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition-colors ${
                      (missionState?.time_scale || 1) === scale
                        ? 'bg-cyan-500/25 text-cyan-300 border border-cyan-500/40 shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {scale}x
                  </button>
                ))}
              </div>
            </div>

            {/* Right: Operational Controls & High-Visibility Blender Launch */}
            <div className="flex flex-wrap items-center gap-2">
              {missionState?.status === 'RUNNING' || missionState?.status === 'DERATED' ? (
                <>
                  <button
                    onClick={pauseMission}
                    className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-mono text-xs font-bold flex items-center gap-1.5 shadow transition-all hover:scale-105 cursor-pointer"
                  >
                    <Pause className="w-3.5 h-3.5 fill-current" /> PAUSE
                  </button>
                  <button
                    onClick={handleRestartMission}
                    className="px-2.5 py-1.5 rounded-lg bg-surface-dark hover:bg-slate-700 text-slate-300 border border-surface-border font-mono text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                    title="Reset sortie to T+00:00"
                  >
                    <RotateCcw className="w-3.5 h-3.5" /> RESET
                  </button>
                </>
              ) : missionState?.status === 'PAUSED' ? (
                <>
                  <button
                    onClick={resumeMission}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-bold flex items-center gap-1.5 shadow transition-all hover:scale-105 cursor-pointer"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" /> RESUME
                  </button>
                  <button
                    onClick={handleRestartMission}
                    className="px-2.5 py-1.5 rounded-lg bg-surface-dark hover:bg-slate-700 text-slate-300 border border-surface-border font-mono text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                    title="Reset sortie to T+00:00"
                  >
                    <RotateCcw className="w-3.5 h-3.5" /> RESET
                  </button>
                </>
              ) : (
                <button
                  onClick={handleStartMission}
                  className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-mono text-xs font-black flex items-center gap-2 shadow-lg shadow-emerald-500/35 transition-all hover:scale-105 animate-pulse cursor-pointer border border-emerald-300"
                  title="Arm & start mission flight execution"
                >
                  <Play className="w-4 h-4 fill-current" />
                  <span>START MISSION</span>
                </button>
              )}

              {/* Operator actions: affect the live mission itself */}
              <div className="flex items-center gap-2 pl-2 ml-1 border-l border-surface-border">
                <button
                  onClick={() => handleDerate(0.85)}
                  className="px-2.5 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 font-mono text-xs font-bold flex items-center gap-1.5 transition-colors"
                  title="Prescriptive Derate: caps maximum throttle demand to 85% to preserve remaining useful life"
                >
                  <Sliders className="w-3.5 h-3.5" /> DERATE 85%
                </button>

                <button
                  onClick={handleAbort}
                  className="px-2.5 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/40 font-mono text-xs font-bold flex items-center gap-1.5 transition-colors"
                  title="Emergency Abort / Return to Base"
                >
                  <Square className="w-3.5 h-3.5 fill-current" /> ABORT RTB
                </button>
              </div>

              {/* View controls: change how you're WATCHING the mission, don't affect it */}
              <div className="flex items-center gap-2 pl-2 ml-1 border-l border-surface-border">
                <button
                  onClick={() => setIsCinemaMode(!isCinemaMode)}
                  className={`px-2.5 py-1.5 rounded-lg font-mono text-xs font-bold flex items-center gap-1.5 transition-colors ${
                    isCinemaMode
                      ? 'bg-cyan-500/25 text-cyan-300 border border-cyan-500/50 shadow-sm'
                      : 'bg-surface-dark hover:bg-slate-700 text-slate-300 border border-surface-border'
                  }`}
                  title={isCinemaMode ? 'Restore split layout' : 'Expand full-width cinema view'}
                >
                  {isCinemaMode ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                  {isCinemaMode ? 'SPLIT VIEW' : 'FULL WIDTH VIEW'}
                </button>
              </div>

              {/* Opens a separate desktop app window, outside the browser -- kept visually
                  distinct so it's never confused with a control over the web view above. */}
              <div className="flex items-center gap-2 pl-2 ml-1 border-l border-dashed border-amber-700/50">
                <span className="text-[9px] font-mono text-amber-500/70 uppercase tracking-wider hidden xl:inline">Opens Blender ↗</span>
                <button
                  onClick={() => launchNativeBlender('client')}
                  className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 hover:from-amber-400 hover:to-orange-500 text-slate-950 font-mono font-extrabold text-xs flex items-center gap-1.5 shadow-md shadow-amber-500/25 transition-all hover:scale-105 border border-amber-300/40 cursor-pointer"
                  title="Opens a separate Blender desktop window mirroring this same live mission at full render quality (EEVEE 120 FPS + real Copernicus DEM terrain). Not required to fly the mission -- the view on this page already shows the same data."
                >
                  <Monitor className="w-3.5 h-3.5" />
                  <span>OPEN IN BLENDER</span>
                  <span className="text-[9px] px-1 py-0.5 rounded bg-black/25 text-slate-950 font-bold">120 FPS</span>
                </button>

                <button
                  onClick={() => launchNativeBlender('canyon')}
                  className="px-2.5 py-1.5 rounded-lg bg-surface-dark hover:bg-slate-700 text-amber-300 border border-amber-500/30 font-mono text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                  title="Opens a separate, disconnected Blender demo flight (not tied to this mission's live state) -- for showing raw flight-physics fidelity on its own."
                >
                  <Zap className="w-3 h-3 fill-amber-400" />
                  <span>BLENDER DEMO (unlinked)</span>
                </button>
              </div>
            </div>
          </div>

          {/* Main Layout: 3D Flight Viewport + Telemetry Diagnostics */}
          <div className={isCinemaMode ? 'space-y-3' : 'grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-start'}>
            {/* Canyon 3D Simulation Frame */}
            <div
              className={`${
                isCinemaMode
                  ? 'w-full h-[500px] max-h-[52vh]'
                  : 'lg:col-span-7 xl:col-span-8 h-[640px]'
              } bg-[#030a12] border border-surface-border rounded-xl overflow-hidden flex flex-col relative shadow-xl`}
            >
              {/* This browser view IS the live mission (same data as the sidebar and, if
                  opened, the Blender window) -- said in plain language, not architecture jargon. */}
              <div className="absolute top-2.5 right-2.5 z-10 pointer-events-none px-2.5 py-1 rounded-md bg-slate-950/80 border border-slate-700/60 backdrop-blur-md flex items-center gap-2 text-[10px] font-mono text-slate-300 shadow">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                <span>LIVE — same mission as the panel on the right</span>
              </div>

              <iframe
                id="canyon-sim-iframe"
                src={`${serverUrl.replace(/\/$/, '')}/apps/canyon_flight/index.html?v=${canyonFlightCacheBust}`}
                className="w-full flex-1 border-0"
                title="Tactical Canyon Flight Simulation"
              />
            </div>

            {/* Propulsion, FlyHash, Reliability & Live Fault Injector */}
            <div
              className={
                isCinemaMode
                  ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3'
                  : 'lg:col-span-5 xl:col-span-4 h-[640px] overflow-y-auto space-y-2.5 pr-1'
              }
            >
              {/* Card 1: Flight Kinematics & Coordinates */}
              <div className="p-3 rounded-xl bg-surface-darker/90 border border-surface-border space-y-2 shadow-md">
                <div className="flex items-center justify-between pb-1 border-b border-surface-border/60">
                  <span className="text-[11px] font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Compass className="w-3.5 h-3.5 text-cyan-400" /> Flight Kinematics & Vitals
                  </span>
                  <span className="text-[10px] font-mono text-cyan-400/80 font-semibold">
                    Ladakh Sector (34.5°N)
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2 rounded-lg bg-surface-dark border border-surface-border/80">
                    <span className="text-[10px] text-slate-400 block font-semibold">ALTITUDE MSL / AGL</span>
                    <div className="text-sm font-bold text-cyan-400 mt-0.5">
                      {Math.round(missionState?.pos_z_m || 0)} m
                      <span className="text-xs text-slate-400 font-normal ml-1">/ {Math.round(missionState?.agl_m || 0)} m AGL</span>
                    </div>
                  </div>

                  <div className="p-2 rounded-lg bg-surface-dark border border-surface-border/80">
                    <span className="text-[10px] text-slate-400 block font-semibold">AIRSPEED TAS / IAS</span>
                    <div className="text-sm font-bold text-white mt-0.5">
                      {Math.round(missionState?.true_airspeed_ktas || 0)} kt
                      <span className="text-xs text-slate-400 font-normal ml-1">/ {Math.round(missionState?.indicated_airspeed_kias || 0)} kt</span>
                    </div>
                  </div>

                  <div className="p-2 rounded-lg bg-surface-dark border border-surface-border/80">
                    <span className="text-[10px] text-slate-400 block font-semibold">HDG / PITCH / BANK</span>
                    <div className="text-xs font-bold text-slate-200 mt-1">
                      {(missionState?.heading_deg || 0).toFixed(0)}° / {(missionState?.pitch_deg || 0).toFixed(1)}° / {(missionState?.roll_bank_deg || 0).toFixed(1)}°
                    </div>
                  </div>

                  <div className="p-2 rounded-lg bg-surface-dark border border-surface-border/80">
                    <span className="text-[10px] text-slate-400 block font-semibold">COMMANDED THROTTLE</span>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-sm font-bold text-amber-400">
                        {(missionState?.commanded_throttle_pct || 0).toFixed(1)}%
                      </span>
                      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700/60">
                        <div
                          className="h-full bg-gradient-to-r from-cyan-400 to-amber-400 rounded-full"
                          style={{ width: `${Math.min(100, Math.max(0, missionState?.commanded_throttle_pct || 0))}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Real-Time Engine Core Vitals (Immediately reflects injected faults) */}
                  <div className="col-span-2 grid grid-cols-3 gap-1.5 pt-1 border-t border-surface-border/60">
                    <div className="p-1.5 rounded bg-surface-dark border border-surface-border text-center">
                      <span className="text-[9px] text-slate-400 block font-semibold">RPM</span>
                      <span className="text-xs font-bold text-cyan-300">{Math.round(missionState?.rpm || 0)}</span>
                    </div>
                    <div className={`p-1.5 rounded border text-center transition-colors ${
                      (missionState?.max_cht_c || 82) > 130
                        ? 'bg-red-950/70 border-red-500 text-red-300 animate-pulse font-extrabold'
                        : 'bg-surface-dark border-surface-border text-slate-200'
                    }`}>
                      <span className="text-[9px] text-slate-400 block font-semibold">CHT MAX</span>
                      <span className="text-xs font-bold">{(missionState?.max_cht_c || 82).toFixed(1)}°C</span>
                    </div>
                    <div className={`p-1.5 rounded border text-center transition-colors ${
                      (missionState?.oil_press_bar || 4.5) < 2.0
                        ? 'bg-red-950/70 border-red-500 text-red-300 animate-pulse font-extrabold'
                        : 'bg-surface-dark border-surface-border text-slate-200'
                    }`}>
                      <span className="text-[9px] text-slate-400 block font-semibold">OIL PRESS</span>
                      <span className="text-xs font-bold">{(missionState?.oil_press_bar || 4.5).toFixed(2)} bar</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Card 2: Remaining Useful Life -- the one number an operator actually acts
                  on: how many more flight hours until the weakest part needs attention. */}
              {missionState?.rul_hours != null && (() => {
                const rulHours = missionState.rul_hours as number;
                const urgent = rulHours < 5;
                const caution = !urgent && rulHours < 50;
                return (
                  <div className="p-3 rounded-xl bg-surface-darker/90 border border-surface-border space-y-2 shadow-md">
                    <div className="flex items-center justify-between pb-1 border-b border-surface-border/60">
                      <span className="text-[11px] font-mono font-bold text-slate-300 uppercase tracking-wider">
                        Remaining Useful Life
                      </span>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-extrabold ${
                        urgent
                          ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                          : caution
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                          : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                      }`}>
                        {urgent ? 'SCHEDULE MAINTENANCE' : caution ? 'MONITOR' : 'HEALTHY'}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-500 leading-snug -mt-1">
                      Estimated flight hours before {missionState.limiting_component !== 'nominal' ? missionState.limiting_component.replace(/_/g, ' ') : 'the weakest part'} needs maintenance, at the current operating condition.
                    </p>
                    <div className="flex items-baseline gap-1.5">
                      <span className={`text-2xl font-mono font-bold ${urgent ? 'text-red-400' : caution ? 'text-amber-400' : 'text-emerald-400'}`}>
                        {rulHours < 1000 ? rulHours.toFixed(1) : Math.round(rulHours).toLocaleString()}
                      </span>
                      <span className="text-xs text-slate-400">flight hours remaining</span>
                    </div>
                  </div>
                );
              })()}

              {/* Card 3: FlyHash Locality-Sensitive Novelty */}
              <div className="p-3 rounded-xl bg-surface-darker/90 border border-surface-border space-y-2 shadow-md">
                <div className="flex items-center justify-between pb-1 border-b border-surface-border/60">
                  <span className="text-[11px] font-mono font-bold text-slate-300 uppercase tracking-wider">
                    Unusual Behavior Detector
                  </span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded font-extrabold ${
                      (missionState?.flyhash_novelty_score || 0) >= 0.6
                        ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                    }`}
                  >
                    {(missionState?.flyhash_novelty_score || 0) >= 0.6 ? 'SOMETHING UNUSUAL' : 'LOOKS NORMAL'}
                  </span>
                </div>
                <p className="text-[10px] text-slate-500 leading-snug -mt-1">
                  Flags telemetry patterns that don't resemble anything seen before, even if no specific fault has been diagnosed yet.
                </p>

                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-slate-400">How unusual (0 = normal):</span>
                    <span className="text-white font-bold font-mono">
                      {(missionState?.flyhash_novelty_score || 0).toFixed(4)}
                    </span>
                  </div>
                  <div className="w-full bg-surface-dark h-2 rounded-full overflow-hidden relative border border-surface-border">
                    <div
                      className={`h-full transition-all duration-300 rounded-full ${
                        (missionState?.flyhash_novelty_score || 0) >= 0.6 ? 'bg-red-500' : 'bg-cyan-400'
                      }`}
                      style={{ width: `${Math.min(100, (missionState?.flyhash_novelty_score || 0) * 100)}%` }}
                    />
                    <div className="absolute top-0 bottom-0 left-[60%] w-0.5 bg-amber-400" title="Anomaly Threshold: 0.60" />
                  </div>
                  <div className="flex justify-between text-[9px] font-mono text-slate-500">
                    <span>0.0 Baseline</span>
                    <span className="text-amber-400/80">Threshold 0.60</span>
                    <span>1.0 Critical</span>
                  </div>
                </div>
              </div>

              {/* Card 4: Live Fault Injector & Stress Testing */}
              <div className="p-3 rounded-xl bg-surface-darker/95 border border-red-500/40 space-y-2.5 shadow-md">
                <div className="flex items-center justify-between pb-1 border-b border-surface-border/60">
                  <span className="text-[11px] font-mono font-bold text-red-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Flame className="w-3.5 h-3.5 text-red-500 animate-pulse" /> Inject Live Fault
                  </span>
                  <button
                    onClick={clearFaults}
                    className="text-[10px] font-mono text-slate-300 hover:text-white flex items-center gap-1 transition-colors px-2 py-0.5 rounded bg-surface-dark hover:bg-slate-700 border border-surface-border cursor-pointer"
                    title="Clear all active faults and restore nominal engine operation"
                  >
                    <RotateCcw className="w-3 h-3" /> Clear Faults
                  </button>
                </div>

                {/* Active Injected Fault Alert Pill */}
                {missionState?.active_faults && missionState.active_faults.length > 0 ? (
                  <div className="p-2 rounded-lg bg-red-950/80 border border-red-500 text-red-200 text-xs font-mono flex items-center justify-between shadow-lg shadow-red-500/20 animate-pulse">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-red-400 animate-ping" />
                      <span className="font-bold uppercase tracking-wider">
                        {missionState.active_faults[0].mode || 'ACTIVE FAULT'}
                      </span>
                      <span className="text-[10px] text-red-300">
                        ({Math.round((missionState.active_faults[0].severity || 0.85) * 100)}%)
                      </span>
                    </div>
                    <button
                      onClick={clearFaults}
                      className="px-2 py-0.5 rounded bg-red-600 hover:bg-red-500 text-white text-[10px] font-black uppercase transition-colors shadow cursor-pointer"
                    >
                      RESET
                    </button>
                  </div>
                ) : (
                  <div className="px-2 py-1 rounded bg-surface-dark/80 border border-surface-border text-[10px] font-mono text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    <span>ENGINE NOMINAL — Ready for live fault injection</span>
                  </div>
                )}

                {/* 1-Click Quick Demo Trigger Buttons */}
                <div className="space-y-1">
                  <span className="text-[9px] font-mono font-bold text-slate-400 uppercase tracking-wider block">
                    Quick Scenario Presets (1-Click Demo)
                  </span>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button
                      onClick={() => { setLiveFaultMode('COOLING_DEGRADATION'); void injectLiveFault('COOLING_DEGRADATION', undefined, 0.85, 10.0); }}
                      className="px-2 py-1.5 rounded-lg bg-red-950/50 hover:bg-red-900/80 border border-red-700/60 text-red-300 text-[10px] font-mono font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-sm"
                      title="Inject Coolant Leak: CHT rises rapidly towards 180°C"
                    >
                      <Flame className="w-3 h-3 text-red-400 shrink-0" />
                      <span className="truncate">🔥 Coolant Leak</span>
                    </button>
                    <button
                      onClick={() => { setLiveFaultMode('OIL_PRESSURE_LOSS'); void injectLiveFault('OIL_PRESSURE_LOSS', undefined, 0.90, 10.0); }}
                      className="px-2 py-1.5 rounded-lg bg-amber-950/50 hover:bg-amber-900/80 border border-amber-700/60 text-amber-300 text-[10px] font-mono font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-sm"
                      title="Inject Oil Pump Relief Valve Fault: Oil pressure drops to 1.2 bar"
                    >
                      <Sliders className="w-3 h-3 text-amber-400 shrink-0" />
                      <span className="truncate">⚠️ Oil Press Drop</span>
                    </button>
                    <button
                      onClick={() => { setLiveFaultMode('MISFIRE'); void injectLiveFault('MISFIRE', 1, 0.90, 10.0); }}
                      className="px-2 py-1.5 rounded-lg bg-orange-950/50 hover:bg-orange-900/80 border border-orange-700/60 text-orange-300 text-[10px] font-mono font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-sm"
                      title="Inject Cylinder 1 Misfire: RPM fluctuation and individual cylinder variance"
                    >
                      <Zap className="w-3 h-3 text-orange-400 shrink-0" />
                      <span className="truncate">⚡ Cyl 1 Misfire</span>
                    </button>
                    <button
                      onClick={() => { setLiveFaultMode('AIR_FILTER_BLOCKAGE'); void injectLiveFault('AIR_FILTER_BLOCKAGE', undefined, 0.85, 10.0); }}
                      className="px-2 py-1.5 rounded-lg bg-rose-950/50 hover:bg-rose-900/80 border border-rose-700/60 text-rose-300 text-[10px] font-mono font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-sm"
                      title="Inject Air Filter Choke: MAP drops and engine derates"
                    >
                      <ShieldAlert className="w-3 h-3 text-rose-400 shrink-0" />
                      <span className="truncate">🌪️ Air Choke</span>
                    </button>
                  </div>
                </div>

                {/* Custom Fault Configuration */}
                <div className="space-y-2 text-xs font-mono pt-1 border-t border-surface-border/60">
                  <select
                    value={liveFaultMode}
                    onChange={(e) => setLiveFaultMode(e.target.value)}
                    className="w-full bg-surface-dark border border-surface-border rounded-lg p-2 text-xs font-mono text-white focus:outline-none focus:border-red-400"
                  >
                    <option value="COOLING_DEGRADATION">Cooling Degradation (Radiator / CHT Rise)</option>
                    <option value="OIL_PRESSURE_LOSS">Oil Pressure Loss (Pump Relief Valve Stuck)</option>
                    <option value="MISFIRE">Cylinder Misfire (Per-Cylinder Spark/Fuel Loss)</option>
                    <option value="AIR_FILTER_BLOCKAGE">Air Filter Blockage (Induction Choke)</option>
                    <option value="BOOST_LEAK">Turbo Boost Leak / Intercooler</option>
                    <option value="WASTEGATE_STUCK_OPEN">Turbo Wastegate Stuck Open</option>
                    <option value="SENSOR_BIAS_DRIFT">Sensor Bias Drift</option>
                    <option value="SENSOR_STUCK">Sensor Frozen / Stuck</option>
                  </select>

                  {(liveFaultMode === 'MISFIRE' || liveFaultMode === 'INJECTOR_CLOGGED' || liveFaultMode === 'SPARK_PLUG_FOULING') && (
                    <div className="flex items-center justify-between p-1.5 rounded bg-surface-dark border border-surface-border text-xs">
                      <span className="text-slate-400 text-[10px]">TARGET CYLINDER:</span>
                      <select
                        value={liveFaultCylinder}
                        onChange={(e) => setLiveFaultCylinder(Number(e.target.value))}
                        className="bg-slate-900 border border-surface-border rounded px-2 py-0.5 text-xs text-white"
                      >
                        {[1, 2, 3, 4].map((cyl) => (
                          <option key={cyl} value={cyl}>
                            Cylinder #{cyl}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 rounded bg-surface-dark border border-surface-border">
                      <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                        <span>Severity:</span>
                        <span className="text-white font-bold">{Math.round(liveFaultSeverity * 100)}%</span>
                      </div>
                      <input
                        type="range"
                        min="0.2"
                        max="1.0"
                        step="0.05"
                        value={liveFaultSeverity}
                        onChange={(e) => setLiveFaultSeverity(Number(e.target.value))}
                        className="w-full accent-red-500 cursor-pointer"
                      />
                    </div>
                    <div className="p-2 rounded bg-surface-dark border border-surface-border">
                      <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                        <span>Ramp:</span>
                        <span className="text-white font-bold">{liveFaultRamp}s</span>
                      </div>
                      <input
                        type="range"
                        min="5"
                        max="60"
                        step="5"
                        value={liveFaultRamp}
                        onChange={(e) => setLiveFaultRamp(Number(e.target.value))}
                        className="w-full accent-red-500 cursor-pointer"
                      />
                    </div>
                  </div>

                  <button
                    onClick={handleInjectFaultLive}
                    disabled={isInjectingLive}
                    className="w-full py-2 rounded-lg bg-gradient-to-r from-red-600 to-rose-700 hover:from-red-500 hover:to-rose-600 text-white font-mono text-xs font-bold transition-all shadow-md shadow-red-500/20 active:scale-[0.99] flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <Flame className="w-3.5 h-3.5" />
                    {isInjectingLive ? 'INJECTING FAULT...' : 'TRIGGER LIVE PROPULSION FAULT'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SUB-TAB 3: SORTIE DEBRIEF & REPLAY LINK                                   */}
      {/* ========================================================================= */}
      {activeTab === 'DEBRIEF' && (
        <div className="space-y-4">
          <div className="p-4 rounded-lg bg-surface-darker/60 border border-surface-border flex flex-wrap items-center justify-between gap-4">
            <div>
              <span className="text-[10px] font-mono font-bold text-emerald-400 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 uppercase">
                Sortie Recorded & Persisted
              </span>
              <h3 className="text-base font-bold font-mono text-white mt-1">
                {definition?.name || 'Tactical Sortie Simulation'}
              </h3>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Mission ID: <strong className="text-cyan-400">{missionState?.mission_id}</strong> | Status:{' '}
                <strong className="text-white">{missionState?.status}</strong> | Duration:{' '}
                {Math.round(missionState?.time_elapsed_sec || 0)} seconds
              </p>
            </div>

            {onNavigate && (
              <button
                onClick={() => onNavigate('MISSION_REPLAY')}
                className="px-5 py-2.5 rounded bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono font-bold text-xs flex items-center gap-2 transition-all shadow-md shadow-cyan-500/20"
              >
                <FastForward className="w-4 h-4 fill-current" />
                OPEN IN HISTORICAL REPLAY SCRUBBER
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="p-3 rounded-lg bg-surface-darker/60 border border-surface-border font-mono">
              <span className="text-[10px] text-slate-400 block">FINAL PROPULSION RPM</span>
              <span className="text-base font-bold text-cyan-400">{Math.round(missionState?.rpm || 0)}</span>
            </div>
            <div className="p-3 rounded-lg bg-surface-darker/60 border border-surface-border font-mono">
              <span className="text-[10px] text-slate-400 block">PEAK CHT THERMAL</span>
              <span className="text-base font-bold text-amber-400">
                {(missionState?.max_cht_c || 0).toFixed(1)} °C
              </span>
            </div>
            <div className="p-3 rounded-lg bg-surface-darker/60 border border-surface-border font-mono">
              <span className="text-[10px] text-slate-400 block">FLYHASH PEAK NOVELTY</span>
              <span className="text-base font-bold text-red-400">
                {(missionState?.flyhash_novelty_score || 0).toFixed(4)}
              </span>
            </div>
            <div className="p-3 rounded-lg bg-surface-darker/60 border border-surface-border font-mono">
              <span className="text-[10px] text-slate-400 block">RELIABILITY INDEX</span>
              <span className="text-base font-bold text-emerald-400">
                {Math.round((missionState?.mission_reliability || 1.0) * 100)}%
              </span>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-surface-darker/60 border border-surface-border space-y-3 font-mono text-xs">
            <h4 className="text-xs font-bold text-slate-300 uppercase">Generated Output Artifacts</h4>
            <div className="space-y-1.5 text-slate-400">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>
                  Telemetry CSV:{' '}
                  <code className="text-cyan-300">
                    report_dump/{missionState?.mission_id}/readings/telemetry_log.csv
                  </code>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>
                  Mission Manifest:{' '}
                  <code className="text-cyan-300">report_dump/{missionState?.mission_id}/mission.json</code>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>
                  Sortie Debrief Report:{' '}
                  <code className="text-cyan-300">report_dump/{missionState?.mission_id}/debrief.md</code>
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
