import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import crypto from 'node:crypto';

const buildBytes = await fs.readFile('../evidence/openstax/v5/release-build-completion.json');
const build = JSON.parse(buildBytes);
const historical = JSON.parse(await fs.readFile('../artifacts/reports/frontend/openstax/2026-09-08T08-27-08-234Z/verification.json', 'utf8'));
const oldAnswer = historical.answers[0].answer;
const runId = new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-');
const output = `../artifacts/reports/frontend/openstax-v5/${runId}`;
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: 'msedge' });
const context = await browser.newContext({ baseURL: 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const record = { passed: false, executed_at: new Date().toISOString(), expected_release_id: build.release_id, historical_release_id: historical.expected_release_id, historical_session_id: historical.session_id, evidence_class: 'Focused actual browser/API/worker check after parser-v5 publication: current genuine OpenStax/E5 citations and preserved historical citations; answering remains explicitly mock. No full width-suite repeat or live scientific-quality claim.', build_evidence_sha256: crypto.createHash('sha256').update(buildBytes).digest('hex'), answers: [], source_views: [], page_errors: [] };
const diagnostic = error => String(error.stack || error).replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi, 'Bearer [redacted]');
const chunks = new Set(build.manifest.chunk_ids);
const runs = new Set(build.manifest.processing_run_ids);
page.on('pageerror', error => record.page_errors.push(diagnostic(error)));
async function api(path) {
  const token = await page.evaluate(() => sessionStorage.getItem('cs30.access-token'));
  const response = await page.request.get(`/api/v1${path}`, { headers: { Authorization: `Bearer ${token}` }, timeout: 120000 });
  expect(response.ok(), `${path}: ${response.status()}`).toBe(true);
  return (await response.json()).data;
}
async function send(question) {
  const count = await page.locator('[data-answer-id]').count();
  await page.getByRole('textbox', { name: 'Message Learning Assistant' }).fill(question);
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  await expect(page.locator('[data-answer-id]')).toHaveCount(count + 1, { timeout: 120000 });
  await expect(page.getByRole('button', { name: 'Stop generation', exact: true })).toHaveCount(0);
  const node = page.locator('[data-answer-id]').last();
  const answer = await api(`/answers/${await node.getAttribute('data-answer-id')}`);
  expect(answer.mode).toBe('interactive_chat');
  expect(answer.response_schema).toBe('chat_response_v1');
  expect(answer.model_mode).toBe('mock');
  expect(answer.response.response_type).toBe('answer');
  for (const evidence of answer.evidence) { expect(chunks.has(evidence.chunk_id)).toBe(true); expect(runs.has(evidence.processing_id)).toBe(true); }
  record.answers.push({ question, answer });
  return answer;
}
async function inspectSource(answer, label, width) {
  await page.setViewportSize({ width, height: 1000 });
  const node = page.locator(`[data-answer-id="${answer.id}"]`);
  const source = answer.evidence.find(item => item.evidence_id === answer.response.citations[0]);
  expect(source).toBeTruthy();
  const exact = await api(`/answers/${answer.id}/evidence/${source.evidence_id}`);
  expect(exact).toEqual(source);
  expect(crypto.createHash('sha256').update(exact.text).digest('hex')).toBe(exact.text_hash);
  expect(new URL(exact.source_url).hostname).toMatch(/(^|\.)openstax\.org$/);
  await node.getByRole('button', { name: /^Open source \d+/ }).first().click();
  const modal = page.getByRole('dialog', { name: 'Sources' });
  await expect(modal).toBeVisible();
  await expect(page.locator('.source-passage')).toHaveText(exact.text);
  await expect(page.locator('.source-title')).toHaveText(exact.source_title);
  await expect(page.locator('.source-attribution')).toContainText('OpenStax / Rice University · Access for free at openstax.org');
  await expect(page.locator('.source-locator')).toContainText('PDF physical pages');
  await expect(page.locator('.source-locator')).toContainText('Figures or formulas may require viewing the original PDF.');
  await expect(page.getByRole('link', { name: 'View original source' })).toHaveAttribute('href', exact.source_url);
  await expect(page.getByRole('link', { name: 'View original source' })).toHaveAttribute('rel', 'noopener noreferrer');
  await modal.locator('.data-details summary').click();
  await expect(modal.locator('.data-details pre')).toContainText(exact.license);
  await modal.locator('.data-details summary').click();
  await page.locator('.source-title').scrollIntoViewIfNeeded();
  const geometry = await modal.evaluate(node => { const r = node.getBoundingClientRect(); return { width: innerWidth, left: r.left, right: r.right, modal_client: node.clientWidth, modal_scroll: node.scrollWidth, html: document.documentElement.scrollWidth, body: document.body.scrollWidth }; });
  expect(geometry.left).toBeGreaterThanOrEqual(0);
  expect(geometry.right).toBeLessThanOrEqual(width + 1);
  expect(geometry.modal_scroll).toBeLessThanOrEqual(geometry.modal_client + 1);
  expect(geometry.html).toBeLessThanOrEqual(width + 1);
  expect(geometry.body).toBeLessThanOrEqual(width + 1);
  record.source_views.push({ label, width, answer_id: answer.id, source: exact, geometry });
  await page.screenshot({ path: `${output}/${label}-source-${width}.png` });
  await page.getByRole('button', { name: 'Close sources', exact: true }).click();
}
try {
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('student2@example.com');
  await page.getByLabel('Password', { exact: true }).fill('Passw0rd!');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeVisible();
  record.historical_history_before = await api(`/sessions/${historical.session_id}/messages?limit=100`);
  const current = await send('What is photosynthesis?');
  record.session_id = new URL(page.url()).pathname.split('/')[2];
  await inspectSource(current, 'current', 1440);
  const followup = await send('Why does it need light?');
  expect(followup.conversation_snapshot.messages.length).toBeGreaterThanOrEqual(2);
  await inspectSource(current, 'current', 390);
  await page.goto(`/chat/${historical.session_id}`);
  await expect(page.locator(`[data-answer-id="${oldAnswer.id}"]`)).toBeVisible();
  const saved = await api(`/answers/${oldAnswer.id}`);
  expect(saved.response).toEqual(oldAnswer.response);
  expect(saved.evidence).toEqual(oldAnswer.evidence);
  await inspectSource(saved, 'historical', 390);
  await inspectSource(saved, 'historical', 1440);
  record.historical_history_after = await api(`/sessions/${historical.session_id}/messages?limit=100`);
  expect(record.historical_history_after).toEqual(record.historical_history_before);
  record.checks = { current_v5_chunk_and_run_membership: true, actual_two_turn_conversation: true, exact_source_hash_title_text_license_link: true, current_and_historical_source_views: true, historical_response_evidence_history_unchanged: true, source_bounds_390_and_1440: true };
  expect(record.page_errors).toEqual([]);
  record.passed = true;
} catch (error) {
  record.error = diagnostic(error);
  await page.screenshot({ path: `${output}/failure.png` }).catch(() => {});
  process.exitCode = 1;
} finally {
  await fs.writeFile(`${output}/verification.json`, JSON.stringify(record, null, 2));
  await browser.close();
  console.log(JSON.stringify({ passed: record.passed, output, session_id: record.session_id, error: record.error }));
}
