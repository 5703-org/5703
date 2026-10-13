import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';

// Uses an actual extracted memory in the dedicated verification account. Every
// mutation is an explicit settings/edit/delete action; no answer is submitted.
const email = process.env.TEST_LEARNER_EMAIL;
const password = process.env.TEST_ACCOUNT_PASSWORD;
const memoryId = process.env.TEST_MEMORY_ID;
if (!email || !password || !memoryId) throw new Error('Supply the dedicated account and actual saved memory ID.');
const output = `../artifacts/reports/frontend/learning-memory/${new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-')}`;
await fs.mkdir(output, { recursive: true });
const sha = value => createHash('sha256').update(value).digest('hex');
const safe = error => String(error.stack || error).replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi, 'Bearer [redacted]').replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, '[redacted token]');
const record = { passed: false, started_at: new Date().toISOString(), memory_id: memoryId, answer_posts: 0, mutations: [], page_errors: [], widths: [], scope: 'Real dedicated-account memory opt-in/source/edit/CAS/deletion controls. No generated answer, fixture substitution or learning-quality rating.' };
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
const context = await browser.newContext({ baseURL: process.env.FRONTEND_URL || 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
page.on('pageerror', error => record.page_errors.push(safe(error)));
page.on('request', request => { if (request.method() === 'POST' && new URL(request.url()).pathname.endsWith('/messages')) record.answer_posts++; });
async function api(path, method = 'GET', data) {
  const token = await page.evaluate(() => sessionStorage.getItem('cs30.access-token'));
  const response = await page.request.fetch(`/api/v1${path}`, { method, data, headers: { Authorization: `Bearer ${token}` } });
  const value = await response.json();
  if (method !== 'GET') record.mutations.push({ path, method, status: response.status(), version: value.data?.version, error_code: value.error?.code || null });
  expect(response.ok(), `${method} ${path}: ${response.status()}`).toBe(true);
  return value.data;
}
async function fit(width) {
  const geometry = await page.evaluate(() => ({ width: innerWidth, scroll_width: document.documentElement.scrollWidth }));
  expect(geometry.scroll_width).toBeLessThanOrEqual(width + 1); record.widths.push(geometry);
}
try {
  record.browser_version = browser.version();
  record.frontend_source_sha256 = sha(await fs.readFile('src/Memory.tsx'));
  await page.goto('/login'); await page.getByLabel('Email', { exact: true }).fill(email); await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeVisible();
  const entries = await api('/me/memories'); const initial = entries.find(item => item.id === memoryId);
  expect(initial?.status).toBe('active'); record.initial_version = initial.version;
  const source = await api(`/me/memories/${memoryId}/source`); record.source_message_id = source.message_id; record.source_message_sha256 = sha(source.content);
  const undoId = process.env.TEST_UNDO_MEMORY_ID;
  if (undoId) {
    expect(undoId).not.toBe(memoryId);
    const undoSource = await api(`/me/memories/${undoId}/source`);
    const notices = (await api(`/sessions/${undoSource.session_id}/memory-notices`)).filter(item => item.source_message_id === undoSource.message_id && item.action === 'undo_save');
    const noticeIndex = notices.findIndex(item => item.memory_id === undoId); expect(noticeIndex).toBeGreaterThanOrEqual(0);
    await page.goto(`/chat/${undoSource.session_id}`);
    const buttons = page.getByRole('button', { name: 'Undo memory save', exact: true });
    await expect(buttons).toHaveCount(notices.length); await buttons.nth(noticeIndex).scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${output}/actual-saved-notices-1440.png` });
    const receipt = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname.endsWith(`/memories/${undoId}/undo`));
    await buttons.nth(noticeIndex).click(); const response = await receipt; expect(response.ok()).toBe(true);
    expect((await api('/me/memories')).some(item => item.id === undoId)).toBe(false);
    record.undo = { memory_id: undoId, actual_notice_version: notices[noticeIndex].version, status: response.status(), removed: true };
  }
  await page.goto('/memory'); const toggle = page.getByRole('checkbox', { name: 'Use learning memory' });
  await expect(toggle).toBeVisible(); record.initial_memory_enabled = await toggle.isChecked();
  if (!record.initial_memory_enabled) { await toggle.click(); await expect(toggle).toBeChecked(); }
  await toggle.click(); await expect(toggle).not.toBeChecked();
  expect((await api('/me/memory/settings')).enabled).toBe(false);
  await toggle.click(); await expect(toggle).toBeChecked(); expect((await api('/me/memory/settings')).enabled).toBe(true);
  let entry = page.locator('.memory-entry').filter({ has: page.getByText(initial.content, { exact: true }) });
  await entry.getByRole('button', { name: 'View source message' }).focus(); await page.keyboard.press('Enter');
  let modal = page.getByRole('dialog', { name: 'Memory source message' }); await expect(modal.locator('.source-passage')).toHaveText(source.content);
  await page.screenshot({ path: `${output}/source-message-1440.png` }); await page.keyboard.press('Escape');
  await expect(entry.getByRole('button', { name: 'View source message' })).toBeFocused();
  await entry.getByRole('button', { name: 'Edit', exact: true }).click();
  modal = page.getByRole('dialog', { name: 'Edit learning memory' });
  const firstEdit = 'Use a short worked example before equations when studying biology.';
  await modal.getByRole('textbox', { name: /^Memory/ }).fill(firstEdit); await modal.getByRole('textbox', { name: /^Scope/ }).fill('biology');
  await modal.getByRole('button', { name: 'Save memory' }).click(); await expect(modal).toHaveCount(0);
  let saved = (await api('/me/memories')).find(item => item.id === memoryId);
  expect(saved.content).toBe(firstEdit); expect(saved.scope).toBe('biology'); expect(saved.version).toBe(initial.version + 1);
  record.edited_version = saved.version; await fit(1440); await page.screenshot({ path: `${output}/saved-memory-1440.png` });
  await page.setViewportSize({ width: 390, height: 844 });
  entry = page.locator('.memory-entry').filter({ has: page.getByText(firstEdit, { exact: true }) });
  await entry.getByRole('button', { name: 'Edit', exact: true }).click(); modal = page.getByRole('dialog', { name: 'Edit learning memory' });
  const draft = 'Use precise terminology, then one brief biology example.';
  await modal.getByRole('textbox', { name: /^Memory/ }).fill(draft);
  // A genuine concurrent saved revision makes this open editor stale.
  const concurrent = await api(`/me/memories/${memoryId}`, 'PATCH', { version: saved.version, content: 'Use one labelled example for biology.', scope: 'biology', expires_at: null });
  await modal.getByRole('button', { name: 'Save memory' }).click();
  await expect(modal.getByRole('alert')).toBeVisible(); await expect(modal.getByRole('textbox', { name: /^Memory/ })).toHaveValue(draft);
  record.concurrent_version = concurrent.version; record.conflict_draft_preserved = true;
  await fit(390); await page.screenshot({ path: `${output}/actual-version-conflict-390.png` });
  await page.keyboard.press('Escape'); await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  entry = page.locator('.memory-entry').filter({ has: page.getByText(concurrent.content, { exact: true }) });
  await entry.getByRole('button', { name: 'Edit', exact: true }).click(); modal = page.getByRole('dialog', { name: 'Edit learning memory' });
  await modal.getByRole('textbox', { name: /^Memory/ }).fill(draft); await modal.getByRole('button', { name: 'Save memory' }).click(); await expect(modal).toHaveCount(0);
  saved = (await api('/me/memories')).find(item => item.id === memoryId); expect(saved.version).toBe(concurrent.version + 1); expect(saved.content).toBe(draft);
  entry = page.locator('.memory-entry').filter({ has: page.getByText(draft, { exact: true }) });
  await entry.getByRole('button', { name: 'Delete', exact: true }).click();
  modal = page.getByRole('dialog', { name: 'Delete this memory?' }); await page.screenshot({ path: `${output}/delete-confirmation-390.png` });
  await modal.getByRole('button', { name: 'Delete memory', exact: true }).click(); await expect(modal).toHaveCount(0);
  expect((await api('/me/memories')).some(item => item.id === memoryId)).toBe(false); await expect(page.getByText(draft, { exact: true })).toHaveCount(0);
  const history = await api(`/sessions/${source.session_id}/messages`); expect(sha(history.items.find(item => item.id === source.message_id).content)).toBe(record.source_message_sha256);
  await toggle.click(); await expect(toggle).not.toBeChecked(); expect((await api('/me/memory/settings')).enabled).toBe(false);
  record.deleted = true; record.original_message_unchanged = true; record.final_memory_enabled = false;
  await page.screenshot({ path: `${output}/deleted-memory-off-390.png` });
  expect(record.answer_posts).toBe(0); expect(record.page_errors).toEqual([]); record.passed = true;
} catch (error) {
  record.failure = safe(error); process.exitCode = 1;
  await page.screenshot({ path: `${output}/failure.png` }).catch(() => {});
  record.dialog_diagnostic = await page.locator('dialog[open]').evaluateAll(nodes => nodes.map(node => ({ label: node.getAttribute('aria-label'), labelled_by: node.getAttribute('aria-labelledby'), text: node.textContent, fields: [...node.querySelectorAll('textarea,input')].map(field => ({ tag: field.tagName, type: field.getAttribute('type'), id: field.id, labels: [...(field.labels || [])].map(label => label.textContent) })) }))).catch(() => []);
}
finally { record.finished_at = new Date().toISOString(); await fs.writeFile(`${output}/verification.json`, JSON.stringify(record, null, 2)); await browser.close(); console.log(JSON.stringify({ output, passed: record.passed, answer_posts: record.answer_posts, failure: record.failure || null })); }
