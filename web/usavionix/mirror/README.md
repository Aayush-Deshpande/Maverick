# USAvionix Deep Frontend Architecture & Asset Teardown
## Advanced Reverse-Engineering Blueprint for High-Fidelity 3D Web Experiences

---

## 1. Executive Summary & Architectural Topology

The **USAvionix** website (`https://www.usavionix.com/`) represents the pinnacle of modern WebGL/3D web engineering, delivering a continuous 60–120 FPS aerospace simulation directly inside the browser. Rather than relying on simple video backgrounds or generic Three.js canvas embeds, the application deploys a synchronized, multi-tier rendering architecture that unifies:

1. **A 6,600dvh Virtual Scroll Runway**: A mathematical scroll timeline controlling 15 discrete mission phases across a continuous viewport canvas.
2. **DCC-Baked Animation Scrubbing**: Camera paths and multi-drone formation choreographies are authored directly in Blender/DCC and exported as dedicated animation GLBs (`camera-animations.glb`, `drone-animations.glb`), with separate rigs for desktop (landscape) and mobile (portrait).
3. **OffscreenCanvas Web Worker Boot**: The initial 3D rotating turbine loading sequence executes entirely inside a dedicated Web Worker on an `OffscreenCanvas`, isolating main-thread React hydration and shader compilation from GPU frame rendering.
4. **Analytic Screen-Space Shaders**: Custom GLSL shaders utilizing partial derivatives (`dFdx`/`dFdy`), blue-noise stochastic dithering, polar-aware normal blending, and screen-space diagonal wipe transitions.
5. **Ultra-Optimized Asset Delivery**: 204 total assets totaling 13.7 MB, utilizing Google Draco geometric compression, embedded WebP GLTF textures (`EXT_texture_webp`), `KHR_materials_unlit` pre-baked lighting, and 32-bit EXR environment maps under 150 KB.

All extracted assets, source chunks, and shaders have been downloaded, verified across multiple network audit passes, and archived locally in the `avionix/` and `frontend-analysis/` directories.

---

## 2. Core Technology Stack & Dependency Matrix

| Layer | Technology | Version / Configuration | Purpose & Implementation Role |
| :--- | :--- | :--- | :--- |
| **Framework** | Next.js | 14.x (App Router) | Server-side rendering, route pre-fetching, layout grouping (`app/(home)` and `app/(info)`). |
| **Runtime UI** | React | 18.x | Declarative component tree, concurrency primitives (`useSyncExternalStore`, `useId`). |
| **3D Rendering** | Three.js + R3F | r160+ / `@react-three/fiber` | Scene graph management, WebGL canvas abstraction, render loop scheduling. |
| **Animation Engine** | `@react-three/drei` | Custom useAnimations | GLTF animation mixer binding, Draco loader wiring, meshopt integration. |
| **Scroll Physics** | `@studio-freight/lenis` | Custom Lenis Controller (`lerp: 0.95`) | Normalized virtual scroll dampening, touch synchronization, section snapping. |
| **State Management** | Zustand + Immer | `zustand` + `immer/produce` | Zero-overhead reactive mission telemetry state, micro-updates without garbage collection. |
| **Geometry Compression** | Google Draco | v1.5.5 (WASM worker) | 80-95% compression on high-poly drone hulls, city terrain, and grid geometries. |
| **Styling & HUD** | Tailwind CSS + Radix UI | Tailwind 3.x + `@radix-ui/react-dialog` | High-density aerospace typography, HUD overlays, accessible modal sheets. |
| **Thread Concurrency** | Dedicated Web Worker | `worker: new Worker(new URL(...))` | OffscreenCanvas loading sequence execution off the main UI thread. |

---

## 3. The 10 "Unknowns": Advanced Hacks & Hidden Implementations

During our deep decompilation and asset dissection, we discovered 10 proprietary techniques that differentiate this site from typical 3D web applications:

### Unknown 1: DCC-Baked Animation Tracks vs. Procedural Interpolation
* **The Problem**: Procedural camera paths (e.g., Catmull-Rom splines or GSAP lerping in JS) require hundreds of lines of code, are difficult for 3D animators to polish, and easily develop unnatural gimbal lock or tangent discontinuities.
* **USAvionix Solution**: The entire camera choreography and drone flight maneuvers are animated in Blender and exported as GLTF animation channels inside `camera-animations.glb` and `drone-animations.glb`. The animation GLB contains zero visible meshes—only transform target dummy nodes (`Camera`, `Drone`, `Drone.001`, `Drone.002`).
* **The Scrubbing Mechanism**: In `tC()` within `page-33beb1af07230f28.js`, the animation action is scrubbed to the exact scroll progress:
  ```javascript
  // Precise boundary clamp: subtract 1e-6 (microsecond) to avoid wrapping to frame 0
  action.time = progress * duration - 1e-6;
  action.play();
  action.paused = true; // Halts auto-advancement by the AnimationMixer

  // Synchronize active Three.js Camera/Mesh to the animated dummy node
  targetObject.position.copy(dummyTracker.position);
  targetObject.rotation.copy(dummyTracker.rotation);
  ```
  This guarantees zero-latency, sub-frame accurate scrubbing synchronized perfectly with user input.

### Unknown 2: Dual Responsive Animation Rigs (Desktop vs. Mobile Viewport Framing)
* **The Problem**: A 3D camera move composed for a 16:9 desktop viewport will cut off focal objects or ruin cinematic framing when viewed on a 9:19.5 smartphone display. Changing camera FOV dynamically alters perspective distortion and focal length unnaturally.
* **USAvionix Solution**: The engineering team authored **two distinct sets of animation GLBs**:
  1. Desktop: `camera-animations.glb` (28.2 KB) and `drone-animations.glb` (16.4 KB).
  2. Mobile: `camera-animations-mobile.glb` (16.9 KB) and `drone-animations-mobile.glb` (15.3 KB).
  The runtime detects screen aspect via `window.matchMedia("(min-width: 768px)")` and automatically hot-swaps the animation clips and dummy trackers. On mobile, camera translations pull back and pitch steeper to maintain strict vertical-safe framing.

### Unknown 3: The 6,600dvh Virtual Scroll Runway & Weighted Stage Snapping
* **The Problem**: Smooth scroll-jacking often feels unresponsive or breaks native momentum.
* **USAvionix Solution**: The page injects a transparent spacer:
  ```html
  <div class="pointer-events-none relative w-full" style="height:calc(6600dvh + 1px + var(--nav-height))"></div>
  ```
  The runway is divided into 15 weighted sections:
  ```javascript
  const sceneWeights = {
    "intro-scene": 100,             // 100vh
    "delta-drone": 500,             // 500vh
    "swarm-scene": 500,             // 500vh
    "mission-preset": 500,          // 500vh
    "flock-scene": 500,             // 500vh
    "real-time-detection": 500,     // 500vh
    "thermal-irregularity": 500,    // 500vh
    "ignition-verified": 500,       // 500vh
    "phalanx-ai": 500,              // 500vh
    "analysis-evaluation": 500,     // 500vh
    "integrated-notifications": 500,// 500vh
    "interdrone-coordination": 500, // 500vh
    "extra-support": 500,           // 500vh
    "zone-stabilized": 100,         // 100vh
    "multi-threat-response": 500    // 500vh
  };
  ```
  Each frame computes:
  - `progress = clamp((scroll - start) / height, 0, 1)`
  - `showRatio = clamp((scroll - (start - innerHeight)) / innerHeight, 0, 1)`
  - `hideRatio = clamp((scroll - end) / innerHeight, 0, 1)`
  - `isActive = showRatio > 0 && hideRatio <= 1`
  When the user releases touch/wheel, a custom physics loop predicts momentum and snaps to `targetSnap = scenes[i].end` using `scrollTo(a, { immediate: true })`.

### Unknown 4: OffscreenCanvas Web Worker Pipeline for Jitter-Free Initial Boot
* **The Problem**: When a complex Next.js + Three.js application loads, JavaScript bundle evaluation, React component tree hydration, and WebGL shader compilation monopolize the main thread for 400–1200ms, causing loading animations to freeze.
* **USAvionix Solution**: The initial rotating 3D loading spinner (`loading-delta.glb`) does not run on the main thread. It is passed to a dedicated Web Worker (`4867.14b24ff1d28f20ed.js`) that renders onto an `OffscreenCanvas`. The spinner runs at a constant 60 FPS while the main thread compiles the heavy application in the background. Only after `mainAppLoaded && imageSequenceLoaded` are verified does the main thread post `{ type: "can-remove-loading" }` to fade out the worker canvas.

