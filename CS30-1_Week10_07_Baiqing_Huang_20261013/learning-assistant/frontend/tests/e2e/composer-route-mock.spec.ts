import { test, expect } from '@playwright/test';
import type { Locator, Page, Route } from '@playwright/test';
import { createHash } from 'node:crypto';
import type { Answer, Capabilities, Evidence, Job, JobReceipt, Message, MessagePage, Profile, Session, User } from '../../src/types';

// Browser regression coverage only. Every API response and history row below is
// synthetic and held in memory. This does not verify a real endpoint, database,
// worker, model, or physical IME. The test environment supplies the frontend
// server; this specification starts no service.
test.use({ storageState: { cookies: [], origins: [] }, serviceWorkers: 'block' });

const timestamp = '2026-10-11T00:00:00Z';
const followUp = 'Why does G3P leave the cycle?';
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
type SendBody = { content: string; use_profile: boolean; answer_mode: 'textbook' };
type Submission = {
  path: string; body: unknown; key: string | null;
  jobId: string; requestId: string; userMessageId: string;
};

class SyntheticChat {
  readonly user: User = {
    id: 'synthetic-composer-learner', email: 'composer@example.invalid',
    full_name: 'Synthetic Composer Learner', role: 'learner', status: 'active', version: 1,
  };
  readonly session: Session;
  readonly profile: Profile = { level: 'intermediate', style: 'concise', language: 'en', topics: [], version: 1 };
  readonly capabilities: Capabilities = {
    model_mode: 'mock', chat_ready: true, evaluation_ready: false,
    feature_flags: {}, missing_reasons: {}, contract_versions: [], providers: [],
  };
  readonly messages: Message[] = [];
  readonly jobs = new Map<string, Job>();
  readonly submissions: Submission[] = [];
  readonly unexpectedRequests: string[] = [];
  readonly browserErrors: string[] = [];
  private activeJobId: string | null = null;
  private latestJobId: string | null = null;
  private receiptReleases: Array<() => void> = [];
  holdReceipt = false;
  historyReads = 0;

  constructor(readonly origin: string, name: string) {
    this.session = {
      id: `synthetic-composer-session-${name}`, title: `Composer regression ${name}`,
      status: 'active', version: 1, created_at: timestamp, updated_at: timestamp,
    };
  }

  releaseReceipts() {
    this.holdReceipt = false;
    for (const release of this.receiptReleases.splice(0)) release();
  }

  latestJob(): Job {
    const job = this.latestJobId && this.jobs.get(this.latestJobId);
    if (!job) throw new Error('No synthetic job has been submitted.');
    return job;
  }

  complete(jobId: string, text = 'Synthetic explanation: fixed carbon can leave as G3P or regenerate RuBP.'): Answer {
    const job = this.jobs.get(jobId);
    if (!job) throw new Error('Unknown synthetic job.');
    const userMessage = this.messages.find(message => message.request_id === job.request_id && message.role === 'user');
    if (!userMessage) throw new Error('The synthetic user message is missing.');
    const sourceText = 'Synthetic classroom source passage for UI acceptance.';
    const evidence: Evidence = {
      evidence_id: 'synthetic-composer-evidence', chunk_id: 'synthetic-composer-chunk',
      asset_id: 'synthetic-composer-asset', processing_id: 'synthetic-composer-processing',
      source_title: 'Synthetic classroom source', source_url: null, locator: 'Fixture paragraph',
      section: 'Synthetic section', pages: [], text: sourceText,
      text_hash: createHash('sha256').update(sourceText, 'utf8').digest('hex'), context_order: 1,
    };
    const answer: Answer = {
      id: `${jobId}-answer`, job_id: jobId, message_id: null,
      request_id: job.request_id, response_schema: 'chat_response_v1',
      mode: 'interactive_chat', answer_mode: 'textbook', model_mode: 'mock',
      source_provenance: 'textbook_evidence', status: 'answered',
      teaching_mode: 'direct', task_id: null, help_level: 0, can_regenerate: false,
      evidence: [evidence], profile_snapshot: { use_profile: false },
      conversation_snapshot: null, presentation: null, timing: {},
      response: {
        schema_version: 'chat_response_v1', response_type: 'answer', answer_text: text,
        short_answer: null, confidence: null, refusal_reason: null,
        citations: [evidence.evidence_id], follow_up_questions: [followUp],
      },
    };
    job.state = 'succeeded'; job.stage = 'completed'; job.answer_id = answer.id;
    userMessage.state = 'completed';
    this.messages.push({
      id: `${jobId}-assistant`, session_id: this.session.id, sequence: this.messages.length + 1,
      role: 'assistant', state: 'completed', content: text, created_at: timestamp,
      request_id: job.request_id, active_answer_id: answer.id, answer,
    });
    this.activeJobId = null;
    return answer;
  }

