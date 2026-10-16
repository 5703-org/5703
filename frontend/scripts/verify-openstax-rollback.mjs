import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';

const baseURL = 'http://127.0.0.1:5173';
const originalId = '39483e7f-efbe-42e7-855e-469fd924383e';
const historySession = 'bbc8a01f-6c5d-4670-bdd9-e4551da3299b';
const runId = new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-');
const output = `../artifacts/reports/frontend/openstax-rollback/${runId}`;
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: 'msedge' });
const adminContext = await browser.newContext({ baseURL, viewport: { width: 1440, height: 1000 } });
const learnerContext = await browser.newContext({ baseURL });
const page = await adminContext.newPage();
const learner = await learnerContext.newPage();
const inflightMutations = new Set();
page.on('request', request => { if (request.method() === 'POST' && /\/corpus\/releases\/[^/]+\/(activate|rollback)$/.test(request.url())) inflightMutations.add(request); });
page.on('requestfinished', request => inflightMutations.delete(request));
page.on('requestfailed', request => inflightMutations.delete(request));
const diagnostic = error => String(error.stack || error).replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi, 'Bearer [redacted]');
const record = { executed_at: new Date().toISOString(), passed: false, original_release_id: originalId, history_session_id: historySession, scope: 'Actual administrator browser A to duplicate validated B to A rollback with identical four official source runs and pinned E5 configuration; no source mutation or semantic-quality claim.', checks: {}, page_errors: [] };
page.on('pageerror', error => record.page_errors.push(error.message));

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
  const result = await response.json();
  expect(response.ok(), JSON.stringify(result.error || response.status())).toBe(true);
  return result.data;
}
async function history() { return await api(learner, `/sessions/${historySession}/messages?limit=100`); }
async function active() { return (await api(page, '/corpus/releases')).filter(release => release.state === 'active'); }

