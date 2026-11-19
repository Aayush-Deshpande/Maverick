// The film's score, synthesised: a pipe organ (8', 4', 2 2/3', 2' ranks, chiff, tremulant), a string section,
// a spiccato ostinato, low brass, and FM bells, in D minor, scheduled ahead on the audio clock against story
// time. The harmony follows the argument: a drone while the twin is calm, a dissonant cluster when the fault
// enters, the dominant held under the drift and the detector, silence when the gate fires and then the full
// chord, a minor-second rub while the forest names the wrong fault, a bright fifth when the open tier flags it,
// the progression for the glide, and F major at touchdown.
import { CHAPTERS, STARTS, T_INJECT, T_TOUCH, TOTAL, type ChapterId } from './story';
import { T_CONFIRM } from './timeline';

const mtof = (m: number) => 440 * Math.pow(2, (m - 69) / 12);
const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

// voicings (MIDI)
const CH = {
  Dm: [38, 50, 57, 62, 65], Bb: [34, 46, 53, 58, 62], F: [41, 48, 57, 60, 65], C: [36, 48, 55, 60, 64],
  Gm: [43, 50, 55, 58, 62], A: [45, 52, 57, 61, 64], Dsus: [38, 50, 57, 62, 64], Fmaj: [41, 53, 57, 60, 65, 69],
  Dm9: [38, 50, 57, 64, 65, 69],
};
type Chord = keyof typeof CH;
/** D natural minor, two octaves from D4, for bells and the ostinato. */
const SCALE = [62, 64, 65, 67, 69, 70, 72, 74, 76, 77, 79, 81];
const OSTINATO = [62, 57, 62, 65, 62, 57, 64, 65];