  private async deny(route: Route, reason: string) {
    this.unexpectedRequests.push(`${route.request().method()} ${route.request().url()}: ${reason}`);
    await route.abort('blockedbyclient');
  }

  route = async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== this.origin) return this.deny(route, 'External origin');
    if (!url.pathname.startsWith('/api/')) return route.continue();
    if (!url.pathname.startsWith('/api/v1/')) return this.deny(route, 'Unexpected API prefix');
    const path = url.pathname.slice('/api/v1'.length);
    const method = request.method();
    let data: unknown;
    if (method === 'POST' && path === '/auth/login') {
      // The ordinary login UI uses a synthetic password; no auth helper or real
      // account is consulted, and this token never reaches a backend.
      data = { access_token: 'synthetic-composer-browser-token' };
    } else if (method === 'GET' && path === '/users/me') data = this.user;
    else if (method === 'GET' && path === '/profiles/me') data = this.profile;
    else if (method === 'GET' && path === '/capabilities') data = this.capabilities;
    else if (method === 'GET' && path === '/sessions') data = [this.session];
    else if (method === 'GET' && path === `/sessions/${this.session.id}`) data = this.session;
    else if (method === 'GET' && path === `/sessions/${this.session.id}/messages`) {
      this.historyReads++;
      data = {
        items: this.messages, active_job_id: this.activeJobId,
        latest_job_id: this.latestJobId, next_after_sequence: null,
      } satisfies MessagePage;
    } else if (method === 'POST' && path === `/sessions/${this.session.id}/messages`) {
      const body: unknown = request.postDataJSON();
      if (!body || typeof body !== 'object' || typeof (body as SendBody).content !== 'string') {
        return this.deny(route, 'Malformed synthetic message');
      }
      const jobId = `${this.session.id}-job-${this.submissions.length + 1}`;
      const requestId = `${jobId}-request`;
      const userMessageId = `${jobId}-user`;
      this.submissions.push({
        path, body, key: request.headers()['idempotency-key'] || null,
        jobId, requestId, userMessageId,
      });
      this.messages.push({
        id: userMessageId, session_id: this.session.id, sequence: this.messages.length + 1,
        role: 'user', state: 'queued', content: (body as SendBody).content,
        created_at: timestamp, request_id: requestId, active_answer_id: null, answer: null,
      });
      this.jobs.set(jobId, {
        id: jobId, request_id: requestId, state: 'queued', stage: 'queued',
        can_retry: false, error: null, answer_id: null, created_at: timestamp, updated_at: timestamp,
      });
      this.activeJobId = this.latestJobId = jobId;
      if (this.holdReceipt) await new Promise<void>(resolve => this.receiptReleases.push(resolve));
      data = {
        job_id: jobId, user_message_id: userMessageId, request_id: requestId,
        poll_url: `/api/v1/jobs/${jobId}`,
      } satisfies JobReceipt;
    } else if (method === 'GET' && path.startsWith('/jobs/')) {
      const job = this.jobs.get(path.slice('/jobs/'.length));
      if (!job) return this.deny(route, 'Unknown synthetic job');
      data = job;
    } else return this.deny(route, 'Unexpected API request');
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ data, meta: { trace_id: 'synthetic-composer-trace' } }),
    });
  };
}

const fixtures = new WeakMap<Page, SyntheticChat>();

