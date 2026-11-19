import { describe, expect, it, vi, afterEach } from 'vitest';
import { createEngineStore, DISCONNECTED_AFTER_MS, STALE_AFTER_MS, dataAgeMs } from './engineStore';
import { SocketManager, RECONNECT_MIN_MS, wsUrl, type SocketLike } from '../api/socket';
import type { StateMessage } from '../api/state';

const msg = (engine_id: string, seq: number): StateMessage =>
  ({ engine_id, seq, sim_time_s: seq, wall_time_iso: '', readings: {}, status: { level: 'UNKNOWN' } } as unknown as StateMessage);

describe('engine store (M0-09)', () => {
  it('keeps the latest message per engine and counts dropped frames', () => {
    const s = createEngineStore();
    s.getState().apply(msg('a', 1), 0);
    s.getState().apply(msg('a', 4), 10);
    s.getState().apply(msg('b', 1), 10);
    expect(s.getState().engines.a.state.seq).toBe(4);
    expect(s.getState().engines.a.dropped).toBe(2);
    expect(Object.keys(s.getState().engines)).toEqual(['a', 'b']);
  });

  it('ignores a duplicate snapshot and resets on a server restart', () => {
    const s = createEngineStore();
    s.getState().apply(msg('a', 5), 0);
    s.getState().apply(msg('a', 5), 50);
    expect(s.getState().engines.a.receivedAt).toBe(0);
    s.getState().apply(msg('a', 1), 60);
    expect(s.getState().engines.a.restarted).toBe(true);
    expect(s.getState().engines.a.state.seq).toBe(1);
  });

  it('goes STALE after 2 s and DISCONNECTED after 10 s without data (T-UI-3)', () => {
    const s = createEngineStore();
    s.getState().apply(msg('a', 1), 0);
    expect(s.getState().connection).toBe('LIVE');
    s.getState().tick(STALE_AFTER_MS);
    expect(s.getState().connection).toBe('STALE');
    s.getState().tick(DISCONNECTED_AFTER_MS);
    expect(s.getState().connection).toBe('DISCONNECTED');
    s.getState().apply(msg('a', 2), DISCONNECTED_AFTER_MS + 1);
    expect(s.getState().connection).toBe('LIVE');
  });

  it('reports no data age (null) for an engine without data, never 0', () => {
    expect(dataAgeMs(undefined, 1000)).toBeNull();
  });
});

class FakeSocket implements SocketLike {
  static all: FakeSocket[] = [];
  readyState = 0;
  sent: string[] = [];
  onopen: ((ev: unknown) => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: ((ev: unknown) => void) | null = null;
  onerror: ((ev: unknown) => void) | null = null;
  constructor(public url: string) { FakeSocket.all.push(this); }
  send(d: string) { this.sent.push(d); }
  close() { this.readyState = 3; this.onclose?.({}); }
  serverOpen() { this.readyState = 1; this.onopen?.({}); }
  serverSend(o: unknown) { this.onmessage?.({ data: JSON.stringify(o) }); }
  serverDrop() { this.readyState = 3; this.onclose?.({}); }
}

describe('socket manager (M0-09)', () => {
  afterEach(() => { vi.useRealTimers(); FakeSocket.all = []; });

  it('uses one socket, subscribes on open, and feeds the store', () => {
    const store = createEngineStore();
    const m = new SocketManager('ws://x/ws/v1', (u) => new FakeSocket(u), store, () => 100);
    m.subscribe(['a']);
    m.start();
    const ws = FakeSocket.all[0];
    ws.serverOpen();
    expect(ws.sent).toEqual([JSON.stringify({ subscribe: ['a'] })]);
    ws.serverSend(msg('a', 1));
    expect(store.getState().engines.a.state.seq).toBe(1);
    expect(FakeSocket.all).toHaveLength(1);
    m.stop();
  });

  it('reconnects with backoff and re-subscribes (resync by snapshot)', () => {
    vi.useFakeTimers();
    const store = createEngineStore();
    const m = new SocketManager('ws://x/ws/v1', (u) => new FakeSocket(u), store, () => 0);
    m.subscribe('fleet');
    m.start();
    FakeSocket.all[0].serverOpen();
    FakeSocket.all[0].serverDrop();
    expect(store.getState().connection).toBe('DISCONNECTED');
    vi.advanceTimersByTime(RECONNECT_MIN_MS);
    expect(FakeSocket.all).toHaveLength(2);
    FakeSocket.all[1].serverOpen();
    expect(FakeSocket.all[1].sent).toEqual([JSON.stringify({ subscribe: 'fleet' })]);
    m.stop();
  });

  it('surfaces server errors instead of ignoring them', () => {
    const store = createEngineStore();
    const m = new SocketManager('ws://x/ws/v1', (u) => new FakeSocket(u), store, () => 0);
    m.start();
    FakeSocket.all[0].serverSend({ type: 'error', message: 'unknown engines' });
    expect(store.getState().lastError).toBe('unknown engines');
    m.stop();
  });

  it('derives ws/wss from the page origin, never a fixed host', () => {
    expect(wsUrl('https://demo.example')).toBe('wss://demo.example/ws/v1');
    expect(wsUrl('http://127.0.0.1:8000/')).toBe('ws://127.0.0.1:8000/ws/v1');
  });
});
