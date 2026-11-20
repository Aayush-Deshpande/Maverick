// One scene recipe for the landing's engine inset and its pre-rendered posters, so the poster
// and the live full-CAD model are lit and framed identically and the swap is invisible.
import type * as THREE_NS from 'three';

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

export function createStage(THREE: Three, RoomEnvironment: new () => THREE_NS.Scene, canvasParent: HTMLElement, opts: { preserveDrawingBuffer?: boolean } = {}) {
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'high-performance', preserveDrawingBuffer: !!opts.preserveDrawingBuffer });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
  renderer.setClearColor(0x000000, 0);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.95;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  canvasParent.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  const env = pmrem.fromScene(room, 0.04);
  scene.environment = env.texture;
  scene.environmentIntensity = 0.85;
  pmrem.dispose();
  // Neutral daylight key with a cool sky fill and a warm ground bounce, like a sheet read by a window.
  const key = new THREE.DirectionalLight(0xffffff, 1.6); key.position.set(4, 6, 5); scene.add(key);
  const sky = new THREE.DirectionalLight(0xbcd3e6, 0.7); sky.position.set(-5, 3, -2); scene.add(sky);
  const ground = new THREE.HemisphereLight(0xe8eef2, 0x8a6a48, 0.45); scene.add(ground);
  const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 100);
  return { renderer, scene, camera, env };
}

const BAKED_WHITE_EMISSIVE = 0.35;   // same rule as LandingHero3D and the console viewer: near-white baked emissive
                                     // without an emissive texture blows out the AE300/VRDE exports

/** Turn off near-white baked emissive that has no emissive texture (it renders the AE300/VRDE solid white). */
export function neutraliseBakedEmissive(root: THREE_NS.Object3D) {
  root.traverse((object) => {
    const mesh = object as THREE_NS.Mesh;
    if (!mesh.isMesh) return;
    for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
      const m = material as THREE_NS.MeshStandardMaterial;
      if (m.emissive && !m.emissiveMap && m.emissive.r > BAKED_WHITE_EMISSIVE && m.emissive.g > BAKED_WHITE_EMISSIVE
          && m.emissive.b > BAKED_WHITE_EMISSIVE) m.emissive.setHex(0x000000);
    }
  });
}

/** Centre and scale a model to a unit stage, and return a camera "home" for a given aspect. */
export function frameModel(THREE: Three, root: THREE_NS.Object3D) {
  neutraliseBakedEmissive(root);
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
