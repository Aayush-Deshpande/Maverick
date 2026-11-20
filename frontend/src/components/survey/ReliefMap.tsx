import { memo, useEffect, useState } from 'react';
import { REGION_LABELS, RIVERS, SHEET, toXY } from './geo.js';
import type { GlideModel } from './glide';

interface Contour { e: number; index: boolean; d: string }
const W = SHEET.width, H = SHEET.height;

const riverD = (path: number[][]) => 'M' + path.map(([lon, lat]) => toXY(lon, lat).map((v) => v.toFixed(1)).join(' ')).join('L');

/** Static sheet linework: contours (plotted in once), rivers, ranges and graticule. Memoised: never re-renders with live data. */
const SheetLinework = memo(function SheetLinework() {
  const [contours, setContours] = useState<Contour[]>([]);
  useEffect(() => {
    let active = true;
    fetch('/survey/contours.json').then((r) => r.json()).then((data: { contours: Contour[] }) => { if (active) setContours(data.contours); }).catch(() => {});
    return () => { active = false; };
  }, []);
  const ticks: Array<{ x?: number; y?: number; label: string }> = [];
  for (let lon = 76; lon <= 78; lon += 0.5) ticks.push({ x: toXY(lon, SHEET.latMax)[0], label: `${Math.floor(lon)}°${lon % 1 ? '30′' : '00′'}E` });
  for (let lat = 34; lat <= 35; lat += 0.5) ticks.push({ y: toXY(SHEET.lonMin, lat)[1], label: `${Math.floor(lat)}°${lat % 1 ? '30′' : '00′'}N` });
  return <g>
    <g className="sv-contours">
      {contours.map((c, i) => <path key={i} d={c.d} pathLength={1} className={c.index ? 'is-index' : undefined} style={{ ['--k' as string]: (c.e - 3200) / 3600 }} />)}
    </g>
    <g className="sv-rivers">
      {RIVERS.map((r) => <g key={r.name}>
        <path id={`river-${r.name}`} d={riverD(r.path)} />
        <text dy={-7}><textPath href={`#river-${r.name}`} startOffset="38%">{r.name}</textPath></text>
      </g>)}
    </g>
    <g className="sv-ranges">
      {REGION_LABELS.map((l) => { const [x, y] = toXY(l.lon, l.lat); return <text key={l.text} x={x} y={y} fontSize={l.size} transform={l.rotate ? `rotate(${l.rotate} ${x} ${y})` : undefined}>{l.text.split('').join(' ')}</text>; })}
    </g>
    <g className="sv-graticule">
      {ticks.map((t) => t.x !== undefined
        ? <g key={t.label}><line x1={t.x} y1={0} x2={t.x} y2={H} /><text x={t.x + 6} y={H - 14}>{t.label}</text></g>
        : <g key={t.label}><line x1={0} y1={t.y} x2={W} y2={t.y} /><text x={14} y={(t.y ?? 0) - 6}>{t.label}</text></g>)}
    </g>
  </g>;
});

/** Live overlay: airfields with reachability, the UAV and its engine-out glide ring. */
export function ReliefMap({ glide, className }: { glide: GlideModel; className?: string }) {
  const [ux, uy] = glide.uav;
  return <svg className={`sv-map ${className ?? ''}`} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid slice" role="img" aria-label={`Schematic relief of the Leh, Nubra and Kargil sector. Engine-out glide range ${glide.rangeNm.toFixed(0)} nautical miles; ${glide.fields.filter((f) => f.reachable).map((f) => f.name).join(', ') || 'no airfield'} reachable.`}>
    <image href="/survey/relief.webp" x={0} y={0} width={W} height={H} preserveAspectRatio="none" />
    <SheetLinework />
    <g className="sv-glide">
      <circle className="sv-glide-ring" cx={ux} cy={uy} r={glide.ringPx} />
      <circle className="sv-glide-fill" cx={ux} cy={uy} r={glide.ringPx} />
      {glide.fields.map((f) => <line key={f.id} className={f.reachable ? 'sv-leg is-reach' : 'sv-leg'} x1={ux} y1={uy} x2={f.x} y2={f.y} />)}
    </g>
    <g className="sv-airfields">
      {glide.fields.map((f) => <g key={f.id} className={f.reachable ? 'is-reach' : undefined} transform={`translate(${f.x} ${f.y})`}>
        <circle r={11} /><path d="M0 -17V-11M0 11V17M-17 0H-11M11 0H17" />
        <text x={18} y={-8} className="sv-af-name">{f.name.toUpperCase()}</text>
        <text x={18} y={10} className="sv-af-meta">{f.id} · {f.distanceNm.toFixed(0)} nm · {f.reachable ? 'in reach' : `${Math.round(-f.marginFt).toLocaleString('en-IN')} ft short`}</text>
      </g>)}
    </g>
    <g className="sv-uav" transform={`translate(${ux} ${uy})`}>
      <path d="M0 -13L3 -2L14 3L3 3L2 10L6 13H-6L-2 10L-3 3L-14 3L-3 -2Z" />
      <text x={18} y={4}>UAV · engine-out</text>
    </g>
  </svg>;
}
