'use strict';
const { armTerminalObserver } = require('./browser_terminal_observer.cjs');

// Call only inside a separately scoped future native journey. This module does
// not log in, read credentials, start services or submit a question on import.
async function observeOneSubmission(page, sessionId, options = {}) {
  const observer = await armTerminalObserver(page, options);
  try {
    const accepted = page.waitForResponse(response => response.request().method() === 'POST' &&
      new URL(response.url()).pathname === `/api/v1/sessions/${sessionId}/messages`, { timeout: 30000 });
    const [response] = await Promise.all([accepted, page.getByRole('button', { name: 'Send message', exact: true }).click()]);
    if (response.status() !== 202) throw new Error('MESSAGE_NOT_ACCEPTED');
    const receipt = (await response.json()).data;
    const terminal = await observer.wait(receipt, options.timeoutMs ?? 210000);
    return { receipt, terminal };
  } finally {
    // Browser closure belongs to the caller after this bounded observation ends.
    await observer.dispose();
  }
}
module.exports = { observeOneSubmission };
