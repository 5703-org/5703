import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';

const originalId = '39483e7f-efbe-42e7-855e-469fd924383e';
const duplicateId = '29f2c946-a664-44f3-bd20-5cb5c886e76a';
const historySession = 'bbc8a01f-6c5d-4670-bdd9-e4551da3299b';
const runId = new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-');
const output = `../artifacts/reports/frontend/openstax-rollback-roundtrip/${runId}`;
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: 'msedge' });
const adminContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1000 } });
const learnerContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' });
const page = await adminContext.newPage();
const learner = await learnerContext.newPage();
const record = { passed: false, executed_at: new Date().toISOString(), original_release_id: originalId, duplicate_release_id: duplicateId, history_session_id: historySession, scope: 'Actual browser A to existing validated duplicate B to A, awaiting completed mutation responses; no new build or source mutation.', checks: {}, page_errors: [] };
const diagnostic = error => String(error.stack || error).replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi, 'Bearer [redacted]');
const inflight = new Set();
page.on('request', request => { if (request.method() === 'POST' && /\/corpus\/releases\/[^/]+\/(activate|rollback)$/.test(request.url())) inflight.add(request); });
page.on('requestfinished', request => inflight.delete(request));
page.on('requestfailed', request => inflight.delete(request));
page.on('pageerror', error => record.page_errors.push(diagnostic(error)));
async function login(target, email) {
  await target.goto('/login');
  await target.getByLabel('Email', { exact: true }).fill(email);
  await target.getByLabel('Password', { exact: true }).fill('Passw0rd!');
  await target.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(target.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeVisible();
}
async function api(target, path, method = 'GET', data) {
  const token = await target.evaluate(() => sessionStorage.getItem('cs30.access-token'));
  const response = await target.request.fetch(`/api/v1${path}`, { method, data, timeout: 120000, headers: { Authorization: `Bearer ${token}` } });
  const body = await response.json();
  expect(response.ok(), JSON.stringify(body.error || response.status())).toBe(true);
  return body.data;
}
async function active() { return (await api(page, '/corpus/releases')).filter(release => release.state === 'active'); }
async function history() { return await api(learner, `/sessions/${historySession}/messages?limit=100`); }
async function selectRelease(release) {
  const node = page.locator('.record').filter({ has: page.getByRole('heading', { name: release.name, exact: true }) });
  const action = release.state === 'validated' ? 'activate' : 'rollback';
  const completed = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/corpus/releases/${release.id}/${action}`), { timeout: 120000 });
  await node.getByRole('button', { name: action === 'activate' ? 'Activate release' : 'Rollback to this release', exact: true }).click();
  const response = await completed;
  await response.finished();
  const receipt = { status: response.status(), data: (await response.json()).data };
  expect(response.status()).toBe(200);
  await expect(node.locator('.record-status')).toHaveText('Active', { timeout: 30000 });
  return receipt;
}
try {
  await login(page, 'admin@example.com');
  await login(learner, 'student2@example.com');
  const releases = await api(page, '/corpus/releases');
  const original = releases.find(release => release.id === originalId);
  const duplicate = releases.find(release => release.id === duplicateId);
  record.before_active = releases.filter(release => release.state === 'active');
  expect(record.before_active.map(release => release.id)).toEqual([originalId]);
  record.duplicate_before = duplicate;
  expect(duplicate.configuration).toEqual(original.configuration);
  for (const key of ['processing_run_ids', 'chunk_ids']) expect([...duplicate.manifest[key]].sort()).toEqual([...original.manifest[key]].sort());
  for (const key of ['embedding_hash', 'embedding_signature', 'configuration_hash', 'content_hash']) expect(duplicate.manifest[key]).toEqual(original.manifest[key]);
  record.history_before = await history();
  expect(record.history_before.items.length).toBeGreaterThanOrEqual(10);
  await page.goto('/admin/corpus');
  record.switch_to_b_response = await selectRelease(duplicate);
  record.during_active = await active();
  expect(record.during_active.map(release => release.id)).toEqual([duplicateId]);
  record.history_during = await history();
  expect(record.history_during).toEqual(record.history_before);
  record.restore_a_response = await selectRelease({ ...original, state: 'retired' });
  record.after_active = await active();
  expect(record.after_active.map(release => release.id)).toEqual([originalId]);
  record.history_after = await history();
  expect(record.history_after).toEqual(record.history_before);
  record.checks = { exact_configuration_runs_chunks_and_vectors: true, completed_http_200_each_mutation: true, one_active_pointer_each_stage: true, complete_saved_history_answers_evidence_unchanged: true };
  record.responsive = [];
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    const node = page.locator('.record').filter({ has: page.getByRole('heading', { name: original.name, exact: true }) });
    await node.scrollIntoViewIfNeeded();
    const geometry = await page.evaluate(() => ({ viewport: innerWidth, html: document.documentElement.scrollWidth, body: document.body.scrollWidth }));
    expect(geometry.html).toBeLessThanOrEqual(width + 1);
    expect(geometry.body).toBeLessThanOrEqual(width + 1);
    record.responsive.push(geometry);
    await page.screenshot({ path: `${output}/restored-release-${width}.png` });
  }
  expect(record.page_errors).toEqual([]);
  record.passed = true;
} catch (error) { record.error = diagnostic(error); }
finally {
  try {
    await expect.poll(() => inflight.size, { timeout: 150000, intervals: [1000] }).toBe(0);
    record.inflight_mutations_before_final_check = inflight.size;
    const current = await active();
    if (current.length !== 1 || current[0].id !== originalId) {
      record.emergency_restore = await api(page, `/corpus/releases/${originalId}/rollback`, 'POST', {});
      record.passed = false;
    }
    record.final_active_ids = (await active()).map(release => release.id);
    expect(record.final_active_ids).toEqual([originalId]);
  } catch (error) { record.restore_error = diagnostic(error); record.passed = false; }
  await fs.writeFile(`${output}/verification.json`, JSON.stringify(record, null, 2));
  await browser.close();
  if (!record.passed) process.exitCode = 1;
  console.log(JSON.stringify({ passed: record.passed, output, final_active_ids: record.final_active_ids, error: record.error, restore_error: record.restore_error }));
}
