/**
 * ANUMAAN Telemetry Simulation Engine
 * 20 Hz high-fidelity physics simulator, residual oscilloscope,
 * RUL particle filter, and SAARTHI prescriptive advisory system.
 */

class TelemetrySimEngine {
  constructor(state, audioSynth) {
    this.state = state;
    this.audioSynth = audioSynth;
    this.intervalId = null;
    this.tickRate = 50; // 20 Hz = 50ms

    // Residual oscilloscope canvas
    this.canvas = null;
    this.ctx = null;
    this.residualHistory = [];
    this.maxHistoryLength = 200;

    // Base nominal parameters (Rotax 912 iS / Austro AE300 / DRDO MALE UAV powerplant)
    this.nominal = {
      rpm: 2350,
      map: 1.95, // bar
      cht: [138.2, 140.5, 139.1, 141.0], // °C
      egt: [682.0, 688.5, 684.0, 689.2], // °C
      oilTemp: 92.4, // °C
      oilPress: 4.25, // bar
      coolantTemp: 84.6, // °C
      coolantPress: 1.85, // bar
      railPress: 1610, // bar
      fuelFlow: 24.6, // kg/h
      vibeRms: 0.12, // g RMS
      busVolts: 28.2, // V
      busAmps: 42.5, // A
      densityAlt: 18500 // ft
    };

    // Initialize residual history buffer
    for (let i = 0; i < this.maxHistoryLength; i++) {
      this.residualHistory.push({
        t: i,
        residual: 0.05 + (Math.random() - 0.5) * 0.04,
        threshold: 0.85,
        healthyBand: 0.20
      });
    }

    this.simTime = 0;
    this.setupListeners();
  }

  setupListeners() {
    this.state.on('faultChanged', (fault) => {
      this.handleFaultChange(fault);
    });
  }

  initCanvas(canvasElement) {
    this.canvas = canvasElement;
    if (this.canvas) {
      this.ctx = this.canvas.getContext('2d');
      this.resizeCanvas();
      window.addEventListener('resize', () => this.resizeCanvas());
    }
  }

  resizeCanvas() {
    if (!this.canvas) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width * (window.devicePixelRatio || 1);
    this.canvas.height = rect.height * (window.devicePixelRatio || 1);
    this.ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
  }

