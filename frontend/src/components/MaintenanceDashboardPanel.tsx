import React, { useState, useEffect } from 'react';
import {
  ClipboardList,
  Shield,
  ShieldCheck,
  UserCheck,
  RefreshCw,
  FileCheck,
  ChevronRight,
  Download,
  FileText,
  Cpu,
  Sparkles,
} from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';
import { AerospaceMarkdown } from './AerospaceMarkdown';

interface MaintenanceDashboardPanelProps {
  state: UnifiedTelemetryState;
  serverUrl: string;
}

interface WorkOrder {
  action_id: string;
  sortie_id: string;
  subsystem_id: string;
  ata_chapter: string;
  description: string;
  status: 'OPEN' | 'SIGNED_OFF';
  rul_p10_hours?: number | null;
  rul_p50_hours?: number | null;
  limiting_component?: string | null;
  signoff_epoch?: number | null;
  signoff_inspector?: string | null;
}

interface BayesianHypothesis {
  mode_id: string;
  location?: string | null;
  probability: number;
  ambiguity_group: string;
  supporting_evidence: string[];
  counter_evidence: string[];
}

interface DualPathRulData {
  component: string;
  location: string;
  physics_rul_hours: number;
  data_rul_hours: number;
  blended_rul_hours: number;
  conformal_lower_bound: number;
  conformal_upper_bound: number;
  nominal_coverage: number;
  disagreement_alarm: boolean;
  limiting_failure_mode: string;
}

const fmt = (v?: number | null, d = 1) => (v !== undefined && v !== null && Number.isFinite(v) ? v.toFixed(d) : '--');

const COMPONENT_LABELS: Record<string, { name: string; ata: string; tboHours: number }> = {
  Cylinder_Head_Assembly: { name: 'Cylinder Head Assembly', ata: 'ATA-72 Engine', tboHours: 2000 },
  Lubrication_Oil_Circuit: { name: 'Lubrication Oil Circuit', ata: 'ATA-79 Lubrication', tboHours: 1200 },
  Reduction_Gearbox: { name: 'Reduction Gearbox', ata: 'ATA-72 Mechanical', tboHours: 1000 },
  Alternator_Bus: { name: 'Alternator Bus / Power', ata: 'ATA-24 Electrical', tboHours: 1500 },
  Fuel_Injection_Rail: { name: 'Fuel Injection Rail', ata: 'ATA-73 Engine Fuel', tboHours: 1000 },
  Ignition_Harness: { name: 'Ignition Harness & Plugs', ata: 'ATA-74 Ignition', tboHours: 800 },
};

