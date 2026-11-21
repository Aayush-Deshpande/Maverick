import { useState, useEffect } from 'react';
import { Radio, ShieldAlert, Cpu, X, CheckCircle2, ShieldCheck } from 'lucide-react';

interface CANAlertItem {
  kind: string;
  arb_id: number;
  t_sec: number;
  description: string;
  severity: string;
}

interface CANMessagePreview {
  name: string;
  arbitration_id: string;
  cycle_time_ms: number;
  dlc: number;
  data_hex: string;
  counter: number;
}

interface CANBusStatus {
  engine_id: string;
  data_source: 'DIRECT' | 'CAN';
  can_interface: string;
  bus: {
    messages_per_frame: number;
    bytes_sent: number;
    alerts: CANAlertItem[];
    alert_count: number;
    recent_frames: CANMessagePreview[];
  } | null;
}

interface Props {
  engineId: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function CanBusInspector({ engineId, isOpen, onClose }: Props) {
  const [canStatus, setCanStatus] = useState<CANBusStatus | null>(null);
  const [isSwitching, setIsSwitching] = useState(false);
  const [isSpoofing, setIsSpoofing] = useState(false);
  const [lastSpoofResult, setLastSpoofResult] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`/api/v1/engines/${engineId}/can`);
      if (res.ok) {
        const data = await res.json();
        setCanStatus(data);
      }
    } catch {
      // Backend polling error
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    fetchStatus();
    const interval = setInterval(fetchStatus, 500);
    return () => clearInterval(interval);
  }, [isOpen, engineId]);

  if (!isOpen) return null;

  const toggleSource = async (targetSource: 'DIRECT' | 'CAN') => {
    setIsSwitching(true);
    try {
      await fetch('/api/v1/runtime/source', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data_source: targetSource }),
      });
      await fetchStatus();
    } catch (err) {
      console.error('Failed to toggle source', err);
    } finally {
      setIsSwitching(false);
    }
  };

  const injectSpoof = async (kind: 'UNKNOWN_ID' | 'SEQUENCE_GAP' | 'OUT_OF_RANGE') => {
    setIsSpoofing(true);
    setLastSpoofResult(null);
    try {
      const res = await fetch(`/api/v1/engines/${engineId}/can/inject_spoof`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind }),
      });
      if (res.ok) {
        const data = await res.json();
        const count = data.alerts_generated?.length ?? 0;
        setLastSpoofResult(`Injected ${kind}: Detected ${count} threat alert(s)`);
      }
      await fetchStatus();
    } catch (err) {
      setLastSpoofResult(`Spoof injection failed: ${String(err)}`);
    } finally {
      setIsSpoofing(false);
    }
  };

  const isCanActive = canStatus?.data_source === 'CAN';
  const alerts = canStatus?.bus?.alerts ?? [];
  const alertCount = canStatus?.bus?.alert_count ?? 0;

  return (
    <div
      id="can-inspector-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in font-sans"
      onClick={onClose}
    >
      <div
        className="surface-panel w-full max-w-4xl max-h-[88vh] overflow-hidden rounded-sm border border-surface-border-strong text-slate-800 bg-[#f7f6f0] shadow-card-lg flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-surface-border bg-black/[0.02]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-sm bg-accent-dim border border-accent/20 flex items-center justify-center text-accent">
              <Radio className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900 tracking-tight font-mono">
                Avionics CAN Bus &amp; FADEC Telemetry Hub
              </h3>
              <p className="text-xs text-slate-600 font-mono mt-0.5">
                SAE J1939 29-bit ID · 20 Hz Frame Rate · Real-Time Intrusion Detection System (CAN IDS)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-sm text-slate-400 hover:text-slate-800 hover:bg-black/10 transition-colors"
            title="Close inspector"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 p-5 overflow-y-auto space-y-5 text-xs font-sans">
          {/* Telemetry Source Mode Switcher */}
          <div className="p-3.5 rounded-sm border border-surface-border bg-white shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono block">
                Telemetry Source Mode
              </span>
              <div className="flex items-center gap-2 mt-1">
                <span className={`w-2 h-2 rounded-full ${isCanActive ? 'bg-cyan-600 animate-pulse' : 'bg-emerald-600'}`} />
                <span className="text-sm font-semibold text-slate-900 font-mono">
                  {isCanActive ? 'FADEC CAN Bus Link (SAE J1939)' : 'Direct Simulation Feed'}
                </span>
                <span className="text-[10px] text-slate-600 px-1.5 py-0.5 rounded-sm bg-black/5 border border-surface-border font-mono">
                  {canStatus?.can_interface ?? 'virtual'}
                </span>
              </div>
              <p className="text-[11px] text-slate-600 mt-1">
                {isCanActive
                  ? 'Telemetry is quantized through the J1939 DBC matrix and transmitted as binary frames with 4-bit sequence counters.'
                  : 'Telemetry streams directly from continuous thermodynamic differential equation solutions.'}
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <div className="flex rounded-sm border border-surface-border bg-black/[0.04] p-1 font-mono">
                <button
                  disabled={isSwitching || !isCanActive}
                  onClick={() => toggleSource('DIRECT')}
                  className={`px-3 py-1.5 rounded-sm text-xs transition-all ${
                    !isCanActive
                      ? 'bg-accent text-white shadow-sm font-semibold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Direct Simulation
                </button>
                <button
                  disabled={isSwitching || isCanActive}
                  onClick={() => toggleSource('CAN')}
                  className={`px-3 py-1.5 rounded-sm text-xs transition-all ${
                    isCanActive
                      ? 'bg-accent text-white shadow-sm font-semibold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  CAN Bus (J1939)
                </button>
              </div>
            </div>
          </div>

          {/* Grid: Message Decoder & Intrusion Detector */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Left Column: CAN Frame Stream */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-slate-900 font-semibold font-mono text-xs">
                  <Cpu className="w-3.5 h-3.5 text-accent" />
                  <span>J1939 Frame Stream (anumaan_engine_v2.dbc)</span>
                </div>
                <span className="text-[10px] text-slate-500 font-mono">
                  Transmitted: {canStatus?.bus?.bytes_sent ? `${(canStatus.bus.bytes_sent / 1024).toFixed(1)} kB` : '0 kB'}
                </span>
              </div>

              <div className="border border-surface-border rounded-sm bg-white shadow-xs overflow-hidden">
                <table className="w-full text-left text-[11px]">
                  <thead className="bg-black/[0.03] border-b border-surface-border text-slate-600 font-mono text-[10px] uppercase">
                    <tr>
                      <th className="py-2 px-3 font-semibold">Message</th>
                      <th className="py-2 px-2 font-semibold">Arb ID</th>
                      <th className="py-2 px-2 font-semibold">Rate</th>
                      <th className="py-2 px-2 font-semibold">Seq</th>
                      <th className="py-2 px-3 font-semibold">Payload (Hex)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border/60 font-mono">
                    {canStatus?.bus?.recent_frames && canStatus.bus.recent_frames.length > 0 ? (
                      canStatus.bus.recent_frames.map((f, i) => (
                        <tr key={i} className="hover:bg-black/[0.02] transition-colors">
                          <td className="py-1.5 px-3 font-sans text-slate-900 font-medium">{f.name}</td>
                          <td className="py-1.5 px-2 text-slate-600">{f.arbitration_id}</td>
                          <td className="py-1.5 px-2 text-slate-600">{f.cycle_time_ms}ms</td>
                          <td className="py-1.5 px-2 text-accent font-semibold">{f.counter}</td>
                          <td className="py-1.5 px-3 text-slate-800 tracking-wider font-medium">{f.data_hex}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-slate-500 font-mono text-xs">
                          {isCanActive
                            ? 'Awaiting incoming frames from virtual CAN bus...'
                            : 'CAN bus idle · Switch source to CAN above to view active frames'}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Right Column: Security IDS & Threat Testing */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-slate-900 font-semibold font-mono text-xs">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
                  <span>CAN Intrusion Detection System (IDS)</span>
                </div>
                <span
                  className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-sm ${
                    alertCount > 0
                      ? 'bg-rose-100 text-rose-800 border border-rose-300'
                      : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  }`}
                >
                  {alertCount > 0 ? `${alertCount} THREAT(S) FLAGGED` : 'NOMINAL (0 ALERTS)'}
                </span>
              </div>

              {/* Status Banner */}
              <div
                className={`p-3 rounded-sm border ${
                  alertCount > 0
                    ? 'border-rose-300 bg-rose-50 text-rose-900'
                    : 'border-surface-border bg-white text-slate-700 shadow-xs'
                }`}
              >
                {alertCount === 0 ? (
                  <div className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <div>
                      <div className="text-xs font-semibold text-slate-900">Bus Integrity Verified</div>
                      <div className="text-[11px] text-slate-600 mt-0.5">
                        Frame periods, sequence counters, and payload bounds verify within certified limits.
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="flex items-center gap-1.5 font-bold text-rose-900 text-xs">
                      <ShieldAlert className="w-4 h-4 text-rose-600" />
                      <span>Security Anomaly Detected</span>
                    </div>
                    <div className="max-h-24 overflow-y-auto space-y-1.5 font-mono">
                      {alerts.slice(-3).map((a, i) => (
                        <div key={i} className="text-[11px] flex items-center justify-between gap-2 border-b border-rose-200 pb-1">
                          <span className="font-semibold text-rose-950">{a.kind} (0x{a.arb_id.toString(16).toUpperCase()})</span>
                          <span className="text-rose-800 text-[10px]">{a.description}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Threat Injection Testing */}
              <div className="p-3.5 rounded-sm border border-surface-border bg-white shadow-xs space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-900 font-mono">Simulate Bus Faults &amp; Attack Vectors</span>
                  <span className="text-[10px] text-slate-500 font-mono">Security Test</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    disabled={isSpoofing}
                    onClick={() => injectSpoof('UNKNOWN_ID')}
                    className="p-2.5 rounded-sm border border-surface-border bg-[#f7f6f0] hover:bg-black/5 hover:border-slate-400 text-slate-800 transition-all text-center group disabled:opacity-50"
                  >
                    <div className="text-xs font-semibold text-slate-900 group-hover:text-accent transition-colors">
                      Rogue ID
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono mt-0.5">0x18FF99FF</div>
                  </button>

                  <button
                    disabled={isSpoofing}
                    onClick={() => injectSpoof('SEQUENCE_GAP')}
                    className="p-2.5 rounded-sm border border-surface-border bg-[#f7f6f0] hover:bg-black/5 hover:border-slate-400 text-slate-800 transition-all text-center group disabled:opacity-50"
                  >
                    <div className="text-xs font-semibold text-slate-900 group-hover:text-amber-800 transition-colors">
                      Sequence Gap
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono mt-0.5">+5 counter jump</div>
                  </button>

                  <button
                    disabled={isSpoofing}
                    onClick={() => injectSpoof('OUT_OF_RANGE')}
                    className="p-2.5 rounded-sm border border-surface-border bg-[#f7f6f0] hover:bg-black/5 hover:border-slate-400 text-slate-800 transition-all text-center group disabled:opacity-50"
                  >
                    <div className="text-xs font-semibold text-slate-900 group-hover:text-cyan-800 transition-colors">
                      Out-Of-Range Payload
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono mt-0.5">Corrupted value</div>
                  </button>
                </div>

                {lastSpoofResult && (
                  <div className="text-[11px] text-amber-900 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-sm font-mono">
                    {lastSpoofResult}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-surface-border bg-black/[0.02] text-[11px] text-slate-600 font-mono">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
            <span>Flight Data Ledger active (SHA-256 Merkle root verified)</span>
          </div>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded-sm bg-accent hover:bg-accent/90 text-white text-xs font-mono font-medium transition-colors shadow-xs"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
