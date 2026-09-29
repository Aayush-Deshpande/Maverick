import React, { useEffect, useRef, useState } from 'react';
import { ArrowUpRight } from 'lucide-react';

interface LandingGCSPreviewProps {
  onLaunchConsole?: () => void;
}

export const LandingGCSPreview: React.FC<LandingGCSPreviewProps> = ({ onLaunchConsole }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [telemetry, setTelemetry] = useState({
    rpm: 2350,
    map: 1.95,
    oilTemp: 92.4,
    rail: 1610,
    cht: [138.2, 140.5, 139.1, 141.0],
    egt: [682.0, 688.5, 684.0, 689.2],
    health: 98.4,
    rul: 450.0,
    residual: 0.03,
  });

  // Animated Oscilloscope Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let t = 0;
    const history: number[] = new Array(120).fill(0);

    const render = () => {
      t += 0.05;
      const width = canvas.width;
      const height = canvas.height;

      // Draw subtle noise with physics residual signature
      const noise = (Math.sin(t * 1.5) * 0.04 + Math.sin(t * 4.2) * 0.02 + (Math.random() - 0.5) * 0.025);
      history.shift();
      history.push(noise);

      // Clear
      ctx.fillStyle = 'rgba(6, 9, 15, 0.85)';
      ctx.fillRect(0, 0, width, height);

      // Grid Lines
      ctx.strokeStyle = 'rgba(0, 240, 255, 0.08)';
      ctx.lineWidth = 1;

      // Horizontal center
      const midY = height / 2;
      ctx.beginPath();
      ctx.moveTo(0, midY);
      ctx.lineTo(width, midY);
      ctx.stroke();

      // CUSUM Noise Band (+- 0.20 sigma)
      const bandOffset = height * 0.22;
      ctx.strokeStyle = 'rgba(0, 240, 255, 0.18)';
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(0, midY - bandOffset);
      ctx.lineTo(width, midY - bandOffset);
      ctx.moveTo(0, midY + bandOffset);
      ctx.lineTo(width, midY + bandOffset);
      ctx.stroke();

      // Redline (+- 0.85 sigma)
      const redlineOffset = height * 0.42;
      ctx.strokeStyle = 'rgba(239, 68, 68, 0.28)';
      ctx.beginPath();
      ctx.moveTo(0, midY - redlineOffset);
      ctx.lineTo(width, midY - redlineOffset);
      ctx.moveTo(0, midY + redlineOffset);
      ctx.lineTo(width, midY + redlineOffset);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw Residual Waveform
      ctx.strokeStyle = '#00f0ff';
      ctx.lineWidth = 2;
      ctx.shadowColor = '#00f0ff';
      ctx.shadowBlur = 8;
      ctx.beginPath();

      const step = width / (history.length - 1);
      for (let i = 0; i < history.length; i++) {
        const x = i * step;
        const val = history[i];
        const y = midY - (val / 0.25) * bandOffset;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.shadowBlur = 0;

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  // Subtle telemetry jitter
  useEffect(() => {
    const timer = setInterval(() => {
      setTelemetry((prev) => ({
        ...prev,
        rpm: Math.round(2350 + (Math.random() - 0.5) * 14),
        map: Number((1.95 + (Math.random() - 0.5) * 0.02).toFixed(2)),
        oilTemp: Number((92.4 + (Math.random() - 0.5) * 0.2).toFixed(1)),
        residual: Number((0.03 + (Math.random() - 0.5) * 0.006).toFixed(3)),
      }));
    }, 1200);
    return () => clearInterval(timer);
  }, []);

  return (
    <section id="gcs" className="py-24 sm:py-32 px-4 sm:px-6 max-w-7xl mx-auto border-b border-white/[0.08]">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div className="space-y-4 max-w-2xl">
          <div className="flex items-center gap-2 text-[11px] font-mono tracking-[0.2em] text-cyan-400 uppercase">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span>04 / REAL-TIME COCKPIT TELEMETRY</span>
            <span className="text-slate-600">—</span>
            <span>GCS PREVIEW</span>
          </div>

          <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-white leading-tight font-display">
            Ground Health Console & Oscilloscope.{' '}
            <span className="font-editorial italic font-normal text-slate-300">
              Live physics performance synced at 20 Hz.
            </span>
          </h2>

          <p className="text-sm text-slate-300 font-sans font-light leading-relaxed">
            STANAG-4586 compliant telemetry link streaming 27 FADEC channels, evaluating analytical residuals in real time against the nominal thermodynamic plant.
          </p>
        </div>

        {onLaunchConsole && (
          <button
            onClick={onLaunchConsole}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xs text-xs font-mono font-bold uppercase bg-cyan-400 text-black hover:bg-cyan-300 transition-all shadow-[0_0_20px_rgba(0,240,255,0.3)] shrink-0 self-start md:self-auto"
          >
            <span>LAUNCH FULL RUNTIME CONSOLE</span>
            <ArrowUpRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Top 4 Status Metric Cards (Direct from previous website) */}
      <div className="mt-12 grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 sm:p-5 rounded-sm bg-[#0c101a]/90 border border-cyan-500/30">
          <div className="flex justify-between items-center text-[10px] font-mono text-slate-400">
            <span>PROPULSION STATE</span>
            <span className="text-cyan-400 font-semibold">20 Hz SYNC</span>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-cyan-400 font-mono mt-1">NOMINAL</div>
          <div className="text-[11px] font-mono text-slate-400 mt-1">All cylinders tracking physics model</div>
        </div>

        <div className="p-4 sm:p-5 rounded-sm bg-[#0c101a]/90 border border-cyan-500/30">
          <div className="flex justify-between items-center text-[10px] font-mono text-slate-400">
            <span>TWIN HEALTH INDEX</span>
            <span className="text-cyan-400 font-semibold">BAYESIAN</span>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-cyan-400 font-mono mt-1">
            {telemetry.health}<span className="text-base font-normal text-slate-400">%</span>
          </div>
          <div className="text-[11px] font-mono text-slate-400 mt-1">Expected life degradation rate: 0.02%/h</div>
        </div>

        <div className="p-4 sm:p-5 rounded-sm bg-[#0c101a]/90 border border-cyan-500/30">
          <div className="flex justify-between items-center text-[10px] font-mono text-slate-400">
            <span>ESTIMATED RUL (P50)</span>
            <span className="text-cyan-400 font-semibold">95% CI</span>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-cyan-400 font-mono mt-1">
            {telemetry.rul}<span className="text-base font-normal text-slate-400"> HRS</span>
          </div>
          <div className="text-[11px] font-mono text-slate-400 mt-1">Safe mission margin: +42.0 hrs</div>
        </div>

        <div className="p-4 sm:p-5 rounded-sm bg-[#0c101a]/90 border border-cyan-500/30">
          <div className="flex justify-between items-center text-[10px] font-mono text-slate-400">
            <span>PHYSICS RESIDUAL</span>
            <span className="text-cyan-400 font-semibold">CUSUM</span>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-cyan-400 font-mono mt-1">
            {telemetry.residual}<span className="text-base font-normal text-slate-400"> σ</span>
          </div>
          <div className="text-[11px] font-mono text-slate-400 mt-1">Threshold redline: 0.85 σ</div>
        </div>
      </div>

      {/* Main Grid: Gauges (Left) vs Oscilloscope & Copilot (Right) */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Gauges & CHT/EGT meters (7 cols) */}
        <div className="lg:col-span-7 p-6 rounded-sm bg-[#0c101a]/80 backdrop-blur border border-white/10 space-y-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <span className="text-xs font-bold font-mono uppercase tracking-wider text-white">
              REAL-TIME 20 Hz ENGINE TELEMETRY
            </span>
            <span className="text-[10px] font-mono text-cyan-400">STANAG-4586 LINK</span>
          </div>

          {/* Primary 4 gauges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-xs bg-[#060913] border border-white/5 space-y-0.5">
              <span className="text-[9px] font-mono text-slate-400 uppercase">RPM</span>
              <div className="text-lg font-bold font-mono text-white">{telemetry.rpm.toLocaleString()}</div>
              <span className="text-[9px] font-mono text-slate-500">MCP: 2300-2400</span>
            </div>
            <div className="p-3 rounded-xs bg-[#060913] border border-white/5 space-y-0.5">
              <span className="text-[9px] font-mono text-slate-400 uppercase">MAP (BOOST)</span>
              <div className="text-lg font-bold font-mono text-white">{telemetry.map} <span className="text-xs font-normal text-slate-400">bar</span></div>
              <span className="text-[9px] font-mono text-slate-500">Nominal: 1.8-2.1</span>
            </div>
            <div className="p-3 rounded-xs bg-[#060913] border border-white/5 space-y-0.5">
              <span className="text-[9px] font-mono text-slate-400 uppercase">OIL TEMP</span>
              <div className="text-lg font-bold font-mono text-white">{telemetry.oilTemp} <span className="text-xs font-normal text-slate-400">°C</span></div>
              <span className="text-[9px] font-mono text-slate-500">Limit: 120°C</span>
            </div>
            <div className="p-3 rounded-xs bg-[#060913] border border-white/5 space-y-0.5">
              <span className="text-[9px] font-mono text-slate-400 uppercase">RAIL PRESS</span>
              <div className="text-lg font-bold font-mono text-white">{telemetry.rail} <span className="text-xs font-normal text-slate-400">bar</span></div>
              <span className="text-[9px] font-mono text-slate-500">Max: 1800 bar</span>
            </div>
          </div>

          {/* CHT 1-4 Bars */}
          <div className="space-y-2 pt-2">
            <div className="flex justify-between text-[10px] font-mono text-slate-400">
              <span>CYLINDER HEAD TEMPERATURES (CHT 1-4)</span>
              <span>STATIC REDLINE: 165.0°C</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {telemetry.cht.map((val, idx) => (
                <div key={idx} className="p-3 rounded-xs bg-[#060913] border border-white/5 space-y-1.5">
                  <div className="flex justify-between text-[10px] font-mono text-slate-400">
                    <span>CYL {idx + 1}</span>
                    <span className="text-white font-bold">{val}°C</span>
                  </div>
                  <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-cyan-400 rounded-full transition-all duration-300"
                      style={{ width: `${(val / 165) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* EGT 1-4 Meters */}
          <div className="space-y-2 pt-2">
            <div className="flex justify-between text-[10px] font-mono text-slate-400">
              <span>EXHAUST GAS TEMPERATURES (EGT 1-4)</span>
              <span>STATIC REDLINE: 750.0°C</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {telemetry.egt.map((val, idx) => (
                <div key={idx} className="p-3 rounded-xs bg-[#060913] border border-white/5 flex justify-between items-center">
                  <span className="text-[10px] font-mono text-slate-400">EGT {idx + 1}</span>
                  <span className="text-sm font-bold font-mono text-slate-200">{val}°C</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Oscilloscope & SAARTHI Advisory (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          {/* Oscilloscope Panel */}
          <div className="p-6 rounded-sm bg-[#0c101a]/80 backdrop-blur border border-white/10 space-y-4 flex-1">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <span className="text-xs font-bold font-mono uppercase tracking-wider text-white">
                ANUMAAN RESIDUAL OSCILLOSCOPE
              </span>
              <span className="text-[10px] font-mono text-cyan-400">r = y_meas - y_twin</span>
            </div>

            <div className="h-44 w-full relative bg-[#04060a] rounded border border-white/10 overflow-hidden">
              <canvas
                ref={canvasRef}
                width={400}
                height={176}
                className="w-full h-full block"
              />
            </div>

            <div className="flex justify-between items-center text-[10px] font-mono text-slate-500 pt-1">
              <span>CUSUM RESIDUAL NOISE BAND (&lt; 0.20 σ)</span>
              <span className="text-red-400 font-semibold">REDLINE TRIP: 0.85 σ</span>
            </div>
          </div>

          {/* SAARTHI Copilot Advisory */}
          <div className="p-5 rounded-sm bg-[#0c101a]/90 border border-cyan-500/30 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs font-bold font-mono uppercase text-white">
                  SAARTHI PRESCRIPTIVE COPILOT
                </span>
              </div>
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                ACTIVE ADVISORY
              </span>
            </div>
            <p className="text-xs font-mono text-slate-300 leading-relaxed pt-1">
              ALL SYSTEMS NOMINAL. Digital twin tracking within 99.4% Bayesian confidence bounds. Fuel reserve sufficient for planned 14h loiter over high-altitude patrol sector.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
