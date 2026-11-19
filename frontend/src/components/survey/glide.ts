import type { EngineFrame } from '../../hooks/useEngineRuntime';
import { AIRFIELDS, SHEET, toXY } from './geo.js';

const FT_PER_NM = 6076.12;
export const DEFAULT_LD = 27.3;

export interface GlideField { id: string; name: string; full: string; x: number; y: number; distanceNm: number; floorFt: number; requiredFt: number; reachable: boolean; marginFt: number }
export interface GlideModel { ld: number; uav: [number, number]; rangeNm: number; ringPx: number; minutesAloft: number; fields: GlideField[]; climbToNearest: number | null }

/** Least-squares position from distances to known points (sheet pixels). */
function trilaterate(points: Array<{ x: number; y: number; r: number }>): [number, number] | null {
  if (points.length < 3) return null;
  const [p0, ...rest] = points;
  let a11 = 0, a12 = 0, a22 = 0, b1 = 0, b2 = 0;
  for (const p of rest) {
    const ax = 2 * (p.x - p0.x), ay = 2 * (p.y - p0.y);
    const b = p0.r ** 2 - p.r ** 2 + p.x ** 2 - p0.x ** 2 + p.y ** 2 - p0.y ** 2;
    a11 += ax * ax; a12 += ax * ay; a22 += ay * ay; b1 += ax * b; b2 += ay * b;
  }
  const det = a11 * a22 - a12 * a12;
  if (Math.abs(det) < 1e-9) return null;
  return [(a22 * b1 - a12 * b2) / det, (a11 * b2 - a12 * b1) / det];
}

/**
 * Engine-out glide on the sheet, using the backend's own model: still-air range = altitude x L/D,
 * and an airfield is reachable when altitude covers distance / L/D plus that field's floor
 * (field elevation and safety margin, recovered from the backend's alt_required_ft).
 */
export function glideModel(frame: EngineFrame | null, altitudeFt: number): GlideModel {
  const g = frame?.glide;
  const ld = g?.ld_ratio ?? DEFAULT_LD;
  const pxPerNm = 1.852 / SHEET.kmPerPx;
  const live = new Map((g?.airfields ?? []).map((a) => [a.airfield_id, a]));
  const known = AIRFIELDS.map((f) => { const [x, y] = toXY(f.lon, f.lat); return { ...f, x, y, live: live.get(f.id) }; });
  const fixes = known.filter((f) => f.live).map((f) => ({ x: f.x, y: f.y, r: (f.live!.distance_nm) * pxPerNm }));
  const leh = known[0];
  const uav = trilaterate(fixes) ?? [leh.x - 220, leh.y - 40];
  const fields = known.map((f) => {
    const distanceNm = f.live?.distance_nm ?? Math.hypot(f.x - uav[0], f.y - uav[1]) / pxPerNm;
    const floorFt = f.live?.alt_required_ft !== undefined ? f.live.alt_required_ft - (f.live.distance_nm * FT_PER_NM) / ld : 12000;
    const requiredFt = (distanceNm * FT_PER_NM) / ld + floorFt;
    return { id: f.id, name: f.name, full: f.full, x: f.x, y: f.y, distanceNm, floorFt, requiredFt, reachable: altitudeFt >= requiredFt, marginFt: altitudeFt - requiredFt };
  }).sort((a, b) => a.distanceNm - b.distanceNm);
  const rangeNm = (altitudeFt * ld) / FT_PER_NM;
  const sink = g?.sink_rate_fpm ?? 245;
  const anyReach = fields.some((f) => f.reachable);
  return { ld, uav, rangeNm, ringPx: rangeNm * pxPerNm, minutesAloft: altitudeFt / sink, fields, climbToNearest: anyReach ? null : Math.ceil(fields[0].requiredFt / 100) * 100 };
}