try {
  await login(page, 'admin@example.com');
  await login(learner, 'student2@example.com');
  record.original_active = await active();
  expect(record.original_active).toHaveLength(1);
  expect(record.original_active[0].id).toBe(originalId);
  const original = record.original_active[0];
  record.history_before = await history();
  expect(record.history_before.items.length).toBeGreaterThanOrEqual(10);
  await page.goto('/admin/corpus');
  await page.getByRole('button', { name: 'Build release', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Build corpus release' });
  const releaseName = `Official corpus local rollback verification ${runId}`;
  await dialog.getByLabel('Release name').fill(releaseName);
  await dialog.getByRole('combobox', { name: 'Configuration', exact: true }).selectOption(original.manifest.configuration_id);
  for (const id of original.manifest.processing_run_ids) await dialog.getByRole('checkbox', { name: new RegExp(id) }).check();
  const created = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/corpus/releases'));
  await dialog.getByRole('button', { name: 'Build release', exact: true }).click();
  const createResponse = await created;
  expect(createResponse.status()).toBe(202);
  record.receipt = (await createResponse.json()).data;
  expect(record.receipt.release_id).not.toBe(originalId);
  console.log(JSON.stringify({ stage: 'duplicate_build_queued', release_id: record.receipt.release_id, output }));
  await expect.poll(async () => (await api(page, '/corpus/releases')).find(release => release.id === record.receipt.release_id)?.state, { timeout: 300000, intervals: [1000, 2000, 5000] }).toBe('validated');
  record.duplicate_validated = (await api(page, '/corpus/releases')).find(release => release.id === record.receipt.release_id);
  expect(record.duplicate_validated.configuration).toEqual(original.configuration);
  expect([...record.duplicate_validated.manifest.processing_run_ids].sort()).toEqual([...original.manifest.processing_run_ids].sort());
  expect([...record.duplicate_validated.manifest.chunk_ids].sort()).toEqual([...original.manifest.chunk_ids].sort());
  expect(record.duplicate_validated.manifest.embedding_hash).toBe(original.manifest.embedding_hash);
  expect(record.duplicate_validated.manifest.embedding_signature).toBe(original.manifest.embedding_signature);
  expect(record.duplicate_validated.manifest.configuration_hash).toBe(original.manifest.configuration_hash);
  expect(record.duplicate_validated.manifest.content_hash).toBe(original.manifest.content_hash);
  await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  const duplicateNode = page.locator('.record').filter({ has: page.getByRole('heading', { name: releaseName, exact: true }) });
  const activationCompleted = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/corpus/releases/${record.receipt.release_id}/activate`), { timeout: 120000 });
  await duplicateNode.getByRole('button', { name: 'Activate release', exact: true }).click();
  const activationResponse = await activationCompleted;
  await activationResponse.finished();
  expect(activationResponse.status()).toBe(200);
  record.activation_response = (await activationResponse.json()).data;
  await expect(duplicateNode.locator('.record-status')).toHaveText('Active', { timeout: 30000 });
  record.during_active = await active();
  expect(record.during_active).toHaveLength(1);
  expect(record.during_active[0].id).toBe(record.receipt.release_id);
  record.history_during = await history();
  expect(record.history_during).toEqual(record.history_before);
  const originalNode = page.locator('.record').filter({ has: page.getByRole('heading', { name: original.name, exact: true }) });
  const rollbackCompleted = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/corpus/releases/${originalId}/rollback`), { timeout: 120000 });
  await originalNode.getByRole('button', { name: 'Rollback to this release', exact: true }).click();
  const rollbackResponse = await rollbackCompleted;
  await rollbackResponse.finished();
  expect(rollbackResponse.status()).toBe(200);
  record.rollback_response = (await rollbackResponse.json()).data;
  await expect(originalNode.locator('.record-status')).toHaveText('Active', { timeout: 30000 });
  record.restored_active = await active();
  expect(record.restored_active).toHaveLength(1);
  expect(record.restored_active[0].id).toBe(originalId);
  record.history_after = await history();
  expect(record.history_after).toEqual(record.history_before);
  record.checks.exact_configuration_run_and_chunk_identity = true;
  record.checks.single_active_pointer_each_stage = true;
  record.checks.history_answers_and_evidence_unchanged = true;
  record.responsive = [];
  for (const width of [320, 390, 768, 1024, 1440, 2560]) {
    await page.setViewportSize({ width, height: 900 });
    const geometry = await page.evaluate(() => ({ viewport: innerWidth, html: document.documentElement.scrollWidth, body: document.body.scrollWidth }));
    expect(geometry.html).toBeLessThanOrEqual(width + 1);
    expect(geometry.body).toBeLessThanOrEqual(width + 1);
    record.responsive.push(geometry);
    if ([390, 1440].includes(width)) {
      await originalNode.scrollIntoViewIfNeeded();
      await page.screenshot({ path: `${output}/restored-release-${width}.png` });
    }
  }
  expect(record.page_errors).toEqual([]);
  record.passed = true;
} catch (error) {
  record.error = diagnostic(error);
  await page.screenshot({ path: `${output}/failure.png` }).catch(() => {});
  throw new Error(record.error);
} finally {
  try {
    await expect.poll(() => inflightMutations.size, { timeout: 150000, intervals: [1000] }).toBe(0);
    record.inflight_mutations_before_final_check = inflightMutations.size;
    const current = await active();
    if (current.length !== 1 || current[0].id !== originalId) {
      record.emergency_restore = await api(page, `/corpus/releases/${originalId}/rollback`, 'POST', {});
      record.passed = false;
    }
    record.final_active_ids = (await active()).map(release => release.id);
  } catch (error) { record.restore_error = diagnostic(error); record.passed = false; }
  await fs.writeFile(`${output}/verification.json`, JSON.stringify(record, null, 2));
  await browser.close();
  if (!record.passed) process.exitCode = 1;
  console.log(JSON.stringify({ passed: record.passed, output, duplicate_release_id: record.receipt?.release_id, final_active_ids: record.final_active_ids, error: record.error, restore_error: record.restore_error }));
}
