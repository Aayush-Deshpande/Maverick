import { useState, useEffect, useRef, useCallback } from 'react';
import { UnifiedTelemetryState, ControlCommand } from '../types/telemetry';

const DEFAULT_STATE: UnifiedTelemetryState = {
  timestamp: Date.now() / 1000,
  sortie_id: 'SORTIE-CONNECTING',
  is_engine_running: true,
  active_commanded_fault_id: 0,
  active_commanded_fault_name: 'NOMINAL',
  telemetry: {
    ENGINE_RPM: 0,
    PROP_RPM: 0,
    TPS: 0,
    CHT_1: 95,
    CHT_2: 95,
    CHT_3: 95,
    CHT_4: 95,
    EGT_1: 780,
    EGT_2: 780,
    EGT_3: 780,
    EGT_4: 780,
    OIL_PRESS: 0,
    OIL_TEMP: 90,
    FUEL_FLOW: 0,
    FUEL_RAIL_P: 0,
    MAP: 88,
    VIB_GEARBOX_RMS: 0,
    BUS_VOLTAGE: 12.4,
    BATTERY_CURRENT: 0,
    FADEC_ACTIVE_LANE: 'LANE_A',
    ALTITUDE_FT: 18500,
    OAT_C: -22,
    TAS_KNOTS: 90,
    FLIGHT_PHASE: 'CRUISE_LOITER',
    THEATER: 'LADAKH',
  },
  analytics: {
    residuals: {},
    anomaly_score: 0,
    health_index: 1.0,
    diagnosed_fault_id: 0,
    diagnosed_fault_name: 'NOMINAL_FLIGHT',
    diagnosed_confidence: 0.99,
    target_3d_mesh: 'All',
    target_parts: [],
    ata_chapter: 'ATA 00-00',
    subsystem: 'PROPULSION_CORE',
    severity: 'NORMAL',
    root_cause: 'Connecting to propulsion telemetry server...',
    prescriptive_action: 'Ensure backend server is running.',
    emergency_checklist: [],
    maintenance_order: 'No maintenance required.',
    go_no_go: 'GO',
    go_no_go_reason: 'Awaiting data link.',
    rul_p10_hours: 500.0,
    rul_p50_hours: 500.0,
    limiting_component: null,
    planned_sortie_hours: 18.0,
    rul_by_component: {},
    sensor_sanity: {
      all_sensors_valid: true,
      drift_detected: false,
      failed_channels: [],
      suppressed_anomaly: false,
      advisory: 'Awaiting data link.',
    },
    subsystem_health: {
      propulsion: 1.0,
      fuel_system: 1.0,
      electrical: 1.0,
      thermal: 1.0,
      mechanical: 1.0,
    },
    causal_chain: [],
  },
};

function normalizeBackendUrl(url: string): string {
  let clean = url.trim().replace(/\/+$/, '');
  if (!clean.startsWith('http://') && !clean.startsWith('https://')) {
    clean = 'http://' + clean;
  }
  // Automatically strip :8000 if using HTTPS on a cloud host (Render, Railway, Vercel) where port 8000 is not exposed
  if (clean.startsWith('https://') && clean.endsWith(':8000')) {
    clean = clean.slice(0, -5);
  }
  return clean;
}

