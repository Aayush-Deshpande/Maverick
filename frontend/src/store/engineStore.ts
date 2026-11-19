/* Single client store (card M0-09, A A6, R 19.3). Every component reads engine state from here; nothing else opens
   a socket or polls. Fed only by src/api/socket.ts. */
import { createStore } from 'zustand/vanilla';
import { useStore } from 'zustand';
import type { StateMessage } from '../api/state';

/* Data-age thresholds for the connection badge (R 19.3: STALE after 2 s, DISCONNECTED after 10 s; T-UI-3). */
export const STALE_AFTER_MS = 2000;
export const DISCONNECTED_AFTER_MS = 10000;

export type Connection = 'CONNECTING' | 'LIVE' | 'STALE' | 'DISCONNECTED';

export interface EngineSlot {
  state: StateMessage;
  receivedAt: number;      // client clock, ms; used ONLY for data age, never for charts (R 19.3: charts use sim time)
  dropped: number;         // seq gaps seen (latest-only server queues drop frames on slow links)
  restarted: boolean;      // seq went backwards: the server restarted, local state was reset
}

export interface EngineStoreState {
  connection: Connection;
  engines: Record<string, EngineSlot>;
  lastError: string | null;
  apply: (msg: StateMessage, now: number) => void;
  setConnection: (c: Connection) => void;
  setError: (e: string | null) => void;
  /* Re-evaluate LIVE/STALE/DISCONNECTED from data age; called by a timer. */
  tick: (now: number) => void;
}

export const createEngineStore = () =>
  createStore<EngineStoreState>((set, get) => ({
    connection: 'CONNECTING',
    engines: {},
    lastError: null,
    apply: (msg, now) => {
      const prev = get().engines[msg.engine_id];
      let dropped = prev ? prev.dropped : 0;   // a frame counter starts at zero (not a reading)
      let restarted = false;
      if (prev) {
        if (msg.seq <= prev.state.seq) {
          if (msg.seq === prev.state.seq) return;          // duplicate (snapshot after resubscribe)
          restarted = true;                                  // server restarted: start over from this message
          dropped = 0;
        } else if (msg.seq > prev.state.seq + 1) {
          dropped += msg.seq - prev.state.seq - 1;
        }
      }
      set({
        engines: { ...get().engines, [msg.engine_id]: { state: msg, receivedAt: now, dropped, restarted } },
        connection: 'LIVE',
      });
    },
    setConnection: (connection) => set({ connection }),
    setError: (lastError) => set({ lastError }),
    tick: (now) => {
      const slots = Object.values(get().engines);
      if (slots.length === 0) return;
      const newest = Math.max(...slots.map((s) => s.receivedAt));
      const age = now - newest;
      const next: Connection = age >= DISCONNECTED_AFTER_MS ? 'DISCONNECTED' : age >= STALE_AFTER_MS ? 'STALE' : 'LIVE';
      if (next !== get().connection) set({ connection: next });
    },
  }));

export const engineStore = createEngineStore();

export function useEngineStore<T>(selector: (s: EngineStoreState) => T): T {
  return useStore(engineStore, selector);
}

/* Data age of one engine in ms, or null when there is no data (shown as NO DATA, never as 0). */
export function dataAgeMs(slot: EngineSlot | undefined, now: number): number | null {
  return slot ? now - slot.receivedAt : null;
}
