// Prepared only. Current application DOM with authored API fixtures; no backend/model acceptance.
const { test, expect } = require('E:/5703/learning-assistant/frontend/node_modules/@playwright/test');

const ORIGIN = 'http://127.0.0.1:15197';
const SESSION_ID = 'ui-only-contract-session58';
const USER_ID = 'ui-only-learner58';
const JOB_ID = 'ui-only-contract-job58';
const DRAFT_KEY = `cs30.draft.${USER_ID}.${SESSION_ID}`;
const OLD_TEXT = 'Previously published explanation remains available.';
const DRAFT_TEXT = 'My unsent follow-up reasoning must remain in the composer.';
const ERROR_TEXT = 'The source check could not confirm a consistent response.';
const TIME = '2026-10-11T00:00:00Z';

test('UI-only: checker contract failure retains the published answer and unsent draft across reload', async ({ page, context }, testInfo) => {
  const requests = [];
  const unexpected = [];
  let releaseFailure = false;
  let failureServed = false;

  const user = { id: USER_ID, full_name: 'UI-only learner', email: 'ui-only@example.test', role: 'student', status: 'active', version: 1 };
  const session = { id: SESSION_ID, title: 'UI-only checker failure fixture', status: 'active', version: 1, created_at: TIME, updated_at: TIME };
  const previousAnswer = {
    id: 'ui-only-published-answer58', request_id: 'ui-only-original-request58', job_id: 'ui-only-original-job58',
    message_id: 'ui-only-assistant-message58', answer_mode: 'textbook', source_provenance: 'textbook_evidence',
    mode: 'interactive_chat', response_schema: 'chat_response_v1', status: 'answered', model_mode: 'mock',
    response: { schema_version: 'chat_response_v1', response_type: 'answer', answer_text: OLD_TEXT,
      short_answer: null, citations: [], refusal_reason: null, follow_up_questions: [], confidence: null },
    evidence: [], profile_snapshot: null, conversation_snapshot: null, timing: {}, can_regenerate: false,
  };
  const runningJob = {
    id: JOB_ID, request_id: 'ui-only-repair-request58', state: 'running', stage: 'checker_contract_repair',
    error: null, answer_id: null, can_retry: false, created_at: TIME, updated_at: TIME,
  };
  const failedJob = { ...runningJob, state: 'failed', error: { code: 'CHECKER_INCONSISTENT', message: ERROR_TEXT }, can_retry: true };
  const history = () => ({
    items: [{ id: previousAnswer.message_id, session_id: SESSION_ID, sequence: 2, role: 'assistant',
      content: '', state: 'answered', active_answer_id: previousAnswer.id, answer: previousAnswer,
      request_id: previousAnswer.request_id, created_at: TIME }],
    next_after_sequence: null, active_job_id: failureServed ? null : JOB_ID,
    latest_job_id: failureServed ? JOB_ID : null,
  });

  // No real account is accessed. Reload only reinstates the fake UI token, never the draft.
  await context.addInitScript(() => sessionStorage.setItem('cs30.access-token', 'ui-only-authored-token58'));
  await context.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== ORIGIN) {
      unexpected.push({ method: request.method(), target: request.url(), reason: 'non-fixture origin' });
      await route.abort('blockedbyclient');
      return;
    }
    if (url.pathname !== '/api' && !url.pathname.startsWith('/api/')) {
      await route.continue();
      return;
    }
    const target = `${url.pathname}${url.search}`;
    requests.push({ method: request.method(), target });
    let data;
    if (request.method() === 'GET') {
      switch (target) {
        case '/api/v1/users/me': data = user; break;
        case '/api/v1/profiles/me': data = { level: 'intermediate', style: 'concise', language: 'en', topics: [], version: 1 }; break;
        case '/api/v1/capabilities':
          data = { model_mode: 'mock', chat_ready: true, evaluation_ready: false,
            missing_reasons: { chat: [], evaluation: ['UI-only fixture'] }, providers: [], feature_flags: {}, contract_versions: [] };
          break;
        case '/api/v1/sessions?status=active': data = [session]; break;
        case `/api/v1/sessions/${SESSION_ID}`: data = session; break;
        case `/api/v1/sessions/${SESSION_ID}/messages?after_sequence=0&limit=100`: data = history(); break;
        case `/api/v1/jobs/${JOB_ID}`:
          failureServed = releaseFailure;
          data = releaseFailure ? failedJob : runningJob;
          break;
        default: break;
      }
    }
    if (data === undefined) {
      unexpected.push({ method: request.method(), target, reason: 'unexpected API or mutation' });
      await route.abort('blockedbyclient');
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ data, meta: { trace_id: 'ui-only-transport58' } }) });
  });

  await page.goto(`${ORIGIN}/chat/${SESSION_ID}`);
  const oldAnswer = page.locator(`[data-answer-id="${previousAnswer.id}"]`);
  const composer = page.getByRole('textbox', { name: 'Message Learning Assistant' });
  await expect(oldAnswer).toContainText(OLD_TEXT);
  await expect(page.getByText('Restoring the source check', { exact: false })).toBeVisible();
  await composer.fill(DRAFT_TEXT);
  await expect.poll(() => page.evaluate(key => sessionStorage.getItem(key), DRAFT_KEY)).toBe(DRAFT_TEXT);
  await expect(page.locator('[data-answer-id]')).toHaveCount(1);
  await expect(page.getByRole('button', { name: 'Stop generation' })).toBeVisible();

  releaseFailure = true;
  await expect(page.getByText('The response could not be completed.', { exact: true })).toBeVisible();
  await expect(page.getByText(ERROR_TEXT, { exact: true })).toBeVisible();
  await page.getByText('Error details', { exact: true }).click();
  await expect(page.getByText('CHECKER_INCONSISTENT', { exact: true })).toBeVisible();
  await expect(page.getByText('Restoring the source check', { exact: false })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Retry response', exact: true })).toBeVisible();
  await expect(oldAnswer).toContainText(OLD_TEXT);
  await expect(page.locator('[data-answer-id]')).toHaveCount(1);
  await expect(composer).toHaveValue(DRAFT_TEXT);
  await expect(page.locator('.user-message')).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath('failure-ui-only.png'), fullPage: true });

  // Observe beyond two normal 750-ms poll intervals without clicking Send or Retry.
  await page.waitForTimeout(1700);
  expect(requests.filter(row => row.method !== 'GET')).toEqual([]);
  expect(unexpected).toEqual([]);
  await page.reload();
  await expect(oldAnswer).toContainText(OLD_TEXT);
  await expect(page.locator('[data-answer-id]')).toHaveCount(1);
  await expect(composer).toHaveValue(DRAFT_TEXT);
  await expect(page.getByText(ERROR_TEXT, { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Retry response', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Stop generation' })).toHaveCount(0);
  await expect.poll(() => page.evaluate(key => sessionStorage.getItem(key), DRAFT_KEY)).toBe(DRAFT_TEXT);
  await expect(page.locator('.user-message')).toHaveCount(0);
  expect(requests.filter(row => row.method !== 'GET')).toEqual([]);
  expect(unexpected).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath('reload-ui-only.png'), fullPage: true });
  await testInfo.attach('ui-only-transport.json', {
    body: Buffer.from(JSON.stringify({ scope: 'UI_ONLY_AUTHORED_API_FIXTURES', browser: 'Microsoft Edge',
      application_source: 'E:/5703/learning-assistant/frontend', requests, unexpected,
      real_api_database_model_operations: 0, automatic_submission_or_retry_posts: 0,
      backend_checker_contract_or_semantic_acceptance: false }, null, 2)), contentType: 'application/json',
  });
});
