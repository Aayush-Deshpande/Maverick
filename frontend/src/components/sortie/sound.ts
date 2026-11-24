// ANUMAAN Sortie Film — Psychoacoustic Cinema Audio Engine (100% Web Audio DSP, zero audio files).
// Master chain: 30Hz sub-cleanup HPF -> 80Hz warmth shelf -> 3.1kHz de-harsh -> soft tape saturator
// -> 3:1 bus glue compressor. Features true 1/f pink-noise Ladakh wind, velvety dual-LPF Rotax hum,
// mechanical escapement chronometer, 180ms pre-impact vacuum breath before T_INJECT, saturated
// missing-fundamental cinema impacts, military VHF radio squelch with sidechain ducking,
// authentic avionics ground chime, and clear touchdown Foley.
import { CHAPTERS, STARTS, TOTAL, T_INJECT, T_TOUCH, startOf } from './story';
import { T_CONFIRM, type Readout } from './timeline';
import { Score } from './score';

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

function makeSaturationCurve(drive = 1.45, samples = 2048) {
  const curve = new Float32Array(samples);
  const norm = Math.tanh(drive);
  for (let i = 0; i < samples; i++) {
    const x = (i * 2) / (samples - 1) - 1;
    curve[i] = Math.tanh(drive * x) / norm;
  }
  return curve as unknown as Float32Array<ArrayBuffer>;
}

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
  private bus: GainNode;      // everything except one-shot impacts; dropped for silences and cuts
  private duckBus: GainNode;  // automatic sidechain ducking for VHF radio & touchdown
  private air: GainNode;      // exterior aircraft + Ladakh wind layers
  private airLP: BiquadFilterNode;
  private reverbSend: GainNode;
  private noise: AudioBuffer;     // white noise (crisp transients, ticks, VHF static, tire chirp)
  private pinkNoise: AudioBuffer; // true 1/f pink noise (Himalayan wind, cowling air, room tone)
  private eng: { osc: OscillatorNode; lp1: BiquadFilterNode; lp2: BiquadFilterNode; g: GainNode; pan: StereoPannerNode };
  private prop: { osc: OscillatorNode; bp: BiquadFilterNode; g: GainNode; am: OscillatorNode };
  private valve: { g: GainNode; lfo: OscillatorNode };
  private windL: { bp: BiquadFilterNode; g: GainNode };
  private windR: { bp: BiquadFilterNode; g: GainNode };
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

    // Cinema Master Bus: 30Hz HPF -> 80Hz warmth -> 3.1kHz fatigue dip -> soft tape glue -> 3:1 compressor
    const masterHP = ctx.createBiquadFilter();
    masterHP.type = 'highpass'; masterHP.frequency.value = 30; masterHP.Q.value = 0.7;

    const masterWarm = ctx.createBiquadFilter();
    masterWarm.type = 'lowshelf'; masterWarm.frequency.value = 80; masterWarm.gain.value = 2.0;

    const masterDeHarsh = ctx.createBiquadFilter();
    masterDeHarsh.type = 'peaking'; masterDeHarsh.frequency.value = 3100; masterDeHarsh.Q.value = 1.0; masterDeHarsh.gain.value = -2.0;

    const masterSat = ctx.createWaveShaper();
    masterSat.curve = makeSaturationCurve(1.25);
    masterSat.oversample = '2x';

    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -14; comp.knee.value = 14; comp.ratio.value = 3.0; comp.attack.value = 0.008; comp.release.value = 0.28;

    this.master = ctx.createGain(); this.master.gain.value = 0;
    this.master
      .connect(masterHP)
      .connect(masterWarm)
      .connect(masterDeHarsh)
      .connect(masterSat)
      .connect(comp)
      .connect(ctx.destination);

    this.duckBus = ctx.createGain(); this.duckBus.gain.value = 1;
    this.duckBus.connect(this.master);

    this.bus = ctx.createGain(); this.bus.connect(this.duckBus);

    // Abbey-Road damped 3.6s dark cathedral hall reverb (160Hz HPF + 3.8kHz LPF, 32ms pre-delay)
    const conv = ctx.createConvolver();
    conv.buffer = this.impulse(3.6, 2.5);
    const revHP = ctx.createBiquadFilter(); revHP.type = 'highpass'; revHP.frequency.value = 160;
    const revLP = ctx.createBiquadFilter(); revLP.type = 'lowpass'; revLP.frequency.value = 3800;
    this.reverbSend = ctx.createGain(); this.reverbSend.gain.value = 0.24;
    const wet = ctx.createGain(); wet.gain.value = 0.56;
    this.reverbSend.connect(conv).connect(revHP).connect(revLP).connect(wet).connect(this.bus);

    // Generate 3s white noise + 3s true 1/f pink noise buffers
    const len = ctx.sampleRate * 3;
    this.noise = ctx.createBuffer(1, len, ctx.sampleRate);
    this.pinkNoise = ctx.createBuffer(1, len, ctx.sampleRate);
    const dw = this.noise.getChannelData(0);
    const dp = this.pinkNoise.getChannelData(0);
    let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
    for (let i = 0; i < len; i++) {
      const w = Math.random() * 2 - 1;
      dw[i] = w;
      b0 = 0.99886 * b0 + w * 0.0555179;
      b1 = 0.99332 * b1 + w * 0.0750759;
      b2 = 0.96900 * b2 + w * 0.1538520;
      b3 = 0.86650 * b3 + w * 0.3104856;
      b4 = 0.55000 * b4 + w * 0.5329522;
      b5 = -0.7616 * b5 - w * 0.0168980;
      dp[i] = Math.max(-1, Math.min(1, (b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362) * 0.11));
      b6 = w * 0.115926;
    }

    // Exterior bus: low-passed when entering the engine cowling or detector's mind
    this.airLP = ctx.createBiquadFilter(); this.airLP.type = 'lowpass'; this.airLP.frequency.value = 15000; this.airLP.Q.value = 0.55;
    this.air = ctx.createGain();
    this.air.connect(this.airLP).connect(this.bus);
    const airRev = ctx.createGain(); airRev.gain.value = 0.22;
    this.airLP.connect(airRev).connect(this.reverbSend);

    // Engine: velvety 4-cyl Rotax firing order through cascaded 24dB/oct lowpass (eliminates mosquito buzz)
    {
      const real = new Float32Array(10), imag = new Float32Array(10);
      [0, 0.55, 1.0, 0.18, 0.34, 0.06, 0.11, 0.025, 0.04, 0.01].forEach((v, i) => { imag[i] = v; });
      const osc = ctx.createOscillator(); osc.setPeriodicWave(ctx.createPeriodicWave(real, imag));
      const lp1 = ctx.createBiquadFilter(); lp1.type = 'lowpass'; lp1.frequency.value = 460; lp1.Q.value = 0.65;
      const lp2 = ctx.createBiquadFilter(); lp2.type = 'lowpass'; lp2.frequency.value = 460; lp2.Q.value = 0.65;
      const g = ctx.createGain(); g.gain.value = 0;
      const pan = ctx.createStereoPanner();
      osc.connect(lp1).connect(lp2).connect(g).connect(pan).connect(this.air); osc.start();
      this.eng = { osc, lp1, lp2, g, pan };
    }
    // Propeller: warm triangle blade-pass throb with crisp aerodynamic blade bite
    {
      const osc = ctx.createOscillator(); osc.type = 'triangle';
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 260; bp.Q.value = 0.8;
      const g = ctx.createGain(); g.gain.value = 0;
      const am = ctx.createOscillator(); am.type = 'sine';
      const amDepth = ctx.createGain(); amDepth.gain.value = 0.22;
      am.connect(amDepth).connect(g.gain);
      osc.connect(bp).connect(g).connect(this.eng.pan); osc.start(); am.start();
      this.prop = { osc, bp, g, am };
    }
    // Valve train: subtle muffled mechanical pulse (pink-noise based)
    {
      const n = this.loop(0, true);
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1950; bp.Q.value = 1.4;
      const g = ctx.createGain(); g.gain.value = 0;
      const lfo = ctx.createOscillator(); lfo.type = 'sine';
      const lg = ctx.createGain(); lg.gain.value = 0.3;
      const gate = ctx.createGain(); gate.gain.value = 0.7;
      lfo.connect(lg).connect(gate.gain);
      n.connect(bp).connect(gate).connect(g).connect(this.eng.pan); lfo.start();
      this.valve = { g, lfo };
    }
    // High-altitude Ladakh wind: decorrelated stereo 1/f pink noise with drifting air-current formants
    {
      const merge = ctx.createChannelMerger(2);
      const mk = (f: number, ch: number) => {
        const n = this.loop(Math.random() * 2.5, true);
        const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = f; bp.Q.value = 0.7;
        const g = ctx.createGain(); g.gain.value = 0;
        n.connect(bp).connect(g).connect(merge, 0, ch);
        return { bp, g };
      };
      this.windL = mk(340, 0); this.windR = mk(490, 1);
      merge.connect(this.air);
    }
    // Inside the cowling: damped aerospace alloy chamber resonance
    {
      const n = this.loop(0, true);
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 920; bp.Q.value = 14;
      const bp2 = ctx.createBiquadFilter(); bp2.type = 'bandpass'; bp2.frequency.value = 1860; bp2.Q.value = 18;
      this.bayRing = ctx.createGain(); this.bayRing.gain.value = 0;
      n.connect(bp).connect(this.bayRing); n.connect(bp2).connect(this.bayRing);
      this.bayRing.connect(this.bus); this.bayRing.connect(this.reverbSend);
    }
    // Sub-bass primal vigilance bed (D1 36.7Hz + A1 55Hz + D2 73.4Hz, zero reverb)
    {
      this.sub = ctx.createGain(); this.sub.gain.value = 0;
      for (const [f, v] of [[36.71, 0.58], [55.0, 0.3], [73.42, 0.14]] as const) {
        const o = ctx.createOscillator(); o.frequency.value = f;
        const og = ctx.createGain(); og.gain.value = v; o.connect(og).connect(this.sub); o.start();
      }
      this.sub.connect(this.bus);
    }
    // Shepard-Risset endless riser (Dunkirk corkscrew illusion)
    this.riserBus = ctx.createGain(); this.riserBus.gain.value = 0;
    {
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 1350;
      this.riserBus.connect(lp).connect(this.bus); lp.connect(this.reverbSend);
      for (let i = 0; i < 6; i++) {
        const o = ctx.createOscillator(); o.type = 'triangle';
        const g = ctx.createGain(); g.gain.value = 0;
        o.connect(g).connect(this.riserBus); o.start();
        this.riser.push({ o, g });
      }
    }
    // Warm low glide foundation pad
    this.swell = ctx.createGain(); this.swell.gain.value = 0;
    {
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 780;
      this.swell.connect(lp); lp.connect(this.bus); lp.connect(this.reverbSend);
      for (const [f, v] of [[73.42, 0.48], [110, 0.34], [146.83, 0.24], [220, 0.14]] as const) {
        for (const det of [-4, 4]) {
          const o = ctx.createOscillator(); o.frequency.value = f; o.detune.value = det;
          const og = ctx.createGain(); og.gain.value = v / 2; o.connect(og).connect(this.swell); o.start();
        }
      }
    }
    // Reservoir shadow voices (backup bus; primary reservoir harmonies live in Score)
    this.voiceBus = ctx.createGain(); this.voiceBus.gain.value = 0;
    this.voiceBus.connect(this.bus); this.voiceBus.connect(this.reverbSend);
    [110, 164.81, 220, 261.63, 329.63, 392, 493.88, 659.25].forEach((f, i) => {
      const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = f;
      const g = ctx.createGain(); g.gain.value = 0;
      const p = ctx.createStereoPanner(); p.pan.value = -0.8 + (1.6 * i) / 7;
      o.connect(g).connect(p).connect(this.voiceBus); o.start();
      this.voices.push({ o, g });
    });
    // Runway roll-out rumble (pink noise through lowpass)
    {
      const n = this.loop(0, true);
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 145;
      this.rumble = ctx.createGain(); this.rumble.gain.value = 0;
      n.connect(lp).connect(this.rumble).connect(this.master);
    }
    this.score = new Score(ctx, this.bus, this.reverbSend, this.noise);
  }

  private impulse(seconds: number, decay: number) {
    const rate = this.ctx.sampleRate, len = Math.floor(rate * seconds);
    const buf = this.ctx.createBuffer(2, len, rate);
    const pre = Math.floor(rate * 0.032);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      let lp = 0;
      for (let i = pre; i < len; i++) {
        const prog = (i - pre) / (len - pre);
        const env = Math.pow(1 - prog, decay);
        const raw = (Math.random() * 2 - 1) * env;
        const alpha = 0.22 + 0.55 * (1 - prog);
        lp = lp + alpha * (raw - lp);
        d[i] = lp;
      }
    }
    return buf;
  }

  private loop(offset = 0, pink = false) {
    const s = this.ctx.createBufferSource();
    s.buffer = pink ? this.pinkNoise : this.noise;
    s.loop = true;
    s.start(0, offset);
    return s;
  }

  private duck(depthLinear: number, holdSec: number, releaseSec = 0.45) {
    const now = this.ctx.currentTime;
    this.duckBus.gain.cancelScheduledValues(now);
    this.duckBus.gain.setTargetAtTime(depthLinear, now, 0.02);
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
    this.master.gain.setTargetAtTime(m ? 0 : 0.9, now, 0.15);
  }
  get isMuted() { return this.muted; }
  setActive(on: boolean) {
    if (this.muted) return;
    const now = this.ctx.currentTime;
    this.master.gain.cancelScheduledValues(now);
    this.master.gain.setTargetAtTime(on ? 0.9 : 0, now, on ? 0.3 : 0.12);
  }

  /* ---------------------------------------------------------------- one-shots */
  private env(node: AudioNode, at: number, peak: number, attack: number, release: number, dest: AudioNode = this.master) {
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(Math.max(0.0002, peak), at + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, at + attack + release);
    node.connect(g).connect(dest);
    return g;
  }

  /** Trailer psychoacoustic inhale: 180ms rising air sweep cutting to 20ms void before T_INJECT. */
  private preImpactBreath() {
    const ctx = this.ctx, now = ctx.currentTime;
    const n = ctx.createBufferSource(); n.buffer = this.pinkNoise;
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass'; bp.Q.value = 1.6;
    bp.frequency.setValueAtTime(260, now);
    bp.frequency.exponentialRampToValueAtTime(1650, now + 0.165);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, now);
    g.gain.exponentialRampToValueAtTime(0.24, now + 0.16);
    g.gain.linearRampToValueAtTime(0.0001, now + 0.175);
    n.connect(bp).connect(g).connect(this.master);
    n.start(now, Math.random()); n.stop(now + 0.19);
  }

  /** Bone-rattling cinema impact: saturated sub-drop (missing-fundamental audible on laptops) + transient snap. */
  hit(level = 1) {
    const ctx = this.ctx, now = ctx.currentTime;

    // Saturated sub-drop (78Hz -> 29Hz) so laptop speakers feel chest thump via 2nd/3rd harmonics
    const o = ctx.createOscillator(); o.type = 'sine';
    o.frequency.setValueAtTime(78, now);
    o.frequency.exponentialRampToValueAtTime(29, now + 1.7);
    const sat = ctx.createWaveShaper(); sat.curve = makeSaturationCurve(2.2);
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 240;
    const g = this.env(o.connect(sat).connect(lp), now, 0.92 * level, 0.01, 2.7);
    g.connect(this.reverbSend);
    o.start(now); o.stop(now + 2.9);

    // Dark air boom
    const n = ctx.createBufferSource(); n.buffer = this.pinkNoise;
    const nlp = ctx.createBiquadFilter(); nlp.type = 'lowpass'; nlp.frequency.value = 180;
    this.env(n.connect(nlp), now, 0.55 * level, 0.008, 1.0);
    n.start(now); n.stop(now + 1.2);

    // Micro mechanical lock transient (gives sharp definition on the exact cut frame)
    const click = ctx.createBufferSource(); click.buffer = this.noise;
    const cbp = ctx.createBiquadFilter(); cbp.type = 'bandpass'; cbp.frequency.value = 2200; cbp.Q.value = 2.0;
    this.env(click.connect(cbp), now, 0.14 * level, 0.002, 0.025);
    click.start(now, Math.random()); click.stop(now + 0.04);
  }

  /** Interstellar-style damped mechanical escapement chronometer tick. */
  private tick(level: number) {
    const ctx = this.ctx, now = ctx.currentTime;
    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass'; bp.frequency.value = this.tock ? 2600 : 3400; bp.Q.value = 3.8;
    this.env(n.connect(bp), now, 0.12 * level, 0.0012, 0.016, this.bus);
    n.start(now, Math.random()); n.stop(now + 0.028);

    const o = ctx.createOscillator(); o.type = 'sine';
    o.frequency.value = this.tock ? 980 : 1320;
    this.tock = !this.tock;
    this.env(o, now, 0.042 * level, 0.0015, 0.022, this.bus);
    o.start(now); o.stop(now + 0.038);
  }

  /** Military aviation VHF radio squelch (PTT click + band-limited static + roger pip) with -3dB ducking. */
  radio() {
    const ctx = this.ctx, now = ctx.currentTime;
    this.duck(0.68, 0.42, 0.45);

    // Band-limited VHF carrier squelch (450-2400 Hz)
    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 480;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2400;
    const sat = ctx.createWaveShaper(); sat.curve = makeSaturationCurve(2.4);
    this.env(n.connect(hp).connect(lp).connect(sat), now, 0.17, 0.003, 0.11, this.master);
    n.start(now, Math.random()); n.stop(now + 0.15);

    // Crisp PTT mic key click + subtle aviation squelch tone
    const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = 1040;
    this.env(o, now + 0.075, 0.036, 0.003, 0.055, this.master);
    o.start(now + 0.075); o.stop(now + 0.16);
  }

  /** Cross-cut to GROUND CONTROL · LEH: dead air, quiet ops room hum, authentic avionics alert chime. */
  ground(dur: number, alertAt: number) {
    const ctx = this.ctx, now = ctx.currentTime;
    this.bus.gain.cancelScheduledValues(now); this.bus.gain.setValueAtTime(0, now);

    // Quiet operations-room air conditioning hum (pink noise lowpassed at 190Hz)
    const n = ctx.createBufferSource(); n.buffer = this.pinkNoise; n.loop = true;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 190;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, now);
    g.gain.exponentialRampToValueAtTime(0.09, now + 0.05);
    g.gain.setValueAtTime(0.09, now + Math.max(0.1, dur - 0.05));
    g.gain.linearRampToValueAtTime(0.0001, now + dur);
    n.connect(lp).connect(g).connect(this.master); n.start(now); n.stop(now + dur + 0.05);

    const chimeRev = ctx.createGain(); chimeRev.gain.value = 0.14;
    chimeRev.connect(this.reverbSend);

    for (const [dt, f] of [[0, 880], [0.16, 659.25]] as const) {
      const o1 = ctx.createOscillator(); o1.type = 'sine'; o1.frequency.value = f;
      const g1 = this.env(o1, now + alertAt + dt, 0.125, 0.005, 0.2, this.master);
      g1.connect(chimeRev);
      o1.start(now + alertAt + dt); o1.stop(now + alertAt + dt + 0.24);

      const o2 = ctx.createOscillator(); o2.type = 'sine'; o2.frequency.value = f * 2;
      this.env(o2, now + alertAt + dt, 0.026, 0.003, 0.14, this.master);
      o2.start(now + alertAt + dt); o2.stop(now + alertAt + dt + 0.18);
    }
  }

  /** Touchdown: crisp rubber-on-asphalt tire chirp + heavy hydraulic gear thump cleanly in front of F major. */
  private touchdown() {
    const ctx = this.ctx, now = ctx.currentTime;
    this.duck(0.68, 0.55, 0.65);

    // Rubber tire spin-up chirp
    const n = ctx.createBufferSource(); n.buffer = this.noise;
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass'; bp.Q.value = 4.2;
    bp.frequency.setValueAtTime(2200, now);
    bp.frequency.exponentialRampToValueAtTime(1080, now + 0.17);
    this.env(n.connect(bp), now, 0.38, 0.004, 0.19, this.master);
    n.start(now); n.stop(now + 0.26);

    // Hydraulic landing gear compression thump
    const o = ctx.createOscillator();
    o.frequency.setValueAtTime(92, now + 0.018);
    o.frequency.exponentialRampToValueAtTime(34, now + 0.35);
    const sat = ctx.createWaveShaper(); sat.curve = makeSaturationCurve(1.8);
    this.env(o.connect(sat), now + 0.018, 0.58, 0.008, 0.34, this.master);
    o.start(now + 0.018); o.stop(now + 0.44);
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
      if (this.lastT < T_INJECT - 0.19 && t >= T_INJECT - 0.19) this.preImpactBreath();
      if (this.lastT < T_CONFIRM && t >= T_CONFIRM) {
        // Gate lock: massive sub-hit -> 1.4s pure breathless silence -> Frisson Dm9 bloom
        this.hit(1.05);
        this.silenceUntil = now + 1.6;
        this.bus.gain.cancelScheduledValues(now);
        this.bus.gain.setValueAtTime(0, now + 0.02);
        this.bus.gain.setValueAtTime(0, now + 1.4);
        this.bus.gain.linearRampToValueAtTime(1, now + 2.85);
      }
      if (this.lastT < T_TOUCH && t >= T_TOUCH) this.touchdown();
      if (this.lastT < TOTAL && t >= TOTAL) {
        this.bus.gain.cancelScheduledValues(now);
        this.bus.gain.setValueAtTime(1, now);
        this.bus.gain.setValueAtTime(0, now + 1.05);
        window.setTimeout(() => this.hit(0.95), 1080);
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
    const loud = running && !dead ? (bay ? 0.44 : 0.11 + 0.42 * near) * (1 - 0.72 * idle) : 0;
    set(this.eng.g.gain, 0.17 * loud, 0.2);
    const engCut = bay ? 290 : 320 + 1350 * near * near;
    set(this.eng.lp1.frequency, engCut, 0.25);
    set(this.eng.lp2.frequency, engCut * 1.15, 0.25);
    set(this.prop.g.gain, (bay ? 0.024 : 0.065 * (0.3 + near)) * (running && !dead ? 1 - 0.85 * idle : 0), dead ? 0.025 : 0.2);
    set(this.valve.g.gain, running && !dead ? (bay ? 0.028 : 0.007 * near) : 0, 0.2);
    set(this.bayRing.gain, bay && running ? 0.011 : 0, 0.3);

    // Breathing Himalayan 1/f pink-noise wind (surges sharply on flash-forward vacuum)
    const high = dead ? 1.85 : id === 'cold' ? 0.35 + 0.65 * k : id === 'decide' || id === 'divert' ? 0.8 : id === 'land' ? 0.52 * (1 - idle) : 0.42;
    const windBase = running ? (bay ? 0.014 : 0.115 * high) : 0.018;
    set(this.windL.g.gain, windBase * (1 + 0.16 * Math.sin(t * 0.78)), 0.4);
    set(this.windR.g.gain, windBase * (1 + 0.16 * Math.cos(t * 0.64)), 0.4);
    set(this.windL.bp.frequency, 310 + 75 * Math.sin(t * 0.42), 0.5);
    set(this.windR.bp.frequency, 460 + 95 * Math.cos(t * 0.37), 0.5);

    // Acoustic claustrophobia inside cowling or detector's mind
    const mind = id === 'pipeline' || (id === 'detect' && t < T_CONFIRM) || id === 'memory' || id === 'beyond';
    set(this.airLP.frequency, mind ? 260 : bay ? 340 : 15000, mind ? 0.55 : 0.3);
    set(this.reverbSend.gain, mind ? 0.4 : bay ? 0.28 : 0.24, 0.6);

    // Accelerating chronometer tick from Twin -> Gate confirmation
    const worst = Math.max(...Object.values(r.ratios));
    const ticking = running && t >= startOf('twin') && t < T_CONFIRM;
    if (ticking && now >= this.nextTick && now >= this.silenceUntil) {
      const z = clamp01(worst / 1.6);
      this.tick(0.35 + 0.45 * z);
      this.nextTick = now + Math.max(0.3125, 1.25 - 0.94 * z);
    }
    if (!ticking) this.nextTick = Math.max(this.nextTick, now);

    // Infrasound primal tension floor (quiet awe during cold/problem, tightening under fault/detect)
    const subLvl = !running || dead ? 0 :
      (id === 'cold' || id === 'problem') ? 0.045 :
      (id === 'signal' || id === 'pipeline' || id === 'detect') && t < T_CONFIRM ? 0.065 + 0.11 * clamp01(worst) :
      0;
    set(this.sub.gain, subLvl, 1.0);

    // Shepard-Risset endless riser through pipeline & detect
    const rising = running && (id === 'pipeline' || (id === 'detect' && t < T_CONFIRM)) ? 0.02 + 0.095 * clamp01(worst / 1.5) : 0;
    set(this.riserBus.gain, rising, rising ? 0.6 : 0.05);
    this.riserPhase = (this.riserPhase + (running ? dt / 7.2 : 0)) % 1;
    this.riser.forEach((v, i) => {
      const pos = (i + this.riserPhase) / this.riser.length;
      v.o.frequency.setTargetAtTime(48 * Math.pow(2, pos * 5.2), now, 0.02);
      set(v.g.gain, Math.pow(Math.sin(Math.PI * pos), 2) * 0.21, 0.05);
    });

    // FlyHash newly firing units
    const newWinners: number[] = [];
    if (id === 'detect' && running && s.winners) {
      for (const u of s.winners) if (!this.prevWinners.has(u)) newWinners.push(u);
      this.prevWinners = new Set(s.winners);
    } else this.prevWinners.clear();

    set(this.voiceBus.gain, 0, 0.8);
    if (s.memory) this.voices.forEach((v, i) => set(v.g.gain, Math.min(1, Math.abs(s.memory![i * 17 % s.memory!.length])) * 0.45, 0.15));

    // Glide foundation pad + breathing score ducking (cowling / Leh ATC / Random Forest split-screen)
    const sw = running && (id === 'divert' || id === 'land') ? (id === 'divert' ? 0.09 + 0.13 * k : 0.2 * (1 - clamp01((t - T_TOUCH - 1) / 5))) : 0;
    set(this.swell.gain, sw * 0.24, id === 'divert' ? 1.4 : 0.8);

    const musicDuck = bay ? 0.92 : id === 'decide' ? 0.26 : id === 'beyond' ? 0.2 : 0;
    this.score.update({
      t,
      ci,
      playing: running && !dead,
      stage: s.stage,
      newWinners,
      unseen: s.unseen,
      memory: s.memory,
      duck: musicDuck,
    });

    // Runway roll-out rumble dying smoothly with aircraft deceleration
    const roll = t >= T_TOUCH && t < T_TOUCH + 4.8 ? 1 - (t - T_TOUCH) / 4.8 : 0;
    set(this.rumble.gain, running ? 0.3 * roll * roll : 0, 0.08);
  }

  dispose() { void this.ctx.close(); }
}
