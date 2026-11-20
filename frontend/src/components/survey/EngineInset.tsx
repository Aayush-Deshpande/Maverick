import { useEffect, useRef, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { ENGINE_MODELS, createStage, disposeObject, fetchModel, frameModel, posterFor } from './engineScene';

interface Props {
  engineId: string;
  label: string;
  /** Start streaming the full CAD model as soon as the browser is idle (hero) or only when visible. */
  eager?: boolean;
}

const mb = (bytes: number) => (bytes / 1e6).toFixed(1);

/**
 * Full-detail CAD engine in a map inset. A poster rendered from the same model, light and camera
 * paints instantly; the full GLB streams with byte progress, decodes in Draco workers, and replaces
 * the poster in place once the first frame is compiled.
 */
export function EngineInset({ engineId, label, eager = false }: Props) {
  const mount = useRef<HTMLDivElement>(null);
  const resetRef = useRef<(() => void) | null>(null);
  const [phase, setPhase] = useState<'poster' | 'loading' | 'ready' | 'failed'>('poster');
  const [progress, setProgress] = useState({ loaded: 0, total: 0 });
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const element = mount.current;
    if (!element) return;
    let cancelled = false;
    let started = false;
    let cleanup = () => {};
    const controller = new AbortController();
    setPhase('poster');
    setProgress({ loaded: 0, total: 0 });

    async function load() {
      if (started || cancelled || !element) return;
      started = true;
      setPhase('loading');
      const [THREE, { GLTFLoader }, { DRACOLoader }, { OrbitControls }, { RoomEnvironment }] = await Promise.all([
        import('three'),
        import('three/examples/jsm/loaders/GLTFLoader.js'),
        import('three/examples/jsm/loaders/DRACOLoader.js'),
        import('three/examples/jsm/controls/OrbitControls.js'),
        import('three/examples/jsm/environments/RoomEnvironment.js'),
      ]);
      // Download and module import overlap; decode starts the moment both are ready.
      const bytesPromise = fetchModel(ENGINE_MODELS[engineId], (loaded, total) => { if (!cancelled) setProgress({ loaded, total }); }, controller.signal);
      if (cancelled) return;
      const { renderer, scene, camera, env } = createStage(THREE, RoomEnvironment, element);
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true; controls.enablePan = false; controls.autoRotateSpeed = 0.5;
      controls.minDistance = 2.4; controls.maxDistance = 9;
      const draco = new DRACOLoader();
      draco.setDecoderPath('/draco/');
      draco.setWorkerLimit(Math.min(4, Math.max(2, (navigator.hardwareConcurrency || 4) - 1)));
      draco.preload();
      const loader = new GLTFLoader();
      loader.setDRACOLoader(draco);
      let frame = 0; let visible = true; let model: import('three').Object3D | null = null;
      let home: ((c: import('three').PerspectiveCamera, a: number) => void) | null = null;
      const resize = () => {
        const w = element.clientWidth, h = element.clientHeight;
        if (!w || !h) return;
        renderer.setSize(w, h, false);
        camera.aspect = w / h; camera.updateProjectionMatrix();
      };
      const ro = new ResizeObserver(resize); ro.observe(element);
      const io = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; }); io.observe(element);
      cleanup = () => { cancelAnimationFrame(frame); ro.disconnect(); io.disconnect(); controls.dispose(); draco.dispose(); env.dispose(); if (model) disposeObject(model); renderer.dispose(); renderer.domElement.remove(); resetRef.current = null; };
      resize();
      const bytes = await bytesPromise;
      if (cancelled) return;
      const gltf = await loader.parseAsync(bytes, '/models/');
      if (cancelled) { disposeObject(gltf.scene); return; }
      model = gltf.scene;
      const framed = frameModel(THREE, model);
      scene.add(framed.group);
      home = framed.home;
      const goHome = () => { home?.(camera, element.clientWidth / Math.max(1, element.clientHeight)); controls.target.set(0, 0, 0); controls.update(); };
      resetRef.current = goHome;
      goHome();
      await renderer.compileAsync(scene, camera);
      if (cancelled) return;
      renderer.render(scene, camera);
      setPhase('ready');
      const reduce = matchMedia('(prefers-reduced-motion: reduce)');
      const animate = () => {
        frame = requestAnimationFrame(animate);
        if (!visible || document.hidden) return;
        controls.autoRotate = !reduce.matches;
        controls.update();
        renderer.render(scene, camera);
      };
      animate();
    }

    const start = () => { load().catch((error) => { if (cancelled) return; console.error('Engine inset:', error); cleanup(); setPhase('failed'); }); };
    let idle: number | undefined;
    let io: IntersectionObserver | undefined;
    if (eager) {
      const kick = () => { idle = (window.requestIdleCallback ?? ((cb: () => void) => window.setTimeout(cb, 200)))(start, { timeout: 1200 } as IdleRequestOptions) as unknown as number; };
      if (document.readyState === 'complete') kick(); else window.addEventListener('load', kick, { once: true });
    } else {
      io = new IntersectionObserver(([entry]) => { if (entry.isIntersecting) { io?.disconnect(); start(); } }, { rootMargin: '200px' });
      io.observe(element);
    }
    return () => { cancelled = true; controller.abort(); io?.disconnect(); if (idle) (window.cancelIdleCallback ?? clearTimeout)(idle); cleanup(); };
  }, [engineId, eager, retry]);

  const pct = progress.total ? Math.round((progress.loaded / progress.total) * 100) : 0;
  return <div className="sv-inset" data-phase={phase}>
    <img className="sv-inset-poster" src={posterFor(engineId)} alt={`${label}, full-detail CAD model`} width={1200} height={900} decoding="async" />
    <div className="sv-inset-gl" ref={mount} role="img" aria-label={`${label}: interactive full CAD model. Drag to orbit, scroll to zoom.`} />
    <div className="sv-inset-status" aria-live="polite">
      {phase === 'loading' && <><span className="sv-inset-bar" style={{ ['--p' as string]: `${pct}%` }} /><span>Full CAD {progress.total ? `${mb(progress.loaded)} / ${mb(progress.total)} MB` : 'connecting…'}</span></>}
      {phase === 'ready' && <><span>Full CAD · drag to orbit</span><button type="button" onClick={() => resetRef.current?.()} aria-label="Reset view"><RotateCcw size={12} /></button></>}
      {phase === 'failed' && <button type="button" onClick={() => setRetry((v) => v + 1)}>3D unavailable · retry</button>}
    </div>
  </div>;
}
