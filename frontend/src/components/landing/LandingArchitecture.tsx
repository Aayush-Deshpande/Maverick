import React, { useState } from 'react';
import { ChevronDown, CheckCircle2 } from 'lucide-react';

interface LayerItem {
  id: number;
  code: string;
  name: string;
  standard: string;
  desc: string;
  subsystems: string[];
}

const SYSTEM_LAYERS: LayerItem[] = [
  {
    id: 1,
    code: 'LAYER 01',
    name: 'PHYSICAL PLANT & AVIONICS SENSORS',
    standard: 'MIL-STD-1553 / ARINC-429 / CANaerospace',
    desc: 'Physical Rotax 912 iS / 914 / 915 iS aero-piston powerplants instrumented with dual FADEC lanes, high-rate vibration accelerometers, high-pressure fuel sensors, thermocouple arrays, and manifold absolute pressure transducers.',
    subsystems: ['Lane A/B FADEC', '4x CHT & 4x EGT Thermocouples', 'High-Rate Vibration Pickups (2 kHz)', 'Fuel Flow & Rail Pressure'],
  },
  {
    id: 2,
    code: 'LAYER 02',
    name: 'ONBOARD REAL-TIME EDGE OBSERVER',
    standard: 'DO-178C DAL-C / MISRA-C++ Compliant',
    desc: 'Deterministic embedded edge processor mounted inside the UAV avionics bay. Operates the 0D thermofluid baseline model and fast Tier-0 residual filter at 20 Hz, ensuring autonomy even during total RF datalink loss.',
    subsystems: ['Embedded C++ State Observer', 'CAN Bus Frame Parsing', 'Edge Innovation Filter', 'Fault Telemetry Buffering'],
  },
  {
    id: 3,
    code: 'LAYER 03',
    name: 'SECURE TACTICAL DATALINK',
    standard: 'STANAG 4586 / MIL-STD-188-220 Telemetry Protocol',
    desc: 'C-band/Ku-band line-of-sight and SATCOM datalink channels transmitting high-density compressed telemetry frames between UAV edge flight computer and Ground Control Station with cryptographic integrity verification.',
    subsystems: ['STANAG 4586 Telemetry Packing', 'Dynamic Bandwidth Adaptation', 'AES-256 Link Encryption', 'Sub-100ms Transmission Budget'],
  },
  {
    id: 4,
    code: 'LAYER 04',
    name: 'GROUND DIGITAL TWIN CORE',
    standard: 'High-Performance Asynchronous Python / UKF',
    desc: 'Full-physics state observer on the GCS workstation executing the Unscented Kalman Filter, 3-way fault attribution tests, and continuous virtual sensor thermofluid synthesis mirroring the airborne plant in real time.',
    subsystems: ['Thermofluid State Observer', 'Virtual Sensor Synthesis (TIT, P_max, h_min)', 'Innovation Covariance Tracking', '3-Way Attribution (NIS Chi-Sq)'],
  },
  {
    id: 5,
    code: 'LAYER 05',
    name: 'ANOMALY & PROGNOSTICS ANALYTICS',
    standard: 'Extreme Value Theory & Conformal Prediction',
    desc: 'Statistical multi-channel Mahalanobis evaluation, Echo State Network (ESN) reservoir computing for candidate fault isolation, and Conformal Prediction intervals calculating component Remaining Useful Life.',
    subsystems: ['Mahalanobis Distance Tracker', 'Reservoir Fault Classifier', 'Paris-Erdogan Damage Model', 'Conformal P10/P50/P90 Bounds'],
  },
  {
    id: 6,
    code: 'LAYER 06',
    name: 'OPERATIONAL GCS HMI & PILOT DECISION SUPPORT',
    standard: 'MIL-STD-1472 / Dual-Role Tactical Console',
    desc: 'High-contrast, distraction-free cockpit displays for tactical pilots and dedicated deep-dive panels for propulsion engineers. Incorporates the SAARTHI operational copilot and real-time glide range diversion maps.',
    subsystems: ['Tactical Flight Deck', 'Propulsion Engineer Console', 'Condition-Based Maintenance (CBM)', 'Tactical Glide Polar Map'],
  },
  {
    id: 7,
    code: 'LAYER 07',
    name: 'FLEET INTELLIGENCE & CROSS-BASE FEDERATED LEARNING',
    standard: 'Privacy-Preserving Federated Averaging (FedAvg)',
    desc: 'Aggregates degradation insights, edge model weights, and calibration matrices across geographically dispersed airbases and VRDE test facilities without transmitting raw operational sortie data over public networks.',
    subsystems: ['Decentralized Local Model Training', 'Encrypted Gradient Aggregation', 'Base-to-Depot Fleet Insights', 'VRDE Engine Bench Synchronization'],
  },
];

