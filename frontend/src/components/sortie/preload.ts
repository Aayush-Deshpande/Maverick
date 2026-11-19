// Loads everything the landing film needs before the site is shown, with byte-level progress and an
// estimated time left. Downloaded bytes are kept and handed to the 3D loaders, so nothing is fetched twice.
// Work that is not a download (building the terrain, compiling shaders, training the reservoir readout)
// is tracked as steps reported by the film.

export interface Task {
  id: string;
  label: string;
  detail: string;
  kind: 'bytes' | 'step';
  loaded: number;
  total: number;
  done: boolean;
  failed: boolean;
}

/** Downloads, with the size each is expected to be (used for the estimate until the server says). */
const DOWNLOADS: Array<{ id: string; url: string; label: string; bytes: number }> = [
  { id: 'airframe', url: '/models/uav_predator.glb', label: 'Airframe', bytes: 1_045_396 },
  { id: 'engine', url: '/models/rotax_912is.glb', label: 'Rotax 912 iS CAD, 109 components', bytes: 7_665_636 },
  { id: 'draco', url: '/draco/draco_decoder.wasm', label: 'Geometry decoder', bytes: 283_091 },
  { id: 'dracojs', url: '/draco/draco_wasm_wrapper.js', label: 'Geometry decoder runtime', bytes: 59_033 },
  { id: 'map', url: '/twin/component_map.json', label: 'Component map', bytes: 18_000 },
  { id: 'insert', url: '/survey/insert-confirm.mp4', label: 'Ground-station recording', bytes: 42_775 },
  { id: 'blender', url: '/survey/blender/rotax_912is_oil_pressure_loss.webp', label: 'Blender render', bytes: 127_136 },
  { id: 'blender2', url: '/survey/blender/rotax_912is_nominal.webp', label: 'Blender render', bytes: 48_848 },
];

/** Non-download steps and roughly how long each takes on a mid-range laptop (seconds), for the estimate. */
const STEPS: Array<{ id: string; label: string; seconds: number }> = [
  { id: 'scene', label: 'Building the terrain and compiling shaders', seconds: 0.8 },
  { id: 'aircraft', label: 'Decoding the airframe', seconds: 0.3 },
  { id: 'bay', label: 'Decoding the engine assembly', seconds: 0.8 },
  { id: 'reservoir', label: 'Training the reservoir readout', seconds: 1.0 },
  { id: 'fonts', label: 'Typefaces', seconds: 0.2 },
];

type Listener = () => void;

class Preloader {
  tasks: Task[] = [];
  private buffers = new Map<string, Promise<ArrayBuffer | null>>();
  private listeners = new Set<Listener>();
  private started = false;
  private startAt = 0;
  private rate = 0; // smoothed bytes per second
  private lastBytes = 0;
  private lastAt = 0;

  constructor() {
    this.tasks = [
      ...DOWNLOADS.map((d) => ({ id: d.id, label: d.label, detail: d.url.split('/').pop() ?? d.url, kind: 'bytes' as const, loaded: 0, total: d.bytes, done: false, failed: false })),
      ...STEPS.map((s) => ({ id: s.id, label: s.label, detail: '', kind: 'step' as const, loaded: 0, total: 1, done: false, failed: false })),
    ];
  }

  start() {
    if (this.started) return;
    this.started = true;
    this.startAt = this.lastAt = performance.now();
    for (const d of DOWNLOADS) this.buffers.set(d.url, this.fetchOne(d.id, d.url));
    (document.fonts?.ready ?? Promise.resolve()).then(() => this.step('fonts'), () => this.step('fonts'));
  }

  private async fetchOne(id: string, url: string): Promise<ArrayBuffer | null> {
    const task = this.tasks.find((t) => t.id === id)!;
    try {
      const res = await fetch(url);
      if (!res.ok || !res.body) throw new Error(String(res.status));
      const len = Number(res.headers.get('content-length'));
      if (len > 0) task.total = len;
      const reader = res.body.getReader();
      const chunks: Uint8Array[] = [];
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        task.loaded += value.byteLength;
        if (task.loaded > task.total) task.total = task.loaded;
        this.emit();
      }
      const out = new Uint8Array(task.loaded);
      let o = 0; for (const c of chunks) { out.set(c, o); o += c.byteLength; }
      task.done = true; task.total = task.loaded;
      this.emit();
      return out.buffer;
    } catch {
      task.failed = true; task.done = true;
      this.emit();
      return null;
    }
  }

  /** The downloaded bytes for a URL (waits for the download), or null if it failed or was not preloaded. */
  bytes(url: string) { return this.buffers.get(url) ?? Promise.resolve(null); }

  step(id: string, failed = false) {
    const t = this.tasks.find((x) => x.id === id);
    if (!t || t.done) return;
    t.done = true; t.loaded = 1; t.failed = failed;
    this.emit();
  }

  subscribe(fn: Listener) { this.listeners.add(fn); return () => { this.listeners.delete(fn); }; }
  private emit() { this.listeners.forEach((fn) => fn()); }

  get ready() { return this.tasks.every((t) => t.done); }
  get anyFailed() { return this.tasks.some((t) => t.failed); }

  /** Overall progress 0..1, bytes and an estimate of seconds left (null until there is a rate to go on). */
  summary() {
    const dl = this.tasks.filter((t) => t.kind === 'bytes');
    const loaded = dl.reduce((s, t) => s + t.loaded, 0);
    const total = dl.reduce((s, t) => s + t.total, 0);
    const now = performance.now();
    const dt = (now - this.lastAt) / 1000;
    if (dt > 0.25) {
      const inst = (loaded - this.lastBytes) / dt;
      this.rate = this.rate ? 0.7 * this.rate + 0.3 * inst : inst;
      this.lastBytes = loaded; this.lastAt = now;
    }
    const stepLeft = STEPS.filter((s) => !this.tasks.find((t) => t.id === s.id)!.done).reduce((s, x) => s + x.seconds, 0);
    const bytesLeft = total - loaded;
    const elapsed = (now - this.startAt) / 1000;
    const haveRate = this.rate > 1000 && elapsed > 0.6;
    const eta = bytesLeft <= 0 ? stepLeft : haveRate ? bytesLeft / this.rate + stepLeft : null;
    const stepsDone = this.tasks.filter((t) => t.kind === 'step' && t.done).length;
    const progress = 0.85 * (total ? loaded / total : 1) + 0.15 * (stepsDone / STEPS.length);
    return { progress: this.ready ? 1 : Math.min(0.995, progress), loaded, total, eta, rate: this.rate, elapsed };
  }
}

export const preloader = new Preloader();
