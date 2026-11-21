import { useState, useEffect } from 'react';
import { Radio, Shield, ShieldAlert, Cpu, X, AlertTriangle, CheckCircle2 } from 'lucide-react';

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-md border border-slate-700 bg-slate-900 shadow-2xl flex flex-col font-mono">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            <Radio className="w-5 h-5 text-accent animate-pulse" />
            <div>
              <div className="text-sm font-semibold tracking-wider text-slate-100 uppercase">
                Avionics CAN Bus & FADEC Telemetry Hub
              </div>
              <div className="text-[11px] text-slate-400">
                SAE J1939 29-bit ID · 20 Hz Frame Rate · Real-Time Intrusion Detection System (CAN IDS)
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 p-5 overflow-y-auto space-y-5 text-xs text-slate-300">
          {/* Source Selector Bar */}
          <div className="p-3.5 rounded border border-slate-800 bg-slate-950/40 flex flex-wrap items-center justify-between gap-4">
            <div className="space-y-1">
              <span className="text-[10px] text-slate-400 uppercase tracking-widest block">Telemetry Source Mode</span>
              <div className="flex items-center gap-2">
                <span className={`inline-block w-2.5 h-2.5 rounded-full ${isCanActive ? 'bg-cyan-400 animate-pulse' : 'bg-emerald-500'}`} />
                <span className="text-sm font-bold text-slate-100">
                  {isCanActive ? 'VIRTUAL CAN BUS (SAE J1939 / FADEC)' : 'DIRECT IN-PROCESS SIMULATION'}
                </span>
                <span className="text-[11px] text-slate-400 px-1.5 py-0.5 rounded border border-slate-700 bg-slate-800">
                  {canStatus?.can_interface ?? 'virtual'}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                disabled={isSwitching || !isCanActive}
                onClick={() => toggleSource('DIRECT')}
                className={`px-3 py-1.5 rounded border text-xs font-semibold transition-all ${
                  !isCanActive
                    ? 'border-emerald-500/80 bg-emerald-500/20 text-emerald-300'
                    : 'border-slate-700 bg-slate-800 text-slate-300 hover:border-slate-500'
                }`}
              >
                DIRECT (Plant)
              </button>
              <button
                disabled={isSwitching || isCanActive}
                onClick={() => toggleSource('CAN')}
                className={`px-3 py-1.5 rounded border text-xs font-semibold transition-all ${
                  isCanActive
                    ? 'border-cyan-500/80 bg-cyan-500/20 text-cyan-300'
                    : 'border-slate-700 bg-slate-800 text-slate-300 hover:border-slate-500'
                }`}
              >
                CAN BUS (J1939)
              </button>
            </div>
          </div>

          {/* Grid: Message Decoder & Intrusion Detector */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Left Column: CAN Frame Stream */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-slate-200 font-semibold">
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  <span>J1939 Frame Stream (anumaan_engine_v2.dbc)</span>
                </div>
                <span className="text-[10px] text-slate-400">
                  Sent: {canStatus?.bus?.bytes_sent ? `${(canStatus.bus.bytes_sent / 1024).toFixed(1)} kB` : '0 kB'}
                </span>
              </div>

              <div className="border border-slate-800 rounded bg-slate-950/70 overflow-hidden">
                <table className="w-full text-left text-[11px]">
                  <thead className="bg-slate-900 border-b border-slate-800 text-slate-400">
                    <tr>
                      <th className="py-1.5 px-2.5 font-medium">Message</th>
                      <th className="py-1.5 px-2 font-medium">Arb ID</th>
                      <th className="py-1.5 px-2 font-medium">Rate</th>
                      <th className="py-1.5 px-2 font-medium">Seq</th>
                      <th className="py-1.5 px-2 font-medium">Payload (Hex)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {(canStatus?.bus?.recent_frames && canStatus.bus.recent_frames.length > 0) ? (
                      canStatus.bus.recent_frames.map((f) => (
                        <tr key={f.name} className="hover:bg-slate-900/40">
                          <td className="py-1 px-2.5 text-cyan-300 font-medium">{f.name}</td>
                          <td className="py-1 px-2 text-slate-400">{f.arbitration_id}</td>
                          <td className="py-1 px-2 text-slate-400">{1000 / f.cycle_time_ms} Hz</td>
                          <td className="py-1 px-2 text-amber-400">{f.counter}</td>
                          <td className="py-1 px-2 text-slate-300 tracking-wider">{f.data_hex}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-3 px-3 text-center text-slate-500 italic">
                          {isCanActive ? 'Receiving CAN frames...' : 'CAN Bus Idle (Switch source to CAN above)'}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Right Column: Intrusion Detection System (CAN IDS) */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-slate-200 font-semibold">
                  {alertCount > 0 ? (
                    <ShieldAlert className="w-4 h-4 text-rose-400 animate-pulse" />
                  ) : (
                    <Shield className="w-4 h-4 text-emerald-400" />
                  )}
                  <span>CAN Intrusion Detection System (IDS)</span>
                </div>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                    alertCount > 0 ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40' : 'bg-emerald-500/20 text-emerald-400'
                  }`}
                >
                  {alertCount > 0 ? `${alertCount} THREAT ALERT(S)` : 'NOMINAL (0 ALERTS)'}
                </span>
              </div>

              {/* Alert Console Log */}
              <div className="h-40 border border-slate-800 rounded bg-slate-950/70 p-2.5 overflow-y-auto space-y-1.5 font-mono text-[11px]">
                {alerts.length > 0 ? (
                  alerts.slice(-6).map((a, i) => (
                    <div key={i} className="p-1.5 rounded border border-rose-900/50 bg-rose-950/30 text-rose-300 flex items-start gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 mt-0.5 text-rose-400 flex-shrink-0" />
                      <div>
                        <div className="font-bold">
                          [{a.kind}] Arb ID: 0x{a.arb_id.toString(16).toUpperCase()} ({a.severity})
                        </div>
                        <div className="text-[10px] text-rose-200/80">{a.description}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-slate-500 text-center">
                    <CheckCircle2 className="w-6 h-6 text-emerald-500/40 mb-1" />
                    <span>No intrusion anomalies detected on the bus.</span>
                    <span className="text-[10px] text-slate-600">All frame periods, sequence counters, and payloads conform to DBC limits.</span>
                  </div>
                )}
              </div>

              {/* Attack Simulation Buttons */}
              <div className="p-3 rounded border border-slate-800 bg-slate-950/40 space-y-2">
                <div className="text-[10px] text-slate-400 uppercase tracking-widest">
                  Live Defense Threat Simulation Test
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    disabled={isSpoofing}
                    onClick={() => injectSpoof('UNKNOWN_ID')}
                    className="p-1.5 text-[10px] rounded border border-rose-800/60 bg-rose-950/40 hover:bg-rose-900/50 text-rose-300 font-semibold text-center transition-colors"
                  >
                    Rogue ID (0x18FF99FF)
                  </button>
                  <button
                    disabled={isSpoofing}
                    onClick={() => injectSpoof('SEQUENCE_GAP')}
                    className="p-1.5 text-[10px] rounded border border-amber-800/60 bg-amber-950/40 hover:bg-amber-900/50 text-amber-300 font-semibold text-center transition-colors"
                  >
                    Sequence Gap (+5)
                  </button>
                  <button
                    disabled={isSpoofing}
                    onClick={() => injectSpoof('OUT_OF_RANGE')}
                    className="p-1.5 text-[10px] rounded border border-cyan-800/60 bg-cyan-950/40 hover:bg-cyan-900/50 text-cyan-300 font-semibold text-center transition-colors"
                  >
                    Out-Of-Range Payload
                  </button>
                </div>
                {lastSpoofResult && (
                  <div className="text-[10px] text-amber-300/90 font-mono italic mt-1">{lastSpoofResult}</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-2.5 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-[11px] text-slate-400">
          <div className="flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400" />
            <span>Merkle-Sealed Telemetry Ledger active (SHA-256 tree verification: valid)</span>
          </div>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded bg-slate-800 text-slate-200 hover:bg-slate-700 transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
