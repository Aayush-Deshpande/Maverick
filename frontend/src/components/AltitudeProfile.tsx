type Wp = { lat: number; lon: number; altitude_ft: number; terrain_ft: number };

const W = 480;
const H = 160;
const PAD = 28;

function km(a: Wp, b: Wp): number {                       // equirectangular, fine for leg lengths of a few km
  const k = Math.cos((((a.lat + b.lat) / 2) * Math.PI) / 180);
  return 111.32 * Math.hypot(b.lat - a.lat, (b.lon - a.lon) * k);
}

/** Altitude profile of a planned route (M5-11): planned altitude against the planner's terrain height (cell maximum)
 *  at each waypoint, over distance flown. Draws only planner output. */
export default function AltitudeProfile({ waypoints }: { waypoints: Wp[] }) {
  if (waypoints.length < 2) return null;
  const d = [0];
  for (let i = 1; i < waypoints.length; i += 1) d.push(d[i - 1] + km(waypoints[i - 1], waypoints[i]));
  const total = d[d.length - 1] || 1;
  const vals = waypoints.flatMap((w) => [w.altitude_ft, w.terrain_ft]);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const span = Math.max(hi - lo, 1);
  const x = (i: number) => PAD + (d[i] / total) * (W - 2 * PAD);
  const y = (ft: number) => H - PAD - ((ft - lo) / span) * (H - 2 * PAD);
  const path = (key: 'altitude_ft' | 'terrain_ft') => waypoints.map((w, i) => `${x(i).toFixed(1)},${y(w[key]).toFixed(1)}`).join(' ');
  const ground = `${PAD},${H - PAD} ${path('terrain_ft')} ${W - PAD},${H - PAD}`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-xl border border-surface-border rounded-sm bg-black/20"
      role="img" aria-label="Altitude profile of the planned route">
      <polygon points={ground} fill="rgba(148,163,184,0.25)" stroke="#64748b" />
      <polyline points={path('altitude_ft')} fill="none" stroke="#e2e8f0" strokeWidth={1.5} />
      <text x={4} y={y(hi) + 4} fontSize={12} fill="#94a3b8">{Math.round(hi)} ft</text>
      <text x={4} y={y(lo) + 4} fontSize={12} fill="#94a3b8">{Math.round(lo)} ft</text>
      <text x={W - PAD} y={H - 8} fontSize={12} fill="#94a3b8" textAnchor="end">{total.toFixed(1)} km</text>
    </svg>
  );
}