### Unknown 5: KHR_materials_unlit + WebP Textures for 120 FPS Terrain Rendering
* **The Problem**: Real-time directional lighting, shadows, and PBR BRDF calculations on complex terrain geometry (`terrain.glb`, 2.09 MB) generate high shader arithmetic costs and thermal throttling on mobile GPUs.
* **USAvionix Solution**: The terrain uses the `KHR_materials_unlit` GLTF extension with textures pre-baked in DCC software and compressed into WebP (`EXT_texture_webp`). In WebGL, the shader simply samples `texture2D` without running dynamic shadow cascades or multi-light loops, freeing GPU cycles for custom post-processing and camera movement.

### Unknown 6: Screen-Space Anti-Aliased Analytic Grid & Radar Shaders
* **The Problem**: Texture-mapped wireframes on curved 3D spheres (like the Earth radar globe) suffer from polar convergence (pinching), texture distortion, and severe aliasing/Moire fringes at oblique angles.
* **USAvionix Solution**: USAvionix renders procedural grids directly in the fragment shader using hardware partial derivatives (`dFdx` and `dFdy`):
  ```glsl
  vec2 ddx = dFdx(uv);
  vec2 ddy = dFdy(uv);
  vec2 uvDeriv = vec2(length(vec2(ddx.x, ddy.x)), length(vec2(ddx.y, ddy.y)));
  vec2 drawWidth = clamp(targetWidth, uvDeriv, vec2(0.5));
  vec2 lineAA = uvDeriv * 1.5;
  vec2 gridUV = abs(fract(uv) * 2.0 - 1.0);
  vec2 grid2 = smoothstep(drawWidth + lineAA, drawWidth - lineAA, gridUV);
  ```
  By clamping the drawn line width to `uvDeriv` and smoothing by `1.5 * uvDeriv`, the grid lines remain exactly 1 to 2 screen pixels wide at any viewing angle or distance, eliminating Moire artifacts entirely without supersampling.

### Unknown 7: Polar Pinching Elimination via Polar-Aware Normal Blending
* **The Problem**: Mapping UV textures to spherical meshes creates severe pinching artifacts at the north and south poles ($vUv.y \approx 0$ or $1$).
* **USAvionix Solution**: In `shader_34_..._noise_terrain.glsl`:
  ```glsl
  vec3 sampleNormalMapPolarBlend(vec2 uv) {
      vec2 repeatedUv = uv * uNormalMapRepeat;
      vec3 uvSample = texture2D(uNormalMap, repeatedUv).xyz * 2.0 - 1.0;
      
      // Object-space XZ projection (rotates with sphere, zero polar convergence)
      vec3 objectNormal = normalize(vPosition);
      vec2 xzUv = objectNormal.xz * uNormalMapRepeat * 0.5 + 0.5;
      vec3 xzSample = texture2D(uNormalMap, xzUv).xyz * 2.0 - 1.0;
      
      // Blend seamlessly into object-space XZ near the top pole
      float polarBlend = smoothstep(0.8, 0.9, uv.y);
      return mix(uvSample, xzSample, polarBlend);
  }
  ```
  This creates a completely seamless radar sphere from equator to pole.

### Unknown 8: Blue Noise Dithering for Artifact-Free Alpha / Heat Transitions
* **The Problem**: Alpha-blended semi-transparent surfaces in Three.js suffer from sorting glitches (depth-write disabled causes back-to-front sorting errors, while depth-write enabled occludes underlying meshes).
* **USAvionix Solution**: In `6288-8ba84c795cccb5ec.js` and `shader_30_...glsl`, USAvionix samples a tiling 64x64 blue noise texture (`bnoise.png`, 48.7 KB):
  ```glsl
  vec2 blueNoiseTexelSize = vec2(textureSize(uBlueNoiseTexture, 0));
  vec4 blueNoiseSample = texture2D(uBlueNoiseTexture, gl_FragCoord.xy / blueNoiseTexelSize);
  ```
  Instead of standard alpha blending, transparency is rendered via blue-noise stochastic screen-door transparency (dithering). The human eye perceives smooth gradients, while the GPU executes opaque depth writes with 100% correct z-buffer occlusions and zero sort overhead.

