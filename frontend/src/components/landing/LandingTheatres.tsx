import React from 'react';
import { Mountain, Sun } from 'lucide-react';

export const LandingTheatres: React.FC = () => {
  return (
    <section id="theatres" className="py-24 sm:py-32 px-4 sm:px-6 max-w-7xl mx-auto border-b border-white/[0.08]">
      {/* Header */}
      <div className="space-y-4 max-w-3xl">
        <div className="flex items-center gap-2 text-[11px] font-hud tracking-[0.2em] text-cyan-400 uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          <span>05 / HIGH-FIDELITY FLIGHT ENVELOPE BENCHMARKS</span>
          <span className="text-slate-600">—</span>
          <span>OPERATIONAL THEATRES</span>
        </div>

        <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-white leading-tight font-display">
          Extreme Environmental Operational Theatres.{' '}
          <span className="font-editorial italic font-normal text-slate-300">
            Validated from sub-zero Himalayan loiter to Thar desert heat soak.
          </span>
        </h2>

        <p className="text-sm sm:text-base text-slate-300 font-sans font-light leading-relaxed">
          Comparing digital twin response and residual divergence across India's two most demanding tactical theatres: the sub-zero high-altitude Himalayan frontier and the extreme thermal desert.
        </p>
      </div>

      {/* Side-by-side Theatres Grid */}
      <div className="mt-16 grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Ladakh Sector Card */}
        <div className="p-6 sm:p-8 rounded-sm bg-[#080b11] border border-cyan-500/40 border-t-2 border-t-cyan-400 space-y-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xs bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                  <Mountain className="w-4 h-4" />
                </div>
                <h3 className="text-base font-bold font-hud text-white tracking-wider uppercase">
                  LADAKH SECTOR // HIGH ALTITUDE LOITER
                </h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-xs bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                FL230 / SUB-ZERO
              </span>
            </div>

            <p className="text-xs sm:text-sm font-sans font-light text-slate-300 leading-relaxed">
              FL230 loiter over Siachen Glacier. Ambient temperature is -35°C, but extreme turbo compression ratio heats intake air to +110°C, driving internal combustion flame temperatures past the limit while exterior cowl air cools thermocouples.
            </p>

            {/* Specs Grid */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <div className="p-3 rounded-xs bg-[#05070c] border border-white/5 space-y-0.5">
                <span className="text-[9px] font-hud text-slate-400 uppercase tracking-wider">ALTITUDE</span>
                <div className="text-sm font-bold font-mono text-cyan-400">23,000 FT MSL</div>
              </div>
              <div className="p-3 rounded-xs bg-[#05070c] border border-white/5 space-y-0.5">
                <span className="text-[9px] font-hud text-slate-400 uppercase tracking-wider">AMBIENT TEMP</span>
                <div className="text-sm font-bold font-mono text-cyan-400">-35.0 °C</div>
              </div>
              <div className="p-3 rounded-xs bg-[#05070c] border border-white/5 space-y-0.5">
                <span className="text-[9px] font-hud text-slate-400 uppercase tracking-wider">INTAKE BOOST</span>
                <div className="text-sm font-bold font-mono text-cyan-400">2.18 BAR (TURBO)</div>
              </div>
              <div className="p-3 rounded-xs bg-[#05070c] border border-white/5 space-y-0.5">
                <span className="text-[9px] font-hud text-slate-400 uppercase tracking-wider">TWIN RESIDUAL</span>
                <div className="text-sm font-bold font-mono text-cyan-400">0.04 σ (NOMINAL)</div>
              </div>
            </div>
          </div>

          <div className="p-3.5 rounded-xs bg-cyan-950/20 border-l-2 border-cyan-400 border-t border-r border-b border-white/5 text-xs font-mono text-slate-300 space-y-1">
            <span className="text-cyan-400 font-bold uppercase tracking-wider text-[11px] font-hud">
              TATTVA Aerothermal Observer:
            </span>
            <p className="leading-relaxed font-sans text-xs text-slate-300 font-light">
              Compensates for ram-air density variations using altitude-adjusted Woschni coefficients, preventing false-safe readings from cold outside air fooling standard probes.
            </p>
          </div>
        </div>

        {/* Thar Desert Card */}
        <div className="p-6 sm:p-8 rounded-sm bg-[#080b11] border border-amber-500/40 border-t-2 border-t-amber-400 space-y-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xs bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
                  <Sun className="w-4 h-4" />
                </div>
                <h3 className="text-base font-bold font-hud text-white tracking-wider uppercase">
                  THAR DESERT // LOW-LEVEL HIGH-HEAT RECON
                </h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-xs bg-amber-500/10 text-amber-400 border border-amber-500/20">
                1500 FT / THERMAL SOAK
              </span>
            </div>

            <p className="text-xs sm:text-sm font-sans font-light text-slate-300 leading-relaxed">
              Low-level reconnaissance at 1,500 ft AGL in +52°C ambient heat with severe airborne dust concentration. High ambient temperature reduces intercooler and radiator heat rejection by 45%.
            </p>

            {/* Specs Grid */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <div className="p-3 rounded-xs bg-[#05070c] border border-white/5 space-y-0.5">
                <span className="text-[9px] font-hud text-slate-400 uppercase tracking-wider">ALTITUDE</span>
                <div className="text-sm font-bold font-mono text-amber-400">1,500 FT AGL</div>
              </div>
              <div className="p-3 rounded-xs bg-[#05070c] border border-white/5 space-y-0.5">
                <span className="text-[9px] font-hud text-slate-400 uppercase tracking-wider">AMBIENT TEMP</span>
                <div className="text-sm font-bold font-mono text-amber-400">+52.0 °C</div>
              </div>
              <div className="p-3 rounded-xs bg-[#05070c] border border-white/5 space-y-0.5">
                <span className="text-[9px] font-hud text-slate-400 uppercase tracking-wider">DUST LOADING</span>
                <div className="text-sm font-bold font-mono text-amber-400">HEAVY PARTICULATE</div>
              </div>
              <div className="p-3 rounded-xs bg-[#05070c] border border-white/5 space-y-0.5">
                <span className="text-[9px] font-hud text-slate-400 uppercase tracking-wider">CORE REJECTION</span>
                <div className="text-sm font-bold font-mono text-amber-400">-45% DERATING</div>
              </div>
            </div>
          </div>

          <div className="p-3.5 rounded-xs bg-amber-950/20 border-l-2 border-amber-400 border-t border-r border-b border-white/5 text-xs font-mono text-slate-300 space-y-1">
            <span className="text-amber-400 font-bold uppercase tracking-wider text-[11px] font-hud">
              SAARTHI Prescriptive Action:
            </span>
            <p className="leading-relaxed font-sans text-xs text-slate-300 font-light">
              Automatically calculates minimum altitude step-climb to find cooler thermal inversion layers and prevents sudden oil thermal breakdown before piston ring seizure.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default LandingTheatres;
