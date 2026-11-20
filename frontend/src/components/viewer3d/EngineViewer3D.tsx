import { Component, Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Bounds, OrbitControls, useBounds, useGLTF } from '@react-three/drei';
import { Box3, Color, Mesh, PMREMGenerator, Vector3, type Material, type MeshStandardMaterial, type Object3D } from 'three';
import * as THREE from 'three';
import type { Highlight } from '../../api/state';
import { LEVEL_COLOUR, focusNodes, highlightMap, type HighlightLevel } from './highlights';
import { componentLabel, useLabels } from '../../utils/labels';
import { ENGINE_ENV_INTENSITY, disposeEnvironment, prepareEngineMaterials, studioEnvironment } from '../../utils/engineMaterials';

type Manifest = { model_url: string; representative_geometry: string | null; components: Array<{ component_id: string; nodes: string[] }> };
export type InjectedPart = { component_id: string; reason: string };
type Props = {
  engineId: string | null;
  highlights: Highlight[] | undefined;
  injected?: InjectedPart[];                               // training mode only (D56): drawn as INJECTED
  api: (path: string, method: string, body?: unknown) => Promise<any>;
  fill?: boolean;                                          // 3D twin view: the engine fills its container
  focusSignal?: number;                                    // increments -> fly to the faulty part (keyboard F)
  bare?: boolean;                                          // canvas only (the 3D twin overlays its own header/legend)
};

const DRACO_PATH = '/draco/';                             // decoder files shipped in frontend/public/draco
const EMISSIVE_INTENSITY = 0.9;
const PULSE_PEAK = 2.2;                                  // peak glow of a highlighted part while it pulses
const PULSE_HZ = 1.2;                                    // highlighted parts breathe at this rate (P Part 6 X2)
const PULSE_MIN = 0.1;                                   // ...between this share of the peak glow and the peak
const ORBIT_DISTANCE = 0.9;                              // fault view: share of the whole-engine framing distance
const ORBIT_LIFT = 0.35;                                 // ...seen slightly from above
const AIM_TOWARD_PART = 0.35;                            // ...looking from the engine centre this far toward the part
const LOOP_SPEED = 0.6;                                  // then a slow loop around the engine (OrbitControls units)
const LOOP_DELAY_MS = 1200;                              // after the fly-to has settled

/** Image-based lighting from the shared procedural studio (utils/engineMaterials; no HDR download). */
function RoomEnv() {
  const { gl, scene } = useThree();
  useEffect(() => {
    const pmrem = new PMREMGenerator(gl);
    const room = studioEnvironment(THREE);
    const env = pmrem.fromScene(room, 0.04).texture;
    scene.environment = env;
    scene.environmentIntensity = ENGINE_ENV_INTENSITY;
    disposeEnvironment(room);
    return () => { scene.environment = null; env.dispose(); pmrem.dispose(); };
  }, [gl, scene]);
  return null;
}

/** Own copies of the materials (the cached GLB stays untouched), with the shared engine material treatment. */
function prepare(root: Object3D): void {
  root.traverse((o) => {
    if (!(o instanceof Mesh) || Array.isArray(o.material)) return;
    o.material = (o.material as MeshStandardMaterial).clone();
    o.userData.baseMaterial = o.material;
  });
  prepareEngineMaterials(root);
}

/** Apply highlight colours to every mesh under a named node; restore the original materials otherwise. */
function applyHighlights(root: Object3D, levels: Map<string, HighlightLevel>): { lit: string[]; glowing: MeshStandardMaterial[] } {
  const lit: string[] = [];
  const glowing: MeshStandardMaterial[] = [];
  const paint = (obj: Object3D, level: HighlightLevel | undefined) => {
    const here = levels.get(obj.name) ?? level;
    if (levels.has(obj.name)) lit.push(obj.name);
    if (obj instanceof Mesh) {
      const base = (obj.userData.baseMaterial ??= obj.material) as Material;
      if (here) {
        const m = (base as MeshStandardMaterial).clone();
        if ('emissive' in m) { m.emissive = new Color(LEVEL_COLOUR[here]); m.emissiveIntensity = EMISSIVE_INTENSITY; glowing.push(m); }
        obj.material = m;
      } else if (obj.material !== base) {
        obj.material = base;
      }
    }
    obj.children.forEach((c) => paint(c, here));
  };
  paint(root, undefined);
  return { lit, glowing };
}

