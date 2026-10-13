'use strict';
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const fs = require('node:fs');
const { createHash } = require('node:crypto');
const MARKDOWN_CONTRACT_SHA256 = '3edc21990e972fae30acc2b22fea1ddee014e8cc7e11b93c67dfa8d6081966d4';

// Match SafeMarkdown's installed parser and citation rendering, rather than
// accepting a nonempty prefix with the right number of source buttons.
async function renderExpectedProse(response, frontendRoot) {
  const resolve = name => require.resolve(name, { paths: [frontendRoot] });
  const React = require(resolve('react'));
  const { renderToStaticMarkup } = require(resolve('react-dom/server'));
  const load = async name => (await import(pathToFileURL(resolve(name)).href)).default;
  const [Markdown, gfm, math, katex] = await Promise.all([
    load('react-markdown'), load('remark-gfm'), load('remark-math'), load('rehype-katex')
  ]);
  const ids = response.citations;
  const citationPlugin = () => tree => {
    const visit = node => {
      if (!node.children || ['link', 'code', 'inlineCode'].includes(node.type)) return;
      node.children = node.children.flatMap(child => {
        if (child.type !== 'text' || !child.value) { visit(child); return [child]; }
        const result = []; let end = 0;
        for (const match of child.value.matchAll(/\[(ev_\d{3,})\]/g)) {
          if (!ids.includes(match[1])) continue;
          if (match.index > end) result.push({ type: 'text', value: child.value.slice(end, match.index) });
          result.push({ type: 'link', url: '#evidence-' + match[1],
            children: [{ type: 'text', value: '[' + (ids.indexOf(match[1]) + 1) + ']' }] });
          end = match.index + match[0].length;
        }
        if (!end) return [child];
        if (end < child.value.length) result.push({ type: 'text', value: child.value.slice(end) });
        return result;
      });
    }; visit(tree);
  };
  const components = {
    a: ({ href, children }) => href?.startsWith('#evidence-') && ids.includes(href.slice(10))
      ? React.createElement('button', { className: 'citation', 'aria-label': 'Open source ' + String(children).replace(/[\[\]]/g, '') }, children)
      : React.createElement('a', { href }, children),
    img: ({ alt }) => React.createElement('span', null, '[Image: ' + (alt || 'No description provided') + ']')
  };
  return renderToStaticMarkup(React.createElement(Markdown, {
    skipHtml: true, remarkPlugins: [gfm, math, citationPlugin],
    rehypePlugins: [[katex, { trust: false, throwOnError: false }]], components
  }, response.answer_text));
}

