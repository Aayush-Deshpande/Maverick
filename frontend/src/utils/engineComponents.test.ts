import { describe, it, expect } from 'vitest';
import { classifyNode, findCylinderNumber } from './engineComponents';

describe('engineComponents classification and cylinder mapping', () => {
  it('correctly classifies casing components', () => {
    expect(classifyNode('crankcase', 'crankcase', 'core', null)).toBe('casing');
    expect(classifyNode('engine_block', 'engine_block', 'core', null)).toBe('casing');
    expect(classifyNode('valve_cover', 'valve_cover', 'core', null)).toBe('casing');
    expect(classifyNode('Rocker_Covers_0', 'rocker_covers', 'core', null)).toBe('casing');
    expect(classifyNode('Cooling_Baffle_Left', 'cooling_air_baffle', 'cooling', null)).toBe('casing');
    expect(classifyNode('Oil_Sump_Base', 'oil_sump', 'lubrication', null)).toBe('casing');
    expect(classifyNode('Engine_Mount_Frame', 'engine_mount', 'structure', null)).toBe('casing');
  });

  it('correctly classifies internal combustion / cylinder components', () => {
    expect(classifyNode('Cylinder_Head_1.001', 'cylinder_head_1', 'combustion', 1)).toBe('internal');
    expect(classifyNode('Cylinder_Barrel_2.001', 'cylinder_barrel_2', 'core', 2)).toBe('internal');
    expect(classifyNode('Injector_3', 'injector_3', 'fuel', 3)).toBe('internal');
    expect(classifyNode('Glow_Plug_4', 'glow_plug_4', 'combustion', 4)).toBe('internal');
    expect(classifyNode('Piston_Assembly_1', undefined, undefined, 1)).toBe('internal');
  });

  it('correctly classifies exhaust and turbo components', () => {
    expect(classifyNode('Exhaust_Manifold', 'exhaust', 'exhaust', null)).toBe('exhaust');
    expect(classifyNode('Turbocharger_Assembly', 'turbocharger', 'turbo', null)).toBe('exhaust');
    expect(classifyNode('Turbo_Turbine_Housing', 'turbo_turbine', 'turbo', null)).toBe('exhaust');
    expect(classifyNode('Wastegate_Actuator', 'wastegate', 'turbo', null)).toBe('exhaust');
  });

  it('correctly classifies accessories and electrical', () => {
    expect(classifyNode('ECU_Housing', 'ecu', 'control', null)).toBe('accessory');
    expect(classifyNode('Wiring_Harness_Main', 'wiring_harness', 'electrical', null)).toBe('accessory');
    expect(classifyNode('Alternator_Body', 'alternator', 'electrical', null)).toBe('accessory');
    expect(classifyNode('Starter_Motor', 'starter', 'electrical', null)).toBe('accessory');
  });

  it('correctly extracts cylinder numbers from metadata and node names', () => {
    expect(findCylinderNumber('anything', 'injector_1', 1)).toBe(1);
    expect(findCylinderNumber('Cylinder_Head_2.001', 'cylinder_head_2', null)).toBe(2);
    expect(findCylinderNumber('Cylinder_Barrel_3', undefined, null)).toBe(3);
    expect(findCylinderNumber('cyl_4_head', undefined, null)).toBe(4);
    expect(findCylinderNumber('crankcase', 'crankcase', null)).toBeNull();
  });
});
