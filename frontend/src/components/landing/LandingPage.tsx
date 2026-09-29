import React from 'react';
import { ArrowUpRight, Radio, Activity, Zap } from 'lucide-react';
import { LandingNav } from './LandingNav';
import { LandingTicker } from './LandingTicker';
import { LandingHero3D } from './LandingHero3D';
import { LandingProblem } from './LandingProblem';
import { LandingPillars } from './LandingPillars';
import { LandingTwin } from './LandingTwin';
import { LandingDetection } from './LandingDetection';
import { LandingPrognosis } from './LandingPrognosis';
import { LandingTheatres } from './LandingTheatres';
import { LandingFleetMap } from './LandingFleetMap';
import { LandingArchitecture } from './LandingArchitecture';
import { LandingMatrix } from './LandingMatrix';
import { LandingGCSPreview } from './LandingGCSPreview';
import { LandingExploreCTA } from './LandingExploreCTA';
import { LandingFooter } from './LandingFooter';
import './landing.css';

interface LandingPageProps {
  onLaunchConsole?: (target?: 'runtime' | 'twin' | 'legacy') => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onLaunchConsole }) => {
  return (
    <div className="an-page text-slate-100 bg-[#080d12] min-h-screen">
      {/* Top Telemetry Ticker */}
      <LandingTicker />

      {/* Main Navigation Header */}
      <LandingNav onLaunch={onLaunchConsole} />

      <main>
        {/* 3D Model View Hero Section */}
        <section id="hero" className="relative pt-10 pb-16 px-4 sm:px-6 lg:px-12 max-w-7xl mx-auto border-b border-white/[0.08]">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 items-center">
            
            {/* Left Headline & Mission Pitch */}
            <div className="lg:col-span-5 space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-sm bg-accent/15 border border-accent/30 text-accent font-mono text-[11px] tracking-widest uppercase">
                <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                DRDO SIH 26054 · CYBER-PHYSICAL TWIN
              </div>

              <h1 className="text-3xl sm:text-5xl lg:text-5xl font-extrabold tracking-tight text-white leading-[1.08] font-mono">
                Real-Time 3D Digital Twin for{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-sky-300 to-white">
                  Aero-Piston UAV Propulsion
                </span>
              </h1>

              <p className="text-sm sm:text-base text-slate-300 font-sans font-light leading-relaxed">
                Physics-anchored state estimation, high-frequency 20 Hz FADEC telemetry ingestion, and conformal prognostic health monitoring for strategic MALE UAVs operating across extreme Indian frontier theaters.
              </p>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <button
                  onClick={() => onLaunchConsole?.('legacy')}
                  className="px-5 py-2.5 rounded-sm bg-accent hover:bg-accent/80 text-white font-mono text-xs font-semibold tracking-wide flex items-center gap-2 shadow-lg transition-all"
                >
                  <Activity className="w-4 h-4" />
                  Launch Tactical GCS <ArrowUpRight className="w-4 h-4" />
                </button>
                <button
                  onClick={() => onLaunchConsole?.('runtime')}
                  className="px-5 py-2.5 rounded-sm bg-white/5 hover:bg-white/10 text-slate-200 border border-white/15 font-mono text-xs font-medium tracking-wide flex items-center gap-2 transition-all"
                >
                  <Zap className="w-4 h-4 text-cyan-400" />
                  Open Engine Runtime <ArrowUpRight className="w-4 h-4" />
                </button>
                <button
                  onClick={() => onLaunchConsole?.('twin')}
                  className="px-5 py-2.5 rounded-sm bg-cyan-950/40 hover:bg-cyan-900/50 text-cyan-300 border border-cyan-500/30 font-mono text-xs font-medium tracking-wide flex items-center gap-2 transition-all"
                >
                  <Radio className="w-4 h-4 text-cyan-400" />
                  Interactive 3D Twin <ArrowUpRight className="w-4 h-4" />
                </button>
              </div>

              {/* Quick Spec Metrics Pill Row */}
              <div className="grid grid-cols-3 gap-3 pt-4 border-t border-white/10">
                <div className="space-y-0.5">
                  <div className="text-[10px] font-mono text-slate-500 uppercase">TELEMETRY</div>
                  <div className="text-sm font-mono font-bold text-white">20 Hz CAN</div>
                  <div className="text-[9px] text-cyan-400 font-mono">Jitter &lt; 2 ms</div>
                </div>
                <div className="space-y-0.5">
                  <div className="text-[10px] font-mono text-slate-500 uppercase">MODELS</div>
                  <div className="text-sm font-mono font-bold text-white">4 Powerplants</div>
                  <div className="text-[9px] text-cyan-400 font-mono">Rotax + TB3 MALE</div>
                </div>
                <div className="space-y-0.5">
                  <div className="text-[10px] font-mono text-slate-500 uppercase">EARLY WARNING</div>
                  <div className="text-sm font-mono font-bold text-white">4.2 Hours</div>
                  <div className="text-[9px] text-emerald-400 font-mono">vs 0 min threshold</div>
                </div>
              </div>
            </div>

            {/* Right Interactive 3D Model View Showcase */}
            <div className="lg:col-span-7">
              <div className="rounded-sm border border-white/15 bg-[#0b1016] shadow-2xl overflow-hidden p-2 sm:p-3">
                <LandingHero3D
                  onLaunchConsole={() => onLaunchConsole?.('runtime')}
                  onExploreTwin={() => onLaunchConsole?.('twin')}
                />
              </div>
            </div>

          </div>
        </section>

        {/* Section 02: Operational Pitch & Mission Challenge */}
        <LandingProblem />

        {/* Section 03: 6 Platform Pillars (NADI, TATTVA, VIMARSHA, BODHA, KOSH, YATRA) */}
        <LandingPillars />

        {/* Section 04: Digital Twin Physics & State Estimation */}
        <LandingTwin />

        {/* Section 05: Multi-Tier Anomaly Isolation */}
        <LandingDetection />

        {/* Section 06: Conformal Remaining Useful Life (RUL) */}
        <LandingPrognosis />

        {/* Section 07: Extreme Flight Theatres (Ladakh & Thar) */}
        <LandingTheatres />

        {/* Section 08: Strategic Fleet Command Map */}
        <LandingFleetMap />

        {/* Section 09: 6-Layer Cyber-Physical Architecture */}
        <LandingArchitecture />

        {/* Section 10: DRDO PS-26054 Requirements Compliance Matrix */}
        <LandingMatrix />

        {/* Section 11: Tactical GCS Cockpit Preview with Oscilloscope */}
        <LandingGCSPreview onLaunchConsole={() => onLaunchConsole?.('legacy')} />

        {/* Section 12: Direct Platform Access & Console Launch Portals */}
        <LandingExploreCTA onLaunch={onLaunchConsole} />
      </main>

      {/* Footer */}
      <LandingFooter onLaunch={onLaunchConsole} />
    </div>
  );
};

export default LandingPage;