async function openSyntheticChat(page: Page, baseURL: string | undefined, name: string) {
  if (!baseURL) throw new Error('This spec requires the frontend baseURL from the Playwright config.');
  const target = new URL(baseURL);
  if (!['http:', 'https:'].includes(target.protocol) || !['127.0.0.1', 'localhost', '[::1]'].includes(target.hostname)) {
    throw new Error('This synthetic spec requires a local frontend origin.');
  }
  const state = new SyntheticChat(target.origin, name);
  fixtures.set(page, state);
  page.on('pageerror', error => state.browserErrors.push(error.message));
  await page.context().route('**/*', state.route);
  await page.goto(`/chat/${state.session.id}`);
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
  await page.getByLabel('Email', { exact: true }).fill(state.user.email);
  await page.getByLabel('Password', { exact: true }).fill('synthetic-only-composer-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const input = page.getByRole('textbox', { name: 'Message Learning Assistant' });
  await expect(input).toBeVisible();
  await page.getByRole('checkbox').uncheck();
  return { state, input };
}

test.afterEach(async ({ page }) => {
  const state = fixtures.get(page);
  if (!state) return;
  state.releaseReceipts();
  expect.soft(state.unexpectedRequests, 'Unexpected requests were aborted').toEqual([]);
  expect.soft(state.browserErrors, 'Browser exceptions').toEqual([]);
});

async function syntheticEnter(input: Locator, keyCode: number, isComposing: boolean, composition = false) {
  return input.evaluate((node, fields) => {
    if (fields.composition) node.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true, data: '学' }));
    const event = new KeyboardEvent('keydown', {
      key: 'Enter', code: 'Enter', keyCode: fields.keyCode, which: fields.keyCode,
      bubbles: true, cancelable: true, isComposing: fields.isComposing,
    });
    const allowed = node.dispatchEvent(event);
    if (fields.composition) node.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true, data: '学' }));
    return {
      native_is_composing: event.isComposing, native_key_code: event.keyCode,
      default_prevented: event.defaultPrevented, dispatch_allowed: allowed,
    };
  }, { keyCode, isComposing, composition });
}

async function browserFrames(input: Locator) {
  await input.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
}

test('Enter submits exactly once while the receipt is pending and shows completion', async ({ page, baseURL }) => {
  const { state, input } = await openSyntheticChat(page, baseURL, 'enter');
  state.holdReceipt = true;
  await input.fill('What happens to fixed carbon?');
  await input.press('Enter');
  await expect.poll(() => state.submissions.length).toBe(1);
  await input.press('Enter');
  await expect(page.locator('.generation-status')).toHaveAttribute('data-progress-state', 'submitting');
  expect(state.submissions).toHaveLength(1);
  state.releaseReceipts();
  await expect(page.locator('.generation-status')).toHaveAttribute('data-progress-state', 'queued');
  const job = state.latestJob();
  job.state = 'running'; job.stage = 'generating';
  await expect(page.locator('.generation-status')).toHaveAttribute('data-progress-state', 'running');
  await expect(page.locator('.generation-status')).toContainText('Preparing an explanation');
  const answer = state.complete(job.id);
  await expect(page.locator('[data-answer-id]')).toHaveAttribute('data-answer-id', answer.id);
  await expect(page.locator('.generation-status')).toHaveCount(0);
  await expect(input).toHaveValue('');
  expect(state.submissions).toHaveLength(1);
  expect(state.submissions[0].path).toBe(`/sessions/${state.session.id}/messages`);
  expect(state.submissions[0].body).toEqual({ content: 'What happens to fixed carbon?', use_profile: false, answer_mode: 'textbook' });
  expect(state.submissions[0].key).toMatch(uuid);
});

test('Shift+Enter inserts a real keyboard newline without submitting', async ({ page, baseURL }) => {
  const { state, input } = await openSyntheticChat(page, baseURL, 'newline');
  await input.fill('First line');
  await input.press('End');
  await input.press('Shift+Enter');
  await page.keyboard.insertText('Second line');
  await expect(input).toHaveValue('First line\nSecond line');
  await expect(page.locator('.generation-status')).toHaveCount(0);
  expect(state.submissions).toHaveLength(0);
});

