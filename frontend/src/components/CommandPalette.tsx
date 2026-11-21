import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Search,
  Cpu,
  Eye,
  AlertTriangle,
  Sliders,
  RotateCcw,
  Radio,
  QrCode,
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
  onInjectFault,
  onClearFaults,
  onSetThrottle,
  onEngineCommand,
}: Props) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const commands = useMemo<CommandItem[]>(() => {
    return [
      // 1. Powerplants
      {
        id: 'engine-rotax-912',
        category: 'Engines',
        title: 'Rotax 912 iSc Sport',
        subtitle: '100 hp Naturally Aspirated · Dual EFI (Baseline Platform)',
        badge: selectedEngineId === 'rotax_912is' ? 'ACTIVE' : undefined,
        icon: <Cpu className="w-4 h-4 text-emerald-700" />,
        action: () => { onSelectEngine('rotax_912is'); onClose(); },
      },
      {
        id: 'engine-rotax-914',
        category: 'Engines',
        title: 'Rotax 914 F',
        subtitle: '115 hp Turbocharged · Automatic wastegate control',
        badge: selectedEngineId === 'rotax_914' ? 'ACTIVE' : undefined,
        icon: <Cpu className="w-4 h-4 text-amber-700" />,
        action: () => { onSelectEngine('rotax_914'); onClose(); },
      },
      {
        id: 'engine-rotax-915',
        category: 'Engines',
        title: 'Rotax 915 iSc',
        subtitle: '141 hp Turbocharged & Intercooled · High-altitude flight profile',
        badge: selectedEngineId === 'rotax_915is' ? 'ACTIVE' : undefined,
        icon: <Cpu className="w-4 h-4 text-amber-700" />,
        action: () => { onSelectEngine('rotax_915is'); onClose(); },
      },
      {
        id: 'engine-austro-ae300',
        category: 'Engines',
        title: 'Austro Engine AE300',
        subtitle: '168 hp Heavy fuel · Common-rail aero-diesel (Jet-A1)',
        badge: selectedEngineId === 'austro_ae300' ? 'ACTIVE' : undefined,
        icon: <Cpu className="w-4 h-4 text-cyan-800" />,
        action: () => { onSelectEngine('austro_ae300'); onClose(); },
      },
      {
        id: 'engine-vrde-22l',
        category: 'Engines',
        title: 'VRDE-Jayem 2.2L',
        subtitle: '180 hp Heavy fuel · Indigenous common-rail UAV diesel (TAPAS-BH-201)',
        badge: selectedEngineId === 'vrde_jayem_2_2l' ? 'ACTIVE' : undefined,
        icon: <Cpu className="w-4 h-4 text-cyan-800" />,
        action: () => { onSelectEngine('vrde_jayem_2_2l'); onClose(); },
      },

      // 2. 3D Render Modes
      {
        id: 'view-solid',
        category: '3D Views',
        title: 'Solid CAD Surface',
        subtitle: 'Certified engineering CAD geometry with baked ambient occlusion',
        badge: 'CAD',
        icon: <Eye className="w-4 h-4 text-slate-700" />,
        action: () => { onSelectViewMode('solid'); onClose(); },
      },
      {
        id: 'view-glass',
        category: '3D Views',
        title: 'X-Ray Optical Glass',
        subtitle: 'Physical transmission casing revealing reciprocating pistons & valves',
        badge: 'X-RAY',
        icon: <Eye className="w-4 h-4 text-cyan-700" />,
        action: () => { onSelectViewMode('glass'); onClose(); },
      },
      {
        id: 'view-thermal',
        category: '3D Views',
        title: 'Thermal FLIR Heatmap',
        subtitle: 'Live Planck blackbody incandescence pyrometry (CHT 50-140°C, EGT 400-950°C)',
        badge: 'FLIR',
        icon: <Flame className="w-4 h-4 text-accent" />,
        action: () => { onSelectViewMode('thermal'); onClose(); },
      },
      {
        id: 'view-ghost',
        category: '3D Views',
        title: 'Twin Ghost',
        subtitle: 'Holographic nominal model comparison overlay for anomaly localization',
        badge: 'GHOST',
        icon: <Eye className="w-4 h-4 text-indigo-700" />,
        action: () => { onSelectViewMode('ghost'); onClose(); },
      },

      // 3. Engine Controls & Levers
      {
        id: 'ctrl-takeoff',
        category: 'Controls',
        title: 'Take-off Power (100% Throttle)',
        subtitle: 'Advance power lever to maximum rated climb throttle',
        badge: '100%',
        icon: <Sliders className="w-4 h-4 text-emerald-700" />,
        action: () => { onSetThrottle?.(100); onClose(); },
      },
      {
        id: 'ctrl-cruise',
        category: 'Controls',
        title: 'Cruise Power (75% Throttle)',
        subtitle: 'Set power lever to standard long-endurance cruise setting',
        badge: '75%',
        icon: <Sliders className="w-4 h-4 text-emerald-700" />,
        action: () => { onSetThrottle?.(75); onClose(); },
      },
      {
        id: 'ctrl-idle',
        category: 'Controls',
        title: 'Flight Idle (20% Throttle)',
        subtitle: 'Retard throttle to minimum flight descent stop',
        badge: 'IDLE',
        icon: <Sliders className="w-4 h-4 text-slate-700" />,
        action: () => { onSetThrottle?.(20); onClose(); },
      },
      {
        id: 'ctrl-reset-engine',
        category: 'Controls',
        title: 'Reset & Restart Engine',
        subtitle: 'Acknowledge alert latches and reset simulation state',
        icon: <RotateCcw className="w-4 h-4 text-slate-700" />,
        action: () => { onEngineCommand?.('RESET'); onClose(); },
      },

      // 4. Fault Scenarios
      {
        id: 'fault-misfire-cyl2',
        category: 'Faults',
        title: 'Ignition Misfire Cylinder 2',
        subtitle: 'Simulates spark plug/coil failure; drops CHT2 and triggers 0.5X vibration',
        badge: 'F01',
        icon: <AlertTriangle className="w-4 h-4 text-amber-700" />,
        action: () => { onInjectFault?.('F01', 1.0); onClose(); },
      },
      {
        id: 'fault-wastegate',
        category: 'Faults',
        title: 'Turbo Wastegate Actuator Seized',
        subtitle: 'Loss of manifold boost pressure control at high altitude',
        badge: 'F14',
        icon: <AlertTriangle className="w-4 h-4 text-accent" />,
        action: () => { onInjectFault?.('F14', 1.0); onClose(); },
      },
      {
        id: 'fault-coolant-leak',
        category: 'Faults',
        title: 'Coolant Hose Leak',
        subtitle: 'Gradual coolant pressure collapse followed by bulk engine thermal runaway',
        badge: 'F21',
        icon: <AlertTriangle className="w-4 h-4 text-accent" />,
        action: () => { onInjectFault?.('F21', 1.0); onClose(); },
      },
      {
        id: 'fault-oil-loss',
        category: 'Faults',
        title: 'Oil Scavenge Pump Loss',
        subtitle: 'Oil pressure collapse below 1.5 bar with critical bearing film thinning',
        badge: 'F23',
        icon: <AlertTriangle className="w-4 h-4 text-accent" />,
        action: () => { onInjectFault?.('F23', 1.0); onClose(); },
      },
      {
        id: 'fault-clear-all',
        category: 'Faults',
        title: 'Clear All Active Faults',
        subtitle: 'Reset injected perturbations and return all physical subsystems to nominal',
        icon: <RotateCcw className="w-4 h-4 text-emerald-700" />,
        action: () => { onClearFaults?.(); onClose(); },
      },

      // 5. Avionics & Connectivity
      {
        id: 'av-open-can',
        category: 'Avionics',
        title: 'Open Avionics CAN Bus & FADEC Hub',
        subtitle: 'Inspect live 20 Hz SAE J1939 telemetry stream and test security IDS',
        icon: <Radio className="w-4 h-4 text-cyan-800" />,
        action: () => { onOpenCanInspector(); onClose(); },
      },
      {
        id: 'av-switch-can',
        category: 'Avionics',
        title: 'Telemetry Source: Switch to CAN Bus Link',
        subtitle: 'Route telemetry through 29-bit J1939 DBC quantization and sequence counters',
        icon: <Radio className="w-4 h-4 text-accent" />,
        action: () => { onOpenCanInspector(); onClose(); },
      },
      {
        id: 'tool-qr',
        category: 'Tools',
        title: 'Mobile Cockpit Pairing (QR Code)',
        subtitle: 'Pair smartphone or tablet as secondary tactical flight deck over Wi-Fi',
        icon: <QrCode className="w-4 h-4 text-slate-700" />,
        action: () => { onOpenConnectionModal(); onClose(); },
      },
    ];
  }, [selectedEngineId, onSelectEngine, onSelectViewMode, onOpenCanInspector, onOpenConnectionModal, onInjectFault, onClearFaults, onSetThrottle, onEngineCommand, onClose]);

  const filteredCommands = useMemo(() => {
    if (!query.trim()) return commands;
    const q = query.toLowerCase().trim();
    return commands.filter(
      (c) =>
        c.title.toLowerCase().includes(q) ||
        c.subtitle.toLowerCase().includes(q) ||
        c.category.toLowerCase().includes(q) ||
        (c.badge && c.badge.toLowerCase().includes(q))
    );
  }, [commands, query]);

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
      id="command-palette-backdrop"
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/60 backdrop-blur-sm animate-fade-in font-sans"
      onClick={onClose}
    >
      <div
        className="surface-panel w-full max-w-xl overflow-hidden rounded-sm border border-surface-border-strong text-slate-800 bg-[#f7f6f0] shadow-card-lg flex flex-col"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3 border-b border-surface-border bg-black/[0.02]">
          <Search className="w-4 h-4 text-slate-500 mr-2.5 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or search (engines, views, faults, throttle)..."
            className="w-full bg-transparent text-sm text-slate-900 placeholder:text-slate-500 focus:outline-none font-sans"
          />
          {query ? (
            <button
              onClick={() => setQuery('')}
              className="p-1 rounded-sm text-slate-400 hover:text-slate-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          ) : (
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] text-slate-600 rounded-sm border border-surface-border bg-white font-mono shadow-xs">
              ESC
            </kbd>
          )}
        </div>

        {/* Command List */}
        <div className="max-h-[55vh] overflow-y-auto p-2 space-y-1">
          {filteredCommands.length > 0 ? (
            filteredCommands.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3 py-2 rounded-sm cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-black/[0.07] border-l-2 border-accent text-slate-950 font-medium'
                      : 'text-slate-800 hover:bg-black/[0.03]'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-7 h-7 rounded-sm bg-white border border-surface-border flex items-center justify-center shrink-0 shadow-xs">
                      {item.icon}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-900 truncate">{item.title}</span>
                        {item.badge && (
                          <span
                            className={`px-1.5 py-0.2 rounded-sm text-[10px] font-mono font-medium ${
                              item.badge === 'ACTIVE'
                                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                                : 'bg-black/5 text-slate-700 border border-surface-border'
                            }`}
                          >
                            {item.badge}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-600 truncate mt-0.5">{item.subtitle}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 ml-3">
                    <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">{item.category}</span>
                    {isSelected && <CornerDownLeft className="w-3.5 h-3.5 text-accent" />}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="py-10 text-center text-slate-500 text-xs font-mono">
              No matching commands found for &quot;{query}&quot;
            </div>
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="flex items-center justify-between px-4 py-2.5 border-t border-surface-border bg-black/[0.02] text-[11px] text-slate-600 font-mono">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="px-1.5 py-0.5 rounded-sm border border-surface-border bg-white text-[10px] shadow-xs mr-1">↑</kbd>
              <kbd className="px-1.5 py-0.5 rounded-sm border border-surface-border bg-white text-[10px] shadow-xs mr-1">↓</kbd>
              Navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded-sm border border-surface-border bg-white text-[10px] shadow-xs mr-1">↵</kbd>
              Select
            </span>
          </div>
          <span className="text-slate-500">Ctrl+K Palette</span>
        </div>
      </div>
    </div>
  );
}
