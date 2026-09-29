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
  renderer.domElement.id = 'anumaan-webgl-canvas';
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.2;
  window.renderer = renderer;

  // High-Fidelity Aerospace Studio Environment Map (PMREMGenerator for PBR Metals)
  try {
    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    pmremGenerator.compileEquirectangularShader();

    const envScene = new THREE.Scene();
    envScene.background = new THREE.Color(0x060913);

    const envLight1 = new THREE.DirectionalLight(0xffffff, 2.5);
    envLight1.position.set(5, 8, 5);
    envScene.add(envLight1);

    const envLight2 = new THREE.DirectionalLight(0x00f0ff, 1.4);
    envLight2.position.set(-6, 3, -4);
    envScene.add(envLight2);

    const envLight3 = new THREE.DirectionalLight(0xf59e0b, 1.0);
    envLight3.position.set(2, -6, -4);
    envScene.add(envLight3);

    const envTexture = pmremGenerator.fromScene(envScene).texture;
    scene.environment = envTexture;
    pmremGenerator.dispose();
  } catch (e) {
    console.log('[3D TWIN] PMREM environment fallback:', e);
  }

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
      if (cameraDirector) {
        cameraDirector.adaptToEngine(engineModel ? engineModel.activeEngineId : 'rotax_912is');
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

  // 10. Viewport Director Controls: Multi-Engine Switching, Optics, Shading & Dynamic Faults
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
      if (mode) {
        engineModel.setShadingMode(mode);
        shadingBtns.forEach(b => {
          if (b.dataset.shading) b.classList.remove('active');
        });
        btn.classList.add('active');
      }
      if (audioSynth && audioSynth.enabled) audioSynth.playUiClick();
    });
  });

  // Auto Orbit Toggle Button
  const orbitBtn = document.getElementById('btn-toggle-orbit');
  if (orbitBtn) {
    orbitBtn.addEventListener('click', () => {
      cameraDirector.isAutoOrbit = !cameraDirector.isAutoOrbit;
      orbitBtn.classList.toggle('active', cameraDirector.isAutoOrbit);
      if (audioSynth && audioSynth.enabled) audioSynth.playUiClick();
    });
  }

  // Multi-Engine Selector (0ms Instant In-Memory Switcher)
  const engineSelectBtns = document.querySelectorAll('.model-select-btn[data-engine]');
  const engineTitleEl = document.getElementById('viewport-engine-title');
  const engineSubtitleEl = document.getElementById('viewport-engine-subtitle');
  const engineSpecContainer = document.getElementById('engine-spec-details');
  const faultButtonsContainer = document.getElementById('fault-injector-buttons-container');
  const resetFaultsBtn = document.getElementById('btn-reset-faults-all');

  function selectEngine(engineId) {
    const prof = window.WEB_ENGINE_PROFILES ? window.WEB_ENGINE_PROFILES[engineId] : null;
    if (!prof) return;

    // 0ms instant model switch in Three.js
    engineModel.switchEngine(engineId);

    // Update Selector Buttons
    engineSelectBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.engine === engineId);
    });

    // Update Header Stamp
    if (engineTitleEl) {
      engineTitleEl.innerHTML = `${prof.name} <span class="stamp-lens" id="viewport-focal-readout">f=75mm (26.9° FOV)</span>`;
    }
    if (engineSubtitleEl) {
      engineSubtitleEl.textContent = prof.subtitle;
    }

    // Populate Subsystem Specs
    if (engineSpecContainer) {
      engineSpecContainer.innerHTML = '';
      const faultKeys = Object.keys(prof.faults || {});
      faultKeys.forEach((fid, idx) => {
        const f = prof.faults[fid];
        const item = document.createElement('div');
        item.className = 'subsystem-item-btn';
        item.innerHTML = `
          <span class="subsystem-name">${f.comp}</span>
          <span class="subsystem-status-dot" id="subsys-dot-${fid}"></span>
        `;
        item.addEventListener('click', () => injectFault(Number(fid)));
        engineSpecContainer.appendChild(item);
      });
    }

    // Populate Dynamic Fault Injector Buttons (1 to 8)
    if (faultButtonsContainer) {
      faultButtonsContainer.innerHTML = '';
      const faultKeys = Object.keys(prof.faults || {});
      faultKeys.forEach((fid) => {
        const f = prof.faults[fid];
        const fBtn = document.createElement('button');
        fBtn.className = 'fault-inject-btn';
        fBtn.dataset.faultId = fid;
        fBtn.innerHTML = `
          <div class="fault-inject-title">
            <span><span class="key-badge">${fid}</span> ${f.short}</span>
            <span class="fault-tag-badge ${f.tag}">${f.tag}</span>
          </div>
          <div class="fault-inject-desc">${f.comp}</div>
        `;
        fBtn.addEventListener('click', () => injectFault(Number(fid)));
        faultButtonsContainer.appendChild(fBtn);
      });
    }

    // Reset active fault
    stateStore.update({ activeFault: 0 });
    if (audioSynth && audioSynth.enabled) audioSynth.playUiClick();
  }

  function injectFault(faultId) {
    engineModel.highlightFault(faultId);
    stateStore.update({ activeFault: faultId });

    // Update active class on fault buttons
    if (faultButtonsContainer) {
      const btns = faultButtonsContainer.querySelectorAll('.fault-inject-btn');
      btns.forEach(b => {
        b.classList.toggle('active', Number(b.dataset.faultId) === faultId);
      });
    }

    // Update subsystem indicator dots
    if (engineSpecContainer) {
      const dots = engineSpecContainer.querySelectorAll('.subsystem-status-dot');
      dots.forEach((dot, idx) => {
        const isFaulty = (idx + 1 === faultId);
        dot.className = `subsystem-status-dot ${isFaulty ? 'red' : ''}`;
      });
    }

    if (audioSynth && audioSynth.enabled) {
      audioSynth.playWarningAlarm();
    }
  }

  function resetAllFaults() {
    engineModel.clearFaultHighlights();
    stateStore.update({ activeFault: 0 });

    if (faultButtonsContainer) {
      const btns = faultButtonsContainer.querySelectorAll('.fault-inject-btn');
      btns.forEach(b => b.classList.remove('active'));
    }

    if (engineSpecContainer) {
      const dots = engineSpecContainer.querySelectorAll('.subsystem-status-dot');
      dots.forEach(dot => {
        dot.className = 'subsystem-status-dot';
      });
    }

    if (audioSynth && audioSynth.enabled) {
      audioSynth.playUiClick();
    }
  }

  engineSelectBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      selectEngine(btn.dataset.engine);
    });
  });

  if (resetFaultsBtn) {
    resetFaultsBtn.addEventListener('click', resetAllFaults);
  }

  // Initial Engine Profile Setup
  selectEngine('rotax_912is');

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

  // 12. Tactical Keyboard Shortcuts (F1-F5 Engine Switch, 1-8 Fault Injection, G/X Ghost Mode, Orbit, Audio)
  const ENGINE_KEY_MAP = {
    'F1': 'rotax_912is',
    'F2': 'rotax_914',
    'F3': 'rotax_915is',
    'F4': 'austro_ae300',
    'F5': 'vrde_jayem_2_2l'
  };

  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    // F1 - F5: Instant 0ms Engine Switch
    if (ENGINE_KEY_MAP[e.key]) {
      e.preventDefault();
      selectEngine(ENGINE_KEY_MAP[e.key]);
      return;
    }

    // 1 - 8: Physics Fault Injection
    if (e.key >= '1' && e.key <= '8') {
      const faultId = parseInt(e.key, 10);
      injectFault(faultId);
      return;
    }

    // 0 or Escape: Reset Faults to Nominal
    if (e.key === '0' || e.key === 'Escape') {
      resetAllFaults();
      return;
    }

    // G or X: Toggle Holographic Ghost X-Ray Vision
    if (e.key === 'g' || e.key === 'G' || e.key === 'x' || e.key === 'X') {
      engineModel.toggleGhostVision();
      const ghostBtn = document.querySelector('.shading-mode-btn[data-shading="ghost"]');
      if (ghostBtn) {
        ghostBtn.classList.toggle('active', engineModel.isGhostVision);
      }
      if (audioSynth && audioSynth.enabled) audioSynth.playUiClick();
      return;
    }

    // Space: Auto Orbit in Viewport or Play in Mission Runway
    if (e.key === ' ') {
      e.preventDefault();
      const currentTab = stateStore.get().activeTab || 'story';
      if (currentTab === 'viewport') {
        cameraDirector.isAutoOrbit = !cameraDirector.isAutoOrbit;
        if (orbitBtn) orbitBtn.classList.toggle('active', cameraDirector.isAutoOrbit);
      } else {
        if (playBtn) playBtn.click();
      }
      return;
    }

    // M: Toggle Audio Synthesizer
    if (e.key === 'm' || e.key === 'M') {
      if (audioBtn) audioBtn.click();
      return;
    }

    // Arrow Navigation for Mission Film (Tab 01)
    if (e.key === 'ArrowRight') {
      storyRunner.nextScene();
    } else if (e.key === 'ArrowLeft') {
      storyRunner.prevScene();
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
