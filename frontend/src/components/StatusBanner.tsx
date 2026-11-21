import { useEffect, useRef, useState } from 'react';
import type { AlertOut, Reason1, Status } from '../api/state';
import { playAlertTone, toneFor } from '../utils/alertTone';
import { channelLabel, useLabels } from '../utils/labels';
import { NO_DATA, num } from '../utils/format';
import InfoTooltip from './InfoTooltip';

type Props = {
  engineId: string | null;
  status: Status | null | undefined;
  alerts: AlertOut[];
  simTimeS: number | null | undefined;
  units?: Record<string, string>;                         // channel -> unit, from the readings
  api: (path: string, method: string, body?: unknown) => Promise<any>;
  onNotice: (text: string) => void;
};

const SHELVE_S = 600;                                     // operator shelve period offered in the UI (10 min)

// D4 / 14 CFR 25.1322: red = NO-GO (warning), amber = CAUTION, cyan = ADVISORY; GO and ENGINE OFF are not alerts.
const LEVEL_STYLE: Record<string, string> = {
  'NO-GO': 'border-critical bg-critical-dim text-critical',
  CAUTION: 'border-warning bg-warning-dim text-warning',
  ADVISORY: 'border-cyan-600/60 bg-cyan-500/10 text-cyan-700',
};

/** Engine status banner and alert list (M6-02): level, every reason with its value and limit, latch and
 *  acknowledge, and per-alert acknowledge / shelve. Everything comes from the state message. */
/** One reason in plain words: the channel's name, its reading and the limit it crossed. */
function reasonText(r: Reason1, label: (id: string) => string, unit: (id: string) => string): string {
  if (r.value == null || r.limit == null) return r.text;
  if (!r.channel) return `${r.text} (${num(r.value, 2)} vs limit ${num(r.limit, 2)})`;
  const side = /LOW/.test(r.code) ? 'below' : /HIGH/.test(r.code) ? 'above' : 'outside';
  const band = /WARNING/.test(r.code) ? 'warning' : /CAUTION/.test(r.code) ? 'caution' : 'normal';
  const u = unit(r.channel);
  return `${label(r.channel)} ${num(r.value, 2)} ${u}, ${side} the ${band} limit of ${num(r.limit, 2)} ${u}`.replace(/\s+,/g, ',').trim();
}

export default function StatusBanner({ engineId, status, alerts, simTimeS, units, api, onNotice }: Props) {
  const labels = useLabels();
  const say = labels.status[status?.level ?? 'UNKNOWN'];
  const level = status?.level ?? 'UNKNOWN';
  const [muted, setMuted] = useState(false);
  const prev = useRef<string | undefined>(undefined);
  useEffect(() => {                                       // aural alert on entering CAUTION / NO-GO (U2)
    const tone = toneFor(prev.current, status?.level);
    prev.current = status?.level;
    if (tone && !muted && !status?.acknowledged) playAlertTone(tone);
  }, [status?.level, status?.acknowledged, muted]);
  const style = LEVEL_STYLE[level] ?? 'border-surface-border text-slate-200';
  const base = engineId ? `/api/v1/engines/${encodeURIComponent(engineId)}` : null;
  const act = async (path: string, body: unknown, text: string) => {
    if (!base) return;
    try { await api(`${base}${path}`, 'POST', body); onNotice(text); }
    catch (e: any) { onNotice(String(e?.message ?? e)); }
  };
  const active = alerts.filter((a) => a.active);
  const shelved = (a: AlertOut) => a.shelved_until != null && simTimeS != null && a.shelved_until > simTimeS;

  return (
    <section aria-label="Engine status" aria-live="polite" className={`rounded-sm border p-4 ${style}`}>
      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex items-center gap-1.5">
          <span className="text-xl font-semibold tracking-tight">{say?.title ?? (level === 'UNKNOWN' ? NO_DATA : level.replace('_', ' '))}</span>
          {say && level !== 'UNKNOWN' && <span className="text-xs font-mono opacity-70">{level.replace('_', ' ')}</span>}
          <InfoTooltip
            title="Engine Health Classification"
            content="Aviation flight readiness status: GO means all engine temperatures, pressures, and sensors are within safe limits. CAUTION alerts to abnormal trends, and NO-GO indicates a critical limit breach requiring immediate pilot action."
            width={280}
            iconClassName="w-3.5 h-3.5 opacity-60 hover:opacity-100 transition-opacity"
          />
        </div>
        <div className="inline-flex items-center gap-1">
          <button type="button" aria-pressed={muted} onClick={() => setMuted(!muted)}
            className="rounded-sm border border-current px-2 py-0.5 text-xs font-mono opacity-70 hover:opacity-100">{muted ? 'Tones off' : 'Tones on'}</button>
          <InfoTooltip
            title="Cockpit Audio Warning Tones"
            content="Controls audible flight deck alarm chimes on or off. When enabled, sounds audio warning and caution chimes if temperatures, pressures, or engine safety limits enter danger zones (following aviation cockpit alerting standards)."
            width={280}
            iconClassName="w-3.5 h-3.5 opacity-60 hover:opacity-100 transition-opacity"
          />
        </div>
        {status?.latched && (
          <div className="inline-flex items-center gap-1">
            <span className="text-xs font-mono">LATCHED{status.acknowledged ? ' · acknowledged, waiting for the cause to clear' : ''}</span>
            <InfoTooltip
              title="Warning Safety Latch"
              content="Keeps this warning active on screen even if the sensor reading briefly dips back into normal range. Ensures the pilot or ground crew investigates the root cause before clearing the alert."
              width={280}
              iconClassName="w-3.5 h-3.5 opacity-60 hover:opacity-100 transition-opacity"
            />
          </div>
        )}
        {status?.latched && !status.acknowledged && (
          <button type="button" onClick={() => act('/status/acknowledge', undefined, 'Status acknowledged')}
            className="ml-auto rounded-sm border border-current px-3 py-1 text-xs font-mono hover:bg-white/5">Acknowledge</button>
        )}
      </div>
      {say && <p className="mt-1 text-sm">{say.text}</p>}
      {(status?.reasons ?? []).length > 0 && (
        <ul className="mt-2 space-y-0.5 text-xs font-mono">
          {status!.reasons!.map((r, i) => (
            <li key={`${r.code}-${i}`}>{reasonText(r, (id) => channelLabel(labels, id), (id) => units?.[id] ?? '')}</li>
          ))}
        </ul>
      )}
      {active.length > 0 && (
        <div className="mt-3 border-t border-current/30 pt-2">
          <div className="text-xs font-mono opacity-80">Alerts ({active.length})</div>
          <ul className="mt-1 space-y-1">
            {active.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-2 text-xs font-mono">
                <span className="font-semibold">{a.level}</span>
                <span>{a.text}</span>
                {a.count > 1 && <span className="opacity-70">×{a.count}</span>}
                {a.action && <span className="opacity-80">→ {a.action}</span>}
                <span className="ml-auto flex gap-1">
                  {shelved(a) ? <span className="opacity-70">shelved</span> : <>
                    {!a.acknowledged && <button type="button" onClick={() => act('/alerts/acknowledge', { alert_id: a.id }, 'Alert acknowledged')}
                      className="rounded-sm border border-current px-2 hover:bg-white/5">Ack</button>}
                    {a.level !== 'NO-GO' && <button type="button" onClick={() => act('/alerts/shelve', { alert_id: a.id, duration_s: SHELVE_S }, 'Alert shelved for 10 min')}
                      className="rounded-sm border border-current px-2 hover:bg-white/5">Shelve 10 min</button>}
                  </>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
