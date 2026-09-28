import React, { createContext, useContext, useMemo } from 'react';
import { useEngineRuntime, EngineProfile, EngineFrame, EngineSchema, FleetMember } from '../hooks/useEngineRuntime';

export interface EngineSelectionContextValue {
  catalog: { selected: string; tick: number; engines: EngineProfile[] } | null;
  fleet: FleetMember[];
  profile: EngineProfile | null;
  schema: EngineSchema | null;
  engineId: string;
  selectEngine: (id: string) => Promise<void>;
  frame: EngineFrame | null;
  connected: boolean;
  latencyMs: number;
  error: string;
  command: (path: string, method: string, body?: unknown) => Promise<any>;
  refreshCatalog: () => Promise<void>;
  isRotax912isSelected: boolean;
  isDefaultEngineSelected: boolean;
}

const EngineSelectionContext = createContext<EngineSelectionContextValue | null>(null);

export interface EngineSelectionProviderProps {
  serverUrl: string;
  children: React.ReactNode;
}

export const EngineSelectionProvider: React.FC<EngineSelectionProviderProps> = ({
  serverUrl,
  children,
}) => {
  const runtime = useEngineRuntime(serverUrl);

  const value = useMemo<EngineSelectionContextValue>(() => {
    return {
      ...runtime,
      isRotax912isSelected: runtime.engineId === 'rotax_912is',
      isDefaultEngineSelected: runtime.engineId === 'rotax_912is',
    };
  }, [runtime]);

  return (
    <EngineSelectionContext.Provider value={value}>
      {children}
    </EngineSelectionContext.Provider>
  );
};

export function useEngineSelection(): EngineSelectionContextValue {
  const context = useContext(EngineSelectionContext);
  if (!context) {
    throw new Error('useEngineSelection must be used within an EngineSelectionProvider');
  }
  return context;
}
