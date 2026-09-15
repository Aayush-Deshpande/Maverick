import { useCallback, useEffect, useRef, useState } from 'react';

// Historical Mission Replay & Scrubber (PRD F12 / final_tasks/02_HISTORICAL_MISSION_REPLAY_AND_SCRUBBER.md).
// Talks to backend/telemetry/replay_engine.py via the /api/replay/* endpoints added in
// backend/server/main.py. Mirrors the request-shape/base-URL convention already used by
// useTelemetrySocket.ts (a plain `http://host:port` serverUrl passed in by the caller) rather
// than inventing a second connection-config story for this one feature.

export interface ReplayManifestSummary {
  mission_id: string;
  sortie_id?: string;
  name?: string;
  uav_tail_number?: string;
  region?: string;
  status?: string;
  severity?: string;
  start_time?: string;
  end_time?: string;
  duration_hours?: number;
  fault_count?: number;
  health_index_start?: number;
  health_index_end?: number;
}

export interface ReplayEventMarker {
  timestamp_epoch: number;
  mission_elapsed_sec: number;
  event_type: string;
  severity: string;
  title: string;
  detail: string;
}

export interface ReplayManifest {
  mission_id: string;
  sortie_id?: string;
  region?: string;
  total_duration_sec: number;
  event_markers: ReplayEventMarker[];
}

// Raw telemetry_log.csv row, passed through as-is by the backend — field names match the
// CSV header exactly (ALTITUDE_M, CHT_C, AGL_M, ...), not a translated/camelCased shape.
export type ReplayFrame = Record<string, number | string | null>;

export type ReplaySpeed = 1 | 2 | 5 | 10;

// Network fetches are throttled to this cadence regardless of playback speed — the source
// telemetry itself samples at roughly this rate, so fetching faster than the data actually
// changes would only add load without improving what's shown (this is what keeps 10x scrubbing
// smooth without flooding the API, per the task doc's own performance requirement).
const FETCH_THROTTLE_MS = 150;

function apiBase(serverUrl: string): string {
  return serverUrl.replace(/\/$/, '');
}

export function useMissionReplay(serverUrl: string) {
  const [manifests, setManifests] = useState<ReplayManifestSummary[]>([]);
  const [manifestsError, setManifestsError] = useState<string | null>(null);
  const [selectedMissionId, setSelectedMissionId] = useState<string | null>(null);
  const [manifest, setManifest] = useState<ReplayManifest | null>(null);

  const [currentTimeSec, setCurrentTimeSec] = useState(0);
  const [frame, setFrame] = useState<ReplayFrame | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<ReplaySpeed>(1);

  const rafRef = useRef<number | null>(null);
  const lastTickRef = useRef<number | null>(null);
  const lastFetchAtRef = useRef(0);
  const inFlightRef = useRef(false);
  const currentTimeRef = useRef(0); // mirrors currentTimeSec for the rAF loop without a stale closure

  useEffect(() => {
    currentTimeRef.current = currentTimeSec;
  }, [currentTimeSec]);

  // ------------------------------------------------------------------
  // Manifest listing / selection
  // ------------------------------------------------------------------

  const refreshManifests = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase(serverUrl)}/api/replay/manifests`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setManifests(data.manifests || []);
      setManifestsError(null);
    } catch (e) {
      setManifestsError(e instanceof Error ? e.message : 'Failed to load replay manifests');
    }
  }, [serverUrl]);

  useEffect(() => {
    refreshManifests();
  }, [refreshManifests]);

  const selectMission = useCallback(
    async (missionId: string) => {
      setIsPlaying(false);
      setSelectedMissionId(missionId);
      setManifest(null);
      setFrame(null);
      setCurrentTimeSec(0);
      try {
        const res = await fetch(`${apiBase(serverUrl)}/api/replay/${missionId}/manifest`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: ReplayManifest = await res.json();
        setManifest(data);
      } catch (e) {
        setManifestsError(e instanceof Error ? e.message : `Failed to load manifest for ${missionId}`);
      }
    },
    [serverUrl]
  );

  // ------------------------------------------------------------------
  // Frame fetching (throttled, always the freshest request wins)
  // ------------------------------------------------------------------

  const fetchFrame = useCallback(
    async (timeSec: number) => {
      if (!selectedMissionId || inFlightRef.current) return;
      inFlightRef.current = true;
      try {
        const res = await fetch(
          `${apiBase(serverUrl)}/api/replay/${selectedMissionId}/frame?time_sec=${timeSec.toFixed(3)}`
        );
        if (res.ok) {
          setFrame(await res.json());
        }
      } catch {
        // a dropped frame fetch mid-scrub is not worth surfacing as an error — the next
        // tick/seek will simply try again
      } finally {
        inFlightRef.current = false;
      }
    },
    [serverUrl, selectedMissionId]
  );

  const seek = useCallback(
    (timeSec: number) => {
      const total = manifest?.total_duration_sec ?? Infinity;
      const clamped = Math.max(0, Math.min(timeSec, total));
      setCurrentTimeSec(clamped);
      currentTimeRef.current = clamped;
      lastFetchAtRef.current = 0; // force an immediate fetch on explicit seek, bypassing the throttle
      fetchFrame(clamped);
    },
    [manifest, fetchFrame]
  );

  const stepBack = useCallback(() => seek(currentTimeRef.current - 10), [seek]);
  const stepForward = useCallback(() => seek(currentTimeRef.current + 10), [seek]);

  // ------------------------------------------------------------------
  // Playback clock — a single requestAnimationFrame loop, not a setInterval, so it never
  // drifts against actual wall-clock time regardless of tab throttling/re-renders.
  // ------------------------------------------------------------------

  useEffect(() => {
    if (!isPlaying || !manifest) {
      lastTickRef.current = null;
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      return;
    }

    const tick = (now: number) => {
      if (lastTickRef.current === null) lastTickRef.current = now;
      const dtSec = (now - lastTickRef.current) / 1000;
      lastTickRef.current = now;

      const total = manifest.total_duration_sec;
      let next = currentTimeRef.current + dtSec * speed;
      if (next >= total) {
        next = total;
        setIsPlaying(false);
      }
      currentTimeRef.current = next;
      setCurrentTimeSec(next);

      if (now - lastFetchAtRef.current >= FETCH_THROTTLE_MS) {
        lastFetchAtRef.current = now;
        fetchFrame(next);
      }

      if (next < total) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlaying, speed, manifest, fetchFrame]);

  const play = useCallback(() => {
    if (manifest && currentTimeRef.current >= manifest.total_duration_sec) {
      seek(0);
    }
    setIsPlaying(true);
  }, [manifest, seek]);

  const pause = useCallback(() => setIsPlaying(false), []);
  const togglePlay = useCallback(() => (isPlaying ? pause() : play()), [isPlaying, play, pause]);

  return {
    manifests,
    manifestsError,
    refreshManifests,
    selectedMissionId,
    manifest,
    selectMission,

    currentTimeSec,
    frame,
    isPlaying,
    speed,
    setSpeed,

    play,
    pause,
    togglePlay,
    seek,
    stepBack,
    stepForward,
  };
}
