// Sheet geometry for the Leh–Nubra–Kargil sector. Shared by the relief generator (Node) and the page.
// Equirectangular projection about the sheet's central latitude; river courses are schematic.
// Bounds put Leh and Thoise near the sheet's centre, the open ground between the title block and legends.

export const SHEET = {
  width: 1600,
  height: 1000,
  lonMin: 75.9,
  lonMax: 78.9,
  latMax: 35.15,
};
const COS = Math.cos((34.4 * Math.PI) / 180);
const PX_PER_DEG_LON = SHEET.width / (SHEET.lonMax - SHEET.lonMin);
const PX_PER_DEG_LAT = PX_PER_DEG_LON / COS;
SHEET.latMin = SHEET.latMax - SHEET.height / PX_PER_DEG_LAT;
/** Kilometres per sheet pixel. */
SHEET.kmPerPx = (111.32 * COS) / PX_PER_DEG_LON;

export function toXY(lon, lat) {
  return [(lon - SHEET.lonMin) * PX_PER_DEG_LON, (SHEET.latMax - lat) * PX_PER_DEG_LAT];
}

export const AIRFIELDS = [
  { id: 'VILH', name: 'Leh', full: 'Leh Kushok Bakula Rimpochee', lon: 77.5465, lat: 34.1359 },
  { id: 'VI82', name: 'Thoise', full: 'Thoise Air Force Station', lon: 77.3753, lat: 34.6526 },
  { id: 'VIKG', name: 'Kargil', full: 'Kargil Airfield', lon: 76.1559, lat: 34.5243 },
];

export const RIVERS = [
  { name: 'Indus', path: [[78.9, 33.6], [78.55, 33.7], [78.25, 33.86], [77.95, 33.96], [77.75, 34.05], [77.58, 34.12], [77.35, 34.22], [77.05, 34.35], [76.75, 34.5], [76.45, 34.6], [76.2, 34.63], [75.9, 34.72]] },
  { name: 'Shyok', path: [[78.9, 35.05], [78.55, 34.92], [78.25, 34.76], [77.95, 34.63], [77.65, 34.55], [77.45, 34.58], [77.2, 34.72], [76.95, 34.86], [76.7, 34.99], [76.5, 35.15]] },
  { name: 'Nubra', path: [[77.26, 35.15], [77.33, 34.92], [77.39, 34.74], [77.45, 34.59]] },
  { name: 'Suru', path: [[75.95, 33.62], [76.0, 34.1], [76.07, 34.35], [76.13, 34.52], [76.2, 34.63]] },
];

export const REGION_LABELS = [
  { text: 'KARAKORAM', lon: 77.6, lat: 35.05, size: 30 },
  { text: 'LADAKH RANGE', lon: 77.25, lat: 34.42, size: 22, rotate: -22 },
  { text: 'ZANSKAR RANGE', lon: 76.85, lat: 33.95, size: 22, rotate: -18 },
  { text: 'CHANGTHANG', lon: 78.45, lat: 33.95, size: 24 },
];
