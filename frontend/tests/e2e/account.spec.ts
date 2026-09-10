import { test, expect } from '@playwright/test';
import { apiCall, assertShell, login } from './helpers';

test('real login, current preferences, resize and account navigation', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page);
  await page.screenshot({ path: '../artifacts/reports/frontend/chat-empty-1440.png' });
  await page.getByRole('button', { name: 'Learning preferences' }).click();
  await expect(page.getByRole('heading', { name: 'Make explanations work for you.' })).toBeVisible();
  await page.getByRole('radio', { name: /Beginner/ }).check();
  await page.getByLabel('Explanation style').selectOption('detailed');
  await page.getByRole('button', { name: 'Save preferences', exact: true }).click();
  await expect(page.getByText('Preferences saved', { exact: true })).toBeVisible();
  const saved = await apiCall(page, '/profiles/me');
  expect(saved.level).toBe('beginner'); expect(saved.style).toBe('detailed');
  for (const width of [320, 390, 640, 768]) {
    await page.setViewportSize({ width, height: 900 });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    expect(overflow).toBe(false);
    await page.getByRole('button', { name: 'Save preferences', exact: true }).scrollIntoViewIfNeeded();
    await expect(page.getByRole('button', { name: 'Save preferences', exact: true })).toBeInViewport();
  }
  await page.getByRole('button', { name: 'Reset to defaults' }).click();
  await expect(page.getByRole('radio', { name: /Intermediate/ })).toBeChecked();
  await page.goto('/chat');
  await expect(page.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await assertShell(page, 390);
  await page.screenshot({ path: '../artifacts/reports/frontend/chat-empty-390.png' });
  await page.getByRole('button', { name: 'Toggle sidebar' }).click();
  await expect(page.getByRole('dialog', { name: 'Navigation' })).toBeVisible();
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('cs30.access-token'))).toBeNull();
});
