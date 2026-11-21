import React, { useState } from 'react';
import { X, Server, Check, HelpCircle, Activity, RefreshCw, Smartphone, Globe, Shield } from 'lucide-react';

interface ConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  serverUrl: string;
  onSave: (url: string) => void;
  isConnected: boolean;
}

export const ConnectionModal: React.FC<ConnectionModalProps> = ({
  isOpen,
  onClose,
  serverUrl,
  onSave,
  isConnected,
}) => {
  const [url, setUrl] = useState(serverUrl);
  const [testStatus, setTestStatus] = useState<'IDLE' | 'TESTING' | 'SUCCESS' | 'ERROR'>('IDLE');
  const [testResult, setTestResult] = useState<string>('');

  if (!isOpen) return null;

  const handleTestLink = async () => {
    let cleanUrl = url.trim().replace(/\/+$/, '');
    if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) {
      cleanUrl = 'http://' + cleanUrl;
    }
    if (cleanUrl.startsWith('https://') && cleanUrl.endsWith(':8000')) {
      cleanUrl = cleanUrl.slice(0, -5);
      setUrl(cleanUrl);
    }
    setTestStatus('TESTING');
    setTestResult('');
    const t0 = performance.now();
    try {
      const res = await fetch(`${cleanUrl}/api/health`, {
        headers: { 'ngrok-skip-browser-warning': '69420' },
      });
      if (res.ok) {
        const data = await res.json();
        const latency = Math.round(performance.now() - t0);
        setTestStatus('SUCCESS');
        setTestResult(`Online (${latency}ms) — ${data.service || 'Aero-Engine Digital Twin Server'}`);
      } else {
        setTestStatus('ERROR');
        setTestResult(`HTTP ${res.status}: ${res.statusText}`);
      }
    } catch (e: any) {
      setTestStatus('ERROR');
      setTestResult(`Connection failed: ${e?.message || 'Host unreachable'}`);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let cleanUrl = url.trim().replace(/\/+$/, '');
    if (cleanUrl.startsWith('https://') && cleanUrl.endsWith(':8000')) {
      cleanUrl = cleanUrl.slice(0, -5);
    }
    onSave(cleanUrl);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="surface-panel w-full max-w-xl max-h-[90vh] overflow-y-auto rounded-sm p-5 sm:p-6 space-y-4 shadow-card-lg border border-surface-border">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-surface-border pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-sm bg-accent-dim flex items-center justify-center text-accent shrink-0">
              <Server className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-white font-mono uppercase tracking-wide">
                Avionics Telemetry &amp; Multi-Screen Datalink Gateway
              </h3>
              <p className="text-[11px] text-slate-400 font-mono">
                FastAPI 20 Hz Telemetry Hub · Web GCS &amp; 3D Viewport Synchronizer
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-sm text-slate-400 hover:text-white hover:bg-white/5 transition-colors shrink-0"
            title="Close settings"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Professional Context Banner */}
        <div className="rounded-sm bg-black/20 border border-surface-border p-3 text-xs text-slate-300 font-sans leading-relaxed">
          <div className="flex items-center gap-1.5 text-accent font-semibold text-[11px] font-mono uppercase tracking-wider">
            <Shield className="w-3.5 h-3.5 text-accent" />
            <span>Why This Gateway Exists (Multi-Device &amp; HIL Demonstration)</span>
          </div>
          <p className="mt-1.5 text-slate-300 text-xs">
            In operational UAV deployments, the Ground Control Station (GCS) connects to the aircraft's onboard telemetry bus via encrypted datalink.
          </p>
          <p className="mt-1 text-slate-400 text-[11px]">
            <strong>Live Multi-Screen Demonstrations:</strong> This gateway allows evaluators to open the control deck on a mobile phone or tablet to inject faults and advance throttle remotely, while simultaneously watching the physical engine simulation and 3D digital twin react in real time on a command center display or Blender viewport.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-300 flex items-center justify-between font-mono">
              <span>Telemetry Gateway Address / Secure Tunnel</span>
              <span className="text-xs font-normal text-slate-500">20 Hz Stream</span>
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setTestStatus('IDLE');
                }}
                placeholder="http://127.0.0.1:8000 or https://your-tunnel.ngrok-free.app"
                className="flex-1 bg-surface border border-surface-border rounded-sm px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-accent-muted focus:shadow-focus-ring"
              />
              <button
                type="button"
                onClick={handleTestLink}
                className="px-3.5 py-2 rounded-sm bg-surface-card border border-surface-border text-slate-300 hover:text-white hover:border-surface-border-strong text-xs font-medium flex items-center gap-1.5 transition-colors font-mono shrink-0"
              >
                {testStatus === 'TESTING' ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-accent" />
                ) : (
                  <Activity className="w-3.5 h-3.5 text-accent" />
                )}
                <span>Test Link</span>
              </button>
            </div>

            {testStatus !== 'IDLE' && (
              <div
                className={`text-xs px-3 py-2 rounded-sm border flex items-center gap-2 font-mono ${
                  testStatus === 'SUCCESS'
                    ? 'bg-success-dim border-success-muted text-success'
                    : testStatus === 'ERROR'
                    ? 'bg-critical-dim border-critical-muted text-critical'
                    : 'bg-surface-card border-surface-border text-slate-300'
                }`}
              >
                <span className="font-medium">Link Status:</span>
                <span>{testResult || 'Testing connection...'}</span>
              </div>
            )}

            <div className="flex items-center justify-between text-xs pt-1 font-mono">
              <span className="text-slate-400">Active Datalink State:</span>
              <span
                className={`font-medium px-2 py-0.5 rounded-sm text-xs border ${
                  isConnected
                    ? 'bg-success-dim text-success border-success-muted'
                    : 'bg-critical-dim text-critical border-critical-muted'
                }`}
              >
                {isConnected ? 'Connected · 20 Hz Synchronized' : 'Disconnected / Awaiting Handshake'}
              </span>
            </div>
          </div>

          {/* Quick Target Presets */}
          <div className="space-y-1.5 font-mono">
            <span className="text-xs uppercase font-medium text-slate-400 tracking-wide">
              Quick Target Presets
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setUrl('http://127.0.0.1:8000')}
                className="text-left px-3 py-2 rounded-sm bg-white/[0.02] border border-surface-border hover:border-surface-border-strong hover:bg-white/[0.04] transition-colors text-xs"
              >
                <div className="flex items-center gap-1.5 text-slate-200 font-medium text-xs">
                  <Server className="w-3 h-3 text-accent" />
                  <span>Workstation HIL</span>
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">Local 20 Hz test bench</div>
                <div className="text-[11px] text-slate-400 font-mono truncate mt-1">127.0.0.1:8000</div>
              </button>

              <button
                type="button"
                onClick={() => setUrl('https://maverick-vnrg.onrender.com')}
                className="text-left px-3 py-2 rounded-sm bg-white/[0.02] border border-surface-border hover:border-surface-border-strong hover:bg-white/[0.04] transition-colors text-xs"
              >
                <div className="flex items-center gap-1.5 text-slate-200 font-medium text-xs">
                  <Globe className="w-3 h-3 text-accent" />
                  <span>Cloud Datalink</span>
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">Public hosted relay</div>
                <div className="text-[11px] text-slate-400 font-mono truncate mt-1">maverick-vnrg...</div>
              </button>

              <button
                type="button"
                onClick={() => setUrl('http://192.168.1.20:8000')}
                className="text-left px-3 py-2 rounded-sm bg-white/[0.02] border border-surface-border hover:border-surface-border-strong hover:bg-white/[0.04] transition-colors text-xs"
              >
                <div className="flex items-center gap-1.5 text-slate-200 font-medium text-xs">
                  <Smartphone className="w-3 h-3 text-accent" />
                  <span>Field Remote</span>
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">Mobile LAN / Wi-Fi IP</div>
                <div className="text-[11px] text-slate-400 font-mono truncate mt-1">192.168.1.20:8000</div>
              </button>
            </div>
          </div>

          {/* Connection Guide */}
          <div className="bg-white/[0.02] p-3.5 rounded-sm border border-surface-border text-xs text-slate-400 space-y-2 font-sans leading-relaxed">
            <div className="flex items-center justify-between text-slate-300 font-medium text-xs font-mono">
              <div className="flex items-center gap-1.5">
                <HelpCircle className="w-3.5 h-3.5 text-accent" />
                <span>Deployment &amp; Mobile Remote Pairing (UX-04)</span>
              </div>
              <span className="text-[10px] text-accent px-1.5 py-0.5 rounded border border-accent/40 bg-accent/10">
                LAN AUTO-PAIR
              </span>
            </div>

            {/* QR Code Remote Card */}
            <div className="flex items-center gap-4 p-2.5 rounded border border-surface-border bg-slate-950/60 font-mono">
              <div className="w-20 h-20 bg-white p-1 rounded flex items-center justify-center flex-shrink-0">
                <svg viewBox="0 0 29 29" className="w-full h-full text-slate-950 fill-current">
                  {/* Stylized QR Code Matrix */}
                  <rect x="0" y="0" width="7" height="7" />
                  <rect x="1" y="1" width="5" height="5" fill="white" />
                  <rect x="2" y="2" width="3" height="3" />
                  <rect x="22" y="0" width="7" height="7" />
                  <rect x="23" y="1" width="5" height="5" fill="white" />
                  <rect x="24" y="2" width="3" height="3" />
                  <rect x="0" y="22" width="7" height="7" />
                  <rect x="1" y="23" width="5" height="5" fill="white" />
                  <rect x="2" y="24" width="3" height="3" />
                  <rect x="9" y="2" width="2" height="2" />
                  <rect x="13" y="2" width="2" height="2" />
                  <rect x="17" y="2" width="2" height="2" />
                  <rect x="9" y="6" width="2" height="2" />
                  <rect x="15" y="6" width="2" height="2" />
                  <rect x="9" y="10" width="11" height="2" />
                  <rect x="2" y="10" width="3" height="2" />
                  <rect x="24" y="10" width="3" height="2" />
                  <rect x="11" y="14" width="7" height="2" />
                  <rect x="21" y="14" width="2" height="2" />
                  <rect x="9" y="18" width="2" height="2" />
                  <rect x="15" y="18" width="5" height="2" />
                  <rect x="9" y="22" width="3" height="2" />
                  <rect x="15" y="22" width="2" height="2" />
                  <rect x="21" y="22" width="4" height="2" />
                  <rect x="11" y="26" width="4" height="2" />
                  <rect x="19" y="26" width="2" height="2" />
                  <rect x="25" y="26" width="2" height="2" />
                </svg>
              </div>
              <div className="space-y-1 min-w-0">
                <div className="text-[11px] font-semibold text-slate-200">
                  Scan to Open Mobile Secondary Screen
                </div>
                <div className="text-[10px] text-slate-400">
                  Evaluators can point their smartphone camera at this QR code to load the wireless GCS cockpit and inject faults remotely.
                </div>
                <div className="text-[10px] text-cyan-400 truncate">
                  Target: {typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.hostname}:8000/?role=pilot` : 'http://192.168.1.x:8000'}
                </div>
              </div>
            </div>

            <p className="text-[11px]">
              1. <strong className="text-slate-300 font-mono">Workstation Evaluation:</strong> Select <code className="text-accent font-mono">http://127.0.0.1:8000</code> to connect directly to the local physics simulator and Blender 3D viewport.
            </p>
            <p className="text-[11px]">
              2. <strong className="text-slate-300 font-mono">Remote Mobile Flight Deck:</strong> Connect a smartphone or tablet to your local Wi-Fi IP or tunnel gateway to demonstrate wireless fault injection and live twin synchronization.
            </p>
          </div>

          <div className="flex justify-end gap-2.5 pt-2 font-mono">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-sm text-xs bg-surface-card border border-surface-border text-slate-300 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex items-center gap-1.5 px-5 py-2 rounded-sm text-xs font-medium bg-accent text-white hover:bg-accent/90 transition-colors shadow-sm"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Save &amp; Connect</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
