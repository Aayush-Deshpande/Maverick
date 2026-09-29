/**
 * PROJECT ANUMAAN — BLENDER CAMERA DIRECTOR & OPTICS CONTROLLER
 * Faithful recreation of DCC/Blender camera rigs, presets, lens optics, and smooth transitions
 */

class BlenderCameraDirector {
  constructor(camera, controls, domElement) {
    this.camera = camera;
    this.controls = controls;
    this.domElement = domElement;

    this.sensorWidth = 36.0; // 35mm Full Frame
    this.isAutoOrbit = true;
    this.orbitSpeed = 0.45; // rad/s
    this.currentAngle = -1.2;
    this.currentElevation = 0.42;
    this.currentDistance = 2.3;
    this.cameraCenter = new THREE.Vector3(0, 0, 0);

    // Transition State
    this.isTransitioning = false;
    this.transitionStart = 0;
    this.transitionDuration = 0.85; // seconds
    this.fromPos = new THREE.Vector3();
    this.toPos = new THREE.Vector3();
    this.fromTarget = new THREE.Vector3();
    this.toTarget = new THREE.Vector3();
    this.fromFov = 45;
    this.toFov = 45;

    // Presets matching DCC / Blender Camera Rig
    this.presets = {
      hero: { name: "Cam_Hero (3/4 ISO)", angle: -1.2, elevation: 0.42, distMult: 1.0, lens: 75.0 },
      turbo: { name: "Cam_Turbo", angle: -0.78, elevation: -0.14, distMult: 0.70, lens: 65.0 },
      fuel: { name: "Cam_Fuel_System", angle: -1.48, elevation: 0.59, distMult: 0.65, lens: 55.0 },
      gearbox: { name: "Cam_Gearbox", angle: -1.57, elevation: 0.24, distMult: 0.60, lens: 60.0 },
      ortho: { name: "Cam_Ortho (Diagnostic)", angle: 0.0, elevation: 1.50, distMult: 1.10, lens: 90.0 },
      wireframe: { name: "Cam_Wireframe", angle: -2.1, elevation: 0.35, distMult: 0.95, lens: 70.0 },
      fault_cyl3: { name: "Cam_Fault_Cyl2", angle: -2.44, elevation: 0.42, distMult: 0.60, lens: 60.0 },
      top: { name: "Cam_Top", angle: 0.0, elevation: 1.45, distMult: 1.15, lens: 55.0 },
      front: { name: "Cam_Front", angle: -Math.PI / 2, elevation: 0.10, distMult: 0.90, lens: 55.0 },
      exhaust: { name: "Cam_Exhaust", angle: -Math.PI / 4, elevation: -0.15, distMult: 0.75, lens: 55.0 }
    };

    this.activePresetKey = 'hero';
    this.adaptToEngine('rotax_912is');
  }

  calculateFov(focalLengthMm) {
    return 2.0 * Math.atan(this.sensorWidth / (2.0 * focalLengthMm)) * (180.0 / Math.PI);
  }

  calculateFocalLength(fovDegrees) {
    return this.sensorWidth / (2.0 * Math.tan((fovDegrees * Math.PI) / 360.0));
  }

  adaptToEngine(engineId) {
    const prof = window.WEB_ENGINE_PROFILES ? window.WEB_ENGINE_PROFILES[engineId] : null;
    if (!prof) return;

    this.currentDistance = prof.defaultDistance || 2.3;
    this.currentElevation = prof.defaultElevation || 0.42;
    this.currentAngle = prof.defaultAngle || -1.2;
    this.cameraCenter.set(0, 0, 0);

    const cx = this.cameraCenter.x + this.currentDistance * Math.cos(this.currentAngle) * Math.cos(this.currentElevation);
    const cy = this.cameraCenter.y + this.currentDistance * Math.sin(this.currentElevation);
    const cz = this.cameraCenter.z + this.currentDistance * Math.sin(this.currentAngle) * Math.cos(this.currentElevation);

    this.camera.position.set(cx, cy, cz);
    if (this.controls) {
      this.controls.target.copy(this.cameraCenter);
      this.controls.update();
    }
    this.isAutoOrbit = true;
  }

