import { test, expect } from 'E:/5703/learning-assistant/frontend/node_modules/@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';

const UI = 'http://127.0.0.1:15199';
const API = 'http://127.0.0.1:18029';
const COMPLETE = 'Light supplies energy to convert carbon dioxide and water into sugars.';
const PROTECTED = 'Oxygen is released.';
const DRAFT = 'My unsent follow-up remains local after the partial source check.';
test.use({ baseURL: UI, trace: 'off', screenshot: 'off' });

test('real mock worker source combination publishes, then honest partial preserves answer and draft through reload', async ({ page }, testInfo) => {
  const directory = process.env.PROOF60_OUTPUT_DIR;
  if (!directory) throw new Error('PROOF60_OUTPUT_DIR is required.');
  const requests: { method: string; path: string }[] = [];
  const unexpected: { method: string; origin: string }[] = [];
  await page.route('**/*', route => {
    const request = route.request();
    const address = new URL(request.url());
    if (![UI, API].includes(address.origin)) {
      unexpected.push({ method: request.method(), origin: address.origin });
      return route.abort('blockedbyclient');
    }
    if (address.pathname.startsWith('/api/')) {
      requests.push({ method: request.method(), path: address.pathname });
    }
    // The real API supplies every response; no authored GET replacement applies.
    return route.continue();
  });
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('student2@example.com');
  await page.getByLabel('Password', { exact: true }).fill('Passw0rd!');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const composer = page.getByRole('textbox', { name: 'Message Learning Assistant' });
  await expect(composer).toBeVisible();
  await expect(page.getByText('Demo (mock model)', { exact: true }).first()).toBeVisible();
  const post = page.waitForResponse(response => response.request().method() === 'POST'
    && response.url().endsWith('/messages'));
  await composer.fill('What is photosynthesis?');
  const started = performance.now();
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  const submitted = await post;
  expect(submitted.status()).toBe(202);
  const first = (await submitted.json()).data;
  const oldAnswer = page.locator('[data-answer-id]').last();
  await expect(oldAnswer).toBeVisible({ timeout: 30000 });
  await expect(oldAnswer.locator('.prose')).toContainText(COMPLETE);
  await expect(oldAnswer.locator('.prose')).toContainText(PROTECTED);
  const mockTFull = performance.now() - started;
  await expect(page.getByRole('button', { name: 'Stop generation', exact: true })).toHaveCount(0);
  await expect(page).toHaveURL(/\/chat\/[0-9a-f-]+$/);
  const sessionId = new URL(page.url()).pathname.split('/')[2];
  const answerId = await oldAnswer.getAttribute('data-answer-id');
  expect(answerId).toBeTruthy();
  const token = await page.evaluate(() => sessionStorage.getItem('cs30.access-token'));
  expect(typeof token).toBe('string');
  const api = async (route: string) => {
    const result = await page.request.get(`${API}/api/v1${route}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(result.ok()).toBe(true);
    return (await result.json()).data;
  };
  const answer = await api(`/answers/${answerId}`);
  const firstJob = await api(`/jobs/${first.job_id}`);
  expect(firstJob.state).toBe('succeeded');
  expect(firstJob.answer_id).toBe(answerId);
  expect(answer.request_id).toBe(first.request_id);
  expect(answer.model_mode).toBe('mock');
  expect(answer.response.answer_text).toBe(`${COMPLETE} [ev_001] ${PROTECTED} [ev_001]`);
  expect(answer.response.citations.length).toBeGreaterThan(0);
  const opened = page.waitForResponse(response => response.request().method() === 'POST'
    && response.url().endsWith(`/answers/${answerId}/exposures`)
    && response.request().postDataJSON()?.kind === 'citation_opened');
  await oldAnswer.getByRole('button', { name: 'Open source 1' }).first().click();
  await expect(page.getByRole('dialog', { name: 'Sources' })).toBeVisible();
  const openResponse = await opened;
  expect(openResponse.ok()).toBe(true);
  const view = (await openResponse.json()).data.citation_view;
  expect(view.evidence_id).toBe(answer.response.citations[0]);
  await expect(page.locator('.source-passage')).toHaveText(
    view.segments.map((part: { text: string }) => part.text).join(''),
  );
  await page.screenshot({ path: testInfo.outputPath('success-source.png'), fullPage: true });
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog', { name: 'Sources' })).toHaveCount(0);
  const evidenceHashes: Record<string, string> = {};
  for (const identity of answer.response.citations) {
    const evidence = await api(`/answers/${answerId}/evidence/${identity}`);
    evidenceHashes[identity] = evidence.text_hash;
  }
  await page.reload();
  await expect(page.locator('[data-answer-id]')).toHaveCount(1);
  await expect(page.locator('[data-answer-id]').last()).toHaveAttribute('data-answer-id', answerId!);
  await expect(page.locator('.assistant-message .prose')).toContainText(COMPLETE);
  await expect(page.locator('.assistant-message .prose')).toContainText(PROTECTED);
  await fs.writeFile(path.join(directory, 'success-dom.txt'), await page.locator('body').innerText(), { flag: 'wx' });
  await page.screenshot({ path: testInfo.outputPath('success-reload.png'), fullPage: true });

  const secondPost = page.waitForResponse(response => response.request().method() === 'POST'
    && response.url().endsWith('/messages'));
  await composer.fill('What is photosynthesis?');
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  const secondResponse = await secondPost;
  expect(secondResponse.status()).toBe(202);
  const second = (await secondResponse.json()).data;
  // This edits only the ordinary client draft, never the frozen submitted request.
  await composer.fill(DRAFT);
  await expect(page.getByText('The response could not be completed.', { exact: true })).toBeVisible({ timeout: 30000 });
  const secondJob = await api(`/jobs/${second.job_id}`);
  expect(secondJob.state).toBe('failed');
  expect(secondJob.answer_id).toBeNull();
  expect(secondJob.error.code).toBe('SEMANTIC_CHECK_FAILED');
  await expect(page.getByText(secondJob.error.message, { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Retry response', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Stop generation', exact: true })).toHaveCount(0);
  await expect(page.locator('[data-answer-id]')).toHaveCount(1);
  await expect(page.locator('[data-answer-id]').last()).toHaveAttribute('data-answer-id', answerId!);
  await expect(page.locator('.assistant-message .prose')).toContainText(COMPLETE);
  await expect(composer).toHaveValue(DRAFT);
  await page.screenshot({ path: testInfo.outputPath('partial-failure.png'), fullPage: true });
  await page.waitForTimeout(1700);
  expect(requests.filter(row => row.method === 'POST' && row.path.endsWith('/messages'))).toHaveLength(2);
  expect(requests.filter(row => row.method === 'POST' && row.path.endsWith('/retry'))).toHaveLength(0);
  await page.reload();
  await expect(page.getByText('The response could not be completed.', { exact: true })).toBeVisible();
  await expect(page.getByText(secondJob.error.message, { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Retry response', exact: true })).toBeVisible();
  await expect(page.locator('[data-answer-id]')).toHaveCount(1);
  await expect(page.locator('[data-answer-id]').last()).toHaveAttribute('data-answer-id', answerId!);
  await expect(page.locator('.assistant-message .prose')).toContainText(COMPLETE);
  await expect(composer).toHaveValue(DRAFT);
  const history = await api(`/sessions/${sessionId}/messages?limit=100`);
  const savedAnswers = history.items.filter((row: { answer?: { id: string } }) => row.answer);
  expect(savedAnswers).toHaveLength(1);
  expect(savedAnswers[0].answer.id).toBe(answerId);
  expect(history.latest_job_id).toBe(second.job_id);
  expect(requests.filter(row => row.method === 'POST' && row.path.endsWith('/messages'))).toHaveLength(2);
  expect(requests.filter(row => row.method === 'POST' && row.path.endsWith('/retry'))).toHaveLength(0);
  expect(unexpected).toEqual([]);
  await fs.writeFile(path.join(directory, 'partial-reload-dom.txt'), await page.locator('body').innerText(), { flag: 'wx' });
  await page.screenshot({ path: testInfo.outputPath('partial-reload.png'), fullPage: true });
  await fs.writeFile(path.join(directory, 'proof60-browser-receipt.json'), JSON.stringify({
    session_id: sessionId,
    success: { request_id: first.request_id, job_id: first.job_id, answer_id: answerId,
      response: answer.response, cited_evidence_ids: answer.response.citations,
      evidence_hashes: evidenceHashes, mock_send_to_complete_dom_ms: mockTFull },
    partial: { request_id: second.request_id, job_id: second.job_id, error_code: secondJob.error.code,
      old_answer_id: answerId, old_answer_preserved: true, draft_preserved_on_reload: true },
    message_posts: requests.filter(row => row.method === 'POST' && row.path.endsWith('/messages')).length,
    automatic_retry_posts: requests.filter(row => row.method === 'POST' && row.path.endsWith('/retry')).length,
    unexpected_origins: unexpected, requests, model_mode: 'mock', actual_browser_api_worker: true,
    scientific_quality_claim: false, live_model_t_full_ms: null,
  }, null, 2), { flag: 'wx' });
});
