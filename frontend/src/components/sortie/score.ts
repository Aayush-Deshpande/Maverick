// ANUMAAN Sortie Score — Zimmer-inspired Cathedral Organ, Bowed Cello/Viola Ensemble,
// Saturated Cinema Brass BRAAAM, Percussive Spiccato Ostinato, and Crystalline FlyHash Bells.
// Eliminates "home harmonium" vibrato in favor of a dynamic Swell-Box Low-Pass Filter,
// 16' sub-pedal pipes, dual-LFO stereo string chorus, and cello body formants.
import { CHAPTERS, STARTS, T_INJECT, T_TOUCH, TOTAL, type ChapterId } from './story';
import { T_CONFIRM } from './timeline';

const mtof = (m: number) => 440 * Math.pow(2, (m - 69) / 12);
const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

function makeWarmDrive(drive = 1.65, samples = 2048) {
  const curve = new Float32Array(samples);
  const norm = Math.tanh(drive);
  for (let i = 0; i < samples; i++) {
    const x = (i * 2) / (samples - 1) - 1;
    curve[i] = Math.tanh(drive * x) / norm;
  }
  return curve as unknown as Float32Array<ArrayBuffer>;
}

// Voicings (MIDI)
const CH = {
  Dm: [38, 50, 57, 62, 65], Bb: [34, 46, 53, 58, 62], F: [41, 48, 57, 60, 65], C: [36, 48, 55, 60, 64],
  Gm: [43, 50, 55, 58, 62], A: [45, 52, 57, 61, 64], Dsus: [38, 50, 57, 62, 64], Fmaj: [41, 53, 57, 60, 65, 69],
  Dm9: [38, 50, 57, 64, 65, 69],
};
type Chord = keyof typeof CH;

const SCALE = [62, 64, 65, 67, 69, 70, 72, 74, 76, 77, 79, 81];
const OSTINATO = [62, 57, 62, 65, 62, 57, 64, 65];

interface Cue {
  chords: Chord[];
  bar: number;
  organ: number;
  swellHz: number; // Cathedral organ swell-box shutter frequency (replaces static brightness)
  strings: number;
  ostinato: number;
  density: 1 | 2;
  bpm: number;
  register: 'soft' | 'full' | 'bright';
}

