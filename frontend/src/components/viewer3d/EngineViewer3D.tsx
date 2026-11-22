import { Component, Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Bounds, OrbitControls, useBounds, useGLTF } from '@react-three/drei';
import { Box3, Color, Mesh, PMREMGenerator, Vector3, type Material, type MeshStandardMaterial, type Object3D } from 'three';
import * as THREE from 'three';
import { Box, Flame, Radio, ScanLine } from 'lucide-react';
import type { Highlight } from '../../api/state';
import { LEVEL_COLOUR, focusNodes, highlightMap, type HighlightLevel } from './highlights';
import { componentLabel, useLabels } from '../../utils/labels';
import { ENGINE_ENV_INTENSITY, disposeEnvironment, prepareEngineMaterials, studioEnvironment } from '../../utils/engineMaterials';
import {
  createGlassCasingMaterial,
  createGhostOverlayMaterial,
  createSmokedCasingMaterial,
  createThermalHeatmapMaterial,
  updateThermalMaterial,
} from '../../utils/engineShaders';
import { classifyNode, findCylinderNumber } from '../../utils/engineComponents';
import ThermalLegend, { getReadingVal, type RawReadingValue } from './ThermalLegend';
import InfoTooltip from '../InfoTooltip';

type Manifest = {
  model_url: string;
  representative_geometry: string | null;
  components: Array<{ component_id: string; nodes: string[]; subsystem?: string; cylinder?: number | null }>;
};

export type InjectedPart = { component_id: string; reason: string };
export type EngineViewMode = 'solid' | 'glass' | 'thermal' | 'ghost';

type Props = {
  engineId: string | null;
  highlights: Highlight[] | undefined;
  injected?: InjectedPart[];                               // training mode only (D56): drawn as INJECTED
  api: (path: string, method: string, body?: unknown) => Promise<any>;
  fill?: boolean;                                          // 3D twin view: the engine fills its container
  focusSignal?: number;                                    // increments -> fly to the faulty part (keyboard F)
  bare?: boolean;                                          // canvas only (the 3D twin overlays its own header/legend)
  autoRotate?: boolean;                                    // default true: cinematic auto-rotation like docs_site
  readings?: Record<string, RawReadingValue> | null;
  viewMode?: EngineViewMode;
  onViewModeChange?: (mode: EngineViewMode) => void;
};

const DRACO_PATH = '/draco/';                             // decoder files shipped in frontend/public/draco
const EMISSIVE_INTENSITY = 0.9;
const PULSE_PEAK = 2.2;                                  // peak glow of a highlighted part while it pulses
const PULSE_HZ = 1.2;                                    // highlighted parts breathe at this rate (P Part 6 X2)
const PULSE_MIN = 0.1;                                   // ...between this share of the peak glow and the peak
const ORBIT_DISTANCE = 2.2;                               // fault view: comfortable distance keeping the engine in view
const ORBIT_LIFT = 0.35;                                 // ...seen slightly from above

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

type ThermalMeshTarget = {
  mesh: Mesh;
  mat: MeshStandardMaterial;
  isExhaust: boolean;
  cyl: number | null;
};

type FadingMeshTarget = {
  mesh: Mesh;
  mat: MeshStandardMaterial;
  base: Material;
};

