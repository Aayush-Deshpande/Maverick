// The sortie film's 3D world: a procedural Karakoram-style valley loop at dusk, the UAV, its
// software twin flying inside it, the glide footprint and the airfields. Everything is a pure
// function of story time `t` (see story.ts), so cuts between chapters are exact.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { CHAPTERS, STARTS, TOTAL, T_TOUCH, T_GLIDE, T_TURN, T_ASSESS, T_DECIDE, FLASH, startOf } from './story';
import { T_CONFIRM, readout } from './timeline';
import { EngineBay, type BayFrame, type ComponentMap } from './bay';
import { preloader } from './preload';

/* ------------------------------------------------------------------ noise */

function hash2(ix: number, iz: number, seed: number) {
  let h = (Math.imul(ix, 374761393) + Math.imul(iz, 668265263) + Math.imul(seed, 982451653)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
function vnoise(x: number, z: number, seed = 0) {
  const ix = Math.floor(x), iz = Math.floor(z);
  const fx = x - ix, fz = z - iz;
  const ux = fx * fx * fx * (fx * (fx * 6 - 15) + 10), uz = fz * fz * fz * (fz * (fz * 6 - 15) + 10);
  const a = hash2(ix, iz, seed), b = hash2(ix + 1, iz, seed), c = hash2(ix, iz + 1, seed), d = hash2(ix + 1, iz + 1, seed);
  return (a + (b - a) * ux + (c - a) * uz + (a - b - c + d) * ux * uz) * 2 - 1;
}
/** Ridged multifractal: sharp crests, the look of high glaciated ranges. */
function ridged(x: number, z: number) {
  let sum = 0, amp = 0.55, freq = 1, weight = 1;
  for (let o = 0; o < 6; o++) {
    let n = 1 - Math.abs(vnoise(x * freq, z * freq, o * 17 + 3));
    n *= n;
    n *= weight;
    weight = Math.min(1, Math.max(0, n * 1.6));
    sum += n * amp;
    freq *= 2.07; amp *= 0.5;
  }
  return sum;
}

/* ------------------------------------------------------------------ geometry of the sortie */

const EXTENT = 9000;
const SPEED = 70; // world units per story second (1 unit ≈ 0.5 m, so ≈ 68 kt)
const CRUISE = 165;
const ROLL = 4.6;
/** Height of the carrier origin above the runway when the wheels touch; set from the model's own bounds. */
let GEAR = 2.3;
const RUNWAY_SURFACE = 0.6;

const loopPts = [
  [0, -1750], [1250, -1500], [1900, -520], [1700, 700], [2050, 1500], [900, 2050],
  [-450, 1650], [-1500, 1950], [-2150, 900], [-1750, -150], [-2050, -1150], [-1050, -1800],
].map(([x, z]) => new THREE.Vector3(x, 0, z));
const path = new THREE.CatmullRomCurve3(loopPts, true, 'centripetal');
const L = path.getLength();
const S0 = 0.04 * L;
const S_TURN = S0 + SPEED * T_TURN;       // where the aircraft leaves the valley it was following
const S_LEH = S_TURN + 0.47 * L;           // Leh lies further along that valley: out of glide reach
const wrap = (s: number) => ((s % L) + L) % L;
const circ = (a: number, b: number) => { const d = Math.abs(wrap(a) - wrap(b)); return Math.min(d, L - d); };
const sstep = (a: number, b: number, x: number) => { const k = Math.min(1, Math.max(0, (x - a) / (b - a))); return k * k * (3 - 2 * k); };

function rawFloor(s: number) {
  const a = (wrap(s) / L) * Math.PI * 2;
  return 40 * Math.sin(a * 3 + 1) + 22 * Math.sin(a * 7 + 0.4);
}
/** Valley floor height along the path, flattened around each airfield. */
function floorAt(s: number) {
  let f = rawFloor(s);
  for (const sa of [S_LEH]) {
    const w = sstep(620, 260, circ(s, sa));
    f = f + (rawFloor(sa) - f) * w;
  }
  return f;
}

/* ---- the divert: a banked turn out of the valley into a side basin, then the final approach to Thoise.
   Built from where the aircraft actually is at the decision, so the turn starts tangent to its track. */
const UP = new THREE.Vector3(0, 1, 0);
const TURN_P = path.getPointAt(wrap(S_TURN) / L).setY(0);
const TURN_T = path.getTangentAt(wrap(S_TURN) / L).setY(0).normalize();
const TURN_N = (() => { const n = new THREE.Vector3().crossVectors(TURN_T, UP).normalize(); return n.dot(TURN_P) < 0 ? n.negate() : n; })();
const turnCurve = new THREE.CatmullRomCurve3([
  TURN_P.clone(),
  TURN_P.clone().addScaledVector(TURN_T, 240),
  TURN_P.clone().addScaledVector(TURN_T, 450).addScaledVector(TURN_N, 160),
  TURN_P.clone().addScaledVector(TURN_T, 540).addScaledVector(TURN_N, 420),
], false, 'centripetal');
const L_TURN = turnCurve.getLength();
const FINAL_DIR = turnCurve.getTangentAt(1).setY(0).normalize();
const FINAL_P = turnCurve.getPointAt(1).setY(0);
/** Branch distance to touchdown: the timeline fixes it, the final straight absorbs it. */
const D_TOUCH = SPEED * (T_TOUCH - T_TURN);
const D_THRESHOLD = D_TOUCH - 60;
const RUNWAY_LEN = 340;
function branchXZ(d: number, out = new THREE.Vector3()) {
  if (d <= L_TURN) return out.copy(turnCurve.getPointAt(Math.max(0, d) / L_TURN)).setY(0);
  return out.copy(FINAL_P).addScaledVector(FINAL_DIR, d - L_TURN);
}
function branchFloor(d: number) {
  const f0 = floorAt(S_TURN), fr = f0 - 22; // the basin sits a little lower than the valley floor
  return f0 + (fr - f0) * sstep(0, D_THRESHOLD, d);
}
const THOISE_CENTRE = branchXZ(D_THRESHOLD + RUNWAY_LEN / 2);

/** Runway centres in plan view: the ground is kept flat around them so nothing pokes through the strip. */
const RUNWAYS_XZ = [[THOISE_CENTRE.x, THOISE_CENTRE.z], ...[S_LEH].map((s) => { const p = path.getPointAt(wrap(s) / L); return [p.x, p.z]; })];

const KARGIL = new THREE.Vector3(-4300, 0, 3100);
const KARGIL_FLOOR = 60;

/* distance field from the valley axis, sampled on a coarse grid */
const DF_N = 180;
const dfDist = new Float32Array(DF_N * DF_N);
const dfFloor = new Float32Array(DF_N * DF_N);
(function buildField() {
  const samples: Array<{ x: number; z: number; f: number }> = [];
  const n = 700;
  for (let i = 0; i < n; i++) {
    const s = (i / n) * L;
    const p = path.getPointAt(i / n);
    samples.push({ x: p.x, z: p.z, f: floorAt(s) });
  }
  for (let d = 0; d <= D_THRESHOLD + RUNWAY_LEN + 260; d += 12) {
    const p = branchXZ(d);
    samples.push({ x: p.x, z: p.z, f: branchFloor(d) });
  }
  for (let j = 0; j < DF_N; j++) for (let i = 0; i < DF_N; i++) {
    const x = (i / (DF_N - 1) - 0.5) * EXTENT, z = (j / (DF_N - 1) - 0.5) * EXTENT;
    let best = 1e12, bf = 0;
    for (const p of samples) { const d = (p.x - x) ** 2 + (p.z - z) ** 2; if (d < best) { best = d; bf = p.f; } }
    let dist = Math.sqrt(best);
    const dk = Math.hypot(x - KARGIL.x, z - KARGIL.z) - 260;
    if (dk < dist) { dist = Math.max(0, dk); bf = KARGIL_FLOOR; }
    dfDist[j * DF_N + i] = dist; dfFloor[j * DF_N + i] = bf;
  }
})();
function sampleField(x: number, z: number) {
  const gx = Math.min(DF_N - 1.001, Math.max(0, (x / EXTENT + 0.5) * (DF_N - 1)));
  const gz = Math.min(DF_N - 1.001, Math.max(0, (z / EXTENT + 0.5) * (DF_N - 1)));
  const i = Math.floor(gx), j = Math.floor(gz), fx = gx - i, fz = gz - j;
  const k = j * DF_N + i;
  const lerp2 = (arr: Float32Array) => (arr[k] * (1 - fx) + arr[k + 1] * fx) * (1 - fz) + (arr[k + DF_N] * (1 - fx) + arr[k + DF_N + 1] * fx) * fz;
  return { d: lerp2(dfDist), f: lerp2(dfFloor) };
}
export function terrainHeight(x: number, z: number) {
  const { d, f } = sampleField(x, z);
  const m = 120 + 860 * ridged(x * 0.00042 + 11.3, z * 0.00042 - 4.1);
  const wall = Math.pow(sstep(95, 820, d), 1.35);
  const nearRunway = Math.min(...RUNWAYS_XZ.map(([rx, rz]) => Math.hypot(x - rx, z - rz)));
  const floorNoise = 3 * vnoise(x * 0.01, z * 0.01, 91) * sstep(200, 460, nearRunway) - 1.2 * (1 - sstep(200, 460, nearRunway));
  return f + floorNoise + (m + 25 * vnoise(x * 0.004, z * 0.004, 5)) * wall;
}

/* ------------------------------------------------------------------ flight */

export interface Pose { pos: THREE.Vector3; fwd: THREE.Vector3; bank: number }

function sAt(t: number) { return S0 + SPEED * Math.min(t, T_TURN); }
/** Distance along the divert branch (0 before the turn), with a braking roll-out after touchdown. */
function routeDist(t: number) {
  if (t <= T_TURN) return 0;
  if (t <= T_TOUCH) return SPEED * (t - T_TURN);
  const k = Math.min(1, (t - T_TOUCH) / ROLL);
  return D_TOUCH + SPEED * ROLL * (k - (k * k) / 2);
}
/** Floor under the aircraft. */
function groundAt(t: number) { return t < T_TURN ? floorAt(sAt(t)) : branchFloor(routeDist(t)); }
/* ---- the approach and landing, built so nothing is discontinuous:
   a gentle push-over onto the glide slope, a linear glide, then a flare whose sink rate reaches zero
   exactly at touchdown (slope-matched to the glide); main wheels first with the nose up, one damped
   suspension compression, the nose lowered onto its wheel, and a braking roll-out. */
const T_APPROACH = T_GLIDE + 1.5; // descent begins as the turn starts and power comes back
const FLARE_K = 0.86;      // fraction of the approach flown on the glide slope
const PUSHOVER = 0.12;     // fraction of the glide slope spent easing into it
const T_FLARE = T_APPROACH + (T_TOUCH - T_APPROACH) * FLARE_K;
function pushover(u: number) {
  const a = PUSHOVER, c = 1 - a / 2;
  return (u < a ? (u * u) / (2 * a) : u - a / 2) / c;
}
/** Suspension: one damped compression after the main wheels meet the runway (units, negative = down). */
function suspension(dt: number) {
  if (dt <= 0) return 0;
  const w = 7.5, zeta = 0.55, wd = w * Math.sqrt(1 - zeta * zeta);
  return -0.32 * Math.exp(-zeta * w * dt) * Math.sin(wd * dt);
}
/** Nose-up attitude added to the flight path (radians). */
function pitchAt(t: number) {
  if (t < T_APPROACH) return 0.03;
  if (t < T_FLARE) return 0.03 + 0.02 * sstep(T_APPROACH, T_APPROACH + 2, t);
  if (t < T_TOUCH) return 0.05 + 0.075 * sstep(T_FLARE, T_TOUCH, t);
  return 0.125 * (1 - sstep(T_TOUCH + 0.25, T_TOUCH + 1.7, t)); // the nose comes down onto its wheel
}
function altAt(t: number, s: number) {
  const cruise = CRUISE + 26 * Math.sin(s * 0.0035) + 10 * Math.sin(s * 0.011);
  if (t <= T_APPROACH) return cruise;
  const ground = GEAR + RUNWAY_SURFACE;
  if (t >= T_TOUCH) return ground + suspension(t - T_TOUCH);
  const k = (t - T_APPROACH) / (T_TOUCH - T_APPROACH);
  const sa = S_TURN + SPEED * 1.5;
  const h0 = CRUISE + 26 * Math.sin(sa * 0.0035) + 10 * Math.sin(sa * 0.011) - ground;
  const c = 1 - PUSHOVER / 2;
  const hf = h0 / (1 + (2 * FLARE_K * c) / (1 - FLARE_K)); // flare entry height that matches the glide slope
  const h = k < FLARE_K ? h0 - (h0 - hf) * pushover(k / FLARE_K) : hf * (1 - (k - FLARE_K) / (1 - FLARE_K)) ** 2;
  return ground + h;
}
function pointAt(t: number, out = new THREE.Vector3()) {
  if (t < T_TURN) {
    const s = sAt(t);
    path.getPointAt(wrap(s) / L, out);
    out.y = floorAt(s) + altAt(t, s);
    return out;
  }
  const d = routeDist(t);
  branchXZ(d, out);
  out.y = branchFloor(d) + altAt(t, S_TURN + d);
  return out;
}
const _a = new THREE.Vector3(), _b = new THREE.Vector3();
function heading(t: number) {
  const p = pointAt(t - 0.05), q = pointAt(t + 0.05);
  return Math.atan2(q.x - p.x, q.z - p.z);
}
export function pose(t: number): Pose {
  const pos = pointAt(t);
  pointAt(t - 0.15, _a); pointAt(t + 0.15, _b);
  const fwd = _b.clone().sub(_a);
  if (fwd.lengthSq() < 1e-6) { if (t < T_TURN) path.getTangentAt(wrap(sAt(t)) / L, fwd); else fwd.copy(FINAL_DIR); }
  fwd.normalize();
  let dh = heading(t + 0.5) - heading(t - 0.5);
  if (dh > Math.PI) dh -= Math.PI * 2; if (dh < -Math.PI) dh += Math.PI * 2;
  const moving = t < T_TOUCH ? 1 : 0;
  const bank = Math.max(-0.48, Math.min(0.48, -dh * 1.5)) * moving; // a calculated turn: about 25 degrees of bank at most
  return { pos, fwd, bank };
}

/* ------------------------------------------------------------------ shaders */

const terrainVert = /* glsl */ `
  varying vec3 vWorld; varying vec3 vNormal;
  void main() {
    vec4 w = modelMatrix * vec4(position, 1.0);
    vWorld = w.xyz; vNormal = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * viewMatrix * w;
  }`;
const terrainFrag = /* glsl */ `
  uniform vec3 uSun; uniform vec3 uFog; uniform float uFogD; uniform vec3 uRing; uniform float uRingA;
  uniform vec3 uRingCol; uniform float uTime;
  varying vec3 vWorld; varying vec3 vNormal;
  float line(float v, float width) { float w = fwidth(v) * width; float d = abs(fract(v - 0.5) - 0.5); return 1.0 - smoothstep(0.0, w, d); }
  void main() {
    vec3 n = normalize(vNormal);
    float h = vWorld.y;
    float diff = max(dot(n, uSun), 0.0);
    float slope = 1.0 - n.y;
    vec3 rock = mix(vec3(0.13, 0.15, 0.155), vec3(0.27, 0.285, 0.27), smoothstep(0.0, 600.0, h));
    float streak = 0.5 + 0.5 * sin(vWorld.x * 0.023 + 3.0 * sin(vWorld.z * 0.004)) * sin(vWorld.z * 0.019 + 2.0 * sin(vWorld.x * 0.005) + h * 0.02);
    float snow = smoothstep(260.0, 640.0, h + 110.0 * sin(vWorld.x * 0.013) * cos(vWorld.z * 0.011)) * smoothstep(0.3, 0.7, n.y + 0.15 * streak);
    vec3 base = mix(rock, vec3(0.78, 0.83, 0.82), snow);
    vec3 col = base * (0.30 + 1.1 * diff) + vec3(0.07, 0.10, 0.105) * (0.6 + 0.4 * n.y);
    // wind-streaked faces catch the low sun
    col += vec3(0.24, 0.27, 0.26) * pow(diff, 2.0) * smoothstep(0.2, 0.6, slope) * (0.4 + 0.6 * streak);
    float dist = length(vWorld - cameraPosition);
    float near = 1.0 - smoothstep(1800.0, 6500.0, dist);
    float minor = line(h / 40.0, 1.1) * 0.16;
    float major = line(h / 200.0, 1.4) * 0.38;
    col = mix(col, vec3(0.72, 0.86, 0.84), (minor + major) * near);
    // faint survey grid
    float grid = max(line(vWorld.x / 500.0, 1.0), line(vWorld.z / 500.0, 1.0)) * 0.07 * near;
    col = mix(col, vec3(0.55, 0.75, 0.74), grid);
    // glide footprint, draped on the ground
    float rd = length(vWorld.xz - uRing.xy);
    float ring = (1.0 - smoothstep(0.0, max(fwidth(rd) * 2.5, 12.0), abs(rd - uRing.z)));
    float inside = 1.0 - smoothstep(uRing.z - 4.0, uRing.z, rd);
    float sweep = 0.5 + 0.5 * sin(rd * 0.03 - uTime * 2.0);
    col = mix(col, uRingCol, uRingA * (ring * 0.95 + inside * (0.10 + 0.06 * sweep)));
    float f = 1.0 - exp(-pow(dist * uFogD, 2.0));
    gl_FragColor = vec4(mix(col, uFog, f), 1.0);
  }`;
const skyFrag = /* glsl */ `
  uniform vec3 uTop; uniform vec3 uHorizon; uniform vec3 uSun; varying vec3 vDir;
  void main() {
    vec3 d = normalize(vDir);
    float k = smoothstep(-0.05, 0.55, d.y);
    vec3 c = mix(uHorizon, uTop, k);
    float s = max(dot(d, normalize(uSun)), 0.0);
    c += vec3(0.95, 0.78, 0.55) * pow(s, 24.0) * 0.35 + vec3(0.9, 0.85, 0.7) * pow(s, 4.0) * 0.08;
    gl_FragColor = vec4(c, 1.0);
  }`;
const ghostVert = /* glsl */ `
  varying vec3 vN; varying vec3 vV;
  void main() { vec4 mv = modelViewMatrix * vec4(position, 1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`;
const ghostFrag = /* glsl */ `
  uniform vec3 uCol; uniform float uA; uniform float uTime; varying vec3 vN; varying vec3 vV;
  void main() {
    float f = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.2);
    float scan = 0.75 + 0.25 * sin(gl_FragCoord.y * 0.9 + uTime * 6.0);
    gl_FragColor = vec4(uCol, (f * 0.95 + 0.04) * uA * scan);
  }`;

/* ------------------------------------------------------------------ world */

export const SKY = { top: new THREE.Color('#4f6966'), horizon: new THREE.Color('#aec4bc') };
const CYAN = new THREE.Color('#58e6f2');
const FOG_D = 0.000155;

export interface ScreenField { id: string; x: number; y: number; on: boolean }
export interface Screen {
  box: { x: number; y: number; w: number; h: number; on: boolean };
  fields: ScreenField[];
  bay: BayFrame | null;
  aircraft: { x: number; y: number; on: boolean };
  flash: boolean;
}


function glowTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d')!;
  const r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(0.25, 'rgba(255,255,255,0.55)'); r.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = r; g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

export class SortieWorld {
  renderer: THREE.WebGLRenderer;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(42, 1, 1, 40000);
  private carrier = new THREE.Group();
  private ghost = new THREE.Group();
  private ghostMats: THREE.ShaderMaterial[] = [];
  private hull: THREE.Vector3[] = [];
  private terrainMat: THREE.ShaderMaterial;
  private trail: THREE.Mesh;
  private trailPos: Float32Array;
  private trailAlpha: Float32Array;
  private glow: THREE.Sprite;
  private glidePath: THREE.Line;
  private fieldPos: Array<{ id: string; p: THREE.Vector3 }> = [];
  private camPos = new THREE.Vector3();
  private camLook = new THREE.Vector3();
  private hasCam = false;
  private env: THREE.Texture | null = null;
  private engineLocal = new THREE.Vector3(0, 0, -11);
  private ringCenter = new THREE.Vector2();
  private ringR = 1;
  private tailPts: THREE.Vector3[] = [];
  private bodyMats: THREE.Material[] = [];
  private xray = 0;
  private prop = new THREE.Group();
  private propLocal = new THREE.Vector3();
  private propDisc: THREE.Mesh | null = null;
  private propBlades: THREE.Group | null = null;
  private flashBase: { p: THREE.Vector3; fwd: THREE.Vector3 } | null = null;
  private wasFlash = false;
  private glidePathCount = 0;
  bay: EngineBay | null = null;
  /** Where the aircraft is for the listener: pan, distance, closing speed (for Doppler). */
  listener = { pan: 0, dist: 100, closing: 0 };
  private lastDist = -1;
  loaded = false;

  constructor(private host: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.6));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    host.appendChild(this.renderer.domElement);
    this.scene.fog = new THREE.FogExp2(SKY.horizon.getHex(), FOG_D * 0.85);

    const sun = new THREE.Vector3(-0.62, 0.32, -0.52).normalize();

    // sky dome
    const sky = new THREE.Mesh(new THREE.SphereGeometry(30000, 32, 16), new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: { uTop: { value: SKY.top }, uHorizon: { value: SKY.horizon }, uSun: { value: sun } },
      vertexShader: 'varying vec3 vDir; void main(){ vDir = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: skyFrag,
    }));
    sky.renderOrder = -1;
    this.scene.add(sky);

    // terrain
    const SEG = 400;
    const geo = new THREE.PlaneGeometry(EXTENT, EXTENT, SEG, SEG);
    geo.rotateX(-Math.PI / 2);
    const pos = geo.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < pos.count; i++) pos.setY(i, terrainHeight(pos.getX(i), pos.getZ(i)));
    geo.computeVertexNormals();
    this.terrainMat = new THREE.ShaderMaterial({
      extensions: { derivatives: true } as never,
      uniforms: {
        uSun: { value: sun }, uFog: { value: SKY.horizon }, uFogD: { value: FOG_D },
        uRing: { value: new THREE.Vector3(0, 0, 0) }, uRingA: { value: 0 }, uRingCol: { value: CYAN }, uTime: { value: 0 },
      },
      vertexShader: terrainVert, fragmentShader: terrainFrag,
    });
    this.scene.add(new THREE.Mesh(geo, this.terrainMat));

    // light for the aircraft
    this.scene.add(new THREE.HemisphereLight(0xd6e8e2, 0x2b2c28, 1.1));
    const key = new THREE.DirectionalLight(0xffe2c0, 2.4); key.position.copy(sun).multiplyScalar(1000); this.scene.add(key);
    const pm = new THREE.PMREMGenerator(this.renderer);
    this.env = pm.fromScene(new RoomEnvironment(), 0.04).texture; pm.dispose();
    this.scene.environment = this.env;
    (this.scene as THREE.Scene & { environmentIntensity?: number }).environmentIntensity = 0.45;

    // airfields
    const runwayAt = (c: THREE.Vector3, dir: THREE.Vector3, len: number, id: string) => {
      const g = new THREE.Group(); g.position.copy(c); g.rotation.y = Math.atan2(dir.x, dir.z);
      const strip = new THREE.Mesh(new THREE.PlaneGeometry(26, len), new THREE.MeshBasicMaterial({ color: 0x1b2224 }));
      strip.rotation.x = -Math.PI / 2; g.add(strip);
      const lights: number[] = [];
      for (let z = -len / 2; z <= len / 2; z += 22) { lights.push(-14, 0.8, z, 14, 0.8, z); }
      for (let k = 1; k <= 7; k++) lights.push(0, 0.8, -len / 2 - k * 16);
      const lg = new THREE.BufferGeometry(); lg.setAttribute('position', new THREE.Float32BufferAttribute(lights, 3));
      g.add(new THREE.Points(lg, new THREE.PointsMaterial({ color: 0xbff6ff, size: 1.6, map: glowTexture(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })));
      this.scene.add(g);
      this.fieldPos.push({ id, p: c.clone().add(new THREE.Vector3(0, 6, 0)) });
    };
    // Thoise: at the end of the divert branch, aligned with the final approach
    runwayAt(THOISE_CENTRE.clone().setY(branchFloor(D_THRESHOLD + RUNWAY_LEN / 2) + RUNWAY_SURFACE), FINAL_DIR, RUNWAY_LEN, 'VI82');
    // Leh: further along the valley the aircraft was following
    {
      const c = path.getPointAt(wrap(S_LEH) / L); c.y = floorAt(S_LEH) + RUNWAY_SURFACE;
      const tan = path.getTangentAt(wrap(S_LEH) / L).setY(0).normalize();
      runwayAt(c, tan, RUNWAY_LEN, 'VILH');
    }
    const kg = KARGIL.clone(); kg.y = KARGIL_FLOOR + 6; this.fieldPos.push({ id: 'VIKG', p: kg });

    // glide footprint, centred where the decision is made
    const at = pointAt(T_ASSESS);
    this.ringCenter.set(at.x, at.z);
    const dT = Math.hypot(this.fieldPos[0].p.x - at.x, this.fieldPos[0].p.z - at.z);
    const dL = Math.hypot(this.fieldPos[1].p.x - at.x, this.fieldPos[1].p.z - at.z);
    this.ringR = Math.min(dT * 1.3, (dT + Math.max(dL, dT * 1.4)) / 2);

    // glide path: where the aircraft will actually go, dashed
    const gp: THREE.Vector3[] = [];
    for (let t = T_TURN; t <= T_TOUCH + ROLL; t += 0.1) gp.push(pointAt(t).add(new THREE.Vector3(0, -1, 0)));
    const gpg = new THREE.BufferGeometry().setFromPoints(gp);
    this.glidePathCount = gp.length;
    this.glidePath = new THREE.Line(gpg, new THREE.LineDashedMaterial({ color: 0xe9fbff, dashSize: 14, gapSize: 10, transparent: true, opacity: 0, depthWrite: false, fog: false }));
    this.glidePath.computeLineDistances();
    this.scene.add(this.glidePath);

    // light trail
    const N = 90;
    this.trailPos = new Float32Array(N * 2 * 3);
    this.trailAlpha = new Float32Array(N * 2);
    const idx: number[] = [];
    for (let i = 0; i < N - 1; i++) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
    const tg = new THREE.BufferGeometry();
    tg.setAttribute('position', new THREE.BufferAttribute(this.trailPos, 3));
    tg.setAttribute('alpha', new THREE.BufferAttribute(this.trailAlpha, 1));
    tg.setIndex(idx);
    this.trail = new THREE.Mesh(tg, new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending,
      uniforms: { uCol: { value: CYAN } },
      vertexShader: 'attribute float alpha; varying float vA; void main(){ vA = alpha; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: 'uniform vec3 uCol; varying float vA; void main(){ gl_FragColor = vec4(uCol, vA); }',
    }));
    this.trail.frustumCulled = false;
    this.scene.add(this.trail);

    // engine fault glow
    this.glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture(), color: 0xff4f8b, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0 }));
    this.glow.scale.setScalar(16);
    this.carrier.add(this.glow);

    this.scene.add(this.carrier);
    this.scene.add(this.ghost);
  }

  async loadAircraft() {
    const draco = new DRACOLoader();
    draco.setDecoderPath('/draco/');
    const loader = new GLTFLoader(); loader.setDRACOLoader(draco);
    // the bytes come from the preloader (already downloaded, with progress); fetch only if it failed
    const buf = await preloader.bytes('/models/uav_predator.glb');
    const gltf = buf ? await loader.parseAsync(buf, '/models/') : await loader.loadAsync('/models/uav_predator.glb');
    draco.dispose();
    const model = gltf.scene;
    // normalise: centre it, nose to +Z, ~30 units span
    const inner = new THREE.Group();
    inner.add(model);
    model.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(model);
    const size = box.getSize(new THREE.Vector3()), centre = box.getCenter(new THREE.Vector3());
    model.position.sub(centre);
    const scale = 30 / Math.max(size.x, size.z);
    inner.scale.setScalar(scale);
    this.carrier.add(inner);
    const len = size.z * scale;
    this.engineLocal.set(0, 0.6, -len * 0.42);
    this.glow.position.copy(this.engineLocal);
    this.carrier.updateMatrixWorld(true);
    // a sparse sample of the real hull, so the target box hugs the airframe from any angle
    const inv = new THREE.Matrix4().copy(this.carrier.matrixWorld).invert();
    const v = new THREE.Vector3();
    inner.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const pa = m.geometry.attributes.position as THREE.BufferAttribute;
      const step = Math.max(1, Math.floor(pa.count / 60));
      for (let i = 0; i < pa.count; i += step) { v.fromBufferAttribute(pa, i).applyMatrix4(m.matrixWorld).applyMatrix4(inv); this.hull.push(v.clone()); }
      // the airframe's own materials, made able to turn to X-ray on the approach to the nacelle
      const mats = Array.isArray(m.material) ? m.material : [m.material];
      mats.forEach((mt) => { if (mt && !this.bodyMats.includes(mt)) this.bodyMats.push(mt); });
    });

    // wheels: the lowest hull point near mid-fuselage is the main gear; the tail is checked separately
    const mid = this.hull.filter((q) => Math.abs(q.z) < len * 0.25);
    if (mid.length) GEAR = -Math.min(...mid.map((q) => q.y)) + 0.05;
    this.tailPts = this.hull.filter((q) => q.z < -len * 0.3);

    // the pusher propeller: a blurred disc while the engine runs, two still blades when it does not
    const tail = this.hull.filter((q) => q.z < -len * 0.45);
    const propZ = Math.min(...this.hull.map((q) => q.z)) - 0.25;
    const propY = tail.length ? tail.reduce((s2, q) => s2 + q.y, 0) / tail.length : 0;
    this.propLocal.set(0, propY, propZ);
    this.prop.position.copy(this.propLocal);
    const discTex = (() => {
      const c = document.createElement('canvas'); c.width = c.height = 256;
      const g = c.getContext('2d')!;
      const grad = g.createRadialGradient(128, 128, 14, 128, 128, 128);
      grad.addColorStop(0, 'rgba(40,44,46,0.0)'); grad.addColorStop(0.2, 'rgba(60,64,66,0.55)'); grad.addColorStop(0.92, 'rgba(70,74,76,0.35)'); grad.addColorStop(1, 'rgba(70,74,76,0)');
      g.fillStyle = grad; g.fillRect(0, 0, 256, 256);
      for (let i = 0; i < 2; i++) { g.save(); g.translate(128, 128); g.rotate(i * Math.PI); g.fillStyle = 'rgba(25,28,30,0.35)'; g.beginPath(); g.moveTo(0, 0); g.arc(0, 0, 124, -0.35, 0.35); g.fill(); g.restore(); }
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
    })();
    this.propDisc = new THREE.Mesh(new THREE.CircleGeometry(3.4, 48), new THREE.MeshBasicMaterial({ map: discTex, transparent: true, depthWrite: false, side: THREE.DoubleSide }));
    this.prop.add(this.propDisc);
    const bladeMat = new THREE.MeshStandardMaterial({ color: 0x2a2e30, roughness: 0.5, metalness: 0.3 });
    this.propBlades = new THREE.Group();
    for (const r0 of [0, Math.PI]) {
      const b0 = new THREE.Mesh(new THREE.BoxGeometry(0.42, 3.2, 0.1), bladeMat);
      b0.position.set(0, 1.6, 0); const piv = new THREE.Group(); piv.rotation.z = r0 + 0.5; piv.add(b0); this.propBlades.add(piv);
    }
    this.prop.add(this.propBlades);
    this.carrier.add(this.prop);

    // the twin: same airframe, drawn as a holographic shell
    const twin = inner.clone(true);
    twin.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const mat = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, uniforms: { uCol: { value: CYAN }, uA: { value: 0 }, uTime: { value: 0 } }, vertexShader: ghostVert, fragmentShader: ghostFrag });
      this.ghostMats.push(mat);
      m.material = mat;
    });
    twin.scale.multiplyScalar(1.015);
    this.ghost.add(twin);
    this.loaded = true;
  }

  /** The engine bay loads after the airframe; the film falls back to the Blender still if it is not ready. */
  async loadBay(map: ComponentMap) {
    const bay = new EngineBay(this.renderer);
    await bay.load(map);
    this.bay = bay;
  }

  resize() {
    const w = this.host.clientWidth, h = this.host.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    // keep the action framed on portrait screens
    this.camera.fov = w / h < 0.8 ? 62 : w / h < 1.2 ? 52 : 42;
    this.camera.updateProjectionMatrix();
  }

  /** Cut: the camera jumps instead of easing (used when the viewer skips between chapters). */
  cut() { this.hasCam = false; }

  private flashing(t: number) { return t >= FLASH.from && t < FLASH.to; }

  /** The flash-forward: the same aircraft, engine dead, gliding over a ridge with nothing below but rock. */
  private flashPose(t: number) {
    if (!this.flashBase) {
      const base = pointAt(FLASH.from);
      const tan = path.getTangentAt(wrap(sAt(FLASH.from)) / L).setY(0).normalize();
      const right = new THREE.Vector3().crossVectors(tan, UP).normalize();
      let best = base.clone(), bestH = -Infinity;
      for (let d = 420; d <= 1100; d += 40) for (const sd of [1, -1]) {
        const p = base.clone().addScaledVector(right, d * sd);
        const hgt = terrainHeight(p.x, p.z);
        if (hgt > bestH) { bestH = hgt; best = p; }
      }
      this.flashBase = { p: best.setY(bestH + 70), fwd: tan };
    }
    const u = (t - FLASH.from) / (FLASH.to - FLASH.from);
    const pos = this.flashBase.p.clone().addScaledVector(this.flashBase.fwd, 70 * u * (FLASH.to - FLASH.from)).add(new THREE.Vector3(0, -9 * u, 0));
    return { pos, fwd: this.flashBase.fwd.clone().add(new THREE.Vector3(0, -0.08, 0)).normalize(), bank: 0.06 };
  }

  private placeAircraft(t: number) {
    const fl = this.flashing(t);
    const { pos, fwd, bank } = fl ? this.flashPose(t) : pose(t);
    const up = new THREE.Vector3(0, 1, 0);
    const left = new THREE.Vector3().crossVectors(up, fwd).normalize();
    const realUp = new THREE.Vector3().crossVectors(fwd, left).normalize();
    const m = new THREE.Matrix4().makeBasis(left, realUp, fwd);
    this.carrier.position.copy(pos);
    this.carrier.quaternion.setFromRotationMatrix(m);
    this.carrier.rotateZ(bank);
    if (!fl) this.carrier.rotateX(-pitchAt(t)); // nose up on approach, in the flare and until the nose wheel is down
    // with the nose up near the ground, keep the tail (and its ventral fin) off the runway
    if (!fl && t > T_FLARE - 1 && this.tailPts.length) {
      this.carrier.updateMatrixWorld(true);
      const v = new THREE.Vector3();
      let low = Infinity;
      for (const q of this.tailPts) low = Math.min(low, v.copy(q).applyMatrix4(this.carrier.matrixWorld).y);
      const runway = groundAt(t) + RUNWAY_SURFACE + 0.15; // the strip under the aircraft
      if (low < runway) this.carrier.position.y += runway - low;
    }
    return { pos, fwd, left };
  }

  private rig(t: number, real: number, pos: THREE.Vector3, fwdIn: THREE.Vector3) {
    const fwd = fwdIn.clone(); fwd.y = 0; fwd.normalize();
    const right = new THREE.Vector3().crossVectors(fwd, new THREE.Vector3(0, 1, 0)).normalize();
    const Y = new THREE.Vector3(0, 1, 0);
    const at = (f: number, r: number, y: number) => pos.clone().addScaledVector(fwd, f).addScaledVector(right, r).addScaledVector(Y, y);
    const ci = (() => { let i = 0; while (i < STARTS.length - 1 && t >= STARTS[i + 1]) i++; return i; })();
    const k = Math.min(1, Math.max(0, (t - STARTS[ci]) / CHAPTERS[ci].dur));
    const e = sstep(0, 1, k);
    const prop = this.carrier.localToWorld(this.propLocal.clone());
    const engine = this.carrier.localToWorld(this.engineLocal.clone());
    // the decision's high map view: the whole footprint, the aircraft and every field in it
    const mapView = () => {
      const tf = this.fieldPos[0].p;
      const c = new THREE.Vector3(this.ringCenter.x, pos.y, this.ringCenter.y);
      const toField = new THREE.Vector3(tf.x - c.x, 0, tf.z - c.z).normalize();
      return {
        cam: c.clone().addScaledVector(toField, -this.ringR * 0.9).add(new THREE.Vector3(0, this.ringR * 1.05, 0)),
        look: c.clone().addScaledVector(toField, this.ringR * 0.22),
      };
    };
    let cam: THREE.Vector3, look: THREE.Vector3;
    if (this.flashing(t)) {
      // the flash-forward: low and behind, the dead aircraft against the sky over bare rock
      const fp = this.flashPose(t);
      const fr = new THREE.Vector3().crossVectors(fp.fwd, Y).normalize();
      cam = fp.pos.clone().addScaledVector(fp.fwd, -62).addScaledVector(fr, -26).add(new THREE.Vector3(0, -10, 0));
      look = fp.pos.clone().addScaledVector(fp.fwd, 25).add(new THREE.Vector3(0, 4, 0));
      return { cam, look };
    }
    switch (CHAPTERS[ci].id) {
      case 'cold': {
        // the hub, then one unbroken pull-back: aircraft, valley, range
        const pull = sstep(0.1, 0.95, k);
        const d = 7 * Math.pow(200, pull);
        const dir = fwd.clone().negate().addScaledVector(right, 0.42).addScaledVector(Y, 0.1 + 0.55 * pull).normalize();
        cam = prop.clone().addScaledVector(dir, d);
        look = prop.clone().lerp(at(260, 0, 30), 0.55 * pull);
        break;
      }
      case 'problem':
        cam = at(-74 + 18 * e, 28 - 10 * e, 18 - 4 * e);
        look = at(40, 0, 4);
        break;
      case 'twin':
        cam = at(-56 + 6 * e, 22 - 6 * e, 12);
        look = at(28, 0, 2);
        break;
      case 'approach': {
        // along the fuselage to the nacelle, closing until the lens is inside the cowling
        const r1 = sstep(0, 0.42, k), r2 = sstep(0.42, 0.96, k);
        const chase = at(-50, 16, 12);
        const side = at(4, 12, 4.5);
        const into = engine.clone().addScaledVector(right, 2.2).add(new THREE.Vector3(0, 1.0, 0)).addScaledVector(fwd, 0.6);
        cam = chase.lerp(side, r1).lerp(into, r2);
        look = at(6, 0, 0.5).lerp(engine, Math.max(0.4 * r1, r2));
        break;
      }
      case 'inside':
      case 'signal':
        cam = engine.clone().addScaledVector(right, 2).add(new THREE.Vector3(0, 1, 0));
        look = engine.clone();
        break;
      case 'pipeline':
      case 'memory':
        cam = at(-120 + 20 * e, 46 - 12 * e, 40 - 8 * e);
        look = at(90, 0, 0);
        break;
      case 'detect':
        if (t < T_CONFIRM) { cam = at(-110 + 14 * e, 40 - 8 * e, 34); look = at(90, 0, 0); }
        else { const e2 = sstep(T_CONFIRM, T_CONFIRM + 5, t); cam = at(62 - 12 * e2, 28 - 4 * e2, 7); look = at(0, 0, 0); }
        break;
      case 'decide': {
        // close on the aircraft while the options arrive, then up until the terrain becomes a map
        const a = 0.9 + 0.9 * sstep(0, 0.35, k);
        const close = at(Math.cos(a) * 60, Math.sin(a) * 60, 14);
        const mv = mapView();
        const r = sstep(0.33, 0.62, k);
        cam = close.lerp(mv.cam, r);
        look = pos.clone().lerp(mv.look, r);
        break;
      }
      case 'divert': {
        // down from the map into a three-quarter chase as the aircraft banks onto the new heading
        const mv = mapView();
        const r = sstep(0.0, 0.55, k);
        cam = mv.cam.clone().lerp(at(-66, -30, 20), r);
        look = mv.look.clone().lerp(at(70, 0, 0), r);
        break;
      }
      case 'beyond': {
        const end = new THREE.Vector3(); pointAt(TOTAL, end);
        const a = 0.6 + real * 0.03;
        cam = end.clone().add(new THREE.Vector3(Math.cos(a) * (90 + 260 * e), 22 + 420 * e, Math.sin(a) * (90 + 260 * e)));
        look = end.clone();
        break;
      }
      default: { // land: one continuous shot, approach to roll-out, stopping beside the runway
        const tf = this.fieldPos[0].p;
        const end = new THREE.Vector3(); pointAt(T_TOUCH + ROLL, end);
        const chase = at(-60, 16, 15);
        const hold = end.clone().addScaledVector(right, 70).addScaledVector(fwd, 55).add(new THREE.Vector3(0, 16, 0));
        const r = sstep(0.45, 0.85, k);
        cam = chase.lerp(hold, r);
        look = pos.clone().lerp(tf, 0.15 * (1 - r));
        break;
      }
    }
    // never put the lens inside a mountain
    const floor = terrainHeight(cam.x, cam.z) + 12;
    if (cam.y < floor && CHAPTERS[ci].id !== 'approach' && CHAPTERS[ci].id !== 'cold') cam.y = floor;
    return { cam, look };
  }

  /** Render one frame at story time t. `real` is wall-clock seconds for idle motion. */
  frame(t: number, real: number, dt: number): Screen {
    const fl = this.flashing(t);
    if (fl !== this.wasFlash) { this.wasFlash = fl; this.hasCam = false; } // the flash-forward is a cut, in and out
    const { pos, fwd } = this.placeAircraft(t);
    const r = readout(t);
    const ci = CHAPTERS.findIndex((_c, i) => t >= STARTS[i] && (i === STARTS.length - 1 || t < STARTS[i + 1]));
    const id = CHAPTERS[ci].id;
    const kc = (t - STARTS[ci]) / CHAPTERS[ci].dur;

    // the propeller: running (blurred disc) everywhere except the flash-forward, slower once power comes back
    if (this.propDisc && this.propBlades) {
      this.propDisc.visible = !fl; this.propBlades.visible = fl;
      if (!fl) this.propDisc.rotation.z = real * (t > T_GLIDE ? 9 : 14);
    }

    // the twin: slides in, locks on, glows as the camera approaches the nacelle, fades once the crew has its answer
    const tIn = startOf('twin');
    const show = fl ? 0 : sstep(tIn + 0.2, tIn + 2.2, t) * (1 - sstep(T_DECIDE, T_DECIDE + 3, t));
    const dock = 1 - sstep(tIn + 0.8, tIn + 4.2, t);
    const nacelle = id === 'approach' ? sstep(0.25, 0.7, kc) : 0;
    this.ghost.position.copy(this.carrier.position);
    this.ghost.quaternion.copy(this.carrier.quaternion);
    this.ghost.translateX(18 * dock); this.ghost.translateY(6 * dock);
    for (const m of this.ghostMats) { m.uniforms.uA.value = show * (0.85 - 0.25 * r.sev + 0.9 * nacelle); m.uniforms.uTime.value = real; m.uniforms.uCol.value = CYAN; }
    this.ghost.visible = show > 0.001 && this.loaded;
    // the skin turns to X-ray as the lens nears the engine
    const xr = id === 'approach' ? sstep(0.35, 0.78, kc) : 0;
    if (Math.abs(xr - this.xray) > 1e-3) {
      this.xray = xr;
      for (const mt of this.bodyMats) { mt.transparent = xr > 0.001; mt.opacity = 1 - 0.85 * xr; mt.depthWrite = xr < 0.5; mt.needsUpdate = true; }
    }

    // engine glow: amber while drifting, alarm rose once confirmed
    const pulse = 0.6 + 0.4 * Math.sin(real * (r.confirmed ? 9 : 5));
    const gm = this.glow.material as THREE.SpriteMaterial;
    gm.opacity = fl ? 0 : Math.min(1, r.sev * 1.8) * pulse * (t < T_TOUCH + ROLL ? 1 : 0.4);
    gm.color.set(r.confirmed ? 0xff3d7f : 0xffb347);

    // trail
    this.trail.visible = !fl;
    const N = this.trailAlpha.length / 2;
    const p = new THREE.Vector3(), q = new THREE.Vector3(), side = new THREE.Vector3();
    for (let i = 0; i < N; i++) {
      const ti = t - i * 0.075;
      pointAt(Math.max(0, ti), p); pointAt(Math.max(0, ti) + 0.05, q);
      side.subVectors(q, p).cross(new THREE.Vector3(0, 1, 0)).normalize().multiplyScalar(1.7 * (1 - i / N) + 0.3);
      p.addScaledVector(fwd, -9).y -= 1.2;
      this.trailPos.set([p.x - side.x, p.y, p.z - side.z, p.x + side.x, p.y, p.z + side.z], i * 6);
      const a = Math.pow(1 - i / N, 1.6) * 0.75 * (ti > 0 ? 1 : 0) * (t < T_TOUCH - 0.5 ? 1 : Math.max(0, 1 - (t - T_TOUCH + 0.5) / 2));
      this.trailAlpha[i * 2] = a; this.trailAlpha[i * 2 + 1] = a;
    }
    (this.trail.geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    (this.trail.geometry.attributes.alpha as THREE.BufferAttribute).needsUpdate = true;

    // the assessment: the footprint sweeps out like a radar return; then the new route draws itself
    const g = sstep(T_ASSESS, T_ASSESS + 2.6, t);
    this.terrainMat.uniforms.uRing.value.set(this.ringCenter.x, this.ringCenter.y, this.ringR * g);
    this.terrainMat.uniforms.uRingA.value = g > 0 ? Math.min(1, g * 1.5) * (1 - 0.6 * sstep(T_TOUCH, T_TOUCH + 3, t)) : 0;
    this.terrainMat.uniforms.uTime.value = real;
    const routeShown = sstep(T_DECIDE + 11.2, T_TURN + 1.2, t);
    this.glidePath.geometry.setDrawRange(0, Math.floor(this.glidePathCount * routeShown));
    (this.glidePath.material as THREE.LineDashedMaterial).opacity = routeShown > 0 ? 0.9 * (1 - sstep(T_TOUCH - 1, T_TOUCH, t)) : 0;

    // camera: eases between shots, snaps on a cut
    const { cam, look } = this.rig(t, real, pos, fwd);
    if (!this.hasCam) { this.camPos.copy(cam); this.camLook.copy(look); this.hasCam = true; }
    const kk = 1 - Math.exp(-dt * (id === 'approach' || id === 'cold' ? 6 : 2.6));
    this.camPos.lerp(cam, kk); this.camLook.lerp(look, Math.min(1, kk * 1.6));
    this.camera.position.copy(this.camPos);
    this.camera.lookAt(this.camLook);
    // a handheld breath on every shot, and a jolt when the film cuts back from the ground station to the lock
    const hit = (at: number, len: number) => (t >= at && t < at + len ? Math.pow(1 - (t - at) / len, 2) : 0);
    const kick = 0.6 * hit(T_CONFIRM, 0.8);
    const breath = id === 'cold' || id === 'approach' ? 0.04 : 0.12;
    const n = (f: number, s2: number) => Math.sin(real * f + s2) * 0.6 + Math.sin(real * f * 2.3 + s2 * 1.7) * 0.4;
    const reach = this.camPos.distanceTo(this.camLook) * 0.006;
    this.camera.translateX(n(1.3, 1) * reach * breath + n(37, 2) * reach * kick * 1.6);
    this.camera.translateY(n(1.1, 3) * reach * breath + n(41, 4) * reach * kick * 1.6);
    this.camera.rotateZ(n(0.7, 5) * 0.004 + n(29, 6) * 0.012 * kick);
    let bay: BayFrame | null = null;
    if ((id === 'inside' || id === 'signal') && this.bay?.loaded) {
      bay = this.bay.film(id === 'inside' ? 'reveal' : 'signal', kc, r.sev, real, this.host.clientWidth, this.host.clientHeight);
    } else {
      this.renderer.render(this.scene, this.camera);
    }

    // the listener: pan from the aircraft's place in frame, distance, and closing speed for Doppler
    {
      const rel = this.carrier.position.clone().applyMatrix4(this.camera.matrixWorldInverse);
      const dist = rel.length();
      this.listener.pan = Math.max(-1, Math.min(1, rel.x / Math.max(20, -rel.z)));
      this.listener.closing = this.lastDist >= 0 && dt > 0 ? (this.lastDist - dist) / dt : 0;
      this.listener.dist = dist;
      this.lastDist = dist;
    }
    // project overlays
    const w = this.host.clientWidth, h = this.host.clientHeight;
    let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9, on = this.loaded;
    const c = new THREE.Vector3();
    if (!this.hull.length) on = false;
    for (const hp of this.hull) {
      c.copy(hp).applyMatrix4(this.carrier.matrixWorld).project(this.camera);
      if (c.z > 1) on = false;
      const x = (c.x * 0.5 + 0.5) * w, y = (-c.y * 0.5 + 0.5) * h;
      minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y);
    }
    c.copy(this.carrier.position).project(this.camera);
    const aircraft = { x: (c.x * 0.5 + 0.5) * w, y: (-c.y * 0.5 + 0.5) * h, on: c.z < 1 && !bay };
    const fields = this.fieldPos.map(({ id: fid, p: fp }) => {
      c.copy(fp).project(this.camera);
      return { id: fid, x: (c.x * 0.5 + 0.5) * w, y: (-c.y * 0.5 + 0.5) * h, on: c.z < 1 && Math.abs(c.x) < 1.1 && Math.abs(c.y) < 1.1 };
    });
    // keep the box (and its tag) inside the frame; drop it when the aircraft fills the screen
    const m = 12;
    minX = Math.max(m, minX); minY = Math.max(m, minY); maxX = Math.min(w - m, maxX); maxY = Math.min(h - 40, maxY);
    if (maxX - minX > w * 0.7 || maxX <= minX || maxY <= minY) on = false;
    if (bay || fl) on = false;
    return { box: { x: minX, y: minY, w: maxX - minX, h: maxY - minY, on }, fields, bay, aircraft, flash: fl };
  }

  dispose() {
    this.scene.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.geometry) m.geometry.dispose();
      const mat = m.material as THREE.Material | THREE.Material[] | undefined;
      if (Array.isArray(mat)) mat.forEach((x) => x.dispose()); else mat?.dispose();
    });
    this.env?.dispose();
    this.bay?.dispose();
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}
