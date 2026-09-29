import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { X, RotateCw, Box, Maximize2, Minimize2, Sun, Moon } from 'lucide-react';

interface ModelViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialModel?: string;
}

const AVAILABLE_MODELS = [
  { id: 'rotax_912is', name: 'Rotax 912 iS Sport', path: '/assets/models/rotax_912is.glb', spec: '1.35L Flat-4 Boxer · 100 hp · Dual FADEC Injection (Primary Ref)' },
  { id: 'rotax_914', name: 'Rotax 914 F Turbo', path: '/assets/models/rotax_914.glb', spec: '1.21L Turbocharged · 115 hp · Auto Wastegate TCU' },
  { id: 'rotax_915is', name: 'Rotax 915 iS Turbo', path: '/assets/models/rotax_915is.glb', spec: '1.35L Turbo Intercooled · 141 hp · High-Altitude Sprint' },
  { id: 'austro_ae300', name: 'Austro Engine AE300', path: '/assets/models/austro_ae300.glb', spec: '2.0L Turbo Diesel · 168 hp · Common-Rail Heavy Fuel' },
  { id: 'vrde_jayem', name: 'VRDE Jayem 2.2L', path: '/assets/models/vrde_jayem_2_2l.glb', spec: '2.2L CI Turbocharged · 180 hp · DRDO Indigenized' },
  { id: 'uav_predator', name: 'Predator-Class MALE Airframe', path: '/assets/models/uav_predator.glb', spec: 'Medium-Altitude Long-Endurance · Pusher Propulsion' },
];

