import type { AlertOut, Status } from '../api/state';
import { NO_DATA, num } from '../utils/format';

type Props = {
  engineId: string | null;
  status: Status | null | undefined;
  alerts: AlertOut[];
  simTimeS: number | null | undefined;
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
export default function StatusBanner({ engineId, status, alerts, simTimeS, api, onNotice }: Props) {
  const level = status?.level ?? 'UNKNOWN';
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
        <span className="text-xl font-semibold font-mono tracking-tight">{level === 'UNKNOWN' ? NO_DATA : level.replace('_', ' ')}</span>
        {status?.latched && <span className="text-xs font-mono">LATCHED{status.acknowledged ? ' · acknowledged, waiting for the cause to clear' : ''}</span>}
        {status?.latched && !status.acknowledged && (
          <button type="button" onClick={() => act('/status/acknowledge', undefined, 'Status acknowledged')}
            className="ml-auto rounded-sm border border-current px-3 py-1 text-xs font-mono hover:bg-white/5">Acknowledge</button>
        )}
      </div>
      {(status?.reasons ?? []).length > 0 && (
        <ul className="mt-2 space-y-0.5 text-xs font-mono">
          {status!.reasons!.map((r, i) => (
            <li key={`${r.code}-${i}`}>
              {r.text}
              {r.value != null && r.limit != null && <span className="opacity-70"> ({num(r.value, 2)} vs limit {num(r.limit, 2)})</span>}
            </li>
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
