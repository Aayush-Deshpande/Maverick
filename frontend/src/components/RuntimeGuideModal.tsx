import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Activity, AlertTriangle, CheckCircle2, Clock, Cpu, Gauge, Info, ShieldCheck, Wrench, X, Zap } from 'lucide-react';

interface RuntimeGuideModalProps {
  open: boolean;
  onClose: () => void;
}

export const RuntimeGuideModal: React.FC<RuntimeGuideModalProps> = ({ open, onClose }) => {
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const modal = (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="runtime-guide-title"
    >
      <div
        className="surface-panel w-full max-w-2xl max-h-[85vh] flex flex-col rounded-sm shadow-card-lg border border-surface-border-strong text-slate-800 bg-[#f7f6f0] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header - pinned at top */}
        <div className="flex items-start justify-between border-b border-surface-border p-4 shrink-0 bg-[#f7f6f0]">
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-[#68757a] font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Flight Deck &amp; Digital Twin Architecture</span>
            </div>
            <h2 id="runtime-guide-title" className="text-base font-bold text-slate-900 tracking-tight mt-1">
              How ANUMAAN Monitors Engine Health, Detects Faults, and Protects Aircraft
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-sm p-1.5 text-slate-400 hover:text-slate-800 hover:bg-black/10 transition-colors"
            title="Close guide (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3.5 text-xs font-sans leading-relaxed text-slate-700">
          {/* Section 1 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-accent font-semibold uppercase tracking-wider text-[11px] font-mono">
              <Zap className="w-3.5 h-3.5" />
              <span>1. Real Engine Physics (20 Times Every Second)</span>
            </div>
            <p className="mt-1.5 text-xs">
              Every reading on this dashboard is driven by a live physical simulation of real aero engines—never fake or randomized numbers. When you advance the throttle or climb to high altitude, the system continuously solves thermodynamic equations at 20 updates per second, computing how heat, airflow, and fuel burning shift in real time.
            </p>
            <p className="mt-1 text-slate-600 text-[11px]">
              When you inject a fault (such as a clogged fuel injector or cooling leak), it alters the engine's internal physical mechanics so you can watch how cylinder temperatures, fuel flow, and pressures genuinely react.
            </p>
          </div>

          {/* Section 2 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px] font-mono">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>2. Smart Sensor Health Check</span>
            </div>
            <p className="mt-1.5 text-xs">
              In real flight, sensor wires can loosen, short-circuit, or degrade. Before judging the engine, ANUMAAN constantly inspects the sensors themselves. If a temperature sensor starts sending erratic data or disconnects, the system automatically quarantines it so a simple wiring glitch never causes a false emergency engine shutdown.
            </p>
          </div>

          {/* Section 3 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px] font-mono">
              <Cpu className="w-3.5 h-3.5 text-cyan-700" />
              <span>3. Background Digital Twin Observer</span>
            </div>
            <p className="mt-1.5 text-xs">
              Running continuously alongside the engine is an advanced mathematical digital twin. Given the current throttle setting, speed, altitude, and outside air temperature, it calculates what every cylinder temperature and oil pressure should be right now. If a physical sensor ever fails, this digital twin can even step in and estimate the missing measurement with high accuracy.
            </p>
          </div>

          {/* Section 4 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px] font-mono">
              <Gauge className="w-3.5 h-3.5 text-indigo-700" />
              <span>4. Virtual Sensors (Seeing Deep Inside the Engine)</span>
            </div>
            <p className="mt-1.5 text-xs">
              Physical sensors cannot be installed everywhere—you cannot put a thermometer inside the fire of a cylinder or on a spinning crankshaft bearing. The digital twin calculates these hidden parameters in real time:
            </p>
            <ul className="mt-1.5 list-disc pl-5 space-y-1 text-slate-600 text-[11px]">
              <li><strong>Peak Cylinder Pressure</strong>: The maximum mechanical force pushing down on each piston crown during combustion.</li>
              <li><strong>Minimum Bearing Oil Film</strong>: The microscopic layer of oil (in micrometers) protecting the crankshaft from metal-on-metal destruction.</li>
              <li><strong>Indicated Power</strong>: The true mechanical horsepower produced inside the combustion chambers.</li>
              <li><strong>Turbine Inlet Temperature</strong>: The extreme exhaust gas heat entering the turbocharger before exiting the aircraft.</li>
            </ul>
          </div>

          {/* Section 5 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px] font-mono">
              <Activity className="w-3.5 h-3.5 text-amber-600" />
              <span>5. Instant Anomaly Detection</span>
            </div>
            <p className="mt-1.5 text-xs">
              The system constantly compares real sensor readings against what the healthy digital twin expects. If an exhaust temperature spikes or cooling drops abnormally, the anomaly detector catches it immediately. A confirmation filter ensures abnormal readings persist across several consecutive checks before sounding an alarm, eliminating false alerts from harmless electrical noise.
            </p>
          </div>

          {/* Section 6 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px] font-mono">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
              <span>6. Pinpoint Root-Cause Diagnosis</span>
            </div>
            <p className="mt-1.5 text-xs">
              Once an anomaly is flagged, the diagnostic engine figures out exactly what is wrong. It can distinguish whether an overheating symptom is caused by an ignition misfire, a clogged fuel injector, or a coolant leak. It identifies the specific cylinder involved and shows its confidence level as a percentage.
            </p>
          </div>

          {/* Section 7 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px] font-mono">
              <Clock className="w-3.5 h-3.5 text-blue-700" />
              <span>7. Remaining Useful Life &amp; Danger Warnings</span>
            </div>
            <p className="mt-1.5 text-xs">
              ANUMAAN tracks metal wear and thermal stress over time to provide two essential safety forecasts:
            </p>
            <ul className="mt-1.5 list-disc pl-5 space-y-1 text-slate-600 text-[11px]">
              <li><strong>Time to Limit</strong>: Warns operators how many minutes remain before a rising temperature or dropping pressure crosses dangerous redlines.</li>
              <li><strong>Remaining Useful Life (RUL)</strong>: Accurately estimates how many operating hours the engine has left before components require scheduled maintenance or overhaul.</li>
            </ul>
          </div>

          {/* Section 8 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px] font-mono">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
              <span>8. Mission Reliability &amp; Risk Forecasting</span>
            </div>
            <p className="mt-1.5 text-xs">
              Before or during a flight mission, ANUMAAN simulates 10,000 potential flight outcomes based on current engine wear and the planned flight route (takeoff, climb, cruise, loiter, return). It provides the exact probability of finishing the mission without engine failure and highlights which component carries the highest risk.
            </p>
          </div>

          {/* Section 9 */}
          <div className="rounded-sm border border-surface-border bg-black/[0.02] p-3">
            <div className="flex items-center gap-1.5 text-slate-800 font-semibold uppercase tracking-wider text-[11px] font-mono">
              <Wrench className="w-3.5 h-3.5 text-slate-700" />
              <span>9. Automated Ground Crew Work Orders</span>
            </div>
            <p className="mt-1.5 text-xs">
              When an issue is diagnosed, the system automatically drafts official aviation-standard work orders (categorized under international ATA chapters like Engine Fuel, Ignition, or Cooling). Ground technicians can review the findings, service the engine, and sign off on completed repairs.
            </p>
          </div>
        </div>

        {/* Modal Footer - pinned at bottom */}
        <div className="flex items-center justify-between border-t border-surface-border p-3 shrink-0 bg-[#f7f6f0]">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-600 font-mono">
            <Info className="w-3.5 h-3.5 text-slate-400" />
            <span>Fully dynamic plant simulation · Zero fake numbers · DRDO / iDEX PS-26054</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-sm bg-accent px-3 py-1.5 text-xs font-mono font-medium text-white hover:bg-accent/90 transition-colors shadow-sm"
          >
            Acknowledge &amp; Close [Esc]
          </button>
        </div>
      </div>
    </div>
  );

  if (typeof document === 'undefined') return modal;
  return createPortal(modal, document.body);
};

export default RuntimeGuideModal;