export const ModelViewerModal: React.FC<ModelViewerModalProps> = ({ isOpen, onClose, initialModel = 'rotax_912is' }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [selectedModel, setSelectedModel] = useState<string>(initialModel);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [wireframe, setWireframe] = useState<boolean>(false);
  const [autoRotate, setAutoRotate] = useState<boolean>(true);
  const [darkStudio, setDarkStudio] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [modelStats, setModelStats] = useState<{ meshes: number; triangles: number }>({ meshes: 0, triangles: 0 });

  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const currentObjectRef = useRef<THREE.Group | null>(null);
  const gridRef = useRef<THREE.GridHelper | null>(null);

  useEffect(() => {
    setSelectedModel(initialModel);
  }, [initialModel]);

  // Main Three.js Scene Setup
  useEffect(() => {
    if (!isOpen || !mountRef.current) return;

    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight;

    const scene = new THREE.Scene();
    const bgColor = darkStudio ? 0x141415 : 0xfcfbf9;
    scene.background = new THREE.Color(bgColor);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(2.4, 1.6, 3.0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    // Khronos PBR Neutral keeps authored base colors (ACES desaturates them)
    renderer.toneMapping = THREE.NeutralToneMapping;
    renderer.toneMappingExposure = 1.0;
    mountRef.current.innerHTML = '';
    mountRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // PMREM Environment for realistic metallic PBR reflections
    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    pmremGenerator.compileEquirectangularShader();
    const roomEnv = new RoomEnvironment();
    scene.environment = pmremGenerator.fromScene(roomEnv, 0.04).texture;
    roomEnv.dispose();

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.autoRotate = autoRotate;
    controls.autoRotateSpeed = 0.8;
    controlsRef.current = controls;

    // Image-based lighting does the heavy lifting (like Blender's Material Preview);
    // a single key light adds shape and shadows. No ambient/hemisphere, which flatten PBR.
    scene.environmentIntensity = darkStudio ? 0.8 : 1.0;

    const keyLight = new THREE.DirectionalLight(0xfffbf5, darkStudio ? 1.4 : 1.2);
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

    const fillLight = new THREE.DirectionalLight(0xf0f4f8, 0.35);
    fillLight.position.set(-5, 3, -4);
    scene.add(fillLight);

    // Ground Grid
    const grid1 = darkStudio ? 0x3f3f46 : 0xd4d4d8;
    const grid2 = darkStudio ? 0x27272a : 0xe4e4e7;
    const grid = new THREE.GridHelper(6, 24, grid1, grid2);
    grid.position.y = -0.6;
    scene.add(grid);
    gridRef.current = grid;

    // Render loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.autoRotate = autoRotate;
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!mountRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
      pmremGenerator.dispose();
      renderer.dispose();
    };
  }, [isOpen, darkStudio]);

  // Load and sanitize GLB model
  useEffect(() => {
    if (!isOpen || !sceneRef.current) return;

    setIsLoading(true);
    const scene = sceneRef.current;

    if (currentObjectRef.current) {
      scene.remove(currentObjectRef.current);
      currentObjectRef.current = null;
    }

    const modelConfig = AVAILABLE_MODELS.find((m) => m.id === selectedModel) || AVAILABLE_MODELS[0];
    const loader = new GLTFLoader();
    const dracoLoader = new DRACOLoader();
    dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.7/');
    loader.setDRACOLoader(dracoLoader);

    loader.load(
      modelConfig.path,
      (gltf) => {
        const object = gltf.scene;
        currentObjectRef.current = object;

        // Auto-center and Scale
        const box = new THREE.Box3().setFromObject(object);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = 1.8 / (maxDim || 1);

        object.scale.setScalar(scale);
        object.position.sub(center.multiplyScalar(scale));
        object.position.y += 0.05;

        let meshCount = 0;
        let triCount = 0;

        object.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            meshCount++;
            mesh.castShadow = true;
            mesh.receiveShadow = true;

            if (mesh.geometry) {
              triCount += mesh.geometry.index
                ? mesh.geometry.index.count / 3
                : mesh.geometry.attributes.position.count / 3;
            }

            if (mesh.material) {
              const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
              materials.forEach((m) => {
                const mat = m as THREE.MeshStandardMaterial;
                mat.wireframe = wireframe;

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
        scene.add(object);
        setIsLoading(false);
      },
      undefined,
      (err) => {
        console.error('Error loading GLB:', err);
        setIsLoading(false);
      }
    );
  }, [isOpen, selectedModel, wireframe]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/60 backdrop-blur-xs p-4 sm:p-6">
      <div
        className={`bg-white border border-stone-300 rounded-[2px] shadow-2xl flex flex-col overflow-hidden transition-all duration-200 ${
          isFullscreen ? 'w-full h-full' : 'w-full max-w-5xl h-[85vh]'
        }`}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-stone-200 bg-stone-50 text-stone-900">
          <div className="flex items-center gap-3">
            <span className="flex h-2 w-2 rounded-full bg-blue-600 animate-pulse" />
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-mono text-xs font-semibold text-stone-900 uppercase tracking-wider">
                  3D Digital Twin Inspection View
                </h3>
                <span className="text-stone-300">|</span>
                <span className="text-xs text-stone-500 font-mono">Draco GLB Asset</span>
              </div>
              <p className="text-xs text-stone-500 mt-0.5">
                {AVAILABLE_MODELS.find((m) => m.id === selectedModel)?.spec}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1.5 text-stone-500 hover:text-stone-900 hover:bg-stone-200/70 rounded transition-colors"
              title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-stone-500 hover:text-stone-900 hover:bg-stone-200/70 rounded transition-colors"
              title="Close modal"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Toolbar & Selector */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-2.5 border-b border-stone-200 bg-white text-xs">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="font-mono text-[11px] uppercase tracking-wider text-stone-400 mr-1">Platform:</span>
            {AVAILABLE_MODELS.map((model) => (
              <button
                key={model.id}
                onClick={() => setSelectedModel(model.id)}
                className={`px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider rounded border transition-colors ${
                  selectedModel === model.id
                    ? 'bg-stone-900 text-white border-stone-900 font-semibold shadow-xs'
                    : 'bg-stone-50 text-stone-600 border-stone-200 hover:bg-stone-100 hover:text-stone-900'
                }`}
              >
                {model.name}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setDarkStudio(!darkStudio)}
              className={`flex items-center gap-1.5 px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider rounded border transition-colors ${
                darkStudio
                  ? 'bg-stone-800 text-amber-300 border-stone-700'
                  : 'bg-stone-50 text-stone-700 border-stone-200 hover:bg-stone-100'
              }`}
              title="Toggle Studio Lighting & Backdrop"
            >
              {darkStudio ? <Moon size={13} /> : <Sun size={13} />}
              <span>{darkStudio ? 'Dark Studio' : 'Light Studio'}</span>
            </button>

            <button
              onClick={() => setWireframe(!wireframe)}
              className={`flex items-center gap-1.5 px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider rounded border transition-colors ${
                wireframe
                  ? 'bg-stone-900 text-white border-stone-900'
                  : 'bg-stone-50 text-stone-600 border-stone-200 hover:bg-stone-100'
              }`}
            >
              <Box size={13} />
              <span>{wireframe ? 'Solid' : 'Wireframe'}</span>
            </button>

            <button
              onClick={() => setAutoRotate(!autoRotate)}
              className={`flex items-center gap-1.5 px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider rounded border transition-colors ${
                autoRotate
                  ? 'bg-stone-900 text-white border-stone-900'
                  : 'bg-stone-50 text-stone-600 border-stone-200 hover:bg-stone-100'
              }`}
            >
              <RotateCw size={13} />
              <span>{autoRotate ? 'Pause' : 'Rotate'}</span>
            </button>
          </div>
        </div>

        {/* 3D Canvas Viewport */}
        <div className={`relative flex-1 ${darkStudio ? 'bg-[#141415]' : 'bg-[#fcfbf9]'} overflow-hidden`}>
          {isLoading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-stone-50/80 z-10 backdrop-blur-xs">
              <div className="size-6 border-2 border-stone-300 border-t-stone-800 rounded-full animate-spin" />
              <p className="mt-3 font-mono text-xs uppercase tracking-widest text-stone-500">
                Decompressing Draco Mesh...
              </p>
            </div>
          )}

          <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

          {/* Model Metrics Overlay */}
          <div className="absolute bottom-3 left-3 bg-white/95 border border-stone-300 px-3 py-1.5 rounded-[2px] font-mono text-[10px] text-stone-600 flex items-center gap-3 backdrop-blur-xs shadow-xs">
            <span>Meshes: <strong className="text-stone-900">{modelStats.meshes}</strong></span>
            <span>Triangles: <strong className="text-stone-900">{modelStats.triangles.toLocaleString()}</strong></span>
            <span className="text-stone-300">|</span>
            <span>Orbit: Click + Drag · Pan: Right-Click · Zoom: Scroll</span>
          </div>
        </div>
      </div>
    </div>
  );
};
