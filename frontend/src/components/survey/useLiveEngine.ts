import { useEffect, useState } from 'react';
import { toSurveyFrame, type EngineFrame } from './frame';

/** Light polling of one engine's state for the landing (no WebSocket, ~0.4 req/s, paused when hidden). */
export function useLiveEngine(serverUrl: string, engineId = 'rotax_912is', intervalMs = 2500) {
  const [frame, setFrame] = useState<EngineFrame | null>(null);
  const [status, setStatus] = useState<'connecting' | 'live' | 'offline'>('connecting');
  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    const tick = async () => {
      if (!active) return;
      if (!document.hidden) {
        try {
          const response = await fetch(`${serverUrl}/api/engines/${encodeURIComponent(engineId)}/state`, { cache: 'no-store' });
          if (!response.ok) throw new Error(String(response.status));
          const data = toSurveyFrame(await response.json());
          if (active) { setFrame(data); setStatus('live'); }
        } catch { if (active) setStatus((s) => (s === 'live' ? 'live' : 'offline')); }
      }
      timer = window.setTimeout(tick, intervalMs);
    };
    void tick();
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, [serverUrl, engineId, intervalMs]);
  return { frame, status };
}
