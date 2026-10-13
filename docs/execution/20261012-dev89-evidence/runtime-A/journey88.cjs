'use strict';

// One direct normal-product journey. Credentials stay in local memory.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { observeCompletion } = require('./completion-observer88.cjs');
const { chromium, expect } = require('E:/5703/learning-assistant/frontend/node_modules/@playwright/test');
const stage = process.argv[2];
if (!['case10', 'case10b', 'case10c'].includes(stage)) throw new Error('FIXED_STAGE_REQUIRED');
const out = path.join(__dirname, stage, 'journey-receipt88.json');
if (fs.existsSync(out)) throw new Error('PRESERVE_PRIOR_JOURNEY');
const receipt = { started_utc: new Date().toISOString(), stage: 'START', status: 'STARTED',
  stdin_end: false, stdin_close: false, exit_code: null, signal: null,
  new_message_submissions: 0, send_to_first_prose_ms: null, send_to_complete_dom_ms: null,
  n: 0, planned_journey_n: 1, completed_answer_n: 0, valid_page_latency_sample: false,
  TTFT_ms: null, stable_p95_ms: null, auth_exported: false, normal_activation_qualified: false,
  browser_closed: false, route_stops: [], events: [] };
let privateValues = []; let sessionId = null; let answerId = null; let messageSubmitted = false;
const memoryLogin = new Promise((resolve, reject) => {
  let bytes = Buffer.alloc(0);
  const timer = setTimeout(() => { bytes.fill(0); reject(new Error('MEMORY_LOGIN_TIMEOUT')); }, 15000);
  process.stdin.on('data', chunk => {
    if (bytes.length + chunk.length > 4096) { bytes.fill(0); clearTimeout(timer); reject(new Error('MEMORY_LOGIN_TOO_LARGE')); return; }
    bytes = Buffer.concat([bytes, chunk]);
  });
  process.stdin.once('end', () => {
    clearTimeout(timer);
    let auth;
    try { auth = JSON.parse(bytes.toString('utf8')); } catch { bytes.fill(0); reject(new Error('MEMORY_LOGIN_INVALID')); return; }
    bytes.fill(0);
    if (!auth || Object.keys(auth).sort().join(',') !== 'email,password' || typeof auth.email !== 'string' || !auth.email
        || typeof auth.password !== 'string' || !auth.password) { reject(new Error('MEMORY_LOGIN_INVALID')); return; }
    privateValues = [auth.email, auth.password];
    resolve({ learner_email: auth.email, password: auth.password });
    auth.email = null; auth.password = null;
  });
  process.stdin.once('error', () => { clearTimeout(timer); bytes.fill(0); reject(new Error('MEMORY_LOGIN_READ_FAILED')); });
});
memoryLogin.catch(() => {});
function readPublic(name) {
  const filename = path.resolve(__dirname, name);
  if (!filename.startsWith(`${path.resolve(__dirname)}${path.sep}`) || fs.lstatSync(filename).isSymbolicLink()
      || fs.realpathSync(filename).toLowerCase() !== filename.toLowerCase()) throw new Error('PUBLIC_PIN_PATH_FORBIDDEN');
  const bytes = fs.readFileSync(filename);
  return { value: JSON.parse(bytes.toString('utf8')), bytes: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex') };
}
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  return value;
}
function publicDigest(value) { return crypto.createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex'); }

function publicError(error) {
  let value = String(error?.stack || error?.message || error);
  for (const secret of privateValues) if (secret) value = value.split(secret).join('[PRIVATE]');
  value = value.replace(/Bearer\s+[A-Za-z0-9_.-]+/gi, 'Bearer [PRIVATE]')
    .replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, '[PRIVATE_TOKEN]');
  return { name: String(error?.name || 'Error'), code: error?.code || null, diagnostic: value.slice(0, 3000) };
}
function event(kind, data = {}) {
  const row = { kind, at_utc: new Date().toISOString(), ...data };
  receipt.events.push(row); process.stdout.write(`${JSON.stringify(row)}\n`);
}
process.stdin.on('end', () => { receipt.stdin_end = true; });
process.stdin.on('close', () => { receipt.stdin_close = true; });
process.stdin.on('error', error => { receipt.stdin_error = publicError(error); });
process.stdin.resume();
process.on('unhandledRejection', error => {
  receipt.unhandled_rejection = publicError(error); console.error(JSON.stringify(receipt.unhandled_rejection));
  process.exitCode = 1;
});
process.on('uncaughtException', error => {
  receipt.uncaught_exception = publicError(error); console.error(JSON.stringify(receipt.uncaught_exception));
  process.exit(1);
});
for (const signal of ['SIGTERM', 'SIGINT']) process.on(signal, () => { receipt.signal = signal; process.exit(1); });
process.on('exit', code => {
  receipt.exit_code = code; receipt.finished_utc = new Date().toISOString();
  fs.writeFileSync(out, `${JSON.stringify(receipt, null, 2)}\n`, { flag: 'wx' });
});

