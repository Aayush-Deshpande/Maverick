import React, { useState } from 'react';

interface DroneAirframe {
  id: string;
  tail: string;
  model: string;
  command: string;
  location: string;
  status: 'AIRBORNE' | 'CAUTION' | 'STANDBY' | 'MAINTENANCE';
  health: number;
  rul: number;
  engine: string;
  coords: { x: number; y: number };
  statusNote: string;
}

const DRONES: DroneAirframe[] = [
  {
    id: 'uav-01',
    tail: 'UAV-01',
    model: 'RUSTOM-II',
    command: 'Northern Command',
    location: 'Leh / FL230',
    status: 'AIRBORNE',
    health: 99.2,
    rul: 450,
    engine: 'Rotax 914 F Turbo',
    coords: { x: 210, y: 70 },
    statusNote: 'Nominal cruise loiter, zero residual drift',
  },
  {
    id: 'uav-02',
    tail: 'UAV-02',
    model: 'TAPAS-BH-201',
    command: 'Western Command',
    location: 'Jodhpur / 1500ft',
    status: 'CAUTION',
    health: 84.1,
    rul: 64,
    engine: 'Austro AE300',
    coords: { x: 130, y: 210 },
    statusNote: 'Intercooler dust loading, core derating 12%',
  },
  {
    id: 'uav-03',
    tail: 'UAV-03',
    model: 'ARCHER-NG',
    command: 'Eastern Command',
    location: 'Tezpur AFS',
    status: 'STANDBY',
    health: 100.0,
    rul: 500,
    engine: 'Rotax 915 iS Turbo',
    coords: { x: 390, y: 190 },
    statusNote: 'Pre-flight digital twin bite checks verified',
  },
  {
    id: 'uav-04',
    tail: 'UAV-04',
    model: 'RUSTOM-II',
    command: 'Depot (3BRD)',
    location: 'Chandigarh',
    status: 'MAINTENANCE',
    health: 68.4,
    rul: 4.2,
    engine: 'VRDE / Jayem 2.2L',
    coords: { x: 190, y: 120 },
    statusNote: 'Cylinder #3 fuel injector nozzle overhaul',
  },
];

