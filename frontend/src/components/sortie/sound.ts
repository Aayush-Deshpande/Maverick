// The film's sound, synthesised in the browser + frame-synced cinema stems.
// Mastered cinema chain: 30Hz HPF, 85Hz warmth, 3.2kHz de-harsh, 3:1 bus compressor,
// frequency-damped 3.4s hall reverb, breathing Ladakh wind, pre-impact fault breath,
// authentic avionics ground chime, VHF radio ducking, and clear touchdown Foley.
import { CHAPTERS, STARTS, TOTAL, T_INJECT, T_TOUCH, startOf } from './story';
import { T_CONFIRM, type Readout } from './timeline';
import { Score } from './score';
import { StemPlayer } from './stemPlayer';

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

export interface Listener {
  /** -1 (left) .. 1 (right): where the aircraft is in the frame */
  pan: number;
  /** world units from the camera */
  dist: number;
  /** closing speed toward the camera, world units per second (positive = approaching) */
  closing: number;
}

export interface SoundState {
  t: number;
  r: Readout;
  ci: number;
  playing: boolean;
  dt: number;
  listener: Listener;
  bay: boolean;
  winners: number[] | null;
  memory: Float32Array | null;
  /** pipeline packet position 0..12 (One frame) */
  stage: number | null;
  /** Never seen: the open tier's verdict and the forest's confidence */
  unseen: { abnormal: boolean; forestTop: number } | null;
  /** the flash-forward: the engine is dead and the music stops; only wind */
  flash: boolean;
}

export class SortieSound {
  ctx: AudioContext;
  private master: GainNode;
  private bus: GainNode;      // everything except one-shot hits; dropped for silences and cuts
  private duckBus: GainNode;  // brief sidechain ducking for radio/touchdown/faults
  private air: GainNode;      // exterior layers
  private airLP: BiquadFilterNode;
  private reverbSend: GainNode;
  private noise: AudioBuffer;
  private eng: { osc: OscillatorNode; lp: BiquadFilterNode; g: GainNode; pan: StereoPannerNode };
  private prop: { osc: OscillatorNode; bp: BiquadFilterNode; g: GainNode; am: OscillatorNode };
  private valve: { g: GainNode; lfo: OscillatorNode };
  private windL: GainNode; private windR: GainNode;
  private bayRing: GainNode;
  private sub: GainNode;
  private riser: Array<{ o: OscillatorNode; g: GainNode }> = [];
  private riserBus: GainNode;
  private swell: GainNode;
  private voices: Array<{ o: OscillatorNode; g: GainNode }> = [];
  private voiceBus: GainNode;
  private rumble: GainNode;
  private lastT = -1;
  private nextTick = 0;
  private tock = false;
  private silenceUntil = 0;
  private muted = false;
  private riserPhase = 0;
  private prevWinners = new Set<number>();
  private score: Score;
  private stems: StemPlayer;

