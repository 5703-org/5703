import { chromium } from '@playwright/test';
import fs from 'node:fs/promises';

const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge', headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto('http://127.0.0.1:5173/login');
const measurements = [];
for (let index = 0; index < 6; index++) {
  if (index) await page.keyboard.press('Control+Equal');
  measurements.push(await page.evaluate(() => ({ innerWidth, outerWidth, devicePixelRatio, visualViewportScale: visualViewport?.scale, rootFontSize: getComputedStyle(document.documentElement).fontSize })));
}
await browser.close();
await fs.mkdir('../artifacts/reports/frontend', { recursive: true });
await fs.writeFile('../artifacts/reports/frontend/keyboard-zoom-probe.json', JSON.stringify({ mechanism: 'Browser keyboard shortcut Control+Equal, not CSS transform or device-scale emulation', measurements, actual_zoom_observed: new Set(measurements.map(item => item.devicePixelRatio)).size > 1 }, null, 2));
console.log(JSON.stringify(measurements));