/** Apply view mode materials and highlight colours; restore original materials otherwise. */
function applyMaterialsAndHighlights(
  root: Object3D,
  levels: Map<string, HighlightLevel>,
  viewMode: EngineViewMode,
  manifest: Manifest | null,
  readings?: Record<string, RawReadingValue> | null,
  sharedGlass?: Material,
  sharedSmoked?: Material,
  sharedGhost?: Material
): { lit: string[]; glowing: MeshStandardMaterial[]; fading: FadingMeshTarget[]; thermalTargets: ThermalMeshTarget[] } {
  const lit: string[] = [];
  const glowing: MeshStandardMaterial[] = [];
  const fading: FadingMeshTarget[] = [];
  const thermalTargets: ThermalMeshTarget[] = [];

  // Build O(1) node -> component metadata lookup map
  const compMap = new Map<string, { component_id: string; subsystem?: string; cylinder?: number | null }>();
  if (manifest?.components) {
    for (const c of manifest.components) {
      for (const nodeName of c.nodes ?? []) {
        compMap.set(nodeName, c);
      }
    }
  }

  const paint = (obj: Object3D, inheritedLevel: HighlightLevel | undefined) => {
    const here = levels.get(obj.name) ?? inheritedLevel;
    if (levels.has(obj.name)) lit.push(obj.name);

    if (obj instanceof Mesh) {
      const base = (obj.userData.baseMaterial ??= obj.material) as Material;
      const comp = compMap.get(obj.name);
      const category = classifyNode(obj.name, comp?.component_id, comp?.subsystem, comp?.cylinder);
      const cyl = findCylinderNumber(obj.name, comp?.component_id, comp?.cylinder);

      if (here) {
        // Diagnosis/Anomaly highlight takes absolute visual precedence
        const m = (base as MeshStandardMaterial).clone();
        if ('emissive' in m) {
          m.emissive = new Color(LEVEL_COLOUR[here]);
          m.emissiveIntensity = EMISSIVE_INTENSITY;
          glowing.push(m);
        }
        obj.userData.isHighlight = true;
        obj.material = m;
      } else if (obj.userData.isHighlight && obj.material && 'emissive' in (obj.material as MeshStandardMaterial)) {
        // Smoothly fade out previously glowing fault highlight
        fading.push({ mesh: obj, mat: obj.material as MeshStandardMaterial, base });
      } else if (viewMode === 'solid') {
        if (obj.material !== base) obj.material = base;
      } else if (viewMode === 'glass') {
        if (category === 'casing') {
          obj.material = sharedGlass ?? base;
        } else {
          if (obj.material !== base) obj.material = base;
        }
      } else if (viewMode === 'thermal') {
        if (category === 'casing') {
          obj.material = sharedSmoked ?? base;
        } else if (category === 'internal') {
          const temp = (cyl ? getReadingVal(readings?.[`CHT_${cyl}`]) : null) ?? getReadingVal(readings?.['CHT']) ?? 115;
          const mat = (obj.userData.thermalMat ??= createThermalHeatmapMaterial(temp, 50, 140, false));
          updateThermalMaterial(mat, temp, 50, 140, false);
          obj.material = mat;
          thermalTargets.push({ mesh: obj, mat, isExhaust: false, cyl });
        } else if (category === 'exhaust') {
          const temp = (cyl ? getReadingVal(readings?.[`EGT_${cyl}`]) : null) ?? getReadingVal(readings?.['EGT']) ?? getReadingVal(readings?.['TIT']) ?? 800;
          const mat = (obj.userData.thermalMat ??= createThermalHeatmapMaterial(temp, 400, 950, true));
          updateThermalMaterial(mat, temp, 400, 950, true);
          obj.material = mat;
          thermalTargets.push({ mesh: obj, mat, isExhaust: true, cyl });
        } else {
          if (obj.material !== base) obj.material = base;
        }
      } else if (viewMode === 'ghost') {
        obj.material = sharedGhost ?? base;
      }
    }

    obj.children.forEach((c) => paint(c, here));
  };

  paint(root, undefined);
  return { lit, glowing, fading, thermalTargets };
}

