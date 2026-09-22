/**
 * PROJECT ANUMAAN — 3D DIGITAL TWIN ENGINE MODEL & SHADER SYSTEM
 * High-fidelity procedural Three.js digital twin representation of the aero piston engine
 * Supports: PBR Cast Aluminum, Wireframe Clay, X-Ray Ghost, Thermal CHT/EGT & Fault Highlighting
 */

class DigitalTwinEngineModel {
  constructor(scene) {
    this.scene = scene;
    this.rootGroup = new THREE.Group();
    this.rootGroup.name = "ANUMAAN_Engine_Root";
    this.scene.add(this.rootGroup);

    // Named Subsystem Component Mesh Registry
    this.subsystems = {};
    
    // Rotating Propeller Reference
    this.propellerGroup = null;

    // Materials Palette
    this.materials = {};
    this.initMaterials();

    // Build Mechanical Geometry
    this.buildEngineArchitecture();
  }

  initMaterials() {
    // 1. PBR Authentic Cast Aluminium (A356-T6)
    this.materials.castAlu = new THREE.MeshStandardMaterial({
      color: 0x5a6068,
      metalness: 0.48,
      roughness: 0.52,
      name: "M_CastAluminium"
    });

    // 2. PBR Machined Alloy (CNC Spigot, Flanges)
    this.materials.machinedAlloy = new THREE.MeshStandardMaterial({
      color: 0xa8b0b8,
      metalness: 0.85,
      roughness: 0.22,
      name: "M_MachinedAlloy"
    });

    // 3. Dark Steel (Propeller Flange, Flywheel)
    this.materials.darkSteel = new THREE.MeshStandardMaterial({
      color: 0x22262a,
      metalness: 0.82,
      roughness: 0.35,
      name: "M_SteelDark"
    });

    // 4. Gold Anodized Stator Shroud (Dual Alternators)
    this.materials.goldAnodized = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      metalness: 0.85,
      roughness: 0.24,
      name: "M_GoldAnodized"
    });

    // 5. Copper Stator Windings
    this.materials.copper = new THREE.MeshStandardMaterial({
      color: 0xc86432,
      metalness: 0.92,
      roughness: 0.20,
      name: "M_Copper"
    });

    // 6. Cobalt Blue (Spin-On Oil Filter)
    this.materials.cobaltBlue = new THREE.MeshStandardMaterial({
      color: 0x0a40a0,
      metalness: 0.20,
      roughness: 0.22,
      name: "M_CobaltBlue"
    });

    // 7. Royal Blue Silicone Coolant Runner
    this.materials.blueSilicone = new THREE.MeshStandardMaterial({
      color: 0x0055d4,
      metalness: 0.05,
      roughness: 0.35,
      name: "M_BlueSilicone"
    });

    // 8. White Firesleeve Hose
    this.materials.firesleeve = new THREE.MeshStandardMaterial({
      color: 0xdddddd,
      metalness: 0.02,
      roughness: 0.70,
      name: "M_FiresleeveWhite"
    });

    // 9. Satin Black Painted Metal
    this.materials.satinBlack = new THREE.MeshStandardMaterial({
      color: 0x14161a,
      metalness: 0.25,
      roughness: 0.32,
      name: "M_MetalPaintedBlack"
    });

    // 10. Fluorescent Green Torque Seal
    this.materials.torqueSeal = new THREE.MeshStandardMaterial({
      color: 0x00ff44,
      emissive: 0x00ff44,
      emissiveIntensity: 0.4,
      metalness: 0.0,
      roughness: 0.3,
      name: "M_TorqueSeal_Green"
    });

    // 11. Wireframe Clay Shading Material
    this.materials.wireframeClay = new THREE.MeshStandardMaterial({
      color: 0x888c94,
      roughness: 0.9,
      metalness: 0.1,
      wireframe: true,
      name: "M_WireframeClay"
    });

    // 12. X-Ray Ghost Holographic Material
    this.materials.xrayGhost = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      wireframe: false,
      transparent: true,
      opacity: 0.22,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      name: "M_XRayGhost"
    });
  }

  buildEngineArchitecture() {
    // -------------------------------------------------------------
    // A. ENGINE CRANKCASE & CYLINDER BLOCKS (Rotax/PD170 Architecture)
    // -------------------------------------------------------------
    const crankcaseGeo = new THREE.BoxGeometry(0.36, 0.28, 0.46);
    const crankcaseMesh = new THREE.Mesh(crankcaseGeo, this.materials.castAlu);
    crankcaseMesh.position.set(0, 0, 0.20);
    crankcaseMesh.castShadow = true;
    crankcaseMesh.receiveShadow = true;
    this.rootGroup.add(crankcaseMesh);
    this.subsystems['crankcase'] = crankcaseMesh;

    // Sump Pan (Bottom)
    const sumpGeo = new THREE.BoxGeometry(0.32, 0.14, 0.42);
    const sumpMesh = new THREE.Mesh(sumpGeo, this.materials.castAlu);
    sumpMesh.position.set(0, -0.20, 0.20);
    this.rootGroup.add(sumpMesh);
    this.subsystems['sump'] = sumpMesh;

    // 4 Individual Cylinders & Heads
    this.subsystems['cylinders'] = [];
    const cylPositions = [
      { id: 1, x: -0.16, y: 0.18, z: 0.36 },
      { id: 2, x: 0.16,  y: 0.18, z: 0.36 },
      { id: 3, x: -0.16, y: 0.18, z: 0.12 },
      { id: 4, x: 0.16,  y: 0.18, z: 0.12 },
    ];

    cylPositions.forEach((cp) => {
      const cylGroup = new THREE.Group();
      cylGroup.position.set(cp.x, cp.y, cp.z);

      // Cylinder Jug (Finned barrel)
      const barrelGeo = new THREE.CylinderGeometry(0.065, 0.065, 0.16, 24);
      const barrelMesh = new THREE.Mesh(barrelGeo, this.materials.castAlu);
      barrelMesh.castShadow = true;
      cylGroup.add(barrelMesh);

      // Cylinder Head (Top)
      const headGeo = new THREE.BoxGeometry(0.14, 0.08, 0.13);
      const headMesh = new THREE.Mesh(headGeo, this.materials.machinedAlloy);
      headMesh.position.set(0, 0.10, 0);
      headMesh.castShadow = true;
      cylGroup.add(headMesh);

      // Spark/Glow Plug
      const plugGeo = new THREE.CylinderGeometry(0.010, 0.010, 0.05, 12);
      const plugMesh = new THREE.Mesh(plugGeo, this.materials.darkSteel);
      plugMesh.position.set(0, 0.15, 0);
      cylGroup.add(plugMesh);

      this.rootGroup.add(cylGroup);
      this.subsystems[`cylinder_${cp.id}`] = cylGroup;
      this.subsystems['cylinders'].push(cylGroup);
    });

    // -------------------------------------------------------------
    // B. REDUCTION GEARBOX HOUSING & PROPELLER SNOUT (Front -Z)
    // -------------------------------------------------------------
    const gearboxGroup = new THREE.Group();
    gearboxGroup.position.set(0, 0.02, -0.05);

    // Tapered Cast Bellhousing Cone
    const bellGeo = new THREE.CylinderGeometry(0.065, 0.170, 0.24, 32);
    bellGeo.rotateX(Math.PI / 2);
    const bellMesh = new THREE.Mesh(bellGeo, this.materials.castAlu);
    bellMesh.position.set(0, 0, -0.12);
    bellMesh.castShadow = true;
    gearboxGroup.add(bellMesh);

    // Stiffener Ribs (Top and Sides)
    const topRibGeo = new THREE.BoxGeometry(0.014, 0.035, 0.22);
    const topRibMesh = new THREE.Mesh(topRibGeo, this.materials.castAlu);
    topRibMesh.position.set(0, 0.09, -0.12);
    gearboxGroup.add(topRibMesh);

    // Machined Snout Collar
    const snoutCollarGeo = new THREE.CylinderGeometry(0.050, 0.065, 0.05, 32);
    snoutCollarGeo.rotateX(Math.PI / 2);
    const snoutCollar = new THREE.Mesh(snoutCollarGeo, this.materials.machinedAlloy);
    snoutCollar.position.set(0, 0, -0.25);
    gearboxGroup.add(snoutCollar);

    // Snout Sensor Pad & Plate
    const sensorPadGeo = new THREE.BoxGeometry(0.028, 0.016, 0.022);
    const sensorPad = new THREE.Mesh(sensorPadGeo, this.materials.machinedAlloy);
    sensorPad.position.set(0, 0.060, -0.25);
    gearboxGroup.add(sensorPad);

    // Polished Propeller Shaft
    const propShaftGeo = new THREE.CylinderGeometry(0.032, 0.032, 0.05, 32);
    propShaftGeo.rotateX(Math.PI / 2);
    const propShaft = new THREE.Mesh(propShaftGeo, this.materials.machinedAlloy);
    propShaft.position.set(0, 0, -0.29);
    gearboxGroup.add(propShaft);

    // Propeller Flange (Dark steel with 6 counterbored holes)
    const flangeGeo = new THREE.CylinderGeometry(0.072, 0.072, 0.015, 36);
    flangeGeo.rotateX(Math.PI / 2);
    const flangeMesh = new THREE.Mesh(flangeGeo, this.materials.darkSteel);
    flangeMesh.position.set(0, 0, -0.32);
    flangeMesh.castShadow = true;
    gearboxGroup.add(flangeMesh);

    // 6 Counterbored Chamfer Rings on Flange Face
    for (let i = 0; i < 6; i++) {
      const angle = (i * Math.PI) / 3;
      const hx = Math.cos(angle) * 0.050;
      const hy = Math.sin(angle) * 0.050;
      const holeRingGeo = new THREE.TorusGeometry(0.0075, 0.0018, 12, 24);
      const holeRing = new THREE.Mesh(holeRingGeo, this.materials.machinedAlloy);
      holeRing.position.set(hx, hy, -0.328);
      gearboxGroup.add(holeRing);
    }

    // Center Pilot Boss & Black Nose Spinner Cap
    const capGeo = new THREE.CylinderGeometry(0.024, 0.028, 0.025, 24);
    capGeo.rotateX(Math.PI / 2);
    const capMesh = new THREE.Mesh(capGeo, this.materials.satinBlack);
    capMesh.position.set(0, 0, -0.34);
    gearboxGroup.add(capMesh);

    // Brass Sight Glass (Lower Port Side)
    const sightGlassGeo = new THREE.CylinderGeometry(0.016, 0.016, 0.010, 16);
    sightGlassGeo.rotateZ(Math.PI / 2);
    const sightGlass = new THREE.Mesh(sightGlassGeo, new THREE.MeshStandardMaterial({ color: 0xcd9b1d, metalness: 0.9, roughness: 0.2 }));
    sightGlass.position.set(-0.11, -0.07, -0.14);
    gearboxGroup.add(sightGlass);

    this.rootGroup.add(gearboxGroup);
    this.subsystems['gearbox'] = gearboxGroup;

    // -------------------------------------------------------------
    // C. DUAL ALTERNATORS (Lower Port Side)
    // -------------------------------------------------------------
    const altGroup = new THREE.Group();
    altGroup.position.set(-0.21, -0.08, 0.16);

    const buildAlternator = (yOffset) => {
      const g = new THREE.Group();
      g.position.set(0, yOffset, 0);

      // Stator Body (Gold Vented Cage)
      const bodyGeo = new THREE.CylinderGeometry(0.056, 0.056, 0.12, 32);
      bodyGeo.rotateX(Math.PI / 2);
      const bodyMesh = new THREE.Mesh(bodyGeo, this.materials.goldAnodized);
      bodyMesh.castShadow = true;
      g.add(bodyMesh);

      // Internal Copper Windings (Visible through slots)
      const copperGeo = new THREE.CylinderGeometry(0.051, 0.051, 0.08, 24);
      copperGeo.rotateX(Math.PI / 2);
      const copperMesh = new THREE.Mesh(copperGeo, this.materials.copper);
      g.add(copperMesh);

      // Front Faceplate (Satin Black with vent rings)
      const faceGeo = new THREE.CylinderGeometry(0.058, 0.058, 0.012, 32);
      faceGeo.rotateX(Math.PI / 2);
      const faceMesh = new THREE.Mesh(faceGeo, this.materials.satinBlack);
      faceMesh.position.set(0, 0, -0.065);
      g.add(faceMesh);

      // Center Hex Nut
      const nutGeo = new THREE.CylinderGeometry(0.012, 0.012, 0.014, 6);
      nutGeo.rotateX(Math.PI / 2);
      const nutMesh = new THREE.Mesh(nutGeo, this.materials.machinedAlloy);
      nutMesh.position.set(0, 0, -0.074);
      g.add(nutMesh);

      // Left Terminal Posts
      for (let i = 0; i < 3; i++) {
        const postGeo = new THREE.CylinderGeometry(0.007, 0.007, 0.024, 12);
        postGeo.rotateZ(Math.PI / 2);
        const postMesh = new THREE.Mesh(postGeo, this.materials.goldAnodized);
        postMesh.position.set(-0.062, (i - 1) * 0.022, 0);
        g.add(postMesh);
      }

      return g;
    };

    const alt1 = buildAlternator(0.065);
    const alt2 = buildAlternator(-0.075);
    altGroup.add(alt1);
    altGroup.add(alt2);

    // 3 Heavy Black Power Cables with Yellow Lugs
    for (let i = 0; i < 3; i++) {
      const curve = new THREE.CubicBezierCurve3(
        new THREE.Vector3(-0.28, -0.08 + i * 0.03, 0.16),
        new THREE.Vector3(-0.32, -0.15, 0.18),
        new THREE.Vector3(-0.30, -0.28, 0.20),
        new THREE.Vector3(-0.25, -0.34, 0.22 + i * 0.02)
      );
      const cableGeo = new THREE.TubeGeometry(curve, 20, 0.007, 8, false);
      const cableMesh = new THREE.Mesh(cableGeo, this.materials.satinBlack);
      altGroup.add(cableMesh);

      // Yellow Terminal Lug
      const lugGeo = new THREE.CylinderGeometry(0.010, 0.010, 0.016, 12);
      const lugMesh = new THREE.Mesh(lugGeo, this.materials.torqueSeal);
      lugMesh.position.set(-0.25, -0.34, 0.22 + i * 0.02);
      altGroup.add(lugMesh);
    }

    this.rootGroup.add(altGroup);
    this.subsystems['alternators'] = altGroup;

    // -------------------------------------------------------------
    // D. LUBRICATION: SPIN-ON OIL FILTER (Cobalt Blue)
    // -------------------------------------------------------------
    const filterGroup = new THREE.Group();
    filterGroup.position.set(-0.19, 0.11, 0.16);
    filterGroup.rotation.set(-0.35, 0.25, -0.20);

    const filterCanisterGeo = new THREE.CylinderGeometry(0.044, 0.044, 0.11, 24);
    const filterCanister = new THREE.Mesh(filterCanisterGeo, this.materials.cobaltBlue);
    filterGroup.add(filterCanister);

    // White Specification Label Band
    const bandGeo = new THREE.CylinderGeometry(0.0445, 0.0445, 0.035, 24);
    const bandMesh = new THREE.Mesh(bandGeo, this.materials.firesleeve);
    bandMesh.position.set(0, -0.01, 0);
    filterGroup.add(bandMesh);

    this.rootGroup.add(filterGroup);
    this.subsystems['oil_filter'] = filterGroup;

    // -------------------------------------------------------------
    // E. VIBRATION MOUNT (Finned Billet Aluminum)
    // -------------------------------------------------------------
    const mountGroup = new THREE.Group();
    mountGroup.position.set(-0.18, -0.22, 0.14);

    const mountBlockGeo = new THREE.BoxGeometry(0.05, 0.065, 0.07);
    const mountBlock = new THREE.Mesh(mountBlockGeo, this.materials.machinedAlloy);
    mountGroup.add(mountBlock);

    // 5 Horizontal Cooling Fins on Outer Flank
    for (let i = 0; i < 5; i++) {
      const finGeo = new THREE.BoxGeometry(0.016, 0.003, 0.065);
      const finMesh = new THREE.Mesh(finGeo, this.materials.machinedAlloy);
      finMesh.position.set(-0.030, -0.024 + i * 0.012, 0);
      mountGroup.add(finMesh);
    }

    // Center Hex Bolt with Green Torque Seal
    const mountBoltGeo = new THREE.CylinderGeometry(0.009, 0.009, 0.012, 6);
    mountBoltGeo.rotateZ(Math.PI / 2);
    const mountBolt = new THREE.Mesh(mountBoltGeo, this.materials.darkSteel);
    mountBolt.position.set(-0.030, 0, 0);
    mountGroup.add(mountBolt);

    const sealMarkGeo = new THREE.BoxGeometry(0.004, 0.014, 0.004);
    const sealMark = new THREE.Mesh(sealMarkGeo, this.materials.torqueSeal);
    sealMark.position.set(-0.036, 0, 0);
    mountGroup.add(sealMark);

    this.rootGroup.add(mountGroup);
    this.subsystems['engine_mount'] = mountGroup;

    // -------------------------------------------------------------
    // F. TWO-STAGE TURBOCHARGER & WASTEGATE (Starboard Side +X)
    // -------------------------------------------------------------
    const turboGroup = new THREE.Group();
    turboGroup.position.set(0.24, 0.04, 0.22);

    // HP Compressor Volute
    const compGeo = new THREE.TorusGeometry(0.048, 0.026, 16, 32);
    const compMesh = new THREE.Mesh(compGeo, this.materials.machinedAlloy);
    compMesh.rotation.y = Math.PI / 2;
    turboGroup.add(compMesh);

    // LP Turbine Volute (Cast iron dark)
    const turbGeo = new THREE.TorusGeometry(0.052, 0.028, 16, 32);
    const turbMesh = new THREE.Mesh(turbGeo, this.materials.darkSteel);
    turbMesh.position.set(0, 0, 0.10);
    turbMesh.rotation.y = Math.PI / 2;
    turboGroup.add(turbMesh);

    // Wastegate Actuator Canister & Rod
    const actGeo = new THREE.CylinderGeometry(0.022, 0.022, 0.055, 20);
    const actMesh = new THREE.Mesh(actGeo, this.materials.satinBlack);
    actMesh.position.set(0.06, 0.08, 0.05);
    turboGroup.add(actMesh);

    const rodGeo = new THREE.CylinderGeometry(0.003, 0.003, 0.09, 8);
    const rodMesh = new THREE.Mesh(rodGeo, this.materials.machinedAlloy);
    rodMesh.position.set(0.06, 0.02, 0.08);
    turboGroup.add(rodMesh);

    this.rootGroup.add(turboGroup);
    this.subsystems['turbocharger'] = turboGroup;

    // -------------------------------------------------------------
    // G. PLUMBING: ARCH HOSES & SILICONE RUNNER
    // -------------------------------------------------------------
    const plumbingGroup = new THREE.Group();

    // Horizontal Royal Blue Silicone Coolant Runner
    const runnerCurve = new THREE.LineCurve3(
      new THREE.Vector3(-0.14, 0.17, 0.02),
      new THREE.Vector3(-0.14, 0.17, 0.38)
    );
    const runnerGeo = new THREE.TubeGeometry(runnerCurve, 20, 0.016, 16, false);
    const runnerMesh = new THREE.Mesh(runnerGeo, this.materials.blueSilicone);
    plumbingGroup.add(runnerMesh);

    // Primary White Firesleeve Arch Hose (Water pump to top manifold)
    const archCurve1 = new THREE.CubicBezierCurve3(
      new THREE.Vector3(-0.12, -0.06, -0.02),
      new THREE.Vector3(-0.16, 0.18, -0.08),
      new THREE.Vector3(-0.06, 0.32, -0.04),
      new THREE.Vector3(0.00, 0.26, 0.04)
    );
    const archGeo1 = new THREE.TubeGeometry(archCurve1, 30, 0.013, 16, false);
    const archMesh1 = new THREE.Mesh(archGeo1, this.materials.firesleeve);
    plumbingGroup.add(archMesh1);

    // Secondary White Firesleeve Arch Hose (Fuel rail to cylinder head)
    const archCurve2 = new THREE.CubicBezierCurve3(
      new THREE.Vector3(-0.15, 0.04, 0.30),
      new THREE.Vector3(-0.18, 0.22, 0.22),
      new THREE.Vector3(-0.12, 0.34, 0.12),
      new THREE.Vector3(-0.06, 0.32, 0.04)
    );
    const archGeo2 = new THREE.TubeGeometry(archCurve2, 30, 0.012, 16, false);
    const archMesh2 = new THREE.Mesh(archGeo2, this.materials.firesleeve);
    plumbingGroup.add(archMesh2);

    this.rootGroup.add(plumbingGroup);
    this.subsystems['plumbing'] = plumbingGroup;

    // -------------------------------------------------------------
    // H. ROTATING PROPELLER BLADES (Animated)
    // -------------------------------------------------------------
    this.propellerGroup = new THREE.Group();
    this.propellerGroup.position.set(0, 0.02, -0.38);

    // 3 Propeller Blades (Composite carbon fiber aerofoil)
    for (let i = 0; i < 3; i++) {
      const angle = (i * 2 * Math.PI) / 3;
      const bladeGroup = new THREE.Group();
      bladeGroup.rotation.z = angle;

      const bladeGeo = new THREE.BoxGeometry(0.05, 0.48, 0.008);
      bladeGeo.translate(0, 0.26, 0);
      const bladeMesh = new THREE.Mesh(bladeGeo, this.materials.satinBlack);
      
      // Yellow Tip
      const tipGeo = new THREE.BoxGeometry(0.051, 0.05, 0.009);
      tipGeo.translate(0, 0.48, 0);
      const tipMesh = new THREE.Mesh(tipGeo, this.materials.torqueSeal);
      bladeGroup.add(bladeMesh);
      bladeGroup.add(tipMesh);

      this.propellerGroup.add(bladeGroup);
    }

    this.rootGroup.add(this.propellerGroup);
    this.subsystems['propeller'] = this.propellerGroup;
  }

  // Set Shading Mode: 'pbr' | 'wireframe' | 'ghost' | 'thermal'
  setShadingMode(mode) {
    this.rootGroup.traverse((child) => {
      if (child.isMesh && child.material) {
        if (mode === 'wireframe') {
          child.material = this.materials.wireframeClay;
        } else if (mode === 'ghost') {
          child.material = this.materials.xrayGhost;
        } else if (mode === 'thermal') {
          // False-color thermal heatmap (Red for hot exhaust, Amber for heads, Cyan for coolant)
          const matName = child.material.name || '';
          if (child.parent === this.subsystems['cylinder_3'] || child.parent === this.subsystems['turbocharger']) {
            child.material = new THREE.MeshStandardMaterial({ color: 0xef4444, emissive: 0xef4444, emissiveIntensity: 0.3 });
          } else if (child.parent === this.subsystems['plumbing']) {
            child.material = new THREE.MeshStandardMaterial({ color: 0x00f0ff, emissive: 0x00f0ff, emissiveIntensity: 0.2 });
          } else {
            child.material = new THREE.MeshStandardMaterial({ color: 0xf59e0b, emissive: 0xf59e0b, emissiveIntensity: 0.1 });
          }
        } else {
          // Restore PBR
          this.restorePbrMaterial(child);
        }
      }
    });
  }

  restorePbrMaterial(mesh) {
    const parent = mesh.parent;
    if (parent === this.subsystems['gearbox']) {
      mesh.material = (mesh.geometry.type.includes('Torus') || mesh.geometry.parameters?.radius < 0.04) ? this.materials.machinedAlloy : this.materials.castAlu;
    } else if (parent === this.subsystems['alternators']) {
      mesh.material = this.materials.goldAnodized;
    } else if (parent === this.subsystems['oil_filter']) {
      mesh.material = this.materials.cobaltBlue;
    } else if (parent === this.subsystems['engine_mount']) {
      mesh.material = this.materials.machinedAlloy;
    } else if (parent === this.subsystems['turbocharger']) {
      mesh.material = this.materials.machinedAlloy;
    } else if (parent === this.subsystems['plumbing']) {
      mesh.material = mesh.geometry.parameters?.radius < 0.014 ? this.materials.firesleeve : this.materials.blueSilicone;
    } else {
      mesh.material = this.materials.castAlu;
    }
  }

  // Highlight Fault Target Component (Pulsing Amber/Red)
  highlightFault(faultType) {
    // Reset any previous highlights
    this.clearFaultHighlights();

    if (faultType === 'none') return;

    let target = null;
    if (faultType === 'combustion_cyl3') {
      target = this.subsystems['cylinder_3'];
    } else if (faultType === 'coolant_loss') {
      target = this.subsystems['plumbing'];
    } else if (faultType === 'turbo_fouling') {
      target = this.subsystems['turbocharger'];
    } else if (faultType === 'rail_drop') {
      target = this.subsystems['cylinder_1'];
    } else if (faultType === 'sensor_rpm_drift') {
      target = this.subsystems['gearbox'];
    }

    if (target) {
      target.traverse((child) => {
        if (child.isMesh) {
          child.userData.originalMaterial = child.material;
          child.material = new THREE.MeshStandardMaterial({
            color: 0xef4444,
            emissive: 0xef4444,
            emissiveIntensity: 0.6,
            roughness: 0.3,
            metalness: 0.5
          });
        }
      });
    }
  }

  clearFaultHighlights() {
    this.rootGroup.traverse((child) => {
      if (child.isMesh && child.userData.originalMaterial) {
        child.material = child.userData.originalMaterial;
        delete child.userData.originalMaterial;
      }
    });
  }

  // Update loop for animations (Spinning propeller & fault pulse)
  update(delta, rpm = 5200) {
    if (this.propellerGroup) {
      // Propeller speed in rad/sec: (RPM * 2 * PI) / 60
      // Scaled down visually for crisp rendering
      const rotSpeed = (rpm / 60) * 0.4;
      this.propellerGroup.rotation.z += rotSpeed * delta;
    }
  }
}

window.DigitalTwinEngineModel = DigitalTwinEngineModel;
