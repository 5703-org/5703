'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const frontendRoot = process.env.CS30_FRONTEND_ROOT || path.resolve(__dirname, '../../frontend');
const { chromium } = require(path.join(frontendRoot, 'node_modules/@playwright/test'));
const { armTerminalObserver, renderExpectedProse } = require('./browser_terminal_observer.cjs');
const { observeOneSubmission } = require('./observe_one_submission.cjs');
const receipt = { job_id: 'fixture-job', request_id: 'fixture-request', user_message_id: 'fixture-user' };
const controls = [];
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CS30_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  let fakeGets = 0;
  try {
    async function fixture({ type = 'answer', state = 'succeeded', denied = false, wrongRequest = false, integrated = false } = {}) {
      const page = await browser.newPage();
      const response = { response_type: type, answer_text: type === 'answer' ? '**Complete** body [ev_001]. Final sentence.' : 'Insufficient evidence for this question.', citations: type === 'answer' ? ['ev_001'] : [] };
      const answer = { id: 'fixture-answer', job_id: receipt.job_id, status: type === 'answer' ? 'answered' : 'refused', request_id: wrongRequest ? 'other-request' : receipt.request_id, response_schema: 'chat_response_v1', response };
      let durable = state;
      await page.route('**/*', route => {
        const pathname = new URL(route.request().url()).pathname;
        if (pathname.startsWith('/api/')) {
          if (route.request().method() === 'POST') return route.fulfill({ status: 202, contentType: 'application/json', body: JSON.stringify({ data: receipt }) });
          fakeGets++;
          return route.fulfill({ status: denied ? 403 : 200, contentType: 'application/json', body: JSON.stringify({ data: pathname.includes('/jobs/') ? { id: receipt.job_id, request_id: receipt.request_id, state: durable, answer_id: durable === 'succeeded' ? answer.id : null } : answer }) });
        }
        return route.fulfill({ contentType: 'text/html', body: '<html><body><button aria-label="Send message">Send</button><article class="user-message" data-message-id="fixture-user"></article></body></html>' });
      });
      await page.goto('http://127.0.0.1:59999/observer-fixture');
      if (integrated) await page.evaluate(() => document.querySelector('button').addEventListener('click', () => { void fetch('/api/v1/sessions/fixture-session/messages', { method: 'POST' }); }));
      const observer = integrated ? null : await armTerminalObserver(page, { pollMs: 25, frontendRoot });
      if (!integrated) await page.getByRole('button', { name: 'Send message' }).click();
      const html = await renderExpectedProse(response, frontendRoot);
      const show = async (id = answer.id, value = html) => page.evaluate(({ id, html }) => {
        document.querySelector('.assistant-message')?.remove();
        const article = document.createElement('article'); article.className = 'assistant-message'; article.dataset.answerId = id;
        article.innerHTML = '<div class="prose">' + html + '</div>'; document.body.append(article);
      }, { id, html: value });
      return { page, observer, show, html, setState: value => { durable = value; } };
    }
    {
      const f = await fixture();
      const bad = await f.page.waitForFunction(async () => false, null, { timeout: 1000 });
      assert.equal(await bad.jsonValue(), false); controls.push('original_async_false_predicate_reproduced');
      let settled = false;
      const waiting = f.observer.wait(receipt, 4000).then(value => { settled = true; return value; });
      await f.show('stale-answer'); await f.page.waitForTimeout(100); assert.equal(settled, false);
      await f.show('fixture-answer', '<p>Complete body <button class="citation" aria-label="Open source 1">[1]</button>.</p>');
      await f.page.waitForTimeout(100); assert.equal(settled, false);
      controls.push('durable_success_wrong_id_and_truncated_matching_citation_do_not_complete');
      await f.show('fixture-answer', '<p><strong>Complete</strong> body <button class="citation" aria-label="Open source 2">[1]</button>. Final sentence.</p>');
      await f.page.waitForTimeout(100); assert.equal(settled, false); controls.push('wrong_citation_identity_rejected');
      await f.show('fixture-answer', '<p><strong>Complete</strong> body <button class="citation" aria-label="Open source 1">[1]</button>.<span style="display:none"> Final sentence.</span></p>');
      await f.page.waitForTimeout(100); assert.equal(settled, false); controls.push('hidden_final_text_does_not_complete');
      await f.show(); const result = await waiting;
      assert.equal(result.kind, 'answer_displayed'); assert.ok(result.elapsed_ms >= 200);
      assert.ok(result.prose.includes('Final sentence.')); controls.push('complete_durable_answer_waits_for_full_render');
      await f.observer.dispose(); await f.observer.dispose();
      assert.equal(await f.page.evaluate(() => window.__terminalObserver112.active), false);
      await f.page.close(); controls.push('idempotent_disposal_after_terminal');
    }
    {
      const f = await fixture({ state: 'running' }); await f.show();
      let settled = false; const waiting = f.observer.wait(receipt, 3000).then(value => { settled = true; return value; });
      await f.page.waitForTimeout(150); assert.equal(settled, false);
      f.setState('succeeded'); assert.equal((await waiting).kind, 'answer_displayed');
      await f.observer.dispose(); await f.page.close(); controls.push('dom_before_durable_commit_does_not_complete');
    }
    {
      const f = await fixture({ type: 'refusal' }); const waiting = f.observer.wait(receipt, 3000); await f.show();
      const value = await waiting; assert.equal(value.kind, 'refusal_displayed'); assert.deepEqual(value.citations, []);
      await f.observer.dispose(); await f.page.close(); controls.push('refusal_is_durable_visible_terminal');
    }
    {
      const f = await fixture({ state: 'failed' }); let settled = false;
      const waiting = f.observer.wait(receipt, 3000).then(value => { settled = true; return value; });
      await f.page.evaluate(() => { document.querySelector('.user-message').innerHTML = '<span class="message-state">Queued</span>'; });
      await f.page.waitForTimeout(100); assert.equal(settled, false);
      await f.page.evaluate(() => { document.querySelector('.user-message').innerHTML = '<span class="message-state">Response failed</span>'; });
      const value = await waiting; assert.equal(value.kind, 'job_failure_displayed'); assert.equal(value.answer_or_refusal_ms, null);
      await f.observer.dispose(); await f.page.close(); controls.push('failure_requires_matching_visible_owner_state_and_is_not_answer');
    }
    for (const [options, pattern, label] of [
      [{ denied: true }, /OBSERVATION_DENIED/, 'denied_observation_stops_without_retry'],
      [{ wrongRequest: true }, /DURABLE_ANSWER_IDENTITY_OR_SHAPE_MISMATCH/, 'wrong_request_rejected']
    ]) {
      const f = await fixture(options); const before = fakeGets;
      await assert.rejects(f.observer.wait(receipt, 3000), pattern);
      const after = fakeGets; await f.page.waitForTimeout(100); assert.equal(fakeGets, after);
      if (options.denied) assert.equal(after - before, 1);
      await f.observer.dispose(); await f.page.close(); controls.push(label);
    }
    {
      const f = await fixture({ integrated: true });
      const waiting = observeOneSubmission(f.page, 'fixture-session', { pollMs: 25, frontendRoot, timeoutMs: 3000 });
      await f.page.waitForTimeout(150); await f.show();
      const value = await waiting; assert.equal(value.terminal.kind, 'answer_displayed');
      assert.equal(await f.page.evaluate(() => window.__terminalObserver112.active), false);
      await f.page.close(); controls.push('integrated_arm_send_accepted_durable_full_dom_dispose');
    }
    {
      const f = await fixture(); const waiting = f.observer.wait(receipt, 3000);
      await f.page.waitForFunction(() => !!window.__terminalObserver112.expected);
      const immediate = await f.page.evaluate(html => new Promise(resolve => {
        const article = document.createElement('article'); article.className = 'assistant-message'; article.dataset.answerId = 'fixture-answer';
        article.innerHTML = '<div class="prose">' + html + '</div>'; document.body.append(article);
        requestAnimationFrame(() => {
          const progress = document.createElement('div'); progress.className = 'generation-status'; document.body.append(progress);
          requestAnimationFrame(() => { progress.remove(); queueMicrotask(() => resolve(window.__terminalObserver112.terminal)); });
        });
      }), f.html);
      assert.equal(immediate, null); assert.equal((await waiting).kind, 'answer_displayed');
      await f.page.close(); controls.push('valid_invalid_restored_candidate_requires_new_stable_frames');
    }
    {
      const f = await fixture({ state: 'running' });
      await assert.rejects(f.observer.wait(receipt, 0), /INVALID_TIMEOUT/);
      assert.equal(await f.page.evaluate(() => window.__terminalObserver112.active), false);
      await f.page.close(); controls.push('zero_timeout_rejected_and_disposed');
    }
    {
      const f = await fixture({ state: 'running' });
      await assert.rejects(f.observer.wait(receipt, 150), /Timeout|TIMEOUT/);
      assert.equal(await f.page.evaluate(() => window.__terminalObserver112.terminal), null);
      assert.equal(await f.page.evaluate(() => window.__terminalObserver112.active), false);
      await f.observer.dispose(); const count = fakeGets; await f.page.waitForTimeout(100); assert.equal(fakeGets, count);
      await f.page.close(); controls.push('timeout_censors_time_and_disposes_polling');
    }
    console.log(JSON.stringify({ status: 'PASS', controls, fake_gets: fakeGets, real_http: 0, provider_calls: 0, database_calls: 0, native111_time_recovered: false }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error.stack); process.exitCode = 1; });
