import React, { useState, useEffect } from 'react';
import {
  ClipboardList,
  Shield,
  ShieldCheck,
  UserCheck,
  RefreshCw,
  FileCheck,
  ChevronRight,
} from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';

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

  useEffect(() => {
    fetchWorkOrders();
    const interval = setInterval(fetchWorkOrders, 5000);
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
    { key: 'OIL_PRESS', label: 'Oil Pressure', val: `${fmt(state.telemetry.OIL_PRESS)} bar` },
    { key: 'OIL_TEMP', label: 'Oil Temperature', val: `${fmt(state.telemetry.OIL_TEMP)} °C` },
    { key: 'FUEL_FLOW', label: 'Fuel Flow Rate', val: `${fmt(state.telemetry.FUEL_FLOW)} L/h` },
    { key: 'MAP', label: 'Manifold Pressure', val: `${fmt(state.telemetry.MAP)} kPa` },
    { key: 'VIB_GEARBOX_RMS', label: 'Gearbox Vibration', val: `${fmt(state.telemetry.VIB_GEARBOX_RMS, 2)} mm/s` },
    { key: 'BUS_VOLTAGE', label: 'DC Bus Voltage', val: `${fmt(state.telemetry.BUS_VOLTAGE)} V` },
  ];

  const sanity = a.sensor_sanity;
  const failedSensors = sanity?.failed_channels || [];
  const driftDetected = sanity?.drift_detected || false;

  const conformalRul = a.conformal_rul || {};

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="surface-panel p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 border-l-4 border-l-emerald-500">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              VIS-04 / CBM-01
            </span>
            <h2 className="text-sm font-semibold text-white tracking-wide">
              Ground Crew Maintenance &amp; Condition-Based Health Terminal
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Certified CBM work-order dispatch, Split-Conformal RUL component life meters, and sensor residual shielding matrix.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-surface-card border border-surface-border text-xs">
            <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
            <input
              type="text"
              value={signoffInspector}
              onChange={(e) => setSignoffInspector(e.target.value)}
              placeholder="Inspector ID"
              className="bg-transparent text-slate-200 text-xs w-28 focus:outline-none border-b border-surface-border focus:border-accent"
            />
          </div>

          <button
            onClick={fetchWorkOrders}
            disabled={isLoadingOrders}
            className="p-1.5 rounded bg-surface-card border border-surface-border text-slate-400 hover:text-white hover:bg-surface-card-hover transition-colors"
            title="Refresh work orders"
          >
            <RefreshCw className={`w-4 h-4 ${isLoadingOrders ? 'animate-spin text-accent' : ''}`} />
          </button>
        </div>
      </div>

      {feedbackMsg && (
        <div
          className={`p-3 rounded text-xs flex items-center justify-between border ${
            feedbackMsg.type === 'success'
              ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/50'
              : 'bg-critical-dim text-critical border-critical-muted'
          }`}
        >
          <span>{feedbackMsg.text}</span>
          <button onClick={() => setFeedbackMsg(null)} className="text-slate-400 hover:text-white ml-2 text-[10px]">
            Dismiss
          </button>
        </div>
      )}

      {/* Grid 1: Split-Conformal RUL & Component Life Meters (AIM-05, F12) */}
      <div className="surface-panel p-4 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-border pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                F12 / AIM-05
              </span>
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                Split-Conformal Remaining Useful Life (RUL) with 90% Coverage
              </h3>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Finite-sample distribution-free uncertainty intervals: P10 conservative lower bound, P50 median, P90 optimistic upper bound.
            </p>
          </div>

          <div className="px-2.5 py-1 rounded bg-indigo-950/50 border border-indigo-800/40 text-[10px] font-mono text-indigo-300 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
            <span>Guaranteed Coverage: 90% (α = 0.10)</span>
          </div>
        </div>

        {/* 6 Subsystem Life Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(COMPONENT_LABELS).map(([compKey, meta]) => {
            const conf = conformalRul[compKey];
            const p10 = conf?.rul_p10_hours ?? a.rul_by_component?.[compKey]?.rul_p10_hours ?? 500;
            const p50 = conf?.rul_p50_hours ?? a.rul_by_component?.[compKey]?.rul_p50_hours ?? 650;
            const p90 = conf?.rul_p90_hours ?? a.rul_by_component?.[compKey]?.rul_p90_hours ?? 800;

            const isLimiting = compKey === a.limiting_component;
            const remainingPct = Math.min(100, Math.max(0, (p10 / meta.tboHours) * 100));

            return (
              <div
                key={compKey}
                className={`p-3.5 rounded border transition-all ${
                  isLimiting
                    ? 'bg-critical-dim/30 border-critical-muted'
                    : 'bg-surface-card border-surface-border'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-xs font-semibold text-white block">{meta.name}</span>
                    <span className="text-[10px] text-slate-500 font-mono">{meta.ata}</span>
                  </div>
                  {isLimiting ? (
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-critical-dim text-critical border border-critical-muted">
                      LIMITING
                    </span>
                  ) : (
                    <span className="text-[10px] text-slate-500 font-mono">TBO {meta.tboHours}h</span>
                  )}
                </div>

                {/* Progress Bar */}
                <div className="mt-3 space-y-1">
                  <div className="flex justify-between text-[10px] font-mono">
                    <span className="text-slate-400">P10 Conservative RUL:</span>
                    <span className={`font-bold ${isLimiting ? 'text-critical' : 'text-slate-100'}`}>
                      {p10 >= 500 ? '>500h' : `${fmt(p10)} h`}
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-surface rounded-full overflow-hidden border border-surface-border">
                    <div
                      className={`h-full transition-all duration-300 ${
                        isLimiting ? 'bg-critical' : remainingPct < 25 ? 'bg-warning' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.max(5, remainingPct)}%` }}
                    />
                  </div>
                </div>

                {/* Conformal Bounds Trio */}
                <div className="grid grid-cols-3 gap-1 pt-2 mt-2 border-t border-surface-border/50 text-center font-mono">
                  <div className="bg-white/[0.02] p-1 rounded">
                    <span className="text-[9px] text-slate-500 block">P10 Low</span>
                    <span className="text-xs font-semibold text-slate-300">{fmt(p10, 0)}h</span>
                  </div>
                  <div className="bg-white/[0.02] p-1 rounded">
                    <span className="text-[9px] text-slate-500 block">P50 Med</span>
                    <span className="text-xs font-semibold text-slate-200">{fmt(p50, 0)}h</span>
                  </div>
                  <div className="bg-white/[0.02] p-1 rounded">
                    <span className="text-[9px] text-slate-500 block">P90 High</span>
                    <span className="text-xs font-semibold text-slate-400">{fmt(p90, 0)}h</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Grid 2: CBM Work Orders & Sign-off Queue (VIS-08, CBM-01) */}
      <div className="surface-panel p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-surface-border pb-2">
          <div className="flex items-center gap-2">
            <ClipboardList className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
              CBM Work Order Dispatch &amp; Inspector Sign-Off Queue
            </h3>
          </div>
          <span className="text-[10px] font-mono text-slate-500">
            {workOrders.filter((w) => w.status === 'OPEN').length} Open Orders
          </span>
        </div>

        {workOrders.length === 0 ? (
          <div className="text-xs text-slate-500 bg-surface-card p-4 rounded border border-surface-border text-center">
            No maintenance work orders have been logged yet. Any simulated or telemetry-detected fault will automatically generate an ATA-coded work order.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="text-[9px] uppercase tracking-wider text-slate-500 border-b border-surface-border text-left">
                  <th className="py-2 pr-3">Action ID</th>
                  <th className="py-2 px-3">ATA Chapter</th>
                  <th className="py-2 px-3">Sortie</th>
                  <th className="py-2 px-3">Description</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 pl-3 text-right">Sign-Off Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/50">
                {workOrders.map((wo) => {
                  const isOpen = wo.status === 'OPEN';
                  return (
                    <tr key={wo.action_id} className="hover:bg-white/[0.02]">
                      <td className="py-2.5 pr-3 font-mono font-medium text-slate-300">
                        {wo.action_id}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-white/5 border border-surface-border text-slate-300">
                          {wo.ata_chapter}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-400">{wo.sortie_id}</td>
                      <td className="py-2.5 px-3 text-slate-300 max-w-xs truncate" title={wo.description}>
                        {wo.description}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                            isOpen
                              ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                              : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                          }`}
                        >
                          {isOpen ? 'OPEN' : 'SIGNED OFF'}
                        </span>
                      </td>
                      <td className="py-2.5 pl-3 text-right">
                        {isOpen ? (
                          <button
                            onClick={() => handleSignOff(wo.action_id)}
                            disabled={signingOffId === wo.action_id}
                            className="px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30 text-[11px] font-medium transition-colors disabled:opacity-50"
                          >
                            {signingOffId === wo.action_id ? 'Signing...' : 'Sign-Off & Close'}
                          </button>
                        ) : (
                          <span className="text-[10px] font-mono text-slate-500">
                            Closed by {wo.signoff_inspector || 'Inspector'}
                          </span>
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

      {/* Grid 3: Sensor Sanity Matrix & Residual Shielding (FDP-06, F14) */}
      <div className="surface-panel p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-border pb-2">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-accent" />
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
              Transducer Sanity &amp; Residual Shielding Matrix (F14 / FDP-06)
            </h3>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                driftDetected
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
              }`}
            >
              {driftDetected ? 'SENSOR DRIFT DETECTED' : 'CALIBRATION STABLE'}
            </span>

            <span
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                failedSensors.length > 0
                  ? 'bg-critical-dim text-critical border-critical-muted'
                  : 'bg-surface-card text-slate-400 border-surface-border'
              }`}
            >
              Residual Shielding: {failedSensors.length > 0 ? `${failedSensors.length} QUARANTINED` : 'STANDBY'}
            </span>
          </div>
        </div>

        <p className="text-[11px] text-slate-400">
          Continuous cross-channel statistical drift tests. Drifting or flatlined sensors are quarantined and zeroed out from model residuals to prevent false engine anomaly alarms.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2">
          {sensorChannels.map((sc) => {
            const isQuarantined = failedSensors.some((f) => f.includes(sc.key) || sc.key.includes(f));
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
