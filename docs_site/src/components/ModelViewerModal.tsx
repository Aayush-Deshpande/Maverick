import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { X, RotateCw, Eye, Box, Maximize2, Minimize2 } from 'lucide-react';

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
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [modelStats, setModelStats] = useState<{ meshes: number; triangles: number }>({ meshes: 0, triangles: 0 });

  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const currentObjectRef = useRef<THREE.Group | null>(null);

  useEffect(() => {
    setSelectedModel(initialModel);
  }, [initialModel]);

  useEffect(() => {
    if (!isOpen || !mountRef.current) return;

    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight;

    // Create Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xfafaf9);
    sceneRef.current = scene;

    // Create Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(2.5, 1.8, 3.2);

    // Create Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    mountRef.current.innerHTML = '';
    mountRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.autoRotate = autoRotate;
    controls.autoRotateSpeed = 1.0;
    controlsRef.current = controls;

    // Lighting (Studio neutral)
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.4);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.8);
    dirLight1.position.set(5, 10, 7);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xf5f5f4, 0.9);
    dirLight2.position.set(-5, -3, -5);
    scene.add(dirLight2);

    // Subtle Ground Grid
    const grid = new THREE.GridHelper(6, 24, 0xd6d3d1, 0xe7e5e4);
    grid.position.y = -0.6;
    scene.add(grid);

    // Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.autoRotate = autoRotate;
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Resize Handler
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
      renderer.dispose();
    };
  }, [isOpen]);

  // Load Model
  useEffect(() => {
    if (!isOpen || !sceneRef.current) return;

    setIsLoading(true);
    const scene = sceneRef.current;

    // Remove existing model
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

        // Auto-center & Scale
        const box = new THREE.Box3().setFromObject(object);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = 1.8 / maxDim;

        object.scale.setScalar(scale);
        object.position.sub(center.multiplyScalar(scale));
        object.position.y += 0.1;

        // Gather stats & apply material settings
        let meshCount = 0;
        let triCount = 0;

        object.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            meshCount++;
            if (mesh.geometry) {
              triCount += mesh.geometry.index
                ? mesh.geometry.index.count / 3
                : mesh.geometry.attributes.position.count / 3;
            }

            if (mesh.material) {
              const mat = mesh.material as THREE.MeshStandardMaterial;
              mat.wireframe = wireframe;
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
        className={`bg-white border border-stone-300 rounded-sm shadow-xl flex flex-col overflow-hidden transition-all duration-200 ${
          isFullscreen ? 'w-full h-full' : 'w-full max-w-5xl h-[85vh]'
        }`}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-stone-200 bg-stone-50">
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
              className="p-1.5 text-stone-500 hover:text-stone-900 hover:bg-stone-200 rounded transition-colors"
              title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-stone-500 hover:text-stone-900 hover:bg-stone-200 rounded transition-colors"
              title="Close modal"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Toolbar & Selector */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-2.5 border-b border-stone-200 bg-white text-xs">
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[11px] uppercase tracking-wider text-stone-400 mr-1">Platform:</span>
            {AVAILABLE_MODELS.map((model) => (
              <button
                key={model.id}
                onClick={() => setSelectedModel(model.id)}
                className={`px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider rounded border transition-colors ${
                  selectedModel === model.id
                    ? 'bg-stone-900 text-white border-stone-900'
                    : 'bg-stone-50 text-stone-600 border-stone-200 hover:bg-stone-100 hover:text-stone-900'
                }`}
              >
                {model.name}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setWireframe(!wireframe)}
              className={`flex items-center gap-1.5 px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider rounded border transition-colors ${
                wireframe
                  ? 'bg-stone-800 text-white border-stone-800'
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
                  ? 'bg-stone-800 text-white border-stone-800'
                  : 'bg-stone-50 text-stone-600 border-stone-200 hover:bg-stone-100'
              }`}
            >
              <RotateCw size={13} />
              <span>{autoRotate ? 'Pause' : 'Rotate'}</span>
            </button>
          </div>
        </div>

        {/* 3D Canvas Viewport */}
        <div className="relative flex-1 bg-[#fafaf9] overflow-hidden">
          {isLoading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-stone-50/80 z-10">
              <div className="size-6 border-2 border-stone-300 border-t-stone-800 rounded-full animate-spin" />
              <p className="mt-3 font-mono text-xs uppercase tracking-widest text-stone-500">
                Decompressing Draco Mesh...
              </p>
            </div>
          )}

          <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

          {/* Model Metrics Overlay */}
          <div className="absolute bottom-3 left-3 bg-white/90 border border-stone-200 px-3 py-1.5 rounded-xs font-mono text-[10px] text-stone-600 flex items-center gap-3">
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
