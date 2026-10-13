import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';

const email = process.env.TEST_LEARNER_EMAIL, password = process.env.TEST_ACCOUNT_PASSWORD;
if (!email || !password) throw new Error('Use the dedicated test account.');
const output = `../artifacts/reports/frontend/teaching-controls/${new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-')}`;
await fs.mkdir(output, { recursive: true });
const sha = value => createHash('sha256').update(value).digest('hex');
const safe = error => String(error.stack || error).replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi, 'Bearer [redacted]').replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, '[redacted token]');
const record = { passed: false, started_at: new Date().toISOString(), scope: 'One prespecified real browser hint → another hint → explicit full explanation journey; no resampling or response interception.', requests: [], exposures: [], page_errors: [] };
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
const context = await browser.newContext({ baseURL: process.env.FRONTEND_URL || 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1000 } });
const page = await context.newPage(); const observations = [];
page.on('pageerror', error => record.page_errors.push(safe(error)));
page.on('response', response => {
  if (response.request().method() !== 'POST' || !new URL(response.url()).pathname.endsWith('/exposures')) return;
  observations.push((async () => { const data = await response.json(); record.exposures.push({ input: response.request().postDataJSON(), status: response.status(), id: data.data?.id, kind: data.data?.kind, error_code: data.error?.code || null }); })());
});
async function api(path) {
  const token = await page.evaluate(() => sessionStorage.getItem('cs30.access-token'));
  const response = await page.request.get(`/api/v1${path}`, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.ok()).toBe(true); return (await response.json()).data;
}
async function submit(label, action) {
  const pending = page.waitForResponse(response => response.request().method() === 'POST' && /\/sessions\/[^/]+\/messages$/.test(new URL(response.url()).pathname));
  await action(); const response = await pending; const envelope = await response.json();
  const row = { label, status: response.status(), input: response.request().postDataJSON(), receipt: envelope.data || null, error_code: envelope.error?.code || null };
  record.requests.push(row); expect(response.status()).toBe(202);
  const deadline = Date.now() + 240000;
  let job;
  do { job = await api(`/jobs/${row.receipt.job_id}`); if (['succeeded', 'failed', 'cancelled'].includes(job.state)) break; await page.waitForTimeout(700); } while (Date.now() < deadline);
  row.job = job; console.log(JSON.stringify({ label, request_id: row.receipt.request_id, state: job.state, error_code: job.error?.code || null }));
  expect(job.state, JSON.stringify(job.error)).toBe('succeeded');
  const answer = await api(`/answers/${job.answer_id}`);
  row.answer = { id: answer.id, response_sha256: sha(JSON.stringify(answer.response)), response_type: answer.response.response_type, teaching_mode: answer.teaching_mode, task_id: answer.task_id, help_level: answer.help_level, presentation_id: answer.presentation?.id, citations: answer.response.citations, memory_applied: !!answer.profile_snapshot?.memory };
  const article = page.locator(`[data-answer-id="${answer.id}"]`); await expect(article).toBeVisible({ timeout: 15000 }); await article.scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${output}/${label}-${page.viewportSize().width}.png` });
  return { answer, article };
}
try {
  record.browser_version = browser.version(); record.chat_source_sha256 = sha(await fs.readFile('src/Chat.tsx'));
  await page.goto('/login'); await page.getByLabel('Email', { exact: true }).fill(email); await page.getByLabel('Password', { exact: true }).fill(password); await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeVisible();
  await page.getByRole('button', { name: 'New chat', exact: true }).click();
  await page.getByLabel('Teaching style').selectOption('hint');
  const profile = page.locator('.profile-toggle input'); if (await profile.isChecked()) await profile.click();
  await page.getByRole('textbox', { name: 'Message Learning Assistant' }).fill('Give only a first hint: why does photosynthesis need light?');
  const first = await submit('first-hint', () => page.getByRole('button', { name: 'Send message', exact: true }).click());
  expect(first.answer.teaching_mode).toBe('hint'); expect(first.answer.help_level).toBe(1); expect(first.answer.response.short_answer).toBeNull();
  record.session_id = new URL(page.url()).pathname.split('/').at(-1);
  await page.setViewportSize({ width: 390, height: 844 });
  const next = await submit('another-hint', () => first.article.getByRole('button', { name: 'Another hint', exact: true }).click());
  expect(next.answer.task_id).toBe(first.answer.task_id); expect(next.answer.teaching_mode).toBe('hint'); expect(next.answer.help_level).toBe(2);
  expect(record.requests[1].input.task_action).toBe('more_hint'); expect(record.requests[1].input.task_id).toBe(first.answer.task_id);
  const full = await submit('full-explanation', () => next.article.getByRole('button', { name: 'Show full explanation', exact: true }).click());
  expect(full.answer.task_id).toBe(first.answer.task_id); expect(full.answer.teaching_mode).toBe('direct'); expect(record.requests[2].input.task_action).toBe('full_explanation');
  await page.getByRole('button', { name: 'Start a new problem', exact: true }).click();
  await expect(page.getByText('Next message starts a new problem.', { exact: true })).toBeVisible(); await expect(page.getByLabel('Teaching style')).toHaveValue('direct');
  await page.screenshot({ path: `${output}/new-problem-ready-390.png` });
  record.new_problem_resets_to_direct = true;
  await page.reload(); await expect(page.locator(`[data-answer-id="${full.answer.id}"]`)).toBeVisible();
  const tasks = await api(`/sessions/${record.session_id}/learning-tasks`); record.persisted_tasks = tasks.map(task => ({ id: task.id, teaching_mode: task.teaching_mode, help_level: task.help_level, state: task.state, version: task.version }));
  await page.waitForTimeout(500); await Promise.all(observations);
  for (const row of record.requests) expect(record.exposures.some(exposure => exposure.status === 200 && exposure.kind === 'rendered' && exposure.input.presentation_id === row.answer.presentation_id)).toBe(true);
  expect(record.page_errors).toEqual([]); record.passed = true;
} catch (error) { record.failure = safe(error); process.exitCode = 1; await page.screenshot({ path: `${output}/failure.png` }).catch(() => {}); }
finally { await Promise.allSettled(observations); record.finished_at = new Date().toISOString(); await fs.writeFile(`${output}/verification.json`, JSON.stringify(record, null, 2)); await browser.close(); console.log(JSON.stringify({ output, passed: record.passed, requests: record.requests.length, failure: record.failure || null })); }
