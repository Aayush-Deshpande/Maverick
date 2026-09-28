import { useCallback, useEffect, useRef, useState } from 'react';

export interface EngineFault {
  mode: string;
  per_cylinder: boolean;
  scalar_visible: boolean;
  layer: string;
  description: string;
}
export interface EngineProfile {
  engine_id: string;
  display_name?: string;
  n_cylinders: number;
  turbocharged: boolean;
  compression_ignition: boolean;
  ready: boolean;
  heavy_ready: boolean;
  tail_id: string;
  commanded_faults: Array<{ mode: string; cylinder?: number | null; severity: number; origin: string }>;
  faults: EngineFault[];
}
export interface EngineDiagnosisHypothesis {
  mode_id: string;
  location: string | null;
  probability: number;
  ambiguity_group_id: string;
  supporting_evidence: string[];
  operator_text: string;
  engineer_text: string;
  maintainer_text: string;
  ata_chapter: string;
}

export interface EngineFrame {
  engine_id: string;
  t: number;
  source: string;
  evidence_class: string;
  channels: Record<string, number>;
  cht: number[];
  egt: number[];
  detection: null | { scores: Record<string, number>; ratios: Record<string, number>; raw_alarm: boolean; confirmed: boolean; top_channels: Array<string | [string, number]> };
  heavy: null | { label: string; classes: string[]; scores: number[] };
  diagnosis?: EngineDiagnosisHypothesis[] | null;
}
interface EngineIndex { selected: string; tick: number; engines: EngineProfile[] }
export interface EngineSchema { channels: Array<{ name: string; unit: string; kind: string; cylinder: number | null; required: boolean }>; operating_limits: Record<string, unknown>; components: string[]; provenance_summary: Record<string, number> }
export interface FleetMember { engine_id: string; ready: boolean; selected?: boolean; t?: number; rpm?: number; max_cht?: number; max_egt?: number; raw_alarm?: boolean | null; confirmed?: boolean | null; top_channels?: string[] }

export function useEngineRuntime(serverUrl: string) {
  const [catalog, setCatalog] = useState<EngineIndex | null>(null);
  const [schema, setSchema] = useState<EngineSchema | null>(null);
  const [fleet, setFleet] = useState<FleetMember[]>([]);
  const [engineId, setEngineId] = useState('rotax_912is');
  const [frame, setFrame] = useState<EngineFrame | null>(null);
  const [connected, setConnected] = useState(false);
  const [latencyMs, setLatencyMs] = useState(0);
  const [error, setError] = useState('');
  const socket = useRef<WebSocket | null>(null);
  const profile = catalog?.engines.find((engine) => engine.engine_id === engineId) ?? null;

  const refreshCatalog = useCallback(async () => {
    try {
      const response = await fetch(`${serverUrl}/api/engines`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`Engine list returned ${response.status}`);
      const data = await response.json() as EngineIndex;
      setCatalog(data);
      setError('');
      if (data.engines.length && !data.engines.some((engine) => engine.engine_id === engineId)) setEngineId(data.selected || data.engines[0].engine_id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Cannot reach engine runtime'); }
  }, [serverUrl, engineId]);

  useEffect(() => { void refreshCatalog(); const id = window.setInterval(() => void refreshCatalog(), 3000); return () => clearInterval(id); }, [refreshCatalog]);

  useEffect(() => {
    let active = true;
    setSchema(null);
    fetch(`${serverUrl}/api/engines/${encodeURIComponent(engineId)}/schema`, { cache: 'no-store' })
      .then((response) => { if (!response.ok) throw new Error(`Profile schema returned ${response.status}`); return response.json() as Promise<EngineSchema>; })
      .then((data) => { if (active) setSchema(data); })
      .catch(() => { if (active) setSchema(null); });
    return () => { active = false; };
  }, [engineId, serverUrl]);

  useEffect(() => {
    let active = true;
    let ws: WebSocket | null = null;
    let retry: number | undefined;
    const connect = () => {
      if (!active) return;
      ws = new WebSocket(`${serverUrl.replace(/^http/, 'ws')}/ws/fleet`);
      ws.onmessage = (event) => { if (active) { try { setFleet((JSON.parse(event.data) as { engines: FleetMember[] }).engines); } catch { /* ignore malformed fleet snapshot */ } } };
      ws.onclose = () => { if (active) retry = window.setTimeout(connect, 2000); };
    };
    connect();
    return () => { active = false; if (retry) clearTimeout(retry); ws?.close(); };
  }, [serverUrl]);

  useEffect(() => {
    setFrame(null); setConnected(false);
    const base = serverUrl.replace(/^http/, 'ws');
    let active = true;
    let ws: WebSocket | null = null;
    let retry: number | undefined;
    let poll: number | undefined;
    const connect = () => {
      if (!active) return;
      ws = new WebSocket(`${base}/ws/engines/${encodeURIComponent(engineId)}`);
      socket.current = ws;
      ws.onopen = () => { if (active) setConnected(true); };
      ws.onmessage = (event) => { if (!active) return; try { setFrame(JSON.parse(event.data) as EngineFrame); setConnected(true); } catch { setError('Received an unreadable engine frame'); } };
      ws.onerror = () => { if (active) setConnected(false); };
      ws.onclose = () => { if (active) { setConnected(false); retry = window.setTimeout(connect, 1500); } };
    };
    connect();
    poll = window.setInterval(async () => {
      if (!active || socket.current?.readyState === WebSocket.OPEN) return;
      const started = performance.now();
      try {
        const response = await fetch(`${serverUrl}/api/engines/${encodeURIComponent(engineId)}/state`, { cache: 'no-store' });
        if (!response.ok) return;
        setFrame(await response.json() as EngineFrame); setLatencyMs(Math.round(performance.now() - started)); setConnected(true);
      } catch { if (active) setConnected(false); }
    }, 1000);
    return () => { active = false; if (retry) clearTimeout(retry); if (poll) clearInterval(poll); ws?.close(); if (socket.current === ws) socket.current = null; };
  }, [engineId, serverUrl]);

  const selectEngine = useCallback(async (id: string) => {
    setEngineId(id);
    try {
      const response = await fetch(`${serverUrl}/api/engines/select`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ engine_id: id }) });
      if (!response.ok) throw new Error(`Engine selection returned ${response.status}`);
    }
    catch { setError('Could not select engine; reconnecting to its stream'); }
  }, [serverUrl]);
  const command = useCallback(async (path: string, method: string, body?: unknown) => {
    const response = await fetch(`${serverUrl}/api/engines/${encodeURIComponent(engineId)}${path}`, { method, headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined });
    if (!response.ok) throw new Error((await response.text()) || `Request failed (${response.status})`);
    return response.status === 204 ? null : response.json();
  }, [engineId, serverUrl]);
  return { catalog, fleet, profile, schema, engineId, selectEngine, frame, connected, latencyMs, error, command, refreshCatalog };
}
