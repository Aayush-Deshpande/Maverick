import React from 'react';
import { Database, Activity, Cpu, Brain, HardDrive, Compass } from 'lucide-react';

interface Pillar {
  id: string;
  name: string;
  devanagari: string;
  role: string;
  tagline: string;
  icon: React.ElementType;
  accentColor: string;
  borderColor: string;
  items: { title: string; desc: string }[];
}

const PILLARS: Pillar[] = [
  {
    id: 'nadi',
    name: 'NADI',
    devanagari: 'नाडी',
    role: 'Telemetry Ingestion',
    tagline: 'High-Frequency CAN Bus Signal Conditioning & Ingestion',
    icon: Database,
    accentColor: 'text-cyan-400',
    borderColor: 'border-cyan-500/30 hover:border-cyan-400/80',
    items: [
      {
        title: '20 Hz CAN-Aerospace Bus',
        desc: 'Synchronous ingestion of 27 primary FADEC telemetry channels with hardware jitter < 2ms.',
      },
      {
        title: '2.5 kHz Vibration FFT',
        desc: 'Piezoelectric accelerometer processing for bearing, valvetrain, and reduction gear harmonics.',
      },
      {
        title: 'Bayesian Sensor Validation',
        desc: 'Cross-channel analytical redundancy isolating faulty sensors from real mechanical faults.',
      },
    ],
  },
  {
    id: 'tattva',
    name: 'TATTVA',
    devanagari: 'तत्त्व',
    role: 'Physics Twin',
    tagline: '1D Thermodynamic Gas Dynamics & First-Principles Engine Model',
    icon: Activity,
    accentColor: 'text-sky-400',
    borderColor: 'border-sky-500/30 hover:border-sky-400/80',
    items: [
      {
        title: 'Double-Wiebe Combustion',
        desc: 'High-precision mass fraction burned modeling for Jet-A1 heavy-fuel turbodiesel cycles.',
      },
      {
        title: 'Woschni Heat Transfer',
        desc: 'Dynamic cylinder wall heat flux calculation adapted for altitude density from FL0 to FL300.',
      },
      {
        title: '2-Stage Sequential Turbo Map',
        desc: 'Non-linear compressor pressure ratio and turbine expansion modeling with wastegate dynamics.',
      },
    ],
  },
  {
    id: 'anumaan',
    name: 'ANUMAAN',
    devanagari: 'अनुमान',
    role: 'State Estimator',
    tagline: 'Unscented Kalman Filter (UKF) & Physics Residual Generator',
    icon: Cpu,
    accentColor: 'text-emerald-400',
    borderColor: 'border-emerald-500/30 hover:border-emerald-400/80',
    items: [
      {
        title: 'Dynamic Residual Vector',
        desc: 'r(t) = y_meas(t) - y_twin(t) computed in real-time across 12 aerothermal state dimensions.',
      },
      {
        title: 'Adaptive Covariance (Q & R)',
        desc: 'Dynamically scales Kalman gain during aggressive throttle maneuvers to eliminate false alarms.',
      },
      {
        title: 'CUSUM Change Detection',
        desc: 'Cumulative sum statistical test detecting insidious low-slope drift invisible to raw thresholds.',
      },
    ],
  },
  {
    id: 'kalpana',
    name: 'KALPANA',
    devanagari: 'कल्पना',
    role: 'Prognostics & RUL',
    tagline: 'Physics-Informed Neural Network (PINN) & Remaining Useful Life',
    icon: Brain,
    accentColor: 'text-amber-400',
    borderColor: 'border-amber-500/30 hover:border-amber-400/80',
    items: [
      {
        title: 'Physics-Constrained PINN',
        desc: 'Embeds Paris-Erdogan crack growth & Arrhenius thermal degradation laws directly into neural loss.',
      },
      {
        title: '500-Particle Monte Carlo Filter',
        desc: 'Projects probabilistic RUL distribution with 5th, 50th, and 95th percentile confidence bounds.',
      },
      {
        title: 'Mission-Adaptive Aging',
        desc: 'RUL dynamically updates based on whether the aircraft is loitering at FL230 or climbing.',
      },
    ],
  },
  {
    id: 'smriti',
    name: 'SMRITI',
    devanagari: 'स्मृति',
    role: 'Fleet Knowledge Graph',
    tagline: 'Fleet Historical Memory & ATA-72/73 Maintenance Ontology',
    icon: HardDrive,
    accentColor: 'text-purple-400',
    borderColor: 'border-purple-500/30 hover:border-purple-400/80',
    items: [
      {
        title: 'ATA-72/73 Ontology',
        desc: 'Formalized knowledge graph of failure modes, symptoms, and maintenance shop visit records.',
      },
      {
        title: 'Vector Memory Embeddings',
        desc: 'Matches in-flight anomalous telemetry signatures against historical fleet failure trajectories.',
      },
      {
        title: 'Post-Flight Auto-Debrief',
        desc: 'Generates automated engineering discrepancy reports and turnaround parts requests upon landing.',
      },
    ],
  },
  {
    id: 'saarthi',
    name: 'SAARTHI',
    devanagari: 'सारथी',
    role: 'Prescriptive Copilot',
    tagline: 'Autonomous Decision Support & Terrain-Aware Gliding Corridor',
    icon: Compass,
    accentColor: 'text-red-400',
    borderColor: 'border-red-500/30 hover:border-red-400/80',
    items: [
      {
        title: 'Adaptive Throttle Derating',
        desc: 'Prescribes safe power envelopes (e.g. 65% MCP) to arrest thermal runaway while maintaining flight.',
      },
      {
        title: 'Terrain-Aware Glide Cone',
        desc: 'Computes 3D safe divert glide corridors to nearest FOB considering mountains & wind.',
      },
      {
        title: 'Human-in-the-Loop Cockpit',
        desc: 'Clear, unambiguous tactical recommendations presented to GCS operators with time-to-act timers.',
      },
    ],
  },
];

