import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';

const email = process.env.TEST_LEARNER_EMAIL;
const password = process.env.TEST_ACCOUNT_PASSWORD;
if (!email?.startsWith('ui-keyboard-') || !password) throw new Error('Supply a dedicated ui-keyboard- test account through the environment.');
const runId = new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-');
const output = `../artifacts/reports/frontend/keyboard-suggestion/${runId}`;
await fs.mkdir(output, { recursive: true });
const record = {
  passed: false, started_at: new Date().toISOString(),
  scope: 'Actual desktop browser key events, persisted mock-model suggestion, real API rejection and stage rendering; real OpenStax/E5 retrieval. No request interception, database answer insertion, live answer or physical-device claim.',
  expected_release_id: '4f11bd70-a486-4d16-b216-78cfe499530a',
  posts: [], stage_observations: [], page_errors: [],
};
const sha = value => createHash('sha256').update(value).digest('hex');
const durableRows = rows => rows.map(item => { const copy = structuredClone(item); if (copy.answer) delete copy.answer.can_regenerate; return copy; });
const diagnostic = error => String(error.stack || error)
  .replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi, 'Bearer [redacted]')
  .replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, '[redacted token]');
const stages = { queued: 'Waiting to begin…', preparing: 'Understanding your question…', retrieving: 'Looking through the sources…', generating: 'Preparing an explanation…', saving: 'Saving your response…', retry_wait: 'Waiting to try again…', processing: 'Working on your question…' };
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
const context = await browser.newContext({ baseURL: process.env.FRONTEND_URL || 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const observers = [];
let archived = false;
page.on('pageerror', error => record.page_errors.push(diagnostic(error)));
page.on('request', request => {
  if (request.method() === 'POST' && new URL(request.url()).pathname.endsWith('/messages')) {
    record.posts.push({ path: new URL(request.url()).pathname, body: request.postDataJSON() });
  }
});
page.on('response', response => {
  if (response.request().method() !== 'GET' || !new URL(response.url()).pathname.includes('/jobs/')) return;
  observers.push((async () => {
    const body = (await response.json()).data;
    if (!body || !['queued', 'running', 'retry_wait'].includes(body.state)) return;
    const observation = { job_id: body.id, state: body.state, stage: body.stage, response_observed_at: new Date().toISOString(), expected_text: stages[body.stage] };
    await page.waitForTimeout(40);
    observation.rendered_text = await page.locator('.generation-status').textContent({ timeout: 2000 }).catch(() => null);
    observation.matches = !!observation.expected_text && observation.rendered_text?.includes(observation.expected_text) === true;
    record.stage_observations.push(observation);
  })().catch(error => record.page_errors.push(diagnostic(error))));
});
async function save() { await fs.writeFile(`${output}/verification.json`, JSON.stringify(record, null, 2)); }
async function api(path, method = 'GET', data) {
  const token = await page.evaluate(() => sessionStorage.getItem('cs30.access-token'));
  const response = await page.request.fetch(`/api/v1${path}`, { method, data, headers: { Authorization: `Bearer ${token}` } });
  const body = await response.json();
  expect(response.ok(), `${method} ${path}: ${JSON.stringify(body.error || {})}`).toBe(true);
  return body.data;
}
async function waitAnswer(count) {
  await expect(page.locator('[data-answer-id]')).toHaveCount(count, { timeout: 120000 });
  await expect(page.getByRole('button', { name: 'Stop generation', exact: true })).toHaveCount(0, { timeout: 15000 });
  const id = await page.locator('[data-answer-id]').last().getAttribute('data-answer-id');
  const answer = await api(`/answers/${id}`);
  expect(answer.model_mode).toBe('mock');
  return answer;
}
try {
  record.browser_version = browser.version();
  record.implementation_sha256 = {};
  for (const path of ['frontend/src/Chat.tsx', 'generation/adapters.py', 'backend/app/modules/answering/service.py']) record.implementation_sha256[path] = sha(await fs.readFile(`../${path}`));
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const composer = page.getByRole('textbox', { name: 'Message Learning Assistant' });
  await expect(composer).toBeVisible();
  expect((await api('/capabilities')).model_mode).toBe('mock');
  record.account_id = (await api('/users/me')).id;
  const profile = await api('/profiles/me');
  record.saved_profile = await api('/profiles/me', 'PUT', { ...profile, level: 'intermediate', style: 'socratic' });
  const session = await api('/sessions', 'POST', { title: `Keyboard and suggestion verification ${runId}` });
  record.session_id = session.id;
  await save();
  await page.goto(`/chat/${session.id}`);
  await expect(composer).toBeVisible();
  await expect(page.getByText('Demo (mock model)', { exact: true }).first()).toBeVisible();
  await composer.fill('What is');
  await composer.press('End');
  await composer.press('Shift+Enter');
  await expect(composer).toHaveValue('What is\n');
  await page.waitForTimeout(150);
  expect(record.posts).toHaveLength(0);
  record.shift_enter = { actual_value: await composer.inputValue(), posts: record.posts.length };
  await composer.pressSequentially('photosynthesis?');
  const firstReceipt = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/sessions/${session.id}/messages`));
  await composer.press('Enter');
  const firstResponse = await firstReceipt;
  expect(firstResponse.status()).toBe(202);
  record.first_receipt = (await firstResponse.json()).data;
  const first = await waitAnswer(1);
  expect(record.posts).toHaveLength(1);
  expect(record.posts[0].body.content).toBe('What is\nphotosynthesis?');
  expect(first.response.response_type).toBe('answer');
  expect(first.profile_snapshot.profile.style).toBe('socratic');
  expect(first.response.follow_up_questions).toEqual(['Which part would you like to explore further?']);
  expect(first.response.citations.length).toBeGreaterThan(0);
  const publication = JSON.parse(await fs.readFile('../evidence/openstax/v5/publication.json'));
  expect(publication.release_id).toBe(record.expected_release_id);
  const chunks = new Set(publication.release.manifest.chunk_ids);
  for (const evidence of first.evidence) {
    expect(chunks.has(evidence.chunk_id)).toBe(true);
    expect(sha(evidence.text)).toBe(evidence.text_hash);
  }
  record.first_answer = first;
  await page.screenshot({ path: `${output}/actual-suggestion.png` });
  const suggestion = first.response.follow_up_questions[0];
  const secondReceipt = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/sessions/${session.id}/messages`));
  await page.locator('.followups').getByRole('button', { name: suggestion, exact: true }).click();
  expect((await secondReceipt).status()).toBe(202);
  record.followup_answer = await waitAnswer(2);
  expect(record.posts).toHaveLength(2);
  expect(record.posts[1].body.content).toBe(suggestion);
  const before = await api(`/sessions/${session.id}/messages?limit=100`);
  expect(before.items).toHaveLength(4);
  expect(before.items.filter(item => item.role === 'user').map(item => item.content)).toEqual(['What is\nphotosynthesis?', suggestion]);
  record.history_before_rejection = before;
  // Archive only this owned verification session via the real endpoint while
  // its already-loaded browser stays stale. Submission must fail, retain the
  // draft, and publish no optimistic fake response. No network mocking is used.
  await api(`/sessions/${session.id}/archive`, 'POST', {});
  archived = true;
  const failureDraft = 'This unsent draft must survive the actual archived-session rejection.';
  record.failure_drafts = [];
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await composer.fill(failureDraft);
    const rejectionPromise = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/sessions/${session.id}/messages`));
    await composer.press('Enter');
    const rejection = await rejectionPromise;
    expect(rejection.status()).toBe(409);
    const rejectionBody = await rejection.json();
    expect(rejectionBody.error.code).toBe('CONFLICT');
    const alert = page.getByRole('alert');
    await expect(alert).toContainText(rejectionBody.error.message);
    await expect(alert).toBeInViewport({ ratio: 1 });
    const alertBox = await alert.boundingBox();
    const transcriptBox = await page.locator('.transcript').boundingBox();
    expect(alertBox.y).toBeGreaterThanOrEqual(transcriptBox.y - 1);
    expect(alertBox.y + alertBox.height).toBeLessThanOrEqual(transcriptBox.y + transcriptBox.height + 1);
    await expect(composer).toHaveValue(failureDraft);
    await expect(page.locator('[data-answer-id]')).toHaveCount(2);
    const archivedHistory = (await api(`/sessions/${session.id}/messages?limit=100`)).items;
    expect(durableRows(archivedHistory)).toEqual(durableRows(before.items));
    expect(archivedHistory.filter(item => item.answer).every(item => item.answer.can_regenerate === false)).toBe(true);
    record.failure_drafts.push({ width, http_status: rejection.status(), error: rejectionBody.error, retained_draft: await composer.inputValue(), full_alert_visible_without_manual_scroll: true, alert_box: alertBox, transcript_box: transcriptBox, saved_rows_unchanged: true, history_comparison_scope: 'All message/answer fields except dynamic can_regenerate; archiving correctly disables regeneration. Exact complete rows are compared again after restore.', actual_failure_kind: 'Submission rejected because this owned session was archived; not a provider execution fault.' });
    await page.screenshot({ path: `${output}/actual-rejection-draft-${width}.png` });
  }
  expect(record.posts).toHaveLength(4);
  await api(`/sessions/${session.id}/restore`, 'POST', {});
  archived = false;
  await page.reload();
  await expect(composer).toHaveValue(failureDraft);
  await expect(page.locator('[data-answer-id]')).toHaveCount(2);
  expect((await api(`/sessions/${session.id}/messages?limit=100`)).items).toEqual(before.items);
  record.reload_draft_preserved = true;
  await Promise.all(observers);
  expect(record.stage_observations.some(row => row.matches && row.stage !== 'queued')).toBe(true);
  record.matched_real_polled_stages = [...new Set(record.stage_observations.filter(row => row.matches).map(row => row.stage))];
  expect(record.page_errors).toEqual([]);
  record.passed = true;
} catch (error) {
  record.error = diagnostic(error);
  await page.screenshot({ path: `${output}/failure.png` }).catch(() => {});
  process.exitCode = 1;
} finally {
  if (archived && record.session_id) {
    try { await api(`/sessions/${record.session_id}/restore`, 'POST', {}); record.cleanup = 'Owned session restored'; }
    catch (error) { record.cleanup_error = diagnostic(error); record.passed = false; process.exitCode = 1; }
  }
  await Promise.all(observers);
  if (record.page_errors.length > 0) {
    record.passed = false;
    process.exitCode = 1;
  }
  record.completed_at = new Date().toISOString();
  await save();
  await browser.close();
  console.log(JSON.stringify({ passed: record.passed, output, session_id: record.session_id, posts: record.posts.length, error: record.error }));
}
