// The film's sound, synthesised in the browser (no audio files). Layers follow what is on screen:
//   exterior  engine (crank/firing harmonics), 3-blade propeller blade-pass, valve-train chatter, stereo wind;
//             panned, filtered and Doppler-shifted from the aircraft's position relative to the camera
//   bay       the same engine heard from inside the cowling: muffled, resonant, close
//   detect    the world low-passed away; each FlyHash unit that newly fires is a pitched ping, placed by column
//   memory    eight voices whose loudness follows eight real reservoir nodes
//   score     sub-bass tension, an endless rise through the drift, a slow organ swell for the glide
//   events    radio squelch, ground-station room and alert, the gate's hit and silence, one tyre chirp,
//             a suspension thump and a roll-out rumble that dies with speed
// Everything is driven from story time by update(); one-shots fire only when time moves forward through them.
import { CHAPTERS, STARTS, TOTAL, T_TOUCH, startOf } from './story';
import { T_CONFIRM, type Readout } from './timeline';
import { Score } from './score';

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

  constructor() {
    const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = (this.ctx = new AC());
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -16; comp.ratio.value = 3.5; comp.attack.value = 0.006; comp.release.value = 0.3;
    this.master = ctx.createGain(); this.master.gain.value = 0;
    this.master.connect(comp).connect(ctx.destination);
    this.bus = ctx.createGain(); this.bus.connect(this.master);

    // a large space: generated stereo impulse response, used as a send
    const conv = ctx.createConvolver();
    conv.buffer = this.impulse(5.2, 2.9); // a large stone space for the organ
    this.reverbSend = ctx.createGain(); this.reverbSend.gain.value = 0.25;
    const wet = ctx.createGain(); wet.gain.value = 0.55;
    this.reverbSend.connect(conv).connect(wet).connect(this.bus);

    const len = ctx.sampleRate * 2;
    this.noise = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = this.noise.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;

    // exterior bus, low-passed when the film goes into the detector's head
    this.airLP = ctx.createBiquadFilter(); this.airLP.type = 'lowpass'; this.airLP.frequency.value = 18000; this.airLP.Q.value = 0.5;
    this.air = ctx.createGain();
    this.air.connect(this.airLP).connect(this.bus);
    this.airLP.connect(this.reverbSend);

    // engine: a periodic wave at crank rate, strongest at the flat-four's 2nd order (two firings per rev)
    {
      const real = new Float32Array(16), imag = new Float32Array(16);
      [0, 0.35, 1, 0.22, 0.55, 0.12, 0.3, 0.08, 0.16, 0.05, 0.09, 0.03, 0.05, 0.02, 0.03, 0.01].forEach((v, i) => { imag[i] = v; });
      const osc = ctx.createOscillator(); osc.setPeriodicWave(ctx.createPeriodicWave(real, imag));
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 900; lp.Q.value = 0.9;
      const g = ctx.createGain(); g.gain.value = 0;
      const pan = ctx.createStereoPanner();
      osc.connect(lp).connect(g).connect(pan).connect(this.air); osc.start();
      this.eng = { osc, lp, g, pan };
    }
    // propeller: blade-pass tone, amplitude-modulated once per revolution
    {
      const osc = ctx.createOscillator(); osc.type = 'sawtooth';
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 320; bp.Q.value = 0.7;
      const g = ctx.createGain(); g.gain.value = 0;
      const am = ctx.createOscillator(); am.type = 'sine';
      const amDepth = ctx.createGain(); amDepth.gain.value = 0.35;
      am.connect(amDepth).connect(g.gain);
      osc.connect(bp).connect(g).connect(this.eng.pan); osc.start(); am.start();
      this.prop = { osc, bp, g, am };
    }
    // valve train: high-passed noise gated at cam rate
    {
      const n = this.loop();
      const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 3200;
      const g = ctx.createGain(); g.gain.value = 0;
      const lfo = ctx.createOscillator(); lfo.type = 'square';
      const lg = ctx.createGain(); lg.gain.value = 0.5;
      const gate = ctx.createGain(); gate.gain.value = 0.5;
      lfo.connect(lg).connect(gate.gain);
      n.connect(hp).connect(gate).connect(g).connect(this.eng.pan); lfo.start();
      this.valve = { g, lfo };
    }
    // wind, decorrelated left and right
    {
      const merge = ctx.createChannelMerger(2);
      const mk = (f: number, ch: number) => {
        const n = this.loop(Math.random() * 2);
        const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = f; bp.Q.value = 0.45;
        const g = ctx.createGain(); g.gain.value = 0;
        n.connect(bp).connect(g).connect(merge, 0, ch);
        return g;
      };
      this.windL = mk(430, 0); this.windR = mk(610, 1);
      merge.connect(this.air);
    }
    // inside the cowling: a resonant metal ring
    {
      const n = this.loop();
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1850; bp.Q.value = 26;
      const bp2 = ctx.createBiquadFilter(); bp2.type = 'bandpass'; bp2.frequency.value = 3170; bp2.Q.value = 30;
      this.bayRing = ctx.createGain(); this.bayRing.gain.value = 0;
      n.connect(bp).connect(this.bayRing); n.connect(bp2).connect(this.bayRing);
      this.bayRing.connect(this.bus); this.bayRing.connect(this.reverbSend);
    }
    // sub-bass tension bed
    {
      this.sub = ctx.createGain(); this.sub.gain.value = 0;
      for (const [f, v] of [[41.2, 0.6], [61.7, 0.35], [82.4, 0.15]] as const) {
        const o = ctx.createOscillator(); o.frequency.value = f;
        const og = ctx.createGain(); og.gain.value = v; o.connect(og).connect(this.sub); o.start();
      }
      this.sub.connect(this.bus);
    }
    // endless rise: octave-spaced voices, loudest mid-range
    this.riserBus = ctx.createGain(); this.riserBus.gain.value = 0;
    {
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 1800;
      this.riserBus.connect(lp).connect(this.bus); lp.connect(this.reverbSend);
      for (let i = 0; i < 5; i++) {
        const o = ctx.createOscillator(); o.type = 'triangle';
        const g = ctx.createGain(); g.gain.value = 0;
        o.connect(g).connect(this.riserBus); o.start();
        this.riser.push({ o, g });
      }
    }
    // the glide swell: an open chord, mostly in the reverb
    this.swell = ctx.createGain(); this.swell.gain.value = 0;
    {
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 1100;
      this.swell.connect(lp); lp.connect(this.bus); lp.connect(this.reverbSend);
      for (const [f, v] of [[73.42, 0.5], [110, 0.38], [146.83, 0.3], [220, 0.2], [277.18, 0.12], [329.63, 0.08]] as const) {
        for (const det of [-5, 5]) {
          const o = ctx.createOscillator(); o.frequency.value = f; o.detune.value = det;
          const og = ctx.createGain(); og.gain.value = v / 2; o.connect(og).connect(this.swell); o.start();
        }
      }
    }
    // memory: eight voices, each following one reservoir node
    this.voiceBus = ctx.createGain(); this.voiceBus.gain.value = 0;
    this.voiceBus.connect(this.bus); this.voiceBus.connect(this.reverbSend);
    [110, 164.81, 220, 261.63, 329.63, 392, 493.88, 659.25].forEach((f, i) => {
      const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = f;
      const g = ctx.createGain(); g.gain.value = 0;
      const p = ctx.createStereoPanner(); p.pan.value = -0.8 + (1.6 * i) / 7;
      o.connect(g).connect(p).connect(this.voiceBus); o.start();
      this.voices.push({ o, g });
    });
    // roll-out rumble
    {
      const n = this.loop();
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 180;
      this.rumble = ctx.createGain(); this.rumble.gain.value = 0;
      n.connect(lp).connect(this.rumble).connect(this.bus);
    }
    this.score = new Score(ctx, this.bus, this.reverbSend, this.noise);
  }

  getMediaStream(): MediaStreamAudioDestinationNode {
    const dest = this.ctx.createMediaStreamDestination();
    this.master.connect(dest);
    return dest;
  }

  private impulse(seconds: number, decay: number) {
    const rate = this.ctx.sampleRate, len = Math.floor(rate * seconds);
    const buf = this.ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      const pre = Math.floor(rate * 0.025);
      for (let i = pre; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - (i - pre) / (len - pre), decay);
    }
    return buf;
  }
  private loop(offset = 0) {
    const s = this.ctx.createBufferSource(); s.buffer = this.noise; s.loop = true; s.start(0, offset); return s;
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
  /** Fade out while the film is off screen or the tab is hidden; back in when it returns. */
  setActive(on: boolean) {
    if (this.muted) return;
    const now = this.ctx.currentTime;
    this.master.gain.cancelScheduledValues(now);
    this.master.gain.setTargetAtTime(on ? 0.85 : 0, now, on ? 0.3 : 0.12);
  }

  /* ---------------------------------------------------------------- one-shots */
  private env(node: AudioNode, at: number, peak: number, attack: number, release: number, dest: AudioNode = this.master) {
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at); g.gain.exponentialRampToValueAtTime(peak, at + attack); g.gain.exponentialRampToValueAtTime(0.0001, at + attack + release);
    node.connect(g).connect(dest);
    return g;
  }
  /** A low impact: a falling sub tone with dark noise, into the space. */
  hit(level = 1) {
    const ctx = this.ctx, now = ctx.currentTime;
    const o = ctx.createOscillator(); o.frequency.setValueAtTime(82, now); o.frequency.exponentialRampToValueAtTime(29, now + 1.8);
    const g = this.env(o, now, 0.9 * level, 0.015, 2.6); g.connect(this.reverbSend);
    o.start(now); o.stop(now + 2.8);
    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 160;
    this.env(n.connect(lp), now, 0.45 * level, 0.01, 1.0);
    n.start(now); n.stop(now + 1.2);
  }
  private tick(level: number) {
    const ctx = this.ctx, now = ctx.currentTime;
    const o = ctx.createOscillator(); o.type = 'square'; o.frequency.value = this.tock ? 1250 : 1650;
    this.tock = !this.tock;
    const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 900;
    this.env(o.connect(hp), now, 0.14 * level, 0.002, 0.035, this.bus);
    o.start(now); o.stop(now + 0.06);
  }
  radio() {
    const ctx = this.ctx, now = ctx.currentTime;
    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 2200; bp.Q.value = 1.4;
    this.env(n.connect(bp), now, 0.2, 0.01, 0.15);
    n.start(now); n.stop(now + 0.2);
    const o = ctx.createOscillator(); o.frequency.value = 1180;
    this.env(o, now + 0.12, 0.05, 0.005, 0.07);
    o.start(now + 0.12); o.stop(now + 0.22);
  }
  /** Cross-cut to the ground station: the air drops out, a quiet room, the console's alert as the gate fires. */
  ground(dur: number, alertAt: number) {
    const ctx = this.ctx, now = ctx.currentTime;
    this.bus.gain.cancelScheduledValues(now); this.bus.gain.setValueAtTime(0, now);
    const n = ctx.createBufferSource(); n.buffer = this.noise; n.loop = true;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 240;
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, now); g.gain.exponentialRampToValueAtTime(0.08, now + 0.06);
    g.gain.setValueAtTime(0.08, now + dur - 0.05); g.gain.linearRampToValueAtTime(0, now + dur);
    n.connect(lp).connect(g).connect(this.master); n.start(now); n.stop(now + dur + 0.05);
    for (const [dt, f] of [[0, 880], [0.16, 660]] as const) {
      const o = ctx.createOscillator(); o.frequency.value = f;
      this.env(o, now + alertAt + dt, 0.13, 0.008, 0.13);
      o.start(now + alertAt + dt); o.stop(now + alertAt + dt + 0.16);
    }
  }
  /** Wheels: one short chirp as the main gear spins up, and the thump of the suspension taking the weight. */
  private touchdown() {
    const ctx = this.ctx, now = ctx.currentTime;
    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.setValueAtTime(1500, now); bp.frequency.exponentialRampToValueAtTime(900, now + 0.18); bp.Q.value = 4;
    this.env(n.connect(bp), now, 0.28, 0.008, 0.2, this.bus);
    n.start(now); n.stop(now + 0.3);
    const o = ctx.createOscillator(); o.frequency.setValueAtTime(70, now + 0.03); o.frequency.exponentialRampToValueAtTime(42, now + 0.35);
    this.env(o, now + 0.03, 0.42, 0.012, 0.32, this.bus);
    o.start(now + 0.03); o.stop(now + 0.45);
  }
  /** Back from a cut: the world returns at once. */
  cut() {
    const now = this.ctx.currentTime;
    this.bus.gain.cancelScheduledValues(now); this.bus.gain.setValueAtTime(1, now);
  }

  /* ---------------------------------------------------------------- the mix, every frame */
  update(s: SoundState) {
    const { t, r, ci, playing, dt, listener, bay } = s;
    const ctx = this.ctx, now = ctx.currentTime;
    const id = CHAPTERS[ci].id;
    const k = clamp01((t - STARTS[ci]) / CHAPTERS[ci].dur);
    const set = (p: AudioParam, v: number, tc = 0.12) => p.setTargetAtTime(v, now, tc);
    const forward = this.lastT >= 0 && t > this.lastT && t - this.lastT < 1;

    if (forward) {
      if (this.lastT < T_CONFIRM && t >= T_CONFIRM) {
        // back from the ground station onto the lock: the hit, then silence
        this.hit(1);
        this.silenceUntil = now + 1.6;
        this.bus.gain.cancelScheduledValues(now); this.bus.gain.setValueAtTime(0, now + 0.02);
        this.bus.gain.setValueAtTime(0, now + 1.4); this.bus.gain.linearRampToValueAtTime(1, now + 2.8);
      }
      if (this.lastT < T_TOUCH && t >= T_TOUCH) this.touchdown();
      if (this.lastT < TOTAL && t >= TOTAL) {
        this.bus.gain.cancelScheduledValues(now); this.bus.gain.setValueAtTime(1, now); this.bus.gain.setValueAtTime(0, now + 1.1);
        window.setTimeout(() => this.hit(0.9), 1100);
      }
    }
    this.lastT = t;

    // where the aircraft is: pan, distance and Doppler (1 unit ≈ 0.5 m; sound ≈ 680 units/s)
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
    const loud = running && !dead ? (bay ? 0.55 : 0.12 + 0.5 * near) * (1 - 0.7 * idle) : 0;
    set(this.eng.g.gain, 0.2 * loud, 0.2);
    set(this.eng.lp.frequency, bay ? 340 : 380 + 2400 * near * near, 0.25);
    set(this.prop.g.gain, (bay ? 0.03 : 0.07 * (0.3 + near)) * (running && !dead ? 1 - 0.85 * idle : 0), dead ? 0.03 : 0.2);
    set(this.valve.g.gain, running && !dead ? (bay ? 0.05 : 0.012 * near) : 0, 0.2);
    set(this.bayRing.gain, bay && running ? 0.012 : 0, 0.3);

    const high = dead ? 1.6 : id === 'cold' ? 0.25 + 0.75 * k : id === 'decide' || id === 'divert' ? 0.9 : id === 'land' ? 0.5 * (1 - idle) : 0.45;
    const windLevel = running ? (bay ? 0.015 : 0.09 * high) : 0.02;
    set(this.windL.gain, windLevel, 0.5); set(this.windR.gain, windLevel, 0.5);

    // into the detector's head: the outside goes dull
    const mind = id === 'pipeline' || (id === 'detect' && t < T_CONFIRM) || id === 'memory' || id === 'beyond';
    set(this.airLP.frequency, mind ? 300 : bay ? 1200 : 18000, mind ? 0.6 : 0.3);
    set(this.reverbSend.gain, mind ? 0.45 : bay ? 0.35 : 0.2, 0.6);

    // tension: the watch tick from the twin to the confirmation, tightening with the strongest scorer
    const worst = Math.max(...Object.values(r.ratios));
    const ticking = running && t >= startOf('twin') && t < T_CONFIRM;
    if (ticking && now >= this.nextTick && now >= this.silenceUntil) {
      const z = clamp01(worst / 1.6);
      this.tick(0.35 + 0.45 * z);
      this.nextTick = now + Math.max(0.3125, 1.25 - 0.94 * z); // a 1.25 s pulse, tightening with the strongest scorer
    }
    if (!ticking) this.nextTick = Math.max(this.nextTick, now);
    set(this.sub.gain, running && (id === 'signal' || id === 'pipeline' || id === 'detect') && t < T_CONFIRM ? 0.05 + 0.1 * clamp01(worst) : 0, 1.2);

    const rising = running && (id === 'pipeline' || (id === 'detect' && t < T_CONFIRM)) ? 0.02 + 0.11 * clamp01(worst / 1.5) : 0;
    set(this.riserBus.gain, rising, rising ? 0.6 : 0.05);
    this.riserPhase = (this.riserPhase + (running ? dt / 7 : 0)) % 1;
    this.riser.forEach((v, i) => {
      const pos = (i + this.riserPhase) / this.riser.length;
      v.o.frequency.setTargetAtTime(55 * Math.pow(2, pos * 5), now, 0.02);
      set(v.g.gain, Math.pow(Math.sin(Math.PI * pos), 2) * 0.25, 0.05);
    });

    // FlyHash: the units that newly fire this frame become bells in the score
    const newWinners: number[] = [];
    if (id === 'detect' && running && s.winners) {
      for (const u of s.winners) if (!this.prevWinners.has(u)) newWinners.push(u);
      this.prevWinners = new Set(s.winners);
    } else this.prevWinners.clear();

    // memory: eight voices follow eight real reservoir nodes
    set(this.voiceBus.gain, 0, 0.8); // the score's organ pipes carry the reservoir now
    if (s.memory) this.voices.forEach((v, i) => set(v.g.gain, Math.min(1, Math.abs(s.memory![i * 17 % s.memory!.length])) * 0.5, 0.15));

    // the glide swell
    const sw = running && (id === 'divert' || id === 'land') ? (id === 'divert' ? 0.1 + 0.16 * k : 0.26 * (1 - clamp01((t - T_TOUCH - 1) / 5))) : 0;
    set(this.swell.gain, sw * 0.25, id === 'divert' ? 1.4 : 0.8); // a pad under the score's organ
    this.score.update({ t, ci, playing: running && !dead, stage: s.stage, newWinners, unseen: s.unseen, memory: s.memory, duck: bay ? 1 : 0 });

    // roll-out rumble, dying with speed
    const roll = t >= T_TOUCH && t < T_TOUCH + 4.6 ? 1 - (t - T_TOUCH) / 4.6 : 0;
    set(this.rumble.gain, running ? 0.22 * roll * roll : 0, 0.08);
  }

  dispose() { void this.ctx.close(); }
}
