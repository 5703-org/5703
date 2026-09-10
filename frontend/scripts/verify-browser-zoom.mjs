import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';

// Change Chromium's native Page zoom preference through browser settings.
// No CSS zoom, deviceScaleFactor, setViewportSize or pageScaleFactor is used.
const profileRoot = path.resolve('../../.browser-test-profiles');
const profile = path.join(profileRoot, `zoom-${Date.now()}`);
const output = path.resolve('../artifacts/reports/frontend');
const fixture = JSON.parse(await fs.readFile('../evidence/integration/ui_stress_fixture.json', 'utf8'));
const context = await chromium.launchPersistentContext(profile, { channel: 'chromium', headless: true, viewport: null, args: ['--window-size=1280,1000'] });
const results = [];
try {
  const settings = context.pages()[0];
  await settings.goto('chrome://settings/appearance');
  const zoom = settings.locator('#zoomLevel');
  await zoom.selectOption({ label: '100%' });
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:5173/login');
  await page.getByLabel('Email', { exact: true }).fill('student2@example.com');
  await page.getByLabel('Password', { exact: true }).fill('Passw0rd!');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeVisible();
  await page.goto(`http://127.0.0.1:5173/chat/${fixture.session_id}`);
  await expect(page.locator('[data-answer-id]')).toHaveAttribute('data-answer-id', fixture.answer_id);
  const baseline = await page.evaluate(() => ({ innerWidth, innerHeight, devicePixelRatio, outerWidth, outerHeight }));
  const draft = 'This draft survives real browser zoom.';
  await page.getByRole('textbox', { name: 'Message Learning Assistant' }).fill(draft);
  let submissions = 0;
  page.on('request', request => { if (request.method() === 'POST' && request.url().endsWith('/messages')) submissions++; });
  for (const percentage of [125, 150, 200, 400]) {
    await zoom.selectOption({ label: `${percentage}%` });
    await page.waitForFunction(({ baselineDpr, percentage }) => Math.abs(devicePixelRatio / baselineDpr - percentage / 100) < 0.02, { baselineDpr: baseline.devicePixelRatio, percentage });
    await page.getByRole('textbox', { name: 'Message Learning Assistant' }).focus();
    await expect(page.getByRole('textbox', { name: 'Message Learning Assistant' })).toHaveValue(draft);
    await expect(page.locator('[data-answer-id]')).toHaveAttribute('data-answer-id', fixture.answer_id);
    const metrics = await page.evaluate(() => {
      const send = document.querySelector('.send-button').getBoundingClientRect();
      return { innerWidth, innerHeight, outerWidth, outerHeight, devicePixelRatio, visualViewportScale: visualViewport.scale, documentWidth: document.documentElement.scrollWidth, bodyWidth: document.body.scrollWidth, send: { left: send.left, right: send.right, top: send.top, bottom: send.bottom, width: send.width, height: send.height } };
    });
    expect(metrics.documentWidth).toBeLessThanOrEqual(metrics.innerWidth + 1);
    expect(metrics.bodyWidth).toBeLessThanOrEqual(metrics.innerWidth + 1);
    expect(metrics.send.right).toBeLessThanOrEqual(metrics.innerWidth + 1);
    expect(metrics.send.bottom).toBeLessThanOrEqual(metrics.innerHeight + 1);
    expect(metrics.send.width).toBeGreaterThanOrEqual(44);
    expect(metrics.send.height).toBeGreaterThanOrEqual(44);
    await page.getByRole('button', { name: 'Open source 1' }).last().click();
    await expect(page.locator('.source-passage')).toBeVisible();
    await page.getByRole('dialog').getByRole('button', { name: /^Close / }).click();
    // Capture the compositor's complete visible surface. Playwright's default
    // screenshot clipping assumes its configured DPR, which native zoom changes.
    const capture = await (await context.newCDPSession(page)).send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false, fromSurface: true });
    await fs.writeFile(path.join(output, `native-browser-zoom-${percentage}.png`), Buffer.from(capture.data, 'base64'));
    results.push({ percentage, settings_option: `${percentage}%`, ...metrics, source_open_close: true, draft_preserved: true, answer_preserved: true });
  }
  expect(results.at(-1).innerWidth).toBeLessThanOrEqual(320);
  expect(submissions).toBe(0);
  await fs.writeFile(path.join(output, 'real-browser-zoom.json'), JSON.stringify({ passed: true, browser: await context.browser()?.version(), mechanism: 'Chromium native settings Appearance > Page zoom dropdown; persistent isolated test profile; native fixed 1280px window; no viewport or scale emulation', baseline, results, duplicate_submissions: submissions, fixture_kind: fixture.fixture_kind, physical_mobile_keyboard: 'Not verified: no physical device available', native_ime: 'Not verified: synthetic composition event coverage is separate' }, null, 2));
  console.log(JSON.stringify({ passed: true, results }, null, 2));
} finally {
  await context.close();
  if (profile.startsWith(profileRoot + path.sep)) await fs.rm(profile, { recursive: true, force: true });
}
