import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import { createHash, randomUUID } from 'node:crypto';

const runId = new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-');
const output = `../artifacts/reports/frontend/history-pagination/${runId}`;
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: 'msedge' });
const context = await browser.newContext({ baseURL: 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const record = { passed: false, executed_at: new Date().toISOString(), fixture_kind: 'UI pagination fixture created through actual API social turns; not corpus input or answer-quality evidence', scope: 'Shipped automatic forward-cursor history pagination at its default 100-row request size, actual saved rows and reading-position preservation. No Load older control is implemented or claimed.', seed_turns: [], browser_pages: [], page_errors: [] };
const diagnostic = error => String(error.stack || error).replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi, 'Bearer [redacted]');
const hash = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const durableRows = rows => rows.map(item => { const copy = structuredClone(item); if (copy.answer) delete copy.answer.can_regenerate; return copy; });
page.on('pageerror', error => record.page_errors.push(diagnostic(error)));
page.on('response', async response => {
  const url = new URL(response.url());
  if (response.request().method() !== 'GET' || !record.session_id || !url.pathname.endsWith(`/sessions/${record.session_id}/messages`)) return;
  try {
    const body = (await response.json()).data;
    record.browser_pages.push({ url: url.pathname + url.search, http_status: response.status(), requested_limit: Number(url.searchParams.get('limit')), after_sequence: Number(url.searchParams.get('after_sequence')), next_after_sequence: body.next_after_sequence, row_ids: body.items.map(item => item.id), sequences: body.items.map(item => item.sequence), rows_sha256: hash(body.items) });
  } catch (error) { record.page_errors.push(diagnostic(error)); }
});
async function save() { await fs.writeFile(`${output}/verification.json`, JSON.stringify(record, null, 2)); }
async function api(path, method = 'GET', data, key) {
  const token = await page.evaluate(() => sessionStorage.getItem('cs30.access-token'));
  const headers = { Authorization: `Bearer ${token}` };
  if (key) headers['Idempotency-Key'] = key;
  const response = await page.request.fetch(`/api/v1${path}`, { method, data, headers, timeout: 120000 });
  const body = await response.json();
  expect(response.ok(), JSON.stringify(body.error || response.status())).toBe(true);
  return body.data;
}
async function complete(receipt) {
  let job;
  await expect.poll(async () => { job = await api(`/jobs/${receipt.job_id}`); return job.state; }, { timeout: 120000, intervals: [100, 250, 500] }).toBe('succeeded');
  return job;
}
async function allHistory() {
  const items = []; let after = 0;
  while (true) {
    const result = await api(`/sessions/${record.session_id}/messages?after_sequence=${after}&limit=100`);
    items.push(...result.items);
    if (result.next_after_sequence === null) return items;
    expect(result.next_after_sequence).toBeGreaterThan(after);
    after = result.next_after_sequence;
  }
}
async function renderedIds() { return await page.locator('.messages article').evaluateAll(nodes => nodes.map(node => node.getAttribute('data-message-id'))); }
async function anchor() {
  return await page.locator('.transcript').evaluate(node => {
    const bounds = node.getBoundingClientRect();
    const row = [...node.querySelectorAll('[data-message-id]')].find(item => { const r = item.getBoundingClientRect(); return r.bottom > bounds.top && r.top < bounds.bottom; });
    return { id: row?.getAttribute('data-message-id'), relative_top: row?.getBoundingClientRect().top - bounds.top, scroll_top: node.scrollTop, scroll_height: node.scrollHeight, client_height: node.clientHeight };
  });
}
try {
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('student2@example.com');
  await page.getByLabel('Password', { exact: true }).fill('Passw0rd!');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeVisible();
  record.capabilities_before = await api('/capabilities');
  expect(record.capabilities_before.model_mode).toBe('mock');
  const session = await api('/sessions', 'POST', { title: `UI pagination fixture ${runId}` });
  record.session_id = session.id;
  await save();
  for (let index = 0; index < 51; index++) {
    const receipt = await api(`/sessions/${session.id}/messages`, 'POST', { content: 'Hello', use_profile: false }, randomUUID());
    const job = await complete(receipt);
    record.seed_turns.push({ index: index + 1, receipt, job_state: job.state, answer_id: job.answer_id });
    await save();
    if ((index + 1) % 10 === 0) console.log(JSON.stringify({ stage: 'actual_social_turns', completed: index + 1, output }));
  }
  const before = await allHistory();
  expect(before).toHaveLength(102);
  expect(before.filter(item => item.role === 'assistant').every(item => item.answer?.model_mode === 'mock' && item.answer.response.response_type === 'social' && item.answer.evidence.length === 0)).toBe(true);
  record.history_before_sha256 = hash(before);
  record.history_before = before;
  await page.goto(`/chat/${session.id}`);
  await expect(page.locator('.messages article')).toHaveCount(102);
  expect(await renderedIds()).toEqual(before.map(item => item.id));
  for (const item of before) await expect(page.locator(`[data-message-id="${item.id}"]`)).toContainText(item.content);
  record.initial_browser_pages = [...record.browser_pages];
  expect(record.initial_browser_pages.some(item => item.requested_limit === 100 && item.after_sequence === 0 && item.row_ids.length === 100 && item.next_after_sequence === 100)).toBe(true);
  expect(record.initial_browser_pages.some(item => item.requested_limit === 100 && item.after_sequence === 100 && item.row_ids.length === 2 && item.next_after_sequence === null)).toBe(true);
  const composer = page.getByRole('textbox', { name: 'Message Learning Assistant' });
  await composer.fill('Hello');
  const submitted = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/sessions/${session.id}/messages`));
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  record.ui_receipt = (await (await submitted).json()).data;
  await page.locator('.transcript').evaluate(node => { node.scrollTop = 200; node.dispatchEvent(new Event('scroll')); });
  await composer.fill('Unsent pagination verification draft');
  record.anchor_before_completion = await anchor();
  await expect(page.locator('.messages article')).toHaveCount(104, { timeout: 120000 });
  await expect(page.getByRole('button', { name: 'Send message', exact: true })).toBeVisible();
  record.anchor_after_completion = await anchor();
  expect(record.anchor_after_completion.id).toBe(record.anchor_before_completion.id);
  expect(Math.abs(record.anchor_after_completion.relative_top - record.anchor_before_completion.relative_top)).toBeLessThanOrEqual(2);
  await expect(composer).toHaveValue('Unsent pagination verification draft');
  const after = await allHistory();
  expect(after).toHaveLength(104);
  expect(durableRows(after.slice(0, 102))).toEqual(durableRows(before));
  expect(await renderedIds()).toEqual(after.map(item => item.id));
  record.history_after_sha256 = hash(after);
  record.saved_rows_unchanged = true;
  record.history_comparison_scope = 'All prior message and answer fields unchanged except dynamic can_regenerate eligibility, which correctly moves to the new latest answer.';
  record.responsive = [];
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await expect(composer).toHaveValue('Unsent pagination verification draft');
    expect(await renderedIds()).toEqual(after.map(item => item.id));
    const geometry = await page.evaluate(() => ({ width: innerWidth, html: document.documentElement.scrollWidth, body: document.body.scrollWidth }));
    expect(geometry.html).toBeLessThanOrEqual(width + 1);
    expect(geometry.body).toBeLessThanOrEqual(width + 1);
    record.responsive.push(geometry);
    await page.screenshot({ path: `${output}/pagination-${width}.png` });
  }
  await page.getByRole('button', { name: 'Jump to latest', exact: true }).click();
  expect(await page.locator('.transcript').evaluate(node => node.scrollHeight - node.scrollTop - node.clientHeight)).toBeLessThanOrEqual(2);
  record.capabilities_after = await api('/capabilities');
  expect(record.capabilities_after.model_mode).toBe('mock');
  expect(record.page_errors).toEqual([]);
  record.passed = true;
} catch (error) {
  record.error = diagnostic(error);
  await page.screenshot({ path: `${output}/failure.png` }).catch(() => {});
  process.exitCode = 1;
} finally {
  await save();
  await browser.close();
  console.log(JSON.stringify({ passed: record.passed, output, session_id: record.session_id, completed_seed_turns: record.seed_turns.length, error: record.error }));
}
