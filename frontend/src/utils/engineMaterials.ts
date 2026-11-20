import type * as THREE_NS from 'three';
import type { Material, MeshStandardMaterial, Object3D } from 'three';

/* One material treatment for every engine viewer (landing survey inset, console 3D view), matching the old
   apps/threejs_twin look: no stray baked glow, full reflections on metals, softer ones on paint/plastic so light
   parts keep their shading instead of washing out to white. */

const BAKED_WHITE_EMISSIVE = 0.35;   // near-white baked emissive without an emissive texture blows out the AE300/VRDE
const METALLIC = 0.4;                // above this a material is treated as metal
const METAL_ENV = 1.0;               // environment reflection strength on metals
const NON_METAL_ENV = 0.65;          // and on non-metals (old twin value)
export const ENGINE_ENV_INTENSITY = 0.85;   // scene.environmentIntensity used with the procedural room

export function prepareEngineMaterials(root: Object3D): void {
  root.traverse((object) => {
    const mesh = object as Object3D & { isMesh?: boolean; material?: Material | Material[] };
    if (!mesh.isMesh || !mesh.material) return;
    for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
      const m = material as MeshStandardMaterial;
      if (!('envMapIntensity' in m)) continue;
      if (m.emissive && !m.emissiveMap && m.emissive.r > BAKED_WHITE_EMISSIVE && m.emissive.g > BAKED_WHITE_EMISSIVE
          && m.emissive.b > BAKED_WHITE_EMISSIVE) m.emissive.setHex(0x000000);
      m.envMapIntensity = m.metalness > METALLIC ? METAL_ENV : NON_METAL_ENV;
      m.needsUpdate = true;
    }
  });
}

/** Procedural studio for image-based lighting: a dark room with soft-box panels (overhead, key, rim). Metals need
 *  dark areas to reflect; three's RoomEnvironment is near-uniform white, which turns the metal-heavy AE300/VRDE
 *  exports white. Built in code, so no environment-map download or licence. Feed it to PMREMGenerator.fromScene. */
export function studioEnvironment(THREE: typeof THREE_NS): THREE_NS.Scene {
  const scene = new THREE.Scene();
  const room = new THREE.Mesh(new THREE.BoxGeometry(12, 8, 12), new THREE.MeshBasicMaterial({ color: 0x23272b, side: THREE.BackSide }));
  room.position.y = 2;
  scene.add(room);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(12, 12), new THREE.MeshBasicMaterial({ color: 0x111315 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -1.9;
  scene.add(floor);
  // [width, height, x, y, z, radiance]: soft boxes like a product-photography set
  const panels: Array<[number, number, number, number, number, number]> = [
    [5, 3, 0, 5.9, 0, 6],       // overhead
    [3, 4, -5.9, 2, 2, 4],      // key, left front
    [2, 4, 5.9, 2, -2, 2.5],    // rim, right back
    [6, 1, 0, 1, -5.9, 1.5],    // back strip
  ];
  for (const [w, h, x, y, z, radiance] of panels) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color().setScalar(radiance) }));
    m.position.set(x, y, z);
    m.lookAt(0, 0, 0);
    scene.add(m);
  }
  return scene;
}

/** Free the studio scene's geometry and materials once PMREM has baked it. */
export function disposeEnvironment(scene: THREE_NS.Scene): void {
  scene.traverse((o) => {
    const mesh = o as THREE_NS.Mesh;
    if (!mesh.isMesh) return;
    mesh.geometry.dispose();
    (mesh.material as THREE_NS.Material).dispose();
  });
}
