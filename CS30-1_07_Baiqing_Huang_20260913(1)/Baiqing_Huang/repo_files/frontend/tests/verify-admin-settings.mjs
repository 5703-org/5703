import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import { randomUUID } from 'node:crypto';

const runId = new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-');
const phase = process.env.ADMIN_UI_PHASE || 'settings';
const output = `../artifacts/reports/frontend/admin-settings/${runId}`;
await fs.mkdir(output, { recursive: true });
const secrets = [process.env.TEST_ACCOUNT_PASSWORD || 'Passw0rd!'];
const sanitize = value => secrets.reduce((text, secret) => secret ? text.replaceAll(secret, '[redacted]') : text, String(value)).replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi, 'Bearer [redacted]').replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, '[redacted token]');
const record = { passed: false, started_at: new Date().toISOString(), phase, scope: 'Actual browser with real API and persisted records; no request interception. Mock connection checks are explicitly labelled. Existing users, conversations and corpus sources are preserved.', checks: [], screenshots: [], errors: [] };
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
const context = await browser.newContext({ baseURL: process.env.FRONTEND_URL || 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
page.on('pageerror', error => record.errors.push(sanitize(error.stack || error)));
let restoreConfiguration = null;
let activationMutationStarted = false;

async function api(path, method = 'GET', data) {
  const token = await page.evaluate(() => sessionStorage.getItem('cs30.access-token'));
  const response = await page.request.fetch(`/api/v1${path}`, { method, data, headers: { Authorization: `Bearer ${token}` }, timeout: 90000 });
  const body = await response.json();
  if (!response.ok()) throw new Error(`${method} ${path}: ${response.status()} ${body.error?.code || 'ERROR'} ${body.error?.message || ''}`);
  return body.data;
}
async function responseFor(path, action) {
  const response = page.waitForResponse(value => value.request().method() === 'POST' && new URL(value.url()).pathname === `/api/v1${path}`, { timeout: 90000 });
  await action();
  const value = await response; const body = await value.json();
  expect(value.ok(), body.error?.code || path).toBe(true);
  return body.data;
}
async function login() {
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill(process.env.TEST_ADMIN_EMAIL || 'admin@example.com');
  await page.getByLabel('Password', { exact: true }).fill(secrets[0]);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeVisible();
}
async function capture(name, target) {
  if (target) await target.scrollIntoViewIfNeeded();
  const bounds = await page.evaluate(() => ({ width: innerWidth, height: innerHeight, scrollWidth: document.documentElement.scrollWidth, bodyWidth: document.body.scrollWidth, elements: [...document.querySelectorAll('.topbar,.admin-navigation,.content-page,input,select,.model-test-result,.record')].filter(node => node.getClientRects().length > 0).map(node => { const rect = node.getBoundingClientRect(); return { tag: node.tagName, class: node.className, left: rect.left, right: rect.right }; }) }));
  expect(bounds.scrollWidth).toBeLessThanOrEqual(bounds.width + 1); expect(bounds.bodyWidth).toBeLessThanOrEqual(bounds.width + 1);
  for (const item of bounds.elements) { expect(item.left, `${name}/${item.tag}`).toBeGreaterThanOrEqual(-1); expect(item.right, `${name}/${item.tag}`).toBeLessThanOrEqual(bounds.width + 1); }
  if (target) { const box = await target.boundingBox(); expect(box).toBeTruthy(); expect(box.y).toBeGreaterThanOrEqual(-1); expect(box.y + box.height).toBeLessThanOrEqual(bounds.height + 1); }
  await page.screenshot({ path: `${output}/${name}.png` }); record.screenshots.push({ name: `${name}.png`, bounds });
}
async function credentialAccepted(email, password) {
  const response = await page.request.post('/api/v1/auth/login', { data: { email, password } });
  // Do not record token bodies, headers, passwords or browser storage.
  return { accepted: response.ok(), status: response.status() };
}
async function checkAccounts() {
  const suffix = Date.now(); const email = `ui-admin-${suffix}@example.com`; const name = `UI admin verification ${suffix}`;
  const initialPassword = `Initial-${randomUUID()}`; const nextPassword = `Updated-${randomUUID()}`; secrets.push(initialPassword, nextPassword);
  await page.goto('/admin/accounts'); await expect(page.getByRole('heading', { name: 'Accounts', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  let dialog = page.getByRole('dialog');
  await dialog.getByLabel('Full name').fill(name); await dialog.getByLabel('Email', { exact: true }).fill(email); await dialog.getByLabel('Initial password').fill(initialPassword);
  const created = await responseFor('/admin/users', () => dialog.getByRole('button', { name: 'Create account', exact: true }).click());
  await expect(dialog).toHaveCount(0); expect(created.email).toBe(email); expect(created.role).toBe('student');
  await page.getByLabel('Find an account').fill(email);
  const row = page.locator('.record').filter({ has: page.getByRole('heading', { name, exact: true }) });
  await expect(row).toBeVisible(); expect((await credentialAccepted(email, initialPassword)).accepted).toBe(true);
  await capture('accounts-created-1440', row);
  await row.getByRole('button', { name: 'Reset password' }).click(); dialog = page.getByRole('dialog');
  await dialog.getByLabel('New password', { exact: true }).fill(nextPassword); await dialog.getByLabel('Confirm new password').fill(nextPassword);
  await dialog.getByRole('button', { name: 'Reset password', exact: true }).click(); await expect(dialog).toHaveCount(0);
  const oldLogin = await credentialAccepted(email, initialPassword); const newLogin = await credentialAccepted(email, nextPassword); expect(oldLogin.accepted).toBe(false); expect(newLogin.accepted).toBe(true);
  await row.getByRole('button', { name: 'Deactivate', exact: true }).click(); await page.getByRole('dialog').getByRole('button', { name: 'Deactivate account', exact: true }).click();
  await expect(row.locator('.record-status')).toHaveText('Deactivated'); const disabledLogin = await credentialAccepted(email, nextPassword); expect(disabledLogin.accepted).toBe(false);
  await page.setViewportSize({ width: 390, height: 844 }); await capture('accounts-deactivated-390', row);
  await row.getByRole('button', { name: 'Restore access', exact: true }).click(); await page.getByRole('dialog').getByRole('button', { name: 'Restore access', exact: true }).click();
  await expect(row.locator('.record-status')).toHaveText('Active'); expect((await credentialAccepted(email, nextPassword)).accepted).toBe(true);
  const saved = (await api('/admin/users')).find(user => user.id === created.id); expect(saved.version).toBe(created.version + 3);
  record.checks.push({ check: 'account_create_reset_deactivate_restore', passed: true, user_id: created.id, email, final_version: saved.version, old_password_login_status: oldLogin.status, new_password_login_status: newLogin.status, disabled_login_status: disabledLogin.status });
}
async function checkSettings() {
  await page.setViewportSize({ width: 1440, height: 1000 }); await page.goto('/admin/models');
  await expect(page.getByRole('button', { name: 'New configuration' })).toBeEnabled(); const before = await api('/admin/model-configurations');
  await page.getByRole('button', { name: 'New configuration' }).click(); await page.getByLabel('Provider preset').selectOption('mock');
  await page.getByLabel('Name', { exact: true }).fill(`UI mock check ${runId}`);
  const saved = await responseFor('/admin/model-configurations', () => page.getByRole('button', { name: 'Save configuration', exact: true }).click());
  await expect(page.getByRole('button', { name: 'Enable tested version' })).toBeDisabled();
  const tested = await responseFor(`/admin/model-configurations/${saved.id}/test`, () => page.getByRole('button', { name: 'Test connection' }).click());
  expect(tested.status).toBe('passed'); expect(tested.model_mode).toBe('mock'); await expect(page.getByText('Mock check passed')).toBeVisible();
  await capture('models-mock-test-1440', page.getByRole('status', { name: 'Latest connection test' }));
  await page.getByRole('button', { name: 'New configuration' }).click(); await page.getByLabel('Name', { exact: true }).fill(`UI network failure ${runId}`); await page.getByLabel('Model name').fill('unreachable-ui-verification'); await page.getByLabel('Base URL').fill('http://127.0.0.1:9/v1');
  await page.getByText('Advanced settings', { exact: true }).click(); await page.getByLabel('Timeout (seconds)').fill('2');
  const unreachable = await responseFor('/admin/model-configurations', () => page.getByRole('button', { name: 'Save configuration', exact: true }).click());
  const failed = await responseFor(`/admin/model-configurations/${unreachable.id}/test`, () => page.getByRole('button', { name: 'Test connection' }).click());
  expect(failed.status).toBe('failed'); await expect(page.getByText('Connection test failed')).toBeVisible(); await expect(page.getByRole('button', { name: 'Enable tested version' })).toBeDisabled();
  await page.setViewportSize({ width: 390, height: 844 }); await capture('models-network-failure-390', page.getByRole('status', { name: 'Latest connection test' }));
  const after = await api('/admin/model-configurations'); expect(after.active_configuration_id).toBe(before.active_configuration_id); expect(after.active_version).toBe(before.active_version);
  record.checks.push({ check: 'saved_configuration_test_outcomes', passed: true, mock_configuration_id: saved.id, mock_test_id: tested.id, failed_configuration_id: unreachable.id, failed_test_id: failed.id, failure_code: failed.diagnostic_code, active_selection_unchanged: true });
}
async function checkDiagnostics() {
  await page.goto('/admin/failures'); await expect(page.getByRole('heading', { name: 'Response diagnostics', exact: true })).toBeVisible();
  await expect(page.getByText('Loading response diagnostics…')).toHaveCount(0); await expect(page.getByRole('alert')).toHaveCount(0);
  await capture('diagnostics-390', page.getByRole('heading', { name: 'Response diagnostics', exact: true }));
  const result = await api('/admin/failures?limit=50&offset=0');
  if (result.items.length) {
    await page.getByRole('button', { name: 'Inspect response' }).first().click(); const dialog = page.getByRole('dialog');
    await expect(dialog.getByText('Loading the recorded trace…')).toHaveCount(0); await expect(dialog.getByText('Actually cited')).toBeVisible();
    await capture('diagnostic-detail-390', dialog.getByText('Actually cited')); await dialog.getByRole('button', { name: 'Close response diagnostics' }).click();
  }
  await page.setViewportSize({ width: 1440, height: 1000 }); await capture('diagnostics-1440', page.getByRole('heading', { name: 'Response diagnostics', exact: true }));
  record.checks.push({ check: 'real_diagnostics_list_detail', passed: true, total: result.total, detail_checked: result.items.length > 0 });
}
async function checkActivation() {
  const id = process.env.TEST_MODEL_CONFIGURATION_ID;
  if (!id || process.env.ALLOW_MODEL_ACTIVATION !== '1') throw new Error('The activation phase requires an explicitly coordinated model ID and activation window.');
  const before = await api('/admin/model-configurations'); expect(before.active_configuration_id).toBe(id); restoreConfiguration = before.items.find(item => item.id === id); expect(restoreConfiguration?.latest_test?.status).toBe('passed');
  await page.goto('/admin/models'); await expect(page.getByLabel('Name', { exact: true })).toHaveValue(restoreConfiguration.name);
  await page.getByLabel('Name', { exact: true }).fill(`UI live version verification ${runId}`);
  const successor = await responseFor(`/admin/model-configurations/${id}/versions`, () => page.getByRole('button', { name: 'Save new version', exact: true }).click());
  expect(successor.has_api_key).toBe(restoreConfiguration.has_api_key); expect(successor.config).toEqual(restoreConfiguration.config);
  const tested = await responseFor(`/admin/model-configurations/${successor.id}/test`, () => page.getByRole('button', { name: 'Test connection', exact: true }).click());
  expect(tested.status).toBe('passed'); expect(tested.model_mode).toBe('live');
  activationMutationStarted = true;
  const enabled = await responseFor(`/admin/model-configurations/${successor.id}/activate`, () => page.getByRole('button', { name: 'Enable tested version', exact: true }).click());
  expect(enabled.active_configuration_id).toBe(successor.id); await expect(page.getByRole('button', { name: 'Enabled', exact: true })).toBeVisible(); await expect(page.getByText('Live model', { exact: true })).toBeVisible();
  await capture('models-live-enabled-1440', page.getByRole('button', { name: 'Enabled', exact: true }));
  await page.getByText('Earlier saved versions', { exact: true }).click(); await page.getByRole('button', { name: `${restoreConfiguration.name} · version ${restoreConfiguration.revision}`, exact: true }).click();
  const restored = await responseFor(`/admin/model-configurations/${id}/activate`, () => page.getByRole('button', { name: 'Enable tested version', exact: true }).click());
  expect(restored.active_configuration_id).toBe(id); expect(restored.active_version).toBe(before.active_version + 2); activationMutationStarted = false;
  await page.setViewportSize({ width: 390, height: 844 }); await capture('models-live-restored-390', page.getByRole('button', { name: 'Enabled', exact: true }));
  record.checks.push({ check: 'live_save_test_enable_restore', passed: true, original_configuration_id: id, successor_configuration_id: successor.id, test_id: tested.id, final_active_version: restored.active_version });
}
async function checkCitations() {
  await page.goto('/chat');
  const question = process.env.UI_CITATION_QUESTION || 'What is photosynthesis?';
  const reuse = process.env.UI_REUSE_SAVED_QUESTION === '1';
  if (reuse) {
    const existing = (await api('/sessions?status=active')).find(session => session.title === question);
    if (!existing) throw new Error('The exact saved question was not found; do not generate a replacement.');
    await page.goto(`/chat/${existing.id}`);
  } else {
    await page.getByRole('textbox', { name: 'Message Learning Assistant' }).fill(question);
    await page.getByRole('button', { name: 'Send message', exact: true }).click();
  }
  await expect(page.locator('[data-answer-id]')).toHaveCount(1, { timeout: 180000 });
  const answerId = await page.locator('[data-answer-id]').getAttribute('data-answer-id');
  const answer = await api(`/answers/${answerId}`); expect(answer.model_mode).toBe('live'); expect(answer.response.response_type).toBe('answer');
  const cited = [...new Set(answer.response.citations)]; expect(cited.length).toBeGreaterThan(0);
  record.answer_observation = { answer_id: answer.id, request_id: answer.request_id, session_path: new URL(page.url()).pathname, question, reused_saved_answer: reuse, submitted: answer.evidence.length, cited: cited.length };
  await expect(page.getByRole('button', { name: `Sources ${cited.length}`, exact: true })).toBeVisible();
  await expect(page.getByText('Live model', { exact: true }).first()).toBeVisible();
  await capture('live-chat-citations-1440', page.getByRole('button', { name: `Sources ${cited.length}`, exact: true }));
  const sessionPath = new URL(page.url()).pathname;
  await page.getByRole('button', { name: `Sources ${cited.length}`, exact: true }).focus();
  await page.keyboard.press('Enter');
  let dialog = page.getByRole('dialog'); const original = await api(`/answers/${answer.id}/evidence/${cited[0]}`);
  await expect(dialog.locator('.source-passage')).toHaveText(original.text);
  if (cited.length > 1) await expect(dialog.locator('.source-tabs .button')).toHaveCount(cited.length);
  await expect(dialog.getByText('OpenStax / Rice University · Access for free at openstax.org')).toBeVisible();
  await expect(dialog.getByRole('link', { name: 'View original source' })).toHaveAttribute('href', original.source_url);
  await page.setViewportSize({ width: 390, height: 844 }); await capture('live-cited-source-390', dialog.getByRole('link', { name: 'View original source' }));
  for (let index = 0; index < 8; index++) {
    await page.keyboard.press('Tab');
    const observation = await page.evaluate(() => ({ tag: document.activeElement?.tagName, within_dialog: !!document.activeElement?.closest('dialog') }));
    (record.keyboard_observations ||= []).push({ index, ...observation });
    expect(observation.within_dialog).toBe(true);
  }
  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole('button', { name: `Sources ${cited.length}`, exact: true })).toBeFocused();
  await page.goto('/admin/failures'); await page.getByLabel('Outcome').selectOption('answered');
  const row = page.locator(`[data-request-id="${answer.request_id}"]`); await expect(row).toBeVisible();
  const diagnostic = await api(`/admin/failures/${answer.request_id}`);
  expect(diagnostic.counts.cited).toBe(cited.length); expect(diagnostic.counts.submitted).toBe(answer.evidence.length);
  await row.getByRole('button', { name: 'Inspect response' }).click(); dialog = page.getByRole('dialog');
  await expect(dialog.getByText('Actually cited')).toBeVisible(); await capture('live-answer-diagnostic-390', dialog.getByText('Actually cited'));
  await dialog.getByRole('button', { name: 'Close response diagnostics' }).click();
  await page.goto(sessionPath); await expect(page.locator('[data-answer-id]')).toHaveAttribute('data-answer-id', answerId);
  await expect(page.getByRole('button', { name: `Sources ${cited.length}`, exact: true })).toBeVisible();
  record.checks.push({ check: 'live_chat_cited_source_and_admin_layers', passed: true, question, answer_id: answer.id, request_id: answer.request_id, session_path: sessionPath, counts: diagnostic.counts, displayed_sources: cited.length, exact_source_text: true, source_url: original.source_url, text_hash: original.text_hash, keyboard_open_focus_trap_escape_return: true, reload_preserved_answer: true });
}
try {
  await login();
  if (phase === 'activation') await checkActivation();
  else if (phase === 'citations') await checkCitations();
  else { await checkAccounts(); await checkSettings(); await checkDiagnostics(); }
  expect(record.errors).toHaveLength(0); record.passed = true;
} catch (error) { record.errors.push(sanitize(error.stack || error)); }
finally {
  if (activationMutationStarted && restoreConfiguration) {
    try {
      const current = await api('/admin/model-configurations');
      if (current.active_configuration_id !== restoreConfiguration.id) await api(`/admin/model-configurations/${restoreConfiguration.id}/activate`, 'POST', { test_id: restoreConfiguration.latest_test.id, expected_active_version: current.active_version });
      record.cleanup_restored = (await api('/admin/model-configurations')).active_configuration_id === restoreConfiguration.id;
    } catch (error) { record.cleanup_error = sanitize(error.stack || error); }
  }
  record.finished_at = new Date().toISOString(); await fs.writeFile(`${output}/verification.json`, JSON.stringify(record, null, 2)); await browser.close();
}
console.log(JSON.stringify({ passed: record.passed, phase, output, checks: record.checks.length, errors: record.errors.length }));
if (!record.passed) process.exitCode = 1;
