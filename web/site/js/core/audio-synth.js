/**
 * PROJECT ANUMAAN — PROCEDURAL AEROSPACE AUDIO SYNTHESIZER
 * Built using native Web Audio API (Zero external MP3/WAV assets needed)
 * Generates: Subsonic aero-piston drone hum, tactical UI clicks, caution chimes, warning klaxons
 */

class TacticalAudioSynthesizer {
  constructor() {
    this.ctx = null;
    this.engineOsc1 = null;
    this.engineOsc2 = null;
    this.engineGain = null;
    this.engineFilter = null;
    this.isEngineRunning = false;
    this.enabled = false;
  }

  init() {
    if (!this.ctx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioContext();
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  toggleAudio(enable) {
    this.enabled = enable;
    if (enable) {
      this.init();
      this.startEngineDrone();
    } else {
      this.stopEngineDrone();
    }
    return this.enabled;
  }

  // Continuous Subsonic Aero Piston Engine Drone
  startEngineDrone() {
    if (!this.ctx || !this.enabled || this.isEngineRunning) return;

    try {
      const t = this.ctx.currentTime;
      
      // Dual oscillator for rich mechanical engine rumble
      this.engineOsc1 = this.ctx.createOscillator();
      this.engineOsc2 = this.ctx.createOscillator();
      this.engineGain = this.ctx.createGain();
      this.engineFilter = this.ctx.createBiquadFilter();

      // Fundamental engine firing frequency ~ 85 Hz (corresponds to ~5100 RPM 4-cylinder 4-stroke)
      this.engineOsc1.type = 'sawtooth';
      this.engineOsc1.frequency.setValueAtTime(85, t);

      // Sub-harmonic tone for deep airframe resonance
      this.engineOsc2.type = 'triangle';
      this.engineOsc2.frequency.setValueAtTime(42.5, t);

      // Low-pass filter to simulate engine cowling and fuselage dampening
      this.engineFilter.type = 'lowpass';
      this.engineFilter.frequency.setValueAtTime(260, t);
      this.engineFilter.Q.setValueAtTime(2.5, t);

      // Master engine volume (low, pleasant cockpit rumble)
      this.engineGain.gain.setValueAtTime(0.001, t);
      this.engineGain.gain.exponentialRampToValueAtTime(0.08, t + 1.5);

      this.engineOsc1.connect(this.engineFilter);
      this.engineOsc2.connect(this.engineFilter);
      this.engineFilter.connect(this.engineGain);
      this.engineGain.connect(this.ctx.destination);

      this.engineOsc1.start(t);
      this.engineOsc2.start(t);
      this.isEngineRunning = true;
    } catch (e) {
      console.warn("Audio init warning:", e);
    }
  }

  updateEngineRPM(rpm) {
    if (!this.isEngineRunning || !this.ctx) return;
    // 4-cylinder 4-stroke: Firing freq = RPM / 60
    const freq = Math.max(30, Math.min(150, (rpm / 60)));
    const t = this.ctx.currentTime;
    this.engineOsc1.frequency.setTargetAtTime(freq, t, 0.1);
    this.engineOsc2.frequency.setTargetAtTime(freq / 2, t, 0.1);
  }

  stopEngineDrone() {
    if (!this.isEngineRunning || !this.ctx) return;
    try {
      const t = this.ctx.currentTime;
      this.engineGain.gain.exponentialRampToValueAtTime(0.0001, t + 0.5);
      setTimeout(() => {
        if (this.engineOsc1) this.engineOsc1.stop();
        if (this.engineOsc2) this.engineOsc2.stop();
        this.isEngineRunning = false;
      }, 550);
    } catch (e) {}
  }

  // Tactical HUD UI Click / Beep
  playUiClick() {
    if (!this.enabled || !this.ctx) return;
    try {
      const t = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(1400, t);
      osc.frequency.exponentialRampToValueAtTime(800, t + 0.04);

      gain.gain.setValueAtTime(0.04, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.04);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(t);
      osc.stop(t + 0.05);
    } catch (e) {}
  }

  // Caution Amber Alert (First Whisper / Anomaly Detection)
  playCautionChime() {
    if (!this.enabled || !this.ctx) return;
    try {
      const t = this.ctx.currentTime;
      const osc1 = this.ctx.createOscillator();
      const osc2 = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc1.type = 'sine';
      osc2.type = 'sine';
      osc1.frequency.setValueAtTime(660, t); // E5
      osc2.frequency.setValueAtTime(880, t + 0.12); // A5

      gain.gain.setValueAtTime(0.06, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.45);

      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(this.ctx.destination);

      osc1.start(t);
      osc1.stop(t + 0.14);
      osc2.start(t + 0.12);
      osc2.stop(t + 0.45);
    } catch (e) {}
  }

  // Warning Red Klaxon (Critical Fault / Failure)
  playWarningAlarm() {
    if (!this.enabled || !this.ctx) return;
    try {
      const t = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(950, t);
      osc.frequency.linearRampToValueAtTime(650, t + 0.22);

      gain.gain.setValueAtTime(0.07, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.24);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(t);
      osc.stop(t + 0.25);
    } catch (e) {}
  }

  // Trigger Alert Sound by State
  triggerAlert(level) {
    if (!this.enabled || !this.ctx) return;
    if (level === 'WARNING' || level === 'CRITICAL') {
      this.playWarningAlarm();
    } else if (level === 'CAUTION') {
      this.playCautionChime();
    } else {
      this.playUiClick();
    }
  }
}

window.tacticalAudio = new TacticalAudioSynthesizer();
