const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ENGINES = [
  { id: 'rotax_912is', name: 'Rotax 912 iS Sport', fault: 'COOLING_DEGRADATION', cyl: null },
  { id: 'rotax_914', name: 'Rotax 914 UL/F', fault: 'COOLING_DEGRADATION', cyl: null },
  { id: 'rotax_915is', name: 'Rotax 915 iS', fault: 'COOLING_DEGRADATION', cyl: null },
  { id: 'austro_ae300', name: 'Austro Engine AE300', fault: 'COOLING_DEGRADATION', cyl: null },
  { id: 'vrde_jayem_2_2l', name: 'VRDE-Jayem 2.2L Turbodiesel', fault: 'COOLING_DEGRADATION', cyl: null },
];

const OUT_DIR = path.resolve(__dirname, '../.playwright-mcp/phase10_matrix');
fs.mkdirSync(OUT_DIR, { recursive: true });

async function run() {
  console.log('=== STARTING 5-ENGINE FULL END-TO-END VERIFICATION ===');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  const matrix = [];

  for (const eng of ENGINES) {
    console.log(`\n--- Verifying Engine: ${eng.name} (${eng.id}) ---`);
    const result = {
      engine: eng.name,
      id: eng.id,
      runtime: false,
      physics: false,
      telemetry: false,
      faults: false,
      detection: false,
      diagnosis: false,
      reliability: false,
      twin3d: false,
    };

    // 1. Backend REST verification
    try {
      // Select engine
      const selRes = await page.request.post('http://127.0.0.1:8000/api/engines/select', {
        data: { engine_id: eng.id },
      });
      if (selRes.ok()) result.runtime = true;

      // Check state
      const stateRes = await page.request.get(`http://127.0.0.1:8000/api/engines/${eng.id}/state`);
      if (stateRes.ok()) {
        const state = await stateRes.json();
        if (state.channels && state.channels.rpm > 0) {
          result.physics = true;
          result.telemetry = true;
        }
      }

      // Check reliability
      const relRes = await page.request.get(`http://127.0.0.1:8000/api/engines/${eng.id}/reliability?hours=18`);
      if (relRes.ok()) {
        const rel = await relRes.json();
        if (rel.reliability > 0 && rel.limiting_component && rel.derate_options?.length > 0) {
          result.reliability = true;
        }
      }

      // Inject fault
      const faultRes = await page.request.post(`http://127.0.0.1:8000/api/engines/${eng.id}/faults`, {
        data: { mode: eng.fault, severity: 0.9, ramp_sec: 1.0 },
      });
      if (faultRes.ok()) result.faults = true;

      // Wait 3 seconds for detector & diagnosis to trigger on injected fault
      await page.waitForTimeout(3000);

      // Check diagnosis
      const diagRes = await page.request.get(`http://127.0.0.1:8000/api/engines/${eng.id}/diagnosis`);
      if (diagRes.ok()) {
        const diag = await diagRes.json();
        if (diag.diagnosis && diag.diagnosis.length > 0) {
          result.diagnosis = true;
          result.detection = true;
        } else {
          // Check state for detection alarm
          const st = await (await page.request.get(`http://127.0.0.1:8000/api/engines/${eng.id}/state`)).json();
          if (st.detection && (st.detection.raw_alarm || st.detection.confirmed || Object.values(st.detection.ratios || {}).some(r => r > 1.0))) {
            result.detection = true;
          }
        }
      }

      // Clear fault
      await page.request.delete(`http://127.0.0.1:8000/api/engines/${eng.id}/faults`);
    } catch (e) {
      console.error(`Backend check error on ${eng.id}:`, e.message);
    }

    // 2. Frontend UI verification: Multi-Engine Runtime tab
    try {
      await page.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(2000);

      // Click "Multi-Engine Runtime" tab
      const runtimeTab = page.locator('button', { hasText: 'Multi-Engine Runtime' });
      if (await runtimeTab.count() > 0) {
        await runtimeTab.click();
        await page.waitForTimeout(1500);

        // Select the engine in the dropdown or fleet grid
        const select = page.locator('select').first();
        if (await select.count() > 0) {
          await select.selectOption(eng.id);
          await page.waitForTimeout(2000);
        }

        // Capture screenshot of Multi-Engine Runtime Console for this engine
        const rtShot = path.join(OUT_DIR, `${eng.id}_runtime_console.png`);
        await page.screenshot({ path: rtShot });
        console.log(`Saved screenshot: ${rtShot}`);
      }

      // 3. Frontend UI verification: 3D Digital Twin tab
      const twinTab = page.locator('button', { hasText: '3D Digital Twin' });
      if (await twinTab.count() > 0) {
        await twinTab.click();
        await page.waitForTimeout(3000);

        // Select engine in Twin if needed
        const twinSelect = page.locator('select').first();
        if (await twinSelect.count() > 0) {
          await twinSelect.selectOption(eng.id);
          // Wait for GLB load
          await page.waitForTimeout(8000);
        }

        const twinShot = path.join(OUT_DIR, `${eng.id}_3d_twin.png`);
        await page.screenshot({ path: twinShot });
        console.log(`Saved screenshot: ${twinShot}`);
        result.twin3d = true;
      }
    } catch (e) {
      console.error(`UI check error on ${eng.id}:`, e.message);
    }

    matrix.push(result);
  }

  await browser.close();

  console.log('\n================ FINAL VERIFICATION MATRIX ================');
  console.table(matrix);

  fs.writeFileSync(
    path.join(OUT_DIR, 'verification_matrix.json'),
    JSON.stringify(matrix, null, 2),
    'utf-8'
  );
  console.log(`Matrix saved to ${path.join(OUT_DIR, 'verification_matrix.json')}`);
}

run().catch((err) => {
  console.error('Test run failed:', err);
  process.exit(1);
});