interface Cue { chords: Chord[]; bar: number; organ: number; strings: number; ostinato: number; density: 1 | 2; bpm: number; register: 'soft' | 'full' | 'bright' }
const CUES: Record<ChapterId, Cue> = {
  open:     { chords: ['Dm'], bar: 8, organ: 0.5, strings: 0, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  twin:     { chords: ['Dm', 'Bb'], bar: 3.5, organ: 0.55, strings: 0.3, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  inside:   { chords: ['Dm', 'Dsus'], bar: 6.5, organ: 0.3, strings: 0.25, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  pipeline: { chords: ['Dm', 'F', 'C', 'Bb'], bar: 3.75, organ: 0.45, strings: 0.3, ostinato: 0.5, density: 1, bpm: 96, register: 'soft' },
  drift:    { chords: ['Dm', 'Bb', 'Gm', 'A'], bar: 1.75, organ: 0.5, strings: 0.45, ostinato: 0.65, density: 2, bpm: 96, register: 'soft' },
  detect:   { chords: ['A'], bar: 6, organ: 0.55, strings: 0.55, ostinato: 0.8, density: 2, bpm: 108, register: 'full' },
  memory:   { chords: ['Dm9'], bar: 11, organ: 0.35, strings: 0.3, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  unseen:   { chords: ['Dm', 'Gm'], bar: 7.5, organ: 0.35, strings: 0.4, ostinato: 0.35, density: 1, bpm: 84, register: 'soft' },
  decide:   { chords: ['Dm', 'Bb'], bar: 4, organ: 0.4, strings: 0.35, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  glide:    { chords: ['Dm', 'Bb', 'F', 'C'], bar: 2.25, organ: 0.75, strings: 0.65, ostinato: 0.4, density: 1, bpm: 80, register: 'full' },
  land:     { chords: ['Dm', 'Bb', 'F', 'C'], bar: 2.5, organ: 0.6, strings: 0.55, ostinato: 0, density: 1, bpm: 80, register: 'full' },
};

export interface ScoreState {
  t: number;
  ci: number;
  playing: boolean;
  /** pipeline packet position 0..12 */
  stage: number | null;
  /** FlyHash units newly firing this frame */
  newWinners: number[];
  /** Never seen: whether the open tier is flagging, and the forest's top probability */
  unseen: { abnormal: boolean; forestTop: number } | null;
  /** reservoir node activations (Memory) */
  memory: Float32Array | null;
  /** 0..1, how far the music should sit under other sound (engine bay) */
  duck: number;
}

export class Score {
  private out: GainNode;
  private organBus: GainNode;
  private stringBus: GainNode;
  private trem: GainNode;
  private schedT = -1;
  private lastStage = -1;
  private flagged = false;
  private lastTension = -1;
  private memVoices: Array<{ g: GainNode }> = [];
  private memBus: GainNode;
  private rub: GainNode;

  constructor(private ctx: AudioContext, dest: AudioNode, space: AudioNode, private noise: AudioBuffer) {
    this.out = ctx.createGain(); this.out.gain.value = 0.9;
    this.out.connect(dest);
    const send = ctx.createGain(); send.gain.value = 0.85; this.out.connect(send).connect(space);
    // organ with a tremulant on its whole bus
    this.trem = ctx.createGain(); this.trem.gain.value = 1;
    const lfo = ctx.createOscillator(); lfo.frequency.value = 5.2;
    const depth = ctx.createGain(); depth.gain.value = 0.035; lfo.connect(depth).connect(this.trem.gain); lfo.start();
    this.organBus = ctx.createGain(); this.organBus.gain.value = 0;
    this.organBus.connect(this.trem).connect(this.out);
    const sl = ctx.createBiquadFilter(); sl.type = 'lowpass'; sl.frequency.value = 2400; sl.Q.value = 0.4;
    this.stringBus = ctx.createGain(); this.stringBus.gain.value = 0;
    this.stringBus.connect(sl).connect(this.out);
    // memory: eight held organ pipes on a Dm9, each loudness following one reservoir node
    this.memBus = ctx.createGain(); this.memBus.gain.value = 0; this.memBus.connect(this.out);
    [50, 53, 57, 60, 64, 65, 69, 74].forEach((m, i) => {
      const g = ctx.createGain(); g.gain.value = 0;
      for (const [h, v] of [[1, 1], [2, 0.4], [3, 0.15]] as const) {
        const o = ctx.createOscillator(); o.frequency.value = mtof(m) * h; o.detune.value = (i % 2 ? 3 : -3);
        const og = ctx.createGain(); og.gain.value = v * 0.5; o.connect(og).connect(g); o.start();
      }
      const p = ctx.createStereoPanner(); p.pan.value = -0.7 + (1.4 * i) / 7;
      g.connect(p).connect(this.memBus);
      this.memVoices.push({ g });
    });
    // the rub: a held minor second (D/Eb) in high strings while the closed world names the wrong fault
    this.rub = ctx.createGain(); this.rub.gain.value = 0; this.rub.connect(this.stringBus);
    for (const m of [74, 75, 69]) for (const det of [-6, 6]) {
      const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = mtof(m); o.detune.value = det;
      const g = ctx.createGain(); g.gain.value = 0.05; o.connect(g).connect(this.rub); o.start();
    }
  }

  /* ---------------------------------------------------------------- instruments */
  private envGain(at: number, attack: number, hold: number, release: number, peak: number) {
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.linearRampToValueAtTime(peak, at + attack);
    g.gain.setValueAtTime(peak, at + attack + hold);
    g.gain.exponentialRampToValueAtTime(0.0001, at + attack + hold + release);
    return g;
  }
  private organ(m: number, at: number, dur: number, level: number, register: Cue['register']) {
    const ctx = this.ctx;
    const ranks: Array<[number, number]> = register === 'soft' ? [[1, 1], [2, 0.35]] : register === 'full' ? [[1, 1], [2, 0.6], [3, 0.3], [4, 0.28]] : [[2, 0.8], [3, 0.4], [4, 0.45]];
    const g = this.envGain(at, register === 'soft' ? 0.5 : 0.12, Math.max(0, dur - 0.5), 1.4, level * (m < 48 ? 0.5 : 0.32));
    for (const [h, v] of ranks) {
      for (const det of h === 1 ? [-2.5, 2.5] : [0]) {
        const o = ctx.createOscillator(); o.frequency.value = mtof(m) * h; o.detune.value = det;
        const og = ctx.createGain(); og.gain.value = v / (h === 1 ? 2 : 1);
        o.connect(og).connect(g); o.start(at); o.stop(at + dur + 1.6);
      }
    }
    // chiff: the breath of the pipe speaking
    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = Math.min(9000, mtof(m) * 3); bp.Q.value = 6;
    const ng = this.envGain(at, 0.008, 0.01, 0.07, level * 0.05);
    n.connect(bp).connect(ng).connect(this.organBus); n.start(at, Math.random()); n.stop(at + 0.12);
    g.connect(this.organBus);
  }
  private strings(m: number, at: number, dur: number, level: number) {
    const ctx = this.ctx;
    const g = this.envGain(at, 1.4, Math.max(0, dur - 1.4), 2.2, level * 0.05);
    for (const det of [-9, -3, 4, 10]) {
      const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = mtof(m); o.detune.value = det;
      o.connect(g); o.start(at); o.stop(at + dur + 2.4);
    }
    g.connect(this.stringBus);
  }
  private spiccato(m: number, at: number, level: number) {
    const ctx = this.ctx;
    const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = mtof(m);
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = mtof(m) * 2.2; bp.Q.value = 1.6;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, at); g.gain.exponentialRampToValueAtTime(0.07 * level, at + 0.006); g.gain.exponentialRampToValueAtTime(0.0001, at + 0.16);
    o.connect(bp).connect(g).connect(this.out); o.start(at); o.stop(at + 0.2);
  }
  brass(m: number, at: number, dur: number, level: number) {
    const ctx = this.ctx;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.Q.value = 2;
    lp.frequency.setValueAtTime(220, at); lp.frequency.linearRampToValueAtTime(2000, at + 0.25); lp.frequency.exponentialRampToValueAtTime(650, at + dur);
    const g = this.envGain(at, 0.22, Math.max(0, dur - 0.22), 1.6, level * 0.16);
    for (const [f, det] of [[1, -6], [1, 6], [2, 0], [0.5, 0]] as const) {
      const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = mtof(m) * f; o.detune.value = det;
      o.connect(lp); o.start(at); o.stop(at + dur + 1.8);
    }
    lp.connect(g).connect(this.out);
  }
  bell(m: number, at: number, level: number, pan = 0) {
    const ctx = this.ctx;
    const c = ctx.createOscillator(); c.frequency.value = mtof(m);
    const mod = ctx.createOscillator(); mod.frequency.value = mtof(m) * 3.5;
    const idx = ctx.createGain(); idx.gain.setValueAtTime(mtof(m) * 2.2, at); idx.gain.exponentialRampToValueAtTime(1, at + 1.6);
    mod.connect(idx).connect(c.frequency);
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, at); g.gain.exponentialRampToValueAtTime(0.06 * level, at + 0.004); g.gain.exponentialRampToValueAtTime(0.0001, at + 2.6);
    const p = ctx.createStereoPanner(); p.pan.value = pan;
    c.connect(g).connect(p).connect(this.out);
    c.start(at); mod.start(at); c.stop(at + 2.7); mod.stop(at + 2.7);
  }

  /** The cut back to the lock after the gate fires: silence is handled by the mix; this is what returns. */
  private landing(at: number) {
    CH.Dm9.forEach((m) => this.organ(m, at, 5, 0.9, 'full'));
    this.brass(38, at, 3.2, 1); this.brass(45, at, 3.2, 0.7);
    CH.Dm.forEach((m) => this.strings(m + 12, at, 5, 0.8));
  }

  /* ---------------------------------------------------------------- the scheduler, called every frame */
  update(s: ScoreState) {
    const ctx = this.ctx, now = ctx.currentTime;
    const id = CHAPTERS[s.ci].id, cue = CUES[id];
    const set = (p: AudioParam, v: number, tc: number) => p.setTargetAtTime(v, now, tc);
    const live = s.playing && s.t < TOTAL + 2;
    const duck = 1 - 0.7 * s.duck;
    set(this.organBus.gain, live ? cue.organ * duck : 0, 0.8);
    set(this.stringBus.gain, live ? cue.strings * duck : 0, 1.0);

    // memory voices and the rub are continuous layers
    set(this.memBus.gain, live && id === 'memory' && s.memory ? 0.05 : 0, 0.8);
    if (s.memory) this.memVoices.forEach((v, i) => set(v.g.gain, Math.min(1, Math.abs(s.memory![(i * 23) % s.memory!.length])), 0.12));
    const rubOn = live && id === 'unseen' && !!s.unseen && !s.unseen.abnormal && s.unseen.forestTop < 0.99;
    set(this.rub.gain, rubOn ? 0.6 : 0, rubOn ? 1.2 : 0.4);
    if (id === 'unseen' && s.unseen?.abnormal && !this.flagged && live) {
      // the open tier speaks: a bright open fifth
      this.flagged = true;
      [62, 69, 74, 81].forEach((m) => this.organ(m, now + 0.02, 3.5, 0.8, 'bright'));
      this.bell(86, now + 0.05, 1, 0.3);
    }
    if (id !== 'unseen') this.flagged = false;

    // events whose story time falls inside the look-ahead window
    const ahead = 0.25;
    if (!live) { this.schedT = -1; return; }
    if (this.schedT < 0 || s.t < this.schedT - 0.6 || s.t - this.schedT > 1.5) this.schedT = s.t; // a jump: start fresh
    const from = this.schedT, to = s.t + ahead;
    if (to <= from) return;
    const atOf = (storyT: number) => now + Math.max(0, storyT - s.t);

    for (let i = 0; i < CHAPTERS.length; i++) {
      const c0 = STARTS[i], c1 = c0 + CHAPTERS[i].dur;
      if (c1 <= from || c0 > to) continue;
      const cu = CUES[CHAPTERS[i].id];
      // chords on the bar
      for (let b = 0; c0 + b * cu.bar < c1; b++) {
        const bt = c0 + b * cu.bar;
        if (bt <= from || bt > to) continue;
        // the gate's confirmation owns the moment: nothing else enters through the silence
        if (bt > T_CONFIRM - 0.2 && bt < T_CONFIRM + 1.5) continue;
        let name: Chord = cu.chords[b % cu.chords.length];
        if (CHAPTERS[i].id === 'land' && bt >= T_TOUCH - 0.2) name = 'Fmaj';
        const dur = Math.min(cu.bar, c1 - bt) + 0.4;
        CH[name].forEach((m) => this.organ(m, atOf(bt), dur, 1, cu.register));
        if (cu.strings > 0) CH[name].slice(1).forEach((m) => this.strings(m + 12, atOf(bt), dur, 1));
      }
      // ostinato: eighths or sixteenths, rising in tempo through the detector
      if (cu.ostinato > 0) {
        const bpm = CHAPTERS[i].id === 'detect' ? cu.bpm + 14 * clamp01((s.t - c0) / Math.max(1, T_CONFIRM - c0)) : cu.bpm;
        const step = 60 / bpm / (2 * cu.density);
        const first = Math.ceil((Math.max(from, c0) - c0) / step);
        for (let n = first; c0 + n * step <= Math.min(to, c1); n++) {
          const nt = c0 + n * step;
          if (nt <= from) continue;
          if (nt > T_CONFIRM - 0.05 && nt < T_CONFIRM + 2.6) continue; // silence after the gate
          const accent = n % (4 * cu.density) === 0 ? 1.3 : 1;
          this.spiccato(OSTINATO[n % OSTINATO.length], atOf(nt), cu.ostinato * accent);
        }
      }
    }
    // the fault enters: low brass and a string cluster under the injection
    if (T_INJECT > from && T_INJECT <= to) {
      this.brass(38, atOf(T_INJECT), 2.6, 0.9);
      [62, 63, 69].forEach((m) => this.strings(m, atOf(T_INJECT), 3.2, 1.4));
    }
    // the gate confirms (the film holds its clock through the ground cross-cut): silence, then the full chord
    if (T_CONFIRM + 1.4 > from && T_CONFIRM + 1.4 <= to) this.landing(atOf(T_CONFIRM + 1.4));
    // touchdown: F major arrives with the wheels
    if (T_TOUCH > from && T_TOUCH <= to) { CH.Fmaj.forEach((m) => this.organ(m, atOf(T_TOUCH), 7, 1, 'full')); this.brass(41, atOf(T_TOUCH), 3, 0.6); }
    this.schedT = to;

    // bells: one per pipeline stage the frame reaches, one per newly firing FlyHash unit
    if (s.stage !== null) {
      const st = Math.floor(s.stage);
      if (st !== this.lastStage && st >= 0) { this.bell(SCALE[st % SCALE.length], now + 0.01, 0.9, -0.6 + (1.2 * st) / 11); this.lastStage = st; }
    } else this.lastStage = -1;
    s.newWinners.slice(0, 4).forEach((u, j) => this.bell(SCALE[(Math.floor(u / 20)) % SCALE.length] + 12, now + 0.02 + j * 0.07, 0.45, -0.9 + (1.8 * (u % 20)) / 19));
    // the tension cue: a single low brass swell when the drift turns into a dominant
    if (id === 'detect' && this.lastTension < 0) { this.brass(45, now + 0.05, 4, 0.5); this.lastTension = s.t; }
    if (id !== 'detect') this.lastTension = -1;
  }
}
