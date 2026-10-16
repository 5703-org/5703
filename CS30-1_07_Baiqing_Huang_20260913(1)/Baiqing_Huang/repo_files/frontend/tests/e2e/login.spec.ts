import { test, expect } from '@playwright/test';
import fs from 'node:fs/promises';

test('login stays usable across viewport widths and short landscape', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: /Welcome to your/ })).toBeVisible();
  const results = [];
  for (const width of [320, 375, 390, 639, 640, 641, 768, 1023, 1024, 1025, 1280, 1440, 1920, 2560]) {
    await page.setViewportSize({ width, height: 900 });
    await page.getByLabel('Email', { exact: true }).fill('learner@example.com');
    await page.getByLabel('Password', { exact: true }).fill('example-password');
    const bounds = await page.evaluate(() => ({ viewport: innerWidth, scrollWidth: document.documentElement.scrollWidth, fields: [...document.querySelectorAll('input,button')].map(node => { const r = node.getBoundingClientRect(); return { left: r.left, right: r.right, width: r.width }; }) }));
    expect(bounds.scrollWidth).toBeLessThanOrEqual(width + 1);
    expect(bounds.fields.every(field => field.left >= 0 && field.right <= width + 1 && field.width >= 44)).toBe(true);
    results.push({ width, ...bounds });
    if ([320, 390, 1440].includes(width)) await page.screenshot({ path: `../artifacts/reports/frontend/login-${width}.png`, fullPage: true });
  }
  await page.setViewportSize({ width: 844, height: 390 });
  await page.getByRole('button', { name: 'Sign in', exact: true }).scrollIntoViewIfNeeded();
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeInViewport();
  await fs.mkdir('../artifacts/reports/frontend', { recursive: true });
  await fs.writeFile('../artifacts/reports/frontend/login-responsive-bounds.json', JSON.stringify({ scope: 'Actual login UI; authenticated API journeys tested separately.', results }, null, 2));
});