export const LandingArchitecture: React.FC = () => {
  const [expandedLayer, setExpandedLayer] = useState<number>(4);

  return (
    <section id="architecture" className="py-24 sm:py-32 px-4 sm:px-6 max-w-7xl mx-auto border-b border-white/[0.08]">
      {/* Header */}
      <div className="space-y-4 max-w-3xl">
        <div className="flex items-center gap-2 text-[11px] font-mono tracking-[0.2em] text-accent uppercase">
          <span>07 / END-TO-END SYSTEM STACK</span>
          <span className="text-slate-600">—</span>
          <span>7-LAYER AIRWORTHINESS ARCHITECTURE</span>
        </div>

        <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-white leading-tight font-mono">
          From in-cylinder flame fronts to fleet depot intelligence.{' '}
          <span className="font-editorial italic font-normal text-slate-300">
            A modular DO-178C DAL-C aligned propulsion architecture.
          </span>
        </h2>

        <p className="text-sm sm:text-base text-slate-400 font-mono leading-relaxed">
          The ANUMAAN architecture spans seven meticulously partitioned engineering layers. Each layer maintains strict boundaries, formal data contracts, and deterministic latency budgets to satisfy CEMILAC and defence airworthiness requirements.
        </p>
      </div>

      {/* Progressive Accordion / Stack Representation */}
      <div className="mt-16 space-y-3">
        {SYSTEM_LAYERS.map((layer) => {
          const isExpanded = expandedLayer === layer.id;
          return (
            <div
              key={layer.id}
              className={`rounded-sm border transition-all duration-200 overflow-hidden ${
                isExpanded
                  ? 'bg-[#0f1522] border-accent/40 shadow-md'
                  : 'bg-[#0a0e17] border-white/10 hover:border-white/20'
              }`}
            >
              {/* Header Bar */}
              <button
                onClick={() => setExpandedLayer(isExpanded ? 0 : layer.id)}
                className="w-full p-4 sm:p-5 flex items-center justify-between text-left gap-4"
              >
                <div className="flex items-center gap-4 flex-wrap">
                  <span className={`px-2 py-0.5 rounded-xs font-mono text-[10px] font-bold ${
                    isExpanded ? 'bg-accent/20 text-accent border border-accent/30' : 'bg-white/5 text-slate-400'
                  }`}>
                    {layer.code}
                  </span>
                  <h3 className="text-xs sm:text-sm font-bold font-mono text-white tracking-wide uppercase">
                    {layer.name}
                  </h3>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-mono text-slate-500 hidden md:block">
                    {layer.standard}
                  </span>
                  <div className={`text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
                    <ChevronDown className="w-4 h-4" />
                  </div>
                </div>
              </button>

              {/* Expanded Details */}
              {isExpanded && (
                <div className="px-4 sm:px-5 pb-5 pt-2 border-t border-white/5 space-y-4 text-xs font-mono">
                  <p className="text-slate-300 leading-relaxed text-xs">
                    {layer.desc}
                  </p>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2">
                    {layer.subsystems.map((sub, i) => (
                      <div key={i} className="p-2.5 rounded-xs bg-white/[0.03] border border-white/[0.06] flex items-center gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-accent shrink-0" />
                        <span className="text-[11px] text-slate-300">{sub}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
};
