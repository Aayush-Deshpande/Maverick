/**
 * PROJECT ANUMAAN — 3D DRONE AIRFRAME & TERRAIN LOADER
 * Loads the authentic USAvionix tactical Delta UAV (delta-pbr.glb),
 * flight animations (drone-animations.glb), and 3D terrain (terrain.glb).
 * Integrates with the Rotax 912 iS / 915 iS aero-piston digital twin.
 */

class DroneAirframeModel {
  constructor(scene) {
    this.scene = scene;
    this.rootGroup = new THREE.Group();
    this.rootGroup.name = "ANUMAAN_Drone_Root";
    this.scene.add(this.rootGroup);

    this.droneMesh = null;
    this.terrainMesh = null;
    this.mixer = null;
    this.animations = [];
    this.activeAction = null;
    this.currentAnimIndex = 0;

    this.isLoaded = false;
    this.mode = 'combined'; // 'drone' | 'engine' | 'combined' | 'flight'

    this.dracoLoader = new THREE.DRACOLoader();
    this.dracoLoader.setDecoderPath('js/vendor/draco/');
    this.dracoLoader.setDecoderConfig({ type: 'js' });
    this.dracoLoader.preload();

    this.loader = new THREE.GLTFLoader();
    this.loader.setDRACOLoader(this.dracoLoader);
    this.loadAssets();
  }

  loadAssets() {
    // 1. Load Delta UAV Airframe
    this.loader.load(
      'assets/models/delta-pbr.glb',
      (gltf) => {
        this.droneMesh = gltf.scene;
        this.droneMesh.name = "Delta_UAV_Airframe";
        
        // Scale and position drone nicely
        this.droneMesh.scale.set(0.6, 0.6, 0.6);
        this.droneMesh.position.set(0, 0, 0);

        // Enhance materials for tactical dark aerospace aesthetic
        this.droneMesh.traverse((child) => {
          if (child.isMesh) {
            child.castShadow = true;
            child.receiveShadow = true;
            if (child.material) {
              child.material.roughness = Math.min(child.material.roughness || 0.5, 0.6);
              child.material.metalness = Math.max(child.material.metalness || 0.2, 0.4);
              if (child.name.includes('turbine') || child.name.includes('Air')) {
                child.material.emissive = new THREE.Color(0x00f0ff);
                child.material.emissiveIntensity = 0.2;
              }
            }
          }
        });

        this.rootGroup.add(this.droneMesh);
        console.log("Tactical Delta UAV airframe loaded successfully.");

        // 2. Load Flight Animations
        this.loadAnimations();

        // 3. Load 3D Terrain
        this.loadTerrain();

        this.isLoaded = true;
      },
      (xhr) => {
        console.log(`Drone loading: ${(xhr.loaded / xhr.total * 100).toFixed(0)}%`);
      },
      (error) => {
        console.error("Error loading delta-pbr.glb:", error);
      }
    );
  }

  loadAnimations() {
    this.loader.load(
      'assets/models/drone-animations.glb',
      (gltf) => {
        if (gltf.animations && gltf.animations.length > 0) {
          this.animations = gltf.animations;
          console.log(`Loaded ${this.animations.length} drone flight animation tracks:`, this.animations.map(a => a.name));
          
          if (this.droneMesh) {
            this.mixer = new THREE.AnimationMixer(this.droneMesh);
            this.playAnimation(0);
          }
        }
      },
      undefined,
      (err) => console.warn("Could not load drone-animations.glb:", err)
    );
  }

  loadTerrain() {
    this.loader.load(
      'assets/models/terrain.glb',
      (gltf) => {
        this.terrainMesh = gltf.scene;
        this.terrainMesh.name = "Himalayan_Ladakh_Terrain";
        this.terrainMesh.scale.set(0.04, 0.04, 0.04);
        this.terrainMesh.position.set(0, -1.8, 0);

        this.terrainMesh.traverse((child) => {
          if (child.isMesh) {
            child.receiveShadow = true;
            if (child.material) {
              child.material.roughness = 0.9;
              child.material.metalness = 0.1;
              // Subtle tactical grid glow on terrain
              child.material.wireframe = false;
            }
          }
        });

        this.rootGroup.add(this.terrainMesh);
        console.log("Tactical 3D terrain loaded successfully.");
      },
      undefined,
      (err) => console.warn("Could not load terrain.glb:", err)
    );
  }

  playAnimation(index = 0) {
    if (!this.mixer || this.animations.length === 0) return;
    this.currentAnimIndex = index % this.animations.length;
    const clip = this.animations[this.currentAnimIndex];

    if (this.activeAction) {
      this.activeAction.fadeOut(0.5);
    }

    this.activeAction = this.mixer.clipAction(clip);
    this.activeAction.reset().fadeIn(0.5).play();
    console.log(`Playing drone animation: ${clip.name}`);
  }

  nextAnimation() {
    if (this.animations.length > 0) {
      this.playAnimation(this.currentAnimIndex + 1);
    }
  }

  setMode(mode) {
    this.mode = mode;
    if (mode === 'drone') {
      if (this.droneMesh) this.droneMesh.visible = true;
      if (this.terrainMesh) this.terrainMesh.visible = false;
      if (window.engineModel && window.engineModel.rootGroup) {
        window.engineModel.rootGroup.visible = false;
      }
    } else if (mode === 'engine') {
      if (this.droneMesh) this.droneMesh.visible = false;
      if (this.terrainMesh) this.terrainMesh.visible = false;
      if (window.engineModel && window.engineModel.rootGroup) {
        window.engineModel.rootGroup.visible = true;
      }
    } else if (mode === 'flight') {
      if (this.droneMesh) this.droneMesh.visible = true;
      if (this.terrainMesh) this.terrainMesh.visible = true;
      if (window.engineModel && window.engineModel.rootGroup) {
        window.engineModel.rootGroup.visible = false;
      }
    } else { // 'combined'
      if (this.droneMesh) this.droneMesh.visible = true;
      if (this.terrainMesh) this.terrainMesh.visible = true;
      if (window.engineModel && window.engineModel.rootGroup) {
        window.engineModel.rootGroup.visible = true;
      }
    }
  }

  update(delta) {
    if (this.mixer) {
      this.mixer.update(delta);
    }

    // Procedural flight attitude jitter & slow banking when no animation is playing
    if (this.droneMesh && (!this.mixer || !this.activeAction)) {
      const time = performance.now() * 0.001;
      this.droneMesh.position.y = Math.sin(time * 1.5) * 0.04;
      this.droneMesh.rotation.z = Math.sin(time * 0.8) * 0.05;
      this.droneMesh.rotation.x = Math.sin(time * 1.2) * 0.02;
    }
  }
}

window.DroneAirframeModel = DroneAirframeModel;
