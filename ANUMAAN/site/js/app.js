/**
 * PROJECT ANUMAAN — MASTER APPLICATION COORDINATOR
 * Connects Three.js 3D Twin, Blender Camera Director, 18-Scene Mission Runner,
 * 20 Hz Telemetry Physics Simulator, Audio Synthesizer, and GCS Dashboard.
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialize Global State Store & Audio Synthesizer
  const stateStore = window.anumaanStore || new MissionStateStore();
  window.anumaanStore = stateStore;

  const audioSynth = window.tacticalAudio || new TacticalAudioSynthesizer();
  window.tacticalAudio = audioSynth;

  // 2. Three.js Scene & Renderer Setup
  const scene = new THREE.Scene();
  window.scene = scene;

  // Cinematic Aerospace Studio Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
  scene.add(ambientLight);

  const keyLight = new THREE.DirectionalLight(0xffffff, 1.3);
  keyLight.position.set(4, 8, 6);
  scene.add(keyLight);

  const fillLight = new THREE.DirectionalLight(0x00f0ff, 0.45);
  fillLight.position.set(-6, 2, -4);
  scene.add(fillLight);

  const rimLight = new THREE.DirectionalLight(0xf59e0b, 0.4);
  rimLight.position.set(0, -6, -4);
  scene.add(rimLight);

  // Perspective Camera
  const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
  window.camera = camera;

  // Single High-Performance WebGL Renderer
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  window.renderer = renderer;

  // Mount to Initial Viewport (Story Tab)
  const initialMountWrapper = document.getElementById('story-viewport-wrapper') || document.body;
  initialMountWrapper.appendChild(renderer.domElement);

  // OrbitControls
  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.maxDistance = 8.0;
  controls.minDistance = 0.4;
  window.controls = controls;

  // 3. Instantiate Engine 3D Model & Subsystems
  const engineModel = new DigitalTwinEngineModel(scene);
  window.engineModel = engineModel;

  // 3b. Instantiate Animated Drone Airframe & Terrain Model
  const droneModel = new DroneAirframeModel(scene);
  window.droneModel = droneModel;

  // 4. Instantiate Blender Camera Director
  const cameraDirector = new BlenderCameraDirector(camera, controls, renderer.domElement);
  window.cameraDirector = cameraDirector;

  // 5. Instantiate 18-Scene Mission Story Runner
  const storyRunner = new MissionStoryRunner(cameraDirector, engineModel);
  window.storyRunner = storyRunner;

  // 6. Instantiate 20 Hz Telemetry Physics Simulator
  const simEngine = new TelemetrySimEngine(stateStore, audioSynth);
  const oscCanvas = document.getElementById('oscilloscope-canvas');
  if (oscCanvas) {
    simEngine.initCanvas(oscCanvas);
  }
  simEngine.start();
  window.simEngine = simEngine;

  // 7. Navigation Tab Switching
  const navLinks = document.querySelectorAll('.nav-link');
  const sections = document.querySelectorAll('.app-section');

  function switchTab(tabId) {
    navLinks.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabId);
    });

    sections.forEach(sec => {
      sec.classList.toggle('active', sec.id === `section-${tabId}`);
    });

    stateStore.update({ activeTab: tabId });

    // Mount Canvas into active view
    if (tabId === 'story') {
      const wrapper = document.getElementById('story-viewport-wrapper');
      if (wrapper && renderer.domElement.parentElement !== wrapper) {
        wrapper.appendChild(renderer.domElement);
      }
    } else if (tabId === 'viewport') {
      const wrapper = document.getElementById('viewport-stage-wrapper');
      if (wrapper && renderer.domElement.parentElement !== wrapper) {
        wrapper.appendChild(renderer.domElement);
      }
    }

    setTimeout(() => {
      handleResize();
      if (simEngine) simEngine.resizeCanvas();
    }, 50);

    if (audioSynth && audioSynth.enabled) {
      audioSynth.playUiClick();
    }
  }

  navLinks.forEach(link => {
    link.addEventListener('click', () => {
      switchTab(link.dataset.tab);
    });
  });

  const quickTourBtn = document.getElementById('btn-quick-tour');
  if (quickTourBtn) {
    quickTourBtn.addEventListener('click', () => switchTab('viewport'));
  }

  // 8. Responsive Resize
  function handleResize() {
    const parent = renderer.domElement.parentElement;
    if (!parent) return;
    const width = parent.clientWidth;
    const height = parent.clientHeight;
    if (width > 0 && height > 0) {
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    }
  }
  window.addEventListener('resize', handleResize);
  setTimeout(handleResize, 100);

  // 9. 18-Scene Story Presenter Controls & Ruler
  const prevBtn = document.getElementById('story-prev-btn');
  const playBtn = document.getElementById('story-play-btn');
  const nextBtn = document.getElementById('story-next-btn');

  if (prevBtn) prevBtn.addEventListener('click', () => storyRunner.prevScene());
  if (nextBtn) nextBtn.addEventListener('click', () => storyRunner.nextScene());

  let autoPlayInterval = null;
  if (playBtn) {
    playBtn.addEventListener('click', () => {
      if (autoPlayInterval) {
        clearInterval(autoPlayInterval);
        autoPlayInterval = null;
        playBtn.textContent = 'PLAY';
        playBtn.classList.remove('active');
      } else {
        playBtn.textContent = 'PAUSE';
        playBtn.classList.add('active');
        autoPlayInterval = setInterval(() => {
          if (storyRunner.activeSceneIndex >= storyRunner.totalScenes - 1) {
            storyRunner.goToScene(0);
          } else {
            storyRunner.nextScene();
          }
        }, 5500);
      }
      if (audioSynth && audioSynth.enabled) audioSynth.playUiClick();
    });
  }

  // Populate 18 Scrubber Ruler Ticks
  const ticksContainer = document.getElementById('ruler-ticks-container');
  if (ticksContainer) {
    ticksContainer.innerHTML = '';
    for (let i = 0; i < storyRunner.totalScenes; i++) {
      const tick = document.createElement('div');
      tick.className = `ruler-tick ${i === 0 ? 'active' : ''}`;
      tick.title = `Scene ${i}: ${storyRunner.scenes[i].title}`;
      tick.addEventListener('click', () => {
        storyRunner.goToScene(i);
      });
      ticksContainer.appendChild(tick);
    }
  }

  // 10. Viewport Director Controls: Presets, Optics, Shading & Faults
  // Presets
  const presetBtns = document.querySelectorAll('.cam-preset-btn');
  presetBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const presetKey = btn.dataset.preset;
      cameraDirector.applyPreset(presetKey);
      presetBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (audioSynth && audioSynth.enabled) audioSynth.playUiClick();
    });
  });

  // Optics Slider
  const focalSlider = document.getElementById('focal-length-slider');
  const focalValEl = document.getElementById('focal-length-val');
  const fovValEl = document.getElementById('calculated-fov-val');
  const stampReadout = document.getElementById('viewport-focal-readout');

  if (focalSlider) {
    focalSlider.addEventListener('input', (e) => {
      const lens = parseFloat(e.target.value);
      cameraDirector.setFocalLength(lens);
      const fov = cameraDirector.calculateFov(lens);
      if (focalValEl) focalValEl.textContent = `${lens.toFixed(1)} mm`;
      if (fovValEl) fovValEl.textContent = `${fov.toFixed(1)}°`;
      if (stampReadout) stampReadout.textContent = `f=${lens.toFixed(0)}mm (${fov.toFixed(1)}° FOV)`;
    });
  }

  // Shading Modes
  const shadingBtns = document.querySelectorAll('.shading-mode-btn');
  shadingBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const mode = btn.dataset.shading;
      engineModel.setShadingMode(mode);
      shadingBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (audioSynth && audioSynth.enabled) audioSynth.playUiClick();
    });
  });

  // 3D Model Selector (Engine vs Drone vs Terrain Sortie)
  const modelSelectBtns = document.querySelectorAll('.model-select-btn');
  modelSelectBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const m = btn.dataset.model;
      if (droneModel) droneModel.setMode(m);
      modelSelectBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (audioSynth && audioSynth.enabled) audioSynth.playUiClick();
    });
  });

  // Fault Injector Buttons
  const faultBtns = document.querySelectorAll('.fault-inject-btn, .btn-reset-faults');
  faultBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const fault = btn.dataset.fault;
      stateStore.update({ activeFault: fault });
      engineModel.highlightFault(fault);

      faultBtns.forEach(b => b.classList.remove('active'));
      if (btn.classList.contains('fault-inject-btn')) {
        btn.classList.add('active');
      }

      if (audioSynth && audioSynth.enabled) {
        if (fault === 'none') {
          audioSynth.playUiClick();
        } else {
          audioSynth.playWarningAlarm();
        }
      }
    });
  });

  // Audio Toggle
  const audioBtn = document.getElementById('audio-toggle-btn');
  if (audioBtn) {
    audioBtn.addEventListener('click', () => {
      const enabled = !audioSynth.enabled;
      audioSynth.toggleAudio(enabled);
      audioBtn.classList.toggle('active', enabled);
      audioBtn.textContent = enabled ? '🔊' : '🔇';
    });
  }

  // Traceability Search Filter
  const traceInput = document.getElementById('trace-search');
  const traceTbody = document.getElementById('traceability-tbody');
  if (traceInput && traceTbody) {
    traceInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      const rows = traceTbody.querySelectorAll('tr');
      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(q) ? '' : 'none';
      });
    });
  }

  // 11. State Change UI Subscriptions (Telemetry, Gauges & Alerts)
  stateStore.subscribe((state, prev) => {
    const t = state.telemetry;

    // Top Ticker
    const tickRpm = document.getElementById('ticker-rpm');
    const tickMap = document.getElementById('ticker-map');
    const tickCht3 = document.getElementById('ticker-cht3');
    const tickEgt3 = document.getElementById('ticker-egt3');
    const tickOil = document.getElementById('ticker-oil');
    const tickRail = document.getElementById('ticker-rail');
    const tickRul = document.getElementById('ticker-rul');
    const tickRes = document.getElementById('ticker-res');
    const tickStatus = document.getElementById('ticker-status');
    const tickDot = document.getElementById('ticker-dot');

    if (tickRpm) tickRpm.textContent = t.rpm.toLocaleString();
    if (tickMap) tickMap.textContent = `${t.map ? t.map.toFixed(2) : '1.95'} bar`;
    if (tickCht3) tickCht3.textContent = `${t.cht ? t.cht[2] : '139.1'}°C`;
    if (tickEgt3) tickEgt3.textContent = `${t.egt ? t.egt[2] : '684.0'}°C`;
    if (tickOil) tickOil.textContent = `${t.oilTemp ? t.oilTemp : '92.4'}°C / ${t.oilPress ? t.oilPress : '4.25'} bar`;
    if (tickRail) tickRail.textContent = `${t.railPress ? t.railPress : '1,610'} bar`;
    if (tickRul) tickRul.textContent = `${state.rulHours ? state.rulHours.toFixed(1) : '450.0'} h`;

    // Alert Styling
    const alertLevel = state.alertLevel || 'NOMINAL';
    if (tickStatus) tickStatus.textContent = `TWIN ${alertLevel}`;
    if (tickDot) {
      tickDot.className = `telemetry-indicator ${alertLevel === 'WARNING' || alertLevel === 'CRITICAL' ? 'red' : alertLevel === 'CAUTION' ? 'amber' : ''}`;
    }

    // GCS Dashboard UI
    const dashStatus = document.getElementById('dash-status-text');
    const dashRul = document.getElementById('dash-rul-val');
    const dashRpm = document.getElementById('dash-rpm-val');
    const dashMap = document.getElementById('dash-map-val');
    const dashOilT = document.getElementById('dash-oilt-val');
    const dashRail = document.getElementById('dash-rail-val');
    const dashAdvisory = document.getElementById('dash-advisory-text');

    if (dashStatus) {
      dashStatus.textContent = alertLevel;
      dashStatus.className = `status-metric-value ${alertLevel === 'WARNING' || alertLevel === 'CRITICAL' ? 'text-red' : alertLevel === 'CAUTION' ? 'text-amber' : 'text-cyan'}`;
    }
    if (dashRul) dashRul.innerHTML = `${state.rulHours ? state.rulHours.toFixed(1) : '450.0'}<span class="status-metric-unit">HRS</span>`;
    if (dashRpm) dashRpm.textContent = t.rpm ? t.rpm.toLocaleString() : '2,350';
    if (dashMap) dashMap.innerHTML = `${t.map ? t.map.toFixed(2) : '1.95'} <span class="status-metric-unit">bar</span>`;
    if (dashOilT) dashOilT.innerHTML = `${t.oilTemp ? t.oilTemp : '92.4'} <span class="status-metric-unit">°C</span>`;
    if (dashRail) dashRail.innerHTML = `${t.railPress ? t.railPress : '1,610'} <span class="status-metric-unit">bar</span>`;
    if (dashAdvisory) dashAdvisory.textContent = state.saarthiAdvisory || 'ALL SYSTEMS NOMINAL. Digital twin tracking within 99.4% Bayesian confidence bounds.';

    // CHT & EGT Cylinders
    if (t.cht && t.cht.length >= 4) {
      for (let c = 1; c <= 4; c++) {
        const chtEl = document.getElementById(`dash-cht${c}`);
        const barEl = document.getElementById(`bar-cht${c}`);
        const egtEl = document.getElementById(`dash-egt${c}`);
        const cVal = t.cht[c - 1];
        const eVal = t.egt ? t.egt[c - 1] : 680;

        if (chtEl) chtEl.textContent = `${cVal}°C`;
        if (egtEl) egtEl.textContent = `${eVal}°C`;
        if (barEl) {
          const pct = Math.min(100, Math.max(0, ((cVal - 100) / 70) * 100));
          barEl.style.width = `${pct}%`;
          barEl.style.background = cVal > 155 ? 'var(--state-red)' : cVal > 145 ? 'var(--state-amber)' : 'var(--state-cyan)';
        }
      }
    }
  });

  // 12. Keyboard Shortcuts
  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    if (e.key === 'ArrowRight') {
      storyRunner.nextScene();
    } else if (e.key === 'ArrowLeft') {
      storyRunner.prevScene();
    } else if (e.key === ' ') {
      e.preventDefault();
      if (playBtn) playBtn.click();
    } else if (e.key === 'm' || e.key === 'M') {
      if (audioBtn) audioBtn.click();
    }
  });

  // 13. Render Animation Loop (60 FPS)
  let lastTime = performance.now();
  function animate(currentTime) {
    requestAnimationFrame(animate);
    const delta = (currentTime - lastTime) / 1000;
    lastTime = currentTime;

    const currentRpm = stateStore.get().telemetry.rpm || 5200;
    if (engineModel) engineModel.update(delta, currentRpm);
    if (droneModel) droneModel.update(delta);
    if (cameraDirector) cameraDirector.update();
    if (controls) controls.update();
    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }
  }
  requestAnimationFrame(animate);

  // Trigger initial scene render
  storyRunner.goToScene(0);
  console.log('Project ANUMAAN System Initialized. WebGL 3D Twin and 18-scene mission runner online.');
});