(async () => {
  let browser; let context; let page; let scopeVerified = false;
  try {
    event('DIRECT_NODE_STARTED', { node_version: process.version, pid: process.pid });
    const admissionFile = path.join(__dirname, 'page-admission89.cjs');
    if (crypto.createHash('sha256').update(fs.readFileSync(admissionFile)).digest('hex') !== 'd8a876f7ec10ca1c0aa86388e269c81dafbb081a34181478466cc669c3d851f0')
      throw new Error('FROZEN_PAGE_METADATA_ADMISSION_CHANGED');
    const { validatePageBundle } = require('./page-admission89.cjs');
    const { protocol, scoped, scope, descriptor, qa } = validatePageBundle(__dirname, stage, readPublic, publicDigest);
    scopeVerified = true;
    receipt.scope_sha256 = scoped.sha256; receipt.protocol_sha256 = protocol.sha256;
    receipt.supplement_descriptor_sha256 = descriptor.sha256; receipt.independent_qa_sha256 = qa.sha256;
    receipt.source_version_sha256 = descriptor.value.instance_source_version_sha256;
    receipt.prior_quality_answer_sha256 = descriptor.value.actual_answer_sha256;
    receipt.maximum_physical_posts = 32; receipt.per_request_provider_calls_maximum = 4;
    receipt.stage = 'ORIGINAL_LOCAL_FIXTURE_LOGIN';
    const auth = await memoryLogin;
    const question = scope.question_text;
    receipt.question_id = scope.question_id;
    receipt.question_sha256 = crypto.createHash('sha256').update(question).digest('hex');
    receipt.stage = 'CHROME_LAUNCH';
    browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true, timeout: 15000 });
    receipt.browser_version = browser.version();
    context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    await context.route('**/*', async route => {
      try {
        const request = route.request(); const address = new URL(request.url());
        if (!['http://127.0.0.1:15198', 'http://127.0.0.1:18029'].includes(address.origin)) throw new Error('BROWSER_ORIGIN_FORBIDDEN');
        if (!['GET', 'HEAD', 'OPTIONS', 'POST'].includes(request.method())) throw new Error('UNEXPECTED_WRITE_METHOD');
        if (request.method() === 'POST') {
          const name = address.pathname;
          if (name === '/api/v1/auth/login' || name === '/api/v1/sessions') { /* Server admits each once. */ }
          else if (sessionId && name === `/api/v1/sessions/${sessionId}/messages`) {
            const body = request.postDataJSON();
            if (messageSubmitted || body.content !== question || body.use_profile !== false || body.answer_mode !== 'textbook'
                || body.reading_context || (body.teaching_mode && body.teaching_mode !== 'direct')
                || Object.keys(body).some(k => !['content', 'use_profile', 'answer_mode', 'teaching_mode', 'task_action'].includes(k)))
              throw new Error('EXACT_SINGLE_PUBLIC_QUESTION_REQUIRED');
            messageSubmitted = true; receipt.new_message_submissions = 1;
          } else if (!/^\/api\/v1\/answers\/[0-9a-f-]{36}\/(exposures|readings)$/.test(name)) throw new Error('UNEXPECTED_POST');
        }
        await route.continue();
      } catch (error) {
        receipt.route_stops.push(publicError(error)); await route.abort('blockedbyclient');
      }
    });
    page = await context.newPage();
    page.on('pageerror', error => event('PAGE_ERROR', publicError(error)));
    receipt.stage = 'NORMAL_LOGIN';
    await page.goto('http://127.0.0.1:15198/login', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.getByLabel('Email', { exact: true }).fill(auth.learner_email);
    await page.getByLabel('Password', { exact: true }).fill(auth.password);
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    auth.password = null; auth.learner_email = null;
    const composer = page.getByRole('textbox', { name: 'Message Learning Assistant', exact: true });
    await expect(composer).toBeVisible({ timeout: 15000 });
    await expect(page.locator('.mode-badge')).toHaveText('Live model');
    event('NORMAL_LOGIN_PASS');
    receipt.stage = 'ONE_FRESH_SESSION';
    const createButton = page.locator('.desktop-sidebar button.new-chat').filter({ hasText: /^New chat$/ });
    await expect(createButton).toHaveCount(1);
    const created = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/v1/sessions', { timeout: 15000 });
    const createClick = createButton.click();
    const [createdResponse] = await Promise.all([created, createClick]);
    if (!createdResponse.ok()) throw new Error('FRESH_SESSION_FAILED');
    sessionId = (await createdResponse.json()).data.id; receipt.session_id = sessionId;
    await expect(page).toHaveURL(`http://127.0.0.1:15198/chat/${sessionId}`);
    await expect(page.locator('.assistant-message')).toHaveCount(0);
    await expect(page.locator('.user-message')).toHaveCount(0);
    await page.getByRole('combobox', { name: 'Answer source', exact: true }).selectOption('textbook');
    await page.getByRole('combobox', { name: 'Teaching style', exact: true }).selectOption('direct');
    await page.locator('.profile-toggle input[type="checkbox"]').uncheck();
    await composer.fill(question);
    await page.evaluate(() => {
      const clock = window.__journey77 = { send: null, first: null, complete: null, answer: null };
      document.addEventListener('click', e => {
        if (e.target instanceof Element && e.target.closest('button')?.getAttribute('aria-label') === 'Send message' && clock.send === null)
          clock.send = performance.now();
      }, { capture: true });
      new MutationObserver(() => {
        if (clock.send === null) return;
        const node = document.querySelector('.assistant-message[data-answer-id]');
        if (!node?.querySelector('.prose')?.textContent?.trim()) return;
        clock.first ??= performance.now();
        if (!document.querySelector('button[aria-label="Stop generation"]') && !document.querySelector('.generation-status') && clock.complete === null) {
          clock.complete = performance.now(); clock.answer = node.getAttribute('data-answer-id');
        }
      }).observe(document.documentElement, { subtree: true, childList: true, attributes: true, characterData: true });
    });
    event('FRESH_EMPTY_SESSION_READY', { session_id: sessionId, profile: false });
    receipt.stage = 'SINGLE_SEND';
    const accepted = page.waitForResponse(r => r.request().method() === 'POST'
      && new URL(r.url()).pathname === `/api/v1/sessions/${sessionId}/messages`, { timeout: 30000 });
    const sendClick = page.getByRole('button', { name: 'Send message', exact: true }).click();
    const [admitted] = await Promise.all([accepted, sendClick]);
    if (admitted.status() !== 202) throw new Error('MESSAGE_NOT_ACCEPTED');
    const jobReceipt = (await admitted.json()).data; receipt.accepted = jobReceipt;
    event('ONE_QUESTION_ACCEPTED', { job_id: jobReceipt.job_id, request_id: jobReceipt.request_id });
    receipt.stage = 'COMPLETE_DOM';
    const clock = await observeCompletion(page, jobReceipt.job_id); answerId = clock.answer;
    receipt.send_to_first_prose_ms = clock.first - clock.send;
    receipt.send_to_complete_dom_ms = clock.complete - clock.send;
    receipt.answer_id = answerId;
    event('COMPLETE_DOM_OBSERVED', { send_to_first_prose_ms: receipt.send_to_first_prose_ms, send_to_complete_dom_ms: receipt.send_to_complete_dom_ms });
    receipt.stage = 'PERSISTED_JOIN';
    const dto = await page.evaluate(async ({ sessionId, answerId, jobId }) => {
      let answerPublicEnvelopeRaw = null;
      const get = async name => {
        const response = await fetch(`/api/v1${name}`, { headers: { Authorization: `Bearer ${sessionStorage.getItem('cs30.access-token')}` } });
        if (!response.ok) throw new Error('PUBLIC_DTO_READ_FAILED');
        const text = await response.text();
        if (name === `/answers/${answerId}`) answerPublicEnvelopeRaw = text;
        return JSON.parse(text).data;
      };
      const job = await get(`/jobs/${jobId}`), answer = await get(`/answers/${answerId}`), history = await get(`/sessions/${sessionId}/messages?limit=100`);
      return { job, answer, history, answerPublicEnvelopeRaw };
    }, { sessionId, answerId, jobId: jobReceipt.job_id });
    if (dto.job.state !== 'succeeded' || dto.job.answer_id !== answerId || dto.answer.request_id !== jobReceipt.request_id
        || dto.answer.model_mode !== 'live' || dto.answer.response_schema !== 'chat_response_v1'
        || dto.answer.response?.response_type !== 'answer' || !dto.answer.response.answer_text?.trim() || dto.history.items.length !== 2)
      throw new Error('PERSISTED_NORMAL_ANSWER_JOIN_FAILED');
    const answerEnvelopeRaw = dto.answerPublicEnvelopeRaw;
    if (typeof answerEnvelopeRaw !== 'string' || Buffer.byteLength(answerEnvelopeRaw, 'utf8') > 4 * 1024 * 1024
        || privateValues.some(secret => secret && answerEnvelopeRaw.includes(secret))
        || /Bearer\s+|"(?:access_token|refresh_token|api_key|password|authorization|email)"\s*:|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/i.test(answerEnvelopeRaw))
      throw new Error('ANSWER_PUBLIC_RAW_SECRET_OR_SIZE_WITHHELD');
    receipt.answer_public_envelope_raw_utf8 = answerEnvelopeRaw;
    receipt.answer_public_envelope_raw_sha256 = crypto.createHash('sha256').update(answerEnvelopeRaw, 'utf8').digest('hex');
    receipt.answer_public_envelope_raw_bytes = Buffer.byteLength(answerEnvelopeRaw, 'utf8');
    receipt.answer_public_envelope_raw_domain = 'Original UTF8 answer endpoint JSON; independent QA parses data.response and computes Python canonical DTO hash';
    receipt.response = dto.answer.response; receipt.answer_timing = dto.answer.timing;
    receipt.answer_completeness = dto.answer.answer_completeness || null;
    const answerNode = page.locator(`.assistant-message[data-answer-id="${answerId}"]`);
    const prose = await answerNode.locator('.prose').innerText();
    receipt.complete_visible_prose = prose;
    receipt.complete_visible_prose_sha256_UTF8 = crypto.createHash('sha256').update(prose, 'utf8').digest('hex');
    const citations = await answerNode.locator('button.citation').evaluateAll(nodes => nodes.map(n => n.getAttribute('aria-label')));
    receipt.citations_before_reload = citations;
    if (!citations.length) throw new Error('INLINE_CITATIONS_UNAVAILABLE');
    receipt.stage = 'REFRESH_AND_SOURCES';
    await page.reload({ waitUntil: 'domcontentloaded' });
    const restored = page.locator(`.assistant-message[data-answer-id="${answerId}"]`);
    await expect(restored.locator('.prose')).toHaveText(prose, { timeout: 15000, useInnerText: true });
    const after = await restored.locator('button.citation').evaluateAll(nodes => nodes.map(n => n.getAttribute('aria-label')));
    receipt.citations_after_reload = after;
    if (JSON.stringify(after) !== JSON.stringify(citations)) throw new Error('REFRESHED_CITATIONS_CHANGED');
    const sources = restored.getByRole('button', { name: /^Sources\s+\d+$/ });
    if (await sources.count()) {
      await sources.click();
      await page.locator('.evidence-modal .source-title').waitFor({ timeout: 15000 });
      receipt.source_title_after_reload = await page.locator('.evidence-modal .source-title').innerText();
      receipt.sources_reopened_after_reload = true;
    } else {
      receipt.sources_reopened_after_reload = false;
      throw new Error('REFRESHED_SOURCES_CONTROL_UNAVAILABLE');
    }
    receipt.refreshed_answer_preserved = true; receipt.refreshed_citations_preserved = true;
    if (receipt.route_stops.length) throw new Error('BROWSER_ROUTE_BOUNDARY_STOP');
    receipt.status = 'NORMAL_PRODUCT_SINGLE_JOURNEY_PASS';
    receipt.n = 1; receipt.completed_answer_n = 1; receipt.valid_page_latency_sample = true;
    if (scope.page_answer_requires_independent_quality_review === true) {
      receipt.DOM_observation_n = 1; receipt.page_technical_completion_passed = true;
      receipt.independent_quality_status = 'PENDING';
      receipt.n = 0; receipt.valid_page_latency_sample = false;
      receipt.actual_page_answer_sha256 = publicDigest(dto.answer.response);
      receipt.actual_page_answer_hash_domain = 'UTF8 JSON sorted keys; JSON.stringify numeric serialization; independent QA recomputes canonical Python DTO hash';
    }
    event('NORMAL_PRODUCT_JOURNEY_PASS', { answer_id: answerId, citations: after.length, sources_reopened: receipt.sources_reopened_after_reload });
  } catch (error) {
    receipt.status = 'STOPPED_PRESERVE_NEW_ROWS'; receipt.error = publicError(error);
    console.error(JSON.stringify({ stage: receipt.stage, ...receipt.error })); process.exitCode = 1;
  } finally {
    if (scopeVerified) try {
      const response = await fetch('http://127.0.0.1:18029/native77/close', { method: 'POST', signal: AbortSignal.timeout(10000) });
      receipt.api_close_status = response.status;
      if (response.status !== 200) throw new Error('OWNED_API_NOT_IDLE');
    } catch (error) {
      receipt.api_close_error = publicError(error);
      receipt.status = 'STOPPED_PRESERVE_NEW_ROWS'; process.exitCode = 1;
    } else { receipt.api_close_skipped = 'PUBLIC_SCOPE_NOT_VERIFIED'; }
    receipt.close_errors = [];
    for (const [resource, stage] of [[context, 'CONTEXT_CLOSE'], [browser, 'BROWSER_CLOSE']]) {
      if (!resource) continue;
      try { await resource.close(); if (stage === 'BROWSER_CLOSE') receipt.browser_closed = true; }
      catch (error) {
        receipt.close_errors.push({ stage, ...publicError(error) });
        receipt.status = 'STOPPED_PRESERVE_NEW_ROWS'; process.exitCode = 1;
      }
    }
    if (receipt.route_stops.length) { receipt.status = 'STOPPED_PRESERVE_NEW_ROWS'; process.exitCode = 1; }
    if (receipt.status !== 'NORMAL_PRODUCT_SINGLE_JOURNEY_PASS') {
      receipt.observed_send_to_complete_dom_ms = receipt.send_to_complete_dom_ms;
      receipt.observed_complete_answer_n = receipt.completed_answer_n;
      receipt.send_to_complete_dom_ms = null; receipt.n = 0; receipt.completed_answer_n = 0;
      receipt.valid_page_latency_sample = false;
    }
    process.stdin.pause();
    event('DIRECT_JOURNEY_FINISHED', { status: receipt.status, stage: receipt.stage, api_close_status: receipt.api_close_status });
  }
})();
