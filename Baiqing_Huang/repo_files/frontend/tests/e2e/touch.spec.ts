import { test, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import { login } from './helpers';

test('emulated touch reaches source, close and feedback controls without hover', async ({ browser }) => {
  const context = await browser.newContext({ baseURL: process.env.FRONTEND_URL || 'http://127.0.0.1:5173', viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  const page = await context.newPage();
  try {
    await login(page);
    const fixture = JSON.parse(await fs.readFile('../evidence/integration/ui_stress_fixture.json', 'utf8'));
    await page.goto(`/chat/${fixture.session_id}`);
    const trigger = page.getByRole('button', { name: 'Open source 1' }).last();
    await trigger.tap();
    await expect(page.locator('.source-passage')).toBeVisible();
    await page.getByRole('button', { name: 'Close sources', exact: true }).tap();
    await expect(trigger).toBeFocused();
    await page.getByRole('button', { name: 'Feedback', exact: true }).tap();
    await expect(page.getByLabel('Comment', { exact: false })).toHaveValue('Keep this original feedback when a replacement fails.');
    await page.getByRole('button', { name: 'Close response feedback' }).tap();
    await expect(page.getByRole('button', { name: 'Send message' })).toBeInViewport();
    await fs.writeFile('../artifacts/reports/frontend/touch-controls.json', JSON.stringify({ passed: true, mechanism: 'Chromium mobile context with touch events; no hover', viewport: { width: 390, height: 844 }, physical_device: false, physical_keyboard: 'not available', source_close_feedback: true, session_id: fixture.session_id }, null, 2));
  } finally { await context.close(); }
});