### Unknown 9: Diagonal Screen-Space 225° Scanline Shader Revealing Tactical Radar
* **The Problem**: Transitioning between a photorealistic satellite map and a tactical wireframe HUD requires a high-tech visual transition that feels military-grade.
* **USAvionix Solution**: The terrain shader incorporates an angled screen-space scan plane:
  ```glsl
  vec2 screenUv = gl_FragCoord.xy / uResolution;
  screenUv = (screenUv - 0.5) / sqrt(2.0) + 0.5;
  vec2 center = vec2(0.5);
  float angle = radians(5.0 * 45.0); // 225 degrees diagonal
  vec2 rotatedUv;
  rotatedUv.x = cos(angle) * (screenUv.x - center.x) - sin(angle) * (screenUv.y - center.y) + center.x;
  rotatedUv.y = sin(angle) * (screenUv.x - center.x) + cos(angle) * (screenUv.y - center.y) + center.y;
  
  // Wipe boundary comparison
  if (rotatedUv.x < uHideRatio) {
      // Tactical Radar Grid mode with Fresnel lighting
  } else {
      // Photorealistic Satellite Base Texture mode
  }
  ```
  At the exact boundary `rotatedUv.x ≈ uHideRatio`, a 2-pixel glowing border laser (`uDpr / uResolution.x * 2.0`) sweeps across the terrain.

### Unknown 10: Hybrid Architecture: 96-Frame AVIF Stills vs. Live WebGL Canvas
* **The Problem**: Rendering full interactive 3D in the footer or during rapid scroll overdraw degrades GPU memory.
* **USAvionix Solution**: The repository contains a pre-rendered 96-frame sequence in AVIF format (`0001.avif` through `0096.avif`, 3.5 MB total). On high-end desktop viewports, the active WebGL scene renders in real time; on mobile low-power mode or inside the simplified footer, the site displays frame 96 (`f.xt[95]`) as an instant, zero-GPU-cost high-fidelity poster image.

---

## 4. Deep Graphics & Shader Breakdown

### 4.1. Jet Engine Plume & Shock-Diamond Shader
The jet engine exhaust is modeled as a truncated cone geometry:
```javascript
<cylinderGeometry args={[0.025, 0.1, 1, 8, 20, true]} />
```
The fragment shader (`shader_26_fragmentShader_..._drone_engine.glsl`) animates supersonic shock diamonds:
```glsl
varying vec3 vViewNormal;
varying vec3 vModelPosition;
varying vec3 vViewPosition;
uniform vec3 uColor;
uniform float uTime;

void main() {
    // Edge glow falloff
    float fresnel = pow(1.0 - dot(normalize(vViewPosition), normalize(vViewNormal)), 3.0);
    
    // Shock diamond pulse along the cylinder Z-axis
    float scan = vModelPosition.z * 7.0 - uTime * 8.0;
    scan = fract(scan);
    scan = 1.0 - smoothstep(0.45, 0.55, scan);
    
    // Core attenuation from nozzle
    vec3 center = vec3(0.0, 0.0, -1.0);
    float dist = distance(vModelPosition, center) * 0.8;
    
    vec3 finalColor = uColor - (scan * 0.15) + (dist * 0.45);
    gl_FragColor = vec4(finalColor, 1.0);
}
```

### 4.2. Fire & Smoke Sprite Sheet Atlas Shader
Wildfire detection instances (`shader_22_fragmentShader_..._fire.glsl`) run an optimized 2D flipbook inside the 3D world:
```glsl
uniform sampler2D uFireTexture;
uniform float uTime;
uniform float uSpeed;
uniform float uFramesPerRow;     // e.g. 8.0
uniform float uTextureColumns;   // e.g. 8.0
uniform float uOpacity;
varying vec2 vUv;

void main() {
    float totalFrames = uFramesPerRow * uFramesPerRow;
    float frameIndex = mod(floor(uTime * uSpeed), totalFrames);
    
    float row = floor(frameIndex / uFramesPerRow);
    float col = mod(frameIndex, uFramesPerRow);
    
    vec2 frameSize = vec2(1.0 / uTextureColumns, 1.0 / uFramesPerRow);
    vec2 frameOffset = vec2(col / uTextureColumns, row / uFramesPerRow);
    vec2 frameUv = vUv * frameSize + frameOffset;
    
    vec4 color = texture2D(uFireTexture, frameUv);
    color.a *= uOpacity;
    if (color.a < 0.01) discard;
    gl_FragColor = color;
}
```

