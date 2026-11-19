// The engine bay: the real Rotax 912 iS CAD (109 named components, the same object names as the Blender
// assembly), grouped into subsystems by the shared component map (twin/component_map.json). At the moment
// of injection the oil-pressure pipeline goes to the fault material and everything else to the X-ray ghost,
// with the colour values of the Blender diagnostic app's own materials.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

export interface ComponentMap {
  highlight: { fault_rgb: number[]; ghost_rgb: number[] };
  engines: Record<string, { subsystems: Record<string, string[]>; faults: Record<string, { pipeline: string[][] }> }>;
}
export interface BayLabel { key: string; x: number; y: number; on: boolean; count: number }

const SUBSYSTEM_NAMES: Record<string, string> = {
  oil: 'Oil system', fuel: 'Fuel', ignition: 'Ignition harness', cooling: 'Cooling', exhaust: 'Exhaust',
  gearbox: 'Reduction gearbox', electrical: 'Electrical', control: 'Dual-lane ECU', structure: 'Engine case',
};
export const subsystemName = (k: string) => SUBSYSTEM_NAMES[k] ?? k;

const sstep = (a: number, b: number, x: number) => { const k = Math.min(1, Math.max(0, (x - a) / (b - a))); return k * k * (3 - 2 * k); };
const matches = (o: THREE.Object3D, prefixes: string[], root: THREE.Object3D) => {
  for (let n: THREE.Object3D | null = o; n; n = n.parent) {
    const name = (n.name || '').replace(/\s+/g, '_');
    if (prefixes.some((p) => name.startsWith(p.replace(/\s+/g, '_')))) return true;
    if (n === root) break;
  }
  return false;
};

export class EngineBay {
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(32, 1, 0.5, 20000);
  loaded = false;
  meshCount = 0;
  private root: THREE.Object3D | null = null;
  private meshes: THREE.Mesh[] = [];
  private originals = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>();
  private faulty = new Set<THREE.Mesh>();
  private anchors: Array<{ key: string; center: THREE.Vector3; count: number }> = [];
  private center = new THREE.Vector3();
  private radius = 100;
  private faultCenter = new THREE.Vector3();
  private ghostMat: THREE.MeshStandardMaterial;
  private faultMat: THREE.MeshStandardMaterial;
  private highlighted = false;
  private env: THREE.Texture;

  constructor(private renderer: THREE.WebGLRenderer) {
    this.scene.background = new THREE.Color(0x05090b);
    const pm = new THREE.PMREMGenerator(renderer);
    this.env = pm.fromScene(new RoomEnvironment(), 0.04).texture; pm.dispose();
    this.scene.environment = this.env;
    (this.scene as THREE.Scene & { environmentIntensity?: number }).environmentIntensity = 0.7;
    this.scene.add(new THREE.HemisphereLight(0xcfe6ee, 0x101416, 0.6));
    const key = new THREE.DirectionalLight(0xfff1e0, 2.2); key.position.set(1, 1.4, 0.8); this.scene.add(key);
    const rim = new THREE.DirectionalLight(0x58e6f2, 1.4); rim.position.set(-1, 0.4, -1.2); this.scene.add(rim);
    this.ghostMat = new THREE.MeshStandardMaterial({ transparent: true, opacity: 0.2, depthWrite: false, roughness: 0.15, metalness: 0.1 });
    this.faultMat = new THREE.MeshStandardMaterial({ roughness: 0.1, metalness: 0.1, emissiveIntensity: 1.2 });
  }