  constructor() {
    const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = (this.ctx = new AC());

    // Master cinema chain: 30Hz HPF -> 85Hz warmth -> 3.2kHz de-harsh -> 3:1 compressor -> destination
    const masterHP = ctx.createBiquadFilter();
    masterHP.type = 'highpass'; masterHP.frequency.value = 30; masterHP.Q.value = 0.7;

    const masterWarm = ctx.createBiquadFilter();
    masterWarm.type = 'lowshelf'; masterWarm.frequency.value = 85; masterWarm.gain.value = 1.5;

    const masterDeHarsh = ctx.createBiquadFilter();
    masterDeHarsh.type = 'peaking'; masterDeHarsh.frequency.value = 3200; masterDeHarsh.Q.value = 1.0; masterDeHarsh.gain.value = -1.5;

    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -15; comp.knee.value = 12; comp.ratio.value = 3.0; comp.attack.value = 0.008; comp.release.value = 0.28;

    this.master = ctx.createGain(); this.master.gain.value = 0;
    this.master.connect(masterHP).connect(masterWarm).connect(masterDeHarsh).connect(comp).connect(ctx.destination);

    this.duckBus = ctx.createGain(); this.duckBus.gain.value = 1;
    this.duckBus.connect(this.master);

    this.bus = ctx.createGain(); this.bus.connect(this.duckBus);

    // Frequency-damped 3.4s dark hall reverb (160Hz HPF + 4.2kHz LPF)
    const conv = ctx.createConvolver();
    conv.buffer = this.impulse(3.4, 2.6);
    const revHP = ctx.createBiquadFilter(); revHP.type = 'highpass'; revHP.frequency.value = 160;
    const revLP = ctx.createBiquadFilter(); revLP.type = 'lowpass'; revLP.frequency.value = 4200;
    this.reverbSend = ctx.createGain(); this.reverbSend.gain.value = 0.22;
    const wet = ctx.createGain(); wet.gain.value = 0.52;
    this.reverbSend.connect(conv).connect(revHP).connect(revLP).connect(wet).connect(this.bus);

    const len = ctx.sampleRate * 2;
    this.noise = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = this.noise.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;

    // Exterior bus, low-passed when inside cowling or detector's mind
    this.airLP = ctx.createBiquadFilter(); this.airLP.type = 'lowpass'; this.airLP.frequency.value = 16000; this.airLP.Q.value = 0.5;
    this.air = ctx.createGain();
    this.air.connect(this.airLP).connect(this.bus);
    const airRev = ctx.createGain(); airRev.gain.value = 0.25;
    this.airLP.connect(airRev).connect(this.reverbSend);

    // Engine: warm 4-cyl Rotax periodic wave
    {
      const real = new Float32Array(12), imag = new Float32Array(12);
      [0, 0.45, 1.0, 0.2, 0.42, 0.08, 0.18, 0.04, 0.08, 0.02, 0.03, 0.01].forEach((v, i) => { imag[i] = v; });
      const osc = ctx.createOscillator(); osc.setPeriodicWave(ctx.createPeriodicWave(real, imag));
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 650; lp.Q.value = 0.7;
      const g = ctx.createGain(); g.gain.value = 0;
      const pan = ctx.createStereoPanner();
      osc.connect(lp).connect(g).connect(pan).connect(this.air); osc.start();
      this.eng = { osc, lp, g, pan };
    }
    // Propeller: warm triangle blade-pass throb
    {
      const osc = ctx.createOscillator(); osc.type = 'triangle';
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 240; bp.Q.value = 0.85;
      const g = ctx.createGain(); g.gain.value = 0;
      const am = ctx.createOscillator(); am.type = 'sine';
      const amDepth = ctx.createGain(); amDepth.gain.value = 0.18;
      am.connect(amDepth).connect(g.gain);
      osc.connect(bp).connect(g).connect(this.eng.pan); osc.start(); am.start();
      this.prop = { osc, bp, g, am };
    }
    // Valve train: softer sine-modulated mechanical chatter
    {
      const n = this.loop();
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 2400; bp.Q.value = 1.2;
      const g = ctx.createGain(); g.gain.value = 0;
      const lfo = ctx.createOscillator(); lfo.type = 'sine';
      const lg = ctx.createGain(); lg.gain.value = 0.35;
      const gate = ctx.createGain(); gate.gain.value = 0.65;
      lfo.connect(lg).connect(gate.gain);
      n.connect(bp).connect(gate).connect(g).connect(this.eng.pan); lfo.start();
      this.valve = { g, lfo };
    }
    // High-altitude Ladakh wind, decorrelated left and right
    {
      const merge = ctx.createChannelMerger(2);
      const mk = (f: number, ch: number) => {
        const n = this.loop(Math.random() * 2);
        const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = f; bp.Q.value = 0.55;
        const g = ctx.createGain(); g.gain.value = 0;
        n.connect(bp).connect(g).connect(merge, 0, ch);
        return g;
      };
      this.windL = mk(380, 0); this.windR = mk(540, 1);
      merge.connect(this.air);
    }
    // Inside the cowling: subtle damped metal resonance
    {
      const n = this.loop();
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1480; bp.Q.value = 18;
      const bp2 = ctx.createBiquadFilter(); bp2.type = 'bandpass'; bp2.frequency.value = 2640; bp2.Q.value = 22;
      this.bayRing = ctx.createGain(); this.bayRing.gain.value = 0;
      n.connect(bp).connect(this.bayRing); n.connect(bp2).connect(this.bayRing);
      this.bayRing.connect(this.bus); this.bayRing.connect(this.reverbSend);
    }
    // Sub-bass tension bed
    {
      this.sub = ctx.createGain(); this.sub.gain.value = 0;
      for (const [f, v] of [[41.2, 0.55], [61.7, 0.3], [82.4, 0.12]] as const) {
        const o = ctx.createOscillator(); o.frequency.value = f;
        const og = ctx.createGain(); og.gain.value = v; o.connect(og).connect(this.sub); o.start();
      }
      this.sub.connect(this.bus);
    }
    // Endless Shepard-style rise
    this.riserBus = ctx.createGain(); this.riserBus.gain.value = 0;
    {
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 1400;
      this.riserBus.connect(lp).connect(this.bus); lp.connect(this.reverbSend);
      for (let i = 0; i < 5; i++) {
        const o = ctx.createOscillator(); o.type = 'triangle';
        const g = ctx.createGain(); g.gain.value = 0;
        o.connect(g).connect(this.riserBus); o.start();
        this.riser.push({ o, g });
      }
    }
    // Glide swell pad
    this.swell = ctx.createGain(); this.swell.gain.value = 0;
    {
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 950;
      this.swell.connect(lp); lp.connect(this.bus); lp.connect(this.reverbSend);
      for (const [f, v] of [[73.42, 0.45], [110, 0.35], [146.83, 0.25], [220, 0.16], [277.18, 0.1], [329.63, 0.06]] as const) {
        for (const det of [-4, 4]) {
          const o = ctx.createOscillator(); o.frequency.value = f; o.detune.value = det;
          const og = ctx.createGain(); og.gain.value = v / 2; o.connect(og).connect(this.swell); o.start();
        }
      }
    }
    // Memory reservoir voices
    this.voiceBus = ctx.createGain(); this.voiceBus.gain.value = 0;
    this.voiceBus.connect(this.bus); this.voiceBus.connect(this.reverbSend);
    [110, 164.81, 220, 261.63, 329.63, 392, 493.88, 659.25].forEach((f, i) => {
      const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = f;
      const g = ctx.createGain(); g.gain.value = 0;
      const p = ctx.createStereoPanner(); p.pan.value = -0.8 + (1.6 * i) / 7;
      o.connect(g).connect(p).connect(this.voiceBus); o.start();
      this.voices.push({ o, g });
    });
    // Roll-out rumble
    {
      const n = this.loop();
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 155;
      this.rumble = ctx.createGain(); this.rumble.gain.value = 0;
      n.connect(lp).connect(this.rumble).connect(this.master);
    }
    this.score = new Score(ctx, this.bus, this.reverbSend, this.noise);
    this.stems = new StemPlayer(ctx, this.bus);
  }

