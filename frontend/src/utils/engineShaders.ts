import * as THREE from 'three';

/**
 * Calculates a high-fidelity physical blackbody incandescence / FLIR Ironbow color.
 *
 * For CHT (Cylinder Head Temperature, nominal ~50 C to 140 C):
 * - Cold (< 60 C): Cool dark slate steel.
 * - 60-85 C: Indigo / deep teal.
 * - 85-110 C: Optimal cruise emerald to warm amber.
 * - 110-128 C: Thermal amber to cadmium orange.
 * - 128-138 C: Warning crimson red.
 * - > 138 C: Incandescent overheat magenta / bright crimson.
 *
 * For EGT (Exhaust Gas Temperature, nominal ~400 C to 950 C):
 * - < 600 C: Deep cherry red.
 * - 600-750 C: Vivid combustion red-orange.
 * - 750-880 C: Bright molten neon orange.
 * - 880-940 C: Cadmium golden yellow.
 * - > 940 C: Incandescent white-hot glow.
 */
export function getBlackbodyColor(
  tempC: number,
  _minTemp = 50,
  _maxTemp = 140,
  isExhaust = false
): THREE.Color {
  if (isExhaust) {
    // EGT Range: 400 C to 950 C+
    const t = Math.max(350, Math.min(1050, tempC));
    if (t < 550) {
      // Dull cherry red
      const f = (t - 350) / 200;
      return new THREE.Color().setRGB(0.4 + 0.35 * f, 0.05 * f, 0.05 * f);
    } else if (t < 720) {
      // Vivid red
      const f = (t - 550) / 170;
      return new THREE.Color().setRGB(0.75 + 0.15 * f, 0.05 + 0.15 * f, 0.02);
    } else if (t < 850) {
      // Molten orange
      const f = (t - 720) / 130;
      return new THREE.Color().setRGB(0.9 + 0.08 * f, 0.2 + 0.45 * f, 0.02 + 0.05 * f);
    } else if (t < 940) {
      // Golden yellow
      const f = (t - 850) / 90;
      return new THREE.Color().setRGB(0.98, 0.65 + 0.25 * f, 0.07 + 0.3 * f);
    } else {
      // Incandescent white hot
      const f = Math.min(1, (t - 940) / 100);
      return new THREE.Color().setRGB(1.0, 0.9 + 0.1 * f, 0.37 + 0.63 * f);
    }
  }

  // CHT Range: 50 C to 140 C+
  const t = Math.max(40, Math.min(160, tempC));
  if (t < 60) {
    // Cool dark slate steel
    const f = (t - 40) / 20;
    return new THREE.Color().setRGB(0.18 + 0.08 * f, 0.22 + 0.08 * f, 0.32 + 0.08 * f);
  } else if (t < 85) {
    // Deep teal / blue-green transition
    const f = (t - 60) / 25;
    return new THREE.Color().setRGB(0.1 + 0.05 * f, 0.3 + 0.35 * f, 0.4 - 0.1 * f);
  } else if (t < 110) {
    // Green to warm amber
    const f = (t - 85) / 25;
    return new THREE.Color().setRGB(0.15 + 0.65 * f, 0.65 - 0.1 * f, 0.3 - 0.2 * f);
  } else if (t < 128) {
    // Warm amber to orange
    const f = (t - 110) / 18;
    return new THREE.Color().setRGB(0.8 + 0.15 * f, 0.55 - 0.25 * f, 0.1 - 0.08 * f);
  } else if (t < 138) {
    // Warning vivid red
    const f = (t - 128) / 10;
    return new THREE.Color().setRGB(0.95, 0.3 - 0.2 * f, 0.02);
  } else {
    // Overheat magenta / neon crimson
    const f = Math.min(1, (t - 138) / 20);
    return new THREE.Color().setRGB(0.95 + 0.05 * f, 0.1 * (1 - f), 0.15 + 0.45 * f);
  }
}

/**
 * Creates an aerospace-grade physical transmission optical glass material.
 * Utilizes MeshPhysicalMaterial transmission (Beer-Lambert optical absorption)
 * with micro-roughness dispersion and Schlick clearcoat edge glints.
 */
export function createGlassCasingMaterial(options?: {
  transmission?: number;
  roughness?: number;
  opacity?: number;
}): THREE.MeshPhysicalMaterial {
  const mat = new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(0xffffff),
    transmission: options?.transmission ?? 0.92,
    ior: 1.48, // crown glass
    roughness: options?.roughness ?? 0.12,
    metalness: 0.04,
    thickness: 0.8, // internal refraction distance
    clearcoat: 1.0,
    clearcoatRoughness: 0.06,
    attenuationColor: new THREE.Color(0xdbeafe), // crisp aerospace blue tint
    attenuationDistance: 0.75,
    transparent: true,
    opacity: options?.opacity ?? 1.0,
    depthWrite: false, // Prevents occluding internal components behind the glass
    envMapIntensity: 1.2,
  });

  return mat;
}

/**
 * Creates a smoked obsidian semi-transparent casing material for THERMAL mode.
 * Allows internal heat signatures to shine through while keeping engine contours visible.
 */
export function createSmokedCasingMaterial(): THREE.MeshPhysicalMaterial {
  return new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(0x0f172a),
    transmission: 0.65,
    ior: 1.42,
    roughness: 0.25,
    metalness: 0.15,
    thickness: 0.5,
    transparent: true,
    opacity: 0.35,
    depthWrite: false,
    envMapIntensity: 0.7,
  });
}

/**
 * Creates a dynamic thermal heatmap material representing physical component temperature.
 */
export function createThermalHeatmapMaterial(
  tempC: number,
  minTempC = 50,
  maxTempC = 140,
  isExhaust = false
): THREE.MeshStandardMaterial {
  const color = getBlackbodyColor(tempC, minTempC, maxTempC, isExhaust);
  const mat = new THREE.MeshStandardMaterial({
    color,
    roughness: 0.35,
    metalness: 0.5,
    emissive: color.clone().multiplyScalar(0.75),
    emissiveIntensity: isExhaust ? 1.2 : 0.65,
    envMapIntensity: 0.85,
  });
  return mat;
}

/**
 * Mutates an existing thermal material in-place during animation / telemetry ticks.
 */
export function updateThermalMaterial(
  mat: THREE.MeshStandardMaterial,
  tempC: number,
  minTempC = 50,
  maxTempC = 140,
  isExhaust = false
): void {
  const color = getBlackbodyColor(tempC, minTempC, maxTempC, isExhaust);
  mat.color.copy(color);
  mat.emissive.copy(color).multiplyScalar(0.75);
  mat.emissiveIntensity = isExhaust ? 1.2 : 0.65;
  mat.needsUpdate = true;
}

/**
 * Creates a holographic Digital Twin Ghost material with glowing cyan rim edges.
 */
export function createGhostOverlayMaterial(): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: new THREE.Color(0x06b6d4),
    emissive: new THREE.Color(0x0891b2),
    emissiveIntensity: 0.8,
    transparent: true,
    opacity: 0.45,
    roughness: 0.15,
    metalness: 0.85,
    depthWrite: false,
    wireframe: false,
  });
}