### 4.3. High-Performance Multi-Layer Atmospheric Clouds
Clouds are stacked horizontal planes (`renderOrder: CLOUDS`, `position: [0, height, 0]`) calculated using procedural simplex noise with custom sun scattering:
```glsl
uniform float uTime;
uniform float uCloudSpeed;
uniform float uCloudScale;
uniform float uCloudDensity;
uniform vec3 uSunPosition;
uniform float uFade;

// Multiple octave noise sampling
// Blends sky color into sun forward scattering
float scatter = pow(max(dot(viewDir, sunDir), 0.0), 4.0);
vec3 finalColor = mix(uSkyColor, uCloudColor + uSunColor * scatter, cloudDensity);
gl_FragColor = vec4(finalColor, cloudDensity * uFade * 0.3);
```

---

## 5. Asset Architecture & Compression Masterclass

### 5.1. Complete 204-Asset Inventory Breakdown
From our multi-pass extraction into `avionix/`:
- **13 3D Models (`.glb`)**: 4.05 MB total
  - `terrain.glb`: 2.09 MB (baked unlit landscape)
  - `delta-pbr.glb`: 964 KB (high-detail hero jet drone with decals and turbine)
  - `city-terrain.glb`: 438 KB (urban elevation grid)
  - `loading-delta.glb`: 140 KB (worker boot spinner)
  - `delta-lowpoly.glb`: 3.8 KB (extreme LOD drone for swarm formations)
  - `camera-animations.glb`: 28.2 KB (12 desktop camera tracks)
  - `camera-animations-mobile.glb`: 16.9 KB (12 mobile camera tracks)
  - `drone-animations.glb`: 16.4 KB (6 drone formation tracks)
  - `drone-animations-mobile.glb`: 15.3 KB (6 mobile drone formation tracks)
  - `grid.glb`, `grid-city.glb`, `power-station.glb`, `building.glb`: 11–33 KB each.
- **96 AVIF Sequence Frames**: 3.51 MB total (average 36.5 KB per 1920x1080 frame).
- **16 WebP / EXR Textures**: 2.24 MB total
  - `fire.webp`: 685 KB (high-res particle flipbook)
  - `city.webp`: 573 KB (satellite imagery)
  - `env.exr`: 148 KB (32-bit float IBL cubemap)
  - `wind.webp`, `noise.webp`, `bnoise.png`: 48–198 KB each.
- **49 JavaScript Chunks**: 3.32 MB total (Next.js App Router, R3F runtime, Three.js core, Web Worker).
- **11 Typography Subsets (`.woff2`)**: 142 KB total (Geist, Geist Mono).
- **1 Three.js Typeface (`.json`)**: 6.3 KB (`orbitron-bold.json` for 3D vector text).
- **1 WebAssembly Binary (`.wasm`)**: 283 KB (Google Draco decompressor).

### 5.2. Draco & Meshopt Compression Pipeline
- Meshes are pre-processed using `gltf-transform` or `draco_encoder`:
  - Position quantization: 14 bits
  - Normal quantization: 10 bits
  - Texcoord quantization: 12 bits
- Textures are embedded directly into GLBs using `EXT_texture_webp`, avoiding separate network roundtrips for diffuse/roughness maps while reducing asset sizes by over 70% compared to standard PNG/JPEG GLBs.

---

## 6. Interaction, HUD & Mission Synchronization Engine

The site’s HUD is not an afterthought—it functions as an aerospace Heads-Up Display strictly bound to the 3D simulation state.

### 6.1. Mission Stages & Telemetry Data Flow
As the virtual scroll progresses through the 15 stages, the Zustand store triggers HUD readouts:
1. `delta-drone` (Alt 1,240m | Speed 74 km/h | Coord: 37.4419°N / 119.8772°W)
2. `swarm-scene` (Flock formation mode | 32 Car / 4 Truck / 1 Person / 2 UAV)
3. `thermal-irregularity` (Signal Intensity: 87% | Classification: Potential Threat)
4. `ignition-verified` (2 Wildfires + 1 Roadblock Detected | Firefighter Units Alerted)
5. `zone-stabilized` (Area Status: SECURED)