for (const scenario of [
  { name: 'native composition flag', keyCode: 13, isComposing: true, composition: true },
  { name: 'independent key code 229', keyCode: 229, isComposing: false, composition: false },
]) {
  test(`IME Enter with ${scenario.name} preserves the draft without submitting`, async ({ page, baseURL }) => {
    const { state, input } = await openSyntheticChat(page, baseURL, `ime-${scenario.keyCode}`);
    const draft = 'Synthetic IME draft';
    await input.fill(draft);
    const observed = await syntheticEnter(input, scenario.keyCode, scenario.isComposing, scenario.composition);
    await browserFrames(input);
    expect(observed).toEqual({
      native_is_composing: scenario.isComposing, native_key_code: scenario.keyCode,
      default_prevented: false, dispatch_allowed: true,
    });
    await expect(input).toHaveValue(draft);
    expect(state.submissions).toHaveLength(0);
  });
}

test('The synthetic normal Enter positive control reaches the product handler', async ({ page, baseURL }) => {
  const { state, input } = await openSyntheticChat(page, baseURL, 'positive-control');
  const content = 'Synthetic keyboard positive control.';
  await input.fill(content);
  const observed = await syntheticEnter(input, 13, false);
  expect(observed).toEqual({
    native_is_composing: false, native_key_code: 13, default_prevented: true, dispatch_allowed: false,
  });
  await expect.poll(() => state.submissions.length).toBe(1);
  expect(state.submissions[0].body).toEqual({ content, use_profile: false, answer_mode: 'textbook' });
  expect(state.submissions[0].key).toMatch(uuid);
  const answer = state.complete(state.latestJob().id);
  await expect(page.locator('[data-answer-id]')).toHaveAttribute('data-answer-id', answer.id);
  expect(state.submissions).toHaveLength(1);
});

test('Follow-up creates a distinct turn in the same session and reloads mock history', async ({ page, baseURL }) => {
  const { state, input } = await openSyntheticChat(page, baseURL, 'followup');
  await input.fill('Explain the carbon cycle.');
  await input.press('Enter');
  await expect.poll(() => state.submissions.length).toBe(1);
  const first = state.complete(state.latestJob().id);
  const firstAnswer = page.locator(`[data-answer-id="${first.id}"]`);
  await expect(firstAnswer).toBeVisible();
  await expect(page.getByRole('button', { name: 'Stop generation', exact: true })).toHaveCount(0);
  const suggestion = firstAnswer.getByRole('button', { name: followUp, exact: true });
  await suggestion.click();
  await expect.poll(() => state.submissions.length).toBe(2);
  await expect(suggestion).toBeDisabled();
  const [initial, next] = state.submissions;
  expect(initial.path).toBe(`/sessions/${state.session.id}/messages`);
  expect(next.path).toBe(initial.path);
  expect(next.body).toEqual({ content: followUp, use_profile: false, answer_mode: 'textbook' });
  expect(initial.key).toMatch(uuid); expect(next.key).toMatch(uuid);
  expect(next.key).not.toBe(initial.key);
  expect(next.jobId).not.toBe(initial.jobId);
  expect(next.requestId).not.toBe(initial.requestId);
  expect(next.userMessageId).not.toBe(initial.userMessageId);
  const second = state.complete(next.jobId, 'Synthetic follow-up explanation: exported G3P supplies other organic molecules.');
  await expect(page.locator('[data-answer-id]')).toHaveCount(2);
  await expect(page.locator('[data-answer-id]').last()).toHaveAttribute('data-answer-id', second.id);
  await expect(page.locator(`[data-message-id="${next.userMessageId}"] .user-bubble`)).toHaveText(followUp);
  await expect(suggestion).toBeEnabled();
  expect(state.messages).toHaveLength(4);
  const historyReads = state.historyReads;
  await page.reload();
  await expect(page.locator('[data-answer-id]')).toHaveCount(2);
  await expect(page.locator('[data-answer-id]').first()).toHaveAttribute('data-answer-id', first.id);
  await expect(page.locator('[data-answer-id]').last()).toHaveAttribute('data-answer-id', second.id);
  expect(state.historyReads).toBeGreaterThan(historyReads);
  expect(state.submissions).toHaveLength(2);
});
