/* Engine console data on /api/v1 (card M0-09b). One socket (src/api/socket.ts) feeds one store; engine selection is
   per client (it never changes what other clients see, audit #23); lists come from the API, never from code. */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { SocketManager, wsUrl } from '../api/socket';
import { useEngineStore } from '../store/engineStore';

export interface V1Engine {
  engine_id: string;
  display_name: string;
  manufacturer?: string;
  ignition_mode?: string;
  induction?: string;
  fuel_system?: string;
  cylinders: number;
  ready: boolean;
}

export interface V1Fault {
  id: string;
  name: string;
  kind: 'PHYSICAL' | 'SENSOR';
  scope: 'ENGINE' | 'CYLINDER' | 'CHANNEL';
  description: string;
  default_severity: number;
  default_ramp_s: number;
}

/* Re-render on a timer so data age keeps counting while no messages arrive. */
export function useNow(intervalMs: number): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs]);
  return now;
}

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json() as { detail?: { message?: string } | string };
    if (typeof body.detail === 'string') return body.detail;
    if (body.detail?.message) return body.detail.message;
  } catch { /* fall through to the status line */ }
  return `Request failed (${response.status})`;
}

export function useEngineRuntime(serverUrl: string) {
  const [engines, setEngines] = useState<V1Engine[]>([]);
  const [engineId, setEngineId] = useState<string | null>(null);
  const [faults, setFaults] = useState<V1Fault[]>([]);
  const [error, setError] = useState('');
  const manager = useRef<SocketManager | null>(null);
  const connection = useEngineStore((s) => s.connection);
  const streamError = useEngineStore((s) => s.lastError);
  const fleet = useEngineStore((s) => s.engines);
  const slot = engineId ? fleet[engineId] : undefined;

  const loadEngines = useCallback(async () => {
    try {
      const response = await fetch(`${serverUrl}/api/v1/engines`, { cache: 'no-store' });
      if (!response.ok) throw new Error(await readError(response));
      const data = await response.json() as { engines: V1Engine[] };
      setEngines(data.engines);
      setError('');
      setEngineId((current) => {
        if (current && data.engines.some((e) => e.engine_id === current)) return current;
        const fromUrl = new URLSearchParams(window.location.search).get('engine');
        return data.engines.find((e) => e.engine_id === fromUrl)?.engine_id ?? data.engines[0]?.engine_id ?? null;
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Cannot reach the engine runtime');
    }
  }, [serverUrl]);

  // engine list on mount and again after every reconnect (no polling)
  useEffect(() => { void loadEngines(); }, [loadEngines]);
  const wasLive = useRef(false);
  useEffect(() => {
    if (connection === 'LIVE' && !wasLive.current) void loadEngines();
    wasLive.current = connection === 'LIVE';
  }, [connection, loadEngines]);

  // the one socket; subscribed to the whole fleet so the fleet cards and the selected engine share it
  useEffect(() => {
    const m = new SocketManager(wsUrl(serverUrl));
    manager.current = m;
    m.subscribe('fleet');
    m.start();
    return () => { m.stop(); manager.current = null; };
  }, [serverUrl]);

  useEffect(() => {
    if (!engineId) return;
    let active = true;
    setFaults([]);
    fetch(`${serverUrl}/api/v1/faults?engine=${encodeURIComponent(engineId)}`, { cache: 'no-store' })
      .then(async (r) => { if (!r.ok) throw new Error(await readError(r)); return r.json() as Promise<{ faults: V1Fault[] }>; })
      .then((d) => { if (active) setFaults(d.faults); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : 'Fault list unavailable'); });
    return () => { active = false; };
  }, [engineId, serverUrl]);

  const command = useCallback(async (path: string, method: string, body?: unknown) => {
    if (!engineId) throw new Error('No engine selected');
    const response = await fetch(`${serverUrl}/api/v1/engines/${encodeURIComponent(engineId)}${path}`, {
      method, headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) throw new Error(await readError(response));
    return response.json();
  }, [engineId, serverUrl]);

  const profile = useMemo(() => engines.find((e) => e.engine_id === engineId) ?? null, [engines, engineId]);
  return {
    engines, engineId, selectEngine: setEngineId, profile, faults, fleet, slot, state: slot?.state ?? null,
    connection, error: error || streamError || '', command, refresh: loadEngines,
  };
}
