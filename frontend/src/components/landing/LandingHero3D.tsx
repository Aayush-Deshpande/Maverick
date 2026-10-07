import { HudFrame } from './HudFrame';
import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { Eye, RotateCcw, Image as ImageIcon, Box, Compass } from 'lucide-react';

import { AERO_LINEUP, LineupItem } from './aeroLineup';

interface LandingHero3DProps {
  onSelectAsset?: (index: number) => void;
  onExploreTwin?: () => void;
  onLaunchConsole?: () => void;
}

export const LandingHero3D: React.FC<LandingHero3DProps> = ({
  onSelectAsset,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const [activeIndex, setActiveIndex] = useState(0);
  const activeIndexRef = useRef(0);
  activeIndexRef.current = activeIndex;

  const [viewMode, setViewMode] = useState<'3d' | 'image'>('3d');
  const [modelLoading, setModelLoading] = useState(false);
  const [loadProgress, setLoadProgress] = useState(0);
  const [loadBytes, setLoadBytes] = useState<{ loaded: number; total: number } | null>(null);
  const [isWireframe, setIsWireframe] = useState(false);
  const [isAutoOrbit, setIsAutoOrbit] = useState(true);
  const isAutoOrbitRef = useRef(true);
  isAutoOrbitRef.current = isAutoOrbit;

  const [modelStats, setModelStats] = useState<{ meshes: number; triangles: number }>({ meshes: 0, triangles: 0 });

  // Three.js instances
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const gltfLoaderRef = useRef<GLTFLoader | null>(null);

  // In-memory model cache for 0ms instant swapping
  const modelCache = useRef<Map<string, THREE.Group>>(new Map());
  const activeModelGroup = useRef<THREE.Group | null>(null);

  const originalMats = useRef<Map<string, THREE.Material | THREE.Material[]>>(new Map());
  const wireframeMats = useRef<Map<string, THREE.Material>>(new Map());

  const targetLookAt = useRef(new THREE.Vector3(0, 0, 0));
  const targetCamPos = useRef(new THREE.Vector3(0, 0.36, 2.4));
  const transitionUntil = useRef(0);

  const activeAsset = AERO_LINEUP[activeIndex];

  // Helper: Enforce that strictly ONLY the specified model is visible across cache and scene
  const enforceModelVisibility = useCallback((targetId: string) => {
    modelCache.current.forEach((grp, key) => {
      grp.visible = (key === targetId);
    });

    const scene = sceneRef.current;
    if (scene) {
      scene.children.forEach((child) => {
        if (child.name && child.name.startsWith('Model_')) {
          child.visible = (child.name === `Model_${targetId}`);
        }
      });
    }
  }, []);

  // Helper: Load a model on-demand and scale it to exact real-world proportional dimensions
  const loadOrShowModel = useCallback((index: number) => {
    const item = AERO_LINEUP[index];
    const scene = sceneRef.current;
    const gltfLoader = gltfLoaderRef.current;
    if (!scene || !gltfLoader) return;

    // Immediately hide ALL existing models so previous engine never lingers
    enforceModelVisibility(item.id);

    // Check if already in memory cache (0ms instant swap)
    if (modelCache.current.has(item.id)) {
      const cached = modelCache.current.get(item.id)!;
      cached.visible = true;
      activeModelGroup.current = cached;
      enforceModelVisibility(item.id);

      // Re-calculate stats from cached model
      let mCount = 0;
      let tCount = 0;
      cached.traverse((child: THREE.Object3D) => {
        if ((child as THREE.Mesh).isMesh) {
          const m = child as THREE.Mesh;
          mCount++;
          if (m.geometry) {
            tCount += m.geometry.index
              ? m.geometry.index.count / 3
              : (m.geometry.attributes.position ? m.geometry.attributes.position.count / 3 : 0);
          }
        }
      });
      setModelStats({ meshes: mCount, triangles: Math.round(tCount) });
      setModelLoading(false);
      setLoadProgress(0);
      setLoadBytes(null);
      return;
    }

    // Load on-demand from /models/...
    setModelLoading(true);
    setLoadProgress(6);
    setLoadBytes(null);

    const techWireMat = new THREE.MeshBasicMaterial({
      color: 0xd67658,
      wireframe: true,
      transparent: true,
      opacity: 0.6,
    });

    gltfLoader.load(
      item.modelPath,
      (gltf) => {
        const model = gltf.scene;
        const group = new THREE.Group();
        group.name = `Model_${item.id}`;

        // Compute raw bounding box & dimensions
        const rawBox = new THREE.Box3().setFromObject(model);
        const center = rawBox.getCenter(new THREE.Vector3());
        const size = rawBox.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);

        // Normalize scale matching docs_site:
        // Engines: exactly 1.7m visual span; Airframe: 2.3m wingspan
        const targetSpan = item.isDrone ? 2.3 : 1.7;
        const scale = targetSpan / (maxDim || 1);

        model.scale.setScalar(scale);
        model.position.sub(center.multiplyScalar(scale));
        model.position.y += 0.02;

        let meshCount = 0;
        let triCount = 0;

        // PBR Material enhancement & sanitization (matching docs_site ModelViewerModal standard)
        model.traverse((child: THREE.Object3D) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            meshCount++;
            mesh.castShadow = true;
            mesh.receiveShadow = true;

            if (mesh.geometry) {
              triCount += mesh.geometry.index
                ? mesh.geometry.index.count / 3
                : (mesh.geometry.attributes.position ? mesh.geometry.attributes.position.count / 3 : 0);
            }

            if (mesh.material) {
              const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
              originalMats.current.set(mesh.uuid, mesh.material);
              wireframeMats.current.set(mesh.uuid, techWireMat);

              materials.forEach((m) => {
                const mat = m as THREE.MeshStandardMaterial;

                // Keep the authored PBR values (same as Blender). Only neutralise baked
                // white emissive with no emissive texture, which blows out Austro/VRDE.
                if (mat.emissive && !mat.emissiveMap) {
                  if (mat.emissive.r > 0.35 && mat.emissive.g > 0.35 && mat.emissive.b > 0.35) {
                    mat.emissive.setHex(0x000000);
                  }
                }

                // Sharper textures at grazing angles
                const maxAniso = rendererRef.current?.capabilities.getMaxAnisotropy() ?? 1;
                [mat.map, mat.normalMap, mat.roughnessMap, mat.metalnessMap, mat.aoMap, mat.emissiveMap].forEach((t) => {
                  if (t) t.anisotropy = maxAniso;
                });

                mat.needsUpdate = true;
              });
            }
          }
        });

        setModelStats({ meshes: meshCount, triangles: Math.round(triCount) });
        group.add(model);
        scene.add(group);

        // Cache in memory
        modelCache.current.set(item.id, group);

        // Enforce strict single-model visibility matching current selection
        const activeItem = AERO_LINEUP[activeIndexRef.current];
        enforceModelVisibility(activeItem.id);
        if (activeItem.id === item.id) {
          activeModelGroup.current = group;
        }

        setLoadProgress(100);
        setTimeout(() => {
          setModelLoading(false);
          setLoadProgress(0);
          setLoadBytes(null);
        }, 150);
      },
      (event: ProgressEvent) => {
        const total = event.total > 0 ? event.total : (item.fileSizeBytes || 0);
        if (total > 0 && event.loaded > 0) {
          const pct = Math.min(99, Math.round((event.loaded / total) * 100));
          setLoadProgress((prev) => Math.max(prev, pct));
          setLoadBytes({ loaded: event.loaded, total });
        } else if (event.loaded > 0) {
          setLoadBytes({ loaded: event.loaded, total: 0 });
        }
      },
      (err) => {
        console.warn(`[HERO 3D] Failed to load ${item.modelPath}:`, err);
        setModelLoading(false);
        setLoadProgress(0);
        setLoadBytes(null);
      }
    );
  }, [enforceModelVisibility]);

  // Initialize Three.js Scene
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 520;

    const scene = new THREE.Scene();
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    camera.position.set(0, 0.36, 2.4);
    cameraRef.current = camera;

    // WebGL Renderer with ACES ToneMapping & soft shadows
    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    // Khronos PBR Neutral keeps authored base colors (ACES desaturates them)
    renderer.toneMapping = THREE.NeutralToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    rendererRef.current = renderer;

    // PMREM Environment for realistic metallic PBR reflections (identical to docs_site)
    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    pmremGenerator.compileEquirectangularShader();
    const roomEnv = new RoomEnvironment();
    scene.environment = pmremGenerator.fromScene(roomEnv, 0.04).texture;
    roomEnv.dispose();

    // Orbit Controls with damping
    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxDistance = 8.0;
    controls.minDistance = 0.3;
    controls.maxPolarAngle = Math.PI / 2 + 0.06;
    controls.target.set(0, 0, 0);
    controlsRef.current = controls;

    // Image-based lighting does the heavy lifting (like Blender's Material Preview);
    // a single key light adds shape and shadows. No ambient/hemisphere, which flatten PBR.
    const keyLight = new THREE.DirectionalLight(0xfffbf2, 1.4);
    keyLight.position.set(3, 4, 3);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(2048, 2048);
    keyLight.shadow.camera.left = -1.6;
    keyLight.shadow.camera.right = 1.6;
    keyLight.shadow.camera.top = 1.6;
    keyLight.shadow.camera.bottom = -1.6;
    keyLight.shadow.camera.near = 0.5;
    keyLight.shadow.camera.far = 12;
    keyLight.shadow.bias = -0.0004;
    keyLight.shadow.normalBias = 0.02;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0xe4edf5, 0.35);
    fillLight.position.set(-5, 3, -4);
    scene.add(fillLight);

    // Aerospace ground grid turntable
    const grid = new THREE.GridHelper(6, 24, 0x1e2d38, 0x8a9ba8);
    const shadowPlane = new THREE.Mesh(
      new THREE.PlaneGeometry(8, 8),
      new THREE.ShadowMaterial({ opacity: 0.12 })
    );
    shadowPlane.rotation.x = -Math.PI / 2;
    shadowPlane.position.y = -0.551;
    shadowPlane.receiveShadow = true;
    scene.add(shadowPlane);
    grid.position.y = -0.55;
    scene.add(grid);

    // Draco + GLTF Setup
    const dracoLoader = new DRACOLoader();
    dracoLoader.setDecoderPath('/draco/');
    dracoLoader.setDecoderConfig({ type: 'wasm' });

    const gltfLoader = new GLTFLoader();
    gltfLoader.setDRACOLoader(dracoLoader);
    gltfLoaderRef.current = gltfLoader;

    // Initial load: Rotax 912 on first visit
    loadOrShowModel(0);

    // Animation Render Loop
    let animationFrameId: number;
    let lastTime = performance.now();

    controls.autoRotateSpeed = 1.0;
    controls.enablePan = true;

    const animate = (currentTime: number) => {
      animationFrameId = requestAnimationFrame(animate);
      const delta = Math.min((currentTime - lastTime) / 1000, 0.1);
      lastTime = currentTime;

      // Only steer the camera during a model-switch / reset transition;
      // otherwise the user's zoom, pan and orbit are left alone.
      if (currentTime < transitionUntil.current) {
        controls.target.lerp(targetLookAt.current, Math.min(delta * 4.0, 1));
        camera.position.lerp(targetCamPos.current, Math.min(delta * 3.0, 1));
      }
      controls.autoRotate = isAutoOrbitRef.current;
      controls.update();

      // Continuous per-frame mutual exclusivity
      const currentActiveItem = AERO_LINEUP[activeIndexRef.current];
      if (currentActiveItem && scene) {
        scene.children.forEach((child) => {
          if (child.name && child.name.startsWith('Model_')) {
            const shouldBeVisible = (child.name === `Model_${currentActiveItem.id}`);
            if (child.visible !== shouldBeVisible) {
              child.visible = shouldBeVisible;
            }
          }
        });
      }

      renderer.render(scene, camera);
    };

    animationFrameId = requestAnimationFrame(animate);

    // Resize Observer
    const handleResize = () => {
      if (!containerRef.current) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    const resizeObserver = new ResizeObserver(handleResize);
    if (container) {
      resizeObserver.observe(container);
    }

    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      dracoLoader.dispose();
      pmremGenerator.dispose();
      renderer.dispose();
    };
  }, [loadOrShowModel]);

  // Handle active index changes
  useEffect(() => {
    loadOrShowModel(activeIndex);

    const item = AERO_LINEUP[activeIndex];
    targetLookAt.current.set(0, 0, 0);

    const dist = item.camDist;
    const angle = item.camAngle;
    const elev = item.camElevation;

    targetCamPos.current.set(
      Math.sin(angle) * dist,
      elev * dist + 0.05,
      Math.cos(angle) * dist
    );
    transitionUntil.current = performance.now() + 1200;

    if (onSelectAsset) {
      onSelectAsset(activeIndex);
    }
  }, [activeIndex, loadOrShowModel, onSelectAsset]);

  // Visibility resync when toggling 3D/Image mode
  useEffect(() => {
    if (viewMode === '3d') {
      const activeItem = AERO_LINEUP[activeIndexRef.current];
      enforceModelVisibility(activeItem.id);
      const cached = modelCache.current.get(activeItem.id);
      if (cached) {
        cached.visible = true;
        activeModelGroup.current = cached;
      }
    }
  }, [viewMode, enforceModelVisibility]);

  // Wireframe toggle
  const toggleWireframe = () => {
    const next = !isWireframe;
    setIsWireframe(next);

    modelCache.current.forEach((grp) => {
      grp.traverse((child: THREE.Object3D) => {
        if ((child as THREE.Mesh).isMesh) {
          const mesh = child as THREE.Mesh;
          if (next) {
            const wire = wireframeMats.current.get(mesh.uuid);
            if (wire) mesh.material = wire;
          } else {
            const orig = originalMats.current.get(mesh.uuid);
            if (orig) mesh.material = orig;
          }
        }
      });
    });
  };

  const resetCamera = () => {
    const item = AERO_LINEUP[activeIndex];
    targetLookAt.current.set(0, 0, 0);
    targetCamPos.current.set(
      Math.sin(item.camAngle) * item.camDist,
      item.camElevation * item.camDist + 0.05,
      Math.cos(item.camAngle) * item.camDist
    );
    transitionUntil.current = performance.now() + 1200;
    setIsAutoOrbit(true);
  };

  return (
    <HudFrame
      topLabel="PROJECT ANUMAAN // DRDO PS-26054"
      bottomLabel="K.1321 // Y.0704 // 20Hz TELEMETRY"
    >
      <div ref={containerRef} className="tactical-console-viewport">
        {/* Full-bleed 3D Three.js WebGL Canvas */}
        <canvas
          ref={canvasRef}
          className={`tactical-canvas ${viewMode === '3d' ? 'is-visible' : 'is-hidden'}`}
        />

        {/* Studio Render View (When Image mode is selected) */}
        {viewMode === 'image' && (
          <div className="tactical-render-view">
            <img src={activeAsset.imagePath} alt={activeAsset.name} />
          </div>
        )}

        {/* Top Safe-Zone: Flush HUD Engine Selector Chips (anchored cleanly beneath top notch) */}
        <div className="tactical-tabs-bar" role="tablist" aria-label="Select aero engine">
          {AERO_LINEUP.map((item, idx) => {
            const isActive = activeIndex === idx;
            const powerVal = item.specs[0]?.value?.split(' ')[0] || '';
            const powerUnit = item.specs[0]?.value?.split(' ')[1] || '';
            return (
              <button
                key={item.id}
                role="tab"
                aria-selected={isActive}
                className={`tactical-tab-chip ${isActive ? 'is-active' : ''}`}
                onClick={() => {
                  setActiveIndex(idx);
                  setIsAutoOrbit(true);
                }}
              >
                <div className="tactical-tab-top">
                  <span className="tactical-tab-indicator" />
                  <span className="tactical-tab-code">{item.code}</span>
                </div>
                <div className="tactical-tab-sub">
                  <span>{powerVal} {powerUnit}</span>
                  <span className="tactical-tab-key">{item.keyBadge}</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Unified Tactical Control Bar (Dark Matte Micro-Chamfered HUD Buttons) */}
        <div className="tactical-control-bar" role="toolbar" aria-label="Viewer controls">
          <button
            type="button"
            className={`tactical-hud-btn ${viewMode === '3d' ? 'is-active' : ''}`}
            onClick={() => setViewMode('3d')}
            title="Interactive 3D View"
          >
            <Box size={13} />
            <span>3D</span>
          </button>
          <button
            type="button"
            className={`tactical-hud-btn ${viewMode === 'image' ? 'is-active' : ''}`}
            onClick={() => setViewMode('image')}
            title="Photorealistic Studio Render"
          >
            <ImageIcon size={13} />
            <span>IMAGE</span>
          </button>

          {viewMode === '3d' && (
            <>
              <button
                type="button"
                className={`tactical-hud-btn ${isAutoOrbit ? 'is-active' : ''}`}
                onClick={() => setIsAutoOrbit(!isAutoOrbit)}
                title="Toggle Auto Rotation"
              >
                <RotateCcw size={13} />
                <span>{isAutoOrbit ? 'ROTATE' : 'STILL'}</span>
              </button>
              <button
                type="button"
                className={`tactical-hud-btn ${isWireframe ? 'is-active' : ''}`}
                onClick={toggleWireframe}
                title="Toggle Wireframe Inspection"
              >
                <Eye size={13} />
                <span>{isWireframe ? 'SOLID' : 'WIRE'}</span>
              </button>
              <button
                type="button"
                className="tactical-hud-btn"
                onClick={resetCamera}
                title="Reset Perspective Orientation"
              >
                <Compass size={13} />
                <span>RESET</span>
              </button>
            </>
          )}
        </div>

        {/* Embedded Telemetry & Specs Footer (Translucent HUD Readout above bottom coordinate notch) */}
        <div className="tactical-telemetry-footer">
          <div className="tactical-telemetry-left">
            <div className="tactical-telemetry-badge">
              <span className="tactical-pulse-dot" />
              <span className="tactical-cat-tag">{activeAsset.name}</span>
            </div>
            <div className="tactical-telemetry-specs">
              <strong className="tactical-spec-primary">{activeAsset.specs[0]?.value}</strong>
              <span className="tactical-spec-sep">//</span>
              <span className="tactical-spec-sub">{activeAsset.specs[2]?.value || activeAsset.specs[1]?.value}</span>
            </div>
          </div>

          <div className="tactical-telemetry-right">
            {modelStats.triangles > 0 ? (
              <div className="tactical-mesh-stats">
                <span className="tactical-stat-chunk">{modelStats.meshes} MESHES</span>
                <span className="tactical-spec-sep">·</span>
                <span className="tactical-stat-chunk">{modelStats.triangles.toLocaleString()} TRIS</span>
                <span className="tactical-orbit-hint">· DRAG TO INSPECT</span>
              </div>
            ) : (
              <span className="tactical-orbit-hint">DRAG TO INSPECT</span>
            )}
          </div>
        </div>

        {/* Tactical Loading Radar (Translucent over Canvas) */}
        {modelLoading && (
          <div className="tactical-loading-radar" role="status" aria-live="polite">
            <div className="tactical-radar-box">
              <div className="tactical-radar-ring">
                <img
                  src="/images/anumaan-mark-editorial.png"
                  alt="ANUMAAN Logo"
                  className="tactical-radar-logo"
                />
              </div>
              <div className="tactical-radar-meta">
                <span className="tactical-radar-kicker">ANUMAAN // DIGITAL TWIN CALIBRATION</span>
                <strong className="tactical-radar-title">{activeAsset.name}</strong>
              </div>
              <div className="tactical-radar-bar">
                <div className="tactical-radar-fill" style={{ width: `${Math.max(6, loadProgress)}%` }} />
              </div>
              <div className="tactical-radar-digits">
                <span>{loadProgress}%</span>
                <span>
                  {loadBytes && loadBytes.total > 0
                    ? `${(loadBytes.loaded / (1024 * 1024)).toFixed(1)} / ${(loadBytes.total / (1024 * 1024)).toFixed(1)} MB`
                    : loadProgress >= 99
                    ? 'COMPILING PBR SHADERS'
                    : 'DRACO DECOMPRESSION'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </HudFrame>
  );
};

export default LandingHero3D;
