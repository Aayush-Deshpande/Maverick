import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Search,
  Cpu,
  Eye,
  AlertTriangle,
  Sliders,
  Power,
  RotateCcw,
  Radio,
  QrCode,
  FileText,
  Volume2,
  X,
  CornerDownLeft,
  Flame,
} from 'lucide-react';

export interface CommandItem {
  id: string;
  category: 'Engines' | '3D Views' | 'Faults' | 'Controls' | 'Avionics' | 'Sorties' | 'Tools';
  title: string;
  subtitle: string;
  badge?: string;
  icon: React.ReactNode;
  action: () => void;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  selectedEngineId: string | null;
  onSelectEngine: (engineId: string) => void;
  onSelectViewMode: (mode: 'solid' | 'glass' | 'thermal' | 'ghost') => void;
  onOpenCanInspector: () => void;
  onOpenConnectionModal: () => void;
  onToggleVoice: () => void;
  onInjectFault?: (faultId: string, severity?: number) => void;
  onClearFaults?: () => void;
  onSetThrottle?: (pct: number) => void;
  onEngineCommand?: (cmd: 'START' | 'STOP' | 'RESET') => void;
}

export default function CommandPalette({
  isOpen,
  onClose,
  selectedEngineId,
  onSelectEngine,
  onSelectViewMode,
  onOpenCanInspector,
  onOpenConnectionModal,
  onToggleVoice,
  onInjectFault,
  onClearFaults,
  onSetThrottle,
  onEngineCommand,
}: Props) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Keyboard shortcut listener for Ctrl+K / Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) {
          onClose();
        } else {
          // Open palette
          // Will be handled in parent or toggled
        }
      } else if (e.key === 'Escape' && isOpen) {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const commands = useMemo<CommandItem[]>(() => {
    const list: CommandItem[] = [
      // 1. Engines
      {
        id: 'eng-rotax-912is',
        category: 'Engines',
        title: 'Switch Engine: Rotax 912 iSc Sport',
        subtitle: '100 HP Naturally Aspirated FADEC (Reference Baseline)',
        badge: selectedEngineId === 'rotax_912is' ? 'ACTIVE' : 'ROTAX 912',
        icon: <Cpu className="w-4 h-4 text-cyan-400" />,
        action: () => { onSelectEngine('rotax_912is'); onClose(); },
      },
      {
        id: 'eng-rotax-914',
        category: 'Engines',
        title: 'Switch Engine: Rotax 914 UL Turbocharged',
        subtitle: '115 HP Turbocharged with Automatic Wastegate Control',
        badge: selectedEngineId === 'rotax_914' ? 'ACTIVE' : 'ROTAX 914',
        icon: <Cpu className="w-4 h-4 text-cyan-400" />,
        action: () => { onSelectEngine('rotax_914'); onClose(); },
      },
      {
        id: 'eng-rotax-915is',
        category: 'Engines',
        title: 'Switch Engine: Rotax 915 iSc Turbocharged',
        subtitle: '141 HP Intercooled High-Altitude Propulsion',
        badge: selectedEngineId === 'rotax_915is' ? 'ACTIVE' : 'ROTAX 915',
        icon: <Cpu className="w-4 h-4 text-cyan-400" />,
        action: () => { onSelectEngine('rotax_915is'); onClose(); },
      },
      {
        id: 'eng-austro-ae300',
        category: 'Engines',
        title: 'Switch Engine: Austro Engine AE300',
        subtitle: '170 HP Common-Rail Turbocharged Aero-Diesel (Jet-A1)',
        badge: selectedEngineId === 'austro_ae300' ? 'ACTIVE' : 'AE300',
        icon: <Cpu className="w-4 h-4 text-cyan-400" />,
        action: () => { onSelectEngine('austro_ae300'); onClose(); },
      },
      {
        id: 'eng-vrde-2-2l',
        category: 'Engines',
        title: 'Switch Engine: DRDO VRDE-Jayem 2.2L Aero-Diesel',
        subtitle: '180 HP Indigenous Common-Rail Diesel for TAPAS-BH-201',
        badge: selectedEngineId === 'vrde_jayem_2_2l' ? 'ACTIVE' : 'VRDE 2.2L',
        icon: <Cpu className="w-4 h-4 text-cyan-400" />,
        action: () => { onSelectEngine('vrde_jayem_2_2l'); onClose(); },
      },

      // 2. 3D Views
      {
        id: 'view-solid',
        category: '3D Views',
        title: '3D View: Solid CAD Surface',
        subtitle: 'Realistic PBR engineering materials with baked shadows',
        badge: 'SOLID',
        icon: <Eye className="w-4 h-4 text-slate-300" />,
        action: () => { onSelectViewMode('solid'); onClose(); },
      },
      {
        id: 'view-glass',
        category: '3D Views',
        title: '3D View: X-Ray Optical Glass',
        subtitle: 'Physical transmission glass casing with exposed internals',
        badge: 'X-RAY',
        icon: <Eye className="w-4 h-4 text-cyan-400" />,
        action: () => { onSelectViewMode('glass'); onClose(); },
      },
      {
        id: 'view-thermal',
        category: '3D Views',
        title: '3D View: Thermal FLIR Heatmap',
        subtitle: 'Live Planck blackbody incandescence pyrometry gradient',
        badge: 'THERMAL',
        icon: <Flame className="w-4 h-4 text-rose-400" />,
        action: () => { onSelectViewMode('thermal'); onClose(); },
      },
      {
        id: 'view-ghost',
        category: '3D Views',
        title: '3D View: Twin Ghost Residual Overlay',
        subtitle: 'Holographic nominal model departures glowing by error',
        badge: 'GHOST',
        icon: <Eye className="w-4 h-4 text-indigo-400" />,
        action: () => { onSelectViewMode('ghost'); onClose(); },
      },

      // 3. Fault Injections
      {
        id: 'fault-misfire-cyl2',
        category: 'Faults',
        title: 'Inject Fault: Ignition Misfire Cylinder 2',
        subtitle: 'Simulates spark plug/coil breakdown; drops CHT2 and spikes vib 0.5X',
        badge: 'F01',
        icon: <AlertTriangle className="w-4 h-4 text-amber-400" />,
        action: () => { onInjectFault?.('F01', 1.0); onClose(); },
      },
      {
        id: 'fault-wastegate',
        category: 'Faults',
        title: 'Inject Fault: Turbo Wastegate Actuator Seized',
        subtitle: 'Loss of MAP boost pressure control at altitude',
        badge: 'F14',
        icon: <AlertTriangle className="w-4 h-4 text-rose-400" />,
        action: () => { onInjectFault?.('F14', 1.0); onClose(); },
      },
      {
        id: 'fault-coolant-leak',
        category: 'Faults',
        title: 'Inject Fault: Coolant Radiator Hose Pinhole Leak',
        subtitle: 'Linear coolant pressure loss followed by bulk overheating',
        badge: 'F21',
        icon: <AlertTriangle className="w-4 h-4 text-rose-400" />,
        action: () => { onInjectFault?.('F21', 1.0); onClose(); },
      },
      {
        id: 'fault-oil-loss',
        category: 'Faults',
        title: 'Inject Fault: Oil Scavenge Pump Loss / Pressure Drop',
        subtitle: 'Oil pressure collapse below 1.5 bar; critical lubrication failure',
        badge: 'F23',
        icon: <AlertTriangle className="w-4 h-4 text-rose-400" />,
        action: () => { onInjectFault?.('F23', 1.0); onClose(); },
      },
      {
        id: 'fault-injector-coking',
        category: 'Faults',
        title: 'Inject Fault: Injector Nozzle Coking',
        subtitle: 'Spray pattern disruption; EGT dispersion across cylinders',
        badge: 'F06',
        icon: <AlertTriangle className="w-4 h-4 text-amber-400" />,
        action: () => { onInjectFault?.('F06', 1.0); onClose(); },
      },

      // 4. Controls
      {
        id: 'ctrl-takeoff',
        category: 'Controls',
        title: 'Throttle: Full Takeoff Power (100%)',
        subtitle: 'Sets power lever to rated maximum takeoff throttle',
        badge: '100% THR',
        icon: <Sliders className="w-4 h-4 text-emerald-400" />,
        action: () => { onSetThrottle?.(100); onClose(); },
      },
      {
        id: 'ctrl-cruise',
        category: 'Controls',
        title: 'Throttle: Continuous Cruise Power (75%)',
        subtitle: 'Sets power lever to long-endurance ISR cruise throttle',
        badge: '75% THR',
        icon: <Sliders className="w-4 h-4 text-emerald-400" />,
        action: () => { onSetThrottle?.(75); onClose(); },
      },
      {
        id: 'ctrl-idle',
        category: 'Controls',
        title: 'Throttle: Ground Idle (0%)',
        subtitle: 'Reduces throttle to minimum idle stop',
        badge: 'IDLE',
        icon: <Sliders className="w-4 h-4 text-slate-400" />,
        action: () => { onSetThrottle?.(0); onClose(); },
      },
      {
        id: 'ctrl-clear-all',
        category: 'Controls',
        title: 'Clear All Active Faults',
        subtitle: 'Restores healthy baseline physics and clears injector/coolant levers',
        badge: 'RESET',
        icon: <RotateCcw className="w-4 h-4 text-cyan-400" />,
        action: () => { onClearFaults?.(); onClose(); },
      },
      {
        id: 'ctrl-restart',
        category: 'Controls',
        title: 'Engine Command: RESTART & RESET',
        subtitle: 'Cyles engine ignition and executes restart settle protocol',
        badge: 'START',
        icon: <Power className="w-4 h-4 text-emerald-400" />,
        action: () => { onEngineCommand?.('START'); onClose(); },
      },

      // 5. Avionics & CAN
      {
        id: 'can-open-hub',
        category: 'Avionics',
        title: 'Open Avionics CAN Bus & FADEC Hub',
        subtitle: 'Inspect live 29-bit J1939 frames, byte rates, and CAN IDS alerts',
        badge: 'CAN HUB',
        icon: <Radio className="w-4 h-4 text-cyan-400" />,
        action: () => { onOpenCanInspector(); onClose(); },
      },
      {
        id: 'can-set-can',
        category: 'Avionics',
        title: 'Telemetry Source: Switch to CAN Bus Link',
        subtitle: 'Route frames through python-can virtual bus with J1939 quantization',
        badge: 'CAN MODE',
        icon: <Radio className="w-4 h-4 text-cyan-400" />,
        action: async () => {
          await fetch('/api/v1/runtime/source', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data_source: 'CAN' }),
          });
          onClose();
        },
      },
      {
        id: 'can-set-direct',
        category: 'Avionics',
        title: 'Telemetry Source: Switch to Direct In-Process',
        subtitle: 'Direct plant memory connection for zero-overhead evaluation',
        badge: 'DIRECT',
        icon: <Radio className="w-4 h-4 text-slate-400" />,
        action: async () => {
          await fetch('/api/v1/runtime/source', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data_source: 'DIRECT' }),
          });
          onClose();
        },
      },

      // 6. Tools
      {
        id: 'tool-qr-phone',
        category: 'Tools',
        title: 'Open Mobile QR Secondary Display Gateway',
        subtitle: 'Pair smartphone or tablet as field remote flight deck',
        badge: 'QR JOIN',
        icon: <QrCode className="w-4 h-4 text-purple-400" />,
        action: () => { onOpenConnectionModal(); onClose(); },
      },
      {
        id: 'tool-voice',
        category: 'Tools',
        title: 'Toggle Tactical Voice Copilot',
        subtitle: 'Activate hands-free speech recognition and audio debrief',
        badge: 'VOICE',
        icon: <Volume2 className="w-4 h-4 text-amber-400" />,
        action: () => { onToggleVoice(); onClose(); },
      },
      {
        id: 'tool-export-pdf',
        category: 'Tools',
        title: 'Export DRDO Sortie Debrief Report',
        subtitle: 'Generate printable mission debrief with Merkle audit hash',
        badge: 'PDF',
        icon: <FileText className="w-4 h-4 text-emerald-400" />,
        action: () => {
          window.open('/api/v1/recordings/latest/report', '_blank');
          onClose();
        },
      },
    ];

    return list;
  }, [
    onSelectEngine,
    onSelectViewMode,
    onOpenCanInspector,
    onOpenConnectionModal,
    onToggleVoice,
    onInjectFault,
    onClearFaults,
    onSetThrottle,
    onEngineCommand,
    onClose,
  ]);

  const filteredCommands = useMemo(() => {
    if (!query.trim()) return commands;
    const q = query.toLowerCase();
    return commands.filter(
      (c) =>
        c.title.toLowerCase().includes(q) ||
        c.subtitle.toLowerCase().includes(q) ||
        c.category.toLowerCase().includes(q) ||
        (c.badge && c.badge.toLowerCase().includes(q))
    );
  }, [commands, query]);

  // Adjust selection if query shrinks list
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredCommands.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredCommands.length) % Math.max(1, filteredCommands.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredCommands[selectedIndex]) {
        filteredCommands[selectedIndex].action();
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-slate-950/75 backdrop-blur-md animate-fade-in font-mono"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl overflow-hidden rounded-lg border border-slate-700 bg-slate-900/95 shadow-2xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3 border-b border-slate-800 bg-slate-950/60">
          <Search className="w-5 h-5 text-slate-400 mr-3 flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search engines, 3D views, faults, CAN avionics, throttle (Ctrl+K)..."
            className="w-full bg-transparent text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none font-mono"
          />
          {query ? (
            <button
              onClick={() => setQuery('')}
              className="p-1 rounded text-slate-500 hover:text-slate-200"
            >
              <X className="w-4 h-4" />
            </button>
          ) : (
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] text-slate-400 rounded border border-slate-700 bg-slate-800">
              ESC
            </kbd>
          )}
        </div>

        {/* Command List */}
        <div className="max-h-[60vh] overflow-y-auto p-2 divide-y divide-slate-800/40">
          {filteredCommands.length > 0 ? (
            filteredCommands.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-md cursor-pointer transition-colors ${
                    isSelected ? 'bg-cyan-500/15 border border-cyan-500/40 text-cyan-200' : 'text-slate-300 hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="p-1.5 rounded bg-slate-800/80 border border-slate-700/60 flex-shrink-0">
                      {item.icon}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-100 truncate">{item.title}</span>
                        {item.badge && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] border border-slate-700 bg-slate-800 text-slate-300 font-bold">
                            {item.badge}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 truncate">{item.subtitle}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                    <span className="text-[10px] text-slate-500 uppercase">{item.category}</span>
                    {isSelected && <CornerDownLeft className="w-3.5 h-3.5 text-cyan-400" />}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="py-8 text-center text-slate-500 text-xs">
              No matching commands found for &quot;{query}&quot;
            </div>
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-slate-800 bg-slate-950/70 text-[10px] text-slate-400">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="px-1 py-0.5 rounded border border-slate-700 bg-slate-800 mr-1">↑</kbd>
              <kbd className="px-1 py-0.5 rounded border border-slate-700 bg-slate-800 mr-1">↓</kbd>
              Navigate
            </span>
            <span>
              <kbd className="px-1 py-0.5 rounded border border-slate-700 bg-slate-800 mr-1">↵</kbd>
              Select
            </span>
          </div>
          <span>ANUMAAN Aerospace C2 Command Palette</span>
        </div>
      </div>
    </div>
  );
}
