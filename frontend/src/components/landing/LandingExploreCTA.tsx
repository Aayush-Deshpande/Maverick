import React from 'react';
import { ArrowUpRight, Activity, Eye, Shield } from 'lucide-react';

interface LandingExploreCTAProps {
  onLaunchConsole?: () => void;
  onOpenTwin?: () => void;
  onOpenLegacy?: () => void;
  onLaunch?: (target?: 'runtime' | 'twin' | 'legacy') => void;
}

export const LandingExploreCTA: React.FC<LandingExploreCTAProps> = ({
  onLaunchConsole,
  onOpenTwin,
  onOpenLegacy,
  onLaunch,
}) => {
  const handleLaunchConsole = () => {
    if (onLaunchConsole) onLaunchConsole();
    else if (onLaunch) onLaunch('runtime');
  };
  const handleOpenTwin = () => {
    if (onOpenTwin) onOpenTwin();
    else if (onLaunch) onLaunch('twin');
  };
  const handleOpenLegacy = () => {
    if (onOpenLegacy) onOpenLegacy();
    else if (onLaunch) onLaunch('legacy');
  };
  return (
    <section id="explore" className="py-24 sm:py-32 px-4 sm:px-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="space-y-4 max-w-3xl">
        <div className="flex items-center gap-2 text-[11px] font-mono tracking-[0.2em] text-accent uppercase">
          <span>08 / PLATFORM ACCESS</span>
          <span className="text-slate-600">—</span>
          <span>EXPLORE THE ACTIVE SYSTEM</span>
        </div>

        <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-white leading-tight font-mono">
          Engineered for mission readiness.{' '}
          <span className="font-editorial italic font-normal text-slate-300">
            Direct operational access to the complete digital twin testbed.
          </span>
        </h2>

        <p className="text-sm sm:text-base text-slate-400 font-mono leading-relaxed">
          Transition from theoretical system architecture to the live operational environment. Explore live 20 Hz FADEC telemetry, inject flight fault scenarios, inspect high-resolution CAD components, or review condition-based maintenance logs.
        </p>
      </div>

      {/* 3 Major Portals Into The Existing System */}
      <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Portal 1: Live Engine Runtime Console */}
        <div className="p-6 rounded-sm bg-[#0c121e] border border-accent/40 flex flex-col justify-between space-y-6 hover:border-accent transition-all group">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="w-9 h-9 rounded-xs bg-accent/20 border border-accent/40 flex items-center justify-center text-accent">
                <Activity className="w-5 h-5" />
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-xs bg-accent/15 text-accent border border-accent/30">
                ACTIVE · 20 Hz
              </span>
            </div>

            <div>
              <h3 className="text-base font-bold text-white font-mono uppercase tracking-wide">
                ENGINE RUNTIME CONSOLE
              </h3>
              <p className="text-xs font-mono text-slate-400 mt-2 leading-relaxed">
                Connect to the live thermodynamic simulation. Adjust throttle, altitude, and ambient air sliders in real time, trigger profile-valid physical engine faults, and observe Tier-0 detector innovations.
              </p>
            </div>

            <div className="space-y-1.5 pt-2 border-t border-white/5 text-[11px] font-mono text-slate-400">
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                <span>27 Live FADEC Channels</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                <span>Mahalanobis Anomaly Tracker</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                <span>Multi-Engine Switching (Rotax &amp; VRDE)</span>
              </div>
            </div>
          </div>

          <button
            onClick={handleLaunchConsole}
            className="w-full py-2.5 px-4 rounded-xs bg-accent text-black font-mono text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 hover:bg-accent/90 transition-all shadow-md"
          >
            <span>LAUNCH RUNTIME CONSOLE</span>
            <ArrowUpRight className="w-4 h-4" />
          </button>
        </div>

        {/* Portal 2: Interactive 3D Digital Twin */}
        <div className="p-6 rounded-sm bg-[#0c121e] border border-white/15 flex flex-col justify-between space-y-6 hover:border-white/30 transition-all group">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="w-9 h-9 rounded-xs bg-white/5 border border-white/10 flex items-center justify-center text-white">
                <Eye className="w-5 h-5" />
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-xs bg-white/5 text-slate-400 border border-white/10">
                WEBGL 3D TWIN
              </span>
            </div>

            <div>
              <h3 className="text-base font-bold text-white font-mono uppercase tracking-wide">
                INTERACTIVE 3D TWIN
              </h3>
              <p className="text-xs font-mono text-slate-400 mt-2 leading-relaxed">
                Full-scale 3D WebGL digital twin with instant in-memory model swapping across all 5 engine configurations. Inspect components, toggle ghost X-ray shaders, and execute camera transitions.
              </p>
            </div>

            <div className="space-y-1.5 pt-2 border-t border-white/5 text-[11px] font-mono text-slate-400">
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span>Subsystem Mesh Dissection</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span>Synchronized RPM Shaft Drive</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span>Diagnostic Fault Illumination</span>
              </div>
            </div>
          </div>

          <button
            onClick={handleOpenTwin}
            className="w-full py-2.5 px-4 rounded-xs bg-white/10 text-white font-mono text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 hover:bg-white/20 transition-all border border-white/10"
          >
            <span>EXPLORE 3D DIGITAL TWIN</span>
            <ArrowUpRight className="w-4 h-4" />
          </button>
        </div>

        {/* Portal 3: Tactical Ground Station */}
        <div className="p-6 rounded-sm bg-[#0c121e] border border-white/15 flex flex-col justify-between space-y-6 hover:border-white/30 transition-all group">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="w-9 h-9 rounded-xs bg-white/5 border border-white/10 flex items-center justify-center text-white">
                <Shield className="w-5 h-5" />
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-xs bg-white/5 text-slate-400 border border-white/10">
                TACTICAL GCS HMI
              </span>
            </div>

            <div>
              <h3 className="text-base font-bold text-white font-mono uppercase tracking-wide">
                OPERATIONAL GCS CONSOLE
              </h3>
              <p className="text-xs font-mono text-slate-400 mt-2 leading-relaxed">
                Multi-role ground station console providing tailored telemetry displays for tactical operators, propulsion engineers, and depot maintenance crew, complete with AI copilot and mission replay.
              </p>
            </div>

            <div className="space-y-1.5 pt-2 border-t border-white/5 text-[11px] font-mono text-slate-400">
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span>Role-Based Tactical HMIs</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span>Voice Copilot &amp; RAG Reasoning</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span>Historical Mission Replay Scrubber</span>
              </div>
            </div>
          </div>

          <button
            onClick={handleOpenLegacy}
            className="w-full py-2.5 px-4 rounded-xs bg-white/10 text-white font-mono text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 hover:bg-white/20 transition-all border border-white/10"
          >
            <span>ENTER GROUND STATION</span>
            <ArrowUpRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </section>
  );
};
