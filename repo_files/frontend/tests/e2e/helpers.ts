import { expect, type Page } from '@playwright/test';
export const email = process.env.TEST_LEARNER_EMAIL || 'student2@example.com';
export const password = process.env.TEST_ACCOUNT_PASSWORD || 'Passw0rd!';
export async function login(page: Page, actor = email) {
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill(actor);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeVisible();
  await expect(page.getByText('Demo (mock model)', { exact: true }).first()).toBeVisible();
}
export async function apiCall(page: Page, path: string, method = 'GET', data?: unknown) {
  const token = await page.evaluate(() => sessionStorage.getItem('cs30.access-token'));
  const response = await page.request.fetch(`/api/v1${path}`, { method, data, headers: { Authorization: `Bearer ${token}`, 'Idempotency-Key': crypto.randomUUID() } });
  const body = await response.json();
  expect(response.ok(), `${method} ${path}: ${JSON.stringify(body.error || {})}`).toBeTruthy();
  return body.data;
}
export async function send(page: Page, question: string) {
  const before = await page.locator('[data-answer-id]').count();
  await page.getByRole('textbox', { name: 'Message Learning Assistant' }).fill(question);
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  await expect(page.locator('[data-answer-id]')).toHaveCount(before + 1, { timeout: 30000 });
  await expect(page.getByRole('button', { name: 'Stop generation', exact: true })).toHaveCount(0);
  return page.locator('[data-answer-id]').last();
}
export async function assertShell(page: Page, width: number) {
  const bounds = await page.evaluate(() => {
    const selectors = ['.topbar', '.chat-workspace', '.composer', '.composer textarea', '.send-button', '.profile-toggle', '.user-bubble', '.assistant-message'];
    return { viewport: innerWidth, scrollWidth: document.documentElement.scrollWidth, bodyWidth: document.body.scrollWidth, elements: selectors.flatMap(selector => [...document.querySelectorAll<HTMLElement>(selector)].filter(node => node.getClientRects().length > 0).map(node => { const r = node.getBoundingClientRect(); return { selector, left: r.left, right: r.right, width: r.width, top: r.top, bottom: r.bottom }; })) };
  });
  expect(bounds.scrollWidth).toBeLessThanOrEqual(width + 1);
  expect(bounds.bodyWidth).toBeLessThanOrEqual(width + 1);
  for (const item of bounds.elements) { expect(item.left, item.selector).toBeGreaterThanOrEqual(-1); expect(item.right, item.selector).toBeLessThanOrEqual(width + 1); }
  if (await page.locator('.send-button').count()) {
    const send = await page.locator('.send-button').boundingBox();
    expect(send!.y + send!.height).toBeLessThanOrEqual((await page.viewportSize())!.height + 1);
    expect(send!.width).toBeGreaterThanOrEqual(44);
    expect(send!.height).toBeGreaterThanOrEqual(44);
  }
  return bounds;
}