const CUES: Record<ChapterId, Cue> = {
  cold:     { chords: ['Dm'], bar: 14, organ: 0,    swellHz: 520,  strings: 0,    ostinato: 0,    density: 1, bpm: 90,  register: 'soft' },
  problem:  { chords: ['Dm'], bar: 10, organ: 0.42, swellHz: 620,  strings: 0.2,  ostinato: 0,    density: 1, bpm: 90,  register: 'soft' },
  twin:     { chords: ['Dm', 'Bb'], bar: 4, organ: 0.44, swellHz: 850, strings: 0.36, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  approach: { chords: ['Dsus'], bar: 8, organ: 0.34, swellHz: 740, strings: 0.42, ostinato: 0,    density: 1, bpm: 90,  register: 'soft' },
  inside:   { chords: ['Dm', 'F'], bar: 6, organ: 0.26, swellHz: 600, strings: 0.32, ostinato: 0, density: 1, bpm: 90,  register: 'soft' },
  signal:   { chords: ['Dm', 'Dsus'], bar: 5, organ: 0.25, swellHz: 680, strings: 0.44, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  pipeline: { chords: ['Dm', 'F', 'C', 'Bb'], bar: 3.5, organ: 0.36, swellHz: 1100, strings: 0.4, ostinato: 0.62, density: 1, bpm: 96, register: 'soft' },
  detect:   { chords: ['A'], bar: 6, organ: 0.44, swellHz: 1450, strings: 0.56, ostinato: 0.85,  density: 2, bpm: 104, register: 'full' },
  memory:   { chords: ['Dm9'], bar: 7, organ: 0.34, swellHz: 960, strings: 0.48, ostinato: 0,    density: 1, bpm: 90,  register: 'soft' },
  decide:   { chords: ['Dm', 'Bb'], bar: 3.5, organ: 0.34, swellHz: 1050, strings: 0.42, ostinato: 0, density: 1, bpm: 90, register: 'soft' },
  divert:   { chords: ['Dm', 'Bb', 'F', 'C'], bar: 2.25, organ: 0.62, swellHz: 2250, strings: 0.72, ostinato: 0.4, density: 1, bpm: 80, register: 'full' },
  land:     { chords: ['Dm', 'Bb', 'F', 'C'], bar: 2.5, organ: 0.52, swellHz: 1950, strings: 0.64, ostinato: 0, density: 1, bpm: 80, register: 'full' },
  beyond:   { chords: ['Dm', 'Gm'], bar: 7.5, organ: 0.24, swellHz: 780, strings: 0.44, ostinato: 0.26, density: 1, bpm: 84, register: 'soft' },
};

export interface ScoreState {
  t: number;
  ci: number;
  playing: boolean;
  stage: number | null;
  newWinners: number[];
  unseen: { abnormal: boolean; forestTop: number } | null;
  memory: Float32Array | null;
  duck: number;
}

export class Score {
  private out: GainNode;
  private organBus: GainNode;
  private organSwellLP: BiquadFilterNode;
  private stringBus: GainNode;
  private brassSat: WaveShaperNode;
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
    const send = ctx.createGain(); send.gain.value = 0.82; this.out.connect(send).connect(space);

    // Temple-Church Pipe Organ Bus: NO harmonium vibrato; warm saturation + 2.1kHz clarity dip + dynamic Swell-Box LPF
    const organSat = ctx.createWaveShaper();
    organSat.curve = makeWarmDrive(1.4);
    organSat.oversample = '2x';

    const organDip = ctx.createBiquadFilter();
    organDip.type = 'peaking'; organDip.frequency.value = 2100; organDip.Q.value = 1.0; organDip.gain.value = -4.2;

    this.organSwellLP = ctx.createBiquadFilter();
    this.organSwellLP.type = 'lowpass'; this.organSwellLP.frequency.value = 750; this.organSwellLP.Q.value = 0.55;

    this.organBus = ctx.createGain(); this.organBus.gain.value = 0;
    this.organBus.connect(organSat).connect(organDip).connect(this.organSwellLP).connect(this.out);

    // Bowed Cello/Viola Ensemble Bus: body formant EQ + Dual-LFO Stereo Ensemble Chorus
    const strBody = ctx.createBiquadFilter();
    strBody.type = 'peaking'; strBody.frequency.value = 240; strBody.Q.value = 0.9; strBody.gain.value = 2.8;

    const strFizzCut = ctx.createBiquadFilter();
    strFizzCut.type = 'peaking'; strFizzCut.frequency.value = 2300; strFizzCut.Q.value = 1.1; strFizzCut.gain.value = -3.2;

    const strLP = ctx.createBiquadFilter();
    strLP.type = 'lowpass'; strLP.frequency.value = 1750; strLP.Q.value = 0.45;

    this.stringBus = ctx.createGain(); this.stringBus.gain.value = 0;
    const strDry = ctx.createGain(); strDry.gain.value = 0.72;
    this.stringBus.connect(strBody).connect(strFizzCut).connect(strLP);
    strLP.connect(strDry).connect(this.out);

    // Dual-LFO stereo ensemble chorus gives lush orchestral width
    for (const [panVal, rate, baseDelay] of [[-0.65, 0.26, 0.014], [0.65, 0.33, 0.019]] as const) {
      const del = ctx.createDelay(0.05); del.delayTime.value = baseDelay;
      const lfo = ctx.createOscillator(); lfo.type = 'sine'; lfo.frequency.value = rate;
      const depth = ctx.createGain(); depth.gain.value = 0.0024;
      lfo.connect(depth).connect(del.delayTime); lfo.start();
      const p = ctx.createStereoPanner(); p.pan.value = panVal;
      const cg = ctx.createGain(); cg.gain.value = 0.36;
      strLP.connect(del).connect(p).connect(cg).connect(this.out);
    }

    // Shared warm brass saturator
    this.brassSat = ctx.createWaveShaper();
    this.brassSat.curve = makeWarmDrive(2.1);
    this.brassSat.oversample = '2x';
    this.brassSat.connect(this.out);

    // Memory: 8 live stereo reservoir voices on Dm9 (clearly audible living AI memory)
    this.memBus = ctx.createGain(); this.memBus.gain.value = 0; this.memBus.connect(this.out);
    [50, 53, 57, 60, 64, 65, 69, 74].forEach((m, i) => {
      const g = ctx.createGain(); g.gain.value = 0;
      for (const [h, v] of [[1, 1], [2, 0.28]] as const) {
        const o = ctx.createOscillator(); o.type = h === 1 ? 'triangle' : 'sine';
        o.frequency.value = mtof(m) * h; o.detune.value = (i % 2 ? 3.5 : -3.5);
        const og = ctx.createGain(); og.gain.value = v * 0.42; o.connect(og).connect(g); o.start();
      }
      const p = ctx.createStereoPanner(); p.pan.value = -0.78 + (1.56 * i) / 7;
      g.connect(p).connect(this.memBus);
      this.memVoices.push({ g });
    });

    // Dissonant minor-second beating (D/Eb) during Random Forest's false confidence
    this.rub = ctx.createGain(); this.rub.gain.value = 0; this.rub.connect(this.stringBus);
    for (const m of [74, 75, 69]) for (const det of [-5, 5]) {
      const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = mtof(m); o.detune.value = det;
      const g = ctx.createGain(); g.gain.value = 0.05; o.connect(g).connect(this.rub); o.start();
    }
  }

  /* ---------------------------------------------------------------- instruments */
  private envGain(at: number, attack: number, hold: number, release: number, peak: number) {
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.linearRampToValueAtTime(Math.max(0.0002, peak), at + attack);
    g.gain.setValueAtTime(Math.max(0.0002, peak), at + attack + hold);
    g.gain.exponentialRampToValueAtTime(0.0001, at + attack + hold + release);
    return g;
  }

  /** Architectural cathedral pipe organ (16' sub-pedal on bass notes, stereo chest spread, soft breath chiff). */
  private organ(m: number, at: number, dur: number, level: number, register: Cue['register']) {
    const ctx = this.ctx;
    const isBass = m < 48;
    const ranks: Array<[number, number]> =
      register === 'soft' ? (isBass ? [[0.5, 0.55], [1, 1], [2, 0.22]] : [[1, 1], [2, 0.25]]) :
      register === 'full' ? (isBass ? [[0.5, 0.65], [1, 1], [2, 0.45], [3, 0.16]] : [[1, 1], [2, 0.45], [3, 0.18], [4, 0.14]]) :
      [[1, 0.5], [2, 0.65], [3, 0.25], [4, 0.22]];

    const g = this.envGain(at, register === 'soft' ? 0.7 : 0.18, Math.max(0, dur - 0.55), 1.7, level * (isBass ? 0.46 : 0.27));
    const pan = ctx.createStereoPanner();
    pan.pan.value = isBass ? 0 : ((m % 5) - 2) * 0.22; // bass dead center, upper pipes spread across organ facade

    for (const [h, v] of ranks) {
      for (const det of h === 1 ? [-3.5, 3.5] : [0]) {
        const o = ctx.createOscillator();
        o.type = h === 0.5 ? 'sine' : 'triangle';
        o.frequency.value = mtof(m) * h;
        o.detune.value = det;
        const og = ctx.createGain(); og.gain.value = v / (h === 1 ? 2 : 1);
        o.connect(og).connect(g); o.start(at); o.stop(at + dur + 1.9);
      }
    }
    // Subtle pipe-speech breath chiff
    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = Math.min(5500, mtof(m) * 2.5); bp.Q.value = 4.5;
    const ng = this.envGain(at, 0.01, 0.012, 0.065, level * 0.032);
    n.connect(bp).connect(ng).connect(this.organBus); n.start(at, Math.random()); n.stop(at + 0.12);
    g.connect(pan).connect(this.organBus);
  }

  private strings(m: number, at: number, dur: number, level: number) {
    const ctx = this.ctx;
    const g = this.envGain(at, 1.5, Math.max(0, dur - 1.4), 2.4, level * 0.052);
    for (const det of [-8, -2.5, 2.5, 8]) {
      const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = mtof(m); o.detune.value = det;
      o.connect(g); o.start(at); o.stop(at + dur + 2.6);
    }
    g.connect(this.stringBus);
  }

  private spiccato(m: number, at: number, level: number) {
    const ctx = this.ctx;
    const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = mtof(m);
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = mtof(m) * 1.75; bp.Q.value = 1.4;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(0.075 * level, at + 0.005);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 0.145);
    o.connect(bp).connect(g).connect(this.out); o.start(at); o.stop(at + 0.18);

    // Crisp bow-rosin bite transient
    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const nbp = ctx.createBiquadFilter(); nbp.type = 'bandpass'; nbp.frequency.value = 2400; nbp.Q.value = 2.2;
    const ng = this.envGain(at, 0.0015, 0.003, 0.014, 0.022 * level);
    n.connect(nbp).connect(ng).connect(this.out); n.start(at, Math.random()); n.stop(at + 0.028);
  }

  /** Cinema low brass BRAAAM: unison detuned horns + sub-octave driven through warm saturator. */
  brass(m: number, at: number, dur: number, level: number) {
    const ctx = this.ctx;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.Q.value = 1.4;
    lp.frequency.setValueAtTime(160, at);
    lp.frequency.linearRampToValueAtTime(1350, at + 0.24);
    lp.frequency.exponentialRampToValueAtTime(420, at + dur);
    const g = this.envGain(at, 0.2, Math.max(0, dur - 0.2), 1.8, level * 0.17);
    for (const [f, det] of [[1, -10], [1, -3], [1, 3], [1, 10], [0.5, 0]] as const) {
      const o = ctx.createOscillator(); o.type = f === 0.5 ? 'triangle' : 'sawtooth';
      o.frequency.value = mtof(m) * f; o.detune.value = det;
      o.connect(lp); o.start(at); o.stop(at + dur + 2.0);
    }
    lp.connect(g).connect(this.brassSat);
  }

  /** Crystalline, glassy FM chime (soft modulation index, warm LP, non-fatiguing). */
  bell(m: number, at: number, level: number, pan = 0) {
    const ctx = this.ctx;
    const c = ctx.createOscillator(); c.frequency.value = mtof(m);
    const mod = ctx.createOscillator(); mod.frequency.value = mtof(m) * 3.0;
    const idx = ctx.createGain();
    idx.gain.setValueAtTime(mtof(m) * 0.95, at);
    idx.gain.exponentialRampToValueAtTime(1, at + 1.1);
    mod.connect(idx).connect(c.frequency);

    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 3400;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(0.032 * level, at + 0.004);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 2.1);
    const p = ctx.createStereoPanner(); p.pan.value = pan;
    c.connect(lp).connect(g).connect(p).connect(this.out);
    c.start(at); mod.start(at); c.stop(at + 2.2); mod.stop(at + 2.2);
  }

  /** Frisson Bloom after the 1.4s Gate-Lock silence: lush Dm9 cathedral organ + low brass + soaring strings. */
  private landing(at: number) {
    CH.Dm9.forEach((m) => this.organ(m, at, 5.2, 0.85, 'full'));
    this.brass(38, at, 3.4, 0.95); this.brass(45, at, 3.4, 0.62);
    CH.Dm.forEach((m) => this.strings(m + 12, at, 5.4, 0.88));
  }

  /* ---------------------------------------------------------------- the scheduler, called every frame */
  update(s: ScoreState) {
    const now = this.ctx.currentTime;
    const id = CHAPTERS[s.ci].id, cue = CUES[id];
    const set = (p: AudioParam, v: number, tc: number) => p.setTargetAtTime(v, now, tc);
    const live = s.playing && s.t < TOTAL + 2;
    const duck = 1 - 0.68 * s.duck;

    set(this.organBus.gain, live ? cue.organ * duck : 0, 0.85);
    set(this.organSwellLP.frequency, live ? cue.swellHz : 500, 1.1);
    set(this.stringBus.gain, live ? cue.strings * duck : 0, 1.0);

    // Live 500-node reservoir harmony (raised presence so judge hears the AI remembering)
    set(this.memBus.gain, live && id === 'memory' && s.memory ? 0.13 : 0, 0.75);
    if (s.memory) this.memVoices.forEach((v, i) => set(v.g.gain, Math.min(1, Math.abs(s.memory![(i * 23) % s.memory!.length])), 0.12));

    // Dissonant minor-second beating while Random Forest is confidently wrong -> snaps to pure open fifth on FlyBrain catch
    const rubOn = live && id === 'beyond' && !!s.unseen && !s.unseen.abnormal && s.unseen.forestTop < 0.99;
    set(this.rub.gain, rubOn ? 0.65 : 0, rubOn ? 1.0 : 0.25);
    if (id === 'beyond' && s.unseen?.abnormal && !this.flagged && live) {
      this.flagged = true;
      [50, 62, 69, 74, 81].forEach((m) => this.organ(m, now + 0.02, 4.0, 0.78, 'bright'));
      this.bell(86, now + 0.04, 0.95, 0.25);
      this.bell(74, now + 0.08, 0.7, -0.25);
    }
    if (id !== 'beyond') this.flagged = false;

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
      for (let b = 0; c0 + b * cu.bar < c1; b++) {
        const bt = c0 + b * cu.bar;
        if (bt <= from || bt > to) continue;
        if (bt > T_CONFIRM - 0.2 && bt < T_CONFIRM + 1.5) continue;
        let name: Chord = cu.chords[b % cu.chords.length];
        if (CHAPTERS[i].id === 'land' && bt >= T_TOUCH - 0.2) name = 'Fmaj';
        const dur = Math.min(cu.bar, c1 - bt) + 0.45;
        CH[name].forEach((m) => this.organ(m, atOf(bt), dur, 1, cu.register));
        if (cu.strings > 0) CH[name].slice(1).forEach((m) => this.strings(m + 12, atOf(bt), dur, 1));
      }
      if (cu.ostinato > 0) {
        const bpm = CHAPTERS[i].id === 'detect' ? cu.bpm + 14 * clamp01((s.t - c0) / Math.max(1, T_CONFIRM - c0)) : cu.bpm;
        const step = 60 / bpm / (2 * cu.density);
        const first = Math.ceil((Math.max(from, c0) - c0) / step);
        for (let n = first; c0 + n * step <= Math.min(to, c1); n++) {
          const nt = c0 + n * step;
          if (nt <= from) continue;
          if (nt > T_CONFIRM - 0.05 && nt < T_CONFIRM + 2.6) continue;
          const accent = n % (4 * cu.density) === 0 ? 1.28 : 1;
          this.spiccato(OSTINATO[n % OSTINATO.length], atOf(nt), cu.ostinato * accent);
        }
      }
    }

    // T_INJECT (01:03): Yellow oil-system cutaway -> dark BRAAAM + tense string cluster
    if (T_INJECT > from && T_INJECT <= to) {
      this.brass(38, atOf(T_INJECT), 2.8, 0.96);
      [62, 63, 69].forEach((m) => this.strings(m, atOf(T_INJECT), 3.4, 1.4));
    }
    // T_CONFIRM + 1.4s: Frisson bloom after Ground Control silence
    if (T_CONFIRM + 1.4 > from && T_CONFIRM + 1.4 <= to) this.landing(atOf(T_CONFIRM + 1.4));
    // T_TOUCH: Warm F-major catharsis with the wheels
    if (T_TOUCH > from && T_TOUCH <= to) {
      CH.Fmaj.forEach((m) => this.organ(m, atOf(T_TOUCH), 7.2, 0.92, 'full'));
      this.brass(41, atOf(T_TOUCH), 3.2, 0.62);
    }
    this.schedT = to;

    // Pipeline & FlyHash crystalline bells (cooldown-limited to 75ms so they sparkle, never spam)
    if (s.stage !== null) {
      const st = Math.floor(s.stage);
      if (st !== this.lastStage && st >= 0) {
        this.bell(SCALE[st % SCALE.length], now + 0.01, 0.72, -0.6 + (1.2 * st) / 11);
        this.lastStage = st;
      }
    } else this.lastStage = -1;

    if (s.newWinners.length > 0 && now - this.lastBellAt >= 0.075) {
      this.lastBellAt = now;
      s.newWinners.slice(0, 2).forEach((u, j) =>
        this.bell(SCALE[(Math.floor(u / 20)) % SCALE.length] + 12, now + 0.015 + j * 0.055, 0.42, -0.85 + (1.7 * (u % 20)) / 19)
      );
    }

    if (id === 'detect' && this.lastTension < 0) { this.brass(45, now + 0.05, 4.2, 0.52); this.lastTension = s.t; }
    if (id !== 'detect') this.lastTension = -1;
  }
}