function Model({
  url,
  levels,
  onLit,
  focusRequest,
  autoRotateEnabled,
  viewMode,
  manifest,
  readings,
}: {
  url: string;
  levels: Map<string, HighlightLevel>;
  onLit: (n: string[]) => void;
  focusRequest: number;
  autoRotateEnabled: boolean;
  viewMode: EngineViewMode;
  manifest: Manifest | null;
  readings?: Record<string, RawReadingValue> | null;
}) {
  const { scene } = useGLTF(url, DRACO_PATH);
  const root = useMemo(() => { const r = scene.clone(true); prepare(r); return r; }, [scene]);
  const glowing = useRef<MeshStandardMaterial[]>([]);
  const fading = useRef<FadingMeshTarget[]>([]);
  const thermalTargets = useRef<ThermalMeshTarget[]>([]);
  const rotateTimer = useRef<number | null>(null);
  const bounds = useBounds();
  const get = useThree((st) => st.get);

  // Shared singleton materials for performance
  const glassMat = useMemo(() => createGlassCasingMaterial(), []);
  const smokedMat = useMemo(() => createSmokedCasingMaterial(), []);
  const ghostMat = useMemo(() => createGhostOverlayMaterial(), []);

  useEffect(() => {
    const r = applyMaterialsAndHighlights(root, levels, viewMode, manifest, readings, glassMat, smokedMat, ghostMat);
    glowing.current = r.glowing;
    fading.current = r.fading;
    thermalTargets.current = r.thermalTargets;
    onLit(r.lit);
  }, [root, levels, viewMode, manifest, glassMat, smokedMat, ghostMat, onLit]);

  // Update dynamic thermal shaders when live readings tick
  useEffect(() => {
    if (viewMode !== 'thermal') return;
    for (const t of thermalTargets.current) {
      const temp = t.isExhaust
        ? ((t.cyl ? getReadingVal(readings?.[`EGT_${t.cyl}`]) : null) ?? getReadingVal(readings?.['EGT']) ?? getReadingVal(readings?.['TIT']) ?? 800)
        : ((t.cyl ? getReadingVal(readings?.[`CHT_${t.cyl}`]) : null) ?? getReadingVal(readings?.['CHT']) ?? 115);
      updateThermalMaterial(t.mat, temp, t.isExhaust ? 400 : 50, t.isExhaust ? 950 : 140, t.isExhaust);
    }
  }, [readings, viewMode]);

  useFrame(({ clock }, delta) => {
    // Pulse: the eye finds the faulty part at once
    const k = PULSE_MIN + (1 - PULSE_MIN) * (0.5 + 0.5 * Math.sin(clock.elapsedTime * 2 * Math.PI * PULSE_HZ));
    for (const m of glowing.current) m.emissiveIntensity = PULSE_PEAK * k;

    // Smoothly decay unhighlighted materials back to baseline
    if (fading.current.length > 0) {
      const activeFading: FadingMeshTarget[] = [];
      for (const item of fading.current) {
        item.mat.emissiveIntensity = THREE.MathUtils.damp(item.mat.emissiveIntensity, 0, 7, delta);
        if (item.mat.emissiveIntensity > 0.02) {
          activeFading.push(item);
        } else {
          item.mesh.material = item.base;
          delete item.mesh.userData.isHighlight;
        }
      }
      fading.current = activeFading;
    }
  });

  const target = useMemo(() => focusNodes(levels).join('|'), [levels]);
  const framed = useRef<Object3D | null>(null);

  useEffect(() => {
    if (rotateTimer.current) {
      window.clearTimeout(rotateTimer.current);
      rotateTimer.current = null;
    }

    const names = new Set(target ? target.split('|') : []);
    const box = new Box3();
    root.traverse((o) => { if (names.has(o.name)) box.expandByObject(o); });
    const controls = get().controls as unknown as { autoRotate: boolean; autoRotateSpeed: number; target: Vector3 } | null;

    if (box.isEmpty()) {
      // Clear/Reset/Nominal state:
      // Pause rotation while camera smoothly flies back to overview
      if (controls) {
        controls.autoRotate = false;
        if (autoRotateEnabled) {
          rotateTimer.current = window.setTimeout(() => {
            if (controls) {
              controls.autoRotate = true;
              controls.autoRotateSpeed = 0.8;
            }
          }, 950);
        }
      }
      // Smoothly animate back to default hero overview framing, looking at engine center
      bounds.moveTo([1.65, 1.1, 2.0]).lookAt({ target: [0, 0.05, 0] });
    } else {
      // Fault injected:
      // Position camera along the vector facing the faulty part, looking towards the engine center
      // so the rotation axis stays concentric with the engine center of mass (just like docs_site!)
      const part = box.getCenter(new Vector3());
      const out = part.clone().sub(new Vector3(0, 0.05, 0));
      out.y = 0;
      if (out.lengthSq() < 1e-9) out.set(1, 0, 1);
      out.normalize();

      const camPos = new Vector3(0, 0.05, 0)
        .addScaledVector(out, ORBIT_DISTANCE)
        .add(new Vector3(0, ORBIT_LIFT, 0));

      bounds.moveTo(camPos).lookAt({ target: [0, 0.05, 0] });

      if (controls) {
        controls.autoRotate = false;
        if (autoRotateEnabled) {
          rotateTimer.current = window.setTimeout(() => {
            if (controls) {
              controls.autoRotate = true;
              controls.autoRotateSpeed = 0.5; // gentle inspection rotation around central axis
            }
          }, 1200);
        }
      }
    }
    framed.current = root;

    return () => {
      if (rotateTimer.current) {
        window.clearTimeout(rotateTimer.current);
        rotateTimer.current = null;
      }
    };
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

/** 3D engine view (M6-05, UX-01): loads the engine's web model named by the component manifest and lights exactly the
 *  nodes listed in state.highlights, in the colour of their level. Highlights come from diagnosis + status (D5).
 *  Supports multi-mode rendering: Solid CAD PBR, Physical X-Ray Glass, Dynamic FLIR Thermal Heatmaps, and Twin Ghost. */
export default function EngineViewer3D({
  engineId,
  highlights: detected,
  injected,
  api,
  fill,
  focusSignal = 0,
  bare,
  autoRotate: propAutoRotate,
  readings,
  viewMode: controlledViewMode,
  onViewModeChange,
}: Props) {
  const [internalMode, setInternalMode] = useState<EngineViewMode>('solid');
  const viewMode = controlledViewMode ?? internalMode;
  const setMode = onViewModeChange ?? setInternalMode;

  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState('');
  const [lit, setLit] = useState<string[]>([]);
  const [focusRequest, setFocusRequest] = useState(0);
  const [internalAutoRotate, setInternalAutoRotate] = useState(true);
  const autoRotate = propAutoRotate !== undefined ? propAutoRotate : internalAutoRotate;
  const setAutoRotate = setInternalAutoRotate;
  const labels = useLabels();

  const highlights = useMemo<Highlight[]>(() => {
    const nodesOf = new Map((manifest?.components ?? []).map((c) => [c.component_id, c.nodes]));
    const training = (injected ?? []).map((p) => ({
      component_id: p.component_id,
      level: 'INJECTED' as const,
      nodes: nodesOf.get(p.component_id) ?? [],
      reason: p.reason,
    }));
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
      {!bare && (
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-white tracking-tight">3D engine digital twin</h3>
            <InfoTooltip
              title="Interactive 3D Engine Twin"
              content="A realistic 3D CAD digital twin of the selected aircraft engine. Switch between Solid PBR, X-Ray Glass, Thermal FLIR, and Holographic Ghost. When a diagnostic fault is detected, affected physical components automatically illuminate."
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
            {lit.length > 0 && (
              <button
                type="button"
                onClick={() => setFocusRequest((n) => n + 1)}
                className="rounded-sm border border-surface-border px-2 py-1 text-xs text-slate-200 hover:border-surface-border-strong"
              >
                Focus fault
              </button>
            )}
          </div>
        </div>
      )}

      <div className={`relative overflow-hidden ${bare ? 'h-full' : `mt-3 rounded-sm border border-surface-border bg-black/20 ${fill ? 'flex-1 min-h-0' : 'h-[min(60vh,420px)]'}`}`}>
        {/* View Mode Segmented HUD Toolbar (rendered in non-bare embed, e.g. standalone console card) */}
        {!bare && (
          <div className="surface-panel absolute right-2 sm:right-3 top-2 sm:top-3 z-10 flex items-center gap-1 rounded-sm border border-surface-border bg-[#f7f6f0] p-1 shadow-xs text-xs font-mono">
            <button
              type="button"
              onClick={() => setMode('solid')}
              className={`px-2 py-1 rounded-xs transition-colors flex items-center gap-1.5 cursor-pointer ${
                viewMode === 'solid' ? 'bg-accent text-white font-semibold shadow-xs' : 'text-slate-700 hover:text-slate-900 hover:bg-black/5'
              }`}
              title="Solid: Full physical engine CAD surface"
            >
              <Box className="w-3.5 h-3.5 text-slate-700" />
              <span className="hidden md:inline">SOLID</span>
            </button>
            <button
              type="button"
              onClick={() => setMode('glass')}
              className={`px-2 py-1 rounded-xs transition-colors flex items-center gap-1.5 cursor-pointer ${
                viewMode === 'glass' ? 'bg-accent text-white font-semibold shadow-xs' : 'text-slate-700 hover:text-slate-900 hover:bg-black/5'
              }`}
              title="X-Ray: Optical glass casing revealing reciprocating internal assemblies"
            >
              <ScanLine className="w-3.5 h-3.5 text-cyan-600" />
              <span className="hidden md:inline">X-RAY</span>
            </button>
            <button
              type="button"
              onClick={() => setMode('thermal')}
              className={`px-2 py-1 rounded-xs transition-colors flex items-center gap-1.5 cursor-pointer ${
                viewMode === 'thermal' ? 'bg-accent text-white font-semibold shadow-xs' : 'text-slate-700 hover:text-slate-900 hover:bg-black/5'
              }`}
              title="Thermal: Live dynamic vertex incandescence pyrometry"
            >
              <Flame className="w-3.5 h-3.5 text-rose-600" />
              <span className="hidden md:inline">THERMAL</span>
            </button>
            <button
              type="button"
              onClick={() => setMode('ghost')}
              className={`px-2 py-1 rounded-xs transition-colors flex items-center gap-1.5 cursor-pointer ${
                viewMode === 'ghost' ? 'bg-accent text-white font-semibold shadow-xs' : 'text-slate-700 hover:text-slate-900 hover:bg-black/5'
              }`}
              title="Wireframe: Holographic structural reference model"
            >
              <Radio className="w-3.5 h-3.5 text-indigo-600" />
              <span className="hidden md:inline">WIREFRAME</span>
            </button>
          </div>
        )}

        {/* Dynamic Thermal FLIR Overlay */}
        {viewMode === 'thermal' && (
          <div className="absolute left-2 sm:left-3 bottom-2 sm:bottom-3 z-10 max-w-[calc(100%-1rem)] sm:max-w-md pointer-events-auto">
            <ThermalLegend readings={readings} />
          </div>
        )}

        {error ? (
          <div className="p-4 text-xs font-mono text-slate-300">{error}</div>
        ) : !manifest ? (
          <div className="p-4 text-xs font-mono text-slate-400">Loading component manifest…</div>
        ) : (
          <ModelBoundary resetKey={manifest.model_url}>
            <Canvas camera={{ position: [1.65, 1.1, 2.0], fov: 42 }} dpr={[1, 2]}>
              <RoomEnv />
              <directionalLight position={[3, 4, 3]} intensity={1.4} />
              <Suspense fallback={null}>
                <Bounds maxDuration={0.9}>
                  <Model
                    url={manifest.model_url}
                    levels={levels}
                    onLit={setLit}
                    focusRequest={focusRequest + focusSignal}
                    autoRotateEnabled={autoRotate}
                    viewMode={viewMode}
                    manifest={manifest}
                    readings={readings}
                  />
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
          </ModelBoundary>
        )}
      </div>

      {!bare && (
        <ul className="mt-2 space-y-0.5 text-xs font-mono">
          {(highlights ?? []).length === 0 && <li className="text-slate-500">No part highlighted: no confident diagnosis.</li>}
          {(highlights ?? []).map((h, i) => (
            <li key={`${h.component_id}-${i}`} className="flex items-center gap-2 text-slate-300">
              <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: LEVEL_COLOUR[h.level as HighlightLevel] }} />
              <span>{h.level === 'INJECTED' ? 'INJECTED (training)' : h.level}</span>
              <span>{componentLabel(labels, h.component_id)}</span>
              <span className="text-slate-500">{h.reason}</span>
              {h.marker_for && <span className="text-slate-500">· part not in the model: {h.marker_for}</span>}
            </li>
          ))}
          {missing.length > 0 && <li className="text-slate-500">{missing.length} highlighted component(s) have no node in this model.</li>}
        </ul>
      )}
    </section>
  );
}
