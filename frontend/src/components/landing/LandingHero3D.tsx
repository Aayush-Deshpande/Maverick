import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { Eye, RotateCcw, Image as ImageIcon, Box, Compass } from 'lucide-react';

export interface LineupItem {
  id: string;
  keyBadge: string;
  name: string;
  code: string;
  subtitle: string;
  category: string;
  specs: { label: string; value: string }[];
  modelPath: string;
  imagePath: string;
  camDist: number;
  camElevation: number;
  camAngle: number;
  isDrone?: boolean;
}

export const AERO_LINEUP: LineupItem[] = [
  {
    id: 'rotax_912is',
    keyBadge: 'F1',
    name: 'Rotax 912 iS Sport',
    code: 'ROTAX 912 iS',
    subtitle: '100 HP Naturally Aspirated Aero-EFI · Dual FADEC (Primary Ref)',
    category: 'MALE UAV PRIMARY PROPULSION',
    specs: [
      { label: 'RATED POWER', value: '100 HP @ 5800 RPM' },
      { label: 'DISPLACEMENT', value: '1,352 cc (4-Cyl Flat)' },
      { label: 'MANAGEMENT', value: 'Redundant Dual FADEC' },
      { label: 'FUEL INJECTION', value: 'Multi-Point Port EFI' },
    ],
    modelPath: '/models/rotax_912is.glb',
    imagePath: '/images/lineup/render_912is_beauty.png',
    camDist: 2.4,
    camElevation: 0.36,
    camAngle: -1.2,
  },
  {
    id: 'rotax_914',
    keyBadge: 'F2',
    name: 'Rotax 914 F Turbo',
    code: 'ROTAX 914 F',
    subtitle: '115 HP Turbocharged Powerplant · Automatic Wastegate TCU',
    category: 'HIGH-ALTITUDE CRUISE EXTENSION',
    specs: [
      { label: 'TAKE-OFF POWER', value: '115 HP (5 min limit)' },
      { label: 'TURBOCHARGING', value: 'Exhaust Wastegate TCU' },
      { label: 'CRITICAL ALTITUDE', value: '16,000 ft ceiling' },
      { label: 'DRY WEIGHT', value: '78.5 kg with turbo' },
    ],
    modelPath: '/models/rotax_914.glb',
    imagePath: '/images/lineup/render_914_solid.png',
    camDist: 2.4,
    camElevation: 0.36,
    camAngle: -1.2,
  },
  {
    id: 'rotax_915is',
    keyBadge: 'F3',
    name: 'Rotax 915 iS Turbo',
    code: 'ROTAX 915 iS',
    subtitle: '141 HP Turbocharged & Intercooled · Full Altitude FADEC',
    category: 'ADVANCED PAYLOAD MALE ENVELOPE',
    specs: [
      { label: 'CONTINUOUS POWER', value: '135 HP to FL150' },
      { label: 'ASPIRATION', value: 'Turbo + Charge-Air Cooler' },
      { label: 'TIME BETWEEN OVERHAUL', value: '1,200 hrs TBO' },
      { label: 'TATTVA RESIDUALS', value: '27-channel telemetry' },
    ],
    modelPath: '/models/rotax_915is.glb',
    imagePath: '/images/lineup/render_915is_framing.png',
    camDist: 2.4,
    camElevation: 0.36,
    camAngle: -1.2,
  },
  {
    id: 'austro_ae300',
    keyBadge: 'F4',
    name: 'Austro Engine AE300',
    code: 'AUSTRO AE300',
    subtitle: '2.0L Turbo Diesel · 168 HP · Common-Rail Heavy Fuel Injection',
    category: 'COMMON-RAIL DIESEL UAV PROPULSION',
    specs: [
      { label: 'MAX POWER', value: '168 HP @ 3880 RPM' },
      { label: 'FUEL COMPATIBILITY', value: 'Jet-A1 / Diesel Fuel' },
      { label: 'INJECTION SYSTEM', value: '1800-bar Common Rail' },
      { label: 'EFFICIENCY', value: '214 g/kWh Low BSFC' },
    ],
    modelPath: '/models/austro_ae300.glb',
    imagePath: '/images/lineup/render_austro_ae300.png',
    camDist: 2.4,
    camElevation: 0.36,
    camAngle: -1.2,
  },
  {
    id: 'vrde_jayem',
    keyBadge: 'F5',
    name: 'VRDE Jayem 2.2L',
    code: 'VRDE 2.2L',
    subtitle: '2.2L CI Turbocharged · 180 HP · DRDO Indigenized Heavy Fuel',
    category: 'DRDO INDIGENOUS AERO-ENGINE (VRDE)',
    specs: [
      { label: 'MAX POWER', value: '180 HP @ 4000 RPM' },
      { label: 'ASPIRATION', value: 'VGT Turbo + Intercooler' },
      { label: 'INDIGENOUS CONTENT', value: '100% Indian Manufacture' },
      { label: 'DEFENCE APPLICATION', value: 'Tactical Long-Range UAV' },
    ],
    modelPath: '/models/vrde_jayem_2_2l.glb',
    imagePath: '/images/lineup/render_vrde_jayem.png',
    camDist: 2.4,
    camElevation: 0.36,
    camAngle: -1.2,
  },
  {
    id: 'uav_predator',
    keyBadge: 'F6',
    name: 'Predator-Class MALE UAV',
    code: 'MALE AIRFRAME',
    subtitle: 'Medium-Altitude Long-Endurance · Pusher Propulsion Configuration',
    category: 'TACTICAL MALE STRATEGIC DRONE (32H+ LOITER)',
    specs: [
      { label: 'PROPULSION', value: 'Rotax 914 / 915 iS Pusher' },
      { label: 'ENDURANCE', value: '32+ Hours SATCOM Loiter' },
      { label: 'SERVICE CEILING', value: '30,000 ft MSL' },
      { label: 'PAYLOAD / MTOW', value: '350 kg / 1,450 kg MTOW' },
    ],
    modelPath: '/models/uav_predator.glb',
    imagePath: '/images/lineup/sc_bayraktar_tb3.png',
    camDist: 3.2,
    camElevation: 0.38,
    camAngle: -1.2,
    isDrone: true,
  },
];

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
      return;
    }

    // Load on-demand from /models/...
    setModelLoading(true);

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

        setModelLoading(false);
      },
      undefined,
      (err) => {
        console.warn(`[HERO 3D] Failed to load ${item.modelPath}:`, err);
        setModelLoading(false);
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
    const grid = new THREE.GridHelper(6, 24, 0x223340, 0x142028);
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
    <div className="an-engine-showcase">
      <div className="an-engine-select" aria-label="Select an engine or airframe">
        {AERO_LINEUP.map((item, idx) => (
          <button
            key={item.id}
            aria-pressed={activeIndex === idx}
            onClick={() => {
              setActiveIndex(idx);
              setIsAutoOrbit(true);
            }}
          >
            <span>{item.code}</span>
            <small>{item.specs[0].value.split(' ')[0]} {item.specs[0].value.split(' ')[1] || ''}</small>
          </button>
        ))}
      </div>
      <figure className="an-engine-stage">
        <div ref={containerRef} className="an-engine-canvas">
          <canvas ref={canvasRef} className={viewMode === '3d' ? 'an-canvas' : 'an-canvas an-canvas-hidden'} />
          {viewMode === 'image' && (
            <div className="an-render-view">
              <img src={activeAsset.imagePath} alt={activeAsset.name} />
            </div>
          )}
          <div className="an-engine-toolbar">
            <button
              aria-pressed={viewMode === '3d'}
              onClick={() => setViewMode('3d')}
              title="Interactive 3D view"
            >
              <Box size={14} /> 3D
            </button>
            <button
              aria-pressed={viewMode === 'image'}
              onClick={() => setViewMode('image')}
              title="Studio render"
            >
              <ImageIcon size={14} /> Image
            </button>
            {viewMode === '3d' && (
              <>
                <button
                  aria-pressed={isAutoOrbit}
                  onClick={() => setIsAutoOrbit(!isAutoOrbit)}
                  title="Toggle slow rotation"
                >
                  <RotateCcw size={14} /> {isAutoOrbit ? 'Rotate' : 'Still'}
                </button>
                <button
                  aria-pressed={isWireframe}
                  onClick={toggleWireframe}
                  title="Toggle wireframe inspection"
                >
                  <Eye size={14} /> {isWireframe ? 'Solid' : 'Wire'}
                </button>
                <button
                  onClick={resetCamera}
                  title="Reset perspective orientation"
                >
                  <Compass size={14} /> Reset
                </button>
              </>
            )}
          </div>

          {modelLoading && <div className="an-model-loading">Loading aerospace digital twin…</div>}

          <figcaption className="an-model-caption">
            <strong>{activeAsset.name}</strong>
            <span>{activeAsset.subtitle}</span>
          </figcaption>

          {modelStats.triangles > 0 && (
            <div className="an-orbit-hint" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span>{modelStats.meshes} MESHES · {modelStats.triangles.toLocaleString()} TRIS</span>
              <span>· DRAG TO INSPECT</span>
            </div>
          )}
        </div>
      </figure>
      <div className="an-selected-specs">
        <span>{activeAsset.category}</span>
        <strong>{activeAsset.specs[0].value}</strong>
        <small>{activeAsset.specs[1]?.value} · {activeAsset.specs[2]?.value}</small>
      </div>
    </div>
  );
};

export default LandingHero3D;