export const LandingPillars: React.FC = () => {
  return (
    <section id="pillars" className="py-24 sm:py-32 px-4 sm:px-6 max-w-7xl mx-auto border-b border-white/[0.08]">
      {/* Header */}
      <div className="space-y-4 max-w-3xl">
        <div className="flex items-center gap-2 text-[11px] font-hud tracking-[0.2em] text-cyan-400 uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          <span>03 / THE 6 ARCHITECTURAL PILLARS</span>
          <span className="text-slate-600">—</span>
          <span>SYSTEM ARCHITECTURE</span>
        </div>

        <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-white leading-tight font-display">
          End-to-End Aerospace Digital Twin Pipeline.{' '}
          <span className="font-editorial italic font-normal text-slate-300">
            Deterministic physics from CAN bus signal to prescriptive diversion.
          </span>
        </h2>

        <p className="text-sm sm:text-base text-slate-300 font-sans font-light leading-relaxed">
          From hardware CAN bus signal conditioning to autonomous prescriptive terrain-aware glide slope calculation, ANUMAAN is partitioned into six deterministic layers conforming to DO-178C / DO-254 standards.
        </p>
      </div>

      {/* 6 Pillars Grid */}
      <div className="mt-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {PILLARS.map((pillar) => {
          const Icon = pillar.icon;
          return (
            <div
              key={pillar.id}
              className={`p-6 sm:p-7 rounded-sm bg-[#080b11] border ${pillar.borderColor} hover:bg-[#0c1017] transition-all duration-300 flex flex-col justify-between space-y-6 relative group`}
            >
              <div className="space-y-4">
                {/* Card Header */}
                <div className="flex items-baseline justify-between border-b border-white/10 pb-3">
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-4 h-4 ${pillar.accentColor}`} />
                    <span className="text-lg sm:text-xl font-bold text-white font-hud tracking-wider uppercase">
                      {pillar.name}
                    </span>
                    <span className="brand-devanagari text-base font-normal text-slate-400">
                      {pillar.devanagari}
                    </span>
                  </div>
                  <span className={`text-[10px] font-hud uppercase tracking-wider font-semibold ${pillar.accentColor}`}>
                    {pillar.role}
                  </span>
                </div>

                {/* Tagline */}
                <p className="text-xs font-sans text-slate-200 font-medium leading-snug">
                  {pillar.tagline}
                </p>

                {/* Sub-pillars list */}
                <div className="space-y-3 pt-2">
                  {pillar.items.map((item, idx) => (
                    <div key={idx} className="space-y-0.5">
                      <div className="text-[11px] font-hud tracking-wide font-bold text-white flex items-center gap-1.5">
                        <span className={`w-1 h-1 rounded-full ${pillar.accentColor.replace('text-', 'bg-')}`} />
                        <span>{item.title}</span>
                      </div>
                      <p className="text-[11px] font-sans font-light text-slate-300 leading-normal pl-2.5">
                        {item.desc}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Footer Indicator */}
              <div className="pt-3 border-t border-white/5 flex items-center justify-between text-[10px] font-mono text-slate-500">
                <span>DO-178C LEVEL B</span>
                <span className={`${pillar.accentColor}`}>DETERMINISTIC // EDGE</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default LandingPillars;
