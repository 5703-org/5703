import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';

const baseURL = process.env.CLEAN_FRONTEND_URL || 'http://127.0.0.1:55173';
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
const context = await browser.newContext({ baseURL, viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
const output = '../artifacts/reports/frontend';
const errors = [];
page.on('pageerror', error => errors.push(error.message));
try {
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('student2@example.com');
  await page.getByLabel('Password', { exact: true }).fill('Passw0rd!');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeVisible();
  const questions = ['What is photosynthesis?', 'Why does it need light?'];
  for (const [index, question] of questions.entries()) {
    await page.getByRole('textbox', { name: 'Message Learning Assistant' }).fill(question);
    await page.getByRole('button', { name: 'Send message', exact: true }).click();
    await expect(page.locator('[data-answer-id]')).toHaveCount(index + 1, { timeout: 30000 });
  }
  const sessionId = new URL(page.url()).pathname.split('/')[2];
  const token = await page.evaluate(() => sessionStorage.getItem('cs30.access-token'));
  const response = await page.request.get(`/api/v1/sessions/${sessionId}/messages?limit=100`, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.ok()).toBe(true);
  const history = (await response.json()).data;
  expect(history.items).toHaveLength(4);
  expect(history.items[3].answer.conversation_snapshot.messages.length).toBeGreaterThanOrEqual(2);
  expect(history.items[3].answer.mode).toBe('interactive_chat');
  const source = history.items[1].answer.evidence[0];
  await page.locator('[data-answer-id]').first().getByRole('button', { name: 'Open source 1' }).first().click();
  await expect(page.locator('.source-passage')).toHaveText(source.text);
  await expect(page.locator('.source-title')).toHaveText(source.source_title);
  await page.getByRole('button', { name: 'Close sources' }).click();
  await page.screenshot({ path: `${output}/clean-install-chat-1440.png` });
  await page.reload();
  await expect(page.locator('[data-answer-id]')).toHaveCount(2);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.getByRole('button', { name: 'Toggle sidebar' }).click();
  await page.getByRole('button', { name: 'Close navigation' }).click();
  await page.screenshot({ path: `${output}/clean-install-chat-390.png` });
  expect(errors).toHaveLength(0);
  await fs.writeFile(`${output}/clean-install-browser.json`, JSON.stringify({ passed: true, base_url: baseURL, browser: browser.version(), deployment: 'independent clean Docker Compose build and database', session_id: sessionId, message_count: history.items.length, answer_ids: history.items.filter(item => item.answer).map(item => item.answer.id), evidence_hash: source.text_hash, followup_context_messages: history.items[3].answer.conversation_snapshot.messages.length, refresh_retained: true, mobile_sidebar_operated: true, console_errors: errors, evidence_class: 'authored/mock software validation, not live model quality' }, null, 2));
  console.log(JSON.stringify({ passed: true, baseURL, sessionId, messages: history.items.length }));
} finally { await browser.close(); }
