import { useEffect, useState } from 'react';
import { NO_DATA, num } from '../utils/format';
import RouteMap from './RouteMap';
import AltitudeProfile from './AltitudeProfile';
import InfoTooltip from './InfoTooltip';

type Airfield = { id: string; name: string; lat: number; lon: number; elevation_ft: number };
type Waypoint = { lat: number; lon: number; altitude_ft: number; terrain_ft: number; climb_rate_fpm: number };
type Plan = {
  feasible: boolean; reason: string; power_factor: number; service_ceiling_ft: number | null;
  waypoints: Waypoint[]; distance_km: number; max_altitude_ft: number; min_clearance_ft: number | null;
  required_altitude_ft: number | null; power_factor_source: { kind: string; ratios?: Record<string, number> };
};

type GlideField = {
  airfield_id: string; name: string; distance_km: number; alt_margin_ft: number; status: string;
  terrain_checked: boolean; min_terrain_clearance_ft: number | null;
};
type Glide = {
  glide_ratio: number; speed_best_glide_kt: number; sink_rate_fpm: number; propeller_feathered: boolean;
  reachable_airfields: GlideField[]; footprint: { range_km: number; lat: number; lon: number }[] | null; terrain: string | null;
};

type Props = {
  engineId: string | null;
  api: (path: string, method: string, body?: unknown) => Promise<any>;
};

/** Terrain route check (M5-08): the backend plans over the Copernicus DEM with the engine's measured power factor
 *  (or one the operator enters) and either returns a route or refuses it with the reason. */
