import { useState } from 'react';
import { useEngineRuntime } from '../hooks/useEngineRuntime';
import { LabelsContext, useFetchLabels } from '../utils/labels';
import TwinStage from './TwinStage';

/** The 3D twin tab: only the engine, full height, driven from the keyboard. Same runtime store and fault API as the
 *  console, so a fault injected here shows on every screen and every highlight comes from state.highlights. */
export default function TwinWorkspace({ serverUrl }: { serverUrl: string }) {
  const runtime = useEngineRuntime(serverUrl);
  const labels = useFetchLabels(runtime.api);
  // D64: the twin exists to watch what you inject, so the injected part shows at once (training display on by
  // default here); diagnosis then recolours it in its alert level. The console keeps D56's default (off).
  const [training, setTraining] = useState(true);
  return (
    <LabelsContext.Provider value={labels}>
      <TwinStage engineId={runtime.engineId ?? null} engines={runtime.engines ?? []} onSelectEngine={runtime.selectEngine}
        state={runtime.state} faults={runtime.faults} cylinders={runtime.profile?.cylinders ?? null} api={runtime.api}
        command={runtime.command} training={training} onTraining={setTraining} />
    </LabelsContext.Provider>
  );
}
