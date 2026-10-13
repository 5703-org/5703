import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
import { randomUUID, randomBytes, createHash } from 'node:crypto';

const origin = process.env.LEARNING_UI_ORIGIN;
const output = process.env.LEARNING_UI_OUTPUT;
const credentialPath = process.env.LEARNING_UI_CREDENTIALS;
const priorPath = process.env.LEARNING_UI_PRIOR;
if (!origin || !output || !credentialPath || !priorPath || new URL(origin).hostname !== '127.0.0.1') throw new Error('Explicit isolated runtime, private login, prior authored fixture and new output path required.');
await fs.mkdir(output, { recursive: false });
const source = await fs.readFile(new URL(import.meta.url)); await fs.writeFile(path.join(output, 'helper-executed-source.txt'), source);
const hash = value => createHash('sha256').update(value).digest('hex');
const credentials = JSON.parse(await fs.readFile(credentialPath, 'utf8')); const admin = credentials.admin || credentials;
const prior = JSON.parse(await fs.readFile(priorPath, 'utf8')); const item = prior.practice_items.find(value => value.kind === 'step');
if (!item) throw new Error('Prior authored two-step fixture is required.');
const proof = { status: 'running', started_at: new Date().toISOString(), origin, item_id: item.id, helper_sha256: hash(source), scope: 'Actual committed practice POST with its response deliberately lost, then browser reload and exact replay. New authored learner; no answer model calls.', calls: [], page_errors: [] };
async function api(route, method, body, token) { const response = await fetch(`${origin}/api/v1${route}`, { method, signal: AbortSignal.timeout(60000), headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) }); const payload = await response.json(); if (!response.ok) throw new Error(`${method} ${route}: ${response.status} ${payload.error?.code}`); return payload.data; }
const browser = await chromium.launch({ channel: 'msedge' }); const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
page.on('pageerror', error => proof.page_errors.push(error.name));
try {
  const adminToken = (await api('/auth/login', 'POST', { email: admin.email, password: admin.password })).access_token;
  const email = `practice-recovery-${randomUUID()}@example.com`; const password = randomBytes(24).toString('base64url');
  proof.learner_id = (await api('/admin/users', 'POST', { email, password, role: 'student', full_name: 'Lost receipt recovery software check' }, adminToken)).id;
  const token = (await api('/auth/login', 'POST', { email, password })).access_token;
  await page.goto(origin); await page.getByLabel('Email', { exact: true }).fill(email); await page.getByLabel('Password', { exact: true }).fill(password); await page.getByRole('button', { name: 'Sign in', exact: true }).click(); await expect(page.locator('.app-shell')).toBeVisible();
  let originalBody; let savedAttemptId;
  await page.route(`**/api/v1/learning/practice/${item.id}/attempts`, async route => {
    const body = route.request().postDataJSON(); const first = originalBody === undefined;
    if (first) originalBody = body;
    const response = await route.fetch({ timeout: 60000 }); const payload = await response.json();
    proof.calls.push({ status: response.status(), body_sha256: hash(JSON.stringify(body)), idempotency_key_sha256: hash(body.idempotency_key), expected_version: body.expected_version, step: body.response.step, receipt_id: payload.data?.id || null, deliberately_lost_response: first });
    if (first) { if (!response.ok() || !payload.data?.id) throw new Error('Original request did not commit.'); savedAttemptId = payload.data.id; await route.abort('failed'); }
    else { if (proof.calls.length === 2) { expect(body).toEqual(originalBody); expect(payload.data.id).toBe(savedAttemptId); } await route.fulfill({ response }); }
  });
  await page.goto(`${origin}/learn/practice/${item.id}`); await page.getByRole('textbox', { name: 'Your work for this step', exact: true }).fill('ready'); await page.getByRole('button', { name: 'Check my attempt', exact: true }).click(); await expect(page.getByRole('button', { name: 'Check saved attempt', exact: true })).toBeEnabled();
  await page.reload(); await expect(page.getByText('Step 2 of 2', { exact: true })).toBeVisible(); await expect(page.getByLabel('Numeric value', { exact: true })).toHaveValue('');
  await page.getByRole('button', { name: 'Check saved attempt', exact: true }).click(); await expect(page.getByRole('button', { name: 'Check saved attempt', exact: true })).toHaveCount(0);
  const reconciled = await api(`/learning/practice/${item.id}/progress`, 'GET', undefined, token); expect(reconciled.attempts.length).toBe(1); expect(reconciled.attempts[0].id).toBe(savedAttemptId); expect(reconciled.version).toBe(1); proof.reconciled = { attempts: reconciled.attempts.length, version: reconciled.version, current_step: reconciled.current_step };
  await page.screenshot({ path: path.join(output, 'recovered-desktop.png'), fullPage: true });
  await page.getByLabel('Numeric value', { exact: true }).fill('5'); await page.getByLabel('Unit', { exact: true }).fill('mL'); await page.getByRole('button', { name: 'Check my attempt', exact: true }).click(); await expect(page.getByText('All steps are saved. Review your attempts or choose another practice question.')).toBeVisible();
  const complete = await api(`/learning/practice/${item.id}/progress`, 'GET', undefined, token); expect(complete.attempts.length).toBe(2); expect(complete.state).toBe('completed'); proof.completed = { attempts: complete.attempts.length, version: complete.version, state: complete.state };
  await page.setViewportSize({ width: 390, height: 844 }); await page.screenshot({ path: path.join(output, 'completed-mobile.png'), fullPage: true }); expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true); expect(proof.page_errors).toEqual([]); proof.status = 'passed';
} catch (error) { proof.status = 'failed'; proof.failure = String(error.message).replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, '[redacted]'); await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {}); }
finally { proof.completed_at = new Date().toISOString(); await fs.writeFile(path.join(output, 'verification.json'), JSON.stringify(proof, null, 2)); await browser.close(); }
console.log(JSON.stringify({ status: proof.status, output })); if (proof.status !== 'passed') process.exitCode = 1;