export default function RoutePlannerPanel({ engineId, api }: Props) {
  const [airfields, setAirfields] = useState<Airfield[]>([]);
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [pf, setPf] = useState('');
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [pos, setPos] = useState({ lat: '', lon: '', alt: '' });
  const [glide, setGlide] = useState<Glide | null>(null);
  const [divert, setDivert] = useState<any>(null);

  useEffect(() => {
    api('/api/v1/planning/airfields', 'GET').then((d) => {
      const list: Airfield[] = d.airfields ?? [];
      setAirfields(list);
      if (list.length > 1) { setFrom(list[0].id); setTo(list[1].id); }
    }).catch((e) => setError(String(e.message ?? e)));
  }, [api]);
  useEffect(() => { setPlan(null); }, [engineId]);

  const run = async () => {
    const a = airfields.find((x) => x.id === from);
    const b = airfields.find((x) => x.id === to);
    if (!engineId || !a || !b) return;
    setBusy(true); setError('');
    try {
      const body: Record<string, unknown> = {
        engine_id: engineId, start: { lat: a.lat, lon: a.lon, altitude_ft: a.elevation_ft }, goal: { lat: b.lat, lon: b.lon },
      };
      if (pf.trim() !== '') body.power_factor = Number(pf);
      setPlan(await api('/api/v1/planning/route', 'POST', body));
    } catch (e: any) {
      setPlan(null); setError(String(e.message ?? e));
    } finally { setBusy(false); }
  };

  const position = () => ({ lat: Number(pos.lat), lon: Number(pos.lon), altitude_ft: Number(pos.alt) });
  const posValid = [pos.lat, pos.lon, pos.alt].every((v) => v.trim() !== '' && Number.isFinite(Number(v)));
  const runGlide = async () => {
    setBusy(true); setError(''); setDivert(null);
    try { setGlide(await api('/api/v1/planning/glide', 'POST', { position: position() })); }
    catch (e: any) { setGlide(null); setError(String(e.message ?? e)); }
    finally { setBusy(false); }
  };
  const runDivert = async (airfieldId: string) => {
    if (!engineId) return;
    setBusy(true); setError('');
    try {
      const body: Record<string, unknown> = { engine_id: engineId, airfield_id: airfieldId, position: position() };
      if (pf.trim() !== '') body.power_factor = Number(pf);
      setDivert(await api('/api/v1/planning/divert', 'POST', body));
    } catch (e: any) { setDivert(null); setError(String(e.message ?? e)); }
    finally { setBusy(false); }
  };
  const ranges = (glide?.footprint ?? []).map((p) => p.range_km).sort((a, b) => a - b);
  const MAP_RADIUS_KM = 150;                              // airfields drawn on the plan view: within this of the centre
  const centre = glide && posValid ? { lat: Number(pos.lat), lon: Number(pos.lon) } : plan?.waypoints[0] ?? null;
  const nearKm = (a: { lat: number; lon: number }) => centre == null ? 0
    : 111.32 * Math.hypot(a.lat - centre.lat, (a.lon - centre.lon) * Math.cos((centre.lat * Math.PI) / 180));

  const select = 'bg-black/20 border border-surface-border rounded-sm px-2 py-1 text-xs text-slate-200';
  return (
    <section className="surface-panel p-4 sm:p-5 rounded-sm">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold text-white tracking-tight">Terrain route check</h3>
        <InfoTooltip
          title="Terrain Route & Clearance Check"
          content="Calculates whether the aircraft can safely climb over high terrain between airfields using the engine's current available power."
          width={280}
        />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs font-mono">
        <select aria-label="From airfield" className={select} value={from} onChange={(e) => setFrom(e.target.value)}>
          {airfields.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <span className="text-slate-500">to</span>
        <select aria-label="To airfield" className={select} value={to} onChange={(e) => setTo(e.target.value)}>
          {airfields.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <input aria-label="Power factor (blank = measured)" className={`${select} w-36`} placeholder="power factor: measured"
          inputMode="decimal" value={pf} onChange={(e) => setPf(e.target.value)} />
        <button type="button" onClick={run} disabled={busy || !engineId || !from || !to}
          className="px-3 py-1 rounded-sm border border-surface-border text-slate-200 hover:bg-white/5 disabled:opacity-50">
          {busy ? 'Planning…' : 'Plan route'}
        </button>
      </div>
      {error && <div className="mt-2 text-xs font-mono text-slate-300">{error}</div>}
      {plan && (
        <div className="mt-3 text-xs font-mono space-y-1">
          <div className={plan.feasible ? 'text-white' : 'text-slate-200'}>{plan.feasible ? 'ROUTE FOUND' : 'ROUTE REFUSED'} · {plan.reason}</div>
          <div className="text-slate-400">
            Power factor {num(plan.power_factor, 2)} ({plan.power_factor_source.kind}
            {plan.power_factor_source.ratios ? `: ${Object.entries(plan.power_factor_source.ratios).map(([k, v]) => `${k} ${num(v, 3)}`).join(', ')}` : ''})
            {' · '}service ceiling {plan.service_ceiling_ft == null ? NO_DATA : `${num(plan.service_ceiling_ft, 0)} ft`}
            {plan.required_altitude_ft != null && ` · terrain needs ${num(plan.required_altitude_ft, 0)} ft`}
          </div>
          {plan.feasible && <>
            <div className="text-slate-400">{num(plan.distance_km, 1)} km · highest {num(plan.max_altitude_ft, 0)} ft · min clearance {plan.min_clearance_ft == null ? NO_DATA : `${num(plan.min_clearance_ft, 0)} ft`} · {plan.waypoints.length} waypoints</div>
            <AltitudeProfile waypoints={plan.waypoints} />
            <div className="text-slate-500">Profile: planned altitude (line) over the planner's terrain height, cell maximum (shaded)</div>
            <div className="max-h-40 overflow-y-auto border border-surface-border rounded-sm">
              <table className="w-full text-left">
                <thead className="text-slate-500"><tr><th className="px-2 py-1">Lat</th><th className="px-2">Lon</th><th className="px-2">Alt ft</th><th className="px-2">Terrain ft</th><th className="px-2">Climb fpm</th></tr></thead>
                <tbody>{plan.waypoints.map((w, i) => (
                  <tr key={i} className="text-slate-300 tabular-nums"><td className="px-2">{num(w.lat, 4)}</td><td className="px-2">{num(w.lon, 4)}</td><td className="px-2">{num(w.altitude_ft, 0)}</td><td className="px-2">{num(w.terrain_ft, 0)}</td><td className="px-2">{num(w.climb_rate_fpm, 0)}</td></tr>
                ))}</tbody>
              </table>
            </div>
          </>}
          <div className="text-slate-500">Copernicus GLO-30 terrain · airframe data ASSUMED · SIMULATION · not for navigation</div>
        </div>
      )}
      <div className="mt-4 flex items-center gap-2">
        <h4 className="text-xs font-semibold text-white">Engine-out glide and divert</h4>
        <InfoTooltip
          title="Emergency Glide & Divert"
          content="Simulates where the aircraft can glide without engine power, calculating whether it can safely reach emergency runways while clearing mountain terrain."
          width={280}
        />
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs font-mono">
        {(['lat', 'lon', 'alt'] as const).map((k) => (
          <input key={k} aria-label={k === 'alt' ? 'Altitude ft' : k} className={`${select} w-24`} inputMode="decimal"
            placeholder={k === 'alt' ? 'altitude ft' : k} value={pos[k]} onChange={(e) => setPos({ ...pos, [k]: e.target.value })} />
        ))}
        <button type="button" onClick={runGlide} disabled={busy || !posValid}
          className="px-3 py-1 rounded-sm border border-surface-border text-slate-200 hover:bg-white/5 disabled:opacity-50">Glide check</button>
      </div>
      {glide && (
        <div className="mt-3 text-xs font-mono space-y-1">
          <div className="text-slate-400">
            L/D {num(glide.glide_ratio, 1)} ({glide.propeller_feathered ? 'feathered' : 'windmilling'}) · best glide {num(glide.speed_best_glide_kt, 0)} kt TAS · sink {num(glide.sink_rate_fpm, 0)} fpm
            {' · '}footprint {ranges.length ? `${num(ranges[0], 1)}–${num(ranges[ranges.length - 1], 1)} km (median ${num(ranges[Math.floor(ranges.length / 2)], 1)})` : `${NO_DATA} (no terrain)`}
          </div>
          <table className="w-full text-left">
            <thead className="text-slate-500"><tr><th className="px-2 py-1">Airfield</th><th className="px-2">km</th><th className="px-2">Margin ft</th><th className="px-2">Terrain clear ft</th><th className="px-2">Status</th><th /></tr></thead>
            <tbody>{glide.reachable_airfields.map((a) => (
              <tr key={a.airfield_id} className="text-slate-300 tabular-nums">
                <td className="px-2">{a.name}</td><td className="px-2">{num(a.distance_km, 1)}</td><td className="px-2">{num(a.alt_margin_ft, 0)}</td>
                <td className="px-2">{a.terrain_checked && a.min_terrain_clearance_ft != null ? num(a.min_terrain_clearance_ft, 0) : 'not checked'}</td>
                <td className="px-2">{a.status}</td>
                <td className="px-2"><button type="button" disabled={busy || !engineId} onClick={() => runDivert(a.airfield_id)}
                  className="px-2 rounded-sm border border-surface-border hover:bg-white/5 disabled:opacity-50">Divert</button></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {(plan || glide) && (
        <div className="mt-3">
          <RouteMap
            route={plan?.feasible ? plan.waypoints : divert?.powered_route?.feasible ? divert.powered_route.waypoints : []}
            footprint={glide?.footprint ?? null}
            airfields={airfields.filter((a) => nearKm(a) <= MAP_RADIUS_KM).map((a) => ({ ...a, status: glide?.reachable_airfields.find((g) => g.airfield_id === a.id)?.status }))}
            aircraft={glide && posValid ? { lat: Number(pos.lat), lon: Number(pos.lon) } : null}
          />
          <div className="mt-1 text-xs font-mono text-slate-500">Plan view: route (solid), engine-out glide footprint (dashed), airfields (squares) · SIMULATION</div>
        </div>
      )}
      {divert && (
        <div className="mt-2 text-xs font-mono text-slate-300 space-y-1">
          <div>Divert {divert.airfield.name}: glide {divert.glide.status}
            {' · '}powered route {divert.powered_route.feasible === true ? `FOUND (${num(divert.powered_route.distance_km, 1)} km, highest ${num(divert.powered_route.max_altitude_ft, 0)} ft)`
              : divert.powered_route.feasible === false ? `REFUSED · ${divert.powered_route.reason}` : `UNAVAILABLE · ${divert.powered_route.message ?? NO_DATA}`}
          </div>
        </div>
      )}
    </section>
  );
}
