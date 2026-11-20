type LatLon = { lat: number; lon: number };
type Field = LatLon & { id: string; name: string; status?: string };

type Props = {
  route?: LatLon[];
  footprint?: LatLon[] | null;
  airfields: Field[];
  aircraft?: LatLon | null;
};

const W = 480;
const H = 320;
const PAD = 24;

/** Plan view of the route, the glide footprint and the airfields (M5-11). Equirectangular projection scaled by
 *  cos(latitude) so distances look right at this latitude; it draws only what the planner and glide API returned. */
export default function RouteMap({ route = [], footprint, airfields, aircraft }: Props) {
  const pts: LatLon[] = [...route, ...(footprint ?? []), ...airfields, ...(aircraft ? [aircraft] : [])];
  if (pts.length === 0) return null;
  const lat0 = pts.reduce((s, p) => s + p.lat, 0) / pts.length;
  const kx = Math.cos((lat0 * Math.PI) / 180);
  const xs = pts.map((p) => p.lon * kx);
  const ys = pts.map((p) => p.lat);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const span = Math.max(x1 - x0, y1 - y0, 1e-3);
  const s = Math.min((W - 2 * PAD) / span, (H - 2 * PAD) / span);
  const px = (p: LatLon) => PAD + (p.lon * kx - x0) * s + ((W - 2 * PAD) - (x1 - x0) * s) / 2;
  const py = (p: LatLon) => H - PAD - (p.lat - y0) * s - ((H - 2 * PAD) - (y1 - y0) * s) / 2;
  const line = (ps: LatLon[]) => ps.map((p) => `${px(p).toFixed(1)},${py(p).toFixed(1)}`).join(' ');
  const kmPerUnit = 111.32;                               // km per degree of latitude (scale bar)
  const barKm = [5, 10, 20, 50, 100].find((k) => (k / kmPerUnit) * s > 60) ?? 100;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-xl border border-surface-border rounded-sm bg-black/20"
      role="img" aria-label="Route, glide footprint and airfields, plan view">
      {footprint && footprint.length > 2 && (
        <polygon points={line(footprint)} fill="rgba(226,232,240,0.07)" stroke="#64748b" strokeDasharray="4 3" strokeWidth={1} />
      )}
      {route.length > 1 && <polyline points={line(route)} fill="none" stroke="#e2e8f0" strokeWidth={1.5} />}
      {route.map((p, i) => <circle key={i} cx={px(p)} cy={py(p)} r={2} fill="#e2e8f0" />)}
      {airfields.map((a) => (
        <g key={a.id}>
          <rect x={px(a) - 3} y={py(a) - 3} width={6} height={6} fill="none" stroke="#94a3b8" />
          <text x={px(a) + 6} y={py(a) + 4} fontSize={12} fill="#cbd5e1">{a.id}{a.status ? ` · ${a.status}` : ''}</text>
        </g>
      ))}
      {aircraft && <path d={`M ${px(aircraft)} ${py(aircraft) - 6} l 5 10 l -10 0 z`} fill="#f8fafc" />}
      <line x1={PAD} y1={H - 8} x2={PAD + (barKm / kmPerUnit) * s} y2={H - 8} stroke="#94a3b8" />
      <text x={PAD} y={H - 12} fontSize={12} fill="#94a3b8">{barKm} km</text>
      <text x={W - PAD} y={PAD - 8} fontSize={12} fill="#94a3b8" textAnchor="end">N ↑</text>
    </svg>
  );
}
