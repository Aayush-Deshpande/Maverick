const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const OUT_DIR = path.resolve('.playwright-mcp', 'phase1');
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

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      console.error('[Browser Error]:', msg.text());
    }
  });

  page.on('response', (res) => {
    if (res.status() === 404 && res.url().includes('/api/replay')) {
      console.error('[404 on replay]:', res.url());
    }
  });

  console.log('Navigating to http://127.0.0.1:5173...');
  await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });

  // 1. Switch to Legacy GCS workspace
  console.log('Clicking Legacy GCS workspace button...');
  await page.getByRole('button', { name: 'Legacy GCS' }).click();
  await page.waitForTimeout(1000);

  // 2. Click Mission Replay tab
  console.log('Navigating to Mission Replay...');
  const replayTab = page.getByRole('button', { name: 'Mission Replay' });
  await replayTab.click();
  await page.waitForTimeout(1000);

  // Find the sortie select element
  const sortieSelect = page.locator('select');
  await sortieSelect.waitFor({ state: 'visible', timeout: 5000 });
  const options = await sortieSelect.locator('option').allInnerTexts();
  console.log(`Found ${options.length} sorties in dropdown. First few:`, options.slice(0, 5));

  // Select a live sortie or mission_007
  const optionValues = await sortieSelect.locator('option').evaluateAll((opts) => opts.map(o => o.value));
  const targetSortie = optionValues.find(v => v.includes('SORTIE-SRV') || v === 'mission_007') || optionValues[1];
  console.log(`Selecting sortie: ${targetSortie}`);
  await sortieSelect.selectOption(targetSortie);
  await page.waitForTimeout(1500);

  // Scrub the timeline
  const slider = page.locator('input[type="range"]');
  if (await slider.isVisible()) {
    console.log('Scrubbing timeline slider...');
    await slider.fill('5');
    await slider.dispatchEvent('change');
    await page.waitForTimeout(1000);
  }

  // Click Play
  const playButton = page.getByRole('button', { name: 'Play', exact: true });
  if (await playButton.isVisible()) {
    await playButton.click();
    await page.waitForTimeout(1500);
    const pauseButton = page.getByRole('button', { name: 'Pause', exact: true });
    if (await pauseButton.isVisible()) {
      await pauseButton.click();
    }
  }

  const replayScreenshot = path.join(OUT_DIR, '01_mission_replay_scrub.png');
  await page.screenshot({ path: replayScreenshot, fullPage: true });
  console.log(`Saved screenshot to ${replayScreenshot}`);

  // 3. Switch to Voice Copilot
  console.log('Navigating to Voice Copilot...');
  const voiceTab = page.getByRole('button', { name: 'Voice Copilot' });
  await voiceTab.click();
  await page.waitForTimeout(1500);

  // Check fallback chip
  const chip = page.locator('#voice-browser-fallback-chip');
  const chipVisible = await chip.isVisible();
  console.log('Voice fallback chip visible:', chipVisible);
  if (chipVisible) {
    const text = await chip.innerText();
    console.log('Voice fallback chip text:', text);
  }

  const voiceScreenshot = path.join(OUT_DIR, '02_voice_copilot_fallback.png');
  await page.screenshot({ path: voiceScreenshot, fullPage: true });
  console.log(`Saved screenshot to ${voiceScreenshot}`);

  await browser.close();
  console.log('Phase 1 browser verification complete!');
}

run().catch((err) => {
  console.error('Browser verification failed:', err);
  process.exit(1);
});
