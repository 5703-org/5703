import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
const originalId = '39483e7f-efbe-42e7-855e-469fd924383e';
const attempt = JSON.parse(await fs.readFile('../artifacts/reports/frontend/openstax-rollback/2026-09-08T08-36-19-078Z/verification.json', 'utf8'));
const runId = new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-');
const output = `../artifacts/reports/frontend/openstax-rollback-recovery/${runId}`;
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: 'msedge' });
const context = await browser.newContext({ baseURL: 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const record = { passed: false, executed_at: new Date().toISOString(), prior_attempt: 'artifacts/reports/frontend/openstax-rollback/2026-09-08T08-36-19-078Z/verification.json', duplicate_release_id: attempt.receipt.release_id, original_release_id: originalId };
const diagnostic = error => String(error.stack || error).replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi, 'Bearer [redacted]');
async function api(path) { const token = await page.evaluate(() => sessionStorage.getItem('cs30.access-token')); const response = await page.request.get(`/api/v1${path}`, { headers: { Authorization: `Bearer ${token}` } }); expect(response.ok()).toBe(true); return (await response.json()).data; }
try {
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('admin@example.com');
  await page.getByLabel('Password', { exact: true }).fill('Passw0rd!');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeVisible();
  record.before = (await api('/corpus/releases')).filter(release => release.state === 'active');
  expect(record.before).toHaveLength(1);
  await page.goto('/admin/corpus');
  if (record.before[0].id !== originalId) {
    expect(record.before[0].id).toBe(attempt.receipt.release_id);
    const original = attempt.original_active[0];
    const node = page.locator('.record').filter({ has: page.getByRole('heading', { name: original.name, exact: true }) });
    const completed = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/corpus/releases/${originalId}/rollback`), { timeout: 120000 });
    await node.getByRole('button', { name: 'Rollback to this release', exact: true }).click();
    const response = await completed;
    expect(response.status()).toBe(200);
    record.actual_rollback_response = (await response.json()).data;
    await expect(node.locator('.record-status')).toHaveText('Active', { timeout: 30000 });
  }
  record.after = (await api('/corpus/releases')).filter(release => release.state === 'active');
  expect(record.after).toHaveLength(1);
  expect(record.after[0].id).toBe(originalId);
  record.passed = true;
  await page.screenshot({ path: `${output}/restored-original-1440.png` });
} catch (error) { record.error = diagnostic(error); process.exitCode = 1; }
finally { await fs.writeFile(`${output}/verification.json`, JSON.stringify(record, null, 2)); await browser.close(); console.log(JSON.stringify({ passed: record.passed, output, active_ids: record.after?.map(release => release.id), error: record.error })); }
