import { Component, Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Bounds, OrbitControls, useBounds, useGLTF } from '@react-three/drei';
import { Box3, Color, Mesh, PMREMGenerator, Vector3, type Material, type MeshStandardMaterial, type Object3D } from 'three';
import * as THREE from 'three';
import type { Highlight } from '../../api/state';
import { LEVEL_COLOUR, focusNodes, highlightMap, type HighlightLevel } from './highlights';
import { componentLabel, useLabels } from '../../utils/labels';
import { ENGINE_ENV_INTENSITY, disposeEnvironment, prepareEngineMaterials, studioEnvironment } from '../../utils/engineMaterials';
import InfoTooltip from '../InfoTooltip';

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
  autoRotate?: boolean;                                    // default true: cinematic auto-rotation like docs_site
};

const DRACO_PATH = '/draco/';                             // decoder files shipped in frontend/public/draco
const EMISSIVE_INTENSITY = 0.9;
const PULSE_PEAK = 2.2;                                  // peak glow of a highlighted part while it pulses
const PULSE_HZ = 1.2;                                    // highlighted parts breathe at this rate (P Part 6 X2)
const PULSE_MIN = 0.1;                                   // ...between this share of the peak glow and the peak
const ORBIT_DISTANCE = 2.2;                               // fault view: comfortable distance keeping the engine in view
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
  // Normalize scale and center to match docs_site / standard CAD presentation
  const box = new Box3().setFromObject(root);
  const center = box.getCenter(new Vector3());
  const size = box.getSize(new Vector3());
  const maxDim = Math.max(size.x, size.y, size.z);
  const scale = 1.8 / (maxDim || 1);

  root.scale.setScalar(scale);
  root.position.x = -center.x * scale;
  root.position.y = -center.y * scale + 0.05;
  root.position.z = -center.z * scale;
  root.updateWorldMatrix(true, true);

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

function Model({ url, levels, onLit, focusRequest, autoRotateEnabled }: { url: string; levels: Map<string, HighlightLevel>;
                                                      onLit: (n: string[]) => void; focusRequest: number; autoRotateEnabled: boolean }) {
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
    const controls = get().controls as unknown as { autoRotate: boolean; autoRotateSpeed: number; target: Vector3 } | null;
    if (box.isEmpty()) {
      if (controls) {
        controls.autoRotate = autoRotateEnabled;
        controls.autoRotateSpeed = 0.8;
      }
      if (framed.current !== root) {
        bounds.moveTo([1.65, 1.1, 2.0]).lookAt({ target: [0, 0.05, 0] });
      }
    } else {
      // stay outside the engine: orbit to the side where the part faces the viewer, whole engine still in frame,
      // aim a little toward the part, then loop slowly around it (P Part 6 X2)
      const part = box.getCenter(new Vector3());
      const out = part.clone().sub(new Vector3(0, 0.05, 0));
      if (out.lengthSq() < 1e-9) out.set(1, 0.4, 1);
      out.normalize().add(new Vector3(0, ORBIT_LIFT, 0)).normalize();
      bounds.moveTo(new Vector3(0, 0.05, 0).addScaledVector(out, ORBIT_DISTANCE))
        .lookAt({ target: new Vector3(0, 0.05, 0).lerp(part, AIM_TOWARD_PART) });
      if (controls) {
        controls.autoRotate = false;
        if (autoRotateEnabled) {
          window.setTimeout(() => { controls.autoRotate = true; controls.autoRotateSpeed = LOOP_SPEED; }, LOOP_DELAY_MS);
        }
      }
    }
    framed.current = root;
  }, [target, focusRequest, root, bounds, autoRotateEnabled, get]);

  useEffect(() => {
    const controls = get().controls as unknown as { autoRotate: boolean; autoRotateSpeed: number } | null;
    if (controls) {
      controls.autoRotate = autoRotateEnabled;
      controls.autoRotateSpeed = 0.8;
    }
  }, [autoRotateEnabled, get]);

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
export default function EngineViewer3D({ engineId, highlights: detected, injected, api, fill, focusSignal = 0, bare, autoRotate: initialAutoRotate = true }: Props) {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState('');
  const [lit, setLit] = useState<string[]>([]);
  const [focusRequest, setFocusRequest] = useState(0);
  const [autoRotate, setAutoRotate] = useState(initialAutoRotate);
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
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-white tracking-tight">3D engine</h3>
          <InfoTooltip
            title="Interactive 3D Engine Twin"
            content="A realistic 3D CAD digital twin of the selected aircraft engine. Drag with your mouse or finger to rotate and inspect internal components. When a diagnostic fault or anomaly is detected, the affected physical component automatically illuminates."
            width={300}
          />
        </div>
        <div className="flex items-center gap-2">
          {manifest?.representative_geometry && <span className="text-xs font-mono text-slate-400">{manifest.representative_geometry}</span>}
          <button
            type="button"
            onClick={() => setAutoRotate((r) => !r)}
            className="rounded-sm border border-surface-border px-2 py-1 text-xs font-mono text-slate-300 hover:text-white hover:border-surface-border-strong transition-colors"
            title={autoRotate ? 'Pause automated 3D rotation' : 'Resume automated 3D rotation'}
          >
            {autoRotate ? 'Pause rotation' : 'Auto-rotate'}
          </button>
          {lit.length > 0 && <button type="button" onClick={() => setFocusRequest((n) => n + 1)}
            className="rounded-sm border border-surface-border px-2 py-1 text-xs text-slate-200 hover:border-surface-border-strong">Focus fault</button>}
        </div>
      </div>}
      <div className={bare ? 'h-full' : `mt-3 rounded-sm border border-surface-border bg-black/20 ${fill ? 'flex-1 min-h-0' : 'h-[min(60vh,420px)]'}`}>
        {error ? <div className="p-4 text-xs font-mono text-slate-300">{error}</div>
          : !manifest ? <div className="p-4 text-xs font-mono text-slate-400">Loading component manifest…</div>
          : <ModelBoundary resetKey={manifest.model_url}>
              <Canvas camera={{ position: [1.65, 1.1, 2.0], fov: 42 }} dpr={[1, 2]}>
                <RoomEnv />
                <directionalLight position={[3, 4, 3]} intensity={1.4} />
                <Suspense fallback={null}>
                  <Bounds maxDuration={0.9}>
                    <Model url={manifest.model_url} levels={levels} onLit={setLit} focusRequest={focusRequest + focusSignal} autoRotateEnabled={autoRotate} />
                  </Bounds>
                </Suspense>
                <OrbitControls
                  makeDefault
                  target={[0, 0.05, 0]}
                  enableDamping
                  dampingFactor={0.05}
                  autoRotate={autoRotate}
                  autoRotateSpeed={0.8}
                  maxPolarAngle={Math.PI / 2 + 0.15}
                  minPolarAngle={0.15}
                  minDistance={1.0}
                  maxDistance={12}
                />
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
