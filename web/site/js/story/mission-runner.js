/**
 * PROJECT ANUMAAN — 18-SCENE CINEMATIC MISSION RUNNER
 * Directly implements the story script from docs/pitch/02_anumaan_pitch_blueprint.md
 * Supports: Presenter Mode (Keyboard ← / →, Space), Scroll Snapping, and Live Audio Synthesis
 */

class MissionStoryRunner {
  constructor(cameraDirector, engineModel) {
    this.director = cameraDirector;
    this.engineModel = engineModel;

    // 18 Scenes Data Definition
    this.scenes = [
      {
        id: "boot",
        phase: "SYSTEM INITIALIZATION",
        title: "The Twin Comes Online",
        caption: "Real-time CAN bus telemetry link established. Physics performance model synchronized across 27 channels at 20 Hz.",
        citation: "DRDO PS-26054 §3.A · SocketCAN / FADEC telemetry link verified",
        camPreset: "wireframe",
        shading: "ghost",
        fault: "none",
        hud: [
          { label: "TWIN STATUS", val: "BOOT_SEQUENCE_COMPLETE", highlight: "cyan" },
          { label: "ENGINE TYPE", val: "TEI-PD170 TURBODIESEL", highlight: "cyan" },
          { label: "TELEMETRY BUS", val: "27 CHANNELS @ 20 Hz", highlight: "cyan" },
          { label: "PHYSICS MODEL", val: "TATTVA V2.4 [SYNCED]", highlight: "cyan" }
        ],
        backdropImage: "assets/06_wireframe_clay.png",
        splitScreen: false,
        theme: "cyan"
      },
      {
        id: "promise",
        phase: "MISSION THESIS",
        title: "Know The Engine Will Fail — Before It Does",
        caption: "An indigenous digital twin that watches every aero piston engine in India's MALE UAV fleet, predicts failures hours ahead, and tells the operator what to do.",
        citation: "Project ANUMAAN · AI-Enabled Digital Twin for Aero Piston Engines",
        camPreset: "hero",
        shading: "pbr",
        fault: "none",
        hud: [
          { label: "TARGET FLEET", val: "INDIA MALE UAVs (TAPAS / ARCHER)", highlight: "cyan" },
          { label: "PROPULSION", val: "SINGLE AERO-PISTON TURBODIESEL", highlight: "cyan" },
          { label: "MISSION PROFILE", val: "HIGH-ALTITUDE LONG ENDURANCE", highlight: "cyan" },
          { label: "SURVEILLANCE", val: "24–45 HOUR SORTIES", highlight: "cyan" }
        ],
        backdropImage: "assets/engine_master_hero.png",
        splitScreen: false,
        theme: "cyan"
      },
      {
        id: "stakes",
        phase: "STRATEGIC CONTEXT",
        title: "Why Single-Engine Reliability Matters",
        caption: "In single-engine MALE UAVs, propulsion loss means complete aircraft loss. 41% of all military UAV mishaps are propulsion-system failures.",
        citation: "USAF Aircraft Accident Investigation Board (AAIB) · DoD UAV Reliability Study",
        camPreset: "hero",
        shading: "pbr",
        fault: "none",
        hud: [
          { label: "REDUNDANCY", val: "SINGLE ENGINE (ZERO FAILOVER)", highlight: "amber" },
          { label: "MISHAP SHARE", val: "41% PROPULSION-CAUSED", highlight: "red" },
          { label: "RECOVERY COST", val: "$18M PER AIRFRAME LOSS", highlight: "red" },
          { label: "CREW AT RISK", val: "UNMANNED / HIGH STRATEGIC VALUE", highlight: "cyan" }
        ],
        backdropImage: "assets/01_hero_front_left.png",
        splitScreen: false,
        theme: "amber"
      },
      {
        id: "aircraft",
        phase: "OPERATIONAL SORTIE",
        title: "Meet The Aircraft: FL250 at Dawn",
        caption: "MALE UAV cruising at 25,000 ft over the northern frontier. Outside air temperature: -31°C. Mission elapsed time: T+14:02.",
        citation: "Operational Envelope · Tapas-BH-201 / Bayraktar TB3 Class UAV",
        camPreset: "hero",
        shading: "pbr",
        fault: "none",
        hud: [
          { label: "ALTITUDE", val: "25,000 FT (7,620 M)", highlight: "cyan" },
          { label: "OAT", val: "-31.4 °C (COLD-SOAK)", highlight: "cyan" },
          { label: "AIRSPEED", val: "135 KTAS / 250 KM/H", highlight: "cyan" },
          { label: "MISSION TIME", val: "T+14:02:44 INTO SORTIE", highlight: "cyan" }
        ],
        backdropImage: "assets/01_hero_front_left.png",
        splitScreen: false,
        theme: "cyan"
      },
      {
        id: "engine",
        phase: "PROPULSION ARCHITECTURE",
        title: "Meet The Engine: TEI-PD170 Architecture",
        caption: "170 hp turbodiesel, 2.1L inline-4, dual-stage sequential turbochargers, common rail injection at 1,600 bar, dual-lane FADEC.",
        citation: "TEI-PD170 Propulsion Technical Specification & Type Certificate",
        camPreset: "turbo",
        shading: "pbr",
        fault: "none",
        hud: [
          { label: "RATED POWER", val: "170 HP @ 2,300 PROP RPM", highlight: "cyan" },
          { label: "ASPIRATION", val: "2-STAGE SEQUENTIAL TURBO", highlight: "cyan" },
          { label: "FUEL SYSTEM", val: "COMMON RAIL (1,600 BAR)", highlight: "cyan" },
          { label: "DRY WEIGHT", val: "162 KG DUAL-LANE FADEC", highlight: "cyan" }
        ],
        backdropImage: "assets/03_closeup_turbo.png",
        splitScreen: false,
        theme: "cyan"
      },
      {
        id: "twin",
        phase: "DIGITAL TWIN SYNCHRONIZATION",
        title: "Two Engines: One Real, One Virtual",
        caption: "They should agree. When they don't, something is changing inside the metal. The residual line sits flat at zero.",
        citation: "TATTVA Physics-Based Thermodynamic Observer · Real vs Synthetic Synchronization",
        camPreset: "hero",
        shading: "ghost",
        fault: "none",
        hud: [
          { label: "PHYSICAL ENGINE", val: "ACTUAL TELEMETRY: SYNCED", highlight: "cyan" },
          { label: "DIGITAL TWIN", val: "THERMODYNAMIC MODEL: SYNCED", highlight: "cyan" },
          { label: "RESIDUAL DELTA", val: "Δ = 0.02 BAR [NOMINAL]", highlight: "cyan" },
          { label: "COHERENCE", val: "99.4% CONVERGENCE", highlight: "cyan" }
        ],
        backdropImage: "assets/engine_master_hero.png",
        splitScreen: true,
        theme: "cyan"
      },
      {
        id: "normal",
        phase: "NOMINAL CRUISE",
        title: "All Normal: Subsystem Health 98%",
        caption: "Smooth endurance cruise. RPM 5,240, oil pressure 4.8 bar, CHT across all four cylinders within 1.5°C of each other.",
        citation: "Nominal Flight Telemetry Log · Mission Sortie #TS-4091",
        camPreset: "fuel",
        shading: "pbr",
        fault: "none",
        hud: [
          { label: "OVERALL HEALTH", val: "0.98 [EXCELLENT]", highlight: "cyan" },
          { label: "OIL PRESSURE", val: "4.82 BAR (LIMIT: 2.0–6.0)", highlight: "cyan" },
          { label: "CHT SPREAD", val: "Δ 1.3 °C (MAX ALLOWED: 15°C)", highlight: "cyan" },
          { label: "TWIN ANOMALY", val: "0.04 [NORMAL]", highlight: "cyan" }
        ],
        backdropImage: "assets/04_closeup_fuel_system.png",
        splitScreen: false,
        theme: "cyan"
      },
      {
        id: "whisper",
        phase: "THE FIRST WHISPER (MONEY SHOT)",
        title: "The Threshold Says Normal. The Twin Disagrees.",
        caption: "Oil pressure dips momentarily from 4.8 to 4.2 bar—well inside conventional thresholds. But physics says it should be 4.8 bar. The twin flags an anomaly.",
        citation: "ANUMAAN Autoencoder Residual Monitor · First Detectable Signal T-2h 47m",
        camPreset: "fault_cyl3",
        shading: "pbr",
        fault: "combustion_cyl3",
        hud: [
          { label: "THRESHOLD GAUGE", val: "4.21 BAR [NORMAL GREEN]", highlight: "cyan" },
          { label: "PHYSICS EXPECTED", val: "4.82 BAR @ 5,240 RPM", highlight: "cyan" },
          { label: "RESIDUAL DELTA", val: "Δ = 0.61 BAR [EXCEEDED]", highlight: "amber" },
          { label: "TWIN ANOMALY", val: "SCORE: 0.72 [CAUTION AMBER]", highlight: "amber" }
        ],
        backdropImage: "assets/07_fault_combustion_failure_cyl_1.png",
        splitScreen: false,
        theme: "amber"
      },
      {
        id: "diagnosis",
        phase: "ISOLATION & DIAGNOSIS",
        title: "Component Isolation: Cylinder #3 Combustion Loss",
        caption: "EGT on Cylinder #3 drops 85°C below the bank average. Vibration harmonic 2X spikes. Component isolation locks onto Cylinder #3.",
        citation: "XGBoost 8-Class Fault Classifier · Diagnostic Confidence 94.6%",
        camPreset: "fault_cyl3",
        shading: "pbr",
        fault: "combustion_cyl3",
        hud: [
          { label: "DIAGNOSIS", val: "CYL #3 COMBUSTION LOSS", highlight: "red" },
          { label: "CONFIDENCE", val: "94.6% [LOCKED]", highlight: "red" },
          { label: "EGT 3 DELTA", val: "-85.2 °C (EGT3: 728°C)", highlight: "red" },
          { label: "OIL CONTAMINATION", val: "FERROUS DEBRIS INCIPIENT", highlight: "amber" }
        ],
        backdropImage: "assets/07_fault_combustion_failure_cyl_1.png",
        splitScreen: false,
        theme: "red"
      },
      {
        id: "prediction",
        phase: "PROGNOSTICS & RUL",
        title: "How Long Do We Have? RUL: 2h 10m",
        caption: "Particle filter prognostics project remaining useful life: p50 is 2h 10m, p10 worst-case is 1h 25m. Distance to base is 1h 50m flight time.",
        citation: "Physics-Informed Degradation Particle Filter · RUL Uncertainty Envelope",
        camPreset: "hero",
        shading: "pbr",
        fault: "combustion_cyl3",
        hud: [
          { label: "RUL (p50 MEDIAN)", val: "2 H 10 MIN REMAINING", highlight: "amber" },
          { label: "RUL (p10 WORST)", val: "1 H 25 MIN [TIGHT MARGIN]", highlight: "red" },
          { label: "TIME TO HOME BASE", val: "1 H 50 MIN (MARGIN -25M)", highlight: "red" },
          { label: "TIME TO DIVERT AFS", val: "38 MIN (AWANTIPORA AFS)", highlight: "cyan" }
        ],
        backdropImage: "assets/01_hero_front_left.png",
        splitScreen: false,
        theme: "red"
      },
      {
        id: "decision",
        phase: "AUTONOMOUS DECISION SUPPORT",
        title: "What Should We Do? SAARTHI Advisory",
        caption: "Home base is beyond the safe p10 margin. SAARTHI calculates diversion to Awantipora AFS, power reduction to 65%, and gradual descent.",
        citation: "SAARTHI Tactical Copilot · Automated Divert & Power Management",
        camPreset: "hero",
        shading: "pbr",
        fault: "combustion_cyl3",
        hud: [
          { label: "PILOT ADVISORY", val: "DIVERT TO AWANTIPORA AFS", highlight: "cyan" },
          { label: "THROTTLE ACTION", val: "REDUCE POWER TO 65% MAX", highlight: "amber" },
          { label: "DESCENT PROFILE", val: "DESCEND TO 12,000 FT AGL", highlight: "cyan" },
          { label: "RECOVERY PROB", val: "99.1% SAFE RETURN", highlight: "cyan" }
        ],
        backdropImage: "assets/01_hero_front_left.png",
        splitScreen: false,
        theme: "cyan"
      },
      {
        id: "resolution",
        phase: "MISSION RECOVERY",
        title: "Aircraft Recovered Safely: Asset Saved",
        caption: "The aircraft lands safely at Awantipora. Automated maintenance work order #WO-7102 is dispatched to ground crews with exact fault components.",
        citation: "Automated Maintenance Dispatch · Work Order #WO-7102 Generated",
        camPreset: "gearbox",
        shading: "pbr",
        fault: "none",
        hud: [
          { label: "MISSION STATUS", val: "ASSET RECOVERED SECURE", highlight: "cyan" },
          { label: "WORK ORDER", val: "#WO-7102 DISPATCHED", highlight: "cyan" },
          { label: "MAINT ACTION", val: "INSPECT INJECTOR 3 / OIL PUMP", highlight: "cyan" },
          { label: "SAVINGS", val: "$18M ASSET PRESERVED", highlight: "cyan" }
        ],
        backdropImage: "assets/05_closeup_gearbox.png",
        splitScreen: false,
        theme: "cyan"
      },
      {
        id: "counterfactual",
        phase: "THE COUNTERFACTUAL AUDIT",
        title: "Without The Twin: Catastrophic Loss at T+16:49",
        caption: "Without ANUMAAN, threshold monitoring stayed green for 2h 45m. The alarm sounded only 90 seconds before complete bearing seizure over mountains.",
        citation: "MQ-1B Djibouti Case Study (2011) Comparative Timeline Audit",
        camPreset: "hero",
        shading: "wireframe",
        fault: "none",
        hud: [
          { label: "THRESHOLD WARNING", val: "T+16:47:30 (90 SEC NOTICE)", highlight: "red" },
          { label: "ENGINE SEIZURE", val: "T+16:49:00 (CATASTROPHIC)", highlight: "red" },
          { label: "LEAD TIME GAINED", val: "+2 H 47 MIN VIA ANUMAAN", highlight: "cyan" },
          { label: "OUTCOME", val: "CRASH AVOIDED / ASSET SAVED", highlight: "cyan" }
        ],
        backdropImage: "assets/06_wireframe_clay.png",
        splitScreen: false,
        theme: "red"
      },
      {
        id: "replay",
        phase: "POST-FLIGHT FORENSICS",
        title: "Every Flight Is Evidence: Replay Engine",
        caption: "SMRITI flight data recorder stores 20 Hz synchronized telemetry and physics states. Operators scrub backwards to inspect the first microsecond of divergence.",
        citation: "SMRITI Mission Knowledge Graph · 100% Deterministic Replay",
        camPreset: "fuel",
        shading: "pbr",
        fault: "none",
        hud: [
          { label: "REPLAY RECORDER", val: "SMRITI FLIGHT RECORDER", highlight: "cyan" },
          { label: "DATA DENSITY", val: "20 HZ SYNCHRONIZED LOGS", highlight: "cyan" },
          { label: "SCRUBBER MARKER", val: "FIRST SIGNAL @ T-2H 47M", highlight: "amber" },
          { label: "EXPORT FORMAT", val: "HDF5 / PARQUET / ARINC-429", highlight: "cyan" }
        ],
        backdropImage: "assets/04_closeup_fuel_system.png",
        splitScreen: false,
        theme: "cyan"
      },
      {
        id: "before_flight",
        phase: "PRE-FLIGHT SIMULATION",
        title: "Tomorrow's Mission, Tested Tonight: KALPANA",
        caption: "Simulate engine thermodynamic behavior before takeoff. Ladakh high-altitude cold (-31°C, 25,000 ft) vs Thar desert heat (+48°C, 3,000 ft).",
        citation: "KALPANA Mission Simulation Studio · Environmental What-If Engine",
        camPreset: "turbo",
        shading: "pbr",
        fault: "none",
        hud: [
          { label: "LADAKH PROFILE", val: "25,000 FT / -31°C [GO]", highlight: "cyan" },
          { label: "THAR PROFILE", val: "3,000 FT / +48°C [CAUTION]", highlight: "amber" },
          { label: "COOLING MARGIN", val: "THAR: CHT MARGIN TIGHT (9°C)", highlight: "amber" },
          { label: "TURBO PR LIMIT", val: "LADAKH: PR 3.42 [WITHIN 3.80]", highlight: "cyan" }
        ],
        backdropImage: "assets/03_closeup_turbo.png",
        splitScreen: false,
        theme: "cyan"
      },
      {
        id: "fleet",
        phase: "STRATEGIC FLEET SCALE",
        title: "Every Engine in the Fleet: 87 MALE UAVs",
        caption: "India has approved 87 indigenous MALE UAVs. Every one carries an engine with no long historical service record. ANUMAAN pools fleet intelligence.",
        citation: "Cabinet Committee on Security (CCS) · Tapas / Archer Procurement Roadmap",
        camPreset: "hero",
        shading: "pbr",
        fault: "none",
        hud: [
          { label: "FLEET SIZE", val: "87 MALE DRONES APPROVED", highlight: "cyan" },
          { label: "BASES MONITORED", val: "AWANTIPORA / BHATINDA / UTTARLAI", highlight: "cyan" },
          { label: "FLEET LEARNING", val: "FEDERATED TWIN KNOWLEDGE GRAPH", highlight: "cyan" },
          { label: "FLEET READINESS", val: "94.2% MISSION CAPABLE", highlight: "cyan" }
        ],
        backdropImage: "assets/engine_master_hero.png",
        splitScreen: false,
        theme: "cyan"
      },
      {
        id: "architecture",
        phase: "THE 6 NAMED LAYERS",
        title: "How It Works: The ANUMAAN Stack",
        caption: "NADI (Telemetry), TATTVA (Physics), ANUMAAN (AI/ML), KALPANA (Simulation), SMRITI (Memory), SAARTHI (Copilot).",
        citation: "Project ANUMAAN System Architecture Specification v2.4",
        camPreset: "wireframe",
        shading: "pbr",
        fault: "none",
        hud: [
          { label: "LAYER 1", val: "NADI [PULSE / CAN BUS]", highlight: "cyan" },
          { label: "LAYER 2", val: "TATTVA [PHYSICS MODEL]", highlight: "cyan" },
          { label: "LAYER 3", val: "ANUMAAN [AI DIAGNOSTICS]", highlight: "cyan" },
          { label: "LAYERS 4-6", val: "KALPANA · SMRITI · SAARTHI", highlight: "cyan" }
        ],
        backdropImage: "assets/06_wireframe_clay.png",
        splitScreen: false,
        theme: "cyan"
      },
      {
        id: "proof",
        phase: "VERIFICATION & EVIDENCE",
        title: "Measured, Not Claimed: 83 Requirements",
        caption: "100% of DRDO PS-26054 requirements traced and verified. 2h 47m advance warning demonstrated with 0.02 false alarms per 10 flight hours.",
        citation: "DRDO Technical Acceptance Report & Verification Matrix",
        camPreset: "hero",
        shading: "pbr",
        fault: "none",
        hud: [
          { label: "DRDO PS-26054", val: "83/83 REQUIREMENTS TRACED", highlight: "cyan" },
          { label: "LEAD TIME GAIN", val: "+2 H 47 MIN ADVANCE WARNING", highlight: "cyan" },
          { label: "FALSE ALARMS", val: "< 0.02 PER 10 FLIGHT HOURS", highlight: "cyan" },
          { label: "RUL ACCURACY", val: "91.4% COVERAGE (p10–p90)", highlight: "cyan" }
        ],
        backdropImage: "assets/engine_master_hero.png",
        splitScreen: false,
        theme: "cyan"
      },
      {
        id: "live",
        phase: "INTERACTIVE LIVE TWIN",
        title: "Launch The Live Digital Twin",
        caption: "Explore the 3D engine with Blender camera director presets, inject live faults, and observe real-time telemetry response.",
        citation: "Click 'Launch Viewport' or press 'L' to enter the live interactive twin",
        camPreset: "hero",
        shading: "pbr",
        fault: "none",
        hud: [
          { label: "INTERACTIVE TWIN", val: "READY FOR FLIGHT CREW", highlight: "cyan" },
          { label: "BLENDER RIG", val: "DCC PRESETS AVAILABLE", highlight: "cyan" },
          { label: "FAULT INJECTION", val: "5 CANONICAL FAULTS LOADED", highlight: "amber" },
          { label: "CONTROL", val: "PRESS 'L' FOR LIVE VIEWPORT", highlight: "cyan" }
        ],
        backdropImage: "assets/engine_master_hero.png",
        splitScreen: false,
        theme: "cyan"
      }
    ];

    this.activeSceneIndex = 0;
    this.totalScenes = this.scenes.length;
  }

