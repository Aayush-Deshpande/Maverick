import React from 'react';
import { Play, Pause, Rewind, FastForward, History, AlertTriangle, AlertOctagon, Info } from 'lucide-react';
import { useMissionReplay, ReplaySpeed, ReplayEventMarker } from '../hooks/useMissionReplay';

interface MissionReplayScrubberProps {
  serverUrl: string;
}

function fmtClock(totalSec: number): string {
  if (!Number.isFinite(totalSec) || totalSec < 0) return '00:00:00';
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = Math.floor(totalSec % 60);
  return [h, m, s].map((v) => String(v).padStart(2, '0')).join(':');
}

const SEVERITY_DOT: Record<string, string> = {
  CRITICAL: 'bg-critical',
  WARNING: 'bg-warning',
  ADVISORY: 'bg-warning',
  NOMINAL: 'bg-success',
};

const SEVERITY_ICON: Record<string, React.ReactNode> = {
  CRITICAL: <AlertOctagon className="w-3.5 h-3.5 text-critical" />,
  WARNING: <AlertTriangle className="w-3.5 h-3.5 text-warning" />,
  ADVISORY: <AlertTriangle className="w-3.5 h-3.5 text-warning" />,
  NOMINAL: <Info className="w-3.5 h-3.5 text-success" />,
};

const SPEED_OPTIONS: ReplaySpeed[] = [1, 2, 5, 10];

/** Field name -> display label for the subset of telemetry_log.csv columns shown in the
 * scrubber's live dial readout while seeking (mirrors ReadingsPanel's gauge labels rather
 * than inventing new ones). */
const DIAL_FIELDS: Array<{ key: string; label: string; unit: string; digits?: number }> = [
  { key: 'ALTITUDE_FT', label: 'Altitude', unit: 'ft', digits: 0 },
  { key: 'AGL_M', label: 'AGL', unit: 'm', digits: 0 },
  { key: 'AIRSPEED_KIAS', label: 'Airspeed', unit: 'kt', digits: 0 },
  { key: 'ENGINE_RPM', label: 'RPM', unit: '', digits: 0 },
  { key: 'CHT_C', label: 'CHT', unit: '°C', digits: 1 },
  { key: 'OIL_PRESS_BAR', label: 'Oil Press', unit: 'bar', digits: 2 },
];

