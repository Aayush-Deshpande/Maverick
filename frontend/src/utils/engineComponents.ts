/**
 * Classification of 3D engine mesh nodes and manifest components into functional categories:
 * - 'casing': structural outer shell (crankcase, block, valve/rocker covers, baffles, oil sump).
 *   Target for optical physical glass / transmission x-ray in GLASS mode, and smoked obsidian in THERMAL mode.
 * - 'internal': internal reciprocating & combustion assemblies (cylinder heads, barrels, pistons, valves, injectors).
 *   Kept solid PBR in GLASS mode; heat-mapped dynamically by live CHT in THERMAL mode.
 * - 'exhaust': exhaust headers, turbocharger, turbine, wastegate.
 *   Kept solid PBR in GLASS mode; heat-mapped dynamically by live EGT / TIT in THERMAL mode.
 * - 'accessory': electrical, starter, alternator, wiring, ECU, sensors.
 * - 'other': general engine fasteners, fittings, miscellaneous.
 */

export type ComponentCategory = 'casing' | 'internal' | 'exhaust' | 'accessory' | 'other';

const CASING_PATTERNS = [
  'crankcase',
  'engine_block',
  'valve_cover',
  'rocker_cover',
  'rocker',
  'timing_cover',
  'timing_gear',
  'sump',
  'oil_sump',
  'baffle',
  'air_baffle',
  'cooling_baffle',
  'cooling_air_baffle',
  'mount',
  'engine_mount',
  'lifting_eye',
  'covers',
  'block',
  'casing',
  'housing',
];

const INTERNAL_PATTERNS = [
  'cylinder_head',
  'cylinder_barrel',
  'piston',
  'valve',
  'injector',
  'fuel_line',
  'spark_plug',
  'glow_plug',
  'plug',
  'crankshaft',
  'connecting_rod',
  'camshaft',
  'head',
  'barrel',
];

const EXHAUST_PATTERNS = [
  'exhaust',
  'header',
  'downpipe',
  'muffler',
  'turbo',
  'turbocharger',
  'turbine',
  'compressor',
  'wastegate',
  'intercooler',
  'boost_pipe',
];

const ACCESSORY_PATTERNS = [
  'ecu',
  'wiring',
  'harness',
  'alternator',
  'starter',
  'relay',
  'pump',
  'fuel_pump',
  'vacuum_pump',
  'water_pump',
  'filter',
  'sensor',
  'dipstick',
  'belt',
  'prop_governor',
  'prop_flange',
  'gearbox',
];

export function findCylinderNumber(
  nodeName: string,
  componentId?: string,
  cylinder?: number | null
): number | null {
  if (typeof cylinder === 'number' && cylinder >= 1 && cylinder <= 8) {
    return cylinder;
  }

  const str = `${nodeName} ${componentId ?? ''}`.toLowerCase();
  
  // Match cyl_4, cylinder_head_1, cyl4, head.001, etc.
  const match = str.match(/(?:cylinder|cyl|head|barrel|injector|plug)[_\-\s]*([1-8])(?:[_\-\s\.]|$)/i)
    || str.match(/(?:^|[_\-\s])([1-8])(?:[_\-\s\.]|$).*(?:cylinder|cyl)/i);

  if (match) {
    const num = parseInt(match[1], 10);
    if (!isNaN(num) && num >= 1 && num <= 8) return num;
  }

  return null;
}

export function classifyNode(
  nodeName: string,
  componentId?: string,
  subsystem?: string,
  cylinder?: number | null
): ComponentCategory {
  const normNode = nodeName.toLowerCase();
  const normComp = (componentId ?? '').toLowerCase();
  const normSub = (subsystem ?? '').toLowerCase();

  // 1. Subsystem-level overrides
  if (normSub === 'electrical' || normSub === 'control' || normSub === 'sensors' || normSub === 'accessories') {
    return 'accessory';
  }
  if (normSub === 'exhaust' || normSub === 'turbo') {
    return 'exhaust';
  }
  if (cylinder !== null && cylinder !== undefined && (normSub === 'combustion' || normSub === 'core' || normSub === 'fuel')) {
    return 'internal';
  }

  // 2. Specific compound casing patterns (valve_cover, rocker_cover, baffles take priority over 'valve')
  if (
    normComp.includes('valve_cover') || normNode.includes('valve_cover') ||
    normComp.includes('rocker') || normNode.includes('rocker') ||
    normComp.includes('crankcase') || normNode.includes('crankcase') ||
    normComp.includes('engine_block') || normNode.includes('engine_block') ||
    normComp.includes('baffle') || normNode.includes('baffle') ||
    normComp.includes('sump') || normNode.includes('sump') ||
    normComp.includes('mount') || normNode.includes('mount')
  ) {
    return 'casing';
  }

  // 3. Exhaust & Turbo
  for (const pat of EXHAUST_PATTERNS) {
    if (normComp.includes(pat) || normNode.includes(pat)) return 'exhaust';
  }

  // 4. Internal combustion parts
  if (normSub === 'combustion') {
    return 'internal';
  }
  for (const pat of INTERNAL_PATTERNS) {
    if (normComp.includes(pat) || normNode.includes(pat)) return 'internal';
  }

  // 5. General accessories
  for (const pat of ACCESSORY_PATTERNS) {
    if (normComp.includes(pat) || normNode.includes(pat)) return 'accessory';
  }

  // 6. Remaining casing patterns (housing, casing, covers)
  for (const pat of CASING_PATTERNS) {
    if (normComp.includes(pat) || normNode.includes(pat)) return 'casing';
  }

  return 'other';
}