  // Get current scene data
  getCurrentScene() {
    return this.scenes[this.activeSceneIndex];
  }

  // Jump to specific scene by index
  goToScene(index) {
    if (index < 0 || index >= this.totalScenes) return;

    this.activeSceneIndex = index;
    const scene = this.scenes[index];

    // 1. Update Camera Preset
    if (this.director && scene.camPreset) {
      this.director.applyPreset(scene.camPreset, true);
    }

    // 2. Update Engine Model Shading & Fault Highlights
    if (this.engineModel) {
      if (scene.shading) {
        this.engineModel.setShadingMode(scene.shading);
      }
      if (scene.fault) {
        this.engineModel.highlightFault(scene.fault);
      }
    }

    // 2b. Update Drone Airframe vs Engine Propulsion 3D Mode
    if (window.droneModel) {
      if (scene.id === 'aircraft' || scene.id === 'stakes' || scene.id === 'recovery') {
        window.droneModel.setMode('flight');
        window.droneModel.playAnimation(0);
      } else if (scene.id === 'promise') {
        window.droneModel.setMode('drone');
      } else {
        window.droneModel.setMode('engine');
      }
    }

    // 3. Audio Sound Effects
    if (window.tacticalAudio && window.tacticalAudio.enabled) {
      if (scene.theme === 'amber') {
        window.tacticalAudio.playCautionChime();
      } else if (scene.theme === 'red') {
        window.tacticalAudio.playWarningAlarm();
      } else {
        window.tacticalAudio.playUiClick();
      }
    }

    // 4. Update Global State Store
    if (window.anumaanStore) {
      window.anumaanStore.setState({
        activeSceneIndex: index,
        storyProgress: index / (this.totalScenes - 1)
      });
    }

    // 5. Render HUD Overlays to DOM
    this.renderHudOverlay();
  }