### 6.2. Camera Micro-Shake Physics Matrix
To simulate jet engine vibration, atmospheric turbulence, and supersonic flight, the camera controller applies procedural shake intensities defined per mission phase:
```javascript
const cameraShakeMatrix = {
  [SCENE.INTRO_SCENE]:           { shakeIntensity: 0.0010 },
  [SCENE.REAL_TIME_DETECTION]:   { shakeIntensity: 0.0020 },
  [SCENE.THERMAL_IRREGULARITY]:  { shakeIntensity: 0.0015 },
  [SCENE.IGNITION_VERIFIED]:     { shakeIntensity: 0.0025 }
};
```
Inside the `useFrame` loop, high-frequency trigonometric noise is scaled by `shakeIntensity` and added to the camera's local translation.

---

## 7. Production Replication Blueprint for Our Project

To replicate this exact architectural standard in our own jet drone engine dashboard project, we can implement four core modules:

### Module 1: Virtual Runway & Lenis Snapping Provider (`VirtualRunway.tsx`)
```typescript
import React, { createContext, useContext, useEffect, useRef } from "react";
import Lenis from "@studio-freight/lenis";
import { create } from "zustand";

interface SceneState {
  progress: number;
  isActive: boolean;
  showRatio: number;
  hideRatio: number;
}

interface MissionStore {
  scenes: Record<string, SceneState>;
  updateScene: (id: string, state: SceneState) => void;
}

export const useMissionStore = create<MissionStore>((set) => ({
  scenes: {},
  updateScene: (id, state) =>
    set((prev) => ({
      scenes: { ...prev.scenes, [id]: state },
    })),
}));

export const VirtualRunwayProvider: React.FC<{
  stages: { id: string; weightVh: number }[];
  children: React.ReactNode;
}> = ({ stages, children }) => {
  const lenisRef = useRef<Lenis | null>(null);

  useEffect(() => {
    const lenis = new Lenis({
      lerp: 0.95,
      syncTouch: true,
      smoothWheel: true,
    });
    lenisRef.current = lenis;

    const onScroll = ({ scroll }: { scroll: number }) => {
      const vh = window.innerHeight;
      let accumulated = 0;

      for (const stage of stages) {
        const height = (stage.weightVh / 100) * vh;
        const start = accumulated;
        const end = start + height;
        accumulated += height;

        const progress = Math.min(Math.max((scroll - start) / height, 0), 1);
        const showRatio = Math.min(Math.max((scroll - (start - vh)) / vh, 0), 1);
        const hideRatio = Math.min(Math.max((scroll - end) / vh, 0), 1);
        const isActive = showRatio > 0 && hideRatio <= 1;

        useMissionStore.getState().updateScene(stage.id, {
          progress,
          isActive,
          showRatio,
          hideRatio,
        });
      }
    };

    lenis.on("scroll", onScroll);
    function raf(time: number) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);

    return () => lenis.destroy();
  }, [stages]);

  const totalVh = stages.reduce((sum, s) => sum + s.weightVh, 0);

  return (
    <div className="relative w-full">
      {/* Fixed Viewport 3D Canvas */}
      <div className="fixed inset-0 w-screen h-screen pointer-events-none z-0">
        {children}
      </div>
      {/* Scroll Runway Spacer */}
      <div style={{ height: `${totalVh}vh` }} className="w-full pointer-events-none" />
    </div>
  );
};
```