  async load(map: ComponentMap) {
    const [fr, fg, fb] = map.highlight.fault_rgb, [gr, gg, gb] = map.highlight.ghost_rgb;
    this.faultMat.color.setRGB(fr, fg, fb); this.faultMat.emissive.setRGB(fr, fg, fb);
    this.ghostMat.color.setRGB(gr, gg, gb); this.ghostMat.emissive.setRGB(0.01, 0.08, 0.18);
    const draco = new DRACOLoader(); draco.setDecoderPath('/draco/');
    const loader = new GLTFLoader(); loader.setDRACOLoader(draco);
    const gltf = await loader.loadAsync('/models/rotax_912is.glb');
    draco.dispose();
    const root = gltf.scene;
    this.scene.add(root);
    root.updateMatrixWorld(true);
    root.traverse((o) => { const m = o as THREE.Mesh; if (m.isMesh) { this.meshes.push(m); this.originals.set(m, m.material); } });
    this.meshCount = this.meshes.length;
    const box = new THREE.Box3().setFromObject(root);
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    this.center.copy(sphere.center); this.radius = sphere.radius;
    const eng = map.engines.rotax_912is;
    for (const [key, prefixes] of Object.entries(eng.subsystems)) {
      const hit = this.meshes.filter((m) => matches(m, prefixes, root));
      if (!hit.length || key === 'structure') continue;
      const b = new THREE.Box3(); hit.forEach((m) => b.union(new THREE.Box3().setFromObject(m)));
      this.anchors.push({ key, center: b.getCenter(new THREE.Vector3()), count: hit.length });
    }
    const pipeline = eng.faults.OIL_PRESSURE_LOSS.pipeline.flat();
    this.meshes.filter((m) => matches(m, pipeline, root)).forEach((m) => this.faulty.add(m));
    const fb2 = new THREE.Box3(); this.faulty.forEach((m) => fb2.union(new THREE.Box3().setFromObject(m)));
    if (!fb2.isEmpty()) fb2.getCenter(this.faultCenter); else this.faultCenter.copy(this.center);
    this.root = root;
    this.loaded = true;
  }

  private setHighlight(on: boolean) {
    if (on === this.highlighted) return;
    this.highlighted = on;
    for (const m of this.meshes) m.material = on ? (this.faulty.has(m) ? this.faultMat : this.ghostMat) : this.originals.get(m)!;
  }

  /**
   * u: 0..1 through the bay sequence; inject: the u at which the fault is injected; split: 0..1, how far
   * the engine has moved to the right half to make room for the Blender render beside it.
   */
  frame(u: number, inject: number, split: number, real: number, w: number, h: number): BayLabel[] {
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
    const after = u >= inject;
    this.setHighlight(after);
    this.faultMat.emissiveIntensity = 1.1 + 0.55 * Math.sin(real * 9);
    const focus = sstep(inject, inject + 0.18, u);
    const target = this.center.clone().lerp(this.faultCenter, focus * 0.85);
    const ang = 0.7 + u * 1.35 + real * 0.015;
    const elev = 0.32 + 0.08 * Math.sin(u * 3);
    const dist = this.radius * (2.55 - 0.7 * focus);
    this.camera.position.set(
      target.x + dist * Math.cos(elev) * Math.cos(ang),
      target.y + dist * Math.sin(elev),
      target.z + dist * Math.cos(elev) * Math.sin(ang),
    );
    this.camera.lookAt(target);
    if (split > 0) this.camera.setViewOffset(w, h, -w * 0.24 * split, 0, w, h); else this.camera.clearViewOffset();
    this.renderer.render(this.scene, this.camera);
    if (split > 0) this.camera.clearViewOffset();

    const v = new THREE.Vector3();
    return this.anchors.map(({ key, center, count }, i) => {
      v.copy(center).project(this.camera);
      const shown = !after ? u > 0.06 + i * 0.045 : key === 'oil';
      return { key, count, x: (v.x * 0.5 + 0.5) * w + w * 0.24 * split, y: (-v.y * 0.5 + 0.5) * h, on: shown && v.z < 1 };
    });
  }

  dispose() {
    this.meshes.forEach((m) => m.geometry.dispose());
    this.ghostMat.dispose(); this.faultMat.dispose(); this.env.dispose();
    if (this.root) this.scene.remove(this.root);
  }
}