  nextScene() {
    if (this.activeSceneIndex < this.totalScenes - 1) {
      this.goToScene(this.activeSceneIndex + 1);
    }
  }

  prevScene() {
    if (this.activeSceneIndex > 0) {
      this.goToScene(this.activeSceneIndex - 1);
    }
  }

  // Render HUD Overlay into DOM elements
  renderHudOverlay() {
    const scene = this.getCurrentScene();
    if (!scene) return;

    // Phase & Ruler
    const phaseLabel = document.getElementById("ruler-phase-text");
    if (phaseLabel) {
      phaseLabel.textContent = `SCENE ${String(this.activeSceneIndex).padStart(2, '0')} // ${scene.phase}`;
    }

    // Update Ticks
    const ticks = document.querySelectorAll(".ruler-tick");
    ticks.forEach((tick, i) => {
      tick.className = "ruler-tick";
      if (i < this.activeSceneIndex) {
        tick.classList.add("passed");
      } else if (i === this.activeSceneIndex) {
        tick.classList.add("active");
        if (scene.theme === 'amber') tick.classList.add("amber");
        if (scene.theme === 'red') tick.classList.add("red");
      }
    });

    // Headline & Tag
    const tagEl = document.getElementById("story-scene-tag");
    const titleEl = document.getElementById("story-scene-title");
    if (tagEl) {
      tagEl.textContent = `// ${scene.phase}`;
      tagEl.className = `story-scene-tag ${scene.theme}`;
    }
    if (titleEl) {
      titleEl.textContent = scene.title;
    }

    // Caption & Citation
    const captionEl = document.getElementById("story-caption-text");
    const citationEl = document.getElementById("story-citation-text");
    if (captionEl) captionEl.textContent = scene.caption;
    if (citationEl) citationEl.textContent = scene.citation;

    // HUD Stack
    const hudStack = document.getElementById("story-hud-stack");
    if (hudStack && scene.hud) {
      hudStack.innerHTML = scene.hud.map(item => `
        <div class="hud-telemetry-row highlight-${item.highlight || 'cyan'}">
          <span class="hud-telemetry-label">${item.label}</span>
          <span class="hud-telemetry-val">${item.val}</span>
        </div>
      `).join('');
    }

    // Split Screen
    const divider = document.getElementById("split-screen-divider");
    if (divider) {
      if (scene.splitScreen) {
        divider.classList.add("active");
      } else {
        divider.classList.remove("active");
      }
    }

    // Photographic Backdrop Image
    const backdrop = document.getElementById("story-image-backdrop");
    if (backdrop) {
      if (scene.backdropImage) {
        backdrop.style.backgroundImage = `url('${scene.backdropImage}')`;
        backdrop.classList.add("active");
      } else {
        backdrop.classList.remove("active");
      }
    }
  }
}

window.MissionStoryRunner = MissionStoryRunner;
