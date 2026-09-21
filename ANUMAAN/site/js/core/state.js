/**
 * PROJECT ANUMAAN — CENTRAL REACTIVE STATE STORE
 * Inspired by Zustand/Redux architecture in clean Vanilla JavaScript
 */

class MissionStateStore {
  constructor() {
    this.state = {
      // Navigation
      activeTab: 'story', // 'story' | 'viewport' | 'problem' | 'architecture' | 'dashboard' | 'simulation' | 'fleet' | 'traceability'
      
      // Story Runway (18 Scenes)
      activeSceneIndex: 0,
      isPlayingStory: false,
      storyProgress: 0.0, // 0.0 to 1.0 within active scene
      
      // Camera Director (Blender Presets)
      activeCameraPreset: 'hero', // 'hero' | 'turbo' | 'fuel' | 'gearbox' | 'ortho' | 'wireframe' | 'fault_cyl3' | 'orbit'
      focalLength: 75.0, // mm
      sensorWidth: 36.0, // mm (35mm Full Frame)
      cameraPos: { x: -1.45, y: 0.67, z: -1.41 },
      cameraTarget: { x: -0.03, y: 0.03, z: 0.36 },
      elevationDeg: 18.0,
      azimuthDeg: 50.0,
      
      // Shading Pass Mode
      shadingMode: 'pbr', // 'pbr' | 'wireframe' | 'ghost' | 'thermal'
      
      // Active Injected Fault
      activeFault: 'none', // 'none' | 'combustion_cyl3' | 'coolant_loss' | 'turbo_fouling' | 'rail_drop' | 'sensor_rpm_drift'
      faultSeverity: 0.0, // 0.0 to 1.0
      
      // Real-Time Telemetry (20 Hz)
      telemetry: {
        rpm: 5240,
        map_inhg: 36.4,
        cht: [108.2, 109.1, 107.8, 108.5], // °C
        egt: [812, 816, 810, 814],         // °C
        oil_press_bar: 4.82,
        oil_temp_c: 94.5,
        fuel_flow_lph: 24.8,
        coolant_temp_c: 88.0,
        bus_voltage: 28.2,
        alternator_current: 34.5,
        vibration_rms: 1.15,
        
        // Twin Analytics
        health_index: 0.98,
        anomaly_score: 0.04,
        residual_val: 0.03,
        rul_p50_hours: 48.0,
        rul_p10_hours: 42.0,
        
        // Status State
        system_status: 'NOMINAL', // 'NOMINAL' | 'CAUTION' | 'CRITICAL' | 'RECOVERED'
        threshold_alert: 'NORMAL', // 'NORMAL' | 'WARNING'
      },
      
      // Audio Enabled
      soundEnabled: false,
      
      // Selected Fleet Drone
      selectedDroneId: 'TAPAS-01',
      
      // Active Simulation Theater
      simulationTheater: 'ladakh' // 'ladakh' | 'thar'
    };
    
    this.listeners = new Set();
  }

  getState() {
    return this.state;
  }

  get() {
    return this.state;
  }

  setState(partialState) {
    const prevState = { ...this.state };
    this.state = { ...this.state, ...partialState };
    
    // Notify subscribers
    for (const listener of this.listeners) {
      listener(this.state, prevState);
    }
  }

  update(partialState) {
    this.setState(partialState);
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  // Event listener helper
  on(event, cb) {
    this.subscribe((state, prev) => {
      if (event === 'faultChanged' && state.activeFault !== prev.activeFault) cb(state.activeFault);
      if (event === 'sceneChanged' && state.activeSceneIndex !== prev.activeSceneIndex) cb(state.activeSceneIndex);
      if (event === 'alertLevelChanged' && state.telemetry.system_status !== prev.telemetry.system_status) cb(state.telemetry.system_status);
      if (event === 'telemetryUpdated') cb(state.telemetry);
      if (event === 'cameraChanged') cb(state);
    });
  }

  // Telemetry Micro-update without full object cloning
  updateTelemetry(key, value) {
    this.state.telemetry[key] = value;
    for (const listener of this.listeners) {
      listener(this.state, this.state);
    }
  }
}

// Global Exports
window.MissionStateStore = MissionStateStore;
window.AnumaanState = MissionStateStore;
window.anumaanStore = new MissionStateStore();