function Model({ url, levels, onLit, focusRequest }: { url: string; levels: Map<string, HighlightLevel>;
                                                      onLit: (n: string[]) => void; focusRequest: number }) {
  const { scene } = useGLTF(url, DRACO_PATH);
  const root = useMemo(() => { const r = scene.clone(true); prepare(r); return r; }, [scene]);  // own copy per viewer
  const glowing = useRef<MeshStandardMaterial[]>([]);
  const bounds = useBounds();
  const get = useThree((st) => st.get);
  useEffect(() => { const r = applyHighlights(root, levels); glowing.current = r.glowing; onLit(r.lit); }, [root, levels, onLit]);
  useFrame(({ clock }) => {                                // pulse: the eye finds the faulty part at once
    const k = PULSE_MIN + (1 - PULSE_MIN) * (0.5 + 0.5 * Math.sin(clock.elapsedTime * 2 * Math.PI * PULSE_HZ));
    for (const m of glowing.current) m.emissiveIntensity = PULSE_PEAK * k;
  });
  // fly to the highest-level parts when that set changes (not every message) or on request. A new engine model
  // frames the whole engine; highlights clearing leaves the camera where it is (no jumping back and forth while a
  // diagnosis hovers at its threshold).
  const target = useMemo(() => focusNodes(levels).join('|'), [levels]);
  const framed = useRef<Object3D | null>(null);
  useEffect(() => {
    const names = new Set(target ? target.split('|') : []);
    const box = new Box3();
    root.traverse((o) => { if (names.has(o.name)) box.expandByObject(o); });
    const controls = get().controls as unknown as { autoRotate: boolean; autoRotateSpeed: number } | null;
    if (box.isEmpty()) {
      if (framed.current !== root) bounds.refresh(root).reset().clip();     // drei 9.122: reset() moves the camera
      if (controls) controls.autoRotate = false;
    } else {
      // stay outside the engine: orbit to the side where the part faces the viewer, whole engine still in frame,
      // aim a little toward the part, then loop slowly around it (P Part 6 X2)
      const { center, distance } = bounds.refresh(root).getSize();
      const part = box.getCenter(new Vector3());
      const out = part.clone().sub(center);
      if (out.lengthSq() < 1e-9) out.copy(get().camera.position).sub(center);
      out.normalize().add(new Vector3(0, ORBIT_LIFT, 0)).normalize();
      bounds.moveTo(center.clone().addScaledVector(out, distance * ORBIT_DISTANCE))
        .lookAt({ target: center.clone().lerp(part, AIM_TOWARD_PART) });
      if (controls) {
        controls.autoRotate = false;
        window.setTimeout(() => { controls.autoRotate = true; controls.autoRotateSpeed = LOOP_SPEED; }, LOOP_DELAY_MS);
      }
    }
    framed.current = root;
  }, [target, focusRequest, root, bounds]);
  return <primitive object={root} />;
}

class ModelBoundary extends Component<{ children: ReactNode; resetKey: string }, { error: string | null }> {
  state = { error: null as string | null };
  static getDerivedStateFromError(e: Error) { return { error: e.message }; }
  componentDidUpdate(prev: { resetKey: string }) { if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null }); }
  render() {
    return this.state.error
      ? <div className="p-4 text-xs font-mono text-slate-300">3D model unavailable: {this.state.error}. Readings and alerts are unaffected.</div>
      : this.props.children;
  }
}

/** 3D engine view (M6-05): loads the engine's web model named by the component manifest and lights exactly the
 *  nodes listed in state.highlights, in the colour of their level. Highlights come from diagnosis + status (D5);
 *  the viewer has no fault tables of its own. */