  start() {
    if (this.intervalId) return;
    this.intervalId = setInterval(() => this.step(), this.tickRate);
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  handleFaultChange(fault) {
    const current = this.state.get();
    if (fault === 'none') {
      this.state.update({
        alertLevel: 'NOMINAL',
        saarthiAdvisory: 'ALL SYSTEMS NOMINAL. Digital twin tracking within 99.4% Bayesian confidence bounds.',
        rulHours: 450.0,
        rulConfidence: 98.6
      });
      if (this.audioSynth && typeof this.audioSynth.triggerAlert === 'function') this.audioSynth.triggerAlert('NOMINAL');
    } else if (fault === 'combustion_cyl3') {
      this.state.update({
        alertLevel: 'WARNING',
        saarthiAdvisory: 'CRITICAL: Cyl 3 micro-thermal runaway detected (residual +18.4°C divergence). Throttle to 65% MCP (2100 RPM). Reroute to FOB Bravo (ETA 18 min, safety margin +42 min).',
        rulHours: 4.2,
        rulConfidence: 94.2
      });
      if (this.audioSynth && typeof this.audioSynth.triggerAlert === 'function') this.audioSynth.triggerAlert('WARNING');
    } else if (fault === 'coolant_loss') {
      this.state.update({
        alertLevel: 'CRITICAL',
        saarthiAdvisory: 'EMERGENCY: Coolant loop decompression. Core thermal dissipation degraded 38%. Initiate immediate controlled descent to 8,000 ft MSL. Divert to primary runway.',
        rulHours: 1.4,
        rulConfidence: 96.8
      });
      if (this.audioSynth && typeof this.audioSynth.triggerAlert === 'function') this.audioSynth.triggerAlert('CRITICAL');
    } else if (fault === 'rail_pressure') {
      this.state.update({
        alertLevel: 'CAUTION',
        saarthiAdvisory: 'CAUTION: Common rail fuel pressure droop (ΔP = -310 bar). High-pressure pump metering valve hysteresis. Limit rapid throttle transients.',
        rulHours: 18.5,
        rulConfidence: 91.5
      });
      if (this.audioSynth && typeof this.audioSynth.triggerAlert === 'function') this.audioSynth.triggerAlert('CAUTION');
    } else if (fault === 'intercooler_fouling') {
      this.state.update({
        alertLevel: 'CAUTION',
        saarthiAdvisory: 'ADVISORY: Intercooler core thermal efficiency -24%. Turbo compressor discharge temp elevated. Density altitude ceiling degraded to FL210.',
        rulHours: 64.0,
        rulConfidence: 89.0
      });
      if (this.audioSynth && typeof this.audioSynth.triggerAlert === 'function') this.audioSynth.triggerAlert('CAUTION');
    } else if (fault === 'sensor_suspect') {
      this.state.update({
        alertLevel: 'CAUTION',
        saarthiAdvisory: 'NADI SENSOR FAULT: Inductive Crank Pick-Up A jitter (+/- 140 RPM). Redundant Hall Sensor B cross-correlation verified nominal. Sensor A isolated from control loop.',
        rulHours: 320.0,
        rulConfidence: 99.1
      });
      if (this.audioSynth && typeof this.audioSynth.triggerAlert === 'function') this.audioSynth.triggerAlert('CAUTION');
    }
  }

  step() {
    this.simTime += 0.05;
    const current = this.state.get();
    const fault = current.activeFault;

    // Jitter & Micro-oscillations
    const jitter = (Math.random() - 0.5) * 0.04;
    const rpmJitter = (Math.random() - 0.5) * 6;

    let rpm = this.nominal.rpm + rpmJitter;
    let map = this.nominal.map + jitter * 0.05;
    let cht = [...this.nominal.cht];
    let egt = [...this.nominal.egt];
    let oilTemp = this.nominal.oilTemp + jitter * 0.2;
    let oilPress = this.nominal.oilPress + jitter * 0.03;
    let railPress = this.nominal.railPress + (Math.random() - 0.5) * 8;
    let fuelFlow = this.nominal.fuelFlow + jitter * 0.1;
    let vibe = this.nominal.vibeRms + Math.abs(jitter * 0.05);

    let residualVal = 0.08 + Math.abs(jitter * 0.05);

    // Apply Fault Physics Dynamics
    if (fault === 'combustion_cyl3') {
      // Cylinder 3 thermal runaway
      cht[2] += 18.4 + Math.sin(this.simTime * 2) * 1.2;
      egt[2] -= 42.0 + Math.cos(this.simTime * 2) * 2.5; // incomplete combustion / unburned fuel cooling EGT probe
      vibe += 0.38 + Math.sin(this.simTime * 8) * 0.08;
      residualVal = 1.42 + Math.sin(this.simTime * 3) * 0.12; // Far above 0.85 threshold
    } else if (fault === 'coolant_loss') {
      // All cylinders rising
      cht[0] += 26.5;
      cht[1] += 28.1;
      cht[2] += 29.4;
      cht[3] += 27.2;
      oilTemp += 19.5;
      oilPress -= 0.85;
      residualVal = 1.85 + Math.sin(this.simTime * 1.5) * 0.15;
    } else if (fault === 'rail_pressure') {
      railPress = 1290 + Math.sin(this.simTime * 4) * 45;
      rpm += Math.sin(this.simTime * 2) * 35; // hunting
      fuelFlow -= 3.2;
      residualVal = 0.95 + Math.sin(this.simTime * 2) * 0.08;
    } else if (fault === 'intercooler_fouling') {
      map -= 0.28;
      fuelFlow += 1.4; // richer compensation
      residualVal = 0.72 + Math.sin(this.simTime) * 0.05;
    } else if (fault === 'sensor_suspect') {
      if (Math.random() < 0.25) {
        rpm += (Math.random() - 0.5) * 280; // spike
      }
      residualVal = 0.88 + (Math.random() - 0.5) * 0.3;
    }

    // Update telemetry in state
    this.state.update({
      telemetry: {
        rpm: Math.round(rpm),
        map: Number(map.toFixed(2)),
        cht: cht.map(c => Number(c.toFixed(1))),
        egt: egt.map(e => Number(e.toFixed(1))),
        oilTemp: Number(oilTemp.toFixed(1)),
        oilPress: Number(oilPress.toFixed(2)),
        railPress: Math.round(railPress),
        fuelFlow: Number(fuelFlow.toFixed(1)),
        vibeRms: Number(vibe.toFixed(3)),
        busVolts: 28.2 + (Math.random() - 0.5) * 0.1,
        busAmps: 42.5 + (Math.random() - 0.5) * 0.8
      }
    });

    // Update audio synth engine RPM
    if (this.audioSynth) {
      this.audioSynth.updateEngineRPM(rpm);
    }

    // Update residual oscilloscope buffer
    this.residualHistory.shift();
    this.residualHistory.push({
      t: this.simTime,
      residual: residualVal,
      threshold: 0.85,
      healthyBand: 0.20
    });

    // Draw oscilloscope
    this.renderOscilloscope();
  }

  renderOscilloscope() {
    if (!this.ctx || !this.canvas) return;

    const ctx = this.ctx;
    const w = this.canvas.width / (window.devicePixelRatio || 1);
    const h = this.canvas.height / (window.devicePixelRatio || 1);

    ctx.clearRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.06)';
    ctx.lineWidth = 1;
    const gridCols = 8;
    const gridRows = 4;
    for (let c = 0; c <= gridCols; c++) {
      const x = (w / gridCols) * c;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let r = 0; r <= gridRows; r++) {
      const y = (h / gridRows) * r;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // Healthy band zone (0.0 to 0.20 residual)
    const maxVal = 2.2;
    const healthyY = h - (0.20 / maxVal) * (h - 20) - 10;
    ctx.fillStyle = 'rgba(0, 240, 255, 0.04)';
    ctx.fillRect(0, healthyY, w, h - healthyY);

    // Threshold line (0.85)
    const threshY = h - (0.85 / maxVal) * (h - 20) - 10;
    ctx.strokeStyle = 'rgba(255, 59, 48, 0.7)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, threshY);
    ctx.lineTo(w, threshY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Text labels
    ctx.font = '9px JetBrains Mono, monospace';
    ctx.fillStyle = 'rgba(255, 59, 48, 0.8)';
    ctx.fillText('CRITICAL THRESHOLD (0.85 σ)', 10, threshY - 4);

    ctx.fillStyle = 'rgba(0, 240, 255, 0.6)';
    ctx.fillText('BAYESIAN NOMINAL ENVELOPE (< 0.20 σ)', 10, healthyY + 12);

    // Draw Residual Curve
    ctx.beginPath();
    const len = this.residualHistory.length;
    for (let i = 0; i < len; i++) {
      const item = this.residualHistory[i];
      const x = (i / (len - 1)) * w;
      const y = h - (Math.min(item.residual, maxVal) / maxVal) * (h - 20) - 10;

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }

    // Color gradient based on current residual
    const currentResidual = this.residualHistory[len - 1].residual;
    let strokeColor = '#00f0ff';
    let glowColor = 'rgba(0, 240, 255, 0.4)';
    if (currentResidual > 0.85) {
      strokeColor = '#ff3b30';
      glowColor = 'rgba(255, 59, 48, 0.6)';
    } else if (currentResidual > 0.40) {
      strokeColor = '#ff9500';
      glowColor = 'rgba(255, 149, 0, 0.5)';
    }

    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2;
    ctx.shadowColor = glowColor;
    ctx.shadowBlur = 8;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Current value dot
    const lastX = w;
    const lastY = h - (Math.min(currentResidual, maxVal) / maxVal) * (h - 20) - 10;
    ctx.fillStyle = strokeColor;
    ctx.beginPath();
    ctx.arc(lastX - 2, lastY, 4, 0, Math.PI * 2);
    ctx.fill();
  }
}

// Export to window
window.TelemetrySimEngine = TelemetrySimEngine;