  private impulse(seconds: number, decay: number) {
    const rate = this.ctx.sampleRate, len = Math.floor(rate * seconds);
    const buf = this.ctx.createBuffer(2, len, rate);
    const pre = Math.floor(rate * 0.032);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      let lp = 0;
      for (let i = pre; i < len; i++) {
        const env = Math.pow(1 - (i - pre) / (len - pre), decay);
        const raw = (Math.random() * 2 - 1) * env;
        const alpha = 0.25 + 0.55 * (1 - (i - pre) / (len - pre));
        lp = lp + alpha * (raw - lp);
        d[i] = lp;
      }
    }
    return buf;
  }

  private loop(offset = 0) {
    const s = this.ctx.createBufferSource(); s.buffer = this.noise; s.loop = true; s.start(0, offset); return s;
  }

  private duck(depthLinear: number, holdSec: number, releaseSec = 0.45) {
    const now = this.ctx.currentTime;
    this.duckBus.gain.cancelScheduledValues(now);
    this.duckBus.gain.setTargetAtTime(depthLinear, now, 0.025);
    this.duckBus.gain.setTargetAtTime(1, now + holdSec, releaseSec);
  }

  async resume() {
    if (this.ctx.state !== 'running') await this.ctx.resume();
    this.setMuted(this.muted);
  }
  setMuted(m: boolean) {
    this.muted = m;
    const now = this.ctx.currentTime;
    this.master.gain.cancelScheduledValues(now);
    this.master.gain.setTargetAtTime(m ? 0 : 0.85, now, 0.15);
  }
  get isMuted() { return this.muted; }
  setActive(on: boolean) {
    if (this.muted) return;
    const now = this.ctx.currentTime;
    this.master.gain.cancelScheduledValues(now);
    this.master.gain.setTargetAtTime(on ? 0.85 : 0, now, on ? 0.3 : 0.12);
  }

  /* ---------------------------------------------------------------- one-shots */
  private env(node: AudioNode, at: number, peak: number, attack: number, release: number, dest: AudioNode = this.master) {
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(peak, at + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, at + attack + release);
    node.connect(g).connect(dest);
    return g;
  }

  /** Subtle 180 ms reverse-air breath right before T_INJECT cutaway. */
  private preImpactBreath() {
    const ctx = this.ctx, now = ctx.currentTime;
    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass'; bp.Q.value = 1.8;
    bp.frequency.setValueAtTime(300, now);
    bp.frequency.exponentialRampToValueAtTime(1400, now + 0.175);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, now);
    g.gain.exponentialRampToValueAtTime(0.12, now + 0.165);
    g.gain.linearRampToValueAtTime(0.0001, now + 0.18);
    n.connect(bp).connect(g).connect(this.master);
    n.start(now, Math.random()); n.stop(now + 0.19);
  }

  /** Cinema sub-drop impact into the hall. */
  hit(level = 1) {
    const ctx = this.ctx, now = ctx.currentTime;
    const o = ctx.createOscillator();
    o.frequency.setValueAtTime(78, now);
    o.frequency.exponentialRampToValueAtTime(30, now + 1.6);
    const g = this.env(o, now, 0.85 * level, 0.012, 2.4);
    g.connect(this.reverbSend);
    o.start(now); o.stop(now + 2.6);

    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 145;
    this.env(n.connect(lp), now, 0.42 * level, 0.008, 0.9);
    n.start(now); n.stop(now + 1.1);
  }

  /** Damped mechanical chronometer tick. */
  private tick(level: number) {
    const ctx = this.ctx, now = ctx.currentTime;
    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass'; bp.frequency.value = this.tock ? 2900 : 3600; bp.Q.value = 3.2;
    this.env(n.connect(bp), now, 0.11 * level, 0.0015, 0.018, this.bus);
    n.start(now, Math.random()); n.stop(now + 0.03);

    const o = ctx.createOscillator(); o.type = 'sine';
    o.frequency.value = this.tock ? 1120 : 1440;
    this.tock = !this.tock;
    this.env(o, now, 0.045 * level, 0.002, 0.022, this.bus);
    o.start(now); o.stop(now + 0.04);
  }

  /** Authentic VHF aviation radio squelch + -2.8 dB music duck. */
  radio() {
    const ctx = this.ctx, now = ctx.currentTime;
    this.duck(0.72, 0.35, 0.4);

    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1750; bp.Q.value = 1.6;
    this.env(n.connect(bp), now, 0.18, 0.004, 0.095, this.master);
    n.start(now, Math.random()); n.stop(now + 0.14);

    const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = 1120;
    this.env(o, now + 0.075, 0.032, 0.004, 0.055, this.master);
    o.start(now + 0.075); o.stop(now + 0.16);
  }

  /** Ground station cross-cut: quiet room + authentic avionics console chime. */
  ground(dur: number, alertAt: number) {
    const ctx = this.ctx, now = ctx.currentTime;
    this.bus.gain.cancelScheduledValues(now); this.bus.gain.setValueAtTime(0, now);
    const n = ctx.createBufferSource(); n.buffer = this.noise; n.loop = true;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 210;
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, now); g.gain.exponentialRampToValueAtTime(0.065, now + 0.06);
    g.gain.setValueAtTime(0.065, now + dur - 0.05); g.gain.linearRampToValueAtTime(0, now + dur);
    n.connect(lp).connect(g).connect(this.master); n.start(now); n.stop(now + dur + 0.05);

    const chimeRev = ctx.createGain(); chimeRev.gain.value = 0.15;
    chimeRev.connect(this.reverbSend);

    for (const [dt, f] of [[0, 880], [0.16, 660]] as const) {
      const o1 = ctx.createOscillator(); o1.type = 'sine'; o1.frequency.value = f;
      const g1 = this.env(o1, now + alertAt + dt, 0.11, 0.006, 0.18, this.master);
      g1.connect(chimeRev);
      o1.start(now + alertAt + dt); o1.stop(now + alertAt + dt + 0.22);

      const o2 = ctx.createOscillator(); o2.type = 'sine'; o2.frequency.value = f * 2;
      this.env(o2, now + alertAt + dt, 0.025, 0.004, 0.14, this.master);
      o2.start(now + alertAt + dt); o2.stop(now + alertAt + dt + 0.18);
    }
  }

  /** Wheels: crisp rubber-on-asphalt chirp + deep suspension thump. */
  private touchdown() {
    const ctx = this.ctx, now = ctx.currentTime;
    this.duck(0.75, 0.5, 0.6);

    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass'; bp.frequency.setValueAtTime(2100, now);
    bp.frequency.exponentialRampToValueAtTime(1150, now + 0.16); bp.Q.value = 4.5;
    this.env(n.connect(bp), now, 0.34, 0.005, 0.18, this.master);
    n.start(now); n.stop(now + 0.25);

    const o = ctx.createOscillator();
    o.frequency.setValueAtTime(84, now + 0.02);
    o.frequency.exponentialRampToValueAtTime(36, now + 0.34);
    this.env(o, now + 0.02, 0.52, 0.01, 0.32, this.master);
    o.start(now + 0.02); o.stop(now + 0.42);
  }

  cut() {
    const now = this.ctx.currentTime;
    this.bus.gain.cancelScheduledValues(now); this.bus.gain.setValueAtTime(1, now);
  }

  /* ---------------------------------------------------------------- the mix, every frame */
  update(s: SoundState) {
    const { t, r, ci, playing, dt, listener, bay } = s;
    const now = this.ctx.currentTime;
    const id = CHAPTERS[ci].id;
    const k = clamp01((t - STARTS[ci]) / CHAPTERS[ci].dur);
    const set = (p: AudioParam, v: number, tc = 0.12) => p.setTargetAtTime(v, now, tc);
    const forward = this.lastT >= 0 && t > this.lastT && t - this.lastT < 1;

    if (forward) {
      if (this.lastT < T_INJECT - 0.18 && t >= T_INJECT - 0.18) this.preImpactBreath();
      if (this.lastT < T_CONFIRM && t >= T_CONFIRM) {
        this.hit(1);
        this.silenceUntil = now + 1.6;
        this.bus.gain.cancelScheduledValues(now);
        this.bus.gain.setValueAtTime(0, now + 0.02);
        this.bus.gain.setValueAtTime(0, now + 1.4);
        this.bus.gain.linearRampToValueAtTime(1, now + 2.8);
      }
      if (this.lastT < T_TOUCH && t >= T_TOUCH) this.touchdown();
      if (this.lastT < TOTAL && t >= TOTAL) {
        this.bus.gain.cancelScheduledValues(now);
        this.bus.gain.setValueAtTime(1, now);
        this.bus.gain.setValueAtTime(0, now + 1.1);
        window.setTimeout(() => this.hit(0.9), 1100);
      }
    }
    this.lastT = t;

    // Aircraft spatialization: pan, distance and Doppler
    const near = clamp01(1 - (listener.dist - 20) / 900);
    const doppler = 680 / Math.max(300, 680 - Math.max(-300, Math.min(300, listener.closing)));
    const idle = t > T_TOUCH ? clamp01((t - T_TOUCH) / 3) : 0;
    const rpm = r.rpm * (1 - 0.55 * idle) * (t >= TOTAL ? 0.6 : 1);
    const crank = (rpm / 60) * doppler;
    set(this.eng.osc.frequency, crank, 0.06);
    const propRev = rpm / 2.43 / 60;
    set(this.prop.osc.frequency, propRev * 3 * doppler, 0.06);
    set(this.prop.am.frequency, propRev, 0.1);
    set(this.valve.lfo.frequency, rpm / 120, 0.1);
    set(this.eng.pan.pan, bay ? 0 : Math.max(-0.9, Math.min(0.9, listener.pan * 0.8)), 0.08);

    const running = playing && t < TOTAL + 0.5;
    const dead = s.flash;
    const loud = running && !dead ? (bay ? 0.48 : 0.11 + 0.44 * near) * (1 - 0.72 * idle) : 0;
    set(this.eng.g.gain, 0.18 * loud, 0.2);
    set(this.eng.lp.frequency, bay ? 310 : 340 + 1700 * near * near, 0.25);
    set(this.prop.g.gain, (bay ? 0.022 : 0.055 * (0.28 + near)) * (running && !dead ? 1 - 0.85 * idle : 0), dead ? 0.03 : 0.2);
    set(this.valve.g.gain, running && !dead ? (bay ? 0.032 : 0.008 * near) : 0, 0.2);
    set(this.bayRing.gain, bay && running ? 0.009 : 0, 0.3);

    // Breathing Ladakh wind
    const high = dead ? 1.5 : id === 'cold' ? 0.25 + 0.75 * k : id === 'decide' || id === 'divert' ? 0.85 : id === 'land' ? 0.5 * (1 - idle) : 0.42;
    const windBase = running ? (bay ? 0.012 : 0.075 * high) : 0.015;
    set(this.windL.gain, windBase * (1 + 0.14 * Math.sin(t * 0.85)), 0.45);
    set(this.windR.gain, windBase * (1 + 0.14 * Math.cos(t * 0.72)), 0.45);

    // Inside cowling or detector's mind
    const mind = id === 'pipeline' || (id === 'detect' && t < T_CONFIRM) || id === 'memory' || id === 'beyond';
    set(this.airLP.frequency, mind ? 280 : bay ? 380 : 16000, mind ? 0.6 : 0.35);
    set(this.reverbSend.gain, mind ? 0.42 : bay ? 0.32 : 0.22, 0.6);

    // Tension chronometer tick
    const worst = Math.max(...Object.values(r.ratios));
    const ticking = running && t >= startOf('twin') && t < T_CONFIRM;
    if (ticking && now >= this.nextTick && now >= this.silenceUntil) {
      const z = clamp01(worst / 1.6);
      this.tick(0.32 + 0.42 * z);
      this.nextTick = now + Math.max(0.3125, 1.25 - 0.94 * z);
    }
    if (!ticking) this.nextTick = Math.max(this.nextTick, now);
    set(this.sub.gain, running && (id === 'signal' || id === 'pipeline' || id === 'detect') && t < T_CONFIRM ? 0.05 + 0.09 * clamp01(worst) : 0, 1.2);

    const rising = running && (id === 'pipeline' || (id === 'detect' && t < T_CONFIRM)) ? 0.018 + 0.09 * clamp01(worst / 1.5) : 0;
    set(this.riserBus.gain, rising, rising ? 0.6 : 0.05);
    this.riserPhase = (this.riserPhase + (running ? dt / 7 : 0)) % 1;
    this.riser.forEach((v, i) => {
      const pos = (i + this.riserPhase) / this.riser.length;
      v.o.frequency.setTargetAtTime(55 * Math.pow(2, pos * 5), now, 0.02);
      set(v.g.gain, Math.pow(Math.sin(Math.PI * pos), 2) * 0.22, 0.05);
    });

    // FlyHash newly firing units
    const newWinners: number[] = [];
    if (id === 'detect' && running && s.winners) {
      for (const u of s.winners) if (!this.prevWinners.has(u)) newWinners.push(u);
      this.prevWinners = new Set(s.winners);
    } else this.prevWinners.clear();

    // Memory reservoir voices
    set(this.voiceBus.gain, 0, 0.8);
    if (s.memory) this.voices.forEach((v, i) => set(v.g.gain, Math.min(1, Math.abs(s.memory![i * 17 % s.memory!.length])) * 0.45, 0.15));

    // Glide swell + dynamic breathing on decide -> divert/land
    const sw = running && (id === 'divert' || id === 'land') ? (id === 'divert' ? 0.09 + 0.14 * k : 0.22 * (1 - clamp01((t - T_TOUCH - 1) / 5))) : 0;
    set(this.swell.gain, sw * 0.24, id === 'divert' ? 1.4 : 0.8);

    const musicDuck = bay ? 1 : id === 'decide' ? 0.22 : 0;
    this.stems.update(t, running, musicDuck, dead);
    this.score.update({
      t,
      ci,
      playing: running && !dead && !this.stems.hasStemAt(t),
      stage: s.stage,
      newWinners,
      unseen: s.unseen,
      memory: s.memory,
      duck: musicDuck,
    });

    // Roll-out rumble
    const roll = t >= T_TOUCH && t < T_TOUCH + 4.6 ? 1 - (t - T_TOUCH) / 4.6 : 0;
    set(this.rumble.gain, running ? 0.26 * roll * roll : 0, 0.08);
  }

  dispose() {
    this.stems.dispose();
    void this.ctx.close();
  }
}
