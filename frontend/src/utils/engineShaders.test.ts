import { describe, it, expect } from 'vitest';
import * as THREE from 'three';
import {
  getBlackbodyColor,
  createGlassCasingMaterial,
  createThermalHeatmapMaterial,
  createGhostOverlayMaterial,
  createSmokedCasingMaterial,
  updateThermalMaterial,
} from './engineShaders';

describe('engineShaders physical materials and thermal heatmaps', () => {
  it('computes realistic blackbody color ramp for CHT temperatures', () => {
    // Cold engine (< 60 C) -> cool dark slate
    const cold = getBlackbodyColor(45, 50, 140, false);
    expect(cold.r).toBeLessThan(0.4);
    expect(cold.b).toBeGreaterThan(0.3);

    // Warm operating engine (~100 C) -> warm amber / greenish-yellow
    const warm = getBlackbodyColor(100, 50, 140, false);
    expect(warm.r).toBeGreaterThan(0.5);

    // Overheat (> 135 C) -> intense red
    const hot = getBlackbodyColor(138, 50, 140, false);
    expect(hot.r).toBeGreaterThan(0.8);
    expect(hot.g).toBeLessThan(0.3);
  });

  it('computes glowing incandescence for exhaust EGT temperatures', () => {
    // Normal exhaust (750 C) -> bright cherry red / orange
    const normExhaust = getBlackbodyColor(750, 400, 950, true);
    expect(normExhaust.r).toBeGreaterThan(0.8);

    // Max limit exhaust (950 C) -> incandescent gold / white hot
    const maxExhaust = getBlackbodyColor(950, 400, 950, true);
    expect(maxExhaust.r).toBeGreaterThan(0.9);
    expect(maxExhaust.g).toBeGreaterThan(0.7);
  });

  it('constructs physical transmission optical glass material', () => {
    const glass = createGlassCasingMaterial();
    expect(glass).toBeInstanceOf(THREE.MeshPhysicalMaterial);
    expect(glass.transmission).toBeCloseTo(0.92, 2);
    expect(glass.ior).toBeCloseTo(1.48, 2);
    expect(glass.transparent).toBe(true);
    expect(glass.depthWrite).toBe(false);
  });

  it('constructs thermal heatmap material with emissive glow', () => {
    const thermal = createThermalHeatmapMaterial(115, 50, 140, false);
    expect(thermal).toBeInstanceOf(THREE.MeshStandardMaterial);
    expect(thermal.emissiveIntensity).toBeGreaterThan(0.4);
    expect(thermal.roughness).toBeLessThan(0.5);
  });

  it('constructs holographic twin ghost material', () => {
    const ghost = createGhostOverlayMaterial();
    expect(ghost.transparent).toBe(true);
    expect(ghost.depthWrite).toBe(false);
    expect(ghost.color.getHexString()).toContain('06b6d4');
  });

  it('constructs smoked casing material for thermal cutaway contrast', () => {
    const smoked = createSmokedCasingMaterial();
    expect(smoked.transparent).toBe(true);
    expect(smoked.opacity).toBeLessThan(0.5);
  });

  it('updates existing thermal material without re-allocation', () => {
    const mat = createThermalHeatmapMaterial(70, 50, 140, false);
    const initialHex = mat.color.getHex();
    updateThermalMaterial(mat, 138, 50, 140, false);
    expect(mat.color.getHex()).not.toBe(initialHex);
  });
});
