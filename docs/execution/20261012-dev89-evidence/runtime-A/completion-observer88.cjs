'use strict';

// Await the evaluated result explicitly; an unresolved Promise is not DOM completion.
function observationTimeout() {
  const error = new Error('COMPLETE_DOM_OBSERVATION_TIMEOUT');
  error.code = 'COMPLETE_DOM_OBSERVATION_TIMEOUT'; return error;
}

async function observeCompletion(page, jobId, { timeout = 210000, interval = 250 } = {}) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    const remaining = Math.max(1, end - Date.now());
    let deadlineTimer; let value;
    try {
      value = await Promise.race([
        new Promise((_, reject) => { deadlineTimer = setTimeout(() => reject(observationTimeout()), remaining); }),
        page.evaluate(async ({ jobId, remaining }) => {
      const clock = window.__journey77;
      if (Number.isFinite(clock?.complete)) return { clock };
      const response = await fetch(`/api/v1/jobs/${jobId}`, {
        headers: { Authorization: `Bearer ${sessionStorage.getItem('cs30.access-token')}` },
        signal: AbortSignal.timeout(remaining)
      });
      if (!response.ok) return { pending: true };
      const job = (await response.json()).data;
      if (['failed', 'cancelled'].includes(job.state))
        return { terminal: { state: job.state, code: job.error?.code || 'UNKNOWN_JOB_FAILURE' } };
      return { pending: true };
        }, { jobId, remaining })
      ]);
    } catch (error) {
      if (Date.now() >= end || ['AbortError', 'TimeoutError'].includes(error?.name)) throw observationTimeout();
      throw error;
    } finally { clearTimeout(deadlineTimer); }
    if (value.terminal) {
      const error = new Error(`NORMAL_JOB_${value.terminal.state.toUpperCase()}:${value.terminal.code}`);
      error.code = value.terminal.code; error.terminal = value.terminal; throw error;
    }
    if (value.clock) {
      const clock = value.clock;
      if (![clock.send, clock.first, clock.complete].every(Number.isFinite)
          || clock.send < 0 || clock.first < clock.send || clock.complete < clock.first || !clock.answer) {
        const error = new Error('INVALID_DOM_CLOCK'); error.code = 'INVALID_DOM_CLOCK'; throw error;
      }
      return clock;
    }
    await new Promise(resolve => setTimeout(resolve, Math.min(interval, Math.max(0, end - Date.now()))));
  }
  throw observationTimeout();
}

module.exports = { observeCompletion };
