// The film's score, synthesised and mastered for cinema clarity:
// warm EQ-sculpted pipe organ, lush bowed strings, spiccato with bow-attack transient,
// warm low brass, and controlled crystalline FM bells (cooldown-limited to prevent ear fatigue).
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
  cold:     { chords: ['Dm'], bar: 14, organ: 0, strings: 0, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  problem:  { chords: ['Dm'], bar: 10, organ: 0.46, strings: 0, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  twin:     { chords: ['Dm', 'Bb'], bar: 4, organ: 0.5, strings: 0.3, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  approach: { chords: ['Dsus'], bar: 8, organ: 0.38, strings: 0.35, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  inside:   { chords: ['Dm', 'F'], bar: 6, organ: 0.3, strings: 0.28, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  signal:   { chords: ['Dm', 'Dsus'], bar: 5, organ: 0.28, strings: 0.4, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  pipeline: { chords: ['Dm', 'F', 'C', 'Bb'], bar: 3.5, organ: 0.42, strings: 0.36, ostinato: 0.55, density: 1, bpm: 96, register: 'soft' },
  detect:   { chords: ['A'], bar: 6, organ: 0.5, strings: 0.55, ostinato: 0.78, density: 2, bpm: 104, register: 'full' },
  memory:   { chords: ['Dm9'], bar: 7, organ: 0.32, strings: 0.32, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  decide:   { chords: ['Dm', 'Bb'], bar: 3.5, organ: 0.36, strings: 0.36, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  divert:   { chords: ['Dm', 'Bb', 'F', 'C'], bar: 2.25, organ: 0.68, strings: 0.65, ostinato: 0.38, density: 1, bpm: 80, register: 'full' },
  land:     { chords: ['Dm', 'Bb', 'F', 'C'], bar: 2.5, organ: 0.54, strings: 0.55, ostinato: 0, density: 1, bpm: 80, register: 'full' },
  beyond:   { chords: ['Dm', 'Gm'], bar: 7.5, organ: 0.32, strings: 0.4, ostinato: 0.28, density: 1, bpm: 84, register: 'soft' },
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
  private lastBellAt = 0;
  private flagged = false;
  private lastTension = -1;
  private memVoices: Array<{ g: GainNode }> = [];
  private memBus: GainNode;
  private rub: GainNode;

  constructor(private ctx: AudioContext, dest: AudioNode, space: AudioNode, private noise: AudioBuffer) {
    this.out = ctx.createGain(); this.out.gain.value = 0.88;
    this.out.connect(dest);
    const send = ctx.createGain(); send.gain.value = 0.78; this.out.connect(send).connect(space);

    // Organ bus: tremulant + 2.2 kHz clarity dip (-3.5 dB) + warm 4.8 kHz low-pass
    this.trem = ctx.createGain(); this.trem.gain.value = 1;
    const lfo = ctx.createOscillator(); lfo.frequency.value = 5.0;
    const depth = ctx.createGain(); depth.gain.value = 0.03; lfo.connect(depth).connect(this.trem.gain); lfo.start();

    const organDip = ctx.createBiquadFilter();
    organDip.type = 'peaking'; organDip.frequency.value = 2200; organDip.Q.value = 1.1; organDip.gain.value = -3.5;
    const organLP = ctx.createBiquadFilter();
    organLP.type = 'lowpass'; organLP.frequency.value = 4800; organLP.Q.value = 0.5;

    this.organBus = ctx.createGain(); this.organBus.gain.value = 0;
    this.organBus.connect(this.trem).connect(organDip).connect(organLP).connect(this.out);

    // Strings bus: warm cello body shelf + smooth 1.9 kHz bow roll-off
    const strWarm = ctx.createBiquadFilter();
    strWarm.type = 'lowshelf'; strWarm.frequency.value = 220; strWarm.gain.value = 2.0;
    const strLP = ctx.createBiquadFilter();
    strLP.type = 'lowpass'; strLP.frequency.value = 1900; strLP.Q.value = 0.45;
    this.stringBus = ctx.createGain(); this.stringBus.gain.value = 0;
    this.stringBus.connect(strWarm).connect(strLP).connect(this.out);

    // Memory: eight held organ pipes on a Dm9, each loudness following one reservoir node
    this.memBus = ctx.createGain(); this.memBus.gain.value = 0; this.memBus.connect(this.out);
    [50, 53, 57, 60, 64, 65, 69, 74].forEach((m, i) => {
      const g = ctx.createGain(); g.gain.value = 0;
      for (const [h, v] of [[1, 1], [2, 0.35], [3, 0.12]] as const) {
        const o = ctx.createOscillator(); o.frequency.value = mtof(m) * h; o.detune.value = (i % 2 ? 3 : -3);
        const og = ctx.createGain(); og.gain.value = v * 0.45; o.connect(og).connect(g); o.start();
      }
      const p = ctx.createStereoPanner(); p.pan.value = -0.7 + (1.4 * i) / 7;
      g.connect(p).connect(this.memBus);
      this.memVoices.push({ g });
    });

    // The rub: a held minor second (D/Eb) in high strings while the closed world names the wrong fault
    this.rub = ctx.createGain(); this.rub.gain.value = 0; this.rub.connect(this.stringBus);
    for (const m of [74, 75, 69]) for (const det of [-5, 5]) {
      const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = mtof(m); o.detune.value = det;
      const g = ctx.createGain(); g.gain.value = 0.045; o.connect(g).connect(this.rub); o.start();
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
    const ranks: Array<[number, number]> =
      register === 'soft' ? [[1, 1], [2, 0.3]] :
      register === 'full' ? [[1, 1], [2, 0.52], [3, 0.24], [4, 0.2]] :
      [[2, 0.72], [3, 0.35], [4, 0.36]];
    const g = this.envGain(at, register === 'soft' ? 0.55 : 0.14, Math.max(0, dur - 0.5), 1.45, level * (m < 48 ? 0.48 : 0.3));
    for (const [h, v] of ranks) {
      for (const det of h === 1 ? [-2.5, 2.5] : [0]) {
        const o = ctx.createOscillator(); o.frequency.value = mtof(m) * h; o.detune.value = det;
        const og = ctx.createGain(); og.gain.value = v / (h === 1 ? 2 : 1);
        o.connect(og).connect(g); o.start(at); o.stop(at + dur + 1.65);
      }
    }
    // Chiff: subtle breath of the pipe speaking
    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = Math.min(7500, mtof(m) * 2.8); bp.Q.value = 5;
    const ng = this.envGain(at, 0.008, 0.01, 0.06, level * 0.04);
    n.connect(bp).connect(ng).connect(this.organBus); n.start(at, Math.random()); n.stop(at + 0.11);
    g.connect(this.organBus);
  }

  private strings(m: number, at: number, dur: number, level: number) {
    const ctx = this.ctx;
    const g = this.envGain(at, 1.45, Math.max(0, dur - 1.45), 2.2, level * 0.048);
    for (const det of [-7, -2.5, 2.5, 7]) {
      const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = mtof(m); o.detune.value = det;
      o.connect(g); o.start(at); o.stop(at + dur + 2.4);
    }
    g.connect(this.stringBus);
  }

  private spiccato(m: number, at: number, level: number) {
    const ctx = this.ctx;
    const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = mtof(m);
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = mtof(m) * 1.8; bp.Q.value = 1.4;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(0.068 * level, at + 0.006);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 0.15);
    o.connect(bp).connect(g).connect(this.out); o.start(at); o.stop(at + 0.19);

    // Subtle bow-resin attack transient
    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const nbp = ctx.createBiquadFilter(); nbp.type = 'bandpass'; nbp.frequency.value = 2600; nbp.Q.value = 2.0;
    const ng = this.envGain(at, 0.002, 0.004, 0.014, 0.018 * level);
    n.connect(nbp).connect(ng).connect(this.out); n.start(at, Math.random()); n.stop(at + 0.03);
  }

  brass(m: number, at: number, dur: number, level: number) {
    const ctx = this.ctx;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.Q.value = 1.5;
    lp.frequency.setValueAtTime(190, at);
    lp.frequency.linearRampToValueAtTime(1550, at + 0.28);
    lp.frequency.exponentialRampToValueAtTime(520, at + dur);
    const g = this.envGain(at, 0.24, Math.max(0, dur - 0.24), 1.65, level * 0.155);
    for (const [f, det] of [[1, -5], [1, 5], [2, 0], [0.5, 0]] as const) {
      const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = mtof(m) * f; o.detune.value = det;
      o.connect(lp); o.start(at); o.stop(at + dur + 1.85);
    }
    lp.connect(g).connect(this.out);
  }

  /** Crystalline, non-fatiguing FM bell (tamed modulation index & warm LP). */
  bell(m: number, at: number, level: number, pan = 0) {
    const ctx = this.ctx;
    const c = ctx.createOscillator(); c.frequency.value = mtof(m);
    const mod = ctx.createOscillator(); mod.frequency.value = mtof(m) * 3.0;
    const idx = ctx.createGain();
    idx.gain.setValueAtTime(mtof(m) * 1.1, at);
    idx.gain.exponentialRampToValueAtTime(1, at + 1.2);
    mod.connect(idx).connect(c.frequency);

    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 3800;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(0.032 * level, at + 0.004);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 2.0);
    const p = ctx.createStereoPanner(); p.pan.value = pan;
    c.connect(lp).connect(g).connect(p).connect(this.out);
    c.start(at); mod.start(at); c.stop(at + 2.1); mod.stop(at + 2.1);
  }

  /** The cut back to the lock after the gate fires: silence is handled by the mix; this is what returns. */
  private landing(at: number) {
    CH.Dm9.forEach((m) => this.organ(m, at, 5, 0.85, 'full'));
    this.brass(38, at, 3.2, 0.95); this.brass(45, at, 3.2, 0.65);
    CH.Dm.forEach((m) => this.strings(m + 12, at, 5, 0.78));
  }

  /* ---------------------------------------------------------------- the scheduler, called every frame */
  update(s: ScoreState) {
    const now = this.ctx.currentTime;
    const id = CHAPTERS[s.ci].id, cue = CUES[id];
    const set = (p: AudioParam, v: number, tc: number) => p.setTargetAtTime(v, now, tc);
    const live = s.playing && s.t < TOTAL + 2;
    const duck = 1 - 0.7 * s.duck;
    set(this.organBus.gain, live ? cue.organ * duck : 0, 0.8);
    set(this.stringBus.gain, live ? cue.strings * duck : 0, 1.0);

    // Memory voices and the rub are continuous layers
    set(this.memBus.gain, live && id === 'memory' && s.memory ? 0.048 : 0, 0.8);
    if (s.memory) this.memVoices.forEach((v, i) => set(v.g.gain, Math.min(1, Math.abs(s.memory![(i * 23) % s.memory!.length])), 0.12));
    const rubOn = live && id === 'beyond' && !!s.unseen && !s.unseen.abnormal && s.unseen.forestTop < 0.99;
    set(this.rub.gain, rubOn ? 0.55 : 0, rubOn ? 1.2 : 0.4);
    if (id === 'beyond' && s.unseen?.abnormal && !this.flagged && live) {
      // The open tier speaks: a bright open fifth
      this.flagged = true;
      [62, 69, 74, 81].forEach((m) => this.organ(m, now + 0.02, 3.5, 0.76, 'bright'));
      this.bell(86, now + 0.05, 0.9, 0.3);
    }
    if (id !== 'beyond') this.flagged = false;

    // Events whose story time falls inside the look-ahead window
    const ahead = 0.25;
    if (!live) { this.schedT = -1; return; }
    if (this.schedT < 0 || s.t < this.schedT - 0.6 || s.t - this.schedT > 1.5) this.schedT = s.t;
    const from = this.schedT, to = s.t + ahead;
    if (to <= from) return;
    const atOf = (storyT: number) => now + Math.max(0, storyT - s.t);

    for (let i = 0; i < CHAPTERS.length; i++) {
      const c0 = STARTS[i], c1 = c0 + CHAPTERS[i].dur;
      if (c1 <= from || c0 > to) continue;
      const cu = CUES[CHAPTERS[i].id];
      // Chords on the bar
      for (let b = 0; c0 + b * cu.bar < c1; b++) {
        const bt = c0 + b * cu.bar;
        if (bt <= from || bt > to) continue;
        if (bt > T_CONFIRM - 0.2 && bt < T_CONFIRM + 1.5) continue;
        let name: Chord = cu.chords[b % cu.chords.length];
        if (CHAPTERS[i].id === 'land' && bt >= T_TOUCH - 0.2) name = 'Fmaj';
        const dur = Math.min(cu.bar, c1 - bt) + 0.4;
        CH[name].forEach((m) => this.organ(m, atOf(bt), dur, 1, cu.register));
        if (cu.strings > 0) CH[name].slice(1).forEach((m) => this.strings(m + 12, atOf(bt), dur, 1));
      }
      // Ostinato: eighths or sixteenths, rising in tempo through the detector
      if (cu.ostinato > 0) {
        const bpm = CHAPTERS[i].id === 'detect' ? cu.bpm + 14 * clamp01((s.t - c0) / Math.max(1, T_CONFIRM - c0)) : cu.bpm;
        const step = 60 / bpm / (2 * cu.density);
        const first = Math.ceil((Math.max(from, c0) - c0) / step);
        for (let n = first; c0 + n * step <= Math.min(to, c1); n++) {
          const nt = c0 + n * step;
          if (nt <= from) continue;
          if (nt > T_CONFIRM - 0.05 && nt < T_CONFIRM + 2.6) continue;
          const accent = n % (4 * cu.density) === 0 ? 1.25 : 1;
          this.spiccato(OSTINATO[n % OSTINATO.length], atOf(nt), cu.ostinato * accent);
        }
      }
    }

    // The fault enters: low brass and a string cluster under the injection
    if (T_INJECT > from && T_INJECT <= to) {
      this.brass(38, atOf(T_INJECT), 2.6, 0.88);
      [62, 63, 69].forEach((m) => this.strings(m, atOf(T_INJECT), 3.2, 1.35));
    }
    // The gate confirms: silence, then the full chord
    if (T_CONFIRM + 1.4 > from && T_CONFIRM + 1.4 <= to) this.landing(atOf(T_CONFIRM + 1.4));
    // Touchdown: F major arrives with the wheels
    if (T_TOUCH > from && T_TOUCH <= to) {
      CH.Fmaj.forEach((m) => this.organ(m, atOf(T_TOUCH), 7, 0.95, 'full'));
      this.brass(41, atOf(T_TOUCH), 3, 0.58);
    }
    this.schedT = to;

    // Bells: pipeline stages + cooldown-limited FlyHash chimes (max 2 per 75 ms window)
    if (s.stage !== null) {
      const st = Math.floor(s.stage);
      if (st !== this.lastStage && st >= 0) {
        this.bell(SCALE[st % SCALE.length], now + 0.01, 0.78, -0.6 + (1.2 * st) / 11);
        this.lastStage = st;
      }
    } else this.lastStage = -1;

    if (s.newWinners.length > 0 && now - this.lastBellAt >= 0.075) {
      this.lastBellAt = now;
      s.newWinners.slice(0, 2).forEach((u, j) =>
        this.bell(SCALE[(Math.floor(u / 20)) % SCALE.length] + 12, now + 0.015 + j * 0.055, 0.42, -0.85 + (1.7 * (u % 20)) / 19)
      );
    }

    // Tension cue: single low brass swell when drift turns into A dominant
    if (id === 'detect' && this.lastTension < 0) { this.brass(45, now + 0.05, 4, 0.48); this.lastTension = s.t; }
    if (id !== 'detect') this.lastTension = -1;
  }
}
