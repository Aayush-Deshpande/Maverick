import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { Eye, RotateCcw, Image as ImageIcon, Box } from 'lucide-react';

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
    subtitle: '100 HP Naturally Aspirated Aero-EFI · Dual FADEC (Lane A/B)',
    category: 'MALE UAV PRIMARY PROPULSION',
    specs: [
      { label: 'RATED POWER', value: '100 HP @ 5800 RPM' },
      { label: 'DISPLACEMENT', value: '1,352 cc (4-Cyl Flat)' },
      { label: 'MANAGEMENT', value: 'Redundant Dual FADEC' },
      { label: 'FUEL INJECTION', value: 'Multi-Point Port EFI' },
    ],
    modelPath: '/models/rotax_912is.glb',
    imagePath: '/images/lineup/render_912is_beauty.png',
    camDist: 2.2,
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
    camDist: 2.2,
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
    camDist: 2.2,
    camElevation: 0.36,
    camAngle: -1.2,
  },
  {
    id: 'bayraktar_tb3',
    keyBadge: 'F4',
    name: 'Bayraktar TB3 MALE UAV',
    code: 'BAYRAKTAR TB3',
    subtitle: 'Carrier-Capable MALE UAV · Foldable Wings · Rotax 915 iS / PD170',
    category: 'TACTICAL MALE STRATEGIC DRONE (32H+ LOITER)',
    specs: [
      { label: 'POWERPLANT', value: 'Rotax 915 iS / PD170 (141 HP)' },
      { label: 'FLIGHT ENDURANCE', value: '32+ Hours SATCOM Loiter' },
      { label: 'SERVICE CEILING', value: '30,000 ft MSL' },
      { label: 'MAX PAYLOAD / MTOW', value: '280 kg / 1,450 kg MTOW' },
    ],
    modelPath: '/models/bayraktar_tb3.glb',
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
  isAutoOrbitRef.current = isAutoOrbit; // Keep ref in sync so animate closure reads live value

  // Three.js instances
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const gltfLoaderRef = useRef<GLTFLoader | null>(null);

  // In-memory model cache for 0ms instant swapping
  const modelCache = useRef<Map<string, THREE.Group>>(new Map());
  const activeModelGroup = useRef<THREE.Group | null>(null);

  const originalMats = useRef<Map<string, THREE.Material>>(new Map());
  const wireframeMats = useRef<Map<string, THREE.Material>>(new Map());

  const targetLookAt = useRef(new THREE.Vector3(0, 0, 0));
  const targetCamPos = useRef(new THREE.Vector3(0, 0.36, 2.2));

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
      setModelLoading(false);
      return;
    }

    // Load on-demand from /models/...
    setModelLoading(true);

    const techWireMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      wireframe: true,
      transparent: true,
      opacity: 0.5,
    });

    gltfLoader.load(
      item.modelPath,
      (gltf) => {
        const model = gltf.scene;
        const group = new THREE.Group();
        group.name = `Model_${item.id}`;

        // Compute raw bounding box
        const rawBox = new THREE.Box3().setFromObject(model);
        const rawSize = new THREE.Vector3();
        rawBox.getSize(rawSize);
        const maxDim = Math.max(rawSize.x, rawSize.y, rawSize.z);

        // Normalize scale:
        // Engines: exactly 1.05m diameter (Rotax 912, 914, 915 will have identical proportional scale!)
        // Drone: 2.2m wingspan
        const targetSpan = item.isDrone ? 2.2 : 1.05;
        const s = targetSpan / (maxDim || 1);
        model.scale.set(s, s, s);

        // Precise mathematical centering at origin (0, 0, 0)
        const scaledBox = new THREE.Box3().setFromObject(model);
        const center = new THREE.Vector3();
        scaledBox.getCenter(center);
        model.position.sub(center);

        // Material enhancement — tuned per asset type
        model.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            mesh.castShadow = true;
            mesh.receiveShadow = true;

            const hasVertexColors = !!(mesh.geometry?.attributes?.color);

            if (hasVertexColors) {
              // Vertex-colored mesh (common in Blender exports) — keep colors, calibrate PBR params
              mesh.material = new THREE.MeshStandardMaterial({
                vertexColors: true,
                roughness: item.isDrone ? 0.72 : 0.38,   // Drone: more matte; engines: shinier
                metalness: item.isDrone ? 0.18 : 0.30,   // Drone: composite body; engines: aluminum
              });
            } else if (!mesh.material) {
              // No material at all — apply a sensible default
              mesh.material = new THREE.MeshStandardMaterial({
                color: item.isDrone ? 0x4a5568 : 0x8a9ab0,  // Drone: dark grey-green; engines: aluminium
                roughness: item.isDrone ? 0.75 : 0.40,
                metalness: item.isDrone ? 0.15 : 0.40,
              });
            } else if ((mesh.material as THREE.MeshStandardMaterial).isMeshStandardMaterial) {
              const m = mesh.material as THREE.MeshStandardMaterial;
              if (item.isDrone) {
                // Bayraktar: fuselage panels should be dark composite, NOT white metallic
                // Clamp metalness down and push roughness up for matte drone body
                m.roughness = Math.max(m.roughness ?? 0.72, 0.65);
                m.metalness = Math.min(m.metalness ?? 0.18, 0.22);
                // If the base color is very bright (near white), darken it to a realistic drone grey
                if (m.color && m.color.r > 0.8 && m.color.g > 0.8 && m.color.b > 0.8) {
                  m.color.set(0x4a5568);
                }
              } else {
                // Engines: ensure they are bright enough to not look dark
                m.roughness = Math.min(m.roughness ?? 0.40, 0.55);
                m.metalness = Math.max(m.metalness ?? 0.40, 0.35);
                // Ensure emissive is not killing the material brightness
                if (m.emissive) m.emissive.set(0x000000);
              }
              m.needsUpdate = true;
            }

            originalMats.current.set(mesh.uuid, mesh.material as THREE.Material);
            wireframeMats.current.set(mesh.uuid, techWireMat);
          }
        });

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

    // Authentic dark aerospace studio background (inspired by web/site/css/viewport-director.css)
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x0d151c);

    // Camera
    const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 100);
    camera.position.set(0, 0.36, 2.2);
    cameraRef.current = camera;

    // WebGL Renderer
    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      powerPreference: 'high-performance',
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.35;  // Slightly brighter base exposure for engine visibility
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    rendererRef.current = renderer;

    // Orbit Controls
    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxDistance = 8.0;
    controls.minDistance = 0.8;
    controls.maxPolarAngle = Math.PI / 2 + 0.05;
    controls.target.set(0, 0, 0);
    controlsRef.current = controls;

    // Studio Lighting — calibrated for engine AND drone models
    // Engines need higher ambient to reveal aluminum detail without overexposing
    // Drones need controlled exposure so composite panels don't wash out to white
    const amb = new THREE.AmbientLight(0xffffff, 1.05);  // Raised from 0.85 for engine visibility
    scene.add(amb);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.6);
    keyLight.position.set(5, 7, 5);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 1024;
    keyLight.shadow.mapSize.height = 1024;
    scene.add(keyLight);

    // Warm front-fill to reduce harsh shadows on engine bodies
    const fillLight = new THREE.DirectionalLight(0xe8f4fd, 0.55);
    fillLight.position.set(-4, 2, 4);
    scene.add(fillLight);

    // Cool cyan accent from rear-left (tech aesthetic)
    const accentLight = new THREE.DirectionalLight(0x00c8e8, 0.35);
    accentLight.position.set(-6, 3, -3);
    scene.add(accentLight);

    // Subtle bottom fill (prevents pure black undersides)
    const rimLight = new THREE.DirectionalLight(0xffffff, 0.40);
    rimLight.position.set(0, -3, -4);
    scene.add(rimLight);

    // A quiet studio keeps attention on the physical engine model.

    // Draco + GLTF Setup (Local hosted Draco wasm decoders for zero-latency offline hosting)
    const dracoLoader = new DRACOLoader();
    dracoLoader.setDecoderPath('/draco/');
    dracoLoader.setDecoderConfig({ type: 'wasm' });

    const gltfLoader = new GLTFLoader();
    gltfLoader.setDRACOLoader(dracoLoader);
    gltfLoaderRef.current = gltfLoader;

    // Initial load: Only load the active 01 Rotax 912 on first visit
    loadOrShowModel(0);

    // Animation Render Loop
    let animationFrameId: number;
    let lastTime = performance.now();
    let currentOrbitAngle = -1.2;

    const animate = (currentTime: number) => {
      animationFrameId = requestAnimationFrame(animate);
      const delta = (currentTime - lastTime) / 1000;
      lastTime = currentTime;

      if (controls && camera) {
        controls.target.lerp(targetLookAt.current, Math.min(delta * 4.0, 1));

        if (isAutoOrbitRef.current) {
          currentOrbitAngle += delta * 0.15;
          const currentIdx = activeIndexRef.current;
          const targetItem = AERO_LINEUP[currentIdx];
          const dist = targetItem.camDist;
          const elev = targetItem.camElevation;

          targetCamPos.current.set(
            Math.sin(currentOrbitAngle) * dist,
            elev * dist + 0.05,
            Math.cos(currentOrbitAngle) * dist
          );
        }

        camera.position.lerp(targetCamPos.current, Math.min(delta * 3.0, 1));
        controls.update();
      }

      // Continuous per-frame mutual exclusivity: strictly ensure only the active selection is visible
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

    // Per-asset tone mapping: drone needs lower exposure to avoid white washout,
    // engines need higher exposure to show aluminum detail
    if (rendererRef.current) {
      rendererRef.current.toneMappingExposure = item.isDrone ? 0.90 : 1.35;
    }

    if (onSelectAsset) {
      onSelectAsset(activeIndex);
    }
  }, [activeIndex, loadOrShowModel, onSelectAsset]);

  // Fix: When switching back from RENDER SC → 3D CAD, explicitly re-enforce model visibility.
  // The animate loop does this every frame but there can be a 1-frame gap on mode switch
  // that leaves the scene in an unexpected state on low-end devices.
  useEffect(() => {
    if (viewMode === '3d') {
      const activeItem = AERO_LINEUP[activeIndexRef.current];
      enforceModelVisibility(activeItem.id);
      // Also ensure the active model group ref is correct
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
      grp.traverse((child) => {
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

  const engineLineup = AERO_LINEUP.slice(0, 3);
  const uavDrone = AERO_LINEUP[3];

  return (
    <div className="an-engine-showcase">
      <div className="an-engine-select" aria-label="Select an engine or airframe">
        {[...engineLineup, uavDrone].map((item, idx) => (
          <button key={item.id} aria-pressed={activeIndex === idx} onClick={() => { setActiveIndex(idx); setIsAutoOrbit(true); }}>
            <span>{item.code}</span><small>{item.specs[0].value}</small>
          </button>
        ))}
      </div>
      <figure className="an-engine-stage">
        <div ref={containerRef} className="an-engine-canvas">
          <canvas ref={canvasRef} className={viewMode === '3d' ? 'an-canvas' : 'an-canvas an-canvas-hidden'} />
          {viewMode === 'image' && <div className="an-render-view"><img src={activeAsset.imagePath} alt={activeAsset.name} /></div>}
          <div className="an-engine-toolbar">
            <button aria-pressed={viewMode === '3d'} onClick={() => setViewMode('3d')} title="Interactive 3D view"><Box size={14} /> 3D</button>
            <button aria-pressed={viewMode === 'image'} onClick={() => setViewMode('image')} title="Studio render"><ImageIcon size={14} /> Image</button>
            {viewMode === '3d' && <button aria-pressed={isAutoOrbit} onClick={() => setIsAutoOrbit(!isAutoOrbit)} title="Toggle slow rotation"><RotateCcw size={14} /> {isAutoOrbit ? 'Rotate' : 'Still'}</button>}
            {viewMode === '3d' && <button aria-pressed={isWireframe} onClick={toggleWireframe} title="Toggle wireframe"><Eye size={14} /> {isWireframe ? 'Solid' : 'Wire'}</button>}
          </div>
          {modelLoading && <div className="an-model-loading">Loading engine model…</div>}
          <figcaption className="an-model-caption"><strong>{activeAsset.name}</strong><span>{activeAsset.subtitle}</span></figcaption>
          <span className="an-orbit-hint">Drag to inspect · Scroll to zoom</span>
        </div>
      </figure>
      <div className="an-selected-specs"><span>{activeAsset.category}</span><strong>{activeAsset.specs[0].value}</strong><small>{activeAsset.specs[1]?.value}</small></div>
    </div>
  );
};

export default LandingHero3D;
