const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const OUT_DIR = path.resolve('.playwright-mcp', 'mission_sim');
if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

const ENGINES = [
  'rotax_912is',
  'rotax_914',
  'rotax_915is',
  'austro_ae300',
  'vrde_jayem_2_2l',
];

async function run() {
  console.log('--- Starting Mission Planning & Simulation Verification ---');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1720, height: 1080 },
  });
  const page = await context.newPage();

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      console.error('[Browser Error]:', msg.text());
    }
  });

  // 1. Open the Web Application
  console.log('Navigating to http://localhost:5173/...');
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  // 2. Click Mission Operations Nav Item
  console.log('Clicking "Mission Operations" navigation tab...');
  const missionTabBtn = page.locator('button:has-text("Mission Operations")');
  await missionTabBtn.waitFor({ state: 'visible', timeout: 10000 });
  await missionTabBtn.click();
  await page.waitForTimeout(1500);

  await page.screenshot({ path: path.join(OUT_DIR, '01_mission_operations_initial.png') });
  console.log('Captured 01_mission_operations_initial.png');

  // 3. Test Sub-Tab 1: Mission Planner & 5 Engine Presets
  console.log('Testing Mission Planner sub-tab...');
  const plannerTabBtn = page.locator('button:has-text("1. PLANNER")');
  await plannerTabBtn.click();
  await page.waitForTimeout(1000);

  // Verify all 5 engines in the dropdown
  const engineSelect = page.locator('select').first();
  for (const eng of ENGINES) {
    console.log(`Selecting engine profile: ${eng}...`);
    await engineSelect.selectOption(eng);
    await page.waitForTimeout(500);
  }

  await page.screenshot({ path: path.join(OUT_DIR, '02_mission_planner_configured.png') });
  console.log('Captured 02_mission_planner_configured.png');

  // 4. Click "VALIDATE & LAUNCH MISSION SIMULATION"
  console.log('Launching Mission Simulation...');
  const launchBtn = page.locator('button:has-text("VALIDATE & LAUNCH MISSION SIMULATION")');
  await launchBtn.click();
  await page.waitForTimeout(3000);

  // 5. Verify Sub-Tab 2: Cockpit & Canyon 3D Sim
  console.log('Inspecting Cockpit & Canyon 3D Flight Simulation...');
  await page.screenshot({ path: path.join(OUT_DIR, '03_canyon_3d_cockpit_running.png') });
  console.log('Captured 03_canyon_3d_cockpit_running.png');

  // Test Cinema View Toggle
  console.log('Testing Cinema View full-width expansion...');
  const cinemaBtn = page.locator('button:has-text("CINEMA VIEW")');
  if (await cinemaBtn.isVisible()) {
    await cinemaBtn.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(OUT_DIR, '03b_canyon_cinema_view.png') });
    console.log('Captured 03b_canyon_cinema_view.png');
    // Restore split view
    const splitBtn = page.locator('button:has-text("SPLIT VIEW")');
    if (await splitBtn.isVisible()) await splitBtn.click();
    await page.waitForTimeout(1000);
  }

  // Test Time Compression 5x
  console.log('Setting time compression to 5x...');
  const comp5xBtn = page.locator('button:has-text("5x")');
  if (await comp5xBtn.isVisible()) {
    await comp5xBtn.click();
    await page.waitForTimeout(2000);
  }

  // 6. Test Live Fault Injection
  console.log('Testing Live Fault Injection: COOLING_DEGRADATION...');
  const injectBtn = page.locator('button:has-text("TRIGGER LIVE PROPULSION FAULT")');
  if (await injectBtn.isVisible()) {
    await injectBtn.click();
    await page.waitForTimeout(4000);
  }

  await page.screenshot({ path: path.join(OUT_DIR, '04_live_fault_injected.png') });
  console.log('Captured 04_live_fault_injected.png');

  // 7. Test Operator Action: Propulsion Derate
  console.log('Commanding Operator Propulsion Derate...');
  const derateBtn = page.locator('button:has-text("DERATE 85%")');
  if (await derateBtn.isVisible()) {
    await derateBtn.click();
    await page.waitForTimeout(2000);
  }

  await page.screenshot({ path: path.join(OUT_DIR, '05_operator_derated.png') });
  console.log('Captured 05_operator_derated.png');

  // 8. Test Operator Action: Abort RTB
  console.log('Commanding Operator Abort RTB...');
  const abortBtn = page.locator('button:has-text("ABORT RTB")');
  if (await abortBtn.isVisible()) {
    await abortBtn.click();
    await page.waitForTimeout(2500);
  }

  // 9. Inspect Sub-Tab 3: Sortie Debrief
  console.log('Inspecting Sortie Debrief...');
  const debriefTabBtn = page.locator('button:has-text("3. SORTIE DEBRIEF")');
  await debriefTabBtn.click();
  await page.waitForTimeout(1500);

  await page.screenshot({ path: path.join(OUT_DIR, '06_sortie_debrief.png') });
  console.log('Captured 06_sortie_debrief.png');

  // 10. Click "OPEN IN HISTORICAL REPLAY SCRUBBER"
  console.log('Transitioning to Historical Replay Scrubber...');
  const openReplayBtn = page.locator('button:has-text("OPEN IN HISTORICAL REPLAY SCRUBBER")');
  if (await openReplayBtn.isVisible()) {
    await openReplayBtn.click();
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(OUT_DIR, '07_transitioned_to_replay.png') });
    console.log('Captured 07_transitioned_to_replay.png');
  }

  // Direct Canyon Standalone Inspection & Camera Modes
  console.log('\nInspecting standalone Canyon Flight Sim app...');
  await page.goto('http://127.0.0.1:8000/apps/canyon_flight/', { waitUntil: 'load' });
  // Wait for Bayraktar TB3 and Ladakh terrain models to load into WebGL
  await page.waitForTimeout(4000);
  await page.screenshot({ path: path.join(OUT_DIR, '08_canyon_chase_cam.png') });
  console.log('Captured 08_canyon_chase_cam.png');

  // Test Camera Modes: Cinematic Follow
  console.log('Testing CINEMATIC FOLLOW camera mode...');
  await page.click('button:has-text("CINEMATIC FOLLOW")');
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(OUT_DIR, '09_canyon_cinematic_cam.png') });
  console.log('Captured 09_canyon_cinematic_cam.png');

  // Test Camera Modes: FPV Nose
  console.log('Testing FPV NOSE camera mode...');
  await page.click('button:has-text("FPV NOSE")');
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(OUT_DIR, '10_canyon_fpv_nose_cam.png') });
  console.log('Captured 10_canyon_fpv_nose_cam.png');

  // Test Camera Modes: Free Orbit
  console.log('Testing FREE ORBIT camera mode...');
  await page.click('button:has-text("FREE ORBIT")');
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(OUT_DIR, '11_canyon_free_orbit_cam.png') });
  console.log('Captured 11_canyon_free_orbit_cam.png');

  await browser.close();
  console.log('\n--- Mission Planning & Simulation Verification COMPLETE ---');
}

run().catch((err) => {
  console.error('Verification failed:', err);
  process.exit(1);
});
