export interface Sheet { width: number; height: number; lonMin: number; lonMax: number; latMax: number; latMin: number; kmPerPx: number }
export interface Airfield { id: string; name: string; full: string; lon: number; lat: number }
export interface River { name: string; path: Array<[number, number]> }
export interface RegionLabel { text: string; lon: number; lat: number; size: number; rotate?: number }
export const SHEET: Sheet;
export function toXY(lon: number, lat: number): [number, number];
export const AIRFIELDS: Airfield[];
export const RIVERS: River[];
export const REGION_LABELS: RegionLabel[];
