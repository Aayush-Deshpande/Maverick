// Frame-synced cinema stem player using decoded Web Audio buffers.
// Locks 4 mastered music stems to story time (t), handles play/pause/scrubbing
// with automatic drift correction, enforces the t=91.95s hard silence gate,
// and falls back silently to procedural score.ts if any audio file is missing.
import { T_TOUCH, TOTAL } from './story';
import { T_CONFIRM } from './timeline';

export interface StemDef {
  id: string;
  url: string;
  start: number;
  end: number;
  fadeIn: number;
  fadeOut: number;
  gain: number;
}

const STEMS: StemDef[] = [
  { id: 'cold_twin',        url: '/audio/01_cold_twin.mp3',        start: 0.0,             end: 62.0,         fadeIn: 1.2,  fadeOut: 1.0,  gain: 0.82 },
  { id: 'fault_detect',     url: '/audio/02_fault_detect.mp3',     start: 62.0,            end: T_CONFIRM,    fadeIn: 0.2,  fadeOut: 0.02, gain: 0.85 },
  { id: 'memory_divert',    url: '/audio/03_memory_divert.mp3',    start: T_CONFIRM + 1.4, end: T_TOUCH,      fadeIn: 0.85, fadeOut: 0.5,  gain: 0.84 },
  { id: 'touchdown_beyond', url: '/audio/04_touchdown_beyond.mp3', start: T_TOUCH,         end: TOTAL + 4.0,  fadeIn: 0.1,  fadeOut: 2.0,  gain: 0.86 },
];

export class StemPlayer {
  private buffers = new Map<string, AudioBuffer>();
  private out: GainNode;
  private activeId: string | null = null;
  private activeSrc: AudioBufferSourceNode | null = null;
  private activeGain: GainNode | null = null;
  private startedAtCtx = 0;
  private startedAtStory = 0;
  private disposed = false;

  constructor(private ctx: AudioContext, dest: AudioNode) {
    this.out = ctx.createGain();
    this.out.gain.value = 1;
    this.out.connect(dest);
    void this.preloadAll();
  }

  private async preloadAll() {
    await Promise.all(
      STEMS.map(async (stem) => {
        try {
          const res = await fetch(stem.url);
          if (!res.ok) return;
          const arr = await res.arrayBuffer();
          if (this.disposed) return;
          const buf = await this.ctx.decodeAudioData(arr);
          if (!this.disposed) this.buffers.set(stem.id, buf);
        } catch {
          // File not placed yet or offline: silently fall back to procedural score.ts
        }
      })
    );
  }

  private findStem(t: number): StemDef | null {
    // Hard silence window between gate lock (T_CONFIRM) and reservoir bloom (T_CONFIRM + 1.4)
    if (t >= T_CONFIRM && t < T_CONFIRM + 1.4) return null;
    for (const s of STEMS) {
      if (t >= s.start && t < s.end) return s;
    }
    return null;
  }

  /** Returns true if a mastered audio file is loaded for the current timestamp. */
  hasStemAt(t: number): boolean {
    const stem = this.findStem(t);
    return !!stem && this.buffers.has(stem.id);
  }

  private stopActive(fadeSec = 0.06) {
    if (!this.activeSrc || !this.activeGain) return;
    const now = this.ctx.currentTime;
    const src = this.activeSrc;
    const g = this.activeGain;
    this.activeSrc = null;
    this.activeGain = null;
    this.activeId = null;

    g.gain.cancelScheduledValues(now);
    g.gain.setValueAtTime(Math.max(0.0001, g.gain.value), now);
    g.gain.linearRampToValueAtTime(0.0001, now + Math.max(0.015, fadeSec));
    try {
      src.stop(now + Math.max(0.02, fadeSec) + 0.02);
    } catch {
      // Already stopped
    }
  }

  private startStem(stem: StemDef, t: number, duck: number) {
    const buf = this.buffers.get(stem.id);
    if (!buf) return;
    const offset = Math.max(0, t - stem.start);
    if (offset >= buf.duration - 0.05) return;

    const now = this.ctx.currentTime;
    const src = this.ctx.createBufferSource();
    src.buffer = buf;

    const g = this.ctx.createGain();
    const targetGain = stem.gain * (1 - 0.62 * duck);
    const fade = offset < 0.25 ? stem.fadeIn : 0.08;
    g.gain.setValueAtTime(0.0001, now);
    g.gain.linearRampToValueAtTime(targetGain, now + fade);

    src.connect(g).connect(this.out);
    src.start(now, offset);

    this.activeId = stem.id;
    this.activeSrc = src;
    this.activeGain = g;
    this.startedAtCtx = now;
    this.startedAtStory = t;
  }

  /** Called every animation frame from SortieSound.update(). */
  update(t: number, playing: boolean, duck: number, flash: boolean) {
    if (!playing || flash || this.ctx.state !== 'running') {
      this.stopActive(0.06);
      return;
    }

    const stem = this.findStem(t);
    if (!stem || !this.buffers.has(stem.id)) {
      // Hard cut if entering the T_CONFIRM silence window
      const inSilence = t >= T_CONFIRM && t < T_CONFIRM + 1.4;
      this.stopActive(inSilence ? 0.015 : 0.25);
      return;
    }

    const now = this.ctx.currentTime;

    if (this.activeId !== stem.id) {
      this.stopActive(stem.fadeOut);
      this.startStem(stem, t, duck);
      return;
    }

    // Drift / scrub detection: re-lock if timeline jumped by > 120 ms
    const expectedT = this.startedAtStory + (now - this.startedAtCtx);
    if (Math.abs(expectedT - t) > 0.12) {
      this.stopActive(0.04);
      this.startStem(stem, t, duck);
      return;
    }

    // Smoothly track engine-bay ducking and end-of-stem fade-out
    if (this.activeGain) {
      const rem = stem.end - t;
      const tail = rem < stem.fadeOut ? Math.max(0, rem / Math.max(0.02, stem.fadeOut)) : 1;
      const target = Math.max(0.0001, stem.gain * (1 - 0.62 * duck) * tail);
      this.activeGain.gain.setTargetAtTime(target, now, 0.12);
    }
  }

  dispose() {
    this.disposed = true;
    this.stopActive(0.02);
    this.buffers.clear();
  }
}