// Verification helper, not product rendering or model orchestration.
async function armTerminalObserver(page, { pollMs = 150, frontendRoot = path.resolve(__dirname, '../../frontend') } = {}) {
  if (!Number.isInteger(pollMs) || pollMs < 25) throw new Error('INVALID_POLL_INTERVAL');
  const renderer = fs.readFileSync(path.join(frontendRoot, 'src/Markdown.tsx'));
  if (createHash('sha256').update(renderer).digest('hex') !== MARKDOWN_CONTRACT_SHA256)
    throw new Error('RENDERER_CONTRACT_CHANGED_REVIEW_HELPER_BEFORE_SEND');
  // Resolve/preload the existing renderer before Send, outside the clock.
  await renderExpectedProse({ answer_text: '', citations: [] }, frontendRoot);
  await page.evaluate(interval => {
    if (window.__terminalObserver112?.active) throw new Error('OBSERVER_ALREADY_ACTIVE');
    const state = window.__terminalObserver112 = {
      active: true, send: null, first: null, complete: null, failed: null,
      receipt: null, job: null, durable: null, terminal: null,
      candidate: null, frame: null, polling: false, controller: null, expected: null,
      observation_errors: 0, authentication_exported: false
    };
    const visible = node => !!node && getComputedStyle(node).visibility !== 'hidden' &&
      getComputedStyle(node).display !== 'none' && node.getBoundingClientRect().width > 0 &&
      node.getBoundingClientRect().height > 0;
    const progressing = () => !!document.querySelector('.generation-status, button[aria-label="Stop generation"]');
    const invalidate = () => {
      state.candidate = null;
      if (state.frame !== null) cancelAnimationFrame(state.frame);
      state.frame = null;
    };
    const probe = () => {
      if (!state.active || state.terminal || !Number.isFinite(state.send) || !state.receipt) return;
      if (state.job && ['failed', 'cancelled'].includes(state.job.state)) {
        const owner = document.querySelector(`.user-message[data-message-id="${CSS.escape(state.receipt.user_message_id)}"]`);
        const failure = owner?.querySelector('.message-state');
        const expectedFailure = state.job.state === 'cancelled' ? 'Generation stopped' : 'Response failed';
        if (visible(failure) && failure.innerText.trim() === expectedFailure && !progressing()) {
          state.failed = performance.now();
          state.terminal = { kind: 'job_failure_displayed', job_state: state.job.state,
            elapsed_ms: state.failed - state.send, answer_or_refusal_ms: null };
        }
        return;
      }
      if (!state.durable || !state.expected || state.job?.state !== 'succeeded' || progressing()) { invalidate(); return; }
      const node = document.querySelector(`.assistant-message[data-answer-id="${CSS.escape(state.durable.id)}"]`);
      const prose = node?.querySelector('.prose');
      if (!visible(prose) || !prose.textContent.trim()) { invalidate(); return; }
      const citations = [...node.querySelectorAll('button.citation')].map(button => button.getAttribute('aria-label'));
      if (prose.textContent !== state.expected.text || prose.innerText !== state.expected.visibleText ||
          JSON.stringify(citations) !== JSON.stringify(state.expected.citations)) { invalidate(); return; }
      const signature = JSON.stringify([node.dataset.answerId, prose.textContent, citations]);
      if (state.candidate !== signature) {
        state.candidate = signature;
        if (state.frame !== null) cancelAnimationFrame(state.frame);
        state.frame = requestAnimationFrame(() => {
          state.frame = requestAnimationFrame(() => { state.frame = null; probe(); });
        });
        return;
      }
      // A matching durable DTO, atomic AnswerView render and stable frame join.
      if (state.frame !== null) return;
      state.first = performance.now(); state.complete = performance.now();
      state.terminal = { kind: state.durable.response.response_type + '_displayed',
        answer_id: state.durable.id, request_id: state.durable.request_id,
        elapsed_ms: state.complete - state.send, answer_or_refusal_ms: state.complete - state.send,
        citations, prose: prose.innerText, response: state.durable.response,
        boundary: 'durable_record_and_matching_stable_terminal_dom_v1' };
    };
    const observe = async path => {
      const response = await fetch('/api/v1' + path, { signal: state.controller.signal,
        headers: { Authorization: `Bearer ${sessionStorage.getItem('cs30.access-token')}` } });
      if ([401, 403].includes(response.status)) {
        state.terminal = { kind: 'observation_denied', path: '/api/v1' + path,
          status: response.status, answer_or_refusal_ms: null };
        return null;
      }
      if (!response.ok) { state.observation_errors += 1; return null; }
      return (await response.json()).data;
    };
    state.poll = async () => {
      if (!state.active || state.terminal || state.polling || !state.receipt || !Number.isFinite(state.send)) return;
      state.polling = true; state.controller = new AbortController();
      try {
        const job = await observe('/jobs/' + encodeURIComponent(state.receipt.job_id));
        if (!state.active || state.terminal || !job) return;
        if (job.id !== state.receipt.job_id || job.request_id !== state.receipt.request_id)
          throw new Error('DURABLE_JOB_IDENTITY_MISMATCH');
        state.job = { id: job.id, state: job.state, answer_id: job.answer_id };
        if (job.state === 'succeeded' && !state.durable) {
          if (typeof job.answer_id !== 'string' || !job.answer_id) throw new Error('SUCCEEDED_JOB_WITHOUT_ANSWER');
          const answer = await observe('/answers/' + encodeURIComponent(job.answer_id));
          if (!state.active || state.terminal || !answer) return;
          if (answer.id !== job.answer_id || answer.request_id !== state.receipt.request_id || answer.job_id !== job.id ||
              answer.response_schema !== 'chat_response_v1' ||
              !['answer', 'refusal'].includes(answer.response?.response_type) ||
              answer.status !== (answer.response.response_type === 'answer' ? 'answered' : 'refused') ||
              typeof answer.response.answer_text !== 'string' || !answer.response.answer_text.trim() ||
              !Array.isArray(answer.response.citations)) throw new Error('DURABLE_ANSWER_IDENTITY_OR_SHAPE_MISMATCH');
          if (answer.response.response_type === 'refusal' && answer.response.citations.length)
            throw new Error('REFUSAL_CITATION_INVARIANT');
          state.durable = { id: answer.id, request_id: answer.request_id,
            response_schema: answer.response_schema, response: answer.response };
        }
        probe();
      } catch (error) {
        if (!state.active || error.name === 'AbortError') return;
        if (error.message.startsWith('DURABLE_') || error.message === 'SUCCEEDED_JOB_WITHOUT_ANSWER' || error.message === 'REFUSAL_CITATION_INVARIANT')
          state.terminal = { kind: 'protocol_failure', code: error.message, answer_or_refusal_ms: null };
        else state.observation_errors += 1;
      } finally { state.polling = false; state.controller = null; }
    };
    state.click = event => {
      if (!state.active || Number.isFinite(state.send) || !(event.target instanceof Element)) return;
      if (event.target.closest('button')?.getAttribute('aria-label') === 'Send message') state.send = performance.now();
    };
    document.addEventListener('click', state.click, { capture: true });
    state.mutations = new MutationObserver(probe);
    state.mutations.observe(document.documentElement, { subtree: true, childList: true, attributes: true, characterData: true });
    state.interval = setInterval(state.poll, interval);
  }, pollMs);
  let disposed = false;
  return {
    async wait(receipt, timeoutMs = 210000) {
      try {
      if (!Number.isInteger(timeoutMs) || timeoutMs < 1) throw new Error('INVALID_TIMEOUT');
      for (const key of ['job_id', 'request_id', 'user_message_id'])
        if (typeof receipt?.[key] !== 'string' || !receipt[key]) throw new Error('INVALID_ACCEPTED_RECEIPT');
      await page.evaluate(value => {
        const state = window.__terminalObserver112;
        if (!state?.active || state.receipt) throw new Error('OBSERVER_BINDING_INVALID');
        state.receipt = value; void state.poll();
      }, { job_id: receipt.job_id, request_id: receipt.request_id, user_message_id: receipt.user_message_id });
      // Never use an async predicate here: a Promise is immediately truthy.
      const deadline = Date.now() + timeoutMs;
      await page.waitForFunction(() => !!(window.__terminalObserver112?.durable || window.__terminalObserver112?.terminal), null, { timeout: timeoutMs, polling: 50 });
      const durable = await page.evaluate(() => window.__terminalObserver112.durable);
      if (durable) {
        const html = await renderExpectedProse(durable.response, frontendRoot);
        await page.evaluate(value => {
          const reference = document.createElement('div'); reference.innerHTML = value;
          reference.className = 'prose'; reference.style.position = 'absolute'; reference.style.left = '-10000px';
          document.body.append(reference);
          try {
          const state = window.__terminalObserver112;
          if (!state.active) throw new Error('OBSERVER_DISPOSED_DURING_WAIT');
          state.expected = { text: reference.textContent, visibleText: reference.innerText,
            citations: [...reference.querySelectorAll('button.citation')].map(button => button.getAttribute('aria-label')) };
          } finally { reference.remove(); }
        }, html);
      }
      const remaining = deadline - Date.now();
      if (remaining <= 0) throw new Error('TERMINAL_OBSERVER_TIMEOUT');
      await page.waitForFunction(() => !!window.__terminalObserver112?.terminal, null, { timeout: remaining, polling: 50 });
      const value = await page.evaluate(() => window.__terminalObserver112.terminal);
      if (['observation_denied', 'protocol_failure'].includes(value.kind)) {
        const error = new Error(value.code || `OBSERVATION_DENIED:${value.path}:${value.status}`);
        error.observation = value; throw error;
      }
      if (!Number.isFinite(value.elapsed_ms) || value.elapsed_ms < 0) throw new Error('INVALID_TERMINAL_TIME');
      return value;
      } finally { await this.dispose(); }
    },
    async dispose() {
      if (disposed) return; disposed = true;
      await page.evaluate(() => {
        const state = window.__terminalObserver112;
        if (!state) return;
        state.active = false; clearInterval(state.interval); state.controller?.abort();
        state.mutations.disconnect(); document.removeEventListener('click', state.click, { capture: true });
        if (state.frame !== null) cancelAnimationFrame(state.frame);
      });
    }
  };
}
module.exports = { armTerminalObserver, renderExpectedProse };
