import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';

const tool = path.resolve('../evaluation/enhancement/highlight_review.html');
const fixturePath = path.resolve('../evaluation/enhancement/highlight_review_input.template.json');
const fixtureBytes = await fs.readFile(fixturePath);
const fixture = JSON.parse(fixtureBytes);
const sha = data => createHash('sha256').update(data).digest('hex');
const runId = new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-');
const output = `../artifacts/reports/frontend/highlight-review/${runId}`;
await fs.mkdir(output, { recursive: true });
const record = { passed: false, executed_at: new Date().toISOString(), evidence_class: 'Automated local-browser functional fixture. Zero human participants; no study ratings or learning/time-effect estimates. Generated fixture downloads are inspected transiently and not delivered as participant measurements.', tool_sha256: sha(await fs.readFile(tool)), fixture_sha256: sha(fixtureBytes), human_participants: 0, actual_network_requests: [], page_errors: [], checks: {} };
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
page.on('pageerror', error => record.page_errors.push(String(error.message)));
page.on('request', request => { if (/^https?:/i.test(request.url())) record.actual_network_requests.push({ method: request.method(), url: request.url() }); });
page.on('dialog', dialog => dialog.accept());
const participant = 'AUTOMATED_FIXTURE_NOT_HUMAN';
async function prepare(input = fixture) {
  await page.goto(pathToFileURL(tool).href);
  await page.getByLabel('Review data file', { exact: true }).setInputFiles({ name: 'authored-format-example.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(input)) });
  await page.getByLabel('Anonymous participant code', { exact: true }).fill(participant);
  await page.getByRole('button', { name: 'Prepare review', exact: true }).click();
}
async function downloaded(name) {
  const waiting = page.waitForEvent('download'); await page.getByRole('button', { name, exact: true }).click();
  const download = await waiting; return JSON.parse(await fs.readFile(await download.path(), 'utf8'));
}
try {
  const invalid = structuredClone(fixture); invalid.items[0].evidence[0].segments[0].text += 'changed';
  await prepare(invalid); await expect(page.getByRole('alert')).toContainText('Both presentations must contain identical source text');
  record.checks.mismatched_text_rejected = true;
  const gold = structuredClone(fixture); gold.items[0].correct_answer = 'Not participant input';
  await prepare(gold); await expect(page.getByRole('alert')).toContainText('Unsupported fields'); record.checks.unexpected_reference_field_rejected = true;
  await prepare(); await expect(page.getByRole('button', { name: 'Start review', exact: true })).toBeVisible();
  expect(await page.getByRole('radio').count()).toBe(0);
  await page.locator('summary').click(); await expect(page.getByRole('button', { name: 'Download analysis key', exact: true })).toBeDisabled();
  const firstKey = await page.evaluate(() => ({ schedule: schedule.map(row => ({ ...row, item_id: data.items[row.item_index].id })), schedule_sha256: scheduleHash }));
  await prepare(); await page.locator('summary').click();
  const repeatedKey = await page.evaluate(() => ({ schedule: schedule.map(row => ({ ...row, item_id: data.items[row.item_index].id })), schedule_sha256: scheduleHash }));
  expect(repeatedKey).toEqual(firstKey); record.checks.fixed_order_reproducible = true;
  const sourceByItem = new Map();
  for (let index = 0; index < firstKey.schedule.length; index++) {
    const row = firstKey.schedule[index]; await page.getByRole('button', { name: 'Start review', exact: true }).click();
    await expect(page.getByRole('heading', { name: `Presentation ${row.presentation_code}`, exact: true })).toBeFocused();
    expect(await page.locator('input[name="support"]:checked').count()).toBe(0);
    const source = await page.locator('.passage').allTextContents();
    if (sourceByItem.has(row.item_id)) expect(source).toEqual(sourceByItem.get(row.item_id)); else sourceByItem.set(row.item_id, source);
    expect(await page.locator('mark').count()).toBe(row.condition === 'highlight' ? 1 : 0);
    if (row.condition === 'highlight' && !record.checks.highlight_screenshot_captured) {
      await page.screenshot({ path: `${output}/desktop-highlight.png`, fullPage: true });
      await page.setViewportSize({ width: 390, height: 844 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      await page.screenshot({ path: `${output}/mobile-highlight.png`, fullPage: true });
      await page.setViewportSize({ width: 1440, height: 1000 }); record.checks.highlight_screenshot_captured = true;
    }
    if (index === 0) {
      await page.screenshot({ path: `${output}/desktop-item.png`, fullPage: true });
      await page.getByRole('button', { name: 'Pause review', exact: true }).click(); await expect(page.locator('#stimulus')).toBeHidden();
      await page.getByRole('button', { name: 'Resume review', exact: true }).click(); await expect(page.locator('#stimulus')).toBeVisible();
      await page.setViewportSize({ width: 390, height: 844 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      await page.screenshot({ path: `${output}/mobile-item.png`, fullPage: true });
      await page.setViewportSize({ width: 1440, height: 1000 });
    }
    await page.getByRole('radio', { name: 'Cannot judge', exact: true }).check();
    await page.getByRole('button', { name: 'Done', exact: true }).click();
  }
  await expect(page.getByRole('status').first()).toContainText('All 4 scheduled presentations completed.');
  await page.getByRole('button', { name: 'Reopen last completed item', exact: true }).click();
  expect(await page.locator('input[name="support"]:checked').count()).toBe(0);
  await page.getByRole('radio', { name: 'Partially supported', exact: true }).check(); await page.getByRole('button', { name: 'Done', exact: true }).click();
  const result = await downloaded('Download judgments');
  const analysisKey = await downloaded('Download analysis key'); expect(analysisKey.schedule_sha256).toBe(firstKey.schedule_sha256);
  expect(result.participant_id).toBe(participant); expect(result.planned_presentations).toBe(4); expect(result.completed_presentations).toBe(4); expect(result.remaining_presentations).toBe(0); expect(result.attempts).toHaveLength(5);
  expect(result.attempts.slice(0, 4).every(item => item.support === 'cannot_judge' && item.attempt === 1 && !item.reopened)).toBe(true);
  expect(result.attempts[4].attempt).toBe(2); expect(result.attempts[4].reopened).toBe(true);
  expect(result.attempts.every(item => item.elapsed_wall_ms >= item.active_visible_ms && item.active_visible_ms >= 0)).toBe(true);
  expect(result.attempts[0].events.map(item => item.kind)).toEqual(['started', 'paused', 'resumed', 'done']);
  expect(result.schedule_sha256).toBe(firstKey.schedule_sha256);
  expect('presentation_mapping' in result).toBe(false); expect(JSON.stringify(result)).not.toContain(fixture.items[0].answer_text);
  record.checks = { ...record.checks, same_source_text_both_presentations: true, correct_mark_only_difference: true, initially_blank_ratings: true, pause_resume_observed: true, keyboard_focus_and_narrow_wrapping: true, earlier_attempts_preserved_on_reopen: true, all_scheduled_denominator_retained: true, judgments_separate_from_analysis_key: true };
  expect(record.actual_network_requests).toEqual([]); expect(record.page_errors).toEqual([]); record.passed = true;
} catch (error) { record.failure = String(error.stack || error); process.exitCode = 1; }
finally { record.finished_at = new Date().toISOString(); await fs.writeFile(`${output}/verification.json`, JSON.stringify(record, null, 2)); await browser.close(); console.log(JSON.stringify({ output, passed: record.passed, failure: record.failure || null })); }
