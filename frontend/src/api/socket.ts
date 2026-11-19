/* The ONE WebSocket per client (card M0-09, DECISIONS D3): /ws/v1 with {"subscribe": ...}. Reconnects with backoff
   and re-subscribes; the server sends a snapshot on every subscribe, so a reconnect is also the resync (R 19.3). */
import type { StateMessage } from './state';
import { engineStore, type EngineStoreState } from '../store/engineStore';

/* Reconnect backoff (ms): first retry fast, then capped so a sleeping laptop does not hammer the server. */
export const RECONNECT_MIN_MS = 500;
export const RECONNECT_MAX_MS = 8000;
/* How often the connection badge re-checks data age. */
export const AGE_CHECK_MS = 500;

export interface SocketLike {
  readyState: number;
  onopen: ((ev: unknown) => void) | null;
  onmessage: ((ev: { data: string }) => void) | null;
  onclose: ((ev: unknown) => void) | null;
  onerror: ((ev: unknown) => void) | null;
  send: (data: string) => void;
  close: () => void;
}

export type SocketFactory = (url: string) => SocketLike;
const OPEN = 1;

/* ws:// or wss:// from the page's own origin (or an explicit http(s) base), never a hard-coded host (audit #62). */
export function wsUrl(base?: string): string {
  const origin = base ?? (typeof window !== 'undefined' ? window.location.origin : '');
  return origin.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws/v1';
}

export class SocketManager {
  private ws: SocketLike | null = null;
  private wanted: string[] | 'fleet' = [];
  private retryMs = RECONNECT_MIN_MS;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private ageTimer: ReturnType<typeof setInterval> | null = null;
  private stopped = false;

  constructor(
    private readonly url: string,
    private readonly factory: SocketFactory = (u) => new WebSocket(u) as unknown as SocketLike,
    private readonly store: { getState: () => EngineStoreState } = engineStore,
    private readonly now: () => number = () => Date.now(),
  ) {}

  start(): void {
    this.stopped = false;
    this.open();
    this.ageTimer = setInterval(() => this.store.getState().tick(this.now()), AGE_CHECK_MS);
  }

  stop(): void {
    this.stopped = true;
    if (this.retryTimer) clearTimeout(this.retryTimer);
    if (this.ageTimer) clearInterval(this.ageTimer);
    this.ws?.close();
    this.ws = null;
  }

  subscribe(engines: string[] | 'fleet'): void {
    this.wanted = engines;
    if (this.ws?.readyState === OPEN) this.ws.send(JSON.stringify({ subscribe: engines }));
  }

  private open(): void {
    const s = this.store.getState();
    s.setConnection('CONNECTING');
    const ws = this.factory(this.url);
    this.ws = ws;
    ws.onopen = () => {
      this.retryMs = RECONNECT_MIN_MS;
      if (this.wanted === 'fleet' || this.wanted.length) ws.send(JSON.stringify({ subscribe: this.wanted }));
    };
    ws.onmessage = (ev) => this.handle(ev.data);
    ws.onerror = () => this.store.getState().setError('connection error');
    ws.onclose = () => {
      if (this.ws !== ws) return;
      this.ws = null;
      if (this.stopped) return;
      this.store.getState().setConnection('DISCONNECTED');
      this.retryTimer = setTimeout(() => this.open(), this.retryMs);
      this.retryMs = Math.min(this.retryMs * 2, RECONNECT_MAX_MS);
    };
  }

  private handle(raw: string): void {
    let msg: unknown;
    try {
      msg = JSON.parse(raw);
    } catch {
      this.store.getState().setError('unreadable message from server');
      return;
    }
    const m = msg as { type?: string; message?: string; engine_id?: string };
    if (m.type === 'error') this.store.getState().setError(m.message ?? 'server error');
    else if (m.type === 'subscribed') this.store.getState().setError(null);
    else if (m.engine_id) this.store.getState().apply(msg as StateMessage, this.now());
  }
}