  flyToVantage(angle, elevation, distance) {
    this.isAutoOrbit = false;
    
    // Distance in meters from engine profile (e.g. 0.9m - 1.4m close-up framing)
    const dist = (typeof distance === 'number' && distance > 0) ? distance : (this.currentDistance * 0.65);
    this.currentAngle = angle;
    this.currentElevation = elevation;
    this.currentDistance = dist;

    const cx = this.cameraCenter.x + dist * Math.cos(angle) * Math.cos(elevation);
    const cy = this.cameraCenter.y + dist * Math.sin(elevation);
    const cz = this.cameraCenter.z + dist * Math.sin(angle) * Math.cos(elevation);

    this.smoothTransitionTo(new THREE.Vector3(cx, cy, cz), this.cameraCenter, 55.0);
  }

  applyPreset(presetKey, animate = true) {
    const preset = this.presets[presetKey];
    if (!preset) return;

    this.activePresetKey = presetKey;
    this.isAutoOrbit = false;

    const dist = this.currentDistance * preset.distMult;
    const cx = this.cameraCenter.x + dist * Math.cos(preset.angle) * Math.cos(preset.elevation);
    const cy = this.cameraCenter.y + dist * Math.sin(preset.elevation);
    const cz = this.cameraCenter.z + dist * Math.sin(preset.angle) * Math.cos(preset.elevation);

    const targetPos = new THREE.Vector3(cx, cy, cz);

    if (!animate) {
      this.camera.position.copy(targetPos);
      if (this.controls) {
        this.controls.target.copy(this.cameraCenter);
        this.controls.update();
      }
      return;
    }

    this.smoothTransitionTo(targetPos, this.cameraCenter, preset.lens);
  }

  smoothTransitionTo(targetPos, targetCenter, lens = 55.0) {
    this.fromPos.copy(this.camera.position);
    this.toPos.copy(targetPos);

    if (this.controls) {
      this.fromTarget.copy(this.controls.target);
    }
    this.toTarget.copy(targetCenter);

    this.fromFov = this.camera.fov;
    this.toFov = this.calculateFov(lens);

    this.transitionStart = performance.now();
    this.isTransitioning = true;
  }

  update(delta = 0.016) {
    if (this.isTransitioning) {
      const elapsed = (performance.now() - this.transitionStart) / 1000.0;
      let t = Math.min(1.0, elapsed / this.transitionDuration);

      // Smooth Quintic Easing
      const ease = t < 0.5 ? 16 * t * t * t * t * t : 1 - Math.pow(-2 * t + 2, 5) / 2;

      this.camera.position.lerpVectors(this.fromPos, this.toPos, ease);
      if (this.controls) {
        this.controls.target.lerpVectors(this.fromTarget, this.toTarget, ease);
        this.controls.update();
      }
      this.camera.fov = THREE.MathUtils.lerp(this.fromFov, this.toFov, ease);
      this.camera.updateProjectionMatrix();

      if (t >= 1.0) {
        this.isTransitioning = false;
      }
    } else if (this.isAutoOrbit && this.controls) {
      this.currentAngle = (this.currentAngle + this.orbitSpeed * delta) % (2 * Math.PI);
      const cx = this.cameraCenter.x + this.currentDistance * Math.cos(this.currentAngle) * Math.cos(this.currentElevation);
      const cy = this.cameraCenter.y + this.currentDistance * Math.sin(this.currentElevation);
      const cz = this.cameraCenter.z + this.currentDistance * Math.sin(this.currentAngle) * Math.cos(this.currentElevation);

      this.camera.position.x += (cx - this.camera.position.x) * 0.08;
      this.camera.position.y += (cy - this.camera.position.y) * 0.08;
      this.camera.position.z += (cz - this.camera.position.z) * 0.08;

      this.controls.target.lerp(this.cameraCenter, 0.08);
      this.controls.update();
    }
  }
}

window.BlenderCameraDirector = BlenderCameraDirector;