export function useTelemetrySocket() {
  const [serverUrl, setServerUrlState] = useState<string>(() => {
    const saved = localStorage.getItem('rotax_backend_url');
    if (saved) return normalizeBackendUrl(saved);
    // Deployed builds (e.g. Vercel) set VITE_API_URL to the hosted backend's public HTTPS URL.
    const envUrl = import.meta.env.VITE_API_URL as string | undefined;
    if (envUrl) return normalizeBackendUrl(envUrl);
    const isLocal = typeof window !== 'undefined' && ['localhost', '127.0.0.1', '0.0.0.0'].includes(window.location.hostname || '');
    if (isLocal) {
      return `http://${window.location.hostname || '127.0.0.1'}:8000`;
    }
    if (typeof window !== 'undefined' && window.location.hostname) {
      if (window.location.hostname.includes('onrender.com')) {
        const proto = window.location.protocol === 'https:' ? 'https:' : 'http:';
        return `${proto}//${window.location.hostname}`;
      }
      return 'https://anumaan-backend-5ru5.onrender.com';
    }
    return 'https://anumaan-backend-5ru5.onrender.com';
  });

  const [state, setState] = useState<UnifiedTelemetryState>(DEFAULT_STATE);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [latencyMs, setLatencyMs] = useState<number>(0);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const socketRef = useRef<WebSocket | null>(null);
  const pollIntervalRef = useRef<number | null>(null);
  const lastWsMessageAtRef = useRef<number | null>(null);

  const setServerUrl = (url: string) => {
    const cleanUrl = normalizeBackendUrl(url);
    localStorage.setItem('rotax_backend_url', cleanUrl);
    setServerUrlState(cleanUrl);
  };

  const sendCommand = useCallback(
    async (cmd: ControlCommand) => {
      // Try WebSocket first
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify(cmd));
        return;
      }

      // Fallback to HTTP POST
      try {
        const res = await fetch(`${serverUrl}/api/control`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'ngrok-skip-browser-warning': '69420',
          },
          body: JSON.stringify(cmd),
        });
        if (!res.ok) {
          console.error('[GCS] Command error:', await res.text());
        }
      } catch (err) {
        console.error('[GCS] HTTP command dispatch failed:', err);
      }
    },
    [serverUrl]
  );

  useEffect(() => {
    let isMounted = true;
    let ws: WebSocket | null = null;

    const wsUrl = serverUrl.replace(/^http/, 'ws') + '/ws/telemetry';

    let animFrameId: number | null = null;
    let pendingState: UnifiedTelemetryState | null = null;
    let lastLatencyUpdateAt = 0;

    function flushState() {
      if (pendingState && isMounted) {
        setState(pendingState);
        pendingState = null;
      }
      animFrameId = null;
    }

    function connectWebSocket() {
      try {
        ws = new WebSocket(wsUrl);
        socketRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
          setIsConnected(true);
          lastWsMessageAtRef.current = null;
          console.log('[GCS] Connected to Backend WebSocket at:', wsUrl);
        };

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'COMMAND_RESULT' || data.type === 'ERROR') {
              return;
            }
            if (data.telemetry && data.analytics) {
              pendingState = data;
              setIsConnected(true);

              const now = performance.now();
              if (lastWsMessageAtRef.current !== null && now - lastLatencyUpdateAt > 250) {
                setLatencyMs(Math.round(now - lastWsMessageAtRef.current));
                lastLatencyUpdateAt = now;
              }
              lastWsMessageAtRef.current = now;

              // Schedule smooth UI render on next animation frame
              if (!animFrameId) {
                animFrameId = requestAnimationFrame(flushState);
              }
            }
          } catch (e) {
            console.error('[GCS] JSON parse error:', e);
          }
        };

        ws.onerror = () => {
          if (!isMounted) return;
          setIsConnected(false);
        };

        ws.onclose = () => {
          if (!isMounted) return;
          setIsConnected(false);
          // Try reconnecting after 2 seconds
          setTimeout(connectWebSocket, 2000);
        };
      } catch (e) {
        console.warn('[GCS] WebSocket initialization failed, falling back to HTTP polling:', e);
      }
    }

    connectWebSocket();

    // Secondary HTTP polling fallback (ensures link even if WebSockets are blocked by proxies)
    pollIntervalRef.current = window.setInterval(async () => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        return; // WebSocket is healthy, no need to poll
      }

      const t0 = performance.now();
      try {
        const res = await fetch(`${serverUrl}/api/state`, {
          cache: 'no-store',
          headers: {
            'ngrok-skip-browser-warning': '69420',
          },
        });
        if (res.ok) {
          const data = await res.json();
          if (isMounted && data.telemetry) {
            setState(data);
            setIsConnected(true);
            setLatencyMs(Math.round(performance.now() - t0));
          }
        } else {
          if (isMounted) setIsConnected(false);
        }
      } catch {
        if (isMounted) setIsConnected(false);
      }
    }, 200);

    return () => {
      isMounted = false;
      if (animFrameId) cancelAnimationFrame(animFrameId);
      if (ws) ws.close();
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [serverUrl]);

  return {
    state,
    isConnected,
    latencyMs,
    serverUrl,
    setServerUrl,
    sendCommand,
    isModalOpen,
    setIsModalOpen,
  };
}
