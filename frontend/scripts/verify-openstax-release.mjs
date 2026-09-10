import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import crypto from 'node:crypto';

const baseURL = process.env.FRONTEND_URL || 'http://127.0.0.1:5173';
const expectedRelease = '39483e7f-efbe-42e7-855e-469fd924383e';
const publicationBytes = await fs.readFile('../evidence/openstax/publication.json');
const publication = JSON.parse(publicationBytes);
expect(publication.release_id).toBe(expectedRelease);
const publishedChunks = new Set(publication.release.manifest.chunk_ids);
const publishedRuns = new Set(publication.release.manifest.processing_run_ids);
const runId = new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-');
const output = `../artifacts/reports/frontend/openstax/${runId}`;
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
const context = await browser.newContext({ baseURL, viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const diagnostic = error => String(error.stack || error).replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi, 'Bearer [redacted]');
const record = { executed_at: new Date().toISOString(), base_url: baseURL, expected_release_id: expectedRelease, browser: browser.version(), evidence_class: 'Real official OpenStax PDFs, real local E5/pgvector retrieval, real browser/API/worker/PostgreSQL; deterministic mock answering. No live model semantic or human teaching-quality claim.', passed: false, checks: {}, answers: [], responsive: [], page_errors: [] };
record.publication_evidence_sha256 = crypto.createHash('sha256').update(publicationBytes).digest('hex');
record.local_implementation_hashes = {};
for (const file of ['generation/adapters.py', 'conversation/query.py', 'frontend/src/Chat.tsx']) record.local_implementation_hashes[file] = crypto.createHash('sha256').update(await fs.readFile(`../${file}`)).digest('hex');
page.on('pageerror', error => record.page_errors.push(error.message));

async function api(path) {
  const token = await page.evaluate(() => sessionStorage.getItem('cs30.access-token'));
  const response = await page.request.get(`/api/v1${path}`, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.ok(), `${path}: ${response.status()}`).toBe(true);
  return (await response.json()).data;
}
async function login() {
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('student2@example.com');
  await page.getByLabel('Password', { exact: true }).fill('Passw0rd!');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeVisible();
  await expect(page.getByText('Demo (mock model)', { exact: true }).first()).toBeVisible();
}
async function send(question) {
  const count = await page.locator('[data-answer-id]').count();
  await page.getByRole('textbox', { name: 'Message Learning Assistant' }).fill(question);
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  await expect(page.locator('[data-answer-id]')).toHaveCount(count + 1, { timeout: 60000 });
  await expect(page.getByRole('button', { name: 'Stop generation', exact: true })).toHaveCount(0);
  const node = page.locator('[data-answer-id]').last();
  const answer = await api(`/answers/${await node.getAttribute('data-answer-id')}`);
  expect(answer.mode).toBe('interactive_chat');
  expect(answer.response_schema).toBe('chat_response_v1');
  expect(answer.model_mode).toBe('mock');
  if (answer.response.response_type === 'answer') expect(answer.response.answer_text).not.toMatch(/\?\s*\[ev_\d+\]\s*$/);
  for (const source of answer.evidence) {
    expect(publishedChunks.has(source.chunk_id), 'Actual answer evidence belongs to the published real corpus').toBe(true);
    expect(publishedRuns.has(source.processing_id)).toBe(true);
  }
  record.answers.push({ question, answer });
  return { node, answer };
}
async function sourceView(node, answer, width) {
  const citedId = answer.response.citations[0];
  const source = answer.evidence.find(item => item.evidence_id === citedId);
  expect(source).toBeTruthy();
  expect(crypto.createHash('sha256').update(source.text).digest('hex')).toBe(source.text_hash);
  expect(new URL(source.source_url).hostname).toMatch(/(^|\.)openstax\.org$/);
  expect(source.license).toContain('https://creativecommons.org/licenses/by-nc-sa/4.0/');
  await node.getByRole('button', { name: /^Open source \d+/ }).first().click();
  const modal = page.getByRole('dialog', { name: 'Sources' });
  await expect(modal).toBeVisible();
  await expect(page.locator('.source-passage')).toHaveText(source.text);
  await expect(page.locator('.source-title')).toHaveText(source.source_title);
  await expect(page.locator('.source-attribution')).toContainText('OpenStax / Rice University · Access for free at openstax.org');
  const link = page.getByRole('link', { name: 'View original source' });
  await expect(link).toHaveAttribute('href', source.source_url);
  await expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  await expect(page.locator('.source-locator')).toContainText('PDF physical pages');
  await modal.locator('.data-details summary').click();
  await expect(modal.locator('.data-details pre')).toBeVisible();
  await expect(modal.locator('.data-details pre')).toContainText(source.license);
  await modal.locator('.data-details summary').click();
  await page.locator('.source-title').scrollIntoViewIfNeeded();
  const bounds = await modal.evaluate(element => { const r = element.getBoundingClientRect(); return { left: r.left, right: r.right, clientWidth: element.clientWidth, scrollWidth: element.scrollWidth }; });
  expect(bounds.left).toBeGreaterThanOrEqual(0);
  expect(bounds.right).toBeLessThanOrEqual(width + 1);
  expect(bounds.scrollWidth).toBeLessThanOrEqual(bounds.clientWidth + 1);
  await page.screenshot({ path: `${output}/source-${width}.png` });
  const locator = await page.locator('.source-locator').innerText();
  await page.getByRole('button', { name: 'Close sources' }).click();
  return { width, source, locator, bounds };
}

try {
  await login();
  const first = await send('What is photosynthesis?');
  expect(first.answer.response.response_type).toBe('answer');
  record.session_id = new URL(page.url()).pathname.split('/')[2];
  record.source_views = [await sourceView(first.node, first.answer, 1440)];
  const second = await send('Why does it need light?');
  expect(second.answer.response.response_type).toBe('answer');
  expect(second.answer.conversation_snapshot.messages.length).toBeGreaterThanOrEqual(2);
  await page.getByRole('checkbox').uncheck();
  const third = await send('Make it simpler');
  expect(third.answer.response.response_type).toBe('answer');
  expect(third.answer.profile_snapshot.use_profile).toBe(false);
  const fourth = await send('Give an example');
  expect(fourth.answer.response.response_type).toBe('answer');
  const topic = await send('How does glycolysis produce ATP from glucose?');
  expect(topic.answer.response.response_type).toBe('answer');
  expect(topic.answer.response.answer_text.toLowerCase()).toContain('glycolysis');
  expect(topic.answer.response.answer_text.toLowerCase()).not.toContain('photosynthesis');
  await topic.node.getByRole('button', { name: 'Feedback', exact: true }).click();
  await page.getByRole('button', { name: 'Helpful', exact: true }).click();
  await page.getByLabel('Comment', { exact: false }).fill('Browser verification: the original source is available for checking this extract.');
  await page.getByRole('button', { name: 'Save feedback', exact: true }).click();
  await expect(page.getByText('Feedback saved for this response.')).toBeVisible();
  await page.getByRole('button', { name: 'Close response feedback' }).click();
  record.feedback_before_regeneration = await api(`/answers/${topic.answer.id}/feedback`);
  await topic.node.getByRole('button', { name: 'Regenerate', exact: true }).click();
  await expect(page.locator('[data-answer-id]').last()).not.toHaveAttribute('data-answer-id', topic.answer.id, { timeout: 60000 });
  await expect(page.locator('[data-answer-id]')).toHaveCount(5);
  record.regenerated_answer = await api(`/answers/${await page.locator('[data-answer-id]').last().getAttribute('data-answer-id')}`);
  expect(record.regenerated_answer.response.response_type).toBe('answer');
  record.feedback_after_regeneration = await api(`/answers/${topic.answer.id}/feedback`);
  expect(record.feedback_after_regeneration).toEqual(record.feedback_before_regeneration);
  const original = await api(`/answers/${topic.answer.id}`);
  expect(original.response).toEqual(topic.answer.response);
  expect(original.evidence).toEqual(topic.answer.evidence);
  record.checks.immutable_original_answer_and_feedback = true;
  const input = page.getByRole('textbox', { name: 'Message Learning Assistant' });
  const draft = 'This unsent draft should survive every responsive width. ' + 'longword'.repeat(35);
  await input.fill(draft);
  let duplicatePosts = 0;
  const watcher = request => { if (request.method() === 'POST' && /\/messages$/.test(request.url())) duplicatePosts++; };
  page.on('request', watcher);
  for (const width of [1440, 768, 390, 320, 639, 640, 641, 1023, 1024, 1025, 1920]) {
    await page.setViewportSize({ width, height: width < 768 ? 844 : 1000 });
    await expect(input).toHaveValue(draft);
    const bounds = await page.evaluate(() => ({ width: innerWidth, htmlWidth: document.documentElement.scrollWidth, bodyWidth: document.body.scrollWidth, composer: document.querySelector('.composer').getBoundingClientRect().toJSON() }));
    expect(bounds.htmlWidth).toBeLessThanOrEqual(width + 1);
    expect(bounds.bodyWidth).toBeLessThanOrEqual(width + 1);
    expect(bounds.composer.left).toBeGreaterThanOrEqual(-1);
    expect(bounds.composer.right).toBeLessThanOrEqual(width + 1);
    await expect(page.getByRole('button', { name: 'Send message', exact: true })).toBeInViewport();
    record.responsive.push(bounds);
    if ([1440, 768, 390, 320, 1920].includes(width)) await page.screenshot({ path: `${output}/conversation-${width}.png` });
  }
  page.off('request', watcher);
  expect(duplicatePosts).toBe(0);
  record.checks.resize_duplicate_posts = duplicatePosts;
  await page.setViewportSize({ width: 390, height: 844 });
  record.source_views.push(await sourceView(page.locator('[data-answer-id]').first(), first.answer, 390));
  await page.getByRole('button', { name: 'Toggle sidebar' }).click();
  await page.getByRole('button', { name: 'Close navigation' }).click();
  await expect(input).toHaveValue(draft);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await input.fill('');
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await login();
  await page.goto(`/chat/${record.session_id}`);
  await expect(page.locator('[data-answer-id]')).toHaveCount(5);
  await expect(page.locator('[data-answer-id]').last()).toHaveAttribute('data-answer-id', record.regenerated_answer.id);
  record.history_after_relogin = await api(`/sessions/${record.session_id}/messages?limit=100`);
  expect(record.history_after_relogin.items).toHaveLength(10);
  record.checks.persisted_after_relogin = true;
  const unrelated = await send('Who won the 2026 Formula One world championship?');
  expect(unrelated.answer.response.response_type).toBe('refusal');
  expect(unrelated.answer.response.citations).toEqual([]);
  await expect(unrelated.node.getByText('Evidence limitation', { exact: true })).toBeVisible();
  await expect(unrelated.node.locator('.prose')).toContainText('mock answerer');
  await page.screenshot({ path: `${output}/mock-limitation-1440.png` });
  await page.locator('.new-chat').click();
  await expect(page).not.toHaveURL(new RegExp(record.session_id));
  await expect(page.locator('[data-answer-id]')).toHaveCount(0);
  const ambiguity = await send('Why does it do that?');
  record.ambiguity_session_id = new URL(page.url()).pathname.split('/')[2];
  expect(ambiguity.answer.response.response_type).toBe('clarification');
  const clarified = await send('I mean photosynthesis.');
  expect(clarified.answer.response.response_type).toBe('answer');
  const sources = await send('What are your sources?');
  expect(sources.answer.response.response_type).toBe('answer');
  expect(sources.answer.response.citations.length).toBeGreaterThan(0);
  const greeting = await send('Hello');
  expect(greeting.answer.response.response_type).toBe('social');
  expect(greeting.answer.response.citations).toEqual([]);
  record.checks.clarification_completion_source_request_social = true;
  expect(record.page_errors).toEqual([]);
  record.checks.actual_browser_zoom = 'Not repeated in this run; earlier native browser zoom evidence remains separate.';
  record.checks.physical_mobile_keyboard_and_native_ime = 'UNVERIFIED: physical device and human/native IME interaction unavailable.';
  record.passed = true;
} catch (error) {
  record.error = diagnostic(error);
  await page.screenshot({ path: `${output}/failure.png` }).catch(() => {});
  throw new Error(record.error);
} finally {
  await fs.writeFile(`${output}/verification.json`, JSON.stringify(record, null, 2));
  await browser.close();
  console.log(JSON.stringify({ passed: record.passed, session_id: record.session_id, output, error: record.error }));
}
