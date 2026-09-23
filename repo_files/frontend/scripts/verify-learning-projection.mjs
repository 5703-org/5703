import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';

// Reads an already-created dedicated test conversation. Normal source-opening
// and rendering events are persisted; this helper never submits an answer.
const email = process.env.TEST_LEARNER_EMAIL;
const password = process.env.TEST_ACCOUNT_PASSWORD;
const sessionId = process.env.TEST_SESSION_ID;
const answerId = process.env.TEST_HINT_ANSWER_ID;
if (!email || !password || !sessionId || !answerId) throw new Error('Supply a dedicated test account, session and saved hint answer through the environment.');
const runId = new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-');
const output = `../artifacts/reports/frontend/learning-projection/${runId}`;
await fs.mkdir(output, { recursive: true });
const sha = value => createHash('sha256').update(value).digest('hex');
const safeError = error => String(error.stack || error).replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi, 'Bearer [redacted]').replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, '[redacted token]');
const record = { passed: false, started_at: new Date().toISOString(), session_id: sessionId, answer_id: answerId, scope: 'Actual browser rendering and explicit source disclosure on a saved dedicated-test hint. No answer generation, request interception, source substitution, independent reading or learning-quality measurement.', answer_posts: 0, exposure_requests: [], exposure_receipts: [], views: [], page_errors: [] };
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
const context = await browser.newContext({ baseURL: process.env.FRONTEND_URL || 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const observations = [];
page.on('pageerror', error => record.page_errors.push(safeError(error)));
page.on('request', request => {
  const path = new URL(request.url()).pathname;
  if (request.method() === 'POST' && path.endsWith('/messages')) record.answer_posts++;
  if (request.method() === 'POST' && path.endsWith('/exposures')) record.exposure_requests.push({ path, body: request.postDataJSON() });
});
page.on('response', response => {
  if (!new URL(response.url()).pathname.endsWith('/exposures')) return;
  observations.push((async () => {
    const body = await response.json();
    record.exposure_receipts.push({ status: response.status(), id: body.data?.id, kind: body.data?.kind, presentation_id: body.data?.presentation_id, error_code: body.error?.code || null });
  })().catch(error => record.page_errors.push(safeError(error))));
});
async function api(path) {
  const token = await page.evaluate(() => sessionStorage.getItem('cs30.access-token'));
  const response = await page.request.get(`/api/v1${path}`, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.ok(), `${path}: ${response.status()}`).toBe(true);
  return (await response.json()).data;
}
async function bounds(locator, width) {
  const value = await locator.evaluate(node => { const r = node.getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, client_width: node.clientWidth, scroll_width: node.scrollWidth, root_width: document.documentElement.scrollWidth, viewport_height: innerHeight }; });
  expect(value.left).toBeGreaterThanOrEqual(-1); expect(value.right).toBeLessThanOrEqual(width + 1);
  expect(value.scroll_width).toBeLessThanOrEqual(value.client_width + 1); expect(value.root_width).toBeLessThanOrEqual(width + 1);
  return value;
}
try {
  record.browser_version = browser.version();
  record.source_hashes = {};
  for (const file of ['src/Chat.tsx', 'src/ControlledEvidence.tsx', 'src/Markdown.tsx', 'src/SourceSegments.tsx', 'src/Exposure.tsx', 'src/Memory.tsx']) record.source_hashes[`frontend/${file}`] = sha(await fs.readFile(file));
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill(email); await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeVisible();
  await page.goto(`/chat/${sessionId}`);
  const article = page.locator(`[data-answer-id="${answerId}"]`);
  await expect(article).toBeVisible();
  const answer = await api(`/answers/${answerId}`);
  expect(answer.teaching_mode).toBe('hint'); expect(answer.presentation?.id).toBeTruthy();
  expect(answer.evidence).toEqual([]); expect(answer.profile_snapshot).toBeNull(); expect(answer.conversation_snapshot).toBeNull();
  expect(answer.response.short_answer).toBeNull();
  expect(answer.presentation.citation_views.length).toBeGreaterThan(0);
  for (const view of answer.presentation.citation_views) expect(view.source_url).toBeNull();
  record.presentation_id = answer.presentation.id; record.approved_response_sha256 = sha(JSON.stringify(answer.response));
  record.help_level = answer.help_level; record.task_id = answer.task_id;
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
    const trigger = article.getByRole('button', { name: /^Open source \d+/ }).first();
    await trigger.scrollIntoViewIfNeeded(); await trigger.focus(); await page.keyboard.press('Enter');
    const modal = page.getByRole('dialog', { name: 'Sources', exact: true });
    await expect(modal.locator('.source-passage')).toBeVisible();
    await expect(modal.getByRole('link', { name: 'View original source' })).toHaveCount(0);
    const previewText = await modal.locator('.source-passage').textContent();
    const highlighted = await modal.locator('mark').allTextContents();
    expect(highlighted.length).toBeGreaterThan(0);
    const geometry = await bounds(modal, width);
    await page.screenshot({ path: `${output}/approved-preview-${width}.png` });
    for (let i = 0; i < 7; i++) { await page.keyboard.press('Tab'); expect(await page.evaluate(() => document.querySelector('dialog[open]')?.contains(document.activeElement))).toBe(true); }
    await modal.getByRole('button', { name: 'Show complete source', exact: true }).click();
    await expect(modal.getByText('Complete source requested', { exact: true })).toBeVisible();
    const fullText = await modal.locator('.source-passage').textContent();
    const link = modal.getByRole('link', { name: 'View original source' });
    await expect(link).toHaveAttribute('href', /^https:\/\//); await expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    await modal.locator('.source-title').scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${output}/explicit-complete-source-${width}.png` });
    record.views.push({ width, preview_sha256: sha(previewText), full_source_sha256: sha(fullText), preview_characters: Array.from(previewText).length, full_source_characters: Array.from(fullText).length, highlighted_spans: highlighted.length, geometry });
    await page.keyboard.press('Escape'); await expect(modal).toHaveCount(0); await expect(trigger).toBeFocused();
  }
  await page.reload(); await expect(article).toBeVisible();
  const reloaded = await api(`/answers/${answerId}`);
  expect(reloaded.response).toEqual(answer.response); expect(reloaded.presentation).toEqual(answer.presentation);
  const history = await api(`/sessions/${sessionId}/messages`);
  const latest = history.items.filter(item => item.answer).at(-1)?.answer;
  record.latest_answer_id = latest?.id;
  if (latest?.id === answerId) {
    await expect(article.getByRole('button', { name: 'Another hint' })).toBeVisible();
    await expect(article.getByRole('button', { name: 'Show full explanation' })).toBeVisible();
  } else {
    // Only the current answer owns continuation actions. This supplied session
    // already contains the later explicit full explanation from the API smoke.
    await expect(article.getByRole('button', { name: 'Another hint' })).toHaveCount(0);
    await expect(article.getByRole('button', { name: 'Show full explanation' })).toHaveCount(0);
  }
  await article.getByRole('button', { name: /^Open source \d+/ }).first().click();
  const restoredPreview = page.getByRole('dialog', { name: 'Sources', exact: true });
  await expect(restoredPreview.locator('.source-passage')).toBeVisible();
  expect(sha(await restoredPreview.locator('.source-passage').textContent())).toBe(record.views[0].preview_sha256);
  await expect(restoredPreview.getByRole('link', { name: 'View original source' })).toHaveCount(0);
  await page.keyboard.press('Escape');
  await Promise.all(observations);
  expect(record.exposure_receipts.every(item => item.status === 200)).toBe(true);
  expect(record.exposure_requests.some(item => item.body.kind === 'rendered' && item.body.surface === 'answer')).toBe(true);
  const expandedIds = new Set(record.exposure_receipts.filter(item => item.kind === 'full_source_requested').map(item => item.id));
  expect(record.exposure_requests.some(item => item.body.kind === 'rendered' && item.body.surface === 'full_source' && expandedIds.has(item.body.parent_exposure_id))).toBe(true);
  expect(record.answer_posts).toBe(0); expect(record.page_errors).toEqual([]);
  record.passed = true;
} catch (error) { record.failure = safeError(error); process.exitCode = 1; }
finally {
  await Promise.allSettled(observations); record.finished_at = new Date().toISOString();
  await fs.writeFile(`${output}/verification.json`, JSON.stringify(record, null, 2));
  await browser.close(); console.log(JSON.stringify({ output, passed: record.passed, answer_posts: record.answer_posts, failure: record.failure || null }));
}