export const LandingFleetMap: React.FC = () => {
  const [selectedDrone, setSelectedDrone] = useState<string>('uav-01');

  return (
    <section id="fleet" className="py-24 sm:py-32 px-4 sm:px-6 max-w-7xl mx-auto border-b border-white/[0.08]">
      {/* Header */}
      <div className="space-y-4 max-w-3xl">
        <div className="flex items-center gap-2 text-[11px] font-mono tracking-[0.2em] text-cyan-400 uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          <span>06 / STRATEGIC FLEET PROGNOSTICS</span>
          <span className="text-slate-600">—</span>
          <span>SMRITI FLEET MEMORY</span>
        </div>

        <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-white leading-tight font-display">
          Indian Operational Theatre Fleet Health.{' '}
          <span className="font-editorial italic font-normal text-slate-300">
            Real-time RUL projections across strategic combat commands.
          </span>
        </h2>

        <p className="text-sm sm:text-base text-slate-300 font-sans font-light leading-relaxed">
          SMRITI centralized fleet memory tracking active tactical UAV airframes across Northern, Western, and Eastern operational commands with Remaining Useful Life (RUL) projections.
        </p>
      </div>

      {/* Main Grid: SVG India Map (Left) vs Fleet Cards (Right) */}
      <div className="mt-16 grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Tactical SVG India Map (7 cols) */}
        <div className="lg:col-span-7 p-6 rounded-sm bg-[#0c101a]/90 backdrop-blur border border-white/10 relative overflow-hidden flex flex-col justify-between h-[520px]">
          <div className="flex items-center justify-between border-b border-white/10 pb-3 z-10">
            <span className="text-xs font-bold font-mono uppercase tracking-wider text-white">
              TACTICAL RADAR SURVEILLANCE GRID // THEATRE AIRFRAMES
            </span>
            <span className="text-[10px] font-mono text-cyan-400">4 ACTIVE NODES</span>
          </div>

          {/* SVG Map Canvas */}
          <div className="relative w-full h-[400px] flex items-center justify-center">
            <svg
              className="w-full h-full max-h-[380px]"
              viewBox="0 0 500 550"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Tactical Grid Pattern */}
              <defs>
                <pattern id="tactical-grid-pattern" width="30" height="30" patternUnits="userSpaceOnUse">
                  <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(0, 240, 255, 0.06)" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#tactical-grid-pattern)" />

              {/* Simplified India Border Silhouette Outline */}
              <path
                d="M 180 50 L 220 30 L 260 50 L 280 90 L 250 140 L 290 180 L 380 180 L 410 150 L 430 180 L 370 230 L 310 240 L 290 280 L 270 360 L 230 450 L 210 490 L 200 450 L 160 350 L 140 280 L 100 230 L 130 190 L 160 140 Z"
                fill="rgba(0, 240, 255, 0.03)"
                stroke="rgba(0, 240, 255, 0.35)"
                strokeWidth="1.5"
                strokeDasharray="4 2"
              />

              {/* Bases & Airframe Nodes */}
              {/* UAV-01: Leh */}
              <g
                transform="translate(210, 70)"
                className="cursor-pointer"
                onClick={() => setSelectedDrone('uav-01')}
              >
                <circle r="14" fill="none" stroke="rgba(0, 240, 255, 0.4)" strokeWidth="1">
                  <animate attributeName="r" values="6;16;6" dur="3s" repeatCount="indefinite" />
                </circle>
                <circle r="5" fill="#00f0ff" />
                <text x="16" y="4" fill="#ffffff" fontFamily="monospace" fontSize="10" fontWeight="bold">
                  UAV-01 [LEH / FL230]
                </text>
                <text x="16" y="16" fill="#00f0ff" fontFamily="monospace" fontSize="8">
                  RUL: 450h // NOMINAL
                </text>
              </g>

              {/* UAV-02: Jodhpur */}
              <g
                transform="translate(130, 210)"
                className="cursor-pointer"
                onClick={() => setSelectedDrone('uav-02')}
              >
                <circle r="12" fill="none" stroke="rgba(245, 158, 11, 0.5)" strokeWidth="1">
                  <animate attributeName="r" values="5;14;5" dur="2s" repeatCount="indefinite" />
                </circle>
                <circle r="5" fill="#f59e0b" />
                <text x="16" y="4" fill="#ffffff" fontFamily="monospace" fontSize="10" fontWeight="bold">
                  UAV-02 [THAR / 1500ft]
                </text>
                <text x="16" y="16" fill="#f59e0b" fontFamily="monospace" fontSize="8">
                  RUL: 64h // DUST FOULING
                </text>
              </g>

              {/* UAV-03: Tezpur */}
              <g
                transform="translate(390, 190)"
                className="cursor-pointer"
                onClick={() => setSelectedDrone('uav-03')}
              >
                <circle r="5" fill="#10b981" />
                <text x="-120" y="4" fill="#ffffff" fontFamily="monospace" fontSize="10" fontWeight="bold">
                  UAV-03 [TEZPUR]
                </text>
                <text x="-120" y="16" fill="#10b981" fontFamily="monospace" fontSize="8">
                  RUL: 500h // TARMAC READY
                </text>
              </g>

              {/* UAV-04: Chandigarh */}
              <g
                transform="translate(190, 120)"
                className="cursor-pointer"
                onClick={() => setSelectedDrone('uav-04')}
              >
                <circle r="5" fill="#ef4444" />
                <text x="14" y="4" fill="#ffffff" fontFamily="monospace" fontSize="10" fontWeight="bold">
                  UAV-04 [DEPOT]
                </text>
                <text x="14" y="16" fill="#ef4444" fontFamily="monospace" fontSize="8">
                  RUL: 4.2h // INJECTOR REPAIR
                </text>
              </g>
            </svg>
          </div>

          <div className="flex justify-between items-center text-[10px] font-mono text-slate-500 pt-2 border-t border-white/5 z-10">
            <span>COORDINATE DATUM: WGS-84</span>
            <span className="text-cyan-400">CLICK NODE TO INSPECT AIRFRAME</span>
          </div>
        </div>

        {/* Right: Fleet Airframes List (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-3 justify-between">
          {DRONES.map((drone) => {
            const isSelected = drone.id === selectedDrone;
            let statusPillBg = 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
            let barColor = 'bg-cyan-400';

            if (drone.status === 'CAUTION') {
              statusPillBg = 'bg-amber-500/10 text-amber-400 border-amber-500/30';
              barColor = 'bg-amber-400';
            } else if (drone.status === 'STANDBY') {
              statusPillBg = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
              barColor = 'bg-emerald-400';
            } else if (drone.status === 'MAINTENANCE') {
              statusPillBg = 'bg-red-500/10 text-red-400 border-red-500/30';
              barColor = 'bg-red-400';
            }

            return (
              <div
                key={drone.id}
                onClick={() => setSelectedDrone(drone.id)}
                className={`p-4 rounded-sm bg-[#0c101a]/85 backdrop-blur border transition-all cursor-pointer flex flex-col gap-2 ${
                  isSelected
                    ? 'border-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.2)] bg-[#101726]'
                    : 'border-white/10 hover:border-white/20'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold font-mono text-white">
                      {drone.tail} // {drone.model}
                    </span>
                  </div>
                  <span className={`text-[9px] font-mono px-2 py-0.5 rounded-xs border font-semibold ${statusPillBg}`}>
                    {drone.status}
                  </span>
                </div>

                <div className="text-[11px] font-mono text-slate-400 flex justify-between">
                  <span>{drone.command} ({drone.location})</span>
                  <span className="text-slate-500">{drone.engine}</span>
                </div>

                <div className="flex justify-between items-center text-xs font-mono pt-1">
                  <span>HEALTH: <strong className="text-white">{drone.health}%</strong></span>
                  <span>RUL: <strong className="text-white">{drone.rul} hrs</strong></span>
                </div>

                <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                  <div className={`h-full ${barColor} rounded-full`} style={{ width: `${drone.health}%` }} />
                </div>

                <div className="text-[10px] font-mono text-slate-400 pt-0.5">
                  &bull; {drone.statusNote}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
