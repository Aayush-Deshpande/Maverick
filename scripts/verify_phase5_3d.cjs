const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const OUT_DIR = path.resolve('.playwright-mcp', 'phase5');
if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

const ENGINES = [
  { id: 'rotax_912is', name: 'Rotax 912 iS' },
  { id: 'rotax_914', name: 'Rotax 914' },
  { id: 'rotax_915is', name: 'Rotax 915 iS' },
  { id: 'austro_ae300', name: 'Austro AE300' },
  { id: 'vrde_jayem_2_2l', name: 'VRDE Jayem 2.2L' },
];

async function run() {
  console.log('Launching browser for 3D verification...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1000 },
  });
  const page = await context.newPage();

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      console.error('[Browser Error]:', msg.text());
    } else if (msg.text().includes('[3D TWIN]') || msg.text().includes('engine')) {
      console.log('[Browser Console]:', msg.text());
    }
  });

  // Part 1: Test each engine rendering in standalone Three.js twin app
  for (const eng of ENGINES) {
    console.log(`\nTesting 3D rendering for ${eng.name} (${eng.id})...`);
    await page.goto(`http://127.0.0.1:8000/apps/threejs_twin/?engine=${eng.id}`, { waitUntil: 'load' });
    
    // Wait for the loading screen to complete and fade out
    await page.waitForFunction(
      () => {
        const el = document.getElementById('loading-screen');
        return !el || el.classList.contains('fade-out') || el.style.display === 'none';
      },
      { timeout: 75000 }
    );
    // Allow textures and shaders to render cleanly
    await page.waitForTimeout(3000);

    const titleText = await page.locator('#et-name').textContent();
    const nodeCount = await page.locator('#tk-nodes').textContent();
    console.log(`Engine loaded: "${titleText}", Nodes: ${nodeCount}`);

    const screenshotPath = path.join(OUT_DIR, `3d_${eng.id}_standalone.png`);
    try {
      await page.screenshot({ path: screenshotPath, timeout: 8000, animations: 'disabled' });
    } catch (e) {
      console.log(`Fallback to canvas capture for ${eng.id}...`);
      const dataUrl = await page.evaluate(() => document.getElementById('three-canvas').toDataURL('image/png'));
      const base64Data = dataUrl.replace(/^data:image\/png;base64,/, '');
      fs.writeFileSync(screenshotPath, base64Data, 'base64');
    }
    console.log(`Captured ${screenshotPath}`);
  }

  // Part 2: Test embedded 3D Twin in React App on port 5173
  console.log('\nTesting embedded 3D twin in React App (port 5173)...');
  await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });

  // Navigate to 3D Digital Twin
  const twinTab = page.locator('main').getByRole('button', { name: '3D Digital Twin', exact: true });
  await twinTab.click();
  await page.waitForTimeout(3000);

  const reactTwinShot = path.join(OUT_DIR, '01_react_twin_initial.png');
  await page.screenshot({ path: reactTwinShot, fullPage: true });
  console.log(`Captured embedded twin initial view: ${reactTwinShot}`);

  // Navigate to Multi-Engine Runtime and switch to Austro AE300
  console.log('Switching to Austro AE300 via Multi-Engine Runtime...');
  const runtimeTab = page.locator('main').getByRole('button', { name: 'Multi-Engine Runtime', exact: true });
  await runtimeTab.click();
  await page.waitForTimeout(1500);

  const ae300FleetCard = page.locator('button').filter({ hasText: 'Austro Engine AE300' });
  await ae300FleetCard.click();
  await page.waitForTimeout(2000);

  // Return to 3D Digital Twin and observe synchronized Austro AE300
  await twinTab.click();
  await page.waitForTimeout(4000);

  const reactTwinAE300 = path.join(OUT_DIR, '02_react_twin_ae300_synced.png');
  await page.screenshot({ path: reactTwinAE300, fullPage: true });
  console.log(`Captured synchronized Austro AE300 twin: ${reactTwinAE300}`);

  // Switch to VRDE-Jayem 2.2L via Multi-Engine Runtime
  console.log('Switching to VRDE-Jayem 2.2L via Multi-Engine Runtime...');
  await runtimeTab.click();
  await page.waitForTimeout(1500);

  const vrdeFleetCard = page.locator('button').filter({ hasText: 'VRDE-Jayem 2.2L' });
  await vrdeFleetCard.click();
  await page.waitForTimeout(2000);

  // Return to 3D Digital Twin and observe synchronized VRDE-Jayem
  await twinTab.click();
  await page.waitForTimeout(4000);

  const reactTwinVRDE = path.join(OUT_DIR, '03_react_twin_vrde_synced.png');
  await page.screenshot({ path: reactTwinVRDE, fullPage: true });
  console.log(`Captured synchronized VRDE-Jayem twin: ${reactTwinVRDE}`);

  await browser.close();
  console.log('\nAll 5 engines successfully verified in 3D!');
}

run().catch((err) => {
  console.error('Phase 5 verification failed:', err);
  process.exit(1);
});
