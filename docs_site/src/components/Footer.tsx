import React from 'react';

interface FooterProps {
  onNavigate: (path: string) => void;
}

export const Footer: React.FC<FooterProps> = ({ onNavigate }) => {
  return (
    <footer className="w-full border-t border-stone-200 bg-[#f6f5f3] text-stone-700 font-sans">
      <div className="max-w-[1280px] mx-auto bg-stone-100/70 sm:border-x border-stone-200/90 py-12 px-4 sm:px-6 lg:px-12 space-y-10">
        {/* Top Summary Row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 pb-10 border-b border-stone-200">
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <span className="size-2 rounded-full bg-blue-600"></span>
              <span className="font-mono text-xs font-bold text-stone-900 uppercase tracking-widest">
                PROJECT ANUMAAN · PS-26054
              </span>
            </div>
            <p className="text-xs text-stone-600 leading-relaxed max-w-md">
              AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs. Built for DRDO under Smart India Hackathon.
            </p>
            <div className="flex flex-wrap gap-2 pt-1 font-mono text-[10px] text-stone-500 uppercase">
              <span className="border border-stone-300 px-2 py-0.5 rounded bg-white">ISO 13374 / OSA-CBM</span>
              <span className="border border-stone-300 px-2 py-0.5 rounded bg-white">STANAG 4586 LOI 2</span>
              <span className="border border-stone-300 px-2 py-0.5 rounded bg-white">MIL-STD-1629A</span>
            </div>
          </div>

          <div>
            <h4 className="font-mono text-[11px] uppercase tracking-wider text-stone-900 font-semibold mb-3">
              Technical Core
            </h4>
            <ul className="space-y-1.5 text-xs text-stone-600">
              <li>
                <button onClick={() => onNavigate('technical/04-system-architecture')} className="hover:text-stone-950 transition-colors">
                  System Architecture
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('technical/06-engine-physics')} className="hover:text-stone-950 transition-colors">
                  Engine Physics &amp; Combustion
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('technical/10-bio-inspired-sparse-novelty-coding')} className="hover:text-stone-950 transition-colors">
                  FlyHash Sparse Novelty
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('technical/11-fault-diagnosis')} className="hover:text-stone-950 transition-colors">
                  Bayesian Fault Diagnosis
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('technical/14-remaining-useful-life')} className="hover:text-stone-950 transition-colors">
                  RUL &amp; Conformal Bounds
                </button>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-mono text-[11px] uppercase tracking-wider text-stone-900 font-semibold mb-3">
              Mission &amp; Validation
            </h4>
            <ul className="space-y-1.5 text-xs text-stone-600">
              <li>
                <button onClick={() => onNavigate('technical/16-mission-planning')} className="hover:text-stone-950 transition-colors">
                  Mission Executive State Machine
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('technical/17-mission-reliability')} className="hover:text-stone-950 transition-colors">
                  Monte Carlo Reliability R(t)
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('technical/15-dataset-strategy')} className="hover:text-stone-950 transition-colors">
                  Dataset Strategy &amp; Benchmarks
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('journey/01-the-engineering-story')} className="hover:text-stone-950 transition-colors">
                  SIH Journey &amp; Self-Corrections
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('journey/02-preparing-for-evaluation')} className="hover:text-stone-950 transition-colors">
                  Judge Defense &amp; Verification
                </button>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Metadata & Legal */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-[11px] font-mono text-stone-500">
          <div>
            <span>Team Midnight Ciphers · Smart India Hackathon PS-26054</span>
            <span className="mx-2 text-stone-300">·</span>
            <span>Defence Research and Development Organisation</span>
          </div>
          <div>
            <span>Zero Em-Dashes · Verified Repository Ground Truth · Defense-Grade Specs</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