export const MaintenanceDashboardPanel: React.FC<MaintenanceDashboardPanelProps> = ({ state, serverUrl }) => {
  const a = state.analytics;
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [isLoadingOrders, setIsLoadingOrders] = useState(false);
  const [signoffInspector, setSignoffInspector] = useState('DRDO-TECH-01');
  const [signingOffId, setSigningOffId] = useState<string | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // WP-08: Bayesian & Dual-Path RUL state
  const [bayesianHypotheses, setBayesianHypotheses] = useState<BayesianHypothesis[]>([]);
  const [dualPathRul, setDualPathRul] = useState<DualPathRulData | null>(null);

  // WP-10: Debrief state
  const [debriefMarkdown, setDebriefMarkdown] = useState<string | null>(null);
  const [isGeneratingDebrief, setIsGeneratingDebrief] = useState(false);
  const [debriefStatus, setDebriefStatus] = useState<string | null>(null);

  // Fetch Work Orders from backend
  const fetchWorkOrders = async () => {
    try {
      setIsLoadingOrders(true);
      const res = await fetch(`${serverUrl}/api/cbm/maintenance`);
      if (res.ok) {
        const data = await res.json();
        setWorkOrders(data.work_orders || []);
      }
    } catch (e) {
      console.error('Failed to fetch maintenance orders', e);
    } finally {
      setIsLoadingOrders(false);
    }
  };

  // Fetch Bayesian Diagnostics & Dual-Path RUL (WP-08)
  const fetchDiagnosticsAndRul = async () => {
    try {
      const [bayesRes, rulRes] = await Promise.all([
        fetch(`${serverUrl}/api/diagnostics/bayesian`),
        fetch(`${serverUrl}/api/prognostics/dual-path-rul`),
      ]);
      if (bayesRes.ok) {
        const bayesData = await bayesRes.json();
        setBayesianHypotheses(bayesData.hypotheses || []);
      }
      if (rulRes.ok) {
        const rulData = await rulRes.json();
        setDualPathRul(rulData);
      }
    } catch (e) {
      console.warn('Failed to fetch Bayesian/RUL metrics', e);
    }
  };

  useEffect(() => {
    fetchWorkOrders();
    fetchDiagnosticsAndRul();
    const interval = setInterval(() => {
      fetchWorkOrders();
      fetchDiagnosticsAndRul();
    }, 6000);
    return () => clearInterval(interval);
  }, [serverUrl]);

  // Sign off an action
  const handleSignOff = async (actionId: string) => {
    try {
      setSigningOffId(actionId);
      setFeedbackMsg(null);
      const res = await fetch(`${serverUrl}/api/cbm/maintenance/${encodeURIComponent(actionId)}/signoff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ inspector: signoffInspector.trim() || 'DRDO-TECH-01' }),
      });
      if (res.ok) {
        setFeedbackMsg({ text: `Work order ${actionId} successfully signed off and closed.`, type: 'success' });
        await fetchWorkOrders();
      } else {
        const err = await res.json();
        setFeedbackMsg({ text: `Sign-off failed: ${err.detail || 'Unknown error'}`, type: 'error' });
      }
    } catch (e: any) {
      setFeedbackMsg({ text: `Sign-off error: ${e.message}`, type: 'error' });
    } finally {
      setSigningOffId(null);
    }
  };

  // Generate Debrief Report (WP-10)
  const handleGenerateDebrief = async () => {
    try {
      setIsGeneratingDebrief(true);
      setDebriefStatus('Synthesizing sortie debrief from telemetry and anomaly graph…');
      const res = await fetch(`${serverUrl}/api/debrief/generate`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setDebriefMarkdown(data.markdown || '# Mission Debrief\n\nNo records generated.');
        setDebriefStatus(`Debrief generated successfully for Sortie ${data.sortie_id}`);
      } else {
        setDebriefStatus(`Generation failed with code ${res.status}`);
      }
    } catch (e: any) {
      setDebriefStatus(`Generation error: ${e.message}`);
    } finally {
      setIsGeneratingDebrief(false);
    }
  };

  const handleFetchLatestDebrief = async () => {
    try {
      setIsGeneratingDebrief(true);
      const res = await fetch(`${serverUrl}/api/debrief/latest`);
      if (res.ok) {
        const data = await res.json();
        setDebriefMarkdown(data.markdown);
        setDebriefStatus(`Loaded report: ${data.filename}`);
      } else {
        setDebriefStatus('No previous debrief report found on server.');
      }
    } catch (e: any) {
      setDebriefStatus(`Load error: ${e.message}`);
    } finally {
      setIsGeneratingDebrief(false);
    }
  };

  const handleDownloadDebrief = () => {
    if (!debriefMarkdown) return;
    const blob = new Blob([debriefMarkdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ANUMAAN_SORTIE_DEBRIEF_${state.sortie_id || Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Sensor channels list for sanity matrix
  const sensorChannels = [
    { key: 'CHT_1', label: 'CHT Cyl 1', val: `${fmt(state.telemetry.CHT_1)} °C` },
    { key: 'CHT_2', label: 'CHT Cyl 2', val: `${fmt(state.telemetry.CHT_2)} °C` },
    { key: 'CHT_3', label: 'CHT Cyl 3', val: `${fmt(state.telemetry.CHT_3)} °C` },
    { key: 'CHT_4', label: 'CHT Cyl 4', val: `${fmt(state.telemetry.CHT_4)} °C` },
    { key: 'EGT_1', label: 'EGT Cyl 1', val: `${fmt(state.telemetry.EGT_1)} °C` },
    { key: 'EGT_2', label: 'EGT Cyl 2', val: `${fmt(state.telemetry.EGT_2)} °C` },
    { key: 'EGT_3', label: 'EGT Cyl 3', val: `${fmt(state.telemetry.EGT_3)} °C` },
    { key: 'EGT_4', label: 'EGT Cyl 4', val: `${fmt(state.telemetry.EGT_4)} °C` },
    { key: 'OIL_PRESS', label: 'Oil Pressure', val: `${fmt(state.telemetry.OIL_PRESS, 2)} bar` },
    { key: 'OIL_TEMP', label: 'Oil Temp', val: `${fmt(state.telemetry.OIL_TEMP)} °C` },
    { key: 'FUEL_FLOW', label: 'Fuel Flow', val: `${fmt(state.telemetry.FUEL_FLOW, 1)} L/h` },
    { key: 'MAP_INHG', label: 'Manifold Pressure', val: `${fmt(state.telemetry.MAP_INHG ?? state.telemetry.MAP, 1)} inHg` },
    { key: 'VIB_GEARBOX_RMS', label: 'Gearbox Vib', val: `${fmt(state.telemetry.VIB_GEARBOX_RMS, 2)} mm/s` },
    { key: 'BUS_VOLTAGE', label: 'DC Bus', val: `${fmt(state.telemetry.BUS_VOLTAGE, 1)} V` },
  ];

  const sanity = a.sensor_sanity;

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="surface-panel p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 border-l-4 border-l-emerald-500">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              VIS-04 / CBM-01 / WP-08 / WP-10
            </span>
            <h2 className="text-sm font-semibold text-white tracking-wide">
              Ground Crew Maintenance &amp; Condition-Based Monitoring (CBM)
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Authoritative Bayesian diagnosis, conformal dual-path RUL, digital sign-offs, and automated sortie debrief generation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              fetchWorkOrders();
              fetchDiagnosticsAndRul();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-surface-card border border-surface-border text-xs font-medium text-slate-300 hover:text-white transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingOrders ? 'animate-spin' : ''}`} />
            <span>Refresh Diagnostics</span>
          </button>
        </div>
      </div>

      {feedbackMsg && (
        <div
          className={`p-3 rounded text-xs border ${
            feedbackMsg.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-critical-dim border-critical-muted text-critical'
          }`}
        >
          {feedbackMsg.text}
        </div>
      )}

      {/* WP-08: Bayesian Failure Mode Hypotheses & Dual-Path Prognostics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Bayesian Diagnostic Distribution */}
        <div className="surface-panel p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-surface-border pb-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                Exact Bayesian Belief Network P(Fault | Evidence)
              </h3>
            </div>
            <span className="text-[10px] font-mono text-cyan-400">B5.3 FMECA NET</span>
          </div>

          <p className="text-xs text-slate-400">
            Log-odds Bayesian posterior distribution updated dynamically from sensor residual evidence signatures.
          </p>

          <div className="space-y-2">
            {bayesianHypotheses.length === 0 ? (
              <div className="text-xs text-slate-500 italic p-3 bg-white/[0.02] rounded border border-surface-border/50">
                Awaiting detector residual evidence vectors...
              </div>
            ) : (
              bayesianHypotheses.map((h, idx) => (
                <div key={idx} className="bg-surface-card p-2.5 rounded border border-surface-border space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-slate-200">{h.mode_id}</span>
                    <span className="font-mono text-xs font-bold text-cyan-300">
                      {(h.probability * 100).toFixed(1)}%
                    </span>
                  </div>
                  {/* Probability Bar */}
                  <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 rounded-full"
                      style={{ width: `${Math.min(100, h.probability * 100)}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                    <span>
                      Ambiguity Group: <span className="text-slate-400 font-mono">{h.ambiguity_group}</span>
                    </span>
                    <span className="truncate max-w-[180px]">
                      {h.supporting_evidence.length > 0 ? h.supporting_evidence.join(', ') : 'Prior belief'}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Dual-Path RUL with Conformal Bounds */}
        <div className="surface-panel p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-surface-border pb-2">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                Dual-Path Prognostic RUL (Physics vs Data-Driven)
              </h3>
            </div>
            <span className="text-[10px] font-mono text-emerald-400">B6.1 CONFORMAL</span>
          </div>

          <p className="text-xs text-slate-400">
            Conformal prediction bounds combining Arrhenius/Paris law degradation physics with autoencoder residual drift models.
          </p>

          {dualPathRul && (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="bg-surface-card p-2.5 rounded border border-surface-border">
                  <span className="text-[10px] text-slate-500 block">PHYSICS RUL</span>
                  <span className="text-base font-bold font-mono text-slate-200 mt-1 block">
                    {dualPathRul.physics_rul_hours}h
                  </span>
                  <span className="text-[9px] text-slate-500">Damage integral</span>
                </div>

                <div className="bg-surface-card p-2.5 rounded border border-surface-border">
                  <span className="text-[10px] text-slate-500 block">DATA ML RUL</span>
                  <span className="text-base font-bold font-mono text-slate-200 mt-1 block">
                    {dualPathRul.data_rul_hours}h
                  </span>
                  <span className="text-[9px] text-slate-500">Drift trajectory</span>
                </div>

                <div className="bg-surface-card p-2.5 rounded border border-emerald-500/30 bg-emerald-500/5">
                  <span className="text-[10px] text-emerald-400 block font-semibold">BLENDED RUL</span>
                  <span className="text-base font-bold font-mono text-emerald-300 mt-1 block">
                    {dualPathRul.blended_rul_hours}h
                  </span>
                  <span className="text-[9px] text-emerald-400">Median synthesis</span>
                </div>
              </div>

              <div className="bg-surface-card p-3 rounded border border-surface-border space-y-1.5 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Conformal 90% Confidence Interval:</span>
                  <span className="font-mono font-bold text-cyan-300">
                    [{dualPathRul.conformal_lower_bound}h – {dualPathRul.conformal_upper_bound}h]
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Limiting Failure Mechanism:</span>
                  <span className="font-mono text-slate-200">{dualPathRul.limiting_failure_mode}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Disagreement Alarm:</span>
                  <span
                    className={`font-mono font-semibold px-2 py-0.5 rounded text-[10px] ${
                      dualPathRul.disagreement_alarm
                        ? 'bg-amber-500/20 text-amber-300'
                        : 'bg-emerald-500/10 text-emerald-400'
                    }`}
                  >
                    {dualPathRul.disagreement_alarm ? 'FLAGGED (PHYSICS != ML)' : 'CONGRUENT'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* WP-10: Automated Post-Flight Debrief Report Workflow */}
      <div className="surface-panel p-4 sm:p-5 space-y-4 border border-cyan-500/20 bg-gradient-to-br from-surface to-slate-950">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-border pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                WP-10 / PRD F12
              </span>
              <h3 className="text-sm font-semibold text-white tracking-wide">
                Automated Post-Flight Sortie Debrief Generator
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Extracts high-rate telemetry, anomaly event graph, and CBM maintenance actions into certified engineering reports.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleGenerateDebrief}
              disabled={isGeneratingDebrief}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold disabled:opacity-50 transition-colors shadow-md"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>{isGeneratingDebrief ? 'Generating Debrief…' : 'Generate Sortie Debrief'}</span>
            </button>

            <button
              onClick={handleFetchLatestDebrief}
              disabled={isGeneratingDebrief}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-surface-card border border-surface-border hover:bg-white/5 text-slate-300 text-xs font-medium transition-colors"
            >
              <span>View Latest</span>
            </button>

            {debriefMarkdown && (
              <button
                onClick={handleDownloadDebrief}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Report</span>
              </button>
            )}
          </div>
        </div>

        {debriefStatus && <p className="text-xs text-cyan-400 font-mono">{debriefStatus}</p>}

        {debriefMarkdown && (
          <div className="bg-slate-950 p-4 rounded-lg border border-cyan-500/30 max-h-[460px] overflow-y-auto">
            <AerospaceMarkdown content={debriefMarkdown} title="Post-Flight Sortie Engineering Debrief" />
          </div>
        )}
      </div>

      {/* Grid 1: Subsystem CBM Wear State & TBO Tracking */}
      <div className="surface-panel p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-surface-border pb-2">
          <div className="flex items-center gap-2">
            <ClipboardList className="w-4 h-4 text-accent" />
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
              Subsystem Wear Accumulators &amp; Time Between Overhaul (TBO)
            </h3>
          </div>
          <span className="text-[10px] font-mono text-slate-500">FLEET CBM GRAPH</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(COMPONENT_LABELS).map(([compKey, meta]) => {
            const compRul = a.rul_by_component?.[compKey];
            const p10 = compRul?.rul_p10_hours;
            const wearPct = p10 !== undefined && p10 < meta.tboHours ? ((meta.tboHours - p10) / meta.tboHours) * 100 : 8.5;

            return (
              <div key={compKey} className="bg-surface-card p-3 rounded border border-surface-border space-y-2">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="font-semibold text-xs text-slate-200 block">{meta.name}</span>
                    <span className="text-[10px] font-mono text-slate-500">{meta.ata}</span>
                  </div>
                  <span className="text-[10px] font-mono text-accent">TBO: {meta.tboHours}h</span>
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] font-mono">
                    <span className="text-slate-400">Cumulative Wear</span>
                    <span className={wearPct > 60 ? 'text-amber-400' : 'text-slate-300'}>{wearPct.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-surface-border rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        wearPct > 75 ? 'bg-critical' : wearPct > 50 ? 'bg-amber-400' : 'bg-accent'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(5, wearPct))}%` }}
                    />
                  </div>
                </div>

                <div className="flex justify-between items-center text-[10px] pt-1 border-t border-surface-border/50">
                  <span className="text-slate-500">Remaining to TBO</span>
                  <span className="font-mono font-semibold text-slate-300">
                    {p10 !== undefined && p10 < 500 ? `${fmt(p10)}h` : `>${meta.tboHours - 100}h`}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Grid 2: Prescriptive Maintenance Action Orders & Digital Sign-off (CBM-01, AIM-07) */}
      <div className="surface-panel p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-border pb-2">
          <div className="flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-accent" />
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
              Maintenance Orders &amp; Technician Sign-Off (CBM-01)
            </h3>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">Inspector ID:</span>
            <input
              type="text"
              value={signoffInspector}
              onChange={(e) => setSignoffInspector(e.target.value)}
              className="bg-surface-card border border-surface-border rounded px-2 py-0.5 text-xs text-white font-mono w-32 focus:outline-none focus:border-accent"
              placeholder="DRDO-TECH-01"
            />
          </div>
        </div>

        {workOrders.length === 0 ? (
          <div className="text-xs text-slate-500 italic p-4 text-center bg-surface-card rounded border border-surface-border">
            No active maintenance orders pending. All subsystems nominal across current sortie.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b border-surface-border text-slate-400 font-mono text-[10px] uppercase">
                  <th className="py-2 px-2.5">Action ID</th>
                  <th className="py-2 px-2.5">ATA Chapter</th>
                  <th className="py-2 px-2.5">Order Description</th>
                  <th className="py-2 px-2.5">Limiting Component</th>
                  <th className="py-2 px-2.5">Status</th>
                  <th className="py-2 px-2.5 text-right">Sign-off</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/50">
                {workOrders.map((wo) => {
                  const isClosed = wo.status === 'SIGNED_OFF';
                  return (
                    <tr key={wo.action_id} className={isClosed ? 'opacity-60 bg-white/[0.01]' : 'bg-surface-card/40'}>
                      <td className="py-2 px-2.5 font-mono text-[11px] text-slate-300 font-semibold">{wo.action_id}</td>
                      <td className="py-2 px-2.5 font-mono text-accent">{wo.ata_chapter}</td>
                      <td className="py-2 px-2.5 max-w-xs">{wo.description}</td>
                      <td className="py-2 px-2.5 font-mono text-slate-400">
                        {wo.limiting_component ? COMPONENT_LABELS[wo.limiting_component]?.name || wo.limiting_component : '--'}
                      </td>
                      <td className="py-2 px-2.5">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                            isClosed
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                              : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                          }`}
                        >
                          {isClosed ? <ShieldCheck className="w-3 h-3" /> : <Shield className="w-3 h-3" />}
                          {wo.status}
                        </span>
                      </td>
                      <td className="py-2 px-2.5 text-right">
                        {isClosed ? (
                          <span className="text-[10px] text-slate-500 font-mono block">
                            By {wo.signoff_inspector || 'TECH'}
                          </span>
                        ) : (
                          <button
                            onClick={() => handleSignOff(wo.action_id)}
                            disabled={signingOffId === wo.action_id}
                            className="px-2.5 py-1 rounded bg-accent-dim text-accent hover:bg-accent hover:text-black border border-accent-muted text-[11px] font-medium transition-colors disabled:opacity-50"
                          >
                            {signingOffId === wo.action_id ? 'Signing…' : 'Sign Off'}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Grid 3: Sensor Sanity Matrix & Shielding (F08, D02) */}
      <div className="surface-panel p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-surface-border pb-2">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
              Sensor Sanity Matrix &amp; Fault Shielding Layer (F08 / D02)
            </h3>
          </div>
          <span className="text-[10px] font-mono text-emerald-400">14-CHANNEL ISOLATION</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2">
          {sensorChannels.map((sc) => {
            const isQuarantined = sanity?.failed_channels?.includes(sc.key);
            return (
              <div
                key={sc.key}
                className={`p-2 rounded border text-xs ${
                  isQuarantined
                    ? 'bg-critical-dim border-critical-muted text-critical'
                    : 'bg-surface-card border-surface-border text-slate-300'
                }`}
              >
                <div className="text-[10px] text-slate-500 truncate">{sc.label}</div>
                <div className="font-mono font-semibold mt-0.5">{sc.val}</div>
                <div className="text-[9px] font-mono mt-1">
                  {isQuarantined ? (
                    <span className="text-critical font-bold">SHIELDED</span>
                  ) : (
                    <span className="text-emerald-400">NOMINAL</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {sanity?.advisory && (
          <div className="text-xs text-slate-300 bg-white/[0.02] p-2.5 rounded border border-surface-border/60">
            <span className="text-slate-500 font-mono text-[10px] block mb-0.5">SENSOR SANITY ADVISORY</span>
            {sanity.advisory}
          </div>
        )}
      </div>

      {/* Grid 4: Prescriptive Action & Emergency Procedure (VIS-08, AIM-07) */}
      <div className="surface-panel p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-surface-border pb-2">
          <div className="flex items-center gap-2">
            <FileCheck className="w-4 h-4 text-accent" />
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
              Diagnosed Prescriptive Action &amp; Maintenance Directives
            </h3>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            ATA: {a.ata_chapter || 'ATA-00'} · Subsystem: {a.subsystem || 'All Systems'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="bg-surface-card p-3 rounded border border-surface-border space-y-2">
            <span className="text-[10px] font-mono text-slate-500 block uppercase">
              Prescriptive Corrective Procedure
            </span>
            <p className="text-slate-200 leading-relaxed">
              {a.prescriptive_action || 'All engine subsystems operating within normal tolerances. Continue routine pre-flight inspections.'}
            </p>
            <div className="pt-2 border-t border-surface-border/50 text-[11px] text-slate-400 font-mono">
              Root Cause: <span className="text-slate-200">{a.root_cause || 'None identified'}</span>
            </div>
          </div>

          <div className="bg-surface-card p-3 rounded border border-surface-border space-y-2">
            <span className="text-[10px] font-mono text-slate-500 block uppercase">
              Emergency &amp; Standard Checklist
            </span>
            {a.emergency_checklist && a.emergency_checklist.length > 0 ? (
              <ul className="space-y-1">
                {a.emergency_checklist.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-1.5 text-slate-300">
                    <ChevronRight className="w-3.5 h-3.5 text-accent shrink-0 mt-0.5" />
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-slate-500 italic">No active emergency checklists required.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
export default MaintenanceDashboardPanel;
