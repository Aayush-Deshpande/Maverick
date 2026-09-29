import React, { useState } from 'react';
import { X, Server, Check, HelpCircle, Activity, Wifi, RefreshCw } from 'lucide-react';

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
        setTestResult(`Online (${latency}ms) — ${data.service || 'Rotax 912 iS Server'}`);
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
    onSave(url);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="surface-panel w-full max-w-lg rounded-sm p-5 sm:p-6 space-y-4 shadow-card-lg border border-surface-border">
        <div className="flex items-center justify-between border-b border-surface-border pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-sm bg-accent-dim flex items-center justify-center text-accent">
              <Server className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-white font-mono uppercase tracking-wide">
                Telemetry Data Link Configuration
              </h3>
              <p className="text-[11px] text-slate-400 font-mono">FastAPI 20 Hz WebSocket / REST hub</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-sm text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-300 flex items-center justify-between font-mono">
              <span>Backend host address / tunnel URL</span>
              <span className="text-[10px] font-normal text-slate-500">Port 8000</span>
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setTestStatus('IDLE');
                }}
                placeholder="http://127.0.0.1:8000"
                className="flex-1 bg-surface border border-surface-border rounded-sm px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-accent-muted focus:shadow-focus-ring"
              />
              <button
                type="button"
                onClick={handleTestLink}
                className="px-3 py-2 rounded-sm bg-surface-card border border-surface-border text-slate-300 hover:text-white hover:border-surface-border-strong text-xs font-medium flex items-center gap-1.5 transition-colors font-mono"
              >
                {testStatus === 'TESTING' ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-accent" />
                ) : (
                  <Activity className="w-3.5 h-3.5 text-accent" />
                )}
                <span>Test</span>
              </button>
            </div>

            {testStatus !== 'IDLE' && (
              <div
                className={`text-[11px] px-3 py-2 rounded-sm border flex items-center gap-2 font-mono ${
                  testStatus === 'SUCCESS'
                    ? 'bg-success-dim border-success-muted text-success'
                    : testStatus === 'ERROR'
                    ? 'bg-critical-dim border-critical-muted text-critical'
                    : 'bg-surface-card border-surface-border text-slate-300'
                }`}
              >
                <span className="font-medium">Status:</span>
                <span>{testResult || 'Testing connection...'}</span>
              </div>
            )}

            <div className="flex items-center justify-between text-xs pt-1 font-mono">
              <span className="text-slate-400">Active link state:</span>
              <span
                className={`font-medium px-2 py-0.5 rounded-sm text-[10px] border ${
                  isConnected
                    ? 'bg-success-dim text-success border-success-muted'
                    : 'bg-critical-dim text-critical border-critical-muted'
                }`}
              >
                {isConnected ? 'Connected' : 'Disconnected / waiting'}
              </span>
            </div>
          </div>

          <div className="space-y-1.5 font-mono">
            <span className="text-[10px] uppercase font-medium text-slate-400 tracking-wide">
              Quick target presets
            </span>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setUrl('http://127.0.0.1:8000')}
                className="text-left px-3 py-2 rounded-sm bg-white/[0.02] border border-surface-border hover:border-surface-border-strong hover:bg-white/[0.04] transition-colors text-xs"
              >
                <div className="flex items-center gap-1.5 text-slate-200 font-medium text-[11px]">
                  <Server className="w-3 h-3 text-accent" />
                  <span>Localhost</span>
                </div>
                <div className="text-[10px] text-slate-400 font-mono truncate">http://127.0.0.1:8000</div>
              </button>

              <button
                type="button"
                onClick={() => setUrl('http://192.168.1.20:8000')}
                className="text-left px-3 py-2 rounded-sm bg-white/[0.02] border border-surface-border hover:border-surface-border-strong hover:bg-white/[0.04] transition-colors text-xs"
              >
                <div className="flex items-center gap-1.5 text-slate-200 font-medium text-[11px]">
                  <Wifi className="w-3 h-3 text-accent" />
                  <span>Local Wi-Fi IP</span>
                </div>
                <div className="text-[10px] text-slate-400 font-mono truncate">http://192.168.1.20:8000</div>
              </button>
            </div>
          </div>

          <div className="bg-white/[0.02] p-3.5 rounded-sm border border-surface-border text-xs text-slate-400 space-y-1.5">
            <div className="flex items-center gap-1.5 text-slate-300 font-medium text-[11px] font-mono">
              <HelpCircle className="w-3.5 h-3.5 text-accent" />
              <span>Connection guide</span>
            </div>
            <p>1. <span className="text-slate-300">Laptop browser:</span> use <code className="text-accent font-mono">http://127.0.0.1:8000</code>.</p>
            <p>2. <span className="text-slate-300">Mobile on Wi-Fi:</span> use your laptop LAN IP <code className="text-accent font-mono">http://192.168.1.20:8000</code>.</p>
            <p>3. <span className="text-slate-300">Vercel / cloud / cellular:</span> run <code className="text-accent font-mono">launch_public_tunnel.bat</code> and paste the <code className="text-accent font-mono">https://....ngrok-free.app</code> URL to prevent browser mixed-content blocks.</p>
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
              <span>Save &amp; connect</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
