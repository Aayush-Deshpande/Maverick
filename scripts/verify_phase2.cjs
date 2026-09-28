const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const OUT_DIR = path.resolve('.playwright-mcp', 'phase2');
if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

async function run() {
  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    permissions: ['microphone'],
  });
  const page = await context.newPage();

  const errors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      console.error('[Browser Error]:', msg.text());
      errors.push(msg.text());
    }
  });

  console.log('Navigating to http://127.0.0.1:5173...');
  await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });

  const tabs = [
    { name: 'Flight Deck', file: '01_flight_deck.png' },
    { name: 'Propulsion', file: '02_propulsion.png' },
    { name: '3D Digital Twin', file: '03_digital_twin.png' },
    { name: 'Multi-Engine Runtime', file: '04_multi_engine_runtime.png' },
    { name: 'Maintenance / CBM', file: '05_maintenance_cbm.png' },
    { name: 'AI & Voice', file: '06_ai_voice.png' },
    { name: 'Mission Replay', file: '07_mission_replay.png' },
  ];

  for (const tab of tabs) {
    console.log(`Clicking tab: ${tab.name}...`);
    const btn = page.locator('main').getByRole('button', { name: tab.name, exact: true });
    await btn.click();
    await page.waitForTimeout(1000);
    const screenshotPath = path.join(OUT_DIR, tab.file);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`Saved screenshot to ${screenshotPath}`);
  }

  await browser.close();
  if (errors.length > 0) {
    console.log(`Finished with ${errors.length} browser errors.`);
  } else {
    console.log('Phase 2 all 7 navigation areas verified with 0 errors!');
  }
}

run().catch((err) => {
  console.error('Phase 2 verification failed:', err);
  process.exit(1);
});