export default function EngineViewer3D({ engineId, highlights: detected, injected, api, fill, focusSignal = 0, bare }: Props) {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState('');
  const [lit, setLit] = useState<string[]>([]);
  const [focusRequest, setFocusRequest] = useState(0);
  const labels = useLabels();
  const highlights = useMemo<Highlight[]>(() => {
    const nodesOf = new Map((manifest?.components ?? []).map((c) => [c.component_id, c.nodes]));
    const training = (injected ?? []).map((p) => ({ component_id: p.component_id, level: 'INJECTED' as const,
      nodes: nodesOf.get(p.component_id) ?? [], reason: p.reason }));
    return [...(detected ?? []), ...training];
  }, [detected, injected, manifest]);
  const levels = useMemo(() => highlightMap(highlights), [highlights]);

  useEffect(() => {
    setManifest(null); setError(''); setLit([]);
    if (!engineId) return;
    api(`/api/v1/engines/${encodeURIComponent(engineId)}/components`, 'GET')
      .then((m) => setManifest(m)).catch((e) => setError(String(e?.message ?? e)));
  }, [engineId, api]);

  const missing = (highlights ?? []).filter((h) => !h.nodes?.length);
  return (
    <section className={bare ? 'h-full' : `surface-panel p-4 sm:p-5 rounded-sm ${fill ? 'h-full flex flex-col' : ''}`} data-highlighted-nodes={lit.join(',')}>
      {!bare && <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-white tracking-tight">3D engine</h3>
        <div className="flex items-center gap-3">
          {manifest?.representative_geometry && <span className="text-xs font-mono text-slate-400">{manifest.representative_geometry}</span>}
          {lit.length > 0 && <button type="button" onClick={() => setFocusRequest((n) => n + 1)}
            className="rounded-sm border border-surface-border px-2 py-1 text-xs text-slate-200 hover:border-surface-border-strong">Focus fault</button>}
        </div>
      </div>}
      <div className={bare ? 'h-full' : `mt-3 rounded-sm border border-surface-border bg-black/20 ${fill ? 'flex-1 min-h-0' : 'h-[min(60vh,420px)]'}`}>
        {error ? <div className="p-4 text-xs font-mono text-slate-300">{error}</div>
          : !manifest ? <div className="p-4 text-xs font-mono text-slate-400">Loading component manifest…</div>
          : <ModelBoundary resetKey={manifest.model_url}>
              <Canvas camera={{ position: [2.5, 1.5, 2.5], fov: 40 }} dpr={[1, 2]}>
                <RoomEnv />
                <directionalLight position={[3, 4, 3]} intensity={1.4} />
                <Suspense fallback={null}>
                  <Bounds fit clip margin={1.2}>
                    <Model url={manifest.model_url} levels={levels} onLit={setLit} focusRequest={focusRequest + focusSignal} />
                  </Bounds>
                </Suspense>
                <OrbitControls makeDefault enableDamping />
              </Canvas>
            </ModelBoundary>}
      </div>
      {!bare && <ul className="mt-2 space-y-0.5 text-xs font-mono">
        {(highlights ?? []).length === 0 && <li className="text-slate-500">No part highlighted: no confident diagnosis.</li>}
        {(highlights ?? []).map((h, i) => (
          <li key={`${h.component_id}-${i}`} className="flex items-center gap-2 text-slate-300">
            <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: LEVEL_COLOUR[h.level as HighlightLevel] }} />
            <span>{h.level === 'INJECTED' ? 'INJECTED (training)' : h.level}</span><span>{componentLabel(labels, h.component_id)}</span><span className="text-slate-500">{h.reason}</span>
            {h.marker_for && <span className="text-slate-500">· part not in the model: {h.marker_for}</span>}
          </li>
        ))}
        {missing.length > 0 && <li className="text-slate-500">{missing.length} highlighted component(s) have no node in this model.</li>}
      </ul>}
    </section>
  );
}