export const MissionReplayScrubber: React.FC<MissionReplayScrubberProps> = ({ serverUrl }) => {
  const replay = useMissionReplay(serverUrl);
  const total = replay.manifest?.total_duration_sec ?? 0;
  const progressPct = total > 0 ? (replay.currentTimeSec / total) * 100 : 0;

  const handleScrub = (e: React.ChangeEvent<HTMLInputElement>) => {
    replay.seek(Number(e.target.value));
  };

  const jumpToMarker = (marker: ReplayEventMarker) => replay.seek(marker.mission_elapsed_sec);

  return (
    <div className="surface-panel p-4 sm:p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-surface-border pb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-accent" />
          <div>
            <h2 className="text-xs font-semibold text-white">Historical Mission Replay</h2>
            <p className="text-[11px] text-slate-500">Scrub any recorded sortie — gauges and event markers sync to the exact timestamp.</p>
          </div>
        </div>

        <select
          className="bg-surface-card border border-surface-border text-[11px] text-slate-300 px-2 py-1.5 font-mono"
          value={replay.selectedMissionId ?? ''}
          onChange={(e) => e.target.value && replay.selectMission(e.target.value)}
        >
          <option value="" disabled>
            Select a sortie…
          </option>
          {replay.manifests.map((m) => (
            <option key={m.mission_id} value={m.mission_id}>
              {m.mission_id} — {m.name ?? m.sortie_id} ({m.severity ?? 'NOMINAL'})
            </option>
          ))}
        </select>
      </div>

      {replay.manifestsError && (
        <div className="text-[11px] text-critical border border-critical-muted bg-critical-dim px-3 py-2">
          {replay.manifestsError}
        </div>
      )}

      {!replay.manifest ? (
        <div className="text-[11px] text-slate-500 border border-surface-border bg-surface-card px-3 py-3">
          No sortie selected. Pick one above to load its telemetry and fault timeline.
        </div>
      ) : (
        <>
          {/* Timeline bar with event markers */}
          <div className="space-y-1.5">
            <div className="relative h-2 bg-surface-card border border-surface-border">
              <div className="absolute inset-y-0 left-0 bg-accent/50" style={{ width: `${progressPct}%` }} />
              {replay.manifest.event_markers.map((marker, i) => {
                const pct = total > 0 ? (marker.mission_elapsed_sec / total) * 100 : 0;
                return (
                  <button
                    key={i}
                    title={`${marker.title} (T+${fmtClock(marker.mission_elapsed_sec)})`}
                    onClick={() => jumpToMarker(marker)}
                    className={`absolute -top-1 w-2.5 h-2.5 rounded-full border border-black/40 ${
                      SEVERITY_DOT[marker.severity] || 'bg-slate-400'
                    }`}
                    style={{ left: `calc(${pct}% - 5px)` }}
                  />
                );
              })}
            </div>
            <input
              type="range"
              min={0}
              max={total}
              step={0.1}
              value={replay.currentTimeSec}
              onChange={handleScrub}
              className="w-full accent-accent"
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-500">
              <span>{fmtClock(replay.currentTimeSec)}</span>
              <span>{fmtClock(total)}</span>
            </div>
          </div>

          {/* VCR controls */}
          <div className="flex items-center justify-center gap-2 flex-wrap">
            <button
              onClick={replay.stepBack}
              className="px-2.5 py-1.5 border border-surface-border bg-surface-card text-slate-300 hover:text-white flex items-center gap-1 text-[11px]"
            >
              <Rewind className="w-3.5 h-3.5" /> -10s
            </button>
            <button
              onClick={replay.togglePlay}
              className="px-3 py-1.5 border border-accent bg-accent-dim text-accent hover:bg-accent/20 flex items-center gap-1.5 text-[11px] font-medium"
            >
              {replay.isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              {replay.isPlaying ? 'Pause' : 'Play'}
            </button>
            <button
              onClick={replay.stepForward}
              className="px-2.5 py-1.5 border border-surface-border bg-surface-card text-slate-300 hover:text-white flex items-center gap-1 text-[11px]"
            >
              +10s <FastForward className="w-3.5 h-3.5" />
            </button>
            <div className="flex items-center gap-1 ml-2">
              {SPEED_OPTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => replay.setSpeed(s)}
                  className={`px-2 py-1.5 border text-[11px] font-mono ${
                    replay.speed === s
                      ? 'border-accent bg-accent-dim text-accent'
                      : 'border-surface-border bg-surface-card text-slate-400 hover:text-white'
                  }`}
                >
                  {s}x
                </button>
              ))}
            </div>
          </div>

          {/* Live dial readout at the scrubbed timestamp */}
          {replay.frame && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
              {DIAL_FIELDS.map(({ key, label, unit, digits }) => {
                const raw = replay.frame?.[key];
                const val = typeof raw === 'number' ? raw.toFixed(digits ?? 1) : '--';
                return (
                  <div key={key} className="surface-panel p-2.5 text-center">
                    <div className="text-[9px] uppercase tracking-wide text-slate-500">{label}</div>
                    <div className="text-sm font-mono font-semibold text-white">
                      {val}
                      {unit && <span className="text-[10px] text-slate-500 ml-0.5">{unit}</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Event marker log */}
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {replay.manifest.event_markers.map((marker, i) => (
              <button
                key={i}
                onClick={() => jumpToMarker(marker)}
                className="w-full flex items-start gap-2 text-left px-2 py-1.5 border border-surface-border/60 bg-surface-card hover:border-accent/60"
              >
                {SEVERITY_ICON[marker.severity] || <Info className="w-3.5 h-3.5 text-slate-500" />}
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-slate-500">T+{fmtClock(marker.mission_elapsed_sec)}</span>
                    <span className="text-[11px] font-medium text-slate-200 truncate">{marker.title}</span>
                  </div>
                  <p className="text-[10px] text-slate-500 truncate">{marker.detail}</p>
                </div>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
