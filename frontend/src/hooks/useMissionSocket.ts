import { useEffect, useRef, useState, useCallback } from 'react';
import { MissionDefinition, MissionState } from '../types/mission';

function getWsUrl(serverUrl: string): string {
  try {
    const url = new URL(serverUrl);
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${url.host}/api/missions/ws`;
  } catch {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || '127.0.0.1:8000';
    return `${protocol}//${host}/api/missions/ws`;
  }
}

export function useMissionSocket(serverUrl: string) {
  const [missionState, setMissionState] = useState<MissionState | null>(null);
  const [definition, setDefinition] = useState<MissionDefinition | null>(null);
  const [templates, setTemplates] = useState<MissionDefinition[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const base = serverUrl.replace(/\/$/, '');

  // Fetch initial templates & definition
  const refreshTemplates = useCallback(async () => {
    try {
      const res = await fetch(`${base}/api/missions/templates`);
      if (res.ok) {
        const data = await res.json();
        setTemplates(data);
      }
    } catch (err) {
      console.warn('Failed to load mission templates:', err);
    }
  }, [base]);

  const refreshDefinition = useCallback(async () => {
    try {
      const res = await fetch(`${base}/api/missions/definition`);
      if (res.ok) {
        const data = await res.json();
        setDefinition(data);
      }
    } catch (err) {
      console.warn('Failed to load mission definition:', err);
    }
  }, [base]);

  useEffect(() => {
    refreshTemplates();
    refreshDefinition();
  }, [refreshTemplates, refreshDefinition]);

  // WebSocket Connection
  useEffect(() => {
    let unmounted = false;
    let ws: WebSocket | null = null;
    let timer: any;

    const connect = () => {
      if (unmounted) return;
      const wsUrl = getWsUrl(serverUrl);
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!unmounted) {
          setIsConnected(true);
          setError(null);
        }
      };

      ws.onmessage = (event) => {
        if (unmounted) return;
        try {
          const state: MissionState = JSON.parse(event.data);
          setMissionState(state);
        } catch {
          // ignore malformed
        }
      };

      ws.onclose = () => {
        if (!unmounted) {
          setIsConnected(false);
          timer = setTimeout(connect, 2000);
        }
      };

      ws.onerror = () => {
        if (!unmounted) {
          setError('Mission WebSocket connection failed');
        }
      };
    };

    connect();

    return () => {
      unmounted = true;
      clearTimeout(timer);
      if (ws) ws.close();
    };
  }, [serverUrl]);

  // REST Control Actions
  const loadMission = useCallback(async (defn: MissionDefinition) => {
    const res = await fetch(`${base}/api/missions/load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(defn),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    setDefinition(data.mission);
    setMissionState(data.state);
    return data;
  }, [base]);

  const startMission = useCallback(async () => {
    const res = await fetch(`${base}/api/missions/start`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }, [base]);

  const pauseMission = useCallback(async () => {
    const res = await fetch(`${base}/api/missions/pause`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }, [base]);

  const resumeMission = useCallback(async () => {
    const res = await fetch(`${base}/api/missions/resume`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }, [base]);

  const abortMission = useCallback(async () => {
    const res = await fetch(`${base}/api/missions/abort`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }, [base]);

  const derateMission = useCallback(async (scale: number = 0.85) => {
    const res = await fetch(`${base}/api/missions/derate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scale }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }, [base]);

  const setTimeScale = useCallback(async (scale: number) => {
    const res = await fetch(`${base}/api/missions/timescale`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scale }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }, [base]);

  const injectLiveFault = useCallback(async (mode: string, cylinder?: number, severity: number = 0.8, ramp_sec: number = 10.0) => {
    const res = await fetch(`${base}/api/missions/faults`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, cylinder, severity, ramp_sec }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }, [base]);

  const clearFaults = useCallback(async () => {
    const res = await fetch(`${base}/api/missions/faults`, { method: 'DELETE' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }, [base]);

  return {
    missionState,
    definition,
    templates,
    isConnected,
    error,
    refreshTemplates,
    refreshDefinition,
    loadMission,
    startMission,
    pauseMission,
    resumeMission,
    abortMission,
    derateMission,
    setTimeScale,
    injectLiveFault,
    clearFaults,
  };
}
