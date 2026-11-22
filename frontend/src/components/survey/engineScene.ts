// One scene recipe for the landing's engine inset and its pre-rendered posters, so the poster
// and the live full-CAD model are lit and framed identically and the swap is invisible.
import type * as THREE_NS from 'three';
import { ENGINE_ENV_INTENSITY, disposeEnvironment, studioEnvironment } from '../../utils/engineMaterials';

export const ENGINE_MODELS: Record<string, string> = {
  rotax_912is: '/models/rotax_912is.glb',
  rotax_914: '/models/rotax_914.glb',
  rotax_915is: '/models/rotax_915is.glb',
  austro_ae300: '/models/austro_ae300.glb',
  vrde_jayem_2_2l: '/models/vrde_jayem_2_2l.glb',
};

export const posterFor = (id: string) => `/survey/posters/${id}.webp`;

type Three = typeof THREE_NS;

/** Fetch a GLB with byte progress. Uses the HTTP cache (models are served immutable). */
export async function fetchModel(url: string, onProgress: (loaded: number, total: number) => void, signal?: AbortSignal): Promise<ArrayBuffer> {
  const response = await fetch(url, { signal });
  if (!response.ok || !response.body) throw new Error(`Model request returned ${response.status}`);
  const total = Number(response.headers.get('content-length')) || 0;
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let loaded = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    loaded += value.byteLength;
    onProgress(loaded, total);
  }
  const out = new Uint8Array(loaded);
  let offset = 0;
  for (const c of chunks) { out.set(c, offset); offset += c.byteLength; }
  return out.buffer;
}

export function createStage(THREE: Three, canvasParent: HTMLElement, opts: { preserveDrawingBuffer?: boolean } = {}) {
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'high-performance', preserveDrawingBuffer: !!opts.preserveDrawingBuffer });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
  renderer.setClearColor(0x000000, 0);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.90;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  canvasParent.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = studioEnvironment(THREE);
  const env = pmrem.fromScene(room, 0.04);
  scene.environment = env.texture;
  scene.environmentIntensity = ENGINE_ENV_INTENSITY;
  disposeEnvironment(room);
  pmrem.dispose();
  // Balanced studio lighting: crisp directional key with soft sky fill and warm ground bounce
  const key = new THREE.DirectionalLight(0xfff8ee, 1.2); key.position.set(4, 6, 5); scene.add(key);
  const sky = new THREE.DirectionalLight(0xbfd4e6, 0.4); sky.position.set(-5, 3, -2); scene.add(sky);
  const ground = new THREE.HemisphereLight(0xf5ede1, 0x5a483a, 0.35); scene.add(ground);
  const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 100);
  return { renderer, scene, camera, env };
}

/** Normalize and calibrate materials to avoid pure white blowout and ensure crisp contrast against cream stage */
export function calibrateMaterials(root: THREE_NS.Object3D) {
  root.traverse((child) => {
    const mesh = child as THREE_NS.Mesh;
    if (!mesh.isMesh || !mesh.material) return;
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const mat of materials) {
      if (!('isMeshStandardMaterial' in mat)) continue;
      const m = mat as THREE_NS.MeshStandardMaterial;
      const name = (m.name || '').toLowerCase();

      // Zero out any unmapped baked emissive glow that blows out in Three.js
      if (m.emissive && !m.emissiveMap) {
        if (m.emissive.r > 0.05 || m.emissive.g > 0.05 || m.emissive.b > 0.05) {
          m.emissive.setRGB(0, 0, 0);
          m.emissiveIntensity = 0;
        }
      }

      if (name.includes('black') || name.includes('rubber') || name.includes('cable') || name.includes('plasticblack')) {
        m.color.setRGB(0.045, 0.045, 0.05);
        m.metalness = Math.min(m.metalness, 0.2);
        m.roughness = Math.max(m.roughness, 0.45);
      } else if (name.includes('castiron') || name.includes('cast_iron')) {
        m.color.setRGB(0.24, 0.25, 0.26);
        m.metalness = 0.8;
        m.roughness = 0.55;
      } else if (name.includes('steeldark') || name.includes('darksteel')) {
        m.color.setRGB(0.33, 0.34, 0.36);
        m.metalness = 0.85;
        m.roughness = 0.36;
      } else if (name.includes('castaluminium') || name.includes('castaluminum') || name.includes('castalu')) {
        m.color.setRGB(0.55, 0.57, 0.60);
        m.metalness = 0.84;
        m.roughness = 0.40;
      } else if (name.includes('machinedalloy')) {
        m.color.setRGB(0.65, 0.67, 0.70);
        m.metalness = 0.85;
        m.roughness = 0.32;
      } else if (name.includes('steel') && !name.includes('dark')) {
        m.color.setRGB(0.52, 0.54, 0.56);
        m.metalness = 0.85;
        m.roughness = 0.35;
      } else if (name.includes('exhaustheattint')) {
        m.color.setRGB(0.38, 0.35, 0.32);
        m.metalness = 0.90;
        m.roughness = 0.42;
      } else if (name.includes('brass') || name.includes('bronze')) {
        m.color.setRGB(0.85, 0.68, 0.25);
        m.metalness = 0.85;
        m.roughness = 0.28;
      } else if (!m.map && m.color.r > 0.85 && m.color.g > 0.85 && m.color.b > 0.85) {
        // Any other blown-out untextured white surface: clamp to realistic engine metal/casing
        m.color.setRGB(0.58, 0.60, 0.63);
        m.metalness = Math.max(m.metalness, 0.65);
        m.roughness = Math.max(0.35, Math.min(0.6, m.roughness));
      }
      m.envMapIntensity = 0.75;
      m.needsUpdate = true;
    }
  });
}

/** Centre and scale a model to a unit stage, and return a camera "home" for a given aspect. */
export function frameModel(THREE: Three, root: THREE_NS.Object3D) {
  const box = new THREE.Box3().setFromObject(root);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const scale = 2.35 / Math.max(size.x, size.y, size.z);
  root.position.sub(center);
  const group = new THREE.Group();
  group.add(root);
  group.scale.setScalar(scale);
  const home = (camera: THREE_NS.PerspectiveCamera, aspect: number) => {
    const distance = aspect < 0.9 ? 6.6 : 5.2;
    camera.position.set(distance * 0.66, distance * 0.3, distance * 0.69);
    camera.lookAt(0, 0, 0);
  };
  return { group, home };
}

export function disposeObject(root: THREE_NS.Object3D) {
  root.traverse((object) => {
    const mesh = object as THREE_NS.Mesh;
    if (!mesh.isMesh) return;
    mesh.geometry.dispose();
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const material of materials) {
      for (const value of Object.values(material)) if (value && typeof value === 'object' && 'isTexture' in value) (value as THREE_NS.Texture).dispose();
      material.dispose();
    }
  });
}
