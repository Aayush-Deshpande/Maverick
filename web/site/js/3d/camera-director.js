/**
 * PROJECT ANUMAAN — BLENDER CAMERA DIRECTOR & OPTICS CONTROLLER
 * Faithful recreation of DCC/Blender camera rigs, presets, lens optics, and smooth transitions
 */

class BlenderCameraDirector {
  constructor(camera, controls, domElement) {
    this.camera = camera;
    this.controls = controls;
    this.domElement = domElement;

    // Sensor Format: 35mm Full-Frame (36.0mm x 24.0mm)
    this.sensorWidth = 36.0;

    // Camera Presets Matrix (Derived from Blender TEI_PD170_Scene cameras)
    this.presets = {
      hero: {
        name: "Cam_Hero (Master 3/4 Parity)",
        pos: new THREE.Vector3(-1.45, 0.67, -1.41),
        target: new THREE.Vector3(-0.03, 0.03, 0.36),
        lens: 75.0, // 75mm telephoto
        desc: "Calibrated 3/4 front-port hero view matching master physical reference photo"
      },
      turbo: {
        name: "Cam_Turbo (Two-Stage Boost)",
        pos: new THREE.Vector3(0.82, 0.28, 0.52),
        target: new THREE.Vector3(0.24, 0.04, 0.22),
        lens: 65.0,
        desc: "Close-up of HP compressor, LP turbine volutes, and wastegate actuator canister"
      },
      fuel: {
        name: "Cam_Fuel_System (Common Rail)",
        pos: new THREE.Vector3(-0.72, 0.46, 0.38),
        target: new THREE.Vector3(-0.10, 0.22, 0.24),
        lens: 55.0,
        desc: "Inspection of high-pressure common rail, solenoid injectors, and ASAK filter"
      },
      gearbox: {
        name: "Cam_Gearbox (Reduction & Prop)",
        pos: new THREE.Vector3(-0.68, 0.18, -0.72),
        target: new THREE.Vector3(0.00, 0.02, -0.22),
        lens: 60.0,
        desc: "Snout collar, 6-bolt prop flange, sight glass, and bellhousing torque marks"
      },
      ortho: {
        name: "Cam_Diagnostic_Ortho (Top-Down)",
        pos: new THREE.Vector3(0.00, 2.20, 0.20),
        target: new THREE.Vector3(0.00, 0.00, 0.20),
        lens: 90.0,
        desc: "Top-down engineering diagnostic blueprint perspective"
      },
      wireframe: {
        name: "Cam_Wireframe (Topology Audit)",
        pos: new THREE.Vector3(-1.20, 1.10, 1.10),
        target: new THREE.Vector3(0.00, 0.00, 0.20),
        lens: 70.0,
        desc: "High-angle perspective tailored for subdivision wireframe and mesh inspection"
      },
      fault_cyl3: {
        name: "Cam_Fault_Cyl3 (Combustion Loss)",
        pos: new THREE.Vector3(-0.55, 0.38, 0.14),
        target: new THREE.Vector3(-0.16, 0.18, 0.12),
        lens: 60.0,
        desc: "Macro lock-on to Cylinder #3 for combustion anomaly and thermal degradation analysis"
      }
    };

    // Transition State
    this.isTransitioning = false;
    this.transitionStart = 0;
    this.transitionDuration = 1.0; // seconds
    this.fromPos = new THREE.Vector3();
    this.toPos = new THREE.Vector3();
    this.fromTarget = new THREE.Vector3();
    this.toTarget = new THREE.Vector3();
    this.fromFov = 45;
    this.toFov = 45;

    // Active Preset
    this.activePresetKey = 'hero';
    this.applyPreset('hero', false);
  }

  // Calculate Field of View (FOV) from Focal Length (mm)
  calculateFov(focalLengthMm) {
    return 2.0 * Math.atan(this.sensorWidth / (2.0 * focalLengthMm)) * (180.0 / Math.PI);
  }

  // Calculate Focal Length (mm) from FOV (degrees)
  calculateFocalLength(fovDegrees) {
    return this.sensorWidth / (2.0 * Math.tan((fovDegrees * Math.PI) / 360.0));
  }

  // Switch to Preset with smooth cinematic interpolation
  applyPreset(presetKey, animate = true) {
    const preset = this.presets[presetKey];
    if (!preset) return;

    this.activePresetKey = presetKey;
    const targetFov = this.calculateFov(preset.lens);

    if (!animate) {
      this.camera.position.copy(preset.pos);
      this.camera.fov = targetFov;
      this.camera.updateProjectionMatrix();
      if (this.controls) {
        this.controls.target.copy(preset.target);
        this.controls.update();
      }
      this.emitTelemetry();
      return;
    }

    // Initialize Smooth Transition
    this.fromPos.copy(this.camera.position);
    this.toPos.copy(preset.pos);
    if (this.controls) {
      this.fromTarget.copy(this.controls.target);
    }
    this.toTarget.copy(preset.target);
    this.fromFov = this.camera.fov;
    this.toFov = targetFov;

    this.transitionStart = performance.now();
    this.isTransitioning = true;
  }

  // Set Focal Length directly via slider (18mm to 135mm)
  setFocalLength(lensMm) {
    const fov = this.calculateFov(lensMm);
    this.camera.fov = fov;
    this.camera.updateProjectionMatrix();
    this.emitTelemetry();
  }

  // Animation Frame Update
  update() {
    if (this.isTransitioning) {
      const elapsed = (performance.now() - this.transitionStart) / 1000.0;
      let t = elapsed / this.transitionDuration;

      if (t >= 1.0) {
        t = 1.0;
        this.isTransitioning = false;
      }

      // Smooth Quintic Easing
      const ease = t < 0.5 ? 16 * t * t * t * t * t : 1 - Math.pow(-2 * t + 2, 5) / 2;

      this.camera.position.lerpVectors(this.fromPos, this.toPos, ease);
      if (this.controls) {
        this.controls.target.lerpVectors(this.fromTarget, this.toTarget, ease);
        this.controls.update();
      }
      this.camera.fov = THREE.MathUtils.lerp(this.fromFov, this.toFov, ease);
      this.camera.updateProjectionMatrix();

      this.emitTelemetry();
    }
  }

  // Emit Live Camera Telemetry to State Store & UI
  emitTelemetry() {
    if (!window.anumaanStore) return;

    const pos = this.camera.position;
    const target = this.controls ? this.controls.target : new THREE.Vector3();
    const distance = pos.distanceTo(target);

    // Calculate Spherical Euler Angles
    const dx = pos.x - target.x;
    const dy = pos.y - target.y;
    const dz = pos.z - target.z;
    const azimuth = Math.atan2(dx, dz) * (180.0 / Math.PI);
    const elevation = Math.asin(dy / distance) * (180.0 / Math.PI);
    const lens = this.calculateFocalLength(this.camera.fov);

    window.anumaanStore.setState({
      focalLength: Math.round(lens * 10) / 10,
      cameraPos: { x: Math.round(pos.x * 100) / 100, y: Math.round(pos.y * 100) / 100, z: Math.round(pos.z * 100) / 100 },
      cameraTarget: { x: Math.round(target.x * 100) / 100, y: Math.round(target.y * 100) / 100, z: Math.round(target.z * 100) / 100 },
      elevationDeg: Math.round(elevation * 10) / 10,
      azimuthDeg: Math.round(azimuth * 10) / 10
    });
  }
}

window.BlenderCameraDirector = BlenderCameraDirector;