### Module 2: Blender DCC Animation Scrubbing Hook (`useDCCScrub.ts`)
```typescript
import { useEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { useAnimations } from "@react-three/drei";
import * as THREE from "three";
import { useMissionStore } from "./VirtualRunway";

export function useDCCScrub(
  sceneId: string,
  clipName: string,
  gltfAnimations: THREE.AnimationClip[],
  trackerNodeName: string,
  targetObjectRef: React.RefObject<THREE.Object3D>,
  rootGroupRef: React.RefObject<THREE.Group>,
  priorityOrder: number = 0
) {
  const { actions } = useAnimations(gltfAnimations, rootGroupRef);
  const trackerRef = useRef<THREE.Object3D | null>(null);
  const actionRef = useRef<THREE.AnimationAction | null>(null);

  useEffect(() => {
    if (rootGroupRef.current) {
      rootGroupRef.current.traverse((child) => {
        if (child.name === trackerNodeName) {
          trackerRef.current = child;
        }
      });
    }
    actionRef.current = actions[clipName] || null;
  }, [actions, clipName, trackerNodeName]);

  useFrame(() => {
    const action = actionRef.current;
    const tracker = trackerRef.current;
    const target = targetObjectRef.current;
    if (!action || !tracker || !target) return;

    const sceneState = useMissionStore.getState().scenes[sceneId];
    if (!sceneState) return;

    const { progress, isActive } = sceneState;
    if (isActive || progress > 0) {
      const duration = action.getClip().duration;
      // Subtract microsecond to guarantee strict non-looping boundary clamping
      action.time = Math.max(0, Math.min(progress * duration - 1e-6, duration));
      action.play();
      action.paused = true;

      // Copy exact translation and quaternion from the animated dummy node
      target.position.copy(tracker.position);
      target.quaternion.copy(tracker.quaternion);
    }
  }, priorityOrder);
}
```

### Module 3: Anti-Aliased Derivative Screen-Space Grid Material
```typescript
import * as THREE from "three";

export const AnalyticRadarGridMaterial = new THREE.ShaderMaterial({
  transparent: true,
  uniforms: {
    uColor: { value: new THREE.Color(0x38bdf8) },
    uGridDensity: { value: new THREE.Vector2(40.0, 25.0) },
    uLineWidth: { value: 0.02 },
  },
  vertexShader: `
    varying vec2 vUv;
    varying vec3 vWorldPosition;
    void main() {
      vUv = uv;
      vec4 worldPos = modelMatrix * vec4(position, 1.0);
      vWorldPosition = worldPos.xyz;
      gl_Position = projectionMatrix * viewMatrix * worldPos;
    }
  `,
  fragmentShader: `
    varying vec2 vUv;
    uniform vec3 uColor;
    uniform vec2 uGridDensity;
    uniform float uLineWidth;

    vec2 getGrid(vec2 uv, float width) {
      vec2 ddx = dFdx(uv);
      vec2 ddy = dFdy(uv);
      vec2 uvDeriv = vec2(length(vec2(ddx.x, ddy.x)), length(vec2(ddx.y, ddy.y)));
      vec2 targetWidth = vec2(width);
      vec2 drawWidth = clamp(targetWidth, uvDeriv, vec2(0.5));
      vec2 lineAA = uvDeriv * 1.5;
      vec2 gridUV = abs(fract(uv) * 2.0 - 1.0);
      vec2 grid2 = smoothstep(drawWidth + lineAA, drawWidth - lineAA, gridUV);
      grid2 *= clamp(targetWidth / drawWidth, 0.0, 1.0);
      return grid2;
    }

    void main() {
      vec2 gridUV = vUv * uGridDensity;
      vec2 g = getGrid(gridUV, uLineWidth);
      float line = max(g.x, g.y);
      if (line < 0.01) discard;
      gl_FragColor = vec4(uColor, line * 0.85);
    }
  `,
});
```

---

## 8. Verification & File Integrity Confirmation

- **Primary Assets Location**: `e:\backup-llm\backup-no-llm\3d_engine\avionix\`
- **Analysis Documentation**: `e:\backup-llm\backup-no-llm\3d_engine\frontend-analysis\`
- **Catalog of Assets**: [`avionix/ASSET_CATALOG.md`](file:///e:/backup-llm/backup-no-llm/3d_engine/avionix/ASSET_CATALOG.md) & [`frontend-analysis/ASSET_CATALOG.md`](file:///e:/backup-llm/backup-no-llm/3d_engine/frontend-analysis/ASSET_CATALOG.md)
- **Extracted GLSL Shaders**: 40 standalone shader files in [`frontend-analysis/extracted/shaders/`](file:///e:/backup-llm/backup-no-llm/3d_engine/frontend-analysis/extracted/shaders/)
- **Total Downloaded Assets**: **204 files**
- **Total Size on Disk**: **13.70 MB**
- **Verification Status**: Multi-pass network audit converged on Pass 3 with **zero missing resources**.
